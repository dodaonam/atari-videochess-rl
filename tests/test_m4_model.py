from __future__ import annotations

import unittest

import chess
import torch

from videochess_rl.model.dataset import collate_examples, model_inputs
from videochess_rl.model.features import INPUT_SCHEMA, encode_board
from videochess_rl.model.inference import select_legal_candidate
from videochess_rl.model.network import BehaviorScorer
from videochess_rl.model.training import behavior_cross_entropy


def board_from_uci(moves: list[str]) -> chess.Board:
    board = chess.Board()
    for uci in moves:
        board.push_uci(uci)
    return board


class M4ModelContractTests(unittest.TestCase):
    def test_versioned_input_shapes_dtypes_and_candidate_identity(self) -> None:
        board = chess.Board()
        features = encode_board(board, sample_id="sample-a", split="train", target_uci="e2e4")
        batch = collate_examples((features,))

        self.assertEqual(INPUT_SCHEMA, "videochess-model-input/1.0")
        self.assertEqual(tuple(batch["board_planes"].shape), (1, 13, 8, 8))
        self.assertEqual(batch["board_planes"].dtype, torch.float32)
        self.assertEqual(tuple(batch["state_scalars"].shape), (1, 6))
        self.assertEqual(batch["state_scalars"].dtype, torch.float32)
        self.assertEqual(tuple(batch["history_moves"].shape), (1, 0, 4))
        self.assertEqual(batch["history_moves"].dtype, torch.int64)
        self.assertEqual(batch["history_mask"].shape, (1, 0))
        self.assertEqual(tuple(batch["candidate_squares"].shape), (1, 20, 2))
        self.assertEqual(batch["candidate_promotion"].dtype, torch.int64)
        self.assertEqual(batch["candidate_flags"].dtype, torch.float32)
        self.assertEqual(batch["candidate_mask"].dtype, torch.bool)
        self.assertEqual(batch["candidate_uci"][0], tuple(sorted(batch["candidate_uci"][0])))
        self.assertEqual(batch["candidate_uci"][0][batch["target_indices"].item()], "e2e4")
        self.assertEqual(set(model_inputs(batch)), {
            "board_planes", "state_scalars", "history_moves", "history_mask",
            "candidate_squares", "candidate_promotion", "candidate_flags",
            "candidate_mask", "candidate_uci",
        })

    def test_actual_parameter_count_matches_accepted_small_model(self) -> None:
        model = BehaviorScorer()
        self.assertEqual(model.trainable_parameter_count, 121_897)
        self.assertLess(model.trainable_parameter_count, 250_000)

    def test_forward_cross_entropy_gradients_and_gradient_clipping(self) -> None:
        white = encode_board(chess.Board(), split="train", target_uci="e2e4")
        black = encode_board(board_from_uci(["e2e4"]), split="train", target_uci="a7a6")
        batch = collate_examples((white, black))
        model = BehaviorScorer()
        logits = model(**model_inputs(batch))
        self.assertEqual(tuple(logits.shape), (2, 20))
        self.assertTrue(torch.isfinite(logits[batch["candidate_mask"]]).all())
        loss = behavior_cross_entropy(logits, batch["candidate_mask"], batch["target_indices"])
        self.assertTrue(torch.isfinite(loss))
        loss.backward()
        for parameter_name in (
            "board_encoder.conv1.weight",
            "history_encoder.gru.weight_ih_l0",
            "metadata_projection.weight",
            "candidate_encoder.local_projection.weight",
            "shared_scorer.weight",
            "behavior_head.weight",
        ):
            parameter = dict(model.named_parameters())[parameter_name]
            self.assertIsNotNone(parameter.grad, parameter_name)
            self.assertTrue(torch.isfinite(parameter.grad).all(), parameter_name)
            self.assertGreater(float(parameter.grad.abs().sum()), 0.0, parameter_name)

    def test_black_rank_flip_and_complete_history_are_preserved(self) -> None:
        initial = encode_board(chess.Board(), split="train")
        after_white_move = encode_board(board_from_uci(["e2e4"]), split="train")
        self.assertEqual(after_white_move.history_length, 1)
        self.assertEqual(after_white_move.history_moves.tolist(), [[12, 28, 0, 1]])
        # Black's pawn on e7 is now a mover-side piece at the flipped rank 1.
        self.assertEqual(int(after_white_move.board_planes[0, 1, chess.FILE_NAMES.index("e")]), 1)
        self.assertNotEqual(initial.history_moves.shape, after_white_move.history_moves.shape)
        self.assertEqual(float(after_white_move.state_scalars[0]), 0.0)
        # Candidate coordinates share the mover-oriented board frame while
        # candidate_uci retains original-orientation semantic identities.
        black_move_index = after_white_move.candidate_uci.index("e7e5")
        self.assertEqual(after_white_move.candidate_squares[black_move_index].tolist(), [12, 28])

    def test_repetition_sensitive_history_is_not_reduced_to_fen(self) -> None:
        board = board_from_uci(["g1f3", "g8f6", "f3g1", "f6g8"] * 2)
        self.assertEqual(board.board_fen(), chess.Board().board_fen())
        self.assertEqual(encode_board(board, split="train").history_length, 8)

    def test_special_candidate_flags_promotions_and_checks(self) -> None:
        castle = encode_board(
            board_from_uci(["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "g8f6"]),
            split="train",
        )
        castle_index = castle.candidate_uci.index("e1g1")
        self.assertEqual(castle.candidate_flags[castle_index].tolist()[1], 1)

        ep_board = board_from_uci(["e2e4", "a7a6", "e4e5", "d7d5"])
        ep = encode_board(ep_board, split="train")
        ep_index = ep.candidate_uci.index("e5d6")
        self.assertEqual(ep.candidate_flags[ep_index].tolist()[0:3], [1, 0, 1])
        self.assertEqual(int(ep.board_planes[12].sum()), 1)

        promotion_board = board_from_uci([
            "b2b4", "e7e6", "b4b5", "c7c6", "b5c6", "e8e7",
            "c6d7", "a7a6",
        ])
        promotions = encode_board(promotion_board, split="train")
        self.assertEqual(
            [uci for uci in promotions.candidate_uci if uci.startswith("d7c8")],
            ["d7c8b", "d7c8n", "d7c8q", "d7c8r"],
        )

        check_board = board_from_uci(["f2f3", "e7e5", "g2g4"])
        checking = encode_board(check_board, split="train")
        check_index = checking.candidate_uci.index("d8h4")
        self.assertEqual(int(checking.candidate_flags[check_index, 3]), 1)

    def test_terminal_empty_candidates_are_not_scored_or_selected(self) -> None:
        board = board_from_uci(["f2f3", "e7e5", "g2g4", "d8h4"])
        self.assertIsNotNone(board.outcome(claim_draw=False))
        terminal = encode_board(board, split="inference")
        self.assertEqual(terminal.candidate_count, 0)
        batch = collate_examples((terminal,), require_targets=False)
        logits = BehaviorScorer()(**model_inputs(batch))
        self.assertEqual(tuple(logits.shape), (1, 0))
        with self.assertRaisesRegex(ValueError, "empty terminal"):
            select_legal_candidate(logits[0], batch["candidate_mask"][0], terminal.candidate_uci)

    def test_legal_mask_excludes_padded_scores_and_ties_are_lexical(self) -> None:
        mask = torch.tensor([[True, True, False]])
        targets = torch.tensor([0])
        logits = torch.tensor([[0.0, 2.0, -100.0]], requires_grad=True)
        baseline = behavior_cross_entropy(logits, mask, targets)
        padded_high = torch.tensor([[0.0, 2.0, 1_000_000.0]], requires_grad=True)
        changed = behavior_cross_entropy(padded_high, mask, targets)
        self.assertEqual(float(baseline.detach()), float(changed.detach()))
        changed.backward()
        self.assertEqual(float(padded_high.grad[0, 2]), 0.0)
        self.assertEqual(select_legal_candidate([1.0, 1.0, 9.0], [True, True, False], ["a2a3", "a2a4", "z9z9"]), "a2a3")

    def test_model_rejects_nonstandard_roots_and_illegal_targets(self) -> None:
        with self.assertRaisesRegex(ValueError, "nonstandard initial"):
            encode_board(chess.Board("8/8/8/8/8/8/4K3/7k w - - 0 1"))
        with self.assertRaisesRegex(ValueError, "exactly once"):
            encode_board(chess.Board(), target_uci="a1a8")

    def test_model_rejects_misaligned_history_masks_and_candidate_identities(self) -> None:
        first = encode_board(board_from_uci(["e2e4", "e7e5"]), split="train")
        second = encode_board(board_from_uci(["d2d4", "d7d5"]), split="train")
        batch = collate_examples((first, second), require_targets=False)
        model = BehaviorScorer()
        broken_history = model_inputs(batch)
        broken_history["history_mask"] = batch["history_mask"].clone()
        broken_history["history_mask"][0, 0] = False
        with self.assertRaisesRegex(ValueError, "true prefix"):
            model(**broken_history)

        broken_candidates = model_inputs(batch)
        broken_candidates["candidate_uci"] = [tuple(reversed(actions)) for actions in batch["candidate_uci"]]
        with self.assertRaisesRegex(ValueError, "lexically ordered"):
            model(**broken_candidates)


if __name__ == "__main__":
    unittest.main()
