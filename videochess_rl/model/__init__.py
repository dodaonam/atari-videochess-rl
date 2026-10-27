"""Versioned supervised-pretraining model interfaces.

M4 behavior logits are preferences over a supplied legal candidate set. They
are not values, rewards, or Double DQN outputs.
"""

from .features import INPUT_SCHEMA, PositionFeatures, encode_board
from .network import BehaviorScorer, M5TransferScorer, ModelConfig, initialize_q_head

__all__ = [
    "INPUT_SCHEMA",
    "BehaviorScorer",
    "M5TransferScorer",
    "ModelConfig",
    "PositionFeatures",
    "encode_board",
    "initialize_q_head",
]
