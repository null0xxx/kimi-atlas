"""Read metadata from the ``.kimi-plugin/plugin.json`` manifest.

Pure helpers only — no CLI. :func:`read_version` returns the top-level
``"version"`` string of the manifest at the given path; a missing file raises
``FileNotFoundError`` (propagated from ``open``), and malformed JSON or a
missing ``"version"`` key raise ``json.JSONDecodeError`` / ``KeyError``
respectively rather than being silently swallowed.
"""
from __future__ import annotations

import json
import os


def read_version(manifest_path: str | os.PathLike[str]) -> str:
    """Return the ``"version"`` string of the plugin manifest at ``manifest_path``.

    Accepts a ``str`` or ``os.PathLike`` path. Raises ``FileNotFoundError`` if
    the file does not exist, ``json.JSONDecodeError`` if it is not valid JSON,
    and ``KeyError`` if it lacks a top-level ``"version"`` field.
    """
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    return manifest["version"]
