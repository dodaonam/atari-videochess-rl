# G5-F02 Remediation and M0–M7 Final Closure Evidence

**Finding:** G5-F02 — unsupported attribution of a Project Owner no-release prohibition
**Independent PM source:** [PR #21 comment 6557663143](https://github.com/dodaonam/atari-videochess-rl/pull/21#issuecomment-6557663143)
**Reviewed PR #21 HEAD:** `fc51b724d6a812ec648aaeb3ba26b8371b8d1989`
**Base branch / integrated baseline:** `initial-idea` at `0b9c4c26ee1d0952a5f9e3b7cd405f5bf4e3008b`
**Current work branch:** `feature/g5-governance-closeout`
**Current decision:** G5 is not approved pending fresh Independent PM review. This is an engineering remediation record, not a PM disposition.

## Finding and root cause

The earlier M7-005 package described **“NO RELEASE / NO PUBLICATION AUTHORIZED”** as an explicit owner decision. The records cited a direct instruction in a Codex session but did not provide an independently verifiable primary-source locator. The latest PM review records the owner's dispute and states that executor-authored summaries are insufficient to establish that prohibition. The defect was an evidence-attribution and governance-state error; it does not invalidate accepted M7 measurements or change the artifact bytes.

The [dated provenance erratum](G5-F02-provenance-erratum-20261101.md) inventories the affected statements, explains the evidence gap, distinguishes the later authenticated owner research-scope instruction from release authorization, and preserves the original historical records with status notices.

## Corrected authorization status

- No affirmative owner authorization to distribute restricted models, checkpoints, datasets, ROM, raw records, manifests, RGB, or other private artifacts is established in the reviewed evidence.
- No independently verifiable blanket owner prohibition is established; the prior attribution is unverified.
- The current Project Owner instruction says accepted research results are final, authorizes no further research campaign or milestone, and does not authorize publication. It does not create a blanket release prohibition.
- No release, deployment, publication, or private-artifact upload is part of this remediation. Repository release/tag/deployment checks are recorded in the sanitized verification logs.
- The distinction is explicit in the [machine-readable status](G5-F02-provenance-status-20261101.json), [corrected M7-005 assessment](M7-005-corrected-disposition-assessment-20261101.md), and [release-disposition inventory](../../docs/07-delivery/RELEASE_DISPOSITION.md).

## Owner final research-scope decision

The Project Owner has recorded that the currently accepted M0–M7 research results are final, including negative and inconclusive findings. No further model training, fine-tuning, simulator/ALE campaign, training seed, opponent/Elo campaign, model-selection campaign, or new milestone is authorized. This does not establish strong chess performance, external course approval, or publication rights. Provenance and scope are recorded in the [owner decision](PROJECT-OWNER-final-research-scope-decision-20261101.md).

## M0–M7 audit and scientific integrity

The [final project closure matrix](M0-M7-final-project-closure-20261101.md) maps M0–M7 criteria to existing accepted evidence and distinguishes engineering completion, PM acceptance, and current G5 review. It classifies O-01–O-08, preserves RSK-014 and PM6-F06, and links the final artifact/reproducibility inventory.

Accepted M7 outcomes are reconstructed from the committed M7 analysis: 90 scheduled and started/reset-observed attempts, 60 terminal White losses, 30 incomplete attempts, zero wins, zero draws, and 9/30 Warm/Scratch matched cells with terminal outcomes. No paired interval was available. Incomplete attempts remain distinct from terminal outcomes. No experimental result, run identity, configuration, checkpoint, raw artifact, or scientific conclusion was changed.

M7-04 delivery acceptance remains intact. G5-F01's M3 final/historical identity repair and regression tests remain intact. The prior G5 PM decision is preserved as a historical decision, but its M7-05 premise is suspended pending fresh review under the latest PM finding. Current proposed canonical state excludes G5 from approved gates and marks G5 ready for review; it does not claim PM acceptance.

## Changed-file groups

- Added the owner final-research decision, G5-F02 erratum and machine status, corrected M7-005 assessment, and M0–M7 closure matrix.
- Corrected current release-status text in `RELEASE_DISPOSITION.md`, `FINAL_REPORT.md`, `MODEL_CARD.md`, `USER_GUIDE.md`, and `HANDOVER.md`.
- Added dated status notices to historical owner, M7-005, G4/G5 decision, and review-handover records; original text remains present for auditability.
- Updated canonical state, backlog, session handoff, blocker summary, verified findings, and the ADR-0004 current-status supplement.
- Added `tests/test_g5_final_closeout.py`; updated governance, M7 delivery, M3 release-provenance, and context tests to distinguish an owner instruction, an executor attribution, absent affirmative permission, an explicit prohibition, and a publication authorization.
- Added sanitized test and verification logs. No research source code or experimental artifact path was changed.

## Verification history

| Check | Source / environment | Result | Evidence |
|---|---|---|---|
| First focused governance/delivery run | Worktree based on `fc51b724d6a812ec648aaeb3ba26b8371b8d1989`; system Python; 2026-11-01 12:31 UTC | 89 tests, 17 assertion failures. Failures were stale G5/no-release expectations, test wording that overreached the direct research-scope wording, and an evidence metadata edit that did not preserve the historical PM verification provenance. Assertions and the metadata were corrected; the failure is retained. | [Sanitized initial failure log](logs/G5-F02-focused-tests-initial-20261101.log) |
| Focused G5/context/delivery suite after remediation | Existing project Python environment; worktree source baseline `fc51b724d6a812ec648aaeb3ba26b8371b8d1989`; 2026-11-01 12:35 UTC | **89 passed, zero failures**, exit 0. | [Focused pass log](logs/G5-F02-focused-tests-pass-r2-20261101.log) |
| First full-suite diagnostic with system Python | Worktree baseline `fc51b724d6a812ec648aaeb3ba26b8371b8d1989`; `/usr/bin/python3`; 2026-11-01 12:37 UTC | **232 tests discovered, 43 import errors**, exit 1 because system Python lacked `chess`, NumPy, and other project dependencies. This was an unsupported interpreter run, not represented as a code pass/failure. No package was installed. | [Sanitized system-Python diagnostic log](logs/G5-F02-full-suite-unfiltered-20261101.log) |
| Full suite in the pre-existing project environment | Worktree baseline `fc51b724d6a812ec648aaeb3ba26b8371b8d1989`; existing Python 3.12.3 environment; 2026-11-01 12:39 UTC | **522 tests, zero failures, three skips**, exit 0. The skips require private M4/M5 artifacts absent from this worktree. The Stockfish UCI readiness test passed using the already-existing project environment executable. No new environment or dependency was installed. | [Full-suite supported-environment log](logs/G5-F02-full-suite-supported-env-precommit-20261101.log) |
| Final focused rerun before checkpoint refresh | Candidate worktree at baseline `fc51b724d6a812ec648aaeb3ba26b8371b8d1989`; 2026-11-01 12:45 UTC | **90 tests, two failures**, exit 1. One failure correctly detected that an unnecessary status banner had changed the hash-pinned G4 acceptance source; the second detected that repository context had changed since the last checkpoint. The immutable G4 file was restored byte-for-byte and the checkpoint will be refreshed after staging the final candidate. Both failures are preserved. | [Focused failure and remediation log](logs/G5-F02-focused-final-precommit-20261101.log) |
| Focused governance/delivery/context rerun after immutable-file restoration and checkpoint | Candidate worktree based on `fc51b724d6a812ec648aaeb3ba26b8371b8d1989`; 2026-11-01 12:50:19 UTC | **91 tests passed, zero failures**, exit 0. This includes the G5-F02 authorization distinctions, hash-pinned G4 record, M3 provenance pairs, M7 metrics, delivery links, canonical state, and context recovery contracts. | [Focused remediation pass log](logs/G5-F02-focused-remediated-r3-20261101.log) |
| Initial staged diff whitespace check | Candidate worktree based on `fc51b724d6a812ec648aaeb3ba26b8371b8d1989`; 2026-11-01 12:54:05 UTC | Exit 2 because a retained unit-test transcript had one trailing space on line 7. The exact failure is preserved. The transcript was sanitized by trimming trailing whitespace only; test output and assertions were not changed. | [Diff-check failure log](logs/G5-F02-diff-check-initial-failure-20261101.log) |
| Diff-check retry and wrapper correction | Same candidate; 2026-11-01 12:54:19–12:54:30 UTC | The retry still returned exit 2 because the sanitized failure log had not yet been restaged. Its first wrapper incorrectly printed a pass label without checking the result; the correction is appended to that retained wrapper log. The next checked run passed. | [Incorrect wrapper/correction record](logs/G5-F02-diff-check-wrapper-failure-20261101.log); [second failed check](logs/G5-F02-diff-check-second-failure-20261101.log) |
| Final staged diff whitespace check | Same candidate; 2026-11-01 12:54:39 UTC | **PASS**, no staged whitespace errors; exit 0 after the sanitized transcripts were restaged. | [Diff-check pass log](logs/G5-F02-diff-check-pass-r3-20261101.log) |
| Pre-push privacy/payload scan | Candidate worktree at base `fc51b724d6a812ec648aaeb3ba26b8371b8d1989`; 2026-11-01 12:55:19 UTC | **PASS**, 10,814 added tracked lines reviewed, 56 text/log items considered by the scanner, zero concrete path/credential matches, zero restricted payload suffixes; exit 0. | [Privacy scan log](logs/G5-F02-privacy-audit-final-20261101.log) |
| Canonical checkpoint and preflight | Worktree baseline `fc51b724d6a812ec648aaeb3ba26b8371b8d1989`; final staged check at 2026-11-01 12:53 UTC | Checkpoint script reported preflight PASS, and the subsequent direct preflight exited 0. `WORKTREE_CONTENT_DRIFT` in the direct preflight was caused by the newly retained preflight log itself and will be cleared by the final checkpoint; `ARTIFACT_MANIFEST_REQUIRED` for local `artifacts/` remains expected. | [Checkpoint run log](logs/G5-F02-checkpoint-r2-20261101.log); [preflight transcript](logs/G5-F02-precommit-final-preflight-20261101.log) |

The initial assertion failures were caused by test expectations and stale provenance metadata, not scientific evidence or production behavior. No source data, protocol, run, metric, model, or artifact was changed to make tests pass.

## Current PM boundary and requested action

The engineering correction is submitted for Independent PM re-review through PR #21. The PM must decide whether the corrected M7-05 evidence satisfies G5, verify the G5-F02 chronology and canonical state, and record an actual G5 disposition. **G5 remains not approved until that decision.** No release/publication permission is established; this record asserts no blanket owner prohibition.

Final clean-clone verification, privacy scan, exact PR HEAD, CI, and task-state provenance will be added after those checks complete. Until then, this record is an in-progress remediation log and does not claim final acceptance.
