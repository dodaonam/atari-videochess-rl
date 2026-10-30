"""Double DQN optimization and fixed-color simulator training loop."""

from __future__ import annotations

import hashlib
import json
import math
import random
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import chess
import numpy as np
import torch
from torch import nn

from videochess_rl.baselines import RandomLegalAgent, SimpleHeuristicAgent
from videochess_rl.model.dataset import collate_examples, model_inputs
from videochess_rl.model.features import PositionFeatures, encode_board, replay_observation_history
from videochess_rl.m5_seeding import paired_seed_schedule, pair_identity, run_identity
from videochess_rl.rl.network import QScorer, clone_target
from videochess_rl.rl.replay import ReplayBuffer
from videochess_rl.rl.targets import double_dqn_target
from videochess_rl.rl.transition import Transition
from videochess_rl.simulator import ChessSimulator


@lru_cache(maxsize=2048)
def _features(history: tuple[str, ...]) -> PositionFeatures:
    return encode_board(replay_observation_history(history), split="replay")


def _batch(features: tuple[PositionFeatures, ...], device: torch.device) -> dict[str, Any]:
    values = collate_examples(features, require_targets=False)
    for key, value in tuple(values.items()):
        if isinstance(value, torch.Tensor):
            values[key] = value.to(device)
    return model_inputs(values)


def epsilon_at(decisions: int, *, start: float = 1.0, end: float = 0.05, decay: int = 37500) -> float:
    if type(decisions) is not int or decisions < 0 or decay < 1 or not 0 <= end <= start <= 1:
        raise ValueError("invalid epsilon schedule")
    return end + (start - end) * max(0.0, 1.0 - decisions / decay)


@torch.inference_mode()
def select_action(model: QScorer, features: PositionFeatures, *, epsilon: float, rng: random.Random, device: torch.device) -> str:
    actions = features.candidate_uci
    if not actions or len(actions) != len(set(actions)) or actions != tuple(sorted(actions)):
        raise ValueError("action selection requires a nonempty unique sorted legal UCI set")
    if not 0 <= epsilon <= 1:
        raise ValueError("epsilon must be in [0,1]")
    if rng.random() < epsilon:
        return rng.choice(actions)
    scores = model(**_batch((features,), device))[0].detach().cpu().tolist()
    if len(scores) != len(actions) or any(not math.isfinite(float(x)) for x in scores):
        raise FloatingPointError("invalid legal candidate Q scores")
    return max(zip(actions, scores), key=lambda pair: (float(pair[1]), -actions.index(pair[0])))[0]


class DoubleDqnLearner:
    def __init__(self, online: QScorer, *, seed: int, exploration_seed: int | None = None,
                 device: str = "cpu", config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.device = torch.device(device)
        self.online = online.to(self.device)
        self.target = clone_target(self.online).to(self.device)
        self.learning_rate = float(self.config.get("learning_rate", 1e-4))
        self.weight_decay = float(self.config.get("weight_decay", 1e-4))
        self.batch_size = int(self.config.get("batch_size", 32))
        self.replay_warmup = int(self.config.get("replay_warmup_transitions", 1024))
        self.update_interval = int(self.config.get("update_interval_decisions", 4))
        self.gamma = float(self.config.get("gamma", 0.99))
        self.target_sync_interval = int(self.config.get("target_sync_interval_gradient_updates", 500))
        self.gradient_clip_norm = float(self.config.get("gradient_clip_norm", 1.0))
        self.optimizer = torch.optim.AdamW(self.online.parameters(), lr=self.learning_rate, weight_decay=self.weight_decay)
        self.replay = ReplayBuffer(int(self.config.get("replay_capacity", 16384)), seed=seed)
        self.exploration_rng = random.Random(seed if exploration_seed is None else exploration_seed)
        self.valid_decisions = self.transitions = self.optimizer_updates = self.completed_episodes = self.target_syncs = 0
        self.invalid_transitions = 0

    def add_transition(self, row: Transition) -> None:
        self.replay.insert(row)
        self.transitions += 1

    def update(self, *, batch_size: int = 32, gamma: float = 0.99) -> dict[str, float | int] | None:
        batch_size = int(self.config.get("batch_size", batch_size))
        gamma = float(self.config.get("gamma", gamma))
        if len(self.replay) < max(batch_size, self.replay_warmup):
            return None
        rows = self.replay.sample(batch_size)
        current = tuple(_features(row.history_before) for row in rows)
        current_inputs = _batch(current, self.device)
        q_rows = self.online(**current_inputs)
        selected: list[torch.Tensor] = []
        for index, row in enumerate(rows):
            uci = current[index].candidate_uci
            if row.selected_uci not in uci:
                raise ValueError("sampled action is absent from its current legal semantic candidate set")
            selected.append(q_rows[index, uci.index(row.selected_uci)])
        selected_q = torch.stack(selected)
        targets: list[float] = []
        bootstrap_rows = [(i, row) for i, row in enumerate(rows) if not row.terminated]
        next_features = tuple(_features(row.history_after) for _, row in bootstrap_rows)
        online_next: list[torch.Tensor] = []
        target_next: list[torch.Tensor] = []
        if bootstrap_rows:
            next_inputs = _batch(next_features, self.device)
            with torch.no_grad():
                online_next = list(self.online(**next_inputs))
                target_next = list(self.target(**next_inputs))
        values: dict[int, float] = {}
        for j, (i, row) in enumerate(bootstrap_rows):
            actions = row.next_legal_actions
            if not actions:
                raise ValueError("nonterminal bootstrap state has no legal action")
            on_map = {uci: float(online_next[j][k].item()) for k, uci in enumerate(next_features[j].candidate_uci)}
            tar_map = {uci: float(target_next[j][k].item()) for k, uci in enumerate(next_features[j].candidate_uci)}
            result = double_dqn_target(reward=row.reward, gamma=gamma, terminated=False, truncated=row.truncated,
                                       legal_uci=actions, q_online_by_uci=on_map, q_target_by_uci=tar_map)
            values[i] = result.bellman_target
        for i, row in enumerate(rows):
            if row.terminated:
                targets.append(float(row.reward))
            else:
                targets.append(values[i])
        target_tensor = torch.tensor(targets, dtype=selected_q.dtype, device=self.device)
        loss = nn.functional.smooth_l1_loss(selected_q, target_tensor)
        if not torch.isfinite(loss):
            raise FloatingPointError("nonfinite Huber loss")
        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(self.online.parameters(), self.gradient_clip_norm)
        if not torch.isfinite(norm) or any(p.grad is not None and not torch.isfinite(p.grad).all() for p in self.online.parameters()):
            self.optimizer.zero_grad(set_to_none=True)
            raise FloatingPointError("nonfinite gradient")
        self.optimizer.step()
        if any(not torch.isfinite(p).all() for p in self.online.parameters()):
            raise FloatingPointError("optimizer produced nonfinite parameters")
        self.optimizer_updates += 1
        synced = 0
        if self.optimizer_updates % self.target_sync_interval == 0:
            self.target.load_state_dict(self.online.state_dict(), strict=True)
            self.target.eval()
            self.target_syncs += 1
            synced = 1
        return {"loss": float(loss.item()), "grad_norm": float(norm.item()), "update": self.optimizer_updates, "target_sync": synced}

    def step_decision(self, row: Transition) -> dict[str, float | int] | None:
        self.add_transition(row)
        self.valid_decisions += 1
        if self.valid_decisions % self.update_interval == 0:
            return self.update()
        return None


def run_training_episodes(learner: DoubleDqnLearner, *, training_seed: int, arm: str, run_id: str,
                          attempt_id: str, max_decisions: int = 50000, snapshot_dir: Path | None = None,
                          device: str = "cpu", on_transition: Any = None, stop_check: Any = None) -> dict[str, Any]:
    """Execute actual M2 decisions; snapshots never reset a live episode."""
    started = time.monotonic()
    episode_rows: list[dict[str, Any]] = []
    opponent_types = (RandomLegalAgent, SimpleHeuristicAgent, RandomLegalAgent, SimpleHeuristicAgent)
    colors = (chess.WHITE, chess.WHITE, chess.BLACK, chess.BLACK)
    last_transition_completed_episode = learner.valid_decisions == max_decisions and learner.completed_episodes > 0
    stop_reason = None
    while learner.valid_decisions < max_decisions:
        if stop_check is not None and stop_check():
            stop_reason = "resource_budget_headroom"
            break
        ep = learner.completed_episodes
        schedule = paired_seed_schedule("m5-double-dqn-paired-v1", training_seed, ep)
        pair_id = pair_identity("m5-double-dqn-paired-v1", training_seed)
        opponent = opponent_types[ep % len(opponent_types)]()
        simulator = ChessSimulator(opponent, max_decisions=400)
        observation = simulator.reset(seed=int(schedule["episode_seed"]), opponent_seed=int(schedule["opponent_rng_seed"]), agent_color=colors[ep % 4])
        episode_start = learner.valid_decisions
        while learner.valid_decisions < max_decisions:
            if stop_check is not None and stop_check():
                stop_reason = "resource_budget_headroom"
                break
            before = observation
            board = replay_observation_history(before.history_uci)
            features = _features(tuple(before.history_uci))
            epsilon = epsilon_at(learner.valid_decisions)
            action_uci = select_action(learner.online, features, epsilon=epsilon, rng=learner.exploration_rng, device=learner.device)
            result = simulator.step_uci(action_uci)
            row = Transition.from_step(before, result, run_id=run_id, attempt_id=attempt_id, episode_index=ep,
                                      decision_index=learner.valid_decisions, training_seed=training_seed,
                                      seed_schedule=schedule)
            update = learner.step_decision(row)
            observation = result.observation
            if result.terminated or result.truncated:
                learner.completed_episodes += 1
                last_transition_completed_episode = True
                episode_rows.append({"episode_index": ep, "decisions": learner.valid_decisions-episode_start,
                                     "reward": result.reward, "terminated": result.terminated,
                                     "truncated": result.truncated, "outcome": result.outcome_result,
                                     "reason": result.outcome_reason or result.truncation_reason})
            else:
                last_transition_completed_episode = False
            if on_transition is not None:
                should_stop = on_transition(learner, row, update)
                if should_stop:
                    stop_reason = "resource_budget_headroom"
            if result.terminated or result.truncated:
                break
            if stop_reason:
                break
        if stop_reason:
            break
        if learner.valid_decisions >= max_decisions:
            break
    return {"run_id": run_id, "attempt_id": attempt_id, "arm": arm, "training_seed": training_seed,
            "valid_decisions": learner.valid_decisions, "transitions": learner.transitions,
            "optimizer_updates": learner.optimizer_updates, "completed_episodes": learner.completed_episodes,
            "target_syncs": learner.target_syncs, "epsilon_final": epsilon_at(learner.valid_decisions),
            "wall_seconds": time.monotonic()-started, "episode_records": episode_rows,
            "stop_reason": stop_reason,
            "final_episode_incomplete": learner.valid_decisions == max_decisions and not last_transition_completed_episode}
