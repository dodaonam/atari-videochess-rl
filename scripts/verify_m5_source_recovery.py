#!/usr/bin/env python3
"""Verify recovered M5 source bytes, checkpoint history, and run-start semantics."""

from __future__ import annotations

import argparse
import ast
import difflib
import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECORD_PATH = ROOT / ".agents/evidence/M5-source-recovery-20261030.json"
RECOVERED_ROOT = ROOT / ".agents/evidence/M5-source-recovered"
CHECKPOINTS = ROOT / ".agents/state/checkpoint-history/segments"
TRAINING_RECORD = ROOT / ".agents/evidence/M5-training-campaign-verification-20261029.json"
BEFORE_ID = "cp-08f98f9d-20261029T043013180672Z"
AFTER_ID = "cp-08f98f9d-20261029T143803674896Z"
EXPECTED_TRAINING_SOURCES = {
    "093992c50e893a7fdd92f2f95faafe28d4f1e73c7351a4a8179a3056c4e63b00": 4,
    "cdcc1fdc0ca0b324e49cfb8b0ff571496a554e9892dfb3620d6454a65ee16da0": 2,
}
EXPECTED_RECOVERED = {
    "checkpoint.py": "19ab713b5a1450c2e4506d9d761768317e0b48fb96a3cb0083965d6a037bc410",
    "replay.py": "5ae4d3d928c524539bcf6b29f4102f09b246d5703b66539f2fad4aa7e2aaa278",
}
EXPECTED_LATER = {
    "videochess_rl/rl/checkpoint.py": "924a95e6accb04c727e2858dbcd6cbda84b970750decc27fd09621bdc61821aa",
    "videochess_rl/rl/replay.py": "21845b0755809d07d480da821c2e809540a0ca4b8e1eddc5785ebdec5cf59b7f",
}
EXPECTED_RUNTIME_CHANGE_PATHS = {
    "videochess_rl/rl/checkpoint.py",
    "videochess_rl/rl/replay.py",
    "videochess_rl/rl/cli.py",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _visible_trailing_spaces(line: str) -> str:
    content = line.rstrip(" ")
    return content + "␠" * (len(line) - len(content))


def _class_methods(source: str, class_name: str) -> dict[str, ast.AST]:
    tree = ast.parse(source)
    cls = next(item for item in tree.body if isinstance(item, ast.ClassDef) and item.name == class_name)
    return {item.name: item for item in cls.body if isinstance(item, ast.FunctionDef)}


def _checkpoint_records() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path in sorted(CHECKPOINTS.glob("*.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if row.get("id") in {BEFORE_ID, AFTER_ID}:
                    records[row["id"]] = row
    if records.keys() != {BEFORE_ID, AFTER_ID}:
        raise ValueError("required source-comparison checkpoint records are missing")
    return records


def _verify_transcript(record: dict[str, Any], path: Path | None) -> dict[str, Any]:
    metadata = record["transcript"]
    candidate = path or Path(metadata["path"])
    if not candidate.is_file():
        return {"available": False, "recorded_path": metadata["path"], "result": "not present in this environment"}
    data = candidate.read_bytes()
    text = data.decode("utf-8")
    if len(data) != metadata["bytes"] or _sha(data) != metadata["sha256"]:
        raise ValueError("supplied transcript no longer matches its recorded byte identity")
    if len(text.splitlines()) != metadata["line_count"]:
        raise ValueError("supplied transcript line count differs from its provenance record")
    lines = text.splitlines()
    raw_lines = data.splitlines(keepends=True)
    ranges = {"checkpoint.py": (1647, 1873), "replay.py": (1874, 2017)}
    for name, (first, last) in ranges.items():
        extracted = b"".join(raw_lines[first - 1:last])
        target = (RECOVERED_ROOT / name).read_bytes()
        if extracted != target or _sha(extracted) != EXPECTED_RECOVERED[name]:
            raise ValueError(f"transcript line extraction does not reproduce authenticated {name}")
    old_cli_excerpt = "\n".join(text.splitlines()[2758:2783]) + "\n"
    if old_cli_excerpt.encode() != (RECOVERED_ROOT / "cli-resume-earlier.pyfrag").read_bytes():
        raise ValueError("CLI recovery excerpt does not reproduce the transcript lines")
    return {"available": True, "path": str(candidate), "bytes": len(data), "sha256": _sha(data),
            "line_count": len(lines), "result": "exact transcript identity and source-line extraction verified"}


def verify(transcript_path: Path | None = None, *, require_private_artifacts: bool = False) -> dict[str, Any]:
    record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    recovered = {}
    for name, expected in EXPECTED_RECOVERED.items():
        data = (RECOVERED_ROOT / name).read_bytes()
        if _sha(data) != expected:
            raise ValueError(f"authenticated recovered source hash mismatch: {name}")
        recovered[name] = {"sha256": expected, "bytes": len(data), "authenticity": "exact byte match to original recorded SHA-256"}

    transcript = _verify_transcript(record, transcript_path)
    before_after = _checkpoint_records()
    before = before_after[BEFORE_ID]["workspace_git"]["repo_file_hashes"]
    after = before_after[AFTER_ID]["workspace_git"]["repo_file_hashes"]
    changed = [{"path": name, "before_sha256": before.get(name), "after_sha256": after.get(name)}
               for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)]
    changed_runtime = [item for item in changed if item["path"].startswith("videochess_rl/") and item["path"].endswith(".py")]
    if {item["path"] for item in changed_runtime} != EXPECTED_RUNTIME_CHANGE_PATHS:
        raise ValueError("checkpoint history runtime-source change set differs from the recorded three-file set")
    cli_record = record["comparisons"]["cli.py"]
    for item in changed_runtime:
        if item["path"] == "videochess_rl/rl/cli.py":
            if (item["before_sha256"] != cli_record["earlier_full_file_sha256"]
                    or item["after_sha256"] != cli_record["later_full_file_sha256"]):
                raise ValueError("CLI checkpoint hashes differ from the recorded training source identities")
            continue
        prior_expected = EXPECTED_RECOVERED[Path(item["path"]).name]
        later_path = ROOT / item["path"]
        if item["before_sha256"] != prior_expected or item["after_sha256"] != EXPECTED_LATER[item["path"]]:
            raise ValueError(f"checkpoint source hashes do not match authenticated code: {item['path']}")
        if _sha(later_path.read_bytes()) != item["after_sha256"]:
            raise ValueError(f"later source file differs from the source snapshot: {item['path']}")

    for name, diff_name in (("checkpoint.py", "checkpoint-to-current.diff"),
                            ("replay.py", "replay-to-current.diff")):
        old = (RECOVERED_ROOT / name).read_text(encoding="utf-8").splitlines()
        later = (ROOT / "videochess_rl/rl" / name).read_text(encoding="utf-8").splitlines()
        diff_lines = difflib.unified_diff(old, later, fromfile=f"recovered/{name}",
                                          tofile=f"current/{name}", lineterm="")
        expected_diff = "\n".join(_visible_trailing_spaces(line) for line in diff_lines) + "\n"
        if expected_diff != (RECOVERED_ROOT / diff_name).read_text(encoding="utf-8"):
            raise ValueError(f"retained source diff is stale: {diff_name}")

    replay_old = _class_methods((RECOVERED_ROOT / "replay.py").read_text(), "ReplayBuffer")
    replay_new = _class_methods((ROOT / "videochess_rl/rl/replay.py").read_text(), "ReplayBuffer")
    replay_buffer_methods_equal = all(ast.dump(replay_old[name], include_attributes=False)
                                      == ast.dump(replay_new[name], include_attributes=False)
                                      for name in ("__init__", "__len__", "transitions", "insert", "sample",
                                                   "state_dict", "from_state_dict"))
    if not replay_buffer_methods_equal:
        raise ValueError("replay learning operations no longer match the recovered source")
    old_journal_methods = _class_methods((RECOVERED_ROOT / "replay.py").read_text(), "ReplayJournal")
    new_journal_methods = _class_methods((ROOT / "videochess_rl/rl/replay.py").read_text(), "ReplayJournal")
    journal_append_identical = (ast.dump(old_journal_methods["append"], include_attributes=False)
                                == ast.dump(new_journal_methods["append"], include_attributes=False))
    if not journal_append_identical:
        raise ValueError("replay journal append operation differs from the recovered source")
    journal_changed_methods = sorted(name for name in old_journal_methods.keys() & new_journal_methods.keys()
                                     if ast.dump(old_journal_methods[name], include_attributes=False)
                                     != ast.dump(new_journal_methods[name], include_attributes=False))
    if journal_changed_methods != ["__init__", "verify"]:
        raise ValueError(f"replay journal changes exceed the verified recovery-only methods: {journal_changed_methods}")
    old_checkpoint_tree = ast.parse((RECOVERED_ROOT / "checkpoint.py").read_text())
    new_checkpoint_tree = ast.parse((ROOT / "videochess_rl/rl/checkpoint.py").read_text())
    old_checkpoint_functions = {node.name: node for node in old_checkpoint_tree.body
                                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    new_checkpoint_functions = {node.name: node for node in new_checkpoint_tree.body
                                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    checkpoint_changed_functions = sorted(name for name in old_checkpoint_functions.keys() & new_checkpoint_functions.keys()
                                          if ast.dump(old_checkpoint_functions[name], include_attributes=False)
                                          != ast.dump(new_checkpoint_functions[name], include_attributes=False))
    if checkpoint_changed_functions != ["restore_training_checkpoint", "verify_training_checkpoint"]:
        raise ValueError("checkpoint diff is not confined to validation and restore")

    group_record = json.loads(TRAINING_RECORD.read_text(encoding="utf-8"))
    groups: dict[str, int] = {}
    for run in group_record["runs"]:
        groups[run["code_sha256"]] = groups.get(run["code_sha256"], 0) + 1
    if groups != EXPECTED_TRAINING_SOURCES:
        raise ValueError("training source groups differ from the immutable six-run campaign record")

    private_root = ROOT / "artifacts/m5"
    resumptions = []
    if private_root.is_dir():
        for run in group_record["runs"]:
            if run["training_seed"] != 20261106:
                continue
            summary = json.loads((private_root / "runs" / run["run_id"] / "run-summary.json").read_text())
            attempt = json.loads((private_root / "runs" / run["run_id"] / "attempt-record.json").read_text())
            if (summary["code"]["source_sha256"] != run["code_sha256"]
                    or summary.get("resume_parent_checkpoint_sha256") is not None
                    or attempt.get("resume_parent_checkpoint_sha256") is not None
                    or attempt.get("attempt_id") != "attempt-0000"
                    or summary.get("valid_decisions") != 50000):
                raise ValueError(f"seed 20261106 run unexpectedly resumed or differs from its record: {run['run_id']}")
            resumptions.append({"run_id": run["run_id"], "arm": run["arm"], "source_sha256": run["code_sha256"],
                                "attempt_id": attempt["attempt_id"], "resume_parent_checkpoint_sha256": None,
                                "valid_decisions": summary["valid_decisions"]})
    elif require_private_artifacts:
        raise FileNotFoundError("private M5 artifacts are required for run-start/resume verification")

    historical_scan = json.loads((ROOT / ".agents/evidence/M5-source-reconciliation-20261030.json").read_text())
    prior_blob_scan = historical_scan["training_identity"]["sha256_file_blob_availability_in_local_git_object_database"]
    cli_source = (ROOT / "videochess_rl/rl/cli.py").read_text(encoding="utf-8")
    cli_tree = ast.parse(cli_source)
    resume_function = next(node for node in cli_tree.body
                           if isinstance(node, ast.FunctionDef) and node.name == "_latest_verified_resume")
    current_cli_fragment = (ast.get_source_segment(cli_source, resume_function) + "\n").encode("utf-8")
    if current_cli_fragment != (RECOVERED_ROOT / "cli-resume-later-current.pyfrag").read_bytes():
        raise ValueError("later CLI recovery-selector fragment changed; refresh the source comparison")
    return {
        "schema": "videochess-m5-source-recovery-verification/1.0",
        "transcript": transcript,
        "recovered_sources": recovered,
        "checkpoint_snapshot_changes": changed,
        "changed_runtime_python_files": changed_runtime,
        "replay_sampling_and_state_operations_identical": replay_buffer_methods_equal,
        "replay_journal_append_identical": journal_append_identical,
        "replay_journal_changed_methods": journal_changed_methods,
        "checkpoint_changed_functions": checkpoint_changed_functions,
        "cli_full_file_recovered": False,
        "cli_resume_function_matches_preserved_later_fragment": True,
        "cli_full_file_sha256_matches_in_git_object_store": {
            cli_record["earlier_full_file_sha256"]: prior_blob_scan.get(cli_record["earlier_full_file_sha256"]),
            cli_record["later_full_file_sha256"]: prior_blob_scan.get(cli_record["later_full_file_sha256"]),
        },
        "training_source_groups": groups,
        "seed_20261106_runs": resumptions,
        "residual_note": "Full CLI file bytes were not reconstructed; its transcript-authenticated training-resume excerpt and recorded patch hunks are preserved separately. The two final-seed runs were attempt-0000 and did not restore a checkpoint.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcript", type=Path, default=None,
                        help="path to the supplied transcript; defaults to its recorded original path")
    parser.add_argument("--require-private-artifacts", action="store_true",
                        help="fail if private run summaries are not available for resume-path verification")
    args = parser.parse_args()
    print(json.dumps(verify(args.transcript, require_private_artifacts=args.require_private_artifacts), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
