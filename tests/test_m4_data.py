from __future__ import annotations

import unittest
from dataclasses import replace

import chess

from videochess_rl.data.contracts import (
    board_position_signature,
    candidate_identity,
    digest,
    replay_history_identity,
    sample_identity,
)
from videochess_rl.model.dataset import (
    EXPECTED_COUNTS,
    EXPECTED_GAME_COUNTS,
    EXPECTED_MANIFEST_SHA256,
    EXPECTED_RELEASE_ID,
    EXPECTED_SPLIT_SHA256,
    _validate_position_against_board,
    collate_examples,
    model_inputs,
    smallest_training_sample_ids,
)
from videochess_rl.model.features import encode_board


class M4DataContractTests(unittest.TestCase):
    def test_loader_is_bound_to_the_accepted_m3_release_and_split(self) -> None:
        self.assertEqual(EXPECTED_RELEASE_ID, "f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890")
        self.assertEqual(EXPECTED_MANIFEST_SHA256, "be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12")
        self.assertEqual(EXPECTED_SPLIT_SHA256, "84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e")
        self.assertEqual(EXPECTED_COUNTS, {"train": 15_196, "validation": 2_015, "test": 2_057})
        self.assertEqual(EXPECTED_GAME_COUNTS, {"train": 795, "validation": 102, "test": 103})

    def setUp(self) -> None:
        self.game = {
            "game_id": "a" * 64,
            "normalized_game_sha256": "b" * 64,
            "source_id": "c" * 64,
            "initial_fen": chess.STARTING_FEN,
            "moves_uci": ["e2e4"],
        }
        board = chess.Board()
        candidates = sorted(move.uci() for move in board.legal_moves)
        sample_id = sample_identity(
            self.game["source_id"], self.game["game_id"], self.game["normalized_game_sha256"], 0
        )
        self.position = {
            "schema": "videochess-position/1.0",
            "schema_version": "videochess-position/1.0",
            "record_id": sample_id,
            "sample_id": sample_id,
            "game_id": self.game["game_id"],
            "source_id": self.game["source_id"],
            "normalized_game_sha256": self.game["normalized_game_sha256"],
            "ply_index": 0,
            "reconstruction_path": {"game_id": self.game["game_id"], "ply_index": 0},
            "fen": board.fen(en_passant="legal"),
            "side_to_move": "white",
            "split": "train",
            "split_id": "train",
            "board_position_signature": board_position_signature(board),
            "history_state_id": replay_history_identity(chess.STARTING_FEN, []),
            "legal_moves_uci": candidates,
            "played_move_uci": "e2e4",
            "candidate_count": len(candidates),
            "candidate_set_sha256": digest({
                "domain": "videochess-candidate-set/v1",
                "sample_id": sample_id,
                "legal_moves_uci": candidates,
            }),
            "played_candidate_id": candidate_identity(sample_id, "e2e4"),
        }

    def test_replayed_position_matches_exact_target_and_candidate_set(self) -> None:
        candidate_uci = _validate_position_against_board(
            self.position, self.game, chess.Board(), "train"
        )
        self.assertIn("e2e4", candidate_uci)
        self.assertEqual(candidate_uci, tuple(self.position["legal_moves_uci"]))

    def test_malformed_target_wrong_split_and_corrupt_history_are_rejected(self) -> None:
        bad_target = dict(self.position, played_move_uci="a1a8")
        with self.assertRaisesRegex(ValueError, "played_move_uci"):
            _validate_position_against_board(bad_target, self.game, chess.Board(), "train")
        with self.assertRaisesRegex(ValueError, "split"):
            _validate_position_against_board(self.position, self.game, chess.Board(), "test")
        bad_history = dict(self.position, history_state_id="d" * 64)
        with self.assertRaisesRegex(ValueError, "history-state"):
            _validate_position_against_board(bad_history, self.game, chess.Board(), "train")

    def test_model_inputs_exclude_results_split_and_dataset_metadata(self) -> None:
        example = encode_board(chess.Board(), sample_id="sample-1", split="train", target_uci="e2e4")
        batch = collate_examples((example,))
        inputs = model_inputs(batch)
        self.assertEqual(set(inputs), {
            "board_planes", "state_scalars", "history_moves", "history_mask",
            "candidate_squares", "candidate_promotion", "candidate_flags",
            "candidate_mask", "candidate_uci",
        })
        self.assertNotIn("target_indices", inputs)
        self.assertNotIn("sample_ids", inputs)
        self.assertNotIn("splits", inputs)
        self.assertNotIn("pgn_result", inputs)

    def test_sanity_ids_are_lexically_smallest_and_train_only(self) -> None:
        base = encode_board(chess.Board(), split="train", target_uci="e2e4")
        train = [replace(base, sample_id=f"{value:064x}") for value in range(140, 0, -1)]
        validation = replace(base, sample_id="0" * 64, split="validation")
        chosen = smallest_training_sample_ids([*train, validation], 128)
        self.assertEqual(chosen, tuple(f"{value:064x}" for value in range(1, 129)))
        self.assertNotIn(validation.sample_id, chosen)

    def test_batch_padding_and_masks_do_not_change_semantic_uci_order(self) -> None:
        short = encode_board(chess.Board(), sample_id="short", split="train", target_uci="e2e4")
        longer_board = chess.Board()
        longer_board.push_uci("e2e4")
        longer_board.push_uci("a7a6")
        longer_board.push_uci("e4e5")
        long = encode_board(longer_board, sample_id="long", split="train", target_uci="e7e6")
        batch = collate_examples((short, long))
        self.assertEqual(tuple(batch["history_moves"].shape), (2, 3, 4))
        self.assertEqual(batch["history_mask"].tolist(), [[False, False, False], [True, True, True]])
        self.assertEqual(batch["candidate_uci"][0], short.candidate_uci)
        self.assertEqual(batch["candidate_uci"][1], long.candidate_uci)
        self.assertEqual(int(batch["candidate_mask"][0].sum()), short.candidate_count)
        self.assertEqual(int(batch["candidate_mask"][1].sum()), long.candidate_count)


if __name__ == "__main__":
    unittest.main()
