<!-- checkpoint-id: cp-4e9a8999-20261030T093734539030Z -->
# Session Handoff

This file is a pointer, not a status snapshot. Do not infer current phase, task status, completion, blockers, or Git state from prose here. The checkpoint ID must match `.agents/state/PROJECT_STATE.yaml`.

## Canonical recovery path

1. Read [`AGENTS.md`](../../AGENTS.md), [`REQUIREMENTS.md`](../../docs/01-foundation/REQUIREMENTS.md), and [`PROJECT_STATE.yaml`](PROJECT_STATE.yaml).
2. Run [`agent_preflight.py`](../../scripts/agent_preflight.py) from the repository root. Review warnings as well as errors.
3. Follow `task_refs` to [`BACKLOG.yaml`](../tasks/BACKLOG.yaml); follow any active task's dependencies, evidence, blocker IDs, and user approval gate.
4. For gate order, criteria, blockers, findings, and decisions, follow [`EXECUTION_PLAN.md`](../../docs/02-management/EXECUTION_PLAN.md), [`ACCEPTANCE_CRITERIA.md`](../../docs/06-quality/ACCEPTANCE_CRITERIA.md), [`BLOCKERS.md`](BLOCKERS.md), [`VERIFIED_FINDINGS.md`](VERIFIED_FINDINGS.md), and the relevant ADR.
   - The current governance decision is [`ADR-0001`](../../docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md); discover later decisions in `docs/02-management/decisions/`.
5. Compare the portable tracked-file manifest with live HEAD/index. Treat the `git` snapshot as workspace-local; an exact portable manifest match after commit/checkout is expected even when branch, HEAD, status, ignored files, or caches differ. The local Git config UUID distinguishes the original workspace from a clean clone. For older checkpoints without a portable manifest, use the safe tracked-file migration path described in `AGENTS.md`. If version-controlled content or canonical references drift, inspect them and never discard work automatically.

## Current canonical status — G3 approved, M6 unauthorized (2026-10-30)

The independent PM approved G3 after verifying M2–M5 completion and PR #11 integration. The approval and post-merge verification are recorded in [G3-final-approval-20261030.md](../evidence/G3-final-approval-20261030.md) and [comment 6519216543](https://github.com/dodaonam/atari-videochess-rl/pull/11#issuecomment-6519216543). `PROJECT_STATE.yaml` is authoritative: G3 is approved, G4 is the next governance gate, M6 is the next engineering milestone pending separate direct authorization, and no M6 task is active. M5 scientific results and the accepted RSK-014 limitation remain unchanged. No training or evaluation was launched in this closeout.

## Historical M5 technical acceptance handoff — before PR merge and G3 decision

Independent PM acceptance of M5-01–M5-05 is permanently recorded in [the acceptance evidence](../evidence/M5-PM-acceptance-20261030.md) and the authoritative [PR #11 decision](https://github.com/dodaonam/atari-videochess-rl/pull/11#issuecomment-6518394524). M5-001 is done; BLK-003 is resolved by PM risk acceptance; RSK-014 remains an accepted residual because full historical CLI bytes are unavailable. The six-run/1,500-game M2 simulator campaign is preserved. PR #11 is open and unmerged for PM-controlled integration. G3 remains unapproved and M6 is not authorized or started. No additional official training/evaluation is required or authorized.

## Historical M5 execution handoff — pre-PM disposition

The following campaign and forensic notes preserve their point-in-time status before the independent PM comment at 2026-10-30T08:22:10Z. Any statement below that PM disposition is pending or M5 is blocked is historical and is superseded by the current status at the top of this handoff and in `PROJECT_STATE.yaml`.

At the time of this historical campaign handoff, canonical state/backlog marked M5/M5-001 blocked by BLK-003 after owner-authorized training/evaluation completion; this status was superseded by the independent PM disposition recorded above. The owner resumed the campaign on 2026-10-29; scope/budget authority is recorded in [the resumption evidence](../evidence/M5-001-resumption-authorization-20261029.md). The original stop and four-run evidence remain preserved in [the pause record](../evidence/M5-pause-after-scratch-20261105-20261029.md).

Before resuming, the four completed runs and all 24 initialization/periodic/final snapshots were reverified. Seed 20261106 has only the two pre-RL initialization artifacts; neither arm has an official training attempt, replay journal, or summary. The 20261105 Scratch episode checkpoint/replay were fully restored and exact-compared after a streaming-tail recovery optimization; the 358-test local suite passed. See the resumption evidence and its retained logs for hashes and timings.

Both remaining `20261106` runs completed, bringing the campaign to six runs and 300,000 decisions. Campaign evidence verifies 73,470 updates, 144 synchronizations, 15 policy schedules and 1,500 unique game rows; 1,494 games ended normally and six are valid decision-cap truncations. The artifact manifest verifies 7 manifests / 6,544,747,450 bytes. PR #11 remains open and unmerged. The post-review audit reproduced the 28 clean-clone evidence-log failures at `575dce5`, included exactly the referenced logs, and added an untracked-M5-log guard. The owner-supplied transcript now recovers historical `checkpoint.py` and `replay.py` byte-for-byte. Replay insertion/sampling/state operations and journal append are identical; checkpoint differences affect validation/restoration. The full historical CLI files remain unavailable, but recorded selector edits are documented and both final-seed attempts are fresh with no resume parent. No learning-distribution change is evidenced; the initial possible sampling confound is superseded, while the CLI byte gap and three-seed statistical limitation remain for PM review. Fourteen source tests passed before a selector-order regression was added; the latest focused suite has 15 PASS. An optional historical full-history restore differential is preserved as INCOMPLETE after 20:16.95 CPU-bound time; it is not counted as a pass. See `.agents/evidence/M5-source-semantics-20261030.json` and `docs/04-research/M5_REMEDIATION_AUDIT.md`. Independent PM disposition of BLK-003/RSK-014 remains pending. No official artifact was changed or experiment rerun; no training/evaluation process is active; G3 remains unapproved and M6 has not started. Final full-suite, clean-clone, preflight, and exact-HEAD CI verification are still to be recorded for the current candidate.
## M4 acceptance and integration pointers

M4-001 and M4 are complete and integrated through PR #8 at `c0a284304d602817922772d08f0ff7904af7ae20`; PR #9 integrated its post-merge evidence at `906178775d48e98e64c709673bfe73177dd15c02`. Use [M4 final acceptance](../evidence/M4-final-acceptance-20261027.md) and [post-merge verification](../evidence/M4-postmerge-delivery-verification-20261027.md) for the criteria, exact local artifact identities, logs, and limitations. This historical acceptance does not approve the current Pre-M5 PR, authorize M5, or approve G3.

## M3 closeout and Pre-M4 pointers (historical)

### Pre-M4 closeout pointer before M4 began — 2026-10-27 (historical)

PR #6 merged into `initial-idea` at `89d085d1865d07b10660e82119488960f766d819` and passed fresh clean-clone archive, preflight, focused-test, and full-suite verification. Use [final Pre-M4 closure](../evidence/PRE-M4-final-closure-20261027.md) for the R01–R08 and PM4 acceptance matrices, verified commands, clean-clone evidence, and exact PR integration identity. The owner's final O-01 decision is [recorded here](../evidence/O-01-owner-decision-20261027.md); the earlier conditional authorization is preserved with a dated supersession addendum in [M4-001 authorization history](../evidence/M4-001-authorization-conditional-20261023.md). O-01 is closed for internal planning and execution authorization. The lack of separate instructor-policy evidence is informational, is not an M4-001 prerequisite, and is not formal instructor approval.

The exact accepted M3 release is outside Git, available at the owner-specified local sibling-worktree path, and was reverified read-only; use [the 2026-10-27 release evidence](../evidence/M3-release-local-verification-20261027.md). Reverify all nine files before any future load. No M4 neural loader consumed it here. ADR-0003 is Accepted; consult [the M4 plan](../plans/M04-supervised-pretraining.md), [MODEL_DESIGN.md](../../docs/03-technical/MODEL_DESIGN.md), and [TRAINING_PROTOCOL.md](../../docs/04-research/TRAINING_PROTOCOL.md) for fixed constraints and the bounded behavior-only protocol. No neural implementation, training run, or M4 acceptance is claimed.

PR #5 / RSK-010 is integrated. Use [checkpoint-history operations](../../docs/05-operations/CHECKPOINT_HISTORY.md) and [migration evidence](../evidence/RSK-010-checkpoint-history-migration-20261023.md); the archive is lossless and append-only, grows linearly, verifies its manifest/segments/logical digest/source backup, and is not crash-atomic across multiple file replacements. Preserve all records and follow the roll-forward/recovery boundary.

The paragraph above records the final Pre-M4 closeout state before M4 implementation. Its historical PR, O-01, and M3 release facts are retained for provenance; current M4 execution status is in the section at the top of this file.
## Pre-integration checkpoint migration and M4 entry audit — 2026-10-23 (historical)

The following was accurate before the separately owner-approved PR #5 merge; current integration and M4 entry status are in the dated closure update above.

PR #4 is merged at `16fc01a3fe731c0a0be127026cc64d049c0cf550`. The lossless RSK-010 migration is implemented on the separate `feature/rsk010-lossless-checkpoint-history` branch and is not yet integrated; see [checkpoint-history operations](../../docs/05-operations/CHECKPOINT_HISTORY.md), [migration evidence](../evidence/RSK-010-checkpoint-history-migration-20261023.md), and the updated risk register. The owner issued direct conditional M4-001 authorization, preserved in [conditional authorization evidence](../evidence/M4-001-authorization-conditional-20261023.md); it is not operational until all listed entry conditions are verified. The exact accepted M3 release is absent from documented local paths, O-01 remains unresolved, and ADR-0003 remains Proposed. Therefore M4-001 remains pending; no active milestone/task or start authorization is recorded, and G3 remains unapproved. Review the migration PR and resolve the owner decisions before any M4 start transition.

The migration is submitted as [PR #5](https://github.com/dodaonam/atari-videochess-rl/pull/5) against `initial-idea`, ready for owner review and not merged. At head `f847690cb7890c70dfed705c62cd7922cdd797b8`, GitHub Actions run 39830065154 passed and a clean clone verified the archive and preflight. This final evidence-only update may advance the branch; verify the live PR head and its own passing check before merge. Neither PR readiness nor a passing workflow constitutes integration or M4 authorization.

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
