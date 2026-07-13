import unittest

from median import median


class TestMedian(unittest.TestCase):
    def test_odd_length_returns_middle(self):
        self.assertEqual(median([3, 1, 2]), 2)

    def test_even_length_returns_mean_of_middle_two(self):
        self.assertEqual(median([4, 1, 3, 2]), 2.5)

    def test_single_element(self):
        self.assertEqual(median([7]), 7)

    def test_negative_and_unsorted(self):
        self.assertEqual(median([-5, -1, -3]), -3)

    def test_even_length_float_result(self):
        self.assertEqual(median([1, 2]), 1.5)

    def test_does_not_mutate_input(self):
        data = [3, 1, 2]
        median(data)
        self.assertEqual(data, [3, 1, 2])

    def test_empty_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            median([])


if __name__ == "__main__":
    unittest.main()
