"""Unit tests for scripts.scheduler — the pure flat-W=3 work-stealing decision core.

Pure over plain dag dicts + scalar inputs; the real dispatch / git-apply / suite-runner
/ free-mem sample / lease clock are the ROOT's deferred I/O. Covers the §6 memory rows,
the §7 halting-drive, crash liveness, and the aggregate that never fabricates a pass.
"""
from __future__ import annotations

import unittest

from scripts import scheduler


class ClassMapTests(unittest.TestCase):
    def test_kind_to_class(self) -> None:
        for kind in ("SCOUT", "CRITIC", "DECOMPOSE"):
            self.assertEqual(scheduler.job_class({"kind": kind}), "read_only")
        for kind in ("DRAFT", "CODE", "LEAF"):
            self.assertEqual(scheduler.job_class({"kind": kind}), "coder")
        for kind in ("BUILD", "INTEGRATE", "INTEGRATION"):
            self.assertEqual(scheduler.job_class({"kind": kind}), "build")

    def test_unknown_kind_is_build_worst_case(self) -> None:
        self.assertEqual(scheduler.job_class({"kind": "???"}), "build")
        self.assertEqual(scheduler.job_class({}), "build")

    def test_class_costs(self) -> None:
        self.assertEqual(scheduler.class_rss_mb("read_only"), 700)
        self.assertEqual(scheduler.class_rss_mb("coder"), 1300)
        self.assertEqual(scheduler.class_rss_mb("build"), 2048)

    def test_constants(self) -> None:
        self.assertEqual(
            (scheduler.ROOT_RSS_MB, scheduler.CEILING_MB, scheduler.FREE_FLOOR_MB, scheduler.W_MAX),
            (1024, 4608, 3072, 3),
        )
