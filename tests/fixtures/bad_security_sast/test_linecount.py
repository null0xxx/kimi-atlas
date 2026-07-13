import os
import tempfile
import unittest

from linecount import count_matches


class TestCountMatches(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".txt", text=True)
        with os.fdopen(fd, "w") as handle:
            handle.write("alpha\nbeta\nalpha\ngamma\n")

    def tearDown(self):
        os.remove(self.path)

    def test_counts_matching_lines(self):
        self.assertEqual(count_matches("alpha", self.path), 2)

    def test_counts_single_match(self):
        self.assertEqual(count_matches("gamma", self.path), 1)

    def test_no_match_returns_zero(self):
        self.assertEqual(count_matches("delta", self.path), 0)


if __name__ == "__main__":
    unittest.main()
