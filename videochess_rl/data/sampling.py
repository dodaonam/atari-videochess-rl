"""File-order-independent game and position sampling."""

from __future__ import annotations

import heapq
from collections import Counter
from dataclasses import dataclass
from typing import Any

import chess

from .contracts import (
    board_position_signature, canonical_fen, candidate_identity, digest,
    game_sample_key, ply_sample_key, replay_history_identity, sample_identity,
    sampling_run_identity,
)


@dataclass
class Group:
    normalized_game_sha256: str
    result: str
    record: dict[str, Any]
    source_game_ids: set[str]
    source_refs: set[str]
    conflict: bool = False


def make_source_game_id(
    parsed: dict[str, Any], *, source_id: str, archive_sha256: str,
    member_name: str, occurrence: int,
) -> str:
    from .contracts import fallback_game_identity

    if parsed.get("source_game_id"):
        return parsed["source_game_id"]
    return fallback_game_identity(
        source_id, archive_sha256, member_name,
        parsed["normalized_game_sha256"], occurrence,
    )


class BottomKGroups:
    """Audit every group, then select the globally lowest-ranked eligible groups.

    Production callers use two passes: :meth:`observe` retains compact
    normalized-result/source-reference metadata for the bounded source; after
    :meth:`begin_selection`, :meth:`select` retains full game records only in
    the bottom-k reservoir. A late conflict therefore cannot leave a vacancy
    or allow a conflicted, previously evicted group back into the release.
    """

    def __init__(self, *, seed: int, max_games: int, source_id: str,
                 archive_sha256: str, member_name: str):
        if max_games < 1:
            raise ValueError("max_games must be positive")
        self.seed = seed
        self.max_games = max_games
        self.source_id = source_id
        self.archive_sha256 = archive_sha256
        self.member_name = member_name
        self.groups: dict[str, Group] = {}
        self.heap: list[tuple[int, bytes, str]] = []
        self.normalized_results: dict[str, str] = {}
        self.normalized_observations: Counter[str] = Counter()
        self.normalized_duplicate_observations = 0
        self.normalized_duplicate_groups = 0
        self.source_ref_seen: set[str] = set()
        self.source_ref_to_normalized: dict[str, str] = {}
        self.conflicting_source_refs: set[str] = set()
        self.source_level_duplicates = 0
        self.conflicting_groups: set[str] = set()
        self.selection_occurrences: Counter[str] = Counter()
        self._selection_started = False

    def _rank(self, normalized: str) -> int:
        return int(game_sample_key(self.seed, normalized), 16)

    def _heap_entry(self, normalized: str) -> tuple[int, bytes, str]:
        # The heap root is the worst retained key: highest rank, then
        # lexicographically highest identity. Invert the secondary key so a
        # standard min-heap preserves the documented (rank, identity) order
        # even for the vanishingly rare SHA-256 rank collision.
        reverse_identity = bytes(255 - value for value in normalized.encode("ascii"))
        return (-self._rank(normalized), reverse_identity, normalized)

    def _trim_stale(self) -> None:
        while self.heap and self.heap[0][2] not in self.groups:
            heapq.heappop(self.heap)
        if len(self.heap) > max(16, 2 * self.max_games):
            self.heap = [self._heap_entry(key) for key in self.groups]
            heapq.heapify(self.heap)

    def observe(self, record: dict[str, Any]) -> None:
        """Add one accepted source observation to the compact full-source audit."""
        normalized = record["normalized_game_sha256"]
        result = record["pgn_result"]
        prior_result = self.normalized_results.setdefault(normalized, result)
        self.normalized_observations[normalized] += 1
        observation_count = self.normalized_observations[normalized]
        if observation_count > 1:
            self.normalized_duplicate_observations += 1
        if observation_count == 2:
            self.normalized_duplicate_groups += 1
        if prior_result != result:
            self.conflicting_groups.add(normalized)
        ref = record.get("source_game_ref_sha256")
        if ref:
            if ref in self.source_ref_seen:
                self.source_level_duplicates += 1
            self.source_ref_seen.add(ref)
            prior_normalized = self.source_ref_to_normalized.setdefault(ref, normalized)
            if prior_normalized != normalized:
                self.conflicting_source_refs.add(ref)
                self.conflicting_groups.update((prior_normalized, normalized))

    def begin_selection(self) -> None:
        """Start the record-retaining pass after the complete audit is known."""
        self.groups.clear()
        self.heap.clear()
        self.selection_occurrences.clear()
        self._selection_started = True

    def select(self, record: dict[str, Any]) -> None:
        """Feed a second-pass record into the bottom-k reservoir."""
        if not self._selection_started:
            raise ValueError("begin_selection() must follow the full-source audit pass")
        normalized = record["normalized_game_sha256"]
        expected_result = self.normalized_results.get(normalized)
        if expected_result is None:
            raise ValueError("selection pass found a normalized game absent from the audit pass")
        self.selection_occurrences[normalized] += 1
        if normalized in self.conflicting_groups:
            return
        if record["pgn_result"] != expected_result:
            raise ValueError("selection pass result differs from the audited normalized-game result")
        occurrence = self.selection_occurrences[normalized]
        game_id = make_source_game_id(
            record, source_id=self.source_id, archive_sha256=self.archive_sha256,
            member_name=self.member_name, occurrence=occurrence,
        )
        ref = record.get("source_game_ref_sha256")
        group = self.groups.get(normalized)
        if group is not None:
            group.source_game_ids.add(game_id)
            if ref:
                group.source_refs.add(ref)
            if group.result != record["pgn_result"]:
                group.conflict = True
                self.conflicting_groups.add(normalized)
                self.groups.pop(normalized, None)
            elif game_id < group.record["game_id"]:
                group.record = {**record, "game_id": game_id}
            return
        candidate = {**record, "game_id": game_id}
        rank = self._rank(normalized)
        self._trim_stale()
        if len(self.groups) < self.max_games:
            self.groups[normalized] = Group(
                normalized, record["pgn_result"], candidate, {game_id}, {ref} if ref else set(),
            )
            heapq.heappush(self.heap, self._heap_entry(normalized))
            return
        worst_rank, _, worst_group = self.heap[0]
        if (rank, normalized) < (-worst_rank, worst_group):
            heapq.heappop(self.heap)
            self.groups.pop(worst_group, None)
            self.groups[normalized] = Group(
                normalized, record["pgn_result"], candidate, {game_id}, {ref} if ref else set(),
            )
            heapq.heappush(self.heap, self._heap_entry(normalized))

    def selected_records(self) -> list[dict[str, Any]]:
        if not self._selection_started:
            raise ValueError("selection pass has not started")
        rows: list[dict[str, Any]] = []
        for group in self.groups.values():
            record = dict(group.record)
            record["source_game_ids"] = sorted(group.source_game_ids)
            record["source_game_ref_hashes"] = sorted(group.source_refs)
            record["game_id"] = min(group.source_game_ids)
            record["record_id"] = record["game_id"]
            rows.append(record)
        return sorted(rows, key=lambda row: row["normalized_game_sha256"])

    def verify_selection_complete(self) -> None:
        if self.normalized_observations != self.selection_occurrences:
            raise ValueError("selection pass observations differ from the full-source audit pass")

    def audit_memory_bytes(self) -> int:
        """Approximate shallow Python storage for the compact global audit."""
        import sys

        containers = (
            self.normalized_results, self.normalized_observations,
            self.source_ref_to_normalized, self.source_ref_seen,
            self.conflicting_source_refs, self.conflicting_groups,
        )
        size = sum(sys.getsizeof(container) for container in containers)
        size += sum(sys.getsizeof(key) + sys.getsizeof(value) for key, value in self.normalized_results.items())
        size += sum(sys.getsizeof(key) + sys.getsizeof(value) for key, value in self.normalized_observations.items())
        size += sum(sys.getsizeof(key) + sys.getsizeof(value) for key, value in self.source_ref_to_normalized.items())
        size += sum(sys.getsizeof(value) for values in (self.source_ref_seen, self.conflicting_source_refs, self.conflicting_groups) for value in values)
        return size


def sample_positions(
    games: list[dict[str, Any]], *, source_id: str, seed: int,
    max_positions_per_game: int, max_positions: int,
    sampling_config_sha256: str | None = None,
) -> list[dict[str, Any]]:
    if max_positions_per_game < 1 or max_positions < 1:
        raise ValueError("position limits must be positive")
    sampling_config_sha256 = sampling_config_sha256 or digest({
        "domain": "videochess-sampling-config/v1", "source_id": source_id,
        "seed": seed, "max_positions_per_game": max_positions_per_game,
        "max_positions": max_positions,
    })
    sampling_id = sampling_run_identity(source_id, seed, sampling_config_sha256)
    ranked: list[tuple[str, str, int]] = []
    for game in games:
        local = sorted(
            (ply_sample_key(seed, source_id, game["game_id"], ply), game["game_id"], ply)
            for ply in range(game["ply_count"])
        )[:max_positions_per_game]
        ranked.extend(local)
    ranked.sort()
    selected = ranked[:max_positions]
    games_by_id = {game["game_id"]: game for game in games}
    output: list[dict[str, Any]] = []
    for _, game_id, ply in selected:
        game = games_by_id[game_id]
        board = chess.Board(game["initial_fen"])
        for uci in game["moves_uci"][:ply]:
            board.push_uci(uci)
        played = game["moves_uci"][ply]
        legal = sorted(move.uci() for move in board.legal_moves)
        if board.is_game_over(claim_draw=False) or played not in legal:
            raise ValueError(f"selected position {game_id}:{ply} is terminal or its played move is illegal")
        sample_id = sample_identity(source_id, game_id, game["normalized_game_sha256"], ply)
        side_result = game["white_result"]
        if board.turn == chess.BLACK:
            side_result = {"win": "loss", "loss": "win", "draw": "draw"}[side_result]
        to_move_value = {"win": 1, "draw": 0, "loss": -1}[side_result]
        pgn_result = game["pgn_result"]
        row = {
            "schema": "videochess-position/1.0",
            "schema_version": "videochess-position/1.0",
            "record_id": sample_id,
            "sample_id": sample_id,
            "source_id": source_id,
            "game_id": game_id,
            "normalized_game_sha256": game["normalized_game_sha256"],
            "ply_index": ply,
            "reconstruction_path": {"game_id": game_id, "ply_index": ply},
            "fen": canonical_fen(board),
            "side_to_move": "white" if board.turn else "black",
            "board_position_signature": board_position_signature(board),
            "history_state_id": replay_history_identity(game["initial_fen"], game["moves_uci"][:ply]),
            "legal_moves_uci": legal,
            "candidate_count": len(legal),
            "candidate_set_sha256": digest({"domain": "videochess-candidate-set/v1", "sample_id": sample_id, "legal_moves_uci": legal}),
            "played_move_uci": played,
            "played_candidate_id": candidate_identity(sample_id, played),
            "pgn_result": game["pgn_result"],
            "white_result": game["white_result"],
            "side_to_move_result": side_result,
            "result_white": pgn_result,
            "result_to_move": to_move_value,
            "sampling_id": sampling_id,
            "sampling_config_sha256": sampling_config_sha256,
            "split": None,
            "split_id": None,
        }
        output.append(row)
    return sorted(output, key=lambda row: row["sample_id"])
