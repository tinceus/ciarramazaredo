"""Offline tests: caption-track choice, the .md rebuild, and the --check tamper guard. Fictional fixtures only."""
import json
import os
import sys
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import harvest  # noqa: E402

INFO = {"id": "vid00000001", "title": "Example talk", "upload_date": "20260102", "duration_string": "1:05",
        "webpage_url": "https://www.youtube.com/watch?v=vid00000001", "description": "A fictional video.",
        "caption_kind": "manual", "caption_lang": "en", "retrieved": "2026-01-03"}
JSON3 = {"events": [{"tStartMs": 0, "segs": [{"utf8": "Hello and"}, {"utf8": " welcome."}]},
                    {"tStartMs": 65000, "segs": [{"utf8": "\n"}]},
                    {"tStartMs": 61500, "segs": [{"utf8": "Thanks for\nwatching."}]}]}


class PickTrack(unittest.TestCase):
    def test_manual_beats_auto(self):
        d = {"subtitles": {"en": [{"ext": "vtt", "url": "x"}, {"ext": "json3", "url": "manual"}]},
             "automatic_captions": {"en": [{"ext": "json3", "url": "auto"}]}}
        self.assertEqual(harvest.pick_track(d), ("manual", "en", "manual"))

    def test_falls_back_to_auto_then_none(self):
        self.assertEqual(harvest.pick_track({"automatic_captions": {"en-orig": [{"ext": "json3", "url": "a"}]}})[0], "auto")
        self.assertEqual(harvest.pick_track({}), (None, None, None))


class BuildAndCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.saved = harvest.RAW, harvest.OUT
        harvest.RAW, harvest.OUT = root / "raw", root / "videos"
        harvest.RAW.mkdir(); harvest.OUT.mkdir()
        (harvest.RAW / "vid00000001.info.json").write_text(json.dumps(INFO))
        (harvest.RAW / "vid00000001.json3").write_text(json.dumps(JSON3))

    def tearDown(self):
        harvest.RAW, harvest.OUT = self.saved
        self.tmp.cleanup()

    def test_build_skips_blank_events_and_stamps_time(self):
        text, name = harvest.build("vid00000001")
        self.assertEqual(name, "2026-01-02_vid00000001.md")
        self.assertIn("[0:00] Hello and welcome.", text)
        self.assertIn("[1:01] Thanks for watching.", text)
        self.assertNotIn("[1:05]", text)

    def test_check_passes_then_fails_on_hand_edit(self):
        text, name = harvest.build("vid00000001")
        (harvest.OUT / name).write_text(text, encoding="utf-8")
        self.assertEqual(harvest.check(), 0)
        (harvest.OUT / name).write_text(text.replace("welcome", "welcomed"), encoding="utf-8")
        self.assertEqual(harvest.check(), 1)


if __name__ == "__main__":
    unittest.main()
