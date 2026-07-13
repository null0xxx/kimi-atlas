"""Advisory requirements-coverage lint (lens 6) — MEDIUM only, never HIGH (V6).

For each frozen success criterion, compute a **literal keyword/identifier
token-overlap** between the criterion and the change diff. A criterion whose
significant tokens have *zero* overlap with the diff is emitted as a MEDIUM
"unconfirmed" defect the CORRECTNESS critic must close. Optionally, any file
changed outside ``scope_paths`` is emitted as a MEDIUM scope-creep defect.

This is a pure string heuristic and is **gameable both ways** — a comment naming
a criterion yields a false green, and an implementation using different
identifiers yields a false red (wasted refine budget). It therefore emits at
most MEDIUM and can never flip the gate; a real gap is escalated only by a model
critic with evidence. Both limits are pinned by explicit unit tests.
"""
from __future__ import annotations

import re

_MEDIUM = "MEDIUM"
_CATEGORY = "REQUIREMENTS-COVERAGE"

# Identifier-ish runs. camelCase/snake_case are split into sub-tokens (below) so
# `emailAddress` / `email_address` overlap the criterion words "email address".
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_CAMEL_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z][a-z]+|[a-z]+|[A-Z]+")

# Diff bookkeeping.
_ADDED_LINE_RE = re.compile(r"^\+(?!\+\+).*$", re.MULTILINE)
_NEW_PATH_RE = re.compile(r"^\+\+\+ (?:b/)?(.+)$", re.MULTILINE)

# Generic words carry no coverage signal; dropping them avoids trivially-matched
# criteria (every diff contains "the", "return", "value", …).
_STOPWORDS: frozenset[str] = frozenset({
    "the", "and", "for", "with", "that", "this", "from", "into", "than", "then",
    "when", "else", "must", "should", "shall", "will", "can", "may", "each",
    "every", "all", "any", "not", "are", "was", "were", "has", "have", "its",
    "value", "values", "return", "returns", "given", "test", "tests", "case",
    "cases", "function", "method", "code", "using", "use", "used", "such",
    "which", "their", "them", "also", "only", "both", "via", "per",
})

_MIN_TOKEN_LEN = 3


def _split_identifier(ident: str) -> list[str]:
    """Split a snake_case/camelCase identifier into its component words."""
    parts: list[str] = [ident]
    for chunk in ident.split("_"):
        parts.extend(_CAMEL_RE.findall(chunk))
    return parts


def _tokenize(text: str) -> set[str]:
    """Return the set of lowercased sub-tokens (length >= 3) found in ``text``."""
    tokens: set[str] = set()
    for word in _WORD_RE.findall(text):
        for part in _split_identifier(word):
            part = part.lower()
            if len(part) >= _MIN_TOKEN_LEN:
                tokens.add(part)
    return tokens


def _significant_tokens(criterion: str) -> set[str]:
    """Tokens of a criterion that carry coverage signal (stopwords removed)."""
    return _tokenize(criterion) - _STOPWORDS


def _added_tokens(diff_text: str) -> set[str]:
    """Tokens appearing on added ('+') lines of the diff (excludes '+++' headers)."""
    added = "\n".join(
        line[1:] for line in _ADDED_LINE_RE.findall(diff_text)
    )
    return _tokenize(added)


def _changed_paths(diff_text: str) -> list[str]:
    """New-side file paths from the diff's '+++' headers (excludes /dev/null)."""
    paths: list[str] = []
    for p in _NEW_PATH_RE.findall(diff_text):
        p = p.strip()
        if p and p != "/dev/null":
            paths.append(p)
    return paths


def _under_scope(path: str, scope_paths: list[str]) -> bool:
    """True if ``path`` is at or below any entry in ``scope_paths``."""
    for scope in scope_paths:
        s = scope.rstrip("/")
        if path == s or path.startswith(s + "/"):
            return True
    return False


def coverage(
    success_criteria: list[str],
    diff_text: str,
    scope_paths: list[str] | None = None,
) -> list[dict]:
    """Return MEDIUM coverage/scope defects for a change diff.

    Args:
        success_criteria: the frozen, ordered success criteria (never re-derived).
        diff_text: the unified diff of the change under review.
        scope_paths: optional allowed paths; when provided, any changed file
            outside every scope entry is flagged as MEDIUM scope-creep. When
            ``None`` the scope check is skipped entirely.

    Returns:
        A list of MEDIUM defects: one "unconfirmed" per criterion with no
        token-overlap against the diff, then one "scope-creep" per out-of-scope
        changed file. Never emits HIGH or CRITICAL (V6). Deterministic order:
        criteria in given order, then changed files in diff order.
    """
    diff_tokens = _added_tokens(diff_text)
    defects: list[dict] = []

    for i, criterion in enumerate(success_criteria):
        crit_tokens = _significant_tokens(criterion)
        if not crit_tokens:
            # Nothing checkable (e.g. all-stopword criterion) — cannot confirm
            # or deny; stay silent rather than emit a meaningless defect.
            continue
        if crit_tokens.isdisjoint(diff_tokens):
            defects.append({
                "id": f"RC{i}",
                "category": _CATEGORY,
                "severity": _MEDIUM,
                "location": f"success_criteria[{i}]",
                "fix": f"No diff token overlaps criterion {criterion!r}; confirm it "
                       f"is implemented (advisory — the CORRECTNESS critic must close this).",
            })

    if scope_paths is not None:
        for j, path in enumerate(_changed_paths(diff_text)):
            if not _under_scope(path, scope_paths):
                defects.append({
                    "id": f"SC{j}",
                    "category": _CATEGORY,
                    "severity": _MEDIUM,
                    "location": path,
                    "fix": f"File {path!r} is changed but lies outside the declared "
                           f"scope_paths ({scope_paths}); confirm the edit is intended.",
                })

    return defects
