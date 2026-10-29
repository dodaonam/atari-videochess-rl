from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/m5_artifact_manifests.py"
spec = importlib.util.spec_from_file_location("m5_artifact_manifests", SCRIPT)
assert spec and spec.loader
manifests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manifests)


class M5ArtifactManifestTests(unittest.TestCase):
    def test_manifest_verification_detects_mutated_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "weights.bin").write_bytes(b"model")
            document = {"schema": "test", "files": manifests.file_inventory(root)}
            (root / "manifest.json").write_text(json.dumps(document))
            self.assertEqual(manifests.verify_manifest(root, root / "manifest.json"), document)
            (root / "weights.bin").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "inventory mismatch"):
                manifests.verify_manifest(root, root / "manifest.json")

    def test_partial_inventory_is_explicit_and_verifiable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "runs" / "attempt-0000"
            run.mkdir(parents=True)
            (run / "attempt-record.json").write_text('{"status":"incomplete"}')
            (run / "replay.journal.jsonl").write_text('{"record":1}\n')
            with self.assertRaisesRegex(RuntimeError, "require six completed runs"):
                manifests.create_manifests(root)
            result = manifests.create_manifests(root, allow_incomplete=True)
            self.assertEqual(result["status"], "partial")
            manifests.verify_manifest(root, root / "artifact-manifest.json")
            manifests.verify_manifest(root, run / "run-manifest.json")

    def test_incomplete_files_cannot_be_called_a_complete_campaign(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "training-campaign.json").write_text(json.dumps({
                "status": "complete", "planned_runs": 6, "completed_runs": 6,
                "total_valid_decisions": 300000, "runs": []
            }))
            evaluation = root / "evaluation"
            evaluation.mkdir()
            (evaluation / "evaluation-report.json").write_text(json.dumps({
                "schedule_complete": True, "executed_games": 1500, "planned_games": 1500,
                "policies_with_recorded_schedule": 15, "per_policy": []
            }))
            result = manifests.create_manifests(root, allow_incomplete=True)
            self.assertEqual(result["status"], "partial")


if __name__ == "__main__":
    unittest.main()
