"""Frozen 1,500-game simulator evaluation and crossed paired summaries."""

from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass
from typing import Any, Sequence

import chess
import torch

from videochess_rl.baselines import RandomLegalAgent, SimpleHeuristicAgent
from videochess_rl.model.features import encode_board, replay_observation_history
from videochess_rl.model.inference import BehaviorPolicy, select_legal_candidate
from videochess_rl.model.dataset import collate_examples, model_inputs
from videochess_rl.rl.network import QScorer
from videochess_rl.simulator import ChessSimulator

EVALUATION_SEEDS = tuple(range(20261130, 20261155))
OPPONENTS = ("random_legal", "simple_material_heuristic")


class QPolicy:
    policy_id = "m5_double_dqn_frozen"

    def __init__(self, model: QScorer, *, policy_id: str, checkpoint_sha256: str) -> None:
        self.model = model.to("cpu").eval()
        self.policy_id = policy_id
        self.checkpoint_sha256 = checkpoint_sha256

    @property
    def config(self) -> dict[str, Any]:
        return {"checkpoint_sha256": self.checkpoint_sha256, "epsilon": 0.0, "gradients": False,
                "replay_insertion": False, "stockfish": "not imported or called"}

    @torch.inference_mode()
    def choose_move(self, observation: Any, legal_moves: Sequence[chess.Move], rng: random.Random) -> chess.Move:
        del rng
        board = replay_observation_history(observation.history_uci)
        if board.fen(en_passant="fen") != observation.fen or board.turn != observation.agent_color:
            raise ValueError("evaluation observation is inconsistent with complete legal history")
        expected = tuple(sorted(move.uci() for move in board.legal_moves))
        supplied = tuple(sorted(move.uci() for move in legal_moves))
        if expected != tuple(observation.legal_moves_uci) or supplied != expected:
            raise ValueError("evaluation legal UCI candidate set is stale or mismatched")
        features = encode_board(board, split="evaluation")
        batch = collate_examples((features,), require_targets=False)
        scores = self.model(**model_inputs(batch))[0]
        action = select_legal_candidate(scores, batch["candidate_mask"][0], features.candidate_uci)
        return chess.Move.from_uci(action)


def _scenario_seed(seed: int, opponent: str, color: chess.Color) -> int:
    payload = f"m5-eval-v2\0{seed}\0{opponent}\0{'white' if color else 'black'}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & ((1 << 63) - 1)


def planned_scenarios() -> tuple[dict[str, Any], ...]:
    rows = []
    for seed in EVALUATION_SEEDS:
        for opponent in OPPONENTS:
            for color in (chess.WHITE, chess.BLACK):
                rows.append({"evaluation_seed": seed, "opponent_id": opponent,
                             "agent_color": "white" if color else "black",
                             "scenario_seed": _scenario_seed(seed, opponent, color)})
    assert len(rows) == 100
    return tuple(rows)


def require_evaluation_snapshot_stage(metadata: dict[str, Any], expected: str) -> None:
    """Require exact roster stage identity before constructing a policy."""
    if metadata.get("stage") != expected:
        raise ValueError("snapshot stage identity does not match the evaluation roster")


def evaluate_policy(policy: Any, *, policy_id: str, max_decisions: int = 400,
                    seeds: Sequence[int] = EVALUATION_SEEDS, max_wall_seconds: float = 2400.0,
                    scenario_keys: set[tuple[int,str,str]] | None = None,
                    progress_callback: Any = None, on_scenario_event: Any = None,
                    attempt_id: str = "evaluation-attempt-0000") -> list[dict[str, Any]]:
    if max_decisions != 400:
        raise ValueError("official evaluation decision cap is frozen at 400")
    records = []
    deadline=time.monotonic()+max_wall_seconds
    deadline_reached=False
    for seed in seeds:
        for opponent_id in OPPONENTS:
            opponent_cls = RandomLegalAgent if opponent_id == "random_legal" else SimpleHeuristicAgent
            for color in (chess.WHITE, chess.BLACK):
                color_id="white" if color else "black"
                if scenario_keys is not None and (seed,opponent_id,color_id) not in scenario_keys:
                    continue
                if time.monotonic() >= deadline:
                    deadline_reached=True
                    break
                scenario_seed = _scenario_seed(seed, opponent_id, color)
                scenario_attempt_id = f"{attempt_id}:{seed}:{opponent_id}:{color_id}"
                simulator = ChessSimulator(opponent_cls(), max_decisions=max_decisions)
                start_event={"policy_id":policy_id,"evaluation_seed":seed,"opponent_id":opponent_id,
                    "agent_color":color_id,"scenario_seed":scenario_seed,
                    "scenario_attempt_id":scenario_attempt_id,"evaluation_attempt_id":attempt_id}
                if on_scenario_event is not None:
                    on_scenario_event("scenario_started",start_event)
                obs = simulator.reset(seed=scenario_seed, opponent_seed=scenario_seed, agent_color=color)
                agent_rng = random.Random(scenario_seed ^ 0x4D354556)
                while True:
                    if time.monotonic() >= deadline:
                        row={"policy_id":policy_id,"evaluation_seed":seed,"opponent_id":opponent_id,
                            "agent_color":"white" if color else "black","scenario_seed":scenario_seed,
                            "scenario_attempt_id":scenario_attempt_id,"evaluation_attempt_id":attempt_id,
                            "status":"incomplete_policy_deadline","truncated":None,"agent_reward":None,
                            "agent_decisions":simulator.episode_decisions,"plies":simulator.episode_plies,
                            "history_uci":list(obs.history_uci),"metric_source":"python_chess_m2_simulator"}
                        records.append(row)
                        if on_scenario_event is not None:
                            on_scenario_event("scenario_incomplete",{"scenario_attempt_id":scenario_attempt_id,"row":row})
                        deadline_reached=True
                        break
                    action = policy.choose_move(obs, simulator.legal_moves, agent_rng)
                    step = simulator.step(action)
                    obs = step.observation
                    if progress_callback is not None:
                        progress_callback({"scenario_attempt_id":scenario_attempt_id,
                            "evaluation_seed":seed,"opponent_id":opponent_id,"agent_color":color_id,
                            "scenario_seed":scenario_seed,"agent_decisions":simulator.episode_decisions,
                            "plies":simulator.episode_plies,"history_uci":list(obs.history_uci)})
                    if step.terminated or step.truncated:
                        break
                if deadline_reached:
                    break
                row={
                    "policy_id": policy_id, "evaluation_seed": seed, "opponent_id": opponent_id,
                    "status":"completed_game",
                    "agent_color": "white" if color else "black", "scenario_seed": scenario_seed,
                    "scenario_attempt_id":scenario_attempt_id,"evaluation_attempt_id":attempt_id,
                    "agent_reward": step.reward, "result": step.outcome_result,
                    "termination_reason": step.outcome_reason, "truncated": step.truncated,
                    "truncation_reason": step.truncation_reason,
                    "agent_decisions": step.episode_decisions,
                    "plies": step.episode_plies, "history_uci": list(step.history_uci),
                    "metric_source": "python_chess_m2_simulator",
                    "game_id": hashlib.sha256(f"{policy_id}|{seed}|{opponent_id}|{color}".encode()).hexdigest(),
                }
                records.append(row)
                if on_scenario_event is not None:
                    on_scenario_event("scenario_completed",{"scenario_attempt_id":scenario_attempt_id,"row":row})
                if deadline_reached: break
            if deadline_reached: break
        if deadline_reached: break
    return records


def summarize_games(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    games=[r for r in rows if r.get("status")=="completed_game"]
    completed = [r for r in games if not r.get("truncated")]
    score = sum((float(r["agent_reward"]) + 1.0) / 2.0 for r in completed)
    wins = sum(r["agent_reward"] == 1.0 and not r.get("truncated") for r in games)
    losses = sum(r["agent_reward"] == -1.0 and not r.get("truncated") for r in games)
    draws = sum(r["agent_reward"] == 0.0 and not r.get("truncated") for r in games)
    return {"game_rows": len(games), "incomplete_scenarios":len(rows)-len(games),
            "completed_games": len(completed), "truncated_games": len(games)-len(completed),
            "wins": wins, "draws": draws, "losses": losses,
            "score_rate_completed": score / len(completed) if completed else None,
            "mean_reward_all_rows": sum(float(r["agent_reward"]) for r in games)/len(games) if games else None}


def crossed_cluster_bootstrap(differences: Sequence[dict[str, Any]], *, iterations: int = 10000,
                              seed: int = 20261160) -> dict[str, Any]:
    """Resample 3 training-seed and 25 evaluation-seed clusters, not game rows."""
    if not differences:
        raise ValueError("paired differences are required")
    train_ids = sorted({str(r["training_seed"]) for r in differences})
    eval_ids = sorted({int(r["evaluation_seed"]) for r in differences})
    if len(train_ids) != 3 or len(eval_ids) != 25:
        raise ValueError("official crossed bootstrap expects three training and 25 evaluation clusters")
    grouped: dict[tuple[str, int], list[float]] = {}
    for row in differences:
        key = (str(row["training_seed"]), int(row["evaluation_seed"]))
        grouped.setdefault(key, []).append(float(row["difference"]))
    point = sum(sum(v)/len(v) for v in grouped.values()) / len(grouped)
    rng = random.Random(seed)
    estimates = []
    for _ in range(iterations):
        ts = [rng.choice(train_ids) for _ in train_ids]
        es = [rng.choice(eval_ids) for _ in eval_ids]
        values = [x for t in ts for e in es for x in grouped.get((t, e), ())]
        if values: estimates.append(sum(values)/len(values))
    estimates.sort()
    return {"point_difference": point, "ci_95_crossed_cluster": [estimates[int(.025*len(estimates))], estimates[min(len(estimates)-1,int(.975*len(estimates)))]] if estimates else None,
            "iterations": iterations, "training_seed_clusters": len(train_ids),
            "evaluation_seed_clusters": len(eval_ids), "few_training_cluster_caveat": True}


def evaluation_seed_cluster_bootstrap(differences: Sequence[dict[str,Any]], *, iterations:int=10000,
                                      seed:int=20261161) -> dict[str,Any]:
    """Paired fixed-policy interval resampling evaluation-seed clusters."""
    if not differences: raise ValueError("paired differences are required")
    eval_ids=sorted({int(r["evaluation_seed"]) for r in differences})
    if len(eval_ids)!=25: raise ValueError("fixed-policy comparison requires all 25 evaluation-seed clusters")
    grouped={key:[float(r["difference"]) for r in differences if int(r["evaluation_seed"])==key] for key in eval_ids}
    point=sum(sum(v)/len(v) for v in grouped.values())/len(grouped)
    rng=random.Random(seed); estimates=[]
    for _ in range(iterations):
        clusters=[rng.choice(eval_ids) for _ in eval_ids]
        values=[x for cluster in clusters for x in grouped[cluster]]
        estimates.append(sum(values)/len(values))
    estimates.sort()
    return {"point_difference":point,"ci_95_evaluation_seed_cluster":[estimates[int(.025*iterations)],estimates[min(iterations-1,int(.975*iterations))]],
            "iterations":iterations,"evaluation_seed_clusters":25}


def paired_white_black_comparison(rows: Sequence[dict[str, Any]], *, iterations: int = 10000,
                                  seed: int = 20261162) -> dict[str, Any]:
    """Compare color-matched scores within evaluation-seed clusters.

    A paired difference is white-agent score minus black-agent score for the
    same evaluation seed and opponent. Truncated and unfinished games are
    censored. Bootstrap resamples the 25 evaluation-seed clusters, retaining
    both opponent contrasts within each cluster.
    """
    indexed: dict[tuple[int, str, str], dict[str, Any]] = {}
    for row in rows:
        if row.get("status") == "completed_game":
            key = (int(row["evaluation_seed"]), str(row["opponent_id"]), str(row["agent_color"]))
            indexed.setdefault(key, row)

    def contrasts(opponents: Sequence[str], bootstrap_seed: int) -> dict[str, Any]:
        differences: list[dict[str, Any]] = []
        planned = 25 * len(opponents)
        for evaluation_seed in EVALUATION_SEEDS:
            for opponent in opponents:
                white = indexed.get((evaluation_seed, opponent, "white"))
                black = indexed.get((evaluation_seed, opponent, "black"))
                if white is None or black is None or white.get("truncated") or black.get("truncated"):
                    continue
                differences.append({"evaluation_seed": evaluation_seed, "opponent_id": opponent,
                    "difference": (float(white["agent_reward"]) - float(black["agent_reward"])) / 2.0})
        complete = len(differences) == planned
        interval = None
        if complete and len({row["evaluation_seed"] for row in differences}) == 25:
            interval = evaluation_seed_cluster_bootstrap(differences, iterations=iterations, seed=bootstrap_seed)
        return {"matched_color_pairs": len(differences), "planned_color_pairs": planned,
                "censored_or_unfinished_pairs": planned - len(differences),
                "mean_white_minus_black_score": sum(row["difference"] for row in differences) / len(differences)
                    if differences else None,
                "evaluation_seed_cluster_bootstrap": interval,
                "interval_status": "computed" if interval else "incomplete_or_censored_pair_set"}

    opponent_results = {opponent: contrasts((opponent,), seed + index)
                        for index, opponent in enumerate(OPPONENTS)}
    return {"comparison": "white_agent_minus_black_agent_score", **contrasts(OPPONENTS, seed),
            "opponent_results": opponent_results,
            "pairing_keys": ["evaluation_seed", "opponent_id", "agent_color"]}


def paired_capped_reward_differences(rows_a: Sequence[dict[str, Any]],
                                     rows_b: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pair complete scheduled scenarios using observed capped simulator reward.

    This includes valid 400-decision truncations with their actual simulator
    reward (zero); it never converts a truncated game into a terminal W/D/L.
    A missing or duplicate scenario rejects the comparison instead of being
    silently dropped.
    """
    def index(rows: Sequence[dict[str, Any]]) -> dict[tuple[int, str, str], dict[str, Any]]:
        result: dict[tuple[int, str, str], dict[str, Any]] = {}
        for row in rows:
            if row.get("status") != "completed_game":
                continue
            key = (int(row["evaluation_seed"]), str(row["opponent_id"]), str(row["agent_color"]))
            if key in result:
                raise ValueError(f"duplicate evaluation scenario in capped-reward comparison: {key}")
            reward = float(row["agent_reward"])
            if reward not in (-1.0, 0.0, 1.0):
                raise ValueError(f"invalid simulator reward in capped-reward comparison: {reward}")
            if row.get("truncated") and reward != 0.0:
                raise ValueError("valid time-limit truncation must retain its observed zero simulator reward")
            result[key] = row
        return result

    indexed_a, indexed_b = index(rows_a), index(rows_b)
    if set(indexed_a) != set(indexed_b):
        raise ValueError("paired capped-reward comparison requires identical completed scenario keys")
    if len(indexed_a) != 100:
        raise ValueError("official capped-reward comparison requires all 100 scenarios for both policies")
    return [{"evaluation_seed": key[0], "opponent_id": key[1], "agent_color": key[2],
             "difference": (float(indexed_a[key]["agent_reward"]) -
                            float(indexed_b[key]["agent_reward"])) / 2.0,
             "a_truncated": bool(indexed_a[key].get("truncated")),
             "b_truncated": bool(indexed_b[key].get("truncated"))}
            for key in sorted(indexed_a)]
