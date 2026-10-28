#!/usr/bin/env python3
"""Bounded, CPU-only M5 feasibility profile; does not run an RL campaign.

This profiles the integrated M2/M4 boundaries using short simulator samples,
synthetic gradient work, and temporary checkpoint serialization. No replay
buffer or persistent model artifact is written.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import random
import resource
import subprocess
import tempfile
import time
from pathlib import Path
from statistics import median

import chess
import numpy as np
import torch
import torch.nn.functional as F

from videochess_rl.baselines import RandomLegalAgent
from videochess_rl.model.checkpoint import load_checkpoint, verify_artifact_manifest
from videochess_rl.model.dataset import collate_examples, model_inputs
from videochess_rl.model.features import encode_board, replay_observation_history
from videochess_rl.model.network import initialize_q_head
from videochess_rl.simulator import ChessSimulator

EXPECTED_CHECKPOINT_SHA256 = "724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4"
EXPECTED_RELEASE_ID = "f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890"
EXPECTED_SPLIT_SHA256 = "84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def quantiles(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {"p50": 0.0, "p95": 0.0, "max": 0.0}

    def q(fraction: float) -> float:
        return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * fraction))]

    return {"p50": q(.50), "p95": q(.95), "max": max(ordered)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=840.0)
    args = parser.parse_args()
    if args.max_seconds <= 0 or args.max_seconds > 840:
        parser.error("max-seconds must be in (0, 840]; total allowance is 15 minutes")
    started = time.monotonic()
    deadline = started + args.max_seconds
    checkpoint = args.checkpoint.expanduser().resolve(strict=True)
    checkpoint_before = sha256(checkpoint)
    if checkpoint_before != EXPECTED_CHECKPOINT_SHA256:
        raise RuntimeError("the accepted M4 checkpoint identity does not match")
    artifact = verify_artifact_manifest(checkpoint.parent)
    if len(artifact["files"]) != 19:
        raise RuntimeError("accepted M4 artifact manifest does not contain the expected 19 files")

    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    random.seed(20261028)
    np.random.seed(20261028)
    torch.manual_seed(20261028)

    model, bundle = load_checkpoint(
        checkpoint,
        expected_release_id=EXPECTED_RELEASE_ID,
        expected_split_sha256=EXPECTED_SPLIT_SHA256,
    )
    model.eval()
    transfer_started = time.perf_counter()
    online = initialize_q_head(model, seed=20261028).eval()
    target = copy.deepcopy(online).eval()
    transfer_seconds = time.perf_counter() - transfer_started
    for key, value in model.m5_transfer_state().items():
        if not torch.equal(value, online.state_dict()[key]):
            raise RuntimeError(f"shared transfer differs at {key}")
    if hasattr(online, "behavior_head") or not hasattr(online, "q_head"):
        raise RuntimeError("M5 scorer did not replace the M4 behavior head")
    if torch.equal(model.behavior_head.weight.detach(), online.q_head.weight.detach()):
        raise RuntimeError("Q head unexpectedly copied the behavior-logit head")
    if not all(torch.equal(value, target.state_dict()[key]) for key, value in online.state_dict().items()):
        raise RuntimeError("target initialization differs from post-transfer online network")

    opponent = RandomLegalAgent()
    simulator = ChessSimulator(opponent, max_decisions=20)
    observation = simulator.reset(seed=20261028, agent_color=chess.WHITE)
    transitions = 0
    transition_seconds: list[float] = []
    features = []
    reconstruction_seconds: list[float] = []
    encoding_seconds: list[float] = []
    history_lengths: list[int] = []
    candidate_counts: list[int] = []
    examples_wire_bytes: list[int] = []
    decision_rng = random.Random(20261028)
    while transitions < 32 and time.monotonic() < deadline:
        state_observation = observation
        legal = simulator.legal_moves
        action = opponent.choose_move(state_observation, legal, decision_rng)
        tick = time.perf_counter()
        result = simulator.step(action)
        transition_seconds.append(time.perf_counter() - tick)
        transitions += 1
        observation = result.observation

        tick = time.perf_counter()
        board = replay_observation_history(state_observation.history_uci)
        reconstruction_seconds.append(time.perf_counter() - tick)
        if board.fen(en_passant="fen") != state_observation.fen:
            raise RuntimeError("M2 history replay does not match observation FEN")
        if board.turn != state_observation.agent_color or board.turn != state_observation.turn:
            raise RuntimeError("simulator observation is not at the fixed agent decision boundary")
        tick = time.perf_counter()
        row = encode_board(board, split="profile")
        encoding_seconds.append(time.perf_counter() - tick)
        if row.candidate_uci != tuple(state_observation.legal_moves_uci):
            raise RuntimeError("model candidate UCI order differs from M2 legal actions")
        features.append(row)
        history_lengths.append(row.history_length)
        candidate_counts.append(row.candidate_count)
        semantic_record = {
            "history_uci": state_observation.history_uci,
            "legal_uci": row.candidate_uci,
            "agent_color": state_observation.agent_side,
            "opponent_id": state_observation.opponent_id,
            "opponent_config_json": state_observation.opponent_config_json,
            "agent_move_uci": action.uci(),
            "reward": result.reward,
            "terminated": result.terminated,
            "truncated": result.truncated,
            "next_history_uci": result.history_uci,
        }
        examples_wire_bytes.append(len(json.dumps(semantic_record, sort_keys=True, separators=(",", ":")).encode()))
        if result.terminated or result.truncated:
            observation = simulator.reset(seed=20261028 + transitions, agent_color=chess.WHITE)

    if transitions < 8 or len(features) < 8:
        raise RuntimeError("deadline prevented the minimum eight-transition profiling sample")

    batch_rows = features[: min(8, len(features))]
    batch = collate_examples(batch_rows, require_targets=False)
    inputs = model_inputs(batch)
    online.eval()
    forward_times = []
    for _ in range(20):
        tick = time.perf_counter()
        with torch.inference_mode():
            logits = online(**inputs)
            target_logits = target(**inputs)
        if not torch.isfinite(logits[batch["candidate_mask"]]).all() or not torch.isfinite(target_logits[batch["candidate_mask"]]).all():
            raise RuntimeError("transferred scorer produced nonfinite legal outputs")
        forward_times.append(time.perf_counter() - tick)
    candidate_evaluations = sum(row.candidate_count for row in batch_rows) * 20 * 2

    online.train()
    target_indices = torch.tensor([0] * len(batch_rows), dtype=torch.long)
    if torch.any(batch["candidate_mask"].sum(1) <= target_indices):
        raise RuntimeError("synthetic gradient sample has an empty legal candidate set")
    optimizer = torch.optim.AdamW(online.parameters(), lr=3e-4, weight_decay=1e-4)
    tick = time.perf_counter()
    optimizer.zero_grad(set_to_none=True)
    gradient_logits = online(**inputs)
    loss = F.cross_entropy(gradient_logits.masked_fill(~batch["candidate_mask"], -1e9), target_indices)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(online.parameters(), 1.0, error_if_nonfinite=True)
    optimizer.step()
    gradient_seconds = time.perf_counter() - tick

    state_bytes = sum(t.numel() * t.element_size() for t in online.state_dict().values())
    online_target_bytes = state_bytes * 2
    with tempfile.TemporaryDirectory(prefix="m5-profile-") as temporary:
        path = Path(temporary) / "prototype-state.pt"
        tick = time.perf_counter()
        torch.save({"online": online.state_dict(), "target": target.state_dict()}, path)
        serialization_seconds = time.perf_counter() - tick
        serialization_bytes = path.stat().st_size

    elapsed = time.monotonic() - started
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    if elapsed > args.max_seconds or elapsed > 840:
        raise RuntimeError("profiling exceeded its hard wall-clock cap")
    if peak_rss > 2 * 1024**3:
        raise RuntimeError("profiling exceeded its 2 GiB RSS cap")
    if sha256(checkpoint) != checkpoint_before:
        raise RuntimeError("the accepted M4 checkpoint changed during profile")
    artifact_after = verify_artifact_manifest(checkpoint.parent)
    if artifact_after != artifact:
        raise RuntimeError("the accepted M4 artifact bundle changed during profile")

    output = {
        "schema": "videochess-pre-m5-feasibility-profile/1.0",
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": str(torch.__version__),
        "numpy": np.__version__,
        "python_chess": chess.__version__,
        "device": "cpu",
        "threads": {"intra_op": torch.get_num_threads(), "inter_op": torch.get_num_interop_threads()},
        "checkpoint": {"path": str(checkpoint), "sha256": checkpoint_before, "size_bytes": checkpoint.stat().st_size,
                       "artifact_files_verified": len(artifact["files"]),
                       "artifact_inventory_sha256": hashlib.sha256(json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                       "artifact_inventory_unchanged_after_profile": True},
        "m3_release_identity": EXPECTED_RELEASE_ID,
        "transfer_dry_run": {"seed": 20261028, "seconds": transfer_seconds,
                             "shared_weights_equal": True, "behavior_head_not_copied": True,
                             "target_initialized_from_online": True, "ddqn_training": False},
        "simulator": {"opponent": opponent.policy_id, "transitions": transitions,
                      "transitions_per_second": transitions / max(sum(transition_seconds), 1e-12),
                      "transition_seconds": quantiles(transition_seconds),
                      "all_transition_states_verified": True},
        "representation": {"reconstruction_seconds": quantiles(reconstruction_seconds),
                           "feature_encoding_seconds": quantiles(encoding_seconds),
                           "history_length": {"min": min(history_lengths), "p50": median(history_lengths), "max": max(history_lengths)},
                           "legal_candidates": {"min": min(candidate_counts), "p50": median(candidate_counts), "max": max(candidate_counts)},
                           "sampled_transition_wire_bytes": {"p50": median(examples_wire_bytes), "max": max(examples_wire_bytes),
                                                              "capacity_4096_at_max_wire_bytes": max(examples_wire_bytes) * 4096}},
        "q_network_profile": {"parameter_count": online.trainable_parameter_count,
                               "forward_batch_size": len(batch_rows),
                               "forward_calls_including_target": 40,
                               "forward_seconds": quantiles(forward_times),
                               "candidate_evaluations_per_second": candidate_evaluations / max(sum(forward_times), 1e-12),
                               "synthetic_optimizer_step_seconds": gradient_seconds,
                               "online_state_tensor_bytes": state_bytes,
                               "online_plus_target_tensor_bytes": online_target_bytes,
                               "temporary_online_target_serialization_bytes": serialization_bytes,
                               "temporary_serialization_seconds": serialization_seconds},
        "resource": {"wall_seconds": elapsed, "peak_rss_bytes": peak_rss, "active_profile_budget_seconds": args.max_seconds},
        "limitations": [
            "Short RandomLegalAgent simulator sample; not an RL run or a performance claim.",
            "Replay storage bytes are compact JSON wire-size estimates, not measured Python heap usage.",
            "Temporary model serialization excludes optimizer state and replay contents.",
            "No full episodes, persistent replay, training campaign, external compute, or artifact mutation occurred.",
        ],
    }
    print(json.dumps(output, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
