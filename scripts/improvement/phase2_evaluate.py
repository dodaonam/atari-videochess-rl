"""Frozen, bounded Phase 2 simulator development and reserved evaluation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import chess

from videochess_rl.improvement.common import ARTIFACTS, ROOT
from videochess_rl.model.checkpoint import load_checkpoint
from videochess_rl.model.inference import BehaviorPolicy
from videochess_rl.rl.checkpoint import load_evaluation_snapshot
from videochess_rl.rl.evaluate import QPolicy, evaluate_policy

EXPERIMENT = "videochess-improvement-20261103-v1"
M4_SHA = "cf5e437ff4e2d6a8e85739df751dec33f16b7bc4c92268f996ec4c612d62feed"
HISTORICAL_M4_SHA = "724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4"
M5_ROOT = ROOT / "artifacts" / "m5"
OFFICIAL = ARTIFACTS / "official"
DEV = OFFICIAL / "simulator-development"
FINAL = OFFICIAL / "simulator-final"


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text())


def load_q(path: Path, *, expected_decisions: int, config_sha: str, code_sha: str):
    model, metadata = load_evaluation_snapshot(path, device="cpu")
    if (metadata.get("experiment_id") != EXPERIMENT
            or metadata.get("execution_kind") != "official"
            or metadata.get("training_seed") != 20261103
            or metadata.get("stage") != "evaluation_only"
            or metadata.get("q_only_evaluation") is not True
            or metadata.get("valid_decisions") != expected_decisions
            or metadata.get("config_sha256") != config_sha
            or metadata.get("code_sha256") != code_sha
            or metadata.get("m4_sha256") != M4_SHA):
        raise ValueError(f"Q-only snapshot metadata mismatch: {path}")
    digest = file_sha(path)
    return QPolicy(model, policy_id=f"double_dqn_{expected_decisions}", checkpoint_sha256=digest), metadata, digest


def outcomes(rows: list[dict], scheduled: int) -> dict:
    wins = sum(r.get("status") == "completed_game" and not r.get("truncated") and r.get("agent_reward") == 1.0 for r in rows)
    losses = sum(r.get("status") == "completed_game" and not r.get("truncated") and r.get("agent_reward") == -1.0 for r in rows)
    draws = sum(r.get("status") == "completed_game" and not r.get("truncated") and r.get("agent_reward") == 0.0 for r in rows)
    trunc = sum(r.get("status") == "completed_game" and r.get("truncated") for r in rows)
    observed_incomplete = sum(r.get("status") != "completed_game" for r in rows)
    incomplete = max(0, scheduled - wins - losses - draws - trunc)
    unattempted = max(0, scheduled - len(rows))
    decisions = sum(int(r.get("agent_decisions") or 0) for r in rows)
    episodes = {}
    for opponent in ("random_legal", "simple_material_heuristic"):
        for color in ("white", "black"):
            subset = [r for r in rows if r.get("opponent_id") == opponent and r.get("agent_color") == color]
            w = sum(r.get("status") == "completed_game" and not r.get("truncated") and r.get("agent_reward") == 1.0 for r in subset)
            d = sum(r.get("status") == "completed_game" and not r.get("truncated") and r.get("agent_reward") == 0.0 for r in subset)
            l = sum(r.get("status") == "completed_game" and not r.get("truncated") and r.get("agent_reward") == -1.0 for r in subset)
            t = sum(r.get("status") == "completed_game" and r.get("truncated") for r in subset)
            observed_inc = sum(r.get("status") != "completed_game" for r in subset)
            inc = max(0, scheduled // 4 - w - d - l - t)
            unattempted_stratum = max(0, scheduled // 4 - len(subset))
            episodes[f"{opponent}/{color}"] = {"scheduled": scheduled // 4, "wins": w, "losses": l, "true_draws": d, "truncations": t, "incomplete": inc,
                "observed_incomplete": observed_inc, "unattempted": unattempted_stratum,
                "score": (w + .5 * d) / (scheduled // 4) if scheduled else None}
    return {"scheduled_games": scheduled, "observed_rows": len(rows), "wins": wins, "losses": losses, "true_draws": draws,
            "truncations": trunc, "incomplete": incomplete, "observed_incomplete": observed_incomplete,
            "unattempted": unattempted, "score": (wins + .5 * draws) / scheduled if scheduled else None,
            "win_rate": wins / scheduled if scheduled else None, "draw_rate": draws / scheduled if scheduled else None,
            "incomplete_rate": (trunc + incomplete) / scheduled if scheduled else None,
            "agent_decisions": decisions, "mean_decisions_per_observed_game": decisions / len(rows) if rows else None,
            "opponent_color_strata": episodes}


def rank(summary: dict) -> tuple:
    by_opp = summary["outcomes"]["opponent_color_strata"]
    simple = [v for k, v in by_opp.items() if k.startswith("simple_material_heuristic/")]
    simple_score = sum(v["score"] for v in simple) / len(simple) if simple else 0.0
    o = summary["outcomes"]
    return (o["score"] if o["score"] is not None else -1.0,
            -(o["truncations"] + o["incomplete"]), simple_score,
            -int(summary["training_decisions"]))


def run_candidates(protocol: dict, official: dict, mode: str) -> dict:
    run_started_utc = datetime.now(timezone.utc).isoformat()
    attempt = read_json(OFFICIAL / "attempt-0000" / "attempt.json")
    identity = attempt["identity"]
    snapshots = []
    rejected = []
    for boundary in protocol["training_snapshot_boundaries"]:
        path = OFFICIAL / "attempt-0000" / f"snapshot-{boundary:06d}.pt"
        sidecar = path.with_suffix(path.suffix + ".manifest.json")
        if not path.is_file() or not sidecar.is_file():
            continue
        try:
            policy, meta, digest = load_q(path, expected_decisions=boundary,
                config_sha=identity["config_sha256"], code_sha=identity["code_sha256"])
            snapshots.append((boundary, path, policy, meta, digest))
        except Exception as exc:
            rejected.append({"path": path.relative_to(ROOT).as_posix(), "reason": f"{type(exc).__name__}: {exc}"})
    if not snapshots:
        raise RuntimeError("no eligible Q-only official snapshots")

    started = time.monotonic()
    plan = protocol["development"] if mode == "dev" else protocol["reserved_final"]
    seeds = plan["stage_1_evaluation_seeds"] if mode == "dev" else plan["evaluation_seeds"]
    budget = plan["candidate_stage_wall_budget_seconds"] if mode == "dev" else plan["wall_budget_seconds"]
    destination = DEV if mode == "dev" else FINAL
    destination.mkdir(parents=True, exist_ok=False)
    rows_by_decision: dict[int, list[dict]] = {n: [] for n, *_ in snapshots}
    ledgers = []

    def evaluate_stage(candidates, stage_seeds, stage_budget, stage):
        stage_start = time.monotonic()
        for n, path, policy, meta, digest in candidates:
            remaining = max(0.0, stage_budget - (time.monotonic() - stage_start))
            if remaining <= 0:
                break
            t0 = time.monotonic()
            rows = evaluate_policy(policy, policy_id=policy.policy_id, max_decisions=400,
                seeds=stage_seeds, max_wall_seconds=remaining,
                attempt_id=f"phase2-{mode}-{stage}-{n}")
            rows_by_decision[n].extend(rows)
            with (destination/"scenario-rows.jsonl").open("a") as stream:
                for row in rows:
                    stream.write(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n")
                stream.flush()
            ledgers.append({"candidate_decisions": n, "snapshot_sha256": digest, "stage": stage,
                "evaluation_seeds": stage_seeds, "rows": len(rows), "wall_seconds": time.monotonic()-t0,
                "outcomes": outcomes(rows, len(stage_seeds)*4)})

    if mode == "dev":
        evaluate_stage(snapshots, seeds, budget, "stage-1")
        first = []
        for n, path, policy, meta, digest in snapshots:
            rows = rows_by_decision[n]
            if rows:
                first.append({"training_decisions": n, "snapshot_path": path.relative_to(ROOT).as_posix(),
                    "snapshot_sha256": digest, "outcomes": outcomes(rows, len(seeds)*4)})
        first.sort(key=rank, reverse=True)
        ext = protocol["development"]["extension"]
        finalists_n = {x["training_decisions"] for x in first[:3]}
        finalists = [x for x in snapshots if x[0] in finalists_n]
        used = time.monotonic()-started
        extension_budget = min(ext["maximum_extension_wall_budget_seconds"], max(0, protocol["development"]["total_wall_budget_seconds"]-used))
        evaluate_stage(finalists, ext["additional_evaluation_seeds"], extension_budget, "extension")
        summaries=[]
        for n, path, policy, meta, digest in snapshots:
            rows=rows_by_decision[n]
            if rows:
                summaries.append({"training_decisions":n,"snapshot_path":path.relative_to(ROOT).as_posix(),"snapshot_sha256":digest,
                    "extended":n in finalists_n,"scheduled_games":len(seeds)*4+(len(ext["additional_evaluation_seeds"])*4 if n in finalists_n else 0),
                    "outcomes":outcomes(rows,len(seeds)*4+(len(ext["additional_evaluation_seeds"])*4 if n in finalists_n else 0))})
        summaries.sort(key=rank,reverse=True)
        if not summaries: raise RuntimeError("no development candidate completed any scenario")
        selected=summaries[0]
        selection={"rule":protocol["development"]["selection"],"selected":selected,
            "ranking":summaries,"initial_stage_ranking":first,"extended_finalists":sorted(finalists_n),
            "eligible_snapshots":[{"training_decisions":n,"path":path.relative_to(ROOT).as_posix(),"sha256":digest} for n,path,_,_,digest in snapshots],
            "stage1_not_evaluated":[n for n,path,_,_,digest in snapshots if not rows_by_decision[n]],
            "selection_frozen_before_reserved_final":True,"final_results_used_for_selection":False}
        (destination/"selection.json").write_text(json.dumps(selection,indent=2,sort_keys=True)+"\n")
    else:
        selection_path=DEV/"selection.json"
        selection=read_json(selection_path)
        selected=selection["selected"]
        selected_path=ROOT/selected["snapshot_path"]
        candidate=next((x for x in snapshots if x[0]==selected["training_decisions"] and x[1]==selected_path),None)
        if candidate is None: raise RuntimeError("selected development snapshot is not eligible for final evaluation")
        policies=[candidate]
        m4_path=ROOT/'artifacts/improvement'/EXPERIMENT/'m4-a/epoch-22.pt'
        if not m4_path.is_file() or file_sha(m4_path)!=M4_SHA: raise RuntimeError("selected M4-A artifact identity changed")
        m4_model,_=load_checkpoint(m4_path,device="cpu")
        m4_policy=BehaviorPolicy(m4_model,checkpoint_sha256=M4_SHA)
        final_rows={"selected_double_dqn":[],"M4-A_behavior_cloning":[]}
        t0=time.monotonic(); total_budget=budget
        for policy_id, policy in ((f"double_dqn_{candidate[0]}",candidate[2]),("M4-A_behavior_cloning",m4_policy)):
            remaining=max(0,total_budget-(time.monotonic()-t0))
            if remaining<=0: break
            rows=evaluate_policy(policy,policy_id=policy_id,max_decisions=400,seeds=seeds,
                max_wall_seconds=remaining,attempt_id=f"phase2-final-{policy_id}")
            final_rows["selected_double_dqn" if policy_id.startswith("double") else policy_id]=rows
            with (destination/"scenario-rows.jsonl").open("a") as stream:
                for row in rows:
                    stream.write(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n")
        if M5_ROOT.exists():
            # Historical M5 is included only when its manifest-backed accepted
            # policy is loadable; no substitute checkpoint is guessed.
            try:
                from videochess_rl.m6.adapter import M5_WARM_CHECKPOINT_SHA256, M5_WARM_SIDECAR_SHA256, load_m5_policy
                manifest=read_json(M5_ROOT/'artifact-manifest.json')
                entry=next(item for item in manifest['files'] if item.get('sha256')==M5_WARM_CHECKPOINT_SHA256 and item.get('path','').endswith('.pt'))
                old_path=M5_ROOT/entry['path']
                old_policy,_=load_m5_policy(old_path,policy_id='historical_m5_warm_50000',arm='warm',training_seed=20261104,
                    expected_checkpoint_sha256=M5_WARM_CHECKPOINT_SHA256,expected_sidecar_sha256=M5_WARM_SIDECAR_SHA256,
                    artifact_root=M5_ROOT)
                remaining=max(0,total_budget-(time.monotonic()-t0))
                if remaining>0:
                    final_rows['historical_M5']=evaluate_policy(old_policy,policy_id='historical_M5_warm_50000',max_decisions=400,
                        seeds=seeds,max_wall_seconds=remaining,attempt_id='phase2-final-historical-m5')
                    with (destination/"scenario-rows.jsonl").open("a") as stream:
                        for row in final_rows['historical_M5']:
                            stream.write(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n")
            except Exception as exc:
                final_rows['historical_M5_unavailable']=[{"status":"unavailable","reason":f"{type(exc).__name__}: {exc}"}]
        final_summary={"frozen_selection":selected,"evaluation_seeds":seeds,"scheduled_games_per_policy":len(seeds)*4,
            "protocol":plan,"selection_may_use_final_results":False,
            "policies":{key:outcomes(rows,len(seeds)*4) for key,rows in final_rows.items() if rows and isinstance(rows,list) and key!='historical_M5_unavailable'}}
        final_summary["rows"]={k:v for k,v in final_rows.items()}
        (destination/"results.json").write_text(json.dumps(final_summary,indent=2,sort_keys=True)+"\n")
        return final_summary

    report={"mode":mode,"protocol_sha256":file_sha(ROOT/'configs/improvement/phase2-evaluation.json'),
        "experiment_id":EXPERIMENT,"training_source_identity":identity,"started_at_utc":run_started_utc,
        "wall_seconds":time.monotonic()-started,"snapshots_found":len(snapshots),"rejected_snapshots":rejected,
        "stage_ledger":ledgers,"selection_path":str((destination/"selection.json").relative_to(ROOT))}
    (destination/"outcomes.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    if mode=="dev": return read_json(destination/"selection.json")
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("dev","final"),required=True)
    args=parser.parse_args()
    protocol=read_json(ROOT/"configs/improvement/phase2-evaluation.json")
    result=run_candidates(protocol,{},args.mode)
    print(json.dumps(result,sort_keys=True),flush=True)


if __name__=="__main__": main()
