"""Lossless checkpoint-history archive and migration tests on disposable repos."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))

import agent_checkpoint
import agent_preflight
import checkpoint_history as archive
import test_agent_context as context_fixture


def _read_state(root: Path) -> dict[str, object]:
    return json.loads((root / ".agents/state/PROJECT_STATE.yaml").read_text(encoding="utf-8"))


def _write_state(root: Path, state: dict[str, object]) -> bytes:
    raw = (json.dumps(state, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    (root / ".agents/state/PROJECT_STATE.yaml").write_bytes(raw)
    return raw


def _fixture(root: Path, history_count: int = 3) -> tuple[dict[str, object], bytes]:
    context_fixture.make_fixture(root)
    for name in ("agent_preflight.py", "agent_checkpoint.py", "checkpoint_history.py"):
        destination = root / "scripts" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / "scripts" / name, destination)
    context_fixture.commit_all(root, "fixture baseline")
    code, detail = agent_checkpoint.checkpoint(root, False, False)
    if code:
        raise AssertionError(detail)
    state = _read_state(root)
    seed = state["checkpoint_history"][0]
    rows: list[dict[str, object]] = []
    for index in range(history_count):
        row = copy.deepcopy(seed)
        row["id"] = f"cp-synthetic-{index + 1:06d}"
        row["created_at_utc"] = f"2026-10-20T00:00:{index:02d}Z"
        row["fixture_extension"] = {"ordinal": index, "note": "preserve unknown logical fields"}
        rows.append(row)
    state["checkpoint_history"] = rows
    portable = state["last_checkpoint"].get("portable_git")
    if isinstance(portable, dict):
        portable["state_sha256"] = agent_preflight._portable_state_sha256(state)
    raw = _write_state(root, state)
    return state, raw


def _preflight(root: Path) -> dict[str, object]:
    return agent_preflight.build_report(root)


def _archive_files(root: Path) -> set[str]:
    directory = root / archive.ARCHIVE_REL
    return {path.relative_to(root).as_posix() for path in directory.rglob("*") if path.is_file()}


class CheckpointHistoryArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def migrate(self, count: int = 3) -> tuple[list[dict[str, object]], bytes]:
        state, before = _fixture(self.root, count)
        expected = copy.deepcopy(archive._legacy_logical_history(state))
        result = archive.migrate_legacy_history(self.root)
        self.assertEqual(result["status"], "migrated")
        migrated = _read_state(self.root)
        inspection = archive.inspect_history_storage(self.root, migrated)
        self.assertEqual(inspection.errors, [])
        self.assertEqual(inspection.records, expected)
        return expected, before

    def test_migration_preserves_every_record_and_original_state_byte_exactly(self) -> None:
        expected, original = self.migrate(139)
        state_path = self.root / ".agents/state/PROJECT_STATE.yaml"
        state = _read_state(self.root)
        self.assertEqual(state["checkpoint_history"], [])
        self.assertEqual(state[archive.POINTER_KEY]["record_count"], 140)
        self.assertNotEqual(state["last_checkpoint"]["id"], "cp-fixture-0001")
        self.assertLess(state_path.stat().st_size, 100_000)
        self.assertLess(state_path.stat().st_size, len(original) // 20)
        self.assertEqual(archive.inspect_history_storage(self.root, state).records, expected)
        restored = archive.restore_original_state_bytes(self.root, state)
        self.assertEqual(restored, original)
        self.assertEqual(hashlib.sha256(restored).hexdigest(), state[archive.POINTER_KEY]["source_state_sha256"])
        self.assertEqual(_preflight(self.root)["errors"], [])

    def test_migration_is_idempotent_and_does_not_duplicate_history(self) -> None:
        expected, _ = self.migrate(17)
        before_state = (self.root / ".agents/state/PROJECT_STATE.yaml").read_bytes()
        before_files = _archive_files(self.root)
        second = archive.migrate_legacy_history(self.root)
        self.assertEqual(second["status"], "already_migrated")
        self.assertEqual((self.root / ".agents/state/PROJECT_STATE.yaml").read_bytes(), before_state)
        self.assertEqual(_archive_files(self.root), before_files)
        self.assertEqual(len(archive.inspect_history_storage(self.root, _read_state(self.root)).records), len(expected))

    def test_preview_does_not_mutate_loaded_state(self) -> None:
        state, raw = _fixture(self.root, 3)
        before = copy.deepcopy(state)
        preview = archive.migration_preview(raw, state)
        self.assertEqual(preview["history_count"], 4)
        self.assertEqual(state, before)

    def test_portable_state_checksum_matches_preflight_for_unicode(self) -> None:
        state, _ = _fixture(self.root, 2)
        state["fixture_text"] = "chess – café"
        self.assertEqual(archive._portable_state_sha256(state), agent_preflight._portable_state_sha256(state))

    def test_retry_finalizes_migration_after_interrupted_post_switch_checkpoint(self) -> None:
        _, _ = _fixture(self.root, 3)
        with patch.object(agent_checkpoint, "checkpoint", return_value=(1, "injected finalization failure")):
            with self.assertRaisesRegex(archive.CheckpointHistoryError, "finalization failed"):
                archive.migrate_legacy_history(self.root)
        state = _read_state(self.root)
        self.assertIn(archive.POINTER_KEY, state)
        self.assertEqual(archive.inspect_history_storage(self.root, state).errors, [])
        result = archive.migrate_legacy_history(self.root)
        self.assertEqual(result["status"], "finalized_existing_migration")
        self.assertEqual(_preflight(self.root)["errors"], [])

    def test_partial_archive_write_after_replace_is_detected_and_resumable(self) -> None:
        _, before = _fixture(self.root, 18)
        original_write = archive.atomic_write_bytes
        injected = False

        def write_then_fail_segment(path: Path, content: bytes) -> None:
            nonlocal injected
            original_write(path, content)
            if path.name == "segment-000002.jsonl.gz" and not injected:
                injected = True
                raise OSError("injected post-replace archive write failure")

        with patch.object(archive, "atomic_write_bytes", side_effect=write_then_fail_segment):
            with self.assertRaisesRegex(OSError, "post-replace"):
                archive.migrate_legacy_history(self.root)
        report = _preflight(self.root)
        self.assertIn("CHECKPOINT_HISTORY_UNREFERENCED", {item["code"] for item in report["errors"]})
        result = archive.migrate_legacy_history(self.root)
        self.assertEqual(result["status"], "migrated")
        state = _read_state(self.root)
        self.assertEqual(archive.inspect_history_storage(self.root, state).records, archive._legacy_logical_history(json.loads(before)))
        self.assertEqual(_preflight(self.root)["errors"], [])

    def test_stale_handoff_after_migration_is_detected_and_checkpoint_repairs_it(self) -> None:
        self.migrate(2)
        handoff_path = self.root / ".agents/state/SESSION_HANDOFF.md"
        handoff_path.write_text("<!-- checkpoint-id: stale-id -->\n# Handoff\n", encoding="utf-8")
        before = _preflight(self.root)
        self.assertIn("HANDOFF_STALE", {item["code"] for item in before["warnings"]})
        code, message = agent_checkpoint.checkpoint(self.root, False, False)
        self.assertEqual(code, 0, message)
        after = _preflight(self.root)
        self.assertNotIn("HANDOFF_STALE", {item["code"] for item in after["warnings"]})
        self.assertEqual(after["errors"], [])

    def test_clean_clone_recovers_migrated_archive_without_local_workspace_state(self) -> None:
        self.migrate(4)
        context_fixture.commit_all(self.root, "commit migrated archive fixture")
        clone = Path(self.temp.name) / "clean-clone"
        subprocess.run(["git", "clone", "--quiet", str(self.root), str(clone)], check=True, capture_output=True, text=True)
        result = subprocess.run(
            [sys.executable, str(clone / "scripts/agent_preflight.py"), "--repo", str(clone), "--json"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["summary"]["checkpoint_history_storage"], "archive")
        self.assertEqual(report["summary"]["checkpoint_history_count"], 5)

    def test_empty_and_single_inline_histories_preserve_current_checkpoint(self) -> None:
        for count, expected_count, expected_segments in ((0, 1, 1), (1, 2, 1)):
            with self.subTest(count=count):
                self.root = Path(self.temp.name) / f"repo-{count}"
                _, _ = self.migrate(count)
                state = _read_state(self.root)
                inspection = archive.inspect_history_storage(self.root, state)
                manifest = inspection.manifest
                self.assertIsNotNone(manifest)
                self.assertEqual(len(manifest["segments"]), expected_segments)
                self.assertEqual(len(inspection.records), expected_count)

    def test_segment_boundary_splits_at_sixteen_records(self) -> None:
        for count, expected_counts in ((15, [16]), (16, [16, 1])):
            with self.subTest(count=count):
                self.root = Path(self.temp.name) / f"segments-{count}"
                rows, _ = self.migrate(count)
                state = _read_state(self.root)
                manifest = archive.inspect_history_storage(self.root, state).manifest
                self.assertEqual([item["record_count"] for item in manifest["segments"]], expected_counts)
                self.assertEqual(archive.inspect_history_storage(self.root, state).records, rows)

    def test_malformed_legacy_history_is_rejected_without_mutation(self) -> None:
        context_fixture.make_fixture(self.root)
        state = _read_state(self.root)
        state["checkpoint_history"] = [{"id": "bad", "created_at_utc": "2026-10-20T00:00:00Z"}]
        before = _write_state(self.root, state)
        with self.assertRaises(archive.CheckpointHistoryError):
            archive.migrate_legacy_history(self.root)
        self.assertEqual((self.root / ".agents/state/PROJECT_STATE.yaml").read_bytes(), before)
        self.assertFalse((self.root / archive.ARCHIVE_REL).exists())

    def test_duplicate_legacy_ids_are_rejected_without_mutation(self) -> None:
        state, _ = _fixture(self.root, 2)
        state["checkpoint_history"][1]["id"] = state["checkpoint_history"][0]["id"]
        before = _write_state(self.root, state)
        with self.assertRaisesRegex(archive.CheckpointHistoryError, "duplicate checkpoint"):
            archive.migrate_legacy_history(self.root)
        self.assertEqual((self.root / ".agents/state/PROJECT_STATE.yaml").read_bytes(), before)

    def test_failure_writing_archive_leaves_legacy_state_unchanged(self) -> None:
        _, before = _fixture(self.root, 17)
        original_write = archive.atomic_write_bytes
        calls = 0

        def fail_one_segment(path: Path, content: bytes) -> None:
            nonlocal calls
            calls += 1
            if path.name == "segment-000002.jsonl.gz":
                raise OSError("injected archive segment write failure")
            original_write(path, content)

        with patch.object(archive, "atomic_write_bytes", side_effect=fail_one_segment):
            with self.assertRaisesRegex(OSError, "injected"):
                archive.migrate_legacy_history(self.root)
        self.assertEqual((self.root / ".agents/state/PROJECT_STATE.yaml").read_bytes(), before)
        self.assertEqual(_archive_files(self.root), set())

    def test_failure_writing_canonical_state_rolls_back_new_archive_files(self) -> None:
        _, before = _fixture(self.root, 17)
        original_write = archive.atomic_write_bytes

        def fail_state(path: Path, content: bytes) -> None:
            if path.name == "PROJECT_STATE.yaml":
                raise OSError("injected canonical state write failure")
            original_write(path, content)

        with patch.object(archive, "atomic_write_bytes", side_effect=fail_state):
            with self.assertRaisesRegex(OSError, "injected"):
                archive.migrate_legacy_history(self.root)
        self.assertEqual((self.root / ".agents/state/PROJECT_STATE.yaml").read_bytes(), before)
        self.assertEqual(_archive_files(self.root), set())

    def test_interrupted_migration_is_detected_and_can_resume_idempotently(self) -> None:
        state, before = _fixture(self.root, 17)
        writes, _, _ = archive._migration_payload(before, state)
        for rel, content in writes.items():
            archive.atomic_write_bytes(self.root / rel, content)
        report = _preflight(self.root)
        self.assertIn("CHECKPOINT_HISTORY_UNREFERENCED", {item["code"] for item in report["errors"]})
        result = archive.migrate_legacy_history(self.root)
        self.assertEqual(result["status"], "migrated")
        self.assertEqual(_preflight(self.root)["errors"], [])

    def test_missing_or_corrupted_archive_is_rejected_but_source_state_can_be_restored(self) -> None:
        rows, original = self.migrate(17)
        state = _read_state(self.root)
        first_segment = state[archive.POINTER_KEY]["manifest_path"]
        manifest = json.loads((self.root / first_segment).read_text())
        target = self.root / archive.ARCHIVE_REL / manifest["segments"][0]["path"]
        target.unlink()
        report = _preflight(self.root)
        self.assertIn("CHECKPOINT_HISTORY_CORRUPT", {item["code"] for item in report["errors"]})
        restored = archive.restore_original_state_bytes(self.root, state)
        self.assertEqual(restored, original)
        self.assertEqual(len(rows), 18)

    def test_segment_byte_tampering_and_manifest_hash_tampering_are_detected(self) -> None:
        self.migrate(2)
        state_path = self.root / ".agents/state/PROJECT_STATE.yaml"
        state = _read_state(self.root)
        manifest_path = self.root / archive.MANIFEST_REL
        manifest = json.loads(manifest_path.read_text())
        segment_path = self.root / archive.ARCHIVE_REL / manifest["segments"][0]["path"]
        original_segment = segment_path.read_bytes()
        segment_path.write_bytes(original_segment + b"x")
        report = _preflight(self.root)
        self.assertIn("CHECKPOINT_HISTORY_CORRUPT", {item["code"] for item in report["errors"]})
        segment_path.write_bytes(original_segment)
        # Corrupt only the canonical pointer after restoring the exact segment.
        state_before = json.loads(state_path.read_text())
        state_before[archive.POINTER_KEY]["manifest_sha256"] = "0" * 64
        _write_state(self.root, state_before)
        report = _preflight(self.root)
        self.assertTrue({item["code"] for item in report["errors"]} & {"CHECKPOINT_HISTORY_POINTER_MISMATCH", "CHECKPOINT_HISTORY_CORRUPT"})

    def test_invalid_gzip_stream_is_reported_as_archive_corruption(self) -> None:
        self.migrate(2)
        state = _read_state(self.root)
        manifest_path = self.root / archive.MANIFEST_REL
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        segment_entry = manifest["segments"][0]
        segment_path = self.root / archive.ARCHIVE_REL / segment_entry["path"]
        invalid_gzip = b"\x1f\x8b\x08\x00invalid-deflate-stream"
        segment_path.write_bytes(invalid_gzip)
        segment_entry["sha256"] = hashlib.sha256(invalid_gzip).hexdigest()
        manifest_bytes = archive._render_json(manifest)
        manifest_path.write_bytes(manifest_bytes)
        state[archive.POINTER_KEY]["manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
        _write_state(self.root, state)

        inspection = archive.inspect_history_storage(self.root, _read_state(self.root))

        self.assertIn("CHECKPOINT_HISTORY_CORRUPT", {code for code, _ in inspection.errors})

    def test_manifest_rejects_boolean_schema_versions_and_counts(self) -> None:
        self.migrate(2)
        manifest = json.loads((self.root / archive.MANIFEST_REL).read_text(encoding="utf-8"))
        for field in ("schema_version", "record_count", "source_history_count", "segment_record_limit"):
            with self.subTest(field=field):
                forged = copy.deepcopy(manifest)
                forged[field] = True
                with self.assertRaises(archive.CheckpointHistoryError):
                    archive._parse_manifest_bytes(archive.canonical_bytes(forged))

    def test_append_after_migration_is_lossless_and_unchanged_repeat_is_noop(self) -> None:
        expected, _ = self.migrate(3)
        migration_checkpoint_record = archive._record_from_checkpoint(_read_state(self.root)["last_checkpoint"])
        context_fixture.commit_all(self.root, "after migration change")
        before_size = (self.root / ".agents/state/PROJECT_STATE.yaml").stat().st_size
        code, message = agent_checkpoint.checkpoint(self.root, False, False)
        self.assertEqual(code, 0, message)
        state = _read_state(self.root)
        full = archive.inspect_history_storage(self.root, state).records
        self.assertEqual(full, [*expected, migration_checkpoint_record])
        self.assertLess((self.root / ".agents/state/PROJECT_STATE.yaml").stat().st_size, before_size + 10_000)
        after_first = (self.root / ".agents/state/PROJECT_STATE.yaml").read_bytes()
        code, message = agent_checkpoint.checkpoint(self.root, False, False)
        self.assertEqual(code, 0, message)
        self.assertIn("no new history entry", message)
        self.assertEqual((self.root / ".agents/state/PROJECT_STATE.yaml").read_bytes(), after_first)
        self.assertEqual(_preflight(self.root)["errors"], [])

    def test_unchanged_checkpoint_refuses_noop_when_archive_integrity_fails(self) -> None:
        self.migrate(2)
        state_before = (self.root / ".agents/state/PROJECT_STATE.yaml").read_bytes()
        manifest = json.loads((self.root / archive.MANIFEST_REL).read_text(encoding="utf-8"))
        segment = self.root / archive.ARCHIVE_REL / manifest["segments"][0]["path"]
        segment.write_bytes(segment.read_bytes() + b"corrupt")
        corrupted_segment = segment.read_bytes()

        with patch.object(agent_checkpoint, "build_report", return_value={"ok": True, "errors": [], "warnings": []}):
            code, message = agent_checkpoint.checkpoint(self.root, False, False)

        self.assertEqual(code, 1)
        self.assertIn("refusing no-op", message)
        self.assertEqual((self.root / ".agents/state/PROJECT_STATE.yaml").read_bytes(), state_before)
        self.assertEqual(segment.read_bytes(), corrupted_segment)

    def test_duplicate_append_does_not_insert_same_record_twice(self) -> None:
        rows, _ = self.migrate(2)
        state = _read_state(self.root)
        current = rows[-1]
        plan = archive.prepare_archive_append(self.root, state, current)
        self.assertFalse(plan.appended)
        self.assertEqual(len(archive.inspect_history_storage(self.root, state).records), len(rows))
        different = copy.deepcopy(current)
        different["created_at_utc"] = "2026-10-23T00:00:00Z"
        with self.assertRaisesRegex(archive.CheckpointHistoryError, "different data"):
            archive.prepare_archive_append(self.root, state, different)

    def test_pending_manifest_append_rolls_forward_only_when_checkpoint_matches(self) -> None:
        rows, _ = self.migrate(4)
        state = _read_state(self.root)
        record = archive._record_from_checkpoint(state["last_checkpoint"])
        plan = archive.prepare_archive_append(self.root, state, record)
        archive.apply_archive_append(self.root, plan)
        report = _preflight(self.root)
        self.assertIn("CHECKPOINT_HISTORY_PENDING_APPEND", {item["code"] for item in report["errors"]})
        result = archive.recover_pending_append(self.root)
        self.assertEqual(result["status"], "recovered")
        after = _read_state(self.root)
        full = archive.inspect_history_storage(self.root, after).records
        self.assertEqual(full[:-1], rows)
        self.assertEqual(full[-1], record)
        self.assertEqual(_preflight(self.root)["errors"], [])

    def test_pending_orphan_segment_recovers_from_current_checkpoint(self) -> None:
        rows, _ = self.migrate(4)
        state = _read_state(self.root)
        record = archive._record_from_checkpoint(state["last_checkpoint"])
        plan = archive.prepare_archive_append(self.root, state, record)
        segment_path, segment_bytes = next((rel, data) for rel, data in plan.writes.items() if rel != archive.MANIFEST_REL)
        archive.atomic_write_bytes(self.root / segment_path, segment_bytes)
        report = _preflight(self.root)
        self.assertIn("CHECKPOINT_HISTORY_PENDING_APPEND", {item["code"] for item in report["errors"]})
        archive.recover_pending_append(self.root)
        after = _read_state(self.root)
        self.assertEqual(archive.inspect_history_storage(self.root, after).records, [*rows, record])
        self.assertEqual(_preflight(self.root)["errors"], [])

    def test_checkpoint_archive_failure_restores_all_canonical_and_archive_files(self) -> None:
        self.migrate(3)
        context_fixture.commit_all(self.root, "trigger archive append")
        state_path = self.root / ".agents/state/PROJECT_STATE.yaml"
        handoff_path = self.root / ".agents/state/SESSION_HANDOFF.md"
        manifest_path = self.root / archive.MANIFEST_REL
        before_state = state_path.read_bytes()
        before_handoff = handoff_path.read_bytes()
        before_manifest = manifest_path.read_bytes()
        before_files = _archive_files(self.root)
        original_write = archive.atomic_write_bytes
        failed = False

        def fail_first_manifest(path: Path, content: bytes) -> None:
            nonlocal failed
            if path == manifest_path and not failed:
                failed = True
                raise OSError("injected append manifest failure")
            original_write(path, content)

        with patch.object(archive, "atomic_write_bytes", side_effect=fail_first_manifest):
            code, message = agent_checkpoint.checkpoint(self.root, False, False)
        self.assertEqual(code, 1)
        self.assertIn("injected append manifest failure", message)
        self.assertTrue(failed)
        self.assertEqual(state_path.read_bytes(), before_state)
        self.assertEqual(handoff_path.read_bytes(), before_handoff)
        self.assertEqual(manifest_path.read_bytes(), before_manifest)
        self.assertEqual(_archive_files(self.root), before_files)
        self.assertEqual(_preflight(self.root)["errors"], [])

    def test_checkpoint_state_write_failure_rolls_back_archive_append(self) -> None:
        self.migrate(3)
        context_fixture.commit_all(self.root, "trigger state failure")
        state_path = self.root / ".agents/state/PROJECT_STATE.yaml"
        handoff_path = self.root / ".agents/state/SESSION_HANDOFF.md"
        before_state = state_path.read_bytes()
        before_handoff = handoff_path.read_bytes()
        before_files = _archive_files(self.root)
        original_write = agent_checkpoint._atomic_write
        failed = False

        def fail_state(path: Path, content: str) -> None:
            nonlocal failed
            if path == state_path and not failed:
                failed = True
                raise OSError("injected canonical state failure")
            original_write(path, content)

        with patch.object(agent_checkpoint, "_atomic_write", side_effect=fail_state):
            code, message = agent_checkpoint.checkpoint(self.root, False, False)
        self.assertEqual(code, 1)
        self.assertIn("injected canonical state failure", message)
        self.assertEqual(state_path.read_bytes(), before_state)
        self.assertEqual(handoff_path.read_bytes(), before_handoff)
        self.assertEqual(_archive_files(self.root), before_files)
        self.assertEqual(_preflight(self.root)["errors"], [])

    def test_unreferenced_archive_backup_is_detected(self) -> None:
        state, before = _fixture(self.root, 1)
        writes, _, _ = archive._migration_payload(before, state)
        for rel, content in writes.items():
            archive.atomic_write_bytes(self.root / rel, content)
        report = _preflight(self.root)
        self.assertIn("CHECKPOINT_HISTORY_UNREFERENCED", {item["code"] for item in report["errors"]})

    def test_unreferenced_file_in_valid_archive_is_detected(self) -> None:
        self.migrate(1)
        extra = self.root / archive.ARCHIVE_REL / "notes.txt"
        extra.write_text("not part of the verified manifest\n", encoding="utf-8")
        report = _preflight(self.root)
        self.assertIn("CHECKPOINT_HISTORY_UNREFERENCED", {item["code"] for item in report["errors"]})


if __name__ == "__main__":
    unittest.main()
