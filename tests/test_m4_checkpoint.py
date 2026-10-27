from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import chess
import torch

from videochess_rl.model.checkpoint import (
    capture_rng_state,
    load_checkpoint,
    save_checkpoint,
    verify_artifact_manifest,
    verify_checkpoint,
    write_artifact_manifest,
)
from videochess_rl.model.features import INPUT_SCHEMA
from videochess_rl.model.network import MODEL_SCHEMA, BehaviorScorer, initialize_q_head
from videochess_rl.model.cli import _environment

REPO = Path(__file__).resolve().parents[1]


class M4CheckpointTests(unittest.TestCase):
    def _save(self, root: Path) -> tuple[Path, BehaviorScorer, dict[str, object]]:
        model = BehaviorScorer()
        metadata = {
            "input_schema": INPUT_SCHEMA,
            "model_schema": MODEL_SCHEMA,
            "model_config": model.config.as_json(),
            "parameter_count": model.trainable_parameter_count,
            "dataset_release_id": "f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890",
            "split_assignment_sha256": "84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e",
            "label_semantics": "played_move_uci behavior target",
            "runtime_environment": _environment(),
        }
        path = root / "pretrained.pt"
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)
        save_checkpoint(path, model, metadata=metadata, optimizer_state=optimizer.state_dict(), rng_state=capture_rng_state())
        return path, model, metadata

    def test_checkpoint_round_trip_and_identity_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path, source, _ = self._save(Path(temporary))
            manifest = verify_checkpoint(path)
            self.assertEqual(manifest["parameter_count"], 121_897)
            loaded, bundle = load_checkpoint(
                path,
                expected_release_id="f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890",
                expected_split_sha256="84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e",
            )
            self.assertEqual(bundle["checkpoint_schema"], "videochess-m4-checkpoint/1.0")
            self.assertTrue(bundle["optimizer_state"])
            self.assertIn("torch_cpu", bundle["rng_state"])
            for key, tensor in source.state_dict().items():
                self.assertTrue(torch.equal(tensor.cpu(), loaded.state_dict()[key].cpu()), key)
            with self.assertRaisesRegex(ValueError, "release identity"):
                load_checkpoint(path, expected_release_id="wrong")

    def test_runtime_version_metadata_uses_safe_builtin_strings(self) -> None:
        environment = _environment()
        self.assertIs(type(environment["torch"]), str)
        self.assertIs(type(environment["numpy"]), str)
        with tempfile.TemporaryDirectory() as temporary:
            path, _, _ = self._save(Path(temporary))
            loaded, bundle = load_checkpoint(path)
            self.assertEqual(bundle["metadata"]["runtime_environment"]["torch"], str(torch.__version__))
            self.assertEqual(loaded.trainable_parameter_count, 121_897)

    def test_corrupt_missing_and_unlisted_artifacts_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, _, _ = self._save(root)
            write_artifact_manifest(root)
            self.assertEqual(len(verify_artifact_manifest(root)["files"]), 2)
            extra = root / "unlisted.extra"
            extra.write_text("unlisted", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "file set"):
                verify_artifact_manifest(root)
            extra.unlink()
            with path.open("ab") as stream:
                stream.write(b"corruption")
            with self.assertRaisesRegex(ValueError, "checksum or size"):
                verify_checkpoint(path)
            with self.assertRaisesRegex(ValueError, "checksum or size"):
                verify_artifact_manifest(root)

    def test_missing_checkpoint_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path, _, _ = self._save(Path(temporary))
            path.with_suffix(path.suffix + ".manifest.json").unlink()
            with self.assertRaisesRegex(ValueError, "manifest is missing"):
                verify_checkpoint(path)

    def test_checkpoint_and_sidecar_symlinks_are_rejected_before_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, _, _ = self._save(root)
            link = root / "checkpoint-link.pt"
            link.symlink_to(path.name)
            with self.assertRaisesRegex(ValueError, "not a symlink"):
                verify_checkpoint(link)
            link.unlink()

            sidecar = path.with_suffix(path.suffix + ".manifest.json")
            original = root / "original.manifest.json"
            sidecar.rename(original)
            sidecar.symlink_to(original.name)
            with self.assertRaisesRegex(ValueError, "manifest is missing or unsafe"):
                verify_checkpoint(path)

    def test_artifact_root_and_nested_symlink_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            root = parent / "artifacts"
            root.mkdir()
            nested = root / "nested"
            nested.mkdir()
            (nested / "result.json").write_text("{}", encoding="utf-8")
            write_artifact_manifest(root)

            outside = parent / "outside"
            outside.mkdir()
            (outside / "result.json").write_text("{}", encoding="utf-8")
            nested.rename(root / "nested-real")
            nested.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "missing or unsafe"):
                verify_artifact_manifest(root)

            nested.unlink()
            (root / "nested-real").rename(nested)
            link = parent / "artifact-link"
            link.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "directory must not be a symlink"):
                verify_artifact_manifest(link)

    def test_selected_checkpoint_can_be_copied_with_verified_filename_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, _, _ = self._save(root)
            target = root / "pretrained-behavior-only.pt"
            shutil.copyfile(source, target)
            sidecar = source.with_suffix(source.suffix + ".manifest.json")
            copied_manifest = json.loads(sidecar.read_text(encoding="utf-8"))
            copied_manifest["checkpoint_file"] = target.name
            target.with_suffix(target.suffix + ".manifest.json").write_text(
                json.dumps(copied_manifest, sort_keys=True), encoding="utf-8",
            )
            self.assertEqual(verify_checkpoint(target)["checkpoint_sha256"], verify_checkpoint(source)["checkpoint_sha256"])
            model, _ = load_checkpoint(target)
            self.assertEqual(model.trainable_parameter_count, 121_897)

    def test_m5_transfer_reuses_representation_and_reinitializes_a_separate_head(self) -> None:
        source = BehaviorScorer()
        source_head = source.behavior_head.weight.detach().clone()
        target = initialize_q_head(source, seed=71)
        self.assertFalse(hasattr(target, "behavior_head"))
        self.assertTrue(hasattr(target, "q_head"))
        self.assertEqual(source.trainable_parameter_count, target.trainable_parameter_count)
        for key, tensor in source.m5_transfer_state().items():
            self.assertTrue(torch.equal(tensor, target.state_dict()[key]), key)
        self.assertFalse(torch.equal(source_head, target.q_head.weight.detach()))
        self.assertNotIn("double_dqn", {name.lower() for name, _ in target.named_modules()})

    def test_inference_reload_works_with_stockfish_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path, _, _ = self._save(Path(temporary))
            manifest = verify_checkpoint(path)
            env = os.environ.copy()
            env["PATH"] = "/usr/bin:/bin"
            env["PYTHONPATH"] = str(REPO)
            code = r'''
import json, shutil, torch
from videochess_rl.baselines import RandomLegalAgent
from videochess_rl.model.checkpoint import load_checkpoint
from videochess_rl.model.inference import BehaviorPolicy
from videochess_rl.simulator import ChessSimulator
assert shutil.which("stockfish") is None
model, _ = load_checkpoint(r"CHECKPOINT")
policy = BehaviorPolicy(model, checkpoint_sha256="HASH")
sim = ChessSimulator(RandomLegalAgent())
obs = sim.reset(seed=19)
move = policy.choose_move(obs, sim.legal_moves, __import__("random").Random(19))
assert move.uci() in obs.legal_moves_uci
assert "chess.engine" not in __import__("sys").modules
print(json.dumps({"move_is_legal": True, "stockfish_path": shutil.which("stockfish"), "engine_imported": False}))
'''.replace("CHECKPOINT", str(path)).replace("HASH", manifest["checkpoint_sha256"])
            process = subprocess.run(
                [sys.executable, "-c", code], cwd=REPO, env=env, text=True,
                capture_output=True, timeout=30,
            )
            self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
            result = json.loads(process.stdout.strip().splitlines()[-1])
            self.assertEqual(result, {"move_is_legal": True, "stockfish_path": None, "engine_imported": False})


if __name__ == "__main__":
    unittest.main()
