"""Offline compatibility smoke test for one frozen, private M5 policy.

This test exercises the existing M2-observation policy boundary only. It does
not construct ALE, perform gameplay, or claim Atari integration success.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import random
import unittest

from videochess_rl.baselines import SimpleHeuristicAgent
from videochess_rl.rl.checkpoint import load_evaluation_snapshot
from videochess_rl.rl.evaluate import QPolicy
from videochess_rl.simulator import ChessSimulator


CHECKPOINT_SHA256 = "0b2405017a8e1d539851f0cd278883d3fd23936fb5c2f7962c813590a6fd1767"


class FrozenM5PolicyCompatibilityTests(unittest.TestCase):
    def _check_snapshot(self, path: Path, expected_sha256: str) -> None:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(digest, expected_sha256)

        model, metadata = load_evaluation_snapshot(path, device="cpu")
        self.assertEqual(metadata["schema"], "videochess-ddqn-evaluation-snapshot/2.0")
        self.assertIs(metadata["resumable"], False)
        self.assertEqual(metadata["stage"], "post_rl")
        self.assertIn(metadata["arm"], {"warm", "scratch"})
        self.assertIn(metadata["training_seed"], {20261104, 20261105, 20261106})
        self.assertEqual(metadata["valid_decisions"], 50_000)

        policy = QPolicy(model, policy_id=f"pre-m6-{metadata['arm']}-{metadata['training_seed']}", checkpoint_sha256=digest)
        before = {name: value.detach().clone() for name, value in model.state_dict().items()}
        simulator = ChessSimulator(SimpleHeuristicAgent(), max_decisions=8)
        observation = simulator.reset(seed=991, agent_color=True)
        legal = simulator.legal_moves
        first = policy.choose_move(observation, legal, random.Random(1))
        second = policy.choose_move(observation, legal, random.Random(2))

        self.assertIn(first, legal)
        self.assertEqual(first, second)
        self.assertFalse(model.training)
        self.assertTrue(all(parameter.grad is None for parameter in model.parameters()))
        for name, value in model.state_dict().items():
            self.assertTrue(value.equal(before[name]), name)
        self.assertNotIn("optimizer", vars(policy))
        self.assertNotIn("replay", vars(policy))
        self.assertEqual(policy.config["epsilon"], 0.0)
        self.assertFalse(policy.config["gradients"])
        self.assertFalse(policy.config["replay_insertion"])
        self.assertEqual(policy.config["stockfish"], "not imported or called")

    def test_selected_private_snapshot_loads_and_infers_without_mutation(self) -> None:
        checkpoint = os.environ.get("VIDEOCHESS_M5_M6_POLICY_CHECKPOINT")
        if not checkpoint:
            self.skipTest("private M5 policy path not configured")

        path = Path(checkpoint)
        self.assertTrue(path.is_file(), f"checkpoint is unavailable: {path}")
        self.assertFalse(path.is_symlink())
        self._check_snapshot(path, CHECKPOINT_SHA256)

    def test_all_private_post_rl_snapshots_load_and_score_offline_state(self) -> None:
        artifact_root = os.environ.get("VIDEOCHESS_M5_M6_ARTIFACT_ROOT")
        if not artifact_root:
            self.skipTest("private M5 artifact root not configured")
        root = Path(artifact_root)
        manifest = json.loads((root / "artifact-manifest.json").read_text(encoding="utf-8"))
        snapshots = [
            item for item in manifest["files"]
            if item["path"].startswith("runs/")
            and item["path"].endswith("stage-post_rl__decisions-050000__eval-snapshot-v2.pt")
        ]
        self.assertEqual(len(snapshots), 6)
        identities: set[tuple[str, int]] = set()
        for item in snapshots:
            path = root / item["path"]
            self.assertTrue(path.is_file(), item["path"])
            self.assertFalse(path.is_symlink(), item["path"])
            self._check_snapshot(path, item["sha256"])
            model, metadata = load_evaluation_snapshot(path, device="cpu")
            identity = (metadata["arm"], metadata["training_seed"])
            self.assertNotIn(identity, identities)
            identities.add(identity)
        self.assertEqual(identities, {
            (arm, seed)
            for arm in ("warm", "scratch")
            for seed in (20261104, 20261105, 20261106)
        })


if __name__ == "__main__":
    unittest.main()
