#!/usr/bin/env python3
"""Supplementary paired bootstrap that retains observed 400-decision rewards."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from videochess_rl.rl.cli import ARTIFACT_ROOT, CONFIG_PATH, sha_file
from videochess_rl.rl.evaluate import (crossed_cluster_bootstrap, evaluation_seed_cluster_bootstrap,
    paired_capped_reward_differences, planned_scenarios)
from videochess_rl.rl.evaluation_journal import recover_policy_attempt_rows

def _policy_slug(policy_id: str) -> str:
    return hashlib.sha256(policy_id.encode()).hexdigest()[:16]


def analyze(artifact_root: Path = ARTIFACT_ROOT, *, iterations: int = 10000) -> dict[str, Any]:
    report_path = artifact_root / "evaluation/evaluation-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not report.get("schedule_complete") or report.get("executed_games") != 1500:
        raise RuntimeError("sensitivity analysis requires the completed official 1,500-game schedule")
    expected_scenarios = {(x["evaluation_seed"], x["opponent_id"], x["agent_color"])
                          for x in planned_scenarios()}
    rows_by_policy: dict[str, list[dict[str, Any]]] = {}
    diagnostics: dict[str, list[dict[str, Any]]] = {}
    for policy in report["per_policy"]:
        policy_id = policy["policy_id"]
        rows, journal_diagnostics = recover_policy_attempt_rows(
            artifact_root / "evaluation" / _policy_slug(policy_id), policy_id)
        done = [row for row in rows if row.get("status") == "completed_game"]
        keys = {(int(row["evaluation_seed"]), row["opponent_id"], row["agent_color"]) for row in done}
        if len(done) != 100 or len(rows) != 100 or keys != expected_scenarios or journal_diagnostics:
            raise ValueError(f"policy {policy_id} lacks 100 verified unique scenarios: {journal_diagnostics}")
        rows_by_policy[policy_id] = done
        diagnostics[policy_id] = journal_diagnostics

    training_seeds = tuple(json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["training"]["paired_seeds"])
    core_specs = []
    for stage in ("pre_rl", "post_rl"):
        core_specs.append((f"warm_vs_scratch_{stage}",
            [(f"warm:{seed}:{stage}", f"scratch:{seed}:{stage}", seed) for seed in training_seeds]))
    for arm in ("warm", "scratch"):
        core_specs.append((f"{arm}_pre_vs_post",
            [(f"{arm}:{seed}:post_rl", f"{arm}:{seed}:pre_rl", seed) for seed in training_seeds]))

    core: list[dict[str, Any]] = []
    for index, (name, pairs) in enumerate(core_specs):
        differences: list[dict[str, Any]] = []
        per_seed = []
        for policy_a, policy_b, seed in pairs:
            matched = paired_capped_reward_differences(rows_by_policy[policy_a], rows_by_policy[policy_b])
            for row in matched:
                row["training_seed"] = seed
            differences.extend(matched)
            per_seed.append({"training_seed": seed, "matched_scenarios": len(matched),
                "mean_capped_reward_difference_a_minus_b": sum(x["difference"] for x in matched)/len(matched),
                "truncated_games_a": sum(x["a_truncated"] for x in matched),
                "truncated_games_b": sum(x["b_truncated"] for x in matched)})
        if len(differences) != 300:
            raise ValueError(f"{name} expected 300 complete paired scenarios, observed {len(differences)}")
        bootstrap = crossed_cluster_bootstrap(differences, iterations=iterations, seed=20261160+index)
        core.append({"comparison": name, "paired_scenarios": len(differences),
            "mean_capped_reward_difference_a_minus_b": bootstrap["point_difference"],
            "crossed_cluster_bootstrap": bootstrap, "per_training_seed": per_seed,
            "pairing_keys": ["training_seed", "evaluation_seed", "opponent_id", "agent_color"]})

    fixed: list[dict[str, Any]] = []
    fixed_ids = ("m4_behavior_only", "baseline:random_legal", "baseline:simple_heuristic")
    for arm in ("warm", "scratch"):
        for seed in training_seeds:
            for stage in ("pre_rl", "post_rl"):
                learned = f"{arm}:{seed}:{stage}"
                for index, control in enumerate(fixed_ids):
                    differences = paired_capped_reward_differences(rows_by_policy[learned], rows_by_policy[control])
                    interval = evaluation_seed_cluster_bootstrap(differences, iterations=iterations,
                        seed=20261170 + index)
                    fixed.append({"comparison": f"{learned}_vs_{control}",
                        "paired_scenarios": len(differences),
                        "mean_capped_reward_difference_a_minus_b": interval["point_difference"],
                        "evaluation_seed_cluster_bootstrap": interval,
                        "truncated_games_a": sum(x["a_truncated"] for x in differences),
                        "truncated_games_b": sum(x["b_truncated"] for x in differences)})

    color: list[dict[str, Any]] = []
    for policy_index, policy in enumerate(report["per_policy"]):
        policy_id = policy["policy_id"]
        indexed = {(int(row["evaluation_seed"]), row["opponent_id"], row["agent_color"]): row
                   for row in rows_by_policy[policy_id]}
        contrasts = []
        for evaluation_seed, opponent in sorted({(key[0], key[1]) for key in expected_scenarios}):
            white = indexed[(evaluation_seed, opponent, "white")]
            black = indexed[(evaluation_seed, opponent, "black")]
            contrasts.append({"evaluation_seed": evaluation_seed, "opponent_id": opponent,
                "difference": (float(white["agent_reward"])-float(black["agent_reward"])) / 2.0,
                "white_truncated": bool(white.get("truncated")),
                "black_truncated": bool(black.get("truncated"))})
        interval = evaluation_seed_cluster_bootstrap(contrasts, iterations=iterations,
            seed=20261190 + policy_index)
        color.append({"policy_id": policy_id, "paired_scenarios": len(contrasts),
            "mean_capped_reward_difference_white_minus_black": interval["point_difference"],
            "evaluation_seed_cluster_bootstrap": interval,
            "truncated_white": sum(x["white_truncated"] for x in contrasts),
            "truncated_black": sum(x["black_truncated"] for x in contrasts)})

    return {"schema": "videochess-m5-evaluation-capped-reward-sensitivity/1.0",
        "analysis_status": "supplementary_post_hoc_sensitivity_not_used_for_checkpoint_selection",
        "primary_evaluation_report": str(report_path.relative_to(ROOT)),
        "primary_evaluation_report_sha256": sha_file(report_path),
        "configuration_sha256": sha_file(CONFIG_PATH),
        "metric": "paired observed simulator agent_reward difference divided by 2; terminal rewards are +/-1/0 and a 400-decision truncation contributes its actual zero reward without being counted as W/D/L",
        "retains_truncated_games": True, "training_seed_clusters": 3, "evaluation_seed_clusters": 25,
        "raw_game_rows_are_independent": False,"bootstrap_iterations": iterations,
        "core_paired_comparisons": core,"fixed_policy_comparisons": fixed,
        "white_black_comparisons": color,"journal_diagnostics": diagnostics}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ARTIFACT_ROOT)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--iterations", type=int, default=10000)
    args = parser.parse_args()
    result = analyze(args.root, iterations=args.iterations)
    destination = args.output or args.root / "evaluation/capped-reward-sensitivity.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({"result":"PASS","output":str(destination),"policies":len(result["white_black_comparisons"]),
        "core_comparisons":len(result["core_paired_comparisons"]),"fixed_comparisons":len(result["fixed_policy_comparisons"]),
        "output_sha256":sha_file(destination)},sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
