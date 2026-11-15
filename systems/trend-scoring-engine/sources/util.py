"""Shared utilities for source fetchers.

stable_id: deterministic short hash for canonical trend IDs.
now_iso:   UTC ISO8601 timestamp string.
Error classes: RateLimitError, APIError, ConfigError - caught individually by runner.py.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone


class RateLimitError(Exception):
    def __init__(self, retry_after: int = 60, message: str = ""):
        super().__init__(message or f"rate limited; retry after {retry_after}s")
        self.retry_after = retry_after


class APIError(Exception):
    pass


class ConfigError(Exception):
    pass


def stable_id(*parts) -> str:
    """12-char hex from sha256 of pipe-joined parts. Same inputs always yield same id."""
    raw = "|".join(str(p) for p in parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_required_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise ConfigError(f"Missing required env var: {name}")
    return v
