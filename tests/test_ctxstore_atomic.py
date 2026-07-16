"""Unit tests for scripts.ctxstore.write_artifact_atomic — crash-safe DAG writes.

``write_artifact_atomic`` serializes to a ``.tmp`` sibling then ``os.replace`` onto
the target, so a crash mid-write never leaves a torn ``plan.dag.json``. It matches
``write_artifact``'s behavior (JSON for dict/list, else str) and only adds atomicity.
Covered: round-trip via ``read_artifact``; no leftover ``.tmp`` after success; an
overwrite is atomic (the target is only ever the old or the new FULL content).
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import ctxstore

_RUN = "run-atomic"
_DAG = {"nodes": [{"id": "n1", "stage": "INIT"}, {"id": "n2", "stage": "OUTPUT"}],
        "edges": [["n1", "n2"]]}


class WriteArtifactAtomicTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name
        ctxstore.init_run(self.base, _RUN, {"intent": "x"})

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_roundtrips_via_read_artifact(self) -> None:
        ctxstore.write_artifact_atomic(self.base, _RUN, "plan.dag.json", _DAG)
        self.assertEqual(ctxstore.read_artifact(self.base, _RUN, "plan.dag.json"), _DAG)

    def test_returned_path_points_at_target(self) -> None:
        p = ctxstore.write_artifact_atomic(self.base, _RUN, "plan.dag.json", _DAG)
        p = Path(p)
        self.assertEqual(p.name, "plan.dag.json")
        self.assertTrue(p.exists())

    def test_non_json_value_written_as_str(self) -> None:
        ctxstore.write_artifact_atomic(self.base, _RUN, "note.txt", "hello")
        self.assertEqual(ctxstore.read_artifact(self.base, _RUN, "note.txt"), "hello")

    def test_no_tmp_file_remains_after_success(self) -> None:
        ctxstore.write_artifact_atomic(self.base, _RUN, "plan.dag.json", _DAG)
        run_dir = Path(self.base) / _RUN
        leftovers = list(run_dir.glob("*.tmp")) + list(run_dir.glob("*.tmp*"))
        self.assertEqual(leftovers, [])

    def test_overwrite_is_atomic_full_content(self) -> None:
        # Write an initial artifact, then overwrite it; the target must always hold
        # a COMPLETE object (old or new), never a torn partial write.
        old = {"v": 1, "nodes": ["a"]}
        new = {"v": 2, "nodes": ["a", "b", "c"]}
        ctxstore.write_artifact_atomic(self.base, _RUN, "plan.dag.json", old)
        self.assertEqual(ctxstore.read_artifact(self.base, _RUN, "plan.dag.json"), old)
        ctxstore.write_artifact_atomic(self.base, _RUN, "plan.dag.json", new)
        got = ctxstore.read_artifact(self.base, _RUN, "plan.dag.json")
        self.assertIn(got, (old, new))
        self.assertEqual(got, new)
        # And no torn .tmp sibling survives the overwrite.
        run_dir = Path(self.base) / _RUN
        self.assertEqual(list(run_dir.glob("*.tmp")), [])

    def test_does_not_change_write_artifact(self) -> None:
        # Sanity: the non-atomic sibling still round-trips independently.
        ctxstore.write_artifact(self.base, _RUN, "plain.json", _DAG)
        self.assertEqual(ctxstore.read_artifact(self.base, _RUN, "plain.json"), _DAG)


if __name__ == "__main__":
    unittest.main()
