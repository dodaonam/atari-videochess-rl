"""Bounded observation-driven multi-turn ALE VideoChess experiments."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import hashlib
import math
import time
from typing import Callable

import chess
import numpy as np

from .controller import (
    ActionFrame,
    ControllerTiming,
    FIRE,
    NOOP,
    plan_cursor_route,
    plan_move,
)
from .demo import _git_state, _utc_now, _write_png
from .environment import ALEConfig, ALEFrame, VideoChessEnv
from .shadow import DesynchronizationError, ShadowBoard
from .vision import BoardEvidenceSet, BoardWindow, VideoChessVision


WINDOW_FRAMES = 33
MAX_CURSOR_ACTIONS_PER_MOVE = 64
ACTION_NAMES = {
    0: "NOOP",
    1: "FIRE",
    2: "UP",
    3: "RIGHT",
    4: "LEFT",
    5: "DOWN",
    6: "UPRIGHT",
    7: "UPLEFT",
    8: "DOWNRIGHT",
    9: "DOWNLEFT",
}
PIECE_VALUE = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}
OPENING_PREFERENCES = (
    "e2e3",
    "e3e4",
    "d2d3",
    "a2a3",
    "b2b3",
    "c2c3",
    "f2f3",
    "g2g3",
    "h2h3",
    "d3d4",
    "g1f3",
    "b1c3",
    "f1c4",
    "f1b5",
    "e1g1",
)


class TurnState(str, Enum):
    PLAYER_TURN = "player_turn"
    PLAYER_MOVE_EXECUTING = "player_move_executing"
    ATARI_THINKING = "atari_thinking"
    OPPONENT_MOVE_COMPLETED = "opponent_move_completed"
    EPISODE_FINISHED = "episode_finished"
    EPISODE_TRUNCATED = "episode_truncated"
    UNCERTAIN = "uncertain_or_desynchronized"


class EpisodeStop(RuntimeError):
    """The bounded episode cannot continue without guessing state."""


def agent_reward_from_ale(ale_reward: float, agent_color: chess.Color) -> float:
    """Convert the wrapper's white-perspective reward to an agent perspective."""
    return float(ale_reward if agent_color == chess.WHITE else -ale_reward)


def choose_diagnostic_move(board: chess.Board) -> str:
    """Choose a transparent one-ply diagnostic move; this is not a chess baseline."""
    legal = sorted(board.legal_moves, key=lambda move: move.uci())
    if not legal:
        raise ValueError("No legal move is available in the observed position")

    for move in legal:
        candidate = board.copy()
        candidate.push(move)
        if candidate.is_checkmate():
            return move.uci()

    simple_moves = [
        move
        for move in legal
        if abs(chess.square_file(move.from_square) - chess.square_file(move.to_square))
        + abs(chess.square_rank(move.from_square) - chess.square_rank(move.to_square))
        == 1
    ]
    candidates = simple_moves or legal
    captures: list[tuple[int, int, str]] = []
    for move in candidates:
        if not board.is_capture(move):
            continue
        victim = board.piece_at(move.to_square)
        victim_value = PIECE_VALUE[victim.piece_type] if victim else PIECE_VALUE[chess.PAWN]
        attacker = board.piece_at(move.from_square)
        attacker_value = PIECE_VALUE[attacker.piece_type] if attacker else 0
        captures.append((victim_value, -attacker_value, move.uci()))
    if captures:
        return max(captures)[2]

    for uci in OPENING_PREFERENCES:
        move = chess.Move.from_uci(uci)
        if move in candidates:
            return uci
    return candidates[0].uci()


def _unique_cursor(window: BoardWindow) -> str | None:
    squares = window.cursor_squares
    return next(iter(squares)) if len(squares) == 1 else None


def _verification_square(board: chess.Board, cursor: str) -> str:
    preferred = ("d4", "e4", "d5", "e5", "a3", "h3", "a6", "h6")
    for square in preferred:
        if square != cursor and board.piece_at(chess.parse_square(square)) is None:
            return square
    for square in chess.SQUARES:
        name = chess.square_name(square)
        if name != cursor and board.piece_at(square) is None:
            return name
    raise EpisodeStop("No empty square is available for cursor-occlusion verification")


def _window_record(
    window: BoardWindow,
    frame: ALEFrame,
    reference_board: chess.Board,
) -> dict[str, object]:
    return {
        "frame_number": frame.frame_number,
        "rgb_sha256": hashlib.sha256(frame.rgb.tobytes()).hexdigest(),
        "stable": window.is_stable,
        "cursor_squares": sorted(window.cursor_squares),
        "matches_reference": window.matches_board(reference_board),
        "matches_reference_except_cursor": window.matches_board_except_cursor(reference_board),
    }


def _piece_channel(color: chess.Color) -> str:
    return "blue" if color == chess.WHITE else "gold"


def _source_selection_evidence(
    window: BoardWindow,
    reference_board: chess.Board,
    source: str,
) -> dict[str, object]:
    """Recognize VideoChess' flashing selected-piece state from RGB only."""
    piece = reference_board.piece_at(chess.parse_square(source))
    if piece is None:
        return {"verified": False, "reason": "source square has no shadow piece"}
    channel = _piece_channel(piece.color)
    counts = [getattr(observation.cell(source), channel) for observation in window.observations]
    visible = sum(count > 0 for count in counts)
    absent = len(counts) - visible
    no_cursor = not window.cursor_squares
    legal_board_view = window.is_stable and window.matches_board_except_cursor(reference_board)
    verified = visible >= 2 and absent >= 2 and no_cursor and legal_board_view
    return {
        "verified": verified,
        "source_square": source,
        "piece_color": "white" if piece.color else "black",
        "piece_visible_frames": visible,
        "piece_absent_frames": absent,
        "cursor_squares": sorted(window.cursor_squares),
        "stable_board_except_cursor": legal_board_view,
        "signature": "selected-piece blink with cursor absent" if verified else None,
    }


def _selected_target_evidence(
    window: BoardWindow,
    reference_board: chess.Board,
    source: str,
    target: str,
) -> dict[str, object]:
    """Verify a flashing selected-piece preview at the requested target square."""
    piece = reference_board.piece_at(chess.parse_square(source))
    if piece is None:
        return {"verified": False, "reason": "source square has no shadow piece"}
    channel = _piece_channel(piece.color)
    source_cell = window.cell(source)
    target_cell = window.cell(target)
    unrelated_squares_match = True
    for square in chess.SQUARES:
        name = chess.square_name(square)
        if name in (source, target):
            continue
        cell = window.cell(name)
        if cell.side == "unknown" and cell.masked_only:
            continue
        expected_piece = reference_board.piece_at(square)
        expected_side = "empty" if expected_piece is None else ("white" if expected_piece.color else "black")
        if cell.side != expected_side:
            unrelated_squares_match = False
            break
    target_piece_seen = target_cell.blue_piece_seen if piece.color else target_cell.gold_piece_seen
    source_piece_seen = source_cell.blue_piece_seen if piece.color else source_cell.gold_piece_seen
    verified = (
        target_piece_seen
        and source_piece_seen
        and unrelated_squares_match
        and window.cursor_squares.issubset({source})
    )
    return {
        "verified": verified,
        "source_square": source,
        "target_square": target,
        "piece_color": "white" if piece.color else "black",
        "source_piece_seen": source_piece_seen,
        "target_piece_seen": target_piece_seen,
        "target_piece_pixel_frames": sum(
            getattr(observation.cell(target), channel) > 0 for observation in window.observations
        ),
        "cursor_squares": sorted(window.cursor_squares),
        "unrelated_squares_match": unrelated_squares_match,
        "signature": "selected-piece preview visible at target" if verified else None,
    }


def run_episode(
    *,
    config: ALEConfig | None = None,
    seed: int = 20261015,
    expected_reset_cursor: str | None = None,
    move_selector: Callable[[chess.Board], str] | None = None,
    max_player_moves: int = 1,
    max_opponent_wait_frames: int = 10000,
    max_episode_frames: int = 54000,
    max_episode_seconds: float = 900.0,
    max_artifact_bytes: int = 250 * 1024 * 1024,
    target_fire_press_frames: int = 16,
    artifact_dir: str | None = None,
    env_factory: Callable[[ALEConfig], VideoChessEnv] = VideoChessEnv,
) -> dict[str, object]:
    """Run a frame- and time-bounded real-ALE episode with atomic RGB checks."""
    if max_player_moves < 1:
        raise ValueError("max_player_moves must be positive")
    if max_opponent_wait_frames < WINDOW_FRAMES:
        raise ValueError(f"max_opponent_wait_frames must be at least {WINDOW_FRAMES}")
    if max_episode_frames < WINDOW_FRAMES or max_episode_seconds <= 0 or max_artifact_bytes <= 0:
        raise ValueError("Episode frame and wall-clock budgets must be positive")

    config = config or ALEConfig.deterministic_dev()
    selector = move_selector or choose_diagnostic_move
    input_observation_frames = 66 if config.frameskip > 1 else WINDOW_FRAMES
    timing = ControllerTiming(
        target_fire_press_frames=target_fire_press_frames,
        frameskip=config.frameskip,
        repeat_action_probability=config.repeat_action_probability,
        source_selection_observation_frames=input_observation_frames,
        selected_target_observation_frames=input_observation_frames,
    )
    started_monotonic = time.monotonic()
    trace: dict[str, object] = {
        "created_at_utc": _utc_now(),
        "git": _git_state(),
        "seed": seed,
        "player_color": "white",
        "move_selector": getattr(selector, "__name__", "custom diagnostic selector"),
        "config": config.as_dict(),
        "controller_timing": {
            "direction_frames": timing.direction_frames,
            "fire_settle_frames": timing.fire_settle_frames,
            "source_fire_press_frames": timing.source_fire_press_frames,
            "target_fire_press_frames": timing.target_fire_press_frames,
            "release_frames": timing.release_frames,
            "source_selection_observation_frames": timing.source_selection_observation_frames,
            "selected_target_observation_frames": timing.selected_target_observation_frames,
            "frameskip": timing.frameskip,
            "repeat_action_probability": timing.repeat_action_probability,
        },
        "episode_budget": {
            "max_player_moves": max_player_moves,
            "max_opponent_wait_frames": max_opponent_wait_frames,
            "max_episode_frames": max_episode_frames,
            "max_episode_seconds": max_episode_seconds,
            "max_artifact_bytes": max_artifact_bytes,
        },
        "runtime": {},
        "reset": {},
        "initial_position": {"verified_from_rgb": False, "cursor_squares": []},
        "actions": [],
        "observations": [],
        "cursor_observations": [],
        "ram_diagnostics_only": [],
        "turn_events": [],
        "turns": [],
        "player_move": {"uci": None, "verified_from_rgb": False},
        "opponent_reply": {"uci": None, "verified_from_rgb": False},
        "terminal": {
            "observed": False,
            "terminated": False,
            "truncated": False,
            "ale_reward_total": 0.0,
            "agent_reward_total": 0.0,
        },
    }
    frames_dir = None
    if artifact_dir is not None:
        from pathlib import Path

        frames_dir = Path(artifact_dir)
        frames_dir.mkdir(parents=True, exist_ok=True)

    with env_factory(config) as env:
        vision = VideoChessVision()
        reset = env.reset(seed=seed)
        last_frame = reset
        initial_observation = vision.observe(reset.rgb)
        initial_window = vision.window((reset.rgb, reset.rgb, reset.rgb))
        trace["runtime"] = env.runtime_info()
        trace["reset"] = {
            "frame_number": reset.frame_number,
            "rgb_shape": list(reset.rgb.shape),
            "rgb_dtype": str(reset.rgb.dtype),
            "rgb_sha256": hashlib.sha256(reset.rgb.tobytes()).hexdigest(),
            "initial_position_verified_from_rgb": initial_observation.matches_start_position(),
            "cursor_squares": sorted(initial_observation.cursor_squares),
            "stable_window": initial_window.is_stable,
        }
        trace["initial_position"] = {
            "verified_from_rgb": initial_observation.matches_start_position(),
            "cursor_squares": sorted(initial_observation.cursor_squares),
        }
        trace["ram_diagnostics_only"].append(
            {"stage": "reset", **env.diagnostic_ram((0xE1, 0xE4, 0xEA, 0xEE))}
        )
        if not initial_observation.matches_start_position() or not initial_window.is_stable:
            trace["status"] = "blocked"
            trace["failure"] = "Reset RGB did not establish a stable standard chess start"
            return trace
        shadow = ShadowBoard()
        if not initial_window.matches_board_except_cursor(shadow.board):
            trace["status"] = "blocked"
            trace["failure"] = "Reset RGB did not agree with the initial shadow position"
            return trace
        cursor = _unique_cursor(initial_window)
        if cursor is None:
            trace["status"] = "blocked"
            trace["failure"] = "Reset RGB did not show one uniquely locatable cursor"
            return trace
        if expected_reset_cursor is not None and cursor != expected_reset_cursor:
            trace["status"] = "blocked"
            trace["failure"] = f"Reset cursor expectation {expected_reset_cursor} disagrees with RGB cursor {cursor}"
            return trace
        current_window = initial_window
        actions: list[dict[str, object]] = trace["actions"]
        observations: list[dict[str, object]] = trace["observations"]
        total_reward = 0.0
        episode_env_steps = 0
        terminal_observed = False
        stop_reason: str | None = None
        max_env_steps = max_episode_frames // config.frameskip
        artifact_bytes = 0

        def set_turn_state(turn_index: int, state: TurnState, reason: str) -> None:
            trace["turn_events"].append(
                {"turn": turn_index, "state": state.value, "reason": reason, "frame_number": last_frame.frame_number}
            )

        def set_input_phase(
            turn: dict[str, object],
            phase: str,
            reason: str,
            **evidence: object,
        ) -> None:
            turn.setdefault("input_phases", []).append(
                {
                    "phase": phase,
                    "reason": reason,
                    "frame_number": last_frame.frame_number,
                    **evidence,
                }
            )

        def execute(action: int, requested_frames: int, name: str) -> list[ALEFrame]:
            nonlocal last_frame, total_reward, episode_env_steps, terminal_observed, stop_reason
            if terminal_observed or stop_reason:
                return []
            env_steps = math.ceil(requested_frames / config.frameskip)
            start_frame = last_frame.frame_number
            start_env_step = episode_env_steps
            start_rgb = last_frame.rgb
            samples: list[ALEFrame] = []
            reward_sum = 0.0
            for _ in range(env_steps):
                if time.monotonic() - started_monotonic >= max_episode_seconds:
                    stop_reason = "per-episode wall-clock budget reached"
                    break
                if episode_env_steps >= max_env_steps:
                    stop_reason = "per-episode ALE frame budget reached"
                    break
                last_frame = env.step(action)
                samples.append(last_frame)
                episode_env_steps += 1
                reward_sum += last_frame.reward
                total_reward += last_frame.reward
                terminal_observed = terminal_observed or last_frame.terminated or last_frame.truncated
                if last_frame.terminated or last_frame.truncated:
                    break
            actions.append(
                {
                    "name": name,
                    "action": ACTION_NAMES[action],
                    "action_index": action,
                    "requested_frames": requested_frames,
                    "frame_number_start": start_frame,
                    "frame_number_end": last_frame.frame_number,
                    "env_step_start": start_env_step,
                    "env_step_end": episode_env_steps,
                    "actual_frame_delta": last_frame.frame_number - start_frame,
                    "changed_pixels_start_to_end": int(np.any(start_rgb != last_frame.rgb, axis=2).sum()),
                    "ale_reward_sum": reward_sum,
                    "terminated": last_frame.terminated,
                    "truncated": last_frame.truncated,
                    "rgb_sha256_end": hashlib.sha256(last_frame.rgb.tobytes()).hexdigest(),
                }
            )
            return samples

        def observe_window(
            name: str,
            reference_board: chess.Board,
            frame_count: int = WINDOW_FRAMES,
        ) -> BoardWindow:
            nonlocal current_window
            samples = execute(NOOP, frame_count, name)
            if not samples:
                raise EpisodeStop(stop_reason or "No ALE frames were available for an observation window")
            current_window = vision.window(tuple(frame.rgb for frame in samples))
            observations.append(_window_record(current_window, samples[-1], reference_board))
            trace["ram_diagnostics_only"].append(
                {
                    "stage": name,
                    **env.diagnostic_ram((0xE1, 0xE4, 0xEA, 0xEE)),
                }
            )
            return current_window

        def move_cursor_to(target: str, reference_board: chess.Board, window: BoardWindow) -> BoardWindow:
            nonlocal current_window
            retries_without_progress = 0
            cursor_actions = 0
            inconclusive_windows = 0
            while cursor_actions < MAX_CURSOR_ACTIONS_PER_MOVE:
                if stop_reason or terminal_observed:
                    raise EpisodeStop(stop_reason or "ALE ended while moving the cursor")
                if not window.is_stable or not window.matches_board_except_cursor(reference_board):
                    window = observe_window("cursor state verification", reference_board)
                    inconclusive_windows += 1
                    if inconclusive_windows > 4:
                        raise EpisodeStop("RGB did not provide a stable board/cursor view")
                    continue
                observed = _unique_cursor(window)
                if observed is None:
                    window = observe_window("cursor location retry", reference_board)
                    inconclusive_windows += 1
                    if inconclusive_windows > 4:
                        raise EpisodeStop("Cursor remained missing or ambiguous in RGB windows")
                    continue
                if observed == target:
                    current_window = window
                    return window
                route = plan_cursor_route(observed, target, timing)
                if not route:
                    raise EpisodeStop(f"Cursor route from {observed} to {target} is empty but positions differ")
                step = route[0]
                execute(step.index, step.frames, f"cursor move toward {target} from {observed}")
                if stop_reason or terminal_observed:
                    raise EpisodeStop(stop_reason or "ALE ended during cursor movement")
                samples = execute(NOOP, timing.release_frames, "cursor direction release")
                cursor_actions += 1
                if stop_reason or terminal_observed:
                    raise EpisodeStop(stop_reason or "ALE ended during cursor movement")
                confirmed = False
                for sample_retry in range(WINDOW_FRAMES):
                    if len(samples) < 2:
                        extra = execute(NOOP, 1, "short cursor observation retry")
                        if not extra:
                            raise EpisodeStop(stop_reason or "ALE frame budget ended during cursor verification")
                        samples.extend(extra)
                        continue
                    candidate_window = vision.window(tuple(frame.rgb for frame in samples))
                    actual = _unique_cursor(candidate_window)
                    if (
                        candidate_window.is_stable
                        and actual is not None
                        and BoardEvidenceSet((window, candidate_window)).matches_board(reference_board)
                    ):
                        window = candidate_window
                        confirmed = True
                        trace["cursor_observations"].append(
                            {
                                "frame_number": last_frame.frame_number,
                                "from_square": observed,
                                "planned_square": step.cursor_after,
                                "observed_square": actual,
                                "movement_confirmed": actual != observed,
                                "unexpected_displacement": actual != step.cursor_after,
                            }
                        )
                        if actual == observed:
                            retries_without_progress += 1
                            if retries_without_progress >= 2:
                                raise EpisodeStop(f"Directional input did not move the cursor from {observed}")
                        else:
                            retries_without_progress = 0
                            inconclusive_windows = 0
                        break
                    inconclusive_windows += 1
                    if inconclusive_windows > WINDOW_FRAMES:
                        raise EpisodeStop("Cursor action changed or obscured the verified board")
                    extra = execute(NOOP, 1, "short cursor observation retry")
                    if not extra:
                        raise EpisodeStop(stop_reason or "ALE frame budget ended during cursor verification")
                    samples.extend(extra)
                if not confirmed:
                    raise EpisodeStop("Cursor remained unlocatable after bounded RGB samples")
            raise EpisodeStop(f"Cursor route exceeded {MAX_CURSOR_ACTIONS_PER_MOVE} verified actions")

        def save_frame(name: str) -> dict[str, object]:
            nonlocal artifact_bytes, stop_reason
            item: dict[str, object] = {
                "name": name,
                "frame_number": last_frame.frame_number,
                "rgb_sha256": hashlib.sha256(last_frame.rgb.tobytes()).hexdigest(),
            }
            if frames_dir is not None:
                if artifact_bytes + last_frame.rgb.nbytes > max_artifact_bytes:
                    stop_reason = "local experimental artifact-byte budget reached"
                    raise EpisodeStop(stop_reason)
                path = frames_dir / f"{name}.png"
                _write_png(path, last_frame.rgb)
                artifact_bytes += path.stat().st_size
                repo_root = Path(__file__).resolve().parents[1]
                try:
                    item["path"] = path.resolve().relative_to(repo_root).as_posix()
                except ValueError:
                    item["path"] = path.name
            trace.setdefault("frames", []).append(item)
            return item

        save_frame("reset")
        set_turn_state(0, TurnState.PLAYER_TURN, "stable reset RGB; white is the observed player side")

        for turn_index in range(1, max_player_moves + 1):
            if terminal_observed or stop_reason:
                break
            board_before = shadow.board.copy()
            if board_before.turn != chess.WHITE:
                set_turn_state(turn_index, TurnState.UNCERTAIN, "shadow board did not return to the white player turn")
                stop_reason = "Expected the white player turn after the observed Atari reply"
                break
            try:
                if not current_window.is_stable or not current_window.matches_board_except_cursor(board_before):
                    current_window = observe_window("player turn validation", board_before)
                current_cursor = _unique_cursor(current_window)
                if current_cursor is None or not current_window.matches_board_except_cursor(board_before):
                    raise EpisodeStop("Player turn lacked a stable legal board and unique cursor observation")

                player_move = selector(board_before.copy())
                planned_move = chess.Move.from_uci(player_move)
                if planned_move not in board_before.legal_moves:
                    raise EpisodeStop(f"Diagnostic selector returned an illegal move: {player_move}")
                plan = plan_move(current_cursor, player_move, board=board_before, timing=timing)
                turn: dict[str, object] = {
                    "turn": turn_index,
                    "board_before_fen": board_before.fen(),
                    "cursor_before": current_cursor,
                    "player_move": {"uci": player_move, "verified_from_rgb": False},
                    "opponent_reply": {"uci": None, "verified_from_rgb": False},
                    "evidence_windows": [],
                    "input_phases": [],
                    "selected_target_observations": [],
                }
                trace["turns"].append(turn)
                trace["player_move"] = turn["player_move"]
                trace["opponent_reply"] = turn["opponent_reply"]
                set_turn_state(turn_index, TurnState.PLAYER_MOVE_EXECUTING, f"executing legal move {player_move}")
                move_source = chess.square_name(planned_move.from_square)
                move_target = chess.square_name(planned_move.to_square)
                source_selection_verified = False
                target_position_verified = False
                set_input_phase(turn, "player_turn_verified", "stable RGB board and unique cursor matched the last verified shadow position")
                set_input_phase(turn, "cursor_navigating_to_source", f"navigating the cursor to {move_source}")
                if current_cursor == move_source:
                    set_input_phase(turn, "source_cursor_verified", f"RGB already showed the cursor on {move_source}", cursor_square=move_source)
                for event in plan:
                    if stop_reason or terminal_observed:
                        break
                    if event.cursor_after is not None:
                        current_window = move_cursor_to(event.cursor_after, board_before, current_window)
                        if event.cursor_after == move_source:
                            set_input_phase(
                                turn,
                                "source_cursor_verified",
                                f"RGB confirmed the cursor on {move_source}",
                                cursor_square=move_source,
                            )
                    elif event.phase == "cursor_to_source":
                        continue
                    elif event.phase == "settle_source":
                        settle_samples = execute(event.index, event.frames, event.phase)
                        if not settle_samples:
                            raise EpisodeStop("No ALE frames were available to verify the source cursor")
                        settle_window = vision.window(tuple(frame.rgb for frame in settle_samples))
                        if (
                            not settle_window.is_stable
                            or _unique_cursor(settle_window) != move_source
                            or not settle_window.matches_board_except_cursor(board_before)
                        ):
                            raise EpisodeStop("Source square/cursor was not stable before FIRE selection")
                        current_window = settle_window
                        set_input_phase(
                            turn,
                            "source_cursor_verified",
                            f"stable RGB confirmed the cursor and legal board at {move_source}",
                            cursor_square=move_source,
                            rgb_sha256=hashlib.sha256(settle_samples[-1].rgb.tobytes()).hexdigest(),
                        )
                    elif event.phase == "select_source":
                        set_input_phase(turn, "source_selection_requested", f"pressed FIRE once on {move_source}")
                        execute(event.index, event.frames, event.phase)
                    elif event.phase == "release_source":
                        execute(event.index, event.frames, event.phase)
                        save_frame(f"turn-{turn_index:02d}-source-fire-released")
                    elif event.phase == "verify_source_selection":
                        selection_samples = execute(event.index, event.frames, event.phase)
                        if not selection_samples:
                            raise EpisodeStop("No ALE frames were available to verify source selection")
                        selection_window = vision.window(tuple(frame.rgb for frame in selection_samples))
                        selection_evidence = _source_selection_evidence(
                            selection_window,
                            board_before,
                            move_source,
                        )
                        selection_evidence["window"] = _window_record(
                            selection_window,
                            selection_samples[-1],
                            board_before,
                        )
                        turn["source_selection_evidence"] = selection_evidence
                        if not selection_evidence["verified"]:
                            set_input_phase(
                                turn,
                                "source_selection_uncertain",
                                "RGB did not show the selected-piece blink; stopped before target input",
                                evidence=selection_evidence,
                            )
                            raise EpisodeStop("Source FIRE did not produce a verified selected-piece RGB signature")
                        source_selection_verified = True
                        set_input_phase(
                            turn,
                            "source_selection_verified",
                            "RGB showed the selected-piece blink with the cursor absent",
                            evidence=selection_evidence,
                        )
                        save_frame(f"turn-{turn_index:02d}-source-selection-verified")
                    elif event.phase == "selected_target_navigation":
                        if not source_selection_verified:
                            raise EpisodeStop("Selected-target navigation was blocked because source selection was unverified")
                        set_input_phase(
                            turn,
                            "selected_target_navigation_requested",
                            f"sent one {ACTION_NAMES[event.index]} input toward {event.selected_target_after}",
                            intended_target=event.selected_target_after,
                        )
                        execute(event.index, event.frames, event.phase)
                    elif event.phase == "release_selected_target":
                        execute(event.index, event.frames, event.phase)
                    elif event.phase == "verify_selected_target":
                        target_samples = execute(event.index, event.frames, event.phase)
                        if not target_samples:
                            raise EpisodeStop("No ALE frames were available to verify the selected target")
                        target_window = vision.window(tuple(frame.rgb for frame in target_samples))
                        target_evidence = _selected_target_evidence(
                            target_window,
                            board_before,
                            move_source,
                            event.selected_target_after or move_source,
                        )
                        target_evidence["window"] = _window_record(
                            target_window,
                            target_samples[-1],
                            board_before,
                        )
                        turn["selected_target_observations"].append(target_evidence)
                        if not target_evidence["verified"]:
                            set_input_phase(
                                turn,
                                "selected_target_uncertain",
                                "RGB did not verify the intended selected-piece preview; no direction was retried",
                                evidence=target_evidence,
                            )
                            raise EpisodeStop(
                                f"Selected target {event.selected_target_after} was not verifiable from RGB; stopped before FIRE"
                            )
                        target_position_verified = event.selected_target_after == move_target
                        set_input_phase(
                            turn,
                            "target_position_verified",
                            f"RGB showed the selected piece preview at {event.selected_target_after}",
                            evidence=target_evidence,
                        )
                        if event.selected_target_after == move_target:
                            save_frame(f"turn-{turn_index:02d}-target-position-verified")
                    elif event.phase == "select_target":
                        if not source_selection_verified or not target_position_verified:
                            raise EpisodeStop("Target FIRE was blocked because source or target position was unverified")
                        set_input_phase(
                            turn,
                            "target_confirmation_requested",
                            f"held FIRE for {event.frames} ALE frames at verified target {move_target}",
                            target_square=move_target,
                            fire_press_frames=event.frames,
                        )
                        execute(event.index, event.frames, event.phase)
                    elif event.phase == "release_target":
                        execute(event.index, event.frames, event.phase)
                        save_frame(f"turn-{turn_index:02d}-target-fire-released")
                    else:
                        execute(event.index, event.frames, event.phase)

                if stop_reason:
                    raise EpisodeStop(stop_reason)
                expected_player_board = board_before.copy()
                expected_player_board.push(planned_move)
                player_window: BoardWindow | None = None
                player_partial_streak = 0
                stagnant_windows = 0
                mismatch_windows = 0
                confirmation_frames = 0
                for _ in range(8):
                    if terminal_observed or stop_reason:
                        break
                    window = observe_window("player move RGB confirmation", expected_player_board)
                    confirmation_frames += window.observations.__len__() * config.frameskip
                    turn["evidence_windows"].append(_window_record(window, last_frame, expected_player_board))
                    remaining_selection = _selected_target_evidence(
                        window,
                        board_before,
                        move_source,
                        move_target,
                    )
                    if remaining_selection["verified"]:
                        set_input_phase(
                            turn,
                            "target_confirmation_uncertain",
                            "RGB still showed the selected piece at source and target after FIRE; stopped without retry",
                            evidence=remaining_selection,
                        )
                        raise EpisodeStop(
                            "Target FIRE did not produce a board transition; the selected-piece preview remained visible, so no retry was issued"
                        )
                    if not window.is_stable:
                        mismatch_windows += 1
                    elif window.matches_board(expected_player_board):
                        player_window = window
                        set_input_phase(
                            turn,
                            "move_transition_observed",
                            "RGB showed the complete candidate player board",
                            evidence=_window_record(window, last_frame, expected_player_board),
                        )
                        break
                    elif window.matches_board_except_cursor(expected_player_board):
                        player_partial_streak += 1
                        if player_partial_streak >= 1:
                            player_window = window
                            set_input_phase(
                                turn,
                                "move_transition_observed",
                                "RGB showed the candidate player board except for the cursor-masked square",
                                evidence=_window_record(window, last_frame, expected_player_board),
                            )
                            break
                    elif window.matches_board_except_cursor(board_before):
                        stagnant_windows += 1
                        if stagnant_windows >= 4:
                            raise EpisodeStop("Player move was not observed; FIRE selection or target input may have failed")
                    else:
                        mismatch_windows += 1
                        if mismatch_windows >= 4:
                            raise EpisodeStop("RGB showed an invalid or unresolved player transition")

                turn["player_move"].update(
                    {
                        "frames_to_candidate_rgb": confirmation_frames,
                        "partial_cursor_masked_candidate": bool(player_window and not player_window.matches_board(expected_player_board)),
                        "verified_from_rgb": False,
                        "candidate_fen": expected_player_board.fen(),
                    }
                )
                turn["player_move"]["diagnostic_ram_only"] = env.diagnostic_ram((0xE1, 0xE4, 0xEA, 0xEE))
                save_frame(f"turn-{turn_index:02d}-player-candidate")
                if player_window is None:
                    raise EpisodeStop("RGB did not confirm the player move within the bounded observation windows")

                set_input_phase(turn, "atari_thinking", "player candidate was observed; waiting for an RGB-verified Atari reply")
                set_turn_state(turn_index, TurnState.ATARI_THINKING, "player candidate observed; waiting for a unique legal Atari reply")
                pending_shadow = ShadowBoard(board=expected_player_board)
                waited_frames = 0
                candidate_reply: str | None = None
                candidate_streak = 0
                mismatch_streak = 0
                reply_window: BoardWindow | None = None
                while waited_frames < max_opponent_wait_frames and not terminal_observed and not stop_reason:
                    chunk = min(WINDOW_FRAMES, max_opponent_wait_frames - waited_frames)
                    window = observe_window("Atari thinking/reply observation", expected_player_board, chunk)
                    waited_frames += max(1, window.observations.__len__()) * config.frameskip
                    turn["evidence_windows"].append(_window_record(window, last_frame, expected_player_board))
                    if not window.is_stable:
                        mismatch_streak += 1
                        if mismatch_streak >= 10:
                            raise EpisodeStop("Atari reply remained visually transitional or ambiguous for ten windows")
                        continue
                    try:
                        inferred = pending_shadow.infer_observed_reply(window, allow_cursor_masked_square=True)
                    except DesynchronizationError:
                        mismatch_streak += 1
                        candidate_reply = None
                        candidate_streak = 0
                        if mismatch_streak >= 10:
                            raise EpisodeStop("RGB did not match the current board or one legal Atari reply")
                        continue
                    mismatch_streak = 0
                    if inferred is None:
                        candidate_reply = None
                        candidate_streak = 0
                        continue
                    if inferred == candidate_reply:
                        candidate_streak += 1
                    else:
                        candidate_reply = inferred
                        candidate_streak = 1
                    if candidate_streak >= 2:
                        reply_window = window
                        break

                turn["opponent_reply"]["frames_waited"] = waited_frames
                turn["opponent_reply"]["candidate_uci"] = candidate_reply
                turn["opponent_reply"]["candidate_from_rgb"] = reply_window is not None
                turn["opponent_reply"]["diagnostic_ram_only"] = env.diagnostic_ram((0xE1, 0xE4, 0xEA, 0xEE))
                if terminal_observed:
                    break
                if reply_window is None or candidate_reply is None:
                    raise EpisodeStop("No stable unique legal Atari reply appeared within the bounded wait")

                reply_move = chess.Move.from_uci(candidate_reply)
                final_candidate = expected_player_board.copy()
                if reply_move not in final_candidate.legal_moves:
                    raise EpisodeStop(f"Inferred Atari reply became illegal before verification: {candidate_reply}")
                final_candidate.push(reply_move)
                reply_cursor = _unique_cursor(reply_window)
                if reply_cursor is None:
                    raise EpisodeStop("Atari reply window did not contain one unique cursor position")
                verification_square = _verification_square(final_candidate, reply_cursor)
                verification_window = move_cursor_to(verification_square, final_candidate, reply_window)
                evidence_set = BoardEvidenceSet((reply_window, verification_window))
                if not evidence_set.matches_board(final_candidate):
                    verification_window = observe_window("full-board coverage retry", final_candidate)
                    evidence_set = BoardEvidenceSet((reply_window, verification_window))
                if not evidence_set.matches_board(final_candidate):
                    raise EpisodeStop("Two stable cursor positions did not jointly verify every board square")

                applied = shadow.apply_observed_sequence((player_move, candidate_reply), evidence_set)
                if applied != (player_move, candidate_reply):
                    raise DesynchronizationError("Verified transition sequence changed before shadow update")
                turn["player_move"].update(
                    {
                        "verified_from_rgb": True,
                        "verification": "intermediate partial window plus complete two-cursor-position RGB coverage",
                        "shadow_fen_after": expected_player_board.fen(),
                    }
                )
                turn["opponent_reply"].update(
                    {
                        "uci": candidate_reply,
                        "verified_from_rgb": True,
                        "shadow_fen_after": shadow.board.fen(),
                        "verification": "unique legal candidate repeated in two windows, then full RGB coverage",
                    }
                )
                set_input_phase(
                    turn,
                    "player_move_confirmed",
                    "the player move and Atari reply were verified by complete multi-cursor RGB coverage",
                    player_move=player_move,
                    opponent_reply=candidate_reply,
                    final_board_rgb_verified=True,
                )
                set_input_phase(
                    turn,
                    "opponent_move_confirmed",
                    f"RGB confirmed the legal Atari reply {candidate_reply}",
                    opponent_reply=candidate_reply,
                )
                turn["board_after_fen"] = shadow.board.fen()
                turn["full_board_evidence"] = {
                    "cursor_positions": [sorted(reply_window.cursor_squares), sorted(verification_window.cursor_squares)],
                    "all_squares_covered": True,
                }
                trace["player_move"] = turn["player_move"]
                trace["opponent_reply"] = turn["opponent_reply"]
                trace["final_position"] = {"matches_shadow_board": True, "shadow_fen": shadow.board.fen()}
                set_turn_state(turn_index, TurnState.OPPONENT_MOVE_COMPLETED, f"RGB confirmed legal Atari move {candidate_reply}")
                save_frame(f"turn-{turn_index:02d}-verified-board")
                trace["ram_diagnostics_only"].append(
                    {"stage": f"turn-{turn_index}-verified-board", **env.diagnostic_ram((0xE1, 0xE4, 0xEA, 0xEE))}
                )
                if terminal_observed:
                    break
                if turn_index < max_player_moves:
                    set_turn_state(turn_index, TurnState.PLAYER_TURN, "complete RGB-verified two-ply transition")
                    current_window = verification_window
            except (EpisodeStop, DesynchronizationError, ValueError) as exc:
                stop_reason = str(exc)
                set_turn_state(turn_index, TurnState.UNCERTAIN, stop_reason)
                break

        trace["terminal"].update(
            {
                "observed": terminal_observed,
                "terminated": last_frame.terminated,
                "truncated": last_frame.truncated,
                "ale_reward_total": total_reward,
                "agent_reward_total": agent_reward_from_ale(total_reward, chess.WHITE),
                "white_result_from_reward": (
                    "white_win" if total_reward > 0 else "white_loss" if total_reward < 0 else None
                ),
                "last_reward": last_frame.reward,
                "last_verified_fen": shadow.board.fen() if shadow.board else None,
                "frame_number": last_frame.frame_number,
                "wall_seconds": round(time.monotonic() - started_monotonic, 3),
                "env_steps": episode_env_steps,
                "artifact_bytes": artifact_bytes,
                "stop_reason": stop_reason,
            }
        )
        if last_frame.terminated:
            set_turn_state(len(trace["turns"]), TurnState.EPISODE_FINISHED, "ALE terminated=True")
        elif last_frame.truncated:
            set_turn_state(len(trace["turns"]), TurnState.EPISODE_TRUNCATED, "ALE truncated=True")
        if stop_reason:
            trace["status"] = "partial"
            trace["failure"] = stop_reason
        elif terminal_observed or len(trace["turns"]) == max_player_moves:
            trace["status"] = "complete"
        else:
            trace["status"] = "partial"
            trace["failure"] = "Episode stopped before a verified move cycle completed"
    return trace
