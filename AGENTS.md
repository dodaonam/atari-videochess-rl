# Atari VideoChess RL — Codex Operating Instructions

These instructions govern Codex work in this repository. Follow the user's current task scope first. Do not infer approval from a proposal, old chat message, file name, plan, or successful preflight.

## 1. Current governance and authorization

The user approved G0 and G1 on 2026-10-14. G1 establishes persistent context and governance; its independent recovery acceptance is retained in `.agents/evidence/G1-10-recovery-verification.md`. G1 approval is a prerequisite for M0 or M1. Read the latest direct user instructions and `.agents/state/PROJECT_STATE.yaml` for live task scope and authorization; do not encode temporary task restrictions here.

G1 scope includes context documents, state files, the G1 inventory decision record, and the two standard-library context scripts/tests. It excludes M0 setup, M1 ALE work, RL/ALE implementation, dependency installation, model training, Colab allocation, and unrelated P2 documents. Preserve the README and all existing user files. Do not commit, push, publish, or release without direct authorization for that action.

The authorized G1 hardening scope covered the audit defects recorded by the user: checkpoint/dry-run safety, acceptance-ID discovery, hash-inventory reporting, evidence provenance, historical-baseline behavior, and cross-document ownership. G1-10 required a genuinely separate Codex session without prior conversation and is recorded as complete in the evidence file above. Consult canonical state/backlog for current status. Do not start M0/M1 unless a current user task authorizes them and canonical state permits it.

The exact current phase, task, next milestone, and Git snapshot are canonical in `.agents/state/PROJECT_STATE.yaml`; do not hard-code a competing live status in this file.

## 2. Source hierarchy and canonical information ownership

Use the following sources in order:

1. Current direct user instructions define the authorized task and can change decisions.
2. [`docs/01-foundation/REQUIREMENTS.md`](docs/01-foundation/REQUIREMENTS.md) owns project constraints, objectives, open approvals, and requirement IDs.
3. [`docs/01-foundation/ROADMAP.md`](docs/01-foundation/ROADMAP.md) is the verbatim research/engineering plan. A proposed roadmap method is not automatically a binding requirement.
4. Approved ADRs own durable decisions; [`docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md`](docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md) is the sole owner of the G/M crosswalk and its rationale. [`docs/02-management/EXECUTION_PLAN.md`](docs/02-management/EXECUTION_PLAN.md) owns engineering order, dependencies, deliverables, and the P0/P1/P2 inventory.
5. [`docs/06-quality/ACCEPTANCE_CRITERIA.md`](docs/06-quality/ACCEPTANCE_CRITERIA.md) owns pass conditions and required evidence.
6. `.agents/state/PROJECT_STATE.yaml` owns current gate/milestone, next-task pointer, checkpoint ID, and last verified Git snapshot.
7. `.agents/tasks/BACKLOG.yaml` owns task IDs, dependencies, statuses, acceptance evidence, and task blocker references.
8. `.agents/state/BLOCKERS.md` owns blocker details; `.agents/state/VERIFIED_FINDINGS.md` owns evidence-backed findings; `docs/02-management/decisions/ADR-*.md` owns durable decisions.
9. Git, tests, runtime logs, and experiment artifacts are evidence of what actually changed or ran. A plan or status statement cannot replace evidence.
10. `.agents/state/SESSION_HANDOFF.md` is a pointer to canonical records, not a summary source. `chat_history.md` is historical context, not current status or approval. `README.md` is the project entry point, not technical truth.

If sources conflict, record both claims, the impact, and a resolution in an ADR or open requirement. Stop dependent work until the conflict is resolved. Do not silently rewrite the roadmap or mark open assignment questions as approved.

## 3. Session recovery and checkpointing

At each new session:

1. Read this file, `REQUIREMENTS.md`, and `.agents/state/PROJECT_STATE.yaml`.
2. Run `python3 scripts/agent_preflight.py` from the repository root. Review every error and warning.
3. Follow the checkpoint ID in `SESSION_HANDOFF.md`; read the canonical state, backlog, active plan, blocker/finding records, relevant ADRs, and acceptance criteria.
4. Compare the portable tracked-file manifest with the current Git index and HEAD. `last_checkpoint.portable_git` records index paths, modes, and blob IDs, plus checksums for semantic project state and the handoff pointer. A clean checkout whose HEAD manifest matches this portable snapshot is an expected commit/checkout transition; it does not depend on the future commit hash. `last_checkpoint.git` retains a workspace-specific branch, HEAD, status, SHA-256 file inventory, and local artifact observations. Do not treat missing ignored/untracked files or generated caches as corruption of the portable baseline. For legacy checkpoints without `portable_git`, preflight uses tracked-file hashes when it can verify every tracked path; otherwise it reports that migration is unverified. Credential-like files, chat history, symlinks, temp files, VCS/cache/build directories, and files over 2 MiB are not ordinary content-hashed inputs. Artifact/data directories still require independent manifests. Dirty or untracked files are evidence to inspect, not permission to discard, stash, reset, or overwrite.
5. Select the next task from state/backlog only after verifying dependencies, acceptance criteria, blockers, and user approval gates.

Checkpoint before a long task, after a meaningful state or gate change, when a blocker appears or clears, and before handoff. Run `python3 scripts/agent_checkpoint.py`, then rerun preflight. The checkpoint script records a local workspace snapshot, a portable manifest from the Git index, and the handoff pointer; a no-op still verifies migrated archive integrity. Caught failures roll back canonical state/handoff and archive appends, but the multi-file sequence is not crash-atomic. Legacy state keeps history inline; migrated state points to the versioned, lossless `.agents/state/checkpoint-history/` archive. Read [`CHECKPOINT_HISTORY.md`](docs/05-operations/CHECKPOINT_HISTORY.md) before migrating or recovering it. Archive files are verified separately from the portable manifest and must be committed with the canonical pointer for clean-clone recovery. `PROJECT_STATE.yaml` is excluded from the portable file manifest to avoid a self-reference; a semantic-state checksum validates its content, and the handoff pointer has its own checksum. Workspace comparison ignores status flips for those checkpoint-owned control files because their content has separate checksums. The script does **not** mark tasks done, change milestones, or infer semantic progress.

If a handoff checkpoint ID is stale, reconstruct from canonical records and refresh it. If preflight reports `CHECKPOINT_HISTORY_PENDING_APPEND`, follow the verified roll-forward procedure in [`CHECKPOINT_HISTORY.md`](docs/05-operations/CHECKPOINT_HISTORY.md); if it reports missing/corrupt archive data, stop and preserve the files. If preflight reports agent-owned partial files, do not parse them as state; inspect the warning and use `python3 scripts/agent_checkpoint.py --recover-partials` to remove only old matching canonical temp files and write a fresh checkpoint. `--dry-run` never changes files, including when combined with `--recover-partials`, and suppresses Python bytecode cache writes. A malformed canonical state is a stop condition, not a cue to guess.

## 4. Governance gates and engineering milestones

Keep governance gates (`G0–G5`) and engineering milestones (`M0–M7`) separate. ADR-0001 is the canonical G/M crosswalk and records how the history's conflicting labels were resolved. `EXECUTION_PLAN.md` owns the engineering sequence, dependencies, and fixed-file inventory. Do not copy the crosswalk or inventory into another status source.

A G gate and its M milestones retain separate statuses and acceptance evidence. The acceptance criteria assign M7-01–M7-03 evaluation ownership to G4 and M7-04–M7-05 delivery ownership to G5; M7's engineering plan may contain work for both gates, but their statuses and evidence remain separate. M0 may begin only after the user reviews and approves G1. M1 depends on M0 and must pass before substantial data/model/RL work. The mapping does not resolve academic, runtime, storage, or external-service questions in `REQUIREMENTS.md`.

Preserve existing `README.md` and other user files. Use `EXECUTION_PLAN.md` for P0/P1/P2 counts, file dispositions, and when plans are created. Other P2 material is deferred until its milestone or decision requires it.

## 5. Engineering and research rules

- Keep ALE control/state extraction, chess simulator, legal-move generation, model, training, and evaluation responsibilities separate.
- ALE observations are the source of truth for Atari play. A `python-chess` shadow board may track history or cross-check a transition, but must not replace the emulator observation or conceal desynchronization.
- Label supervised Stockfish pretraining, simulator RL, and ALE evaluation/fine-tuning as separate evidence tracks. Never call simulator performance Atari performance or supervised learning RL.
- Stockfish is not part of the inference decision path. Confirm assignment rules before any offline engine-based evaluation or other use not already approved.
- Implement the planned RL algorithm directly in PyTorch; do not add Stable-Baselines or Ray RLlib unless the user changes this constraint.
- Verify reward perspective, terminal/truncation handling, legal-action masks, Double DQN targets, and teacher-score perspective/scale before relying on training results.
- Treat model shape, feature planes, reward shaping, curriculum, ranking loss, hyperparameters, and Atari fine-tuning as experimental proposals unless explicitly accepted.
- Never invent results, claim a test ran when it did not, or report an aspirational Elo as achieved.

## 6. Testing and verification

Define observable success before implementation. Add focused tests for new behavior and run the relevant tests before reporting completion. G1 scripts use Python standard-library `unittest` and no new dependency. Their checks cover JSON-compatible YAML schemas, task IDs/dependencies/evidence provenance, all table and bullet acceptance IDs, local Markdown links, blocker consistency, stale handoff, Git/content/hash-inventory drift, dry-run and partial writes, and fresh-process recovery. A fresh Python process is not proof that a separate Codex session can recover context; G1-10 requires an independent session with no conversation history.

For technical work, follow the coverage and pass conditions in [`TEST_STRATEGY.md`](docs/06-quality/TEST_STRATEGY.md) and `ACCEPTANCE_CRITERIA.md`. A development ALE configuration is for debugging only; record the actual environment settings for any reported evaluation. Run M0/M1 environment or ALE tests only when the latest direct user instructions and canonical state authorize them.

## 7. Reproducibility and evidence

For each future experiment, record source revision, full config, command, seeds/RNG state as needed, library/ALE/ROM/Stockfish versions, runtime/hardware, dataset provenance/hash/split, opponent pool, raw metrics, checkpoint checksum, and artifact location. Store large datasets/checkpoints in approved persistent storage, not only ephemeral Colab storage or ordinary Git history.

Context state uses JSON-compatible YAML 1.2 so Python's standard library can parse and validate it without added dependencies. Persist repository-relative POSIX paths only. The G1-start baseline is immutable historical evidence; do not compare it to current files as an ongoing change detector. Use `last_checkpoint.portable_git` to verify committed tracked content and interpret commit/checkout transitions; use `last_checkpoint.git` for workspace-local status and file observations. For command/test evidence, record the actual execution timestamp, exit code, Git revision, result, and sanitized retained log path. Mark earlier reports whose timestamp/log was not preserved as `historical_unverified`; never backfill invented provenance. Do not store credentials, tokens, full environment dumps, or copied chat transcripts in state. Reference `chat_history.md` by path only when historical context is needed.

## 8. Execution boundaries

- Work only within the current user-authorized scope; preserve all existing tracked, modified, and untracked files.
- Do not start an engineering milestone unless the latest direct user instructions authorize it and canonical state permits it.
- Do not install dependencies, alter system configuration, allocate Colab resources, incur costs, or upload data without separate authorization.
- Do not expose credentials in chat, source, logs, or artifacts.
- Do not edit the README merely to satisfy an inventory count.
- Do not commit, push, publish, or release without direct authorization for that action.
- Follow [`PR_REVIEW_AND_INTEGRATION.md`](docs/02-management/PR_REVIEW_AND_INTEGRATION.md): Codex may implement, verify, and open an authorized PR but must not merge any PR, self-approve as PM, enable auto-merge, or push directly to `initial-idea`/`main`. PM independently reviews and decides; an authorized human/operator performs any merge after that decision. Passing CI or technical milestone completion is never merge authorization.
- A new milestone requires its own direct authorization and a canonical state transition. Completion/readiness of one milestone does not automatically start or authorize the next milestone. Keep PM review, repository integration, milestone authorization, and governance-gate approval separate.

## 9. Blockers and completion reports

A blocker record must state its ID, evidence, impact, owner, and unblock condition. An approval gate is not a technical blocker. Keep incomplete tasks incomplete; never fabricate a finding to fill a template.

A completion report states exact file changes, verification commands/results, what was not run, discrepancies or unresolved approvals, current state, and next user action. A gate is ready for review only when its acceptance evidence exists and state/backlog are consistent. Gate approval and authorization for a specific follow-on task are distinct; read the current request and canonical state before acting.

## 10. Review bundle exports

For a project or task review archive, follow [`.agents/skills/export-review-bundle/SKILL.md`](.agents/skills/export-review-bundle/SKILL.md) and run `python3 scripts/export_review_bundle.py --scope <scope>`. The default is a working-tree snapshot; use `--mode staged` for the index or `--mode committed --commit <revision>` for a specific commit. Bundles are written under the ignored `.agents/review-bundles/` directory. A bundle records project status for review and does not grant approval to start another task. Include files over 2 MiB only after explicit user approval; stop if a sensitive-content finding is reported.
