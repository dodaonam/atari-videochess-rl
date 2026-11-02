from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from videochess_rl.m7.policies import FrozenPolicyError, _manifest_entries
from videochess_rl.m7.protocol import build_config, frozen_policy_roster, validate_config


class M7PolicyIdentityTests(unittest.TestCase):
    def test_nine_policy_ids_and_six_checkpoint_hashes_are_unique(self) -> None:
        roster = frozen_policy_roster()
        self.assertEqual(len(roster), 9)
        self.assertEqual(len({row["policy_id"] for row in roster}), 9)
        learned = [row for row in roster if row["policy_type"] == "frozen_m5_double_dqn_q_policy"]
        self.assertEqual(len(learned), 6)
        self.assertEqual(len({row["checkpoint_file_sha256"] for row in learned}), 6)
        self.assertEqual(len({row["sidecar_manifest_file_sha256"] for row in learned}), 6)
        for row in learned:
            self.assertEqual(row["snapshot_stage"], "post_rl")
            self.assertEqual(row["valid_training_decisions"], 50000)
            self.assertTrue(row["artifact_relative_path"].startswith("runs/"))
            self.assertFalse(row["artifact_relative_path"].startswith("/"))

    def test_m4_metadata_hash_is_distinct_from_sidecar_file_hash(self) -> None:
        m4 = next(row for row in frozen_policy_roster() if row["policy_type"] == "frozen_m4_supervised_behavior_policy")
        self.assertNotEqual(m4["sidecar_metadata_sha256"], m4["sidecar_manifest_file_sha256"])
        self.assertEqual(m4["sidecar_metadata_sha256"], "63615d8d0ed27900fdf86d3f3084ca95cd562f9ec2f9a7e94bca4b0f6301e0c8")

    def test_manifest_inventory_rejects_hash_path_and_symlink_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "payload.bin"
            payload.write_bytes(b"accepted")
            record = {"path": "payload.bin", "sha256": hashlib.sha256(b"accepted").hexdigest()}
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"files": [record]}), encoding="utf-8")
            expected = hashlib.sha256(manifest.read_bytes()).hexdigest()
            self.assertEqual(_manifest_entries(root, "manifest.json", expected)["payload.bin"], record)
            with self.assertRaises(FrozenPolicyError):
                _manifest_entries(root, "manifest.json", "0" * 64)
            unsafe = {"files": [{"path": "../outside", "sha256": "0" * 64}]}
            manifest.write_text(json.dumps(unsafe), encoding="utf-8")
            with self.assertRaises(FrozenPolicyError):
                _manifest_entries(root, "manifest.json", hashlib.sha256(manifest.read_bytes()).hexdigest())

    def test_config_roster_paths_are_root_relative_and_not_private_absolute_paths(self) -> None:
        config = build_config()
        validate_config(config)
        for row in config["accepted_inputs"]["m5"]["policies"]:
            self.assertTrue(row["artifact_relative_path"].startswith("runs/"))
            self.assertNotIn("/home/", row["artifact_relative_path"])
            self.assertNotIn("..", Path(row["artifact_relative_path"]).parts)


if __name__ == "__main__":
    unittest.main()
