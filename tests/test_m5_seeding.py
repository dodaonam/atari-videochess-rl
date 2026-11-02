"""Executable M5 seed-contract tests; no DDQN learner is implemented here."""

from __future__ import annotations

import inspect
import json
import subprocess
import sys
import unittest
from pathlib import Path

from videochess_rl.m5_seeding import (
    EXPERIMENT_ID,
    PAIR_ID_DOMAIN,
    RNG_DOMAINS,
    SEED_DOMAIN,
    SEED_DERIVATION_SCHEMA,
    derive_seed,
    paired_seed_schedule,
    pair_identity,
    run_identity,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/m5_seed_derivation_v1.json"


class M5SeedDerivationTests(unittest.TestCase):
    def test_known_answer_vectors_match_canonical_fixture(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(fixture["derivation_schema"], SEED_DERIVATION_SCHEMA)
        encoding = fixture["encoding"]
        self.assertEqual(encoding["pair_prefix_hex"], PAIR_ID_DOMAIN.hex())
        self.assertEqual(encoding["seed_prefix_hex"], SEED_DOMAIN.hex())
        self.assertEqual(
            encoding["seed_output"],
            "(domain_code << 60) | (first_8_digest_bytes_big_endian AND 0x0fffffffffffffff)",
        )
        for vector in fixture["vectors"]:
            with self.subTest(seed=vector["training_seed"], episode=vector["episode_index"]):
                pair = pair_identity(vector["experiment_id"], vector["training_seed"])
                self.assertEqual(pair, vector["pair_id"])
                schedule = paired_seed_schedule(
                    vector["experiment_id"], vector["training_seed"], vector["episode_index"]
                )
                self.assertEqual(schedule, vector["schedule"])
                if "run_ids" in vector:
                    self.assertEqual(
                        run_identity(pair, "warm", 0), vector["run_ids"]["warm_attempt_0"]
                    )
                    self.assertEqual(
                        run_identity(pair, "scratch", 0), vector["run_ids"]["scratch_attempt_0"]
                    )

    def test_pair_schedule_is_shared_across_distinct_run_and_arm_identities(self) -> None:
        pair_id = pair_identity(EXPERIMENT_ID, 20261104)
        warm_run_id = run_identity(pair_id, "warm", 0)
        scratch_run_id = run_identity(pair_id, "scratch", 0)
        self.assertNotEqual(warm_run_id, scratch_run_id)
        self.assertTrue(warm_run_id.startswith(f"m5-{pair_id}__warm__"))
        self.assertTrue(scratch_run_id.startswith(f"m5-{pair_id}__scratch__"))
        expected = paired_seed_schedule(EXPERIMENT_ID, 20261104, 3)
        # Each run resolves to the same stable pair key. The run-specific IDs
        # cannot enter this API, so distinct arm/run identities share the seed
        # schedule by construction.
        self.assertEqual(expected["pair_id"], pair_id)
        self.assertEqual(expected, paired_seed_schedule(EXPERIMENT_ID, 20261104, 3))
        self.assertNotEqual(run_identity(pair_id, "warm", 0), run_identity(pair_id, "warm", 1))
        self.assertNotIn("run_id", inspect.signature(paired_seed_schedule).parameters)
        self.assertNotIn("arm", inspect.signature(paired_seed_schedule).parameters)

    def test_training_seed_pairs_and_rng_domains_are_separated(self) -> None:
        first = paired_seed_schedule(EXPERIMENT_ID, 20261104, 0)
        second = paired_seed_schedule(EXPERIMENT_ID, 20261105, 0)
        self.assertNotEqual(first["pair_id"], second["pair_id"])
        first_values = [first[key] for key in first if key.endswith("_seed")]
        second_values = [second[key] for key in second if key.endswith("_seed")]
        self.assertTrue(set(first_values).isdisjoint(second_values))
        self.assertEqual(len({first[key] for key in first if key.endswith("_seed")}), len(RNG_DOMAINS))
        for domain_code, key in enumerate(
            (
                "episode_seed",
                "opponent_rng_seed",
                "exploration_rng_seed",
                "replay_sampling_rng_seed",
                "q_head_initialization_seed",
                "scratch_representation_initialization_seed",
            )
        ):
            self.assertEqual(first[key] >> 60, domain_code)
            self.assertEqual(second[key] >> 60, domain_code)

    def test_episode_and_opponent_seeds_are_indexed_but_root_streams_are_stable(self) -> None:
        episode_zero = paired_seed_schedule(EXPERIMENT_ID, 20261104, 0)
        episode_one = paired_seed_schedule(EXPERIMENT_ID, 20261104, 1)
        self.assertNotEqual(episode_zero["episode_seed"], episode_one["episode_seed"])
        self.assertNotEqual(episode_zero["opponent_rng_seed"], episode_one["opponent_rng_seed"])
        for key in (
            "exploration_rng_seed",
            "replay_sampling_rng_seed",
            "q_head_initialization_seed",
            "scratch_representation_initialization_seed",
        ):
            self.assertEqual(episode_zero[key], episode_one[key])

    def test_restart_derives_the_same_next_episode_seed_from_completed_count(self) -> None:
        completed_episodes = 9
        expected = paired_seed_schedule(EXPERIMENT_ID, 20261104, completed_episodes)
        code = (
            "import json; from videochess_rl.m5_seeding import paired_seed_schedule; "
            f"print(json.dumps(paired_seed_schedule({EXPERIMENT_ID!r}, 20261104, {completed_episodes}), sort_keys=True))"
        )
        restarted = subprocess.run(
            [sys.executable, "-c", code], cwd=ROOT, check=True, capture_output=True, text=True
        )
        self.assertEqual(json.loads(restarted.stdout), expected)

    def test_initialization_domains_keep_warm_and_scratch_contract_distinct(self) -> None:
        schedule = paired_seed_schedule(EXPERIMENT_ID, 20261104, 0)
        self.assertEqual(schedule["q_head_initialization_seed"], derive_seed(
            20261104, schedule["pair_id"], "q_head_initialization"
        ))
        self.assertNotEqual(
            schedule["q_head_initialization_seed"],
            schedule["scratch_representation_initialization_seed"],
        )

    def test_config_and_active_docs_use_only_versioned_pair_seed_contract(self) -> None:
        config = json.loads((ROOT / "configs/rl/m5-double-dqn-v1.json").read_text(encoding="utf-8"))
        derivation = config["seed_derivation"]
        self.assertEqual(derivation["schema"], SEED_DERIVATION_SCHEMA)
        self.assertEqual(derivation["implementation"], "videochess_rl.m5_seeding")
        self.assertEqual(derivation["run_identity_implementation"], "videochess_rl.m5_seeding.run_identity")
        self.assertEqual(derivation["experiment_id"], EXPERIMENT_ID)
        self.assertEqual(derivation["master_seed_source"], "training_seed")
        self.assertEqual(derivation["rng_domains"], list(RNG_DOMAINS))
        self.assertFalse(derivation["run_id_used_in_seed_derivation"])
        self.assertEqual(derivation["pair_identity"]["prefix_hex"], PAIR_ID_DOMAIN.hex())
        self.assertEqual(derivation["stream_seed"]["prefix_hex"], SEED_DOMAIN.hex())
        fixture_encoding = json.loads(FIXTURE.read_text(encoding="utf-8"))["encoding"]
        self.assertEqual(fixture_encoding["pair_prefix_hex"], derivation["pair_identity"]["prefix_hex"])
        self.assertEqual(fixture_encoding["seed_prefix_hex"], derivation["stream_seed"]["prefix_hex"])
        self.assertEqual(fixture_encoding["seed_output"], derivation["stream_seed"]["output"])
        self.assertEqual(
            derivation["pair_identity"]["encoding"],
            "U32BE(experiment_id_ascii_length) || experiment_id_ascii || U64BE(training_seed)",
        )
        self.assertEqual(
            derivation["stream_seed"]["encoding"],
            "U64BE(master_seed) || pair_id_raw_32_bytes || U32BE(domain_ascii_length) || domain_ascii || U64BE(index)",
        )
        self.assertEqual(derivation["stream_seed"]["accepted_integer_range"], "0..2^63-1")
        self.assertEqual(derivation["rng_domain_codes"], {name: index for index, name in enumerate(RNG_DOMAINS)})
        self.assertEqual(
            derivation["stream_seed"]["output"],
            "(domain_code << 60) | (first_8_digest_bytes_big_endian AND 0x0fffffffffffffff)",
        )
        self.assertEqual(derivation["run_identity_format"], "m5-{pair_id}__{arm}__attempt-{attempt_index:04d}")
        self.assertIn("never reused", derivation["attempt_index_contract"])
        self.assertEqual(config["training"]["paired_streams"]["derivation_schema"], SEED_DERIVATION_SCHEMA)
        self.assertNotIn("episode_seed_derivation", config["training"])

        active_paths = (
            ROOT / "docs/03-technical/RL_ALGORITHM.md",
            ROOT / "docs/04-research/M5_EXPERIMENT_PROTOCOL.md",
            ROOT / ".agents/plans/M05-double-dqn.md",
            ROOT / "docs/06-quality/M5_TEST_MATRIX.md",
            ROOT / "docs/05-operations/REPRODUCIBILITY.md",
            ROOT / "docs/03-technical/MDP_SPEC.md",
        )
        active_text = "\n".join(path.read_text(encoding="utf-8") for path in active_paths)
        self.assertNotIn("sha256(master_seed || NUL || run_id", active_text)
        self.assertNotIn("stable run ID, and next completed-episode index", active_text)
        self.assertIn(SEED_DERIVATION_SCHEMA, active_text)

    def test_invalid_seed_inputs_are_rejected(self) -> None:
        pair = pair_identity(EXPERIMENT_ID, 20261104)
        with self.assertRaises(ValueError):
            pair_identity("experiment with spaces", 1)
        with self.assertRaises(ValueError):
            derive_seed(1, pair.upper(), "episode_seed")
        with self.assertRaises(ValueError):
            derive_seed(1, pair, "run_id")
        with self.assertRaises(TypeError):
            derive_seed(True, pair, "episode_seed")
        with self.assertRaises(ValueError):
            derive_seed(1, pair, "episode_seed", -1)

    def test_run_identity_is_provenance_only_and_validates_arm_attempt(self) -> None:
        pair = pair_identity(EXPERIMENT_ID, 20261104)
        self.assertEqual(run_identity(pair, "warm", 0), f"m5-{pair}__warm__attempt-0000")
        self.assertEqual(run_identity(pair, "scratch", 10000), f"m5-{pair}__scratch__attempt-10000")
        with self.assertRaises(ValueError):
            run_identity(pair, "evaluation", 0)
        with self.assertRaises(ValueError):
            run_identity(pair, "warm", -1)


if __name__ == "__main__":
    unittest.main()
