#!/usr/bin/env python
"""runner.py - fetch, score, and cache trends for the trend scoring engine.

Modes:
  python runner.py                  # refresh only if stale (>24h)
  python runner.py --refresh        # force refresh of all sources
  python runner.py --source reddit --refresh   # refresh one source
  python runner.py --print-status   # print cache freshness + source health, exit
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, ROOT)

# Optional .env loading; fine if dotenv is missing or .env doesn't exist
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass

from scoring.rank import score_and_rank, score_one  # noqa: E402
from sources import (  # noqa: E402
    apify_instagram,
    apify_tiktok,
    apify_twitter,
    reddit_public,
    serpapi_google_trends,
)
from sources.util import APIError, ConfigError, RateLimitError, now_iso  # noqa: E402

logging.basicConfig(
    level=os.environ.get("TRENDS_LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
LOG = logging.getLogger("runner")

SOURCES = ["google_trends", "reddit", "twitter", "instagram", "tiktok"]


def _fetcher_for(name: str, config: dict):
    """Returns (callable, args) tuple for the named source."""
    src_cfg = config.get("sources", {}) or {}
    if name == "google_trends":
        return serpapi_google_trends.fetch, [config["keywords"]["all"]]
    if name == "reddit":
        c = src_cfg.get("reddit", {})
        return reddit_public.fetch, [c.get("subreddits", []), c.get("max_items", 200)]
    if name == "twitter":
        c = src_cfg.get("twitter", {})
        return apify_twitter.fetch, [c.get("search_terms", []), c.get("max_items", 200)]
    if name == "instagram":
        c = src_cfg.get("instagram", {})
        return apify_instagram.fetch, [c.get("hashtags", []), c.get("max_items", 50)]
    if name == "tiktok":
        c = src_cfg.get("tiktok", {})
        return apify_tiktok.fetch, [c.get("hashtags", []), c.get("max_items", 50)]
    raise ValueError(f"Unknown source: {name}")


def load_config() -> dict:
    with open(os.path.join(ROOT, "config.yaml")) as f:
        return yaml.safe_load(f)


def load_cache(filename: str, default):
    path = os.path.join(DATA, filename)
    if not os.path.exists(path):
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        LOG.warning("Corrupt cache %s (%s); using default", filename, e)
        return default


def save_cache(filename: str, data) -> None:
    os.makedirs(DATA, exist_ok=True)
    path = os.path.join(DATA, filename)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(tmp, path)


def is_stale(last_iso, max_h: int) -> bool:
    if not last_iso:
        return True
    try:
        last = datetime.fromisoformat(str(last_iso).replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return True
    return (datetime.now(timezone.utc) - last) > timedelta(hours=max_h)


def log_error(source: str, kind: str, exc: Exception, extra: dict = None) -> None:
    entry = {
        "ts": now_iso(),
        "source": source,
        "kind": kind,
        "msg": str(exc)[:500],
    }
    if extra:
        entry.update(extra)
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "errors.log"), "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def fetch_one(name: str, config: dict, prior_health: dict):
    fetcher, args = _fetcher_for(name, config)
    last_ok = (prior_health.get(name) or {}).get("last_ok")
    try:
        results = fetcher(*args)
        return results, {"status": "ok", "count": len(results), "last_ok": now_iso()}
    except RateLimitError as e:
        log_error(name, "rate_limit", e, {"retry_after": e.retry_after})
        return [], {"status": "rate_limited", "retry_after": e.retry_after, "last_ok": last_ok}
    except APIError as e:
        log_error(name, "api_error", e)
        return [], {"status": "error", "error": str(e)[:200], "last_ok": last_ok}
    except ConfigError as e:
        log_error(name, "config_error", e)
        return [], {"status": "misconfigured", "error": str(e)[:200], "last_ok": last_ok}
    except Exception as e:  # last-resort: log and continue with other sources
        log_error(name, "unknown", e)
        return [], {"status": "error", "error": str(e)[:200], "last_ok": last_ok}


def fetch_all(config: dict, prior_health: dict):
    raw = []
    health = {}
    for name in SOURCES:
        results, h = fetch_one(name, config, prior_health)
        raw.extend(results)
        health[name] = h
    return raw, health


def merge_with_prior(new_scored: list, prior_scored: list, failed_sources: set, config: dict) -> list:
    """Keep prior trends from sources that errored this cycle so a transient failure
    doesn't drop their voice. Recency scoring naturally ages them out over time."""
    if not failed_sources:
        return new_scored
    new_ids = {t["id"] for t in new_scored}
    keep = [t for t in prior_scored if t.get("source") in failed_sources and t["id"] not in new_ids]
    if not keep:
        return new_scored
    LOG.info("Preserving %d prior trends from failed sources: %s", len(keep), sorted(failed_sources))

    # Re-score so recency reflects current time
    rescored = []
    for t in keep:
        clean = {k: v for k, v in t.items() if k not in ("scores", "tagged_vertical", "tagged_reframe", "rejected", "rejection_reason")}
        s = score_one(clean, config)
        if s is None or s.get("rejected"):
            continue
        threshold = (config.get("thresholds") or {}).get("cache_inclusion", 0.50)
        if s["scores"]["total"] >= threshold:
            rescored.append(s)

    combined = new_scored + rescored
    combined.sort(key=lambda x: x["scores"]["total"], reverse=True)
    return combined[: config.get("max_cache_size", 100)]


def prune_served(window_days: int) -> None:
    served = load_cache("served.json", {"served": []})
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    kept = []
    for entry in served.get("served", []):
        try:
            served_at = datetime.fromisoformat(str(entry["served_at"]).replace("Z", "+00:00"))
            if served_at >= cutoff:
                kept.append(entry)
        except (KeyError, ValueError):
            kept.append(entry)
    if len(kept) != len(served.get("served", [])):
        save_cache("served.json", {"served": kept})
        LOG.info("served.json: pruned to %d entries", len(kept))


def cmd_refresh(args, config: dict) -> int:
    cache = load_cache("trends.json", {"last_refresh": None, "source_health": {}, "trends": []})

    if args.source:
        if args.source not in SOURCES:
            print(f"Unknown source: {args.source}. Valid: {SOURCES}", file=sys.stderr)
            return 2
        results, h = fetch_one(args.source, config, cache.get("source_health", {}))
        scored_new = score_and_rank(results, config)
        # Keep other-source trends as-is; replace this source's trends
        prior_other = [t for t in cache.get("trends", []) if t.get("source") != args.source]
        all_trends = prior_other + scored_new
        all_trends.sort(key=lambda x: x.get("scores", {}).get("total", 0), reverse=True)
        all_trends = all_trends[: config.get("max_cache_size", 100)]
        new_health = {**cache.get("source_health", {}), args.source: h}
        save_cache("trends.json", {"last_refresh": now_iso(), "source_health": new_health, "trends": all_trends})
        print(f"Refreshed {args.source}: {len(scored_new)} new scored trends. Cache total: {len(all_trends)}.")
        return 0

    raw, health = fetch_all(config, cache.get("source_health", {}))
    scored_new = score_and_rank(raw, config)
    failed = {s for s, h in health.items() if h.get("status") not in ("ok",) or h.get("count", 0) == 0}
    final = merge_with_prior(scored_new, cache.get("trends", []), failed, config)
    save_cache("trends.json", {"last_refresh": now_iso(), "source_health": health, "trends": final})
    prune_served(config.get("served_window_days", 30))
    ok_count = sum(1 for h in health.values() if h.get("status") == "ok")
    print(f"Refreshed: {len(final)} qualifying trends. Sources OK: {ok_count}/{len(health)}.")
    return 0


def cmd_print_status(config: dict) -> int:
    cache = load_cache("trends.json", {"last_refresh": None, "source_health": {}, "trends": []})
    age_label = "n/a"
    if cache.get("last_refresh"):
        try:
            last = datetime.fromisoformat(str(cache["last_refresh"]).replace("Z", "+00:00"))
            age_h = (datetime.now(timezone.utc) - last).total_seconds() / 3600
            age_label = f"{age_h:.1f}h"
        except (ValueError, AttributeError):
            pass
    payload = {
        "last_refresh": cache.get("last_refresh"),
        "age": age_label,
        "trend_count": len(cache.get("trends", [])),
        "source_health": cache.get("source_health", {}),
    }
    print(json.dumps(payload, indent=2, default=str))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="runner", description="trend engine data refresh + cache orchestrator")
    p.add_argument("--refresh", action="store_true", help="Force refresh of all sources (or one source via --source)")
    p.add_argument("--source", help=f"Refresh only one source: {'|'.join(SOURCES)}")
    p.add_argument("--print-status", action="store_true", help="Print cache freshness + source health and exit")
    args = p.parse_args()

    config = load_config()

    if args.print_status:
        return cmd_print_status(config)

    if args.refresh or args.source:
        return cmd_refresh(args, config)

    # Default: refresh only if stale
    cache = load_cache("trends.json", {"last_refresh": None, "source_health": {}, "trends": []})
    if is_stale(cache.get("last_refresh"), config.get("max_cache_age_hours", 24)):
        return cmd_refresh(args, config)
    print(f"Cache fresh ({cache.get('last_refresh')}). {len(cache.get('trends', []))} trends available.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
