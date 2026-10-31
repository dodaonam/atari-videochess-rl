"""Independent, raw-record reconstruction and cluster-aware M7 analysis."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import random
import statistics
from typing import Any, Iterable

import chess

from videochess_rl.m6.ledger import (
    build_artifact_manifest,
    iter_verified_hash_chain,
    sha256_file,
    verify_artifact_manifest,
    verify_episode_trace,
)
from videochess_rl.m6.campaign import _slug
from videochess_rl.m7.protocol import (
    ALE_SEEDS,
    M4_ROOT_MANIFEST_SHA256,
    M5_ROOT_MANIFEST_SHA256,
    M6_V1_CONFIG_SHA256,
    M6_V1_MANIFEST_SHA256,
    M6_V2_CONFIG_SHA256,
    M6_V2_MANIFEST_SHA256,
    load_frozen_config,
    schedule_sha256,
)


class AnalysisIntegrityError(ValueError):
    """Raw evidence is missing, unsafe, or inconsistent with its frozen identity."""


KNOWN_TERMINAL_RUNNER_CATEGORIES = {"ALE_TERMINATED"}


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def classify_raw_ale_outcome(trace: dict[str, Any]) -> str:
    """Classify solely from ALE terminal flags/reward and explicit censor state."""
    terminal = trace.get("terminal")
    if not isinstance(terminal, dict):
        return "incomplete"
    terminated = terminal.get("ale_terminated") is True
    truncated = terminal.get("ale_truncated") is True
    if terminated and not truncated:
        reward = _finite_number(terminal.get("ale_reward_total"))
        if reward is None or reward == 0:
            return "terminal_unknown"
        return "win" if reward > 0 else "loss"  # the authorized M7 agent is White
    if truncated:
        return "truncated"
    return "incomplete"


def recorded_outcome_matches_raw(record: dict[str, Any], raw_outcome: str) -> bool:
    """Check M7 records and immutable M6-era records against raw ALE facts."""
    if record.get("schema") == "videochess-m6-attempt-record/1.0":
        # M6's runner vocabulary is retained in its own artifacts. Normalize only
        # for analysis, without editing the accepted raw record.
        historical_m6_map = {
            "win": "win",
            "draw": "draw",
            "loss": "loss",
            "terminal_unknown": "terminal_unknown",
            "ale_truncated": "truncated",
            "incomplete": "incomplete",
            "runner_truncated": "incomplete",
        }
        return historical_m6_map.get(record.get("outcome")) == raw_outcome
    return record.get("outcome") == raw_outcome


def normalized_recorded_outcome(record: dict[str, Any]) -> str:
    if record.get("schema", record.get("record_schema")) == "videochess-m6-attempt-record/1.0":
        historical_m6_map = {
            "win": "win", "draw": "draw", "loss": "loss",
            "terminal_unknown": "terminal_unknown", "ale_truncated": "truncated",
            "incomplete": "incomplete", "runner_truncated": "incomplete",
        }
        outcome = historical_m6_map.get(record.get("recorded_outcome", record.get("outcome")))
        if outcome is None:
            raise AnalysisIntegrityError(f"unsupported historical M6 outcome: {record.get('outcome')!r}")
        return outcome
    outcome = record.get("recorded_outcome", record.get("outcome"))
    if not isinstance(outcome, str):
        raise AnalysisIntegrityError("attempt record has no outcome category")
    return outcome


def paired_interval_with_censoring(
    paired_rows: list[dict[str, Any]], *, scheduled_pairs: int, censored_pairs: int,
) -> dict[str, Any]:
    """Suppress inferential intervals when terminal-only pairing is censored."""
    if censored_pairs:
        finite = [float(row["difference"]) for row in paired_rows]
        return {
            "point_difference": sum(finite) / len(finite) if finite else None,
            "ci_95_crossed_cluster": None,
            "iterations": 10000,
            "bootstrap_seed": 20261290,
            "training_seed_clusters": len({str(row["training_seed"]) for row in paired_rows}),
            "evaluation_seed_clusters": len({int(row["evaluation_seed"]) for row in paired_rows}),
            "matched_pair_rows": len(paired_rows),
            "scheduled_pairs": scheduled_pairs,
            "censored_pairs": censored_pairs,
            "status": "unavailable_incomplete_or_censored_pair_set",
        }
    result = crossed_cluster_bootstrap(paired_rows)
    result.update({"scheduled_pairs": scheduled_pairs, "censored_pairs": 0})
    return result


def _game_score(wins: int, draws: int, terminal_known: int) -> float | None:
    if terminal_known <= 0:
        return None
    return (wins + 0.5 * draws) / terminal_known


def classify_terminal_cell(rows: Iterable[dict[str, Any]]) -> dict[str, int | float | None]:
    counts = {key: 0 for key in ("wins", "draws", "losses", "terminal_unknown", "truncated", "incomplete", "not_started")}
    names = {"win": "wins", "draw": "draws", "loss": "losses"}
    for row in rows:
        category = row.get("outcome", "not_started")
        category = names.get(category, category)
        if category not in counts:
            raise AnalysisIntegrityError(f"unsupported attempt category: {category!r}")
        counts[category] += 1
    known = counts["wins"] + counts["draws"] + counts["losses"]
    counts["terminal_known_games"] = known
    counts["terminal_only_game_score"] = _game_score(counts["wins"], counts["draws"], known)
    return counts


def _quantile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("quantile requires at least one value")
    index = int(round(probability * (len(sorted_values) - 1)))
    return sorted_values[max(0, min(index, len(sorted_values) - 1))]


def crossed_cluster_bootstrap(
    rows: list[dict[str, Any]],
    *,
    difference_key: str = "difference",
    training_key: str = "training_seed",
    evaluation_key: str = "evaluation_seed",
    iterations: int = 10000,
    seed: int = 20261290,
) -> dict[str, Any]:
    """Cross-resample whole training and evaluation clusters, preserving pairs."""
    if iterations != 10000:
        raise ValueError("the preregistered M7 bootstrap uses exactly 10,000 resamples")
    finite_rows = []
    for row in rows:
        value = _finite_number(row.get(difference_key))
        if value is not None:
            finite_rows.append((str(row[training_key]), int(row[evaluation_key]), value))
    train_ids = sorted({row[0] for row in finite_rows})
    eval_ids = sorted({row[1] for row in finite_rows})
    if not finite_rows or not train_ids or not eval_ids:
        return {
            "point_difference": None,
            "ci_95_crossed_cluster": None,
            "iterations": iterations,
            "bootstrap_seed": seed,
            "training_seed_clusters": len(train_ids),
            "evaluation_seed_clusters": len(eval_ids),
            "matched_pair_rows": len(finite_rows),
            "status": "unavailable_no_valid_pairs",
        }
    grouped: dict[tuple[str, int], list[float]] = {}
    for train_id, eval_id, value in finite_rows:
        grouped.setdefault((train_id, eval_id), []).append(value)
    point = sum(value for _, _, value in finite_rows) / len(finite_rows)
    rng = random.Random(seed)
    estimates: list[float] = []
    for _ in range(iterations):
        sampled_train = [rng.choice(train_ids) for _ in train_ids]
        sampled_eval = [rng.choice(eval_ids) for _ in eval_ids]
        values = [
            value
            for train_id in sampled_train
            for eval_id in sampled_eval
            for value in grouped.get((train_id, eval_id), ())
        ]
        if values:
            estimates.append(sum(values) / len(values))
    estimates.sort()
    if len(estimates) != iterations:
        return {
            "point_difference": point,
            "ci_95_crossed_cluster": None,
            "iterations": iterations,
            "bootstrap_seed": seed,
            "successful_resamples": len(estimates),
            "training_seed_clusters": len(train_ids),
            "evaluation_seed_clusters": len(eval_ids),
            "matched_pair_rows": len(finite_rows),
            "status": "unavailable_some_resamples_had_no_matched_cells",
        }
    return {
        "point_difference": point,
        "ci_95_crossed_cluster": [_quantile(estimates, 0.025), _quantile(estimates, 0.975)],
        "iterations": iterations,
        "bootstrap_seed": seed,
        "successful_resamples": len(estimates),
        "training_seed_clusters": len(train_ids),
        "evaluation_seed_clusters": len(eval_ids),
        "matched_pair_rows": len(finite_rows),
        "few_training_cluster_caveat": len(train_ids) <= 3,
        "status": "computed_descriptive_cluster_interval",
    }


def evaluation_seed_bootstrap(
    values: list[dict[str, Any]],
    *,
    value_key: str = "value",
    cluster_key: str = "evaluation_seed",
    iterations: int = 10000,
    seed: int = 20261290,
) -> dict[str, Any]:
    """Resample whole evaluation-seed blocks for a fixed frozen policy."""
    if iterations != 10000:
        raise ValueError("the preregistered M7 bootstrap uses exactly 10,000 resamples")
    grouped: dict[int, list[float]] = {}
    for row in values:
        value = _finite_number(row.get(value_key))
        if value is not None:
            grouped.setdefault(int(row[cluster_key]), []).append(value)
    ids = sorted(grouped)
    if not ids:
        return {"mean": None, "ci_95_seed_cluster": None, "iterations": iterations, "bootstrap_seed": seed,
                "evaluation_seed_clusters": 0, "status": "unavailable_no_valid_clusters"}
    clusters = {key: sum(items) / len(items) for key, items in grouped.items()}
    point = sum(clusters.values()) / len(clusters)
    rng = random.Random(seed)
    estimates = sorted(sum(clusters[rng.choice(ids)] for _ in ids) / len(ids) for _ in range(iterations))
    return {"mean": point, "ci_95_seed_cluster": [_quantile(estimates, 0.025), _quantile(estimates, 0.975)],
            "iterations": iterations, "bootstrap_seed": seed, "evaluation_seed_clusters": len(ids),
            "status": "computed_descriptive_seed_cluster_interval"}


def _raw_terminal_score(row: dict[str, Any]) -> float | None:
    if row.get("outcome") == "win":
        return 1.0
    if row.get("outcome") == "draw":
        return 0.5
    if row.get("outcome") == "loss":
        return 0.0
    return None


def _m5_policy_identity(policy_id: str) -> tuple[str | None, int | None, str | None]:
    if policy_id == "m4_behavior_only":
        return "m4_behavior_only", None, None
    if policy_id.startswith("baseline:"):
        return policy_id.split(":", 1)[1], None, None
    parts = policy_id.split(":")
    if len(parts) == 3 and parts[0] in {"warm", "scratch"} and parts[2] in {"pre_rl", "post_rl"}:
        return parts[0], int(parts[1]), parts[2]
    raise AnalysisIntegrityError(f"unrecognized accepted M5 policy identity {policy_id!r}")


def load_m5_raw_rows(m5_root: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    supplied_root = Path(m5_root).expanduser()
    if supplied_root.is_symlink():
        raise AnalysisIntegrityError("accepted M5 root must not be a symbolic link")
    root = supplied_root.resolve(strict=True)
    manifest_path = root / "artifact-manifest.json"
    if manifest_path.is_symlink() or sha256_file(manifest_path) != M5_ROOT_MANIFEST_SHA256:
        raise AnalysisIntegrityError("accepted M5 root manifest hash changed")
    from scripts.m5_artifact_manifests import verify_manifest

    manifest = verify_manifest(root, manifest_path)
    if manifest.get("status") != "complete":
        raise AnalysisIntegrityError("accepted M5 raw evaluation root is not complete")
    report_path = root / "evaluation/evaluation-report.json"
    if not report_path.is_file() or report_path.is_symlink():
        raise AnalysisIntegrityError("accepted M5 evaluation report is missing/unsafe")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    final_paths = [row for row in manifest["files"] if row["path"].startswith("evaluation/") and row["path"].endswith("/final-rows-attempt-0000.json")]
    if len(final_paths) != 15:
        raise AnalysisIntegrityError(f"expected 15 accepted M5 policy raw-row files; found {len(final_paths)}")
    for item in final_paths:
        path = root / item["path"]
        if path.is_symlink() or not path.is_file() or sha256_file(path) != item["sha256"]:
            raise AnalysisIntegrityError(f"accepted M5 raw-row file hash mismatch: {item['path']}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or len(data) != 100:
            raise AnalysisIntegrityError(f"accepted M5 policy schedule is malformed: {item['path']}")
        rows.extend(data)
    if len(rows) != 1500 or len({row.get("game_id") for row in rows}) != 1500:
        raise AnalysisIntegrityError("accepted M5 raw rows do not form 1,500 unique game records")
    groups = {row.get("policy_id") for row in rows}
    if len(groups) != 15 or any(sum(row.get("policy_id") == group for row in rows) != 100 for group in groups):
        raise AnalysisIntegrityError("accepted M5 raw rows do not contain 15 complete 100-game policy groups")
    if any(row.get("metric_source") != "python_chess_m2_simulator" for row in rows):
        raise AnalysisIntegrityError("M5 raw evaluation rows contain an unexpected evidence track")
    for row in rows:
        _m5_policy_identity(str(row.get("policy_id")))
        if row.get("status") not in {"completed_game", "incomplete_policy_deadline"}:
            raise AnalysisIntegrityError(f"unsupported M5 raw-row status: {row.get('status')!r}")
        if not isinstance(row.get("truncated"), bool):
            raise AnalysisIntegrityError("M5 raw row is missing its terminal/truncation distinction")
        if not row["truncated"] and row.get("status") == "completed_game" and _finite_number(row.get("agent_reward")) not in {-1.0, 0.0, 1.0}:
            raise AnalysisIntegrityError("M5 terminal row has unsupported agent-perspective reward")
    raw_summary = summarize_m5_rows(rows)
    accepted_per_policy = report.get("per_policy")
    if not isinstance(accepted_per_policy, list) or len(accepted_per_policy) != 15:
        raise AnalysisIntegrityError("accepted M5 machine report lacks all 15 policy summaries")
    for accepted in accepted_per_policy:
        policy_id = accepted.get("policy_id")
        raw = raw_summary["by_policy"].get(policy_id)
        summary = accepted.get("summary", {})
        if raw is None or accepted.get("games") != raw["scheduled"] or accepted.get("planned_games") != 100:
            raise AnalysisIntegrityError(f"M5 raw/report policy schedule mismatch for {policy_id!r}")
        if (
            summary.get("game_rows") != raw["scheduled"]
            or summary.get("completed_games") != raw["terminal_known_games"]
            or summary.get("truncated_games") != raw["truncated"]
            or summary.get("wins") != raw["wins"]
            or summary.get("draws") != raw["draws"]
            or summary.get("losses") != raw["losses"]
            or summary.get("score_rate_completed") != raw["terminal_only_game_score"]
        ):
            raise AnalysisIntegrityError(f"M5 raw W/D/L reconstruction differs from accepted report for {policy_id!r}")
    return rows, {"root_manifest_sha256": M5_ROOT_MANIFEST_SHA256, "raw_rows": len(rows),
                  "raw_policy_files": len(final_paths), "evaluation_report_sha256": sha256_file(report_path),
                  "evaluation_report_schedule_complete": report.get("schedule_complete")}


def _m5_outcome(row: dict[str, Any]) -> str:
    if row.get("status") != "completed_game":
        return "incomplete"
    if row.get("truncated") is True:
        return "truncated"
    reward = _finite_number(row.get("agent_reward"))
    if reward is None:
        return "terminal_unknown"
    return "win" if reward > 0 else "loss" if reward < 0 else "draw"


def summarize_m5_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_policy: dict[str, list[dict[str, Any]]] = {}
    for raw in rows:
        row = dict(raw)
        row["outcome"] = _m5_outcome(row)
        by_policy.setdefault(str(row["policy_id"]), []).append(row)
    summaries: dict[str, Any] = {}
    for policy_id, group in sorted(by_policy.items()):
        counts = classify_terminal_cell(row for row in group)
        scheduled = len(group)
        complete = counts["terminal_known_games"]
        counts.update({
            "scheduled": scheduled,
            "completion_rate_known_wdl": complete / scheduled if scheduled else None,
            "game_score_denominator": complete,
            "evidence_track": "M2 python-chess simulator; not Atari",
        })
        summaries[policy_id] = counts
    return {"scheduled_rows": len(rows), "policy_count": len(summaries), "by_policy": summaries}


def _m5_score_map(rows: list[dict[str, Any]]) -> dict[tuple[str, int, str, str, str], dict[str, Any]]:
    mapped = {}
    for raw in rows:
        arm, training_seed, stage = _m5_policy_identity(str(raw["policy_id"]))
        key = (str(arm), int(training_seed or 0), str(stage or "baseline"), str(raw["evaluation_seed"]),
               f"{raw['opponent_id']}|{raw['agent_color']}")
        if key in mapped:
            raise AnalysisIntegrityError(f"duplicate M5 paired scenario key: {key}")
        row = dict(raw)
        row["outcome"] = _m5_outcome(row)
        row["score"] = (float(raw["agent_reward"]) + 1.0) / 2.0 if row["outcome"] in {"win", "draw", "loss"} else None
        row["training_seed"] = int(training_seed or 0)
        row["stage"] = stage or "baseline"
        mapped[key] = row
    return mapped


def paired_m5_comparison(rows: list[dict[str, Any]], left: Any, right: Any, *, label: str) -> dict[str, Any]:
    # Index by the shared scenario dimensions. Baselines are paired to each
    # training-seed cluster at the same evaluation seed/opponent/color.
    left_rows: dict[tuple[int, int, str, str], dict[str, Any]] = {}
    right_source: list[tuple[int, int, str, str, dict[str, Any]]] = []
    for raw in rows:
        arm, train_seed, stage = _m5_policy_identity(str(raw["policy_id"]))
        key = (int(train_seed or 0), int(raw["evaluation_seed"]), str(raw["opponent_id"]), str(raw["agent_color"]))
        row = dict(raw)
        row["outcome"] = _m5_outcome(row)
        row["score"] = (float(raw["agent_reward"]) + 1.0) / 2.0 if row["outcome"] in {"win", "draw", "loss"} else None
        row["training_seed"] = int(train_seed or 0)
        row["stage"] = stage or "baseline"
        if left(raw):
            if key in left_rows:
                raise AnalysisIntegrityError(f"duplicate left M5 comparison key for {label}: {key}")
            left_rows[key] = row
        if right(raw):
            right_source.append((*key, row))
    training_seeds = sorted({key[0] for key in left_rows if key[0]})
    right_rows: dict[tuple[int, int, str, str], dict[str, Any]] = {}
    for train_seed, eval_seed, opponent, color, row in right_source:
        target_seeds = training_seeds if train_seed == 0 and training_seeds else [train_seed]
        for target_seed in target_seeds:
            key = (target_seed, eval_seed, opponent, color)
            if key in right_rows:
                raise AnalysisIntegrityError(f"duplicate right M5 comparison key for {label}: {key}")
            right_rows[key] = row
    keys = set(left_rows) | set(right_rows)
    paired: list[dict[str, Any]] = []
    matched = 0
    censored = 0
    missing = 0
    for key in keys:
        a, b = left_rows.get(key), right_rows.get(key)
        if a is None or b is None:
            missing += 1
            continue
        if a["score"] is None or b["score"] is None:
            censored += 1
            continue
        matched += 1
        paired.append({"training_seed": key[0] if key[0] else "fixed", "evaluation_seed": key[1], "difference": a["score"] - b["score"]})
    if censored:
        interval = {
            "point_difference": sum(row["difference"] for row in paired) / len(paired) if paired else None,
            "ci_95_crossed_cluster": None,
            "iterations": 10000,
            "bootstrap_seed": 20261290,
            "training_seed_clusters": len({row["training_seed"] for row in paired}),
            "evaluation_seed_clusters": len({row["evaluation_seed"] for row in paired}),
            "matched_pair_rows": len(paired),
            "status": "unavailable_incomplete_or_censored_pair_set",
        }
    else:
        interval = crossed_cluster_bootstrap(paired)
    per_seed: list[dict[str, Any]] = []
    for train_seed in sorted({row["training_seed"] for row in paired}, key=str):
        values = [row["difference"] for row in paired if row["training_seed"] == train_seed]
        per_seed.append({"training_seed": train_seed, "matched_pairs": len(values),
                         "mean_score_difference": sum(values) / len(values) if values else None})
    return {"comparison": label, "left_minus_right": interval, "matched_terminal_pairs": matched,
            "censored_pairs": censored, "unmatched_rows": missing, "per_training_seed": per_seed,
            "pairing_keys": ["training_seed", "evaluation_seed", "opponent_id", "agent_color"],
            "terminal_only_complete_case": True}


def analyze_m5(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summaries = summarize_m5_rows(rows)
    comparisons: list[dict[str, Any]] = []
    for arm in ("warm", "scratch"):
        comparisons.append(paired_m5_comparison(
            rows,
            lambda row, arm=arm: row["policy_id"].startswith(f"{arm}:") and row["policy_id"].endswith(":post_rl"),
            lambda row, arm=arm: row["policy_id"].startswith(f"{arm}:") and row["policy_id"].endswith(":pre_rl"),
            label=f"{arm}_pre_vs_post",
        ))
    for stage in ("pre_rl", "post_rl"):
        comparisons.append(paired_m5_comparison(
            rows,
            lambda row, stage=stage: row["policy_id"].startswith("warm:") and row["policy_id"].endswith(f":{stage}"),
            lambda row, stage=stage: row["policy_id"].startswith("scratch:") and row["policy_id"].endswith(f":{stage}"),
            label=f"warm_vs_scratch_{stage}",
        ))
    fixed = [
        ("m4_behavior_only", lambda row: row["policy_id"] == "m4_behavior_only"),
        ("random_legal", lambda row: row["policy_id"] == "baseline:random_legal"),
        ("simple_heuristic", lambda row: row["policy_id"] == "baseline:simple_heuristic"),
    ]
    for policy_id in sorted(summaries["by_policy"]):
        if not policy_id.startswith(("warm:", "scratch:")):
            continue
        for baseline_name, baseline_predicate in fixed:
            comparisons.append(paired_m5_comparison(
                rows,
                lambda row, policy_id=policy_id: row["policy_id"] == policy_id,
                baseline_predicate,
                label=f"{policy_id}_minus_{baseline_name}",
            ))
    return {"evidence_track": "M5 simulator only", "policy_summary": summaries,
            "paired_comparisons": comparisons,
            "limitations": ["1,500 rows are clustered by three training-seed pairs and 25 evaluation seeds.",
                            "Truncated scenarios remain censored and are excluded from terminal-only W/D/L.",
                            "RSK-014 remains an accepted historical source-reconstruction limitation."]}


def _trace_move_metrics(trace: dict[str, Any]) -> dict[str, Any]:
    initiated = 0
    rgb_verified = 0
    replies = 0
    policy_decisions = 0
    legal_actions = 0
    valid_legal_actions = 0
    latencies: dict[str, list[float]] = {
        "input_validation_latency_seconds": [],
        "policy_choose_move_latency_seconds": [],
        "adapter_total_latency_seconds": [],
    }
    for turn in trace.get("turns", []):
        if not isinstance(turn, dict):
            continue
        player_move = turn.get("player_move") if isinstance(turn.get("player_move"), dict) else {}
        if player_move.get("input_initiated") is True:
            initiated += 1
            rgb_verified += int(player_move.get("verified_from_rgb") is True)
        reply = turn.get("opponent_reply") if isinstance(turn.get("opponent_reply"), dict) else {}
        replies += int(reply.get("verified_from_rgb") is True)
        decision = turn.get("policy_decision") if isinstance(turn.get("policy_decision"), dict) else {}
        selected = decision.get("selected_uci")
        candidates = decision.get("legal_candidates_uci")
        if isinstance(selected, str):
            policy_decisions += 1
            if isinstance(candidates, list):
                legal_actions += 1
                valid_legal_actions += int(selected in candidates)
        for key in latencies:
            number = _finite_number(decision.get(key))
            if number is not None and number >= 0:
                latencies[key].append(number)
    terminal = trace.get("terminal", {})
    if not isinstance(terminal, dict):
        terminal = {}
    cursor = terminal.get("cursor_diagnostics", {})
    if not isinstance(cursor, dict):
        cursor = {}
    desyncs = cursor.get("stable_board_disagreements")
    if not isinstance(desyncs, int) or desyncs < 0:
        desyncs = int(terminal.get("runner_stop_category") == "CONTROLLER_BOARD_DESYNCHRONIZED")
    corrections = cursor.get("unexpected_displacements_corrected", 0)
    if not isinstance(corrections, int) or corrections < 0:
        corrections = 0
    shadow_terminal_diagnostic = None
    if terminal.get("runner_stop_category") == "POLICY_INPUT_INVALID":
        contexts = [turn.get("decision_input") for turn in trace.get("turns", [])
                    if isinstance(turn, dict) and isinstance(turn.get("decision_input"), dict)]
        if contexts:
            context = contexts[-1]
            history = context.get("history_uci")
            if not isinstance(history, list) or any(not isinstance(move, str) for move in history):
                raise AnalysisIntegrityError("policy-input terminal diagnostic lacks a valid ordered move history")
            board = chess.Board()
            try:
                for move in history:
                    board.push_uci(move)
            except ValueError as exc:
                raise AnalysisIntegrityError("policy-input terminal diagnostic has an illegal shadow history") from exc
            if board.fen(en_passant="fen") != context.get("fen"):
                raise AnalysisIntegrityError("policy-input terminal diagnostic FEN differs from its replayed history")
            shadow_outcome = board.outcome(claim_draw=False)
            if shadow_outcome is not None:
                shadow_terminal_diagnostic = {
                    "shadow_termination": shadow_outcome.termination.name,
                    "shadow_winner": "white" if shadow_outcome.winner is chess.WHITE else "black" if shadow_outcome.winner is chess.BLACK else None,
                    "shadow_legal_moves_available": board.legal_moves.count() > 0,
                    "ale_terminated": terminal.get("ale_terminated") is True,
                    "ale_truncated": terminal.get("ale_truncated") is True,
                    "ale_reward_total": terminal.get("ale_reward_total"),
                    "classification": "nonterminal_ALE_policy_stop; retain as incomplete, not a draw",
                }
    return {
        "initiated_player_moves": initiated,
        "rgb_verified_initiated_player_moves": rgb_verified,
        "verified_atari_replies": replies,
        "policy_decisions": policy_decisions,
        "legal_action_proposals": legal_actions,
        "legal_action_validations_passed": valid_legal_actions,
        "desynchronizations": desyncs,
        "cursor_corrections": corrections,
        "rgb_verified_move_rate": rgb_verified / initiated if initiated else None,
        "legal_action_validity_rate": valid_legal_actions / legal_actions if legal_actions else None,
        "policy_latencies": {key: _distribution(items) for key, items in latencies.items()},
        "policy_latency_samples": latencies,
        "stop_category": terminal.get("runner_stop_category"),
        "stop_reason": terminal.get("runner_stop_reason") or terminal.get("stop_reason"),
        "shadow_terminal_policy_input_diagnostic": shadow_terminal_diagnostic,
        "incomplete_final_move_category": terminal.get("incomplete_final_move_category"),
        "ale_frames": terminal.get("ale_frames"),
        "post_reset_action_frames": terminal.get("post_reset_action_frames"),
        "environment_steps": terminal.get("environment_steps"),
        "wall_seconds": terminal.get("wall_seconds"),
    }


def _distribution(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "median": None, "p95": None, "minimum": None, "maximum": None}
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "median": statistics.median(ordered),
        "p95": _quantile(ordered, 0.95),
        "minimum": ordered[0],
        "maximum": ordered[-1],
    }


def _artifact_tree_bytes(root: Path) -> int:
    if root.is_symlink() or not root.is_dir():
        raise AnalysisIntegrityError("campaign artifact parent is missing or unsafe")
    total = 0
    for path in root.rglob("*"):
        if path.is_symlink():
            raise AnalysisIntegrityError(f"symbolic link in campaign artifact parent: {path.name}")
        if path.is_file():
            total += path.stat().st_size
    return total


def _read_attempt_tree(attempt_dir: Path, *, repository_root: Path, expected_run_id: str,
                       expected_game_id: str, expected_policy_id: str, expected_seed: int,
                       attempt_record: dict[str, Any], source_identity: dict[str, Any] | None = None) -> dict[str, Any]:
    if attempt_dir.is_symlink() or not attempt_dir.is_dir():
        raise AnalysisIntegrityError("attempt artifact directory is missing or unsafe")
    attempt_path = attempt_dir / "attempt.json"
    if attempt_path.is_symlink() or not attempt_path.is_file():
        raise AnalysisIntegrityError("attempt.json is missing or unsafe")
    raw_record = json.loads(attempt_path.read_text(encoding="utf-8"))
    if raw_record != attempt_record:
        raise AnalysisIntegrityError(f"attempt.json differs from its hash-chained ledger record: {attempt_dir.name}")
    if (
        raw_record.get("run_id") != expected_run_id
        or raw_record.get("game_id") != expected_game_id
        or raw_record.get("policy_id") != expected_policy_id
        or raw_record.get("ale_seed") != expected_seed
        or raw_record.get("agent_color") != "white"
    ):
        raise AnalysisIntegrityError(f"attempt metadata differs from frozen M7 identity: {attempt_dir.name}")
    if raw_record.get("reset_observed") is not True:
        return {
            "attempt_id": raw_record["attempt_id"],
            "record_schema": raw_record.get("schema"),
            "game_id": expected_game_id,
            "policy_id": expected_policy_id,
            "ale_seed": expected_seed,
            "reset_observed": False,
            "outcome": "not_started",
            "recorded_outcome": raw_record.get("outcome"),
            "stop_reason": raw_record.get("stop_reason"),
            "metrics": {},
            "resource": {},
        }
    trace_path = attempt_dir / "trace.json"
    attempt_manifest_path = attempt_dir / "attempt-manifest.json"
    if trace_path.is_symlink() or attempt_manifest_path.is_symlink() or not trace_path.is_file() or not attempt_manifest_path.is_file():
        raise AnalysisIntegrityError(f"reset-observed attempt lacks a safe trace/manifest: {attempt_dir.name}")
    if sha256_file(trace_path) != raw_record.get("trace_sha256"):
        raise AnalysisIntegrityError(f"attempt trace file hash differs from ledger: {attempt_dir.name}")
    # M6's accepted immutable attempt schema calls this artifact_manifest_sha256;
    # the new M7 schema uses attempt_manifest_sha256. Read both without rewriting
    # either historical record.
    attempt_manifest_sha = raw_record.get("attempt_manifest_sha256")
    if attempt_manifest_sha is None:
        attempt_manifest_sha = raw_record.get("artifact_manifest_sha256")
    if sha256_file(attempt_manifest_path) != attempt_manifest_sha:
        raise AnalysisIntegrityError(f"attempt manifest file hash differs from ledger: {attempt_dir.name}")
    attempt_manifest = json.loads(attempt_manifest_path.read_text(encoding="utf-8"))
    expected_manifest = build_artifact_manifest(attempt_dir, exclude=("attempt.json", "attempt-manifest.json"))
    if attempt_manifest != expected_manifest:
        raise AnalysisIntegrityError(f"attempt-level artifact inventory mismatch: {attempt_dir.name}")
    trace_document = json.loads(trace_path.read_text(encoding="utf-8"))
    if trace_document.get("schema") != "videochess-m6-episode-trace/1.0":
        raise AnalysisIntegrityError(f"unsupported raw episode trace schema: {attempt_dir.name}")
    trace = trace_document.get("episode")
    if not isinstance(trace, dict) or trace.get("run_id") != expected_run_id or trace.get("game_id") != expected_game_id:
        raise AnalysisIntegrityError(f"trace run/game identity mismatch: {attempt_dir.name}")
    if trace.get("attempt_id") != raw_record.get("attempt_id") or trace.get("seed") != expected_seed:
        raise AnalysisIntegrityError(f"trace attempt/seed identity mismatch: {attempt_dir.name}")
    if trace.get("player_color") != "white" or trace.get("config", {}).get("env_id") != "ALE/VideoChess-v5":
        raise AnalysisIntegrityError(f"trace color/environment differs from frozen M7 contract: {attempt_dir.name}")
    if trace.get("runtime", {}).get("rom_sha256") != "d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7":
        raise AnalysisIntegrityError(f"trace ROM identity differs from frozen M7 contract: {attempt_dir.name}")
    verify_episode_trace(trace)
    outcome = classify_raw_ale_outcome(trace)
    record_outcome = raw_record.get("outcome")
    if not recorded_outcome_matches_raw(raw_record, outcome):
        raise AnalysisIntegrityError(f"raw ALE terminal classification differs from attempt record: {attempt_dir.name}")
    metrics = _trace_move_metrics(trace)
    terminal = trace.get("terminal", {})
    if (
        terminal.get("player_moves_attempted") != metrics["initiated_player_moves"]
        or terminal.get("verified_player_moves") != metrics["rgb_verified_initiated_player_moves"]
        or terminal.get("verified_atari_replies") != metrics["verified_atari_replies"]
    ):
        raise AnalysisIntegrityError(f"attempted/verified move counts disagree with raw turns: {attempt_dir.name}")
    if source_identity is not None:
        git = trace.get("git", {})
        if git.get("head") != source_identity.get("git_commit") or git.get("tree") != source_identity.get("git_tree"):
            raise AnalysisIntegrityError(f"trace source revision differs from the frozen run: {attempt_dir.name}")
    return {
        "attempt_id": raw_record["attempt_id"],
        "record_schema": raw_record.get("schema"),
        "game_id": expected_game_id,
        "policy_id": expected_policy_id,
        "ale_seed": expected_seed,
        "reset_observed": True,
        "outcome": outcome,
        "recorded_outcome": record_outcome,
        "ale_reward_white_perspective": terminal.get("ale_reward_total"),
        "score": 1.0 if outcome == "win" else 0.5 if outcome == "draw" else 0.0 if outcome == "loss" else None,
        "stop_reason": metrics["stop_reason"],
        "metrics": metrics,
        "attempt_manifest_sha256": attempt_manifest_sha,
        "trace_sha256": raw_record.get("trace_sha256"),
        "resource": {
            "peak_rss_bytes": raw_record.get("peak_rss_bytes"),
            "artifact_bytes": raw_record.get("artifact_bytes"),
            "wall_seconds": raw_record.get("wall_seconds"),
        },
    }


def _schedule_cell_status(attempt_rows: list[dict[str, Any]]) -> str:
    reset_rows = [row for row in attempt_rows if row.get("reset_observed")]
    if not reset_rows:
        return "not_started"
    if len(reset_rows) != 1:
        raise AnalysisIntegrityError("one frozen schedule cell has multiple observed resets")
    return str(reset_rows[0]["outcome"])


def _summarize_atari_cells(cells: list[dict[str, Any]]) -> dict[str, Any]:
    by_policy: dict[str, list[dict[str, Any]]] = {}
    for cell in cells:
        by_policy.setdefault(cell["policy_id"], []).append(cell)
    summaries: dict[str, Any] = {}
    for policy_id, group in sorted(by_policy.items()):
        outcomes = [row["outcome"] for row in group]
        counts = {
            "wins": outcomes.count("win"), "draws": outcomes.count("draw"), "losses": outcomes.count("loss"),
            "terminal_unknown": outcomes.count("terminal_unknown"), "truncated": outcomes.count("truncated"),
            "incomplete": outcomes.count("incomplete"), "not_started": outcomes.count("not_started"),
        }
        terminal_known = counts["wins"] + counts["draws"] + counts["losses"]
        scheduled = len(group)
        known_points = counts["wins"] + 0.5 * counts["draws"]
        unresolved = scheduled - terminal_known
        score_rows = [{"evaluation_seed": row["ale_seed"], "value": row["score"]}
                      for row in group if row.get("score") is not None]
        move_rows = [{"evaluation_seed": row["ale_seed"], "value": row["metrics"].get("rgb_verified_move_rate")}
                     for row in group if row.get("reset_observed") and row["metrics"].get("rgb_verified_move_rate") is not None]
        decision_count = sum(row["metrics"].get("legal_action_proposals", 0) for row in group if row.get("reset_observed"))
        valid_decisions = sum(row["metrics"].get("legal_action_validations_passed", 0) for row in group if row.get("reset_observed"))
        initiated = sum(row["metrics"].get("initiated_player_moves", 0) for row in group if row.get("reset_observed"))
        verified = sum(row["metrics"].get("rgb_verified_initiated_player_moves", 0) for row in group if row.get("reset_observed"))
        replies = sum(row["metrics"].get("verified_atari_replies", 0) for row in group if row.get("reset_observed"))
        latency_samples: dict[str, list[float]] = {
            "input_validation_latency_seconds": [],
            "policy_choose_move_latency_seconds": [],
            "adapter_total_latency_seconds": [],
        }
        for row in group:
            for key, items in row.get("metrics", {}).get("policy_latency_samples", {}).items():
                latency_samples.setdefault(key, []).extend(items)
        stop_categories: dict[str, int] = {}
        stop_reasons: dict[str, int] = {}
        for row in group:
            category = row.get("metrics", {}).get("stop_category")
            reason = row.get("metrics", {}).get("incomplete_final_move_category")
            if category:
                stop_categories[category] = stop_categories.get(category, 0) + 1
            if reason:
                stop_reasons[reason] = stop_reasons.get(reason, 0) + 1
        process_rows = [attempt.get("resource", {}) for cell in group for attempt in cell.get("attempts", [])]
        summaries[policy_id] = {
            **counts,
            "scheduled": scheduled,
            "started_after_ale_reset": scheduled - counts["not_started"],
            "terminal_attempts": terminal_known + counts["terminal_unknown"],
            "terminal_attempt_rate": (terminal_known + counts["terminal_unknown"]) / scheduled if scheduled else None,
            "known_terminal_result_rate": terminal_known / scheduled if scheduled else None,
            "terminal_known_games": terminal_known,
            "terminal_wdl_denominator": terminal_known,
            "win_rate_terminal_known": counts["wins"] / terminal_known if terminal_known else None,
            "draw_rate_terminal_known": counts["draws"] / terminal_known if terminal_known else None,
            "loss_rate_terminal_known": counts["losses"] / terminal_known if terminal_known else None,
            "terminal_only_game_score": _game_score(counts["wins"], counts["draws"], terminal_known),
            "game_score_denominator": terminal_known,
            "terminal_completion_rate": (terminal_known + counts["terminal_unknown"]) / scheduled if scheduled else None,
            "rgb_verified_initiated_moves": verified,
            "initiated_moves": initiated,
            "rgb_verified_move_rate": verified / initiated if initiated else None,
            "verified_atari_replies": replies,
            "legal_action_validation_passed": valid_decisions,
            "legal_action_proposals": decision_count,
            "legal_action_validity_rate": valid_decisions / decision_count if decision_count else None,
            "desynchronizations": sum(row["metrics"].get("desynchronizations", 0) for row in group if row.get("reset_observed")),
            "cursor_corrections": sum(row["metrics"].get("cursor_corrections", 0) for row in group if row.get("reset_observed")),
            "attempt_process_count": sum(row.get("attempt_process_count", 0) for row in group),
            "stop_category_counts": stop_categories,
            "incomplete_final_move_category_counts": stop_reasons,
            "policy_latency_distributions": {key: _distribution(items) for key, items in latency_samples.items()},
            "resource_distributions": {
                key: _distribution([float(item[key]) for item in process_rows if _finite_number(item.get(key)) is not None])
                for key in ("process_cpu_seconds", "process_cpu_utilization_one_core_percent",
                            "process_cpu_utilization_machine_percent", "process_peak_rss_bytes",
                            "observed_process_wall_seconds", "attempt_trace_peak_rss_bytes",
                            "campaign_artifact_bytes_after_attempt", "free_disk_bytes_after_attempt")
            },
            "ale_frame_distribution": _distribution([
                float(row["metrics"]["ale_frames"]) for row in group
                if row.get("reset_observed") and _finite_number(row.get("metrics", {}).get("ale_frames")) is not None
            ]),
            "score_interval_by_ale_seed": (
                evaluation_seed_bootstrap(score_rows) if len(score_rows) == scheduled else {
                    "mean": sum(row["value"] for row in score_rows) / len(score_rows) if score_rows else None,
                    "ci_95_seed_cluster": None, "iterations": 10000, "bootstrap_seed": 20261290,
                    "evaluation_seed_clusters": len(score_rows), "scheduled_seed_blocks": scheduled,
                    "status": "unavailable_incomplete_or_terminal_unknown_seed_blocks",
                }
            ),
            "move_rate_interval_by_ale_seed": (
                evaluation_seed_bootstrap(move_rows) if len(move_rows) == scheduled else {
                    "mean": sum(row["value"] for row in move_rows) / len(move_rows) if move_rows else None,
                    "ci_95_seed_cluster": None, "iterations": 10000, "bootstrap_seed": 20261290,
                    "evaluation_seed_clusters": len(move_rows), "scheduled_seed_blocks": scheduled,
                    "status": "unavailable_missing_or_undefined_move_rate_blocks",
                }
            ),
            "full_schedule_score_bounds": {
                "denominator": scheduled,
                "lower_all_unresolved_are_losses": known_points / scheduled if scheduled else None,
                "upper_all_unresolved_are_wins": (known_points + unresolved) / scheduled if scheduled else None,
                "unresolved_cells": unresolved,
                "imputation_performed": False,
            },
            "per_seed_cells": [
                {"ale_seed": row["ale_seed"], "outcome": row["outcome"], "score": row.get("score"),
                 "metrics": {key: value for key, value in row.get("metrics", {}).items() if key != "policy_latency_samples"}}
                for row in sorted(group, key=lambda item: item["ale_seed"])
            ],
        }
    return {"scheduled_cells": len(cells), "policy_count": len(summaries), "by_policy": summaries}


def _reconstruct_atari_run(
    run_dir: str | Path,
    *,
    expected_run_id: str,
    expected_config_sha256: str,
    expected_root_manifest_sha256: str,
    repository_root: str | Path,
    expected_source_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify a whole raw run tree and independently reconstruct its scheduled cells."""
    supplied_root = Path(run_dir).expanduser()
    if supplied_root.is_symlink():
        raise AnalysisIntegrityError("ALE run root must not be a symbolic link")
    root = supplied_root.resolve(strict=True)
    if not root.is_dir():
        raise AnalysisIntegrityError("ALE run root is missing or unsafe")
    manifest_path = root / "artifact-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file() or sha256_file(manifest_path) != expected_root_manifest_sha256:
        raise AnalysisIntegrityError(f"accepted ALE root manifest hash mismatch: {expected_run_id}")
    root_manifest = verify_artifact_manifest(root)
    run_manifest_path = root / "run-manifest.json"
    ledger_path = root / "events.jsonl"
    if run_manifest_path.is_symlink() or ledger_path.is_symlink() or not run_manifest_path.is_file() or not ledger_path.is_file():
        raise AnalysisIntegrityError("ALE raw run is missing its manifest or ledger")
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    if run_manifest.get("run_id") != expected_run_id or run_manifest.get("configuration_sha256") != expected_config_sha256:
        raise AnalysisIntegrityError(f"ALE run manifest identity mismatch: {expected_run_id}")
    schedule = run_manifest.get("seed_schedule")
    attempt_limit = run_manifest.get("attempt_limit", run_manifest.get("scheduled_attempt_count"))
    if not isinstance(schedule, list) or not schedule or attempt_limit != len(schedule):
        raise AnalysisIntegrityError("ALE run manifest has a malformed frozen schedule")
    game_map = {row.get("game_id"): row for row in schedule if isinstance(row, dict)}
    if len(game_map) != len(schedule) or any(not isinstance(key, str) for key in game_map):
        raise AnalysisIntegrityError("ALE run schedule contains duplicate or malformed game identities")
    recorded_source = {key: run_manifest.get(key) for key in ("git_commit", "git_tree", "source_bundle_sha256")}
    if any(not isinstance(value, str) or not value for value in recorded_source.values()):
        raise AnalysisIntegrityError("ALE run manifest lacks a complete source identity")
    trace_source_identity = expected_source_identity or recorded_source
    if any(recorded_source.get(key) != trace_source_identity.get(key) for key in recorded_source):
        raise AnalysisIntegrityError("ALE source identity differs from the expected frozen identity")
    run_started_hash = None
    started: dict[str, dict[str, Any]] = {}
    finished: dict[str, dict[str, Any]] = {}
    reset_ids: set[str] = set()
    reset_games: set[str] = set()
    resource_rows: list[dict[str, Any]] = []
    retry_count = 0
    for event in iter_verified_hash_chain(ledger_path, expected_run_id=expected_run_id):
        kind = event["event_type"]
        payload = event["payload"]
        attempt_id = payload.get("attempt_id")
        if kind == "run_started":
            if run_started_hash is not None:
                raise AnalysisIntegrityError("ALE ledger contains multiple run_started records")
            run_started_hash = payload.get("run_manifest_sha256")
            if payload.get("schedule") != schedule:
                raise AnalysisIntegrityError("ALE ledger schedule differs from the frozen run manifest")
        elif kind == "attempt_started":
            if not isinstance(attempt_id, str) or attempt_id in started:
                raise AnalysisIntegrityError("ALE ledger contains malformed/duplicate attempt starts")
            row = game_map.get(payload.get("game_id"))
            if row is None or payload.get("policy_id") != row.get("policy_id") or payload.get("ale_seed") != row.get("ale_seed"):
                raise AnalysisIntegrityError("ALE attempt start is outside the frozen schedule")
            started[attempt_id] = payload
        elif kind == "ale_reset_observed":
            if not isinstance(attempt_id, str) or attempt_id not in started:
                raise AnalysisIntegrityError("ALE reset has no preceding attempt start")
            game_id = payload.get("game_id")
            if game_id in reset_games:
                raise AnalysisIntegrityError("one ALE schedule cell has multiple observed resets")
            reset_games.add(game_id)
            reset_ids.add(attempt_id)
        elif kind == "attempt_finished":
            if not isinstance(attempt_id, str) or attempt_id not in started or attempt_id in finished:
                raise AnalysisIntegrityError("ALE attempt completion lacks one unique start")
            record = payload.get("attempt_record")
            if not isinstance(record, dict) or record.get("attempt_id") != attempt_id:
                raise AnalysisIntegrityError("ALE attempt completion record is malformed")
            finished[attempt_id] = record
        elif kind == "attempt_resource_observed":
            resource_rows.append(payload)
        elif kind == "process_start_retry":
            if payload.get("action_attempted") is not False:
                raise AnalysisIntegrityError("recorded startup retry occurred after an ALE action")
            retry_count += 1
    if run_started_hash != sha256_file(run_manifest_path):
        raise AnalysisIntegrityError("ALE run manifest hash differs from ledger run_started identity")
    if set(started) != set(finished):
        raise AnalysisIntegrityError("ALE ledger has an unfinished process; resume/recover before analysis")
    if len(reset_games) != len(reset_ids) or retry_count > 1:
        raise AnalysisIntegrityError("ALE reset or startup-retry accounting is inconsistent")

    repo_root = Path(repository_root).resolve()
    attempt_root = root / "attempts"
    expected_attempt_dirs = {_slug(attempt_id) for attempt_id in started}
    if attempt_root.exists():
        for child in attempt_root.iterdir():
            if child.is_symlink() or not child.is_dir() or child.name not in expected_attempt_dirs:
                raise AnalysisIntegrityError("unregistered/unsafe directory in ALE attempt tree")

    attempts_by_game: dict[str, list[dict[str, Any]]] = {}
    resources_by_attempt = {row.get("attempt_id"): row for row in resource_rows if isinstance(row.get("attempt_id"), str)}
    if len(resources_by_attempt) != len(resource_rows):
        raise AnalysisIntegrityError("ALE runtime resource ledger has duplicate or malformed attempt identities")
    for attempt_id, record in finished.items():
        start = started[attempt_id]
        game_id = str(start["game_id"])
        scheduled = game_map[game_id]
        if record.get("game_id") != game_id or record.get("policy_id") != scheduled.get("policy_id") or record.get("ale_seed") != scheduled.get("ale_seed"):
            raise AnalysisIntegrityError("attempt record differs from its scheduled ledger identity")
        attempt_dir = attempt_root / _slug(attempt_id)
        reconstructed = _read_attempt_tree(
            attempt_dir,
            repository_root=repo_root,
            expected_run_id=expected_run_id,
            expected_game_id=game_id,
            expected_policy_id=str(scheduled["policy_id"]),
            expected_seed=int(scheduled["ale_seed"]),
            attempt_record=record,
            source_identity=trace_source_identity,
        )
        reconstructed["attempt_id"] = attempt_id
        reconstructed["execution_order"] = int(scheduled.get("slot", scheduled.get("attempt_index", -1)))
        resource_row = resources_by_attempt.get(attempt_id)
        if resource_row is not None:
            if resource_row.get("game_id") != game_id or resource_row.get("policy_id") != scheduled.get("policy_id") or resource_row.get("ale_seed") != scheduled.get("ale_seed"):
                raise AnalysisIntegrityError("ALE runtime resource record differs from its scheduled attempt")
            reconstructed["resource"] = resource_row
        attempts_by_game.setdefault(game_id, []).append(reconstructed)

    cells: list[dict[str, Any]] = []
    for slot, scheduled in enumerate(schedule):
        game_id = scheduled["game_id"]
        attempts = attempts_by_game.get(game_id, [])
        reset_attempts = [row for row in attempts if row.get("reset_observed")]
        if len(reset_attempts) > 1:
            raise AnalysisIntegrityError("multiple reset attempts are recorded for one scheduled ALE cell")
        selected = reset_attempts[0] if reset_attempts else (attempts[-1] if attempts else None)
        cells.append({
            "slot": scheduled.get("slot", slot),
            "game_id": game_id,
            "policy_id": scheduled["policy_id"],
            "ale_seed": int(scheduled["ale_seed"]),
            "outcome": selected["outcome"] if selected else "not_started",
            "reset_observed": bool(reset_attempts),
            "attempt_process_count": len(attempts),
            "attempts": attempts,
            "score": selected.get("score") if selected else None,
            "metrics": selected.get("metrics", {}) if selected else {},
        })
    if len(cells) != len(schedule) or len({row["game_id"] for row in cells}) != len(schedule):
        raise AnalysisIntegrityError("ALE reconstruction omitted or duplicated a scheduled cell")
    return {
        "run_id": expected_run_id,
        "run_manifest_sha256": sha256_file(run_manifest_path),
        "root_artifact_manifest_sha256": sha256_file(manifest_path),
        "configuration_sha256": expected_config_sha256,
        "scheduled_attempts": len(schedule),
        "attempt_processes_started": len(started),
        "reset_observed_cells": len(reset_games),
        "startup_retries": retry_count,
        "resource_observations": resource_rows,
        "cells": cells,
        "policy_summary": _summarize_atari_cells(cells),
        "runtime_identity": run_manifest.get("runtime_construction") or run_manifest.get("ale_runtime_construction"),
        "source_identity": {key: run_manifest.get(key) for key in ("git_commit", "git_tree", "source_bundle_sha256")},
        "artifact_bytes": root_manifest.get("total_bytes"),
    }


def _m7_comparisons(config: dict[str, Any], cells: list[dict[str, Any]]) -> dict[str, Any]:
    by_cell = {(row["policy_id"], row["ale_seed"]): row for row in cells}
    roster = config["accepted_inputs"]["m5"]["policies"]
    rl_by_seed = {(row["arm"], int(row["training_seed"])): row["policy_id"] for row in roster}
    baselines = ("m4-behavior-only-seed-20261024", "random-legal", "simple-heuristic")
    fixed_policy_comparisons: list[dict[str, Any]] = []
    for (arm, train_seed), rl_policy in sorted(rl_by_seed.items()):
        for baseline in baselines:
            paired: list[dict[str, Any]] = []
            matched = censored = 0
            for ale_seed in ALE_SEEDS:
                rl = by_cell[(rl_policy, ale_seed)]
                base = by_cell[(baseline, ale_seed)]
                if rl["score"] is None or base["score"] is None:
                    censored += 1
                    continue
                matched += 1
                paired.append({"training_seed": train_seed, "evaluation_seed": ale_seed,
                               "difference": rl["score"] - base["score"]})
            fixed_policy_comparisons.append({
                "comparison": f"{rl_policy}_minus_{baseline}",
                "arm": arm,
                "training_seed": train_seed,
                "matched_terminal_seed_blocks": matched,
                "censored_or_unknown_seed_blocks": censored,
                "paired_cluster_bootstrap": paired_interval_with_censoring(
                    paired, scheduled_pairs=10, censored_pairs=censored,
                ),
                "estimand": "terminal-only ALE score difference on matched common ALE seeds",
                "generalizes_across_training_seeds": False,
            })

    warm_scratch: list[dict[str, Any]] = []
    per_seed: list[dict[str, Any]] = []
    for seed in (20261104, 20261105, 20261106):
        warm = rl_by_seed[("warm", seed)]
        scratch = rl_by_seed[("scratch", seed)]
        seed_rows: list[dict[str, Any]] = []
        censored = 0
        for ale_seed in ALE_SEEDS:
            a = by_cell[(warm, ale_seed)]
            b = by_cell[(scratch, ale_seed)]
            if a["score"] is None or b["score"] is None:
                censored += 1
                continue
            seed_rows.append({"training_seed": seed, "evaluation_seed": ale_seed,
                              "difference": a["score"] - b["score"]})
        warm_scratch.extend(seed_rows)
        per_seed.append({
            "training_seed": seed,
            "matched_terminal_seed_blocks": len(seed_rows),
            "censored_or_unknown_seed_blocks": censored,
            "mean_warm_minus_scratch": sum(row["difference"] for row in seed_rows) / len(seed_rows) if seed_rows else None,
        })
    baseline_pairs = []
    for left, right in ((baselines[0], baselines[1]), (baselines[0], baselines[2]), (baselines[1], baselines[2])):
        paired = [
            {"training_seed": "fixed", "evaluation_seed": ale_seed,
             "difference": by_cell[(left, ale_seed)]["score"] - by_cell[(right, ale_seed)]["score"]}
            for ale_seed in ALE_SEEDS
            if by_cell[(left, ale_seed)]["score"] is not None and by_cell[(right, ale_seed)]["score"] is not None
        ]
        baseline_pairs.append({
            "comparison": f"{left}_minus_{right}",
            "paired_cluster_bootstrap": paired_interval_with_censoring(
                paired, scheduled_pairs=10, censored_pairs=10 - len(paired),
            ),
        })
    return {
        "rl_policy_vs_baseline": fixed_policy_comparisons,
        "warm_vs_scratch_post_rl": {
            "matched_terminal_training_seed_by_ale_seed_cells": len(warm_scratch),
            "censored_or_unknown_cells": 30 - len(warm_scratch),
            "crossed_training_seed_and_ale_seed_bootstrap": paired_interval_with_censoring(
                warm_scratch, scheduled_pairs=30, censored_pairs=30 - len(warm_scratch),
            ),
            "per_training_seed_effects": per_seed,
            "training_seed_pairs": 3,
            "severe_training_replication_limitation": True,
        },
        "baseline_pairs": baseline_pairs,
    }


def _load_m4_imitation(m4_root: str | Path) -> dict[str, Any]:
    supplied_root = Path(m4_root).expanduser()
    if supplied_root.is_symlink():
        raise AnalysisIntegrityError("accepted M4 artifact root must not be a symbolic link")
    root = supplied_root.resolve(strict=True)
    if not root.is_dir():
        raise AnalysisIntegrityError("accepted M4 artifact root is missing or unsafe")
    from videochess_rl.model.checkpoint import verify_artifact_manifest

    verify_artifact_manifest(root)
    manifest_path = root / "artifact_manifest.json"
    if sha256_file(manifest_path) != M4_ROOT_MANIFEST_SHA256:
        raise AnalysisIntegrityError("accepted M4 root manifest identity changed")
    test_path = root / "test_evaluation.json"
    if test_path.is_symlink() or not test_path.is_file():
        raise AnalysisIntegrityError("accepted M4 test evaluation record is missing/unsafe")
    test_record = json.loads(test_path.read_text(encoding="utf-8"))
    metrics = test_record.get("metrics", {})
    if (
        test_record.get("selected_seed") != 20261024
        or test_record.get("selected_epoch") != 11
        or metrics.get("split") != "test"
        or metrics.get("examples") != 2057
    ):
        raise AnalysisIntegrityError("accepted M4 test-evaluation identity differs from the frozen report")
    return {
        "evidence_track": "M4 supervised imitation only",
        "run_id": "m4-behavior-20261027-r4",
        "training_seed": test_record["selected_seed"],
        "selected_epoch": test_record["selected_epoch"],
        "checkpoint_sha256": test_record["checkpoint_sha256"],
        "root_manifest_sha256": sha256_file(manifest_path),
        "test_evaluation_record_sha256": sha256_file(test_path),
        "positions": metrics["examples"],
        "legal_candidate_evaluations": metrics.get("candidate_evaluations"),
        "legal_top1_accuracy": metrics.get("top1_accuracy"),
        "legal_top3_accuracy": metrics.get("top3_accuracy"),
        "mrr": metrics.get("mrr"),
        "metric_interpretation": "agreement with played historical moves; not W/D/L, Atari performance, RL improvement, chess strength, or Elo",
        "raw_position_predictions_available": False,
        "raw_record_limitation": "the accepted M4 root contains its machine-readable aggregate test_evaluation.json, not per-position prediction rows",
    }


def analyze_m7_run(run_dir: str | Path, *, config_path: str | Path) -> dict[str, Any]:
    config = load_frozen_config(config_path)
    supplied_root = Path(run_dir).expanduser()
    if supplied_root.is_symlink():
        raise AnalysisIntegrityError("M7 raw run root must not be a symbolic link")
    root = supplied_root.resolve(strict=True)
    manifest_path = root / "run-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise AnalysisIntegrityError("M7 run manifest is missing/unsafe")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("protocol_id") != config["protocol_id"]
        or manifest.get("configuration_sha256") != sha256_file(config_path)
        or manifest.get("schedule_sha256") != config["research_design"]["schedule_sha256"]
        or manifest.get("seed_schedule") != config["research_design"]["schedule"]
        or manifest.get("run_id") != root.name
    ):
        raise AnalysisIntegrityError("M7 run manifest differs from its frozen protocol/configuration/schedule")
    expected_source = {key: manifest.get(key) for key in ("git_commit", "git_tree", "source_bundle_sha256")}
    from videochess_rl.m7.campaign import run_identity

    expected_run_id = run_identity(
        expected_source,
        sha256_file(config_path),
        config["research_design"]["schedule_sha256"],
        config["run_id_prefix"],
    )
    if manifest.get("run_id") != expected_run_id:
        raise AnalysisIntegrityError("M7 run ID does not match its source/configuration/schedule identity")
    reconstructed = _reconstruct_atari_run(
        root,
        expected_run_id=str(manifest["run_id"]),
        expected_config_sha256=sha256_file(config_path),
        expected_root_manifest_sha256=sha256_file(root / "artifact-manifest.json"),
        repository_root=Path(__file__).resolve().parents[2],
        expected_source_identity=expected_source,
    )
    if reconstructed["scheduled_attempts"] != 90 or reconstructed["policy_summary"]["policy_count"] != 9:
        raise AnalysisIntegrityError("M7 run does not reconstruct to the complete 90-cell/nine-policy schedule")
    summary_path = root / "summary.json"
    if summary_path.is_symlink() or not summary_path.is_file():
        raise AnalysisIntegrityError("M7 summary is missing or unsafe")
    campaign_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    accounting = campaign_summary.get("schedule_accounting", {})
    accounting_cells = accounting.get("cells", [])
    if (
        campaign_summary.get("schema") != "videochess-m7-campaign-summary/1.0"
        or campaign_summary.get("run_id") != manifest["run_id"]
        or campaign_summary.get("configuration_sha256") != sha256_file(config_path)
        or campaign_summary.get("schedule_sha256") != config["research_design"]["schedule_sha256"]
        or campaign_summary.get("scheduled_attempt_count") != 90
        or accounting.get("scheduled_cells") != 90
        or accounting.get("all_cells_retained") is not True
        or len(accounting_cells) != 90
        or campaign_summary.get("process_resource_observations") != reconstructed["resource_observations"]
    ):
        raise AnalysisIntegrityError("M7 summary identity/resource rows disagree with the verified raw run")
    reset_count = 0
    process_started_count = 0
    for raw_cell, summary_cell in zip(reconstructed["cells"], accounting_cells, strict=True):
        if (
            summary_cell.get("game_id") != raw_cell["game_id"]
            or summary_cell.get("policy_id") != raw_cell["policy_id"]
            or summary_cell.get("ale_seed") != raw_cell["ale_seed"]
            or summary_cell.get("slot") != raw_cell["slot"]
            or summary_cell.get("scheduled") is not True
            or summary_cell.get("reset_observed") is not raw_cell["reset_observed"]
            or summary_cell.get("started") is not raw_cell["reset_observed"]
            or summary_cell.get("attempt_process_count") != raw_cell["attempt_process_count"]
            or summary_cell.get("attempt_process_started") is not bool(raw_cell["attempt_process_count"])
        ):
            raise AnalysisIntegrityError("M7 summary schedule cell differs from independent ledger reconstruction")
        if raw_cell["attempts"]:
            selected_attempt = next(
                (row for row in raw_cell["attempts"] if row.get("reset_observed")),
                raw_cell["attempts"][-1],
            )
            if summary_cell.get("selected_attempt_status") != normalized_recorded_outcome(selected_attempt):
                raise AnalysisIntegrityError("M7 summary attempt status differs from its verified raw attempt record")
        elif summary_cell.get("selected_attempt_status") != "not_started":
            raise AnalysisIntegrityError("M7 summary labels an unattempted cell as an attempt outcome")
        reset_count += int(raw_cell["reset_observed"])
        process_started_count += int(bool(raw_cell["attempt_process_count"]))
    if (
        accounting.get("started_cells") != reset_count
        or accounting.get("reset_observed_cells") != reset_count
        or accounting.get("not_started_cells") != 90 - reset_count
        or accounting.get("attempt_process_started_cells") != process_started_count
    ):
        raise AnalysisIntegrityError("M7 summary schedule totals differ from independent raw reconstruction")
    artifact_parent_total_bytes = _artifact_tree_bytes(root.parent)
    if artifact_parent_total_bytes > int(config["resource_limits"]["maximum_campaign_artifact_bytes"]):
        raise AnalysisIntegrityError("final M7 artifact parent exceeds the authorized 8-GiB ceiling")
    comparisons = _m7_comparisons(config, reconstructed["cells"])
    return {
        "run_id": reconstructed["run_id"],
        "protocol_id": config["protocol_id"],
        "configuration_sha256": sha256_file(config_path),
        "schedule_sha256": config["research_design"]["schedule_sha256"],
        "source_identity": reconstructed["source_identity"],
        "raw_run_manifest_sha256": reconstructed["run_manifest_sha256"],
        "raw_artifact_manifest_sha256": reconstructed["root_artifact_manifest_sha256"],
        "scheduled_attempt_count": reconstructed["scheduled_attempts"],
        "attempt_processes_started": reconstructed["attempt_processes_started"],
        "reset_observed_cells": reconstructed["reset_observed_cells"],
        "policy_summary": reconstructed["policy_summary"],
        "paired_comparisons": comparisons,
        "resource_observations": reconstructed["resource_observations"],
        "artifact_bytes": reconstructed["artifact_bytes"],
        "artifact_parent_total_bytes_after_finalization": artifact_parent_total_bytes,
        "resource_stop_reason": campaign_summary.get("resource_stop_reason"),
        "resource_limits": manifest.get("resource_limits"),
        "episode_limits": manifest.get("episode_limits"),
        "evaluation_identity": {
            key: config["ale_profile"][key]
            for key in (
                "environment_id", "rom_sha256", "agent_color", "mode", "difficulty", "observation_type",
                "frameskip", "repeat_action_probability", "registered_default_max_num_frames_per_episode",
                "effective_max_num_frames_per_episode", "runner_maximum_post_reset_action_frames",
            )
        } | {"ale_evaluation_seeds": config["research_design"]["ale_evaluation_seeds"]},
        "campaign_resources": {
            "pre_campaign": manifest.get("campaign_resource_snapshot_before_first_attempt"),
            "campaign_artifact_bytes_after": campaign_summary.get("campaign_artifact_bytes"),
            "run_manifest_inventory_bytes_excluding_manifest": reconstructed["artifact_bytes"],
            "artifact_parent_total_bytes_after_finalization": artifact_parent_total_bytes,
            "free_disk_bytes_after": campaign_summary.get("free_disk_bytes_after_campaign"),
            "peak_process_rss_bytes": campaign_summary.get("maximum_process_rss_bytes"),
            "aggregate_process_cpu_seconds": campaign_summary.get("aggregate_process_cpu_seconds"),
            "aggregate_observed_process_wall_seconds": campaign_summary.get("aggregate_observed_process_wall_seconds"),
            "campaign_observed_session_wall_seconds": campaign_summary.get("campaign_observed_session_wall_seconds"),
            "setup_seconds_before_first_attempt": campaign_summary.get("setup_seconds_before_first_attempt"),
            "resume_recovery_seconds": campaign_summary.get("resume_recovery_seconds"),
            "resource_stop_reason": campaign_summary.get("resource_stop_reason"),
        },
        "summary_reconciliation": {
            "summary_matches_verified_schedule": True,
            "summary_resource_rows_match_hash_chained_ledger": True,
            "reset_observed_cells_from_raw": reset_count,
            "attempt_process_started_cells_from_raw": process_started_count,
        },
        "runtime_identity": reconstructed["runtime_identity"],
        "confirmatory_endpoints": config["primary_metrics"],
        "elo_disposition": config["elo_disposition"],
    }


def analyze_all_tracks(
    *,
    config_path: str | Path,
    m7_run_dir: str | Path,
    m4_artifact_root: str | Path,
    m5_artifact_root: str | Path,
    m6_v1_root: str | Path,
    m6_v2_root: str | Path,
) -> dict[str, Any]:
    """Reconstruct all five evidence tracks without pooling incompatible runs."""
    config = load_frozen_config(config_path)
    m5_rows, m5_input = load_m5_raw_rows(m5_artifact_root)
    m5_analysis = analyze_m5(m5_rows)
    m4_analysis = _load_m4_imitation(m4_artifact_root)

    m6_ids = config["accepted_inputs"]["m6"]
    m6_v1 = _reconstruct_atari_run(
        m6_v1_root,
        expected_run_id=m6_ids["v1"]["run_id"],
        expected_config_sha256=m6_ids["v1"]["configuration_sha256"],
        expected_root_manifest_sha256=m6_ids["v1"]["root_manifest_sha256"],
        repository_root=Path(__file__).resolve().parents[2],
    )
    m6_v2 = _reconstruct_atari_run(
        m6_v2_root,
        expected_run_id=m6_ids["v2"]["run_id"],
        expected_config_sha256=m6_ids["v2"]["configuration_sha256"],
        expected_root_manifest_sha256=m6_ids["v2"]["root_manifest_sha256"],
        repository_root=Path(__file__).resolve().parents[2],
    )
    if (m6_v1["scheduled_attempts"], m6_v2["scheduled_attempts"]) != (35, 20):
        raise AnalysisIntegrityError("historical M6 v1/v2 schedules do not match their separately frozen identities")
    if m6_v1["run_id"] == m6_v2["run_id"] or m6_v1["root_artifact_manifest_sha256"] == m6_v2["root_artifact_manifest_sha256"]:
        raise AnalysisIntegrityError("historical M6 v1 and v2 identities were incorrectly collapsed")

    m7 = analyze_m7_run(m7_run_dir, config_path=config_path)
    if m7["policy_summary"]["policy_count"] != 9 or m7["scheduled_attempt_count"] != 90:
        raise AnalysisIntegrityError("M7 analysis did not retain the complete authorized policy × seed schedule")

    return {
        "schema": "videochess-m7-all-track-analysis/1.0",
        "analysis_protocol": config["protocol_id"],
        "scientific_basis": config["scientific_basis"],
        "analysis_created_from_raw_records": True,
        "bootstrap": {"resamples": 10000, "seed": 20261290, "interval": "95% cluster bootstrap"},
        "tracks": {
            "M4_supervised_imitation": m4_analysis,
            "M5_simulator_Double_DQN": {"input_identity": m5_input, **m5_analysis},
            "M6_stage3_v1_ALE": m6_v1,
            "M6_stage3_v2_ALE": m6_v2,
            "M7_option_B_ALE": m7,
        },
        "elo": {
            "disposition": config["elo_disposition"],
            "calibrated_opponent_pool_approved": False,
            "terminal_match_schedule_minimum_met": False,
            "rating_anchor_approved": False,
            "rating_model_approved": False,
            "elo_value": None,
        },
        "cross_track_rules": {
            "M4_accuracy_is_not_game_score": True,
            "M5_simulator_is_not_ALE": True,
            "M6_v1_and_v2_are_not_pooled": True,
            "M7_ALE_is_not_pooled_with_historical_M6": True,
            "evaluation_seeds_are_not_training_replications": True,
            "incomplete_attempts_are_not_draws": True,
        },
        "limitations": [
            "Only three accepted M5 training-seed pairs exist; this limits inference about the training method.",
            "M7 uses one White-side ALE profile and one built-in VideoChess opponent.",
            "M6 v1, M6 v2, and M7 use distinct schedule/horizon identities and are descriptive across protocols.",
            "M4 accepted test evidence is an aggregate machine-readable record; no per-position predictions are retained in the accepted M4 root.",
            "RSK-014 remains the accepted M5 historical source-reconstruction limitation.",
            "PM6-F06 remains an immutable M6 v2 metadata erratum; original v2 manifests are unchanged.",
        ],
    }
