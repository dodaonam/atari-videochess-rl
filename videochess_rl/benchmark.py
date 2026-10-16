"""Reproducible CPU benchmark for the M2 chess simulator baselines."""

from __future__ import annotations

import argparse
import json
import os
import platform
import random
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import chess

from .baselines import RandomLegalAgent, SimpleHeuristicAgent
from .simulator import ChessSimulator, MovePolicy


def _git_revision() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _working_tree_dirty() -> bool | None:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        return None
    return bool(result.stdout.strip())


def _play_game(
    *,
    agent: MovePolicy,
    opponent: MovePolicy,
    color: chess.Color,
    seed: int,
    agent_seed: int,
    max_decisions: int,
    source_revision: str | None,
) -> dict[str, object]:
    started = time.perf_counter()
    simulator = ChessSimulator(opponent, max_decisions=max_decisions)
    agent_rng = random.Random(agent_seed)
    observation = None
    result = None
    status = "external_failure"
    failure_type: str | None = None

    try:
        observation = simulator.reset(seed=seed, agent_color=color)
        while True:
            move = agent.choose_move(observation, simulator.legal_moves, agent_rng)
            result = simulator.step(move)
            observation = result.observation
            if result.terminated:
                status = "completed"
                break
            if result.truncated:
                status = "truncated"
                break
    except KeyboardInterrupt:
        status = "interrupted"
        failure_type = "KeyboardInterrupt"
    except Exception as exc:
        status = "external_failure"
        failure_type = type(exc).__name__

    history = (
        result.history_uci
        if result is not None
        else observation.history_uci
        if observation is not None
        else tuple(move.uci() for move in simulator.board.move_stack)
    )
    outcome_result = result.outcome_result if result is not None and result.terminated else None
    agent_result = result.reward if result is not None and result.terminated else None
    return {
        "status": status,
        "metric_source": "chess_simulator",
        "agent_policy": agent.policy_id,
        "agent_config": agent.config,
        "opponent_policy": opponent.policy_id,
        "opponent_config": opponent.config,
        "agent_color": "white" if color == chess.WHITE else "black",
        "seed": seed,
        "agent_policy_seed": agent_seed,
        "max_agent_decisions": max_decisions,
        "outcome_result_white_perspective": outcome_result,
        "agent_result": agent_result,
        "agent_wdl": (
            "win" if agent_result == 1.0 else "loss" if agent_result == -1.0 else "draw"
        ) if result is not None and result.terminated else None,
        "termination_reason": result.outcome_reason if result is not None and result.terminated else None,
        "terminated": bool(result is not None and result.terminated),
        "truncated": bool(result is not None and result.truncated),
        "truncation_reason": result.truncation_reason if result is not None else None,
        "external_failure_or_interruption": status in {"external_failure", "interrupted"},
        "failure_type": failure_type,
        "episode_decisions": result.episode_decisions if result is not None else 0,
        "episode_plies": result.episode_plies if result is not None else 0,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "moves_uci": list(history),
        "source_revision": source_revision,
        "ale_metrics_included": False,
    }


def _summarize(games: list[dict[str, object]]) -> dict[str, object]:
    by_policy: dict[str, dict[str, object]] = {}
    policy_ids = sorted({str(game["agent_policy"]) for game in games})
    for policy_id in policy_ids:
        policy_games = [game for game in games if game["agent_policy"] == policy_id]
        completed = [game for game in policy_games if game["status"] == "completed"]
        colors: dict[str, dict[str, int]] = {}
        for color in ("white", "black"):
            color_games = [game for game in completed if game["agent_color"] == color]
            colors[color] = {
                "games": len(color_games),
                "wins": sum(game["agent_wdl"] == "win" for game in color_games),
                "draws": sum(game["agent_wdl"] == "draw" for game in color_games),
                "losses": sum(game["agent_wdl"] == "loss" for game in color_games),
            }
        by_policy[policy_id] = {
            "games": len(policy_games),
            "completed_games": len(completed),
            "truncated_games": sum(game["status"] == "truncated" for game in policy_games),
            "external_failures": sum(game["status"] == "external_failure" for game in policy_games),
            "interruptions": sum(game["status"] == "interrupted" for game in policy_games),
            "wins": sum(game["agent_wdl"] == "win" for game in completed),
            "draws": sum(game["agent_wdl"] == "draw" for game in completed),
            "losses": sum(game["agent_wdl"] == "loss" for game in completed),
            "completed_mean_decisions": (
                round(sum(int(game["episode_decisions"]) for game in completed) / len(completed), 3)
                if completed
                else None
            ),
            "by_agent_color": colors,
        }
    return {
        "games": len(games),
        "completed_games": sum(game["status"] == "completed" for game in games),
        "truncated_games": sum(game["status"] == "truncated" for game in games),
        "external_failures": sum(game["status"] == "external_failure" for game in games),
        "interruptions": sum(game["status"] == "interrupted" for game in games),
        "by_agent_policy": by_policy,
    }


def run_baseline_benchmark(
    seeds: Sequence[int],
    *,
    max_decisions: int = 400,
    output_path: str | Path | None = None,
) -> dict[str, object]:
    """Play both baseline identities as White and Black for each input seed."""
    normalized_seeds = tuple(seeds)
    if not normalized_seeds:
        raise ValueError("at least one seed is required")
    if any(isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 for seed in normalized_seeds):
        raise ValueError("seeds must be non-negative integers")
    if max_decisions <= 0:
        raise ValueError("max_decisions must be positive")

    policies: tuple[MovePolicy, ...] = (RandomLegalAgent(), SimpleHeuristicAgent())
    source_revision = _git_revision()
    games: list[dict[str, object]] = []
    interrupted = False
    for seed_index, base_seed in enumerate(normalized_seeds):
        for agent_index, agent in enumerate(policies):
            opponent = policies[1 - agent_index]
            for color_index, color in enumerate((chess.WHITE, chess.BLACK)):
                game_seed = base_seed * 1009 + agent_index * 2 + color_index
                agent_seed = base_seed * 2027 + agent_index * 17 + color_index
                game = _play_game(
                    agent=agent,
                    opponent=opponent,
                    color=color,
                    seed=game_seed,
                    agent_seed=agent_seed,
                    max_decisions=max_decisions,
                    source_revision=source_revision,
                )
                game["seed_group"] = base_seed
                game["seed_index"] = seed_index
                games.append(game)
                if game["status"] == "interrupted":
                    interrupted = True
                    break
            if interrupted:
                break
        if interrupted:
            break

    created_at = datetime.now(timezone.utc)
    run = {
        "schema_version": 1,
        "run_id": created_at.strftime("m2-baseline-%Y%m%dT%H%M%SZ"),
        "created_at_utc": created_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "metric_source": "chess_simulator",
        "ale_metrics_included": False,
        "rating_claim": None,
        "configuration": {
            "base_seeds": list(normalized_seeds),
            "max_agent_decisions": max_decisions,
            "starting_position": "standard initial chess position",
            "agent_color_coverage": ["white", "black"],
            "pairings": [
                {"agent": policies[0].policy_id, "opponent": policies[1].policy_id},
                {"agent": policies[1].policy_id, "opponent": policies[0].policy_id},
            ],
            "seed_derivation": {
                "episode": "base_seed * 1009 + agent_policy_index * 2 + color_index",
                "agent_policy": "base_seed * 2027 + agent_policy_index * 17 + color_index",
            },
        },
        "runtime": {
            "python": sys.version.split()[0],
            "python_chess": chess.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
            "git_revision": source_revision,
            "git_worktree_dirty": _working_tree_dirty(),
        },
        "summary": _summarize(games),
        "games": games,
    }
    if output_path is not None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        run["output_path"] = output.as_posix()
        output.write_text(json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return run


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", default=[20261016, 20261017])
    parser.add_argument("--max-decisions", type=int, default=400)
    parser.add_argument("--output", type=Path, required=True, help="path for the per-game JSON report")
    args = parser.parse_args(argv)
    run = run_baseline_benchmark(args.seeds, max_decisions=args.max_decisions, output_path=args.output)
    print(json.dumps({key: run[key] for key in ("run_id", "runtime", "configuration", "summary", "output_path")}, indent=2, sort_keys=True))
    return 0 if run["summary"]["external_failures"] == 0 and run["summary"]["interruptions"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
