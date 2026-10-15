"""Bounded observation-driven M1 closed-loop demonstration."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import zlib

import chess
import numpy as np

from .controller import ActionFrame, DOWN, LEFT, NOOP, RIGHT, UP, plan_move
from .environment import ALEConfig, ALEFrame, VideoChessEnv
from .shadow import DesynchronizationError, ShadowBoard
from .vision import BoardObservation, BoardWindow, VideoChessVision


WINDOW_FRAMES = 33
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


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git_revision() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _git_state() -> dict[str, object]:
    repo = Path(__file__).resolve().parents[1]
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo,
        ).stdout.splitlines()
        return {"branch": branch, "head": _git_revision(), "dirty_paths": status}
    except (OSError, subprocess.CalledProcessError):
        return {"branch": None, "head": None, "dirty_paths": []}


def _write_png(path: Path, rgb: np.ndarray) -> None:
    height, width, _ = rgb.shape

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    rows = b"".join(b"\0" + row.tobytes() for row in rgb)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows, 9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def _window_summary(window: BoardWindow) -> dict[str, object]:
    squares = ("e2", "e3", "c7", "c5")
    return {
        "cursor_squares": sorted(window.cursor_squares),
        "cells": {
            square: {
                "side": window.cell(square).side,
                "gold_piece_seen": window.cell(square).gold_piece_seen,
                "blue_piece_seen": window.cell(square).blue_piece_seen,
                "cursor_seen": window.cell(square).cursor_seen,
            }
            for square in squares
        },
    }


def run_closed_loop(
    *,
    config: ALEConfig | None = None,
    seed: int = 20261015,
    player_move: str = "e2e3",
    cursor_origin: str = "d4",
    max_opponent_wait_frames: int = 10000,
    artifact_dir: Path | None = None,
) -> dict[str, object]:
    """Execute and verify one real player move and one real ALE reply.

    RGB is the only input used to plan/check moves. ALE RAM is read separately
    for diagnostics and is never passed to the controller or shadow board.
    """
    if max_opponent_wait_frames < WINDOW_FRAMES:
        raise ValueError(f"max_opponent_wait_frames must be at least {WINDOW_FRAMES}")
    config = config or ALEConfig.deterministic_dev()
    trace: dict[str, object] = {
        "created_at_utc": _utc_now(),
        "git": _git_state(),
        "seed": seed,
        "config": config.as_dict(),
        "runtime": {},
        "reset": {},
        "actions": [],
        "ram_diagnostics_only": [],
        "player_move": {"uci": player_move, "verified_from_rgb": False},
        "opponent_reply": {"uci": None, "verified_from_rgb": False},
        "terminal": {"observed": False, "reward_total": 0.0},
    }

    frames_dir = artifact_dir
    if frames_dir is not None:
        frames_dir.mkdir(parents=True, exist_ok=True)

    with VideoChessEnv(config) as env:
        vision = VideoChessVision()
        reset = env.reset(seed=seed)
        trace["runtime"] = env.runtime_info()
        initial = vision.observe(reset.rgb)
        trace["reset"] = {
            "frame_number": reset.frame_number,
            "rgb_shape": list(reset.rgb.shape),
            "rgb_dtype": str(reset.rgb.dtype),
            "rgb_sha256": hashlib.sha256(reset.rgb.tobytes()).hexdigest(),
            "cursor_squares": sorted(initial.cursor_squares),
            "initial_position_verified_from_rgb": initial.matches_start_position(),
            "info_keys": sorted(reset.info),
        }
        trace["initial_position"] = {
            "verified_from_rgb": initial.matches_start_position(),
            "cursor_squares": sorted(initial.cursor_squares),
        }

        def capture(name: str, frame: ALEFrame, observation: BoardObservation | None = None) -> dict[str, object]:
            digest = hashlib.sha256(frame.rgb.tobytes()).hexdigest()
            item: dict[str, object] = {
                "name": name,
                "frame_number": frame.frame_number,
                "rgb_sha256": digest,
            }
            if frames_dir is not None:
                image_path = frames_dir / f"{name}.png"
                _write_png(image_path, frame.rgb)
                repo_root = Path(__file__).resolve().parents[1]
                try:
                    item["path"] = image_path.resolve().relative_to(repo_root).as_posix()
                except ValueError:
                    item["path"] = image_path.name
            if observation is not None:
                item["cursor_squares"] = sorted(observation.cursor_squares)
                item["e2"] = observation.cell("e2").__dict__
                item["e3"] = observation.cell("e3").__dict__
                item["c7"] = observation.cell("c7").__dict__
                item["c5"] = observation.cell("c5").__dict__
            return item

        captures: list[dict[str, object]] = [capture("reset", reset, initial)]
        trace["frames"] = captures
        trace["ram_diagnostics_only"].append(
            {"stage": "reset", **env.diagnostic_ram((0xE1, 0xE4, 0xEA))}
        )
        if not trace["initial_position"]["verified_from_rgb"]:
            trace["status"] = "blocked"
            trace["failure"] = "RGB reset observation does not match the verified standard start layout"
            return trace
        if initial.cursor_squares != frozenset({cursor_origin}):
            trace["status"] = "blocked"
            trace["failure"] = f"Expected reset cursor at {cursor_origin}; observed {sorted(initial.cursor_squares)}"
            return trace

        shadow = ShadowBoard()
        actions: list[dict[str, object]] = trace["actions"]
        total_reward = 0.0
        last_frame = reset
        terminal_observed = False

        def execute(event: ActionFrame, name: str) -> list[ALEFrame]:
            nonlocal last_frame, total_reward, terminal_observed
            requested = event.frames
            env_steps = math.ceil(requested / config.frameskip)
            start_frame = last_frame.frame_number
            start_rgb = last_frame.rgb
            samples: list[ALEFrame] = []
            reward_sum = 0.0
            for _ in range(env_steps):
                last_frame = env.step(event.index)
                samples.append(last_frame)
                reward_sum += last_frame.reward
                terminal_observed = terminal_observed or last_frame.terminated or last_frame.truncated
                if last_frame.terminated or last_frame.truncated:
                    break
            total_reward += reward_sum
            actions.append(
                {
                    "name": name,
                    "action": ACTION_NAMES[event.index],
                    "action_index": event.index,
                    "requested_frames": requested,
                    "actual_frame_delta": last_frame.frame_number - start_frame,
                    "changed_pixels_start_to_end": int(np.any(start_rgb != last_frame.rgb, axis=2).sum()),
                    "reward_sum": reward_sum,
                    "terminated": last_frame.terminated,
                    "truncated": last_frame.truncated,
                    "rgb_sha256_end": hashlib.sha256(last_frame.rgb.tobytes()).hexdigest(),
                }
            )
            return samples

        def observe_noop_window(frame_count: int) -> tuple[BoardWindow, ALEFrame, int]:
            start_frame = last_frame.frame_number
            samples = execute(ActionFrame(NOOP, frame_count), "NOOP verification window")
            window = vision.window(tuple(frame.rgb for frame in samples))
            return window, samples[-1], samples[-1].frame_number - start_frame

        action_plan = plan_move(cursor_origin, player_move)
        for index, event in enumerate(action_plan):
            execute(event, f"player action {index + 1}")
            if (
                event.index in (UP, RIGHT, LEFT, DOWN)
                and event.frames >= 33
                and actions[-1]["changed_pixels_start_to_end"] == 0
            ):
                trace["status"] = "partial"
                trace["failure"] = "Directional Atari action produced no RGB change; remaining actions were stopped"
                trace["terminal"].update({"observed": terminal_observed, "reward_total": total_reward})
                return trace
            if terminal_observed:
                break

        move = chess.Move.from_uci(player_move)
        expected_player_board = shadow.board.copy()
        if move not in expected_player_board.legal_moves:
            trace["status"] = "blocked"
            trace["failure"] = f"Requested player move is not legal: {player_move}"
            return trace
        expected_player_board.push(move)

        player_window: BoardWindow | None = None
        stabilization_frames = 0
        while stabilization_frames < 10 * WINDOW_FRAMES and not terminal_observed:
            window, last_frame, actual_delta = observe_noop_window(WINDOW_FRAMES)
            stabilization_frames += actual_delta
            if window.matches_board(expected_player_board):
                player_window = window
                break
        trace["player_move"].update(
            {
                "frames_to_rgb_confirmation": stabilization_frames,
                "verified_from_rgb": player_window is not None,
                "board_window": _window_summary(player_window) if player_window else None,
            }
        )
        trace["ram_diagnostics_only"].append(
            {"stage": "after-player-window", **env.diagnostic_ram((0xE1, 0xE4, 0xEA))}
        )
        captures.append(capture("after-player-move", last_frame, vision.observe(last_frame.rgb)))
        if player_window is None:
            trace["status"] = "partial"
            trace["failure"] = "RGB did not confirm the player move within the bounded stabilization window"
            trace["terminal"].update({"observed": terminal_observed, "reward_total": total_reward})
            return trace

        shadow.apply_observed_move(player_move, player_window)
        trace["player_move"]["shadow_fen_after"] = shadow.board.fen()

        waited_frames = 0
        candidate_reply: str | None = None
        candidate_streak = 0
        mismatch_streak = 0
        reply_window: BoardWindow | None = None
        while waited_frames < max_opponent_wait_frames and not terminal_observed:
            chunk = min(WINDOW_FRAMES, max_opponent_wait_frames - waited_frames)
            window, last_frame, actual_delta = observe_noop_window(chunk)
            waited_frames += actual_delta
            try:
                inferred = shadow.infer_observed_reply(window)
            except DesynchronizationError as exc:
                mismatch_streak += 1
                candidate_reply = None
                candidate_streak = 0
                if mismatch_streak >= 3:
                    trace["status"] = "partial"
                    trace["failure"] = f"Persistent RGB/shadow mismatch while waiting for Atari reply: {exc}"
                    break
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

        trace["opponent_reply"].update(
            {
                "frames_waited": waited_frames,
                "verified_from_rgb": reply_window is not None,
                "uci": candidate_reply if reply_window else None,
                "board_window": _window_summary(reply_window) if reply_window else None,
            }
        )
        if reply_window is not None:
            observed_reply = shadow.apply_observed_reply(reply_window)
            if observed_reply != candidate_reply:
                raise DesynchronizationError("Opponent reply changed between inference and shadow update")
            trace["opponent_reply"]["shadow_fen_after"] = shadow.board.fen()
            trace["status"] = "complete"
        elif "status" not in trace:
            trace["status"] = "partial"
            trace["failure"] = "No stable legal Atari reply was observed within the bounded wait"

        final_window = reply_window
        trace["final_position"] = {
            "matches_shadow_board": final_window.matches_board(shadow.board) if final_window else False,
            "shadow_fen": shadow.board.fen(),
        }
        captures.append(capture("final", last_frame, vision.observe(last_frame.rgb)))
        trace["ram_diagnostics_only"].append(
            {"stage": "final", **env.diagnostic_ram((0xE1, 0xE4, 0xEA))}
        )
        trace["terminal"].update({"observed": terminal_observed, "reward_total": total_reward})
        trace["terminal"]["last_reward"] = last_frame.reward
        trace["terminal"]["last_terminated"] = last_frame.terminated
        trace["terminal"]["last_truncated"] = last_frame.truncated

    return trace


def write_trace(path: Path, trace: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
