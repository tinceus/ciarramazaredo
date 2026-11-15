"""Pre-scoring compliance filter: red-line claims and prospect-blame phrasing.

These checks run BEFORE scoring so non-compliant trends never reach the cache.
A human applies a second pass before anything is published.

red_lines:      claims the brand never makes (free offers, guaranteed savings, government-program language).
prospect_blame: framing that makes the buyer the villain. The villain must be a systemic problem
                (bad data, broken systems), never the person we sell to.
"""
from __future__ import annotations


def is_compliant(text: str, red_lines: list[str], prospect_blame: list[str]) -> tuple[bool, str | None]:
    """Returns (passes, reason). Phrases are case-insensitive substring matches."""
    t = text.lower()
    for phrase in red_lines or []:
        if phrase.lower() in t:
            return False, f"red_line:{phrase}"
    for phrase in prospect_blame or []:
        if phrase.lower() in t:
            return False, f"prospect_blame:{phrase}"
    return True, None
