"""Reproducible M5 profile, paired training, and frozen evaluation CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import re
import resource
import shutil
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chess
import numpy as np
import torch

from videochess_rl.baselines import RandomLegalAgent, SimpleHeuristicAgent
from videochess_rl.m5_seeding import EXPERIMENT_ID, paired_seed_schedule, pair_identity, run_identity
from videochess_rl.model.checkpoint import load_checkpoint, verify_artifact_manifest
from videochess_rl.model.dataset import model_inputs, collate_examples
from videochess_rl.model.features import encode_board, replay_observation_history
from videochess_rl.model.inference import BehaviorPolicy
from videochess_rl.data.contracts import config_identity
from videochess_rl.rl.checkpoint import (save_evaluation_snapshot, save_training_checkpoint, load_evaluation_snapshot,
    restore_training_checkpoint, load_training_checkpoint_bundle, verify_training_checkpoint)
from videochess_rl.rl.evaluate import (QPolicy, evaluate_policy, summarize_games,
    paired_white_black_comparison, require_evaluation_snapshot_stage)
from videochess_rl.rl.evaluation_journal import EvaluationEventJournal, recover_policy_attempt_rows
from videochess_rl.rl.network import make_scratch_scorer, make_warm_scorer, clone_target
from videochess_rl.rl.replay import ReplayBuffer, ReplayJournal
from videochess_rl.rl.training import DoubleDqnLearner, epsilon_at, run_training_episodes, select_action, _features
from videochess_rl.rl.transition import Transition
from videochess_rl.source_snapshot import capture_source_snapshot
from videochess_rl.simulator import ChessSimulator

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs/rl/m5-double-dqn-v1.json"


def _configured_directory(environment_name: str, default_path: str) -> Path:
    """Resolve a private artifact directory from an override or documented default."""
    value = os.environ.get(environment_name)
    return Path(value).expanduser() if value else Path(default_path)


M4_DIR = _configured_directory(
    "VIDEOCHESS_M5_M4_DIR",
    "/home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r4",
)
M4_CHECKPOINT_SHA = "724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4"
M3_DIR = _configured_directory(
    "VIDEOCHESS_M5_M3_RELEASE_DIR",
    "/home/dodaonam/Projects/atari-videochess-rl-m3/artifacts/m3/training-support/release-final-closure-r6",
)
ARTIFACT_ROOT = ROOT / "artifacts/m5"
# Exact immutable source identities accepted for the narrowly scoped recovery
# fixes below. 2026-10-28's safe TorchVersion loader is the original contract;
# 093992... is the pre-streaming implementation whose only subsequent change
# is bounded replay reconstruction / pre-mutation checkpoint validation.
RECOVERY_COMPATIBLE_CODE_SHA256 = frozenset({
    "e2cb7a957b21e43f4b6499a5364c89de4dbf3ce0889f4cffa7307808fa2e8419",
    "093992c50e893a7fdd92f2f95faafe28d4f1e73c7351a4a8179a3056c4e63b00",
})


def sha_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temp.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    with temp.open("rb") as f: os.fsync(f.fileno())
    os.replace(temp,path)
    fd=os.open(path.parent,os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def load_config() -> dict[str,Any]:
    return json.loads(CONFIG_PATH.read_text())


def config_hash() -> str: return sha_file(CONFIG_PATH)


def _campaign_usage_with_active_run(committed_seconds: float, active_run_started: float,
                                   now_monotonic: float) -> float:
    """Add only the current uncommitted run interval to committed ledger time."""
    return float(committed_seconds) + max(0.0, float(now_monotonic) - float(active_run_started))


def _require_unfinalized_artifact_root(path: Path) -> None:
    manifest = path / "artifact-manifest.json"
    if manifest.exists() or manifest.is_symlink():
        raise RuntimeError("refusing to modify a finalized or previously inventoried immutable M5 artifact root")


def source_hash() -> str:
    h=hashlib.sha256()
    for path in sorted((ROOT/"videochess_rl").rglob("*.py")):
        h.update(path.relative_to(ROOT).as_posix().encode()+b"\0")
        h.update(path.read_bytes())
    return h.hexdigest()


def code_identity() -> dict[str,Any]:
    import subprocess
    revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    dirty=bool(subprocess.check_output(["git","status","--porcelain"],cwd=ROOT,text=True).strip())
    return {"source_revision":revision,"source_dirty":dirty,"source_sha256":source_hash()}


def environment_identity() -> dict[str,Any]:
    return {"python":sys.version,"platform":platform.platform(),"processor":platform.processor(),
            "logical_cpu_count":os.cpu_count(),"torch":str(torch.__version__),"numpy":str(np.__version__),
            "python_chess":str(chess.__version__),"device":"cpu","cuda_available":torch.cuda.is_available(),
            "torch_threads":torch.get_num_threads(),"torch_interop_threads":torch.get_num_interop_threads()}


def verify_m3_release_artifact() -> tuple[dict[str,Any],str]:
    manifest_path=M3_DIR/"manifest.json"; manifest_bytes=manifest_path.read_bytes()
    manifest_sha=hashlib.sha256(manifest_bytes).hexdigest()
    manifest=json.loads(manifest_bytes)
    if manifest.get("schema")!="videochess-release/1.0" or manifest.get("release_id")!="f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890":
        raise ValueError("M3 release identity or schema mismatch")
    digest_line=(M3_DIR/"manifest.sha256").read_text(encoding="ascii").strip().split()
    if not digest_line or digest_line[0]!=manifest_sha: raise ValueError("M3 release manifest sidecar mismatch")
    expected={}
    for item in manifest.get("outputs",[]):
        name=item.get("path")
        if not isinstance(name,str) or Path(name).name!=name or name in expected: raise ValueError("M3 output manifest has an unsafe/duplicate path")
        expected[name]=(item.get("sha256"),item.get("bytes"))
    if set(expected)!={"config.json","games.jsonl","positions.jsonl","rejections.jsonl","source_manifest.json","split.json","stats.json"}:
        raise ValueError("M3 release output inventory differs from the accepted contract")
    for name,(digest,size) in expected.items():
        path=M3_DIR/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size!=size or sha_file(path)!=digest:
            raise ValueError(f"M3 release file integrity mismatch: {name}")
    config=json.loads((M3_DIR/"config.json").read_text()); source=json.loads((M3_DIR/"source_manifest.json").read_text())
    split=json.loads((M3_DIR/"split.json").read_text())
    payload=dict(config); payload.pop("config_sha256",None)
    if config_identity(payload)!=config.get("config_sha256") or config.get("config_sha256")!=manifest.get("config_sha256"):
        raise ValueError("M3 config identity mismatch")
    if source.get("archive_sha256")!=manifest.get("source_archive_sha256") or source.get("member_sha256")!=manifest.get("source_member_sha256"):
        raise ValueError("M3 source provenance differs from release manifest")
    if config.get("source_archive_sha256")!=manifest.get("source_archive_sha256") or config.get("source_member_sha256")!=manifest.get("source_member_sha256"):
        raise ValueError("M3 config source provenance differs from release manifest")
    if split.get("split_assignment_sha256")!=manifest.get("split_assignment_sha256"):
        raise ValueError("M3 split identity differs from release manifest")
    return manifest,manifest_sha


def peak_rss_bytes() -> int:
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value*1024 if sys.platform.startswith("linux") else value)


def artifact_size_bytes() -> int:
    return sum(p.stat().st_size for p in ARTIFACT_ROOT.rglob("*") if p.is_file()) if ARTIFACT_ROOT.exists() else 0


def verify_transfer_inputs() -> tuple[Any,dict[str,Any],dict[str,Any]]:
    if not M4_CHECKPOINT_SHA or sha_file(M4_DIR/"pretrained-behavior-only.pt") != M4_CHECKPOINT_SHA:
        raise ValueError("accepted M4 checkpoint SHA mismatch")
    m4_manifest=verify_artifact_manifest(M4_DIR)
    m4_model,bundle=load_checkpoint(M4_DIR/"pretrained-behavior-only.pt")
    meta=bundle["metadata"]
    output_semantics=meta.get("parameter_output_semantics")
    if meta.get("checkpoint_role") != "pretrained_behavior_only" or not isinstance(output_semantics,str) or not output_semantics.startswith("uncalibrated behavior preference logit; not a Q-value"):
        raise ValueError("M4 source is not the accepted behavior-only artifact")
    if meta.get("dataset_release_id") != "f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890":
        raise ValueError("M4 checkpoint references an unexpected M3 release")
    release,release_sha=verify_m3_release_artifact()
    if release["release_id"] != meta["dataset_release_id"] or release_sha != meta.get("release_manifest_sha256"):
        raise ValueError("accepted M3 release provenance does not match M4 checkpoint metadata")
    if m4_model.trainable_parameter_count != meta.get("parameter_count"):
        raise ValueError("M4 parameter count mismatch")
    return m4_model, {"checkpoint_sha256":M4_CHECKPOINT_SHA,"artifact_manifest_files":len(m4_manifest["files"]),
                      "model_schema":meta["model_schema"],"input_schema":meta["input_schema"],
                      "parameter_count":m4_model.trainable_parameter_count,
                      "m3_release_id":release["release_id"],"m3_manifest_sha256":release_sha,
                      "m4_metadata_sha256":sha_file(M4_DIR/"pretrained-behavior-only.pt.manifest.json")},meta


def _opponent_and_color(ep: int):
    types=(RandomLegalAgent,SimpleHeuristicAgent,RandomLegalAgent,SimpleHeuristicAgent)
    colors=(chess.WHITE,chess.WHITE,chess.BLACK,chess.BLACK)
    return types[ep%4](),colors[ep%4]


def _snapshot_name(run_id: str, arm: str, seed: int, stage: str, decisions: int,attempt_index: int=0) -> str:
    return f"{run_id}__{arm}__seed-{seed}__attempt-{attempt_index:04d}__stage-{stage}__decisions-{decisions:06d}__eval-snapshot-v2.pt"


def _representation_state(model: Any) -> dict[str,torch.Tensor]:
    return {k:v for k,v in model.state_dict().items() if not k.startswith(("q_head.","behavior_head."))}


def _compatible_initialization_metadata(actual:dict[str,Any],expected:dict[str,Any])->bool:
    if actual==expected: return True
    old_code=actual.get("code_sha256")
    if old_code not in RECOVERY_COMPATIBLE_CODE_SHA256: return False
    normalized=dict(actual); normalized["code_sha256"]=expected.get("code_sha256")
    return normalized==expected


def _model_state_sha256(state:dict[str,torch.Tensor])->str:
    return hashlib.sha256(b"".join(k.encode()+v.detach().cpu().contiguous().numpy().tobytes()
                                    for k,v in sorted(state.items()))).hexdigest()


def _save_initialization_pair(seed: int, m4_model: Any, m4_meta: dict[str,Any], transfer: dict[str,Any]) -> dict[str,Any]:
    config=load_config(); schedule=paired_seed_schedule(EXPERIMENT_ID,seed,0); pair_id=pair_identity(EXPERIMENT_ID,seed)
    paths={}; models={}
    for arm in ("warm","scratch"):
        rid=run_identity(pair_id,arm,0); run_dir=ARTIFACT_ROOT/"runs"/rid; run_dir.mkdir(parents=True,exist_ok=True)
        if arm=="warm":
            model=make_warm_scorer(m4_model,q_head_seed=int(schedule["q_head_initialization_seed"]))
        else:
            model=make_scratch_scorer(representation_seed=int(schedule["scratch_representation_initialization_seed"]),
                                      q_head_seed=int(schedule["q_head_initialization_seed"]))
        models[arm]=model
        target_model=clone_target(model)
        target_equal=all(torch.equal(v,target_model.state_dict()[k]) for k,v in model.state_dict().items())
        if not target_equal or any(k.startswith("behavior_head.") for k in model.state_dict()):
            raise ValueError("initial Q model/target or output-head contract failed")
        shared=_representation_state(model)
        shared_hash=_model_state_sha256(shared)
        q_hash=hashlib.sha256(b"".join(v.detach().cpu().contiguous().numpy().tobytes() for k,v in sorted(model.state_dict().items()) if k.startswith("q_head."))).hexdigest()
        online_hash=_model_state_sha256(model.state_dict()); target_hash=_model_state_sha256(target_model.state_dict())
        if online_hash!=target_hash: raise ValueError("target/online initialization hashes differ")
        meta={"schema":"videochess-ddqn-evaluation-snapshot/2.0","resumable":False,
              "experiment_id":EXPERIMENT_ID,"pair_id":pair_id,"run_id":rid,"arm":arm,"training_seed":seed,
              "attempt_index":0,"stage":"pre_rl","valid_decisions":0,"optimizer_updates":0,"completed_episodes":0,
              "model_config":model.config.as_json(),"model_schema":model.config.model_schema,"input_schema":model.config.input_schema,
              "seed_schedule":schedule,"m4_source_sha256":M4_CHECKPOINT_SHA if arm=="warm" else None,
              "shared_representation_sha256":shared_hash,"q_head_sha256":q_hash,"online_sha256":online_hash,
              "target_sha256":target_hash,"target_initially_equal":target_equal,
              "behavior_head_transferred":False,"stockfish_required_for_inference":False,
              "config_sha256":config_hash(),"code_sha256":source_hash()}
        snap=run_dir/_snapshot_name(rid,arm,seed,"pre_rl",0)
        sidecar=snap.with_suffix(snap.suffix+".manifest.json")
        if snap.exists() or sidecar.exists():
            frozen,old_meta=load_evaluation_snapshot(snap)
            if not _compatible_initialization_metadata(old_meta,meta) or any(not torch.equal(v,frozen.state_dict()[k]) for k,v in model.state_dict().items()):
                raise ValueError("existing pre-RL snapshot differs from its deterministic initialization")
            manifest=json.loads(sidecar.read_text())
        else:
            manifest=save_evaluation_snapshot(snap,model,metadata=meta)
        init={"identity":{k:meta[k] for k in ("experiment_id","pair_id","run_id","arm","training_seed","attempt_index")},
              "seed_schedule":schedule,"m4_source":transfer if arm=="warm" else None,
              "source_model_schema":m4_meta["model_schema"] if arm=="warm" else None,
              "shared_representation_sha256":shared_hash,"q_head_sha256":q_hash,
              "online_sha256":online_hash,"target_sha256":target_hash,
              "behavior_head_transferred":False,"target_initially_equal":target_equal,
              "pre_rl_snapshot":{"path":str(snap.relative_to(ROOT)),**manifest}}
        init_path=run_dir/"initialization-manifest.json"
        if init_path.exists():
            if json.loads(init_path.read_text())!=init:
                raise ValueError("existing initialization manifest conflicts with current accepted source/config")
        else: json_write(init_path,init)
        paths[arm]=str(snap); models[arm]=model
    # Paired Q-head seed and protocol should yield exactly equal fresh Q-head tensors.
    for name in ("weight","bias"):
        if not torch.equal(models["warm"].q_head.state_dict()[name],models["scratch"].q_head.state_dict()[name]):
            raise ValueError("paired Q-head initialization is not equal across arms")
    if _representation_state(models["warm"]).keys() != m4_model.m5_transfer_state().keys():
        raise ValueError("M4 shared representation key set mismatch")
    for key,value in m4_model.m5_transfer_state().items():
        if not torch.equal(value,models["warm"].state_dict()[key].cpu()):
            raise ValueError(f"warm shared representation differs from M4 at {key}")
    if paths["warm"] and models["warm"].m5_transfer_state().keys():
        warm_shared=_model_state_sha256(_representation_state(models["warm"]))
        scratch_shared=_model_state_sha256(_representation_state(models["scratch"]))
        if warm_shared==scratch_shared: raise ValueError("Scratch representation unexpectedly matches Warm-start")
    return {"seed":seed,"pair_id":pair_id,"snapshots":paths,
            "warm_shared_equals_m4":True,"warm_behavior_head_excluded":True,
            "paired_q_head_equal":True,"scratch_shared_independent":True}


def _load_existing_ledger() -> dict[str,Any]:
    path=ARTIFACT_ROOT/"resource-ledger.json"
    if path.exists(): return json.loads(path.read_text())
    return {"schema":"videochess-m5-resource-ledger/1.0","campaign_started_at_utc":datetime.now(timezone.utc).isoformat(),
            "profile_seconds":0.0,"failed_profile_seconds_unverified_but_conservatively_charged":0.0,
            "recovery_validation_seconds":0.0,"run_seconds":{},"evaluation_seconds":{},"events":[]}


def run_real_replay_probe(threads: list[int] | None = None) -> dict[str,Any]:
    config=load_config(); train=config["training"]; ARTIFACT_ROOT.mkdir(parents=True,exist_ok=True)
    # Match the authorized profile/training inter-op setting before PyTorch initializes parallel work.
    torch.set_num_interop_threads(1)
    profile_root=ARTIFACT_ROOT/"feasibility"; profile_root.mkdir(parents=True,exist_ok=True)
    existing=[int(p.name.removeprefix("profile-attempt-")) for p in profile_root.glob("profile-attempt-*")
              if p.is_dir() and p.name.removeprefix("profile-attempt-").isdigit()]
    profile_attempt=max(existing,default=-1)+1
    probe_dir=profile_root/f"profile-attempt-{profile_attempt:04d}"; probe_dir.mkdir(parents=True,exist_ok=False)
    started=time.monotonic(); m4_model,transfer,m4_meta=verify_transfer_inputs()
    seed=config["training"]["paired_seeds"][0]; schedule=paired_seed_schedule(EXPERIMENT_ID,seed,0)
    model=make_scratch_scorer(representation_seed=int(schedule["scratch_representation_initialization_seed"]),
                              q_head_seed=int(schedule["q_head_initialization_seed"]))
    learner=DoubleDqnLearner(model,seed=int(schedule["replay_sampling_rng_seed"]),
                             exploration_seed=int(schedule["exploration_rng_seed"]),
                             config={"replay_capacity":16384,"replay_warmup_transitions":1024,"batch_size":32,
                                     "learning_rate":1e-4,"weight_decay":1e-4,"update_interval_decisions":4,
                                     "gamma":.99,"target_sync_interval_gradient_updates":500,"gradient_clip_norm":1.0})
    journal=ReplayJournal(probe_dir/"real-replay.journal.jsonl")
    candidate_counts=[]; history_lengths=[]; decision_times=[]; reset_times=[]; completed_episodes=0; last_episode_end=0
    while learner.valid_decisions < 1024 or learner.valid_decisions != last_episode_end:
        ep=completed_episodes
        es=paired_seed_schedule(EXPERIMENT_ID,seed,ep)
        opponent,color=_opponent_and_color(ep)
        sim=ChessSimulator(opponent,max_decisions=400)
        reset_started=time.perf_counter()
        observation=sim.reset(seed=int(es["episode_seed"]),opponent_seed=int(es["opponent_rng_seed"]),agent_color=color)
        reset_times.append(time.perf_counter()-reset_started)
        while True:
            t0=time.perf_counter(); before=observation
            features=_features(tuple(before.history_uci))
            candidate_counts.append(features.candidate_count); history_lengths.append(features.history_length)
            action=select_action(learner.online,features,epsilon=epsilon_at(learner.valid_decisions),
                                 rng=learner.exploration_rng,device=learner.device)
            result=sim.step_uci(action)
            row=Transition.from_step(before,result,run_id=f"m5-real-replay-profile-{profile_attempt:04d}",attempt_id=f"profile-attempt-{profile_attempt:04d}",
                                    episode_index=ep,decision_index=learner.valid_decisions,training_seed=seed,seed_schedule=es)
            learner.replay.insert(row); learner.transitions+=1; learner.valid_decisions+=1
            jhead=journal.append(row); observation=result.observation
            decision_times.append(time.perf_counter()-t0)
            if result.terminated or result.truncated:
                learner.completed_episodes+=1; completed_episodes+=1; last_episode_end=learner.valid_decisions
                break
    replay_state=learner.replay.state_dict()
    updates=[]; thread_records=[]; original_threads=torch.get_num_threads()
    for count in (threads or [1,2,4]):
        if count<1: continue
        torch.set_num_threads(count)
        test_model=make_scratch_scorer(representation_seed=int(schedule["scratch_representation_initialization_seed"]),
                                      q_head_seed=int(schedule["q_head_initialization_seed"]))
        probe=DoubleDqnLearner(test_model,seed=int(schedule["replay_sampling_rng_seed"]),
                               exploration_seed=int(schedule["exploration_rng_seed"]),device="cpu",
                               config={"replay_capacity":16384,"replay_warmup_transitions":1024,"batch_size":32,
                                       "learning_rate":1e-4,"weight_decay":1e-4,"update_interval_decisions":4,
                                       "gamma":.99,"target_sync_interval_gradient_updates":500,"gradient_clip_norm":1.0})
        probe.replay=ReplayBuffer.from_state_dict(replay_state); probe.valid_decisions=learner.valid_decisions
        times=[]
        for _ in range(5):
            t0=time.perf_counter(); result=probe.update(); times.append(time.perf_counter()-t0)
            if result is None: raise RuntimeError("actual replay did not satisfy the configured warm-up")
        thread_records.append({"torch_threads":count,"update_seconds":times,"mean":float(np.mean(times)),
                               "p95_empirical":float(np.quantile(times,.95)),"max":max(times)})
    torch.set_num_threads(original_threads)
    # Measure an actual immutable episode-boundary bundle and journal prefix cost.
    ckpt_dir=probe_dir/"checkpoint-cost"; ckpt_dir.mkdir(exist_ok=True)
    checkpoint_learner=DoubleDqnLearner(make_scratch_scorer(representation_seed=int(schedule["scratch_representation_initialization_seed"]),
        q_head_seed=int(schedule["q_head_initialization_seed"])),seed=int(schedule["replay_sampling_rng_seed"]),
        exploration_seed=int(schedule["exploration_rng_seed"]))
    checkpoint_learner.replay=ReplayBuffer.from_state_dict(replay_state)
    checkpoint_learner.online.load_state_dict(probe.online.state_dict(),strict=True)
    checkpoint_learner.target.load_state_dict(probe.target.state_dict(),strict=True)
    checkpoint_learner.optimizer.load_state_dict(probe.optimizer.state_dict())
    checkpoint_learner.valid_decisions=learner.valid_decisions; checkpoint_learner.transitions=learner.transitions
    checkpoint_learner.completed_episodes=learner.completed_episodes
    checkpoint_learner.optimizer_updates=probe.optimizer_updates
    cp=ckpt_dir/"probe-episode-boundary.pt"; t0=time.perf_counter()
    cp_manifest=save_training_checkpoint(cp,checkpoint_learner,identity={"run_id":"probe","arm":"scratch","training_seed":seed,
        "code_sha256":source_hash(),"config_sha256":config_hash()},journal=journal,journal_head=jhead,
        episode_complete=True,resource_accounting={"probe":True,"elapsed_seconds":time.monotonic()-started})
    checkpoint_seconds=time.perf_counter()-t0
    obs_mean=float(np.mean(decision_times)); obs_p95=float(np.quantile(decision_times,.95))
    selected=min(thread_records,key=lambda row:row["mean"])
    avg_episode=learner.valid_decisions/max(1,learner.completed_episodes)
    episode_count=50000/avg_episode
    boot_rng=np.random.default_rng(20261128)
    boot_means=np.asarray([boot_rng.choice(np.asarray(decision_times),size=len(decision_times),replace=True).mean()
                           for _ in range(1000)],dtype=np.float64)
    decision_mean_upper=float(np.quantile(boot_means,.95))
    projected_run_mean=50000*obs_mean + episode_count*float(np.mean(reset_times)) + 12500*selected["mean"] + episode_count*checkpoint_seconds
    projected_run_upper95=50000*decision_mean_upper + episode_count*float(np.quantile(reset_times,.95)) + 12500*selected["p95_empirical"] + episode_count*checkpoint_seconds
    report={"schema":"videochess-m5-real-replay-feasibility/1.0","profile_attempt":profile_attempt,
        "recorded_at_utc":datetime.now(timezone.utc).isoformat(),
        "code":code_identity(),"config_sha256":config_hash(),"environment":environment_identity(),"transfer":transfer,
        "probe":{"valid_transitions":learner.transitions,"valid_agent_decisions":learner.valid_decisions,
                 "completed_episodes":learner.completed_episodes,"simulator_with_policy_decisions_per_second":1/obs_mean,
                 "decision_latency_seconds":{"mean":obs_mean,"p95":float(np.quantile(decision_times,.95)),"max":max(decision_times)},
                 "simulator_reset_seconds":{"mean":float(np.mean(reset_times)),"p95":float(np.quantile(reset_times,.95)),"samples":len(reset_times)},
                 "candidate_count":{"mean":float(np.mean(candidate_counts)),"p95":float(np.quantile(candidate_counts,.95)),"max":max(candidate_counts)},
                 "history_length":{"mean":float(np.mean(history_lengths)),"p95":float(np.quantile(history_lengths,.95)),"max":max(history_lengths)},
                 "replay_size":len(learner.replay),"replay_journal_bytes":journal.path.stat().st_size,
                 "updates_on_disposable_model_copy":thread_records,"checkpoint_seconds":checkpoint_seconds,
                 "checkpoint_bytes":cp_manifest["size_bytes"],"checkpoint_sha256":cp_manifest["sha256"],
                 "peak_process_rss_bytes":peak_rss_bytes()},
        "projection":{"selected_cpu_threads":selected["torch_threads"],"projected_seconds_per_50000_run_mean":projected_run_mean,
                      "projected_seconds_per_50000_run_upper95":projected_run_upper95,
                      "per_run_cap_seconds":8*3600,"projected_campaign_seconds_including_measured_probe":6*projected_run_upper95+(time.monotonic()-started),
                      "campaign_cap_seconds":60*3600,"fits_run_cap":projected_run_upper95<8*3600,
                      "fits_campaign_cap":6*projected_run_upper95+(time.monotonic()-started)<60*3600,
                      "decision_mean_bootstrap_replicates":1000,"decision_mean_upper95_seconds":decision_mean_upper,
                      "small_sample_caveat":"Decision latency upper bound resamples the measured real-M2 decision mean; five actual-replay updates give a noisy update-tail estimate. Projection includes reset and amortized checkpoint costs."},
        "backend":{"local_cpu_available":True,"colab_cpu_t4_accessible":False,"t4_sessions_active":0,
                   "selected_backend":"local_cpu" if projected_run_upper95<8*3600 else None},
        "not_official_training":True,"official_paired_campaign_started":False}
    report["projection"]["projected_campaign_seconds_including_measured_probe"]=6*projected_run_upper95+(time.monotonic()-started)
    if report["projection"]["fits_run_cap"] and report["projection"]["fits_campaign_cap"]:
        # Freeze the measured backend and thread configuration before any official run.
        config["training"]["compute_backend"]="local_cpu"
        config["training"]["torch_threads"]={"intra_op":selected["torch_threads"],"inter_op":1}
        config["training"]["backend_selection"]={"selected":"local_cpu","selected_at_utc":report["recorded_at_utc"],
            "decision_basis":"measured M2 simulator + legal-candidate inference + real replay batch-32 updates + checkpoint serialization",
            "cpu_thread_benchmarks":thread_records,"colab_cpu_t4_accessible":False,
            "t4_preference_threshold_end_to_end_speedup":0.20,"selected_by":selected["torch_threads"]}
        json_write(CONFIG_PATH,config)
        report["profile_config_sha256"] = report["config_sha256"]
        report["config_sha256"] = config_hash()
        report["backend"]["torch_threads_frozen"]={"intra_op":selected["torch_threads"],"inter_op":1}
    report_path=probe_dir/"real-replay-feasibility.json"
    json_write(report_path,report)
    ledger=_load_existing_ledger(); ledger["profile_seconds"]+=time.monotonic()-started
    ledger["events"].append({"kind":"real_replay_profile","at_utc":report["recorded_at_utc"],
                             "duration_seconds":time.monotonic()-started,"report_path":str(report_path.relative_to(ROOT)),
                             "report_sha256":sha_file(report_path)})
    json_write(ARTIFACT_ROOT/"resource-ledger.json",ledger)
    # Retain work product and exact content inventory.
    files=[]
    for path in sorted(probe_dir.rglob("*")):
        if path.is_file() and path.name!="artifact_manifest.json": files.append({"path":path.relative_to(probe_dir).as_posix(),"sha256":sha_file(path),"size_bytes":path.stat().st_size})
    json_write(probe_dir/"artifact_manifest.json",{"schema":"videochess-m5-artifacts/1.0","files":files})
    return report


def _attempt_dirs(pair_id: str,arm: str) -> list[tuple[int,Path]]:
    prefix=f"m5-{pair_id}__{arm}__attempt-"
    root=ARTIFACT_ROOT/"runs"
    result=[]
    if root.exists():
        for path in root.glob(prefix+"*"):
            suffix=path.name.removeprefix(prefix)
            if path.is_dir() and suffix.isdigit(): result.append((int(suffix),path))
    return sorted(result)


def _latest_verified_resume(pair_id: str,arm: str,seed: int) -> tuple[Path|None,dict[str,Any]|None]:
    expected={"experiment_id":EXPERIMENT_ID,"pair_id":pair_id,"arm":arm,"training_seed":seed,
              "config_sha256":config_hash()}
    compatible_code_hashes=RECOVERY_COMPATIBLE_CODE_SHA256 | {source_hash()}
    candidates=[]; errors=[]
    for _,directory in _attempt_dirs(pair_id,arm):
        for path in directory.glob("*__resume-v2.pt"):
            match=re.search(r"__episodes-(\d+)__decisions-(\d+)__resume-v2\.pt$",path.name)
            order=(int(match.group(1)),int(match.group(2))) if match else (-1,-1)
            candidates.append((order,path))
    for _,path in sorted(candidates,key=lambda x:x[0],reverse=True):
        try:
            # Order immutable checkpoints from their counters in the filename.
            # Load and verify newest first, checking the full journal once; an
            # older journal prefix is only read if the newest bundle is invalid.
            bundle=load_training_checkpoint_bundle(path,verify_journal=False)
            if bundle.get("identity",{}).get("code_sha256") not in compatible_code_hashes:
                raise ValueError("checkpoint code identity is not current or explicitly recovery-compatible")
            if any(bundle.get("identity",{}).get(k)!=v for k,v in expected.items()):
                raise ValueError("checkpoint identity is incompatible with this paired run")
            verify_training_checkpoint(path,verify_journal=True)
            return path,bundle
        except Exception as exc:
            errors.append(f"{path.name}: {type(exc).__name__}: {exc}")
    if candidates:
        raise ValueError("no valid compatible M5 recovery checkpoint remains: "+"; ".join(errors))
    return None,None


def _latest_completed_summary(pair_id: str,arm: str) -> dict[str,Any]|None:
    for _,directory in reversed(_attempt_dirs(pair_id,arm)):
        path=directory/"run-summary.json"
        if path.exists():
            row=json.loads(path.read_text())
            if row.get("completion")=="complete" and row.get("valid_decisions")==50000: return row
    return None


def train_campaign() -> dict[str,Any]:
    _require_unfinalized_artifact_root(ARTIFACT_ROOT)
    config=load_config(); ARTIFACT_ROOT.mkdir(parents=True,exist_ok=True)
    campaign_start_wall=datetime.now(timezone.utc).isoformat()
    setup_started=time.monotonic(); ledger=_load_existing_ledger()
    train=config["training"]
    if train.get("compute_backend")!="local_cpu" or not isinstance(train.get("torch_threads"),dict):
        raise RuntimeError("official training requires a completed feasibility gate and frozen backend/thread configuration")
    state=json.loads((ROOT/".agents/state/PROJECT_STATE.yaml").read_text())
    task=next(t for t in json.loads((ROOT/".agents/tasks/BACKLOG.yaml").read_text())["tasks"] if t["id"]=="M5-001")
    if state["engineering"].get("active_milestone")!="M5" or state["engineering"].get("next_milestone_status")!="in_progress" or not state["engineering"].get("start_authorized") or task.get("status")!="in_progress":
        raise RuntimeError("canonical state does not authorize the active M5-001 campaign")
    reports=sorted((ARTIFACT_ROOT/"feasibility").glob("profile-attempt-*/real-replay-feasibility.json"))
    if not reports: raise RuntimeError("real-replay feasibility report is missing")
    feasibility=json.loads(reports[-1].read_text())
    if not feasibility["projection"].get("fits_run_cap") or not feasibility["projection"].get("fits_campaign_cap"):
        raise RuntimeError("real-replay feasibility gate did not pass")
    torch.set_num_threads(int(train["torch_threads"]["intra_op"]))
    torch.set_num_interop_threads(int(train["torch_threads"]["inter_op"]))
    runtime_inputs=[".agents/state/PROJECT_STATE.yaml", ".agents/tasks/BACKLOG.yaml",
                    reports[-1].relative_to(ROOT).as_posix()]
    ledger_path=ARTIFACT_ROOT/"resource-ledger.json"
    if ledger_path.is_file(): runtime_inputs.append(ledger_path.relative_to(ROOT).as_posix())
    source_snapshot=capture_source_snapshot(ROOT,ARTIFACT_ROOT/"source-snapshots",additional_files=runtime_inputs)
    if source_snapshot["source_sha256"]!=source_hash() or source_snapshot["configuration_sha256"]!=config_hash():
        raise RuntimeError("captured source/configuration bundle differs from the live M5 training inputs")
    m4_model,transfer,m4_meta=verify_transfer_inputs()
    init=[]
    for seed in train["paired_seeds"]: init.append(_save_initialization_pair(seed,m4_model,m4_meta,transfer))
    init_summary={"config_sha256":config_hash(),"m4_transfer":transfer,"pairs":init}
    init_path=ARTIFACT_ROOT/"initialization-summary.json"
    if init_path.exists() and json.loads(init_path.read_text())!=init_summary:
        raise ValueError("existing paired initialization summary changed")
    if not init_path.exists(): json_write(init_path,init_summary)
    setup_seconds=time.monotonic()-setup_started
    ledger["training_setup_seconds"]=float(ledger.get("training_setup_seconds",0))+setup_seconds
    ledger["last_updated_at_utc"]=datetime.now(timezone.utc).isoformat()
    json_write(ARTIFACT_ROOT/"resource-ledger.json",ledger)
    def committed_campaign_seconds():
        return (float(ledger.get("profile_seconds",0))
            +float(ledger.get("failed_profile_seconds_unverified_but_conservatively_charged",0))
            +float(ledger.get("recovery_validation_seconds",0))
            +float(ledger.get("training_setup_seconds",0))
            +sum(float(x) for x in ledger.get("run_seconds",{}).values()))
    total_used=committed_campaign_seconds(); run_summaries=[]; campaign_incomplete=False
    campaign_start=time.monotonic()
    for seed in train["paired_seeds"]:
        pair_id=pair_identity(EXPERIMENT_ID,seed)
        schedule=paired_seed_schedule(EXPERIMENT_ID,seed,0)
        for arm in ("warm","scratch"):
            completed=_latest_completed_summary(pair_id,arm)
            if completed is not None:
                run_summaries.append(completed); continue
            prior_dirs=[item for item in _attempt_dirs(pair_id,arm)
                        if (item[1]/"attempt-record.json").exists() or (item[1]/"replay.journal.jsonl").exists()
                        or (item[1]/"run-summary.json").exists()]
            previous_incomplete=[]
            for _,previous_dir in prior_dirs:
                previous_summary=previous_dir/"run-summary.json"
                if previous_summary.exists():
                    previous=json.loads(previous_summary.read_text())
                    previous_incomplete.append(previous)
            if previous_incomplete:
                # A recorded hard stop is terminal for this authorized budget; do not silently retry it.
                run_summaries.append(previous_incomplete[-1]); campaign_incomplete=True; break
            attempt_start=time.monotonic()
            if arm=="warm": online=make_warm_scorer(m4_model,q_head_seed=int(schedule["q_head_initialization_seed"]))
            else: online=make_scratch_scorer(representation_seed=int(schedule["scratch_representation_initialization_seed"]),
                                             q_head_seed=int(schedule["q_head_initialization_seed"]))
            learner=DoubleDqnLearner(online,seed=int(schedule["replay_sampling_rng_seed"]),
                exploration_seed=int(schedule["exploration_rng_seed"]),device="cpu",
                config={"replay_capacity":16384,"replay_warmup_transitions":1024,"batch_size":32,
                        "learning_rate":1e-4,"weight_decay":1e-4,"update_interval_decisions":4,"gamma":.99,
                        "target_sync_interval_gradient_updates":500,"gradient_clip_norm":1.0})
            resume_path,resume_bundle=_latest_verified_resume(pair_id,arm,seed)
            if resume_path:
                resume_code_sha=resume_bundle["identity"].get("code_sha256")
                current_code_sha=source_hash()
                if resume_code_sha not in RECOVERY_COMPATIBLE_CODE_SHA256 | {current_code_sha}:
                    raise ValueError("resume checkpoint code identity is not explicitly compatible")
                resume_code_compatibility=None if resume_code_sha==current_code_sha else {
                    "from_source_sha256":resume_code_sha,"to_source_sha256":current_code_sha,
                    "reason":"weights-only recovery compatibility for TorchVersion environment metadata; no model, transition, optimizer, RNG, or scientific configuration change"}
                restored=restore_training_checkpoint(resume_path,learner,expected_identity={"experiment_id":EXPERIMENT_ID,
                    "pair_id":pair_id,"arm":arm,"training_seed":seed,"config_sha256":config_hash()})
                resume_parent_sha=sha_file(resume_path)
            else:
                restored=None; resume_parent_sha=None; resume_code_compatibility=None
            attempt_index=(prior_dirs[-1][0]+1) if prior_dirs else 0
            rid=run_identity(pair_id,arm,attempt_index); attempt_id=f"attempt-{attempt_index:04d}"
            run_dir=ARTIFACT_ROOT/"runs"/rid
            if run_dir.exists():
                if attempt_index!=0 or not (run_dir/"initialization-manifest.json").exists() or (run_dir/"attempt-record.json").exists():
                    raise FileExistsError(f"refusing to reuse M5 attempt directory {run_dir}")
            else: run_dir.mkdir(parents=True,exist_ok=False)
            journal=ReplayJournal(run_dir/"replay.journal.jsonl")
            journal_head={"record_count":0,"chain_sha256":"0"*64}
            if resume_path:
                for retained in learner.replay.transitions: journal_head=journal.append(retained)
                old_journal=resume_bundle["journal"]
                with Path(old_journal["path"]).open("rb") as stream:
                    old_count=sum(1 for _ in stream)
                old_dir=resume_path.parent
                incomplete_record={"schema":"videochess-m5-attempt-segment/1.0","status":"abandoned_and_recovered",
                    "run_id":old_dir.name,"attempt_id":old_dir.name.rsplit("attempt-",1)[-1],
                    "resume_checkpoint":str(resume_path.relative_to(ROOT)),"resume_checkpoint_sha256":resume_parent_sha,
                    "committed_decisions_at_checkpoint":int(resume_bundle["counters"]["valid_decisions"]),
                    "abandoned_journal_transitions_after_checkpoint":max(0,old_count-int(old_journal["record_count"])),
                    "logical_decisions_double_counted":False,"physical_time_still_charged":True,
                    "recovery_started_at_utc":datetime.now(timezone.utc).isoformat()}
                incomplete_path=old_dir/"attempt-segment-recovered.json"
                if not incomplete_path.exists(): json_write(incomplete_path,incomplete_record)
            elif prior_dirs:
                # No episode-boundary state existed; preserve, abandon and replay this uncommitted attempt from its immutable initialization.
                previous_dir=prior_dirs[-1][1]; previous_journal=previous_dir/"replay.journal.jsonl"
                abandoned_count=0
                if previous_journal.exists():
                    with previous_journal.open("rb") as stream: abandoned_count=sum(1 for _ in stream)
                marker={"schema":"videochess-m5-attempt-segment/1.0","status":"abandoned_before_first_verified_episode_checkpoint",
                        "run_id":previous_dir.name,"uncommitted_journal_transitions":abandoned_count,
                        "logical_decisions_double_counted":False,"physical_time_still_charged":True,
                        "recovery_started_at_utc":datetime.now(timezone.utc).isoformat()}
                marker_path=previous_dir/"attempt-segment-recovered.json"
                if not marker_path.exists(): json_write(marker_path,marker)
            run_start=attempt_start; last_ledger=attempt_start; last_attempt_record=0.0
            budget_key=f"{pair_id}:{arm}"
            run_base_seconds=float(ledger.get("run_seconds",{}).get(budget_key,0))
            run_cap=float(train["per_run_wall_minutes_hard_cap"])*60
            campaign_cap=float(train["aggregate_campaign_wall_hours_hard_cap"])*3600
            last_size_check=time.monotonic(); cached_artifact_size=artifact_size_bytes()
            attempt_doc={"schema":"videochess-m5-attempt/1.0","status":"running","run_id":rid,
                "attempt_id":attempt_id,"pair_id":pair_id,"arm":arm,"training_seed":seed,
                "source_snapshot":source_snapshot,
                "resume_parent_checkpoint_sha256":resume_parent_sha,"started_at_utc":datetime.now(timezone.utc).isoformat(),
                "resume_code_compatibility":resume_code_compatibility,
                "committed_counters_at_start":{"valid_decisions":learner.valid_decisions,
                    "completed_episodes":learner.completed_episodes,"optimizer_updates":learner.optimizer_updates}}
            json_write(run_dir/"attempt-record.json",attempt_doc)
            last_transition_id=None
            def stop_check():
                nonlocal last_size_check,cached_artifact_size
                now=time.monotonic()
                used=_campaign_usage_with_active_run(total_used,run_start,now)
                run_used=run_base_seconds+(now-run_start)
                if time.monotonic()-last_size_check>=5:
                    cached_artifact_size=artifact_size_bytes(); last_size_check=time.monotonic()
                return (run_used>=run_cap-60 or used>=campaign_cap-120
                    or peak_rss_bytes()>=int(train["local_process_rss_bytes_hard_cap"])
                    or cached_artifact_size>=int(train["artifact_directory_bytes_hard_cap"]))
            def on_transition(current:DoubleDqnLearner,row:Transition,update:Any):
                nonlocal journal_head,last_ledger,last_attempt_record,last_transition_id
                journal_head=journal.append(row); d=current.valid_decisions
                last_transition_id=row.transition_id
                if row.terminated or row.truncated:
                    with (run_dir/"episodes.jsonl").open("a",encoding="utf-8") as stream:
                        stream.write(json.dumps({"episode_index":row.episode_index,"agent_color":row.agent_color,
                            "opponent_id":row.opponent_id,"reward":row.reward,"terminated":row.terminated,
                            "truncated":row.truncated,"outcome_result":row.outcome_result,
                            "outcome_reason":row.outcome_reason,"truncation_reason":row.truncation_reason,
                            "valid_decisions":d},sort_keys=True,separators=(",",":"))+"\n")
                if d in (10000,20000,30000,40000,50000):
                    meta={"schema":"videochess-ddqn-evaluation-snapshot/2.0","resumable":False,
                        "experiment_id":EXPERIMENT_ID,"pair_id":pair_id,"run_id":rid,"arm":arm,
                        "training_seed":seed,"attempt_index":attempt_index,"stage":"post_rl" if d==50000 else f"decisions_{d}",
                        "valid_decisions":d,"transitions":current.transitions,"optimizer_updates":current.optimizer_updates,
                        "completed_episodes":current.completed_episodes,"epsilon":epsilon_at(d),
                        "model_config":current.online.config.as_json(),"seed_schedule":schedule,
                        "m4_source_sha256":M4_CHECKPOINT_SHA if arm=="warm" else None,
                        "config_sha256":config_hash(),"code_sha256":source_hash(),"target_syncs":current.target_syncs,
                        "target_sha256":hashlib.sha256(b"".join(t.detach().cpu().contiguous().numpy().tobytes() for t in current.target.state_dict().values())).hexdigest(),
                        "capture_order":config["training"]["evaluation_snapshot_capture_order"]}
                    save_evaluation_snapshot(run_dir/_snapshot_name(rid,arm,seed,meta["stage"],d,attempt_index),current.online,metadata=meta)
                if row.terminated or row.truncated:
                    checkpoint=run_dir/f"{rid}__{arm}__seed-{seed}__attempt-{attempt_index:04d}__episodes-{current.completed_episodes:05d}__decisions-{d:06d}__resume-v2.pt"
                    init_manifest_path=ARTIFACT_ROOT/"runs"/run_identity(pair_id,arm,0)/"initialization-manifest.json"
                    save_training_checkpoint(checkpoint,current,identity={"experiment_id":EXPERIMENT_ID,"pair_id":pair_id,
                        "run_id":rid,"attempt_id":attempt_id,"arm":arm,"training_seed":seed,
                        "code_sha256":source_hash(),"config_sha256":config_hash(),
                        "m4_source_sha256":M4_CHECKPOINT_SHA if arm=="warm" else None,
                        "m3_release_id":transfer["m3_release_id"],"m3_manifest_sha256":transfer["m3_manifest_sha256"],
                        "initialization_manifest_sha256":sha_file(init_manifest_path),
                        "seed_schedule_schema":config["seed_derivation"]["schema"],
                        "rng_root_seeds":schedule,"episode_seed_schedule":row.seed_schedule,
                        "episode_index":row.episode_index,"agent_color":row.agent_color,
                        "opponent_id":row.opponent_id,"opponent_config_json":row.opponent_config_json,
                        "opponent_color_schedule":config["training"]["opponent_color_schedule"],
                        "transition_schema":"videochess-ddqn-transition/1.0","replay_schema":"videochess-ddqn-replay/1.0",
                        "input_schema":current.online.config.input_schema,"model_schema":current.online.config.model_schema,
                        "environment":environment_identity()},journal=journal,journal_head=journal_head,
                        episode_complete=True,resource_accounting={"logical_run_physical_seconds":run_base_seconds+(time.monotonic()-run_start),
                        "attempt_elapsed_seconds":time.monotonic()-run_start,
                        "campaign_seconds":_campaign_usage_with_active_run(total_used,run_start,time.monotonic())})
                now=time.monotonic()
                if now-last_ledger>=5:
                    delta=now-last_ledger
                    ledger.setdefault("run_seconds",{})[budget_key]=float(ledger.get("run_seconds",{}).get(budget_key,0))+delta
                    ledger.setdefault("attempt_seconds",{})[rid]=float(ledger.get("attempt_seconds",{}).get(rid,0))+delta
                    ledger["last_updated_at_utc"]=datetime.now(timezone.utc).isoformat()
                    json_write(ARTIFACT_ROOT/"resource-ledger.json",ledger); last_ledger=now
                if now-last_attempt_record>=30:
                    attempt_doc.update({"updated_at_utc":datetime.now(timezone.utc).isoformat(),
                        "committed_counters":{"valid_decisions":current.valid_decisions,"transitions":current.transitions,
                        "optimizer_updates":current.optimizer_updates,"completed_episodes":current.completed_episodes,
                        "target_syncs":current.target_syncs},"elapsed_attempt_seconds":now-run_start,
                        "run_budget_seconds":run_base_seconds+now-run_start,"peak_process_rss_bytes":peak_rss_bytes()})
                    json_write(run_dir/"attempt-record.json",attempt_doc); last_attempt_record=now
                return stop_check()
            result=run_training_episodes(learner,training_seed=seed,arm=arm,run_id=rid,attempt_id=attempt_id,
                max_decisions=50000,device="cpu",on_transition=on_transition,stop_check=stop_check)
            if result["final_episode_incomplete"]:
                json_write(run_dir/"incomplete-episode-at-decision-cap.json",{
                    "schema":"videochess-m5-incomplete-episode/1.0","episode_index":learner.completed_episodes,
                    "valid_decisions":learner.valid_decisions,"last_committed_transition_id":last_transition_id,
                    "terminated":None,"truncated":None,"reward":None,"simulator_reset":False,
                    "reason":"exact_50000_decision_cap_reached_mid_episode"})
            duration=time.monotonic()-run_start; final_delta=time.monotonic()-last_ledger
            ledger.setdefault("run_seconds",{})[budget_key]=float(ledger.get("run_seconds",{}).get(budget_key,0))+final_delta
            ledger.setdefault("attempt_seconds",{})[rid]=float(ledger.get("attempt_seconds",{}).get(rid,0))+final_delta
            ledger["last_updated_at_utc"]=datetime.now(timezone.utc).isoformat(); json_write(ARTIFACT_ROOT/"resource-ledger.json",ledger)
            completion="complete" if result["valid_decisions"]==50000 else "incomplete"
            summary={**result,"run_id":rid,"attempt_id":attempt_id,"pair_id":pair_id,"config_sha256":config_hash(),
                "code":code_identity(),"source_snapshot":source_snapshot,"environment":environment_identity(),
                "initialization":str((ARTIFACT_ROOT/"runs"/run_identity(pair_id,arm,0)/"initialization-manifest.json").relative_to(ROOT)),
                "m4_source_sha256":M4_CHECKPOINT_SHA if arm=="warm" else None,"peak_process_rss_bytes":peak_rss_bytes(),
                "replay_journal_bytes":journal.path.stat().st_size,"run_started_at_utc":attempt_doc["started_at_utc"],
                "attempt_wall_seconds":duration,"cumulative_run_physical_seconds":ledger["run_seconds"][budget_key],
                "completion":completion,"stop_reason":result["stop_reason"],"resume_parent_checkpoint_sha256":resume_parent_sha}
            attempt_doc.update({"status":completion,"finished_at_utc":datetime.now(timezone.utc).isoformat(),
                "committed_counters":{"valid_decisions":learner.valid_decisions,"transitions":learner.transitions,
                    "optimizer_updates":learner.optimizer_updates,"completed_episodes":learner.completed_episodes,
                    "target_syncs":learner.target_syncs},"run_budget_seconds":ledger["run_seconds"][budget_key],
                "stop_reason":result["stop_reason"]})
            json_write(run_dir/"attempt-record.json",attempt_doc); json_write(run_dir/"run-summary.json",summary)
            run_summaries.append(summary); total_used=committed_campaign_seconds()
            if completion!="complete":
                json_write(ARTIFACT_ROOT/"campaign-status.json",{"status":"incomplete","reason":result["stop_reason"],"run":summary})
                campaign_incomplete=True; break
        if campaign_incomplete: break
    report={"schema":"videochess-m5-training-campaign/1.0","config_sha256":config_hash(),
        "started_at_utc":campaign_start_wall,"duration_seconds":time.monotonic()-campaign_start,
        "runs":run_summaries,"planned_runs":6,"completed_runs":sum(r.get("completion")=="complete" for r in run_summaries),
        "source_snapshots":{row["source_snapshot"]["archive_sha256"]:row["source_snapshot"]
                            for row in run_summaries if row.get("source_snapshot")},
        "total_valid_decisions":sum(r.get("valid_decisions",0) for r in run_summaries),
        "total_cumulative_run_physical_seconds":sum(float(x) for x in ledger.get("run_seconds",{}).values()),
        "campaign_profile_recovery_and_setup_seconds":float(ledger.get("profile_seconds",0))+float(ledger.get("failed_profile_seconds_unverified_but_conservatively_charged",0))+float(ledger.get("recovery_validation_seconds",0))+float(ledger.get("training_setup_seconds",0)),
        "total_authorized_training_campaign_budget_consumed_seconds":committed_campaign_seconds(),
        "resource_ledger":str((ARTIFACT_ROOT/"resource-ledger.json").relative_to(ROOT)),"g3_approved":False,
        "status":"complete" if not campaign_incomplete and sum(r.get("completion")=="complete" for r in run_summaries)==6 else "incomplete"}
    json_write(ARTIFACT_ROOT/"training-campaign.json",report)
    return report


def run_evaluation() -> dict[str,Any]:
    config=load_config(); summary_path=ARTIFACT_ROOT/"training-campaign.json"
    if not summary_path.exists(): raise RuntimeError("training campaign has not produced its policy set")
    training=json.loads(summary_path.read_text())
    if training["completed_runs"]!=6 or training["total_valid_decisions"]!=300000:
        raise RuntimeError("evaluation requires all six completed 50,000-decision runs")
    eval_dir=ARTIFACT_ROOT/"evaluation"; eval_dir.mkdir(parents=True,exist_ok=True)
    all_seeds=tuple(config["evaluation"]["seeds"])
    scenario_keys={(seed,opp,color) for seed in all_seeds for opp in ("random_legal","simple_material_heuristic") for color in ("white","black")}
    ledger=_load_existing_ledger(); campaign_start=time.monotonic()
    overhead_start=time.monotonic()
    m4_model,transfer,m4_meta=verify_transfer_inputs()
    m4_policy=BehaviorPolicy(m4_model,checkpoint_sha256=M4_CHECKPOINT_SHA)
    policies=[("m4_behavior_only",m4_policy)]
    for seed in config["training"]["paired_seeds"]:
        pair=pair_identity(EXPERIMENT_ID,seed)
        for arm in ("warm","scratch"):
            initial_id=run_identity(pair,arm,0); initial_dir=ARTIFACT_ROOT/"runs"/initial_id
            run_record=next(r for r in training["runs"] if r.get("pair_id")==pair and r.get("arm")==arm and r.get("completion")=="complete")
            final_id=run_record["run_id"]; final_dir=ARTIFACT_ROOT/"runs"/final_id
            for stage,decisions,run_id,run_dir,attempt in (("pre_rl",0,initial_id,initial_dir,0),
                    ("post_rl",50000,final_id,final_dir,int(run_record["attempt_id"].split("-")[-1]))):
                candidate=run_dir/_snapshot_name(run_id,arm,seed,stage,decisions,attempt)
                model,meta=load_evaluation_snapshot(candidate)
                require_evaluation_snapshot_stage(meta,stage)
                sha=sha_file(candidate)
                policy_id=f"{arm}:{seed}:{stage}"
                policies.append((policy_id,QPolicy(model,policy_id=policy_id,checkpoint_sha256=sha)))
    policies += [("baseline:random_legal",RandomLegalAgent()),("baseline:simple_heuristic",SimpleHeuristicAgent())]
    if len(policies)!=15: raise RuntimeError(f"policy roster wrong: {len(policies)}")
    ledger["evaluation_overhead_seconds"]=float(ledger.get("evaluation_overhead_seconds",0))+(time.monotonic()-overhead_start)
    ledger["evaluation_campaign_seconds"]=float(ledger.get("evaluation_campaign_seconds",0))+(time.monotonic()-overhead_start)
    json_write(ARTIFACT_ROOT/"resource-ledger.json",ledger)

    def policy_slug(policy_id:str)->str: return hashlib.sha256(policy_id.encode()).hexdigest()[:16]
    journal_diagnostics: dict[str,list[dict[str,Any]]] = {}
    def prior_policy_rows(policy_id:str)->list[dict[str,Any]]:
        root=eval_dir/policy_slug(policy_id)
        rows,diagnostics=recover_policy_attempt_rows(root,policy_id)
        journal_diagnostics[policy_id]=diagnostics
        return rows
    for policy_id,policy in policies:
        base_rows=prior_policy_rows(policy_id)
        completed_keys={(r["evaluation_seed"],r["opponent_id"],r["agent_color"])
                        for r in base_rows if r.get("status")=="completed_game"}
        missing=scenario_keys-completed_keys
        policy_used=float(ledger.get("evaluation_seconds",{}).get(policy_id,0))
        campaign_used=float(ledger.get("evaluation_campaign_seconds",0))
        policy_remaining=max(0.0,40*60-policy_used)
        campaign_remaining=max(0.0,12*3600-campaign_used)
        if missing and policy_remaining>1 and campaign_remaining>1:
            root=eval_dir/policy_slug(policy_id); root.mkdir(parents=True,exist_ok=True)
            attempts=list(root.glob("events-attempt-*.jsonl"))+list(root.glob("rows-attempt-*.json"))
            attempt_idx=max((int(x.stem.split("-")[-1]) for x in attempts),default=-1)+1
            attempt_id=f"evaluation-attempt-{attempt_idx:04d}"
            journal=EvaluationEventJournal(root/f"events-attempt-{attempt_idx:04d}.jsonl",
                                           policy_id=policy_id,attempt_id=attempt_id)
            last_flush=time.monotonic()
            def record_scenario_event(event_type:str,payload:dict[str,Any])->None:
                journal.append(event_type,{**payload,"recorded_at_utc":datetime.now(timezone.utc).isoformat()})
            def progress_callback(progress_event:dict[str,Any]|None=None):
                nonlocal last_flush
                now=time.monotonic()
                if now-last_flush>=5:
                    if progress_event is not None:
                        journal.append("scenario_progress",{**progress_event,
                            "recorded_at_utc":datetime.now(timezone.utc).isoformat()})
                    delta=now-last_flush
                    ledger.setdefault("evaluation_seconds",{})[policy_id]=float(ledger.get("evaluation_seconds",{}).get(policy_id,0))+delta
                    ledger["evaluation_campaign_seconds"]=float(ledger.get("evaluation_campaign_seconds",0))+delta
                    ledger["last_updated_at_utc"]=datetime.now(timezone.utc).isoformat()
                    json_write(ARTIFACT_ROOT/"resource-ledger.json",ledger); last_flush=now
            try:
                evaluate_policy(policy,policy_id=policy_id,max_wall_seconds=min(policy_remaining,campaign_remaining),
                    scenario_keys=missing,progress_callback=progress_callback,
                    on_scenario_event=record_scenario_event,attempt_id=attempt_id)
            finally:
                try:
                    delta=time.monotonic()-last_flush
                    if delta>0:
                        ledger.setdefault("evaluation_seconds",{})[policy_id]=float(ledger.get("evaluation_seconds",{}).get(policy_id,0))+delta
                        ledger["evaluation_campaign_seconds"]=float(ledger.get("evaluation_campaign_seconds",0))+delta
                        ledger["last_updated_at_utc"]=datetime.now(timezone.utc).isoformat()
                        json_write(ARTIFACT_ROOT/"resource-ledger.json",ledger)
                finally:
                    journal.close()
    all_attempts={p_id:prior_policy_rows(p_id) for p_id,_ in policies}
    completed_by_policy={}; incomplete_attempts=[]
    for policy_id,attempt_rows in all_attempts.items():
        done={}
        for row in attempt_rows:
            key=(row.get("evaluation_seed"),row.get("opponent_id"),row.get("agent_color"))
            if row.get("status")=="completed_game": done.setdefault(key,row)
            else: incomplete_attempts.append(row)
        completed_by_policy[policy_id]=done
        policy_dir=eval_dir/policy_slug(policy_id); policy_dir.mkdir(parents=True,exist_ok=True)
        # A new immutable consolidated snapshot is published for each evaluation invocation.
        snapshots=list(policy_dir.glob("final-rows-attempt-*.json")); snap_idx=max((int(x.stem.split("-")[-1]) for x in snapshots),default=-1)+1
        json_write(policy_dir/f"final-rows-attempt-{snap_idx:04d}.json",list(done.values()))
        pending=sorted(scenario_keys-set(done))
        json_write(policy_dir/f"unresolved-attempt-{snap_idx:04d}.json",[
            {"evaluation_seed":x[0],"opponent_id":x[1],"agent_color":x[2],"status":"not_completed"} for x in pending])
    comparison_rows=[]
    def summarize_pair_groups(name:str,pairs:list[tuple[str,str]],*,crossed:bool):
        deltas=[]; censored=0; per_seed=[]
        for policy_a,policy_b in pairs:
            seed=int(policy_a.split(":")[1])
            a=completed_by_policy.get(policy_a,{}); b=completed_by_policy.get(policy_b,{})
            seed_deltas=[]
            for key in sorted(scenario_keys):
                if key not in a or key not in b:
                    censored+=1; continue
                ra,rb=a[key],b[key]
                if ra.get("truncated") or rb.get("truncated"):
                    censored+=1; continue
                delta=(float(ra["agent_reward"])-float(rb["agent_reward"]))/2
                item={"training_seed":seed,"evaluation_seed":key[0],"opponent_id":key[1],"agent_color":key[2],"difference":delta}
                deltas.append(item); seed_deltas.append(delta)
            per_seed.append({"training_seed":seed,"matched_terminal_pairs":len(seed_deltas),
                             "mean_score_difference":sum(seed_deltas)/len(seed_deltas) if seed_deltas else None})
        grid={(r["training_seed"],r["evaluation_seed"]) for r in deltas}
        interval=None; status="incomplete_or_censored_pair_grid"
        if crossed and len(grid)==3*25 and len(deltas)==3*25*4:
            from videochess_rl.rl.evaluate import crossed_cluster_bootstrap
            interval=crossed_cluster_bootstrap(deltas); status="computed"
        comparison_rows.append({"comparison":name,"matched_terminal_pairs":len(deltas),"censored_or_unfinished_pairs":censored,
            "mean_paired_score_difference_a_minus_b":sum(r["difference"] for r in deltas)/len(deltas) if deltas else None,
            "crossed_cluster_bootstrap":interval,"interval_status":status,"per_training_seed":per_seed,
            "pairing_keys":["training_seed","stage","evaluation_seed","opponent_id","agent_color"]})
    for stage in ("pre_rl","post_rl"):
        summarize_pair_groups(f"warm_vs_scratch_{stage}",[
            (f"warm:{seed}:{stage}",f"scratch:{seed}:{stage}") for seed in config["training"]["paired_seeds"]],crossed=True)
    for arm in ("warm","scratch"):
        summarize_pair_groups(f"{arm}_pre_vs_post",[
            (f"{arm}:{seed}:post_rl",f"{arm}:{seed}:pre_rl") for seed in config["training"]["paired_seeds"]],crossed=True)
    fixed_policy_comparisons=[]
    fixed_labels=("m4_behavior_only","baseline:random_legal","baseline:simple_heuristic")
    for arm in ("warm","scratch"):
        for seed in config["training"]["paired_seeds"]:
            for stage in ("pre_rl","post_rl"):
                learned=f"{arm}:{seed}:{stage}"
                for fixed in fixed_labels:
                    a=completed_by_policy.get(learned,{}); b=completed_by_policy.get(fixed,{})
                    deltas=[]; censored=0
                    for key in sorted(scenario_keys):
                        if key not in a or key not in b or a[key].get("truncated") or b[key].get("truncated"):
                            censored+=1; continue
                        deltas.append({"evaluation_seed":key[0],"opponent_id":key[1],"agent_color":key[2],
                            "difference":(float(a[key]["agent_reward"])-float(b[key]["agent_reward"]))/2})
                    interval=None
                    if len(deltas)==100:
                        from videochess_rl.rl.evaluate import evaluation_seed_cluster_bootstrap
                        interval=evaluation_seed_cluster_bootstrap(deltas)
                    fixed_policy_comparisons.append({"comparison":f"{learned}_vs_{fixed}",
                        "matched_terminal_pairs":len(deltas),"censored_or_unfinished_pairs":censored,
                        "mean_paired_score_difference_a_minus_b":sum(x["difference"] for x in deltas)/len(deltas) if deltas else None,
                        "evaluation_seed_cluster_bootstrap":interval,
                        "interval_status":"computed" if interval else "incomplete_or_censored_pair_set"})
    per_policy=[]; breakdowns=[]; color_comparisons=[]
    for policy_id,_ in policies:
        rows=list(completed_by_policy[policy_id].values()); summary=summarize_games(rows)
        per_policy.append({"policy_id":policy_id,"games":len(rows),"planned_games":100,
                           "schedule_complete":len(rows)==100,"summary":summary})
        for opponent,color in ((o,c) for o in ("random_legal","simple_material_heuristic") for c in ("white","black")):
            subset=[r for r in rows if r["opponent_id"]==opponent and r["agent_color"]==color]
            breakdowns.append({"policy_id":policy_id,"opponent_id":opponent,"agent_color":color,
                               "planned_games":25,"schedule_complete":len(subset)==25,**summarize_games(subset)})
        color_comparisons.append({"policy_id":policy_id,**paired_white_black_comparison(rows)})
    final_rows=[row for policy_id in completed_by_policy for row in completed_by_policy[policy_id].values()]
    report={"schema":"videochess-m5-evaluation-campaign/1.0","planned_policies":15,
        "policies_with_recorded_schedule":len(per_policy),"fully_completed_policy_schedules":sum(p["schedule_complete"] for p in per_policy),
        "planned_games":1500,"executed_games":len(final_rows),"unresolved_scenarios":1500-len(final_rows),
        "evaluation_attempt_rows":sum(map(len,all_attempts.values())),"incomplete_attempts":len(incomplete_attempts),
        "wall_seconds":time.monotonic()-campaign_start,"cumulative_campaign_seconds":float(ledger.get("evaluation_campaign_seconds",0)),
        "per_policy":per_policy,"opponent_color_breakdown":breakdowns,"matched_comparisons":comparison_rows,
        "fixed_policy_comparisons":fixed_policy_comparisons,"white_black_comparisons":color_comparisons,
        "journal_diagnostics":journal_diagnostics,
        "raw_rows_are_independent":False,"training_seed_clusters":3,"evaluation_seed_clusters":25,
        "few_training_cluster_caveat":True,"rows_path":str(eval_dir.relative_to(ROOT)),
        "metric_source":"python_chess_m2_simulator","truncated_games":sum(r.get("truncated") is True for r in final_rows),
        "complete_games":sum(not r.get("truncated") for r in final_rows),"schedule_complete":len(final_rows)==1500}
    json_write(eval_dir/"evaluation-report.json",report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(prog="python -m videochess_rl.rl.cli")
    sub=parser.add_subparsers(dest="command",required=True)
    profile=sub.add_parser("profile",help="run actual M2 replay feasibility gate")
    profile.add_argument("--threads",default="1,2,4")
    sub.add_parser("train-all",help="run six official paired M5 jobs after passing profile gate")
    sub.add_parser("evaluate",help="run frozen 1,500-game schedule after six complete runs")
    args=parser.parse_args(argv)
    if args.command=="profile":
        report=run_real_replay_probe([int(x) for x in args.threads.split(",")]); print(json.dumps(report,indent=2))
        return 0 if report["projection"]["fits_run_cap"] and report["projection"]["fits_campaign_cap"] else 2
    if args.command=="train-all":
        report=train_campaign(); print(json.dumps(report,indent=2)); return 0 if report["completed_runs"]==6 else 2
    report=run_evaluation(); print(json.dumps(report,indent=2)); return 0 if report["executed_games"]==1500 else 2


if __name__=="__main__": raise SystemExit(main())
