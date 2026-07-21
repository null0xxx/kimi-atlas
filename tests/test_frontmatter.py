"""One shared frontmatter primitive fixes the opposite BOM/CRLF blind spots (F7)."""
import unittest

from scripts import frontmatter, run_negative_gate as rng, skillregistry

_BOM = "﻿"


class TestSharedPrimitive(unittest.TestCase):
    """The primitive itself is BOTH BOM-aware AND CRLF-aware."""

    def test_lf(self):
        m = frontmatter.match("---\nname: a\n---\nbody\n")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "name: a")

    def test_crlf(self):
        m = frontmatter.match("---\r\nname: a\r\n---\r\nbody\n")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "name: a")

    def test_bom_lf(self):
        m = frontmatter.match(_BOM + "---\nname: a\n---\nbody\n")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "name: a")

    def test_bom_crlf(self):
        m = frontmatter.match(_BOM + "---\r\nname: a\r\n---\r\nbody\n")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "name: a")

    def test_no_fence(self):
        self.assertIsNone(frontmatter.match("no fence here\n"))


class TestSharedFrontmatter(unittest.TestCase):
    """Each caller now handles its previously-broken case and keeps its own contract."""

    def test_skillregistry_parses_bom_prefixed(self):
        text = _BOM + "---\nname: demo\ndescription: d\n---\nbody\n"
        self.assertEqual(skillregistry.parse_frontmatter(text)["name"], "demo")

    def test_strip_frontmatter_handles_crlf(self):
        text = "---\r\ntools: Read\r\nmodel: x\r\n---\r\nPROMPT BODY\n"
        self.assertEqual(rng.strip_frontmatter(text), "PROMPT BODY\n")

    def test_both_use_shared_pattern(self):
        self.assertIs(skillregistry._FRONTMATTER_RE, frontmatter.FRONTMATTER_RE)
        self.assertIs(rng._FRONTMATTER_RE, frontmatter.FRONTMATTER_RE)

    def test_missing_fence_still_raises_and_passes_through(self):
        with self.assertRaises(ValueError):
            skillregistry.parse_frontmatter("no fence here\n")
        self.assertEqual(rng.strip_frontmatter("no fence\n"), "no fence\n")


if __name__ == "__main__":
    unittest.main()
