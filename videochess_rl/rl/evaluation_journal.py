"""Durable, append-only events for recoverable frozen policy evaluation."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Sequence

EVALUATION_EVENT_SCHEMA = "videochess-m5-evaluation-event/1.0"


class EvaluationJournalCorruption(ValueError):
    """Raised when a non-tail evaluation journal record fails integrity checks."""


def _canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


class EvaluationEventJournal:
    """Create one new journal attempt; existing evidence is never overwritten."""

    def __init__(self, path: str | Path, *, policy_id: str, attempt_id: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.policy_id = policy_id
        self.attempt_id = attempt_id
        self.sequence = 0
        self.previous = "0" * 64
        self._fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_APPEND, 0o600)
        self._closed = False
        parent_fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)

    def append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self._closed:
            raise RuntimeError("evaluation event journal is closed")
        if not isinstance(event_type, str) or not event_type:
            raise ValueError("evaluation event type must be nonempty")
        event = {**payload, "type": event_type, "policy_id": self.policy_id, "attempt_id": self.attempt_id}
        record = {"schema": EVALUATION_EVENT_SCHEMA, "sequence": self.sequence,
                  "previous": self.previous, "event": event}
        digest = hashlib.sha256(_canonical_bytes(record)).hexdigest()
        encoded = _canonical_bytes({**record, "chain_sha256": digest}) + b"\n"
        view = memoryview(encoded)
        while view:
            written = os.write(self._fd, view)
            if written <= 0:
                raise OSError("short write to evaluation event journal")
            view = view[written:]
        os.fsync(self._fd)
        self.sequence += 1
        self.previous = digest
        return {**record, "chain_sha256": digest}

    def close(self) -> None:
        if self._closed:
            return
        os.fsync(self._fd)
        os.close(self._fd)
        self._closed = True

    def __enter__(self) -> "EvaluationEventJournal":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


def read_evaluation_event_journal(path: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Verify a journal chain, retaining valid records before any torn tail.

    A malformed final line is reported as an incomplete diagnostic and left
    untouched. Corruption before the final line is fatal because later records
    cannot be trusted against the broken chain.
    """
    path = Path(path)
    events: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    previous = "0" * 64
    expected_sequence = 0
    size = path.stat().st_size
    with path.open("rb") as stream:
        while True:
            raw = stream.readline()
            if not raw:
                break
            line_number = expected_sequence + 1
            is_last = stream.tell() == size
            has_newline = raw.endswith(b"\n")
            try:
                record = json.loads(raw)
                if not isinstance(record, dict):
                    raise ValueError("record is not an object")
                if record.get("schema") != EVALUATION_EVENT_SCHEMA:
                    raise ValueError("unexpected evaluation journal schema")
                if record.get("sequence") != expected_sequence:
                    raise ValueError("evaluation event sequence mismatch")
                if record.get("previous") != previous:
                    raise ValueError("evaluation event hash-chain predecessor mismatch")
                event = record.get("event")
                if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                    raise ValueError("evaluation event payload is malformed")
                payload = {key: record[key] for key in ("schema", "sequence", "previous", "event")}
                digest = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
                if record.get("chain_sha256") != digest:
                    raise ValueError("evaluation event digest mismatch")
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError, ValueError) as exc:
                diagnostic = {"path": str(path), "line": line_number,
                              "status": "malformed_final_record" if is_last else "corrupt_record",
                              "message": str(exc)}
                if is_last:
                    diagnostics.append(diagnostic)
                    break
                raise EvaluationJournalCorruption(f"{path}: {diagnostic}") from exc
            if not has_newline and is_last:
                diagnostics.append({"path": str(path), "line": line_number,
                                    "status": "valid_final_record_without_newline"})
            events.append(event)
            previous = digest
            expected_sequence += 1
    return events, diagnostics


def recover_policy_attempt_rows(policy_root: str | Path, policy_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Read legacy completed arrays and journaled outcomes/incomplete attempts."""
    root = Path(policy_root)
    rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    if not root.exists():
        return rows, diagnostics

    for path in sorted(root.glob("rows-attempt-*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
                raise ValueError("legacy evaluation rows must be a JSON array of objects")
            rows.extend(value)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            diagnostics.append({"path": str(path), "status": "unreadable_legacy_rows", "message": str(exc)})

    for path in sorted(root.glob("events-attempt-*.jsonl")):
        events, journal_diagnostics = read_evaluation_event_journal(path)
        diagnostics.extend(journal_diagnostics)
        open_scenarios: dict[str, dict[str, Any]] = {}
        journal_attempt_id: str | None = None
        for event in events:
            if event.get("policy_id") != policy_id:
                raise EvaluationJournalCorruption(f"{path}: event policy identity mismatch")
            event_attempt_id = event.get("attempt_id")
            if not isinstance(event_attempt_id, str) or not event_attempt_id:
                raise EvaluationJournalCorruption(f"{path}: event attempt identity is missing")
            if journal_attempt_id is None:
                journal_attempt_id = event_attempt_id
            elif event_attempt_id != journal_attempt_id:
                raise EvaluationJournalCorruption(f"{path}: attempt identity changed within one journal")
            event_type = event.get("type")
            scenario_id = event.get("scenario_attempt_id")
            if event_type == "scenario_started":
                if not isinstance(scenario_id, str) or scenario_id in open_scenarios:
                    raise EvaluationJournalCorruption(f"{path}: missing or duplicate scenario attempt identity")
                open_scenarios[scenario_id] = {**event}
            elif event_type == "scenario_progress":
                if scenario_id in open_scenarios:
                    open_scenarios[scenario_id]["latest_progress"] = event
            elif event_type in {"scenario_completed", "scenario_incomplete", "scenario_error"}:
                row = event.get("row")
                if isinstance(row, dict):
                    if row.get("policy_id") != policy_id:
                        raise EvaluationJournalCorruption(f"{path}: outcome row policy identity mismatch")
                    if row.get("scenario_attempt_id") != scenario_id:
                        raise EvaluationJournalCorruption(f"{path}: outcome row scenario identity mismatch")
                    rows.append(row)
                if isinstance(scenario_id, str):
                    open_scenarios.pop(scenario_id, None)
        for scenario_id, start in open_scenarios.items():
            latest = start.get("latest_progress", {})
            rows.append({
                "policy_id": policy_id,
                "evaluation_seed": start.get("evaluation_seed"),
                "opponent_id": start.get("opponent_id"),
                "agent_color": start.get("agent_color"),
                "scenario_seed": start.get("scenario_seed"),
                "scenario_attempt_id": scenario_id,
                "evaluation_attempt_id": start.get("attempt_id"),
                "status": "interrupted_scenario_attempt",
                "truncated": None,
                "agent_reward": None,
                "result": None,
                "agent_decisions": latest.get("agent_decisions", 0),
                "plies": latest.get("plies", 0),
                "history_uci": latest.get("history_uci", start.get("history_uci", [])),
                "metric_source": "python_chess_m2_simulator",
            })
    return rows, diagnostics
