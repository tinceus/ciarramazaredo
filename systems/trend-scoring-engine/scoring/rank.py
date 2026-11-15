"""Composite scoring + ranking + cross-source dedup.

score_one:           score one canonical trend record against config
cross_source_dedup:  merge near-duplicate titles across sources, keep highest engagement
score_and_rank:      full pipeline - id-dedup, score, threshold, dedup, sort, truncate
"""
from __future__ import annotations

import logging

from .compliance import is_compliant
from .recency_signal import recency, signal_strength
from .relevance import audience_match, reframe_potential, vertical_relevance

LOG = logging.getLogger(__name__)


def score_one(trend: dict, config: dict) -> dict | None:
    """Score one trend. Returns enriched trend, or {..., rejected: True} if compliance fails."""
    text = f"{trend.get('title', '')} {trend.get('text', '')}".strip()

    ok, reason = is_compliant(
        text,
        config.get("red_lines", []) or [],
        config.get("prospect_blame", []) or [],
    )
    if not ok:
        return {**trend, "rejected": True, "rejection_reason": reason}

    keywords = config.get("keywords", {}) or {}
    v_score, vertical = vertical_relevance(text, keywords.get("verticals", {}) or {})
    a_score = audience_match(text, config.get("audience_signals", {}) or {})
    r_score, reframe = reframe_potential(text, config.get("reframe_triggers", {}) or {})
    rec_score = recency(trend.get("first_seen", ""))
    sig_score = signal_strength(
        int(trend.get("engagement") or 0),
        trend.get("source", ""),
        config.get("source_baselines", {}) or {},
    )

    weights = config.get("weights", {}) or {}
    src_w = (config.get("source_weights", {}) or {}).get(trend.get("source"), 1.0)

    total = src_w * (
        weights.get("vertical", 0.30) * v_score
        + weights.get("audience", 0.20) * a_score
        + weights.get("reframe", 0.25) * r_score
        + weights.get("recency", 0.15) * rec_score
        + weights.get("signal", 0.10) * sig_score
    )

    return {
        **trend,
        "scores": {
            "vertical": round(v_score, 3),
            "audience": round(a_score, 3),
            "reframe": round(r_score, 3),
            "recency": round(rec_score, 3),
            "signal": round(sig_score, 3),
            "total": round(total, 3),
        },
        "tagged_vertical": vertical,
        "tagged_reframe": reframe,
    }


def _shingles(text: str, n: int = 4) -> set:
    """4-shingle tokens for cross-source title similarity."""
    tokens = (text or "").lower().split()
    if len(tokens) < n:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def cross_source_dedup(trends: list[dict], threshold: float = 0.85) -> list[dict]:
    """Merge trends with near-duplicate titles. Keeps record with highest engagement;
    annotates context.cross_source with all merged source names."""
    if not trends:
        return []
    shingles = [(t, _shingles(t.get("title", ""))) for t in trends]
    out = []
    used = [False] * len(trends)
    for i, (t_i, sh_i) in enumerate(shingles):
        if used[i]:
            continue
        cluster = [t_i]
        for j in range(i + 1, len(trends)):
            if used[j]:
                continue
            t_j, sh_j = shingles[j]
            if _jaccard(sh_i, sh_j) >= threshold:
                cluster.append(t_j)
                used[j] = True
        used[i] = True
        if len(cluster) == 1:
            out.append(t_i)
        else:
            best = max(cluster, key=lambda c: int(c.get("engagement") or 0))
            merged = {
                **best,
                "context": {
                    **(best.get("context") or {}),
                    "cross_source": sorted({c.get("source") for c in cluster if c.get("source")}),
                },
            }
            out.append(merged)
    return out


def score_and_rank(raw: list[dict], config: dict) -> list[dict]:
    """Full pipeline: id-dedup, score, threshold, cross-source dedup, sort, truncate to max_cache_size."""
    seen_ids = set()
    scored = []
    rejected = 0
    for t in raw:
        tid = t.get("id")
        if not tid or tid in seen_ids:
            continue
        seen_ids.add(tid)
        s = score_one(t, config)
        if s is None:
            continue
        if s.get("rejected"):
            rejected += 1
            continue
        threshold = (config.get("thresholds") or {}).get("cache_inclusion", 0.50)
        if s["scores"]["total"] >= threshold:
            scored.append(s)

    LOG.info(
        "score_and_rank: %d raw, %d compliance-rejected, %d above threshold (%.2f)",
        len(raw), rejected, len(scored),
        (config.get("thresholds") or {}).get("cache_inclusion", 0.50),
    )

    scored = cross_source_dedup(scored)
    scored.sort(key=lambda x: x["scores"]["total"], reverse=True)

    return scored[: config.get("max_cache_size", 100)]
