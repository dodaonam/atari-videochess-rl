from __future__ import annotations

import unittest
from dataclasses import replace
from unittest.mock import patch
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

import chess
import torch

from videochess_rl.model.features import encode_board
from videochess_rl.model.network import BehaviorScorer
from videochess_rl.model.training import (
    TrainingConfig,
    behavior_cross_entropy,
    configure_determinism,
    evaluate_examples,
    fit_seed,
    run_overfit_gate,
)
from videochess_rl.model.cli import RUN_SCHEMA, _event, _prior_m4_runs, _prior_seed_time_usage


class M4TrainingTests(unittest.TestCase):
    @staticmethod
    def examples() -> tuple:
        white = encode_board(chess.Board(), sample_id="a", split="train", target_uci="e2e4")
        board = chess.Board()
        board.push_uci("e2e4")
        validation = encode_board(board, sample_id="b", split="validation", target_uci="a7a6", ply_index=1)
        return white, validation

    def test_masked_cross_entropy_ignores_padding_and_validates_targets(self) -> None:
        mask = torch.tensor([[True, True, False]])
        target = torch.tensor([1])
        logits = torch.tensor([[0.0, 2.0, -100.0]], requires_grad=True)
        high_padding = torch.tensor([[0.0, 2.0, 1_000_000.0]], requires_grad=True)
        loss_a = behavior_cross_entropy(logits, mask, target)
        loss_b = behavior_cross_entropy(high_padding, mask, target)
        self.assertEqual(float(loss_a.detach()), float(loss_b.detach()))
        loss_b.backward()
        self.assertEqual(float(high_padding.grad[0, 2]), 0.0)
        with self.assertRaisesRegex(ValueError, "padded or illegal"):
            behavior_cross_entropy(logits.detach(), mask, torch.tensor([2]))
        with self.assertRaisesRegex(ValueError, "at least one legal candidate"):
            behavior_cross_entropy(torch.zeros((1, 2)), torch.zeros((1, 2), dtype=torch.bool), torch.tensor([0]))
        with self.assertRaisesRegex(FloatingPointError, "non-finite"):
            behavior_cross_entropy(torch.tensor([[float("inf"), 0.0, 0.0]]), mask, target)

    def test_validation_metrics_include_uniform_baseline_and_ranking(self) -> None:
        train, validation = self.examples()
        result = evaluate_examples(BehaviorScorer(), (validation,), include_strata=True)
        self.assertEqual(result["split"], "validation")
        self.assertEqual(result["examples"], 1)
        self.assertIn("mrr", result)
        self.assertIn("uniform_legal_baseline", result)
        self.assertIn("black_to_move", result["by_side_to_move"])
        self.assertIn("opening_plies_0_19", result["by_target_move_type_or_phase"])
        with self.assertRaisesRegex(ValueError, "cannot mix data splits"):
            evaluate_examples(BehaviorScorer(), (train, validation))

    def test_seed_configuration_reproduces_model_initialization(self) -> None:
        first_state = None
        for _ in range(2):
            settings = configure_determinism(20261022)
            model = BehaviorScorer()
            if first_state is None:
                first_state = {key: value.clone() for key, value in model.state_dict().items()}
            else:
                self.assertTrue(all(torch.equal(first_state[key], value) for key, value in model.state_dict().items()))
            self.assertTrue(settings["deterministic_algorithms"])
            self.assertEqual(settings["intraop_threads"], 1)

    def test_adamw_updates_weights_and_records_gradient_clipping(self) -> None:
        train, validation = self.examples()
        configure_determinism(7)
        model = BehaviorScorer()
        before = model.behavior_head.weight.detach().clone()
        result = fit_seed(
            model,
            (train,),
            (validation,),
            seed=7,
            config=TrainingConfig(
                batch_size=1,
                maximum_epochs=1,
                early_stopping_patience=1,
                learning_rate=3e-4,
                max_seconds_per_seed=60,
            ),
        )
        self.assertEqual(result.optimizer_updates, 1)
        self.assertEqual(result.best_epoch, 1)
        self.assertFalse(torch.equal(before, model.behavior_head.weight))
        epoch = result.epoch_history[0]
        self.assertLessEqual(epoch["max_postclip_gradient_norm"], 1.00001)
        self.assertGreaterEqual(epoch["max_preclip_gradient_norm"], epoch["max_postclip_gradient_norm"])

    def test_tensor_budget_microbatches_accumulate_to_effective_batch_size(self) -> None:
        train, validation = self.examples()
        rows = tuple(replace(train, sample_id=f"train-{index}") for index in range(4))
        configure_determinism(17)
        with patch("videochess_rl.model.training.MAX_PADDED_CANDIDATE_SLOTS", 20):
            result = fit_seed(
                BehaviorScorer(),
                rows,
                (validation,),
                seed=17,
                config=TrainingConfig(
                    batch_size=4,
                    maximum_epochs=1,
                    early_stopping_patience=1,
                    max_seconds_per_seed=60,
                ),
            )
        self.assertEqual(result.optimizer_updates, 1)
        self.assertEqual(result.epoch_history[0]["physical_microbatches"], 4)

    def test_retry_budget_ledger_accumulates_aggregate_and_per_seed_time(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            gate_failure = root / "attempt-1"
            gate_failure.mkdir()
            (gate_failure / "run_manifest.json").write_text(json.dumps({
                "schema": RUN_SCHEMA,
                "started_at_utc": now,
                "ended_at_utc": now,
                "execution_elapsed_seconds": 12.0,
                "training_config": {"seeds": [20261022, 20261023, 20261024]},
                "sanity_gate": {"status": "FAIL", "duration_seconds": 8.0},
                "seed_runs": [],
            }), encoding="utf-8")
            training_failure = root / "attempt-2"
            training_failure.mkdir()
            (training_failure / "run_manifest.json").write_text(json.dumps({
                "schema": RUN_SCHEMA,
                "started_at_utc": now,
                "ended_at_utc": now,
                "execution_elapsed_seconds": 30.0,
                "training_config": {"seeds": [20261022, 20261023, 20261024]},
                "sanity_gate": {"status": "PASS", "duration_seconds": 5.0},
                "seed_runs": [
                    {"seed": 20261022, "duration_seconds": 15.0, "seed_elapsed_including_gate_seconds": 20.0},
                    {"seed": 20261023, "duration_seconds": 10.0, "seed_elapsed_including_gate_seconds": 10.0},
                ],
            }), encoding="utf-8")

            prior = _prior_m4_runs(root)
            seed_usage = _prior_seed_time_usage(prior)
            self.assertEqual(sum(run["_execution_elapsed_seconds"] for run in prior), 42.0)
            self.assertEqual(seed_usage[20261022], 28.0)
            self.assertEqual(seed_usage[20261023], 10.0)

    def test_stage_event_records_stage_name_and_details(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _event(root, "stage", name="reverify_release_and_load_features", seed=20261022)
            event = json.loads((root / "events.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(event["event"], "stage")
            self.assertEqual(event["name"], "reverify_release_and_load_features")
            self.assertEqual(event["seed"], 20261022)
            self.assertTrue(event["at_utc"].endswith("Z"))

    def test_early_stop_keeps_earlier_epoch_when_validation_ties(self) -> None:
        train, validation = self.examples()
        configure_determinism(9)
        model = BehaviorScorer()
        result = fit_seed(
            model,
            (train,),
            (validation,),
            seed=9,
            config=TrainingConfig(
                batch_size=1,
                maximum_epochs=10,
                early_stopping_patience=4,
                learning_rate=0.0,
                weight_decay=0.0,
                max_seconds_per_seed=60,
            ),
        )
        self.assertEqual(result.stop_reason, "validation_patience")
        self.assertEqual(result.best_epoch, 1)
        self.assertEqual(len(result.epoch_history), 5)
        self.assertEqual(result.optimizer_updates, 5)

    def test_budget_stop_and_split_isolation_are_explicit(self) -> None:
        train, validation = self.examples()
        model = BehaviorScorer()
        stopped = fit_seed(
            model, (train,), (validation,), seed=3,
            config=TrainingConfig(max_seconds_per_seed=0, maximum_epochs=2),
        )
        self.assertEqual(stopped.stop_reason, "seed_time_limit_before_epoch")
        self.assertEqual(stopped.optimizer_updates, 0)
        test_example = encode_board(chess.Board(), split="test", target_uci="e2e4")
        with self.assertRaisesRegex(ValueError, "validation-split"):
            fit_seed(BehaviorScorer(), (train,), (test_example,), seed=3)

    def test_sanity_gate_records_fixed_sample_and_respects_zero_update_limit(self) -> None:
        base, _ = self.examples()
        rows = tuple(
            replace(base, sample_id=f"sample-{index:03d}")
            for index in range(128)
        )
        result = run_overfit_gate(BehaviorScorer(), rows, seed=11, max_updates=0)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["sample_id_count"], 128)
        self.assertEqual(result["updates"], 0)
        self.assertEqual(result["final"]["updates"], 0)
        self.assertIn("cross_entropy", result["final"])


if __name__ == "__main__":
    unittest.main()
