"""Regression tests for the standard-library, read-only raw M6 v2 auditor."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_m6_v2_artifacts import (
    GENESIS,
    LEDGER_SCHEMA,
    MANIFEST_SCHEMA,
    canonical_bytes,
    expected_schedule,
    latency_summary,
    outcome_from_trace,
    portable_artifact_root,
    safe_relative,
    trace_rows,
    verify_ledger,
    verify_trace_chain,
    verify_tree,
)


class M6V2RawAuditTests(unittest.TestCase):
    def test_artifact_root_report_is_portable_and_repository_relative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "artifacts" / "m6" / "v2" / "run-id"
            root.mkdir(parents=True)
            self.assertEqual(portable_artifact_root(root), "artifacts/m6/v2/run-id")

    def test_external_artifact_root_report_does_not_expose_host_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "private-run-id"
            root.mkdir()
            self.assertEqual(portable_artifact_root(root), "external-artifact-root/private-run-id")

    def _write_tree_manifest(self, root: Path) -> None:
        payload = b"verified fixture bytes\x00"
        (root / "payload.bin").write_bytes(payload)
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "files": [{
                "path": "payload.bin",
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }],
            "total_bytes": len(payload),
        }
        (root / "artifact-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def test_tree_manifest_verifies_content_and_rejects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_tree_manifest(root)
            report, rows = verify_tree(root)
            self.assertEqual(report["file_count"], 1)
            self.assertEqual(report["total_bytes"], len(b"verified fixture bytes\x00"))
            self.assertEqual(set(rows), {"payload.bin"})
            (root / "payload.bin").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "size/hash mismatch"):
                verify_tree(root)

    def test_tree_manifest_rejects_unlisted_files_and_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_tree_manifest(root)
            (root / "unexpected.txt").write_text("unexpected", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "path set differs"):
                verify_tree(root)
            (root / "unexpected.txt").unlink()
            try:
                (root / "linked.txt").symlink_to(root / "payload.bin")
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are unavailable on this filesystem")
            with self.assertRaisesRegex(ValueError, "symlink"):
                verify_tree(root)

    def test_ledger_chain_verifies_and_detects_payload_mutation(self) -> None:
        run_id = "audit-fixture"
        core = {
            "schema": LEDGER_SCHEMA,
            "run_id": run_id,
            "sequence": 1,
            "previous_event_sha256": GENESIS,
            "event_type": "run_started",
            "payload": {"schedule": []},
        }
        event_hash = hashlib.sha256(GENESIS.encode("ascii") + canonical_bytes(core)).hexdigest()
        line = json.dumps({**core, "event_sha256": event_hash}, ensure_ascii=False,
                          sort_keys=True, separators=(",", ":")) + "\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text(line, encoding="utf-8")
            report, records = verify_ledger(path, run_id)
            self.assertEqual(report["event_count"], 1)
            self.assertEqual(records["run_started"]["schedule"], [])
            path.write_text(line.replace('"schedule":[]', '"schedule":[1]'), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                verify_ledger(path, run_id)

    def test_trace_chain_verifies_and_detects_trace_mutation(self) -> None:
        trace = {
            "reset": None,
            "initial_position": None,
            "turns": [],
            "terminal": None,
            "terminal_observation": None,
        }
        payload_sha = hashlib.sha256(canonical_bytes(trace)).hexdigest()
        rows = trace_rows(trace)
        rows.append(("complete_trace_payload_sha256", {"sha256": payload_sha}))
        previous = GENESIS
        events = []
        for sequence, (kind, payload) in enumerate(rows, 1):
            core = {
                "sequence": sequence,
                "previous_event_sha256": previous,
                "event_type": kind,
                "payload": payload,
            }
            previous = hashlib.sha256(previous.encode("ascii") + canonical_bytes(core)).hexdigest()
            events.append({**core, "event_sha256": previous})
        trace["event_hash_chain"] = {
            "schema": "videochess-m6-trace-event-chain/1.0",
            "event_count": len(events),
            "payload_sha256": payload_sha,
            "head_sha256": previous,
            "events": events,
        }
        self.assertEqual(verify_trace_chain(trace)["head_sha256"], previous)
        trace["terminal"] = {"ale_terminated": True}
        with self.assertRaisesRegex(ValueError, "payload SHA-256"):
            verify_trace_chain(trace)

    def test_outcome_classification_requires_finite_reward_and_ale_flags(self) -> None:
        self.assertEqual(outcome_from_trace({"ale_terminated": True, "ale_truncated": False, "ale_reward_total": -1.0}), "loss")
        self.assertEqual(outcome_from_trace({"ale_terminated": True, "ale_truncated": False, "ale_reward_total": 0.0}), "terminal_unknown")
        for reward in (float("nan"), float("inf"), float("-inf"), 10**1000, "-1", True, None):
            with self.subTest(reward=reward):
                self.assertEqual(outcome_from_trace({"ale_terminated": True, "ale_truncated": False,
                                                     "ale_reward_total": reward}), "terminal_unknown")
        self.assertEqual(outcome_from_trace({"ale_terminated": False, "ale_truncated": True,
                                             "ale_reward_total": 0.0}), "ale_truncated")
        self.assertEqual(outcome_from_trace({"ale_terminated": False, "ale_truncated": False,
                                             "runner_stop_category": "RUNNER_MAX_ALE_FRAMES"}), "runner_truncated")
        self.assertEqual(outcome_from_trace({"ale_terminated": False, "ale_truncated": False,
                                             "runner_stop_category": "OPPONENT_RESPONSE_TIMEOUT"}), "incomplete")

    def test_frozen_schedule_reconstructs_predeclared_order(self) -> None:
        config = json.loads((Path(__file__).resolve().parents[1] / "configs/m6/m6-stage3-v2.json").read_text())
        schedule = expected_schedule(config)
        self.assertEqual(len(schedule), 20)
        self.assertEqual([row["slot"] for row in schedule], list(range(20)))
        self.assertEqual(hashlib.sha256(canonical_bytes(schedule)).hexdigest(),
                         "be4e6548e6fd3e3db4605e6b55fbe860848dccb2df87d8a7122145bdabe22ffc")

    def test_latency_summary_uses_ordered_raw_observations(self) -> None:
        self.assertEqual(latency_summary([]), {
            "count": 0, "median": None, "iqr": None, "p95": None, "max": None,
        })
        result = latency_summary([4.0, 1.0, 3.0, 2.0])
        self.assertEqual(result["count"], 4)
        self.assertEqual(result["median"], 2.5)
        self.assertEqual(result["iqr"], 1.5)
        self.assertEqual(result["max"], 4.0)

    def test_safe_relative_path_rejects_traversal_and_absolute_paths(self) -> None:
        self.assertEqual(safe_relative("attempts/game/trace.json"), "attempts/game/trace.json")
        for path in ("../outside", "/absolute/file", "attempts\\game", "C:/drive/file"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                safe_relative(path)


if __name__ == "__main__":
    unittest.main()
