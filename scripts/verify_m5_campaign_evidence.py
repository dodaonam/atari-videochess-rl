#!/usr/bin/env python3
"""Read-only cross-check of private M5 training/evaluation campaign records.

Run only where the project-scoped ``artifacts/m5`` directory is available.
This verifies identities, counters, replay/evaluation event chains, fixed
scenario coverage, and resource-ledger arithmetic without changing artifacts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts/m5"
CONFIG_SHA = "84d305084397ad18397dfe395fab58de824fa056729675d0d1cd9ca8bdd06d8d"
EVALUATION_SEEDS = set(range(20261130, 20261155))
OPPONENT_IDS = {"random_legal", "simple_material_heuristic"}
COLORS = {"white", "black"}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_chain(path: Path, *, evaluation: bool = False) -> tuple[int, str, dict[str, int]]:
    previous = "0" * 64
    count = 0
    kinds: dict[str, int] = {}
    with path.open("rb") as stream:
        for number, raw in enumerate(stream, 1):
            row = json.loads(raw)
            if evaluation:
                payload = {key: row[key] for key in ("schema", "sequence", "previous", "event")}
                kind = str(row["event"]["type"])
                expected_previous = previous
                expected_sequence = count
            else:
                payload = {key: row[key] for key in ("schema", "previous", "transition")}
                kind = "transition"
                expected_previous = previous
                expected_sequence = None
            if row.get("previous") != expected_previous:
                raise ValueError(f"{path}: predecessor mismatch at line {number}")
            if evaluation and row.get("sequence") != expected_sequence:
                raise ValueError(f"{path}: event sequence mismatch at line {number}")
            digest = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            ).hexdigest()
            if row.get("chain_sha256") != digest:
                raise ValueError(f"{path}: hash-chain mismatch at line {number}")
            previous = digest
            count += 1
            kinds[kind] = kinds.get(kind, 0) + 1
    return count, previous, kinds


def verify_training() -> dict[str, Any]:
    campaign = json.loads((ROOT / ".agents/evidence/M5-training-campaign-verification-20261029.json").read_text())
    if campaign["completed_runs"] != 6 or campaign["planned_runs"] != 6:
        raise ValueError("training campaign plan/completion counts disagree")
    if campaign["completed_runs"] != 6 or campaign["total_valid_decisions"] != 300000:
        raise ValueError("training campaign does not show six exact-budget runs")
    rows = []
    replay_total = 0
    updates_total = 0
    sync_total = 0
    for record in campaign["runs"]:
        run_id = record["run_id"]
        run_dir = ARTIFACTS / "runs" / run_id
        summary = json.loads((run_dir / "run-summary.json").read_text())
        manifest = json.loads((run_dir / "run-manifest.json").read_text())
        attempt = json.loads((run_dir / "attempt-record.json").read_text())
        expected = (50000, 12245, 24)
        actual = (summary["valid_decisions"], summary["optimizer_updates"], summary["target_syncs"])
        if actual != expected or actual != (record["valid_decisions"], record["optimizer_updates"], record["target_syncs"]):
            raise ValueError(f"{run_id}: decision/update/sync counters disagree")
        if summary["config_sha256"] != CONFIG_SHA or record["config_sha256"] != CONFIG_SHA:
            raise ValueError(f"{run_id}: config identity differs")
        source_hash = summary["code"]["source_sha256"]
        if source_hash != record["code_sha256"] or source_hash != manifest["source_identity"]["source_sha256"]:
            raise ValueError(f"{run_id}: code-source identities disagree")
        counters = attempt["committed_counters"]
        if attempt["status"] != "complete" or counters["valid_decisions"] != 50000 or counters["optimizer_updates"] != 12245 or counters["target_syncs"] != 24:
            raise ValueError(f"{run_id}: attempt record is incomplete or inconsistent")
        snapshot = Path(record["post_rl_snapshot"]["path"])
        if _sha(snapshot) != record["post_rl_snapshot"]["sha256"]:
            raise ValueError(f"{run_id}: final policy snapshot checksum mismatch")
        sidecar = Path(str(snapshot) + ".manifest.json")
        meta = json.loads(sidecar.read_text())
        if meta.get("sha256") != record["post_rl_snapshot"]["sha256"] or meta.get("resumable") is not False:
            raise ValueError(f"{run_id}: final snapshot sidecar mismatch or incorrectly resumable")
        journal = run_dir / "replay.journal.jsonl"
        count, chain, _ = _verify_chain(journal)
        if count != 50000:
            raise ValueError(f"{run_id}: replay chain has {count} records, expected 50000")
        replay_total += count
        updates_total += actual[1]
        sync_total += actual[2]
        rows.append({"run_id": run_id, "arm": record["arm"], "training_seed": record["training_seed"],
                     "decisions": actual[0], "updates": actual[1], "syncs": actual[2],
                     "episodes": summary["completed_episodes"], "source_sha256": source_hash,
                     "replay_records": count, "replay_chain_sha256": chain,
                     "final_snapshot_sha256": record["post_rl_snapshot"]["sha256"]})
    if replay_total != 300000 or updates_total != 73470 or sync_total != 144:
        raise ValueError("campaign total counters disagree with the six run records")
    ledger = json.loads((ARTIFACTS / "resource-ledger.json").read_text())
    run_seconds = sum(float(value) for value in ledger["run_seconds"].values())
    other_seconds = sum(float(ledger.get(key, 0.0)) for key in (
        "profile_seconds", "failed_profile_seconds_unverified_but_conservatively_charged",
        "recovery_validation_seconds", "training_setup_seconds"))
    campaign_seconds = run_seconds + other_seconds
    if campaign_seconds > 216000 or any(float(value) > 28800 for value in ledger["run_seconds"].values()):
        raise ValueError("training resource ledger exceeds an approved cap")
    return {"runs": rows, "valid_decisions": 300000, "replay_records": replay_total,
            "optimizer_updates": updates_total, "target_syncs": sync_total,
            "run_physical_seconds": run_seconds, "profile_recovery_setup_seconds": other_seconds,
            "campaign_seconds": campaign_seconds}


def verify_evaluation() -> dict[str, Any]:
    report = json.loads((ARTIFACTS / "evaluation/evaluation-report.json").read_text())
    policy_summary = {row["policy_id"]: row for row in report["per_policy"]}
    if len(policy_summary) != 15 or report["planned_games"] != 1500 or report["executed_games"] != 1500:
        raise ValueError("evaluation policy/game plan is not exactly 15 by 100")
    all_rows = []
    policy_count = 0
    journal_records = 0
    for directory in sorted((ARTIFACTS / "evaluation").iterdir()):
        rows_path = directory / "final-rows-attempt-0000.json"
        journal_path = directory / "events-attempt-0000.jsonl"
        if not rows_path.is_file() or not journal_path.is_file():
            continue
        policy_count += 1
        rows = json.loads(rows_path.read_text())
        if len(rows) != 100:
            raise ValueError(f"{directory.name}: expected 100 raw game rows")
        scenarios = {(row["evaluation_seed"], row["opponent_id"], row["agent_color"]) for row in rows}
        expected_scenarios = {(seed, opponent, color) for seed in EVALUATION_SEEDS
                              for opponent in OPPONENT_IDS for color in COLORS}
        if scenarios != expected_scenarios:
            raise ValueError(f"{directory.name}: fixed evaluation scenario set differs")
        policy_ids = {row["policy_id"] for row in rows}
        if len(policy_ids) != 1 or next(iter(policy_ids)) not in policy_summary:
            raise ValueError(f"{directory.name}: policy identity mismatch")
        count, _, types = _verify_chain(journal_path, evaluation=True)
        if types.get("scenario_started") != 100 or types.get("scenario_completed") != 100:
            raise ValueError(f"{directory.name}: event journal start/completion count mismatch")
        journal_records += count
        all_rows.extend(rows)
    keys = [(row["policy_id"], row["evaluation_seed"], row["opponent_id"], row["agent_color"]) for row in all_rows]
    if policy_count != 15 or len(all_rows) != 1500 or len(set(keys)) != 1500:
        raise ValueError("evaluation is incomplete or has duplicate policy/scenario rows")
    truncated = [row for row in all_rows if row["truncated"]]
    terminal = [row for row in all_rows if not row["truncated"]]
    if len(truncated) != 6 or len(terminal) != 1494:
        raise ValueError("terminal/truncation counts differ from the reported evaluation")
    for row in truncated:
        if row["agent_reward"] != 0 or row["result"] is not None or row["truncation_reason"] != "max_agent_decisions":
            raise ValueError("truncated game was mislabeled or has fabricated terminal/reward data")
    for policy_id, policy in policy_summary.items():
        own_rows = [row for row in terminal if row["policy_id"] == policy_id]
        actual = {"wins": sum(row["agent_reward"] == 1.0 for row in own_rows),
                  "draws": sum(row["agent_reward"] == 0.0 for row in own_rows),
                  "losses": sum(row["agent_reward"] == -1.0 for row in own_rows),
                  "truncated_games": sum(row["policy_id"] == policy_id for row in truncated)}
        summary = policy["summary"]
        expected = {key: summary[key] for key in actual}
        if actual != expected:
            raise ValueError(f"{policy_id}: raw W/D/L/truncation rows disagree with report summary")
    ledger = json.loads((ARTIFACTS / "resource-ledger.json").read_text())
    evaluation_seconds = float(ledger["evaluation_campaign_seconds"])
    if evaluation_seconds > 43200 or any(float(seconds) > 2400 for seconds in ledger["evaluation_seconds"].values()):
        raise ValueError("evaluation resource ledger exceeds an approved cap")
    return {"policies": policy_count, "rows": len(all_rows), "unique_scenarios": len(set(keys)),
            "terminal_games": len(terminal), "truncated_games": len(truncated),
            "event_journal_records": journal_records, "evaluation_seconds": evaluation_seconds}


def main() -> int:
    if not ARTIFACTS.is_dir():
        raise SystemExit("private artifacts/m5 is unavailable; run on the authorized local artifact host")
    result = {"schema": "videochess-m5-private-campaign-verification/1.0",
              "training": verify_training(), "evaluation": verify_evaluation(),
              "read_only": True}
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
