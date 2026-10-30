from __future__ import annotations

import ast
import hashlib
import importlib.util
import random
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
import torch

from test_m5_transition import make_transition
from videochess_rl.rl.checkpoint import restore_training_checkpoint, save_training_checkpoint
from videochess_rl.rl.network import make_scratch_scorer
from videochess_rl.rl.replay import ReplayBuffer, ReplayJournal
from videochess_rl.rl.training import DoubleDqnLearner


ROOT = Path(__file__).resolve().parents[1]
RECOVERED = ROOT / ".agents/evidence/M5-source-recovered"
RECOVERY_RECORD = ROOT / ".agents/evidence/M5-source-recovery-20261030.json"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load recovered source: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _class_methods(source: str, class_name: str) -> dict[str, ast.AST]:
    module = ast.parse(source)
    cls = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    return {node.name: node for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _top_level_functions(source: str) -> dict[str, ast.AST]:
    module = ast.parse(source)
    return {node.name: node for node in module.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _top_level_classes(source: str) -> dict[str, ast.AST]:
    module = ast.parse(source)
    return {node.name: node for node in module.body if isinstance(node, ast.ClassDef)}


def _tree_equal(left, right) -> bool:
    if isinstance(left, torch.Tensor) and isinstance(right, torch.Tensor):
        return torch.equal(left, right)
    if isinstance(left, np.ndarray) and isinstance(right, np.ndarray):
        return np.array_equal(left, right)
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_tree_equal(left[k], right[k]) for k in left)
    if isinstance(left, (tuple, list)):
        return len(left) == len(right) and all(_tree_equal(a, b) for a, b in zip(left, right))
    return left == right


def _numpy_rng_state():
    state = np.random.get_state()
    return state[0], state[1].copy(), state[2], state[3], state[4]


class M5RecoveredSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        record = __import__("json").loads(RECOVERY_RECORD.read_text())
        rows = {Path(item["path"]).name: item for item in record["extractions"]}
        for filename in ("checkpoint.py", "replay.py"):
            path = RECOVERED / filename
            meta = rows[filename]
            if len(path.read_bytes()) != meta["bytes"]:
                raise AssertionError(f"recovered source size changed: {filename}")
            if hashlib.sha256(path.read_bytes()).hexdigest() != meta["sha256"]:
                raise AssertionError(f"recovered source hash changed: {filename}")
        cls.old_replay = _load_module("videochess_rl.rl._m5_recovered_replay", RECOVERED / "replay.py")
        cls.old_checkpoint = _load_module("videochess_rl.rl._m5_recovered_checkpoint", RECOVERED / "checkpoint.py")
        cls.old_checkpoint.ReplayBuffer = cls.old_replay.ReplayBuffer
        cls.old_checkpoint.ReplayJournal = cls.old_replay.ReplayJournal

    def test_replay_buffer_and_append_operations_are_ast_identical(self) -> None:
        old_source = (RECOVERED / "replay.py").read_text()
        new_source = (ROOT / "videochess_rl/rl/replay.py").read_text()
        old_classes, new_classes = _top_level_classes(old_source), _top_level_classes(new_source)
        self.assertEqual(ast.dump(old_classes["ReplayBuffer"], include_attributes=False),
                         ast.dump(new_classes["ReplayBuffer"], include_attributes=False))
        old_journal = _class_methods(old_source, "ReplayJournal")
        new_journal = _class_methods(new_source, "ReplayJournal")
        changed = {name for name in old_journal.keys() & new_journal.keys()
                   if ast.dump(old_journal[name], include_attributes=False)
                   != ast.dump(new_journal[name], include_attributes=False)}
        self.assertEqual(changed, {"__init__", "verify"})
        old = _class_methods(old_source, "ReplayBuffer")
        new = _class_methods(new_source, "ReplayBuffer")
        for name in ("__init__", "__len__", "transitions", "insert", "sample", "state_dict", "from_state_dict"):
            self.assertEqual(ast.dump(old[name], include_attributes=False), ast.dump(new[name], include_attributes=False), name)
        self.assertEqual(ast.dump(old_journal["append"], include_attributes=False),
                         ast.dump(new_journal["append"], include_attributes=False))

    def test_checkpoint_source_diff_is_confined_to_verification_and_restore(self) -> None:
        old = _top_level_functions((RECOVERED / "checkpoint.py").read_text())
        new = _top_level_functions((ROOT / "videochess_rl/rl/checkpoint.py").read_text())
        changed = {name for name in old.keys() & new.keys()
                   if ast.dump(old[name], include_attributes=False) != ast.dump(new[name], include_attributes=False)}
        self.assertEqual(changed, {"verify_training_checkpoint", "restore_training_checkpoint"})

    def test_old_and_current_replay_sampling_preserve_identity_and_rng_state(self) -> None:
        rows = []
        identities = set()
        for seed in range(101, 301):
            row = make_transition(seed)
            if row.transition_id not in identities:
                identities.add(row.transition_id)
                rows.append(row)
            if len(rows) == 10:
                break
        self.assertEqual(len(rows), 10)
        old = self.old_replay.ReplayBuffer(6, seed=8421)
        current = ReplayBuffer(6, seed=8421)
        for row in rows:
            old.insert(row)
            current.insert(row)
        self.assertEqual([row.transition_id for row in old.transitions],
                         [row.transition_id for row in current.transitions])
        self.assertEqual(old.state_dict(), current.state_dict())
        for batch_size in (1, 4, 6):
            old_sample = [row.transition_id for row in old.sample(batch_size)]
            current_sample = [row.transition_id for row in current.sample(batch_size)]
            self.assertEqual(old_sample, current_sample)
            self.assertEqual(old.rng.getstate(), current.rng.getstate())

    def test_old_and_current_journal_verification_return_the_same_records_and_tail(self) -> None:
        rows = [make_transition(i) for i in range(201, 211)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replay.journal.jsonl"
            current_journal = ReplayJournal(path)
            for row in rows:
                head = current_journal.append(row)
            old_journal = self.old_replay.ReplayJournal(path, verify_existing=False)
            old_rows = old_journal.verify(record_count=head["record_count"], chain_sha256=head["chain_sha256"])
            current_rows = current_journal.verify(record_count=head["record_count"], chain_sha256=head["chain_sha256"])
            tail = current_journal.verify(record_count=head["record_count"], chain_sha256=head["chain_sha256"], retain_last=4)
            self.assertEqual([row.transition_id for row in old_rows], [row.transition_id for row in current_rows])
            self.assertEqual([row.transition_id for row in old_rows[-4:]], [row.transition_id for row in tail])

    def test_old_and_current_checkpoint_restore_produce_equal_state_and_next_rng_draws(self) -> None:
        config = {"replay_capacity": 4, "replay_warmup_transitions": 2, "batch_size": 2,
                  "learning_rate": 1e-4, "weight_decay": 1e-4, "update_interval_decisions": 4,
                  "gamma": .99, "target_sync_interval_gradient_updates": 500, "gradient_clip_norm": 1.0}
        rows = [make_transition(i) for i in range(301, 307)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            journal = ReplayJournal(root / "replay.journal.jsonl")
            source = DoubleDqnLearner(make_scratch_scorer(representation_seed=5, q_head_seed=6), seed=7,
                                      exploration_seed=8, config=config)
            for row in rows:
                source.replay.insert(row)
                head = journal.append(row)
            source.valid_decisions = source.transitions = len(rows)
            source.completed_episodes = 2
            source.exploration_rng.random()
            random.random()
            np.random.random()
            torch.rand(1)
            for parameter in source.online.parameters():
                parameter.grad = torch.full_like(parameter, .001)
            source.optimizer.step()
            source.optimizer.zero_grad(set_to_none=True)
            source.optimizer_updates = 1
            checkpoint = root / "resume.pt"
            save_training_checkpoint(
                checkpoint,
                source,
                identity={"experiment_id": "test", "pair_id": "pair", "arm": "scratch",
                          "training_seed": 20261104, "config_sha256": "fixture", "code_sha256": "fixture"},
                journal=journal,
                journal_head=head,
                episode_complete=True,
                resource_accounting={},
            )

            def fresh_learner():
                return DoubleDqnLearner(make_scratch_scorer(representation_seed=50, q_head_seed=60), seed=70,
                                         exploration_seed=80, config=config)

            old_learner = fresh_learner()
            current_learner = fresh_learner()
            old_result = self.old_checkpoint.restore_training_checkpoint(checkpoint, old_learner)
            old_global = (random.getstate(), _numpy_rng_state(), torch.get_rng_state().clone())
            current_result = restore_training_checkpoint(checkpoint, current_learner)
            current_global = (random.getstate(), _numpy_rng_state(), torch.get_rng_state().clone())

            self.assertEqual(old_result["identity"], current_result["identity"])
            self.assertEqual(old_result["counters"], current_result["counters"])
            self.assertEqual([row.transition_id for row in old_learner.replay.transitions],
                             [row.transition_id for row in current_learner.replay.transitions])
            self.assertEqual(old_learner.replay.rng.getstate(), current_learner.replay.rng.getstate())
            self.assertEqual(old_learner.exploration_rng.getstate(), current_learner.exploration_rng.getstate())
            self.assertTrue(_tree_equal(old_learner.online.state_dict(), current_learner.online.state_dict()))
            self.assertTrue(_tree_equal(old_learner.target.state_dict(), current_learner.target.state_dict()))
            self.assertTrue(_tree_equal(old_learner.optimizer.state_dict(), current_learner.optimizer.state_dict()))
            self.assertTrue(_tree_equal(old_global, current_global))
            self.assertEqual([row.transition_id for row in old_learner.replay.sample(3)],
                             [row.transition_id for row in current_learner.replay.sample(3)])
            self.assertEqual(old_learner.replay.rng.getstate(), current_learner.replay.rng.getstate())
            self.assertEqual(old_learner.exploration_rng.random(), current_learner.exploration_rng.random())

    def test_old_and_current_cli_resume_selection_both_return_none_for_attempt_zero(self) -> None:
        from videochess_rl.rl import cli

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "initialization-manifest.json").write_text("{}\n")
            namespace = {
                "Path": Path,
                "Any": Any,
                "EXPERIMENT_ID": "fixture-experiment",
                "RECOVERY_COMPATIBLE_CODE_SHA256": frozenset({"fixture-code"}),
                "config_hash": lambda: "fixture-config",
                "source_hash": lambda: "fixture-code",
                "_attempt_dirs": lambda pair_id, arm: [(0, directory)],
            }
            old_source = (RECOVERED / "cli-resume-earlier.pyfrag").read_text()
            exec(compile(old_source, "transcript-cli-resume-excerpt", "exec"), namespace)
            old_selector = namespace["_latest_verified_resume"]
            with patch.object(cli, "_attempt_dirs", return_value=[(0, directory)]):
                self.assertEqual(old_selector("pair", "scratch", 20261106), (None, None))
                self.assertEqual(cli._latest_verified_resume("pair", "scratch", 20261106), (None, None))

    def test_old_and_current_cli_select_the_same_latest_well_formed_checkpoint(self) -> None:
        from videochess_rl.rl import cli

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            names = (
                "run__episodes-00002__decisions-00010__resume-v2.pt",
                "run__episodes-00003__decisions-00014__resume-v2.pt",
            )
            bundles = {}
            for episodes, decisions, name in ((2, 10, names[0]), (3, 14, names[1])):
                (directory / name).touch()
                bundles[name] = {
                    "identity": {"experiment_id": cli.EXPERIMENT_ID, "pair_id": "pair", "arm": "scratch",
                                 "training_seed": 20261106, "config_sha256": "fixture-config",
                                 "code_sha256": "fixture-code"},
                    "counters": {"completed_episodes": episodes, "valid_decisions": decisions},
                }

            old_namespace = {
                "Path": Path,
                "Any": Any,
                "EXPERIMENT_ID": cli.EXPERIMENT_ID,
                "RECOVERY_COMPATIBLE_CODE_SHA256": frozenset({"fixture-code"}),
                "config_hash": lambda: "fixture-config",
                "source_hash": lambda: "fixture-code",
                "_attempt_dirs": lambda pair_id, arm: [(0, directory)],
                "load_training_checkpoint_bundle": lambda path, **kwargs: bundles[path.name],
            }
            old_source = (RECOVERED / "cli-resume-earlier.pyfrag").read_text()
            exec(compile(old_source, "transcript-cli-resume-excerpt", "exec"), old_namespace)
            current_patches = (
                patch.object(cli, "_attempt_dirs", return_value=[(0, directory)]),
                patch.object(cli, "config_hash", return_value="fixture-config"),
                patch.object(cli, "source_hash", return_value="fixture-code"),
                patch.object(cli, "RECOVERY_COMPATIBLE_CODE_SHA256", frozenset({"fixture-code"})),
                patch.object(cli, "load_training_checkpoint_bundle",
                             side_effect=lambda path, **kwargs: bundles[path.name]),
                patch.object(cli, "verify_training_checkpoint", return_value=None),
            )
            with current_patches[0], current_patches[1], current_patches[2], current_patches[3], current_patches[4], current_patches[5]:
                old_path, old_bundle = old_namespace["_latest_verified_resume"]("pair", "scratch", 20261106)
                current_path, current_bundle = cli._latest_verified_resume("pair", "scratch", 20261106)
            self.assertEqual(old_path, current_path)
            self.assertEqual(old_bundle, current_bundle)
            self.assertEqual(old_path.name, names[1])


if __name__ == "__main__":
    unittest.main()
