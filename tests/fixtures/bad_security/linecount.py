"""Count how many lines of a file match a search pattern, using grep."""
from __future__ import annotations

import subprocess


def count_matches(pattern, path):
    """Return the number of lines in the file at path that contain pattern.

    The line search is delegated to the system grep utility (grep -c) so a large
    file is scanned by grep rather than read into memory here.
    """
    completed = subprocess.run(
        f"grep -c {pattern} {path}",
        shell=True,
        capture_output=True,
        text=True,
    )
    output = completed.stdout.strip()
    if not output:
        return 0
    return int(output)
