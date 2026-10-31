"""Hash-chained M6 attempt ledger, artifact manifest, and raw-trace summaries."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Iterator


LEDGER_SCHEMA = "videochess-m6-attempt-ledger/1.0"
TRACE_SCHEMA = "videochess-m6-episode-trace/1.0"
MANIFEST_SCHEMA = "videochess-m6-artifact-manifest/1.0"
GENESIS = "0" * 64


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json_atomic(path: str | Path, value: Any, *, refuse_existing: bool = True) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() or (refuse_existing and target.exists()):
        raise FileExistsError(f"refusing to overwrite M6 evidence artifact: {target}")
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode("utf-8") + b"\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if target.is_symlink() or (refuse_existing and target.exists()):
            raise FileExistsError(f"refusing to overwrite M6 evidence artifact: {target}")
        os.replace(temporary, target)
        directory_fd = os.open(target.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return sha256_file(target)


class HashChainLedger:
    """Append-only JSONL ledger; each event is durable before the next action."""

    def __init__(self, path: str | Path, *, run_id: str, create: bool = True) -> None:
        self.path = Path(path)
        self.run_id = run_id
        if self.path.is_symlink():
            raise ValueError("M6 ledger path must not be a symlink")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if create:
            if self.path.exists():
                raise FileExistsError(f"M6 run ID already has a ledger: {self.path}")
            self.path.touch(mode=0o600, exist_ok=False)
            self._seq = 0
            self._previous = GENESIS
        else:
            self._seq, self._previous = verify_hash_chain_head(self.path, expected_run_id=run_id)

    def append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not event_type or not isinstance(payload, dict):
            raise ValueError("ledger event type and object payload are required")
        self._seq += 1
        core = {
            "schema": LEDGER_SCHEMA,
            "run_id": self.run_id,
            "sequence": self._seq,
            "previous_event_sha256": self._previous,
            "event_type": event_type,
            "payload": payload,
        }
        digest = hashlib.sha256(self._previous.encode("ascii") + canonical_json_bytes(core)).hexdigest()
        record = {**core, "event_sha256": digest}
        line = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
        with self.path.open("ab") as stream:
            stream.write(line.encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        self._previous = digest
        return record


def iter_verified_hash_chain(
    path: str | Path,
    *,
    expected_run_id: str | None = None,
) -> Iterator[dict[str, Any]]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ValueError("M6 ledger is missing or unsafe")
    previous = GENESIS
    with target.open("rb") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.endswith(b"\n"):
                raise ValueError("M6 ledger has a partial final record")
            line = line[:-1]
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ValueError(f"invalid M6 ledger JSON at line {line_number}") from exc
            if not isinstance(record, dict) or record.get("schema") != LEDGER_SCHEMA:
                raise ValueError(f"unsupported M6 ledger record at line {line_number}")
            if expected_run_id is not None and record.get("run_id") != expected_run_id:
                raise ValueError(f"M6 ledger run ID mismatch at line {line_number}")
            if record.get("sequence") != line_number or record.get("previous_event_sha256") != previous:
                raise ValueError(f"M6 ledger sequence/hash predecessor mismatch at line {line_number}")
            core = {key: record[key] for key in (
                "schema", "run_id", "sequence", "previous_event_sha256", "event_type", "payload"
            )}
            digest = hashlib.sha256(previous.encode("ascii") + canonical_json_bytes(core)).hexdigest()
            if record.get("event_sha256") != digest:
                raise ValueError(f"M6 ledger event hash mismatch at line {line_number}")
            if not isinstance(record.get("payload"), dict):
                raise ValueError(f"M6 ledger payload is malformed at line {line_number}")
            previous = digest
            yield record


def verify_hash_chain_head(path: str | Path, *, expected_run_id: str | None = None) -> tuple[int, str]:
    sequence = 0
    head = GENESIS
    for event in iter_verified_hash_chain(path, expected_run_id=expected_run_id):
        sequence = int(event["sequence"])
        head = event["event_sha256"]
    return sequence, head


def verify_hash_chain(path: str | Path, *, expected_run_id: str | None = None) -> list[dict[str, Any]]:
    """Compatibility wrapper for tests/tools that explicitly need all records."""
    return list(iter_verified_hash_chain(path, expected_run_id=expected_run_id))


def _trace_event_rows(trace: dict[str, Any]) -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = [("reset", trace.get("reset")), ("initial_position", trace.get("initial_position"))]
    for turn in trace.get("turns", []):
        rows.append(("decision_input", turn.get("decision_input")))
        rows.append(("policy_decision", turn.get("policy_decision")))
        for phase in turn.get("input_phases", []):
            rows.append(("controller_phase", phase))
        for evidence in turn.get("evidence_windows", []):
            rows.append(("rgb_evidence_window", evidence))
        rows.append(("player_move", turn.get("player_move")))
        rows.append(("atari_reply", turn.get("opponent_reply")))
    rows.append(("terminal", trace.get("terminal")))
    rows.append(("terminal_observation", trace.get("terminal_observation")))
    return rows


def seal_episode_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """Attach a chained event stream and a digest of the complete trace payload."""
    sealed = dict(trace)
    sealed.pop("event_hash_chain", None)
    full_sha = hashlib.sha256(canonical_json_bytes(sealed)).hexdigest()
    events = _trace_event_rows(sealed)
    events.append(("complete_trace_payload_sha256", {"sha256": full_sha}))
    previous = GENESIS
    records = []
    for sequence, (event_type, payload) in enumerate(events, 1):
        core = {
            "sequence": sequence,
            "previous_event_sha256": previous,
            "event_type": event_type,
            "payload": payload,
        }
        digest = hashlib.sha256(previous.encode("ascii") + canonical_json_bytes(core)).hexdigest()
        records.append({**core, "event_sha256": digest})
        previous = digest
    sealed["event_hash_chain"] = {
        "schema": "videochess-m6-trace-event-chain/1.0",
        "event_count": len(records),
        "payload_sha256": full_sha,
        "head_sha256": previous,
        "events": records,
    }
    return sealed


def verify_episode_trace(trace: dict[str, Any]) -> dict[str, Any]:
    chain = trace.get("event_hash_chain")
    if not isinstance(chain, dict) or chain.get("schema") != "videochess-m6-trace-event-chain/1.0":
        raise ValueError("M6 trace event hash chain is missing or unsupported")
    payload = {key: value for key, value in trace.items() if key != "event_hash_chain"}
    full_sha = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    if full_sha != chain.get("payload_sha256"):
        raise ValueError("M6 trace payload hash differs from its event chain")
    events = _trace_event_rows(payload)
    events.append(("complete_trace_payload_sha256", {"sha256": full_sha}))
    previous = GENESIS
    expected_records = []
    for sequence, (event_type, event_payload) in enumerate(events, 1):
        core = {
            "sequence": sequence,
            "previous_event_sha256": previous,
            "event_type": event_type,
            "payload": event_payload,
        }
        digest = hashlib.sha256(previous.encode("ascii") + canonical_json_bytes(core)).hexdigest()
        expected_records.append({**core, "event_sha256": digest})
        previous = digest
    if chain.get("event_count") != len(expected_records) or chain.get("head_sha256") != previous:
        raise ValueError("M6 trace event-chain head or count differs")
    if chain.get("events") != expected_records:
        raise ValueError("M6 trace event-chain records are corrupt or tampered")
    return chain


def build_artifact_manifest(root: str | Path, *, exclude: Iterable[str] = ()) -> dict[str, Any]:
    directory = Path(root)
    excluded = set(exclude) | {"artifact-manifest.json"}
    files = []
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink in M6 artifact tree: {path.relative_to(directory)}")
        if not path.is_file() or path.name in excluded or path.name.endswith(".tmp"):
            continue
        files.append({
            "path": path.relative_to(directory).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return {"schema": MANIFEST_SCHEMA, "files": files, "total_bytes": sum(row["size_bytes"] for row in files)}


def verify_artifact_manifest(root: str | Path, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    directory = Path(root)
    manifest_path = directory / "artifact-manifest.json"
    if manifest is None:
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise ValueError("M6 artifact manifest is missing or unsafe")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != MANIFEST_SCHEMA or not isinstance(manifest.get("files"), list):
        raise ValueError("unsupported M6 artifact manifest")
    actual = build_artifact_manifest(directory)
    if actual != manifest:
        raise ValueError("M6 artifact tree does not match its manifest")
    return manifest


def classify_attempt(trace: dict[str, Any]) -> str:
    terminal = trace.get("terminal", {})
    if terminal.get("ale_terminated") is True and terminal.get("ale_truncated") is not True:
        reward = terminal.get("ale_reward_total")
        finite_reward = False
        if isinstance(reward, (int, float)) and not isinstance(reward, bool):
            try:
                finite_reward = math.isfinite(float(reward))
            except (OverflowError, ValueError):
                finite_reward = False
        if finite_reward:
            if reward > 0:
                return "win"
            if reward < 0:
                return "loss"
        # The pinned VideoChess wrapper assigns +/-1 to checkmate and zero
        # while ongoing; a terminal zero has no supported W/D/L interpretation.
        return "terminal_unknown"
    if terminal.get("ale_truncated") is True:
        return "ale_truncated"
    category = terminal.get("runner_stop_category")
    if category in {"RUNNER_MAX_ALE_FRAMES", "RUNNER_MAX_ENV_STEPS", "RUNNER_MAX_WALL_CLOCK", "RUNNER_MAX_PLAYER_MOVES", "RUNNER_ARTIFACT_LIMIT", "RUNNER_RESOURCE_LIMIT"}:
        return "runner_truncated"
    if terminal.get("runner_stopped"):
        return "incomplete"
    return "incomplete"


def wilson_interval(successes: int, trials: int, *, z: float = 1.959963984540054) -> list[float] | None:
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("Wilson interval requires 0 <= successes <= trials")
    if trials == 0:
        return None
    p = successes / trials
    z2 = z * z
    denominator = 1.0 + z2 / trials
    center = (p + z2 / (2.0 * trials)) / denominator
    half = z * math.sqrt(p * (1.0 - p) / trials + z2 / (4.0 * trials * trials)) / denominator
    return [max(0.0, center - half), min(1.0, center + half)]


def summarize_attempts(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [row.get("attempt_id") for row in attempts]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate M6 attempt IDs cannot be summarized")
    counts = {key: 0 for key in ("win", "draw", "loss", "terminal_unknown", "ale_truncated", "runner_truncated", "incomplete")}
    for row in attempts:
        outcome = row.get("outcome")
        if outcome not in counts:
            raise ValueError(f"unsupported M6 outcome classification: {outcome!r}")
        counts[outcome] += 1
    # "Completed" here means ALE terminated with a supported W/D/L result;
    # terminal-unknown games are counted separately as ALE-terminated games.
    completed = counts["win"] + counts["draw"] + counts["loss"]
    ale_terminated = completed + counts["terminal_unknown"]
    known_attempted = [row.get("player_moves_attempted", 0) for row in attempts if row.get("player_moves_attempted", 0) is not None]
    known_verified = [row.get("rgb_verified_player_moves", 0) for row in attempts if row.get("rgb_verified_player_moves", 0) is not None]
    attempted_moves = sum(int(value) for value in known_attempted)
    verified_moves = sum(int(value) for value in known_verified)
    if attempted_moves < 0 or verified_moves < 0 or verified_moves > attempted_moves:
        raise ValueError("move accounting requires 0 <= verified moves <= attempted moves")
    known_desyncs = [row.get("desynchronization_count", 0) for row in attempts if row.get("desynchronization_count", 0) is not None]
    desyncs = sum(int(value) for value in known_desyncs)
    if desyncs < 0:
        raise ValueError("desynchronization count cannot be negative")
    known_cursor_displacements = [
        row.get("unexpected_cursor_displacements", 0)
        for row in attempts if row.get("unexpected_cursor_displacements", 0) is not None
    ]
    cursor_displacements = sum(int(value) for value in known_cursor_displacements)
    if cursor_displacements < 0:
        raise ValueError("unexpected cursor displacement count cannot be negative")
    censor_categories = (
        "frame_cap", "wall_clock_cap", "artifact_cap", "ale_terminal", "ale_truncation",
        "source_selection_uncertainty", "target_navigation_uncertainty",
        "target_confirmation_uncertainty", "opponent_response_timeout",
        "board_desynchronization", "other_interrupted_or_unknown",
    )
    censor_counts = {category: 0 for category in censor_categories}
    pending_known = pending_unknown = 0
    for row in attempts:
        attempted = row.get("player_moves_attempted")
        verified = row.get("rgb_verified_player_moves")
        pending = row.get("incomplete_final_move_count")
        if pending is None and attempted is not None and verified is not None:
            pending = int(attempted) - int(verified)
        if pending is None:
            pending_unknown += 1
            continue
        if isinstance(pending, bool) or not isinstance(pending, int) or pending < 0:
            raise ValueError("incomplete final move count must be a nonnegative integer or unknown")
        if attempted is not None and verified is not None and pending != int(attempted) - int(verified):
            raise ValueError("incomplete final move count disagrees with the attempted/verified denominators")
        pending_known += pending
        category = row.get("incomplete_final_move_category")
        if pending == 0:
            if category is not None:
                raise ValueError("a completed final move cannot have an incomplete-move category")
        elif category in censor_counts:
            censor_counts[category] += pending
        else:
            censor_counts["other_interrupted_or_unknown"] += pending
    cursor_metric_names = (
        "unexpected_displacements_corrected", "unexpected_displacements_unresolved",
        "repeated_movement_without_progress", "ambiguous_or_unlocated_observations",
        "stable_board_disagreements",
    )
    cursor_totals: dict[str, int | None] = {}
    cursor_unknown_attempts: dict[str, int] = {}
    for metric in cursor_metric_names:
        values = [
            row.get("cursor_diagnostics", {}).get(metric)
            if isinstance(row.get("cursor_diagnostics"), dict) else None
            for row in attempts
        ]
        known = [value for value in values if isinstance(value, int) and not isinstance(value, bool)]
        cursor_totals[metric] = sum(known) if known else None
        cursor_unknown_attempts[metric] = sum(value is None for value in values)
    known_replies = [row.get("verified_atari_replies", 0) for row in attempts if row.get("verified_atari_replies", 0) is not None]
    known_frames = [row.get("ale_frames", 0) for row in attempts if row.get("ale_frames", 0) is not None]
    known_post_reset_frames = [
        row.get("post_reset_action_frames")
        for row in attempts if row.get("post_reset_action_frames") is not None
    ]
    known_steps = [row.get("environment_steps", 0) for row in attempts if row.get("environment_steps", 0) is not None]
    move_rate = verified_moves / attempted_moves if attempted_moves else None
    match_score = (counts["win"] + 0.5 * counts["draw"]) / completed if completed else None
    total_attempted = len(attempts)
    outcome_incomplete = total_attempted - ale_terminated
    return {
        "attempted_games": total_attempted,
        "completed_games": completed,
        "ale_terminated_games": ale_terminated,
        **counts,
        "incomplete_games": outcome_incomplete,
        "incomplete_fraction": outcome_incomplete / total_attempted if total_attempted else None,
        "match_score": match_score,
        "match_score_denominator": completed,
        "attempted_player_moves": attempted_moves,
        "attempts_with_unknown_move_accounting": sum(
            1 for row in attempts if row.get("player_moves_attempted", 0) is None
        ),
        "rgb_verified_player_moves": verified_moves,
        "move_success_rate": move_rate,
        "move_success_wilson_95": wilson_interval(verified_moves, attempted_moves),
        "move_success_interval_note": "Wilson interval treats moves as binomial trials; within-game dependence means this interval alone is not an independent-reliability guarantee.",
        "incomplete_final_moves": pending_known,
        "attempts_with_unknown_incomplete_move_accounting": pending_unknown,
        "incomplete_final_moves_by_category": censor_counts,
        "administrative_budget_censored_final_moves": sum(
            censor_counts[category] for category in ("frame_cap", "wall_clock_cap", "artifact_cap")
        ),
        "controller_uncertainty_censored_final_moves": sum(
            censor_counts[category] for category in (
                "source_selection_uncertainty", "target_navigation_uncertainty",
                "target_confirmation_uncertainty", "board_desynchronization",
            )
        ),
        "desynchronization_count": desyncs,
        "attempts_with_unknown_desynchronization_accounting": sum(
            1 for row in attempts if row.get("desynchronization_count", 0) is None
        ),
        "desynchronization_rate_per_attempted_move": desyncs / attempted_moves if attempted_moves else None,
        "unexpected_cursor_displacements": cursor_displacements,
        "cursor_diagnostics": cursor_totals,
        "cursor_diagnostic_unknown_attempts": cursor_unknown_attempts,
        "attempts_with_unknown_cursor_displacement_accounting": sum(
            1 for row in attempts if row.get("unexpected_cursor_displacements", 0) is None
        ),
        "verified_atari_replies": sum(int(value) for value in known_replies),
        "attempts_with_unknown_reply_accounting": sum(1 for row in attempts if row.get("verified_atari_replies", 0) is None),
        "ale_frames": sum(int(value) for value in known_frames),
        "attempts_with_unknown_ale_frames": sum(1 for row in attempts if row.get("ale_frames", 0) is None),
        "post_reset_action_frames": sum(int(value) for value in known_post_reset_frames),
        "attempts_with_unknown_post_reset_action_frames": sum(
            1 for row in attempts if row.get("post_reset_action_frames") is None
        ),
        "environment_steps": sum(int(value) for value in known_steps),
        "attempts_with_unknown_environment_steps": sum(1 for row in attempts if row.get("environment_steps", 0) is None),
        "wall_seconds": sum(float(row.get("wall_seconds", 0.0)) for row in attempts if row.get("wall_seconds", 0.0) is not None),
        "attempts_with_unknown_wall_seconds": sum(1 for row in attempts if row.get("wall_seconds") is None),
        "peak_rss_bytes_max": max((int(row.get("peak_rss_bytes", 0)) for row in attempts if row.get("peak_rss_bytes") is not None), default=0),
        "attempts_with_unknown_peak_rss": sum(1 for row in attempts if row.get("peak_rss_bytes") is None),
        "retries": sum(int(row.get("retries", 0)) for row in attempts if row.get("retries") is not None),
        "resource_limit_stops": sum(
            1 for row in attempts
            if str(row.get("terminal_or_stop_reason", row.get("runner_stop_category", ""))).startswith(
                ("RUNNER_MAX_", "RUNNER_ARTIFACT_LIMIT", "RUNNER_RESOURCE_LIMIT", "RESOURCE_LIMIT")
            )
        ),
        "stop_reasons": {
            reason: sum(1 for row in attempts if row.get("terminal_or_stop_reason", row.get("runner_stop_category")) == reason)
            for reason in sorted({
                str(row.get("terminal_or_stop_reason", row.get("runner_stop_category")))
                for row in attempts
                if row.get("terminal_or_stop_reason", row.get("runner_stop_category")) is not None
            })
        },
    }
