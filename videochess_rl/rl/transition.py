"""Validated, semantic replay transitions for the M2 simulator."""

from __future__ import annotations

import hashlib
import json
import math
from collections import OrderedDict
from dataclasses import asdict, dataclass
from typing import Any

import chess

from videochess_rl.model.features import PositionFeatures, encode_board, replay_observation_history
from videochess_rl.m5_seeding import EXPERIMENT_ID, paired_seed_schedule
from videochess_rl.simulator import Observation, StepResult

TRANSITION_SCHEMA = "videochess-ddqn-transition/1.0"
_VALIDATED: OrderedDict[str,str] = OrderedDict()
_VALIDATION_CACHE_LIMIT = 32768


def _legal(board: chess.Board) -> tuple[str, ...]:
    return tuple(sorted(move.uci() for move in board.legal_moves))


@dataclass(frozen=True, slots=True)
class Transition:
    schema: str
    transition_id: str
    run_id: str
    attempt_id: str
    episode_index: int
    decision_index: int
    training_seed: int
    agent_color: str
    opponent_id: str
    opponent_config_json: str
    selected_uci: str
    opponent_reply_uci: str | None
    history_before: tuple[str, ...]
    history_after: tuple[str, ...]
    legal_actions: tuple[str, ...]
    next_legal_actions: tuple[str, ...]
    reward: float
    terminated: bool
    truncated: bool
    outcome_result: str | None
    outcome_reason: str | None
    truncation_reason: str | None
    seed_schedule: dict[str, int | str]

    @classmethod
    def from_step(
        cls, before: Observation, result: StepResult, *, run_id: str, attempt_id: str,
        episode_index: int, decision_index: int, training_seed: int,
        seed_schedule: dict[str, int | str],
    ) -> "Transition":
        if before.turn != before.agent_color:
            raise ValueError("agent observation must be at the fixed agent turn")
        board = replay_observation_history(before.history_uci)
        if board.fen(en_passant="fen") != before.fen or _legal(board) != tuple(before.legal_moves_uci):
            raise ValueError("current observation does not reconstruct from legal history")
        if result.agent_move_uci not in _legal(board):
            raise ValueError("selected action is stale or illegal")
        expected = board.copy(stack=True)
        expected.push_uci(result.agent_move_uci)
        if result.opponent_move_uci is not None:
            if expected.outcome(claim_draw=False) is not None or expected.turn == before.agent_color:
                raise ValueError("opponent reply follows a terminal state or is not the opponent turn")
            try:
                reply = chess.Move.from_uci(result.opponent_move_uci)
            except ValueError as exc:
                raise ValueError("malformed opponent reply UCI") from exc
            if reply not in expected.legal_moves:
                raise ValueError("opponent reply is illegal")
            expected.push(reply)
        if tuple(result.history_uci) != tuple(move.uci() for move in expected.move_stack):
            raise ValueError("post-transition history differs from the actual simulator step")
        if tuple(result.observation.history_uci) != tuple(result.history_uci):
            raise ValueError("post-step observation history mismatch")
        if (result.observation.opponent_id != before.opponent_id
                or result.observation.opponent_config_json != before.opponent_config_json):
            raise ValueError("opponent identity/config changed inside an episode")
        if result.observation.fen != expected.fen(en_passant="fen"):
            raise ValueError("post-step FEN differs from reconstructed history")
        if result.terminated and result.truncated:
            raise ValueError("a transition cannot be both terminal and truncated")
        if not math.isfinite(float(result.reward)) or result.reward not in (-1.0, 0.0, 1.0):
            raise ValueError("M2 terminal reward must be finite agent-perspective -1/0/+1")
        if result.terminated:
            outcome = expected.outcome(claim_draw=False)
            if outcome is None or result.outcome_result != outcome.result():
                raise ValueError("terminal outcome does not match reconstructed chess state")
            expected_reward = 0.0 if outcome.winner is None else (1.0 if outcome.winner == before.agent_color else -1.0)
            if result.reward != expected_reward:
                raise ValueError("terminal reward is not from the fixed agent perspective")
        elif result.reward != 0.0:
            raise ValueError("nonterminal/truncated transition cannot invent reward")
        if result.truncated and (result.truncation_reason != "max_agent_decisions" or result.terminated):
            raise ValueError("unsupported or inconsistent truncation reason")
        if not result.terminated and not result.truncated and expected.outcome(claim_draw=False) is not None:
            raise ValueError("simulator omitted a true chess terminal flag")
        legal_next = _legal(expected)
        if tuple(result.observation.legal_moves_uci) != legal_next:
            raise ValueError("next legal set differs from reconstructed board")
        # Keep actual raw next legal moves reconstructable; bootstrap policy masks terminal separately.
        key = cls._identity_document(run_id=run_id,attempt_id=attempt_id,episode_index=episode_index,
            decision_index=decision_index,training_seed=training_seed,agent_color="white" if before.agent_color else "black",
            opponent_id=before.opponent_id,opponent_config_json=before.opponent_config_json,
            history_before=tuple(before.history_uci),selected_uci=result.agent_move_uci,history_after=tuple(result.history_uci))
        transition_id = hashlib.sha256(json.dumps(key, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        row = cls(
            TRANSITION_SCHEMA, transition_id, run_id, attempt_id, episode_index, decision_index,
            training_seed, "white" if before.agent_color else "black", before.opponent_id,
            before.opponent_config_json,
            result.agent_move_uci, result.opponent_move_uci, tuple(before.history_uci),
            tuple(result.history_uci), tuple(before.legal_moves_uci), legal_next,
            float(result.reward), bool(result.terminated), bool(result.truncated),
            result.outcome_result, result.outcome_reason, result.truncation_reason, dict(seed_schedule),
        )
        row.validate()
        return row

    def validate(self) -> None:
        content=json.dumps(self.to_json(),sort_keys=True,separators=(",",":"),allow_nan=False)
        fingerprint=hashlib.sha256(content.encode()).hexdigest()
        if _VALIDATED.get(self.transition_id)==fingerprint:
            _VALIDATED.move_to_end(self.transition_id)
            return
        if self.schema != TRANSITION_SCHEMA:
            raise ValueError("unsupported transition schema")
        if not all(isinstance(x, str) and x for x in (self.transition_id, self.run_id, self.attempt_id, self.opponent_id)):
            raise ValueError("transition identity fields must be nonempty strings")
        if any(type(x) is not int or x < 0 for x in (self.episode_index, self.decision_index)):
            raise ValueError("episode and decision indices must be nonnegative integers")
        expected_schedule=paired_seed_schedule(EXPERIMENT_ID,self.training_seed,self.episode_index)
        if self.seed_schedule!=expected_schedule:
            raise ValueError("transition seed schedule does not recompute from paired seed contract and episode index")
        identity=self._identity_document(run_id=self.run_id,attempt_id=self.attempt_id,episode_index=self.episode_index,
            decision_index=self.decision_index,training_seed=self.training_seed,agent_color=self.agent_color,
            opponent_id=self.opponent_id,opponent_config_json=self.opponent_config_json,
            history_before=self.history_before,selected_uci=self.selected_uci,history_after=self.history_after)
        expected_id=hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        if self.transition_id!=expected_id:
            raise ValueError("transition ID does not bind its run/episode/action/history provenance")
        if self.agent_color not in ("white", "black") or self.terminated and self.truncated:
            raise ValueError("invalid color or terminal/truncation flags")
        if len(self.legal_actions) != len(set(self.legal_actions)) or tuple(sorted(self.legal_actions)) != self.legal_actions:
            raise ValueError("current legal UCI set must be unique and sorted")
        board = replay_observation_history(self.history_before)
        if ("white" if board.turn else "black") != self.agent_color or _legal(board) != self.legal_actions:
            raise ValueError("current position/color/legal set is inconsistent")
        move = chess.Move.from_uci(self.selected_uci)
        if move.uci() not in self.legal_actions:
            raise ValueError("selected semantic UCI is not currently legal")
        after = replay_observation_history(self.history_after)
        if tuple(self.history_after[:len(self.history_before)]) != self.history_before:
            raise ValueError("post-state history is not an extension of current history")
        new_moves = self.history_after[len(self.history_before):]
        expected_new = (self.selected_uci,) + ((self.opponent_reply_uci,) if self.opponent_reply_uci else ())
        if tuple(new_moves) != expected_new:
            raise ValueError("post-state history does not encode selected move plus optional reply")
        first = board.copy(stack=True); first.push_uci(self.selected_uci)
        first_outcome = first.outcome(claim_draw=False)
        if first_outcome is not None and self.opponent_reply_uci is not None:
            raise ValueError("opponent replied after the agent action already ended the game")
        if first_outcome is None and self.opponent_reply_uci is None:
            raise ValueError("a live agent action must include the simulator's opponent reply")
        if _legal(after) != self.next_legal_actions:
            raise ValueError("next legal actions do not reconstruct")
        if not math.isfinite(self.reward) or self.reward not in (-1.0, 0.0, 1.0):
            raise ValueError("invalid reward")
        outcome=after.outcome(claim_draw=False)
        if self.terminated:
            if outcome is None or self.outcome_result != outcome.result():
                raise ValueError("terminal outcome metadata differs from reconstructed state")
            # Use the transition's fixed color, independent of the side now moving.
            agent_is_white=self.agent_color=="white"
            expected_reward=0.0 if outcome.winner is None else (1.0 if outcome.winner==agent_is_white else -1.0)
            if self.reward!=expected_reward or self.outcome_reason != outcome.termination.name.lower():
                raise ValueError("terminal reward/reason is not consistent with the fixed agent perspective")
        elif self.truncated:
            if outcome is not None or self.reward!=0.0 or self.truncation_reason!="max_agent_decisions":
                raise ValueError("truncation must be a valid nonterminal zero-reward time limit")
        elif outcome is not None or self.reward!=0.0:
            raise ValueError("true terminal state lacks termination flag or nonterminal reward is fabricated")
        try:
            opponent_config=json.loads(self.opponent_config_json)
        except (TypeError,ValueError) as exc:
            raise ValueError("opponent config is not valid JSON") from exc
        if not isinstance(opponent_config,dict): raise ValueError("opponent config must be an object")
        _VALIDATED[self.transition_id]=fingerprint
        _VALIDATED.move_to_end(self.transition_id)
        while len(_VALIDATED)>_VALIDATION_CACHE_LIMIT: _VALIDATED.popitem(last=False)

    @staticmethod
    def _identity_document(*,run_id:str,attempt_id:str,episode_index:int,decision_index:int,
                           training_seed:int,agent_color:str,opponent_id:str,opponent_config_json:str,
                           history_before:tuple[str,...],selected_uci:str,history_after:tuple[str,...])->dict[str,Any]:
        return {"run_id":run_id,"attempt_id":attempt_id,"episode_index":episode_index,
                "decision_index":decision_index,"training_seed":training_seed,"agent_color":agent_color,
                "opponent_id":opponent_id,"opponent_config_json":opponent_config_json,
                "history_before":list(history_before),"selected_uci":selected_uci,"history_after":list(history_after)}

    def current_features(self) -> PositionFeatures:
        return encode_board(replay_observation_history(self.history_before), split="replay")

    def next_features(self) -> PositionFeatures:
        if self.terminated:
            raise ValueError("true terminal transitions do not need bootstrap features")
        return encode_board(replay_observation_history(self.history_after), split="replay")

    def to_json(self) -> dict[str, Any]:
        value = asdict(self)
        for key in ("history_before", "history_after", "legal_actions", "next_legal_actions"):
            value[key] = list(value[key])
        return value

    @classmethod
    def from_json(cls, value: dict[str, Any]) -> "Transition":
        if not isinstance(value, dict):
            raise ValueError("transition JSON must be an object")
        fields = dict(value)
        for key in ("history_before", "history_after", "legal_actions", "next_legal_actions"):
            if not isinstance(fields.get(key), list):
                raise ValueError(f"{key} must be a JSON array")
            fields[key] = tuple(fields[key])
        row = cls(**fields)
        row.validate()
        return row
