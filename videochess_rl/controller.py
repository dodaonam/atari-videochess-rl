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
DIRECTION_FRAMES = 33
FIRE_SETTLE_FRAMES = 33


@dataclass(frozen=True)
class ActionFrame:
    index: int
    frames: int


def _square(square: str) -> tuple[int, int]:
    if len(square) != 2 or square[0] not in "abcdefgh" or square[1] not in "12345678":
        raise ValueError(f"Invalid chess square: {square!r}")
    return 8 - int(square[1]), ord(square[0]) - ord("a")


def _cursor_steps(start: str, target: str) -> list[int]:
    row, col = _square(start)
    target_row, target_col = _square(target)
    actions: list[int] = []
    while col != target_col:
        action = RIGHT if target_col > col else LEFT
        col += 1 if action == RIGHT else -1
        actions.append(action)
    while row != target_row:
        action = DOWN if target_row > row else UP
        row += 1 if action == DOWN else -1
        actions.append(action)
    return actions


def plan_move(cursor_origin: str, uci: str) -> tuple[ActionFrame, ...]:
    """Plan one legal move from the observed initial chess position.

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

    board = chess.Board()
    if move not in board.legal_moves:
        raise ValueError(f"Move is not legal from the observed start position: {uci}")

    actions: list[ActionFrame] = []
    cursor = cursor_origin
    cursor_actions = _cursor_steps(cursor, source)
    for index, direction in enumerate(cursor_actions):
        actions.append(ActionFrame(direction, DIRECTION_FRAMES))
        if index < len(cursor_actions) - 1:
            actions.append(ActionFrame(NOOP, 1))
        row, col = _square(cursor)
        if direction == RIGHT:
            col += 1
        elif direction == LEFT:
            col -= 1
        elif direction == DOWN:
            row += 1
        else:
            row -= 1
        cursor = chr(ord("a") + col) + str(8 - row)

    actions.extend((ActionFrame(NOOP, FIRE_SETTLE_FRAMES), ActionFrame(FIRE, 1), ActionFrame(NOOP, 1)))

    movement = _cursor_steps(source, target)
    for index, direction in enumerate(movement):
        actions.append(ActionFrame(direction, DIRECTION_FRAMES))
        if index < len(movement) - 1:
            actions.append(ActionFrame(NOOP, 1))

    actions.extend((ActionFrame(NOOP, FIRE_SETTLE_FRAMES), ActionFrame(FIRE, 1), ActionFrame(NOOP, 1)))
    return tuple(actions)
