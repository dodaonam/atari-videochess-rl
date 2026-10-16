"""Schema, color coverage, and metric-separation checks for M2 benchmarks."""

from __future__ import annotations

import json
import random
import tempfile
import unittest
from pathlib import Path

import chess

from videochess_rl.benchmark import _play_game, run_baseline_benchmark
from videochess_rl.simulator import Observation


class FirstLegalPolicy:
    policy_id = "test_first_legal"

    @property
    def config(self) -> dict[str, object]:
        return {}

    def choose_move(self, observation, legal_moves, rng):
        del observation, rng
        return chess.Move.from_uci(sorted(move.uci() for move in legal_moves)[0])


class FailingAgent:
    policy_id = "test_failure"

    @property
    def config(self) -> dict[str, object]:
        return {}

    def choose_move(self, observation: Observation, legal_moves, rng: random.Random) -> chess.Move:
        del observation, legal_moves, rng
        raise RuntimeError("simulated agent failure")


class InterruptingAgent:
    policy_id = "test_interrupt"

    @property
    def config(self) -> dict[str, object]:
        return {}

    def choose_move(self, observation: Observation, legal_moves, rng: random.Random) -> chess.Move:
        del observation, legal_moves, rng
        raise KeyboardInterrupt


class BenchmarkTests(unittest.TestCase):
    def test_benchmark_records_seeded_both_color_games_and_separates_truncation(self) -> None:
        run = run_baseline_benchmark([31], max_decisions=1)

        self.assertEqual(run["metric_source"], "chess_simulator")
        self.assertFalse(run["ale_metrics_included"])
        self.assertIsNone(run["rating_claim"])
        self.assertEqual(run["summary"]["games"], 4)
        self.assertEqual(run["summary"]["truncated_games"], 4)
        self.assertEqual(run["summary"]["completed_games"], 0)
        self.assertEqual(run["summary"]["external_failures"], 0)
        self.assertEqual(run["summary"]["interruptions"], 0)

        for policy_id, summary in run["summary"]["by_agent_policy"].items():
            self.assertEqual(summary["games"], 2, policy_id)
            self.assertEqual(summary["completed_games"], 0)
            self.assertEqual(summary["wins"], 0)
            self.assertEqual(summary["draws"], 0)
            self.assertEqual(summary["losses"], 0)
            self.assertEqual(summary["by_agent_color"]["white"]["games"], 0)
            self.assertEqual(summary["by_agent_color"]["black"]["games"], 0)

        self.assertEqual({game["agent_color"] for game in run["games"]}, {"white", "black"})
        for game in run["games"]:
            self.assertEqual(game["status"], "truncated")
            self.assertFalse(game["terminated"])
            self.assertTrue(game["truncated"])
            self.assertEqual(game["truncation_reason"], "max_agent_decisions")
            self.assertIsNone(game["agent_wdl"])
            self.assertIsNone(game["outcome_result_white_perspective"])
            self.assertFalse(game["ale_metrics_included"])
            self.assertGreaterEqual(len(game["moves_uci"]), 2)

    def test_same_configuration_reproduces_semantic_game_records(self) -> None:
        first = run_baseline_benchmark([41], max_decisions=2)
        second = run_baseline_benchmark([41], max_decisions=2)

        first_semantic = [
            (g["agent_policy"], g["opponent_policy"], g["agent_color"], g["seed"], g["moves_uci"], g["status"])
            for g in first["games"]
        ]
        second_semantic = [
            (g["agent_policy"], g["opponent_policy"], g["agent_color"], g["seed"], g["moves_uci"], g["status"])
            for g in second["games"]
        ]
        self.assertEqual(first_semantic, second_semantic)

    def test_per_game_json_report_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "benchmark.json"
            run = run_baseline_benchmark([51], max_decisions=1, output_path=output)
            written = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(written["run_id"], run["run_id"])
        self.assertEqual(written["configuration"], run["configuration"])
        self.assertEqual(written["games"], run["games"])
        self.assertEqual(written["output_path"], output.as_posix())

    def test_invalid_benchmark_configuration_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            run_baseline_benchmark([], max_decisions=1)
        with self.assertRaises(ValueError):
            run_baseline_benchmark([-1], max_decisions=1)
        with self.assertRaises(ValueError):
            run_baseline_benchmark([1], max_decisions=0)

    def test_external_failure_is_recorded_without_becoming_a_chess_result(self) -> None:
        game = _play_game(
            agent=FailingAgent(),
            opponent=FirstLegalPolicy(),
            color=chess.WHITE,
            seed=61,
            agent_seed=62,
            max_decisions=1,
            source_revision="test-revision",
        )

        self.assertEqual(game["status"], "external_failure")
        self.assertTrue(game["external_failure_or_interruption"])
        self.assertEqual(game["failure_type"], "RuntimeError")
        self.assertFalse(game["terminated"])
        self.assertFalse(game["truncated"])
        self.assertIsNone(game["agent_wdl"])
        self.assertIsNone(game["outcome_result_white_perspective"])

    def test_interrupt_is_recorded_separately_from_failure_and_termination(self) -> None:
        game = _play_game(
            agent=InterruptingAgent(),
            opponent=FirstLegalPolicy(),
            color=chess.BLACK,
            seed=63,
            agent_seed=64,
            max_decisions=1,
            source_revision="test-revision",
        )

        self.assertEqual(game["status"], "interrupted")
        self.assertTrue(game["external_failure_or_interruption"])
        self.assertEqual(game["failure_type"], "KeyboardInterrupt")
        self.assertFalse(game["terminated"])
        self.assertFalse(game["truncated"])
        self.assertIsNone(game["agent_wdl"])


if __name__ == "__main__":
    unittest.main()
