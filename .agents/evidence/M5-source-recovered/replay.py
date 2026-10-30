"""Bounded semantic replay with deterministic sampling and a verifiable journal."""

from __future__ import annotations

import hashlib
import json
import os
import random
from collections import deque
from pathlib import Path
from typing import Any

from .transition import TRANSITION_SCHEMA, Transition

REPLAY_SCHEMA = "videochess-ddqn-replay/1.0"
JOURNAL_SCHEMA = "videochess-ddqn-replay-journal/1.0"


class ReplayBuffer:
    def __init__(self, capacity: int, *, seed: int) -> None:
        if type(capacity) is not int or capacity < 1 or type(seed) is not int or seed < 0:
            raise ValueError("capacity and seed must be positive/nonnegative integers")
        self.capacity = capacity
        self.rng = random.Random(seed)
        self._rows: deque[Transition] = deque(maxlen=capacity)
        self._ids: set[str] = set()
        self.inserted_count = 0
        self.evicted_count = 0

    def __len__(self) -> int:
        return len(self._rows)

    @property
    def transitions(self) -> tuple[Transition,...]:
        return tuple(self._rows)

    def insert(self, row: Transition) -> None:
        row.validate()
        if row.schema != TRANSITION_SCHEMA:
            raise ValueError("unsupported transition schema")
        if row.transition_id in self._ids:
            raise ValueError("duplicate transition identity")
        if len(self._rows) == self.capacity:
            old = self._rows[0]
            self._ids.remove(old.transition_id)
            self.evicted_count += 1
        self._rows.append(row)
        self._ids.add(row.transition_id)
        self.inserted_count += 1

    def sample(self, batch_size: int) -> tuple[Transition, ...]:
        if type(batch_size) is not int or not 1 <= batch_size <= len(self._rows):
            raise ValueError("sample size must be within the current replay length")
        return tuple(self.rng.sample(tuple(self._rows), batch_size))

    def state_dict(self) -> dict[str, Any]:
        return {
            "schema": REPLAY_SCHEMA, "transition_schema": TRANSITION_SCHEMA,
            "capacity": self.capacity, "rows": [row.to_json() for row in self._rows],
            "rng_state": self.rng.getstate(), "inserted_count": self.inserted_count,
            "evicted_count": self.evicted_count,
        }

    @classmethod
    def from_state_dict(cls, state: dict[str, Any]) -> "ReplayBuffer":
        if state.get("schema") != REPLAY_SCHEMA or state.get("transition_schema") != TRANSITION_SCHEMA:
            raise ValueError("unsupported replay/checkpoint schema")
        rows = state.get("rows")
        if not isinstance(rows, list) or len(rows) > state.get("capacity", -1):
            raise ValueError("invalid replay row collection")
        buffer = cls(int(state["capacity"]), seed=0)
        for item in rows:
            buffer.insert(Transition.from_json(item))
        if len(buffer._ids) != len(rows):
            raise ValueError("duplicate transitions in replay snapshot")
        buffer.inserted_count = int(state["inserted_count"])
        buffer.evicted_count = int(state["evicted_count"])
        buffer.rng.setstate(_nested_tuple(state["rng_state"]))
        if buffer.inserted_count < len(rows) or buffer.evicted_count != buffer.inserted_count - len(rows):
            raise ValueError("replay counters disagree with retained/evicted rows")
        return buffer


def _nested_tuple(value: Any) -> Any:
    return tuple(_nested_tuple(x) for x in value) if isinstance(value, list) else value


class ReplayJournal:
    """Append-only JSONL hash chain; checkpoints pin a committed prefix."""

    def __init__(self, path: str | Path, *, verify_existing: bool = True) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            if verify_existing: self.verify()
            with self.path.open("rb") as stream:
                stream.seek(max(0, self.path.stat().st_size - 8192))
                tail = stream.read().splitlines()
            self.chain_sha256 = json.loads(tail[-1])["chain_sha256"] if tail else "0" * 64
            with self.path.open("rb") as stream:
                self.record_count = sum(1 for _ in stream)
        else:
            self.path.touch()
            self.chain_sha256 = "0" * 64
            self.record_count = 0

    def append(self, row: Transition) -> dict[str, Any]:
        row.validate()
        previous = self.chain_sha256
        payload = {"schema": JOURNAL_SCHEMA, "previous": previous, "transition": row.to_json()}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        record = dict(payload, chain_sha256=hashlib.sha256(canonical.encode()).hexdigest())
        encoded = (json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
        with self.path.open("ab") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        self.record_count += 1
        self.chain_sha256 = record["chain_sha256"]
        return {"record_count": self.record_count, "chain_sha256": self.chain_sha256, "file_bytes": self.path.stat().st_size}

    def verify(self, *, record_count: int | None = None, chain_sha256: str | None = None) -> tuple[Transition, ...]:
        rows: list[Transition] = []
        previous = "0" * 64
        raw_lines = self.path.read_bytes().splitlines()
        if record_count is not None and not 0 <= record_count <= len(raw_lines):
            raise ValueError("journal prefix count exceeds available records")
        stop = len(raw_lines) if record_count is None else record_count
        for index, raw in enumerate(raw_lines[:stop]):
            record = json.loads(raw)
            if record.get("schema") != JOURNAL_SCHEMA or record.get("previous") != previous:
                raise ValueError(f"replay journal chain mismatch at record {index}")
            payload = {key: record[key] for key in ("schema", "previous", "transition")}
            expected = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
            if record.get("chain_sha256") != expected:
                raise ValueError(f"replay journal digest mismatch at record {index}")
            row = Transition.from_json(record["transition"])
            rows.append(row)
            previous = expected
        if chain_sha256 is not None and previous != chain_sha256:
            raise ValueError("replay journal checkpoint head mismatch")
        if record_count is None and stop != len(raw_lines):
            raise ValueError("replay journal contains an incomplete trailing record")
        return tuple(rows)
