"""Apify TikTok - clockworks/tiktok-scraper actor for hashtag videos.

Reliability: LOW-MEDIUM. Heavy consumer skew; supplementary signal only.
Auth: APIFY_TOKEN env var.
Refresh cadence: 24h.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apify_client import ApifyClient

from . import util

LOG = logging.getLogger(__name__)
ACTOR_ID = "clockworks/tiktok-scraper"


def fetch(hashtags: list[str], results_limit: int = 50) -> list[dict]:
    if not hashtags:
        return []
    token = util.get_required_env("APIFY_TOKEN")
    client = ApifyClient(token)
    run_input = {
        "hashtags": hashtags,
        "resultsLimit": results_limit,
    }
    try:
        run = client.actor(ACTOR_ID).call(run_input=run_input, timeout_secs=180)
    except Exception as e:
        raise util.APIError(f"Apify TikTok actor call failed: {e}") from e

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    out = []
    for item in items:
        n = _normalize(item)
        if n is not None:
            out.append(n)
    LOG.info("tiktok: %d videos from %d hashtags", len(out), len(hashtags))
    return out


def _normalize(item: dict) -> dict | None:
    vid_id = item.get("id")
    text = item.get("text") or ""
    if not vid_id:
        return None
    plays = int(item.get("playCount") or 0)
    diggs = int(item.get("diggCount") or 0)
    shares = int(item.get("shareCount") or 0)
    comments = int(item.get("commentCount") or 0)
    author = item.get("authorMeta") or {}

    create_time = item.get("createTime")
    if isinstance(create_time, (int, float)):
        first_seen = datetime.fromtimestamp(create_time, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        first_seen = create_time or util.now_iso()

    return {
        "id": util.stable_id("tiktok", vid_id),
        "source": "tiktok",
        "title": text[:120] if text else f"TikTok {vid_id}",
        "text": text,
        "url": item.get("webVideoUrl"),
        "first_seen": first_seen,
        "engagement": int(plays * 0.001 + diggs + shares * 5 + comments * 3),
        "metric": {
            "plays": plays,
            "diggs": diggs,
            "shares": shares,
            "comments": comments,
        },
        "author_authority": int(author.get("fans") or 0),
        "context": {
            "author_username": author.get("name"),
        },
    }
