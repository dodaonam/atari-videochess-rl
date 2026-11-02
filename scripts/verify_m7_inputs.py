#!/usr/bin/env python3
"""Read-only reverification of the frozen M7 policy population and M4–M6 inputs."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from videochess_rl.m6.ledger import sha256_file
from videochess_rl.m7.analysis import (
    _load_m4_imitation,
    _reconstruct_atari_run,
    analyze_m5,
    load_m5_raw_rows,
)
from videochess_rl.m7.policies import load_frozen_policy_roster
from videochess_rl.m7.protocol import (
    M6_V1_CONFIG_SHA256,
    M6_V1_MANIFEST_SHA256,
    M6_V2_CONFIG_SHA256,
    M6_V2_MANIFEST_SHA256,
    load_frozen_config,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--m4-root", type=Path, required=True)
    parser.add_argument("--m5-root", type=Path, required=True)
    parser.add_argument("--m6-v1-root", type=Path, required=True)
    parser.add_argument("--m6-v2-root", type=Path, required=True)
    args = parser.parse_args()

    config = load_frozen_config(args.config)
    roster, _ = load_frozen_policy_roster(
        args.config, m4_artifact_root=args.m4_root, m5_artifact_root=args.m5_root,
    )
    if len(roster) != 9:
        raise SystemExit("M7 input reverification failed: expected exactly nine verified policy adapters")
    m4 = _load_m4_imitation(args.m4_root)
    m5_rows, m5_identity = load_m5_raw_rows(args.m5_root)
    m5_analysis = analyze_m5(m5_rows)
    m6_ids = config["accepted_inputs"]["m6"]
    m6_runs = {}
    for version, run_root, config_sha, manifest_sha, expected_attempts in (
        ("v1", args.m6_v1_root, M6_V1_CONFIG_SHA256, M6_V1_MANIFEST_SHA256, 35),
        ("v2", args.m6_v2_root, M6_V2_CONFIG_SHA256, M6_V2_MANIFEST_SHA256, 20),
    ):
        run_id = m6_ids[version]["run_id"]
        reconstructed = _reconstruct_atari_run(
            run_root,
            expected_run_id=run_id,
            expected_config_sha256=config_sha,
            expected_root_manifest_sha256=manifest_sha,
            repository_root=ROOT,
        )
        if reconstructed["scheduled_attempts"] != expected_attempts:
            raise SystemExit(f"M6 {version} did not reconstruct its accepted schedule denominator")
        m6_runs[version] = {
            "run_id": run_id,
            "configuration_sha256": config_sha,
            "root_manifest_sha256": reconstructed["root_artifact_manifest_sha256"],
            "scheduled_attempts": reconstructed["scheduled_attempts"],
            "reset_observed_cells": reconstructed["reset_observed_cells"],
            "outcomes_by_policy": {
                policy: {key: row[key] for key in ("wins", "draws", "losses", "terminal_unknown", "truncated", "incomplete", "not_started", "terminal_only_game_score", "terminal_wdl_denominator")}
                for policy, row in reconstructed["policy_summary"]["by_policy"].items()
            },
        }
    v2_counts = Counter()
    for row in m6_runs["v2"]["outcomes_by_policy"].values():
        for key in ("wins", "draws", "losses", "terminal_unknown", "truncated", "incomplete", "not_started"):
            v2_counts[key] += row[key]
    if v2_counts != Counter({"losses": 11, "incomplete": 9, "wins": 0, "draws": 0,
                             "terminal_unknown": 0, "truncated": 0, "not_started": 0}):
        raise SystemExit("M6 v2 raw outcomes differ from its accepted 11-loss/9-incomplete record")

    result = {
        "schema": "videochess-m7-input-reverification/1.0",
        "configuration_sha256": sha256_file(args.config),
        "schedule_sha256": config["research_design"]["schedule_sha256"],
        "rom_sha256": config["ale_profile"]["rom_sha256"],
        "m4": {
            **{key: m4[key] for key in ("run_id", "training_seed", "selected_epoch", "checkpoint_sha256", "root_manifest_sha256", "test_evaluation_record_sha256", "positions", "legal_top1_accuracy", "legal_top3_accuracy")},
            "sidecar_file_sha256": config["accepted_inputs"]["m4"]["sidecar_manifest_file_sha256"],
            "metadata_sha256": config["accepted_inputs"]["m4"]["metadata_sha256"],
            "sidecar_hash_field_note": "63615d... is the accepted metadata checksum; cc0af4... is the sidecar file SHA-256",
        },
        "m5": {
            "root_manifest_sha256": m5_identity["root_manifest_sha256"],
            "raw_evaluation_rows": len(m5_rows),
            "policy_count": m5_analysis["policy_summary"]["policy_count"],
            "outcomes_by_policy": m5_analysis["policy_summary"]["by_policy"],
            "pre_post_and_warm_scratch_comparisons": m5_analysis["paired_comparisons"][:4],
            "accepted_run_count": 6,
            "training_decisions_per_run": 50000,
            "source_provenance_limitation": "RSK-014 remains an accepted historical limitation",
        },
        "m6": m6_runs,
        "m7_policy_roster": [
            {key: row.get(key) for key in (
                "policy_id", "display_name", "policy_type", "arm", "training_seed", "snapshot_stage",
                "m5_run_id", "artifact_relative_path", "valid_training_decisions",
                "checkpoint_file_sha256", "sidecar_manifest_file_sha256",
            ) if key in row}
            for row in config["accepted_inputs"]["m5"]["policies"]
        ] + [
            {"policy_id": "m4-behavior-only-seed-20261024",
             **{key: config["accepted_inputs"]["m4"].get(key) for key in (
                 "run_id", "training_seed", "selected_epoch", "checkpoint_file", "checkpoint_sha256",
                 "sidecar_file", "sidecar_manifest_file_sha256", "metadata_sha256", "root_manifest_sha256",
             )}},
            {"policy_id": "random-legal", "policy_type": "random_legal"},
            {"policy_id": "simple-heuristic", "policy_type": "simple_heuristic", "implementation_id": "simple-material-heuristic"},
        ],
        "integrity_disposition": "PASS; accepted artifacts and historical records were read-only",
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
