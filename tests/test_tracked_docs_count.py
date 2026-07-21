"""AGENTS.md's 'N tracked docs' claim must equal the inventory_drift gate's own
count (F5).

There is exactly ONE source of truth for the tracked-doc count: the
``inventory_drift`` gate (the same ``scan_tree`` logic ``make ci`` runs). This
test derives the live count from that gate and asserts the number stated in
``AGENTS.md`` equals it, so the prose can never silently drift again — add or
remove a tracked doc without updating ``AGENTS.md`` and this test FAILS.
"""
import pathlib
import re
import unittest

from scripts import inventory_drift

_ROOT = pathlib.Path(__file__).resolve().parents[1]


class TestTrackedDocsCount(unittest.TestCase):
    def test_agents_md_count_matches_gate(self):
        count = len(inventory_drift.scan_tree(_ROOT))
        text = (_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        m = re.search(r"(\d+)\s+tracked docs", text)
        self.assertIsNotNone(m, "AGENTS.md has no 'N tracked docs' claim")
        self.assertEqual(
            int(m.group(1)),
            count,
            "AGENTS.md's tracked-doc count is stale; it must equal the "
            "inventory_drift gate's live count",
        )


if __name__ == "__main__":
    unittest.main()
