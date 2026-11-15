"""Recency decay and engagement signal-strength scoring.

recency:         exp(-age_days/decay_days). Day 0 = 1.0, decay_days = ~0.37.
signal_strength: log10(engagement+1) / log10(baseline+1), capped at 1.0.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone


def recency(first_seen: str, decay_days: float = 5.0) -> float:
    """Exponential decay on trend age. Returns 0.0 if timestamp is unparseable."""
    if not first_seen:
        return 0.0
    try:
        seen = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return 0.0
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - seen).total_seconds() / 86400
    if age_days < 0:
        return 1.0  # future timestamp; treat as fresh
    return math.exp(-age_days / decay_days)


def signal_strength(engagement: int, source: str, baselines: dict) -> float:
    """Log-normalize engagement against per-source baseline. Returns 0..1."""
    if engagement is None or engagement <= 0:
        return 0.0
    base = (baselines or {}).get(source, 100)
    return min(math.log10(engagement + 1) / math.log10(base + 1), 1.0)
