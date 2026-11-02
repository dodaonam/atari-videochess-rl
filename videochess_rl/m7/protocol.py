"""Frozen scientific design and schedule validation for M7 Option B."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any


CONFIG_SCHEMA = "videochess-m7-option-b-config/1.0"
PROTOCOL_ID = "M7-Option-B/1.0.0"
SCIENTIFIC_BASIS = "M7-EVAL/1.0.0"
AUTHORIZATION_ID = "M7-AUTH-20261031-OPTION-B"
RUN_ID_PREFIX = "m7-option-b-20261031-v1"

ROM_SHA256 = "d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7"
M4_ROOT_MANIFEST_SHA256 = "f00fde1c59325105e0ffd45bb45eb269dfa303416010c9a0b6c6be47bd9a9921"
M4_CHECKPOINT_SHA256 = "724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4"
M4_METADATA_SHA256 = "63615d8d0ed27900fdf86d3f3084ca95cd562f9ec2f9a7e94bca4b0f6301e0c8"
M4_SIDECAR_FILE_SHA256 = "cc0af4694e45fc23acb740c652dd9a62e1bcaf7851815d179693d09539f0f606"
M5_ROOT_MANIFEST_SHA256 = "a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c"
M6_V1_CONFIG_SHA256 = "05aedeb30efb8b6b97667c44f9d606b58d4da8ae20800d4ef143e629420cebac"
M6_V1_MANIFEST_SHA256 = "22ac6ec7e0f4a48f52b2452654d4adecaf111f38ea37f5d9517f173c838716d7"
M6_V2_CONFIG_SHA256 = "663651050db80ab027b452241c7d39837ec7986927c0aefc7c7be631f459a49b"
M6_V2_MANIFEST_SHA256 = "bc0068aa2254e4c15165247ee299f48940cca9b7c21f6a288fd13812631ea2b2"

ALE_SEEDS = tuple(range(20261201, 20261211))


def _m5_policy(
    *, arm: str, seed: int, run_id: str, relative_path: str,
    checkpoint_sha256: str, sidecar_file_sha256: str,
) -> dict[str, Any]:
    return {
        "policy_id": f"m5-{arm}-seed-{seed}-post-rl",
        "display_name": f"{arm.title()} post-RL, training seed {seed}",
        "policy_type": "frozen_m5_double_dqn_q_policy",
        "arm": arm,
        "training_seed": seed,
        "snapshot_stage": "post_rl",
        "valid_training_decisions": 50000,
        "m5_run_id": run_id,
        "artifact_relative_path": relative_path,
        "checkpoint_file_sha256": checkpoint_sha256,
        "sidecar_manifest_file_sha256": sidecar_file_sha256,
        "sidecar_embedded_checkpoint_sha256": checkpoint_sha256,
        "m5_root_manifest_sha256": M5_ROOT_MANIFEST_SHA256,
    }


def frozen_policy_roster() -> list[dict[str, Any]]:
    """Return exact accepted identities, in the preregistered base order."""
    return [
        _m5_policy(
            arm="warm", seed=20261104,
            run_id="m5-e072011a58411f4ff26040013ba2e8c71212e6c83acf755337c2d7e1e01378d7__warm__attempt-0001",
            relative_path="runs/m5-e072011a58411f4ff26040013ba2e8c71212e6c83acf755337c2d7e1e01378d7__warm__attempt-0001/m5-e072011a58411f4ff26040013ba2e8c71212e6c83acf755337c2d7e1e01378d7__warm__attempt-0001__warm__seed-20261104__attempt-0001__stage-post_rl__decisions-050000__eval-snapshot-v2.pt",
            checkpoint_sha256="0b2405017a8e1d539851f0cd278883d3fd23936fb5c2f7962c813590a6fd1767",
            sidecar_file_sha256="80d8689e4b349576c5708bb4dce3451e5a8c64d81470cd6f4273a4746844b682",
        ),
        _m5_policy(
            arm="warm", seed=20261105,
            run_id="m5-75b4300109faf28e59770a022ee13435ab4c92c6ab19750a83ad79ed9bbc581c__warm__attempt-0000",
            relative_path="runs/m5-75b4300109faf28e59770a022ee13435ab4c92c6ab19750a83ad79ed9bbc581c__warm__attempt-0000/m5-75b4300109faf28e59770a022ee13435ab4c92c6ab19750a83ad79ed9bbc581c__warm__attempt-0000__warm__seed-20261105__attempt-0000__stage-post_rl__decisions-050000__eval-snapshot-v2.pt",
            checkpoint_sha256="e864d8351cb03b7e671e7a061226711b2d33b23bbaca97e899c09f1d2eb59670",
            sidecar_file_sha256="dceb8c11c3ebd239048ba6e51bb8fd1ea26d72f9129ec6e4ed3bc4847cffabf0",
        ),
        _m5_policy(
            arm="warm", seed=20261106,
            run_id="m5-89235d5a197920cce40c4a52a034f68e27a6ecc3e5eb2ab0bef80b037ffef870__warm__attempt-0000",
            relative_path="runs/m5-89235d5a197920cce40c4a52a034f68e27a6ecc3e5eb2ab0bef80b037ffef870__warm__attempt-0000/m5-89235d5a197920cce40c4a52a034f68e27a6ecc3e5eb2ab0bef80b037ffef870__warm__attempt-0000__warm__seed-20261106__attempt-0000__stage-post_rl__decisions-050000__eval-snapshot-v2.pt",
            checkpoint_sha256="c037adc652a00ea131366c5f15ac78811a223459312f9bac5f676f267cf36bcd",
            sidecar_file_sha256="cf52cc191543ddcdfa460b1a1a07c6e9d941d09eee69fb673b09c18f97037b8d",
        ),
        _m5_policy(
            arm="scratch", seed=20261104,
            run_id="m5-e072011a58411f4ff26040013ba2e8c71212e6c83acf755337c2d7e1e01378d7__scratch__attempt-0000",
            relative_path="runs/m5-e072011a58411f4ff26040013ba2e8c71212e6c83acf755337c2d7e1e01378d7__scratch__attempt-0000/m5-e072011a58411f4ff26040013ba2e8c71212e6c83acf755337c2d7e1e01378d7__scratch__attempt-0000__scratch__seed-20261104__attempt-0000__stage-post_rl__decisions-050000__eval-snapshot-v2.pt",
            checkpoint_sha256="3749b0c0b6ae44d3ad5d6bf0863b60937a59fbe881e0bdf4932bdce6033ca400",
            sidecar_file_sha256="1c15e5bc4ba2437df113671dc316accbdfe6d8b59069ed29ed187daebf4fff1e",
        ),
        _m5_policy(
            arm="scratch", seed=20261105,
            run_id="m5-75b4300109faf28e59770a022ee13435ab4c92c6ab19750a83ad79ed9bbc581c__scratch__attempt-0000",
            relative_path="runs/m5-75b4300109faf28e59770a022ee13435ab4c92c6ab19750a83ad79ed9bbc581c__scratch__attempt-0000/m5-75b4300109faf28e59770a022ee13435ab4c92c6ab19750a83ad79ed9bbc581c__scratch__attempt-0000__scratch__seed-20261105__attempt-0000__stage-post_rl__decisions-050000__eval-snapshot-v2.pt",
            checkpoint_sha256="e63ab18289135e411fb4c00a025d2985446475e5b70881ca7e9190559c20b3f8",
            sidecar_file_sha256="d0bc5b1e08ede42282a9c921b4da6181341f9c7c4d633454642e7fe9312cc2e6",
        ),
        _m5_policy(
            arm="scratch", seed=20261106,
            run_id="m5-89235d5a197920cce40c4a52a034f68e27a6ecc3e5eb2ab0bef80b037ffef870__scratch__attempt-0000",
            relative_path="runs/m5-89235d5a197920cce40c4a52a034f68e27a6ecc3e5eb2ab0bef80b037ffef870__scratch__attempt-0000/m5-89235d5a197920cce40c4a52a034f68e27a6ecc3e5eb2ab0bef80b037ffef870__scratch__attempt-0000__scratch__seed-20261106__attempt-0000__stage-post_rl__decisions-050000__eval-snapshot-v2.pt",
            checkpoint_sha256="94838bc8c3547a5b8ce9e1d8c1dde66b86163defb868b18be6185895acf9663c",
            sidecar_file_sha256="7335dce64b7d070271ed490828022851f42232c1aacc7eed9014e360cd7e6779",
        ),
        {
            "policy_id": "m4-behavior-only-seed-20261024",
            "display_name": "Accepted M4 r4 behavior-only",
            "policy_type": "frozen_m4_supervised_behavior_policy",
            "training_seed": 20261024,
            "selected_epoch": 11,
            "checkpoint_file": "pretrained-behavior-only.pt",
            "checkpoint_file_sha256": M4_CHECKPOINT_SHA256,
            "sidecar_file": "pretrained-behavior-only.pt.manifest.json",
            "sidecar_manifest_file_sha256": M4_SIDECAR_FILE_SHA256,
            "sidecar_metadata_sha256": M4_METADATA_SHA256,
            "artifact_manifest_file": "artifact_manifest.json",
            "artifact_manifest_sha256": M4_ROOT_MANIFEST_SHA256,
            "input_schema": "videochess-model-input/1.0",
            "model_schema": "videochess-behavior-scorer/1.0",
        },
        {
            "policy_id": "random-legal",
            "display_name": "RandomLegal",
            "policy_type": "random_legal",
            "checkpoint_file_sha256": None,
            "sidecar_manifest_file_sha256": None,
        },
        {
            "policy_id": "simple-heuristic",
            "display_name": "SimpleHeuristic",
            "policy_type": "simple_heuristic",
            "implementation_id": "simple-material-heuristic",
            "checkpoint_file_sha256": None,
            "sidecar_manifest_file_sha256": None,
        },
    ]


POLICY_BASE_ORDER = tuple(
    row["policy_id"] for row in frozen_policy_roster()
)


def counterbalanced_policy_order(block_index: int) -> tuple[str, ...]:
    if isinstance(block_index, bool) or not isinstance(block_index, int) or block_index < 0:
        raise ValueError("block_index must be a non-negative integer")
    count = len(POLICY_BASE_ORDER)
    offset = (block_index * 4) % count
    direction = 1 if block_index % 2 == 0 else -1
    return tuple(POLICY_BASE_ORDER[(offset + direction * index) % count] for index in range(count))


def build_schedule(seeds: tuple[int, ...] = ALE_SEEDS) -> list[dict[str, Any]]:
    if len(seeds) != 10 or len(set(seeds)) != 10 or any(isinstance(seed, bool) for seed in seeds):
        raise ValueError("Option B requires ten unique ALE seeds")
    rows: list[dict[str, Any]] = []
    for block_index, seed in enumerate(seeds):
        for order_index, policy_id in enumerate(counterbalanced_policy_order(block_index)):
            rows.append({
                "slot": len(rows),
                "seed_block_index": block_index,
                "policy_order_index": order_index,
                "policy_id": policy_id,
                "ale_seed": seed,
                "game_id": f"{policy_id}-ale-seed-{seed}",
            })
    return rows


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def schedule_sha256(schedule: list[dict[str, Any]]) -> str:
    return sha256_bytes(canonical_json_bytes(schedule))


def build_config() -> dict[str, Any]:
    roster = frozen_policy_roster()
    seeds = list(ALE_SEEDS)
    schedule = build_schedule(ALE_SEEDS)
    return {
        "schema": CONFIG_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "scientific_basis": SCIENTIFIC_BASIS,
        "run_id_prefix": RUN_ID_PREFIX,
        "authorization_id": AUTHORIZATION_ID,
        "authorization_evidence_path": ".agents/evidence/M7-001-authorization-20261031.md",
        "historical_status": {
            "pre_m7_protocol_status_at_pr16": "proposed; Option B not authorized",
            "later_owner_decision": "direct owner order authorizes this separately versioned execution configuration; it does not retroactively change the proposal's historical status",
            "g4_status": "HOLD_NOT_APPROVED",
            "phase_ii_gate": "M7-004 and M7-005 require verified independent G4 approval",
        },
        "research_design": {
            "option": "B_additional_ale_comparison",
            "evaluation_unit": "one policy × one ALE seed block",
            "scheduled_attempts": 90,
            "policy_ids": [row["policy_id"] for row in roster],
            "ale_evaluation_seeds": seeds,
            "seed_overlap_check": {
                "m6_v1_seeds": list(range(20261130, 20261140)),
                "m6_v2_seeds": list(range(20261130, 20261140)),
                "overlap": [],
            },
            "opponent": "built-in ALE VideoChess opponent as Black; no Stockfish opponent/evaluator",
            "policy_selection": "all six accepted post-RL M5 snapshots, accepted M4 r4 behavior-only policy, RandomLegal, and SimpleHeuristic; no outcome-based selection",
            "training_seed_replications": 3,
            "evaluation_seed_blocks": 10,
            "seed_pairing": "all nine policies share each ALE seed; compare within seed blocks; M5 training seeds remain clustered",
            "order_algorithm": "for seed block i, offset=(4*i) mod 9 into the fixed policy base order; traverse forward for even i and backward for odd i",
            "schedule": schedule,
            "schedule_sha256": schedule_sha256(schedule),
        },
        "accepted_inputs": {
            "m4": {
                "run_id": "m4-behavior-20261027-r4",
                "training_seed": 20261024,
                "selected_epoch": 11,
                "checkpoint_file": "pretrained-behavior-only.pt",
                "checkpoint_sha256": M4_CHECKPOINT_SHA256,
                "metadata_sha256": M4_METADATA_SHA256,
                "sidecar_file": "pretrained-behavior-only.pt.manifest.json",
                "sidecar_metadata_sha256": M4_METADATA_SHA256,
                "sidecar_manifest_file_sha256": M4_SIDECAR_FILE_SHA256,
                "root_manifest_sha256": M4_ROOT_MANIFEST_SHA256,
                "historical_imitation": {
                    "positions": 2057,
                    "legal_top1_accuracy": 0.298979,
                    "legal_top3_accuracy": 0.543996,
                    "interpretation": "imitation agreement only; not Atari W/D/L, RL improvement, or Elo",
                },
            },
            "m5": {
                "root_manifest_sha256": M5_ROOT_MANIFEST_SHA256,
                "configuration_sha256": "84d305084397ad18397dfe395fab58de824fa056729675d0d1cd9ca8bdd06d8d",
                "completed_runs": 6,
                "training_seeds": [20261104, 20261105, 20261106],
                "valid_training_decisions_per_run": 50000,
                "simulator_evaluation": {
                    "scheduled_rows": 1500,
                    "terminal_games": 1494,
                    "truncations": 6,
                },
                "policies": [row for row in roster if row["policy_type"] == "frozen_m5_double_dqn_q_policy"],
            },
            "m6": {
                "v1": {
                    "run_id": "m6-stage3-ad3998200e31-c5ff389dc4fe",
                    "configuration_sha256": M6_V1_CONFIG_SHA256,
                    "root_manifest_sha256": M6_V1_MANIFEST_SHA256,
                    "scheduled_attempts": 35,
                    "ale_seeds": list(range(20261130, 20261140)),
                },
                "v2": {
                    "run_id": "m6-stage3-v2-91f51b14690e-d05d42400cfc",
                    "configuration_sha256": M6_V2_CONFIG_SHA256,
                    "root_manifest_sha256": M6_V2_MANIFEST_SHA256,
                    "scheduled_attempts": 20,
                    "ale_seeds": list(range(20261130, 20261140)),
                    "outcomes": {"terminal_losses": 11, "terminal_wins": 0, "terminal_draws": 0, "incomplete": 9},
                    "initiated_moves": 405,
                    "rgb_verified_moves": 385,
                    "verified_replies": 385,
                    "desynchronizations": 0,
                    "profile": "M6 v2 extended-horizon runtime profile; v2's 20-attempt campaign ceiling is not reused",
                },
                "pm6_f06_erratum": "preserve the original metadata inconsistency and cite its accepted erratum; do not edit historical M6 records",
            },
        },
        "ale_profile": {
            "environment_id": "ALE/VideoChess-v5",
            "rom_sha256": ROM_SHA256,
            "agent_color": "white",
            "mode": 4,
            "difficulty": 0,
            "observation_type": "rgb",
            "frameskip": 4,
            "repeat_action_probability": 0.25,
            "registered_default_max_num_frames_per_episode": 108000,
            "effective_max_num_frames_per_episode": 500000,
            "runner_maximum_post_reset_action_frames": 432000,
            "expected_frame_counter_reset_offset": 4,
            "maximum_player_moves": 200,
            "maximum_opponent_wait_frames": 40000,
            "controller_timing": {
                "direction_hold_frames": 33,
                "source_fire_press_frames": 1,
                "target_fire_press_frames": 16,
                "release_frames": 1,
                "observation_window_frames": 66,
                "target_fire_settle_windows": 3,
            },
            "observation_source_of_truth": "ALE RGB; shadow board only tracks/cross-checks verified history",
            "closed_loop": ["observe", "validate", "decide", "execute", "verify"],
        },
        "outcome_rules": {
            "reward_perspective": "White",
            "positive_finite_terminal_reward": "White win",
            "negative_finite_terminal_reward": "White loss",
            "zero_or_nonfinite_terminal_reward": "terminal_unknown",
            "incomplete_or_runner_truncated_is_draw": False,
            "game_score": "(wins + 0.5 * draws) / terminal_games; null when terminal_games is zero",
            "scheduled_categories": ["scheduled", "started", "terminal", "truncated", "terminal_unknown", "incomplete", "not_started"],
        },
        "primary_metrics": [
            "per-policy terminal W/D/L and terminal-only game score with explicit denominators",
            "schedule completion and each nonterminal/missing category",
            "RGB-verified initiated moves divided by all initiated player moves",
        ],
        "secondary_metrics": [
            "verified Atari replies, desynchronizations, cursor corrections, controller uncertainty and timeout reasons",
            "per-attempt ALE frames, environment steps, wall time, process CPU time/utilization, peak RSS, artifact bytes",
            "per-policy input-validation, choose-move and total adapter latency distributions",
        ],
        "analysis_freeze": {
            "bootstrap_resamples": 10000,
            "bootstrap_seed": 20261290,
            "interval": "95% cluster bootstrap; resample ALE seed blocks and preserve within-block policy pairings; where training policies are compared, retain the three training-seed pairs as clusters",
            "training_seed_caveat": "three training-seed pairs are a severe inference limitation; no robust superiority/generalization claim",
            "claim_labels": ["confirmatory", "exploratory", "post-hoc_sensitivity"],
        },
        "elo_disposition": "Elo not reported: calibrated pool/design not approved or unavailable.",
        "resource_limits": {
            "device": "local_cpu",
            "maximum_simultaneous_ale_processes": 1,
            "scheduled_attempts": 90,
            "maximum_wall_seconds_per_attempt": 1800,
            "maximum_aggregate_gameplay_seconds": 162000,
            "expected_gameplay_time": {
                "hours": 4.4,
                "historical_basis": "M6 v2 observed mean of approximately 176 seconds per attempt; 90-attempt extrapolation only",
                "guaranteed": False,
            },
            "maximum_campaign_artifact_bytes": 8589934592,
            "artifact_finalization_reserve_bytes": 134217728,
            "minimum_free_bytes_before_first_attempt": 12884901888,
            "maximum_process_rss_bytes": None,
            "maximum_pre_action_process_start_retries": 1,
            "retry_rule": "one global process-start retry only before reset/ALE action; no replacement after reset, action, outcome, or partial game",
            "colab_gpu_paid_cloud_or_external_service": False,
            "private_artifact_upload": False,
            "aggregate_gameplay_limit_note": "90 × 1,800 seconds = 162,000 seconds = 45 hours; setup/recovery overhead is measured separately",
        },
        "privacy": {
            "raw_rgb_rom_checkpoints_datasets_and_raw_traces": "owner-local only; outside Git and external services",
            "committed_evidence": "sanitized reports, configs, code, hashes and approved logs only",
            "public_release_authorized": False,
        },
    }


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema") != CONFIG_SCHEMA or config.get("protocol_id") != PROTOCOL_ID:
        raise ValueError("unsupported or changed M7 Option B configuration identity")
    if config.get("scientific_basis") != SCIENTIFIC_BASIS or config.get("authorization_id") != AUTHORIZATION_ID:
        raise ValueError("M7 scientific basis or owner authorization identity changed")
    if config.get("run_id_prefix") != RUN_ID_PREFIX:
        raise ValueError("M7 run identity prefix changed")
    profile = config.get("ale_profile", {})
    expected_profile = build_config()["ale_profile"]
    if profile != expected_profile:
        raise ValueError("M7 ALE/VideoChess runtime profile differs from the owner authorization")
    if config.get("resource_limits") != build_config()["resource_limits"]:
        raise ValueError("M7 resource envelope differs from the owner authorization")
    if config.get("outcome_rules") != build_config()["outcome_rules"]:
        raise ValueError("M7 outcome classification changed")
    if config.get("analysis_freeze") != build_config()["analysis_freeze"]:
        raise ValueError("M7 analysis bootstrap design changed")
    expected = build_config()
    for key in ("accepted_inputs", "primary_metrics", "secondary_metrics", "elo_disposition", "privacy"):
        if config.get(key) != expected[key]:
            raise ValueError(f"M7 frozen {key} changed")
    design = config.get("research_design", {})
    if design.get("ale_evaluation_seeds") != list(ALE_SEEDS):
        raise ValueError("M7 evaluation seed schedule differs from owner-authorized seeds")
    if design.get("seed_overlap_check", {}).get("overlap") != []:
        raise ValueError("M7 seeds overlap an accepted M6 ALE population")
    if design.get("policy_ids") != list(POLICY_BASE_ORDER):
        raise ValueError("M7 policy roster or mapping changed")
    expected_schedule = build_schedule(ALE_SEEDS)
    if design.get("schedule") != expected_schedule:
        raise ValueError("M7 frozen 90-cell schedule is incomplete, duplicated, or reordered")
    if design.get("schedule_sha256") != schedule_sha256(expected_schedule):
        raise ValueError("M7 frozen schedule hash does not match its canonical cells")
    if len(expected_schedule) != 90:
        raise ValueError("M7 Option B must contain exactly 90 scheduled cells")
    per_cell = {(row["policy_id"], row["ale_seed"]) for row in expected_schedule}
    if len(per_cell) != 90 or len({row["game_id"] for row in expected_schedule}) != 90:
        raise ValueError("M7 schedule has duplicate policy/seed cells or game IDs")
    if any(sum(row["policy_id"] == p["policy_id"] for row in expected_schedule) != 10 for p in frozen_policy_roster()):
        raise ValueError("every M7 policy must have exactly ten scheduled attempts")
    if any(sum(row["ale_seed"] == seed for row in expected_schedule) != 9 for seed in ALE_SEEDS):
        raise ValueError("every M7 evaluation seed block must contain the same nine policies")
    for row in frozen_policy_roster():
        if row["policy_type"] == "frozen_m5_double_dqn_q_policy":
            rel = PurePosixPath(row["artifact_relative_path"])
            if rel.is_absolute() or ".." in rel.parts or not row["artifact_relative_path"].startswith("runs/"):
                raise ValueError("M5 checkpoint path must be a safe artifact-root-relative POSIX path")


def write_frozen_config(path: str | Path) -> dict[str, Any]:
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite frozen M7 configuration: {destination}")
    config = build_config()
    validate_config(config)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(config, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return config


def load_frozen_config(path: str | Path) -> dict[str, Any]:
    supplied = Path(path).expanduser()
    if supplied.is_symlink():
        raise ValueError("frozen M7 configuration must not be a symbolic link")
    config = json.loads(supplied.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    validate_config(config)
    return config
