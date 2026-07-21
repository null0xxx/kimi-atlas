"""The one canonical YAML-frontmatter fence primitive (stdlib-only).

Both the skill-registry parser and the negative-gate role-file stripper build on
this single regex so encoding handling is fixed in exactly one place (F7). It is
BOM-aware (an optional leading U+FEFF) AND CRLF-aware (``\\r?\\n`` at every line
break), closing the opposite blind spots the two former copies each had.
``group(1)`` captures the inner frontmatter block; ``match.end()`` is the offset
just past the closing fence.

The primitive is PURE (string -> parsed) and treats the text as untrusted DATA
(SAFE-2): it never interprets the content, only locates the fence. Each caller
keeps its own raise-vs-passthrough policy on the missing-fence case on top of
this shared match.
"""
from __future__ import annotations

import re

# ``\ufeff?``  optional leading UTF-8 BOM              (was missing from skillregistry's copy)
# ``\r?\n``     CRLF- or LF-terminated lines           (was missing from run_negative_gate's copy)
# ``(.*?)``     the inner frontmatter block             (consumed by skillregistry via group(1))
# ``\r?\n?``    optional newline after the closing fence (run_negative_gate slices at end())
FRONTMATTER_RE = re.compile(
    r"\A\ufeff?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n?",
    re.DOTALL,
)


def match(text: str) -> "re.Match[str] | None":
    """Return the leading-frontmatter match, or ``None`` when no fence is present."""
    return FRONTMATTER_RE.match(text)
