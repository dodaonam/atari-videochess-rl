from __future__ import annotations

import subprocess
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from videochess_rl import source_snapshot
from videochess_rl.rl.cli import ROOT as REPOSITORY_ROOT, _require_unfinalized_artifact_root, source_hash
from videochess_rl.source_snapshot import capture_source_snapshot, verify_source_snapshot


class M5SourceSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "videochess_rl/rl").mkdir(parents=True)
        (self.root / "configs/rl").mkdir(parents=True)
        (self.root / "videochess_rl/__init__.py").write_text("\"\"\"fixture\"\"\"\n")
        (self.root / "videochess_rl/rl/cli.py").write_text("VALUE = 1\n")
        (self.root / "configs/rl/m5-double-dqn-v1.json").write_text('{"test": true}\n')
        (self.root / "pyproject.toml").write_text("[project]\nname='fixture'\n")
        (self.root / "uv.lock").write_text("version = 1\n")
        (self.root / ".python-version").write_text("3.12\n")
        (self.root / ".agents/state").mkdir(parents=True)
        (self.root / ".agents/tasks").mkdir(parents=True)
        (self.root / ".agents/state/PROJECT_STATE.yaml").write_text('{"phase": "fixture"}\n')
        (self.root / ".agents/tasks/BACKLOG.yaml").write_text('{"task": "fixture"}\n')
        (self.root / "artifacts/m5/feasibility").mkdir(parents=True)
        (self.root / "artifacts/m5/feasibility/profile.json").write_text('{"fits": true}\n')
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "M5 snapshot test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "m5-snapshot-test@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture baseline"], cwd=self.root, check=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_capture_is_recoverable_content_addressed_and_includes_lock_and_config(self) -> None:
        destination = self.root / "artifacts/m5/source-snapshots"
        runtime_inputs = [".agents/state/PROJECT_STATE.yaml", ".agents/tasks/BACKLOG.yaml",
                          "artifacts/m5/feasibility/profile.json"]
        first = capture_source_snapshot(self.root, destination, additional_files=runtime_inputs)
        second = capture_source_snapshot(self.root, destination, additional_files=runtime_inputs)
        self.assertEqual(first["archive_sha256"], second["archive_sha256"])
        self.assertEqual(first["path"], second["path"])
        self.assertFalse(first["source_dirty"])
        self.assertEqual(first["source_sha256"], second["source_sha256"])

        path = self.root / first["path"]
        verified = verify_source_snapshot(path, expected_archive_sha256=first["archive_sha256"])
        self.assertEqual(verified["source_sha256"], first["source_sha256"])
        with zipfile.ZipFile(path) as archive:
            self.assertIn("source/configs/rl/m5-double-dqn-v1.json", archive.namelist())
            self.assertIn("source/uv.lock", archive.namelist())
            self.assertIn("source/.agents/state/PROJECT_STATE.yaml", archive.namelist())
            self.assertIn("source/artifacts/m5/feasibility/profile.json", archive.namelist())
            self.assertEqual(archive.read("source/videochess_rl/rl/cli.py"), b"VALUE = 1\n")
        self.assertEqual(verified["additional_runtime_inputs"], runtime_inputs)

    def test_snapshot_aggregate_uses_the_same_algorithm_as_training_run_identity(self) -> None:
        files = source_snapshot._read_source(REPOSITORY_ROOT, ())
        self.assertEqual(source_snapshot._package_source_sha256(files), source_hash())

    def test_training_refuses_to_mutate_a_finalized_artifact_root(self) -> None:
        empty = self.root / "empty-artifacts"
        _require_unfinalized_artifact_root(empty)
        empty.mkdir()
        (empty / "artifact-manifest.json").write_text('{"status": "complete"}\n')
        with self.assertRaisesRegex(RuntimeError, "immutable M5 artifact root"):
            _require_unfinalized_artifact_root(empty)

    def test_dirty_runtime_source_is_captured_and_recorded(self) -> None:
        source = self.root / "videochess_rl/rl/cli.py"
        source.write_text("VALUE = 2\n")
        snapshot = capture_source_snapshot(self.root, self.root / "artifacts/m5/source-snapshots")
        self.assertTrue(snapshot["source_dirty"])
        self.assertTrue(snapshot["source_status_entries"])
        self.assertEqual(verify_source_snapshot(self.root / snapshot["path"])["source_sha256"],
                         snapshot["source_sha256"])

    def test_tampered_file_bytes_are_rejected_even_without_expected_archive_hash(self) -> None:
        snapshot = capture_source_snapshot(self.root, self.root / "artifacts/m5/source-snapshots")
        original_path = self.root / snapshot["path"]
        tampered_path = self.root / "tampered.zip"
        with zipfile.ZipFile(original_path) as source, zipfile.ZipFile(tampered_path, "w") as target:
            for name in source.namelist():
                data = source.read(name)
                if name == "source/videochess_rl/rl/cli.py":
                    data = b"VALUE = 999\n"
                target.writestr(name, data)
        with self.assertRaisesRegex(ValueError, "file hash mismatch"):
            verify_source_snapshot(tampered_path)

    def test_symlinked_python_source_is_rejected(self) -> None:
        (self.root / "videochess_rl/rl/linked.py").symlink_to(self.root / "videochess_rl/rl/cli.py")
        with self.assertRaisesRegex(ValueError, "symlink|unsafe"):
            capture_source_snapshot(self.root, self.root / "artifacts/m5/source-snapshots")

    def test_source_change_during_capture_is_rejected_before_publication(self) -> None:
        original_read = source_snapshot._read_source
        calls = 0

        def change_between_reads(root: Path, additional_files: tuple[str, ...]) -> dict[str, bytes]:
            nonlocal calls
            calls += 1
            if calls == 2:
                (root / "videochess_rl/rl/cli.py").write_text("VALUE = 3\n")
            return original_read(root, additional_files)

        destination = self.root / "artifacts/m5/source-snapshots"
        with patch.object(source_snapshot, "_read_source", side_effect=change_between_reads):
            with self.assertRaisesRegex(RuntimeError, "changed while"):
                capture_source_snapshot(self.root, destination)
        self.assertFalse(destination.exists())

    def test_missing_runtime_input_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing or unsafe"):
            capture_source_snapshot(self.root, self.root / "artifacts/m5/source-snapshots",
                                    additional_files=[".agents/state/missing.json"])


if __name__ == "__main__":
    unittest.main()
