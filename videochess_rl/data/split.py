"""Deterministic game grouping and board-overlap ownership/purge."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .contracts import (
    SPLIT_SCHEMA, assign_game_split, board_signature_owner, split_manifest_identity,
)


class SplitError(ValueError):
    """Split invariants or configured holdout acceptance failed."""

    def __init__(self, message: str, manifest: dict[str, Any] | None = None):
        super().__init__(message)
        self.manifest = manifest


def split_and_purge(
    games: list[dict[str, Any]], positions: list[dict[str, Any]], *, seed: int,
    min_holdout_positions: int, min_holdout_retention: float = 0.5,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if min_holdout_positions < 1 or not 0.0 <= min_holdout_retention <= 1.0:
        raise ValueError("invalid holdout limits")
    assignment_by_group: dict[str, str] = {}
    game_assignments: list[list[str]] = []
    for game in games:
        group = game["normalized_game_sha256"]
        split = assign_game_split(seed, group)
        prior = assignment_by_group.setdefault(group, split)
        if prior != split:
            raise SplitError("normalized duplicate group was assigned to multiple splits")
        game_assignments.append([group, split])
    for row in positions:
        split = assignment_by_group.get(row["normalized_game_sha256"])
        if split is None:
            raise SplitError(f"position {row['sample_id']} has no parent split")
        row["split"] = split
        row["split_id"] = split

    by_board: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in positions:
        by_board[row["board_position_signature"]].append(row)
    owners: dict[str, str] = {}
    purged: list[dict[str, str]] = []
    for signature, rows in by_board.items():
        present = {row["split"] for row in rows}
        owner = board_signature_owner(seed, signature, present)
        owners[signature] = owner
        for row in rows:
            if row["split"] != owner:
                purged.append({
                    "sample_id": row["sample_id"],
                    "board_position_signature": signature,
                    "original_split": row["split"],
                    "owner_split": owner,
                    "game_id": row["game_id"],
                    "history_state_id": row["history_state_id"],
                    "side_to_move": row["side_to_move"],
                    "white_result": row["white_result"],
                    "pgn_result": row["pgn_result"],
                    "side_to_move_result": row["side_to_move_result"],
                    "ply_index": row["ply_index"],
                    "candidate_count": row["candidate_count"],
                    "played_move_uci": row["played_move_uci"],
                })
    kept = [row for row in positions if row["split"] == owners[row["board_position_signature"]]]
    if len({row["sample_id"] for row in positions}) != len(positions):
        raise SplitError("duplicate sample_id before split purge")
    if len({row["sample_id"] for row in kept}) != len(kept):
        raise SplitError("duplicate sample_id after split purge")

    before = {name: sum(row["split"] == name for row in positions) for name in ("train", "validation", "test")}
    after = {name: sum(row["split"] == name for row in kept) for name in ("train", "validation", "test")}
    retention = {
        name: (after[name] / before[name] if before[name] else 0.0)
        for name in ("train", "validation", "test")
    }
    failures = [
        f"{name} holdout has {after[name]} retained positions (minimum {min_holdout_positions})"
        for name in ("validation", "test") if after[name] < min_holdout_positions
    ]
    failures.extend(
        f"{name} retention {retention[name]:.4f} is below {min_holdout_retention:.4f}"
        for name in ("validation", "test") if retention[name] < min_holdout_retention
    )
    warnings = [
        f"{name} holdout retention is below the 80% warning threshold ({retention[name]:.4f})"
        for name in ("validation", "test") if retention[name] < 0.8
    ]
    cross_split_signatures = sum(
        len({row["split"] for row in rows}) > 1 for rows in by_board.values()
    )
    remaining_by_board: dict[str, set[str]] = defaultdict(set)
    for row in kept:
        remaining_by_board[row["board_position_signature"]].add(row["split"])
    if any(len(splits) > 1 for splits in remaining_by_board.values()):
        raise SplitError("board-position overlap remains after ownership purge")
    owner_rows = [[signature, owner] for signature, owner in owners.items()]
    purge_rows = [
        [row["sample_id"], row["original_split"], row["owner_split"]]
        for row in purged
    ]
    assignment_hash = split_manifest_identity(seed, game_assignments, owner_rows, purge_rows)
    split_manifest = {
        "schema": SPLIT_SCHEMA,
        "split_seed": seed,
        "game_group_assignments": sorted(game_assignments),
        "board_signature_owners": sorted(owner_rows),
        "purged_samples": sorted(purged, key=lambda row: row["sample_id"]),
        "split_assignment_sha256": assignment_hash,
        "game_counts": {
            name: sum(split == name for split in assignment_by_group.values())
            for name in ("train", "validation", "test")
        },
        "position_counts_before_purge": before,
        "position_counts_after_purge": after,
        "position_retention": retention,
        "board_signatures_before": len(by_board),
        "board_signatures_cross_split_before": cross_split_signatures,
        "board_signatures_after": len(remaining_by_board),
        "board_signatures_cross_split_after": 0,
        "distinct_history_states_before": len({row["history_state_id"] for row in positions}),
        "distinct_history_states_after": len({row["history_state_id"] for row in kept}),
        "purged_position_count": len(purged),
        "purged_candidate_count": sum(row["candidate_count"] for row in purged),
        "holdout_minimum": min_holdout_positions,
        "holdout_minimum_retention": min_holdout_retention,
        "holdout_warning_retention": 0.8,
        "holdout_failures": failures,
        "holdout_warnings": warnings,
        "release_valid": not failures,
    }
    if failures:
        raise SplitError("; ".join(failures), split_manifest)
    return sorted(kept, key=lambda row: row["sample_id"]), split_manifest
