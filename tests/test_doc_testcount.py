"""No hard-coded test-count may live in README.md / AGENTS.md — it always drifts
(F4). The suite size is proven by `make test`, not by prose.

The real suite count rises on every test addition (713 -> 877 -> ...), so any
literal number baked into the provenance docs is perpetually stale. This guard
forbids the drift-prone phrasings from ever reappearing: the shields.io badge
`tests-<N>`, a bare `<N> tests` / `<N> tests green` claim, `<N> unit test(s)`
(space- or hyphen-joined), and the parenthesised dodge `suite green (<N>)` /
`suite (<N>)` (which reads as a count but escapes the "next to the word tests"
patterns). The patterns are deliberately narrow — they require the literal word
"test(s)" next to the number, or a test-*suite* phrase immediately wrapping a
bare parenthesised number, so unrelated counts such as "22 tracked docs",
"115 skills", "712 files", "6-lens", or "v1.0.0" are ignored.
"""
import pathlib
import re
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_DOCS = ("README.md", "AGENTS.md")
_PATTERNS = (
    re.compile(r"tests-\d+"),                       # shields.io badge: tests-<N>
    re.compile(r"\b\d+\s+tests\b"),                 # "<N> tests" / "<N> tests green"
    re.compile(r"\b\d+\s+unit[\s-]tests?\b"),       # "<N> unit tests" / "<N> unit-test(s)"
    re.compile(r"\bsuite\s+green\s*\(\d+\)"),       # paren dodge: "suite green (<N>)"
    re.compile(r"\btest[\s-]suite\s*\(\d+\)"),      # paren dodge: "test-suite (<N>)"
)

# A crafted sample per pattern that MUST be caught — proves the guard is not vacuous
# (esp. the paren-dodge patterns added after "unit-test suite green (919)" slipped past).
_MUST_CATCH = (
    "tests-920", "920 tests", "920 unit tests", "920 unit-test",
    "unit-test suite green (920)", "the test-suite (920) is green",
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
        # The guard must actually bite: every crafted phrasing is caught by some pattern.
        for sample in _MUST_CATCH:
            self.assertTrue(
                any(p.search(sample) for p in _PATTERNS),
                f"guard is vacuous: no pattern catches the drift-prone phrasing {sample!r}",
            )


if __name__ == "__main__":
    unittest.main()
