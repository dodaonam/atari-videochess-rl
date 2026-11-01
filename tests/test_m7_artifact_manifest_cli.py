from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from scripts.verify_m7_artifact_manifest import main
from videochess_rl.m6.ledger import build_artifact_manifest


class M7ArtifactManifestCliTests(unittest.TestCase):
    def make_manifest(self, root: Path) -> Path:
        (root / "nested").mkdir()
        (root / "first.txt").write_text("frozen", encoding="utf-8")
        (root / "nested" / "second.bin").write_bytes(b"\x00\x01manifest-test")
        manifest = build_artifact_manifest(root)
        path = root / "artifact-manifest.json"
        path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def invoke(self, *arguments: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = main(list(arguments))
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_valid_manifest_and_expected_hash_are_reported_without_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "private-run"
            root.mkdir()
            manifest_path = self.make_manifest(root)
            expected = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            code, output, error = self.invoke(
                "--root", str(root), "--expected-manifest-sha256", expected
            )
            result = json.loads(output)
            self.assertEqual(code, 0, error)
            self.assertEqual(result["status"], "verified")
            self.assertEqual(result["root_label"], "private-run")
            self.assertEqual(result["manifest_sha256"], expected)
            self.assertTrue(result["read_only"])
            self.assertNotIn(temp_dir, output)

    def test_mismatched_manifest_hash_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "private-run"
            root.mkdir()
            self.make_manifest(root)
            code, _, error = self.invoke(
                "--root", str(root), "--expected-manifest-sha256", "0" * 64
            )
            self.assertEqual(code, 1)
            self.assertIn("differs from the expected identity", error)

    def test_modified_payload_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "private-run"
            root.mkdir()
            self.make_manifest(root)
            (root / "first.txt").write_text("changed", encoding="utf-8")
            code, _, error = self.invoke("--root", str(root))
            self.assertEqual(code, 1)
            self.assertIn("does not match its manifest", error)

    def test_unlisted_payload_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "private-run"
            root.mkdir()
            self.make_manifest(root)
            (root / "unlisted.txt").write_text("extra", encoding="utf-8")
            code, _, error = self.invoke("--root", str(root))
            self.assertEqual(code, 1)
            self.assertIn("does not match its manifest", error)

    def test_unsafe_manifest_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "private-run"
            root.mkdir()
            self.make_manifest(root)
            manifest_path = root / "artifact-manifest.json"
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
            document["files"][0]["path"] = "../outside.txt"
            manifest_path.write_text(json.dumps(document), encoding="utf-8")
            code, _, error = self.invoke("--root", str(root))
            self.assertEqual(code, 1)
            self.assertIn("does not match its manifest", error)

    def test_symlinked_root_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir)
            root = parent / "private-run"
            root.mkdir()
            self.make_manifest(root)
            link = parent / "run-link"
            try:
                link.symlink_to(root, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlinks unavailable")
            code, _, error = self.invoke("--root", str(link))
            self.assertEqual(code, 1)
            self.assertIn("must not be a symbolic link", error)


if __name__ == "__main__":
    unittest.main()
