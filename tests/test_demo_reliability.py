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

    def test_worker_error_is_terminal_even_without_episode_or_trace_event(self):
        state = DemoSessionState()
        state.apply({"event": "worker_error", "error_type": "ALEStartupError", "error": "ROM load failed"})
        state.apply({"event": "worker_finished", "status": "failed"})
        self.assertFalse(state.smoke_ok)
        self.assertIn("ALEStartupError", state.display_status)
        self.assertIn("ROM load failed", state.display_status)

    def test_successful_bounded_episode_has_trace_and_replay_lifecycle(self):
        state = DemoSessionState()
        state.apply({"event": "episode_finished", "status": "runner_stopped", "failure": "player move cap",
                     "terminal": {"runner_stop_category": "RUNNER_MAX_PLAYER_MOVES"}})
        state.apply({"event": "trace_saved", "path": "trace.json"})
        state.apply({"event": "worker_finished", "status": "completed", "replay_available": True})
        self.assertTrue(state.smoke_ok)
        self.assertTrue(state.replay_available)
        self.assertIn("player move cap", state.display_status)

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
