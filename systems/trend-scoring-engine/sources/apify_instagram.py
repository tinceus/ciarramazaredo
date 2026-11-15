"""Apify Instagram - apify/instagram-hashtag-scraper actor for hashtag posts.

Reliability: MEDIUM. High consumer noise; audience-match scorer drops most.
Auth: APIFY_TOKEN env var.
Refresh cadence: 24h.
"""
from __future__ import annotations

import logging

from apify_client import ApifyClient

from . import util

LOG = logging.getLogger(__name__)
ACTOR_ID = "apify/instagram-hashtag-scraper"


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
        raise util.APIError(f"Apify Instagram actor call failed: {e}") from e

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    out = []
    for item in items:
        n = _normalize(item)
        if n is not None:
            out.append(n)
    LOG.info("instagram: %d posts from %d hashtags", len(out), len(hashtags))
    return out


def _normalize(item: dict) -> dict | None:
    post_id = item.get("id") or item.get("shortCode")
    caption = item.get("caption") or ""
    if not post_id or not caption:
        return None
    likes = int(item.get("likesCount") or 0)
    comments = int(item.get("commentsCount") or 0)
    return {
        "id": util.stable_id("instagram", post_id),
        "source": "instagram",
        "title": caption[:120],
        "text": caption,
        "url": item.get("url"),
        "first_seen": item.get("timestamp") or util.now_iso(),
        "engagement": likes + comments * 3,
        "metric": {
            "likes": likes,
            "comments": comments,
        },
        "author_authority": None,
        "context": {
            "owner_username": item.get("ownerUsername"),
            "hashtag": item.get("hashtag"),
        },
    }
