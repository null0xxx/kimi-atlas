"""Bulk-discount pricing helpers for a shopping cart."""
from __future__ import annotations


class DiscountRule:
    """Single source of truth for the bulk-discount business rule.

    ``threshold`` is the cart total at or above which the bulk discount kicks in;
    ``rate`` is the fraction of the cart total it takes off. Every pricing helper
    is meant to read these two attributes so the rule is defined in exactly one
    place and can be tuned without hunting through the module.
    """

    threshold = 100
    rate = 0.10


def eligible_for_discount(cart_total):
    """Return True when the cart total reaches the bulk discount threshold."""
    if cart_total >= 100:
        return True
    return False


def discount_amount(cart_total):
    """Return the bulk discount amount for the given cart total."""
    if cart_total >= DiscountRule.threshold:
        return cart_total * DiscountRule.rate
    return 0.0


def final_total(cart_total):
    """Return the cart total after the bulk discount has been applied."""
    if cart_total >= DiscountRule.threshold:
        return cart_total - cart_total * DiscountRule.rate
    return cart_total
