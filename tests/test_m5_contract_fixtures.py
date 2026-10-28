"""Validate preparatory M5 oracle data; this is not a DDQN learner test."""

from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "m5_double_dqn_targets.json"
CHECKPOINT_FIXTURE = Path(__file__).parent / "fixtures" / "m5_checkpoint_boundaries.json"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class M5DoubleDqnFixtureTests(unittest.TestCase):
    def test_complete_evaluation_schedule_and_pairing_match_config_and_protocol(self) -> None:
        config = json.loads((REPOSITORY_ROOT / "configs/rl/m5-double-dqn-v1.json").read_text(encoding="utf-8"))
        protocol = (REPOSITORY_ROOT / "docs/04-research/M5_EXPERIMENT_PROTOCOL.md").read_text(encoding="utf-8")
        matrix = (REPOSITORY_ROOT / "docs/06-quality/M5_TEST_MATRIX.md").read_text(encoding="utf-8")
        evaluation = config["evaluation"]
        self.assertEqual(config["schema"], "videochess-m5-ddqn-config/1.1")
        self.assertEqual(config["protocol"], "m5-ddqn-comparison/1.1")
        self.assertIn("m5-ddqn-comparison/1.1", protocol)
        self.assertIn("m5-tests/1.1", matrix)
        groups = evaluation["policy_checkpoint_groups"]
        checkpoint_count = sum(
            group.get("count", len(group.get("training_seeds", [])) * len(group.get("stages", [])))
            for group in groups.values()
        )
        games_per_checkpoint = (
            len(evaluation["seeds"])
            * len(config["environment"]["opponents"])
            * len(config["environment"]["agent_colors"])
            * evaluation["games_per_opponent_per_color_per_seed"]
        )

        self.assertTrue(evaluation["both_agent_colors"])
        self.assertEqual(checkpoint_count, evaluation["policy_checkpoint_count"])
        self.assertEqual(checkpoint_count, 15)
        self.assertEqual(groups["warm_double_dqn"]["stages"], ["pre_rl", "post_rl"])
        self.assertEqual(groups["scratch_double_dqn"]["stages"], ["pre_rl", "post_rl"])
        self.assertEqual(groups["warm_double_dqn"]["training_seeds"], config["training"]["paired_seeds"])
        self.assertEqual(groups["scratch_double_dqn"]["training_seeds"], config["training"]["paired_seeds"])
        self.assertEqual(evaluation["policy_checkpoint_identity_fields"], ["arm", "training_seed", "stage"])
        self.assertIsNone(groups["m4_behavior_only"]["training_seed"])
        self.assertIsNone(groups["random_legal_baseline"]["training_seed"])
        self.assertIsNone(groups["simple_heuristic_baseline"]["training_seed"])
        self.assertTrue(config["training"]["initialization_snapshot"]["required_per_ddqn_arm_seed"])
        self.assertEqual(games_per_checkpoint, evaluation["games_per_policy_checkpoint"])
        self.assertEqual(games_per_checkpoint * checkpoint_count, 600)
        self.assertEqual(games_per_checkpoint * checkpoint_count, evaluation["planned_total_games"])
        self.assertEqual(evaluation["games_per_policy_checkpoint"], 40)
        self.assertEqual(evaluation["max_wall_minutes_per_checkpoint"], 20)
        self.assertEqual(evaluation["aggregate_wall_hours_hard_cap"], 3)
        accounting = evaluation["evaluation_budget_accounting"]
        self.assertEqual(accounting["sum_of_individual_caps_minutes"], checkpoint_count * 20)
        self.assertEqual(accounting["aggregate_cap_minutes"], 180)
        self.assertEqual(accounting["minimum_average_budget_seconds_per_game_at_aggregate_cap"], 18)
        self.assertEqual(evaluation["evaluation_pairing"]["scenario_key"], ["evaluation_seed", "opponent_id", "agent_color"])
        self.assertEqual(evaluation["evaluation_pairing"]["warm_scratch_comparison_key"], ["training_seed", "stage", "evaluation_seed", "opponent_id", "agent_color"])
        self.assertEqual(evaluation["evaluation_pairing"]["before_after_comparison_key"], ["arm", "training_seed", "evaluation_seed", "opponent_id", "agent_color"])
        self.assertEqual(evaluation["evaluation_pairing"]["paired_uncertainty_method"], "crossed_cluster_bootstrap_over_training_seed_and_evaluation_seed")
        self.assertEqual(evaluation["evaluation_pairing"]["training_seed_clusters"], 3)
        self.assertEqual(evaluation["evaluation_pairing"]["evaluation_seed_clusters"], 10)
        self.assertTrue(evaluation["evaluation_pairing"]["few_training_cluster_caveat_required"])
        self.assertFalse(evaluation["evaluation_pairing"]["same_realized_trajectory_claimed"])
        self.assertFalse(evaluation["evaluation_pairing"]["independent_observations_assumed"])
        self.assertIn("15", protocol)
        self.assertIn("**600 planned games**", protocol)
        self.assertIn("18 seconds/game", protocol)
        self.assertIn("15 snapshots total", matrix)
        self.assertIn("derives 600 games", matrix)
        self.assertIn("Different initial Q scores can choose different actions", protocol)
        self.assertIn("(training_seed, stage, evaluation_seed, opponent_id, agent_color)", protocol)
        self.assertIn("crossed paired cluster bootstrap", protocol)
        self.assertIn("only three training-seed clusters", protocol)
        self.assertNotIn("receives the same transitions", protocol)
        self.assertNotIn("same transitions as B", protocol)

    def test_warm_scratch_and_before_after_pairs_have_stable_unique_ids(self) -> None:
        config = json.loads((REPOSITORY_ROOT / "configs/rl/m5-double-dqn-v1.json").read_text(encoding="utf-8"))
        seeds = config["training"]["paired_seeds"]
        groups = config["evaluation"]["policy_checkpoint_groups"]
        self.assertEqual(config["training"]["initialization_snapshot"]["capture_decision"], 0)
        self.assertTrue(config["training"]["initialization_snapshot"]["capture_after_target_copy"])
        self.assertTrue(config["training"]["initialization_snapshot"]["capture_before_first_gradient_update"])
        warm = {(seed, stage) for seed in groups["warm_double_dqn"]["training_seeds"] for stage in groups["warm_double_dqn"]["stages"]}
        scratch = {(seed, stage) for seed in groups["scratch_double_dqn"]["training_seeds"] for stage in groups["scratch_double_dqn"]["stages"]}
        self.assertEqual(warm, {(seed, stage) for seed in seeds for stage in ("pre_rl", "post_rl")})
        self.assertEqual(scratch, warm)
        identities = [
            f"{arm}:{seed}:{stage}"
            for arm in ("warm", "scratch")
            for seed in seeds
            for stage in ("pre_rl", "post_rl")
        ] + ["m4:frozen", "baseline:random_legal", "baseline:simple_heuristic"]
        self.assertEqual(len(identities), 15)
        self.assertEqual(len(set(identities)), len(identities))

    def test_snapshot_and_resumable_checkpoint_contracts_are_separate(self) -> None:
        config = json.loads((REPOSITORY_ROOT / "configs/rl/m5-double-dqn-v1.json").read_text(encoding="utf-8"))
        algorithm = (REPOSITORY_ROOT / "docs/03-technical/RL_ALGORITHM.md").read_text(encoding="utf-8")
        plan = (REPOSITORY_ROOT / ".agents/plans/M05-double-dqn.md").read_text(encoding="utf-8")
        fixture = json.loads(CHECKPOINT_FIXTURE.read_text(encoding="utf-8"))
        training = config["training"]
        names = training["artifact_names"]
        self.assertIn("__eval-snapshot-v1.pt", names["evaluation_snapshot"])
        self.assertIn("__resume-v1.pt", names["resumable_checkpoint"])
        self.assertIn("__incomplete.json", names["attempt_segment"])
        self.assertIn("{attempt_index", names["evaluation_snapshot"])
        self.assertIn("{attempt_index", names["resumable_checkpoint"])

        self.assertEqual(training["evaluation_snapshot_decision_interval"], 2500)
        self.assertEqual(training["final_evaluation_snapshot_valid_decisions"], 10000)
        self.assertEqual(training["evaluation_snapshot_schema"], "videochess-ddqn-evaluation-snapshot/1.0")
        self.assertFalse(training["evaluation_snapshot_is_resumable"])
        self.assertEqual(training["resumable_checkpoint_schema"], "videochess-ddqn-checkpoint/1.0")
        self.assertEqual(training["resumable_checkpoint_boundary"], "completed_episode_only")
        self.assertTrue(training["periodic_snapshot_continues_live_episode"])
        self.assertTrue(training["only_final_decision_snapshot_stops_training"])
        self.assertEqual(training["evaluation_snapshot_capture_order"], fixture["capture_order"])
        self.assertIn("latest-resume.json", algorithm)
        self.assertIn("If a wall-time or memory cap is exhausted", algorithm)
        self.assertEqual(fixture["periodic_decision_milestones"], [2500, 5000, 7500, 10000])
        self.assertIn("non-resumable", algorithm)
        self.assertIn("latest resumable checkpoint", algorithm)
        self.assertIn("deterministically replay work since that checkpoint", algorithm)
        self.assertIn("mid-episode", plan)

        cases = {case["id"]: case for case in fixture["cases"]}
        periodic = cases["periodic_snapshot_mid_episode_continues"]
        self.assertEqual(periodic["valid_decision_after_step"], 2500)
        self.assertTrue(periodic["snapshot_evaluation_valid"])
        self.assertFalse(periodic["snapshot_resumable"])
        self.assertTrue(periodic["continue_same_live_episode"])
        self.assertFalse(periodic["episode_reset"])
        self.assertFalse(periodic["resumable_checkpoint_written"])
        self.assertFalse(periodic["synthetic_flags_or_reward_added"])

        boundary = cases["episode_boundary_snapshot_and_resume_checkpoint_are_distinct"]
        self.assertTrue(boundary["snapshot_evaluation_valid"])
        self.assertFalse(boundary["snapshot_resumable"])
        self.assertTrue(boundary["checkpoint_is_resume_valid"])

        mid_episode = cases["decision_cap_mid_episode"]
        self.assertTrue(mid_episode["valid_transition"] and mid_episode["transition_inserted"])
        self.assertEqual(mid_episode["valid_decision_after_step"], 10000)
        self.assertTrue(mid_episode["evaluation_snapshot_written"] and mid_episode["snapshot_evaluation_valid"])
        self.assertFalse(mid_episode["snapshot_resumable"])
        self.assertFalse(mid_episode["event_adds_reward"])
        self.assertFalse(mid_episode["event_sets_terminated"])
        self.assertFalse(mid_episode["event_sets_truncated"])
        self.assertFalse(mid_episode["event_resets_simulator"])
        self.assertLess(mid_episode["latest_episode_checkpoint_decisions"], 10000)

        real_truncation = cases["decision_cap_is_real_environment_truncation"]
        self.assertTrue(real_truncation["simulator_truncated"])
        self.assertTrue(real_truncation["episode_checkpoint_written"])
        self.assertFalse(real_truncation["event_overrides_simulator_flags"])

        interrupted = cases["resource_interruption_mid_episode_before_endpoint"]
        self.assertEqual(interrupted["restored_committed_decisions"], interrupted["resume_checkpoint_decisions"])
        self.assertFalse(interrupted["abandoned_logical_decisions_counted_twice"])
        self.assertTrue(interrupted["abandoned_wall_time_counts_toward_caps"])
        self.assertTrue(interrupted["rng_restored_from_episode_checkpoint"])
        self.assertFalse(interrupted["superseded_attempt_snapshots_eligible_for_final_selection"])

    def test_online_target_disagreement_uses_online_action_in_target_value(self) -> None:
        document = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(document["schema"], "videochess-m5-double-dqn-target-fixture/1.0")
        case = next(row for row in document["cases"] if row["id"] == "online_target_disagree_nonterminal")
        online_action = max(case["legal_uci"], key=lambda uci: (case["q_online_by_uci"][uci], tuple(-ord(c) for c in uci)))
        self.assertEqual(online_action, case["expected_online_action_uci"])
        target_preferred = max(case["legal_uci"], key=lambda uci: case["q_target_by_uci"][uci])
        self.assertNotEqual(online_action, target_preferred)
        target_value = case["q_target_by_uci"][online_action]
        calculated = case["reward_agent"] + document["gamma"] * case["bootstrap_mask"] * target_value
        self.assertAlmostEqual(calculated, case["expected_bellman_target"], places=12)

    def test_terminal_and_valid_truncation_masks_are_distinct(self) -> None:
        document = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cases = {row["id"]: row for row in document["cases"]}
        terminal = cases["true_terminal_no_bootstrap"]
        self.assertEqual(terminal["legal_uci"], [])
        self.assertEqual(terminal["bootstrap_mask"], 0)
        self.assertIsNone(terminal["expected_online_action_uci"])
        self.assertEqual(terminal["expected_bellman_target"], terminal["reward_agent"])

        automatic_draw = cases["automatic_draw_terminal_has_raw_board_moves_but_no_bootstrap_candidates"]
        self.assertEqual(automatic_draw["termination"], "seventyfive_moves")
        self.assertIn("test_seventyfive_move_rule_is_automatic_after_full_transition", automatic_draw["source_test"])
        self.assertTrue(automatic_draw["terminal_fen"])
        self.assertGreater(automatic_draw["raw_board_legal_uci_count"], 0)
        self.assertEqual(automatic_draw["legal_uci"], [])
        self.assertEqual(automatic_draw["bootstrap_mask"], 0)
        self.assertEqual(automatic_draw["expected_bellman_target"], 0.0)

        truncated = cases["valid_time_limit_truncation_bootstraps"]
        self.assertTrue(truncated["legal_uci"])
        self.assertEqual(truncated["bootstrap_mask"], 1)
        target = truncated["reward_agent"] + document["gamma"] * truncated["q_target_by_uci"][truncated["expected_online_action_uci"]]
        self.assertAlmostEqual(target, truncated["expected_bellman_target"], places=12)
        self.assertTrue(math.isfinite(target))


if __name__ == "__main__":
    unittest.main()
