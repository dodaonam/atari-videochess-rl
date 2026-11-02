#!/usr/bin/env python3
"""Read-only dry-run of the accepted M4-to-M5 representation boundary.

This script does not train or save an M5 model. Run with Stockfish absent from
PATH to verify safe loading and representative legal candidate inference.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
import shutil
import sys
from pathlib import Path

import chess
import torch

from videochess_rl.baselines import RandomLegalAgent
from videochess_rl.model.checkpoint import load_checkpoint, verify_artifact_manifest
from videochess_rl.model.dataset import collate_examples, model_inputs
from videochess_rl.model.features import INPUT_SCHEMA, encode_board
from videochess_rl.model.inference import BehaviorPolicy, select_legal_candidate
from videochess_rl.model.network import initialize_q_head
from videochess_rl.simulator import ChessSimulator

CHECKPOINT_SHA256 = "724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4"
RELEASE_ID = "f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890"
SPLIT_SHA256 = "84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    path = Path(sys.argv[1]).expanduser().resolve(strict=True) if len(sys.argv) == 2 else Path(
        "/home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r4/pretrained-behavior-only.pt"
    ).resolve(strict=True)
    if shutil.which("stockfish") is not None or "chess.engine" in sys.modules:
        raise RuntimeError("engine-free verification requires Stockfish absent and chess.engine unloaded")
    before = sha256(path)
    if before != CHECKPOINT_SHA256:
        raise RuntimeError("accepted M4 checkpoint SHA-256 differs")
    bundle_manifest = verify_artifact_manifest(path.parent)
    if len(bundle_manifest["files"]) != 19:
        raise RuntimeError("expected exactly 19 accepted M4 run artifacts")
    behavior, bundle = load_checkpoint(path, expected_release_id=RELEASE_ID, expected_split_sha256=SPLIT_SHA256)
    if bundle["metadata"].get("input_schema") != INPUT_SCHEMA:
        raise RuntimeError("M4 checkpoint input schema differs")
    if bundle["metadata"].get("teacher_scores_or_targets_used") is not False:
        raise RuntimeError("accepted checkpoint is not attested as behavior-only")

    seed = 20261028
    online = initialize_q_head(behavior, seed=seed).eval()
    target = copy.deepcopy(online).eval()
    for key, value in behavior.m5_transfer_state().items():
        if not torch.equal(value, online.state_dict()[key]):
            raise RuntimeError(f"shared representation weight mismatch: {key}")
    if hasattr(online, "behavior_head") or not hasattr(online, "q_head"):
        raise RuntimeError("M5 wrapper must replace the behavior head")
    if torch.equal(behavior.behavior_head.weight.detach(), online.q_head.weight.detach()):
        raise RuntimeError("M4 behavior head was copied as the Q head")
    for key, value in online.state_dict().items():
        if not torch.equal(value, target.state_dict()[key]):
            raise RuntimeError(f"target network initial copy mismatch: {key}")

    simulator = ChessSimulator(RandomLegalAgent())
    observation = simulator.reset(seed=seed, agent_color=chess.WHITE)
    legal = simulator.legal_moves
    behavior_policy = BehaviorPolicy(behavior, checkpoint_sha256=before)
    behavior_move = behavior_policy.choose_move(observation, legal, random.Random(seed))
    board = chess.Board()
    features = encode_board(board)
    batch = collate_examples((features,), require_targets=False)
    with torch.inference_mode():
        q_logits = online(**model_inputs(batch))[0]
    if not torch.isfinite(q_logits[batch["candidate_mask"][0]]).all():
        raise RuntimeError("fresh Q scorer produced a nonfinite legal candidate score")
    q_action = select_legal_candidate(q_logits, batch["candidate_mask"][0], features.candidate_uci)
    if behavior_move.uci() not in observation.legal_moves_uci or q_action not in observation.legal_moves_uci:
        raise RuntimeError("an inference action is outside the authoritative legal UCI set")
    if "chess.engine" in sys.modules or shutil.which("stockfish") is not None:
        raise RuntimeError("Stockfish unexpectedly entered the inference environment")
    if sha256(path) != before:
        raise RuntimeError("accepted M4 checkpoint changed during transfer verification")
    after_manifest = verify_artifact_manifest(path.parent)
    if after_manifest != bundle_manifest:
        raise RuntimeError("accepted M4 artifact bundle changed during transfer verification")

    print(json.dumps({
        "schema": "videochess-m4-to-m5-transfer-verification/1.0",
        "checkpoint_sha256": before,
        "artifact_files_verified": len(bundle_manifest["files"]),
        "release_id": bundle["metadata"].get("dataset_release_id"),
        "model_schema": bundle["metadata"].get("model_schema"),
        "input_schema": INPUT_SCHEMA,
        "parameter_count": behavior.trainable_parameter_count,
        "shared_representation_equal": True,
        "behavior_head_excluded": True,
        "fresh_q_head_seed": seed,
        "target_initialized_from_transferred_online": True,
        "m4_behavior_move_uci": behavior_move.uci(),
        "untrained_q_scorer_move_uci": q_action,
        "both_actions_legal": True,
        "stockfish_path": shutil.which("stockfish"),
        "chess_engine_imported": "chess.engine" in sys.modules,
        "source_artifacts_unchanged": True,
        "ddqn_training_performed": False
    }, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
