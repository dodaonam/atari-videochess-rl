"""Read-only CPU inference test for the exact frozen M6 policy roster."""

from __future__ import annotations

import os
from pathlib import Path
import unittest

import chess

from tests.test_m6_adapter import _context
from videochess_rl.m6.adapter import M6PolicyAdapter
from videochess_rl.m6.campaign import load_policy_roster


class M6PrivatePolicyRosterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        m5_root = os.environ.get("VIDEOCHESS_M5_M6_ARTIFACT_ROOT")
        m4_root = os.environ.get("VIDEOCHESS_M6_M4_ARTIFACT_ROOT")
        if not m5_root or not m4_root:
            raise unittest.SkipTest("private M4/M5 artifact roots are not configured")
        if not Path(m5_root).is_dir() or not Path(m4_root).is_dir():
            raise unittest.SkipTest("private M4/M5 artifact roots are unavailable on this checkout")
        cls.roster = load_policy_roster(m5_root, m4_root)

    def test_all_frozen_policies_score_one_verified_rgb_state_without_mutation(self) -> None:
        context = _context()
        expected_ids = {
            "m5-warm-seed-20261104-post-rl",
            "m5-scratch-seed-20261104-post-rl",
            "m4-behavior-only-seed-20261024",
            "simple-material-heuristic",
            "random-legal",
        }
        self.assertEqual(set(self.roster), expected_ids)
        for policy_id, (policy, identity) in self.roster.items():
            with self.subTest(policy_id=policy_id):
                model = getattr(policy, "model", None)
                before = ({name: tensor.detach().clone() for name, tensor in model.state_dict().items()}
                          if model is not None else None)
                adapter = M6PolicyAdapter(policy, identity, rng_seed=20261130)
                first = adapter(context)
                self.assertIn(first.uci, context.legal_moves_uci)
                self.assertEqual(first.metadata["policy_id"], identity.policy_id)
                self.assertEqual(first.metadata["checkpoint_sha256"], identity.checkpoint_sha256)
                self.assertFalse(first.metadata["training"])
                self.assertFalse(first.metadata["optimizer"])
                self.assertFalse(first.metadata["replay_insertion"])
                self.assertFalse(first.metadata["stockfish"])
                second = adapter(context)
                self.assertEqual(first.uci, second.uci)
                if model is not None:
                    self.assertFalse(model.training)
                    self.assertTrue(all(parameter.grad is None for parameter in model.parameters()))
                    self.assertTrue(all((model.state_dict()[name] == tensor).all().item() for name, tensor in before.items()))
                self.assertEqual(context.side_to_move, chess.WHITE)


if __name__ == "__main__":
    unittest.main()
