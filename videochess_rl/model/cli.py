"""Reproducible, resource-bounded M4 behavior-cloning experiment runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chess
import numpy as np
import torch

from videochess_rl.baselines import RandomLegalAgent, SimpleHeuristicAgent
from videochess_rl.model.checkpoint import (
    capture_rng_state,
    load_checkpoint,
    save_checkpoint,
    verify_artifact_manifest,
    verify_checkpoint,
    write_artifact_manifest,
)
from videochess_rl.model.dataset import (
    EXPECTED_COUNTS,
    EXPECTED_GAME_COUNTS,
    EXPECTED_MANIFEST_SHA256,
    EXPECTED_RELEASE_ID,
    EXPECTED_SPLIT_SHA256,
    M4Dataset,
    load_m3_release,
    smallest_training_sample_ids,
)
from videochess_rl.model.features import INPUT_SCHEMA
from videochess_rl.model.inference import BehaviorPolicy
from videochess_rl.model.network import MODEL_SCHEMA, BehaviorScorer, ModelConfig
from videochess_rl.model.training import (
    TrainingBudgetExceeded,
    TrainingConfig,
    configure_determinism,
    evaluate_examples,
    fit_seed,
    peak_rss_bytes,
    run_overfit_gate,
)
from videochess_rl.simulator import ChessSimulator

RUN_SCHEMA = "videochess-m4-run/1.0"
RELEASE_PATH = Path(
    "/home/dodaonam/Projects/atari-videochess-rl-m3/artifacts/m3/training-support/release-final-closure-r6"
)
PREVIOUS_RELEASE_EVIDENCE = Path(".agents/evidence/logs/M4-release-verification-20261027.json")
AGGREGATE_LIMIT_SECONDS = 3 * 60 * 60
SEED_LIMIT_SECONDS = 45 * 60
PROCESS_RSS_LIMIT_BYTES = 2 * 1024**3
FEATURE_CACHE_LIMIT_BYTES = 512 * 1024**2
SIMULATOR_LIMIT_SECONDS = 20 * 60


class ExperimentStop(RuntimeError):
    """A recorded, bounded stop that must prevent downstream acceptance."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _json_write(path: Path, value: Any) -> None:
    encoded = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _event(root: Path, name: str, **fields: Any) -> None:
    line = json.dumps({"at_utc": _utc_now(), "event": name, **fields}, sort_keys=True, allow_nan=False)
    with (root / "events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _sha256(path: Path) -> tuple[str, int]:
    digestor = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digestor.update(chunk)
            size += len(chunk)
    return digestor.hexdigest(), size


def _git_revision(repo: Path) -> tuple[str | None, bool | None]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=False,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=repo, capture_output=True, text=True, check=False,
    )
    return (
        revision.stdout.strip() if revision.returncode == 0 else None,
        bool(status.stdout.strip()) if status.returncode == 0 else None,
    )


def _environment() -> dict[str, Any]:
    return {
        "python": sys.version,
        "python_executable": sys.executable,
        "torch": torch.__version__,
        "numpy": np.__version__,
        "python_chess": chess.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "logical_cpu_count": os.cpu_count(),
        "device": "cpu",
        "torch_intraop_threads": torch.get_num_threads(),
        "torch_interop_threads": torch.get_num_interop_threads(),
        "stockfish_executable_on_path": shutil.which("stockfish"),
    }


def _previous_verification(repo: Path) -> dict[str, Any]:
    path = repo / PREVIOUS_RELEASE_EVIDENCE
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("exit_code") != 0
        or value.get("unchanged") is not True
        or value.get("files_before") != value.get("files_after")
    ):
        raise ValueError("prior release verification evidence is missing, failed, or reports mutation")
    stdout = json.loads(value.get("stdout", "{}"))
    if (
        stdout.get("release_id") != EXPECTED_RELEASE_ID
        or stdout.get("manifest_sha256") != EXPECTED_MANIFEST_SHA256
        or stdout.get("games") != 1_000
        or stdout.get("positions") != sum(EXPECTED_COUNTS.values())
    ):
        raise ValueError("prior release evidence does not identify the accepted M3 release")
    if len(value.get("files_before", {})) != 9:
        raise ValueError("prior release evidence does not inventory all nine accepted files")
    return {
        "evidence_path": PREVIOUS_RELEASE_EVIDENCE.as_posix(),
        "revision": value.get("revision"),
        "command": value.get("command"),
        "started_at_utc": value.get("started_at_utc"),
        "ended_at_utc": value.get("ended_at_utc"),
        "duration_seconds": float(value["duration_seconds"]),
        "exit_code": 0,
        "unchanged": True,
        "files_before": value.get("files_before"),
        "files_after": value.get("files_after"),
        "stdout_summary": stdout,
    }


def _assert_remaining(global_deadline: float, stage: str) -> float:
    remaining = global_deadline - time.monotonic()
    if remaining <= 0:
        raise TrainingBudgetExceeded(f"aggregate three-hour budget reached before {stage}")
    if peak_rss_bytes() > PROCESS_RSS_LIMIT_BYTES:
        raise TrainingBudgetExceeded(f"process peak RSS exceeded 2 GiB before {stage}")
    return remaining


def _utc_elapsed(started: str, ended: str | None = None) -> float:
    start = datetime.fromisoformat(started.replace("Z", "+00:00"))
    end = datetime.fromisoformat((ended or _utc_now()).replace("Z", "+00:00"))
    return max(0.0, (end - start).total_seconds())


def _prior_m4_runs(artifact_base: Path) -> list[dict[str, Any]]:
    """Read prior attempt manifests in this dedicated external artifact root."""
    if not artifact_base.exists():
        return []
    if artifact_base.is_symlink() or not artifact_base.is_dir():
        raise ValueError("M4 artifact root must be a real directory")
    runs: list[dict[str, Any]] = []
    for child in sorted(artifact_base.iterdir()):
        manifest_path = child / "run_manifest.json"
        if not child.is_dir() or not manifest_path.exists():
            continue
        if child.is_symlink() or manifest_path.is_symlink() or not manifest_path.is_file():
            raise ValueError(f"unsafe prior M4 run manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema") != RUN_SCHEMA:
            raise ValueError(f"unrecognized run manifest in the dedicated M4 artifact root: {manifest_path}")
        if not isinstance(manifest.get("started_at_utc"), str):
            raise ValueError(f"prior M4 run has no start timestamp: {manifest_path}")
        ended = manifest.get("ended_at_utc")
        recorded = manifest.get("execution_elapsed_seconds")
        if ended:
            elapsed = float(recorded) if isinstance(recorded, (int, float)) else _utc_elapsed(
                manifest["started_at_utc"], ended
            )
        else:
            # A process killed between writes is charged from its UTC start to
            # now, which is conservative and prevents a retry resetting caps.
            elapsed = max(
                float(recorded or 0.0),
                _utc_elapsed(manifest["started_at_utc"]),
            )
        if elapsed < 0 or not math.isfinite(elapsed):
            raise ValueError(f"prior M4 run has invalid elapsed time: {manifest_path}")
        runs.append(manifest | {"_execution_elapsed_seconds": elapsed, "_manifest_path": str(manifest_path)})
    return runs


def _prior_seed_time_usage(runs: list[dict[str, Any]]) -> dict[int, float]:
    """Accumulate each seed's elapsed time across recorded/aborted attempts."""
    usage: dict[int, float] = {}
    for run in runs:
        configured_seeds = run.get("training_config", {}).get("seeds", [20261022, 20261023, 20261024])
        first_seed = int(configured_seeds[0])
        records = run.get("seed_runs", [])
        recorded_seeds: set[int] = set()
        first_seed_includes_gate = False
        for record in records:
            if not isinstance(record, dict) or record.get("seed") is None:
                continue
            seed = int(record["seed"])
            recorded_seeds.add(seed)
            elapsed = record.get("seed_elapsed_including_gate_seconds")
            if not isinstance(elapsed, (int, float)):
                elapsed = record.get("duration_seconds", 0.0)
                if seed == first_seed:
                    elapsed += float(run.get("sanity_gate", {}).get("duration_seconds", 0.0) or 0.0)
            if seed == first_seed and record.get("seed_elapsed_including_gate_seconds") is not None:
                first_seed_includes_gate = True
            usage[seed] = usage.get(seed, 0.0) + float(elapsed)

        gate = run.get("sanity_gate")
        if not first_seed_includes_gate and isinstance(gate, dict):
            gate_seconds = gate.get("duration_seconds")
            if isinstance(gate_seconds, (int, float)):
                usage[first_seed] = usage.get(first_seed, 0.0) + float(gate_seconds)

        active_seed = run.get("active_seed")
        if active_seed is not None and int(active_seed) not in recorded_seeds:
            stage_start = run.get("current_stage_started_at_utc") or run.get("started_at_utc")
            usage[int(active_seed)] = usage.get(int(active_seed), 0.0) + _utc_elapsed(
                stage_start, run.get("ended_at_utc")
            )
        elif (
            run.get("current_stage") == "fixed_128_example_sanity_gate"
            and not isinstance(gate, dict)
        ):
            stage_start = run.get("current_stage_started_at_utc") or run.get("started_at_utc")
            usage[first_seed] = usage.get(first_seed, 0.0) + _utc_elapsed(
                stage_start, run.get("ended_at_utc")
            )
    return usage


def _checkpoint_metadata(
    model: BehaviorScorer,
    *,
    revision: str | None,
    worktree_dirty: bool | None,
    seed: int,
    epoch: int,
    dataset: M4Dataset,
    config: TrainingConfig,
    validation_record: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    return {
        "checkpoint_role": "pretrained_behavior_only",
        "run_id": run_id,
        "checkpoint_created_at_utc": _utc_now(),
        "command": [sys.executable, "-m", "videochess_rl.model.cli", "run", *sys.argv[2:]],
        "source_revision": revision,
        "source_worktree_dirty": worktree_dirty,
        "runtime_environment": _environment(),
        "input_schema": INPUT_SCHEMA,
        "model_schema": MODEL_SCHEMA,
        "model_config": model.config.as_json(),
        "parameter_count": model.trainable_parameter_count,
        "dataset_release_id": dataset.release_id,
        "release_manifest_sha256": dataset.manifest_sha256,
        "split_assignment_sha256": dataset.split_assignment_sha256,
        "split_counts": dataset.counts,
        "label_semantics": "played_move_uci from recorded PGN history; behavior cloning only",
        "teacher_scores_or_targets_used": False,
        "stockfish_used_for_training_or_inference": False,
        "seed": seed,
        "selected_epoch_for_seed": epoch,
        "selection_metric": "validation_nll_only",
        "validation_record": validation_record,
        "training_config": config.as_json(),
        "early_stopping_state_at_checkpoint": {
            "best_epoch": epoch,
            "best_validation_nll": validation_record["nll"],
            "no_improvement_epochs": 0,
            "patience": config.early_stopping_patience,
            "maximum_epochs": config.maximum_epochs,
        },
        "parameter_output_semantics": "uncalibrated behavior preference logit; not a Q-value or reward",
    }


def _save_epoch_checkpoint(
    path: Path,
    model: BehaviorScorer,
    optimizer: torch.optim.Optimizer,
    epoch_record: dict[str, Any],
    *,
    revision: str | None,
    worktree_dirty: bool | None,
    seed: int,
    dataset: M4Dataset,
    config: TrainingConfig,
    run_id: str,
) -> dict[str, Any]:
    metadata = _checkpoint_metadata(
        model, revision=revision, worktree_dirty=worktree_dirty, seed=seed, epoch=int(epoch_record["epoch"]),
        dataset=dataset, config=config, validation_record=epoch_record["validation"], run_id=run_id,
    )
    return save_checkpoint(
        path,
        model,
        metadata=metadata,
        optimizer_state=optimizer.state_dict(),
        rng_state=capture_rng_state(),
    )


def _profile_inference(
    model: BehaviorScorer,
    examples: tuple[Any, ...],
    *,
    max_seconds: float,
) -> dict[str, Any]:
    model.eval()
    latencies: list[float] = []
    candidate_total = 0
    started = time.perf_counter()
    with torch.inference_mode():
        for example in examples[:256]:
            if time.perf_counter() - started >= max_seconds:
                raise TrainingBudgetExceeded("inference profile reached its aggregate time budget")
            from videochess_rl.model.dataset import collate_examples, model_inputs

            batch = collate_examples((example,))
            inputs = model_inputs(batch)
            begin = time.perf_counter()
            logits = model(**inputs)
            elapsed = time.perf_counter() - begin
            if not torch.isfinite(logits[0, :example.candidate_count]).all():
                raise FloatingPointError("latency profile found non-finite legal candidate logits")
            latencies.append(elapsed)
            candidate_total += example.candidate_count
    elapsed_all = time.perf_counter() - started
    sorted_values = sorted(latencies)
    return {
        "examples": len(latencies),
        "candidate_evaluations": candidate_total,
        "candidate_count_p50": float(np.percentile([item.candidate_count for item in examples[:256]], 50)),
        "candidate_count_p95": float(np.percentile([item.candidate_count for item in examples[:256]], 95)),
        "model_forward_latency_seconds_p50": float(np.percentile(sorted_values, 50)),
        "model_forward_latency_seconds_p95": float(np.percentile(sorted_values, 95)),
        "precomputed_feature_collation_plus_model_seconds_per_example": elapsed_all / len(latencies),
        "candidate_evaluations_per_second": candidate_total / elapsed_all if elapsed_all else None,
        "source_partition": "training; first 256 lexically ordered sample IDs; profiling only",
        "elapsed_seconds": elapsed_all,
    }


def _inference_only_subprocess(
    repo: Path,
    checkpoint: Path,
    sha256: str,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    script = r'''
import json, random, shutil, sys
from videochess_rl.baselines import RandomLegalAgent
from videochess_rl.model.checkpoint import load_checkpoint
from videochess_rl.model.inference import BehaviorPolicy
from videochess_rl.simulator import ChessSimulator
assert shutil.which("stockfish") is None
model, _ = load_checkpoint(r"CHECKPOINT", expected_release_id="RELEASE")
policy = BehaviorPolicy(model, checkpoint_sha256="HASH")
simulator = ChessSimulator(RandomLegalAgent())
observation = simulator.reset(seed=20261027)
move = policy.choose_move(observation, simulator.legal_moves, random.Random(1))
assert move.uci() in observation.legal_moves_uci
assert "chess.engine" not in sys.modules
print(json.dumps({"legal_move": move.uci(), "stockfish_path": shutil.which("stockfish"), "engine_module_loaded": False}))
'''.replace("CHECKPOINT", str(checkpoint)).replace("RELEASE", EXPECTED_RELEASE_ID).replace("HASH", sha256)
    environment = os.environ.copy()
    environment["PATH"] = "/usr/bin:/bin"
    environment["PYTHONPATH"] = str(repo)
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=repo, env=environment,
        capture_output=True, text=True, timeout=timeout_seconds, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"engine-free inference subprocess failed: {result.stderr[-2000:]}")
    value = json.loads(result.stdout.strip().splitlines()[-1])
    if value.get("stockfish_path") is not None or value.get("engine_module_loaded") is not False:
        raise RuntimeError("inference-only process detected Stockfish")
    return {"exit_code": result.returncode, "stdout": value, "path": environment["PATH"]}


def _play_policy_game(
    policy: BehaviorPolicy,
    opponent: Any,
    *,
    opponent_id: str,
    seed: int,
    agent_color: chess.Color,
    max_decisions: int,
    deadline: float,
) -> tuple[dict[str, Any], list[float], int]:
    simulator = ChessSimulator(opponent, max_decisions=max_decisions)
    episode_start = time.perf_counter()
    observation = simulator.reset(seed=seed, agent_color=agent_color)
    policy_rng = random.Random(seed ^ 0x5A17)
    latencies: list[float] = []
    selected_candidate_count = 0
    status = "external_failure"
    failure_type: str | None = None
    while True:
        if time.monotonic() >= deadline:
            status = "interrupted_simulator_budget"
            break
        if peak_rss_bytes() > PROCESS_RSS_LIMIT_BYTES:
            status = "process_rss_limit"
            failure_type = "PeakRSSExceeded2GiB"
            break
        try:
            started = time.perf_counter()
            action = policy.choose_move(observation, simulator.legal_moves, policy_rng)
            latencies.append(time.perf_counter() - started)
            selected_candidate_count += len(observation.legal_moves_uci)
            transition = simulator.step(action)
            observation = transition.observation
            if transition.terminated:
                status = "completed"
                break
            if transition.truncated:
                status = "truncated"
                break
        except Exception as exc:
            status = "external_failure"
            failure_type = type(exc).__name__
            break

    board = simulator.board
    outcome = board.outcome(claim_draw=False)
    if status == "completed" and outcome is None:
        status, failure_type = "external_failure", "SimulatorOutcomeMissing"
    if status == "truncated" and outcome is not None:
        status, failure_type = "external_failure", "TerminalOutcomeMisclassifiedAsTruncation"
    if status == "completed" and outcome is not None:
        agent_result: float | None = (
            0.0 if outcome.winner is None else 1.0 if outcome.winner == agent_color else -1.0
        )
        wdl: str | None = "win" if agent_result == 1.0 else "loss" if agent_result == -1.0 else "draw"
    else:
        agent_result, wdl = None, None
    return ({
        "status": status,
        "opponent": opponent_id,
        "agent_color": "white" if agent_color == chess.WHITE else "black",
        "seed": seed,
        "agent_wdl": wdl,
        "agent_result": agent_result,
        "outcome_result_white_perspective": outcome.result() if status == "completed" and outcome else None,
        "termination_reason": outcome.termination.name.lower() if status == "completed" and outcome else None,
        "terminated": status == "completed",
        "truncated": status == "truncated",
        "truncation_reason": "max_agent_decisions" if status == "truncated" else None,
        "failure_type": failure_type,
        "agent_decisions": simulator.episode_decisions,
        "plies": simulator.episode_plies,
        "elapsed_seconds": time.perf_counter() - episode_start,
        "moves_uci": [move.uci() for move in board.move_stack],
        "metric_source": "M2 chess simulator; not Atari",
    }, latencies, selected_candidate_count)


def _simulator_benchmark(
    model: BehaviorScorer,
    checkpoint_sha256: str,
    *,
    max_seconds: float = SIMULATOR_LIMIT_SECONDS,
) -> dict[str, Any]:
    started = time.monotonic()
    deadline = started + max_seconds
    policy = BehaviorPolicy(model, checkpoint_sha256=checkpoint_sha256)
    games: list[dict[str, Any]] = []
    latencies: list[float] = []
    candidate_total = 0
    stopped_early = False
    for opponent_id in ("random_legal", "simple_material_heuristic"):
        for seed in range(20261030, 20261040):
            for color in (chess.WHITE, chess.BLACK):
                if time.monotonic() >= deadline:
                    stopped_early = True
                    break
                opponent = RandomLegalAgent() if opponent_id == "random_legal" else SimpleHeuristicAgent()
                game, game_latencies, game_candidates = _play_policy_game(
                    policy, opponent, opponent_id=opponent_id, seed=seed,
                    agent_color=color, max_decisions=400, deadline=deadline,
                )
                games.append(game)
                latencies.extend(game_latencies)
                candidate_total += game_candidates
                if game["status"] in {"interrupted_simulator_budget", "process_rss_limit"}:
                    stopped_early = True
                    break
            if stopped_early:
                break
        if stopped_early:
            break

    groups: dict[str, Any] = {}
    for opponent_id in ("random_legal", "simple_material_heuristic"):
        opponent_games = [game for game in games if game["opponent"] == opponent_id]
        by_color: dict[str, Any] = {}
        for color_name in ("white", "black"):
            color_games = [game for game in opponent_games if game["agent_color"] == color_name]
            completed = [game for game in color_games if game["status"] == "completed"]
            by_color[color_name] = {
                "scheduled_games": 20,
                "games_recorded": len(color_games),
                "completed_games": len(completed),
                "wins": sum(game["agent_wdl"] == "win" for game in completed),
                "draws": sum(game["agent_wdl"] == "draw" for game in completed),
                "losses": sum(game["agent_wdl"] == "loss" for game in completed),
                "truncated_games": sum(game["status"] == "truncated" for game in color_games),
                "interrupted_games": sum(game["status"].startswith("interrupted") for game in color_games),
                "external_failures": sum(game["status"] == "external_failure" for game in color_games),
            }
        groups[opponent_id] = {"games": len(opponent_games), "by_agent_color": by_color}
    failure_games = [
        game for game in games
        if game["status"] in {"external_failure", "process_rss_limit"}
    ]
    incomplete_games = [
        game for game in games
        if game["status"] in {"interrupted_simulator_budget", "process_rss_limit"}
    ]
    benchmark_status = (
        "failed_game_or_resource_limit" if failure_games
        else "complete" if len(games) == 40 and not incomplete_games
        else "incomplete_allowed_time_or_resource_limit"
    )
    elapsed = time.monotonic() - started
    return {
        "status": benchmark_status,
        "scheduled_games": 40,
        "games_recorded": len(games),
        "max_agent_decisions_per_game": 400,
        "seeds": list(range(20261030, 20261040)),
        "opponents": ["random_legal", "simple_material_heuristic"],
        "stockfish_available": shutil.which("stockfish") is not None,
        "total_elapsed_seconds": elapsed,
        "hard_time_limit_seconds": max_seconds,
        "stopped_early": stopped_early,
        "candidate_evaluations": candidate_total,
        "candidate_evaluations_per_second": candidate_total / elapsed if elapsed else None,
        "inference_latency_seconds_p50": float(np.percentile(latencies, 50)) if latencies else None,
        "inference_latency_seconds_p95": float(np.percentile(latencies, 95)) if latencies else None,
        "by_opponent": groups,
        "games": games,
        "interpretation": "M2 simulator behavior check only; no chess rating or Atari claim",
    }


def _artifact_directory(args: argparse.Namespace, repo: Path, run_id: str) -> Path:
    if run_id in {".", ".."} or Path(run_id).name != run_id or any(char in run_id for char in ("/", "\\")):
        raise ValueError("run_id must be a single safe directory name")
    base = Path(args.artifact_root).expanduser().resolve()
    if base == repo or repo in base.parents:
        raise ValueError("M4 model/training artifacts must remain outside the Git checkout")
    base.mkdir(parents=True, exist_ok=True)
    target = base / run_id
    target.mkdir(exist_ok=False)
    return target


def run_experiment(args: argparse.Namespace) -> int:
    repo = Path(__file__).resolve().parents[2]
    revision, dirty = _git_revision(repo)
    previous = _previous_verification(repo)
    requested_artifact_root = Path(args.artifact_root).expanduser()
    if requested_artifact_root.is_symlink():
        raise ValueError("M4 artifact root must not be a symlink")
    artifact_base = requested_artifact_root.resolve()
    if artifact_base == repo or repo in artifact_base.parents:
        raise ValueError("M4 model/training artifacts must remain outside the Git checkout")
    artifact_base.mkdir(parents=True, exist_ok=True)
    prior_runs = _prior_m4_runs(artifact_base)
    prior_execution_seconds = sum(run["_execution_elapsed_seconds"] for run in prior_runs)
    prior_seed_usage = _prior_seed_time_usage(prior_runs)
    used_before_this_run = previous["duration_seconds"] + prior_execution_seconds
    started_mono = time.monotonic()
    global_remaining = AGGREGATE_LIMIT_SECONDS - used_before_this_run
    global_deadline = started_mono + global_remaining
    run_id = args.run_id or datetime.now(timezone.utc).strftime("m4-behavior-%Y%m%dT%H%M%SZ")
    root = _artifact_directory(args, repo, run_id)
    config = TrainingConfig()
    model_config = ModelConfig()
    manifest: dict[str, Any] = {
        "schema": RUN_SCHEMA,
        "run_id": run_id,
        "status": "running",
        "current_stage": "initialization",
        "current_stage_started_at_utc": _utc_now(),
        "active_seed": None,
        "started_at_utc": _utc_now(),
        "ended_at_utc": None,
        "elapsed_seconds_including_prior_release_verification": None,
        "execution_elapsed_seconds": 0.0,
        "aggregate_seconds_used_before_this_run": used_before_this_run,
        "prior_m4_run_execution_seconds": prior_execution_seconds,
        "prior_seed_time_usage_seconds": {str(seed): seconds for seed, seconds in sorted(prior_seed_usage.items())},
        "source_revision": revision,
        "source_worktree_dirty": dirty,
        "command": [sys.executable, "-m", "videochess_rl.model.cli", "run", *sys.argv[2:]],
        "artifact_directory": str(root),
        "environment": _environment(),
        "prior_release_verification": previous,
        "budgets": {
            "aggregate_seconds": AGGREGATE_LIMIT_SECONDS,
            "aggregate_seconds_already_used": used_before_this_run,
            "seed_seconds": SEED_LIMIT_SECONDS,
            "simulator_seconds": SIMULATOR_LIMIT_SECONDS,
            "process_peak_rss_bytes": PROCESS_RSS_LIMIT_BYTES,
            "feature_cache_target_bytes": FEATURE_CACHE_LIMIT_BYTES,
            "model_parameter_limit_exclusive": 250_000,
        },
        "model": {"input_schema": INPUT_SCHEMA, "model_schema": MODEL_SCHEMA, "config": model_config.as_json()},
        "training_config": config.as_json(),
        "dataset": {
            "release_path": str(Path(args.release_dir).expanduser().resolve()),
            "release_id": EXPECTED_RELEASE_ID,
            "manifest_sha256": EXPECTED_MANIFEST_SHA256,
            "split_assignment_sha256": EXPECTED_SPLIT_SHA256,
            "expected_position_counts": EXPECTED_COUNTS,
            "expected_game_counts": EXPECTED_GAME_COUNTS,
            "target": "played_move_uci only",
            "stockfish_scores_or_targets_used": False,
        },
        "sanity_gate": None,
        "seed_runs": [],
        "selected_checkpoint": None,
        "test_evaluation": None,
        "simulator_evaluation": None,
        "inference_profile": None,
        "resource_measurements": {"peak_rss_bytes_at_start": peak_rss_bytes()},
        "known_limitations": [
            "behavior cloning of historical PGN actions is not optimal move selection or RL",
            "simulator results are not Atari performance or calibrated chess strength",
            "the third-party curated package is used only locally within the established bounded scope",
        ],
    }
    exit_code = 1
    _json_write(root / "run_manifest.json", manifest)
    _event(root, "run_started", source_revision=revision, source_worktree_dirty=dirty)

    def stage(name: str, **details: Any) -> None:
        manifest["current_stage"] = name
        manifest["current_stage_started_at_utc"] = _utc_now()
        manifest["active_seed"] = details.get("seed") if name == "seed_training" else None
        manifest["execution_elapsed_seconds"] = time.monotonic() - started_mono
        manifest["elapsed_seconds_including_prior_release_verification"] = (
            used_before_this_run + time.monotonic() - started_mono
        )
        _event(root, "stage", name=name, **details)
        _json_write(root / "run_manifest.json", manifest)

    try:
        if revision is None:
            raise ExperimentStop("could not establish the source Git revision")
        if global_remaining <= 0:
            raise TrainingBudgetExceeded("prior release verification exhausted the aggregate budget")
        stage("reverify_release_and_load_features", release_dir=str(Path(args.release_dir).expanduser().resolve()))
        configure_determinism(config.seeds[0])
        manifest["environment"] = _environment()
        _json_write(root / "run_manifest.json", manifest)
        dataset = load_m3_release(args.release_dir)
        manifest["dataset"].update({
            "verified_release_id": dataset.release_id,
            "verified_manifest_sha256": dataset.manifest_sha256,
            "verified_split_assignment_sha256": dataset.split_assignment_sha256,
            "position_counts": dataset.counts,
            "game_counts": dataset.game_counts,
            "candidate_counts": dataset.candidate_counts,
            "max_history_length": dataset.max_history_length,
            "max_candidate_count": dataset.max_candidate_count,
            "verification_seconds": dataset.verification_seconds,
            "replay_tensorization_seconds": dataset.replay_seconds,
            "loader_total_seconds": dataset.total_load_seconds,
            "feature_payload_bytes": dataset.feature_payload_bytes,
            "feature_cache_target_pass": dataset.feature_payload_bytes < FEATURE_CACHE_LIMIT_BYTES,
            "release_file_inventory": dataset.file_inventory,
            "cross_split_board_signature_overlap_after_purge": 0,
            "post_load_release_files_unchanged": True,
        })
        if dataset.feature_payload_bytes >= FEATURE_CACHE_LIMIT_BYTES:
            raise TrainingBudgetExceeded("feature cache reached the 512 MiB target boundary")
        _assert_remaining(global_deadline, "sanity gate")
        stage("fixed_128_example_sanity_gate", examples=128)

        selected_ids = smallest_training_sample_ids(dataset.train, 128)
        training_by_id = {row.sample_id: row for row in dataset.train}
        sanity_rows = tuple(training_by_id[sample_id] for sample_id in selected_ids)
        configure_determinism(config.seeds[0])
        gate_started_at_utc = _utc_now()
        gate_started = time.monotonic()
        gate_model = BehaviorScorer(model_config)
        first_seed_prior = prior_seed_usage.get(config.seeds[0], 0.0)
        gate_deadline = min(
            SEED_LIMIT_SECONDS - first_seed_prior - (time.monotonic() - gate_started) - 2.0,
            _assert_remaining(global_deadline, "sanity gate") - 2.0,
        )
        if gate_deadline <= 0:
            raise TrainingBudgetExceeded("the fixed sanity gate has no remaining first-seed time budget")
        try:
            gate = run_overfit_gate(
                gate_model, sanity_rows, seed=config.seeds[0], max_updates=500,
                max_seconds=gate_deadline,
                learning_rate=config.learning_rate,
                weight_decay=config.weight_decay,
                gradient_clip_norm=config.gradient_clip_norm,
            )
        except Exception as exc:
            gate = {
                "status": "ERROR",
                "seed": config.seeds[0],
                "sample_ids": list(selected_ids),
                "sample_id_count": len(selected_ids),
                "updates": None,
                "error": {"type": type(exc).__name__, "message": str(exc)},
                "thresholds": {"cross_entropy_max": 0.05, "legal_top1_accuracy_min": 0.99, "max_updates": 500},
            }
            _json_write(root / "sanity_gate.json", gate)
            raise
        gate["seed_model_initialization"] = "deterministic seed 20261022 before model construction"
        gate["started_at_utc"] = gate_started_at_utc
        gate["sample_ids_sha256"] = hashlib.sha256("\n".join(selected_ids).encode()).hexdigest()
        _json_write(root / "sanity_gate.json", gate)
        manifest["sanity_gate"] = {
            "status": gate["status"],
            "seed": gate["seed"],
            "updates": gate["updates"],
            "passed_at_update": gate["passed_at_update"],
            "final": gate["final"],
            "duration_seconds": gate["duration_seconds"],
            "sample_id_count": gate["sample_id_count"],
            "sample_ids_file": "sanity_gate.json",
            "sample_ids_sha256": gate["sample_ids_sha256"],
            "thresholds": gate["thresholds"],
        }
        manifest["execution_elapsed_seconds"] = time.monotonic() - started_mono
        manifest["elapsed_seconds_including_prior_release_verification"] = (
            used_before_this_run + time.monotonic() - started_mono
        )
        _json_write(root / "run_manifest.json", manifest)
        _event(root, "sanity_gate_finished", **manifest["sanity_gate"])
        if gate["status"] != "PASS":
            manifest["status"] = "sanity_gate_failed" if gate["status"] == "FAIL" else "sanity_gate_incomplete"
            manifest["failure"] = {
                "reason": "128-example overfit gate did not meet both fixed thresholds within 500 updates",
                "gate_status": gate["status"],
            }
            exit_code = 2
            return exit_code

        stage("bounded_seed_training", seeds=list(config.seeds))
        for seed_index, seed in enumerate(config.seeds):
            aggregate_remaining = _assert_remaining(global_deadline, f"seed {seed}")
            seed_budget_started = gate_started if seed_index == 0 else time.monotonic()
            seed_prior = prior_seed_usage.get(seed, 0.0)
            seed_used = seed_prior + time.monotonic() - seed_budget_started
            seed_remaining = min(SEED_LIMIT_SECONDS - seed_used, aggregate_remaining - 2.0)
            if seed_remaining <= 0:
                manifest["seed_runs"].append({
                    "seed": seed, "status": "not_started_budget", "reason": "no authorized per-seed time remained",
                })
                break
            determinism = configure_determinism(seed)
            model = BehaviorScorer(model_config)
            seed_config = TrainingConfig(
                max_seconds_per_seed=max(0, int(min(
                    SEED_LIMIT_SECONDS - seed_prior - (time.monotonic() - seed_budget_started) - 2.0,
                    global_deadline - time.monotonic() - 2.0,
                ))),
            )
            if seed_config.max_seconds_per_seed < 1:
                manifest["seed_runs"].append({
                    "seed": seed, "status": "not_started_budget",
                    "reason": "reserved per-seed safety margin left less than one training second",
                })
                break
            checkpoint_path = root / "checkpoints" / f"seed-{seed}-validation-best.pt"

            def save_best(
                epoch: int,
                candidate_model: BehaviorScorer,
                optimizer: torch.optim.Optimizer,
                epoch_record: dict[str, Any],
            ) -> None:
                del epoch
                _save_epoch_checkpoint(
                    checkpoint_path, candidate_model, optimizer, epoch_record,
                    revision=revision, worktree_dirty=dirty, seed=seed, dataset=dataset, config=seed_config,
                    run_id=run_id,
                )

            stage("seed_training", seed=seed, prior_seed_seconds=seed_prior)
            seed_started = time.monotonic()
            try:
                fit = fit_seed(
                    model, dataset.train, dataset.validation,
                    seed=seed, config=seed_config, on_best=save_best,
                )
            except Exception as exc:
                failed_seed_record = {
                    "seed": seed,
                    "status": "failed",
                    "determinism": determinism,
                    "training_config": seed_config.as_json(),
                    "duration_seconds": time.monotonic() - seed_started,
                    "seed_elapsed_including_gate_seconds": time.monotonic() - seed_budget_started,
                    "seed_elapsed_including_gate_and_prior_attempts_seconds": (
                        seed_prior + time.monotonic() - seed_budget_started
                    ),
                    "exception": {"type": type(exc).__name__, "message": str(exc)},
                    "checkpoint_path": checkpoint_path.relative_to(root).as_posix() if checkpoint_path.exists() else None,
                    "checkpoint_manifest": verify_checkpoint(checkpoint_path) if checkpoint_path.exists() else None,
                }
                _json_write(root / f"seed-{seed}.json", failed_seed_record)
                manifest["seed_runs"].append(failed_seed_record)
                _event(root, "seed_failed", **failed_seed_record)
                _json_write(root / "run_manifest.json", manifest)
                raise
            seed_record = {
                "seed": seed,
                "status": (
                    "complete" if fit.best_epoch is not None and fit.stop_reason in {"maximum_epochs", "validation_patience"}
                    else "budget_limited_with_validation_checkpoint" if fit.best_epoch is not None
                    else "no_validation_checkpoint"
                ),
                "determinism": determinism,
                "training_config": seed_config.as_json(),
                "epochs": fit.epoch_history,
                "best_epoch": fit.best_epoch,
                "best_validation_nll": fit.best_validation_nll,
                "stop_reason": fit.stop_reason,
                "optimizer_updates": fit.optimizer_updates,
                "duration_seconds": fit.duration_seconds,
                "seed_elapsed_including_gate_seconds": time.monotonic() - seed_budget_started,
                "seed_elapsed_including_gate_and_prior_attempts_seconds": (
                    seed_prior + time.monotonic() - seed_budget_started
                ),
                "peak_rss_bytes": peak_rss_bytes(),
                "checkpoint_path": checkpoint_path.relative_to(root).as_posix() if checkpoint_path.exists() else None,
                "checkpoint_manifest": verify_checkpoint(checkpoint_path) if checkpoint_path.exists() else None,
            }
            _json_write(root / f"seed-{seed}.json", seed_record)
            manifest["seed_runs"].append(seed_record)
            manifest["active_seed"] = None
            manifest["execution_elapsed_seconds"] = time.monotonic() - started_mono
            manifest["elapsed_seconds_including_prior_release_verification"] = (
                used_before_this_run + time.monotonic() - started_mono
            )
            _event(root, "seed_finished", seed=seed, status=seed_record["status"],
                   best_epoch=fit.best_epoch, best_validation_nll=fit.best_validation_nll,
                   stop_reason=fit.stop_reason, duration_seconds=fit.duration_seconds)
            _json_write(root / "run_manifest.json", manifest)
            if peak_rss_bytes() > PROCESS_RSS_LIMIT_BYTES:
                raise TrainingBudgetExceeded(f"process peak RSS exceeded 2 GiB after seed {seed}")
            if seed_prior + time.monotonic() - seed_budget_started > SEED_LIMIT_SECONDS:
                raise TrainingBudgetExceeded(f"seed {seed} exceeded its recorded hard time budget")

        completed_runs = [
            result for result in manifest["seed_runs"]
            if result.get("best_validation_nll") is not None and result.get("checkpoint_path")
        ]
        if not completed_runs:
            raise ExperimentStop("no seed produced a validation-selected checkpoint")
        incomplete_seeds = [
            result for result in manifest["seed_runs"] if result.get("status") != "complete"
        ]
        missing_seeds = [
            seed for seed in config.seeds
            if seed not in {result.get("seed") for result in manifest["seed_runs"]}
        ]
        if incomplete_seeds or missing_seeds:
            manifest["status"] = "incomplete_seed_training"
            manifest["failure"] = {
                "reason": "the fixed CPU seed protocol did not complete every configured seed",
                "incomplete_seed_runs": incomplete_seeds,
                "not_started_seed_ids": missing_seeds,
            }
            _event(root, "training_protocol_incomplete", **manifest["failure"])
            exit_code = 2
            return exit_code
        selected = min(completed_runs, key=lambda item: (item["best_validation_nll"], item["seed"]))
        _assert_remaining(global_deadline, "frozen test evaluation")
        stage("freeze_validation_selected_checkpoint", selected_seed=selected["seed"],
              best_epoch=selected["best_epoch"], validation_nll=selected["best_validation_nll"])
        selected_source = root / selected["checkpoint_path"]
        frozen_path = root / "pretrained-behavior-only.pt"
        shutil.copyfile(selected_source, frozen_path)
        selected_sidecar = selected_source.with_suffix(selected_source.suffix + ".manifest.json")
        frozen_sidecar = frozen_path.with_suffix(frozen_path.suffix + ".manifest.json")
        shutil.copyfile(selected_sidecar, frozen_sidecar)
        frozen_sidecar_data = json.loads(frozen_sidecar.read_text(encoding="utf-8"))
        frozen_sidecar_data["checkpoint_file"] = frozen_path.name
        _json_write(frozen_sidecar, frozen_sidecar_data)
        frozen_integrity = verify_checkpoint(frozen_path)
        frozen_model, frozen_bundle = load_checkpoint(
            frozen_path,
            expected_release_id=EXPECTED_RELEASE_ID,
            expected_split_sha256=EXPECTED_SPLIT_SHA256,
        )
        if selected["best_epoch"] != frozen_bundle["metadata"].get("selected_epoch_for_seed"):
            raise ValueError("frozen checkpoint epoch differs from validation-selected epoch")
        manifest["selected_checkpoint"] = {
            "path": frozen_path.name,
            "sha256": frozen_integrity["checkpoint_sha256"],
            "size_bytes": frozen_integrity["checkpoint_size_bytes"],
            "manifest": frozen_integrity,
            "seed": selected["seed"],
            "epoch": selected["best_epoch"],
            "validation_nll": selected["best_validation_nll"],
            "selection_rule": "minimum validation NLL across seeds; ties select the lower seed; test split not inspected",
            "checkpoint_role": "pretrained behavior-only; no Q-values",
        }
        _json_write(root / "selected_checkpoint.json", manifest["selected_checkpoint"])

        _assert_remaining(global_deadline, "one-time test evaluation")
        stage("single_frozen_test_evaluation", selected_seed=selected["seed"], selected_epoch=selected["best_epoch"])
        test_started = time.perf_counter()
        test_metrics = evaluate_examples(
            frozen_model, dataset.test, batch_size=64, include_strata=True,
            max_seconds=_assert_remaining(global_deadline, "test evaluation") - 2.0,
        )
        if peak_rss_bytes() > PROCESS_RSS_LIMIT_BYTES:
            raise TrainingBudgetExceeded("process peak RSS exceeded 2 GiB during final test evaluation")
        test_record = {
            "evaluated_once": True,
            "selected_seed": selected["seed"],
            "selected_epoch": selected["best_epoch"],
            "checkpoint_sha256": frozen_integrity["checkpoint_sha256"],
            "metrics": test_metrics,
            "duration_seconds": time.perf_counter() - test_started,
            "selection_used_test_metrics": False,
        }
        _json_write(root / "test_evaluation.json", test_record)
        manifest["test_evaluation"] = test_record

        engine_free = _inference_only_subprocess(
            repo, frozen_path, frozen_integrity["checkpoint_sha256"],
            timeout_seconds=min(
                60.0,
                max(1.0, _assert_remaining(global_deadline, "engine-free inference") - 5.0),
            ),
        )
        _json_write(root / "engine_free_inference.json", engine_free)
        manifest["engine_free_inference"] = engine_free

        _assert_remaining(global_deadline, "inference profiling")
        stage("inference_resource_profile")
        inference_profile = _profile_inference(
            frozen_model, dataset.train,
            max_seconds=_assert_remaining(global_deadline, "inference profiling") - 2.0,
        )
        manifest["inference_profile"] = inference_profile

        _assert_remaining(global_deadline, "simulator evaluation")
        stage("bounded_40_game_simulator_evaluation")
        simulator_seconds = min(
            SIMULATOR_LIMIT_SECONDS,
            _assert_remaining(global_deadline, "simulator benchmark") - 5.0,
        )
        if simulator_seconds <= 0:
            raise TrainingBudgetExceeded("aggregate budget leaves no safe time for simulator evaluation")
        simulator_result = _simulator_benchmark(
            frozen_model, frozen_integrity["checkpoint_sha256"], max_seconds=simulator_seconds,
        )
        _json_write(root / "simulator_evaluation.json", simulator_result)
        manifest["simulator_evaluation"] = {
            key: value for key, value in simulator_result.items() if key != "games"
        }
        manifest["simulator_evaluation"]["games_file"] = "simulator_evaluation.json"
        manifest["resource_measurements"].update({
            "peak_rss_bytes": peak_rss_bytes(),
            "feature_payload_bytes": dataset.feature_payload_bytes,
            "model_state_tensor_bytes": sum(
                tensor.numel() * tensor.element_size() for tensor in frozen_model.state_dict().values()
            ),
            "checkpoint_size_bytes": frozen_integrity["checkpoint_size_bytes"],
            "model_parameter_count": frozen_model.trainable_parameter_count,
            "aggregate_elapsed_seconds_including_prior_release_verification": (
                used_before_this_run + time.monotonic() - started_mono
            ),
            "aggregate_budget_remaining_seconds": max(0.0, global_deadline - time.monotonic()),
        })
        if simulator_result["status"] == "complete":
            manifest["status"] = "completed"
            exit_code = 0
        elif simulator_result["status"] == "incomplete_allowed_time_or_resource_limit":
            manifest["status"] = "incomplete_simulator_budget"
            manifest["limitations"] = [
                "The prescribed 40-game simulator set was interrupted by its authorized 20-minute or aggregate budget; only recorded games are reported."
            ]
            exit_code = 2
        else:
            raise ExperimentStop("simulator benchmark recorded a policy/integrity failure")
    except KeyboardInterrupt:
        manifest["status"] = "interrupted"
        manifest["failure"] = {"type": "KeyboardInterrupt", "stage": manifest["current_stage"]}
        exit_code = 130
    except Exception as exc:
        manifest["status"] = "failed_or_budget_stopped"
        manifest["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "stage": manifest["current_stage"],
        }
        _event(root, "run_stopped", **manifest["failure"])
        print(f"M4 run stopped at {manifest['current_stage']}: {type(exc).__name__}: {exc}", file=sys.stderr)
        exit_code = 2 if isinstance(exc, (TrainingBudgetExceeded, ExperimentStop)) else 1
    finally:
        manifest["ended_at_utc"] = _utc_now()
        manifest["execution_elapsed_seconds"] = time.monotonic() - started_mono
        manifest["elapsed_seconds_including_prior_release_verification"] = (
            used_before_this_run + time.monotonic() - started_mono
        )
        manifest["resource_measurements"]["peak_rss_bytes"] = peak_rss_bytes()
        _json_write(root / "run_manifest.json", manifest)
        artifact_manifest = write_artifact_manifest(root)
        print(json.dumps({
            "run_id": run_id,
            "status": manifest["status"],
            "artifact_directory": str(root),
            "source_revision": revision,
            "elapsed_seconds_including_prior_release_verification": manifest["elapsed_seconds_including_prior_release_verification"],
            "peak_rss_bytes": manifest["resource_measurements"]["peak_rss_bytes"],
            "artifact_file_count": len(artifact_manifest["files"]),
        }, sort_keys=True))
    return exit_code


def verify_artifacts(args: argparse.Namespace) -> int:
    root = Path(args.directory).expanduser().resolve(strict=True)
    artifact_manifest = verify_artifact_manifest(root)
    run_path = root / "run_manifest.json"
    run_manifest = json.loads(run_path.read_text(encoding="utf-8"))
    if run_manifest.get("schema") != RUN_SCHEMA:
        raise ValueError("unsupported M4 run manifest schema")
    selected = run_manifest.get("selected_checkpoint")
    checkpoint_result = None
    if selected:
        checkpoint = root / selected["path"]
        checkpoint_result = verify_checkpoint(checkpoint)
        if checkpoint_result.get("checkpoint_sha256") != selected.get("sha256"):
            raise ValueError("selected checkpoint checksum differs from the run manifest")
        loaded_model, bundle = load_checkpoint(
            checkpoint,
            expected_release_id=EXPECTED_RELEASE_ID,
            expected_split_sha256=EXPECTED_SPLIT_SHA256,
        )
        if loaded_model.trainable_parameter_count != selected.get("manifest", {}).get("parameter_count"):
            raise ValueError("selected checkpoint parameter count differs from its run record")
        if bundle["metadata"].get("teacher_scores_or_targets_used") is not False:
            raise ValueError("selected checkpoint does not attest to the behavior-only target protocol")
    print(json.dumps({
        "artifact_directory": str(root),
        "artifact_files_verified": len(artifact_manifest["files"]),
        "run_status": run_manifest.get("status"),
        "checkpoint": checkpoint_result,
    }, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m videochess_rl.model.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="verify the accepted M3 release and run bounded M4")
    run_parser.add_argument("--release-dir", type=Path, default=RELEASE_PATH)
    run_parser.add_argument(
        "--artifact-root", type=Path,
        default=Path("/home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4"),
    )
    run_parser.add_argument("--run-id")
    run_parser.set_defaults(handler=run_experiment)
    verify_parser = commands.add_parser("verify-artifacts", help="verify M4 run and checkpoint hashes")
    verify_parser.add_argument("directory", type=Path)
    verify_parser.set_defaults(handler=verify_artifacts)
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
