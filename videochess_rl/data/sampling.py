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
    """Retain the same lowest-ranked normalized games regardless of input order."""

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
        self.heap: list[tuple[int, str]] = []
        self.seen_normalized: set[str] = set()
        self.normalized_duplicate_observations = 0
        self.normalized_duplicate_groups = 0
        self.source_ref_seen: set[str] = set()
        self.source_ref_to_normalized: dict[str, str] = {}
        self.conflicting_source_refs: set[str] = set()
        self.source_level_duplicates = 0
        self.conflicting_groups: set[str] = set()
        self.occurrences: Counter[str] = Counter()

    def _rank(self, normalized: str) -> int:
        return int(game_sample_key(self.seed, normalized), 16)

    def _trim_stale(self) -> None:
        while self.heap and self.heap[0][1] not in self.groups:
            heapq.heappop(self.heap)
        if len(self.heap) > max(16, 2 * self.max_games):
            self.heap = [(-self._rank(key), key) for key in self.groups]
            heapq.heapify(self.heap)

    def add(self, record: dict[str, Any]) -> None:
        normalized = record["normalized_game_sha256"]
        self.occurrences[normalized] += 1
        occurrence = self.occurrences[normalized]
        game_id = make_source_game_id(
            record, source_id=self.source_id, archive_sha256=self.archive_sha256,
            member_name=self.member_name, occurrence=occurrence,
        )
        ref = record.get("source_game_ref_sha256")
        if ref:
            if ref in self.source_ref_seen:
                self.source_level_duplicates += 1
            self.source_ref_seen.add(ref)
            prior_normalized = self.source_ref_to_normalized.setdefault(ref, normalized)
            if prior_normalized != normalized:
                self.conflicting_source_refs.add(ref)
                self.conflicting_groups.update((prior_normalized, normalized))
                self.groups.pop(prior_normalized, None)
                self.groups.pop(normalized, None)
                return

        if normalized in self.conflicting_groups:
            return

        if normalized in self.seen_normalized:
            self.normalized_duplicate_observations += 1
            if self.occurrences[normalized] == 2:
                self.normalized_duplicate_groups += 1
        else:
            self.seen_normalized.add(normalized)
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
            heapq.heappush(self.heap, (-rank, normalized))
            return
        worst_rank, worst_group = self.heap[0]
        if rank < -worst_rank or (rank == -worst_rank and normalized < worst_group):
            heapq.heappop(self.heap)
            self.groups.pop(worst_group, None)
            self.groups[normalized] = Group(
                normalized, record["pgn_result"], candidate, {game_id}, {ref} if ref else set(),
            )
            heapq.heappush(self.heap, (-rank, normalized))

    def selected_records(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for group in self.groups.values():
            record = dict(group.record)
            record["source_game_ids"] = sorted(group.source_game_ids)
            record["source_game_ref_hashes"] = sorted(group.source_refs)
            record["game_id"] = min(group.source_game_ids)
            record["record_id"] = record["game_id"]
            rows.append(record)
        return sorted(rows, key=lambda row: row["normalized_game_sha256"])


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
    sampling_id = digest({
        "domain": "videochess-sampling-run/v1", "source_id": source_id,
        "seed": seed, "sampling_config_sha256": sampling_config_sha256,
    })
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
