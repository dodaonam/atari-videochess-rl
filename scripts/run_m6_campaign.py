#!/usr/bin/env python3
"""Run authorized M6 Atari diagnostics or the frozen Stage 3 campaign."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from videochess_rl.m6.campaign import CONFIG_PATH_V2, M6Campaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=("stage1", "stage2-debug", "stage2-default", "stage3"))
    parser.add_argument("--m5-artifact-root", type=Path,
                        default=os.environ.get("VIDEOCHESS_M5_M6_ARTIFACT_ROOT"))
    parser.add_argument("--m4-artifact-root", type=Path,
                        default=os.environ.get("VIDEOCHESS_M6_M4_ARTIFACT_ROOT"))
    parser.add_argument("--artifact-root", type=Path, default=REPO_ROOT / "artifacts/m6")
    parser.add_argument("--resume", action="store_true",
                        help="continue only unfinished frozen schedule entries; never replay a reset attempt")
    parser.add_argument("--stage3-protocol", choices=("v1", "v2"), default="v1",
                        help="select the separately frozen Stage 3 protocol (v1 remains the default)")
    args = parser.parse_args()
    if args.m5_artifact_root is None:
        parser.error("the private M5 artifact root is required")
    if args.m4_artifact_root is None and args.stage3_protocol == "v1":
        parser.error("the M4 private artifact root is required for v1/diagnostic policy rosters")
    if args.resume and args.stage != "stage3":
        parser.error("--resume is supported only for the frozen Stage 3 run")
    if args.stage3_protocol == "v2" and args.stage != "stage3":
        parser.error("Stage 3 v2 does not authorize debug diagnostics or other campaign stages")
    campaign_kwargs = {"config_path": CONFIG_PATH_V2} if args.stage3_protocol == "v2" else {}
    campaign = M6Campaign(
        artifact_root=args.artifact_root,
        m5_root=args.m5_artifact_root,
        m4_root=args.m4_artifact_root,
        **campaign_kwargs,
    )
    if args.stage == "stage3":
        summary = campaign.run_stage3(resume=args.resume)
    else:
        summary = campaign.run_diagnostics(stage=args.stage)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
