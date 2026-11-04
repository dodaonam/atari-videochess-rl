"""Regression coverage for post-merge demo identity, lifecycle, preflight, and storage."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import queue
import sys
import threading
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

from videochess_rl.environment import ALEConfig, ALEFrame
from videochess_rl.episode import run_episode
from videochess_rl.improvement import demo, policies
from videochess_rl.improvement.live import DemoSessionState, LiveDemoWindow
from videochess_rl.improvement.preflight import run_demo_preflight


class FakeWidget:
    def __init__(self):
        self.options = {}

    def configure(self, **kwargs):
        self.options.update(kwargs)


class FakeTreeview:
    def __init__(self): self.rows = {}; self.next_id = 0
    def get_children(self): return tuple(self.rows)
    def delete(self, item): self.rows.pop(item, None)
    def insert(self, _parent, _where, *, values, tags):
        self.next_id += 1; key = str(self.next_id); self.rows[key] = (values, tags); return key
    def see(self, _item): pass


class FakeRoot:
    def __init__(self): self.destroyed = False; self.callbacks = []
    def destroy(self): self.destroyed = True
    def after(self, delay, callback): self.callbacks.append((delay, callback))


class FakeEnvironment:
    def __init__(self, runtime):
        self._runtime = runtime
        self.closed = False

    def runtime_info(self):
        return self._runtime

    def close(self):
        self.closed = True


class PolicySeedContractTests(unittest.TestCase):
    def test_double_dqn_snapshot_load_is_independent_of_reset_seed(self):
        model = torch.nn.Linear(1, 1)
        metadata = {"experiment_id": policies.EXPERIMENT, "training_seed": 20261103,
            "execution_kind": "official", "q_only_evaluation": True, "resumable": False,
            "code_sha256": "c" * 64, "config_sha256": "d" * 64,
            "m4_sha256": policies.M4_SHA256, "valid_decisions": 250000}
        with TemporaryDirectory() as temp:
            attempt = Path(temp)
            (attempt / "run.json").write_text(json.dumps({"identity": {
                "experiment_id": policies.EXPERIMENT, "training_seed": 20261103,
                "execution_kind": "official", "code_sha256": "c" * 64,
                "config_sha256": "d" * 64}, "valid_decisions": 250000,
                "optimizer_updates": 62245, "target_syncs": 124, "completed_episodes": 3203}))
            with patch.object(policies, "ATTEMPT", attempt), \
                 patch.object(policies, "sha256", return_value="a" * 64), \
                 patch.object(policies, "load_evaluation_snapshot", return_value=(model, metadata)):
                first, first_identity = policies.load_demo_policy("double-dqn", checkpoint="snapshot.pt",
                    expected_sha256="a" * 64, policy_rng_seed=20261103)
                custom, custom_identity = policies.load_demo_policy("double-dqn", checkpoint="snapshot.pt",
                    expected_sha256="a" * 64, policy_rng_seed=123456)
        self.assertEqual(first_identity.training_seed, 20261103)
        self.assertEqual(custom_identity.training_seed, 20261103)
        self.assertEqual(first_identity.checkpoint_sha256, custom_identity.checkpoint_sha256)
        self.assertEqual(first_identity.policy_type, custom_identity.policy_type)
        self.assertEqual(first.rng_seed, 20261103)
        self.assertEqual(custom.rng_seed, 123456)

    def test_invalid_q_hash_and_immutable_training_metadata_are_rejected(self):
        with TemporaryDirectory() as temp:
            attempt = Path(temp)
            (attempt / "run.json").write_text(json.dumps({"identity": {
                "experiment_id": policies.EXPERIMENT, "training_seed": 20261103,
                "execution_kind": "official", "code_sha256": "c" * 64,
                "config_sha256": "d" * 64}, "valid_decisions": 250000,
                "optimizer_updates": 62245, "target_syncs": 124, "completed_episodes": 3203}))
            good_meta = {"experiment_id": policies.EXPERIMENT, "training_seed": 20261103,
                "execution_kind": "official", "q_only_evaluation": True, "resumable": False,
                "code_sha256": "c" * 64, "config_sha256": "d" * 64,
                "m4_sha256": policies.M4_SHA256, "valid_decisions": 250000}
            with patch.object(policies, "ATTEMPT", attempt), \
                 patch.object(policies, "load_evaluation_snapshot", return_value=(object(), good_meta)):
                with patch.object(policies, "sha256", return_value="b" * 64):
                    with self.assertRaisesRegex(ValueError, "SHA-256"):
                        policies.load_demo_policy("double-dqn", checkpoint="snapshot.pt",
                            expected_sha256="a" * 64, policy_rng_seed=123456)
                with patch.object(policies, "sha256", return_value="a" * 64):
                    bad_meta = dict(good_meta, training_seed=123456)
                    with patch.object(policies, "load_evaluation_snapshot", return_value=(object(), bad_meta)):
                        with self.assertRaisesRegex(ValueError, "metadata"):
                            policies.load_demo_policy("double-dqn", checkpoint="snapshot.pt",
                                expected_sha256="a" * 64, policy_rng_seed=123456)

    def test_m4_a_loads_with_custom_reset_seed_and_keeps_checkpoint_identity(self):
        model = torch.nn.Linear(1, 1)
        bundle = {"metadata": {"checkpoint_role": "improvement_m4", "run_id": policies.EXPERIMENT,
            "seed": policies.M4_TRAINING_SEED, "dataset_release_id": policies.M4_DATASET_RELEASE,
            "input_schema": "videochess-model-input/1.0",
            "model_schema": "videochess-behavior-scorer/1.0"}}
        with patch.object(policies, "sha256", return_value=policies.M4_SHA256), \
             patch.object(policies, "load_checkpoint", return_value=(model, bundle)):
            first, first_identity = policies.load_demo_policy("m4-a", policy_rng_seed=20261103)
            custom, custom_identity = policies.load_demo_policy("m4-a", policy_rng_seed=123456)
        self.assertEqual(first.rng_seed, 20261103)
        self.assertEqual(custom.rng_seed, 123456)
        self.assertEqual(custom_identity.training_seed, policies.M4_TRAINING_SEED)
        self.assertEqual(custom_identity.checkpoint_sha256, first_identity.checkpoint_sha256)
        self.assertEqual(custom_identity.policy_type, first_identity.policy_type)

    def test_m4_a_rejects_wrong_hash_and_immutable_training_metadata(self):
        model = torch.nn.Linear(1, 1)
        valid = {"checkpoint_role": "improvement_m4", "run_id": policies.EXPERIMENT,
            "seed": policies.M4_TRAINING_SEED, "dataset_release_id": policies.M4_DATASET_RELEASE,
            "input_schema": "videochess-model-input/1.0",
            "model_schema": "videochess-behavior-scorer/1.0"}
        with patch.object(policies, "load_checkpoint", return_value=(model, {"metadata": valid})):
            with patch.object(policies, "sha256", return_value="0" * 64):
                with self.assertRaisesRegex(ValueError, "identity mismatch"):
                    policies.load_demo_policy("m4-a")
            with patch.object(policies, "sha256", return_value=policies.M4_SHA256):
                bad = dict(valid, seed=123456)
                with patch.object(policies, "load_checkpoint", return_value=(model, {"metadata": bad})):
                    with self.assertRaisesRegex(ValueError, "training metadata"):
                        policies.load_demo_policy("m4-a", policy_rng_seed=123456)


class DemoPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        config = ALEConfig.deterministic_dev(mode=4)
        self.runtime = {"config": config.as_dict(), "rom_sha256": demo.ROM_SHA256,
            "rom_name": "video_chess.bin",
            "ale_py": "0.11.2", "gymnasium": "1.4.0", "ale_episode_frame_limit": 108000,
            "instance_runtime": {"mode": 4, "difficulty": 0, "frameskip": 1,
                "repeat_action_probability": 0.0, "obs_type": "rgb", "action_count": 10,
                "action_set": list(range(10)), "observation_shape": [210, 160, 3]}}
        self.envs = []

    def env_factory(self, _config):
        env = FakeEnvironment(self.runtime)
        self.envs.append(env)
        return env

    @staticmethod
    def loader(policy, **_kwargs):
        return object(), SimpleNamespace(policy_id=policy, policy_type="q_only",
            checkpoint_sha256="a" * 64, training_seed=20261103, valid_decisions=250000)

    def run_check(self, **overrides):
        args = dict(policy="double-dqn", checkpoint="snapshot.pt", expected_sha256="a" * 64,
            reset_seed=123456, output_root=Path(self.temp.name) / "output", require_display=False,
            env_factory=self.env_factory, policy_loader=self.loader)
        args.update(overrides)
        return run_demo_preflight(**args)

    def test_valid_runtime_rom_model_and_writable_output_pass(self):
        report = self.run_check()
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["atari_reset_seed"], 123456)
        self.assertEqual(report["model_training_seed"], 20261103)
        self.assertTrue(self.envs[0].closed)
        self.assertNotIn("stockfish", {item["name"] for item in report["checks"]})

    def test_missing_checkpoint_and_wrong_checkpoint_hash_are_actionable(self):
        missing = self.run_check(policy_loader=lambda *_a, **_k: (_ for _ in ()).throw(FileNotFoundError("snapshot absent")))
        self.assertFalse(missing["ok"])
        check = next(item for item in missing["checks"] if item["name"] == "policy_checkpoint")
        self.assertIn("FileNotFoundError", check["observed"])
        wrong_hash = self.run_check(policy_loader=lambda *_a, **_k: (_ for _ in ()).throw(ValueError("SHA-256 mismatch")))
        self.assertFalse(wrong_hash["ok"])
        self.assertIn("SHA-256", next(item for item in wrong_hash["checks"] if item["name"] == "policy_checkpoint")["observed"])

    def test_wrong_rom_or_environment_contract_fails(self):
        self.runtime["rom_sha256"] = "0" * 64
        report = self.run_check()
        self.assertFalse(report["ok"])
        self.assertFalse(next(item for item in report["checks"] if item["name"] == "videochess_environment")["ok"])
        self.runtime["rom_sha256"] = demo.ROM_SHA256
        self.runtime["instance_runtime"]["action_count"] = 9
        report = self.run_check()
        self.assertFalse(report["ok"])
        self.assertFalse(next(item for item in report["checks"] if item["name"] == "environment_contract")["ok"])

    def test_missing_display_and_unwritable_output_are_reported(self):
        no_display = self.run_check(environ={}, require_display=True)
        self.assertFalse(no_display["ok"])
        self.assertFalse(next(item for item in no_display["checks"] if item["name"] == "display")["ok"])
        blocker = Path(self.temp.name) / "not-a-directory"
        blocker.write_text("existing")
        bad_output = self.run_check(output_root=blocker / "child")
        self.assertFalse(bad_output["ok"])
        self.assertFalse(next(item for item in bad_output["checks"] if item["name"] == "artifact_output")["ok"])

    def test_symlinked_artifact_output_is_rejected(self):
        with TemporaryDirectory() as temp:
            target = Path(temp) / "target"; target.mkdir()
            link = Path(temp) / "link"; link.symlink_to(target, target_is_directory=True)
            report = self.run_check(output_root=link)
        self.assertFalse(report["ok"])
        self.assertIn("symlink", next(item for item in report["checks"] if item["name"] == "artifact_output")["observed"])

    def test_missing_tk_is_reported_without_making_it_a_module_import_failure(self):
        with patch.dict(sys.modules, {"tkinter": None}):
            report = self.run_check(environ={"DISPLAY": ":fake"}, require_display=True)
        self.assertFalse(report["ok"])
        self.assertFalse(next(item for item in report["checks"] if item["name"] == "tk_display")["ok"])


class DemoLifecycleTests(unittest.TestCase):
    def test_trace_notification_cannot_replace_terminal_reason(self):
        window = object.__new__(LiveDemoWindow)
        window.session_state = DemoSessionState()
        window.status = FakeWidget()
        window.turn_label = FakeWidget()
        window.back_button = FakeWidget()
        window.forward_button = FakeWidget()
        window.replay_label = FakeWidget()
        window.trace_status = FakeWidget()
        window.frames = []
        window.finished = False
        window.finished_status = None
        window.auto_smoke = False
        window.trace_path = None
        window.render_frame = lambda *_args, **_kwargs: None
        window.handle_event({"event": "episode_finished", "status": "partial",
            "failure": "target confirmation uncertain", "terminal": {
                "runner_stop_category": "CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN",
                "runner_stop_reason": "target confirmation uncertain", "ale_terminated": False,
                "ale_truncated": False}, "frame_number": 99})
        original = window.status.options["text"]
        window.handle_event({"event": "trace_saved", "path": "trace.json"})
        self.assertEqual(window.status.options["text"], original)
        self.assertIn("target confirmation uncertain", original)
        self.assertEqual(window.trace_status.options["text"], "Trace: saved")

    def test_final_session_summary_keeps_exact_stop_after_all_worker_events(self):
        window = object.__new__(LiveDemoWindow)
        window.session_state = DemoSessionState()
        window.status = FakeWidget(); window.turn_label = FakeWidget()
        window.back_button = FakeWidget(); window.forward_button = FakeWidget()
        window.replay_label = FakeWidget(); window.trace_status = FakeWidget()
        window.frames = []; window.move_rows = {}; window.move_table = FakeTreeview()
        window.finished = False; window.finished_status = None
        window.auto_smoke = False; window.trace_path = None
        window._worker_terminal_seen = False; window.render_frame = lambda *_args, **_kwargs: None
        terminal = {"runner_stop_category": "CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN",
            "runner_stop_reason": "Target FIRE remained uncertain after bounded settling",
            "ale_terminated": False, "ale_truncated": False}
        window.handle_event({"event": "episode_finished", "status": "partial",
            "failure": terminal["runner_stop_reason"], "terminal": terminal, "frame_number": 100})
        window.handle_event({"event": "trace_saved", "path": "trace.json"})
        window.handle_event({"event": "session_summary", "summary": {
            "outcome": "controller_uncertainty", "runner_stop_category": terminal["runner_stop_category"],
            "runner_stop_reason": terminal["runner_stop_reason"], "replay_diagnostics": []}})
        window.handle_event({"event": "worker_finished", "status": "completed", "replay_available": True})
        text = window.status.options["text"]
        self.assertIn("Controller stopped safely", text)
        self.assertIn(terminal["runner_stop_category"], text)
        self.assertIn(terminal["runner_stop_reason"], text)

    def test_worker_summary_distinguishes_all_stop_classes(self):
        cases = (
            ({"runner_stop_category": "ALE_TERMINATED", "ale_terminated": True}, "ale_game_terminated", "completed"),
            ({"runner_stop_category": "ALE_TRUNCATED", "ale_truncated": True}, "ale_truncated", "completed"),
            ({"runner_stop_category": "RUNNER_MAX_WALL_CLOCK"}, "runner_limit", "completed"),
            ({"runner_stop_category": "CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN"}, "controller_uncertainty", "completed"),
            ({"runner_stop_category": "RUNNER_USER_CANCEL"}, "user_cancelled", "completed"),
            ({"runner_stop_category": "RUNNER_MAX_PLAYER_MOVES"}, "worker_runtime_failure", "failed"),
        )
        for terminal, expected, worker_status in cases:
            with self.subTest(expected=expected):
                summary = demo.build_live_summary({"status": "partial", "terminal": terminal},
                    worker_status=worker_status)
                self.assertEqual(summary["outcome"], expected)

    def test_replay_diagnostics_separate_optional_candidate_warning_and_inconsistency(self):
        with TemporaryDirectory() as temp:
            frames = Path(temp); (frames / "reset.png").write_bytes(b"reset")
            unverified = {"turns": [{"turn": 1,
                "player_move": {"uci": "e2e4", "input_initiated": True, "verified_from_rgb": False},
                "opponent_reply": {"uci": None, "verified_from_rgb": False}}]}
            diagnostics = demo.diagnose_replay_artifacts(unverified, frames)
            self.assertEqual([(item["severity"], item["code"]) for item in diagnostics],
                [("INFO", "REPLAY_UNVERIFIED_CANDIDATE_NOT_PRODUCED")])
            self.assertFalse((frames / "turn-01-player-candidate.png").exists())

            verified = {"turns": [{"turn": 1,
                "player_move": {"uci": "e2e4", "input_initiated": True, "verified_from_rgb": True},
                "opponent_reply": {"uci": "e7e5", "verified_from_rgb": True}}]}
            diagnostics = demo.diagnose_replay_artifacts(verified, frames)
            self.assertEqual({item["severity"] for item in diagnostics}, {"WARNING"})
            self.assertEqual({item["code"] for item in diagnostics}, {
                "REPLAY_PLAYER_FRAME_MISSING", "REPLAY_VERIFIED_REPLY_FRAME_MISSING"})
            self.assertFalse((frames / "turn-01-player-candidate.png").exists())
            self.assertFalse((frames / "turn-01-verified-board.png").exists())

            reached_candidate = {"turns": [{"turn": 1,
                "player_move": {"uci": "e2e4", "input_initiated": True,
                                "verified_from_rgb": False, "candidate_fen": "candidate"},
                "opponent_reply": {"uci": None, "verified_from_rgb": False}}]}
            diagnostics = demo.diagnose_replay_artifacts(reached_candidate, frames)
            self.assertEqual([(item["severity"], item["code"]) for item in diagnostics],
                [("WARNING", "REPLAY_PLAYER_FRAME_MISSING")])

            (frames / "turn-01-verified-board.png").write_bytes(b"unexpected")
            diagnostics = demo.diagnose_replay_artifacts(unverified, frames)
            self.assertIn("REPLAY_BOARD_ARTIFACT_INCONSISTENT", {item["code"] for item in diagnostics})

    def test_terminal_ram_replay_sequence_must_reproduce_legal_checkmate(self):
        import chess
        from videochess_rl.atari_ram import VIDEO_CHESS_ROM_SHA256

        board = chess.Board()
        board.push_uci("f2f3")
        board.push_uci("e7e5")
        terminal = board.copy()
        terminal.push_uci("g2g4")
        terminal.push_uci("d8h4")
        self.assertTrue(terminal.is_checkmate())
        with TemporaryDirectory() as temp:
            frames = Path(temp)
            for name in ("reset", "turn-01-player-candidate", "turn-01-verified-board", "turn-02-player-candidate"):
                (frames / f"{name}.png").write_bytes(name.encode())
            trace = {
                "frames": [{"name": name} for name in (
                    "reset", "turn-01-player-candidate", "turn-01-verified-board",
                    "turn-02-player-candidate",
                )],
                "turns": [
                    {
                        "turn": 1,
                        "player_move": {"uci": "f2f3", "input_initiated": True, "verified_from_rgb": True},
                        "opponent_reply": {"uci": "e7e5", "verified_from_rgb": True},
                    },
                    {
                        "turn": 2,
                        "board_before_fen": board.fen(en_passant="fen"),
                        "player_move": {
                            "uci": "g2g4", "input_initiated": True, "verified_from_rgb": False,
                            "candidate_fen": board.copy(stack=True).fen(en_passant="fen"),
                        },
                        "opponent_reply": {"uci": "d8h4", "verified_from_rgb": False},
                    },
                ],
                "terminal": {"ale_terminated": True, "ale_truncated": False},
                "terminal_sequence_verification": {
                    "verified": True,
                    "rom_sha256": VIDEO_CHESS_ROM_SHA256,
                    "sequence": ["g2g4", "d8h4"],
                    "terminal_fen": terminal.fen(en_passant="fen"),
                    "player_move": "g2g4",
                    "atari_reply": "d8h4",
                    "ale_reward": -1.0,
                },
            }
            diagnostics = demo.diagnose_replay_artifacts(trace, frames)
            self.assertNotIn("REPLAY_TERMINAL_RAM_SEQUENCE_INVALID", {item["code"] for item in diagnostics})
            trace["terminal_sequence_verification"]["terminal_fen"] = chess.Board().fen()
            diagnostics = demo.diagnose_replay_artifacts(trace, frames)
        self.assertIn("REPLAY_TERMINAL_RAM_SEQUENCE_INVALID", {item["code"] for item in diagnostics})

    def test_terminal_ram_replay_requires_explicit_final_player_and_atari_moves(self):
        import chess
        from videochess_rl.atari_ram import VIDEO_CHESS_ROM_SHA256

        before = chess.Board()
        before.push_uci("f2f3")
        before.push_uci("e7e5")
        candidate = before.copy()
        candidate.push_uci("g2g4")
        board = candidate.copy()
        board.push_uci("d8h4")
        with TemporaryDirectory() as temp:
            frames = Path(temp)
            for name in ("reset", "turn-01-player-candidate", "turn-01-verified-board", "turn-02-player-candidate"):
                (frames / f"{name}.png").write_bytes(name.encode())
            trace = {
                "frames": [{"name": name} for name in (
                    "reset", "turn-01-player-candidate", "turn-01-verified-board",
                    "turn-02-player-candidate",
                )],
                "turns": [
                    {
                        "turn": 1,
                        "player_move": {"uci": "f2f3", "input_initiated": True, "verified_from_rgb": True},
                        "opponent_reply": {"uci": "e7e5", "verified_from_rgb": True},
                    },
                    {
                        "turn": 2,
                        "board_before_fen": before.fen(en_passant="fen"),
                        "player_move": {
                            "uci": "g2g4", "input_initiated": True, "verified_from_rgb": False,
                            "candidate_fen": candidate.fen(en_passant="fen"),
                        },
                        "opponent_reply": {"uci": "d8h4", "verified_from_rgb": False},
                    },
                ],
                "terminal": {"ale_terminated": True, "ale_truncated": False},
                "terminal_sequence_verification": {
                    "verified": True,
                    "rom_sha256": VIDEO_CHESS_ROM_SHA256,
                    "sequence": ["g2g4", "d8h4"],
                    "terminal_fen": board.fen(en_passant="fen"),
                    "ale_reward": -1.0,
                },
            }
            diagnostics = demo.diagnose_replay_artifacts(trace, frames)

        self.assertIn("REPLAY_TERMINAL_RAM_SEQUENCE_INVALID", {item["code"] for item in diagnostics})

    def test_malformed_replay_metadata_is_an_error(self):
        with TemporaryDirectory() as temp:
            frames = Path(temp); (frames / "reset.png").write_bytes(b"reset")
            diagnostics = demo.diagnose_replay_artifacts({"turns": ["bad turn"]}, frames)
        self.assertEqual(diagnostics[0]["severity"], "ERROR")
        self.assertEqual(diagnostics[0]["code"], "REPLAY_TURN_INVALID")

    def test_live_summary_file_is_concise_and_machine_readable(self):
        class RecordingViewer:
            frames = []
            def __init__(self): self.events = []
            def publish(self, event): self.events.append(event)
        trace = {"status": "partial", "move_selector": "double-dqn", "seed": 7,
            "turns": [], "terminal": {"runner_stop_category": "CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN",
                "runner_stop_reason": "Target state remained uncertain", "ale_terminated": False,
                "ale_truncated": False, "incomplete_final_move_count": 1,
                "incomplete_final_move_category": "target_confirmation_uncertainty",
                "player_moves_attempted": 1, "verified_player_moves": 0, "verified_atari_replies": 0}}
        with TemporaryDirectory() as temp:
            root = Path(temp); frames = root / "frames"; frames.mkdir()
            (frames / "reset.png").write_bytes(b"reset")
            viewer = RecordingViewer()
            demo.run_demo_worker(viewer, episode_runner=lambda **_kwargs: trace, episode_kwargs={},
                trace_path=root / "trace.json", summary_path=root / "live_summary.json",
                replay_artifact_dir=frames,
                summary_metadata={"policy_id": "double_dqn_250000", "checkpoint_sha256": "a" * 64,
                    "model_training_seed": 20261103, "ale_seed": 7})
            summary = json.loads((root / "live_summary.json").read_text())
        self.assertEqual(summary["runner_stop_category"], "CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN")
        self.assertEqual(summary["runner_stop_reason"], "Target state remained uncertain")
        self.assertEqual(summary["incomplete_final_move_count"], 1)
        self.assertEqual(summary["model_training_seed"], 20261103)
        self.assertEqual(summary["ale_seed"], 7)
        self.assertNotIn("turns", summary)
        self.assertNotIn("actions", summary)
        self.assertNotIn("rgb", summary)
        self.assertIn("session_summary", [event["event"] for event in viewer.events])

    def test_verified_turn_replays_white_candidate_then_atari_reply(self):
        window = object.__new__(LiveDemoWindow)
        window.session_state = DemoSessionState(); window.move_rows = {}
        window.move_table = FakeTreeview(); window.turn_label = FakeWidget(); window.status = FakeWidget()
        window.verified_turns = 0; window.frames = []; window.replay_index = 0
        window.replay_label = FakeWidget(); window.finished = True
        window.render_frame = lambda *_args, **_kwargs: None
        window.record_replay({"event": "reset_verified", "frame_number": 1,
            "fen": "start", "rgb": np.zeros((2, 2, 3), dtype=np.uint8)})
        window.handle_event({"event": "verified_turn", "turn": 1, "player_san": "e4",
            "player_uci": "e2e4", "opponent_san": "e5", "opponent_uci": "e7e5",
            "player_candidate_frame_number": 10, "player_candidate_fen": "after e4",
            "player_candidate_rgb": np.ones((2, 2, 3), dtype=np.uint8),
            "player_move_verified_earlier": False,
            "frame_number": 20, "fen": "after e5", "rgb": np.full((2, 2, 3), 2, dtype=np.uint8)})
        self.assertEqual(len(window.frames), 3)
        self.assertIn("White e4 candidate", window.frames[1]["label"])
        self.assertIn("Atari e5 verified", window.frames[2]["label"])
        window.replay_back()
        self.assertEqual(window.replay_index, 1)
        self.assertIn("White e4 candidate", window.replay_label.options["text"])
        window.replay_forward()
        self.assertEqual(window.replay_index, 2)
        self.assertIn("Atari e5 verified", window.replay_label.options["text"])

    def test_incomplete_selected_move_stays_unverified_and_never_enters_replay(self):
        window = object.__new__(LiveDemoWindow)
        window.session_state = DemoSessionState(); window.move_rows = {}
        window.move_table = FakeTreeview(); window.turn_label = FakeWidget(); window.status = FakeWidget()
        window.frames = []; window.finished = False; window.finished_status = None
        window.back_button = FakeWidget(); window.forward_button = FakeWidget()
        window.replay_label = FakeWidget(); window.trace_status = FakeWidget()
        window.auto_smoke = False; window.trace_path = None
        window.render_frame = lambda *_args, **_kwargs: None
        window.handle_event({"event": "move_selected", "turn": 1, "san": "e4", "uci": "e2e4"})
        window.handle_event({"event": "episode_finished", "status": "partial",
            "failure": "Target confirmation uncertain", "terminal": {
                "runner_stop_category": "CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN",
                "runner_stop_reason": "Target confirmation uncertain", "ale_terminated": False,
                "ale_truncated": False}, "frame_number": 10})
        values = list(window.move_table.rows.values())[0][0]
        self.assertIn("unverified", values[1])
        self.assertNotIn("✓", values[1])
        self.assertEqual(values[2], "—")
        self.assertEqual(window.frames, [])

    def test_worker_error_is_terminal_even_without_episode_or_trace_event(self):
        state = DemoSessionState()
        state.apply({"event": "worker_error", "error_type": "ALEStartupError", "error": "ROM load failed"})
        state.apply({"event": "worker_finished", "status": "failed"})
        self.assertFalse(state.smoke_ok)
        self.assertIn("ALEStartupError", state.display_status)
        self.assertIn("ROM load failed", state.display_status)

    def test_terminal_ram_checkmate_is_labeled_separately_from_rgb_verified_history(self):
        state = DemoSessionState()
        state.apply({
            "event": "episode_finished",
            "status": "ale_terminated",
            "terminal": {
                "ale_terminated": True,
                "ale_truncated": False,
                "white_result_from_reward": "white_loss",
                "runner_stop_category": "ALE_TERMINATED",
            },
            "terminal_sequence_verification": {
                "verified": True,
                "terminal_ram_player_move_count": 1,
                "terminal_ram_atari_reply_count": 1,
            },
        })
        self.assertEqual(state.terminal_ram_verified_player_moves_displayed, 1)
        self.assertEqual(state.terminal_ram_verified_atari_replies_displayed, 1)
        self.assertIn("White loss", state.display_status)
        self.assertIn("checkmate verified from ALE RAM", state.display_status)

    def test_interactive_worker_completion_is_not_gated_by_smoke_contract(self):
        window = object.__new__(LiveDemoWindow)
        window.auto_smoke = False
        window.session_state = DemoSessionState()
        window._worker_terminal_seen = False
        window.exit_code = 0
        window.finished = False
        window.status = FakeWidget()
        window._maybe_start_smoke_replay = lambda: None
        window.handle_event({"event": "worker_finished", "status": "completed", "replay_available": True})
        self.assertTrue(window._worker_terminal_seen)
        self.assertEqual(window.exit_code, 0)
        self.assertIsNone(window.session_state.episode_status)

    def test_close_on_finish_waits_for_worker_completion(self):
        window = object.__new__(LiveDemoWindow)
        window.session_state = DemoSessionState()
        window._worker_terminal_seen = False
        window.exit_code = 0
        window.finished = False
        window.status = FakeWidget()
        window.auto_smoke = False
        window.close_on_finish = True
        window._maybe_start_smoke_replay = lambda: None
        window.handle_event({"event": "worker_finished", "status": "completed", "replay_available": True})
        self.assertTrue(window._worker_terminal_seen)
        self.assertTrue(window.closing)

    def test_successful_bounded_episode_has_trace_and_replay_lifecycle(self):
        state = DemoSessionState(required_player_moves=2)
        state.apply({"event": "verified_turn"}); state.apply({"event": "verified_turn"})
        state.apply({"event": "episode_finished", "status": "runner_stopped", "failure": "player move cap",
                     "terminal": {"runner_stop_category": "RUNNER_MAX_PLAYER_MOVES", "runner_stopped": True,
                         "observed": False, "terminated": False, "truncated": False,
                         "ale_terminated": False, "ale_truncated": False,
                         "runner_stop_reason": "runner stopped after the configured 2 player-move limit",
                         "player_moves_attempted": 2,
                         "verified_player_moves": 2, "verified_atari_replies": 2,
                         "incomplete_final_move_count": 0}})
        state.apply({"event": "trace_saved", "path": "trace.json"})
        state.apply({"event": "worker_finished", "status": "completed", "replay_available": True})
        self.assertTrue(state.smoke_ok)
        self.assertTrue(state.replay_available)
        self.assertIn("player move cap", state.display_status)

    def test_completed_worker_and_saved_trace_do_not_accept_one_turn_uncertainty(self):
        state = DemoSessionState(required_player_moves=2)
        state.apply({"event": "verified_turn"})
        state.apply({"event": "episode_finished", "status": "partial", "failure": "target FIRE uncertain",
                     "terminal": {"runner_stop_category": "CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN",
                         "runner_stopped": True, "ale_terminated": False, "ale_truncated": False,
                         "player_moves_attempted": 2, "verified_player_moves": 1,
                         "verified_atari_replies": 1, "incomplete_final_move_count": 1}})
        state.apply({"event": "trace_saved", "path": "trace.json"})
        state.apply({"event": "worker_finished", "status": "completed", "replay_available": True})
        self.assertFalse(state.smoke_ok)
        self.assertEqual(state.worker_status, "completed")
        self.assertEqual(state.trace_status, "saved")
        self.assertEqual(state.terminal_category, "CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN")

    def test_trace_save_error_does_not_erase_episode_stop_reason(self):
        state = DemoSessionState()
        state.apply({"event": "episode_finished", "status": "partial", "failure": "target was uncertain",
                     "terminal": {"runner_stop_category": "CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN"}})
        state.apply({"event": "trace_save_error", "error_type": "OSError", "error": "disk full"})
        self.assertFalse(state.smoke_ok)
        self.assertIn("disk full", state.display_status)
        self.assertIn("target was uncertain", state.display_status)

    def test_ale_truncation_is_shown_as_incomplete_not_game_result(self):
        window = object.__new__(LiveDemoWindow)
        window.session_state = DemoSessionState()
        window.status = FakeWidget(); window.turn_label = FakeWidget()
        window.back_button = FakeWidget(); window.forward_button = FakeWidget()
        window.replay_label = FakeWidget(); window.trace_status = FakeWidget()
        window.frames = []; window.finished = False; window.finished_status = None
        window.auto_smoke = False; window.trace_path = None
        window.render_frame = lambda *_args, **_kwargs: None
        window.handle_event({"event": "episode_finished", "status": "ale_truncated", "terminal": {
            "ale_terminated": False, "ale_truncated": True, "observed": False,
            "runner_stop_category": "ALE_TRUNCATED"}, "frame_number": 108000})
        self.assertIn("truncated", window.status.options["text"])
        self.assertNotIn("game terminated", window.status.options["text"])

    def test_move_scorecard_marks_pending_move_then_shows_only_verified_pair(self):
        window = object.__new__(LiveDemoWindow)
        window.session_state = DemoSessionState(); window.move_rows = {}
        window.move_table = FakeTreeview(); window.turn_label = FakeWidget(); window.status = FakeWidget()
        window.verified_turns = 0; window.frames = []; window.latest_rgb = None
        window.render_frame = lambda *_args, **_kwargs: None
        window.handle_event({"event": "move_selected", "turn": 1, "san": "e4", "uci": "e2e4"})
        pending = list(window.move_table.rows.values())[0]
        self.assertIn("e4 ?", pending[0][1])
        window.handle_event({"event": "verified_turn", "turn": 1, "player_san": "e4",
            "player_uci": "e2e4", "opponent_san": "e5", "opponent_uci": "e7e5",
            "frame_number": 300, "rgb": None})
        verified = list(window.move_table.rows.values())[0]
        self.assertEqual(verified[0][1:], ("e4 ✓", "e5 ✓"))
        self.assertNotIn("pending", verified[1])
        self.assertEqual(window.session_state.verified_player_moves_displayed, 1)
        self.assertEqual(window.session_state.verified_atari_replies_displayed, 1)

    def test_terminal_ram_checkmate_row_and_terminal_frame_are_labeled_without_a_board_snapshot(self):
        window = object.__new__(LiveDemoWindow)
        window.auto_smoke = False
        window.session_state = DemoSessionState()
        window.move_rows = {14: {"white": "Ke2-f1", "black": "Atari thinking…",
                                 "white_pending": False, "black_pending": True}}
        window.move_table = FakeTreeview()
        window.frames = []
        window.replay_index = 0
        window.finished = False
        window.finished_status = None
        window.trace_path = None
        window.status = FakeWidget()
        window.turn_label = FakeWidget()
        window.back_button = FakeWidget()
        window.forward_button = FakeWidget()
        window.replay_label = FakeWidget()
        window.render_frame = lambda *_args, **_kwargs: None
        terminal_sequence = {
            "verified": True,
            "turn": 14,
            "player_move_san": "Kf1",
            "atari_reply_san": "Qxf2#",
            "terminal_fen": "checkmate-fen",
            "terminal_ram_player_move_count": 1,
            "terminal_ram_atari_reply_count": 1,
            "ale_reward": -1.0,
        }

        window.handle_event({
            "event": "episode_finished",
            "status": "ale_terminated",
            "terminal": {
                "ale_terminated": True,
                "ale_truncated": False,
                "white_result_from_reward": "white_loss",
                "runner_stop_category": "ALE_TERMINATED",
            },
            "terminal_sequence_verification": terminal_sequence,
            "frame_number": 35342,
            "rgb": np.zeros((210, 160, 3), dtype=np.uint8),
        })

        values = list(window.move_table.rows.values())[0][0]
        self.assertIn("terminal RAM", values[1])
        self.assertIn("terminal RAM", values[2])
        self.assertEqual(window.frames[0]["label"], "ALE terminal · -1.0 · no board snapshot")
        self.assertIsNone(window.frames[0].get("fen"))
        self.assertIn("checkmate verified from terminal ALE RAM", window.status.options["text"])
        self.assertEqual(window.session_state.terminal_ram_verified_player_moves_displayed, 1)
        self.assertEqual(window.session_state.terminal_ram_verified_atari_replies_displayed, 1)

    def test_verified_player_counter_is_not_double_counted_at_atari_reply(self):
        state = DemoSessionState()
        state.apply({"event": "player_move_verified", "turn": 1})
        state.apply({"event": "verified_turn", "turn": 1, "player_move_verified_earlier": True})
        self.assertEqual(state.verified_player_moves_displayed, 1)
        self.assertEqual(state.verified_atari_replies_displayed, 1)
        self.assertEqual(state.verified_pairs_displayed, 1)

    def test_worker_failure_sets_automatic_close_without_waiting_for_trace(self):
        window = object.__new__(LiveDemoWindow)
        window.session_state = DemoSessionState()
        window.status = FakeWidget()
        window.back_button = FakeWidget()
        window.forward_button = FakeWidget()
        window.frames = []
        window.finished = False
        window.finished_status = None
        window.exit_code = 1
        window.auto_smoke = True
        window.closing = False
        window._worker_terminal_seen = False
        window._smoke_started = False
        window._maybe_start_smoke_replay = lambda: None
        window.handle_event({"event": "worker_error", "error_type": "RuntimeError", "error": "worker exploded"})
        self.assertTrue(window.closing)
        self.assertEqual(window.exit_code, 1)
        self.assertIn("worker exploded", window.status.options["text"])

    def test_auto_smoke_persists_failure_and_destroys_without_trace(self):
        class DeadWorker:
            @staticmethod
            def is_alive(): return False
        with TemporaryDirectory() as temp:
            window = object.__new__(LiveDemoWindow)
            window.root = FakeRoot(); window.worker = DeadWorker()
            window.status = FakeWidget()
            window.events = queue.Queue(); window.frame_lock = threading.Lock()
            window.latest_frame_event = None; window.closing = True; window.auto_smoke = True
            window.finished = True; window._worker_terminal_seen = True; window._worker_exit_grace = False
            window.session_state = DemoSessionState()
            window.session_state.apply({"event": "worker_error", "error_type": "ROMError", "error": "ROM rejected"})
            window.policy_name = "m4-a"
            window.identity = SimpleNamespace(policy_type="behavior_cloning", training_seed=20261103,
                                               checkpoint_sha256="a" * 64)
            window.demo_seed = 123456; window.max_player_moves = 2
            window.artifact_dir = Path(temp); window.frames = []; window.verified_turns = 0
            window.replay_test = None; window.smoke_resize_checked = False
            window.layout_check = None; window.finished_status = "worker_failed"
            window.trace_path = None; window.exit_code = 1; window.session_limits = {}
            window.latest_rgb = None
            window.poll()
            record = json.loads((Path(temp) / "demo-verification.json").read_text())
        self.assertTrue(window.root.destroyed)
        self.assertEqual(record["exit_code"], 1)
        self.assertIn("ROM rejected", record["session_state"]["worker_error"])
        self.assertIsNone(record["trace_path"])

    def test_unexpected_worker_death_after_episode_event_still_closes_smoke(self):
        class DeadWorker:
            @staticmethod
            def is_alive(): return False
        with TemporaryDirectory() as temp:
            window = object.__new__(LiveDemoWindow)
            window.root = FakeRoot(); window.worker = DeadWorker()
            window.status = FakeWidget()
            window.events = queue.Queue(); window.frame_lock = threading.Lock()
            window.latest_frame_event = None; window.closing = False; window.auto_smoke = True
            window.finished = True; window._worker_terminal_seen = False; window._worker_exit_grace = False
            window.session_state = DemoSessionState()
            window.session_state.apply({"event": "episode_finished", "status": "partial",
                "failure": "controller stopped", "terminal": {"runner_stop_category": "CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN"}})
            window.policy_name = "m4-a"
            window.identity = SimpleNamespace(policy_type="behavior_cloning", training_seed=20261103,
                                               checkpoint_sha256="a" * 64)
            window.demo_seed = 123456; window.max_player_moves = 2
            window.artifact_dir = Path(temp); window.frames = []; window.verified_turns = 0
            window.replay_test = None; window.smoke_resize_checked = False
            window.layout_check = None; window.finished_status = "partial"
            window.trace_path = None; window.exit_code = 1; window.session_limits = {}
            window.latest_rgb = None
            window.poll()
            self.assertFalse(window.root.destroyed)
            window.poll()
            record = json.loads((Path(temp) / "demo-verification.json").read_text())
        self.assertTrue(window.root.destroyed)
        self.assertEqual(record["session_state"]["worker_error_type"], "UnexpectedWorkerExit")
        self.assertIn("controller stopped", record["session_state"]["primary_reason"])

    def test_final_worker_events_published_after_queue_drain_get_one_grace_poll(self):
        class RacingWorker:
            def __init__(self, events): self.events = events; self.published = False
            def is_alive(self):
                if not self.published:
                    self.published = True
                    self.events.put({"event": "worker_error", "error_type": "FrameError", "error": "late frame error"})
                    self.events.put({"event": "worker_finished", "status": "failed"})
                return False
        with TemporaryDirectory() as temp:
            window = object.__new__(LiveDemoWindow)
            window.root = FakeRoot(); window.events = queue.Queue()
            window.worker = RacingWorker(window.events); window.frame_lock = threading.Lock()
            window.latest_frame_event = None; window.closing = False; window.auto_smoke = True
            window.finished = False; window._worker_terminal_seen = False; window._worker_exit_grace = False
            window.session_state = DemoSessionState(); window.status = FakeWidget()
            window.back_button = FakeWidget(); window.forward_button = FakeWidget()
            window.policy_name = "m4-a"
            window.identity = SimpleNamespace(policy_type="behavior_cloning", training_seed=20261103,
                                               checkpoint_sha256="a" * 64)
            window.demo_seed = 123456; window.max_player_moves = 2
            window.artifact_dir = Path(temp); window.frames = []; window.verified_turns = 0
            window.replay_test = None; window.smoke_resize_checked = False; window.layout_check = None
            window.finished_status = None; window.trace_path = None; window.exit_code = 1
            window.session_limits = {}; window.latest_rgb = None
            window._maybe_start_smoke_replay = lambda: None
            window.poll()
            self.assertFalse(window.root.destroyed)
            self.assertTrue(window.root.callbacks)
            window.poll()
            record = json.loads((Path(temp) / "demo-verification.json").read_text())
        self.assertTrue(window.root.destroyed)
        self.assertEqual(record["session_state"]["worker_error_type"], "FrameError")
        self.assertEqual(record["session_state"]["worker_error"], "late frame error")

    def test_worker_failures_at_setup_reset_policy_and_frame_stages_are_terminal(self):
        class RecordingViewer:
            frames = []
            def __init__(self): self.events = []
            def publish(self, event): self.events.append(event)

        for failure_type in ("EnvironmentConstructionError", "ROMVerificationError",
                             "EnvironmentResetError", "PolicyExecutionError", "FrameAcquisitionError"):
            viewer = RecordingViewer()
            def raise_stage(**_kwargs):
                raise RuntimeError(f"{failure_type}: injected")
            demo.run_demo_worker(viewer, episode_runner=raise_stage, episode_kwargs={},
                                 trace_path=Path("not-written.json"))
            self.assertEqual(viewer.events[-1]["event"], "worker_finished")
            self.assertEqual(viewer.events[-1]["status"], "failed")
            error = next(event for event in viewer.events if event["event"] == "worker_error")
            self.assertIn(failure_type, error["error"])
            self.assertIn("Traceback", error["traceback"])
            self.assertNotIn("trace_saved", [event["event"] for event in viewer.events])

    def test_trace_writer_failure_is_nonzero_lifecycle_not_false_success(self):
        class RecordingViewer:
            frames = []
            def __init__(self): self.events = []
            def publish(self, event): self.events.append(event)
        viewer = RecordingViewer()
        def fail_write(_path, _trace): raise OSError("disk full")
        demo.run_demo_worker(viewer, episode_runner=lambda **_kwargs: {"status": "runner_stopped"},
            episode_kwargs={}, trace_path=Path("trace.json"), trace_writer=fail_write)
        kinds = [event["event"] for event in viewer.events]
        self.assertEqual(kinds, ["trace_save_error", "worker_error", "worker_finished"])
        self.assertEqual(viewer.events[-1]["status"], "failed")
        self.assertIn("disk full", viewer.events[1]["error"])

    def test_early_rom_mismatch_emits_one_terminal_event_and_closes_environment(self):
        config = ALEConfig.deterministic_dev(mode=4)
        class FakeEpisodeEnvironment:
            closed = False
            def __init__(self, _config): pass
            def __enter__(self): return self
            def __exit__(self, *_args): self.closed = True
            def reset(self, *, seed=None):
                return ALEFrame(np.zeros((210, 160, 3), dtype=np.uint8), 0.0, False, False, {}, 0)
            def runtime_info(self): return {"config": config.as_dict(), "rom_sha256": "0" * 64}
            def diagnostic_ram(self, _addresses): return {}
        envs = []
        def factory(cfg):
            env = FakeEpisodeEnvironment(cfg)
            envs.append(env)
            return env
        events = []
        trace = run_episode(config=config, seed=17, expected_rom_sha256="a" * 64,
            max_player_moves=1, progress_callback=events.append, env_factory=factory)
        self.assertEqual(trace["terminal"]["runner_stop_category"], "ENVIRONMENT_PROFILE_MISMATCH")
        terminals = [event for event in events if event["event"] == "episode_finished"]
        self.assertEqual(len(terminals), 1)
        self.assertFalse(terminals[0]["terminal"]["observed"])
        self.assertTrue(envs[0].closed)


def smoke_fixture(*, players=2, replies=2, category="RUNNER_MAX_PLAYER_MOVES",
                  status="runner_stopped", ale_terminated=False, ale_truncated=False,
                  worker_status="completed", trace_status="saved", gui_players=None,
                  gui_replies=None, pending=0, terminal_present=True):
    turns = []
    for index in range(max(players + pending, replies)):
        turns.append({"player_move": {"uci": "e2e4", "verified_from_rgb": index < players,
                                       "input_initiated": True},
                      "opponent_reply": {"uci": "e7e5", "verified_from_rgb": index < replies}})
    terminal = {"player_moves_attempted": max(players + pending, 0),
        "verified_player_moves": players, "verified_atari_replies": replies,
        "incomplete_final_move_count": pending, "runner_stopped": not (ale_terminated or ale_truncated),
        "observed": ale_terminated or ale_truncated,
        "terminated": ale_terminated, "truncated": ale_truncated,
        "ale_terminated": ale_terminated, "ale_truncated": ale_truncated,
        "runner_stop_category": category,
        "runner_stop_reason": "runner stopped after the configured 2 player-move limit"
            if category == "RUNNER_MAX_PLAYER_MOVES" else "injected stop reason"}
    trace = {"status": status, "terminal": terminal if terminal_present else None, "turns": turns,
             "episode_budget": {"max_player_moves": 2}}
    event_terminal = dict(terminal) if terminal_present else None
    gplayers = players if gui_players is None else gui_players
    greplies = replies if gui_replies is None else gui_replies
    verification = {"window_created": True, "requested_player_moves": 2,
        "verified_atari_turns_displayed": min(gplayers, greplies),
        "verified_player_moves_displayed": gplayers, "verified_atari_replies_displayed": greplies,
        "captured_verified_state_count": gplayers + 1, "gui_checks_ok": True,
        "pending_player_actions": pending,
        "episode_status": status, "episode_terminal": event_terminal,
        "resized_1100x680": True, "layout_check": {"ok": True},
        "replay_test": {"left_moved_backward": True, "right_moved_forward": True},
        "replay_available": True, "trace_path": "trace.json", "exit_code": 0,
        "session_state": {"worker_status": worker_status, "trace_status": trace_status,
                          "trace_path": "trace.json", "worker_error": None,
                          "episode_status": status, "episode_terminal": event_terminal,
                          "verified_pairs_displayed": min(gplayers, greplies),
                          "verified_player_moves_displayed": gplayers,
                          "verified_atari_replies_displayed": greplies,
                          "required_player_moves": 2}}
    return trace, verification


class AutoSmokeAcceptanceTests(unittest.TestCase):
    def assert_verdict(self, trace, verification, expected, *failure_codes):
        result = demo.verify_auto_smoke(trace, verification, requested_player_moves=2)
        self.assertEqual(result["verdict"], expected, result)
        codes = {failure["code"] for failure in result["failures"]}
        for code in failure_codes:
            self.assertIn(code, codes, result)
        return result

    def test_a_valid_two_move_bounded_smoke_passes(self):
        trace, verification = smoke_fixture()
        result = self.assert_verdict(trace, verification, "SMOKE_PASS")
        self.assertEqual((result["verified_player_moves"], result["verified_atari_replies"]), (2, 2))

    def test_b_original_one_turn_then_target_uncertainty_is_incomplete(self):
        trace, verification = smoke_fixture(players=1, replies=1,
            category="CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN", status="partial", pending=1)
        result = self.assert_verdict(trace, verification, "SMOKE_INCOMPLETE", "required_move_count_not_met",
                                     "unexpected_episode_status", "unexpected_stop_category")
        self.assertIn("CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN", result["terminal_category"])

    def test_c_two_player_moves_but_one_reply_fails(self):
        trace, verification = smoke_fixture(players=2, replies=1,
            category="OPPONENT_RESPONSE_TIMEOUT", status="partial")
        self.assert_verdict(trace, verification, "SMOKE_INCOMPLETE", "required_move_count_not_met",
                            "unpaired_trace_moves", "unexpected_stop_category")

    def test_d_unconfirmed_pending_second_player_move_fails(self):
        trace, verification = smoke_fixture(players=1, replies=1,
            category="CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN", status="partial", pending=1)
        self.assert_verdict(trace, verification, "SMOKE_INCOMPLETE", "pending_move",
                            "required_move_count_not_met")

    def test_e_abnormal_controller_stop_fails_even_with_sufficient_counts(self):
        trace, verification = smoke_fixture(category="CONTROLLER_BOARD_DESYNCHRONIZED", status="partial")
        self.assert_verdict(trace, verification, "SMOKE_INCOMPLETE", "unexpected_episode_status",
                            "unexpected_stop_category")

    def test_f_trace_and_gui_count_disagreement_is_runtime_failure(self):
        trace, verification = smoke_fixture(gui_replies=1)
        self.assert_verdict(trace, verification, "SMOKE_RUNTIME_FAILURE", "gui_trace_count_mismatch")

    def test_g_missing_terminal_is_controlled_runtime_failure(self):
        trace, verification = smoke_fixture(terminal_present=False)
        result = self.assert_verdict(trace, verification, "SMOKE_RUNTIME_FAILURE", "terminal_missing")
        self.assertIn("terminal", result["failures"][0]["message"])
        trace, verification = smoke_fixture()
        trace["terminal"] = ["malformed"]
        self.assert_verdict(trace, verification, "SMOKE_RUNTIME_FAILURE", "terminal_missing")
        trace, verification = smoke_fixture()
        trace["terminal"].pop("runner_stop_reason", None)
        verification["episode_terminal"].pop("runner_stop_reason", None)
        verification["session_state"]["episode_terminal"].pop("runner_stop_reason", None)
        self.assert_verdict(trace, verification, "SMOKE_RUNTIME_FAILURE", "stop_reason_missing")

    def test_h_worker_and_trace_failures_are_runtime_failures(self):
        trace, verification = smoke_fixture(worker_status="failed", trace_status="failed")
        self.assert_verdict(trace, verification, "SMOKE_RUNTIME_FAILURE", "worker_not_completed",
                            "trace_not_saved")
        trace, verification = smoke_fixture()
        verification["session_state"]["worker_error"] = "injected worker exception"
        self.assert_verdict(trace, verification, "SMOKE_RUNTIME_FAILURE", "worker_error")

    def test_i_timeout_and_ale_truncation_fail_with_actual_reason(self):
        trace, verification = smoke_fixture(players=1, replies=1, category="RUNNER_MAX_WALL_CLOCK",
                                            status="runner_stopped", pending=1)
        self.assert_verdict(trace, verification, "SMOKE_INCOMPLETE", "unexpected_stop_category")
        trace, verification = smoke_fixture(category="ALE_TRUNCATED", status="ale_truncated",
                                            ale_truncated=True)
        self.assert_verdict(trace, verification, "SMOKE_INCOMPLETE", "ale_truncated")
        trace, verification = smoke_fixture(category="ALE_TERMINATED", status="ale_terminated",
                                            ale_terminated=True)
        self.assert_verdict(trace, verification, "SMOKE_INCOMPLETE", "ale_terminated_early")

    def test_j_replay_and_layout_failures_prevent_success(self):
        trace, verification = smoke_fixture()
        verification["replay_test"]["right_moved_forward"] = False
        self.assert_verdict(trace, verification, "SMOKE_RUNTIME_FAILURE", "replay_failed")
        trace, verification = smoke_fixture()
        verification["layout_check"]["ok"] = False
        self.assert_verdict(trace, verification, "SMOKE_RUNTIME_FAILURE", "layout_failed")

    def test_replay_metadata_error_prevents_smoke_acceptance(self):
        trace, verification = smoke_fixture()
        verification["session_state"]["replay_diagnostics"] = [{
            "severity": "ERROR", "code": "REPLAY_BOARD_ARTIFACT_INCONSISTENT",
            "message": "test fixture inconsistency"}]
        self.assert_verdict(trace, verification, "SMOKE_RUNTIME_FAILURE", "replay_artifact_inconsistent")

    def test_k_saved_trace_and_replay_do_not_accept_incomplete_exercise(self):
        trace, verification = smoke_fixture(players=1, replies=1, category="RUNNER_MAX_WALL_CLOCK",
                                            status="runner_stopped", pending=1)
        result = self.assert_verdict(trace, verification, "SMOKE_INCOMPLETE", "required_move_count_not_met")
        self.assertEqual(result["trace_status"], "saved")
        self.assertTrue(result["replay_available"])

    def test_terminal_event_must_match_trace_terminal_counts_and_category(self):
        trace, verification = smoke_fixture()
        verification["episode_terminal"]["verified_atari_replies"] = 1
        self.assert_verdict(trace, verification, "SMOKE_RUNTIME_FAILURE", "gui_trace_terminal_mismatch")

    def test_extra_unattempted_trace_turn_cannot_be_ignored(self):
        trace, verification = smoke_fixture()
        trace["turns"].append({"player_move": {"input_initiated": False, "verified_from_rgb": False},
                               "opponent_reply": {"verified_from_rgb": False}})
        self.assert_verdict(trace, verification, "SMOKE_RUNTIME_FAILURE", "extra_trace_turns")

    def test_cli_exit_and_verification_artifact_reject_one_turn_controller_failure(self):
        trace_fixture, verification_fixture = smoke_fixture(players=1, replies=1,
            category="CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN", status="partial", pending=1)
        class FakeWindow:
            def __init__(self, **kwargs):
                self.artifact_dir = kwargs["artifact_dir"]
            def start(self):
                (self.artifact_dir / "trace.json").write_text(json.dumps(trace_fixture))
                (self.artifact_dir / "demo-verification.json").write_text(json.dumps(verification_fixture))
                return 0  # Reproduce the old false-positive GUI-side exit.
        identity = SimpleNamespace(policy_id="test-q", policy_type="double_dqn_q_only",
                                   training_seed=20261103, checkpoint_sha256="a" * 64)
        with TemporaryDirectory() as temp, patch.object(demo, "ARTIFACTS", Path(temp)), \
             patch("videochess_rl.improvement.preflight.run_demo_preflight", return_value={"ok": True, "checks": []}), \
             patch.object(policies, "load_demo_policy", return_value=(object(), identity)), \
             patch("videochess_rl.improvement.live.LiveDemoWindow", FakeWindow):
            code = demo.main(["--policy", "double-dqn", "--checkpoint", "snapshot.pt",
                              "--checkpoint-sha256", "a" * 64, "--auto-smoke"])
            records = list(Path(temp).glob("live-demo/*/demo-verification.json"))
            self.assertEqual(len(records), 1)
            record = json.loads(records[0].read_text())
            old_trace = json.loads((records[0].parent / "trace.json").read_text())
            old_predicate = (verification_fixture["window_created"] and verification_fixture["resized_1100x680"]
                and verification_fixture["layout_check"]["ok"]
                and verification_fixture["replay_test"]["left_moved_backward"]
                and verification_fixture["replay_test"]["right_moved_forward"]
                and verification_fixture["verified_atari_turns_displayed"] >= 1
                and old_trace["terminal"]["verified_atari_replies"] >= 1
                and verification_fixture["session_state"]["worker_status"] == "completed")
            self.assertTrue(old_predicate, "fixture must reproduce the previous permissive acceptance")
        self.assertEqual(code, 2)
        self.assertEqual(record["smoke_verdict"], "SMOKE_INCOMPLETE")
        self.assertEqual(record["exit_code"], code)
        self.assertEqual(record["authoritative_verification"]["verified_player_moves"], 1)
        self.assertEqual(record["authoritative_verification"]["terminal_category"],
                         "CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN")

    def test_cli_exit_and_verification_artifact_accept_valid_two_move_run(self):
        class FakeWindow:
            def __init__(self, **kwargs): self.artifact_dir = kwargs["artifact_dir"]
            def start(self):
                trace, verification = smoke_fixture()
                (self.artifact_dir / "trace.json").write_text(json.dumps(trace))
                (self.artifact_dir / "demo-verification.json").write_text(json.dumps(verification))
                return 0
        identity = SimpleNamespace(policy_id="test-m4", policy_type="behavior_cloning",
                                   training_seed=20261103, checkpoint_sha256="b" * 64)
        with TemporaryDirectory() as temp, patch.object(demo, "ARTIFACTS", Path(temp)), \
             patch("videochess_rl.improvement.preflight.run_demo_preflight", return_value={"ok": True, "checks": []}), \
             patch.object(policies, "load_demo_policy", return_value=(object(), identity)), \
             patch("videochess_rl.improvement.live.LiveDemoWindow", FakeWindow):
            code = demo.main(["--policy", "m4-a", "--auto-smoke"])
            records = list(Path(temp).glob("live-demo/*/demo-verification.json"))
            record = json.loads(records[0].read_text())
        self.assertEqual(code, 0)
        self.assertEqual(record["smoke_verdict"], "SMOKE_PASS")
        self.assertEqual(record["exit_code"], 0)

    def test_cli_missing_trace_is_recorded_as_runtime_failure(self):
        _, verification_fixture = smoke_fixture()
        class FakeWindow:
            def __init__(self, **kwargs): self.artifact_dir = kwargs["artifact_dir"]
            def start(self):
                (self.artifact_dir / "demo-verification.json").write_text(json.dumps(verification_fixture))
                return 0
        identity = SimpleNamespace(policy_id="test-m4", policy_type="behavior_cloning",
                                   training_seed=20261103, checkpoint_sha256="b" * 64)
        with TemporaryDirectory() as temp, patch.object(demo, "ARTIFACTS", Path(temp)), \
             patch("videochess_rl.improvement.preflight.run_demo_preflight", return_value={"ok": True, "checks": []}), \
             patch.object(policies, "load_demo_policy", return_value=(object(), identity)), \
             patch("videochess_rl.improvement.live.LiveDemoWindow", FakeWindow):
            code = demo.main(["--policy", "m4-a", "--auto-smoke"])
            records = list(Path(temp).glob("live-demo/*/demo-verification.json"))
            record = json.loads(records[0].read_text())
        self.assertEqual(code, 4)
        self.assertEqual(record["smoke_verdict"], "SMOKE_RUNTIME_FAILURE")
        self.assertIn("invalid_episode_trace", {row["code"] for row in record["smoke_failures"]})

    def test_cli_gui_initialization_exception_is_persisted_and_nonzero(self):
        class BrokenWindow:
            def __init__(self, **_kwargs): raise RuntimeError("injected Tk creation failure")
        identity = SimpleNamespace(policy_id="test-m4", policy_type="behavior_cloning",
                                   training_seed=20261103, checkpoint_sha256="b" * 64)
        with TemporaryDirectory() as temp, patch.object(demo, "ARTIFACTS", Path(temp)), \
             patch("videochess_rl.improvement.preflight.run_demo_preflight", return_value={"ok": True, "checks": []}), \
             patch.object(policies, "load_demo_policy", return_value=(object(), identity)), \
             patch("videochess_rl.improvement.live.LiveDemoWindow", BrokenWindow):
            code = demo.main(["--policy", "m4-a", "--auto-smoke"])
            records = list(Path(temp).glob("live-demo/*/demo-verification.json"))
            record = json.loads(records[0].read_text())
        self.assertEqual(code, 5)
        self.assertEqual(record["smoke_verdict"], "SMOKE_RUNTIME_FAILURE")
        self.assertIn("injected Tk creation failure", record["smoke_failures"][0]["message"])


class DemoArtifactDirectoryTests(unittest.TestCase):
    def test_rapid_and_concurrent_sessions_never_collide(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            now = datetime(2026, 11, 3, tzinfo=timezone.utc)
            with ThreadPoolExecutor(max_workers=8) as pool:
                paths = list(pool.map(lambda _: demo.allocate_session_artifact_dir(root, "m4-a", now=now), range(24)))
            self.assertEqual(len(set(paths)), 24)
            self.assertTrue(all(path.is_dir() for path in paths))
            self.assertTrue(all(not list(path.iterdir()) for path in paths))

    def test_collision_does_not_overwrite_existing_session(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            now = datetime(2026, 11, 3, tzinfo=timezone.utc)
            base = now.strftime("%Y%m%dT%H%M%S.%fZ")
            existing = root / f"{base}-double-dqn-fixed"
            existing.mkdir()
            sentinel = existing / "trace.json"
            sentinel.write_text("preserve")
            values = iter(("fixed", "next"))
            created = demo.allocate_session_artifact_dir(root, "double-dqn", now=now,
                token_factory=lambda: next(values))
            self.assertNotEqual(created, existing)
            self.assertEqual(sentinel.read_text(), "preserve")

    def test_symlinked_session_root_is_rejected(self):
        with TemporaryDirectory() as temp:
            target = Path(temp) / "target"; target.mkdir()
            link = Path(temp) / "link"; link.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                demo.allocate_session_artifact_dir(link, "m4-a")


if __name__ == "__main__":
    unittest.main()
