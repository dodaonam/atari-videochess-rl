"""Atomic JSONL output, batch journal, release hashing, and verification."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any, Iterable

from .contracts import (
    GAME_SCHEMA, LEGACY_SPLIT_SCHEMA, POSITION_SCHEMA, SPLIT_SCHEMA, board_position_signature,
    board_signature_owner, config_identity, reconstruct_position,
    release_identity, replay_history_identity, sample_identity,
    split_manifest_identity, validate_game_record, validate_position_record,
)
from .source import sha256_file, validate_source_manifest
from .stats import (
    STATS_SCHEMA, quality_distribution_shifts, summarize_dataset,
)
from .split import MIN_HOLDOUT_RETENTION


class ExportError(ValueError):
    """Dataset output, journal, or release failed validation."""


def json_line(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8") + b"\n"


def _write_new(path: Path, data: bytes) -> None:
    if path.exists():
        raise ExportError(f"refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.partial")
    with temp.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temp, path)
    except FileExistsError as exc:
        raise ExportError(f"refusing to overwrite existing file: {path}") from exc
    finally:
        temp.unlink(missing_ok=True)


def _write_jsonl_new(path: Path, rows: Iterable[dict[str, Any]], cap: int) -> tuple[int, int, str]:
    if path.exists():
        raise ExportError(f"refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.partial")
    digest = hashlib.sha256()
    total = count = 0
    with temp.open("xb") as stream:
        for row in rows:
            line = json_line(row)
            total += len(line)
            if total > cap:
                raise ExportError(f"output exceeds configured byte cap ({cap})")
            stream.write(line)
            digest.update(line)
            count += 1
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temp, path)
    except FileExistsError as exc:
        raise ExportError(f"refusing to overwrite existing file: {path}") from exc
    finally:
        temp.unlink(missing_ok=True)
    return count, total, digest.hexdigest()


def _copy_file_new(path: Path, source: Path, cap: int) -> tuple[int, str]:
    if path.exists():
        raise ExportError(f"refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.partial")
    total = 0
    digest = hashlib.sha256()
    with source.open("rb") as input_stream, temp.open("xb") as output_stream:
        while True:
            chunk = input_stream.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > cap:
                raise ExportError(f"copied output exceeds configured byte cap ({cap})")
            output_stream.write(chunk)
            digest.update(chunk)
        output_stream.flush()
        os.fsync(output_stream.fileno())
    try:
        os.link(temp, path)
    except FileExistsError as exc:
        raise ExportError(f"refusing to overwrite existing file: {path}") from exc
    finally:
        temp.unlink(missing_ok=True)
    return total, digest.hexdigest()


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ExportError(f"invalid JSONL at {path.name}:{line_number}") from exc
            if not isinstance(value, dict):
                raise ExportError(f"JSONL row is not an object at {path.name}:{line_number}")
            yield value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ExportError(f"invalid JSONL at {path.name}:{line_number}") from exc
            if not isinstance(value, dict):
                raise ExportError(f"JSONL row is not an object at {path.name}:{line_number}")
            rows.append(value)
    return rows


def _append_journal(path: Path, entry: dict[str, Any]) -> None:
    line = json_line(entry)
    with path.open("ab") as stream:
        stream.write(line)
        stream.flush()
        os.fsync(stream.fileno())


def _journal_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries = _load_jsonl(path)
    for index, entry in enumerate(entries):
        if entry.get("batch_index") != index:
            raise ExportError("journal batch indices have a gap, overlap, or reordering")
    return entries


def _verify_batches(run_dir: Path, identity: dict[str, Any]) -> list[dict[str, Any]]:
    journal_path = run_dir / "journal.jsonl"
    entries = _journal_entries(journal_path)
    batch_dirs = sorted(path for path in run_dir.glob("batch-*" ) if path.is_dir())
    expected_names = [f"batch-{index:06d}" for index in range(len(entries))]
    if [path.name for path in batch_dirs] != expected_names:
        raise ExportError("batch segments and journal do not form a contiguous sequence")
    seen_games: set[str] = set()
    seen_samples: set[str] = set()
    expected_record_start = 0
    prior_source_ordinal_max = 0
    for index, entry in enumerate(entries):
        if entry.get("input_identity") != identity:
            raise ExportError("journal segment identity changed")
        directory = run_dir / f"batch-{index:06d}"
        for name, key in (("games.jsonl", "games_sha256"), ("positions.jsonl", "positions_sha256")):
            digest, size = sha256_file(directory / name)
            if digest != entry.get(key) or size != entry.get(name.replace(".jsonl", "_bytes")):
                raise ExportError(f"batch hash/size mismatch: {directory.name}/{name}")
        games = _load_jsonl(directory / "games.jsonl")
        positions = _load_jsonl(directory / "positions.jsonl")
        if entry.get("record_index_start") != expected_record_start:
            raise ExportError("journal record ranges contain a gap or overlap")
        game_count = entry.get("game_count")
        if not isinstance(game_count, int) or game_count != len(games) or game_count < 1:
            raise ExportError("journal game count does not match the committed batch")
        if entry.get("record_index_end_exclusive") != expected_record_start + game_count:
            raise ExportError("journal record range does not match its game count")
        position_count = entry.get("position_count")
        if not isinstance(position_count, int) or position_count != len(positions):
            raise ExportError("journal position count does not match the committed batch")
        source_ordinals = [game.get("source_ordinal") for game in games]
        if any(not isinstance(value, int) or value < 1 for value in source_ordinals):
            raise ExportError("journal batch contains an invalid source ordinal")
        if entry.get("source_ordinal_min") != min(source_ordinals) or entry.get("source_ordinal_max") != max(source_ordinals):
            raise ExportError("journal source ordinal range differs from committed game rows")
        if min(source_ordinals) <= prior_source_ordinal_max:
            raise ExportError("journal source ordinal ranges overlap or are out of order")
        expected_record_start += game_count
        prior_source_ordinal_max = max(source_ordinals)
        game_ids = {game["game_id"] for game in games}
        sample_ids = {row["sample_id"] for row in positions}
        if len(game_ids) != len(games) or len(sample_ids) != len(positions):
            raise ExportError(f"duplicate IDs in batch {index}")
        if seen_games & game_ids or seen_samples & sample_ids:
            raise ExportError("overlapping game/sample IDs across batch segments")
        seen_games.update(game_ids)
        seen_samples.update(sample_ids)
        if any(row.get("game_id") not in seen_games for row in positions):
            raise ExportError("journal position references a game outside committed segments")
        if entry.get("game_ids") != sorted(game_ids) or entry.get("sample_ids") != sorted(sample_ids):
            raise ExportError(f"journal ID set mismatch in batch {index}")
    unjournaled = [path for path in run_dir.glob(".batch-*.partial")]
    if unjournaled:
        raise ExportError("agent-owned partial batch files need inspection; run was preserved")
    return entries


def write_batches(
    run_dir: Path, games: list[dict[str, Any]], positions: list[dict[str, Any]], *,
    input_identity: dict[str, Any], batch_size: int = 100, resume: bool = False,
) -> None:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    run_dir.mkdir(parents=True, exist_ok=True)
    run_manifest = run_dir / "run.json"
    identity_bytes = json.dumps(input_identity, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    if run_manifest.exists():
        existing = json.loads(run_manifest.read_text(encoding="utf-8"))
        if existing != input_identity:
            raise ExportError("resume refused because source/config/code identity changed")
        if not resume and (
            (run_dir / "journal.jsonl").exists()
            or any(path.is_dir() for path in run_dir.glob("batch-*"))
        ):
            raise ExportError("staging segments exist; pass --resume to validate and continue")
    else:
        if resume:
            raise ExportError("cannot resume: no staging run manifest exists")
        _write_new(run_manifest, identity_bytes)
    prior = _verify_batches(run_dir, input_identity) if resume else []
    if not resume and (run_dir / "journal.jsonl").exists():
        raise ExportError("new run unexpectedly has an existing journal")
    position_by_game: dict[str, list[dict[str, Any]]] = {}
    for row in positions:
        position_by_game.setdefault(row["game_id"], []).append(row)
    ordered_games = sorted(games, key=lambda row: (row["source_ordinal"], row["game_id"]))
    existing_indices = len(prior)
    total_batches = (len(ordered_games) + batch_size - 1) // batch_size
    seen_expected_games: set[str] = set()
    seen_expected_samples: set[str] = set()
    for batch_index in range(total_batches):
        batch_games = ordered_games[batch_index * batch_size:(batch_index + 1) * batch_size]
        ids = {game["game_id"] for game in batch_games}
        batch_positions = sorted(
            (row for game_id in ids for row in position_by_game.get(game_id, [])),
            key=lambda row: row["sample_id"],
        )
        game_ids = sorted(ids)
        sample_ids = sorted(row["sample_id"] for row in batch_positions)
        if seen_expected_games & ids or seen_expected_samples & set(sample_ids):
            raise ExportError("duplicate IDs generated across deterministic batches")
        seen_expected_games.update(ids)
        seen_expected_samples.update(sample_ids)
        directory = run_dir / f"batch-{batch_index:06d}"
        game_bytes = b"".join(json_line(row) for row in batch_games)
        position_bytes = b"".join(json_line(row) for row in batch_positions)
        if batch_index < existing_indices:
            entry = prior[batch_index]
            if entry.get("game_ids") != game_ids or entry.get("sample_ids") != sample_ids:
                raise ExportError("resume output identities differ from journal")
            if hashlib.sha256(game_bytes).hexdigest() != entry.get("games_sha256"):
                raise ExportError("resume game rows differ from committed segment")
            if hashlib.sha256(position_bytes).hexdigest() != entry.get("positions_sha256"):
                raise ExportError("resume position rows differ from committed segment")
            continue
        if directory.exists():
            raise ExportError("unjournaled batch directory exists; preserve and inspect it")
        temp = run_dir / f".batch-{batch_index:06d}.partial"
        temp.mkdir()
        _write_new(temp / "games.jsonl", game_bytes)
        _write_new(temp / "positions.jsonl", position_bytes)
        os.rename(temp, directory)
        entry = {
            "batch_index": batch_index,
            "input_identity": input_identity,
            "record_index_start": batch_index * batch_size,
            "record_index_end_exclusive": batch_index * batch_size + len(batch_games),
            "source_ordinal_min": min(game["source_ordinal"] for game in batch_games),
            "source_ordinal_max": max(game["source_ordinal"] for game in batch_games),
            "game_ids": game_ids, "sample_ids": sample_ids,
            "game_count": len(batch_games), "position_count": len(batch_positions),
            "games_bytes": len(game_bytes), "games_sha256": hashlib.sha256(game_bytes).hexdigest(),
            "positions_bytes": len(position_bytes), "positions_sha256": hashlib.sha256(position_bytes).hexdigest(),
        }
        _append_journal(run_dir / "journal.jsonl", entry)
    if len(prior) > total_batches:
        raise ExportError("journal has segments beyond the regenerated dataset")


def write_release_files(
    release_staging: Path, run_dir: Path, positions: list[dict[str, Any]],
    split_manifest: dict[str, Any], stats: dict[str, Any], source_manifest: dict[str, Any],
    config: dict[str, Any], *, max_output_bytes: int,
    allow_synthetic_source_for_test: bool = False,
) -> dict[str, Any]:
    if release_staging.exists():
        raise ExportError(f"release staging path exists; preserve and inspect: {release_staging}")
    release_staging.mkdir(parents=True)
    games_dir = sorted(path for path in run_dir.glob("batch-*") if path.is_dir())
    game_rows = []
    for directory in games_dir:
        game_rows.extend(_load_jsonl(directory / "games.jsonl"))
    game_rows.sort(key=lambda row: row["game_id"])
    split_rows = sorted(positions, key=lambda row: row["sample_id"])
    # The purge ledger lives in split.json. Dataset positions contain only retained rows.
    outputs: dict[str, tuple[int, str]] = {}
    budget = max_output_bytes
    for name, rows in (("games.jsonl", game_rows), ("positions.jsonl", split_rows)):
        _, size, digest = _write_jsonl_new(release_staging / name, rows, budget)
        outputs[name] = (size, digest)
        budget -= size
        if budget < 0:
            raise ExportError("release outputs exceed max_output_bytes")
    rejection_source = run_dir / "parse-rejections.jsonl"
    if not rejection_source.is_file():
        raise ExportError("parse-rejection ledger is missing from the completed scan")
    rejection_size, rejection_sha = _copy_file_new(
        release_staging / "rejections.jsonl", rejection_source, budget,
    )
    outputs["rejections.jsonl"] = (rejection_size, rejection_sha)
    budget -= rejection_size
    metadata = {
        "source_manifest.json": source_manifest,
        "config.json": config,
        "split.json": split_manifest,
        "stats.json": stats,
    }
    for name, value in metadata.items():
        data = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
        if len(data) > budget:
            raise ExportError("release metadata exceeds max_output_bytes")
        _write_new(release_staging / name, data)
        outputs[name] = (len(data), hashlib.sha256(data).hexdigest())
        budget -= len(data)
    output_rows = [[name, size, digest] for name, (size, digest) in outputs.items()]
    release_id = release_identity(
        source_manifest["archive_sha256"],
        [GAME_SCHEMA, POSITION_SCHEMA, SPLIT_SCHEMA],
        config["config_sha256"], config["code_revision"],
        split_manifest["split_assignment_sha256"], output_rows,
    )
    manifest = {
        "schema": "videochess-release/1.0",
        "release_id": release_id,
        "source_archive_sha256": source_manifest["archive_sha256"],
        "source_member_sha256": source_manifest["member_sha256"],
        "source_decision_id": source_manifest["source_decision_id"],
        "authorization_id": source_manifest["authorization_id"],
        "schema_versions": [GAME_SCHEMA, POSITION_SCHEMA, SPLIT_SCHEMA],
        "config_sha256": config["config_sha256"],
        "code_revision": config["code_revision"],
        "dirty_code_tree": config["dirty_code_tree"],
        "code_tree_sha256": config["code_tree_sha256"],
        "split_assignment_sha256": split_manifest["split_assignment_sha256"],
        "outputs": [
            {"path": name, "bytes": size, "sha256": digest}
            for name, (size, digest) in sorted(outputs.items())
        ],
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    _write_new(release_staging / "manifest.json", manifest_bytes)
    _write_new(
        release_staging / "manifest.sha256",
        (hashlib.sha256(manifest_bytes).hexdigest() + "  manifest.json\n").encode("ascii"),
    )
    # Internal batch directories are not part of the user-facing release. They
    # remain in run_dir for recovery and audit.
    verify_release(release_staging, allow_synthetic_source_for_test=allow_synthetic_source_for_test)
    return manifest


def verify_release(
    release_dir: Path, *, allow_synthetic_source_for_test: bool = False,
) -> dict[str, Any]:
    manifest_path = release_dir / "manifest.json"
    if not manifest_path.is_file():
        raise ExportError("release manifest is missing")
    manifest_bytes = manifest_path.read_bytes()
    expected_manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    hash_line = (release_dir / "manifest.sha256").read_text(encoding="ascii").strip().split()
    if not hash_line or hash_line[0] != expected_manifest_hash:
        raise ExportError("manifest checksum mismatch")
    manifest = json.loads(manifest_bytes)
    if manifest.get("schema") != "videochess-release/1.0":
        raise ExportError("unsupported release manifest schema")
    output_paths: set[str] = set()
    for output in manifest["outputs"]:
        name = output.get("path")
        if not isinstance(name, str) or Path(name).name != name or name in output_paths:
            raise ExportError("release output path is unsafe or duplicated")
        output_paths.add(name)
        path = release_dir / name
        if path.is_symlink() or not path.is_file():
            raise ExportError(f"release output is missing or is a symlink: {name}")
        digest, size = sha256_file(path)
        if digest != output["sha256"] or size != output["bytes"]:
            raise ExportError(f"release output hash/size mismatch: {name}")
    required_outputs = {
        "games.jsonl", "positions.jsonl", "rejections.jsonl", "source_manifest.json",
        "config.json", "split.json", "stats.json",
    }
    if output_paths != required_outputs:
        raise ExportError("release output manifest does not list the required dataset layers")
    source_doc = json.loads((release_dir / "source_manifest.json").read_text(encoding="utf-8"))
    if source_doc.get("test_fixture") is True:
        if not allow_synthetic_source_for_test:
            raise ExportError("synthetic source fixture is not a production release")
    else:
        try:
            validate_source_manifest(source_doc)
        except ValueError as exc:
            raise ExportError(f"release source manifest is invalid: {exc}") from exc
    if source_doc.get("archive_sha256") != manifest.get("source_archive_sha256"):
        raise ExportError("release and source manifest archive identities disagree")
    if source_doc.get("member_sha256") != manifest.get("source_member_sha256"):
        raise ExportError("release and source manifest member identities disagree")
    config_doc = json.loads((release_dir / "config.json").read_text(encoding="utf-8"))
    config_hash = config_doc.get("config_sha256")
    config_payload = dict(config_doc)
    config_payload.pop("config_sha256", None)
    if not config_hash or config_identity(config_payload) != config_hash:
        raise ExportError("release config identity does not recompute")
    if config_hash != manifest.get("config_sha256"):
        raise ExportError("release config hash differs from release manifest")
    if config_doc.get("source_archive_sha256") != manifest.get("source_archive_sha256") or config_doc.get("source_member_sha256") != manifest.get("source_member_sha256"):
        raise ExportError("release config source identities differ from release manifest")
    if config_doc.get("source_id") != source_doc.get("source_id"):
        raise ExportError("release config source_id differs from source manifest")
    if config_doc.get("code_revision") != manifest.get("code_revision") or config_doc.get("code_tree_sha256") != manifest.get("code_tree_sha256"):
        raise ExportError("release code identity differs from release manifest")
    games = _load_jsonl(release_dir / "games.jsonl")
    positions = _load_jsonl(release_dir / "positions.jsonl")
    games_by_id = {row["game_id"]: row for row in games}
    if len(games_by_id) != len(games):
        raise ExportError("duplicate game_id in release")
    if len({row["sample_id"] for row in positions}) != len(positions):
        raise ExportError("duplicate sample_id in release")
    seen_board_splits: dict[str, set[str]] = {}
    for game in games:
        validate_game_record(game)
        if game["source_archive_sha256"] != source_doc.get("archive_sha256") or game["source_member_name"] != source_doc.get("member_name"):
            raise ExportError("game provenance differs from release source manifest")
    for row in positions:
        game = games_by_id.get(row.get("game_id"))
        if game is None:
            raise ExportError(f"dangling game_id in position {row.get('sample_id')}")
        validate_position_record(row, game)
        seen_board_splits.setdefault(row["board_position_signature"], set()).add(row["split"])
    if any(len(splits) > 1 for splits in seen_board_splits.values()):
        raise ExportError("cross-split board-position overlap remains in release")
    split_doc = json.loads((release_dir / "split.json").read_text(encoding="utf-8"))
    if split_doc.get("schema") not in {LEGACY_SPLIT_SCHEMA, SPLIT_SCHEMA}:
        raise ExportError("unsupported split manifest schema")
    if split_doc.get("schema") not in manifest.get("schema_versions", []):
        raise ExportError("release schema-version list does not include its split manifest version")
    stats_doc = json.loads((release_dir / "stats.json").read_text(encoding="utf-8"))
    quality_version = stats_doc.get("quality_report_version", 1)
    if not isinstance(quality_version, int) or isinstance(quality_version, bool) or quality_version < 1:
        raise ExportError("quality report version is malformed")
    if quality_version >= 2 and (
        split_doc.get("schema") != SPLIT_SCHEMA
        or stats_doc.get("schema") != STATS_SCHEMA
        or SPLIT_SCHEMA not in manifest.get("schema_versions", [])
    ):
        raise ExportError("quality report v2 requires the versioned split/statistics schema extensions")
    if quality_version < 2 and split_doc.get("schema") == SPLIT_SCHEMA:
        raise ExportError("split schema 1.1 requires quality report v2")
    configured_minimum = config_doc.get("min_holdout_positions")
    if (isinstance(configured_minimum, bool) or not isinstance(configured_minimum, int)
            or configured_minimum < 1):
        raise ExportError("release config holdout position minimum is malformed")
    if split_doc.get("holdout_minimum") != configured_minimum:
        raise ExportError("split holdout count minimum differs from the immutable release config")
    retention_basis_points = config_doc.get("min_holdout_retention_basis_points", 5000)
    if (isinstance(retention_basis_points, bool)
            or not isinstance(retention_basis_points, int)
            or not int(MIN_HOLDOUT_RETENTION * 10_000) <= retention_basis_points <= 10_000):
        raise ExportError(
            "release config holdout retention must be an integer from 5000 through 10000 basis points"
        )
    configured_retention = retention_basis_points / 10_000
    if split_doc.get("holdout_minimum_retention") != configured_retention:
        raise ExportError("split holdout retention minimum differs from the immutable release config")
    split_minimum = split_doc.get("holdout_minimum")
    if isinstance(split_minimum, bool) or not isinstance(split_minimum, int) or split_minimum < 1:
        raise ExportError("split holdout position minimum is malformed")
    assignments = dict(split_doc.get("game_group_assignments", []))
    for row in positions:
        if assignments.get(row["normalized_game_sha256"]) != row["split"]:
            raise ExportError("position split does not inherit its normalized game assignment")
    if not split_doc.get("release_valid"):
        raise ExportError("split manifest marks release invalid")
    if len(assignments) != len(split_doc.get("game_group_assignments", [])):
        raise ExportError("duplicate normalized-game assignments in split manifest")
    if set(assignments) != {game["normalized_game_sha256"] for game in games}:
        raise ExportError("split manifest game groups do not cover the release games exactly")
    expected_game_counts = {
        name: sum(split == name for split in assignments.values())
        for name in ("train", "validation", "test")
    }
    if split_doc.get("game_counts") != expected_game_counts:
        raise ExportError("split manifest game counts do not match game-group assignments")
    if any(game.get("split") != assignments.get(game["normalized_game_sha256"]) for game in games):
        raise ExportError("game split does not inherit its normalized-game assignment")
    retained_ids = {row["sample_id"] for row in positions}
    purged = split_doc.get("purged_samples", [])
    purged_ids = [row.get("sample_id") for row in purged]
    if len(set(purged_ids)) != len(purged_ids) or retained_ids.intersection(purged_ids):
        raise ExportError("purge ledger contains duplicate or retained sample IDs")
    owner_map = dict(split_doc.get("board_signature_owners", []))
    if len(owner_map) != len(split_doc.get("board_signature_owners", [])):
        raise ExportError("duplicate board signature owners")
    prior_rows: list[dict[str, Any]] = []
    for row in positions:
        prior_rows.append({
            "sample_id": row["sample_id"], "game_id": row["game_id"],
            "board_position_signature": row["board_position_signature"],
            "history_state_id": row["history_state_id"], "split": row["split"],
            "side_to_move": row["side_to_move"], "white_result": row["white_result"],
            "pgn_result": row["pgn_result"], "side_to_move_result": row["side_to_move_result"],
            "ply_index": row["ply_index"], "candidate_count": row["candidate_count"],
        })
    for row in purged:
        required = {
            "sample_id", "game_id", "board_position_signature", "history_state_id",
            "original_split", "owner_split", "side_to_move", "white_result", "ply_index", "candidate_count",
            "played_move_uci",
        }
        if quality_version >= 2:
            required.update({"pgn_result", "side_to_move_result"})
        if not required.issubset(row):
            raise ExportError("purge ledger row misses fields required for independent auditing")
        game = games_by_id.get(row["game_id"])
        if game is None:
            raise ExportError("purged row references a missing game")
        board = reconstruct_position(game, row["ply_index"])
        expected_white = {"1-0": "win", "0-1": "loss", "1/2-1/2": "draw"}[game["pgn_result"]]
        expected_to_move = expected_white if board.turn else {"win": "loss", "loss": "win", "draw": "draw"}[expected_white]
        if quality_version >= 2 and (
            row["pgn_result"] != game["pgn_result"]
            or row["white_result"] != expected_white
            or row["side_to_move_result"] != expected_to_move
        ):
            raise ExportError("purge ledger game-result perspectives do not match the reconstructed parent state")
        prior_rows.append({
            "sample_id": row["sample_id"], "game_id": row["game_id"],
            "board_position_signature": row["board_position_signature"],
            "history_state_id": row["history_state_id"], "split": row["original_split"],
            "side_to_move": row["side_to_move"], "white_result": row["white_result"],
            "pgn_result": row.get("pgn_result", game["pgn_result"]),
            "side_to_move_result": row.get("side_to_move_result", expected_to_move),
            "ply_index": row["ply_index"], "candidate_count": row["candidate_count"],
        })
        if assignments.get(game["normalized_game_sha256"]) != row["original_split"]:
            raise ExportError("purged row does not trace to a game in its original assigned split")
        board = reconstruct_position(game, row["ply_index"])
        legal = {move.uci() for move in board.legal_moves}
        if row["played_move_uci"] not in legal or row["candidate_count"] != len(legal):
            raise ExportError("purged candidate metadata does not reconstruct from its parent game")
        if row["side_to_move"] != ("white" if board.turn else "black"):
            raise ExportError("purged side-to-move metadata does not reconstruct")
        if row["board_position_signature"] != board_position_signature(board):
            raise ExportError("purged board signature does not reconstruct")
        expected_history = replay_history_identity(game["initial_fen"], game["moves_uci"][:row["ply_index"]])
        if row["history_state_id"] != expected_history:
            raise ExportError("purged replay-history identity does not reconstruct")
        expected_sample = sample_identity(
            game["source_id"], game["game_id"], game["normalized_game_sha256"], row["ply_index"],
        )
        if row["sample_id"] != expected_sample:
            raise ExportError("purged sample identity does not reconstruct")
        if row["owner_split"] != owner_map.get(row["board_position_signature"]):
            raise ExportError("purged row owner differs from split manifest")
    if len({row["sample_id"] for row in prior_rows}) != len(prior_rows):
        raise ExportError("pre-purge sample identities are not unique")
    prior_board_splits: dict[str, set[str]] = {}
    for row in prior_rows:
        prior_board_splits.setdefault(row["board_position_signature"], set()).add(row["split"])
    expected_owners = {
        signature: board_signature_owner(split_doc["split_seed"], signature, splits)
        for signature, splits in prior_board_splits.items()
    }
    if expected_owners != owner_map:
        raise ExportError("board signature owner assignment does not recompute")
    cross_split_before = sum(len(splits) > 1 for splits in prior_board_splits.values())
    if split_doc.get("board_signatures_cross_split_before") != cross_split_before:
        raise ExportError("pre-purge cross-split board overlap count does not recompute")
    if split_doc.get("board_signatures_before") != len(prior_board_splits):
        raise ExportError("pre-purge board signature count does not recompute")
    for row in positions:
        if row["split"] != owner_map.get(row["board_position_signature"]):
            raise ExportError("retained row is not in its board-signature owner split")
    before_counts = {
        name: sum(row["split"] == name for row in prior_rows)
        for name in ("train", "validation", "test")
    }
    after_counts = {
        name: sum(row["split"] == name for row in positions)
        for name in ("train", "validation", "test")
    }
    if split_doc.get("position_counts_before_purge") != before_counts:
        raise ExportError("pre-purge position counts do not match retained rows and purge ledger")
    if split_doc.get("position_counts_after_purge") != after_counts:
        raise ExportError("position counts do not match split manifest")
    retention = {
        name: (after_counts[name] / before_counts[name] if before_counts[name] else 0.0)
        for name in ("train", "validation", "test")
    }
    if split_doc.get("position_retention") != retention:
        raise ExportError("position retention does not recompute")
    min_holdout = split_minimum
    min_retention = split_doc.get("holdout_minimum_retention")
    if (isinstance(min_retention, bool) or not isinstance(min_retention, (int, float))
            or not MIN_HOLDOUT_RETENTION <= min_retention <= 1.0):
        raise ExportError("split holdout retention minimum is below the mandatory 50% policy or malformed")
    warning_retention = split_doc.get("holdout_warning_retention", 0.8)
    if (isinstance(warning_retention, bool) or not isinstance(warning_retention, (int, float))
            or not 0 <= warning_retention <= 1):
        raise ExportError("holdout warning retention threshold is malformed")
    if quality_version >= 2 and warning_retention != 0.8:
        raise ExportError("quality report v2 requires the documented 80% holdout warning threshold")
    expected_warnings = [
        f"{name} holdout retention is below the 80% warning threshold ({retention[name]:.4f})"
        for name in ("validation", "test") if retention[name] < warning_retention
    ]
    if ((quality_version >= 2 and "holdout_warnings" not in split_doc)
            or ("holdout_warnings" in split_doc and split_doc.get("holdout_warnings") != expected_warnings)):
        raise ExportError("holdout retention warnings do not match the measured retention")
    for name in ("validation", "test"):
        if after_counts[name] < min_holdout or retention[name] < MIN_HOLDOUT_RETENTION:
            raise ExportError(
                f"{name} holdout fails the mandatory minimum position/50% retention gate"
            )
        if retention[name] < min_retention:
            raise ExportError(f"{name} holdout fails the recorded minimum/retention gate")
    expected_holdout_failures = [
        f"{name} holdout has {after_counts[name]} retained positions (minimum {min_holdout})"
        for name in ("validation", "test") if after_counts[name] < min_holdout
    ] + [
        f"{name} retention {retention[name]:.4f} is below {min_retention:.4f}"
        for name in ("validation", "test") if retention[name] < min_retention
    ]
    if split_doc.get("holdout_failures") != expected_holdout_failures:
        raise ExportError("holdout failure summary does not recompute")
    if split_doc.get("purged_position_count") != len(purged):
        raise ExportError("purged position count does not match the audit ledger")
    if split_doc.get("purged_candidate_count") != sum(row["candidate_count"] for row in purged):
        raise ExportError("purged candidate count does not match the audit ledger")
    if split_doc.get("distinct_history_states_before") != len({row["history_state_id"] for row in prior_rows}):
        raise ExportError("pre-purge replay-state count does not match the audit ledger")
    if split_doc.get("distinct_history_states_after") != len({row["history_state_id"] for row in positions}):
        raise ExportError("post-purge replay-state count does not match retained positions")
    if split_doc.get("board_signatures_after") != len({row["board_position_signature"] for row in positions}):
        raise ExportError("post-purge board signature count does not match retained positions")
    assignment_hash = split_manifest_identity(
        split_doc["split_seed"], split_doc["game_group_assignments"],
        split_doc["board_signature_owners"],
        [[row["sample_id"], row["original_split"], row["owner_split"]] for row in purged],
    )
    if assignment_hash != split_doc.get("split_assignment_sha256") or assignment_hash != manifest.get("split_assignment_sha256"):
        raise ExportError("split assignment identity does not recompute")
    if stats_doc.get("source", {}).get("source_id") != source_doc.get("source_id"):
        raise ExportError("dataset statistics source identity differs from source manifest")
    if stats_doc.get("selected_games") != len(games):
        raise ExportError("dataset statistics game count does not match release")
    if stats_doc.get("positions_selected_before_purge") != len(prior_rows) or stats_doc.get("positions_retained_after_purge") != len(positions):
        raise ExportError("dataset statistics position counts do not match release")
    if stats_doc.get("splits") != split_doc:
        raise ExportError("dataset statistics split summary differs from the split manifest")
    if stats_doc.get("quality_report_version", 1) >= 2:
        try:
            recomputed_stats = summarize_dataset(
                games, prior_rows, positions, split_doc, stats_doc["scan"],
                sampling=stats_doc["sampling"],
                resources=stats_doc["resource_measurements"],
                config_sha256=config_hash, source_manifest=source_doc,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ExportError(f"dataset statistics cannot be recomputed from release rows: {exc}") from exc
        expected_before = recomputed_stats["position_quality_before_purge"]
        expected_after = recomputed_stats["position_quality_after_purge"]
        if stats_doc.get("position_quality_before_purge") != expected_before:
            raise ExportError("pre-purge quality distributions do not reconcile with release rows")
        if stats_doc.get("position_quality_after_purge") != expected_after:
            raise ExportError("post-purge quality distributions do not reconcile with release rows")
        if stats_doc.get("distribution_shift_after_purge_fraction") != quality_distribution_shifts(expected_before, expected_after):
            raise ExportError("reported quality distribution shifts do not reconcile with pre/post-purge rows")
        candidate_counts = [row["candidate_count"] for row in prior_rows]
        expected_candidate_histogram: dict[str, int] = {}
        for candidate_count in candidate_counts:
            key = str(candidate_count)
            expected_candidate_histogram[key] = expected_candidate_histogram.get(key, 0) + 1
        expected_candidate_histogram = dict(sorted(expected_candidate_histogram.items(), key=lambda item: int(item[0])))
        if (stats_doc.get("legal_candidates", {}).get("total") != sum(candidate_counts)
                or stats_doc.get("legal_candidates", {}).get("histogram") != expected_candidate_histogram):
            raise ExportError("legal candidate statistics do not reconcile with pre-purge position rows")
        expected_missing = {
            "white_elo": sum(game.get("white_elo") is None for game in games),
            "black_elo": sum(game.get("black_elo") is None for game in games),
            "time_control": sum(not game.get("time_control") for game in games),
            "date": sum(not game.get("date") for game in games),
        }
        if stats_doc.get("missing_metadata") != expected_missing:
            raise ExportError("missing metadata counts do not reconcile with released game records")
        expected_time_controls: dict[str, int] = {}
        for game in games:
            key = str(game.get("time_control") or "missing")
            expected_time_controls[key] = expected_time_controls.get(key, 0) + 1
        if stats_doc.get("time_control_distribution") != dict(sorted(expected_time_controls.items())):
            raise ExportError("time-control statistics do not reconcile with released game records")
        expected_rating_metadata = {
            "one_or_more_missing": sum(game.get("white_elo") is None or game.get("black_elo") is None for game in games),
            "both_present": sum(game.get("white_elo") is not None and game.get("black_elo") is not None for game in games),
        }
        if stats_doc.get("rating_metadata") != expected_rating_metadata:
            raise ExportError("rating metadata availability counts do not reconcile with game records")
        expected_headers: dict[str, int] = {}
        for game in games:
            for key in game.get("header_keys", []):
                expected_headers[key] = expected_headers.get(key, 0) + 1
        if stats_doc.get("header_key_frequency") != dict(sorted(expected_headers.items())):
            raise ExportError("PGN header-key frequency does not reconcile with game records")
        clock_report = stats_doc.get("clock_information", {})
        if clock_report.get("status") != "unavailable" or not clock_report.get("reason"):
            raise ExportError("unavailable clock metadata must be explicitly reported")
        if stats_doc != recomputed_stats:
            differing = sorted(
                key for key in set(stats_doc) | set(recomputed_stats)
                if stats_doc.get(key) != recomputed_stats.get(key)
            )
            raise ExportError(
                "dataset statistics do not recompute from release rows, config, and source manifest: "
                + ", ".join(differing[:12])
            )
    rejection_counts: dict[str, dict[str, int]] = {"rejected": {}, "quarantined": {}}
    prior_rejection_ordinal = 0
    rejection_total = 0
    for row in _iter_jsonl(release_dir / "rejections.jsonl"):
        if row.get("status") not in rejection_counts or not isinstance(row.get("reason_code"), str):
            raise ExportError("parse-rejection ledger contains an invalid status or reason code")
        ordinal = row.get("source_ordinal")
        if not isinstance(ordinal, int) or ordinal <= prior_rejection_ordinal:
            raise ExportError("parse-rejection source ordinals are not strictly increasing")
        prior_rejection_ordinal = ordinal
        status_counts = rejection_counts[row["status"]]
        status_counts[row["reason_code"]] = status_counts.get(row["reason_code"], 0) + 1
        rejection_total += 1
    scan = stats_doc.get("scan", {})
    if rejection_counts["rejected"] != scan.get("rejection_reasons", {}) or rejection_counts["quarantined"] != scan.get("quarantine_reasons", {}):
        raise ExportError("parse-rejection ledger reason counts differ from scan statistics")
    if rejection_total != scan.get("parse_rejection_records"):
        raise ExportError("parse-rejection ledger row count differs from scan statistics")
    if scan.get("games_seen") != scan.get("games_accepted_before_dedup", 0) + rejection_total:
        raise ExportError("scan game totals do not reconcile with accepted and rejected records")
    if scan.get("games_rejected") != sum(rejection_counts["rejected"].values()):
        raise ExportError("scan rejected-game count does not reconcile with the rejection ledger")
    if scan.get("games_quarantined") != sum(rejection_counts["quarantined"].values()):
        raise ExportError("scan quarantined-game count does not reconcile with the rejection ledger")
    if quality_version >= 2:
        source_conflicts = scan.get("conflicting_source_reference_sha256")
        normalized_conflicts = scan.get("conflicting_normalized_game_sha256")
        if (not isinstance(source_conflicts, list) or source_conflicts != sorted(set(source_conflicts))
                or scan.get("conflicting_source_reference_count") != len(source_conflicts)):
            raise ExportError("source-reference conflict identities/count do not reconcile")
        if (not isinstance(normalized_conflicts, list) or normalized_conflicts != sorted(set(normalized_conflicts))
                or scan.get("conflicting_normalized_groups") != len(normalized_conflicts)):
            raise ExportError("normalized-game conflict identities/count do not reconcile")
        for conflict_id in source_conflicts + normalized_conflicts:
            if (not isinstance(conflict_id, str) or len(conflict_id) != 64
                    or any(char not in "0123456789abcdef" for char in conflict_id)):
                raise ExportError("conflict audit contains a malformed SHA-256 identity")
        accepted_observations = scan.get("games_accepted_before_dedup")
        duplicate_observations = scan.get("normalized_duplicate_observations")
        audited_groups = scan.get("full_source_audit_groups")
        if (not isinstance(accepted_observations, int) or not isinstance(duplicate_observations, int)
                or not isinstance(audited_groups, int)
                or accepted_observations - duplicate_observations != audited_groups):
            raise ExportError("full-source normalized-game observation totals do not reconcile")
        if (not isinstance(scan.get("normalized_duplicate_groups"), int)
                or not 0 <= scan["normalized_duplicate_groups"] <= duplicate_observations):
            raise ExportError("normalized-game duplicate group count is inconsistent")
        if scan.get("games_accepted_selected") != len(games):
            raise ExportError("selected-game count does not reconcile with scan statistics")
        if scan.get("input_scan_complete") != (config_doc.get("sampling_mode") == "bottom_k"):
            raise ExportError("source-scan completeness does not match the configured sampling mode")
    output_rows = [
        [item["path"], item["bytes"], item["sha256"]]
        for item in manifest["outputs"]
    ]
    expected_release_id = release_identity(
        manifest["source_archive_sha256"], manifest["schema_versions"],
        manifest["config_sha256"], manifest["code_revision"],
        manifest["split_assignment_sha256"], output_rows,
    )
    if manifest.get("release_id") != expected_release_id:
        raise ExportError("release identity does not recompute")
    expected_paths = {item["path"] for item in manifest["outputs"]} | {"manifest.json", "manifest.sha256"}
    actual_paths = {path.name for path in release_dir.iterdir() if path.is_file()}
    if actual_paths != expected_paths:
        raise ExportError("release contains missing or unlisted output files")
    return {
        "release_id": manifest["release_id"],
        "games": len(games), "positions": len(positions),
        "rejections": rejection_total,
        "output_bytes": sum(item["bytes"] for item in manifest["outputs"]),
        "manifest_sha256": expected_manifest_hash,
        "outputs_verified": len(manifest["outputs"]),
    }
