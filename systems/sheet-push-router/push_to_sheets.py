#!/usr/bin/env python3
"""
Sheet Push Helper
=================
Routes approved content into the correct post-mapping Google Sheet
through one standalone Apps Script web app (appscript/Code.gs).

Secrets come from the environment: SHEET_ROUTER_URL and SHEET_ROUTER_TOKEN.
The brand-to-spreadsheet map lives in config.json (copy config.example.json).
"""

import json
import os
import re
import sys
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Optional

CONFIG_PATH = Path(os.environ.get("SHEET_ROUTER_CONFIG") or Path(__file__).with_name("config.json"))


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def _endpoint() -> tuple:
    """(web_app_url, token) from the environment. Fails loudly before any network call."""
    missing = [k for k in ("SHEET_ROUTER_URL", "SHEET_ROUTER_TOKEN") if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Missing env var(s): {', '.join(missing)}. Set them in a local .env file.")
    return os.environ["SHEET_ROUTER_URL"], os.environ["SHEET_ROUTER_TOKEN"]


def resolve_vertical(vertical: str) -> str:
    """Accept aliases like 'brand-a' and map to the canonical name 'Brand A'."""
    config = load_config()
    sheets = config["sheets"]
    if vertical in sheets:
        return vertical
    aliases = config.get("vertical_aliases", {})
    key = vertical.strip().lower()
    if key in aliases:
        return aliases[key]
    raise ValueError(
        f"Unknown vertical: '{vertical}'. "
        f"Available: {list(sheets.keys())} or aliases: {list(aliases.keys())}"
    )


def get_sheet_id(vertical: str) -> str:
    config = load_config()
    canonical = resolve_vertical(vertical)
    return config["sheets"][canonical]["sheet_id"]


def _post(payload: dict) -> dict:
    url, token = _endpoint()
    payload = dict(payload)
    payload["token"] = token
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read().decode("utf-8", errors="replace")
        return _parse_response(raw)
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}", "body": e.read().decode("utf-8", errors="ignore")}
    except urllib.error.URLError as e:
        return {"error": f"Network error: {e.reason}"}


def _parse_response(raw: str) -> dict:
    """Apps Script returns HTTP 200 with an HTML error page on an uncaught server-side
    error (most often a column data-validation rejection on B/C). Parse JSON when we get
    it; otherwise surface a structured error with the validation detail instead of crashing
    on json.loads (the recurring batch-push failure mode)."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r'(The data you entered[^<]*)', raw)
        return {"error": "non-JSON Apps Script response (likely a column data-validation rejection)",
                "detail": (m.group(1).strip() if m else raw[:300])}


def _get(params: dict) -> dict:
    base, token = _endpoint()
    params = dict(params)
    params["token"] = token
    url = base + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode("utf-8", errors="replace")
        return _parse_response(raw)
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}", "body": e.read().decode("utf-8", errors="ignore")}
    except urllib.error.URLError as e:
        return {"error": f"Network error: {e.reason}"}


# ----- Public API -----

def list_sheets(vertical: str) -> dict:
    """List all tabs in the given vertical's spreadsheet."""
    return _post({
        "spreadsheetId": get_sheet_id(vertical),
        "op": "listSheets",
    })


def read_sheet(vertical: str, tab: str) -> dict:
    """Read all rows of a tab. Used to find date-to-row mapping."""
    return _get({
        "spreadsheetId": get_sheet_id(vertical),
        "sheet": tab,
    })


def write_cell(vertical: str, tab: str, row: int, col: int, value: str) -> dict:
    """Write a single cell. row/col are 1-based (col D = 4)."""
    return _post({
        "spreadsheetId": get_sheet_id(vertical),
        "sheet": tab,
        "op": "writeCell",
        "row": row,
        "col": col,
        "value": value,
    })


def update_range(vertical: str, tab: str, range_a1: str, values: list) -> dict:
    """Write a 2D array of values to an A1 range (e.g. 'D2:F8')."""
    return _post({
        "spreadsheetId": get_sheet_id(vertical),
        "sheet": tab,
        "op": "updateRange",
        "range": range_a1,
        "values": values,
    })


def clear_range(vertical: str, tab: str, range_a1: str) -> dict:
    """Clear contents of an A1 range."""
    return _post({
        "spreadsheetId": get_sheet_id(vertical),
        "sheet": tab,
        "op": "clearRange",
        "range": range_a1,
    })


# Column-B (Content Pillar) data-validation set, as enforced by the spreadsheets themselves.
# This is the team's per-sheet dropdown, NOT the writer's content-type taxonomy. Map a content
# type to one of these before writing column B (e.g. Thought Leadership -> Education), or write
# D:F only and let the team set B. A value outside a sheet's dropdown makes the SHEET reject
# the whole B:F write (HTTP 200 + HTML error page; now surfaced by _parse_response). If a
# sheet's dropdown differs, capture it from the rejection's "detail" and map accordingly.
CONTENT_PILLAR_OPTIONS = {
    "Education", "FAQ", "Myth", "Process", "Engagement", "Inspirational",
}
TAG_OPTIONS = {"Poster", "Carousel", "Reel"}


def push_post_map(
    vertical: str,
    tab: str,
    rows_by_date: dict,
) -> dict:
    """
    Push generated content to a post-mapping sheet by matching dates in column A.

    For each matched date the function writes:
      - B (Content Pillar)  if `content_pillar` provided
      - C (Tag)             if `tag` provided
      - D (Write-up)        if `write_up` provided
      - E (FB/IG Caption)   if `fb_caption` provided
      - F (LinkedIn Caption) if `linkedin_caption` provided

    Cells with no provided value preserve their existing target content. F is only
    written when explicitly provided so LinkedIn captions are never accidentally
    blanked.

    rows_by_date: {
        "Monday, June 1": {
            "content_pillar": "Education",      # one of CONTENT_PILLAR_OPTIONS
            "tag": "Carousel",                  # one of TAG_OPTIONS
            "write_up": "...",
            "fb_caption": "...",
            "linkedin_caption": "..."
        },
        ...
    }
    """
    sheet_data = read_sheet(vertical, tab)
    if "error" in sheet_data:
        return sheet_data

    rows = sheet_data.get("rows", [])
    date_to_row_and_existing = {}
    for i, row in enumerate(rows):
        if i == 0 or not row:
            continue
        date_cell = str(row[0]).strip() if row[0] is not None else ""
        if date_cell:
            date_to_row_and_existing[date_cell] = (i + 1, row)

    results = []
    not_found = []
    validation_warnings = []

    for date_str, content in rows_by_date.items():
        date_key = date_str.strip()
        if date_key not in date_to_row_and_existing:
            not_found.append(date_key)
            continue
        row_num, existing_row = date_to_row_and_existing[date_key]

        # Validate dropdown values against allowed sets
        cp = content.get("content_pillar", "")
        if cp and cp not in CONTENT_PILLAR_OPTIONS:
            validation_warnings.append(
                f"{date_key}: content_pillar '{cp}' not in {sorted(CONTENT_PILLAR_OPTIONS)}"
            )
        tag = content.get("tag", "")
        if tag and tag not in TAG_OPTIONS:
            validation_warnings.append(
                f"{date_key}: tag '{tag}' not in {sorted(TAG_OPTIONS)}"
            )

        # Build B:F write with existing values preserved for any cell not provided
        def existing(idx):
            v = existing_row[idx] if len(existing_row) > idx else ""
            return "" if v is None else str(v)

        def pick(new_val, existing_idx):
            return new_val if new_val and str(new_val).strip() else existing(existing_idx)

        bf_row = [
            pick(cp, 1),                            # B
            pick(tag, 2),                           # C
            pick(content.get("write_up", ""), 3),   # D
            pick(content.get("fb_caption", ""), 4), # E
            pick(content.get("linkedin_caption", ""), 5),  # F
        ]
        result = update_range(vertical, tab, f"B{row_num}:F{row_num}", [bf_row])
        results.append({"date": date_key, "row": row_num, "result": result})

    return {
        "ok": all(r["result"].get("ok") for r in results),
        "updates_made": len(results),
        "not_found": not_found,
        "validation_warnings": validation_warnings,
        "details": results,
    }


# ----- CLI for quick testing -----

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  push_to_sheets.py list-sheets <vertical>")
        print("  push_to_sheets.py read <vertical> <tab>")
        print("  push_to_sheets.py write-cell <vertical> <tab> <row> <col> <value>")
        print("  push_to_sheets.py clear <vertical> <tab> <range>")
        print("  push_to_sheets.py verticals")
        sys.exit(1)

    cmd = sys.argv[1]
    try:
        if cmd == "verticals":
            cfg = load_config()
            print(json.dumps(list(cfg["sheets"].keys()), indent=2))
        elif cmd == "list-sheets":
            print(json.dumps(list_sheets(sys.argv[2]), indent=2))
        elif cmd == "read":
            print(json.dumps(read_sheet(sys.argv[2], sys.argv[3]), indent=2))
        elif cmd == "write-cell":
            v, tab, r, c, val = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
            print(json.dumps(write_cell(v, tab, r, c, val), indent=2))
        elif cmd == "clear":
            print(json.dumps(clear_range(sys.argv[2], sys.argv[3], sys.argv[4]), indent=2))
        else:
            print(f"Unknown command: {cmd}")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
