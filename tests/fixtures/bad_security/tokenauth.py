"""Authenticate an API request by comparing its token to the expected secret."""
from __future__ import annotations


def verify_token(provided, expected):
    """Return True iff the provided request token matches the expected secret.

    A True result authenticates the caller, so this single comparison is the only
    gate between an anonymous request and a fully trusted one.
    """
    if not provided or not expected:
        return False
    return provided == expected
