"""Measured data-quality and leakage summaries."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

import chess

STATS_SCHEMA = "videochess-dataset-stats/1.1"


def _distribution(rows: list[dict[str, Any]], field: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        value = row.get(field)
        counts["missing" if value in (None, "") else str(value)] += 1
    return counts


def _ply_band(ply: int) -> str:
    if ply < 10:
        return "opening_0_9"
    if ply < 40:
        return "early_10_39"
    if ply < 80:
        return "middle_40_79"
    return "late_80_plus"


def _rate(counter: Counter[str], total: int) -> dict[str, dict[str, float | int]]:
    return {
        key: {"count": value, "fraction": value / total if total else 0.0}
        for key, value in sorted(counter.items())
    }


def _quantiles(values: list[int]) -> dict[str, int | float | None]:
    if not values:
        return {"min": None, "p10": None, "median": None, "p90": None, "max": None}
    ordered = sorted(values)

    def pick(q: float) -> int:
        return ordered[min(len(ordered) - 1, int(q * (len(ordered) - 1)))]

    return {"min": ordered[0], "p10": pick(0.10), "median": pick(0.50), "p90": pick(0.90), "max": ordered[-1]}


def _rating_band(value: Any) -> str:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return "missing"
    lower = (value // 100) * 100
    return f"{lower}-{lower + 99}"


def position_quality_distributions(
    rows: list[dict[str, Any]], games_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Summarize position and parent-game attributes for one purge phase."""
    fields = {
        "ply_band": Counter(), "side_to_move": Counter(), "pgn_result": Counter(),
        "white_result": Counter(), "side_to_move_result": Counter(),
        "candidate_count": Counter(), "white_elo_band": Counter(),
        "black_elo_band": Counter(), "time_control": Counter(),
        "repetition_context": Counter(), "split": Counter(),
    }
    board_signatures: set[str] = set()
    history_states: set[str] = set()
    candidate_rows = 0
    for row in rows:
        game = games_by_id.get(row.get("game_id"))
        if game is None:
            raise ValueError(f"quality statistics cannot find parent game {row.get('game_id')!r}")
        fields["ply_band"][_ply_band(row["ply_index"])] += 1
        fields["side_to_move"][str(row.get("side_to_move") or "missing")] += 1
        fields["pgn_result"][str(row.get("pgn_result", game["pgn_result"]))] += 1
        fields["white_result"][str(row.get("white_result") or "missing")] += 1
        fields["side_to_move_result"][str(row.get("side_to_move_result") or "missing")] += 1
        fields["candidate_count"][str(row["candidate_count"])] += 1
        fields["white_elo_band"][_rating_band(game.get("white_elo"))] += 1
        fields["black_elo_band"][_rating_band(game.get("black_elo"))] += 1
        fields["time_control"][str(game.get("time_control") or "missing")] += 1
        fields["split"][str(row.get("split") or "missing")] += 1
        board = chess.Board(game["initial_fen"])
        for uci in game["moves_uci"][:row["ply_index"]]:
            board.push_uci(uci)
        repetition = (
            "threefold_current" if board.is_repetition(3) else
            "repeated_before" if board.is_repetition(2) else "first_occurrence"
        )
        fields["repetition_context"][repetition] += 1
        board_signatures.add(row["board_position_signature"])
        history_states.add(row["history_state_id"])
        candidate_rows += row["candidate_count"]
    total = len(rows)
    return {
        "positions": total,
        "candidate_rows": candidate_rows,
        "distinct_board_signatures": len(board_signatures),
        "distinct_replay_history_states": len(history_states),
        "distributions": {name: _rate(counter, total) for name, counter in sorted(fields.items())},
    }


def quality_distribution_shifts(
    before: dict[str, Any], after: dict[str, Any],
) -> dict[str, dict[str, float]]:
    """Return after-minus-before fractions for every retained quality field."""
    shifts: dict[str, dict[str, float]] = {}
    for field in sorted(before["distributions"]):
        first = before["distributions"][field]
        second = after["distributions"][field]
        keys = set(first) | set(second)
        shifts[field] = {
            key: (second.get(key, {}).get("fraction", 0.0) - first.get(key, {}).get("fraction", 0.0))
            for key in sorted(keys)
        }
    return shifts


def summarize_dataset(
    games: list[dict[str, Any]], positions_before: list[dict[str, Any]],
    positions_after: list[dict[str, Any]], split_manifest: dict[str, Any],
    parse_counts: dict[str, Any], *, sampling: dict[str, Any],
    resources: dict[str, Any], config_sha256: str, source_manifest: dict[str, Any],
) -> dict[str, Any]:
    games_by_id = {game["game_id"]: game for game in games}
    quality_before = position_quality_distributions(positions_before, games_by_id)
    quality_after = position_quality_distributions(positions_after, games_by_id)
    candidates = [row["candidate_count"] for row in positions_before]
    side = _distribution(positions_before, "side_to_move")
    result = _distribution(positions_before, "white_result")
    before_ply = Counter(_ply_band(row["ply_index"]) for row in positions_before)
    after_ply = Counter(_ply_band(row["ply_index"]) for row in positions_after)
    before_to_move_result = _distribution(positions_before, "side_to_move_result")
    positions_per_game = Counter(row["game_id"] for row in positions_before)
    position_pairs = len(positions_before) * (len(positions_before) - 1) // 2
    within_game_pairs = sum(count * (count - 1) // 2 for count in positions_per_game.values())
    opening_prefixes = Counter(
        " ".join(game["moves_uci"][:8]) for game in games
    )
    opening_total = sum(opening_prefixes.values())
    opening_hhi = math.fsum(
        (count / opening_total) ** 2 for count in opening_prefixes.values()
    ) if opening_total else 0.0
    rating = Counter()
    for game in games:
        if game.get("white_elo") is None or game.get("black_elo") is None:
            rating["one_or_more_missing"] += 1
        else:
            rating["both_present"] += 1
    times = Counter("missing" if not game.get("time_control") else str(game["time_control"]) for game in games)

    return {
        "schema": STATS_SCHEMA,
        "quality_report_version": 2,
        "source": {
            "source_id": source_manifest["source_id"],
            "publisher": source_manifest["publisher"],
            "archive_sha256": source_manifest["archive_sha256"],
            "archive_bytes": source_manifest["archive_bytes"],
            "member_name": source_manifest["member"]["name"],
            "member_sha256": source_manifest["member_sha256"],
            "member_bytes": source_manifest["member_bytes"],
        },
        "config_sha256": config_sha256,
        "scan": parse_counts,
        "selected_games": len(games),
        "source_level_duplicate_observations": parse_counts.get("source_level_duplicates", 0),
        "normalized_game_duplicate_groups": parse_counts.get("normalized_duplicate_groups", 0),
        "normalized_game_duplicate_observations": parse_counts.get("normalized_duplicate_observations", 0),
        "conflicting_normalized_groups": parse_counts.get("conflicting_normalized_groups", 0),
        "sampling": sampling,
        "game_lengths_plies": _quantiles([game["ply_count"] for game in games]),
        "game_length_histogram": dict(sorted(Counter(_ply_band(game["ply_count"]) for game in games).items())),
        "opening_concentration": {
            "identity": "first 8 main-line UCI plies (or complete shorter game)",
            "unique_prefixes": len(opening_prefixes),
            "top_20_prefixes": [
                {"uci_prefix": prefix, "games": count}
                for prefix, count in sorted(
                    opening_prefixes.items(), key=lambda item: (-item[1], item[0]),
                )[:20]
            ],
            "hhi": round(opening_hhi, 8),
        },
        "positions_selected_before_purge": len(positions_before),
        "positions_retained_after_purge": len(positions_after),
        "position_grouping": {
            "games_with_selected_positions": len(positions_per_game),
            "positions_per_game": _quantiles(list(positions_per_game.values())),
            "same_game_pair_fraction": within_game_pairs / position_pairs if position_pairs else 0.0,
        },
        "legal_candidates": {
            "total": sum(candidates), "per_position": _quantiles(candidates),
            "histogram": dict(sorted(Counter(map(str, candidates)).items(), key=lambda item: int(item[0]))),
        },
        "side_to_move_before_purge": _rate(side, len(positions_before)),
        "white_result_before_purge": _rate(result, len(positions_before)),
        "side_to_move_result_before_purge": _rate(before_to_move_result, len(positions_before)),
        "positions_by_ply_band_before_purge": dict(sorted(before_ply.items())),
        "positions_by_ply_band_after_purge": dict(sorted(after_ply.items())),
        "distribution_shift_after_purge_fraction": {
            **quality_distribution_shifts(quality_before, quality_after),
        },
        "position_quality_before_purge": quality_before,
        "position_quality_after_purge": quality_after,
        "clock_information": {
            "status": "unavailable",
            "reason": "The selected Elite package is documented as omitting clock times; clock comments are not retained in the release.",
        },
        # Preserve both states even when one count is zero. Release verification
        # recomputes this availability summary from the game records.
        "rating_metadata": {
            "one_or_more_missing": rating["one_or_more_missing"],
            "both_present": rating["both_present"],
        },
        "time_control_distribution": dict(sorted(times.items())),
        "header_key_frequency": dict(sorted(Counter(
            key for game in games for key in game.get("header_keys", [])
        ).items())),
        "missing_metadata": {
            "white_elo": sum(game.get("white_elo") is None for game in games),
            "black_elo": sum(game.get("black_elo") is None for game in games),
            "time_control": sum(not game.get("time_control") for game in games),
            "date": sum(not game.get("date") for game in games),
        },
        "splits": split_manifest,
        "resource_measurements": resources,
    }
