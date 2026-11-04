<!-- checkpoint-id: cp-80f18bbd-20261104T154405360779Z -->
# Session Handoff

This file is a pointer, not a status snapshot. Do not infer current phase, task status, completion, blockers, or Git state from prose here. The checkpoint ID must match `.agents/state/PROJECT_STATE.yaml`.

## Canonical recovery path

1. Read [`AGENTS.md`](../../AGENTS.md), [`REQUIREMENTS.md`](../../docs/01-foundation/REQUIREMENTS.md), and [`PROJECT_STATE.yaml`](PROJECT_STATE.yaml).
2. Run [`agent_preflight.py`](../../scripts/agent_preflight.py) from the repository root. Review warnings as well as errors.
3. Follow `task_refs` to [`BACKLOG.yaml`](../tasks/BACKLOG.yaml); follow any active task's dependencies, evidence, blocker IDs, and user approval gate.
4. For gate order, criteria, blockers, findings, and decisions, follow [`EXECUTION_PLAN.md`](../../docs/02-management/EXECUTION_PLAN.md), [`ACCEPTANCE_CRITERIA.md`](../../docs/06-quality/ACCEPTANCE_CRITERIA.md), [`BLOCKERS.md`](BLOCKERS.md), [`VERIFIED_FINDINGS.md`](VERIFIED_FINDINGS.md), and the relevant ADR.
   - The current governance decision is [`ADR-0001`](../../docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md); discover later decisions in `docs/02-management/decisions/`.
5. Compare the portable tracked-file manifest with live HEAD/index. Treat the `git` snapshot as workspace-local; an exact portable manifest match after commit/checkout is expected even when branch, HEAD, status, ignored files, or caches differ. The local Git config UUID distinguishes the original workspace from a clean clone. For older checkpoints without a portable manifest, use the safe tracked-file migration path described in `AGENTS.md`. If version-controlled content or canonical references drift, inspect them and never discard work automatically.

## Pre-M7 review package pointer — 2026-10-31

For the preparation-only assessment, M7 work breakdown, and evaluation contract, follow the [Pre-M7 readiness plan](../plans/PRE-M7-readiness.md), [M7 engineering plan](../plans/M07-evaluation-delivery.md), [M7 evaluation protocol](../../docs/04-research/M7_EVALUATION_PROTOCOL.md), and [Pre-M7 verification evidence](../evidence/PRE-M7-readiness-20261031.md). These are independent-review materials, not authorization; live gate, task, and M7 authorization remain in `PROJECT_STATE.yaml` and `BACKLOG.yaml`.

## Current canonical pointer — G5 approved with limitations; M0–M7 research and governance closed (2026-11-01)

The Independent PM approved G5 with limitations and resolved G5-F02 at [PR #21 comment 6558975009](https://github.com/dodaonam/atari-videochess-rl/pull/21#issuecomment-6558975009). PR #21 was merged at 6495bda01daae557a084e8863d2148e08be6cca7. All G0–G5 gates have approved decisions for their recorded scopes; all M0–M7 engineering tasks are done. The Project Owner accepts existing research results as final; no new campaign or milestone is authorized. G5-F01's M3 provenance repair and M7-04 acceptance remain intact. There is no affirmative owner authorization for restricted artifact distribution and no verified blanket owner prohibition; no release was performed. See the [final G5 PM acceptance](../evidence/G5-PM-final-decision-20261101.md), [G5-F02 status](../evidence/G5-F02-provenance-status-20261101.json), [owner research-scope decision](../evidence/PROJECT-OWNER-final-research-scope-decision-20261101.md), and [final project matrix](../evidence/M0-M7-final-project-closure-20261101.md). The earlier pending-review pointers below are historical.

## Historical pointer — G5-F02 remediation submitted before fresh PM approval (2026-11-01)

PR #20 remains integrated at `0b9c4c26ee1d0952a5f9e3b7cd405f5bf4e3008b`; its earlier PM G5 decision is preserved as historical. The later Independent PM finding [G5-F02](https://github.com/dodaonam/atari-videochess-rl/pull/21#issuecomment-6557663143) suspends reliance on the disputed M7-05 owner-release premise and requires fresh review. M7-04 acceptance and G5-F01 resolution remain intact. Current proposed canonical state on amended [PR #21](https://github.com/dodaonam/atari-videochess-rl/pull/21), branch `feature/g5-governance-closeout`, has G0–G4 approved and G5 ready for review, not approved. No affirmative authorization to distribute restricted artifacts is established; the prior blanket owner-prohibition attribution is unverified. The Project Owner has separately recorded existing accepted research results as final; no further research milestone or campaign is authorized. See [G5-F02 erratum](../evidence/G5-F02-provenance-erratum-20261101.md), [research-scope decision](../evidence/PROJECT-OWNER-final-research-scope-decision-20261101.md), and [project closure matrix](../evidence/M0-M7-final-project-closure-20261101.md).

## Historical pointer — M7-005 G5-F01 remediation before later G5 decisions (2026-11-01)

This point-in-time section records the prior executor-authored owner no-release attribution, which is now unverified under G5-F02. Do not use it as current authorization evidence. The PM later issued a G5 decision on PR #20; its M7-05 premise is now subject to fresh review. See the current pointer above and the provenance erratum.

## Historical canonical pointer — M7-004 package ready for Independent PM review (2026-11-01)

At the M7-004 submission checkpoint, PR #18 was the latest integration and M7-005 remained pending and unstarted. That point-in-time pointer is superseded by the current M7-005 closeout pointer above. The [M7-004 acceptance evidence](../evidence/M7-004-acceptance-20261101.md), [evidence inventory](../evidence/M7-004-evidence-inventory-20261101.json), and four delivery documents remain the M7-04 evidence; their results are unchanged.

## Historical PR #15 corrective continuation — PM6C-F01 (completed)

The PM requested changes on [PR #15 comment 6541119468](https://github.com/dodaonam/atari-videochess-rl/pull/15#issuecomment-6541119468), identifying false `verified` provenance for a non-resolving backlog revision. The correction was completed and independently accepted at feature HEAD `b0d4a1303d2a639e164a9b9fb103bb442d366f1d`; PR #15 was merged into `initial-idea` at `fa7683822c436f3e9d6c3455a24cd1f4a6cbb463`. See the [PM6C-F01 provenance correction report](../evidence/M6C-F01-provenance-correction-20261031.md), its [machine-readable audit](../evidence/M6C-F01-provenance-audit-20261031.json), and `scripts/audit_m6_closeout_provenance.py`. This historical correction did not reopen M6 acceptance, run ALE, alter M6 artifacts, approve G4, or authorize M7.

## Historical pre-acceptance M6 handoff — before PR #14 merge

The dated M6 execution and corrective reports preserve their point-in-time pending-review wording. They are superseded for current governance by the PM acceptance record above; their historical results and limitations remain unchanged.

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

## Final consolidation review pointer — 2026-11-02

The owner-authorized final housekeeping/integration task is documented in the [consolidation audit](../evidence/FINAL-CONSOLIDATION-audit-20261102.md) and [verification ledger](../evidence/FINAL-CONSOLIDATION-verification-20261102.md). It does not reopen M0–M7 or authorize a campaign/release. Exact final feature HEAD, clean-clone results, and CI belong to its separate main-target PR handover; the executor must leave that PR open and unmerged.

## Independent improvement campaign recovery pointer

Read `improvement_campaign` in [canonical project state](PROJECT_STATE.yaml)
and the [Phase 1 handoff](../../docs/improvement/PHASE1_HANDOFF.md). Its direct
owner authorization and separation from historical M0–M7 are recorded in
[ADR-0005](../../docs/02-management/decisions/ADR-0005-independent-improvement-campaign.md).
This is a pointer, not a competing campaign status or Phase 2 authorization.

## Improvement campaign Phase 2 execution pointer — 2026-11-03

The Project Owner directly authorized Phase 2 and the Independent PM accepted the Phase 1 handoff. Current pre-run authorization and config/code identities are in `PROJECT_STATE.yaml`; full local artifact verification and deadline budgeting are in `../../.agents/evidence/improvement/phase2-pre-run-freeze.json`. The feature branch remains the Phase 1 branch. The single official attempt `attempt-0000` started at 2026-11-03T02:55:57.782730Z from revision `76c898ed0dd8a2e8bf0c76cbd8565f83077284e0`; do not start another training campaign. Follow the Phase 2 assignment; preserve private artifacts locally and leave any final consolidation PR open and unmerged.

## PR #24 remediation (2026-11-03)

The PM-requested remediation is complete on the existing feature branch. See
`docs/improvement/PM24_REMEDIATION.md` for findings, evidence, and the remaining
owner/PM integration-history decision. The official training run and all
accepted scientific results are immutable. No merge or history rewrite is
authorized. Current verification evidence is under
`.agents/evidence/improvement/phase2-remediation-verification.json`. The remaining
owner/PM decision is the integration method for the already-published branch history.
