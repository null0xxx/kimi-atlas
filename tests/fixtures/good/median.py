"""A small, pure statistics helper."""
from __future__ import annotations


def median(numbers):
    """Return the median of a non-empty sequence of numbers.

    For an odd-length input the single middle value is returned. For an
    even-length input the arithmetic mean of the two middle values is returned.
    The input is copied before sorting, so the caller's sequence is never
    mutated. Raises ValueError when the input is empty.
    """
    ordered = sorted(numbers)
    if not ordered:
        raise ValueError("median() requires at least one number")
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2
