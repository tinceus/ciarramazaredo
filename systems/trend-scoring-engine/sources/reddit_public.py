"""Reddit public JSON API - no auth, no Apify, hits subreddit /top.json directly.

Reliability: MEDIUM-HIGH. Reddit's public JSON is stable but rate-limited (~10 req/min unauthenticated).
Auth: none. Reddit requires only a descriptive User-Agent.
Refresh cadence: 12h.

Implementation note: this source started on an Apify actor and moved to the public JSON
endpoint when that actor went paid-only. No token needed.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

import requests

from . import util

LOG = logging.getLogger(__name__)
USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "trend-scoring-engine/1.0 (research script)")


def fetch(subreddits: list[str], max_items: int = 100) -> list[dict]:
    """Fetch top-of-day posts for each subreddit via public JSON. Returns canonical records."""
    if not subreddits:
        return []
    out: list[dict] = []
    headers = {"User-Agent": USER_AGENT}
    per_sub_limit = min(max_items, 100)
    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/top.json"
        params = {"t": "day", "limit": per_sub_limit}
        try:
            r = requests.get(url, params=params, headers=headers, timeout=15)
        except requests.exceptions.RequestException as e:
            raise util.APIError(f"Reddit JSON request failed for r/{sub}: {e}") from e

        if r.status_code == 429:
            retry = int(r.headers.get("Retry-After", "60"))
            raise util.RateLimitError(retry_after=retry, message=f"Reddit 429 for r/{sub}")
        if r.status_code in (403, 404):
            LOG.warning("reddit r/%s: %d (private/banned/typo) - skipping", sub, r.status_code)
            continue
        if r.status_code >= 400:
            raise util.APIError(f"Reddit {r.status_code} for r/{sub}: {r.text[:200]}")

        try:
            children = r.json().get("data", {}).get("children", []) or []
        except ValueError as e:
            raise util.APIError(f"Reddit returned non-JSON for r/{sub}: {e}") from e

        for child in children:
            n = _normalize(child.get("data", {}), sub)
            if n is not None:
                out.append(n)

        time.sleep(1.0)  # politeness; stay well under unauthenticated rate limit

    LOG.info("reddit: %d posts from %d subreddits", len(out), len(subreddits))
    return out


def _normalize(post: dict, fallback_sub: str) -> dict | None:
    post_id = post.get("id")
    title = post.get("title")
    if not post_id or not title:
        return None
    body = (post.get("selftext") or "")[:2000]
    upvotes = int(post.get("score") or 0)
    comments = int(post.get("num_comments") or 0)
    created_utc = post.get("created_utc")
    try:
        if created_utc is not None:
            created_iso = datetime.fromtimestamp(float(created_utc), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            created_iso = util.now_iso()
    except (ValueError, TypeError):
        created_iso = util.now_iso()
    permalink = post.get("permalink")
    url = f"https://www.reddit.com{permalink}" if permalink else post.get("url")
    return {
        "id": util.stable_id("reddit", post_id),
        "source": "reddit",
        "title": title,
        "text": body or title,
        "url": url,
        "first_seen": created_iso,
        "engagement": upvotes + comments * 2,
        "metric": {
            "upvotes": upvotes,
            "comments": comments,
            "upvote_ratio": post.get("upvote_ratio"),
        },
        "author_authority": None,
        "context": {
            "subreddit": post.get("subreddit") or fallback_sub,
            "username": post.get("author"),
        },
    }
