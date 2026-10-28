"""Tests for the bounded Pre-M5 CPU feasibility probe, not a DDQN learner."""

from __future__ import annotations

import unittest

import numpy as np
import torch

from scripts.profile_m5_feasibility_v2 import (
    HISTORY_STRESS_PLIES,
    MAX_PROFILE_SECONDS,
    REPLAY_CAPACITY,
    build_replay_wire_probe,
    make_max_history_stress,
)
from videochess_rl.model.features import PositionFeatures


class M5FeasibilityProfileTests(unittest.TestCase):
    def test_hard_bounds_and_history_shape_are_explicit(self) -> None:
        self.assertEqual(MAX_PROFILE_SECONDS, 840.0)
        self.assertEqual(HISTORY_STRESS_PLIES, 801)
        self.assertEqual(REPLAY_CAPACITY, 4096)
        batch = {
            "history_moves": torch.zeros((32, 4, 4), dtype=torch.int64),
            "history_mask": torch.ones((32, 4), dtype=torch.bool),
            "candidate_mask": torch.ones((32, 1), dtype=torch.bool),
        }
        stressed = make_max_history_stress(batch)
        self.assertEqual(tuple(stressed["history_moves"].shape), (32, 801, 4))
        self.assertTrue(torch.all(stressed["history_mask"]))
        self.assertEqual(int(stressed["candidate_mask"].sum()), 32)

    def test_replay_probe_serializes_distinct_bounded_records(self) -> None:
        rows = tuple(
            PositionFeatures(
                sample_id=f"profile-{index:02d}", split="train",
                board_planes=np.zeros((13, 8, 8), dtype=np.uint8),
                state_scalars=np.zeros((6,), dtype=np.float32),
                history_moves=np.zeros((index, 4), dtype=np.uint8),
                candidate_squares=np.asarray([[0, 1]], dtype=np.uint8),
                candidate_promotion=np.zeros((1,), dtype=np.uint8),
                candidate_flags=np.zeros((1, 4), dtype=np.uint8),
                candidate_uci=("a1b1",), target_index=0, target_uci="a1b1",
            )
            for index in range(32)
        )
        observed = build_replay_wire_probe(rows)
        self.assertEqual(observed["capacity"], 4096)
        self.assertEqual(observed["unique_record_count"], 4096)
        self.assertGreater(observed["tracemalloc_incremental_peak_bytes"], 0)
        self.assertGreater(
            observed["measured_container_and_bytes_object_bytes"],
            observed["stored_wire_bytes"],
        )
        self.assertFalse(observed["persistent_file_written"])
        self.assertFalse(observed["semantically_valid_transitions_claimed"])
        short_stress = build_replay_wire_probe(rows, history_plies=32)
        self.assertEqual(short_stress["history_plies_per_state"], 32)
        self.assertGreater(short_stress["stored_wire_bytes"], observed["stored_wire_bytes"])


if __name__ == "__main__":
    unittest.main()
