"""Pure semantic-UCI Double DQN target construction."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class DoubleDqnTarget:
    selected_uci: str | None
    target_value: float | None
    bellman_target: float


def double_dqn_target(
    *, reward: float, gamma: float, terminated: bool, truncated: bool,
    legal_uci: Sequence[str], q_online_by_uci: Mapping[str, float],
    q_target_by_uci: Mapping[str, float],
) -> DoubleDqnTarget:
    """Online net chooses; target net scores that exact legal semantic action."""
    if not math.isfinite(reward) or not math.isfinite(gamma) or not 0 <= gamma <= 1:
        raise ValueError("reward/gamma must be finite and gamma in [0,1]")
    if terminated and truncated:
        raise ValueError("a transition cannot be both terminal and truncated")
    if terminated:
        if legal_uci:
            raise ValueError("true terminal MDP bootstrap set must be empty")
        return DoubleDqnTarget(None, None, float(reward))
    if not legal_uci or len(set(legal_uci)) != len(legal_uci) or tuple(sorted(legal_uci)) != tuple(legal_uci):
        raise ValueError("nonterminal bootstrap requires a unique sorted legal UCI set")
    if set(q_online_by_uci) != set(legal_uci) or set(q_target_by_uci) != set(legal_uci):
        raise ValueError("online/target scores must cover exactly the same legal UCI actions")
    for score in (*q_online_by_uci.values(), *q_target_by_uci.values()):
        if not math.isfinite(float(score)):
            raise FloatingPointError("nonfinite candidate value")
    # Sorted iteration provides a deterministic lexical tie-break.
    selected = max(legal_uci, key=lambda uci: (float(q_online_by_uci[uci]), -legal_uci.index(uci)))
    target_value = float(q_target_by_uci[selected])
    return DoubleDqnTarget(selected, target_value, float(reward + gamma * target_value))
