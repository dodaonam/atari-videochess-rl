"""Bounded PGN dataset generation and atomic release finalization."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import Any

import chess

from .contracts import config_identity
from .export import ExportError, _write_new, verify_release, write_batches, write_release_files
from .pgn import SourceLimitError, iter_pgn_games
from .sampling import BottomKGroups, sample_positions
from .source import inspect_zip, sha256_file, validate_source_manifest
from .split import SplitError, split_and_purge
from .stats import summarize_dataset


class PipelineError(RuntimeError):
    """A bounded dataset build failed and preserved its staging evidence."""


def _code_context(repository_root: Path) -> dict[str, Any]:
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repository_root, text=True,
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=repository_root, text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PipelineError(f"cannot identify code revision: {exc}") from exc
    files = sorted((repository_root / "videochess_rl/data").glob("*.py"))
    code_hash = hashlib.sha256()
    for path in files:
        code_hash.update(path.name.encode("utf-8") + b"\0")
        code_hash.update(path.read_bytes())
    code_hash.update((repository_root / "pyproject.toml").read_bytes())
    return {
        "code_revision": revision,
        "dirty_code_tree": bool(status.strip()),
        "code_tree_sha256": code_hash.hexdigest(),
    }


def _write_metrics(path: Path, metrics: dict[str, Any]) -> None:
    if path.exists():
        raise PipelineError(f"refusing to overwrite run metrics: {path}")
    _write_new(path, json.dumps(metrics, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")


def _process_rss_mib() -> float | None:
    try:
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux reports KiB; macOS reports bytes.
        return round(value / 1024 if platform.system() == "Linux" else value / (1024 * 1024), 2)
    except (ImportError, AttributeError, OSError):
        return None


def _parse_source(
    archive: Path, source_manifest: dict[str, Any], *, config: dict[str, Any],
    source_id: str, run_dir: Path, input_identity: dict[str, Any],
    resume: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    if run_dir.exists() and not resume:
        raise PipelineError(f"run directory exists; use --resume after verifying it: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    run_manifest = run_dir / "run.json"
    identity_bytes = json.dumps(input_identity, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    if run_manifest.exists():
        if not resume:
            raise PipelineError("run identity exists; --resume is required")
        if json.loads(run_manifest.read_text(encoding="utf-8")) != input_identity:
            raise PipelineError("resume refused because source/config/code identity changed")
    else:
        if resume:
            raise PipelineError("resume requested without a run identity manifest")
        _write_new(run_manifest, identity_bytes)
    archive_hash, archive_bytes = sha256_file(archive, max_bytes=config["max_archive_bytes"])
    if (archive_hash, archive_bytes) != (source_manifest["archive_sha256"], source_manifest["archive_bytes"]):
        raise PipelineError("local source archive no longer matches its immutable source manifest")
    member_name = source_manifest["member"]["name"]
    stream_metrics: dict[str, Any] = {}
    grouper = BottomKGroups(
        seed=config["seed"], max_games=config["max_games"], source_id=source_id,
        archive_sha256=archive_hash, member_name=member_name,
    )
    counts: Counter[str] = Counter()
    reject_reasons: Counter[str] = Counter()
    quarantine_reasons: Counter[str] = Counter()
    started = time.monotonic()
    complete_scan = config["sampling_mode"] == "bottom_k"
    rejection_path = run_dir / "parse-rejections.jsonl"
    rejection_temp = run_dir / f".parse-rejections-{os.getpid()}.partial"
    if rejection_temp.exists():
        raise PipelineError(f"partial rejection ledger already exists; inspect and preserve it: {rejection_temp}")
    rejection_stream = rejection_temp.open("xb")
    rejection_count = 0
    try:
        with __import__("zipfile").ZipFile(archive, "r") as bundle:
            with bundle.open(member_name, "r") as member:
                iterator = iter_pgn_games(
                    member,
                    source_id=source_id,
                    archive_sha256=archive_hash,
                    member_name=member_name,
                    max_games_seen=config["max_input_games_seen"],
                    max_game_bytes=config["max_game_bytes"],
                    max_total_decompressed_bytes=config["max_total_decompressed_bytes"],
                    max_header_bytes=config["max_header_bytes"],
                    max_header_value_bytes=config["max_header_value_bytes"],
                    max_comment_bytes=config["max_comment_bytes"],
                    stream_stats=stream_metrics,
                    complete_scan=complete_scan,
                )
                for ordinal, result in iterator:
                    counts["games_seen"] += 1
                    if result.stats.get("header_bytes") is not None:
                        counts["header_bytes_total"] += result.stats["header_bytes"]
                    if result.status == "accepted" and result.game is not None:
                        counts["games_accepted_before_dedup"] += 1
                        grouper.add(result.game)
                    elif result.status == "rejected":
                        counts["games_rejected"] += 1
                        reject_reasons[result.reason_code or "unknown"] += 1
                        rejection_stream.write(json.dumps({
                            "source_ordinal": ordinal, "status": result.status,
                            "reason_code": result.reason_code or "unknown",
                            "header_sha256": result.stats.get("header_sha256"),
                            "header_keys": result.stats.get("header_keys", []),
                        }, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n")
                        rejection_count += 1
                    else:
                        counts["games_quarantined"] += 1
                        quarantine_reasons[result.reason_code or "unknown"] += 1
                        rejection_stream.write(json.dumps({
                            "source_ordinal": ordinal, "status": result.status,
                            "reason_code": result.reason_code or "unknown",
                            "header_sha256": result.stats.get("header_sha256"),
                            "header_keys": result.stats.get("header_keys", []),
                        }, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n")
                        rejection_count += 1
                    if time.monotonic() - started > config["max_elapsed_seconds"]:
                        raise SourceLimitError("max elapsed seconds exceeded during PGN scan")
                    if ordinal % 10_000 == 0:
                        _write_progress(run_dir, ordinal, counts, started)
        if complete_scan and stream_metrics.get("stream_sha256") != source_manifest["member_sha256"]:
            raise PipelineError("streamed PGN member hash differs from source manifest")
        if stream_metrics.get("decompressed_bytes_read") != source_manifest["member_bytes"] and complete_scan:
            raise PipelineError("streamed PGN byte count differs from approved member size")
        rejection_stream.flush()
        os.fsync(rejection_stream.fileno())
        rejection_stream.close()
        temp_hash, temp_bytes = sha256_file(rejection_temp)
        if rejection_path.exists():
            if not resume:
                raise PipelineError("a parse-rejection ledger already exists; use --resume to compare it")
            prior_hash, prior_bytes = sha256_file(rejection_path)
            if (prior_hash, prior_bytes) != (temp_hash, temp_bytes):
                raise PipelineError("resumed scan produced a different parse-rejection ledger")
            rejection_temp.unlink()
        else:
            os.link(rejection_temp, rejection_path)
            rejection_temp.unlink()
    except Exception as exc:
        if not rejection_stream.closed:
            rejection_stream.close()
        _write_failure(run_dir, {
            "status": "incomplete", "failure_type": type(exc).__name__,
            "reason": str(exc)[:500], "games_seen": counts["games_seen"],
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "input_identity": input_identity,
        })
        if isinstance(exc, (PipelineError, SourceLimitError, ExportError, SplitError)):
            raise
        raise PipelineError(f"PGN processing failed: {type(exc).__name__}: {exc}") from exc
    finally:
        (run_dir / "scan-progress.json").unlink(missing_ok=True)

    games = grouper.selected_records()
    if len(games) > config["max_games"]:
        raise PipelineError("selected unique game count exceeds configured cap")
    duplicate_counts = {
        "source_level_duplicates": grouper.source_level_duplicates,
        "conflicting_source_reference_count": len(grouper.conflicting_source_refs),
        "normalized_duplicate_groups": grouper.normalized_duplicate_groups,
        "normalized_duplicate_observations": grouper.normalized_duplicate_observations,
        "conflicting_normalized_groups": len(grouper.conflicting_groups),
    }
    for game in games:
        game["source_archive_sha256"] = archive_hash
        game["source_member_name"] = member_name
        game["source_member"] = member_name
        game["split"] = None
        game["split_id"] = None
    positions = sample_positions(
        games, source_id=source_id, seed=config["sampling_seed"],
        max_positions_per_game=config["max_positions_per_game"],
        max_positions=config["max_positions"],
        sampling_config_sha256=config["config_sha256"],
    )
    parse_counts = {
        **dict(counts),
        **duplicate_counts,
        "games_seen": counts["games_seen"],
        "games_accepted_selected": len(games),
        "games_rejected": counts["games_rejected"],
        "games_quarantined": counts["games_quarantined"],
        "rejection_reasons": dict(sorted(reject_reasons.items())),
        "quarantine_reasons": dict(sorted(quarantine_reasons.items())),
        "parse_rejection_records": rejection_count,
        "parse_rejection_ledger_sha256": sha256_file(rejection_path)[0],
        "input_scan_complete": complete_scan,
        "member_stream": stream_metrics,
    }
    return games, positions, parse_counts


def _write_progress(run_dir: Path, games_seen: int, counts: Counter[str], started: float) -> None:
    path = run_dir / "scan-progress.json"
    temp = path.with_name(".scan-progress.partial")
    data = {
        "games_seen": games_seen, "games_accepted_before_dedup": counts["games_accepted_before_dedup"],
        "games_rejected": counts["games_rejected"], "games_quarantined": counts["games_quarantined"],
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    temp.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _write_failure(run_dir: Path, failure: dict[str, Any]) -> None:
    path = run_dir / "failure.json"
    if path.exists():
        path = run_dir / f"failure-{int(time.time())}.json"
    _write_new(path, json.dumps(failure, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")


def _validate_config(config: dict[str, Any]) -> None:
    required = {
        "sampling_mode", "seed", "sampling_seed", "split_seed", "max_games",
        "max_input_games_seen", "max_positions", "max_positions_per_game",
        "min_holdout_positions", "max_archive_bytes", "max_member_bytes",
        "max_total_decompressed_bytes", "max_output_bytes", "max_elapsed_seconds",
        "max_workers", "memory_mib", "max_game_bytes", "max_header_bytes",
        "max_header_value_bytes", "max_comment_bytes", "batch_size",
    }
    missing = sorted(required - set(config))
    if missing:
        raise PipelineError(f"dataset config misses required caps/values: {', '.join(missing)}")
    if config["sampling_mode"] not in {"source_window", "bottom_k"}:
        raise PipelineError("sampling_mode must be source_window or bottom_k")
    if config["max_workers"] != 1:
        raise PipelineError("M3 source parsing is single-worker only")
    for field in required - {"sampling_mode"}:
        if not isinstance(config[field], int) or config[field] < 1:
            raise PipelineError(f"{field} must be a positive integer")
    if config["sampling_mode"] == "bottom_k" and config["max_input_games_seen"] <= config["max_games"]:
        raise PipelineError("bottom_k scan cap must cover the full source beyond the selected game cap")


def build_dataset(
    archive: Path, source_manifest_path: Path, config_path: Path,
    output_path: Path, *, run_id: str, repository_root: Path,
    source_decision_path: Path, authorization_path: Path,
    confirm_write: bool, resume: bool = False,
    allow_synthetic_source_for_test: bool = False,
) -> dict[str, Any]:
    if not confirm_write:
        raise PipelineError("build requires explicit --confirm-write")
    if output_path.exists():
        raise PipelineError(f"refusing to overwrite existing release: {output_path}")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    config_doc = json.loads(config_path.read_text(encoding="utf-8")) if config_path.suffix == ".json" else None
    if config_doc is None:
        import tomllib
        with config_path.open("rb") as stream:
            config_doc = tomllib.load(stream)
    config = dict(config_doc.get("dataset", config_doc))
    _validate_config(config)
    if not source_decision_path.is_file() or not authorization_path.is_file():
        raise PipelineError("source decision or M3 authorization evidence is missing")
    if allow_synthetic_source_for_test and source_manifest.get("test_fixture") is True:
        pass
    else:
        try:
            validate_source_manifest(source_manifest)
        except ValueError as exc:
            raise PipelineError(f"source manifest validation failed: {exc}") from exc
        approval = source_manifest["approval_evidence"]
        terms = source_manifest["source_terms_evidence"]
        if (repository_root / approval["source_decision_path"]).resolve() != source_decision_path.resolve():
            raise PipelineError("source decision evidence path differs from the build argument")
        if (repository_root / approval["authorization_path"]).resolve() != authorization_path.resolve():
            raise PipelineError("authorization evidence path differs from the build argument")
        for record, field_name in (
            (approval["source_decision_path"], "source_decision_sha256"),
            (approval["authorization_path"], "authorization_sha256"),
            (terms["path"], "sha256"),
        ):
            relative = Path(record)
            if relative.is_absolute() or ".." in relative.parts:
                raise PipelineError("source evidence paths must be safe repository-relative paths")
            actual, _ = sha256_file(repository_root / relative)
            expected = approval[field_name] if field_name in approval else terms[field_name]
            if actual != expected:
                raise PipelineError(f"recorded source evidence hash mismatch: {record}")
    if source_manifest.get("member_sha256") is None:
        raise PipelineError("source manifest has no measured PGN member hash")
    code = _code_context(repository_root)
    archive_sha, archive_bytes = sha256_file(archive, max_bytes=config["max_archive_bytes"])
    if archive_sha != source_manifest.get("archive_sha256") or archive_bytes != source_manifest.get("archive_bytes"):
        raise PipelineError("archive differs from source manifest")
    archive_info = inspect_zip(
        archive, max_archive_bytes=config["max_archive_bytes"],
        max_member_bytes=config["max_member_bytes"],
        max_total_uncompressed_bytes=config["max_total_decompressed_bytes"],
        max_compression_ratio=config.get("max_compression_ratio", 200),
        expected_member=source_manifest["member"]["name"],
        expected_sha256=source_manifest["archive_sha256"],
        expected_bytes=source_manifest["archive_bytes"],
    )
    if archive_info["member"]["uncompressed_bytes"] != source_manifest["member_bytes"]:
        raise PipelineError("declared PGN member size differs from source manifest")
    if archive_info["member"]["uncompressed_bytes"] > config["max_member_bytes"]:
        raise PipelineError("PGN member exceeds configured member cap")
    source_id = source_manifest["source_id"]
    if source_manifest["member"]["name"] != source_manifest.get("member_name"):
        raise PipelineError("source manifest member names disagree")

    expanded_config = {
        **config,
        "source_archive_sha256": archive_sha,
        "source_member_sha256": source_manifest["member_sha256"],
        "source_id": source_id,
        "source_decision_id": source_manifest["source_decision_id"],
        "authorization_id": source_manifest["authorization_id"],
        "python_version": platform.python_version(),
        "python_chess_version": chess.__version__,
        **code,
    }
    expanded_config["config_sha256"] = config_identity(expanded_config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_root = output_path.parent.parent / "runs"
    run_dir = run_root / f"{run_id}.staging"
    release_staging = output_path.parent / f".{output_path.name}.{run_id}.staging"
    if release_staging.exists():
        raise PipelineError(f"incomplete release staging already exists; preserve and inspect: {release_staging}")
    if output_path.exists():
        raise PipelineError(f"release already exists: {output_path}")
    run_identity = {
        "schema": "videochess-run/1.0", "run_id": run_id,
        "source_archive_sha256": archive_sha,
        "source_member_sha256": source_manifest["member_sha256"],
        "source_member_name": source_manifest["member"]["name"],
        "config_sha256": expanded_config["config_sha256"],
        "code_revision": code["code_revision"],
        "code_tree_sha256": code["code_tree_sha256"],
        "python_version": expanded_config["python_version"],
        "python_chess_version": expanded_config["python_chess_version"],
        "authorization_id": source_manifest["authorization_id"],
        "source_decision_id": source_manifest["source_decision_id"],
    }
    started = time.monotonic()
    # Fail before source processing if peak staging plus release and a 20% reserve
    # cannot fit in the current filesystem. The exact row estimate is checked again.
    disk_free = shutil.disk_usage(output_path.parent).free
    declared_input = archive_bytes + source_manifest["member_bytes"]
    preflight_estimate = int((declared_input + 2 * config["max_output_bytes"]) * 1.2)
    if disk_free < preflight_estimate:
        raise PipelineError(f"insufficient free disk for bounded peak estimate: need {preflight_estimate}, have {disk_free}")

    try:
        games, positions_before, parse_counts = _parse_source(
            archive, source_manifest, config=expanded_config, source_id=source_id,
            run_dir=run_dir, input_identity=run_identity, resume=resume,
        )
        positions, split_manifest = split_and_purge(
            games, positions_before, seed=config["split_seed"],
            min_holdout_positions=config["min_holdout_positions"],
            min_holdout_retention=config.get("min_holdout_retention_basis_points", 5000) / 10_000,
        )
        for game in games:
            game["split"] = next(
                split for group, split in split_manifest["game_group_assignments"]
                if group == game["normalized_game_sha256"]
            )
            game["split_id"] = game["split"]
        estimated_bytes = sum(len(json.dumps(row, sort_keys=True, ensure_ascii=False).encode("utf-8")) + 1 for row in games + positions)
        estimated_bytes += len(json.dumps(split_manifest, ensure_ascii=False).encode("utf-8"))
        estimated_bytes += len(json.dumps(expanded_config, ensure_ascii=False).encode("utf-8"))
        if estimated_bytes > config["max_output_bytes"]:
            raise PipelineError(f"estimated output bytes {estimated_bytes} exceed cap {config['max_output_bytes']}")
        if shutil.disk_usage(output_path.parent).free < int((archive_bytes + 2 * estimated_bytes) * 1.2):
            raise PipelineError("free disk fell below measured peak estimate plus 20% reserve")
        sampling = {
            "method": config["sampling_mode"],
            "seed": config["sampling_seed"],
            "game_seed": config["seed"],
            "split_seed": config["split_seed"],
            "max_games": config["max_games"],
            "max_positions": config["max_positions"],
            "max_positions_per_game": config["max_positions_per_game"],
        }
        stable_resources = {
            "max_elapsed_seconds": config["max_elapsed_seconds"],
            "max_workers": config["max_workers"],
            "memory_mib": config["memory_mib"],
            "max_archive_bytes": config["max_archive_bytes"],
            "max_member_bytes": config["max_member_bytes"],
            "max_output_bytes": config["max_output_bytes"],
        }
        stats = summarize_dataset(
            games, positions_before, positions, split_manifest, parse_counts,
            sampling=sampling, resources=stable_resources,
            config_sha256=expanded_config["config_sha256"],
            source_manifest=source_manifest,
        )
        write_batches(
            run_dir, games, positions, input_identity=run_identity,
            batch_size=config["batch_size"], resume=resume,
        )
        manifest = write_release_files(
            release_staging, run_dir, positions, split_manifest, stats,
            source_manifest, expanded_config,
            max_output_bytes=config["max_output_bytes"],
            allow_synthetic_source_for_test=allow_synthetic_source_for_test,
        )
        verification = verify_release(
            release_staging, allow_synthetic_source_for_test=allow_synthetic_source_for_test,
        )
        if output_path.exists():
            raise PipelineError("release destination appeared before atomic finalization")
        os.rename(release_staging, output_path)
        elapsed = round(time.monotonic() - started, 3)
        metrics = {
            "schema": "videochess-run-metrics/1.0",
            "run_id": run_id, "release_id": manifest["release_id"],
            "elapsed_seconds": elapsed,
            "peak_rss_mib": _process_rss_mib(),
            "disk_free_before_bytes": disk_free,
            "estimated_output_bytes": estimated_bytes,
            "source_archive_bytes": archive_bytes,
            "source_member_bytes": source_manifest["member_bytes"],
            "games_seen": parse_counts["games_seen"],
            "games_accepted_selected": len(games),
            "positions_selected": len(positions_before),
            "positions_retained": len(positions),
            "output_bytes": sum(item["bytes"] for item in manifest["outputs"]),
            "verification": verification,
        }
        _write_metrics(run_dir / "run-metrics.json", metrics)
        return {"release": manifest, "verification": verification, "run_metrics": metrics, "output_path": str(output_path)}
    except SplitError as exc:
        _write_failure(run_dir, {
            "status": "incomplete", "failure_type": "SplitError",
            "reason": str(exc)[:500], "split_manifest": exc.manifest,
            "input_identity": run_identity,
        })
        raise PipelineError(f"leakage/holdout validation failed: {exc}") from exc
    except Exception as exc:
        if not (run_dir / "failure.json").exists():
            _write_failure(run_dir, {
                "status": "incomplete", "failure_type": type(exc).__name__,
                "reason": str(exc)[:500], "input_identity": run_identity,
            })
        if isinstance(exc, PipelineError):
            raise
        raise PipelineError(f"dataset build failed: {type(exc).__name__}: {exc}") from exc
