# M7 G5 Delivery Review Handover

**Review scope:** M7-004/M7-04 and M7-005/M7-05 delivery acceptance
**Review gate:** G5 — Delivery
**Engineering status:** M7-001 through M7-005 complete as engineering tasks on the submitted branch, subject to final PR verification recorded in the M7-005 acceptance evidence
**PM status:** G4 approved with scientific limitations; M7-04 accepted as delivery engineering evidence; G5 pending Independent PM decision
**Owner release decision:** **NO RELEASE / NO PUBLICATION AUTHORIZED**

## A. Executive verdict

The engineering package is prepared for independent G5 review. The owner has authorized M7-005 engineering and has expressly decided that no model, dataset, ROM, raw record, private artifact, deployment, or release package may be published or distributed. No release is part of this PR. M7 engineering completion does not constitute G5 approval. The verification qualification inherited from M7-004 remains visible: the unfiltered clean-clone suite had one environment failure because Stockfish was unavailable; it is not represented as passing.

## B. Acceptance mapping

| Criterion | Responsible gate | Evidence | Engineering status | PM status |
|---|---|---|---|---|
| M7-01 | G4 | [M7-001 acceptance](M7-001-acceptance-20261101.md) | Done | Accepted within the bounded G4 decision |
| M7-02 | G4 | [M7-002 acceptance](M7-002-acceptance-20261101.md), [raw-derived analysis](M7-analysis-final-r2-20261101/M7_ANALYSIS.md) | Done | Accepted within the bounded G4 decision |
| M7-03 | G4 | [M7-003 acceptance](M7-003-acceptance-20261101.md) | Done; Elo not reported | Accepted as non-reportability |
| M7-04 | G5 | [M7-004 acceptance](M7-004-acceptance-20261101.md), [PR #19](https://github.com/dodaonam/atari-videochess-rl/pull/19) | Done | M7-04 engineering evidence accepted by Independent PM; PR #19 merged. This is not G5 approval. |
| M7-05 | G5 | [Owner no-release decision](M7-005-owner-no-release-decision-20261101.md), [release disposition](../../docs/07-delivery/RELEASE_DISPOSITION.md), [M7-005 acceptance](M7-005-acceptance-20261101.md) | Engineering complete with the verified no-release disposition and acceptance record | Pending Independent PM G5 decision |

The G4 source decision is in [the canonical G4 acceptance record](G4-PM-acceptance-20261101.md) and the [PR #17 comment](https://github.com/dodaonam/atari-videochess-rl/pull/17#issuecomment-6552570969). M7-04's bounded PM acceptance is the [PR #19 review comment](https://github.com/dodaonam/atari-videochess-rl/pull/19#issuecomment-6553580590); it explicitly says **not G5 approval**. PR #19 was merged at `0f45fa06c235658da48d3d41a9091c06580bfe27`; its reviewed source was `05a94ef096da9bc0467970e0ea8ec1dc88d953e3`.

## C. Scientific boundaries carried forward

The G5 handover preserves the accepted M7 Option B record without changing its analysis:

- 90/90 scheduled attempts started and reset-observed.
- 60 terminal White losses, 30 incomplete attempts, zero wins and zero draws.
- Incomplete attempts are not draws or terminal losses.
- The Warm-20261105 policy has zero terminal games; its terminal-only score is undefined.
- Only 9/30 Warm/Scratch matched cells have terminal observations; a valid paired interval was unavailable.
- No RL superiority, equivalence, broad generalization, or calibrated Elo is established.
- O-02 remains unresolved; no certain academic pass is claimed.
- RSK-014 and PM6-F06 remain disclosed.
- Single built-in opponent, White-only ALE evaluation, censoring, controller/runtime limits, and owner-local raw evidence remain limitations.

The M4 imitation, M5 simulator, M6 v1, M6 v2, and M7 ALE tracks remain separate. The no-release disposition does not alter model selection, metrics, or research conclusions.

## D. Release and privacy disposition

The authoritative owner decision and itemized distribution table are in [RELEASE_DISPOSITION.md](../../docs/07-delivery/RELEASE_DISPOSITION.md). ROM, M3 source and teacher data, M4/M5 checkpoints, M5 raw training/simulator records, M6 v1/v2 raw ALE records, M7 raw ALE/RGB records, and private manifests/payloads remain owner-controlled and are not included in this PR. M3 third-party redistribution terms and broader rights remain unverified. A hash does not grant access or redistribution rights.

Previously committed source, sanitized reports, configurations, hashes, and accepted evidence remain in the repository under its existing visibility. The task does not retroactively unpublish them. No new license is supplied, no external upload is authorized, and no public release/deployment was created.

## E. Verification and known limitations

The [M7-005 acceptance record](M7-005-acceptance-20261101.md) links the exact commands, timestamps, source revisions, exit codes, sanitized logs, privacy inspection, and clean-clone result for the initial PR submission. At candidate commit `007d52397e68b9cadce71f6cc833317d9667dc4c`, the clean-clone full suite ran 509 tests with one unavailable-Stockfish readiness failure and three skips; excluding exactly that test yielded 508 tests, three skips, and zero failures/errors. At the later evidence-only candidate `5503ba83e8141ee0df26daffd491e745edf6cf69`, clean-clone preflight passed with the expected artifact-manifest warning and the focused suite passed 82 tests. These are historical engineering verification results, not G5 acceptance. The original note that exact-PR CI remained pending is superseded by the code-bearing check recorded in §H; the amended PR's live exact HEAD and check must still be verified by the PM.

The read-only GitHub branch-protection query for `initial-idea` returned HTTP 404 (“Branch not protected”); no branch protections or rulesets were changed. The PR therefore still requires explicit Independent PM review and an authorized operator's integration action under the repository review policy.

Inherited M7-004 results remain: the focused delivery/manifest/governance tests passed 24 tests; clean-clone preflight passed with the expected `ARTIFACT_MANIFEST_REQUIRED` warning; the unfiltered clean-clone suite ran 505 tests, with one failure in `test_m0_smoke.M0EnvironmentSmokeTests.test_stockfish_answers_uci_readiness_without_searching` because no Stockfish executable was available, and three skips. Excluding exactly that unavailable test yielded 504 executed, three skipped, zero failures/errors. This exclusion is not reported as an unfiltered pass. GitHub Actions run 41274320489 passed on the exact M7-004 reviewed HEAD, but it was a repository-preflight/context suite, not the full repository suite.

## F. Open decisions

- **O-02:** whether full-game ALE performance is a hard submission requirement or a research target with an accepted fallback.
- **O-03:** future course checkpoints/date changes beyond the owner-confirmed 2026-11-03 presentation date.
- **O-04:** external compute/storage entitlements and permissions; this task uses no external compute or storage.
- **O-05:** ALE/ROM behavior and evaluation-setting semantics beyond verified runtime evidence.
- **O-06:** broader redistribution rights; the M3 source package's third-party license remains unstated/unverified.
- **O-07:** Stockfish use outside the previously authorized bounded M3 teacher-label scope.
- **O-08:** opponent pool and rating method for any future Elo claim.

RSK-014 remains the accepted M5 source-provenance limitation. PM6-F06 remains the M6 v2 metadata erratum. None is closed or changed by this delivery record.

## G. Independent PM review request

Please review the actual M7-005 PR diff and exact final HEAD; verify the direct owner authorization and no-release decision provenance; check the artifact-category inventory, existing-content distinction, rights/unknowns, and privacy boundary; verify M7-05 evidence and links; confirm M7-004 PM acceptance is not misrepresented as G5 approval; inspect the actual current and inherited test limitations; and confirm canonical state/backlog keep M7-001–M7-005 engineering statuses accurate, G4 approved, G5 pending, and no release authorized. Record an explicit G5 decision. Do not infer G5 approval or release permission from this handover, PR readiness, or CI.

## H. G5-F01 provenance remediation supplement — 2026-11-01

The first PR #20 review at HEAD `f3ef2976f446594dca6e4b6d5d219734cc33f966` returned **REQUEST CHANGES / G5 HOLD** for G5-F01. The M3 release-disposition inventory mixed the historical corrective r4/r5 release ID with the accepted final r6/r7 manifest hash and omitted the accepted final teacher-r1 binding. The PM finding concerns delivery-document provenance; it does not indicate that accepted M3 source artifacts or scientific results were incorrect.

The amended inventory now lists four distinct M3 entries: accepted final dataset r6/r7; historical corrective dataset r4/r5; accepted final teacher-r1; and historical corrective teacher-r2. The final and historical dataset/teacher bindings are checked against structured closure, repeat, and teacher-manifest records. `HANDOVER.md` now labels the accepted final release as final and separates historical corrective identities. Detailed sources, corrections, and test logs are in the [G5-F01 remediation record](M7-005-G5-F01-remediation-20261101.md).

At code-bearing commit `0d3ee8221698f52bf2c7658657e505900ab5485d`, clean-clone preflight and the focused 86-test suite passed. The unfiltered 513-test suite reported one unavailable-Stockfish readiness failure and three skips; it is not called a passing full suite. Excluding only that exact test yielded 512 tests, three skips, and zero failures. GitHub Actions `Repository preflight` passed on that revision; it is a context/preflight check, not the full local test suite. The PM must verify the live amended PR HEAD and its own CI before deciding G5.

G5 remains **NOT APPROVED pending Independent PM re-review**. The Project Owner's **NO RELEASE / NO PUBLICATION AUTHORIZED** decision is unchanged. This supplement records no approval and does not authorize merge or distribution.

A clean clone at `545c95589b078f5249951d3d869b4eb42fb0f96a` also passed preflight and the 86-test focused suite after the acceptance/handover corrections. The full suite results remain those at code-bearing `0d3ee822…`, with the one unavailable-Stockfish failure and the exact single-test filtered pass. Both code-bearing and final-document checks, plus logs, are mapped in the [G5-F01 remediation evidence](M7-005-G5-F01-remediation-20261101.md). Please verify the live amended PR HEAD and its own CI before deciding G5.
