#!/usr/bin/env python3
"""Harvest caption tracks for every video on one YouTube channel. Self-contained, so a scheduler can run it unattended.

  python3 harvest.py inventory <channel_url>             list the channel's videos into inventory.json
  python3 harvest.py fetch [--limit N] [--minutes M]   fetch transcripts for videos not yet fetched (resumable, host's own playlists first)
  python3 harvest.py status              counts by status
  python3 harvest.py --check             rebuild every video .md from raw/ and fail on any difference

Engines, in order:
  1. yt-dlp metadata + json3 caption track (manual captions win over automatic), with 429 backoff.
  2. youtube-transcript-api, only when yt-dlp found no json3 track URL.
  3. Whisper (base.en, local, low priority) on the downloaded audio, used while captions are IP-blocked
     (block noted in state.json; captions are retried after BLOCK_HOURS) or when a video has no captions.
Runs are bounded by --minutes and guarded by a lock so scheduled runs never overlap. Nothing is retyped: raw/<id>.info.json + raw/<id>.json3 (or raw/<id>.api.json) are what YouTube
returned; videos/<date>_<id>.md is rebuilt from them.
"""
import datetime
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW, OUT = HERE / "raw", HERE / "videos"
INV, LOG = HERE / "inventory.json", HERE / "harvest_log.json"
KEEP = ("id", "title", "upload_date", "duration", "duration_string", "channel", "channel_url", "webpage_url", "description")
WAITS = (30, 90)
PAUSE = 10  # seconds between videos
STATE, LOCK, TMP = HERE / "state.json", HERE / ".lock", HERE / "tmp"
BLOCK_HOURS = 3
WHISPER = os.environ.get("WHISPER_BIN", "whisper")


class Blocked(Exception):
    pass


class NoCaptions(Exception):
    pass


def ytdlp_json(vid):
    r = subprocess.run(["yt-dlp", "--no-warnings", "--skip-download", "-j", "https://www.youtube.com/watch?v=" + vid],
                       capture_output=True, text=True)
    if r.returncode != 0:
        err = r.stderr.strip()[-400:]
        if "429" in err or "Sign in to confirm" in err:
            raise Blocked(err)
        if "unavailable" in err.lower() or "private" in err.lower() or "removed" in err.lower():
            raise NoCaptions("unavailable: " + err[-160:])
        raise RuntimeError(err)
    return json.loads(r.stdout)


def pick_track(d):
    subs, auto = d.get("subtitles") or {}, d.get("automatic_captions") or {}
    for kind, pool, lang in (("manual", subs, "en"), ("manual", subs, "en-US"), ("auto", auto, "en"), ("auto", auto, "en-orig")):
        for t in pool.get(lang) or []:
            if t.get("ext") == "json3":
                return kind, lang, t["url"]
    return None, None, None


def engine_ytdlp(vid):
    for attempt, wait in enumerate((0,) + WAITS):
        if wait:
            print(f"  {vid}: 429, waiting {wait}s", flush=True)
            time.sleep(wait)
        d = ytdlp_json(vid)
        kind, lang, url = pick_track(d)
        if not url:
            return d, None
        try:
            body = urllib.request.urlopen(url, timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                continue
            raise
        info = {k: d.get(k) for k in KEEP}
        info.update({"caption_kind": kind, "caption_lang": lang, "retrieved": datetime.date.today().isoformat(),
                     "fetched_by": "harvest.py (yt-dlp json3)"})
        RAW.mkdir(exist_ok=True)
        (RAW / f"{vid}.info.json").write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding="utf-8")
        (RAW / f"{vid}.json3").write_bytes(body)
        return d, "json3"
    raise Blocked("still 429 after retries")


def engine_api(vid, d):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        raise NoCaptions("no json3 track and youtube-transcript-api not installed")
    try:
        t = YouTubeTranscriptApi().fetch(vid, languages=["en", "en-US", "en-GB"])
    except Exception as e:
        name = type(e).__name__
        if name in ("IpBlocked", "RequestBlocked"):
            raise Blocked(name)
        if name in ("TranscriptsDisabled", "NoTranscriptFound", "VideoUnavailable", "CouldNotRetrieveTranscript"):
            raise NoCaptions(name)
        raise
    info = {k: d.get(k) for k in KEEP} if d else {"id": vid}
    info.update({"caption_kind": "generated" if t.is_generated else "manual", "caption_lang": t.language_code,
                 "retrieved": datetime.date.today().isoformat(), "fetched_by": "harvest.py (youtube-transcript-api)"})
    snippets = [{"text": s.text, "start": s.start, "duration": s.duration} for s in t]
    RAW.mkdir(exist_ok=True)
    (RAW / f"{vid}.api.json").write_text(json.dumps({"info": info, "snippets": snippets}, indent=1, ensure_ascii=False), encoding="utf-8")
    return "api"


def engine_whisper(vid, d):
    TMP.mkdir(exist_ok=True)
    for f in TMP.glob(vid + ".*"):
        f.unlink()
    r = subprocess.run(["yt-dlp", "--no-warnings", "-f", "bestaudio", "-x", "--audio-format", "m4a",
                        "-o", str(TMP / "%(id)s.%(ext)s"), "https://www.youtube.com/watch?v=" + vid], capture_output=True, text=True)
    audio = TMP / f"{vid}.m4a"
    if r.returncode != 0 or not audio.exists():
        err = r.stderr.strip()[-300:]
        if "429" in err or "Sign in to confirm" in err:
            raise Blocked("audio: " + err)
        raise NoCaptions("unavailable: audio download failed: " + err[-160:])
    w = subprocess.run(["nice", "-n", "15", WHISPER, str(audio), "--model", "base.en", "--language", "en", "--output_format", "json",
                        "--output_dir", str(TMP), "--fp16", "False", "--verbose", "False"], capture_output=True, text=True)
    out = TMP / f"{vid}.json"
    if w.returncode != 0 or not out.exists():
        raise RuntimeError("whisper failed: " + w.stderr.strip()[-200:])
    segs = [{"start": s["start"], "text": s["text"].strip()} for s in json.loads(out.read_text())["segments"]]
    info = {k: d.get(k) for k in KEEP}
    info.update({"caption_kind": "whisper", "caption_lang": "en", "retrieved": datetime.date.today().isoformat(),
                 "fetched_by": "harvest.py (local Whisper base.en on the audio)"})
    RAW.mkdir(exist_ok=True)
    (RAW / f"{vid}.whisper.json").write_text(json.dumps({"info": info, "segments": segs}, indent=1, ensure_ascii=False), encoding="utf-8")
    audio.unlink(); out.unlink()
    return "whisper"


def stamp(sec):
    s = int(sec)
    return f"{s // 60}:{s % 60:02d}"


def build(vid):
    if (RAW / f"{vid}.json3").exists():
        info = json.loads((RAW / f"{vid}.info.json").read_text(encoding="utf-8"))
        cap = json.loads((RAW / f"{vid}.json3").read_text(encoding="utf-8"))
        rows = []
        for ev in cap.get("events", []):
            text = "".join(s.get("utf8", "") for s in (ev.get("segs") or [])).replace("\n", " ").strip()
            if text:
                rows.append((ev.get("tStartMs", 0) / 1000, text))
        via = "YouTube's caption track (yt-dlp json3)"
    elif (RAW / f"{vid}.whisper.json").exists():
        d = json.loads((RAW / f"{vid}.whisper.json").read_text(encoding="utf-8"))
        info = d["info"]
        rows = [(x["start"], x["text"]) for x in d["segments"] if x["text"]]
        via = "local Whisper base.en transcription of the audio"
    else:
        d = json.loads((RAW / f"{vid}.api.json").read_text(encoding="utf-8"))
        info = d["info"]
        rows = [(x["start"], x["text"].replace("\n", " ").strip()) for x in d["snippets"] if x["text"].strip()]
        via = "YouTube's caption track (youtube-transcript-api)"
    day = info.get("upload_date")
    iso = f"{day[:4]}-{day[4:6]}-{day[6:]}" if day else "undated"
    auto = info["caption_kind"] in ("auto", "generated", "whisper")
    head = [f"# {info.get('title')}", "",
            f"Written by harvest.py from {via}. Not retyped. `harvest.py --check` fails on a hand edit.", "",
            f"- Video ID: {vid}", f"- URL: {info.get('webpage_url') or 'https://www.youtube.com/watch?v=' + vid}",
            f"- Published: {iso}", f"- Length: {info.get('duration_string') or ''}",
            f"- Captions: {info['caption_kind']} ({info['caption_lang']})" + ("; machine transcription can mishear names and numbers" if auto else ""),
            f"- Retrieved: {info['retrieved']}", "", "## Description", "", (info.get("description") or "").strip(), "",
            "## Transcript, continuous", "", " ".join(t for _, t in rows), "", "## Transcript, timestamped", ""]
    return "\n".join(head + [f"[{stamp(s)}] {t}" for s, t in rows]) + "\n", f"{iso}_{vid}.md"


def inventory(channel_url):
    """Flat-list the channel's uploads. Playlists can be added by hand; a playlist with "guest": true is fetched last."""
    r = subprocess.run(["yt-dlp", "--no-warnings", "--flat-playlist", "-J", channel_url.rstrip("/") + "/videos"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("yt-dlp failed: " + r.stderr.strip()[-300:])
    videos = {e["id"]: {"id": e["id"], "title": e.get("title"), "tabs": ["videos"], "playlists": [], "duration": e.get("duration")}
              for e in json.loads(r.stdout).get("entries") or [] if e.get("id")}
    INV.write_text(json.dumps({"channel": channel_url, "videos": videos, "playlists": []}, indent=1, ensure_ascii=False))
    print(f"inventory: {len(videos)} videos")


def load():
    inv = json.loads(INV.read_text())
    log = json.loads(LOG.read_text()) if LOG.exists() else {}
    return inv, log


def save(log):
    LOG.write_text(json.dumps(log, indent=1) + "\n")


def fetch_all(limit, minutes):
    try:
        LOCK.mkdir()
    except FileExistsError:
        if time.time() - LOCK.stat().st_mtime < 6 * 3600:
            print("another run holds the lock; exiting"); return
        LOCK.rmdir(); LOCK.mkdir()
    try:
        _fetch(limit, minutes)
    finally:
        LOCK.rmdir()


def _fetch(limit, minutes):
    inv, log = load()
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    OUT.mkdir(exist_ok=True)
    guest = {p["title"] for p in inv["playlists"] if p["guest"]}
    order = list(inv["videos"])
    def rank(v):
        pl = inv["videos"][v]["playlists"]
        return (bool(pl) and all(x in guest for x in pl), order.index(v))
    todo = sorted([v for v in inv["videos"] if log.get(v, {}).get("status") not in ("ok", "unavailable")], key=rank)
    deadline = time.time() + minutes * 60 if minutes else None
    done = 0
    for n, vid in enumerate(todo[:limit] if limit else todo, 1):
        if deadline and time.time() > deadline:
            print("time budget reached"); break
        captions_ok = time.time() > st.get("captions_blocked_until", 0)
        prior = log.get(vid, {}).get("status")
        try:
            got = None
            d = ytdlp_json(vid)
            if captions_ok and prior != "no_captions":
                try:
                    d, got = engine_ytdlp(vid)
                    if not got:
                        got = engine_api(vid, d)
                except Blocked as e:
                    st["captions_blocked_until"] = time.time() + BLOCK_HOURS * 3600
                    STATE.write_text(json.dumps(st))
                    print(f"  captions blocked ({str(e)[:60]}); Whisper for {BLOCK_HOURS}h", flush=True)
                except NoCaptions:
                    pass
            if not got:
                got = engine_whisper(vid, d)
            text, name = build(vid)
            (OUT / name).write_text(text, encoding="utf-8")
            log[vid] = {"status": "ok", "file": f"videos/{name}", "engine": got}
            done += 1
        except Blocked as e:
            print(f"{n}/{len(todo)} {vid} BLOCKED ({str(e)[:80]}); stopping this batch", flush=True)
            break
        except NoCaptions as e:
            log[vid] = {"status": "unavailable" if str(e).startswith("unavailable") else "no_captions", "detail": str(e)[:200]}
        except Exception as e:
            log[vid] = {"status": "error", "detail": repr(e)[-200:]}
        save(log)
        print(f"{n}/{len(todo)} {vid} {log[vid]['status']} {log[vid].get('engine','')}", flush=True)
        time.sleep(PAUSE)
    save(log)
    status(f"batch fetched {done}")


def status(prefix="status"):
    inv, log = load()
    counts = {}
    for v in inv["videos"]:
        s = log.get(v, {}).get("status", "pending")
        counts[s] = counts.get(s, 0) + 1
    print(prefix + ": " + json.dumps({"inventory": len(inv["videos"]), **counts}))


def check():
    bad = n = 0
    for p in sorted(RAW.glob("*.info.json")) + sorted(RAW.glob("*.api.json")) + sorted(RAW.glob("*.whisper.json")):
        vid = p.name.split(".")[0]
        if p.name.endswith(".info.json") and not (RAW / f"{vid}.json3").exists():
            continue
        n += 1
        text, name = build(vid)
        f = OUT / name
        if not f.exists() or f.read_text(encoding="utf-8") != text:
            print("DIFF", name)
            bad += 1
    print(f"YOUTUBE CORPUS {'PASS' if not bad else 'FAIL'}: {n} transcripts checked")
    return 1 if bad else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["inventory"] and len(a) > 1:
        inventory(a[1])
    elif a[:1] == ["fetch"]:
        lim = int(a[a.index("--limit") + 1]) if "--limit" in a else 0
        mins = int(a[a.index("--minutes") + 1]) if "--minutes" in a else 0
        fetch_all(lim, mins)
    elif a[:1] == ["status"]:
        status()
    elif a[:1] == ["--check"]:
        sys.exit(check())
    else:
        print(__doc__)
