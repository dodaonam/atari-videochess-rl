#!/usr/bin/env python3
"""Preflight, non-result-bearing smoke, run, or safely resume M7 Option B."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from videochess_rl.m7.campaign import M7CampaignRunner


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/m7/m7-option-b-1.0.0.json")
    parser.add_argument("--m4-artifact-root", type=Path, required=True)
    parser.add_argument("--m5-artifact-root", type=Path, required=True)
    parser.add_argument("--artifact-parent", type=Path, default=ROOT / "artifacts/m7-option-b")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preflight-only", action="store_true", help="verify committed config, inputs, runtime and resource reserve; no reset")
    mode.add_argument("--smoke-only", action="store_true", help="run two same-seed RGB resets and legal policy decisions; no ALE actions")
    mode.add_argument("--resume", action="store_true", help="verify run identity/ledger and resume only eligible unstarted cells")
    args = parser.parse_args()

    runner = M7CampaignRunner(
        repository_root=ROOT,
        config_path=args.config,
        m4_artifact_root=args.m4_artifact_root,
        m5_artifact_root=args.m5_artifact_root,
        artifact_parent=args.artifact_parent,
    )
    if args.preflight_only:
        result = runner.preflight_only()
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
        return 0 if result["storage_preflight_pass"] and result["no_conflicting_m7_run"] else 2
    if args.smoke_only:
        print(json.dumps(runner.smoke_test(), ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
        return 0
    result = runner.run(resume=args.resume)
    summary = result["summary"]
    accounting = summary["schedule_accounting"]
    print(json.dumps({
        "run_id": result["run_id"],
        "run_dir": Path(result["run_dir"]).relative_to(ROOT).as_posix(),
        "scheduled": accounting["scheduled_cells"],
        "started": accounting["started_cells"],
        "reset_observed": accounting["reset_observed_cells"],
        "not_started": accounting["not_started_cells"],
        "resource_stop_reason": summary["resource_stop_reason"],
        "artifact_files": len(result["artifact_manifest"]["files"]),
        "artifact_bytes": result["artifact_manifest"]["total_bytes"],
    }, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
