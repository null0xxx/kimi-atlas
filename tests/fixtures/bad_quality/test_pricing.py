import unittest

from pricing import eligible_for_discount, discount_amount, final_total


class TestPricing(unittest.TestCase):
    def test_eligible_above_threshold(self):
        self.assertTrue(eligible_for_discount(150))

    def test_eligible_at_threshold(self):
        self.assertTrue(eligible_for_discount(100))

    def test_not_eligible_below_threshold(self):
        self.assertFalse(eligible_for_discount(99))

    def test_discount_amount_for_qualifying_cart(self):
        self.assertEqual(discount_amount(200), 20.0)

    def test_discount_amount_at_threshold(self):
        self.assertEqual(discount_amount(100), 10.0)

    def test_no_discount_below_threshold(self):
        self.assertEqual(discount_amount(50), 0.0)

    def test_final_total_applies_discount(self):
        self.assertEqual(final_total(200), 180.0)

    def test_final_total_at_threshold(self):
        self.assertEqual(final_total(100), 90.0)

    def test_final_total_below_threshold_unchanged(self):
        self.assertEqual(final_total(50), 50.0)


if __name__ == "__main__":
    unittest.main()
