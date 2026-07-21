"""Unit tests for scripts.ctxstore — persistence, canonical stages, refine ledger.

Each pure/IO function gets happy + failure + boundary coverage, plus the two
kimi-atlas invariants: per-``run_id`` keying (runs are isolated under one base) and
a MONOTONIC refine counter read from the on-disk ledger (advance REFINE twice →
get_refine_passes == 2).
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import ctxstore

_PACKET = {
    "intent": "implement add(a, b)",
    "success_criteria": ["returns a + b", "handles negatives"],
    "scope_paths": ["add.py"],
    "verify_cmd": "python3 -m unittest",
    "baseline_sha": "deadbeef",
    "debug_tokens": ["TODO", "FIXME"],
    "test_glob": "test_*.py",
}

# The 9 fields the context schema requires (references/schemas.json).
_CONTEXT_REQUIRED = {
    "run_id": str,
    "intent": str,
    "success_criteria": list,
    "stages": dict,
    "refine_passes": int,
    "draft_ref": str,
    "verify_cmd": str,
    "scope_paths": list,
    "baseline_sha": str,
}


class CtxStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name
        self.run_id = "20260713-000000"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ---- constants --------------------------------------------------------

    def test_stages_are_canonical_and_partitioned(self) -> None:
        # Full ordered machine (PLAN §2 fact 13).
        self.assertEqual(
            ctxstore.STAGES,
            ("INIT", "INTENT_CAPTURED", "CLARIFY", "TRIAGED", "GROUNDED",
             "CODED", "VERIFIED", "REFINE", "OUTPUT"),
        )
        self.assertEqual(ctxstore.CONDITIONAL_STAGES, ("CLARIFY", "REFINE"))
        # Mandatory = STAGES minus the conditional ones, order preserved.
        self.assertEqual(
            ctxstore.MANDATORY_STAGES,
            ("INIT", "INTENT_CAPTURED", "TRIAGED", "GROUNDED",
             "CODED", "VERIFIED", "OUTPUT"),
        )
        self.assertEqual(
            set(ctxstore.MANDATORY_STAGES) & set(ctxstore.CONDITIONAL_STAGES), set()
        )

    # ---- init_run (happy / immutability / schema shape) -------------------

    def test_init_run_writes_intent_and_full_context(self) -> None:
        ctxstore.init_run(self.base, self.run_id, _PACKET)
        run_dir = Path(self.base) / self.run_id
        self.assertTrue((run_dir / "intent.txt").exists())
        self.assertEqual(
            (run_dir / "intent.txt").read_text(encoding="utf-8"), _PACKET["intent"]
        )
        st = ctxstore.get_state(self.base, self.run_id)
        # Every context-schema-required field is present with the right type.
        for field, typ in _CONTEXT_REQUIRED.items():
            self.assertIn(field, st)
            self.assertIsInstance(st[field], typ)
        self.assertEqual(st["current_state"], "INIT")
        self.assertEqual(st["stages"], {})
        self.assertEqual(st["refine_passes"], 0)
        self.assertEqual(st["draft_ref"], "")
        self.assertEqual(st["success_criteria"], _PACKET["success_criteria"])
        self.assertEqual(st["verify_cmd"], _PACKET["verify_cmd"])
        self.assertEqual(st["scope_paths"], _PACKET["scope_paths"])
        self.assertEqual(st["baseline_sha"], _PACKET["baseline_sha"])
        # clarify_resolution is optional — absent at init (before CLARIFY fires).
        self.assertNotIn("clarify_resolution", st)

    def test_init_run_is_idempotent_and_intent_immutable(self) -> None:
        ctxstore.init_run(self.base, self.run_id, _PACKET)
        ctxstore.advance(self.base, self.run_id, "INTENT_CAPTURED")
        # Re-init with a different intent must NOT clobber captured state.
        ctxstore.init_run(self.base, self.run_id, {**_PACKET, "intent": "HIJACKED"})
        st = ctxstore.get_state(self.base, self.run_id)
        self.assertEqual(st["intent"], _PACKET["intent"])
        self.assertIn("INTENT_CAPTURED", st["stages"])
        run_dir = Path(self.base) / self.run_id
        self.assertEqual(
            (run_dir / "intent.txt").read_text(encoding="utf-8"), _PACKET["intent"]
        )

    def test_init_run_defaults_missing_packet_fields(self) -> None:
        # Boundary: an empty packet still yields a schema-shaped context.
        ctxstore.init_run(self.base, "empty", {})
        st = ctxstore.get_state(self.base, "empty")
        for field, typ in _CONTEXT_REQUIRED.items():
            self.assertIsInstance(st[field], typ)
        self.assertEqual(st["intent"], "")
        self.assertEqual(st["success_criteria"], [])

    # ---- advance (stage ledger + telemetry) -------------------------------

    def test_advance_marks_stage_logs_and_returns_state(self) -> None:
        ctxstore.init_run(self.base, self.run_id, _PACKET)
        returned = ctxstore.advance(self.base, self.run_id, "INTENT_CAPTURED")
        self.assertEqual(returned["current_state"], "INTENT_CAPTURED")
        self.assertEqual(returned["stages"]["INTENT_CAPTURED"]["status"], "done")
        # Exactly one telemetry line, carrying the stage.
        log = (Path(self.base) / self.run_id / "log.jsonl").read_text(encoding="utf-8")
        lines = [ln for ln in log.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1)
        rec = json.loads(lines[0])
        self.assertEqual(rec["stage"], "INTENT_CAPTURED")
        self.assertEqual(rec["run_id"], self.run_id)
        self.assertIn("ts", rec)

    def test_advance_records_telemetry_extras(self) -> None:
        ctxstore.init_run(self.base, self.run_id, _PACKET)
        ctxstore.advance(self.base, self.run_id, "CODED", agent="coder", est_tokens=42)
        log = (Path(self.base) / self.run_id / "log.jsonl").read_text(encoding="utf-8")
        rec = json.loads([ln for ln in log.splitlines() if ln.strip()][-1])
        self.assertEqual(rec["agent"], "coder")
        self.assertEqual(rec["est_tokens"], 42)

    def test_advance_updates_merge_state_fields(self) -> None:
        # CLARIFY writes clarify_resolution atomically with the stage transition.
        ctxstore.init_run(self.base, self.run_id, _PACKET)
        st = ctxstore.advance(
            self.base, self.run_id, "CLARIFY",
            updates={"clarify_resolution": "verify_cmd supplied by user"},
        )
        self.assertEqual(st["clarify_resolution"], "verify_cmd supplied by user")
        self.assertIn("CLARIFY", st["stages"])
        # Persisted, not just in the returned dict.
        self.assertEqual(
            ctxstore.get_state(self.base, self.run_id)["clarify_resolution"],
            "verify_cmd supplied by user",
        )

    def test_one_log_line_per_canonical_stage(self) -> None:
        ctxstore.init_run(self.base, self.run_id, _PACKET)
        for stage in ("INIT", "INTENT_CAPTURED", "TRIAGED", "GROUNDED",
                      "CODED", "VERIFIED", "OUTPUT"):
            ctxstore.advance(self.base, self.run_id, stage)
        log = (Path(self.base) / self.run_id / "log.jsonl").read_text(encoding="utf-8")
        stages = [json.loads(ln)["stage"] for ln in log.splitlines() if ln.strip()]
        self.assertEqual(
            stages,
            ["INIT", "INTENT_CAPTURED", "TRIAGED", "GROUNDED",
             "CODED", "VERIFIED", "OUTPUT"],
        )

    # ---- refine counter (MONOTONIC, ledger-derived) -----------------------

    def test_refine_counter_zero_before_any_refine(self) -> None:
        ctxstore.init_run(self.base, self.run_id, _PACKET)
        ctxstore.advance(self.base, self.run_id, "VERIFIED")
        self.assertEqual(ctxstore.get_refine_passes(self.base, self.run_id), 0)

    def test_refine_counter_monotonic_two_passes(self) -> None:
        ctxstore.init_run(self.base, self.run_id, _PACKET)
        ctxstore.advance(self.base, self.run_id, "REFINE")
        self.assertEqual(ctxstore.get_refine_passes(self.base, self.run_id), 1)
        st = ctxstore.advance(self.base, self.run_id, "REFINE")
        self.assertEqual(ctxstore.get_refine_passes(self.base, self.run_id), 2)
        # The persisted state field mirrors the ledger count.
        self.assertEqual(st["refine_passes"], 2)

    def test_refine_counter_reads_ledger_not_state_memory(self) -> None:
        # Even if state's refine_passes is corrupted, the ledger is authoritative.
        ctxstore.init_run(self.base, self.run_id, _PACKET)
        ctxstore.advance(self.base, self.run_id, "REFINE")
        state_path = Path(self.base) / self.run_id / "state.json"
        data = json.loads(state_path.read_text(encoding="utf-8"))
        data["refine_passes"] = 99  # tamper with model-visible state
        state_path.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(ctxstore.get_refine_passes(self.base, self.run_id), 1)

    def test_get_refine_passes_zero_when_no_ledger(self) -> None:
        # Boundary: no run / no log file at all → 0, not an error.
        self.assertEqual(ctxstore.get_refine_passes(self.base, "nonexistent"), 0)

    # ---- run_id keying (isolation) ----------------------------------------

    def test_runs_are_isolated_by_run_id(self) -> None:
        ctxstore.init_run(self.base, "runA", _PACKET)
        ctxstore.init_run(self.base, "runB", {**_PACKET, "intent": "other"})
        ctxstore.advance(self.base, "runA", "REFINE")
        ctxstore.advance(self.base, "runA", "REFINE")
        ctxstore.advance(self.base, "runB", "CODED")
        self.assertEqual(ctxstore.get_refine_passes(self.base, "runA"), 2)
        self.assertEqual(ctxstore.get_refine_passes(self.base, "runB"), 0)
        self.assertEqual(ctxstore.get_state(self.base, "runA")["intent"], _PACKET["intent"])
        self.assertEqual(ctxstore.get_state(self.base, "runB")["intent"], "other")
        self.assertNotIn("CODED", ctxstore.get_state(self.base, "runA")["stages"])

    # ---- artifacts + drafts ----------------------------------------------

    def test_write_read_artifact_json_and_text(self) -> None:
        ctxstore.init_run(self.base, self.run_id, _PACKET)
        ctxstore.write_artifact(self.base, self.run_id, "critic.json", {"verdict": "OK"})
        ctxstore.write_artifact(self.base, self.run_id, "note.txt", "hello")
        self.assertEqual(
            ctxstore.read_artifact(self.base, self.run_id, "critic.json"),
            {"verdict": "OK"},
        )
        self.assertEqual(
            ctxstore.read_artifact(self.base, self.run_id, "note.txt"), "hello"
        )

    def test_write_draft_versions_and_updates_draft_ref(self) -> None:
        ctxstore.init_run(self.base, self.run_id, _PACKET)
        p1 = ctxstore.write_draft(self.base, self.run_id, "v1 body")
        self.assertTrue(p1.endswith("draft.v1.md"))
        self.assertEqual(ctxstore.read_draft(self.base, self.run_id), "v1 body")
        self.assertEqual(
            ctxstore.get_state(self.base, self.run_id)["draft_ref"], "draft.v1.md"
        )
        p2 = ctxstore.write_draft(self.base, self.run_id, "v2 body")
        self.assertTrue(p2.endswith("draft.v2.md"))
        self.assertEqual(ctxstore.read_draft(self.base, self.run_id), "v2 body")
        self.assertEqual(
            ctxstore.get_state(self.base, self.run_id)["draft_ref"], "draft.v2.md"
        )

    # ---- failure modes ----------------------------------------------------

    def test_get_state_missing_run_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            ctxstore.get_state(self.base, "never-created")

    def test_read_draft_missing_raises(self) -> None:
        ctxstore.init_run(self.base, self.run_id, _PACKET)
        with self.assertRaises(FileNotFoundError):
            ctxstore.read_draft(self.base, self.run_id)

    def test_read_artifact_missing_raises(self) -> None:
        ctxstore.init_run(self.base, self.run_id, _PACKET)
        with self.assertRaises(FileNotFoundError):
            ctxstore.read_artifact(self.base, self.run_id, "absent.json")


class RollbackLedgerTests(unittest.TestCase):
    """Additive two-phase rollback ledger ops — pure persistence, no subprocess.

    Pins the frozen invariants (Part C): log.jsonl append-only + NEVER truncated, the
    REFINE counter stays monotonic (rollback lines carry stage=="ROLLBACK", never "REFINE"),
    intent.txt immutable, and get_refine_passes byte-for-byte unaffected by any rollback.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name
        self.run_id = "20260720-000000"
        ctxstore.init_run(self.base, self.run_id, dict(_PACKET))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _log_lines(self) -> list[str]:
        p = Path(self.base) / self.run_id / "log.jsonl"
        return p.read_text(encoding="utf-8").splitlines() if p.exists() else []

    # ---- last_green_stage (pure) -----------------------------------------

    def test_last_green_stage_none_when_no_checkpoints(self) -> None:
        self.assertIsNone(ctxstore.last_green_stage(ctxstore.get_state(self.base, self.run_id)))

    def test_last_green_stage_picks_furthest_along_STAGES(self) -> None:
        state = {"checkpoints": {"CODED": "sha_coded", "VERIFIED": "sha_verified"}}
        # VERIFIED is further along STAGES than CODED -> the last STABLE ref, not baseline.
        self.assertEqual(ctxstore.last_green_stage(state), "VERIFIED")

    def test_last_green_stage_ignores_unknown_stage_keys(self) -> None:
        state = {"checkpoints": {"CODED": "s1", "NOT_A_STAGE": "s2"}}
        self.assertEqual(ctxstore.last_green_stage(state), "CODED")

    def test_last_green_stage_is_pure_no_disk(self) -> None:
        before = sorted(p.name for p in (Path(self.base) / self.run_id).iterdir())
        ctxstore.last_green_stage({"checkpoints": {"VERIFIED": "x"}})
        after = sorted(p.name for p in (Path(self.base) / self.run_id).iterdir())
        self.assertEqual(before, after)  # touched nothing

    # ---- rollback_to (two-phase append) ----------------------------------

    def test_rollback_intent_then_complete_updates_state(self) -> None:
        ctxstore.rollback_to(self.base, self.run_id, "sha1", "VERIFIED", "rollback_intent")
        st = ctxstore.get_state(self.base, self.run_id)
        self.assertEqual(st["rollback_pending"], {"target_sha": "sha1", "target_stage": "VERIFIED"})
        st2 = ctxstore.rollback_to(self.base, self.run_id, "sha1", "VERIFIED", "rollback_complete")
        self.assertNotIn("rollback_pending", st2)
        self.assertEqual(st2["current_state"], "VERIFIED")

    def test_rollback_to_rejects_unknown_event(self) -> None:
        with self.assertRaises(ValueError):
            ctxstore.rollback_to(self.base, self.run_id, "sha1", "VERIFIED", "bogus")

    def test_rollback_lines_carry_ROLLBACK_stage_not_REFINE(self) -> None:
        ctxstore.rollback_to(self.base, self.run_id, "sha1", "VERIFIED", "rollback_intent")
        rec = json.loads(self._log_lines()[-1])
        self.assertEqual(rec["stage"], "ROLLBACK")
        self.assertEqual(rec["event"], "rollback_intent")
        self.assertEqual(rec["target_sha"], "sha1")

    # ---- FROZEN-invariant pins -------------------------------------------

    def test_rollback_never_inflates_refine_counter(self) -> None:
        ctxstore.advance(self.base, self.run_id, "REFINE")
        ctxstore.advance(self.base, self.run_id, "REFINE")
        self.assertEqual(ctxstore.get_refine_passes(self.base, self.run_id), 2)
        ctxstore.rollback_to(self.base, self.run_id, "sha1", "VERIFIED", "rollback_intent")
        ctxstore.rollback_to(self.base, self.run_id, "sha1", "VERIFIED", "rollback_complete")
        self.assertEqual(ctxstore.get_refine_passes(self.base, self.run_id), 2)  # monotonic, untouched

    def test_refine_advance_after_rollback_stays_monotonic(self) -> None:
        # Task-invariant (2): a rollback_to followed by a REFINE advance never LOWERS the
        # count — it keeps climbing. Pre-count is nonzero, so this is not a 0==0 vacuous pass.
        ctxstore.advance(self.base, self.run_id, "REFINE")
        ctxstore.advance(self.base, self.run_id, "REFINE")
        pre = ctxstore.get_refine_passes(self.base, self.run_id)
        self.assertEqual(pre, 2)
        ctxstore.rollback_to(self.base, self.run_id, "sha1", "VERIFIED", "rollback_intent")
        ctxstore.rollback_to(self.base, self.run_id, "sha1", "VERIFIED", "rollback_complete")
        # A genuine REFINE after the rollback advances the ledger, never resets it.
        ctxstore.advance(self.base, self.run_id, "REFINE")
        post = ctxstore.get_refine_passes(self.base, self.run_id)
        self.assertGreater(post, pre)  # strictly monotonic
        self.assertEqual(post, 3)

    def test_log_is_only_appended_never_truncated(self) -> None:
        ctxstore.advance(self.base, self.run_id, "REFINE")
        n0 = len(self._log_lines())
        b0 = (Path(self.base) / self.run_id / "log.jsonl").stat().st_size
        ctxstore.rollback_to(self.base, self.run_id, "sha1", "VERIFIED", "rollback_intent")
        ctxstore.rollback_to(self.base, self.run_id, "sha1", "VERIFIED", "rollback_complete")
        self.assertEqual(len(self._log_lines()), n0 + 2)  # only grew (line count)
        self.assertGreater((Path(self.base) / self.run_id / "log.jsonl").stat().st_size, b0)  # only grew (bytes)

    def test_intent_txt_untouched_by_rollback(self) -> None:
        p = Path(self.base) / self.run_id / "intent.txt"
        before = p.read_text(encoding="utf-8")
        ctxstore.rollback_to(self.base, self.run_id, "sha1", "VERIFIED", "rollback_intent")
        self.assertEqual(p.read_text(encoding="utf-8"), before)

    # ---- failure path: unknown target stage → sensible error, no partial write ---

    def test_rollback_to_rejects_unknown_target_stage(self) -> None:
        n0 = len(self._log_lines())
        st_before = ctxstore.get_state(self.base, self.run_id)
        with self.assertRaises(ValueError):
            ctxstore.rollback_to(self.base, self.run_id, "sha1", "NOT_A_STAGE", "rollback_intent")
        # No partial write: log untouched and no rollback_pending leaked into state.
        self.assertEqual(len(self._log_lines()), n0)
        st_after = ctxstore.get_state(self.base, self.run_id)
        self.assertNotIn("rollback_pending", st_after)
        self.assertEqual(st_after["current_state"], st_before["current_state"])

    # ---- pending_rollback (ledger-derived, torn-recovery) ----------------

    def test_pending_rollback_none_when_balanced(self) -> None:
        ctxstore.rollback_to(self.base, self.run_id, "sha1", "VERIFIED", "rollback_intent")
        ctxstore.rollback_to(self.base, self.run_id, "sha1", "VERIFIED", "rollback_complete")
        self.assertIsNone(ctxstore.pending_rollback(self.base, self.run_id))

    def test_pending_rollback_reports_open_intent(self) -> None:
        ctxstore.rollback_to(self.base, self.run_id, "sha9", "VERIFIED", "rollback_intent")
        self.assertEqual(
            ctxstore.pending_rollback(self.base, self.run_id),
            {"target_sha": "sha9", "target_stage": "VERIFIED"},
        )

    def test_pending_rollback_skips_malformed_lines(self) -> None:
        (Path(self.base) / self.run_id / "log.jsonl").open("a", encoding="utf-8").write("not json\n")
        self.assertIsNone(ctxstore.pending_rollback(self.base, self.run_id))


if __name__ == "__main__":
    unittest.main()
