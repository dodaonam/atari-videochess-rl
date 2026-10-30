"""M5 Q model reusing the accepted M4 action-conditioned representation."""

from __future__ import annotations

import torch
from torch import nn

from videochess_rl.model.network import BehaviorScorer, M5TransferScorer, ModelConfig, initialize_q_head


class QScorer(M5TransferScorer):
    """Scalar Q(s,a) for each legal candidate, identified externally by UCI."""

    def forward(self, **inputs: object) -> torch.Tensor:
        return super().forward(**inputs)  # type: ignore[arg-type]


def make_warm_scorer(source: BehaviorScorer, *, q_head_seed: int) -> QScorer:
    if isinstance(source, M5TransferScorer):
        raise TypeError("warm start source must be an accepted M4 behavior model")
    transferred = initialize_q_head(source, seed=q_head_seed)
    target = QScorer(transferred.config, seed=q_head_seed)
    missing, unexpected = target.load_state_dict(transferred.state_dict(), strict=True)
    if missing or unexpected:
        raise RuntimeError(f"M4 transfer failed: {missing}, {unexpected}")
    return target


def make_scratch_scorer(*, representation_seed: int, q_head_seed: int, config: ModelConfig | None = None) -> QScorer:
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(representation_seed)
        initialized = QScorer(config or ModelConfig(), seed=q_head_seed)
    return initialized


def clone_target(online: QScorer) -> QScorer:
    target = QScorer(online.config, seed=0)
    target.load_state_dict(online.state_dict(), strict=True)
    target.requires_grad_(False)
    target.eval()
    return target
