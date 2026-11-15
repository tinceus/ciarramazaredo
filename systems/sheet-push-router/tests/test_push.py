"""Offline tests for push_to_sheets.py. The web app is faked; no network. Fictional rows only."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import push_to_sheets as p  # noqa: E402

ROWS = [
    ["Posting Date", "Pillar", "Tag", "Write-up", "FB/IG", "LinkedIn"],
    ["Monday, June 1", "Education", "Reel", "old write-up", "old caption", "old linkedin"],
    ["Wednesday, June 3", "", "", "", "", ""],
]


class ParseResponse(unittest.TestCase):
    def test_json_passes_through(self):
        self.assertEqual(p._parse_response('{"ok": true}'), {"ok": True})

    def test_html_error_page_becomes_structured_error(self):
        html = "<html><body><div>The data you entered in cell B2 violates the validation rules</div></body></html>"
        out = p._parse_response(html)
        self.assertIn("non-JSON", out["error"])
        self.assertTrue(out["detail"].startswith("The data you entered in cell B2"))


class Endpoint(unittest.TestCase):
    def test_missing_env_fails_before_network(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                p._endpoint()


class PushPostMap(unittest.TestCase):
    def setUp(self):
        self.writes = []
        patches = [
            mock.patch.object(p, "read_sheet", return_value={"rows": ROWS}),
            mock.patch.object(p, "update_range", side_effect=lambda v, t, rng, vals: self.writes.append((rng, vals)) or {"ok": True}),
        ]
        for m in patches:
            m.start()
            self.addCleanup(m.stop)

    def test_matches_date_and_preserves_cells_not_provided(self):
        out = p.push_post_map("a", "June", {"Monday, June 1": {"fb_caption": "new caption"}})
        self.assertTrue(out["ok"])
        self.assertEqual(self.writes, [("B2:F2", [["Education", "Reel", "old write-up", "new caption", "old linkedin"]])])

    def test_unknown_date_and_bad_dropdown_are_reported(self):
        out = p.push_post_map("a", "June", {
            "Friday, June 5": {"write_up": "x"},
            "Wednesday, June 3": {"content_pillar": "Thought Leadership", "tag": "Reel"},
        })
        self.assertEqual(out["not_found"], ["Friday, June 5"])
        self.assertEqual(len(out["validation_warnings"]), 1)
        self.assertIn("Thought Leadership", out["validation_warnings"][0])

    def test_read_error_stops_before_any_write(self):
        with mock.patch.object(p, "read_sheet", return_value={"error": "Unauthorized"}):
            self.assertEqual(p.push_post_map("a", "June", {"Monday, June 1": {"write_up": "x"}}), {"error": "Unauthorized"})
        self.assertEqual(self.writes, [])


if __name__ == "__main__":
    unittest.main()
