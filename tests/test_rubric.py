"""The rubric vocabulary lives in exactly one module and every pure core imports
it (F6)."""
import unittest

from scripts import quality, rubric, run_negative_gate, verdict


class TestRubricSingleSource(unittest.TestCase):
    def test_dimensions_canonical(self):
        self.assertEqual(
            rubric.DIMENSIONS,
            ("CORRECTNESS", "CODE-QUALITY", "SECURITY",
             "TEST-ADEQUACY", "DOES-IT-RUN", "REQUIREMENTS-COVERAGE"),
        )

    def test_all_cores_share_one_dimensions_object(self):
        self.assertIs(verdict._DIMENSIONS, rubric.DIMENSIONS)
        self.assertIs(quality._DIMENSIONS, rubric.DIMENSIONS)

    def test_all_cores_share_one_blocking_set(self):
        self.assertIs(verdict._BLOCKING, rubric.BLOCKING)
        self.assertIs(quality._BLOCKING, rubric.BLOCKING)
        self.assertIs(run_negative_gate._BLOCKING, rubric.BLOCKING)

    def test_schema_key_sets_shared(self):
        self.assertIs(quality._SEVERITIES, rubric.SEVERITIES)
        self.assertIs(quality._CRITIC_TOP_KEYS, rubric.CRITIC_TOP_KEYS)
        self.assertIs(quality._DEFECT_KEYS, rubric.DEFECT_KEYS)


if __name__ == "__main__":
    unittest.main()
