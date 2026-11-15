"""Offline tests for compliance + scoring + ranking. No network calls. Fictional text only."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from scoring.compliance import is_compliant
from scoring.rank import cross_source_dedup, score_and_rank, score_one
from scoring.recency_signal import recency, signal_strength
from scoring.relevance import audience_match, reframe_potential, vertical_relevance


def _today_iso(offset_days: int = 0) -> str:
    dt = datetime.now(timezone.utc) + timedelta(days=offset_days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture
def config():
    with open(os.path.join(ROOT, "config.yaml")) as f:
        return yaml.safe_load(f)


def _check(config, text):
    return is_compliant(text, config["red_lines"], config["prospect_blame"])


# ---------- Compliance: red lines ----------

def test_red_line_free_install_rejected(config):
    ok, reason = _check(config, "Get a free install on your new roof")
    assert not ok
    assert "free install" in reason


def test_red_line_guaranteed_savings_rejected(config):
    ok, reason = _check(config, "guaranteed savings on your monthly bill")
    assert not ok
    assert "guaranteed savings" in reason


def test_red_line_government_pays_rejected(config):
    ok, reason = _check(config, "the government pays for your whole plan")
    assert not ok
    assert "government pays for" in reason


def test_red_line_case_insensitive(config):
    ok, _ = _check(config, "GUARANTEED RESULTS for everyone")
    assert not ok


# ---------- Compliance: prospect blame ----------

def test_prospect_blame_rejected(config):
    ok, reason = _check(config, "honestly all sales reps lie and contractors are scammers")
    assert not ok
    assert "prospect_blame" in reason


def test_compliant_text_passes(config):
    ok, reason = _check(config, "How contractors handle bad lead quality at scale")
    assert ok
    assert reason is None


# ---------- Vertical relevance ----------

def test_vertical_relevance_home_services(config):
    score, vertical = vertical_relevance(
        "HVAC and roofing contractor owners compare home services lead vendors",
        config["keywords"]["verticals"],
    )
    assert vertical == "home_services"
    assert score >= 0.66  # 2-3 hits / 3


def test_vertical_relevance_legal(config):
    score, vertical = vertical_relevance(
        "Personal injury law firm case intake is slower this quarter",
        config["keywords"]["verticals"],
    )
    assert vertical == "legal"
    assert score > 0


def test_vertical_relevance_dental(config):
    score, vertical = vertical_relevance(
        "Dental practice owners say new patient calls are up but chair time is flat",
        config["keywords"]["verticals"],
    )
    assert vertical == "dental"
    assert score > 0


def test_vertical_relevance_empty_input(config):
    score, vertical = vertical_relevance("totally unrelated content about cooking", config["keywords"]["verticals"])
    assert score == 0
    assert vertical == "general"


# ---------- Audience match ----------

def test_audience_match_b2b(config):
    score = audience_match(
        "Our close rate dropped because lead quality crashed and CPL is fine but rep productivity tanked",
        config["audience_signals"],
    )
    assert score > 0.7


def test_audience_match_consumer(config):
    score = audience_match(
        "Should I get a new roof for my home? My bill is high, is it worth it",
        config["audience_signals"],
    )
    assert score < 0.5


def test_audience_match_neutral_default(config):
    score = audience_match("Random text with no signals at all", config["audience_signals"])
    assert score == 0.40


# ---------- Reframe potential ----------

def test_reframe_opportunity_cost(config):
    score, reframe = reframe_potential(
        "That was a wasted hour on a dead lead my best closer cannot touch",
        config["reframe_triggers"],
    )
    assert reframe == "opportunity_cost"
    assert score > 0


def test_reframe_input_quality(config):
    score, reframe = reframe_potential(
        "Junk leads, every batch. Total tire kickers, dead-lead city, wasted dial after wasted dial",
        config["reframe_triggers"],
    )
    assert reframe == "input_quality"
    assert score > 0


def test_reframe_denominator(config):
    score, reframe = reframe_potential(
        "Our close rate looks fine but the team passed on most of them and quietly rejected the rest",
        config["reframe_triggers"],
    )
    assert reframe == "denominator"
    assert score > 0


# ---------- Recency decay ----------

def test_recency_today_is_full():
    assert recency(_today_iso()) > 0.99


def test_recency_5_days_decays_to_e_inverse():
    # decay_days=5.0, age=5 days -> exp(-1), about 0.367
    score = recency(_today_iso(offset_days=-5), decay_days=5.0)
    assert 0.30 < score < 0.45


def test_recency_garbage_input_returns_zero():
    assert recency("not a timestamp") == 0.0
    assert recency("") == 0.0
    assert recency(None) == 0.0


def test_recency_future_timestamp_treated_fresh():
    assert recency(_today_iso(offset_days=1)) >= 0.99


# ---------- Signal strength ----------

def test_signal_strength_zero():
    assert signal_strength(0, "reddit", {"reddit": 1000}) == 0.0


def test_signal_strength_at_baseline():
    assert 0.99 <= signal_strength(1000, "reddit", {"reddit": 1000}) <= 1.0


def test_signal_strength_above_baseline_caps():
    assert signal_strength(100000, "reddit", {"reddit": 1000}) == 1.0


def test_signal_strength_unknown_source_uses_default():
    score = signal_strength(50, "unknown_source", {"reddit": 1000})
    assert 0 < score < 1.0  # default baseline = 100


# ---------- score_one integration ----------

def test_score_one_drops_red_line(config):
    trend = {
        "id": "test1",
        "source": "reddit",
        "title": "Free install from the government",
        "text": "Free install, the government pays for all of it",
        "first_seen": _today_iso(),
        "engagement": 500,
    }
    result = score_one(trend, config)
    assert result.get("rejected")
    assert "red_line" in result.get("rejection_reason", "")


def test_score_one_clean_home_services_b2b_topic(config):
    trend = {
        "id": "test2",
        "source": "reddit",
        "title": "HVAC contractor: dealing with bad leads from aggregators",
        "text": "Roofing and HVAC contractor owners venting about junk leads and lead quality issues. Dead leads everywhere; wasted dials all day.",
        "first_seen": _today_iso(),
        "engagement": 800,
    }
    result = score_one(trend, config)
    assert not result.get("rejected")
    assert result["scores"]["total"] > 0.5
    assert result["tagged_vertical"] == "home_services"
    assert result["tagged_reframe"] == "input_quality"


def test_score_total_caps_at_one(config):
    text = (
        "home services hvac roofing plumbing contractor "
        "lead quality close rate CPL pipeline rep productivity "
        "lead quality bad leads dead lead junk leads wasted dial scrub"
    )
    trend = {
        "id": "test3",
        "source": "google_trends",
        "title": text,
        "text": text,
        "first_seen": _today_iso(),
        "engagement": 100000,
    }
    result = score_one(trend, config)
    assert not result.get("rejected")
    assert result["scores"]["total"] <= 1.0


# ---------- Cross-source dedup ----------

def test_cross_source_dedup_merges_near_duplicates():
    a = {"id": "a", "source": "reddit", "title": "Contractor lead quality is terrible right now everyone", "engagement": 500}
    b = {"id": "b", "source": "twitter", "title": "Contractor lead quality is terrible right now everyone", "engagement": 1000}
    out = cross_source_dedup([a, b], threshold=0.85)
    assert len(out) == 1
    assert out[0]["id"] == "b"
    assert set(out[0]["context"]["cross_source"]) == {"reddit", "twitter"}


def test_cross_source_dedup_keeps_distinct():
    a = {"id": "a", "source": "reddit", "title": "Contractor lead quality is terrible right now and getting worse", "engagement": 500}
    b = {"id": "b", "source": "twitter", "title": "Law firm intake teams are drowning in call volume this year", "engagement": 1000}
    out = cross_source_dedup([a, b], threshold=0.85)
    assert len(out) == 2


# ---------- score_and_rank pipeline ----------

STRONG = {
    "id": "high",
    "source": "reddit",
    "title": "Contractor lead quality crisis: dead leads everywhere",
    "text": "Lead quality has crashed for HVAC and roofing contractor owners. Dead leads, junk leads, tire kickers. Best closers wasted on bad leads. CPL is fine but margin is tanking.",
    "engagement": 800,
}


def test_score_and_rank_admits_strong_trends(config):
    out = score_and_rank([{**STRONG, "first_seen": _today_iso()}], config)
    assert "high" in {t["id"] for t in out}


def test_score_and_rank_dedups_by_id(config):
    same = {**STRONG, "id": "duplicate", "first_seen": _today_iso()}
    out = score_and_rank([same, dict(same), dict(same)], config)
    assert len([t for t in out if t["id"] == "duplicate"]) == 1


def test_score_and_rank_filters_compliance_violations(config):
    raw = [{
        "id": "bad",
        "source": "reddit",
        "title": "Free install with guaranteed savings",
        "text": "free install with guaranteed savings",
        "first_seen": _today_iso(),
        "engagement": 5000,
    }]
    assert score_and_rank(raw, config) == []
