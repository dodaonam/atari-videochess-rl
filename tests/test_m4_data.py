from __future__ import annotations

import unittest
from dataclasses import replace
import random
from unittest.mock import patch

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
    collated_effective_model_input_sha256,
    effective_model_input_sha256,
    model_inputs,
    select_distinct_training_examples,
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

    @staticmethod
    def _distinct_positions(count: int) -> list:
        rng = random.Random(81027)
        rows = []
        cursor = 0
        while len(rows) < count:
            board = chess.Board()
            while board.outcome(claim_draw=False) is None and len(rows) < count:
                legal = sorted(move.uci() for move in board.legal_moves)
                target = legal[rng.randrange(len(legal))]
                rows.append(encode_board(
                    board, sample_id=f"{cursor:064x}", split="train", target_uci=target,
                ))
                cursor += 1
                board.push_uci(target)
        return rows

    def test_distinct_selector_is_deterministic_train_only_and_iteration_independent(self) -> None:
        rows = self._distinct_positions(132)
        validation = replace(rows[0], sample_id="0" * 64, split="validation")
        first = select_distinct_training_examples([*rows, validation], 128)
        second = select_distinct_training_examples([validation, *reversed(rows)], 128)
        self.assertEqual(first.sample_ids, second.sample_ids)
        self.assertEqual(first.input_sha256, second.input_sha256)
        self.assertEqual(len(first.examples), 128)
        self.assertEqual(len(set(first.sample_ids)), 128)
        self.assertEqual(tuple(sorted(first.sample_ids)), first.sample_ids)
        self.assertTrue(all(row.split == "train" for row in first.examples))
        self.assertEqual(first.sample_ids_sha256, second.sample_ids_sha256)
        self.assertEqual(first.input_identities_sha256, second.input_identities_sha256)
        self.assertEqual(first.rule, "m4-02-distinct-effective-input-ascending-sample-id/1.0")

    def test_selector_deduplicates_conflicting_and_matching_targets_without_label_selection(self) -> None:
        board = chess.Board()
        first = encode_board(board, sample_id="a", split="train", target_uci="c2c4")
        conflict = encode_board(board, sample_id="b", split="train", target_uci="e2e4")
        same_label = replace(first, sample_id="c")
        later_board = chess.Board()
        later_board.push_uci("e2e4")
        later = encode_board(later_board, sample_id="z", split="train", target_uci="a7a6")
        selected = select_distinct_training_examples(
            [conflict, later, same_label, first], count=2,
        )
        self.assertEqual(selected.sample_ids, ("a", "z"))
        self.assertEqual(selected.examples[0].target_uci, "c2c4")
        self.assertEqual(len(set(selected.input_sha256)), 2)
        self.assertEqual(
            effective_model_input_sha256(first),
            effective_model_input_sha256(conflict),
        )

    def test_effective_input_identity_excludes_labels_and_provenance(self) -> None:
        example = encode_board(
            chess.Board(), sample_id="sample-a", split="train", target_uci="e2e4",
        )
        changed_metadata = replace(
            example, sample_id="sample-b", split="validation", target_index=0,
            target_uci="d2d4", ply_index=900,
        )
        self.assertEqual(
            effective_model_input_sha256(example),
            effective_model_input_sha256(changed_metadata),
        )

    def test_unpadded_identity_matches_collated_inputs_with_unrelated_padding(self) -> None:
        short = encode_board(chess.Board(), sample_id="short", split="train", target_uci="e2e4")
        board = chess.Board()
        for uci in ("e2e4", "a7a6", "e4e5"):
            board.push_uci(uci)
        long = encode_board(board, sample_id="long", split="train", target_uci="d7d5")
        batch = collate_examples((short, long))
        for index, example in enumerate((short, long)):
            self.assertEqual(
                collated_effective_model_input_sha256(batch, index),
                effective_model_input_sha256(example),
            )
        malformed = replace(short, candidate_uci=tuple(reversed(short.candidate_uci)))
        with self.assertRaisesRegex(ValueError, "lexically ordered"):
            effective_model_input_sha256(malformed)

    def test_selector_detects_digest_collision_instead_of_merging_unequal_inputs(self) -> None:
        first_board = chess.Board()
        first = encode_board(first_board, sample_id="a", split="train", target_uci="e2e4")
        second_board = chess.Board()
        second_board.push_uci("e2e4")
        second = encode_board(second_board, sample_id="b", split="train", target_uci="a7a6")
        with patch("videochess_rl.model.dataset._effective_model_input_digest", return_value="same-hash"):
            with self.assertRaisesRegex(RuntimeError, "identity collision"):
                select_distinct_training_examples((first, second), count=2)


if __name__ == "__main__":
    unittest.main()
