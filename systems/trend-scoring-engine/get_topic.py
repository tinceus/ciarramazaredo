#!/usr/bin/env python3
"""get_topic.py: surface ONE topic recommendation. Always returns something.

3-tier fallback:
  1. data/trends.json      (live cache, written by runner.py on a daily schedule)
  2. seed_topics.json      (curated evergreen topics, versioned with the code)
  3. INLINE_SEEDS below    (last resort, cannot fail)

Output: a structured Markdown trend brief on stdout. A writer (or an LLM step)
turns the brief into a publish-ready topic card.

Usage:
    python3 get_topic.py                       # any vertical
    python3 get_topic.py --vertical legal
    python3 get_topic.py --no-mark-served      # preview without dedup
    python3 get_topic.py --json                # raw JSON instead of Markdown
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
SEEDS = os.path.join(ROOT, "seed_topics.json")
SERVE_DEDUP_DAYS = 14

VERTICAL_ALIASES = {
    "home": "home_services",
    "home_services": "home_services",
    "legal": "legal",
    "law": "legal",
    "dental": "dental",
    "general": "general",
}

REFRAME_HUMAN = {
    "input_quality": "Input-Quality",
    "opportunity_cost": "Opportunity-Cost",
    "denominator": "Denominator",
}

REFRAME_BIAS = {
    "input_quality": "cost-invisibility",
    "opportunity_cost": "allocation bias",
    "denominator": "survivorship bias",
}

VERTICAL_ACCOUNT = {
    "home_services": "Account A (home services)",
    "legal": "Account B (legal)",
    "dental": "Account C (dental)",
    "general": "Main brand account",
}

# Last-resort fallback, used only when both trends.json and seed_topics.json are
# missing or empty. Fictional examples. Each passes the red-line and prospect-blame filters.
INLINE_SEEDS = [
    {
        "id": "inline_home_001",
        "source": "seed",
        "title": "Contractors tracking cost per lead but not cost per booked job",
        "text": "Home services owners compare vendors on cost per lead. The number that decides margin is cost per booked job, and junk leads hide inside the cheaper price.",
        "first_seen": "2026-01-01T00:00:00Z",
        "engagement": 100,
        "metric": {"sourced_from": "example only; verify against your own CRM"},
        "context": {"claim_to_verify": "booked-job rate by vendor"},
        "scores": {"total": 0.78, "vertical": 1.0, "audience": 0.85, "reframe": 1.0, "recency": 0.5, "signal": 0.4},
        "tagged_vertical": "home_services",
        "tagged_reframe": "input_quality",
    },
    {
        "id": "inline_legal_001",
        "source": "seed",
        "title": "Intake close rate hides the leads your team quietly skips",
        "text": "Law firm intake teams report a healthy close rate while signed cases stay flat. The denominator is wrong: leads the team passed on never enter the math.",
        "first_seen": "2026-01-01T00:00:00Z",
        "engagement": 100,
        "metric": {"sourced_from": "example only; verify with intake disposition codes"},
        "context": {"claim_to_verify": "skip rate range"},
        "scores": {"total": 0.74, "vertical": 0.85, "audience": 0.90, "reframe": 1.0, "recency": 0.5, "signal": 0.4},
        "tagged_vertical": "legal",
        "tagged_reframe": "denominator",
    },
    {
        "id": "inline_dental_001",
        "source": "seed",
        "title": "The front-desk hour spent on a tire-kicker lead",
        "text": "Dental practices measure booking rate against total calls and miss the staff time lost on tire-kicker leads. That hour was not spent on a patient who would have booked.",
        "first_seen": "2026-01-01T00:00:00Z",
        "engagement": 100,
        "metric": {"sourced_from": "example only; verify with call logs"},
        "context": {"claim_to_verify": "staff time per unqualified call"},
        "scores": {"total": 0.74, "vertical": 0.85, "audience": 0.90, "reframe": 1.0, "recency": 0.5, "signal": 0.4},
        "tagged_vertical": "dental",
        "tagged_reframe": "opportunity_cost",
    },
]


def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def get_candidate_pool() -> tuple[list, str, str | None]:
    """Returns (trends_list, tier_name, last_refresh_iso). Never raises."""
    cache = load_json(os.path.join(DATA, "trends.json"), {})
    trends = cache.get("trends") or []
    if trends:
        return trends, "live", cache.get("last_refresh")

    seeds = load_json(SEEDS, {})
    seed_list = seeds.get("topics") or []
    if seed_list:
        return seed_list, "seed_file", None

    return INLINE_SEEDS, "inline_fallback", None


def get_served_ids(window_days: int = SERVE_DEDUP_DAYS) -> set:
    served = load_json(os.path.join(DATA, "served.json"), {"served": []})
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    out = set()
    for entry in served.get("served", []):
        try:
            served_at = datetime.fromisoformat(str(entry.get("served_at")).replace("Z", "+00:00"))
            if served_at >= cutoff:
                out.add(entry.get("id"))
        except (ValueError, TypeError):
            pass
    return out


def append_served(trend: dict) -> None:
    path = os.path.join(DATA, "served.json")
    served = load_json(path, {"served": []})
    served["served"].append({
        "id": trend.get("id"),
        "served_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "topic_title": (trend.get("title") or "")[:200],
    })
    os.makedirs(DATA, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(served, f, indent=2)
    os.replace(tmp, path)


def format_source(trend: dict) -> str:
    src = trend.get("source", "unknown")
    metric = trend.get("metric") or {}
    ctx = trend.get("context") or {}
    if src == "google_trends":
        ev = metric.get("extracted_value")
        return f"Google Trends: '{trend.get('title')}' rising query" + (f", +{ev}% week-over-week" if ev else "")
    if src == "reddit":
        return f"r/{ctx.get('subreddit', '?')}: {metric.get('upvotes', 0)} upvotes, {metric.get('comments', 0)} comments"
    if src == "twitter":
        parts = [f"{metric.get('likes', 0)} likes", f"{metric.get('retweets', 0)} retweets", f"{metric.get('replies', 0)} replies"]
        return "X: " + ", ".join(parts)
    if src == "instagram":
        return f"Instagram: {metric.get('likes', 0)} likes, {metric.get('comments', 0)} comments"
    if src == "tiktok":
        plays = metric.get("plays", 0)
        return f"TikTok: {plays:,} plays, {metric.get('diggs', 0)} likes, {metric.get('shares', 0)} shares" if plays else f"TikTok: {metric.get('diggs', 0)} likes"
    if src == "seed":
        return "Curated evergreen seed (compliance pre-vetted)"
    return src


def format_brief(trend: dict, tier: str, last_refresh: str | None, fallback_notes: list) -> str:
    title = (trend.get("title") or "").strip()
    if len(title) > 110:
        title = title[:107] + "..."
    body = (trend.get("text") or "").strip()
    if len(body) > 600:
        body = body[:597] + "..."
    scores = trend.get("scores") or {}
    reframe = trend.get("tagged_reframe", "input_quality")
    vertical = trend.get("tagged_vertical", "general")
    src_display = format_source(trend)

    out = list(fallback_notes)
    if fallback_notes:
        out.append("")

    out.append("# Topic Brief")
    out.append("")
    out.append(f"**Topic candidate:** {title}")
    out.append("")
    out.append(f"**Trend Source:** {src_display}")
    if trend.get("url"):
        out.append(f"**Link:** {trend['url']}")
    out.append("")
    out.append("**Raw signal text:**")
    out.append(f"> {body}")
    out.append("")
    out.append(f"**Detected vertical:** `{vertical}`")
    out.append(f"**Detected reframe:** {REFRAME_HUMAN.get(reframe, reframe)}")
    out.append(f"**Behavioral bias to leverage:** {REFRAME_BIAS.get(reframe, '?')}")
    out.append(f"**Suggested account:** {VERTICAL_ACCOUNT.get(vertical, VERTICAL_ACCOUNT['general'])}")
    out.append("")
    out.append("**Scores:** "
               f"total={scores.get('total', '?')}, "
               f"vertical={scores.get('vertical', '?')}, "
               f"audience={scores.get('audience', '?')}, "
               f"reframe={scores.get('reframe', '?')}, "
               f"recency={scores.get('recency', '?')}, "
               f"signal={scores.get('signal', '?')}")
    out.append(f"**Trend ID:** `{trend.get('id', '?')}`")
    out.append(f"**Source tier:** {tier}" + (f" (refreshed {last_refresh})" if last_refresh else ""))
    out.append("")
    out.append("---")
    out.append("")
    out.append("## Next step: turn the brief into a topic card")
    out.append("")
    out.append("- **Topic** (6-12 words, no clickbait)")
    out.append("- **Trend Source** (the metric line above, verbatim)")
    out.append("- **Why it lands for the buyer** (2 sentences: pain point + vertical fit)")
    out.append("- **Reframe / Bias / Awareness stage**")
    out.append("- **Metric-led hook** (only the metric shown above, no invented numbers, max 22 words)")
    out.append("- **Claims to verify before publishing** (2 claims, each with a source)")
    out.append("- **Suggested format** and **suggested account**")
    out.append("")
    out.append("**Gates** (these override everything else):")
    out.append("- Villain = the system (bad data, broken process), never the prospect")
    out.append("- Red lines: no free-offer framing, no unqualified savings guarantees, no government-program language")
    out.append("- Numeric anchor: use only the metrics shown above")
    out.append("- Voice: calm, advisory, data-backed. No exclamation marks. No urgency tactics.")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Surface one topic recommendation")
    parser.add_argument("--vertical", help="Filter to vertical: " + " | ".join(sorted(set(VERTICAL_ALIASES))))
    parser.add_argument("--no-mark-served", action="store_true", help="Don't update served.json")
    parser.add_argument("--json", action="store_true", help="Output raw JSON of selected trend instead of Markdown")
    args = parser.parse_args()

    requested_vertical = None
    if args.vertical:
        requested_vertical = VERTICAL_ALIASES.get(args.vertical.lower())
        if not requested_vertical:
            print(f"Unknown vertical '{args.vertical}'. Use: {', '.join(sorted(set(VERTICAL_ALIASES)))}", file=sys.stderr)
            return 2

    pool, tier, last_refresh = get_candidate_pool()
    served = get_served_ids()
    fallback_notes = []

    if tier == "seed_file":
        fallback_notes.append("> **Live cache empty.** Serving from the curated seed bank. Run `python3 runner.py --refresh` to repopulate.")
    elif tier == "inline_fallback":
        fallback_notes.append("> **Live cache and seed bank both unavailable.** Serving from the inline fallback. Run `python3 runner.py --refresh` and check `seed_topics.json`.")

    candidates = [t for t in pool if t.get("id") not in served]
    if requested_vertical:
        filtered = [t for t in candidates if t.get("tagged_vertical") == requested_vertical]
        if not filtered and candidates:
            fallback_notes.append(f"> **No qualifying `{requested_vertical}` topics.** Showing the top topic from any vertical instead.")
        else:
            candidates = filtered

    candidates.sort(key=lambda t: (t.get("scores") or {}).get("total", 0), reverse=True)

    if not candidates and pool:
        fallback_notes.append(f"> **All topics served in the last {SERVE_DEDUP_DAYS} days.** Re-serving the highest-scored anyway.")
        candidates = sorted(pool, key=lambda t: (t.get("scores") or {}).get("total", 0), reverse=True)
        if requested_vertical:
            v_filtered = [t for t in candidates if t.get("tagged_vertical") == requested_vertical]
            if v_filtered:
                candidates = v_filtered

    if not candidates:
        print("ERROR: No topics available in any tier. Run `python3 runner.py --refresh` and confirm `seed_topics.json` exists.", file=sys.stderr)
        return 1

    pick = candidates[0]

    if args.json:
        print(json.dumps({
            "trend": pick,
            "tier": tier,
            "last_refresh": last_refresh,
            "fallback_notes": fallback_notes,
        }, indent=2, default=str))
    else:
        print(format_brief(pick, tier, last_refresh, fallback_notes))

    if not args.no_mark_served:
        try:
            append_served(pick)
        except OSError as e:
            print(f"\n# Note: could not update served.json ({e}). Topic was served but dedup history not recorded.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
