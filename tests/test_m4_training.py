from __future__ import annotations

import unittest
from dataclasses import replace
from unittest.mock import patch
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace

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
from videochess_rl.model.cli import (
    CURRENT_RELEASE_EVIDENCE,
    HISTORICAL_RELEASE_EVIDENCE,
    RUN_SCHEMA,
    _event,
    _prior_diagnostic_seconds,
    _prior_m4_runs,
    _prior_seed_time_usage,
    _previous_verification,
    verify_artifacts,
)
from videochess_rl.model.checkpoint import write_artifact_manifest


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

    def test_prior_read_only_diagnostic_is_charged_to_aggregate_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / ".agents/evidence/logs/M4-02-sanity-gate-diagnostic-20261027.json"
            path.parent.mkdir(parents=True)
            evidence = {
                "schema": "videochess-m4-sanity-input-conflict-diagnostic/1.0",
                "status": "structural_conflict_blocks_threshold",
                "duration_seconds": 134.85,
                "diagnostic_git_revision": "e5e42f703bfd3386c94de17b607aa5102b60201f",
                "dataset": {
                    "release_id": "f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890",
                    "manifest_sha256": "be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12",
                    "split_assignment_sha256": "84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e",
                    "post_load_release_files_unchanged": True,
                },
            }
            path.write_text(json.dumps(evidence), encoding="utf-8")
            self.assertEqual(_prior_diagnostic_seconds(root)["duration_seconds"], 134.85)
            evidence["dataset"]["release_id"] = "wrong-release"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "accepted immutable M3 release"):
                _prior_diagnostic_seconds(root)

    def test_prior_release_verification_budget_charges_historical_and_current_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = {
                f"file-{index}.json": {"sha256": f"{index:064x}", "size_bytes": index}
                for index in range(9)
            }
            stdout = json.dumps({
                "release_id": "f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890",
                "manifest_sha256": "be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12",
                "games": 1_000,
                "positions": 19_268,
            })
            for relative, duration in (
                (HISTORICAL_RELEASE_EVIDENCE, 111.186),
                (CURRENT_RELEASE_EVIDENCE, 96.5),
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                value = {
                    "schema": "videochess-m4-release-verification/1.0" if relative == CURRENT_RELEASE_EVIDENCE else "historical",
                    "revision": "a" * 40,
                    "duration_seconds": duration,
                    "exit_code": 0,
                    "unchanged": True,
                    "files_before": files,
                    "files_after": files,
                    "stdout": stdout,
                }
                if relative == CURRENT_RELEASE_EVIDENCE:
                    value.update({
                        "release_id": "f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890",
                        "manifest_sha256": "be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12",
                        "split_assignment_sha256": "84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e",
                    })
                path.write_text(json.dumps(value), encoding="utf-8")
            result = _previous_verification(root)
            self.assertEqual(result["duration_seconds"], 207.686)
            self.assertEqual(len(result["checks"]), 2)
            self.assertTrue(result["unchanged"])

            current_path = root / CURRENT_RELEASE_EVIDENCE
            current = json.loads(current_path.read_text(encoding="utf-8"))
            current["split_assignment_sha256"] = "0" * 64
            current_path.write_text(json.dumps(current), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "incorrect explicit release identities"):
                _previous_verification(root)

    def test_artifact_verifier_checks_persisted_m4_sanity_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ids = [f"{value:064x}" for value in range(128)]
            identities = [f"{value + 1000:064x}" for value in range(128)]
            ids_hash = hashlib.sha256("\n".join(ids).encode()).hexdigest()
            identities_hash = hashlib.sha256("\n".join(identities).encode("ascii")).hexdigest()
            selection = {
                "schema": "videochess-m4-sanity-selection/1.0",
                "protocol_revision": "M4-02-distinct-effective-inputs/1.0",
                "count": 128,
                "selected_ids_and_order": ids,
                "sample_ids_sha256": ids_hash,
                "effective_input_sha256": identities,
                "effective_input_identities_sha256": identities_hash,
                "identities_pairwise_distinct": True,
                "source_split": "train",
                "label_independent": True,
                "collated_input_equivalence_verified": True,
            }
            (root / "sanity_selection.json").write_text(json.dumps(selection), encoding="utf-8")
            (root / "run_manifest.json").write_text(json.dumps({
                "schema": RUN_SCHEMA,
                "sanity_sample_selection": {
                    "file": "sanity_selection.json",
                    "sample_ids_sha256": ids_hash,
                    "effective_input_identities_sha256": identities_hash,
                },
                "selected_checkpoint": None,
            }), encoding="utf-8")
            write_artifact_manifest(root)
            with redirect_stdout(StringIO()):
                self.assertEqual(verify_artifacts(SimpleNamespace(directory=root)), 0)

            selection["effective_input_sha256"][1] = selection["effective_input_sha256"][0]
            (root / "sanity_selection.json").write_text(json.dumps(selection), encoding="utf-8")
            write_artifact_manifest(root)
            with self.assertRaisesRegex(ValueError, "violates its versioned train-only contract"):
                verify_artifacts(SimpleNamespace(directory=root))

            selection["effective_input_sha256"] = identities
            (root / "sanity_selection.json").write_text(json.dumps(selection), encoding="utf-8")
            malicious_manifest = {
                "schema": RUN_SCHEMA,
                "sanity_sample_selection": {
                    "file": "../../outside.json",
                    "sample_ids_sha256": ids_hash,
                    "effective_input_identities_sha256": identities_hash,
                },
                "selected_checkpoint": {"path": "../../outside.pt"},
            }
            (root / "run_manifest.json").write_text(json.dumps(malicious_manifest), encoding="utf-8")
            write_artifact_manifest(root)
            with self.assertRaisesRegex(ValueError, "selection path is unsafe"):
                verify_artifacts(SimpleNamespace(directory=root))

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
