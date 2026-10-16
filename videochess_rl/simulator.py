"""History-preserving chess simulator for the M2 decision process.

This module owns simulated chess transitions only. It has no ALE, screen, or
joystick dependency; the existing M1 environment remains the source of truth
for Atari observations and outcomes.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Protocol, Sequence

import chess


class SimulatorError(RuntimeError):
    """Base class for simulator lifecycle and transition errors."""


class InvalidActionError(SimulatorError, ValueError):
    """Raised when an agent action is not legal in the current position."""


class EpisodeStateError(SimulatorError):
    """Raised when a transition is requested outside a live episode."""


class OpponentPolicyError(SimulatorError):
    """Raised when an opponent fails or returns an illegal action."""


class MovePolicy(Protocol):
    """Small interface implemented by baseline or caller-supplied policies.

    Policies without ``reset_episode(seed=...)`` must be stateless across
    episodes. A stateful policy may implement that optional hook to restore
    its episode-local state for reproducible repeated resets. Policy identity
    and configuration must remain stable for the lifetime of a simulator.
    """

    @property
    def policy_id(self) -> str: ...

    @property
    def config(self) -> dict[str, object]: ...

    def choose_move(
        self,
        observation: Observation,
        legal_moves: Sequence[chess.Move],
        rng: random.Random,
    ) -> chess.Move: ...


@dataclass(frozen=True, slots=True)
class Observation:
    """Immutable agent-facing snapshot; it never exposes the mutable Board."""

    fen: str
    board_fen: str
    turn: chess.Color
    agent_color: chess.Color
    castling_rights: str
    ep_square: str | None
    halfmove_clock: int
    fullmove_number: int
    legal_moves_uci: tuple[str, ...]
    history_uci: tuple[str, ...]
    opponent_id: str
    opponent_config_json: str
    episode_decisions: int

    @property
    def side_to_move(self) -> str:
        return "white" if self.turn == chess.WHITE else "black"

    @property
    def agent_side(self) -> str:
        return "white" if self.agent_color == chess.WHITE else "black"


@dataclass(frozen=True, slots=True)
class StepResult:
    """One completed agent decision transition and its stopping metadata."""

    observation: Observation
    reward: float
    terminated: bool
    truncated: bool
    agent_move_uci: str
    opponent_move_uci: str | None
    outcome_result: str | None
    outcome_reason: str | None
    truncation_reason: str | None
    episode_decisions: int
    episode_plies: int
    history_uci: tuple[str, ...]
    metric_source: str = "chess_simulator"


class ChessSimulator:
    """A fixed-color chess agent plays one move plus at most one reply per step.

    ``python-chess.Board`` and its complete move stack are the sole rules state.
    Invalid agent moves do not mutate state. Opponent errors roll back the
    entire attempted decision transition so callers can record an external
    failure without mistaking a half-applied turn for a chess result.
    """

    def __init__(self, opponent: MovePolicy, *, max_decisions: int = 400) -> None:
        if isinstance(max_decisions, bool) or not isinstance(max_decisions, int) or max_decisions <= 0:
            raise ValueError("max_decisions must be positive")
        self._opponent = opponent
        self._opponent_id, self._opponent_config_json = self._describe_policy(opponent)
        self.max_decisions = int(max_decisions)
        self._board = chess.Board()
        self._agent_color = chess.WHITE
        self._rng = random.Random(0)
        self._episode_decisions = 0
        self._episode_start_ply = 0
        self._ready = False
        self._stopped = False

    @staticmethod
    def _describe_policy(policy: MovePolicy) -> tuple[str, str]:
        policy_id = getattr(policy, "policy_id", None)
        config = getattr(policy, "config", None)
        if not isinstance(policy_id, str) or not policy_id.strip():
            raise TypeError("opponent policy must provide a non-empty policy_id")
        if not isinstance(config, dict):
            raise TypeError("opponent policy config must be a JSON-compatible dict")
        try:
            encoded = json.dumps(config, sort_keys=True, separators=(",", ":"), allow_nan=False)
            json.loads(encoded)
        except (TypeError, ValueError) as exc:
            raise TypeError("opponent policy config must be JSON-compatible") from exc
        return policy_id, encoded

    @property
    def board(self) -> chess.Board:
        """Return an independent Board copy, including its move history."""
        return self._board.copy(stack=True)

    @property
    def agent_color(self) -> chess.Color:
        return self._agent_color

    @property
    def episode_decisions(self) -> int:
        return self._episode_decisions

    @property
    def episode_plies(self) -> int:
        return len(self._board.move_stack) - self._episode_start_ply

    @property
    def legal_moves(self) -> tuple[chess.Move, ...]:
        self._require_ready()
        return tuple(chess.Move.from_uci(move.uci()) for move in self._board.legal_moves)

    @property
    def observation(self) -> Observation:
        self._require_ready()
        return self._make_observation()

    def reset(
        self,
        *,
        seed: int,
        agent_color: chess.Color = chess.WHITE,
        initial_board: chess.Board | None = None,
    ) -> Observation:
        """Start a seeded episode and return its first agent decision state.

        Standard games start from the ordinary initial position. If the agent
        is Black, the opponent plays White's opening move during reset. A
        supplied test/analysis Board must already be at the agent's turn and
        is copied with its complete move stack.
        """
        if not isinstance(agent_color, bool):
            raise ValueError("agent_color must be chess.WHITE or chess.BLACK")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("seed must be an integer")

        if initial_board is not None and not isinstance(initial_board, chess.Board):
            raise TypeError("initial_board must be a python-chess Board")
        board = initial_board.copy(stack=True) if initial_board is not None else chess.Board()
        if board.chess960:
            raise ValueError("M2 simulator supports standard chess, not Chess960")
        if not board.is_valid():
            raise ValueError(
                f"initial_board is not a valid standard chess position (status={board.status()})"
            )
        if initial_board is not None and board.turn != agent_color:
            raise ValueError("initial_board must have the agent to move")
        if board.outcome(claim_draw=False) is not None:
            raise ValueError("initial_board must be a live chess position")

        try:
            self._reset_opponent_policy(seed)
        except BaseException:
            # A failed episode reset may have changed policy-local state, so
            # the previously active simulator episode is no longer reusable.
            self._ready = False
            self._stopped = True
            raise
        self._board = board
        self._agent_color = agent_color
        self._rng = random.Random(seed)
        self._episode_decisions = 0
        self._episode_start_ply = len(board.move_stack)
        self._ready = False
        self._stopped = False

        if initial_board is None and agent_color == chess.BLACK:
            try:
                opening = self._choose_opponent_move()
                self._board.push(opening)
            except BaseException:
                # Board rollback is guaranteed. A policy's private state and
                # the consumed RNG stream are external to the chess snapshot.
                self._board = board
                raise

        self._ready = True
        return self._make_observation()

    def step(self, action: chess.Move) -> StepResult:
        """Apply one legal agent move and, while live, one opponent reply."""
        self._require_ready()
        if self._stopped:
            raise EpisodeStateError("episode is already terminated or truncated; call reset()")
        self._assert_opponent_identity()
        if not isinstance(action, chess.Move):
            raise InvalidActionError("action must be a python-chess Move; use step_uci() for serialized UCI")

        legal_by_uci = {move.uci() for move in self._board.legal_moves}
        try:
            action_uci = action.uci()
        except (IndexError, ValueError) as exc:
            raise InvalidActionError("action contains invalid square or promotion data") from exc
        if action_uci not in legal_by_uci:
            raise InvalidActionError(f"move {action_uci!r} is illegal or stale in the current position")

        before = self._board.copy(stack=True)
        canonical_action = chess.Move.from_uci(action_uci)
        self._board.push(canonical_action)
        opponent_uci: str | None = None

        outcome = self._board.outcome(claim_draw=False)
        if outcome is None:
            try:
                opponent_move = self._choose_opponent_move()
                opponent_uci = opponent_move.uci()
                self._board.push(opponent_move)
            except BaseException:
                # Roll back the entire attempted chess transition, including
                # agent move, but not policy-local state or consumed RNG.
                self._board = before
                self._stopped = True
                raise
            outcome = self._board.outcome(claim_draw=False)

        self._episode_decisions += 1
        terminated = outcome is not None
        truncated = not terminated and self._episode_decisions >= self.max_decisions
        self._stopped = terminated or truncated

        if outcome is None:
            reward = 0.0
            outcome_result = None
            outcome_reason = None
        else:
            outcome_result = outcome.result()
            outcome_reason = outcome.termination.name.lower()
            if outcome.winner is None:
                reward = 0.0
            else:
                reward = 1.0 if outcome.winner == self._agent_color else -1.0

        observation = self._make_observation()
        return StepResult(
            observation=observation,
            reward=reward,
            terminated=terminated,
            truncated=truncated,
            agent_move_uci=action_uci,
            opponent_move_uci=opponent_uci,
            outcome_result=outcome_result,
            outcome_reason=outcome_reason,
            truncation_reason="max_agent_decisions" if truncated else None,
            episode_decisions=self._episode_decisions,
            episode_plies=self.episode_plies,
            history_uci=tuple(move.uci() for move in self._board.move_stack),
        )

    def step_uci(self, uci: str) -> StepResult:
        """Parse a serialized UCI action and apply it through ``step``."""
        if not isinstance(uci, str):
            raise InvalidActionError("UCI action must be a string")
        try:
            action = chess.Move.from_uci(uci)
        except ValueError as exc:
            raise InvalidActionError(f"invalid UCI move {uci!r}") from exc
        return self.step(action)

    def _choose_opponent_move(self) -> chess.Move:
        self._assert_opponent_identity()
        legal_uci = tuple(sorted(move.uci() for move in self._board.legal_moves))
        if not legal_uci:
            raise OpponentPolicyError("opponent was requested to move in a terminal position")
        observation = self._make_observation()
        legal_moves = tuple(chess.Move.from_uci(uci) for uci in legal_uci)
        try:
            selected = self._opponent.choose_move(observation, legal_moves, self._rng)
            self._assert_opponent_identity()
        except Exception as exc:
            raise OpponentPolicyError(
                f"opponent policy {self._opponent_id!r} raised {type(exc).__name__}"
            ) from exc
        if not isinstance(selected, chess.Move):
            raise OpponentPolicyError(f"opponent policy {self._opponent_id!r} did not return a Move")
        try:
            selected_uci = selected.uci()
        except (IndexError, ValueError) as exc:
            raise OpponentPolicyError(f"opponent policy {self._opponent_id!r} returned a malformed Move") from exc
        if selected_uci not in legal_uci:
            raise OpponentPolicyError(
                f"opponent policy {self._opponent_id!r} returned illegal move {selected_uci!r}"
            )
        return chess.Move.from_uci(selected_uci)

    def _reset_opponent_policy(self, seed: int) -> None:
        self._assert_opponent_identity()
        reset_episode = getattr(self._opponent, "reset_episode", None)
        if reset_episode is None:
            return
        if not callable(reset_episode):
            raise TypeError("opponent reset_episode attribute must be callable")
        try:
            reset_episode(seed=seed)
        except Exception as exc:
            raise OpponentPolicyError(
                f"opponent policy {self._opponent_id!r} failed to reset: {type(exc).__name__}"
            ) from exc
        self._assert_opponent_identity()

    def _assert_opponent_identity(self) -> None:
        try:
            current = self._describe_policy(self._opponent)
        except (TypeError, ValueError, AttributeError) as exc:
            raise OpponentPolicyError(
                f"opponent policy {self._opponent_id!r} has invalid identity/configuration"
            ) from exc
        if current != (self._opponent_id, self._opponent_config_json):
            raise OpponentPolicyError(
                "opponent policy identity/configuration changed after simulator construction"
            )

    def _make_observation(self) -> Observation:
        return Observation(
            fen=self._board.fen(en_passant="fen"),
            board_fen=self._board.board_fen(),
            turn=self._board.turn,
            agent_color=self._agent_color,
            castling_rights=self._board.castling_xfen(),
            ep_square=chess.square_name(self._board.ep_square) if self._board.ep_square is not None else None,
            halfmove_clock=self._board.halfmove_clock,
            fullmove_number=self._board.fullmove_number,
            legal_moves_uci=tuple(sorted(move.uci() for move in self._board.legal_moves)),
            history_uci=tuple(move.uci() for move in self._board.move_stack),
            opponent_id=self._opponent_id,
            opponent_config_json=self._opponent_config_json,
            episode_decisions=self._episode_decisions,
        )

    def _require_ready(self) -> None:
        if not self._ready:
            raise EpisodeStateError("reset() must be called before reading or stepping the simulator")
