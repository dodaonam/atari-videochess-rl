"""Run a preflighted, bounded Atari VideoChess session in the local Tk viewer."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
import uuid

from .common import ARTIFACTS, write

ROM_SHA256 = "d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7"


def diagnose_replay_artifacts(trace: object, artifact_dir: Path) -> list[dict[str, object]]:
    """Report replay evidence gaps without inventing or accepting a board state."""
    import chess

    diagnostics: list[dict[str, object]] = []

    def add(severity: str, code: str, message: str, turn: int | None = None) -> None:
        item: dict[str, object] = {"severity": severity, "code": code, "message": message}
        if turn is not None:
            item["turn"] = turn
        diagnostics.append(item)

    if not isinstance(trace, dict):
        add("ERROR", "REPLAY_TRACE_INVALID", "Replay trace metadata is missing or malformed.")
        return diagnostics
    turns = trace.get("turns")
    if not isinstance(turns, list):
        add("ERROR", "REPLAY_TURNS_INVALID", "Replay turn metadata is missing or malformed.")
        return diagnostics
    recorded_frames = trace.get("frames")
    if recorded_frames is not None and not isinstance(recorded_frames, list):
        add("ERROR", "REPLAY_FRAME_METADATA_INVALID", "Replay frame metadata is malformed.")
        recorded_frames = []
    frame_names = {
        item.get("name") for item in (recorded_frames or [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }

    artifact_dir = Path(artifact_dir)
    if not (artifact_dir / "reset.png").is_file():
        add("WARNING", "REPLAY_RESET_FRAME_MISSING", "The initial RGB replay frame is missing.")

    board = chess.Board()
    seen_turns: set[int] = set()
    for index, turn in enumerate(turns):
        if not isinstance(turn, dict):
            add("ERROR", "REPLAY_TURN_INVALID", f"Replay turn {index + 1} is malformed.")
            continue
        number = turn.get("turn")
        if not isinstance(number, int) or isinstance(number, bool) or number < 1 or number in seen_turns:
            add("ERROR", "REPLAY_TURN_ID_INVALID", f"Replay turn {index + 1} has an invalid or duplicate turn number.")
            continue
        seen_turns.add(number)

        player = turn.get("player_move")
        reply = turn.get("opponent_reply")
        if not isinstance(player, dict) or not isinstance(reply, dict):
            add("ERROR", "REPLAY_MOVE_METADATA_INVALID", f"Replay move metadata for turn {number} is incomplete.", number)
            continue
        player_path = artifact_dir / f"turn-{number:02d}-player-candidate.png"
        board_path = artifact_dir / f"turn-{number:02d}-verified-board.png"
        player_image = player_path.is_file()
        board_image = board_path.is_file()
        player_frame_recorded = f"turn-{number:02d}-player-candidate" in frame_names
        board_frame_recorded = f"turn-{number:02d}-verified-board" in frame_names
        player_uci = player.get("uci")
        player_verified = player.get("verified_from_rgb") is True
        player_attempted = player.get("input_initiated") is True
        phases = turn.get("input_phases")
        phases = phases if isinstance(phases, list) else []
        candidate_stage_reached = (
            "candidate_fen" in player or player_frame_recorded
            or any(isinstance(phase, dict) and phase.get("phase") in {
                "move_transition_observed", "atari_thinking"} for phase in phases)
        )

        if not isinstance(player_uci, str) or not player_uci:
            if player_attempted or player_verified or player_image:
                add("ERROR", "REPLAY_PLAYER_MOVE_INCONSISTENT", f"Turn {number} has player action evidence without a move identity.", number)
            if reply.get("verified_from_rgb") is True or board_image:
                add("ERROR", "REPLAY_REPLY_WITHOUT_PLAYER", f"Turn {number} has reply evidence without a player move.", number)
            continue
        try:
            player_move = chess.Move.from_uci(player_uci)
            if player_move not in board.legal_moves:
                raise ValueError("illegal in verified replay history")
        except (ValueError, TypeError):
            add("ERROR", "REPLAY_PLAYER_MOVE_INVALID", f"Turn {number} has an invalid move in replay metadata.", number)
            continue
        if player_verified and not player_attempted:
            add("ERROR", "REPLAY_PLAYER_VERIFICATION_INCONSISTENT", f"Turn {number} is marked verified without initiated input.", number)
        if candidate_stage_reached and not player_attempted:
            add("ERROR", "REPLAY_CANDIDATE_WITHOUT_INPUT", f"Turn {number} has candidate-stage evidence without initiated input.", number)
        if player_image and not player_attempted:
            add("ERROR", "REPLAY_PLAYER_ARTIFACT_INCONSISTENT", f"Turn {number} has a candidate image without an initiated action.", number)
        if player_image and not player_frame_recorded:
            add("ERROR", "REPLAY_PLAYER_ARTIFACT_UNRECORDED", f"Turn {number} has a candidate image absent from trace frame metadata.", number)
        if not player_image:
            if player_verified or candidate_stage_reached:
                add("WARNING", "REPLAY_PLAYER_FRAME_MISSING", f"The RGB candidate image for turn {number} is missing.", number)
            elif player_attempted:
                add("INFO", "REPLAY_UNVERIFIED_CANDIDATE_NOT_PRODUCED", f"No candidate image was produced for unverified turn {number}; replay remains at the last verified state.", number)

        reply_verified = reply.get("verified_from_rgb") is True
        reply_uci = reply.get("uci")
        if reply_verified and not player_verified:
            add("ERROR", "REPLAY_REPLY_VERIFICATION_INCONSISTENT", f"Turn {number} has a verified Atari reply without a verified player move.", number)
        if board_image and not reply_verified:
            add("ERROR", "REPLAY_BOARD_ARTIFACT_INCONSISTENT", f"Turn {number} has a verified-board image without a verified Atari reply.", number)
        if board_image and not board_frame_recorded:
            add("ERROR", "REPLAY_BOARD_ARTIFACT_UNRECORDED", f"Turn {number} has a verified-board image absent from trace frame metadata.", number)

        # This validator follows only fully RGB-verified moves. A policy-selected
        # or candidate UCI never advances the diagnostic board by itself.
        if player_verified:
            board.push(player_move)
        if reply_verified:
            if not isinstance(reply_uci, str) or not reply_uci:
                add("ERROR", "REPLAY_REPLY_MOVE_INVALID", f"Turn {number} has a verified Atari reply without a move identity.", number)
                continue
            try:
                reply_move = chess.Move.from_uci(reply_uci)
                if reply_move not in board.legal_moves:
                    raise ValueError("illegal in verified replay history")
            except (ValueError, TypeError):
                add("ERROR", "REPLAY_REPLY_MOVE_INVALID", f"Turn {number} has an invalid move in replay metadata.", number)
                continue
            if not board_image:
                add("WARNING", "REPLAY_VERIFIED_REPLY_FRAME_MISSING", f"The RGB board image for verified Atari reply {number} is missing.", number)
            board.push(reply_move)

    return diagnostics


def verified_replay_snapshot_count(trace: object) -> int:
    """Count actual reset/player/reply RGB states represented by a trace."""
    if not isinstance(trace, dict):
        return 0
    initial = trace.get("initial_position")
    count = int(isinstance(initial, dict) and initial.get("verified_from_rgb") is True)
    turns = trace.get("turns")
    if not isinstance(turns, list):
        return count
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        player = turn.get("player_move")
        reply = turn.get("opponent_reply")
        count += int(isinstance(player, dict) and player.get("verified_from_rgb") is True)
        count += int(isinstance(reply, dict) and reply.get("verified_from_rgb") is True)
    return count


def build_live_summary(
    trace: object,
    *,
    metadata: dict | None = None,
    worker_status: str = "completed",
    worker_error_type: str | None = None,
    worker_error: str | None = None,
    replay_diagnostics: list[dict[str, object]] | None = None,
    replay_state_count: int | None = None,
) -> dict[str, object]:
    """Build a concise local result record without move-level or RGB payloads."""
    metadata = metadata or {}
    trace_data = trace if isinstance(trace, dict) else {}
    terminal = trace_data.get("terminal")
    terminal = terminal if isinstance(terminal, dict) else {}
    category = terminal.get("runner_stop_category")
    if worker_status != "completed":
        outcome = "worker_runtime_failure"
    elif terminal.get("ale_terminated") is True:
        outcome = "ale_game_terminated"
    elif terminal.get("ale_truncated") is True:
        outcome = "ale_truncated"
    elif category == "RUNNER_USER_CANCEL":
        outcome = "user_cancelled"
    elif isinstance(category, str) and (category.startswith("RUNNER_MAX_") or category in {
            "RUNNER_ARTIFACT_LIMIT", "RUNNER_RESOURCE_LIMIT"}):
        outcome = "runner_limit"
    elif isinstance(category, str) and (category.startswith("CONTROLLER_") or category == "OPPONENT_RESPONSE_TIMEOUT"):
        outcome = "controller_uncertainty"
    elif isinstance(category, str) and category in {"EXCEPTION_OR_EXTERNAL_INTERRUPTION", "UNKNOWN"}:
        outcome = "episode_runtime_failure"
    elif category:
        outcome = "incomplete_episode"
    else:
        outcome = "outcome_unavailable"

    turns = trace_data.get("turns")
    turns = turns if isinstance(turns, list) else []
    replay_verified_half_moves = 0
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        for key in ("player_move", "opponent_reply"):
            move = turn.get(key)
            replay_verified_half_moves += int(
                isinstance(move, dict) and move.get("verified_from_rgb") is True
            )
    if replay_state_count is None:
        replay_state_count = verified_replay_snapshot_count(trace)
    diagnostics = [dict(item) for item in (replay_diagnostics or []) if isinstance(item, dict)]
    counts = {severity: sum(item.get("severity") == severity for item in diagnostics)
              for severity in ("INFO", "WARNING", "ERROR")}
    summary: dict[str, object] = {
        "schema_version": 1,
        "policy_id": metadata.get("policy_id", trace_data.get("move_selector")),
        "checkpoint_sha256": metadata.get("checkpoint_sha256"),
        "model_training_seed": metadata.get("model_training_seed"),
        "ale_seed": metadata.get("ale_seed", trace_data.get("seed")),
        "status": trace_data.get("status", "worker_failed" if worker_status != "completed" else "unknown"),
        "outcome": outcome,
        "runner_stop_category": category,
        "runner_stop_reason": terminal.get("runner_stop_reason") or trace_data.get("failure") or worker_error,
        "incomplete_final_move_count": terminal.get("incomplete_final_move_count"),
        "incomplete_final_move_category": terminal.get("incomplete_final_move_category"),
        "ale_terminated": terminal.get("ale_terminated", False),
        "ale_truncated": terminal.get("ale_truncated", False),
        "white_result": terminal.get("white_result_from_reward") if terminal.get("ale_terminated") is True else None,
        "ale_reward_total": terminal.get("ale_reward_total"),
        "player_moves_attempted": terminal.get("player_moves_attempted", 0),
        "verified_player_moves": terminal.get("verified_player_moves", 0),
        "verified_atari_replies": terminal.get("verified_atari_replies", 0),
        "last_verified_fen": terminal.get("last_verified_fen"),
        "worker_status": worker_status,
        "worker_error_type": worker_error_type,
        "worker_error": worker_error,
        "replay_snapshots_available": replay_state_count,
        "replay_verified_half_moves": replay_verified_half_moves,
        "replay_diagnostic_counts": counts,
        "replay_diagnostics": diagnostics,
    }
    return summary


def verify_auto_smoke(trace: object, verification: object, *, requested_player_moves: int) -> dict:
    """Validate the bounded smoke against the authoritative episode trace and GUI record.

    A normal worker return or a persisted trace is not an episode success.  The
    only successful automated smoke is the configured runner move-cap stop
    after every requested player move and corresponding Atari reply was RGB
    verified, with the GUI displaying the same pairs and passing its checks.
    """
    failures: list[dict[str, str]] = []
    runtime_failure = False

    def fail(code: str, message: str, *, runtime: bool = False) -> None:
        nonlocal runtime_failure
        failures.append({"code": code, "message": message})
        runtime_failure = runtime_failure or runtime

    if (not isinstance(requested_player_moves, int) or isinstance(requested_player_moves, bool)
            or requested_player_moves != 2):
        fail("invalid_requested_moves", "automated smoke contract requires exactly two player moves", runtime=True)
        requested_player_moves = 0
    if not isinstance(verification, dict):
        fail("invalid_verification_record", "GUI verification record is missing or malformed", runtime=True)
        verification = {}
    if not isinstance(trace, dict):
        fail("invalid_episode_trace", "episode trace is missing or malformed", runtime=True)
        trace = {}

    session = verification.get("session_state")
    if not isinstance(session, dict):
        fail("invalid_session_state", "GUI session lifecycle record is missing or malformed", runtime=True)
        session = {}
    worker_status = session.get("worker_status")
    trace_status = session.get("trace_status")
    if worker_status != "completed":
        fail("worker_not_completed", f"worker status was {worker_status!r}, expected 'completed'", runtime=True)
    if session.get("worker_error") is not None:
        fail("worker_error", f"worker error was reported: {session.get('worker_error')}", runtime=True)
    replay_diagnostics = session.get("replay_diagnostics")
    if isinstance(replay_diagnostics, list):
        for item in replay_diagnostics:
            if isinstance(item, dict) and item.get("severity") == "ERROR":
                fail("replay_artifact_inconsistent", str(item.get("code") or "replay metadata inconsistent"), runtime=True)
    if trace_status != "saved":
        fail("trace_not_saved", f"trace persistence status was {trace_status!r}, expected 'saved'", runtime=True)
    if verification.get("trace_path") != "trace.json":
        fail("trace_reference_invalid", "verification record does not reference the expected trace", runtime=True)
    if session.get("trace_path") != "trace.json":
        fail("session_trace_reference_invalid", "session lifecycle does not reference the persisted trace", runtime=True)
    if (not isinstance(verification.get("exit_code"), int)
            or isinstance(verification.get("exit_code"), bool)):
        fail("gui_exit_code_missing", "GUI lifecycle exit code is missing or malformed", runtime=True)
    if verification.get("window_created") is not True:
        fail("window_not_created", "live GUI window was not verified", runtime=True)
    if verification.get("resized_1100x680") is not True:
        fail("resize_failed", "required GUI resize was not verified", runtime=True)
    layout = verification.get("layout_check")
    if not isinstance(layout, dict) or layout.get("ok") is not True:
        fail("layout_failed", "required GUI layout check did not pass", runtime=True)
    replay = verification.get("replay_test")
    if (not isinstance(replay, dict) or replay.get("left_moved_backward") is not True
            or replay.get("right_moved_forward") is not True):
        fail("replay_failed", "replay backward and forward checks did not both pass", runtime=True)
    if verification.get("replay_available") is not True:
        fail("replay_unavailable", "verified replay states were not available", runtime=True)
    if verification.get("gui_checks_ok") is not True:
        fail("gui_smoke_failed", "GUI replay, resize, or layout checks did not pass", runtime=True)
    captured_states = verification.get("captured_verified_state_count")
    if (not isinstance(captured_states, int) or isinstance(captured_states, bool)
            or captured_states < 2):
        fail("insufficient_replay_states", f"GUI captured {captured_states!r} states; at least two are required for replay", runtime=True)

    terminal = trace.get("terminal")
    turns = trace.get("turns")
    episode_budget = trace.get("episode_budget")
    if not isinstance(terminal, dict):
        fail("terminal_missing", "authoritative trace terminal record is missing or malformed", runtime=True)
        terminal = {}
    if not isinstance(turns, list):
        fail("turns_missing", "authoritative trace turn list is missing or malformed", runtime=True)
        turns = []
    cap = episode_budget.get("max_player_moves") if isinstance(episode_budget, dict) else None
    if (not isinstance(cap, int) or isinstance(cap, bool) or cap != requested_player_moves):
        fail("trace_move_cap_mismatch", "trace episode budget does not record the requested two-player-move cap", runtime=True)

    def count(container: dict, key: str, label: str) -> int | None:
        value = container.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            fail(f"invalid_{key}", f"{label} must be a non-negative integer; got {value!r}", runtime=True)
            return None
        return value

    attempted = count(terminal, "player_moves_attempted", "attempted player moves")
    trace_players = count(terminal, "verified_player_moves", "trace verified player moves")
    trace_replies = count(terminal, "verified_atari_replies", "trace verified Atari replies")
    incomplete = count(terminal, "incomplete_final_move_count", "incomplete final move count")
    if "runner_stopped" not in terminal or not isinstance(terminal.get("runner_stopped"), bool):
        fail("runner_stop_missing", "terminal runner_stopped flag is missing or malformed", runtime=True)
    if "observed" not in terminal or not isinstance(terminal.get("observed"), bool):
        fail("terminal_observed_missing", "terminal observed flag is missing or malformed", runtime=True)
    if "ale_terminated" not in terminal or not isinstance(terminal.get("ale_terminated"), bool):
        fail("ale_termination_missing", "terminal ALE termination flag is missing or malformed", runtime=True)
    if "ale_truncated" not in terminal or not isinstance(terminal.get("ale_truncated"), bool):
        fail("ale_truncation_missing", "terminal ALE truncation flag is missing or malformed", runtime=True)
    if (not isinstance(terminal.get("terminated"), bool)
            or not isinstance(terminal.get("truncated"), bool)):
        fail("termination_aliases_missing", "terminal terminated/truncated fields are missing or malformed", runtime=True)
    category = terminal.get("runner_stop_category")
    reason = terminal.get("runner_stop_reason")
    episode_status = trace.get("status")
    if not isinstance(category, str) or not category:
        fail("terminal_category_missing", "terminal stop category is missing or malformed", runtime=True)

    turn_attempts = turn_players = turn_replies = complete_pairs = 0
    for index, turn in enumerate(turns):
        if not isinstance(turn, dict):
            fail("malformed_turn", f"trace turn {index + 1} is malformed", runtime=True)
            continue
        player = turn.get("player_move")
        reply = turn.get("opponent_reply")
        if not isinstance(player, dict) or not isinstance(reply, dict):
            fail("malformed_turn_moves", f"trace turn {index + 1} lacks player/reply records", runtime=True)
            continue
        if not isinstance(player.get("input_initiated"), bool):
            fail("malformed_player_attempt", f"trace turn {index + 1} lacks an input_initiated flag", runtime=True)
        turn_attempts += player.get("input_initiated") is True
        if not isinstance(player.get("verified_from_rgb"), bool) or not isinstance(reply.get("verified_from_rgb"), bool):
            fail("malformed_verification_flags", f"trace turn {index + 1} lacks Boolean RGB-verification flags", runtime=True)
        player_verified = player.get("verified_from_rgb") is True
        reply_verified = reply.get("verified_from_rgb") is True
        if player_verified and (not isinstance(player.get("uci"), str) or not player.get("uci")):
            fail("verified_player_move_missing_uci", f"verified player move in turn {index + 1} lacks UCI identity", runtime=True)
        if reply_verified and (not isinstance(reply.get("uci"), str) or not reply.get("uci")):
            fail("verified_reply_missing_uci", f"verified Atari reply in turn {index + 1} lacks UCI identity", runtime=True)
        turn_players += player_verified
        turn_replies += reply_verified
        complete_pairs += player_verified and reply_verified

    displayed_pairs = count(verification, "verified_atari_turns_displayed", "GUI displayed verified pairs")
    displayed_players = count(verification, "verified_player_moves_displayed", "GUI displayed player moves")
    displayed_replies = count(verification, "verified_atari_replies_displayed", "GUI displayed Atari replies")
    pending_actions = count(verification, "pending_player_actions", "GUI pending player actions")
    if trace_players is not None and turn_players != trace_players:
        fail("trace_player_count_mismatch", f"trace terminal reports {trace_players} verified player moves but turn records contain {turn_players}", runtime=True)
    if trace_replies is not None and turn_replies != trace_replies:
        fail("trace_reply_count_mismatch", f"trace terminal reports {trace_replies} verified replies but turn records contain {turn_replies}", runtime=True)
    if attempted is not None and turn_attempts != attempted:
        fail("trace_attempt_count_mismatch", f"trace terminal reports {attempted} player attempts but turn records contain {turn_attempts}", runtime=True)
    if trace_players != trace_replies:
        fail("unpaired_trace_moves", f"trace has {trace_players} verified player moves and {trace_replies} verified replies")
    if trace_players != requested_player_moves or trace_replies != requested_player_moves:
        fail("required_move_count_not_met", f"requested {requested_player_moves} player moves and replies; trace verifies {trace_players} player moves and {trace_replies} replies")
    if attempted != requested_player_moves:
        fail("attempt_count_mismatch", f"requested {requested_player_moves} player moves; trace records {attempted} attempts")
    if incomplete != 0:
        fail("pending_move", f"trace records {incomplete} incomplete final player moves")
    if len(turns) > requested_player_moves:
        fail("extra_trace_turns", f"trace contains {len(turns)} turns for a {requested_player_moves}-move smoke", runtime=True)
    if displayed_pairs != complete_pairs or displayed_players != turn_players or displayed_replies != turn_replies:
        fail("gui_trace_count_mismatch", f"GUI displays {displayed_players} player moves, {displayed_replies} replies, and {displayed_pairs} verified pairs; authoritative trace contains {turn_players}, {turn_replies}, and {complete_pairs}", runtime=True)
    if pending_actions != 0:
        fail("gui_pending_action", f"GUI still shows {pending_actions} unconfirmed player actions")

    # The bounded smoke must end at the configured runner cap.  ALE terminal,
    # truncation, controller failure, cancellation, and time/resource limits
    # remain truthful incomplete outcomes even if their worker and trace succeed.
    if episode_status != "runner_stopped":
        fail("unexpected_episode_status", f"episode status was {episode_status!r}, expected 'runner_stopped'")
    if category != "RUNNER_MAX_PLAYER_MOVES" or terminal.get("runner_stopped") is not True:
        fail("unexpected_stop_category", f"episode stop category was {category!r}, expected 'RUNNER_MAX_PLAYER_MOVES'")
    if not isinstance(reason, str) or not reason.strip():
        fail("stop_reason_missing", "authoritative runner stop reason is missing or malformed", runtime=True)
    elif reason != f"runner stopped after the configured {requested_player_moves} player-move limit":
        fail("stop_reason_mismatch", "authoritative stop reason does not identify the configured player-move cap")
    if terminal.get("observed") is True:
        fail("unexpected_terminal_observation", "ALE terminal state was observed before the configured runner stop")
    if terminal.get("terminated") is not terminal.get("ale_terminated"):
        fail("termination_field_mismatch", "terminated and ale_terminated fields disagree", runtime=True)
    if terminal.get("truncated") is not terminal.get("ale_truncated"):
        fail("truncation_field_mismatch", "truncated and ale_truncated fields disagree", runtime=True)
    if terminal.get("ale_terminated") is True:
        fail("ale_terminated_early", "ALE terminated before the configured bounded smoke stop")
    if terminal.get("ale_truncated") is True:
        fail("ale_truncated", "ALE truncated before the configured bounded smoke stop")
    gui_requested = verification.get("requested_player_moves")
    if (not isinstance(gui_requested, int) or isinstance(gui_requested, bool)
            or gui_requested != requested_player_moves):
        fail("requested_move_contract_mismatch", "GUI verification requested-move count does not match the CLI contract", runtime=True)
    if (session.get("episode_status") != verification.get("episode_status")
            or session.get("episode_terminal") != verification.get("episode_terminal")
            or session.get("verified_pairs_displayed") != displayed_pairs
            or session.get("verified_player_moves_displayed") != displayed_players
            or session.get("verified_atari_replies_displayed") != displayed_replies
            or session.get("required_player_moves") != requested_player_moves):
        fail("session_record_mismatch", "GUI session lifecycle disagrees with its top-level verification record", runtime=True)
    event_terminal = verification.get("episode_terminal")
    if not isinstance(event_terminal, dict):
        fail("gui_terminal_missing", "GUI did not record the episode terminal event", runtime=True)
    elif (event_terminal.get("runner_stop_category") != category
          or event_terminal.get("runner_stopped") != terminal.get("runner_stopped")
          or event_terminal.get("ale_terminated") != terminal.get("ale_terminated")
          or event_terminal.get("ale_truncated") != terminal.get("ale_truncated")
          or event_terminal.get("terminated") != terminal.get("terminated")
          or event_terminal.get("truncated") != terminal.get("truncated")
          or event_terminal.get("observed") != terminal.get("observed")
          or event_terminal.get("player_moves_attempted") != attempted
          or event_terminal.get("verified_player_moves") != trace_players
          or event_terminal.get("verified_atari_replies") != trace_replies
          or event_terminal.get("incomplete_final_move_count") != incomplete
          or event_terminal.get("runner_stop_reason") != reason
          or verification.get("episode_status") != episode_status):
        fail("gui_trace_terminal_mismatch", "GUI terminal event disagrees with the authoritative trace", runtime=True)

    verdict = "SMOKE_PASS" if not failures else ("SMOKE_RUNTIME_FAILURE" if runtime_failure else "SMOKE_INCOMPLETE")
    return {
        "verdict": verdict,
        "requested_player_moves": requested_player_moves,
        "verified_player_moves": trace_players,
        "verified_atari_replies": trace_replies,
        "episode_status": episode_status,
        "terminal_category": category,
        "stop_reason": reason,
        "worker_status": worker_status,
        "trace_status": trace_status,
        "replay_available": verification.get("replay_available"),
        "replay_test": replay if isinstance(replay, dict) else None,
        "layout_check": layout if isinstance(layout, dict) else None,
        "failures": failures,
    }


def allocate_session_artifact_dir(root: Path, policy: str, *, now=None, token_factory=None) -> Path:
    """Atomically allocate a unique, auditable session directory; never overwrite."""
    now = now or datetime.now(timezone.utc)
    token_factory = token_factory or (lambda: uuid.uuid4().hex[:10])
    root = Path(root)
    if any(parent.is_symlink() for parent in (root, *root.parents)):
        raise ValueError("refusing to allocate demo artifacts through a symlinked root")
    root.mkdir(parents=True, exist_ok=True)
    base = f"{now.strftime('%Y%m%dT%H%M%S.%fZ')}-{policy}"
    for collision in range(1000):
        token = token_factory()
        suffix = f"-{token}" if collision == 0 else f"-{token}-{collision:03d}"
        candidate = root / f"{base}{suffix}"
        try:
            candidate.mkdir(exist_ok=False)
            return candidate
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate a unique demo artifact directory after 1000 attempts")


def run_demo_worker(viewer, *, episode_runner, episode_kwargs: dict, trace_path: Path,
                    trace_writer=write, summary_path: Path | None = None,
                    summary_metadata: dict | None = None,
                    replay_artifact_dir: Path | None = None) -> None:
    """Execute one demo worker and always publish a terminal worker event."""
    worker_status = "failed"
    trace: object = None
    replay_state_count = 0
    failure_type: str | None = None
    failure_message: str | None = None
    try:
        trace = episode_runner(**episode_kwargs)
        replay_state_count = verified_replay_snapshot_count(trace)
        try:
            trace_writer(trace_path, trace)
        except Exception as exc:
            viewer.publish({"event": "trace_save_error", "error_type": type(exc).__name__,
                            "error": str(exc)})
            raise
        viewer.publish({"event": "trace_saved", "path": trace_path.name})
        diagnostics = (diagnose_replay_artifacts(trace, replay_artifact_dir)
                       if replay_artifact_dir is not None else [])
        summary = build_live_summary(
            trace, metadata=summary_metadata, replay_diagnostics=diagnostics,
            replay_state_count=replay_state_count,
        )
        if summary_path is not None:
            write(summary_path, summary)
            print("LIVE_SESSION_RESULT " + json.dumps(summary, sort_keys=True), flush=True)
        for item in diagnostics:
            turn_label = f" turn={item['turn']}" if "turn" in item else ""
            print(f"{item['severity']}: {item['code']}{turn_label}: {item['message']}",
                  file=sys.stderr if item["severity"] != "INFO" else sys.stdout, flush=True)
        viewer.publish({"event": "session_summary", "summary": summary})
        worker_status = "completed"
    except Exception as exc:
        import traceback
        failure_type = type(exc).__name__
        failure_message = str(exc)
        viewer.publish({"event": "worker_error", "error_type": type(exc).__name__,
            "error": str(exc), "traceback": traceback.format_exc()})
    finally:
        if worker_status != "completed" and summary_path is not None:
            summary = build_live_summary(
                trace, metadata=summary_metadata, worker_status="failed",
                worker_error_type=failure_type, worker_error=failure_message,
                replay_state_count=replay_state_count,
            )
            try:
                write(summary_path, summary)
                viewer.publish({"event": "session_summary", "summary": summary})
                print("LIVE_SESSION_RESULT " + json.dumps(summary, sort_keys=True), flush=True)
            except Exception as exc:
                viewer.publish({"event": "session_summary_error", "error_type": type(exc).__name__,
                                "error": str(exc)})
        viewer.publish({"event": "worker_finished", "status": worker_status,
            "reason": None if worker_status == "completed" else "episode or trace persistence did not complete",
            "replay_available": replay_state_count > 1})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", choices=("double-dqn", "m4-a"), default="m4-a")
    parser.add_argument("--checkpoint", help="Required Q-only snapshot for --policy double-dqn")
    parser.add_argument("--checkpoint-sha256")
    parser.add_argument("--seed", "--reset-seed", dest="reset_seed", type=int, default=20261103,
                        help="Atari emulator reset seed, independent of immutable model training seed")
    parser.add_argument("--max-player-moves", type=int, default=24)
    parser.add_argument("--max-seconds", type=float, default=900.0)
    parser.add_argument("--auto-smoke", action="store_true",
                        help="Run a bounded two-move live ALE smoke, test resize/replay, and close")
    parser.add_argument("--preflight-only", action="store_true",
                        help="Check readiness without resetting or stepping Atari")
    args = parser.parse_args(argv)
    if args.auto_smoke:
        args.max_player_moves = 2
        args.max_seconds = min(args.max_seconds, 180.0)
    if args.max_player_moves < 1 or args.max_seconds <= 0:
        parser.error("move and wall-clock bounds must be positive")
    from .preflight import run_demo_preflight
    report = run_demo_preflight(policy=args.policy, checkpoint=args.checkpoint,
        expected_sha256=args.checkpoint_sha256, reset_seed=args.reset_seed,
        output_root=ARTIFACTS / "live-demo")
    print(json.dumps(report, sort_keys=True), flush=True)
    if not report["ok"]:
        return 3
    if args.preflight_only:
        return 0

    import torch
    torch.set_num_threads(1)
    from videochess_rl.episode import run_episode
    from videochess_rl.environment import ALEConfig
    from .live import LiveDemoWindow, LiveEnvironment
    from .policies import load_demo_policy
    policy, identity = load_demo_policy(args.policy, checkpoint=args.checkpoint,
        expected_sha256=args.checkpoint_sha256, policy_rng_seed=args.reset_seed)
    artifact_dir = allocate_session_artifact_dir(ARTIFACTS / "live-demo", args.policy)
    run_limits = {
        "max_player_moves": args.max_player_moves,
        "max_wall_seconds": args.max_seconds,
        "runner_frame_cap": 150000,
        "runner_environment_step_cap": 150000,
        "ale_episode_frame_cap": next((item["observed"].get("ale_episode_frame_limit")
            for item in report["checks"] if item["name"] == "videochess_environment" and item["ok"]), None),
        "opponent_response_frame_cap": 30000,
        "artifact_byte_cap": 128 * 1024 * 1024,
        "ale_truncation_is_game_terminal": False,
    }

    def worker(viewer):
        def publish_frame(frame):
            viewer.publish({"event": "frame", "frame_number": frame.frame_number,
                            "rgb": frame.rgb})
        episode_kwargs = dict(config=ALEConfig.deterministic_dev(mode=4), seed=args.reset_seed,
                expected_rom_sha256=ROM_SHA256, decision_selector=policy,
                max_player_moves=args.max_player_moves, max_opponent_wait_frames=30000,
                max_episode_frames=150000, max_episode_env_steps=150000,
                max_episode_seconds=args.max_seconds, max_artifact_bytes=128 * 1024 * 1024,
                artifact_dir=str(artifact_dir / "frames"), stop_event=viewer.stop_event,
                progress_callback=viewer.publish,
                env_factory=lambda config: LiveEnvironment(config, frame_callback=publish_frame))
        run_demo_worker(viewer, episode_runner=run_episode, episode_kwargs=episode_kwargs,
                        trace_path=artifact_dir / "trace.json",
                        summary_path=artifact_dir / "live_summary.json",
                        replay_artifact_dir=artifact_dir / "frames",
                        summary_metadata={
                            "policy_id": identity.policy_id,
                            "checkpoint_sha256": identity.checkpoint_sha256,
                            "model_training_seed": identity.training_seed,
                            "ale_seed": args.reset_seed,
                        })

    try:
        window = LiveDemoWindow(policy_name=identity.policy_id, identity=identity,
            artifact_dir=artifact_dir, max_player_moves=args.max_player_moves,
            run_worker=worker, demo_seed=args.reset_seed, auto_smoke=args.auto_smoke,
            session_limits=run_limits)
    except Exception as exc:
        message = f"could not initialize the live Tk window: {type(exc).__name__}: {exc}"
        if args.auto_smoke:
            try:
                write(artifact_dir / "demo-verification.json", {
                    "smoke_verdict": "SMOKE_RUNTIME_FAILURE", "exit_code": 5,
                    "smoke_failures": [{"code": "gui_initialization_failed", "message": message}]})
            except OSError:
                pass
        print(message, file=sys.stderr)
        return 5
    exit_code = window.start()
    if args.auto_smoke:
        result_path = artifact_dir / "demo-verification.json"
        if not result_path.is_file():
            failure = {"smoke_verdict": "SMOKE_RUNTIME_FAILURE", "exit_code": 4,
                "smoke_failures": [{"code": "verification_record_missing",
                                    "message": "GUI verification record was not written"}]}
            try:
                write(result_path, failure)
            except OSError:
                pass
            print(json.dumps(failure, sort_keys=True), file=sys.stderr)
            return 4
        trace_path = artifact_dir / "trace.json"
        try:
            result = json.loads(result_path.read_text())
            trace = json.loads(trace_path.read_text()) if trace_path.is_file() else None
            verdict = verify_auto_smoke(trace, result, requested_player_moves=args.max_player_moves)
            if exit_code != 0 and verdict["verdict"] == "SMOKE_PASS":
                verdict["verdict"] = "SMOKE_RUNTIME_FAILURE"
                verdict["failures"].append({"code": "gui_exit_nonzero",
                    "message": f"GUI returned nonzero exit code {exit_code}"})
            result["authoritative_verification"] = verdict
            result["smoke_verdict"] = verdict["verdict"]
            result["smoke_failures"] = verdict["failures"]
            result["exit_code"] = 0 if verdict["verdict"] == "SMOKE_PASS" else (4 if verdict["verdict"] == "SMOKE_RUNTIME_FAILURE" else 2)
            write(result_path, result)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            verdict = {"verdict": "SMOKE_RUNTIME_FAILURE", "failures": [
                {"code": "verification_input_invalid", "message": f"could not validate smoke records: {type(exc).__name__}: {exc}"}]}
            try:
                write(result_path, verdict)
            except OSError:
                pass
            print(json.dumps(verdict, sort_keys=True), file=sys.stderr)
            return 4
        console_summary = {
            "policy": result.get("policy_name"),
            "checkpoint_sha256": result.get("checkpoint_sha256"),
            "verification_record": result_path.name,
            **verdict,
        }
        print(json.dumps(console_summary, sort_keys=True))
        return result["exit_code"]
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
