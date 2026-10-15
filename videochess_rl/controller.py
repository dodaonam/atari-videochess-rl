"""Measured Atari action plans for the VideoChess joystick and FIRE button."""

from __future__ import annotations

from dataclasses import dataclass

import chess


NOOP = 0
FIRE = 1
UP = 2
RIGHT = 3
LEFT = 4
DOWN = 5
UPRIGHT = 6
UPLEFT = 7
DOWNRIGHT = 8
DOWNLEFT = 9
DIRECTION_FRAMES = 33
FIRE_SETTLE_FRAMES = 33


@dataclass(frozen=True)
class ActionFrame:
    index: int
    frames: int
    cursor_after: str | None = None
    phase: str = "action"


@dataclass(frozen=True)
class ControllerTiming:
    direction_frames: int = DIRECTION_FRAMES
    fire_settle_frames: int = FIRE_SETTLE_FRAMES
    fire_press_frames: int = 1
    release_frames: int = 1
    frameskip: int = 1
    repeat_action_probability: float = 0.0

    def __post_init__(self) -> None:
        if min(self.direction_frames, self.fire_settle_frames, self.fire_press_frames, self.release_frames, self.frameskip) < 1:
            raise ValueError("Controller frame timings and frameskip must be positive")
        if not 0.0 <= self.repeat_action_probability <= 1.0:
            raise ValueError("repeat_action_probability must be between 0 and 1")


def _square(square: str) -> tuple[int, int]:
    if len(square) != 2 or square[0] not in "abcdefgh" or square[1] not in "12345678":
        raise ValueError(f"Invalid chess square: {square!r}")
    return 8 - int(square[1]), ord(square[0]) - ord("a")


def _cursor_steps(start: str, target: str) -> list[int]:
    row, col = _square(start)
    target_row, target_col = _square(target)
    actions: list[int] = []
    while row != target_row and col != target_col:
        row_action = UP if target_row < row else DOWN
        col_action = RIGHT if target_col > col else LEFT
        action = {
            (UP, RIGHT): UPRIGHT,
            (UP, LEFT): UPLEFT,
            (DOWN, RIGHT): DOWNRIGHT,
            (DOWN, LEFT): DOWNLEFT,
        }[(row_action, col_action)]
        actions.append(action)
        row += -1 if row_action == UP else 1
        col += 1 if col_action == RIGHT else -1
    while col != target_col:
        action = RIGHT if target_col > col else LEFT
        col += 1 if action == RIGHT else -1
        actions.append(action)
    while row != target_row:
        action = DOWN if target_row > row else UP
        row += 1 if action == DOWN else -1
        actions.append(action)
    return actions


def _cursor_path(start: str, target: str) -> list[tuple[int, str]]:
    row, col = _square(start)
    path: list[tuple[int, str]] = []
    for action in _cursor_steps(start, target):
        if action == RIGHT:
            col += 1
        elif action == LEFT:
            col -= 1
        elif action == DOWN:
            row += 1
        elif action == UPRIGHT:
            row -= 1
            col += 1
        elif action == UPLEFT:
            row -= 1
            col -= 1
        elif action == DOWNRIGHT:
            row += 1
            col += 1
        elif action == DOWNLEFT:
            row += 1
            col -= 1
        else:
            row -= 1
        path.append((action, chr(ord("a") + col) + str(8 - row)))
    return path


def plan_cursor_route(
    cursor_origin: str,
    target: str,
    timing: ControllerTiming | None = None,
) -> tuple[ActionFrame, ...]:
    """Plan one verified cursor step at a time toward a requested square."""
    timing = timing or ControllerTiming()
    return tuple(
        ActionFrame(action, timing.direction_frames, cursor_after=square, phase="cursor_route")
        for action, square in _cursor_path(cursor_origin, target)
    )


def plan_move(
    cursor_origin: str,
    uci: str,
    *,
    board: chess.Board | None = None,
    timing: ControllerTiming | None = None,
) -> tuple[ActionFrame, ...]:
    """Plan a legal move from the supplied verified position and observed cursor.

    Direction holds and short FIRE pulses reflect the measured deterministic
    development configuration. Each pulse remains an Atari joystick action;
    the board is verified separately from RGB after execution.
    """
    try:
        move = chess.Move.from_uci(uci)
        source = chess.square_name(move.from_square)
        target = chess.square_name(move.to_square)
        _square(cursor_origin)
    except (ValueError, IndexError) as exc:
        raise ValueError(f"Invalid square or UCI move: {uci!r}") from exc

    board = board or chess.Board()
    timing = timing or ControllerTiming()
    if move not in board.legal_moves:
        raise ValueError(f"Move is not legal from the current position: {uci}")

    actions: list[ActionFrame] = []
    for start, destination, phase, cursor_is_moving in (
        (cursor_origin, source, "cursor_to_source", True),
        (source, target, "selected_target_navigation", False),
    ):
        path = _cursor_path(start, destination)
        for index, (direction, cursor_after) in enumerate(path):
            actions.append(
                ActionFrame(
                    direction,
                    timing.direction_frames,
                    cursor_after if cursor_is_moving else None,
                    phase,
                )
            )
            if index < len(path) - 1:
                actions.append(ActionFrame(NOOP, timing.release_frames, phase=phase))
        if phase == "cursor_to_source":
            actions.extend((
                ActionFrame(NOOP, timing.fire_settle_frames, phase="settle_source"),
                ActionFrame(FIRE, timing.fire_press_frames, phase="select_source"),
                ActionFrame(NOOP, timing.release_frames, phase="release_source"),
            ))
    actions.extend((
        ActionFrame(NOOP, timing.fire_settle_frames, phase="settle_target"),
        ActionFrame(FIRE, timing.fire_press_frames, phase="select_target"),
        ActionFrame(NOOP, timing.release_frames, phase="release_target"),
    ))
    return tuple(actions)
