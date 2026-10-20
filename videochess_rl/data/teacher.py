"""Bounded Stockfish 19 offline teacher sidecar generation."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import chess
import chess.engine

from .contracts import (
    TEACHER_SCHEMA, canonical_fen, candidate_identity, config_identity, digest,
    reconstruct_position, sample_set_identity, validate_position_record,
)
from .export import _write_new, json_line, verify_release
from .source import sha256_file


class TeacherError(RuntimeError):
    """Teacher configuration or bounded engine run failed."""


def _cp_transform(cp: int) -> str:
    return format(math.tanh(cp / 400.0), ".8f")


def _score_data(info: dict[str, Any], board: chess.Board) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    pov_score = info.get("score")
    if pov_score is None:
        return None, None
    relative = pov_score.pov(board.turn)
    if relative.is_mate():
        mate = relative.mate()
        raw = {
            "type": "mate", "value": mate,
            "perspective": "side_to_move",
        }
        white_mate = mate if board.turn == chess.WHITE else (-mate if mate is not None else None)
        return raw, {"type": "mate", "value": white_mate, "perspective": "white"}
    cp = relative.score(mate_score=None)
    if cp is None:
        return None, None
    raw = {"type": "cp", "value": int(cp), "unit": "centipawn", "perspective": "side_to_move"}
    white_cp = int(cp) if board.turn == chess.WHITE else -int(cp)
    return raw, {"type": "cp", "value": white_cp, "unit": "centipawn", "perspective": "white"}


def _wdl_data(info: dict[str, Any], turn: chess.Color) -> dict[str, int] | None:
    value = info.get("wdl")
    if value is None:
        return None
    if hasattr(value, "pov"):
        value = value.pov(turn)
    fields = ("wins", "draws", "losses")
    if all(hasattr(value, field) for field in fields):
        return {field: int(getattr(value, field)) for field in fields}
    return None


def _engine_config(engine: chess.engine.SimpleEngine, requested: dict[str, Any]) -> dict[str, Any]:
    configured = getattr(engine.protocol, "config", {})
    if not isinstance(configured, Mapping):
        raise TeacherError("UCI protocol does not expose effective option values")
    result = {}
    for name, expected in requested.items():
        if name not in configured and name.lower() not in configured:
            raise TeacherError(f"engine effective option is unavailable for {name}")
        actual = configured.get(name, configured.get(name.lower()))
        if actual != expected:
            raise TeacherError(f"engine did not retain requested option {name}={expected!r}; got {actual!r}")
        result[name] = actual
    return result


def _terminate_engine(engine: chess.engine.SimpleEngine) -> None:
    """Close the protocol and kill a subprocess that does not exit promptly."""
    try:
        engine.close()
    except Exception:
        pass
    try:
        transport = getattr(engine, "transport", None)
        process = transport.get_extra_info("subprocess") if transport is not None else None
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=2)
    except Exception:
        pass


def _kill_engine_process(engine: chess.engine.SimpleEngine) -> bool:
    """Interrupt a UCI subprocess without cancelling python-chess's future."""
    try:
        transport = getattr(engine, "transport", None)
        process = transport.get_extra_info("subprocess") if transport is not None else None
        if process is not None and process.poll() is None:
            process.kill()
            return True
    except Exception:
        pass
    return False


def run_teacher(
    release_dir: Path, games_path: Path, output_dir: Path, *,
    engine_path: Path, expected_engine_sha256: str,
    license_path: Path, expected_license_sha256: str,
    max_positions: int, sample_seed: int, nodes_per_position: int,
    multipv: int = 3, threads: int = 1, hash_mib: int = 64,
    timeout_seconds: float = 30.0, max_wall_seconds: int = 1800,
    authorization_id: str, source_decision_id: str,
    confirm_write: bool, code_revision: str,
    max_output_bytes: int = 64 * 1024 * 1024,
    allow_synthetic_source_for_test: bool = False,
) -> dict[str, Any]:
    if not confirm_write:
        raise TeacherError("teacher run requires explicit --confirm-write")
    if output_dir.exists():
        raise TeacherError(f"refusing to overwrite teacher sidecar: {output_dir}")
    if not (1 <= max_positions <= 1000 and 1 <= nodes_per_position <= 50_000):
        raise TeacherError("teacher limits exceed the bounded M3 ceiling")
    if multipv not in (1, 2, 3) or threads != 1 or not 1 <= hash_mib <= 256:
        raise TeacherError("teacher options exceed the bounded M3 settings")
    if max_output_bytes < 1024 * 1024:
        raise TeacherError("teacher output cap must be at least 1 MiB")
    if not engine_path.is_file() or not os.access(engine_path, os.X_OK):
        raise TeacherError("verified Stockfish binary is missing or not executable")
    binary_sha, binary_bytes = sha256_file(engine_path)
    license_sha, license_bytes = sha256_file(license_path)
    if binary_sha != expected_engine_sha256 or license_sha != expected_license_sha256:
        raise TeacherError("Stockfish binary or retained license text hash differs from M0 evidence")
    verified = verify_release(release_dir, allow_synthetic_source_for_test=allow_synthetic_source_for_test)
    release = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
    if release.get("authorization_id") != authorization_id or release.get("source_decision_id") != source_decision_id:
        raise TeacherError("teacher authorization/source-decision IDs differ from the dataset release")
    games_manifest = next((item for item in release["outputs"] if item["path"] == "games.jsonl"), None)
    games_sha, games_bytes = sha256_file(games_path)
    if not games_manifest or (games_sha, games_bytes) != (games_manifest["sha256"], games_manifest["bytes"]):
        raise TeacherError("teacher game input differs from the verified dataset release")
    position_rows = []
    with (release_dir / "positions.jsonl").open("r", encoding="utf-8") as stream:
        for line in stream:
            position_rows.append(json.loads(line))
    games = {}
    with games_path.open("r", encoding="utf-8") as stream:
        for line in stream:
            game = json.loads(line)
            games[game["game_id"]] = game
    if len({row["sample_id"] for row in position_rows}) != len(position_rows):
        raise TeacherError("release contains duplicate samples")
    ranked = sorted(
        (
            digest({"domain": "videochess-teacher-sample/v1", "seed": sample_seed, "sample_id": row["sample_id"]}),
            row["sample_id"], row,
        )
        for row in position_rows
    )
    selected = [item[2] for item in ranked[:max_positions]]
    if not selected:
        raise TeacherError("release contains no positions to analyze")
    teacher_config = {
        "schema": TEACHER_SCHEMA, "sample_seed": sample_seed,
        "max_positions": max_positions, "nodes_per_position": nodes_per_position,
        "multipv": multipv, "threads": threads, "hash_mib": hash_mib,
        "timeout_seconds": format(timeout_seconds, ".3f"),
        "watchdog_grace_seconds": format(min(2.0, timeout_seconds * 0.1), ".3f"),
        "clear_hash_between_positions": True,
        "max_wall_seconds": max_wall_seconds,
        "max_output_bytes": max_output_bytes,
        "node_budget_semantics": "one UCI nodes limit per root position search, shared across its MultiPV lines",
        "time_budget_semantics": "UCI movetime cap per root position, also used as the python-chess protocol response deadline",
        "watchdog_grace_semantics": "min(2 seconds, 10 percent of the per-root cap, remaining run wall budget after the cap)",
        "raw_root_perspective": "side_to_move",
        "normalization": {
            "id": "cp-tanh-400/v1",
            "formula": "tanh(cp / 400.0), rounded to 8 decimal places",
            "scope": "centipawn scores only; mate scores remain typed and have no normalized scalar",
        },
    }
    code_dir = Path(__file__).resolve().parent
    code_hash = hashlib.sha256()
    for path in sorted(code_dir.glob("*.py")):
        code_hash.update(path.name.encode("utf-8") + b"\0")
        code_hash.update(path.read_bytes())
    code_tree_sha256 = code_hash.hexdigest()
    teacher_config_sha = config_identity(teacher_config)
    sample_set_sha = sample_set_identity([row["sample_id"] for row in selected])
    teacher_run_id = digest({
        "domain": "videochess-teacher-run/v1",
        "teacher_schema_version": TEACHER_SCHEMA,
        "dataset_release_id": release["release_id"],
        "teacher_config_sha256": teacher_config_sha,
        "engine_sha256": binary_sha,
        "engine_license_sha256": license_sha,
        "code_revision": code_revision,
        "code_tree_sha256": code_tree_sha256,
        "sample_ids_sha256": sample_set_sha,
    })
    requested_options = {
        "Threads": threads, "Hash": hash_mib, "MultiPV": multipv,
        "UCI_Chess960": False,
    }
    started = time.monotonic()
    result_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    engine = None
    engine_usable = True
    effective_options: dict[str, Any] = {}
    engine_id: dict[str, Any] = {}
    output_dir.mkdir(parents=True, exist_ok=False)

    def status_row(
        position: dict[str, Any], status: str, reason: str,
        search_time_cap_seconds: float | None = None,
        watchdog_grace_seconds: float | None = None,
    ) -> dict[str, Any]:
        row = {
            "schema": TEACHER_SCHEMA, "teacher_run_id": teacher_run_id,
            "teacher_config_sha256": teacher_config_sha,
            "dataset_release_id": release["release_id"],
            "sample_id": position["sample_id"], "game_id": position["game_id"],
            "ply_index": position["ply_index"], "root_fen": position["fen"],
            "split": position["split"], "split_id": position["split_id"],
            "root_perspective": "side_to_move", "status": status,
            "reason": reason[:240],
        }
        if search_time_cap_seconds is not None:
            row["search_time_cap_seconds"] = round(search_time_cap_seconds, 6)
        if watchdog_grace_seconds is not None:
            row["watchdog_grace_seconds"] = round(watchdog_grace_seconds, 6)
        return row

    try:
        engine = chess.engine.SimpleEngine.popen_uci(str(engine_path), timeout=timeout_seconds)
        engine_id = dict(engine.id)
        if "Stockfish 19" not in engine_id.get("name", ""):
            raise TeacherError(f"UCI identity is not Stockfish 19: {engine_id.get('name', 'unknown')}")
        supported = engine.options
        missing = [name for name in ("Threads", "Hash", "MultiPV", "UCI_Chess960", "Clear Hash") if name not in supported]
        if missing:
            raise TeacherError(f"Stockfish is missing required UCI options: {missing}")
        configure_options = {"Threads": threads, "Hash": hash_mib}
        if "UCI_ShowWDL" in supported:
            configure_options["UCI_ShowWDL"] = True
            requested_options["UCI_ShowWDL"] = True
        engine.configure(configure_options)
        effective_options = _engine_config(engine, configure_options)
        for position_index, position in enumerate(selected):
            elapsed_total = time.monotonic() - started
            remaining_wall = max_wall_seconds - elapsed_total
            if remaining_wall <= 0.01:
                for remaining in selected[position_index:]:
                    failure = {"sample_id": remaining["sample_id"], "status": "not_attempted", "reason": "teacher wall-time cap reached"}
                    failures.append(failure)
                    result_rows.append(status_row(remaining, "not_attempted", failure["reason"]))
                break
            position_time_cap = min(timeout_seconds, remaining_wall)
            watchdog_grace = min(2.0, position_time_cap * 0.1, max(0.0, remaining_wall - position_time_cap))
            game = games.get(position["game_id"])
            if game is None:
                failure = {"sample_id": position["sample_id"], "status": "error", "reason": "missing parent game"}
                failures.append(failure)
                result_rows.append(status_row(position, "error", failure["reason"]))
                continue
            search_timed_out = threading.Event()
            try:
                board = reconstruct_position(game, position["ply_index"])
                if canonical_fen(board) != position["fen"]:
                    raise TeacherError("reconstructed teacher board differs from release FEN")
                if board.is_game_over(claim_draw=False):
                    failure = {"sample_id": position["sample_id"], "status": "terminal", "reason": "position is terminal"}
                    failures.append(failure)
                    result_rows.append(status_row(position, "terminal", failure["reason"]))
                    continue
                before = time.monotonic()
                engine.configure({"Clear Hash": None})
                def expire_search() -> None:
                    if _kill_engine_process(engine):
                        search_timed_out.set()

                watchdog = threading.Timer(
                    timeout_seconds + watchdog_grace,
                    expire_search,
                )
                watchdog.daemon = True
                watchdog.start()
                try:
                    infos = engine.analyse(
                        board, chess.engine.Limit(nodes=nodes_per_position, time=position_time_cap),
                        multipv=multipv,
                    )
                finally:
                    watchdog.cancel()
                if search_timed_out.is_set():
                    raise TimeoutError("Stockfish did not return before the per-position watchdog")
                # python-chess owns these options because they follow each
                # board/search. Verify their effective values after searching.
                effective_options.update(_engine_config(engine, {
                    "MultiPV": multipv, "UCI_Chess960": False,
                }))
                if isinstance(infos, dict):
                    infos = [infos]
                elapsed = round(time.monotonic() - before, 6)
                lines = []
                for rank, info in enumerate(infos, 1):
                    pv = info.get("pv") or []
                    first_move = pv[0].uci() if pv else None
                    if first_move is None:
                        raise TeacherError("engine returned no usable principal variation/root action")
                    if first_move not in position["legal_moves_uci"]:
                        raise TeacherError(f"engine returned illegal root action {first_move}")
                    raw_score, white_score = _score_data(info, board)
                    if raw_score is None:
                        raise TeacherError("engine returned no root score")
                    cp_value = raw_score["value"] if raw_score["type"] == "cp" else None
                    wdl = _wdl_data(info, board.turn)
                    lines.append({
                        "rank": rank,
                        "pv_uci": [move.uci() for move in pv],
                        "first_move_uci": first_move,
                        "candidate_id": candidate_identity(position["sample_id"], first_move) if first_move else None,
                        "raw_score_side_to_move": raw_score,
                        "raw_score_white": white_score,
                        "transformed_target": _cp_transform(cp_value) if cp_value is not None else None,
                        "transform_id": "cp-tanh-400/v1" if cp_value is not None else None,
                        "mate_normalization": "mate retained as signed mate distance; no centipawn substitution" if raw_score["type"] == "mate" else None,
                        "wdl_side_to_move": wdl,
                        "depth": info.get("depth"),
                        "seldepth": info.get("seldepth"),
                        "nodes": info.get("nodes"),
                        "elapsed_seconds": elapsed,
                    })
                result_rows.append({
                    "schema": TEACHER_SCHEMA, "teacher_run_id": teacher_run_id,
                    "teacher_config_sha256": teacher_config_sha,
                    "dataset_release_id": release["release_id"],
                    "sample_id": position["sample_id"],
                    "game_id": position["game_id"], "ply_index": position["ply_index"],
                    "root_fen": position["fen"],
                    "split": position["split"], "split_id": position["split_id"],
                    "root_perspective": "side_to_move",
                    "search_time_cap_seconds": round(position_time_cap, 6),
                    "watchdog_grace_seconds": round(watchdog_grace, 6),
                    "status": "ok", "multipv_lines": lines,
                    "engine": {"name": engine_id.get("name"), "author": engine_id.get("author"), "binary_sha256": binary_sha},
                })
            except (chess.engine.EngineError, TimeoutError, OSError, TeacherError, ValueError) as exc:
                reason = (
                    f"TimeoutError: Stockfish exceeded {position_time_cap:.3f}s search cap plus {watchdog_grace:.3f}s watchdog grace"
                    if search_timed_out.is_set() else f"{type(exc).__name__}: {str(exc)[:240]}"
                )
                failures.append({"sample_id": position["sample_id"], "status": "error", "reason": reason})
                result_rows.append(status_row(position, "error", reason, position_time_cap, watchdog_grace))
                if isinstance(exc, (chess.engine.EngineError, TimeoutError, OSError)):
                    engine_usable = False
                    if engine is not None:
                        _terminate_engine(engine)
                if engine is None or not engine_usable or getattr(engine, "returncode", None) is not None:
                    for remaining in selected[position_index + 1:]:
                        failure = {"sample_id": remaining["sample_id"], "status": "not_attempted", "reason": "engine exited after a position failure"}
                        failures.append(failure)
                        result_rows.append(status_row(remaining, "not_attempted", failure["reason"]))
                    break
    except Exception as exc:
        if result_rows:
            partial = b"".join(json_line(row) for row in result_rows)
            if len(partial) <= max_output_bytes:
                _write_new(output_dir / "teacher.partial.jsonl", partial)
        _write_new(
            output_dir / "failure.json",
            json.dumps({"status": "incomplete", "failure_type": type(exc).__name__, "reason": str(exc)[:500]}, sort_keys=True, indent=2).encode("utf-8") + b"\n",
        )
        raise TeacherError(f"Stockfish teacher run failed: {type(exc).__name__}: {exc}") from exc
    finally:
        if engine is not None:
            if engine_usable:
                try:
                    engine.quit()
                except Exception:
                    pass
            _terminate_engine(engine)
    elapsed_total = round(time.monotonic() - started, 3)
    successful_rows = [row for row in result_rows if row["status"] == "ok"]
    if not successful_rows:
        partial = b"".join(json_line(row) for row in result_rows)
        if len(partial) <= max_output_bytes:
            _write_new(output_dir / "teacher.partial.jsonl", partial)
        _write_new(
            output_dir / "failure.json",
            json.dumps({"status": "incomplete", "failure_type": "TeacherError", "reason": "teacher run produced no successful positions"}, sort_keys=True, indent=2).encode("utf-8") + b"\n",
        )
        raise TeacherError("teacher run produced no successful position records")
    rows_bytes = b"".join(json_line(record) for record in result_rows)
    if len(rows_bytes) > max_output_bytes:
        _write_new(
            output_dir / "failure.json",
            json.dumps({"status": "incomplete", "failure_type": "TeacherError", "reason": "teacher output byte cap exceeded", "observed_bytes": len(rows_bytes), "max_output_bytes": max_output_bytes}, sort_keys=True, indent=2).encode("utf-8") + b"\n",
        )
        raise TeacherError("teacher output byte cap exceeded")
    row_path = output_dir / "teacher.jsonl"
    _write_new(row_path, rows_bytes)
    row_sha = hashlib.sha256(rows_bytes).hexdigest()
    score_types = {"cp": 0, "mate": 0}
    root_nodes = []
    for record in successful_rows:
        root_nodes.append(max((line["nodes"] or 0 for line in record["multipv_lines"]), default=0))
        for line in record["multipv_lines"]:
            score_types[line["raw_score_side_to_move"]["type"]] += 1
    manifest = {
        "schema": "videochess-teacher-run-manifest/1.0",
        "teacher_run_id": teacher_run_id,
        "dataset_release_id": release["release_id"],
        "dataset_manifest_sha256": verified["manifest_sha256"],
        "source_archive_sha256": release["source_archive_sha256"],
        "source_decision_id": source_decision_id,
        "authorization_id": authorization_id,
        "engine": {
            "name": engine_id.get("name"), "author": engine_id.get("author"),
            "binary_sha256": binary_sha, "binary_bytes": binary_bytes,
            "license_sha256": license_sha, "license_bytes": license_bytes,
            "license": "GPL-3.0; host binary/license are not redistributed",
            "host_binary_reference": "existing M0 Stockfish 19 installation",
            "platform": platform.platform(),
        },
        "search": {
            "requested_options": requested_options, "effective_options": effective_options,
            "limit_type": "nodes_and_time", "nodes_per_root_position": nodes_per_position,
            "node_budget_semantics": teacher_config["node_budget_semantics"],
            "time_budget_semantics": teacher_config["time_budget_semantics"],
            "watchdog_grace_semantics": teacher_config["watchdog_grace_semantics"],
            "max_search_time_cap_seconds": timeout_seconds,
            "watchdog_grace_seconds": min(2.0, timeout_seconds * 0.1),
            "search_watchdog_seconds": timeout_seconds + min(2.0, timeout_seconds * 0.1),
            "applied_search_time_caps_seconds": [
                row["search_time_cap_seconds"] for row in result_rows
                if row.get("search_time_cap_seconds") is not None
            ],
            "applied_watchdog_graces_seconds": [
                row["watchdog_grace_seconds"] for row in result_rows
                if row.get("watchdog_grace_seconds") is not None
            ],
            "clear_hash_between_positions": True,
            "reported_nodes_per_analyzed_root": root_nodes,
            "reported_nodes_total": sum(root_nodes),
            "multipv": multipv, "threads": threads, "hash_mib": hash_mib,
            "wall_watchdog_seconds": timeout_seconds,
            "root_score_perspective": "side_to_move; White conversion stored separately",
        },
        "normalization": teacher_config["normalization"],
        "mate_handling": "signed mate distance retained in its own type; no arbitrary centipawn constant and no scalar normalization",
        "sample_seed": sample_seed,
        "sample_ids_sha256": sample_set_sha,
        "positions_selected": len(selected),
        "positions_analyzed": len(successful_rows),
        "positions_with_rows": len(result_rows),
        "positions_failed_or_unattempted": failures,
        "multipv_score_types": score_types,
        "teacher_config": teacher_config,
        "teacher_config_sha256": teacher_config_sha,
        "code_revision": code_revision,
        "code_tree_sha256": code_tree_sha256,
        "results": {"path": row_path.name, "bytes": len(rows_bytes), "sha256": row_sha},
        "elapsed_seconds": elapsed_total,
        "throughput_positions_per_second": round(len(successful_rows) / elapsed_total, 4) if elapsed_total else None,
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    _write_new(output_dir / "manifest.json", manifest_bytes)
    _write_new(output_dir / "manifest.sha256", (hashlib.sha256(manifest_bytes).hexdigest() + "  manifest.json\n").encode("ascii"))
    verify_teacher_run(output_dir, release_dir, allow_synthetic_source_for_test=allow_synthetic_source_for_test)
    return manifest


def verify_teacher_run(
    teacher_dir: Path, release_dir: Path, *, allow_synthetic_source_for_test: bool = False,
) -> dict[str, Any]:
    """Verify sidecar hashes, deterministic coverage, PV legality, and score semantics."""
    manifest_path = teacher_dir / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    expected_manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    checksum = (teacher_dir / "manifest.sha256").read_text(encoding="ascii").strip().split()
    if not checksum or checksum[0] != expected_manifest_sha:
        raise TeacherError("teacher manifest checksum mismatch")
    manifest = json.loads(manifest_bytes)
    release_check = verify_release(release_dir, allow_synthetic_source_for_test=allow_synthetic_source_for_test)
    release_manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "videochess-teacher-run-manifest/1.0":
        raise TeacherError("unsupported teacher run manifest schema")
    if manifest.get("dataset_release_id") != release_check["release_id"] or manifest.get("dataset_manifest_sha256") != release_check["manifest_sha256"]:
        raise TeacherError("teacher run is bound to a different dataset release")
    if manifest.get("source_archive_sha256") != release_manifest.get("source_archive_sha256"):
        raise TeacherError("teacher source archive identity differs from dataset release")
    if manifest.get("authorization_id") != release_manifest.get("authorization_id") or manifest.get("source_decision_id") != release_manifest.get("source_decision_id"):
        raise TeacherError("teacher authorization/source decision differs from dataset release")
    config = manifest.get("teacher_config")
    if not isinstance(config, dict) or config_identity(config) != manifest.get("teacher_config_sha256"):
        raise TeacherError("teacher configuration identity does not recompute")
    if manifest.get("normalization") != config.get("normalization"):
        raise TeacherError("teacher normalization differs from its configuration")
    results = manifest.get("results", {})
    if results.get("path") != "teacher.jsonl":
        raise TeacherError("teacher results path is unsafe or unexpected")
    rows_path = teacher_dir / "teacher.jsonl"
    rows_sha, rows_bytes = sha256_file(rows_path, max_bytes=config.get("max_output_bytes"))
    if rows_sha != results.get("sha256") or rows_bytes != results.get("bytes"):
        raise TeacherError("teacher results hash or byte count mismatch")
    actual_paths = {path.name for path in teacher_dir.iterdir() if path.is_file()}
    if actual_paths != {"teacher.jsonl", "manifest.json", "manifest.sha256"}:
        raise TeacherError("teacher sidecar contains unlisted files")

    positions: dict[str, dict[str, Any]] = {}
    with (release_dir / "positions.jsonl").open("r", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            positions[row["sample_id"]] = row
    games: dict[str, dict[str, Any]] = {}
    with (release_dir / "games.jsonl").open("r", encoding="utf-8") as stream:
        for line in stream:
            game = json.loads(line)
            games[game["game_id"]] = game
    sample_seed = manifest.get("sample_seed")
    selected_limit = config.get("max_positions")
    if not isinstance(selected_limit, int) or selected_limit < 1:
        raise TeacherError("teacher selected-position limit is malformed")
    selected = sorted(
        positions.values(),
        key=lambda row: (
            digest({"domain": "videochess-teacher-sample/v1", "seed": sample_seed, "sample_id": row["sample_id"]}),
            row["sample_id"],
        ),
    )[:selected_limit]
    selected_ids = [row["sample_id"] for row in selected]
    sample_sha = sample_set_identity(selected_ids)
    if sample_sha != manifest.get("sample_ids_sha256"):
        raise TeacherError("teacher deterministic sample selection does not recompute")
    expected_run_id = digest({
        "domain": "videochess-teacher-run/v1", "teacher_schema_version": TEACHER_SCHEMA,
        "dataset_release_id": release_check["release_id"],
        "teacher_config_sha256": manifest["teacher_config_sha256"],
        "engine_sha256": manifest["engine"]["binary_sha256"],
        "engine_license_sha256": manifest["engine"]["license_sha256"],
        "code_revision": manifest["code_revision"],
        "code_tree_sha256": manifest["code_tree_sha256"],
        "sample_ids_sha256": sample_sha,
    })
    if manifest.get("teacher_run_id") != expected_run_id:
        raise TeacherError("teacher run identity does not recompute")

    seen: set[str] = set()
    score_types = {"cp": 0, "mate": 0}
    nodes_by_root: list[int] = []
    applied_time_caps: list[float] = []
    applied_watchdog_graces: list[float] = []
    success_count = 0
    failure_rows: list[dict[str, str]] = []
    with rows_path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            sample_id = row.get("sample_id")
            if sample_id not in selected_ids or sample_id in seen:
                raise TeacherError(f"teacher row sample identity is unexpected or duplicated at line {line_number}")
            seen.add(sample_id)
            if row.get("schema") != TEACHER_SCHEMA or row.get("teacher_run_id") != expected_run_id:
                raise TeacherError(f"teacher row schema/run identity mismatch at line {line_number}")
            applied_time_cap = row.get("search_time_cap_seconds")
            applied_grace = row.get("watchdog_grace_seconds")
            if applied_time_cap is not None:
                if (isinstance(applied_time_cap, bool) or not isinstance(applied_time_cap, (int, float))
                        or not 0 < applied_time_cap <= float(config["timeout_seconds"])):
                    raise TeacherError(f"teacher per-position time cap is invalid at line {line_number}")
                applied_time_caps.append(float(applied_time_cap))
            if applied_grace is not None:
                if (isinstance(applied_grace, bool) or not isinstance(applied_grace, (int, float))
                        or not 0 <= applied_grace <= min(2.0, float(applied_time_cap) * 0.1) + 1e-6):
                    raise TeacherError(f"teacher watchdog grace is invalid at line {line_number}")
                applied_watchdog_graces.append(float(applied_grace))
            if row.get("dataset_release_id") != release_check["release_id"]:
                raise TeacherError(f"teacher row dataset identity mismatch at line {line_number}")
            position = positions[sample_id]
            if row.get("split") != position["split"] or row.get("split_id") != position["split_id"]:
                raise TeacherError(f"teacher row split does not inherit its parent sample at line {line_number}")
            if row.get("status") != "ok":
                if row.get("status") not in {"error", "terminal", "not_attempted"} or not row.get("reason"):
                    raise TeacherError(f"teacher failure row is malformed at line {line_number}")
                failure_rows.append({"sample_id": sample_id, "status": row["status"], "reason": row["reason"]})
                continue
            success_count += 1
            game = games.get(position["game_id"])
            if game is None or row.get("game_id") != position["game_id"] or row.get("ply_index") != position["ply_index"]:
                raise TeacherError(f"teacher row parent sample mismatch at line {line_number}")
            root_board = validate_position_record(position, game)
            if row.get("root_fen") != position["fen"] or row.get("root_perspective") != "side_to_move":
                raise TeacherError(f"teacher root state/perspective mismatch at line {line_number}")
            lines = row.get("multipv_lines")
            if not isinstance(lines, list) or not 1 <= len(lines) <= config["multipv"]:
                raise TeacherError(f"teacher MultiPV count is invalid at line {line_number}")
            nodes_by_root.append(max((entry.get("nodes") or 0 for entry in lines), default=0))
            prior_rank = 0
            for entry in lines:
                rank = entry.get("rank", 0)
                if not isinstance(rank, int) or rank <= prior_rank:
                    raise TeacherError(f"teacher MultiPV ranks are not increasing at line {line_number}")
                prior_rank = rank
                pv = entry.get("pv_uci", [])
                if not pv or entry.get("first_move_uci") != pv[0]:
                    raise TeacherError(f"teacher PV has no stable root action at line {line_number}")
                move = chess.Move.from_uci(pv[0])
                if move not in root_board.legal_moves:
                    raise TeacherError(f"teacher PV root action is illegal at line {line_number}")
                if candidate_identity(sample_id, pv[0]) != entry.get("candidate_id"):
                    raise TeacherError(f"teacher candidate identity mismatch at line {line_number}")
                line_board = root_board.copy()
                for uci in pv:
                    move = chess.Move.from_uci(uci)
                    if move not in line_board.legal_moves:
                        raise TeacherError(f"teacher PV is illegal at line {line_number}")
                    line_board.push(move)
                raw = entry.get("raw_score_side_to_move", {})
                white = entry.get("raw_score_white", {})
                if raw.get("perspective") != "side_to_move" or white.get("perspective") != "white":
                    raise TeacherError(f"teacher score perspectives are missing at line {line_number}")
                if raw.get("type") == "cp":
                    if white.get("type") != "cp" or raw.get("unit") != "centipawn":
                        raise TeacherError(f"centipawn score typing is invalid at line {line_number}")
                    expected_white = raw["value"] if position["side_to_move"] == "white" else -raw["value"]
                    if white.get("value") != expected_white or entry.get("transformed_target") != _cp_transform(raw["value"]):
                        raise TeacherError(f"centipawn score perspective/normalization mismatch at line {line_number}")
                    if entry.get("transform_id") != "cp-tanh-400/v1" or entry.get("mate_normalization") is not None:
                        raise TeacherError(f"centipawn transform metadata is invalid at line {line_number}")
                elif raw.get("type") == "mate":
                    expected_white = raw.get("value") if position["side_to_move"] == "white" else (-raw.get("value") if raw.get("value") is not None else None)
                    if white.get("type") != "mate" or white.get("value") != expected_white:
                        raise TeacherError(f"mate score perspective conversion mismatch at line {line_number}")
                    if entry.get("transformed_target") is not None or entry.get("transform_id") is not None or not entry.get("mate_normalization"):
                        raise TeacherError(f"mate score was incorrectly normalized at line {line_number}")
                else:
                    raise TeacherError(f"unknown teacher score type at line {line_number}")
                score_types[raw["type"]] += 1
    if seen != set(selected_ids):
        raise TeacherError("teacher sidecar does not contain one status row per selected sample")
    if success_count != manifest.get("positions_analyzed") or len(selected_ids) != manifest.get("positions_selected"):
        raise TeacherError("teacher manifest position totals differ from result rows")
    if failure_rows != manifest.get("positions_failed_or_unattempted"):
        raise TeacherError("teacher failure summary differs from result rows")
    search = manifest.get("search", {})
    if applied_time_caps != search.get("applied_search_time_caps_seconds"):
        raise TeacherError("teacher per-position search caps differ from the manifest")
    if applied_watchdog_graces != search.get("applied_watchdog_graces_seconds"):
        raise TeacherError("teacher watchdog grace values differ from the manifest")
    if score_types != manifest.get("multipv_score_types") or nodes_by_root != manifest.get("search", {}).get("reported_nodes_per_analyzed_root"):
        raise TeacherError("teacher score/node summaries differ from result rows")
    return {
        "teacher_run_id": expected_run_id, "positions_selected": len(selected_ids),
        "positions_analyzed": success_count,
        "positions_failed_or_unattempted": len(selected_ids) - success_count,
        "multipv_score_types": score_types, "manifest_sha256": expected_manifest_sha,
        "results_sha256": rows_sha,
    }
