#!/usr/bin/env python3
"""Migrate, verify, and recover the portable checkpoint-history archive."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from checkpoint_history import (
    CheckpointHistoryError,
    inspect_history_storage,
    migrate_legacy_history,
    migration_preview,
    recover_pending_append,
    restore_original_state_bytes,
    atomic_write_bytes,
)


def _load_state(root: Path) -> tuple[bytes, dict[str, object]]:
    raw = (root / ".agents/state/PROJECT_STATE.yaml").read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise CheckpointHistoryError("canonical state must be a JSON object")
    return raw, value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="repository root (default: current directory)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    migrate_parser = subparsers.add_parser("migrate", help="preview or apply the lossless inline-history migration")
    migrate_parser.add_argument("--apply", action="store_true", help="write and verify the archive and compact state")
    subparsers.add_parser("verify", help="verify inline or archived history and print its logical identity")
    subparsers.add_parser("recover-pending", help="roll forward one append proven by the current checkpoint")
    restore_parser = subparsers.add_parser("restore-original", help="write the byte-exact pre-migration state backup")
    restore_parser.add_argument("--output", type=Path, required=True, help="new output path; existing different files are never overwritten")
    args = parser.parse_args(argv)
    root = args.repo.resolve()

    try:
        raw, state = _load_state(root)
        if args.command == "migrate":
            if args.apply:
                result = migrate_legacy_history(root)
            elif "checkpoint_history_archive" in state:
                inspection = inspect_history_storage(root, state)
                result = {"status": "already_migrated", "record_count": len(inspection.records), "errors": inspection.errors}
                if inspection.errors:
                    raise CheckpointHistoryError("existing archive failed verification: " + "; ".join(f"{c}: {m}" for c, m in inspection.errors))
            else:
                result = migration_preview(raw, state)
                result["status"] = "dry_run_only"
                result["apply_command"] = "python3 scripts/migrate_checkpoint_history.py --repo . migrate --apply"
        elif args.command == "verify":
            inspection = inspect_history_storage(root, state)
            if inspection.errors:
                raise CheckpointHistoryError("; ".join(f"{code}: {message}" for code, message in inspection.errors))
            result = {
                "status": "verified",
                "storage": "archive" if "checkpoint_history_archive" in state else "legacy_inline",
                "record_count": len(inspection.records),
                "first_id": inspection.records[0]["id"] if inspection.records else None,
                "last_id": inspection.records[-1]["id"] if inspection.records else None,
                "logical_sha256": state.get("checkpoint_history_archive", {}).get("logical_sha256") if isinstance(state.get("checkpoint_history_archive"), dict) else None,
            }
        elif args.command == "recover-pending":
            result = recover_pending_append(root)
        else:
            restored = restore_original_state_bytes(root, state)
            output = args.output
            if output.exists():
                if output.read_bytes() != restored:
                    raise CheckpointHistoryError(f"refusing to overwrite different existing output: {output}")
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                atomic_write_bytes(output, restored)
            result = {"status": "restored_byte_exact_source_state", "output": str(output), "bytes": len(restored)}
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, CheckpointHistoryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
