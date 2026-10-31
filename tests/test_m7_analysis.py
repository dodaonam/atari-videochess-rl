from __future__ import annotations

import unittest

from videochess_rl.m7.analysis import (
    _summarize_atari_cells,
    classify_raw_ale_outcome,
    classify_terminal_cell,
    crossed_cluster_bootstrap,
    normalized_recorded_outcome,
    paired_m5_comparison,
    paired_interval_with_censoring,
    recorded_outcome_matches_raw,
    summarize_m5_rows,
)


def trace(*, terminated: bool, truncated: bool, reward: object, stop: str | None = None) -> dict:
    return {"terminal": {
        "ale_terminated": terminated,
        "ale_truncated": truncated,
        "ale_reward_total": reward,
        "runner_stop_category": stop,
    }}


class M7AnalysisTests(unittest.TestCase):
    def test_terminal_reward_is_white_perspective_and_unknown_is_not_draw(self) -> None:
        self.assertEqual(classify_raw_ale_outcome(trace(terminated=True, truncated=False, reward=1.0)), "win")
        self.assertEqual(classify_raw_ale_outcome(trace(terminated=True, truncated=False, reward=-1.0)), "loss")
        self.assertEqual(classify_raw_ale_outcome(trace(terminated=True, truncated=False, reward=0.0)), "terminal_unknown")
        self.assertEqual(classify_raw_ale_outcome(trace(terminated=True, truncated=False, reward=float("nan"))), "terminal_unknown")
        self.assertEqual(classify_raw_ale_outcome(trace(terminated=False, truncated=True, reward=0.0)), "truncated")
        self.assertEqual(classify_raw_ale_outcome(trace(terminated=False, truncated=False, reward=0.0, stop="OPPONENT_RESPONSE_TIMEOUT")), "incomplete")

    def test_historical_m6_vocabulary_is_normalized_without_calling_runner_stop_a_draw(self) -> None:
        schema = "videochess-m6-attempt-record/1.0"
        self.assertTrue(recorded_outcome_matches_raw({"schema": schema, "outcome": "runner_truncated"}, "incomplete"))
        self.assertTrue(recorded_outcome_matches_raw({"schema": schema, "outcome": "ale_truncated"}, "truncated"))
        self.assertTrue(recorded_outcome_matches_raw({"schema": schema, "outcome": "terminal_unknown"}, "terminal_unknown"))
        self.assertFalse(recorded_outcome_matches_raw({"schema": schema, "outcome": "runner_truncated"}, "draw"))
        self.assertEqual(normalized_recorded_outcome({"schema": schema, "outcome": "runner_truncated"}), "incomplete")
        self.assertEqual(normalized_recorded_outcome({"schema": schema, "outcome": "ale_truncated"}), "truncated")

    def test_paired_interval_is_withheld_when_terminal_pairing_is_censored(self) -> None:
        result = paired_interval_with_censoring(
            [{"training_seed": 1, "evaluation_seed": 11, "difference": 0.5}],
            scheduled_pairs=2,
            censored_pairs=1,
        )
        self.assertEqual(result["point_difference"], 0.5)
        self.assertIsNone(result["ci_95_crossed_cluster"])
        self.assertEqual(result["status"], "unavailable_incomplete_or_censored_pair_set")

    def test_terminal_only_score_uses_known_wdl_denominator_and_can_be_null(self) -> None:
        summary = classify_terminal_cell([
            {"outcome": "win"}, {"outcome": "draw"}, {"outcome": "loss"},
            {"outcome": "terminal_unknown"}, {"outcome": "truncated"},
            {"outcome": "incomplete"}, {"outcome": "not_started"},
        ])
        self.assertEqual(summary["terminal_known_games"], 3)
        self.assertEqual(summary["terminal_only_game_score"], 0.5)
        self.assertEqual(summary["terminal_unknown"], 1)
        self.assertEqual(summary["incomplete"], 1)
        self.assertEqual(summary["not_started"], 1)
        self.assertIsNone(classify_terminal_cell([{"outcome": "incomplete"}])["terminal_only_game_score"])

    def test_m5_truncation_is_not_counted_as_draw(self) -> None:
        rows = [
            {"policy_id": "warm:20261104:post_rl", "status": "completed_game", "truncated": False, "agent_reward": 1.0},
            {"policy_id": "warm:20261104:post_rl", "status": "completed_game", "truncated": False, "agent_reward": 0.0},
            {"policy_id": "warm:20261104:post_rl", "status": "completed_game", "truncated": True, "agent_reward": 0.0},
            {"policy_id": "warm:20261104:post_rl", "status": "incomplete_policy_deadline", "truncated": None, "agent_reward": None},
        ]
        summary = summarize_m5_rows(rows)["by_policy"]["warm:20261104:post_rl"]
        self.assertEqual(summary["wins"], 1)
        self.assertEqual(summary["draws"], 1)
        self.assertEqual(summary["truncated"], 1)
        self.assertEqual(summary["incomplete"], 1)
        self.assertEqual(summary["terminal_known_games"], 2)
        self.assertEqual(summary["terminal_only_game_score"], 0.75)
        self.assertEqual(summary["scheduled"], 4)

    def test_crossed_cluster_bootstrap_is_deterministic_and_cluster_bounded(self) -> None:
        rows = [{"training_seed": train, "evaluation_seed": block, "difference": 0.25}
                for train in (1, 2, 3) for block in range(10)]
        a = crossed_cluster_bootstrap(rows)
        b = crossed_cluster_bootstrap(rows)
        self.assertEqual(a, b)
        self.assertEqual(a["iterations"], 10000)
        self.assertEqual(a["training_seed_clusters"], 3)
        self.assertEqual(a["evaluation_seed_clusters"], 10)
        self.assertEqual(a["point_difference"], 0.25)
        self.assertEqual(a["ci_95_crossed_cluster"], [0.25, 0.25])
        self.assertTrue(a["few_training_cluster_caveat"])

    def test_m5_pairing_preserves_seed_and_marks_censoring(self) -> None:
        rows = []
        for seed in (20261104, 20261105, 20261106):
            for eval_seed in (20261130, 20261131):
                for opponent in ("random_legal", "simple_material_heuristic"):
                    for color in ("white", "black"):
                        rows.append({"policy_id": f"warm:{seed}:post_rl", "evaluation_seed": eval_seed,
                                     "opponent_id": opponent, "agent_color": color, "status": "completed_game",
                                     "truncated": False, "agent_reward": 1.0})
                        rows.append({"policy_id": f"warm:{seed}:pre_rl", "evaluation_seed": eval_seed,
                                     "opponent_id": opponent, "agent_color": color, "status": "completed_game",
                                     "truncated": False, "agent_reward": -1.0})
        rows[0]["truncated"] = True
        rows[0]["agent_reward"] = 0.0
        result = paired_m5_comparison(
            rows,
            lambda row: row["policy_id"].endswith(":post_rl"),
            lambda row: row["policy_id"].endswith(":pre_rl"),
            label="warm_pre_vs_post",
        )
        self.assertEqual(result["matched_terminal_pairs"], 23)
        self.assertEqual(result["censored_pairs"], 1)
        self.assertEqual(result["left_minus_right"]["ci_95_crossed_cluster"], None)
        self.assertEqual(result["left_minus_right"]["status"], "unavailable_incomplete_or_censored_pair_set")
        self.assertEqual(len(result["per_training_seed"]), 3)

    def test_m7_policy_summary_keeps_all_scheduled_categories_and_bounds(self) -> None:
        cells = [
            {"policy_id": "warm", "ale_seed": 1, "outcome": "win", "reset_observed": True,
             "score": 1.0, "attempt_process_count": 1, "attempts": [],
             "metrics": {"initiated_player_moves": 2, "rgb_verified_initiated_player_moves": 1,
                         "verified_atari_replies": 1, "legal_action_proposals": 2,
                         "legal_action_validations_passed": 2, "desynchronizations": 0,
                         "cursor_corrections": 3, "rgb_verified_move_rate": 0.5,
                         "legal_action_validity_rate": 1.0, "policy_latencies": {},
                         "policy_latency_samples": {}, "ale_frames": 40}},
            {"policy_id": "warm", "ale_seed": 2, "outcome": "incomplete", "reset_observed": True,
             "score": None, "attempt_process_count": 1, "attempts": [], "metrics": {}},
            {"policy_id": "warm", "ale_seed": 3, "outcome": "not_started", "reset_observed": False,
             "score": None, "attempt_process_count": 0, "attempts": [], "metrics": {}},
        ]
        summary = _summarize_atari_cells(cells)["by_policy"]["warm"]
        self.assertEqual(summary["scheduled"], 3)
        self.assertEqual(summary["wins"], 1)
        self.assertEqual(summary["incomplete"], 1)
        self.assertEqual(summary["not_started"], 1)
        self.assertEqual(summary["terminal_known_games"], 1)
        self.assertEqual(summary["terminal_only_game_score"], 1.0)
        self.assertEqual(summary["full_schedule_score_bounds"]["denominator"], 3)
        self.assertEqual(summary["rgb_verified_move_rate"], 0.5)
        self.assertEqual(summary["legal_action_validity_rate"], 1.0)
        self.assertEqual(summary["cursor_corrections"], 3)


if __name__ == "__main__":
    unittest.main()
