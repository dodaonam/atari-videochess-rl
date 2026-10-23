# Agent Plan and Context Rules

This file defines how project plans and persistent context are maintained. The current status and task are not stored here; read `.agents/state/PROJECT_STATE.yaml` and `.agents/tasks/BACKLOG.yaml`.

## 1. Canonical records

| Record | Owns | Must not become |
|---|---|---|
| `docs/02-management/EXECUTION_PLAN.md` | Engineering milestone order, dependencies, deliverables, and fixed-file inventory. | A live task-status board or duplicate G/M crosswalk. |
| `docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md` | Accepted governance-to-engineering crosswalk and its resolution rationale. | Live phase or task status. |
| `.agents/state/PROJECT_STATE.yaml` | Current governance gate, engineering milestone, next action reference, last verified Git snapshot, and checkpoint ID. | A copy of the backlog, blocker details, or handoff narrative. |
| `.agents/tasks/BACKLOG.yaml` | Stable task IDs, dependencies, statuses, exact next actions, acceptance criterion IDs, evidence, and any task-level blocker IDs. | A project overview or experiment-results store. |
| `.agents/state/BLOCKERS.md` | Active and resolved blocker records and the evidence/condition needed to clear them. | A list of ordinary pending tasks or external questions already owned by `REQUIREMENTS.md`. |
| `.agents/state/VERIFIED_FINDINGS.md` | Evidence-backed facts and findings with stable IDs and repository-relative evidence. | Design proposals, status, or unverified assumptions. |
| `docs/02-management/decisions/ADR-*.md` | Accepted or proposed decisions, context, alternatives, rationale, consequences, and evidence. | A chronological chat transcript. |
| `.agents/state/SESSION_HANDOFF.md` | Pointer to canonical records plus a checkpoint ID. | A duplicate state/task summary. |
| Experiment run manifests and metrics | Run config, provenance, measurements, and artifact references. | Project decisions or milestone status. |

If a detail must be repeated for navigation, link or cite its canonical ID instead of copying its value.

## 2. Task plan format

Each task in `BACKLOG.yaml` must have:

- a stable, unique ID (`G1-001`, `M0-001`, etc.); never recycle an ID;
- a concise title and owning governance gate or engineering milestone;
- status: `pending`, `in_progress`, `blocked`, `done`, or `cancelled`;
- `depends_on` IDs, with no missing references or dependency cycles;
- an exact `next_action` for every incomplete task; completed/cancelled tasks use an empty string;
- `acceptance_criteria_ids` referencing IDs in `docs/06-quality/ACCEPTANCE_CRITERIA.md` (do not copy criterion prose into the task);
- evidence entries for every `done` task, with at least one currently verified record;
- blocker IDs for every `blocked` task;
- `requires_user_gate_approval` where a user review/authorization gate must be passed.

Each task's `acceptance_criteria_ids` applies to its evidence set. State and backlog use `schema_version: 2`. Every evidence entry has provenance `verified`, `historical_unverified`, `manual_pending`, or `manual_verified`. Verified commands/tests carry execution and recording timestamps, exit code, full Git revision, result, and an existing sanitized repository-relative log path. Verified file reviews carry a recording timestamp and revision. Historical reports whose original logs/timestamps were not retained keep those fields null and use `historical_unverified`; they cannot be the only evidence for a task marked `done`. Manual acceptance records use a sanitized retained result, actual session timestamp, and Git revision without an invented process exit code.

`requires_user_gate_approval` is an **entry prerequisite** only when the task must wait for an already approved upstream gate. ADR-0001's G/M crosswalk records which engineering work contributes to a gate's eventual acceptance; a gate that covers a milestone is not thereby a prerequisite to start that milestone. In particular, G3 covers M2–M5 and G4 covers M6 plus M7 evaluation, so G3 closure cannot be required before M3, M4, or M5 work, and G4 closure cannot be required before M6. Use `engineering.start_authorized` plus `engineering.start_authorization_record` before setting an engineering milestone in progress. The record identifies its authorization ID, task, milestone, direct user/PM authority, UTC time, bounded scope, and `.agents/evidence/` path; the active task must cite that file as manual-verified authorization evidence. A plan, dependency completion, research document, or Boolean flag alone never supplies authorization. G3/G4 remain open until their acceptance and review conditions are met.

The task owns its progress. `PROJECT_STATE.yaml` points to the active/next task; `SESSION_HANDOFF.md` points to state and backlog. A command result is evidence only when its actual result has been recorded, not merely because a command appears in a plan.

## 3. Milestone plan format

Create milestone plans according to the canonical file inventory in `docs/02-management/EXECUTION_PLAN.md`; do not create future engineering milestone plans prematurely. The G1 consistency hardening task plan is `.agents/plans/G1-consistency-hardening.md`, referenced by G1-007 and G1-008 in the backlog; it is not an M0/M1 plan. Task status remains canonical in backlog/state.

Each milestone plan should include:

1. `plan_id`, milestone, plan status, source requirements, and relevant ADR IDs;
2. objective, scope, explicit exclusions, and dependencies;
3. task IDs linked to the canonical backlog (the plan may explain steps but must not own status);
4. acceptance criterion IDs from `ACCEPTANCE_CRITERIA.md`;
5. commands/checks to run and expected evidence, without claiming they have passed;
6. risks, open approvals, checkpoint cadence, and recovery steps;
7. a completion review that updates the backlog/state only after evidence exists.

Use status values `draft`, `ready`, `in_progress`, `blocked`, `complete`, or `superseded`. A plan is not permission to execute its milestone.

## 4. Decision records

Use an ADR when a choice changes the architecture, source-of-truth model, milestone mapping, priority classification, data policy, or evaluation interpretation. A decision must state its scope and whether it is only a project-process decision or also needs user/instructor approval. Use `proposed`, `accepted`, `rejected`, or `superseded`; retain superseded records and link replacements.

Do not turn an open requirement into an accepted ADR without the required user/instructor approval. Do not create speculative ADRs for choices that have not arisen.

## 5. Context recovery and checkpoints

Before resuming work:

1. Read root `AGENTS.md`, `REQUIREMENTS.md`, and `PROJECT_STATE.yaml`.
2. Run `python3 scripts/agent_preflight.py` from the repository root.
3. Read the handoff pointer, then follow it to state, backlog, active plan, blocker/finding records, relevant ADRs, and evidence.
4. Verify `last_checkpoint.portable_git` against the live tracked index and HEAD. It contains a path/mode/blob manifest, a semantic state checksum, and a handoff checksum; a matching clean HEAD is an expected commit/checkout transition, not a demand for a saved future commit hash. The `last_checkpoint.git` section is a workspace-local observation of branch, HEAD, status, ordinary-file hashes, and artifact inventory. A local UUID in Git config identifies that workspace; a clone without the UUID uses the portable baseline. Missing local-only files and cache directories do not invalidate the portable baseline. Legacy state uses a safe tracked-file hash migration when complete; otherwise preflight reports that migration is unverified.
5. Select the next task from canonical state/backlog and verify its dependencies and user gates.

Checkpoint before long-running work, after a significant change or gate result, after a blocker changes, and before handoff. Use `python3 scripts/agent_checkpoint.py`; then rerun preflight. Legacy state stores prior snapshots inline; migrated state stores them in the versioned archive documented by [`CHECKPOINT_HISTORY.md`](../docs/05-operations/CHECKPOINT_HISTORY.md). The script snapshots portable tracked content and local workspace observations and updates the handoff pointer. Caught failures roll back the state/handoff pair and archive append; a process interruption can still leave a detectable pending append because those files are not one transaction. Commit archive files with the state pointer and verify them independently on a clean clone. Checkpointing does not mark tasks done or change milestone status.

Each canonical file is replaced atomically on its own; the state and handoff pair is not a crash-transactional write. If a caught failure occurs after provisional writes, the checkpoint command restores the original state bytes, handoff bytes, and any local workspace identity it created. For a migrated archive, caught append failures also restore the previous manifest and remove the newly appended segment. A process or power loss can leave a stale handoff or a pending archive append; preflight identifies these states, and `CHECKPOINT_HISTORY.md` defines the safe recovery commands. Preflight also reports orphan `.tmp-*` files. Inspect the report and use `--recover-partials` only for old agent-owned canonical temp files. Never read a temp file as canonical state.

## 6. Portable YAML and file handling

The state files use **JSON-compatible YAML 1.2** so the scripts can parse and validate them with the Python standard library and no project dependencies. Keep them valid JSON and valid YAML; do not add YAML-only tags, aliases, or comments. The scripts enforce the documented schema version and required fields.

All persisted paths are repository-relative POSIX paths. Do not store machine-specific absolute paths, credentials, tokens, full environment dumps, or chat transcripts in project state. Link to the existing `chat_history.md` only when historical context is necessary; do not copy its contents.

## 7. Changes and recovery safety

- Inspect existing files and Git status before edits. Preserve dirty and untracked work.
- Do not infer completion from a stale handoff, an old chat, a plan checkbox, or a file's existence.
- If the live state contradicts the handoff, discard the handoff's implicit snapshot and reconstruct from state, backlog, Git, evidence, and blockers; then refresh the pointer.
- If a task is incomplete, keep it pending/in progress/blocked and update its canonical `next_action` field. Acceptance criterion prose remains in `ACCEPTANCE_CRITERIA.md`; backlog entries reference criterion IDs and evidence only.
- If validation detects malformed or partial state, stop dependent work. Preserve the last readable state, inspect the diff/temp files, and recover atomically; do not auto-rewrite canonical state from guesses.
- Large datasets, replay buffers, checkpoints, and credentials are not stored in these context files or ordinary Git history.
