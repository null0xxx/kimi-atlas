"""No hard-coded test-count may live in README.md / AGENTS.md — it always drifts
(F4). The suite size is proven by `make test`, not by prose.

The real suite count rises on every test addition (713 -> 877 -> ...), so any
literal number baked into the provenance docs is perpetually stale. This guard
forbids the drift-prone phrasings from ever reappearing: the shields.io badge
`tests-<N>`, a bare `<N> tests` / `<N> tests green` claim, and `<N> unit test(s)`
(space- or hyphen-joined). The patterns are deliberately narrow — they require
the literal word "test(s)" next to the number, so unrelated counts such as
"22 tracked docs", "115 skills", "712 files", "6-lens", or "v1.0.0" are ignored.
"""
import pathlib
import re
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_DOCS = ("README.md", "AGENTS.md")
_PATTERNS = (
    re.compile(r"tests-\d+"),                   # shields.io badge: tests-<N>
    re.compile(r"\b\d+\s+tests\b"),             # "<N> tests" / "<N> tests green"
    re.compile(r"\b\d+\s+unit[\s-]tests?\b"),   # "<N> unit tests" / "<N> unit-test(s)"
)


class TestNoHardcodedTestCount(unittest.TestCase):
    def test_docs_have_no_numeric_test_count(self):
        for name in _DOCS:
            text = (_ROOT / name).read_text(encoding="utf-8")
            for pat in _PATTERNS:
                match = pat.search(text)
                found = match.group(0) if match else None
                self.assertIsNone(
                    match,
                    f"{name}: hard-coded test count {pat.pattern!r} must be removed "
                    f"(found {found!r}) — reference `make test` instead of a "
                    f"literal number, which always drifts (F4).",
                )


if __name__ == "__main__":
    unittest.main()
