"""SerpAPI Google Trends - RELATED_QUERIES rising for each seed keyword.

Reliability: HIGH. Numeric output, no free-text hallucination risk.
Auth: SERPAPI_KEY env var.
Refresh cadence: 24h (per config.yaml sources implicit; runner controls).
"""
from __future__ import annotations

import logging

import requests

from . import util

LOG = logging.getLogger(__name__)
ENDPOINT = "https://serpapi.com/search"


def fetch(keywords: list[str], timeframe: str = "now 7-d") -> list[dict]:
    """Fetch rising related queries for each seed keyword. Returns canonical trend records."""
    api_key = util.get_required_env("SERPAPI_KEY")
    out: list[dict] = []
    for kw in keywords:
        params = {
            "engine": "google_trends",
            "q": kw,
            "data_type": "RELATED_QUERIES",
            "date": timeframe,
            "geo": "US",
            "api_key": api_key,
        }
        try:
            r = requests.get(ENDPOINT, params=params, timeout=20)
        except requests.exceptions.RequestException as e:
            raise util.APIError(f"SerpAPI request failed for '{kw}': {e}") from e

        if r.status_code == 429:
            retry = int(r.headers.get("Retry-After", "60"))
            raise util.RateLimitError(retry_after=retry, message=f"SerpAPI 429 for '{kw}'")
        if r.status_code >= 400:
            raise util.APIError(f"SerpAPI {r.status_code} for '{kw}': {r.text[:200]}")

        data = r.json()
        rising = (data.get("related_queries") or {}).get("rising") or []
        ts = util.now_iso()
        for q in rising:
            query = q.get("query")
            if not query:
                continue
            out.append({
                "id": util.stable_id("google_trends", query, ts[:10]),
                "source": "google_trends",
                "title": query,
                "text": query,
                "url": q.get("link"),
                "first_seen": ts,
                "engagement": int(q.get("extracted_value") or 0),
                "metric": {
                    "value_label": q.get("value"),
                    "extracted_value": q.get("extracted_value"),
                },
                "author_authority": None,
                "context": {"seed_keyword": kw, "geo": "US", "timeframe": timeframe},
            })
    LOG.info("google_trends: %d rising queries from %d seed keywords", len(out), len(keywords))
    return out
