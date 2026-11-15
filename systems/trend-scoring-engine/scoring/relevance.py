"""Vertical, audience, and reframe scoring - keyword-density based.

vertical_relevance:  which configured vertical does this trend hit hardest?
audience_match:      B2B operator language vs consumer language ratio
reframe_potential:   does the trend support Input-Quality, Opportunity-Cost, or Denominator reframe?
"""
from __future__ import annotations


def vertical_relevance(text: str, verticals: dict) -> tuple[float, str]:
    """Score 0..1 per vertical based on keyword hits (capped at 3 hits = 1.0).
    Returns (best_score, best_vertical_name). When no vertical keyword hits,
    tag is 'general' rather than arbitrarily defaulting to the first dict key."""
    t = text.lower()
    if not verticals:
        return 0.0, "general"
    scores = {}
    for v, kws in verticals.items():
        hits = sum(1 for kw in (kws or []) if kw.lower() in t)
        scores[v] = min(hits / 3.0, 1.0)
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return 0.0, "general"
    return scores[best], best


def audience_match(text: str, signals: dict) -> float:
    """B2B vs consumer signal ratio. Neutral 0.40 when no signals are present."""
    t = text.lower()
    b2b_terms = (signals or {}).get("b2b", []) or []
    consumer_terms = (signals or {}).get("consumer", []) or []
    b2b = sum(1 for s in b2b_terms if s.lower() in t)
    consumer = sum(1 for s in consumer_terms if s.lower() in t)
    if b2b + consumer == 0:
        return 0.40
    return b2b / (b2b + consumer)


def reframe_potential(text: str, triggers: dict) -> tuple[float, str]:
    """Score per reframe type based on trigger word presence (capped at 2 hits = 1.0).
    Returns (best_score, best_reframe_name)."""
    t = text.lower()
    if not triggers:
        return 0.0, ""
    scores = {}
    for name, trgs in triggers.items():
        hits = sum(1 for trg in (trgs or []) if trg.lower() in t)
        scores[name] = min(hits / 2.0, 1.0)
    best = max(scores, key=scores.get)
    return scores[best], best
