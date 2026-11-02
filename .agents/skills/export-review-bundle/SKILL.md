---
name: export-review-bundle
description: Use when preparing a complete, portable review archive for a project phase, milestone, experiment, task, or ad hoc review request.
---

# Export Review Bundle

Use this skill when a reviewer needs enough project files and evidence to inspect a requested scope independently.

## Workflow

1. Read `AGENTS.md`, `docs/01-foundation/REQUIREMENTS.md`, `.agents/state/PROJECT_STATE.yaml`, `.agents/tasks/BACKLOG.yaml`, the active plan, relevant decisions, blockers, findings, and acceptance criteria. Do not read `chat_history.md` or infer authorization from archived state.
2. Identify the requested scope, current gate and milestone, matching backlog tasks, dependency tasks, evidence references, acceptance criteria, and unresolved review limitations. If the scope is arbitrary, use task text, file references, local links, and source imports to discover related files; do not use a phase-specific file allowlist.
3. Inspect branch, HEAD, index, worktree, untracked files, and ignore rules. Pick one snapshot mode. Never substitute content from another mode:
   - Default `working-tree` reads current tracked files and relevant non-ignored untracked files.
   - `staged` reads the index, using HEAD only when its blob is identical to the index.
   - `committed` reads only the requested Git commit.
4. Run `python3 scripts/export_review_bundle.py --scope <scope>`. For other modes, pass `--mode staged` or `--mode committed --commit <revision>`. The output is written under `.agents/review-bundles/`.
5. Review the generated `REVIEW_README.md` and `REVIEW_MANIFEST.json`. Confirm required context, dependencies, file provenance, exclusions, hashes, and limitations fit the requested review. The exporter checks ZIP CRCs, member coverage, SHA-256 values, and that project state and Git staging were not changed.

## Security and limits

The exporter excludes Git metadata, virtual environments, generated caches, temporary files, credentials, private configuration, conversation history, prior ZIPs, the export directory, and large data or model artifacts by default. If a selected file looks sensitive, export stops and reports paths and pattern labels only. Never copy a secret into a report or archive. Do not work around a finding by renaming or weakening a file check.

Files over 2 MiB require explicit user approval before inclusion. Only after approval, pass `--include-large`; inspect the exact files and purpose first. This option never overrides secret detection, path safety, or symlink checks. Selected symlinks and unsafe archive paths stop export. Missing evidence, unresolved approvals, excluded dependencies, or unparsed imports must remain visible as limitations.

An archive is a review artifact. Its contents do not authorize a milestone, environment change, external service, compute use, commit, or push.
