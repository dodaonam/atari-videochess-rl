# G1 Cross-Document Consistency and Recovery Hardening

- **Plan ID:** G1-HARDENING-001
- **Milestone:** G1
- **Task owner:** `.agents/tasks/BACKLOG.yaml` (`G1-007`, followed by `G1-008`)
- **Source:** Current user request, G1 audit report, and current `ACCEPTANCE_CRITERIA.md`
- **Decision reference:** `ADR-0001` for G/M ownership only

## Objective

Fix the reported context-script defects, reconcile canonical ownership and evidence rules, and leave G1 unapproved until the independent Codex-session recovery check and user review are complete.

## Scope and exclusions

- Modify only G0/G1 documentation, persistent context, the two context scripts, their standard-library tests, and a verification record.
- Do not edit `ROADMAP.md`, `README.md`, original HTML, chat history, application code, or dependency configuration.
- Do not start M0/M1, install dependencies, allocate compute, train, commit, or push.
- Run all destructive/recovery cases only in disposable temporary Git repositories.

## Work sequence

1. Add failing tests for dry-run recovery, a one-call checkpoint from a clean worktree, tracked and untracked content drift, all criterion formats, oversized files, artifact directories, and historical baseline behavior.
2. Fix the checkpoint and preflight root causes with standard-library code; expose the discovered criterion and hash-inventory result in JSON recovery output.
3. Reconcile ADR ownership references, M7 evaluation/delivery acceptance ownership, evidence provenance rules, and baseline/artifact descriptions. Keep historical claims explicitly unverified when timestamps or original logs are unavailable.
4. Record this hardening task and verification evidence in canonical state/backlog. Preserve the independent Codex-session acceptance as pending; do not claim G1 approval.
5. Run the full unittest suite, preflight, link/criterion/state checks, and a final self-review against the user audit checklist.

## Acceptance

- All documented acceptance IDs are discoverable, and future M2–M7 task references validate.
- Dry-run makes no filesystem changes; a successful checkpoint is immediately consistent after one invocation.
- One large-file warning is emitted, large/unreadable files and artifact directories are separately identified, and artifact contents are left to independent manifests.
- Historical G1 baseline entries do not create recurring warnings after authorized future edits.
- All cross-document ownership and M7 gate references agree with ADR-0001.
- Backlog evidence distinguishes current verified runs from historical reports without invented timestamps or logs.
- G1 remains unapproved; M0/M1 remain unauthorized.

## Review focus

- Snapshot content must be captured after both canonical files are atomically updated, without self-referential state hashing.
- Artifact directories must be reported without hashing or copying artifact contents into project state.
- The review must distinguish current hardening test evidence from G1 claims whose original stdout/logs were not retained.
- A programmatic recovery subprocess is not a substitute for a new Codex session with no prior conversation.
