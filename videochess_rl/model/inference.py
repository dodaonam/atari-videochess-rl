"""Engine-free legal-candidate inference adapter for the M2 simulator."""

from __future__ import annotations

import random
import math
from typing import Sequence

import chess
import torch

from videochess_rl.action_contract import canonical_model_fen, legal_action_candidates
from videochess_rl.simulator import Observation

from .dataset import collate_examples, model_inputs
from .features import PositionFeatures, encode_board, replay_observation_history
from .network import BehaviorScorer


def select_legal_candidate(
    logits: torch.Tensor | Sequence[float],
    candidate_mask: torch.Tensor | Sequence[bool],
    candidate_uci: Sequence[str],
) -> str:
    scores = logits.detach().cpu().flatten().tolist() if isinstance(logits, torch.Tensor) else list(logits)
    mask = candidate_mask.detach().cpu().flatten().tolist() if isinstance(candidate_mask, torch.Tensor) else list(candidate_mask)
    if len(scores) != len(mask) or len(scores) != len(candidate_uci):
        raise ValueError("scores, masks, and semantic UCI candidates must have identical lengths")
    if not candidate_uci or not any(mask):
        raise ValueError("cannot select an action from an empty terminal legal set")
    if len(set(candidate_uci)) != len(candidate_uci) or tuple(candidate_uci) != tuple(sorted(candidate_uci)):
        raise ValueError("candidate UCI identities must be unique and lexically ordered")
    best_index: int | None = None
    best_score = float("-inf")
    for index, (score, is_legal) in enumerate(zip(scores, mask)):
        if not is_legal:
            continue
        value = float(score)
        if not math.isfinite(value):
            raise FloatingPointError("legal candidate score is non-finite")
        if best_index is None or value > best_score:
            best_index, best_score = index, value
    if best_index is None:
        raise ValueError("no legal candidate is selectable")
    return candidate_uci[best_index]


class BehaviorPolicy:
    """Select a legal move from an M2 Observation using M4 behavior logits."""

    policy_id = "m4_behavior_clone"

    def __init__(self, model: BehaviorScorer, *, checkpoint_sha256: str) -> None:
        self.model = model.to("cpu").eval()
        self.checkpoint_sha256 = checkpoint_sha256

    @property
    def config(self) -> dict[str, object]:
        return {
            "input_schema": self.model.config.input_schema,
            "model_schema": self.model.config.model_schema,
            "checkpoint_sha256": self.checkpoint_sha256,
            "selection": "maximum behavior logit over lexical legal UCI candidates; ties choose first",
            "stockfish": "not imported or called",
        }

    @torch.inference_mode()
    def choose_move(
        self,
        observation: Observation,
        legal_moves: Sequence[chess.Move],
        rng: random.Random,
    ) -> chess.Move:
        del rng  # Deterministic lexical tie-breaking is part of the inference contract.
        if observation.turn != observation.agent_color:
            raise ValueError("M4 policy may only choose on the agent's turn")
        board = replay_observation_history(observation.history_uci)
        if board.turn != observation.agent_color or board.turn != observation.turn:
            raise ValueError("reconstructed board side-to-move differs from the agent")
        if board.fen(en_passant="fen") != observation.fen:
            raise ValueError("M2 observation FEN does not match its complete move history")
        legal_uci = tuple(sorted(move.uci() for move in board.legal_moves))
        if legal_uci != tuple(observation.legal_moves_uci):
            raise ValueError("M2 observation legal moves do not match reconstructed history")
        supplied_uci = tuple(sorted(move.uci() for move in legal_moves))
        if supplied_uci != legal_uci:
            raise ValueError("simulator-supplied legal moves differ from reconstructed legal moves")
        candidates = legal_action_candidates(board)
        if not candidates:
            raise ValueError("terminal chess states do not produce policy actions")
        features = encode_board(board, split="inference")
        if features.candidate_uci != tuple(item.uci for item in candidates):
            raise RuntimeError("encoded action identities differ from authoritative legal candidates")
        batch = collate_examples((features,), require_targets=False)
        logits = self.model(**model_inputs(batch))[0]
        selected = select_legal_candidate(logits, batch["candidate_mask"][0], features.candidate_uci)
        return chess.Move.from_uci(selected)


def features_from_observation(observation: Observation) -> PositionFeatures:
    """Validated, standalone feature construction used by contract tests/tools."""
    board = replay_observation_history(observation.history_uci)
    if board.fen(en_passant="fen") != observation.fen:
        raise ValueError("observation FEN does not match replayed move history")
    if canonical_model_fen(board) != board.fen(en_passant="legal"):
        raise RuntimeError("model FEN canonicalization failed")
    candidates = tuple(sorted(move.uci() for move in board.legal_moves))
    if candidates != tuple(observation.legal_moves_uci):
        raise ValueError("observation legal set does not match replay")
    return encode_board(board, split="inference")
