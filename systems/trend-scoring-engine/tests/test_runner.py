"""Failure handling in runner.py: one bad source never sinks the refresh. No network calls."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import runner  # noqa: E402
from sources.util import APIError, RateLimitError  # noqa: E402


def _isolate(monkeypatch, tmp_path, fn):
    monkeypatch.setattr(runner, "DATA", str(tmp_path))
    monkeypatch.setattr(runner, "_fetcher_for", lambda name, config: (fn, []))


def test_rate_limit_is_logged_and_keeps_last_ok(monkeypatch, tmp_path):
    def boom():
        raise RateLimitError(retry_after=120)
    _isolate(monkeypatch, tmp_path, boom)
    results, health = runner.fetch_one("reddit", {}, {"reddit": {"last_ok": "2026-01-01T00:00:00Z"}})
    assert results == []
    assert health == {"status": "rate_limited", "retry_after": 120, "last_ok": "2026-01-01T00:00:00Z"}
    assert "rate_limit" in (tmp_path / "errors.log").read_text()


def test_unexpected_error_does_not_raise(monkeypatch, tmp_path):
    def boom():
        raise APIError("upstream 500")
    _isolate(monkeypatch, tmp_path, boom)
    _, health = runner.fetch_one("twitter", {}, {})
    assert health["status"] == "error"


def test_prior_trends_survive_a_failed_source():
    config = runner.load_config()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prior = [{
        "id": "old1",
        "source": "twitter",
        "title": "HVAC contractor lead quality: junk leads and dead leads",
        "text": "Roofing contractor owners say lead quality fell. Bad leads, wasted dials, close rate down.",
        "first_seen": now,
        "engagement": 900,
        "scores": {"total": 0.9},
    }]
    merged = runner.merge_with_prior([], prior, {"twitter"}, config)
    assert [t["id"] for t in merged] == ["old1"]
    assert merged[0]["scores"]["total"] != 0.9  # re-scored against the current time
