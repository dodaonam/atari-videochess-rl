"""Command-line interface for bounded M3 source, build, verification, and teacher runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import shutil
import stat
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import chess

from .contracts import source_identity
from .export import ExportError, verify_release
from .pipeline import PipelineError, build_dataset
from .source import (
    SourceError, download_archive, hash_member, inspect_zip, sha256_file,
    validate_source_manifest, write_json_atomic,
)
from .teacher import TeacherError, run_teacher, verify_teacher_run

ELITE_URL = "https://database.nikonoel.fr/lichess_elite_2022-05.zip"
SOURCE_DECISION_ID = "M3-SOURCE-ELITE-2022-05-LOCAL-20261020"
AUTHORIZATION_ID = "M3-001-owner-20261020"
LICENSE_STATUS = "third_party_license_unstated_internal_use_owner_authorized_no_redistribution"


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _json_print(value: Any) -> None:
    print(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False))


def _set_memory_limit(mib: int) -> None:
    if mib < 128:
        raise ValueError("memory cap must be at least 128 MiB")
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    limit = mib * 1024 * 1024
    if hard != resource.RLIM_INFINITY and hard < limit:
        limit = hard
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def _check_authorization_files(source_decision: Path, authorization: Path) -> None:
    if not source_decision.is_file() or not authorization.is_file():
        raise ValueError("required M3 source decision/authorization evidence is missing")
    if ELITE_URL not in source_decision.read_text(encoding="utf-8"):
        raise ValueError("source decision does not name the selected archive URL")
    auth_text = authorization.read_text(encoding="utf-8")
    if "directly authorized M3-001" not in auth_text:
        raise ValueError("direct M3 authorization record is not valid")


def command_fetch(args: argparse.Namespace) -> None:
    if not args.confirm_write:
        raise ValueError("fetch requires --confirm-write")
    root = repository_root()
    decision = Path(args.source_decision)
    authorization = Path(args.authorization)
    if not decision.is_absolute():
        decision = root / decision
    if not authorization.is_absolute():
        authorization = root / authorization
    _check_authorization_files(decision, authorization)
    if args.url != ELITE_URL:
        raise ValueError("this authorized M3 fetch command accepts only the selected May 2022 source URL")
    archive_path = Path(args.archive)
    manifest_path = Path(args.manifest)
    if not archive_path.is_absolute():
        archive_path = root / archive_path
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    if manifest_path.exists():
        raise ValueError(f"refusing to overwrite source manifest: {manifest_path}")
    terms_path = root / ".agents/evidence/M3-source-terms-20261020.md"
    if not terms_path.is_file():
        raise ValueError("committed source terms evidence is missing")
    decision_hash, _ = sha256_file(decision)
    authorization_hash, _ = sha256_file(authorization)
    terms_hash, _ = sha256_file(terms_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    future_output_cap = args.max_future_output_bytes
    if future_output_cap < 1:
        raise ValueError("future output byte cap must be positive")
    disk_free = shutil.disk_usage(archive_path.parent).free
    projected_peak = int((args.max_archive_bytes + args.max_total_decompressed_bytes + 2 * future_output_cap) * 1.2)
    if disk_free < projected_peak:
        raise ValueError(f"insufficient free disk before download: need {projected_peak} bytes, have {disk_free}")
    downloaded = download_archive(
        args.url, archive_path, max_bytes=args.max_archive_bytes,
        timeout_seconds=args.timeout_seconds, retries=args.retries,
    )
    inspected = inspect_zip(
        archive_path, max_archive_bytes=args.max_archive_bytes,
        max_member_bytes=args.max_member_bytes,
        max_total_uncompressed_bytes=args.max_total_decompressed_bytes,
        max_members=args.max_members,
        max_compression_ratio=args.max_compression_ratio,
        expected_member=args.expected_member,
        expected_sha256=downloaded["archive_sha256"],
        expected_bytes=downloaded["archive_bytes"],
    )
    member_name = inspected["member"]["name"]
    member_sha, member_bytes = hash_member(
        archive_path, member_name,
        max_decompressed_bytes=args.max_total_decompressed_bytes,
    )
    if member_bytes != inspected["member"]["uncompressed_bytes"]:
        raise SourceError("decompressed member bytes differ from ZIP directory metadata")
    os.chmod(archive_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    try:
        archive_rel = archive_path.relative_to(root).as_posix()
    except ValueError:
        archive_rel = archive_path.name
    try:
        code_revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"cannot identify source acquisition revision: {exc}") from exc
    manifest = {
        "schema": "videochess-source-manifest/1.0",
        "schema_version": "videochess-source-manifest/1.0",
        "source_id": source_identity(
            "lichess-elite", "https://database.nikonoel.fr/", "lichess-elite-2022-05",
        ),
        "publisher": "Lichess Elite Database (third-party curated package)",
        "upstream_data_origin": "Lichess game data; official Lichess database exports state CC0 for official exports",
        "original_data_provenance": "Lichess games selected and repackaged by the third-party Lichess Elite Database publisher",
        "canonical_source_url": "https://database.nikonoel.fr/",
        "archive_url": args.url,
        "archive_filename": archive_path.name,
        "published_archive_checksum": None,
        "license_name": None,
        "license_url": None,
        "license_unknown_reason": "publisher page does not state a license for this filtered third-party package",
        "upstream_license_note": "CC0 is stated for official Lichess database exports only and is not attributed to this third-party package",
        "source_decision_id": SOURCE_DECISION_ID,
        "authorization_id": AUTHORIZATION_ID,
        "license_status": LICENSE_STATUS,
        "rights_boundary": "bounded internal academic research; local retention; no upload or redistribution of archive or bulk derived game records",
        "approval_id": AUTHORIZATION_ID,
        "retrieved_at_utc": downloaded["retrieved_at_utc"],
        "source_page_sha256": "b0bc850f67e5064e3ca9369b5ff0e91cdb0030a8af5f928e9aefa35a219ec88a",
        "rights_evidence_path": terms_path.relative_to(root).as_posix(),
        "rights_evidence_sha256": terms_hash,
        "source_terms_evidence": {
            "path": terms_path.relative_to(root).as_posix(), "sha256": terms_hash,
            "publisher_page_sha256": "b0bc850f67e5064e3ca9369b5ff0e91cdb0030a8af5f928e9aefa35a219ec88a",
            "upstream_terms_page_sha256": "2b1db536724631cd0a21e24bff3693b26037676e4f91489072f584be51e24b0d",
            "checked_at_utc": "2026-10-20T14:53:45Z",
        },
        "approval_evidence": {
            "source_decision_path": decision.relative_to(root).as_posix(),
            "source_decision_sha256": decision_hash,
            "authorization_path": authorization.relative_to(root).as_posix(),
            "authorization_sha256": authorization_hash,
        },
        "publisher_reported_games": 355535,
        "publisher_reported_compressed_size": "93 MB",
        "retrieval": downloaded,
        "archive_sha256": downloaded["archive_sha256"],
        "archive_bytes": downloaded["archive_bytes"],
        "archive_path": archive_rel,
        "member": inspected["member"],
        "member_name": member_name,
        "archive_member": inspected["member"],
        "member_crc": inspected["member"]["crc32"],
        "member_sha256": member_sha,
        "member_bytes": member_bytes,
        "declared_total_uncompressed_bytes": inspected["declared_total_uncompressed_bytes"],
        "compression_ratio": inspected["compression_ratio"],
        "zip_entry_count": inspected["zip_entry_count"],
        "crc_verified": True,
        "disk_preflight": {
            "free_bytes_before_download": disk_free,
            "projected_peak_bytes_with_20_percent_reserve": projected_peak,
            "future_output_cap_bytes": future_output_cap,
        },
        "retrieval_limits": {
            "max_archive_bytes": args.max_archive_bytes,
            "max_member_bytes": args.max_member_bytes,
            "max_total_decompressed_bytes": args.max_total_decompressed_bytes,
            "max_compression_ratio": args.max_compression_ratio,
        },
        "parser_name": "python-chess PGN reader",
        "python_version": sys.version.split()[0],
        "python_chess_version": chess.__version__,
        "filter_config_sha256": None,
        "filter_config_unknown_reason": "The third-party publisher does not publish its filter implementation/configuration; its page summary is captured in the terms evidence.",
        "code_revision": code_revision,
        "source_notes": "Publisher reports standard games, excludes bullet, and since December 2021 uses the 2500+ versus 2300+ filter; this is not independently verified for each record.",
    }
    validate_source_manifest(manifest)
    write_json_atomic(manifest_path, manifest)
    _json_print({
        "source_manifest_path": manifest_path.relative_to(root).as_posix() if manifest_path.is_relative_to(root) else manifest_path.name,
        "archive_path": archive_rel, "archive_bytes": downloaded["archive_bytes"],
        "archive_sha256": downloaded["archive_sha256"], "member": inspected["member"],
        "member_bytes": member_bytes, "member_sha256": member_sha,
        "crc_verified": True, "rights_status": LICENSE_STATUS,
    })


def command_build(args: argparse.Namespace) -> None:
    root = repository_root()
    config_path = Path(args.config)
    source_manifest = Path(args.source_manifest)
    archive = Path(args.archive)
    output = Path(args.output)
    decision = Path(args.source_decision)
    authorization = Path(args.authorization)
    values = (config_path, source_manifest, archive, output, decision, authorization)
    resolved = [path if path.is_absolute() else root / path for path in values]
    result = build_dataset(
        resolved[2], resolved[1], resolved[0], resolved[3], run_id=args.run_id,
        repository_root=root, source_decision_path=resolved[4],
        authorization_path=resolved[5], confirm_write=args.confirm_write,
        resume=args.resume,
    )
    _json_print(result)


def command_verify(args: argparse.Namespace) -> None:
    release = Path(args.release)
    if not release.is_absolute():
        release = repository_root() / release
    result = verify_release(release)
    if args.teacher_run:
        teacher_dir = Path(args.teacher_run)
        if not teacher_dir.is_absolute():
            teacher_dir = repository_root() / teacher_dir
        result["teacher"] = verify_teacher_run(teacher_dir, release)
    if args.source_manifest:
        manifest_path = Path(args.source_manifest)
        if not manifest_path.is_absolute():
            manifest_path = repository_root() / manifest_path
        source = json.loads(manifest_path.read_text(encoding="utf-8"))
        validate_source_manifest(source)
        for evidence in (
            source["source_terms_evidence"],
            {"path": source["approval_evidence"]["source_decision_path"], "sha256": source["approval_evidence"]["source_decision_sha256"]},
            {"path": source["approval_evidence"]["authorization_path"], "sha256": source["approval_evidence"]["authorization_sha256"]},
        ):
            relative = Path(evidence["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("source evidence path is unsafe")
            actual, _ = sha256_file(repository_root() / relative)
            if actual != evidence["sha256"]:
                raise ValueError(f"source evidence checksum mismatch: {evidence['path']}")
        archive = Path(args.archive or source["archive_path"])
        if not archive.is_absolute():
            archive = repository_root() / archive
        actual_sha, actual_bytes = sha256_file(archive, max_bytes=source["archive_bytes"])
        if actual_sha != source["archive_sha256"] or actual_bytes != source["archive_bytes"]:
            raise ValueError("source archive hash/size mismatch")
        limits = source["retrieval_limits"]
        checked_zip = inspect_zip(
            archive, max_archive_bytes=limits["max_archive_bytes"],
            max_member_bytes=limits["max_member_bytes"],
            max_total_uncompressed_bytes=limits["max_total_decompressed_bytes"],
            max_compression_ratio=limits["max_compression_ratio"],
            expected_member=source["member_name"],
            expected_sha256=source["archive_sha256"], expected_bytes=source["archive_bytes"],
        )
        if checked_zip["member"] != source["member"]:
            raise ValueError("source ZIP member metadata differs from the immutable manifest")
        member_sha, member_bytes = hash_member(
            archive, source["member_name"], max_decompressed_bytes=source["member_bytes"],
        )
        if member_sha != source["member_sha256"] or member_bytes != source["member_bytes"]:
            raise ValueError("source member hash/size mismatch")
        result["source_archive"] = {"sha256": actual_sha, "bytes": actual_bytes}
        result["source_member"] = {"sha256": member_sha, "bytes": member_bytes, "crc_verified": True}
    _json_print(result)


def command_teacher(args: argparse.Namespace) -> None:
    root = repository_root()
    release = Path(args.release)
    games = Path(args.games) if args.games else release / "games.jsonl"
    output = Path(args.output)
    engine = Path(args.engine)
    license_file = Path(args.license)
    for name, path in (("release", release), ("games", games), ("output", output), ("engine", engine), ("license", license_file)):
        if not path.is_absolute():
            if name == "engine" and not (root / path).exists():
                path = Path("/home/dodaonam/Projects/atari-videochess-rl") / path
            else:
                path = root / path
        if name == "release": release = path
        elif name == "games": games = path
        elif name == "output": output = path
        elif name == "engine": engine = path
        elif name == "license": license_file = path
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"cannot identify teacher code revision: {exc}") from exc
    result = run_teacher(
        release, games, output, engine_path=engine,
        expected_engine_sha256=args.engine_sha256,
        license_path=license_file, expected_license_sha256=args.license_sha256,
        max_positions=args.max_positions, sample_seed=args.seed,
        nodes_per_position=args.nodes, multipv=args.multipv,
        threads=args.threads, hash_mib=args.hash_mib,
        timeout_seconds=args.timeout_seconds, max_wall_seconds=args.max_wall_seconds,
        authorization_id=AUTHORIZATION_ID, source_decision_id=SOURCE_DECISION_ID,
        confirm_write=args.confirm_write, code_revision=revision,
        max_output_bytes=args.max_output_bytes,
    )
    _json_print(result)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="videochess-data")
    sub = result.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch", help="download only the owner-authorized source with hard caps")
    fetch.add_argument("--url", default=ELITE_URL)
    fetch.add_argument("--archive", required=True)
    fetch.add_argument("--manifest", required=True)
    fetch.add_argument("--source-decision", default=".agents/evidence/M3-source-decision-20261020.md")
    fetch.add_argument("--authorization", default=".agents/evidence/M3-authorization-20261020.md")
    fetch.add_argument("--max-archive-bytes", type=int, default=150 * 1024 * 1024)
    fetch.add_argument("--max-member-bytes", type=int, default=512 * 1024 * 1024)
    fetch.add_argument("--max-total-decompressed-bytes", type=int, default=512 * 1024 * 1024)
    fetch.add_argument("--max-compression-ratio", type=int, default=200)
    fetch.add_argument("--max-members", type=int, default=16)
    fetch.add_argument("--max-future-output-bytes", type=int, default=2 * 1024 * 1024 * 1024)
    fetch.add_argument("--expected-member")
    fetch.add_argument("--timeout-seconds", type=int, default=45)
    fetch.add_argument("--retries", type=int, default=2)
    fetch.add_argument("--confirm-write", action="store_true")
    fetch.set_defaults(func=command_fetch)

    build = sub.add_parser("build", help="build a bounded dataset release from an approved local source")
    build.add_argument("--archive", required=True)
    build.add_argument("--source-manifest", required=True)
    build.add_argument("--config", required=True)
    build.add_argument("--output", required=True)
    build.add_argument("--run-id", required=True)
    build.add_argument("--source-decision", default=".agents/evidence/M3-source-decision-20261020.md")
    build.add_argument("--authorization", default=".agents/evidence/M3-authorization-20261020.md")
    build.add_argument("--confirm-write", action="store_true")
    build.add_argument("--resume", action="store_true")
    build.set_defaults(func=command_build)

    verify = sub.add_parser("verify", help="validate release and optionally source hashes")
    verify.add_argument("--release", required=True)
    verify.add_argument("--source-manifest")
    verify.add_argument("--archive")
    verify.add_argument("--teacher-run")
    verify.set_defaults(func=command_verify)

    teacher = sub.add_parser("teacher", help="run capped Stockfish teacher labeling as a sidecar")
    teacher.add_argument("--release", required=True)
    teacher.add_argument("--games")
    teacher.add_argument("--output", required=True)
    teacher.add_argument("--engine", required=True)
    teacher.add_argument("--engine-sha256", required=True)
    teacher.add_argument("--license", required=True)
    teacher.add_argument("--license-sha256", required=True)
    teacher.add_argument("--max-positions", type=int, default=128)
    teacher.add_argument("--seed", type=int, default=20261020)
    teacher.add_argument("--nodes", type=int, default=5000)
    teacher.add_argument("--multipv", type=int, default=3)
    teacher.add_argument("--threads", type=int, default=1)
    teacher.add_argument("--hash-mib", type=int, default=64)
    teacher.add_argument("--timeout-seconds", type=float, default=30.0)
    teacher.add_argument("--max-wall-seconds", type=int, default=1800)
    teacher.add_argument("--max-output-bytes", type=int, default=64 * 1024 * 1024)
    teacher.add_argument("--confirm-write", action="store_true")
    teacher.set_defaults(func=command_teacher)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "build":
            config_path = Path(args.config)
            if not config_path.is_absolute():
                config_path = repository_root() / config_path
            import tomllib
            with config_path.open("rb") as stream:
                config = tomllib.load(stream).get("dataset", {})
            _set_memory_limit(config.get("memory_mib", 1024))
        elif args.command == "teacher":
            _set_memory_limit(args.memory_mib if hasattr(args, "memory_mib") else 1024)
        args.func(args)
        return 0
    except (ValueError, SourceError, PipelineError, ExportError, TeacherError, OSError, zipfile.BadZipFile) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
