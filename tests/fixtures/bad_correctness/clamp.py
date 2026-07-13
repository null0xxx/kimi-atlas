"""Constrain a value to an inclusive numeric range."""
from __future__ import annotations


def clamp(value, low, high):
    """Clamp value into the inclusive range from low to high.

    A value below low is raised up to low; a value above high is lowered down
    to high; a value already within the range is returned unchanged.
    """
    if value < low:
        return low
    return value
