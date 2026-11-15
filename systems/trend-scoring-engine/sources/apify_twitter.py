"""Apify X/Twitter - apidojo/tweet-scraper actor for top tweets by search term.

Reliability: MEDIUM. Scraping-based; occasional gaps.
Quality floor: drop tweets with <100 followers AND <5 engagement (filters obvious bot/spam noise; lets B2B operator content with modest reach through).
Auth: APIFY_TOKEN env var.
Refresh cadence: 6h.
"""
from __future__ import annotations

import logging

from apify_client import ApifyClient

from . import util

LOG = logging.getLogger(__name__)
ACTOR_ID = "apidojo/tweet-scraper"

MIN_FOLLOWERS = 100
MIN_ENGAGEMENT = 5


def fetch(search_terms: list[str], max_items: int = 200) -> list[dict]:
    if not search_terms:
        return []
    token = util.get_required_env("APIFY_TOKEN")
    client = ApifyClient(token)
    run_input = {
        "searchTerms": search_terms,
        "maxItems": max_items,
        "sort": "Top",
        "tweetLanguage": "en",
    }
    try:
        run = client.actor(ACTOR_ID).call(run_input=run_input, timeout_secs=180)
    except Exception as e:
        raise util.APIError(f"Apify Twitter actor call failed: {e}") from e

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    out = []
    for item in items:
        n = _normalize(item)
        if n is None:
            continue
        if (n["author_authority"] or 0) < MIN_FOLLOWERS and n["engagement"] < MIN_ENGAGEMENT:
            continue
        out.append(n)
    LOG.info("twitter: %d tweets after quality floor from %d search terms", len(out), len(search_terms))
    return out


def _normalize(item: dict) -> dict | None:
    tweet_id = item.get("id")
    text = item.get("text") or item.get("fullText")
    if not tweet_id or not text:
        return None
    likes = int(item.get("likeCount") or 0)
    retweets = int(item.get("retweetCount") or 0)
    replies = int(item.get("replyCount") or 0)
    author = item.get("author") or {}
    return {
        "id": util.stable_id("twitter", tweet_id),
        "source": "twitter",
        "title": text[:120],
        "text": text,
        "url": item.get("url") or item.get("twitterUrl"),
        "first_seen": item.get("createdAt") or util.now_iso(),
        "engagement": likes + retweets * 2 + replies * 3,
        "metric": {
            "likes": likes,
            "retweets": retweets,
            "replies": replies,
            "views": int(item.get("viewCount") or 0),
        },
        "author_authority": int(author.get("followers") or 0),
        "context": {
            "username": author.get("userName"),
            "search_term": item.get("searchTerm"),
        },
    }
