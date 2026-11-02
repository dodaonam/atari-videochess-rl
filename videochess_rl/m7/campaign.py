"""Serialized, hash-chained execution of the frozen 90-cell M7 ALE schedule."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import time
from typing import Any, Iterator

from videochess_rl.environment import ALEConfig, VideoChessEnv
from videochess_rl.m6.campaign import (
    ExperimentIdentityError,
    M6Campaign,
    _slug,
    dependency_identity,
    git_identity,
    profile_config,
    summarize_run,
    utc_now,
    verify_runtime_matches_lock,
)
from videochess_rl.m6.ledger import (
    HashChainLedger,
    build_artifact_manifest,
    iter_verified_hash_chain,
    sha256_file,
    verify_artifact_manifest,
    write_json_atomic,
)
from videochess_rl.m7.policies import load_frozen_policy_roster
from videochess_rl.m7.protocol import (
    CONFIG_SCHEMA,
    ROM_SHA256,
    canonical_json_bytes,
    load_frozen_config,
    schedule_sha256,
)


class M7CampaignError(RuntimeError):
    """Frozen M7 identity, resource, or recovery checks failed closed."""


LOCK_NAME = ".m7-active.lock"
RUN_MANIFEST_NAME = "run-manifest.json"
LEDGER_NAME = "events.jsonl"
SUMMARY_NAME = "summary.json"
ARTIFACT_MANIFEST_NAME = "artifact-manifest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _runtime_config(config: dict[str, Any]) -> ALEConfig:
    profile = config["ale_profile"]
    return profile_config(
        "ale-v5-extended-horizon",
        mode=int(profile["mode"]),
        max_num_frames_per_episode=int(profile["effective_max_num_frames_per_episode"]),
    )


def inspect_ale_runtime(config: dict[str, Any]) -> dict[str, Any]:
    """Construct, inspect, and close ALE without reset or action."""
    expected = config["ale_profile"]
    ale_config = _runtime_config(config)
    if ale_config.as_dict() != {
        "env_id": expected["environment_id"],
        "obs_type": expected["observation_type"],
        "frameskip": expected["frameskip"],
        "repeat_action_probability": expected["repeat_action_probability"],
        "mode": expected["mode"],
        "difficulty": expected["difficulty"],
        "max_num_frames_per_episode": expected["effective_max_num_frames_per_episode"],
    }:
        raise M7CampaignError("constructed ALEConfig differs from the frozen M7 profile")
    with VideoChessEnv(ale_config) as env:
        runtime = env.runtime_info()
    if runtime.get("rom_sha256") != ROM_SHA256:
        raise M7CampaignError("constructed ALE ROM hash differs from the accepted VideoChess ROM")
    if runtime.get("ale_episode_frame_limit") != expected["effective_max_num_frames_per_episode"]:
        raise M7CampaignError("ALE did not honor the frozen 500,000-frame episode horizon")
    registered_default = runtime.get("registered_defaults", {}).get("max_num_frames_per_episode")
    if registered_default != expected["registered_default_max_num_frames_per_episode"]:
        raise M7CampaignError("registered ALE default horizon differs from the recorded 108,000-frame baseline")
    instance = runtime.get("instance_runtime", {})
    if (
        instance.get("mode") != expected["mode"]
        or instance.get("difficulty") != expected["difficulty"]
        or instance.get("frameskip") != expected["frameskip"]
        or instance.get("repeat_action_probability") != expected["repeat_action_probability"]
        or instance.get("obs_type") != expected["observation_type"]
    ):
        raise M7CampaignError("ALE read-back configuration differs from the frozen M7 profile")
    if instance.get("max_num_frames_per_episode") != expected["effective_max_num_frames_per_episode"]:
        raise M7CampaignError("ALE instance read-back differs from the frozen extended horizon")
    return runtime


def _run_digest(source: dict[str, str], config_sha: str, schedule_sha: str, prefix: str) -> str:
    identity = {
        "run_id_prefix": prefix,
        "source_commit": source["git_commit"],
        "source_tree": source["git_tree"],
        "source_bundle_sha256": source["source_bundle_sha256"],
        "configuration_sha256": config_sha,
        "schedule_sha256": schedule_sha,
    }
    return hashlib.sha256(canonical_json_bytes(identity)).hexdigest()


def run_identity(source: dict[str, str], config_sha: str, schedule_sha: str, prefix: str) -> str:
    return f"{prefix}-{_run_digest(source, config_sha, schedule_sha, prefix)[:12]}"


def _active_process(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _require_committed_bytes(path: Path, repository_root: Path) -> None:
    try:
        relative = path.resolve().relative_to(repository_root.resolve()).as_posix()
    except ValueError as exc:
        raise M7CampaignError("M7 source/configuration path is outside the repository") from exc
    if path.is_symlink() or not path.is_file():
        raise M7CampaignError(f"M7 source/configuration file is missing or unsafe: {relative}")
    try:
        subprocess.run(
            ["git", "cat-file", "-e", f"HEAD:{relative}"],
            cwd=repository_root,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        committed = subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=repository_root)
    except subprocess.CalledProcessError as exc:
        raise M7CampaignError(f"M7 source/configuration file is absent from committed HEAD: {relative}") from exc
    if path.read_bytes() != committed:
        raise M7CampaignError(f"M7 source/configuration differs from committed HEAD: {relative}")


def _require_clean_worktree(repository_root: Path) -> None:
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repository_root,
        text=True,
    )
    if status.strip():
        raise M7CampaignError("official M7 execution requires a clean committed worktree; inspect status without discarding files")


def _require_private_artifact_parent(artifact_parent: Path, repository_root: Path) -> None:
    try:
        relative = artifact_parent.resolve().relative_to(repository_root.resolve())
    except ValueError:
        return
    if not relative.parts or relative.parts[0] == ".git":
        raise M7CampaignError("private M7 artifacts cannot be stored in the Git database")
    ignored = subprocess.run(
        ["git", "check-ignore", "--quiet", "--no-index", "--", relative.as_posix()],
        cwd=repository_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0
    if not ignored:
        raise M7CampaignError("M7 artifact parent is inside Git but is not ignored; private traces must remain outside Git")


def _required_m7_run_sources(config_path: Path) -> tuple[Path, ...]:
    module_dir = Path(__file__).resolve().parent
    repo_root = module_dir.parents[1]
    return (
        config_path,
        module_dir / "__init__.py",
        module_dir / "campaign.py",
        module_dir / "protocol.py",
        module_dir / "policies.py",
        module_dir / "analysis.py",
        repo_root / "scripts/run_m7_campaign.py",
        repo_root / "scripts/analyze_m7_campaign.py",
        repo_root / "scripts/verify_m7_inputs.py",
        repo_root / "uv.lock",
        repo_root / "videochess_rl/environment.py",
        repo_root / "videochess_rl/episode.py",
        repo_root / "videochess_rl/m6/campaign.py",
        repo_root / "videochess_rl/m6/adapter.py",
        repo_root / "videochess_rl/m6/ledger.py",
        repo_root / "videochess_rl/vision.py",
    )


@contextmanager
def _run_lock(run_dir: Path, *, resume: bool) -> Iterator[dict[str, Any]]:
    if not run_dir.exists():
        if resume:
            raise M7CampaignError("M7 resume run directory is unavailable")
        run_dir.mkdir(parents=True, exist_ok=False)
    path = run_dir / LOCK_NAME
    if path.is_symlink():
        raise M7CampaignError("M7 runner lock path is a symbolic link")
    if path.exists():
        if not resume:
            raise M7CampaignError("M7 run directory is already active or has an unreviewed lock")
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
            pid = int(previous["pid"])
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise M7CampaignError("M7 active lock is malformed; preserve it and stop") from exc
        if _active_process(pid):
            raise M7CampaignError("another process is using this M7 run identity")
        recovery = run_dir / "recovery"
        recovery.mkdir(exist_ok=True)
        stale_path = recovery / f"stale-runner-lock-{_utc().replace(':', '').replace('-', '')}.json"
        os.replace(path, stale_path)
    payload = {"pid": os.getpid(), "acquired_at_utc": _utc(), "host_platform": platform.system()}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    try:
        yield payload
    finally:
        if path.is_file() and not path.is_symlink():
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                current = {}
            if current.get("pid") == os.getpid():
                path.unlink()


class M7CampaignRunner:
    """Execute one preregistered schedule, preserving every attempted slot."""

    def __init__(
        self,
        *,
        repository_root: str | Path,
        config_path: str | Path,
        m4_artifact_root: str | Path,
        m5_artifact_root: str | Path,
        artifact_parent: str | Path | None = None,
    ) -> None:
        self.repo_root = Path(repository_root).resolve()
        supplied_config_path = Path(config_path).expanduser()
        if supplied_config_path.is_symlink():
            raise M7CampaignError("frozen M7 configuration must not be a symbolic link")
        self.config_path = supplied_config_path.resolve()
        if not self.config_path.is_file():
            raise M7CampaignError("frozen M7 configuration is missing or unsafe")
        self.config = load_frozen_config(self.config_path)
        self.roster, _ = load_frozen_policy_roster(
            self.config_path,
            m4_artifact_root=m4_artifact_root,
            m5_artifact_root=m5_artifact_root,
        )
        self.ale_config = _runtime_config(self.config)
        self.episode_limits = {
            "maximum_player_moves": int(self.config["ale_profile"]["maximum_player_moves"]),
            "maximum_opponent_wait_frames": int(self.config["ale_profile"]["maximum_opponent_wait_frames"]),
            "maximum_ale_frames": int(self.config["ale_profile"]["runner_maximum_post_reset_action_frames"]),
            "maximum_wall_seconds": int(self.config["resource_limits"]["maximum_wall_seconds_per_attempt"]),
        }
        self.campaign_limits = self.config["resource_limits"]
        requested_artifact_parent = Path(artifact_parent or (self.repo_root / "artifacts/m7-option-b")).expanduser()
        if requested_artifact_parent.is_symlink():
            raise M7CampaignError("M7 artifact parent must not be a symbolic link")
        self.artifact_parent = requested_artifact_parent.resolve()
        self.artifact_parent.mkdir(parents=True, exist_ok=True)
        _require_private_artifact_parent(self.artifact_parent, self.repo_root)
        # Reuse the accepted M6 closed-loop runtime's controller, action verification,
        # episode trace, and recovery implementation without modifying M6's frozen configs.
        self.runtime = object.__new__(M6Campaign)
        self.runtime.repo_root = self.repo_root
        self.runtime.artifact_root = self.artifact_parent
        self.runtime.config_path = self.config_path
        self.runtime.config_data = {
            "schema": CONFIG_SCHEMA,
            "profile_id": "ale-v5-extended-horizon",
            "ale_horizon": {"max_num_frames_per_episode": self.config["ale_profile"]["effective_max_num_frames_per_episode"]},
            "episode_limits": self.episode_limits,
            "campaign_limits": {
                "maximum_artifact_bytes": self.campaign_limits["maximum_campaign_artifact_bytes"],
                "artifact_metadata_reserve_bytes": self.campaign_limits["artifact_finalization_reserve_bytes"],
                "minimum_free_bytes_before_campaign": self.campaign_limits["minimum_free_bytes_before_first_attempt"],
                "maximum_process_rss_bytes": self.campaign_limits["maximum_process_rss_bytes"],
                "maximum_game_attempts": self.campaign_limits["scheduled_attempts"],
                "maximum_gameplay_wall_seconds": self.campaign_limits["maximum_aggregate_gameplay_seconds"],
                "maximum_pre_action_process_start_retries": self.campaign_limits["maximum_pre_action_process_start_retries"],
            },
        }
        self.runtime.episode_limits = self.episode_limits
        self.runtime.campaign_limits = self.runtime.config_data["campaign_limits"]
        self.runtime.ale_horizon = int(self.config["ale_profile"]["effective_max_num_frames_per_episode"])
        self.runtime.m4_root = Path(m4_artifact_root)
        self.runtime.m5_root = Path(m5_artifact_root)
        self.runtime.roster = self.roster
        self.runtime.startup_retries_used = 0

    def preflight_only(self) -> dict[str, Any]:
        _require_clean_worktree(self.repo_root)
        for source_file in _required_m7_run_sources(self.config_path):
            _require_committed_bytes(source_file.resolve(), self.repo_root)
        source = git_identity(self.repo_root)
        runtime = inspect_ale_runtime(self.config)
        locked = verify_runtime_matches_lock(self.repo_root)
        free = shutil.disk_usage(self.artifact_parent).free
        minimum = int(self.campaign_limits["minimum_free_bytes_before_first_attempt"])
        config_sha = sha256_file(self.config_path)
        schedule_sha = schedule_sha256(self.config["research_design"]["schedule"])
        prospective_run_id = run_identity(
            source, config_sha, schedule_sha, self.config["run_id_prefix"],
        )
        prior_runs = [
            child.name for child in self.artifact_parent.iterdir()
            if child.is_dir() and child.name.startswith(self.config["run_id_prefix"])
        ]
        return {
            "schema": "videochess-m7-prerun-preflight/1.0",
            "observed_at_utc": _utc(),
            "read_only_campaign_state": True,
            "official_attempts_started": 0,
            "source": source,
            "configuration_sha256": config_sha,
            "schedule_sha256": schedule_sha,
            "prospective_run_id": prospective_run_id,
            "runtime": runtime,
            "dependency_lock_verification": locked,
            "free_bytes": free,
            "minimum_free_bytes": minimum,
            "storage_preflight_pass": free >= minimum,
            "prior_m7_run_directories": sorted(prior_runs),
            "no_conflicting_m7_run": not prior_runs,
            "policy_ids": sorted(self.roster),
            "policy_count": len(self.roster),
            "seed_count": len(self.config["research_design"]["ale_evaluation_seeds"]),
            "scheduled_cells": len(self.config["research_design"]["schedule"]),
        }

    def smoke_test(self, *, seed: int = 0) -> dict[str, Any]:
        """Non-result-bearing one-reset policy/input smoke; executes no ALE action."""
        import chess
        from videochess_rl.episode import AtariDecisionContext
        from videochess_rl.m6.adapter import M6PolicyAdapter
        from videochess_rl.vision import VideoChessVision

        vision = VideoChessVision()
        reset_frames = []
        policy_choices = 0
        policy_ids = sorted(self.roster)
        for _ in range(2):
            with VideoChessEnv(self.ale_config) as env:
                frame = env.reset(seed=seed)
            observation = vision.observe(frame.rgb)
            evidence = vision.window((frame.rgb, frame.rgb, frame.rgb))
            board = chess.Board()
            if not observation.matches_start_position() or not evidence.is_stable or not evidence.matches_board_except_cursor(board):
                raise M7CampaignError("non-official ALE reset smoke did not produce stable RGB-confirmed start state")
            legal = tuple(sorted(move.uci() for move in board.legal_moves))
            context = AtariDecisionContext(
                board=board,
                fen=board.fen(en_passant="fen"),
                side_to_move=chess.WHITE,
                history_uci=(),
                legal_moves_uci=legal,
                frame_number=frame.frame_number,
                rgb_sha256=hashlib.sha256(frame.rgb.tobytes()).hexdigest(),
                rgb_frame=frame.rgb,
                rgb_observation=observation,
                rgb_evidence=evidence,
                standard_reset_verified=True,
            )
            for policy_id in policy_ids:
                policy, identity = self.roster[policy_id]
                adapter = M6PolicyAdapter(policy, identity, rng_seed=seed)
                result = adapter(context)
                if result.uci not in legal:
                    raise M7CampaignError(f"policy {policy_id} failed the legal-action smoke contract")
                policy_choices += 1
            reset_frames.append(hashlib.sha256(frame.rgb.tobytes()).hexdigest())
        if reset_frames[0] != reset_frames[1]:
            raise M7CampaignError("same-seed ALE reset smoke produced different RGB observations")
        return {
            "schema": "videochess-m7-non-result-bearing-smoke/1.0",
            "smoke_seed": seed,
            "seed_overlaps_official_schedule": seed in self.config["research_design"]["ale_evaluation_seeds"],
            "reset_count": 2,
            "same_seed_reset_rgb_reproducible": True,
            "reset_rgb_sha256": reset_frames[0],
            "policy_adapters_initialized": len(policy_ids),
            "legal_policy_decisions": policy_choices,
            "ale_actions_executed": 0,
            "official_attempts_started": 0,
            "classification": "technical_smoke_only; excluded from official M7 schedule and metrics",
        }

    def _manifest(self, *, run_id: str, source: dict[str, str], runtime_info: dict[str, Any], free_bytes: int,
                  artifact_bytes_before: int, setup_seconds: float) -> dict[str, Any]:
        config_sha = sha256_file(self.config_path)
        design = self.config["research_design"]
        dependency_lock = verify_runtime_matches_lock(self.repo_root)
        policy_rows = [
            {key: getattr(identity, key) for key in identity.__slots__}
            for _, identity in sorted(self.roster.values(), key=lambda item: item[1].policy_id)
        ]
        return {
            "schema": "videochess-m7-run-manifest/1.0",
            "protocol_id": self.config["protocol_id"],
            "scientific_basis": self.config["scientific_basis"],
            "authorization_id": self.config["authorization_id"],
            "run_id": run_id,
            "run_id_prefix": self.config["run_id_prefix"],
            "run_identity_derivation": "SHA-256 over run prefix, source commit/tree/bundle, frozen configuration SHA-256, and complete counterbalanced schedule SHA-256",
            "run_identity_inputs": {
                "source_commit": source["git_commit"],
                "source_tree": source["git_tree"],
                "source_bundle_sha256": source["source_bundle_sha256"],
                "configuration_sha256": config_sha,
                "schedule_sha256": design["schedule_sha256"],
            },
            "frozen_at_utc": _utc(),
            **source,
            "configuration_path": self.config_path.relative_to(self.repo_root).as_posix(),
            "configuration_sha256": config_sha,
            "schedule_sha256": design["schedule_sha256"],
            "scheduled_attempt_count": len(design["schedule"]),
            "seed_schedule": design["schedule"],
            "policy_roster": policy_rows,
            "ale_runtime_construction": runtime_info,
            "rom_sha256": runtime_info["rom_sha256"],
            "registered_default_horizon": self.config["ale_profile"]["registered_default_max_num_frames_per_episode"],
            "effective_ale_horizon": runtime_info["ale_episode_frame_limit"],
            "runtime_lock_verification": dependency_lock,
            "campaign_resource_snapshot_before_first_attempt": {
                "free_disk_bytes": free_bytes,
                "m7_artifact_bytes": artifact_bytes_before,
                "setup_seconds_before_manifest": setup_seconds,
                "logical_cpu_count": os.cpu_count(),
                "cpu_model": _cpu_model(),
                "memory_total_bytes": _memory_total_bytes(),
            },
            "resource_limits": self.campaign_limits,
            "episode_limits": self.episode_limits,
            "accepted_input_identities": self.config["accepted_inputs"],
            "primary_metrics": self.config["primary_metrics"],
            "outcome_rules": self.config["outcome_rules"],
            "privacy": self.config["privacy"],
            "training_or_finetuning": False,
            "stockfish_in_inference_or_evaluation": False,
            "prior_m6_configurations_are_not_reused": True,
        }

    def _recover_run_state(self, run_dir: Path, run_id: str, source: dict[str, str], schedule: list[dict[str, Any]]) -> dict[str, Any]:
        manifest_path = run_dir / RUN_MANIFEST_NAME
        ledger_path = run_dir / LEDGER_NAME
        if run_dir.is_symlink() or not run_dir.is_dir() or manifest_path.is_symlink() or ledger_path.is_symlink():
            raise M7CampaignError("M7 resume run directory or control files are missing/unsafe")
        if not manifest_path.is_file() or not ledger_path.is_file():
            raise M7CampaignError("M7 resume requires the frozen run manifest and attempt ledger")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        checks = {
            "schema": "videochess-m7-run-manifest/1.0",
            "protocol_id": self.config["protocol_id"],
            "run_id": run_id,
            "configuration_sha256": sha256_file(self.config_path),
            "schedule_sha256": self.config["research_design"]["schedule_sha256"],
            "scheduled_attempt_count": len(schedule),
            "seed_schedule": schedule,
            "effective_ale_horizon": 500000,
            **source,
        }
        if any(manifest.get(key) != expected for key, expected in checks.items()):
            raise M7CampaignError("M7 run manifest differs from the current committed source/config/schedule")
        started_payloads: dict[str, dict[str, Any]] = {}
        started_ids: set[str] = set()
        reset_ids: set[str] = set()
        completed_ids: set[str] = set()
        finished_records: dict[str, dict[str, Any]] = {}
        reset_game_ids: set[str] = set()
        incomplete_event_buffers: dict[str, list[dict[str, Any]]] = {}
        run_started_manifest_hash: str | None = None
        startup_retries_used = 0
        process_action_started: set[str] = set()
        schedule_by_game = {row["game_id"]: row for row in schedule}
        for event in iter_verified_hash_chain(ledger_path, expected_run_id=run_id):
            kind = event["event_type"]
            payload = event["payload"]
            if kind == "run_started":
                if run_started_manifest_hash is not None:
                    raise M7CampaignError("M7 ledger has duplicate run_started events")
                run_started_manifest_hash = payload.get("run_manifest_sha256")
                if payload.get("schedule_sha256") != self.config["research_design"]["schedule_sha256"] or payload.get("schedule") != schedule:
                    raise M7CampaignError("M7 ledger run_started identity differs from frozen schedule")
            attempt_id = payload.get("attempt_id")
            if kind == "attempt_started":
                if not isinstance(attempt_id, str) or attempt_id in started_ids:
                    raise M7CampaignError("M7 ledger has malformed or duplicate attempt_started identity")
                game_id = payload.get("game_id")
                item = schedule_by_game.get(game_id)
                if item is None or payload.get("policy_id") != item["policy_id"] or payload.get("ale_seed") != item["ale_seed"]:
                    raise M7CampaignError("M7 attempt identity is outside the frozen policy × seed schedule")
                started_ids.add(attempt_id)
                started_payloads[attempt_id] = payload
                incomplete_event_buffers[attempt_id] = [event]
            elif isinstance(attempt_id, str) and attempt_id in incomplete_event_buffers:
                incomplete_event_buffers[attempt_id].append(event)
            if kind == "ale_action_started" and isinstance(attempt_id, str):
                process_action_started.add(attempt_id)
            elif kind == "ale_reset_observed" and isinstance(attempt_id, str):
                game_id = payload.get("game_id")
                if game_id in reset_game_ids:
                    raise M7CampaignError(f"duplicate M7 reset observed for one scheduled cell: {game_id}")
                reset_game_ids.add(game_id)
                reset_ids.add(attempt_id)
            elif kind == "attempt_finished":
                if not isinstance(attempt_id, str) or attempt_id not in started_ids or attempt_id in completed_ids:
                    raise M7CampaignError("M7 ledger has malformed or duplicate attempt completion")
                record = payload.get("attempt_record")
                if not isinstance(record, dict) or record.get("attempt_id") != attempt_id:
                    raise M7CampaignError("M7 attempt completion payload is malformed")
                completed_ids.add(attempt_id)
                finished_records[attempt_id] = record
                incomplete_event_buffers.pop(attempt_id, None)
            elif kind == "process_start_retry":
                if payload.get("action_attempted") is not False:
                    raise M7CampaignError("M7 startup retry is only permitted before any ALE action")
                startup_retries_used += 1
        if run_started_manifest_hash != sha256_file(manifest_path):
            raise M7CampaignError("frozen M7 run manifest does not match its run_started ledger identity")
        if startup_retries_used > 1:
            raise M7CampaignError("M7 ledger exceeds the one global pre-action startup retry")

        # A crash can occur after mkdir but before attempt_started is durably appended.
        # Only an empty orphan directory proves no reset/action was possible here.
        attempts_root = run_dir / "attempts"
        if attempts_root.exists():
            known_dirs = {_slug(attempt_id) for attempt_id in started_ids}
            expected_dirs = {
                _slug(self._attempt_id(item, retry=retry))
                for item in schedule for retry in (False, True)
            }
            for child in attempts_root.iterdir():
                if child.is_symlink() or not child.is_dir():
                    raise M7CampaignError("unexpected/non-directory path in M7 attempt tree")
                if child.name not in known_dirs:
                    if child.name not in expected_dirs:
                        raise M7CampaignError("unregistered directory exists in the M7 attempt tree")
                    if any(child.iterdir()):
                        raise M7CampaignError("unregistered M7 attempt directory has content; preserve it and stop")
                    orphan_attempt_dirs = incomplete_event_buffers.setdefault(f"orphan:{child.name}", [])
                    orphan_attempt_dirs.append({"orphan_directory": child.name, "path": child.relative_to(self.repo_root).as_posix()})

        return {
            "manifest": manifest,
            "started_payloads": started_payloads,
            "started_ids": started_ids,
            "reset_ids": reset_ids,
            "completed_ids": completed_ids,
            "finished_records": finished_records,
            "reset_game_ids": reset_game_ids,
            "incomplete_event_buffers": incomplete_event_buffers,
            "process_action_started": process_action_started,
            "startup_retries_used": startup_retries_used,
            "run_started_manifest_hash": run_started_manifest_hash,
        }

    def _accounting_snapshot(self, schedule: list[dict[str, Any]], started_ids: set[str], reset_game_ids: set[str],
                             finished_records: dict[str, dict[str, Any]]) -> dict[str, Any]:
        process_by_game: dict[str, list[dict[str, Any]]] = {}
        for record in finished_records.values():
            game_id = record.get("game_id")
            if isinstance(game_id, str):
                process_by_game.setdefault(game_id, []).append(record)
        rows = []
        for item in schedule:
            attempts = process_by_game.get(item["game_id"], [])
            reset_records = [record for record in attempts if record.get("reset_observed")]
            selected = reset_records[-1] if reset_records else (attempts[-1] if attempts else None)
            rows.append({
                "slot": item["slot"],
                "game_id": item["game_id"],
                "policy_id": item["policy_id"],
                "ale_seed": item["ale_seed"],
                "scheduled": True,
                "started": item["game_id"] in reset_game_ids,
                "attempt_process_started": bool(attempts) or any(
                    payload.get("game_id") == item["game_id"] for payload in getattr(self, "_started_payloads", {}).values()
                ),
                "reset_observed": item["game_id"] in reset_game_ids,
                "attempt_process_count": len(attempts),
                "attempt_ids": [record.get("attempt_id") for record in attempts],
                "selected_attempt_status": selected.get("outcome") if selected else "not_started",
                "selected_stop_reason": selected.get("stop_reason") or selected.get("terminal_or_stop_reason") if selected else "not_started",
            })
        started_cells = sum(row["started"] for row in rows)
        not_started = len(rows) - started_cells
        return {
            "scheduled_cells": len(rows),
            "started_cells": started_cells,
            "attempt_process_started_cells": sum(row["attempt_process_started"] for row in rows),
            "reset_observed_cells": sum(row["reset_observed"] for row in rows),
            "not_started_cells": not_started,
            "all_cells_retained": len(rows) == 90,
            "cells": rows,
        }

    def _create_initial_run(self, run_dir: Path, run_id: str, source: dict[str, str], runtime_info: dict[str, Any],
                            free_bytes: int, setup_seconds: float, schedule: list[dict[str, Any]]) -> HashChainLedger:
        if run_dir.is_symlink() or not run_dir.is_dir():
            raise M7CampaignError("M7 run directory was not created safely under its exclusive lock")
        unexpected = [item.name for item in run_dir.iterdir() if item.name != LOCK_NAME]
        if unexpected:
            raise M7CampaignError(f"new M7 run identity directory was not empty: {unexpected}")
        artifact_bytes = max(0, self.runtime._artifact_bytes() - (run_dir / LOCK_NAME).stat().st_size)
        manifest = self._manifest(
            run_id=run_id,
            source=source,
            runtime_info=runtime_info,
            free_bytes=free_bytes,
            artifact_bytes_before=artifact_bytes,
            setup_seconds=setup_seconds,
        )
        manifest_sha = write_json_atomic(run_dir / RUN_MANIFEST_NAME, manifest)
        ledger = HashChainLedger(run_dir / LEDGER_NAME, run_id=run_id)
        ledger.append("run_started", {
            "run_manifest_sha256": manifest_sha,
            "schedule_sha256": self.config["research_design"]["schedule_sha256"],
            "schedule": schedule,
            "protocol_id": self.config["protocol_id"],
            "started_at_utc": _utc(),
        })
        ledger.append("campaign_session_started", {"started_at_utc": _utc(), "resume": False})
        return ledger

    def _resume_ledger(self, run_dir: Path, run_id: str, state: dict[str, Any]) -> HashChainLedger:
        ledger = HashChainLedger(run_dir / LEDGER_NAME, run_id=run_id, create=False)
        ledger.append("campaign_session_started", {"started_at_utc": _utc(), "resume": True})
        return ledger

    def _stop_check(self, run_id: str, next_item: dict[str, Any], gameplay_seconds: float) -> str | None:
        limits = self.campaign_limits
        current_artifacts = self.runtime._artifact_bytes()
        free_bytes = shutil.disk_usage(self.artifact_parent).free
        rss_bytes = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
        if gameplay_seconds >= int(limits["maximum_aggregate_gameplay_seconds"]):
            reason = "authorized aggregate gameplay allowance reached"
        elif current_artifacts + int(limits["artifact_finalization_reserve_bytes"]) >= int(limits["maximum_campaign_artifact_bytes"]):
            reason = "8-GiB M7 artifact ceiling reached with finalization reserve"
        elif free_bytes <= int(limits["artifact_finalization_reserve_bytes"]):
            reason = "free disk reached the finalization reserve"
        elif limits.get("maximum_process_rss_bytes") is not None and rss_bytes >= int(limits["maximum_process_rss_bytes"]):
            reason = "6-GiB process RSS ceiling reached"
        else:
            return None
        return reason

    def run(self, *, resume: bool = False) -> dict[str, Any]:
        started_mono = time.monotonic()
        setup_started = time.monotonic()
        _require_clean_worktree(self.repo_root)
        _require_committed_bytes(self.config_path, self.repo_root)
        for source_file in _required_m7_run_sources(self.config_path):
            _require_committed_bytes(source_file, self.repo_root)
        source = git_identity(self.repo_root)
        runtime_lock = verify_runtime_matches_lock(self.repo_root)
        runtime_info = inspect_ale_runtime(self.config)
        if runtime_info["rom_sha256"] != self.config["ale_profile"]["rom_sha256"]:
            raise M7CampaignError("ALE ROM hash differs from the immutable M7 configuration")
        free_bytes = shutil.disk_usage(self.artifact_parent).free
        minimum_free = int(self.campaign_limits["minimum_free_bytes_before_first_attempt"])
        if free_bytes < minimum_free:
            raise M7CampaignError(f"M7 needs at least {minimum_free} free bytes; observed {free_bytes}")
        config_sha = sha256_file(self.config_path)
        schedule = self.config["research_design"]["schedule"]
        schedule_sha = schedule_sha256(schedule)
        run_id = run_identity(source, config_sha, schedule_sha, self.config["run_id_prefix"])
        run_dir = self.artifact_parent / run_id
        setup_seconds = time.monotonic() - setup_started
        if resume and (run_dir.is_symlink() or not run_dir.is_dir()):
            raise M7CampaignError("the frozen M7 run directory is unavailable for resume")
        if not resume and run_dir.exists():
            raise FileExistsError("M7 run identity already exists; refusing duplicate official execution")
        if not resume:
            prior_runs = [
                child for child in self.artifact_parent.iterdir()
                if child.is_dir() and child.name.startswith(self.config["run_id_prefix"])
            ]
            if prior_runs:
                raise M7CampaignError("a prior M7 run registration exists; inspect it before a new official run")
        elif (run_dir / ARTIFACT_MANIFEST_NAME).is_file():
            completed_manifest = verify_artifact_manifest(run_dir)
            completed_summary = json.loads((run_dir / SUMMARY_NAME).read_text(encoding="utf-8"))
            return {"run_id": run_id, "run_dir": run_dir, "summary": completed_summary, "artifact_manifest": completed_manifest}

        with _run_lock(run_dir, resume=resume):
            recovery_started = time.monotonic()
            if resume:
                state = self._recover_run_state(run_dir, run_id, source, schedule)
                ledger = self._resume_ledger(run_dir, run_id, state)
                started_payloads = state["started_payloads"]
                started_ids = state["started_ids"]
                reset_ids = state["reset_ids"]
                completed_ids = state["completed_ids"]
                finished_records = state["finished_records"]
                reset_game_ids = state["reset_game_ids"]
                event_buffers = state["incomplete_event_buffers"]
                process_action_started = state["process_action_started"]
                self.runtime.startup_retries_used = state["startup_retries_used"]
            else:
                state = None
                ledger = self._create_initial_run(run_dir, run_id, source, runtime_info, free_bytes, setup_seconds, schedule)
                started_payloads = {}
                started_ids: set[str] = set()
                reset_ids: set[str] = set()
                completed_ids: set[str] = set()
                finished_records: dict[str, dict[str, Any]] = {}
                reset_game_ids: set[str] = set()
                event_buffers: dict[str, list[dict[str, Any]]] = {}
                process_action_started: set[str] = set()
                self.runtime.startup_retries_used = 0
            recovery_seconds = time.monotonic() - recovery_started
            schedule_by_game = {item["game_id"]: item for item in schedule}
            consumed_gameplay = sum(self.runtime._record_wall_bound_seconds(row) for row in finished_records.values())

            def run_slot(item: dict[str, Any], attempt_id: str, allowed_seconds: float) -> dict[str, Any]:
                wall_started = time.monotonic()
                cpu_started = time.process_time()
                record = self.runtime._run_one(
                    ledger=ledger,
                    run_id=run_id,
                    stage="m7-option-b",
                    profile="ale-v5-extended-horizon",
                    config=self.ale_config,
                    schedule=item,
                    max_player_moves=int(self.episode_limits["maximum_player_moves"]),
                    max_episode_seconds=min(float(self.episode_limits["maximum_wall_seconds"]), allowed_seconds),
                    attempt_id_override=attempt_id,
                )
                observed_wall = time.monotonic() - wall_started
                cpu_seconds = time.process_time() - cpu_started
                cpus = max(1, os.cpu_count() or 1)
                peak_rss = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
                artifact_bytes = self.runtime._artifact_bytes()
                free_now = shutil.disk_usage(self.artifact_parent).free
                resource_row = {
                    "attempt_id": record["attempt_id"],
                    "game_id": item["game_id"],
                    "policy_id": item["policy_id"],
                    "ale_seed": item["ale_seed"],
                    "observed_process_wall_seconds": observed_wall,
                    "process_cpu_seconds": cpu_seconds,
                    "process_cpu_utilization_one_core_percent": (100.0 * cpu_seconds / observed_wall) if observed_wall else None,
                    "process_cpu_utilization_machine_percent": (100.0 * cpu_seconds / observed_wall / cpus) if observed_wall else None,
                    "logical_cpu_count": cpus,
                    "process_peak_rss_bytes": peak_rss,
                    "attempt_trace_peak_rss_bytes": record.get("peak_rss_bytes"),
                    "campaign_artifact_bytes_after_attempt": artifact_bytes,
                    "free_disk_bytes_after_attempt": free_now,
                }
                ledger.append("attempt_resource_observed", resource_row)
                started_ids.add(record["attempt_id"])
                completed_ids.add(record["attempt_id"])
                finished_records[record["attempt_id"]] = record
                started_payloads[record["attempt_id"]] = {
                    "game_id": item["game_id"], "policy_id": item["policy_id"], "ale_seed": item["ale_seed"]
                }
                if record.get("reset_observed"):
                    reset_ids.add(record["attempt_id"])
                    reset_game_ids.add(item["game_id"])
                return record

            resource_stop_reason: str | None = None
            # Recover a process that stopped between its durable start/reset records.
            if resume and state is not None:
                for orphan_id, rows in list(event_buffers.items()):
                    if orphan_id.startswith("orphan:"):
                        orphan_name = rows[0]["orphan_directory"]
                        orphan_path = run_dir / "attempts" / orphan_name
                        ledger.append("pre_action_orphan_directory", {
                            "attempt_directory": orphan_path.relative_to(self.repo_root).as_posix(),
                            "action_possible": False,
                            "reason": "process stopped after creating an empty attempt directory but before attempt_started was durable",
                        })
                for item in schedule:
                    base_id = self._attempt_id(item, retry=False)
                    retry_id = self._attempt_id(item, retry=True)
                    candidates = (base_id, retry_id)
                    recovered = False
                    for attempt_id in candidates:
                        if attempt_id in reset_ids and attempt_id not in completed_ids:
                            attempt_events = event_buffers.get(attempt_id, [])
                            if not attempt_events:
                                raise M7CampaignError("interrupted reset has no retained attempt event buffer")
                            record = self.runtime._recover_interrupted_reset(
                                run_id=run_id,
                                schedule=item,
                                attempt_id=attempt_id,
                                events=attempt_events,
                                ledger=ledger,
                            )
                            completed_ids.add(attempt_id)
                            finished_records[attempt_id] = record
                            event_buffers.pop(attempt_id, None)
                            recovered = True
                            break
                    if recovered:
                        continue
                    for attempt_id in candidates:
                        if attempt_id not in started_ids or attempt_id in completed_ids:
                            continue
                        if attempt_id in reset_ids or attempt_id in process_action_started:
                            continue
                        self.runtime._finish_pre_reset_failure(
                            ledger=ledger,
                            run_id=run_id,
                            game_id=item["game_id"],
                            attempt_id=attempt_id,
                            policy_id=item["policy_id"],
                            seed=int(item["ale_seed"]),
                            reason="resume classified the interrupted process as pre-reset and pre-action",
                        )
                        completed_ids.add(attempt_id)
                        finished_records[attempt_id] = {
                            "attempt_id": attempt_id,
                            "game_id": item["game_id"],
                            "policy_id": item["policy_id"],
                            "reset_observed": False,
                            "outcome": "incomplete",
                            "stop_reason": "interrupted_before_reset",
                            "wall_seconds": None,
                        }
                        event_buffers.pop(attempt_id, None)

            for item in schedule:
                base_id = self._attempt_id(item, retry=False)
                retry_id = self._attempt_id(item, retry=True)
                if any(attempt_id in reset_ids for attempt_id in (base_id, retry_id)):
                    continue
                if retry_id in completed_ids or retry_id in started_ids:
                    continue
                base_record = finished_records.get(base_id)
                pre_action_failure = bool(
                    base_record
                    and not base_record.get("reset_observed")
                    and not base_record.get("startup_state", {}).get("action_attempted")
                    and base_id not in process_action_started
                )
                orphan_retry_needed = base_id not in started_ids and (run_dir / "attempts" / _slug(base_id)).exists()
                if base_id in completed_ids and not pre_action_failure and not orphan_retry_needed:
                    continue
                if base_id in started_ids and base_id not in completed_ids:
                    # An empty directory without ledger start was handled above; any other
                    # unfinished identity should have been recovered or explicitly closed.
                    raise M7CampaignError("unresolved started M7 attempt remains after recovery")
                if pre_action_failure or orphan_retry_needed:
                    if self.runtime.startup_retries_used >= int(self.campaign_limits["maximum_pre_action_process_start_retries"]):
                        continue
                if base_id not in started_ids and base_id not in completed_ids and not orphan_retry_needed:
                    pass

                stop_reason = self._stop_check(run_id, item, consumed_gameplay)
                if stop_reason:
                    resource_stop_reason = stop_reason
                    ledger.append("resource_stop", {
                        "reason": stop_reason,
                        "next_game_id": item["game_id"],
                        "remaining_schedule_count": len(schedule) - int(item["slot"]),
                        "campaign_artifact_bytes": self.runtime._artifact_bytes(),
                        "free_disk_bytes": shutil.disk_usage(self.artifact_parent).free,
                        "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024),
                    })
                    break
                if pre_action_failure or orphan_retry_needed:
                    self.runtime.startup_retries_used += 1
                    ledger.append("process_start_retry", {
                        "attempt_id": base_id,
                        "retry_attempt_id": retry_id,
                        "game_id": item["game_id"],
                        "action_attempted": False,
                        "reason": "one globally limited pre-reset/pre-action technical startup retry",
                    })
                    attempt_id = retry_id
                else:
                    attempt_id = base_id
                record = run_slot(item, attempt_id, float(self.episode_limits["maximum_wall_seconds"]))
                if (
                    attempt_id == base_id
                    and not record.get("reset_observed")
                    and record.get("runner_stop_category") == "PROCESS_START_FAILURE"
                    and not record.get("startup_state", {}).get("action_attempted")
                    and self.runtime.startup_retries_used < int(self.campaign_limits["maximum_pre_action_process_start_retries"])
                ):
                    self.runtime.startup_retries_used += 1
                    ledger.append("process_start_retry", {
                        "attempt_id": base_id,
                        "retry_attempt_id": retry_id,
                        "game_id": item["game_id"],
                        "action_attempted": False,
                        "reason": record.get("stop_reason"),
                    })
                    retry_record = run_slot(item, retry_id, float(self.episode_limits["maximum_wall_seconds"]))
                    record = retry_record
                consumed_gameplay += self.runtime._record_wall_bound_seconds(record)
                resource_stop_reason = self._stop_check(run_id, item, consumed_gameplay)
                if resource_stop_reason:
                    ledger.append("resource_stop", {
                        "reason": resource_stop_reason,
                        "completed_game_id": item["game_id"],
                        "campaign_artifact_bytes": self.runtime._artifact_bytes(),
                        "free_disk_bytes": shutil.disk_usage(self.artifact_parent).free,
                        "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024),
                    })
                    break
                accounting = self._accounting_snapshot(schedule, started_ids, reset_game_ids, finished_records)
                ledger.append("run_progress_checkpoint", {
                    "recorded_at_utc": _utc(),
                    "completed_attempt_ids": sorted(completed_ids),
                    "completed_reset_game_ids": sorted(reset_game_ids),
                    "remaining_schedule_count": 90 - len(reset_game_ids),
                    "schedule_accounting_sha256": hashlib.sha256(canonical_json_bytes(accounting)).hexdigest(),
                    "run_manifest_sha256": sha256_file(run_dir / RUN_MANIFEST_NAME),
                    "resource_stop_reason": None,
                })
                cell_status = "reset" if item["game_id"] in reset_game_ids else "started_without_reset"
                print(f"M7 cell {item['slot'] + 1:02d}/90: {item['policy_id']} seed={item['ale_seed']} status={cell_status} wall={record.get('wall_seconds')}", flush=True)

            accounting = self._accounting_snapshot(schedule, started_ids, reset_game_ids, finished_records)
            ledger.append("run_progress_checkpoint", {
                "recorded_at_utc": _utc(),
                "completed_attempt_ids": sorted(completed_ids),
                "completed_reset_game_ids": sorted(reset_game_ids),
                "scheduled_game_ids": [row["game_id"] for row in schedule],
                "unexecuted_game_ids": [row["game_id"] for row in schedule if row["game_id"] not in reset_game_ids],
                "remaining_schedule_count": 90 - len(reset_game_ids),
                "schedule_accounting_sha256": hashlib.sha256(canonical_json_bytes(accounting)).hexdigest(),
                "resource_stop_reason": resource_stop_reason,
                "run_manifest_sha256": sha256_file(run_dir / RUN_MANIFEST_NAME),
            })
            session_seconds = time.monotonic() - started_mono
            ledger.append("campaign_session_finished", {
                "finished_at_utc": _utc(),
                "observed_session_wall_seconds": session_seconds,
                "setup_seconds_before_first_attempt": setup_seconds,
                "resume_recovery_seconds": recovery_seconds,
            })
            ledger.append("run_finished", {
                "finished_at_utc": _utc(),
                "resource_stop_reason": resource_stop_reason,
                "schedule_reset_count": len(reset_game_ids),
                "scheduled_count": 90,
            })

            raw_summary = summarize_run(run_dir / LEDGER_NAME, run_id=run_id, repo_root=self.repo_root)
            resource_rows = [
                event["payload"] for event in iter_verified_hash_chain(run_dir / LEDGER_NAME, expected_run_id=run_id)
                if event["event_type"] == "attempt_resource_observed"
            ]
            output = {
                "schema": "videochess-m7-campaign-summary/1.0",
                "run_id": run_id,
                "protocol_id": self.config["protocol_id"],
                "configuration_sha256": config_sha,
                "schedule_sha256": schedule_sha,
                "source_commit": source["git_commit"],
                "source_tree": source["git_tree"],
                "source_bundle_sha256": source["source_bundle_sha256"],
                "scheduled_attempt_count": 90,
                "schedule_accounting": accounting,
                "resource_stop_reason": resource_stop_reason,
                "accepted_input_identities": self.config["accepted_inputs"],
                "runtime_lock_verification": runtime_lock,
                "ale_runtime": runtime_info,
                "raw_reconstruction_seed": raw_summary,
                "process_resource_observations": resource_rows,
                "campaign_artifact_bytes": self.runtime._artifact_bytes(),
                "free_disk_bytes_after_campaign": shutil.disk_usage(self.artifact_parent).free,
                "maximum_process_rss_bytes": max((row["process_peak_rss_bytes"] for row in resource_rows), default=0),
                "aggregate_process_cpu_seconds": sum(row["process_cpu_seconds"] for row in resource_rows),
                "aggregate_observed_process_wall_seconds": sum(row["observed_process_wall_seconds"] for row in resource_rows),
                "campaign_observed_session_wall_seconds": session_seconds,
                "setup_seconds_before_first_attempt": setup_seconds,
                "resume_recovery_seconds": recovery_seconds,
                "protocol_deviation_register": [],
            }
            write_json_atomic(run_dir / SUMMARY_NAME, output)
            manifest = build_artifact_manifest(run_dir, exclude=(LOCK_NAME,))
            write_json_atomic(run_dir / ARTIFACT_MANIFEST_NAME, manifest)

        # The lock is removed before final read-only verification, so the final
        # inventory is a complete clean-tree manifest and catches any mismatch.
        verified = verify_artifact_manifest(run_dir)
        return {"run_id": run_id, "run_dir": run_dir, "summary": output, "artifact_manifest": verified}

    def _attempt_id(self, item: dict[str, Any], *, retry: bool) -> str:
        base = f"{_slug(item['policy_id'])}-seed-{item['ale_seed']}-slot-{item['slot']:03d}-attempt-0000-m7"
        return f"{base}-startup-retry-0001" if retry else base


def _cpu_model() -> str | None:
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        return None
    return None


def _memory_total_bytes() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError):
        return None
    return None
