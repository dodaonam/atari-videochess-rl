# M0–M7 Final Engineering Closure and Independent PM Handover

**Recorded:** 2026-11-01
**Project Owner scope decision:** Existing accepted research results are final; no further research campaigns or milestone are authorized.
**Engineering disposition:** M0–M7 engineering scope complete; final governance package submitted for Independent PM review.
**Current G5:** Not approved pending fresh review of G5-F02 remediation and M7-05 evidence.
**Release status:** No affirmative authorization for restricted artifact publication is established; no release is part of this closeout. The earlier blanket-owner-prohibition attribution is unverified.

## Project closure summary

The project implemented a reproducible local foundation, ALE feasibility/control, a chess simulator and non-learning baselines, a bounded expert-data/teacher pipeline, supervised behavior cloning, custom Double DQN simulator training, Atari integration, and a preregistered Option B ALE evaluation with analysis and delivery documentation. The accepted research evidence is now final by direct Project Owner scope instruction. This is a research-scope closure, not a claim of strong playing performance, course approval, unrestricted artifact rights, or a positive RL result.

M7's accepted Option B run scheduled 90 policy × seed attempts; 90 started and were reset-observed, 60 ended in terminal White losses, 30 remained incomplete, and zero wins or draws were observed. Only 9/30 Warm/Scratch matched cells had terminal outcomes and no valid paired confidence interval was available. The findings do not establish RL superiority, Warm-start superiority, equivalence, broad generalization, reliable simulator-to-Atari transfer, calibrated Elo, or satisfaction of external course requirements.

## Final engineering acceptance matrix

“Engineering complete” is distinct from gate approval. Historical criteria are mapped to their controlling acceptance evidence; this matrix does not retroactively re-run private experiments.

| Milestone / criterion | Engineering status | Authoritative acceptance evidence | Governance / limitation |
|---|---|---|---|
| M0-01–M0-04 | Accepted and complete | [M0 user acceptance](M0-acceptance.md), [final technical verification](M0-final-technical-verification.md), [finalization verification](M0-finalization-verification.md) | G0/G1 history; environment facts are scoped to their recorded time. |
| M1-01–M1-06 | Accepted and complete | [M1/G2 final verification](M1-G2-final-verification-20261016.md), [terminal verification](M1-04-terminal-verification.md), M1 artifact manifest and retained sanitized logs | G2 approved; terminal board final state and untested profiles remain explicitly limited. |
| M2-01–M2-04 | Accepted and integrated | [M2 acceptance](M2-acceptance-20261016.md), [post-M2 integration verification](POST-M2-INTEGRATION-VERIFICATION-20261017.md) | Simulator metrics remain separate from ALE. |
| M3-01–M3-04 | Accepted and integrated | [M3 acceptance](M3-acceptance-20261021.md), [final closure report](M3-final-closure-20261021.md), [machine-readable final closure](M3-final-closure-record-20261021.json) | Final r6/r7 and teacher identities remain paired; source package license remains unverified under O-06. G5-F01 repair is preserved. |
| M4-01–M4-04 | Accepted and integrated | [M4 final acceptance](M4-final-acceptance-20261027.md), [post-merge delivery verification](M4-postmerge-delivery-verification-20261027.md) | Imitation accuracy is not game score, RL performance, or Elo. |
| M5-01–M5-05 | PM accepted with limitations and integrated | [M5 PM acceptance](M5-PM-acceptance-20261030.md), [M5 final report](../../docs/04-research/M5_FINAL_REPORT.md), accepted campaign/evaluation verification records | Simulator-only results; three training-seed pairs and RSK-014 source-history limitation remain. |
| M6-01–M6-05 | PM accepted with qualifications and integrated | [M6 PM acceptance](M6-001-PM-acceptance-20261031.md), [M6 final corrective closeout](M6-final-corrective-closeout-20261031.md), [PM6-F06 erratum](M6-PM6-F06-erratum-20261031.md) | Stage 3 v1 and v2 remain distinct; raw artifact access and private replay limits remain. |
| M7-01 | Engineering complete; G4 accepted with scientific limitations | [M7-001 acceptance](M7-001-acceptance-20261101.md), [G4 PM acceptance](G4-PM-acceptance-20261101.md) | Exact 90-cell Option B schedule and outcomes are preserved. |
| M7-02 | Engineering complete; G4 accepted with scientific limitations | [M7-002 acceptance](M7-002-acceptance-20261101.md), [final raw-derived analysis](M7-analysis-final-r2-20261101/M7_ANALYSIS.md), machine-readable analysis and manifest | Censoring, seed dependence, and unavailable paired uncertainty remain. |
| M7-03 | Engineering complete; G4 accepted | [M7-003 acceptance](M7-003-acceptance-20261101.md) | Elo not reported; no calibrated pool or design was approved/available. |
| M7-04 | Engineering complete and independently accepted | [M7-004 acceptance](M7-004-acceptance-20261101.md), [PR #19 PM decision](https://github.com/dodaonam/atari-videochess-rl/pull/19#issuecomment-6553580590), PR #19 merge | The accepted environment-verification qualification remains. G5-F02 does not reopen M7-04. |
| M7-05 | Engineering evidence complete; fresh PM review required | [corrected disposition assessment](M7-005-corrected-disposition-assessment-20261101.md), [G5-F02 erratum](G5-F02-provenance-erratum-20261101.md), [release inventory](../../docs/07-delivery/RELEASE_DISPOSITION.md) | Prior owner-prohibition attribution is unverified; no affirmative restricted-artifact release authorization is established. G5 is not approved pending fresh PM decision. |

## Governance chronology and live boundary

- G0/G1: user approved; foundational acceptance records remain authoritative.
- G2: user-approved after M1 feasibility evidence.
- G3: Independent PM approved after M2–M5 review and PR #11 integration; see [G3 final approval](G3-final-approval-20261030.md).
- G4: Independent PM approved with scientific limitations for M7-01–M7-03; see [G4 PM acceptance](G4-PM-acceptance-20261101.md).
- G5: An earlier PM approval was recorded after PR #20. The later PM finding [G5-F02](https://github.com/dodaonam/atari-videochess-rl/pull/21#issuecomment-6557663143) suspends reliance on its M7-05 owner-release premise and rejects the canonical closeout at PR #21 HEAD `fc51b724d6a812ec648aaeb3ba26b8371b8d1989`. M7-04 acceptance and G5-F01 resolution remain valid. The proposed state on the amended PR records G5 as ready for fresh review, not approved.
- PR #21 remains open and unmerged until the Independent PM reviews the amended exact HEAD and decides the G5/M7-05 status.

## Project Owner final research-scope decision

The direct owner instruction says the currently accepted research/experimental results are final and no additional research campaigns, training, or new milestone are authorized. It preserves the negative/inconclusive findings and does not authorize publication. The instruction is recorded from this execution context; no separate public issue, signature, or exact timestamp was provided. See [the decision record](PROJECT-OWNER-final-research-scope-decision-20261101.md).

## Final requirements disposition

| Requirement | Closeout classification | Status |
|---|---|---|
| O-01 — internal project use of the selected custom PyTorch RL / behavior-cloning scope | Closed for internal project planning and execution by the prior owner decision; no instructor approval is claimed | Historical owner decision remains in effect for completed scope; do not infer external course permission. |
| O-02 — full-game ALE hard requirement vs target/fallback | External course requirement unverified; retained limitation | Open; M7 results do not prove full-game performance. |
| O-03 — future course checkpoints/date changes | Current presentation date was owner-confirmed; any further course schedule remains external | No further research execution is authorized; do not infer grading acceptance. |
| O-04 — external compute/storage entitlement and paid-resource policy | External entitlement not required or used for this final closeout | Unverified outside historical local CPU runs; no further allocation authorized. |
| O-05 — ALE/ROM behavior and official settings | Partially characterized by M1/M6/M7 runtime evidence; broader course/runtime semantics remain external/unverified | Residual limitation. |
| O-06 — public redistribution rights | M3 package rights remain unstated/unverified; ROM and private payload rights remain artifact-specific | No affirmative publication authorization established; rights unresolved. |
| O-07 — Stockfish roles beyond accepted M3 labeling | No new engine use requested; broader benchmark/opponent/instructor constraints remain open | Outside closed research scope. |
| O-08 — calibrated opponent pool and Elo method | No approved calibrated pool/design; Elo not reportable | No rating claimed; no new campaign authorized. |

RSK-014 and PM6-F06 remain disclosed. No course, instructor, or third-party approval is fabricated.

## Final artifact inventory and reproducibility

The linked acceptance evidence and [M7 evidence inventory](M7-004-evidence-inventory-20261101.json) identify accepted run IDs, configurations, checkpoint hashes, and manifests. The [release disposition](../../docs/07-delivery/RELEASE_DISPOSITION.md) distinguishes sanitized Git content from owner-controlled local datasets, checkpoints, ROM, raw training/evaluation records, RGB, and private payloads. M3/M4/M5/M6/M7 raw artifacts remain outside Git where specified; access and re-verification require the Project Owner's permitted local artifacts. Hashes establish identity, not distribution rights.

For repository-only setup and safe checks, use the [User Guide](../../docs/07-delivery/USER_GUIDE.md), [Setup](../../docs/05-operations/SETUP.md), and project lock/commands. Private artifact verification requires authorized inputs and must remain read-only. Re-running historical training or evaluation is outside final scope and is not required for ordinary checkout verification.

## Verification and integrity boundary

At clean-clone source revision `2a26ce76c95eedfa216d31d482f6c0fd942e7fd5`, `python3 scripts/agent_preflight.py` passed with the expected `ARTIFACT_MANIFEST_REQUIRED` warning; the 91-test focused governance/delivery/context suite passed; and the unfiltered repository suite passed **524 tests with three private M4/M5 artifact skips and zero failures**. Stockfish UCI readiness passed using the existing Python 3.12.3 project environment; no packages were installed. Commands, UTC timestamps, source revision, exit codes, and sanitized logs are in the [G5-F02 remediation evidence](G5-F02-remediation-20261101.md). A first privacy scan invocation failed because the single-branch clean clone lacked an `origin/initial-idea` ref; after fetching that ref, both the repository content scan and an independent scan of all 22 checkpoint-history segments passed with no path/credential matches or restricted payload suffixes. The exact-head GitHub Actions run [41308813509](https://github.com/dodaonam/atari-videochess-rl/actions/runs/41308813509) completed successfully for `2a26ce76…`; it runs repository preflight/context checks, not the complete Python suite.

The same preflight, focused suite, and unfiltered full suite were rerun on PR HEAD `6504ecaea7b685d22fdb2d2effae4e0cb3588a78` after the clean-clone evidence update: preflight passed, 91 focused tests passed, and 524 full tests passed with three skips. Exact-HEAD GitHub Actions run [41309565210](https://github.com/dodaonam/atari-videochess-rl/actions/runs/41309565210) succeeded on that revision. The full suite used the already-existing project environment; no package or system dependency was installed. The final G5-F02 record separates these checks from earlier system-Python diagnostics and retains all failures/remediation chronology.

After C3 preflight found three C2 log links missing from the committed tree, C4 committed those logs. A fresh C4 clone passed preflight and all 91 focused governance/delivery/context tests; exact-head GitHub Actions run [41310316412](https://github.com/dodaonam/atari-videochess-rl/actions/runs/41310316412) succeeded. C4 changes only sanitized verification logs and checkpoint history; no application/test source or experimental evidence changed after the 524-test full-suite pass at C2.

C6's exact-head CI then detected a portable-checkpoint transition error caused by adding tracked verification logs without refreshing the checkpoint. C7 refreshed the canonical checkpoint; a fresh C7 clone passed preflight and 91 focused tests, and exact-head GitHub Actions run [41311026076](https://github.com/dodaonam/atari-videochess-rl/actions/runs/41311026076) succeeded. The C7 privacy scan checked 12,578 added tracked lines, 56 text/log items, and 29 compressed checkpoint segments without finding sensitive paths, credentials, or restricted payloads. The unfiltered full suite remains the 524-test C2 run; no application or test source changed after that full-suite run.

The path-level diff contains governance state, sanitized documentation/evidence, regression tests, and checkpoint history only. It contains no M3–M7 dataset, metric, raw trace, configuration, model checkpoint, experiment manifest, ROM, or accepted scientific conclusion. The exact candidate was checked for concrete paths, credentials, restricted payload suffixes, and compressed checkpoint contents; the results are in the [G5-F02 remediation record](G5-F02-remediation-20261101.md).

## Residual future work

No planned Codex engineering task or research campaign remains in the currently authorized scope. Optional future research, instructor clarification, licensing review, or a release proposal would require its own decision and authorization. Such possibilities are not active tasks. The current required external action is Independent PM review and disposition of G5-F02/M7-05 on amended PR #21, followed by the PM's own post-merge verification if accepted.
