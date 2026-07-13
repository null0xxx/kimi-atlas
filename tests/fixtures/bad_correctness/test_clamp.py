import unittest

from clamp import clamp


class TestClamp(unittest.TestCase):
    def test_value_below_low_is_raised_to_low(self):
        self.assertEqual(clamp(-3, 0, 10), 0)

    def test_value_within_range_is_unchanged(self):
        self.assertEqual(clamp(4, 0, 10), 4)

    def test_value_equal_to_low_is_unchanged(self):
        self.assertEqual(clamp(0, 0, 10), 0)


if __name__ == "__main__":
    unittest.main()
