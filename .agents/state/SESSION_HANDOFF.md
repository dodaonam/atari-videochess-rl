<!-- checkpoint-id: cp-c3b6aa32-20261022T162122935175Z -->
# Session Handoff

This file is a pointer, not a status snapshot. Do not infer current phase, task status, completion, blockers, or Git state from prose here. The checkpoint ID must match `.agents/state/PROJECT_STATE.yaml`.

## Canonical recovery path

1. Read [`AGENTS.md`](../../AGENTS.md), [`REQUIREMENTS.md`](../../docs/01-foundation/REQUIREMENTS.md), and [`PROJECT_STATE.yaml`](PROJECT_STATE.yaml).
2. Run [`agent_preflight.py`](../../scripts/agent_preflight.py) from the repository root. Review warnings as well as errors.
3. Follow `task_refs` to [`BACKLOG.yaml`](../tasks/BACKLOG.yaml); follow any active task's dependencies, evidence, blocker IDs, and user approval gate.
4. For gate order, criteria, blockers, findings, and decisions, follow [`EXECUTION_PLAN.md`](../../docs/02-management/EXECUTION_PLAN.md), [`ACCEPTANCE_CRITERIA.md`](../../docs/06-quality/ACCEPTANCE_CRITERIA.md), [`BLOCKERS.md`](BLOCKERS.md), [`VERIFIED_FINDINGS.md`](VERIFIED_FINDINGS.md), and the relevant ADR.
   - The current governance decision is [`ADR-0001`](../../docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md); discover later decisions in `docs/02-management/decisions/`.
5. Compare the portable tracked-file manifest with live HEAD/index. Treat the `git` snapshot as workspace-local; an exact portable manifest match after commit/checkout is expected even when branch, HEAD, status, ignored files, or caches differ. The local Git config UUID distinguishes the original workspace from a clean clone. For older checkpoints without a portable manifest, use the safe tracked-file migration path described in `AGENTS.md`. If version-controlled content or canonical references drift, inspect them and never discard work automatically.

## M3 closeout and Pre-M4 pointers

M3 acceptance and integration are recorded in [M3 acceptance](../evidence/M3-acceptance-20261021.md) and [post-merge verification](../evidence/M3-postmerge-integration-verification-20261021.md); PR #3 is merged. Earlier dated M3 sections below preserve their review-stage context and are superseded for live status by those closeout records and canonical state/backlog. For the current readiness review, follow the [Pre-M4 readiness evidence](../evidence/PRE-M4-readiness-20261022.md), [M4 plan](../plans/M04-supervised-pretraining.md), [model design](../../docs/03-technical/MODEL_DESIGN.md), [training protocol](../../docs/04-research/TRAINING_PROTOCOL.md), and proposed [ADR-0003](../../docs/02-management/decisions/ADR-0003-pretraining-model-interface.md). These are review materials, not authorization; use canonical state/backlog for M4 status.

For the independent final Pre-M4 hardening review, use the hardening supplement and exact-revision verification matrix in [PRE-M4-readiness-20261022.md](../evidence/PRE-M4-readiness-20261022.md), the checkpoint failure/rollback contract in [PLANS.md](../PLANS.md), and the updated RSK-010 boundary in [RISK_REGISTER.md](../../docs/02-management/RISK_REGISTER.md). R07 is conditional pending lossless history migration before checkpoint-heavy work; M4 remains pending separate authorization.

## Post-M2 and Pre-M3 review pointers

For M2 acceptance and integration history, follow the [M02 plan](../plans/M02-chess-foundation.md), accepted [ADR-0002](../../docs/02-management/decisions/ADR-0002-chess-mdp-action-and-perspective.md), [acceptance evidence](../evidence/M2-acceptance-20261016.md), [GitHub delivery record](../evidence/M2-github-delivery-20261016.md), [post-M2 integration verification](../evidence/POST-M2-INTEGRATION-VERIFICATION-20261017.md), and [Pull Request #1](https://github.com/dodaonam/atari-videochess-rl/pull/1).

For the Pre-M3 audit and owner review, inspect [PRE-M3 readiness evidence](../evidence/PRE-M3-readiness-20261017.md), [M03 plan](../plans/M03-expert-dataset.md), the research contracts under docs/04-research/, [REPRODUCIBILITY.md](../../docs/05-operations/REPRODUCIBILITY.md), and the [Pre-M3 Pull Request #2](https://github.com/dodaonam/atari-videochess-rl/pull/2). Current gate, task, milestone, and authorization are owned by PROJECT_STATE.yaml and BACKLOG.yaml. Planning and readiness do not mark M3 started or authorize its source acquisition.

For the authorized M3 implementation and independent review, inspect [M3 authorization](../evidence/M3-authorization-20261020.md), [source decision and terms](../evidence/M3-source-decision-20261020.md), [source manifest](../evidence/M3-source-manifest-20261020.json), [execution and acceptance evidence](../evidence/M3-execution-20261020.md), [release manifest](../evidence/M3-release-manifest-r3-20261020.json), [teacher manifest](../evidence/M3-teacher-manifest-r2-20261020.json), and [r3/r4 reproducibility evidence](../evidence/M3-reproducibility-r3-r4-20261020.json). Use PROJECT_STATE.yaml and BACKLOG.yaml for current task and review status; this pointer section does not approve M3 or G3. At the implementation-review stage, [M3 PR #3](https://github.com/dodaonam/atari-videochess-rl/pull/3) was open for PM acceptance; the accepted and merged outcome is recorded in the M3 closeout pointers above.

For the 2026-10-21 corrective-hardening review, use [corrective audit, acceptance matrix, artifact identities, historical comparison, and PM checklist](../evidence/M3-corrective-hardening-20261021.md), the [machine-readable run records](../evidence/M3-corrective-run-records-20261021.json), corrected [r4 release manifest](../evidence/M3-corrective-release-manifest-r4-20261021.json), [r4/r5 byte-comparison record](../evidence/M3-corrective-reproducibility-r4-r5-20261021.json), corrected [Stockfish teacher manifest](../evidence/M3-corrective-teacher-manifest-r2-20261021.json), and sanitized run logs in `../evidence/logs/`. At the time of this corrective review, raw source, releases, and the teacher sidecar were retained as ignored artifacts under `artifacts/m3/`; the artifacts are absent from the current checkout. F-01 through F-08 and adjacent F-09 through F-11 were dispositioned. That review-stage status preceded the later M3 acceptance and merge recorded above; G3 remains unapproved.

For final M3 closure, use the [NEW-01 through NEW-04/E-01 closure report](../evidence/M3-final-closure-20261021.md), its [machine-readable source/release/teacher/test identities](../evidence/M3-final-closure-record-20261021.json), and final closure logs in `../evidence/logs/`. The corrected local r6/r7 releases share release ID `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`; the 128-position teacher run is separately bound and verified. Final exact-PR-HEAD clean-clone output and GitHub check scope are recorded in PR #3 after push; formal acceptance and merge are documented above. G3 remains unapproved.

## Checkpoint operation

After a meaningful change, before a long task, and before handing off, run:

```bash
python3 scripts/agent_checkpoint.py
python3 scripts/agent_preflight.py
```

For old partial-write temp files, inspect the preflight warning, then use `python3 scripts/agent_checkpoint.py --recover-partials` and rerun preflight. The checkpoint script does not update task status or claim acceptance; update canonical state/backlog only from evidence.
