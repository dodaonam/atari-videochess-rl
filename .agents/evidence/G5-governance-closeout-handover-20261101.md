# G5 Governance Closeout — Independent PM Handover

## A. Executive verdict

The Independent PM has approved G5 for M7-04 and M7-05 with scientific, environment-verification, and no-release limitations. G5-F01 is resolved. PR #20 was integrated at its exact approved revision. This branch records the authentic G5 decision in canonical state and proposes that state transition for review. The governance-closeout PR is not yet integrated and must receive a fresh Independent PM review.

**Owner disposition:** **NO RELEASE / NO PUBLICATION AUTHORIZED.** No release, upload, distribution, deployment, publication, or third-party access is authorized.

## B. Decision provenance

- Official source: [Independent PM final review, PR #20 comment 6556836388](https://github.com/dodaonam/atari-videochess-rl/pull/20#issuecomment-6556836388), created `2026-11-01T10:39:28Z`.
- Exact decision: **G5 APPROVED WITH SCIENTIFIC, ENVIRONMENT-VERIFICATION, AND NO-RELEASE LIMITATIONS** for M7-04/M7-05; G5-F01 resolved; PR #20 accepted for integration at the reviewed head.
- PR #20 approved head: `ec7ab8c0fe097004eb4d37018be898c68f41364b`.
- Reviewed base: `initial-idea` at `0f45fa06c235658da48d3d41a9091c06580bfe27`.
- The API identifies the comment account as `dodaonam` with OWNER association; the comment body identifies the decision as the Independent PM final review. We make no claim about a distinct account identity.
- Formal record: [G5-PM acceptance](G5-PM-acceptance-20261101.md) and [machine-readable decision](G5-PM-acceptance-20261101.json).

## C. PR #20 integration provenance

- PR: [#20](https://github.com/dodaonam/atari-videochess-rl/pull/20), base `initial-idea`.
- Source head: `ec7ab8c0fe097004eb4d37018be898c68f41364b` (the exact PM-approved revision).
- Previous integration baseline: `0f45fa06c235658da48d3d41a9091c06580bfe27`.
- Merge method: merge commit, consistent with PR #19.
- Actual merge commit: `0b9c4c26ee1d0952a5f9e3b7cd405f5bf4e3008b`, reported by GitHub at `2026-11-01T10:47:15Z`.
- Verified parents: the prior integration baseline and the exact reviewed PR head. The approved head is an ancestor of the fetched `origin/initial-idea` at the merge commit.
- Verification: [source comment log](logs/G5-source-verification-20261101.log) and [PR #20 integration log](logs/G5-pr20-integration-verification-20261101.log).
- The one-time direct Project Owner authorization and its scope are recorded in [G5-PR20 integration authorization](G5-PR20-integration-authorization-20261101.md). It grants no standing Codex merge authority. The separate closeout PR remains unmerged.

## D. Acceptance mapping

| Criterion | Gate | Evidence | Engineering status | PM status |
|---|---|---|---|---|
| M7-01 | G4 | M7-001 acceptance and G4 PM record | Done | Accepted with scientific limitations |
| M7-02 | G4 | M7-002 acceptance and analysis bundle | Done | Accepted with scientific limitations |
| M7-03 | G4 | M7-003 acceptance | Done; Elo not reported | Accepted as non-reportability |
| M7-04 | G5 | [M7-004 acceptance](M7-004-acceptance-20261101.md), four delivery documents, PR #19 and G5 decision | Done | Accepted |
| M7-05 | G5 | [Owner no-release decision](M7-005-owner-no-release-decision-20261101.md), [release inventory](../../docs/07-delivery/RELEASE_DISPOSITION.md), [M7-005 acceptance](M7-005-acceptance-20261101.md), and PR #20 | Done as explicit no-release disposition | Accepted; no publication required or authorized |

## E. Scientific limitations preserved

- M7 recorded 90 scheduled and started/reset-observed attempts: 60 terminal White losses, 30 incomplete, zero wins, and zero draws. Incomplete attempts remain distinct from terminal outcomes.
- Only 9/30 Warm/Scratch matched cells had terminal observations; a valid paired confidence interval was unavailable.
- No RL superiority, equivalence, or broad generalization is established. No calibrated Elo was reported.
- O-02 and O-06 remain unresolved. RSK-014 and PM6-F06 remain disclosed. M5 and M6 limitations remain unchanged.
- M4, M5, M6 v1, M6 v2, and M7 remain separate evidence tracks. No accepted M3–M7 data, metrics, configurations, checkpoints, manifests, or scientific conclusions changed.

## F. Environment-verification limitations

- **Previously accepted PR #20 verification:** unfiltered clean-clone suite 513 tests, one unavailable-Stockfish UCI-readiness failure, and three skips; the unfiltered suite did not pass. Excluding exactly that test yielded 512 tests, three skips, and zero failures/errors. The focused suite passed 86 tests; three private-artifact tests were skipped. The exact approved head's GitHub run [41297779574](https://github.com/dodaonam/atari-videochess-rl/actions/runs/41297779574) passed `Repository preflight` / `context`, not the full Python suite.
- **Governance-closeout working tree based on merge commit `0b9c4c2`:** the focused contracts passed **89/89** after the final provenance-parent assertion at `2026-11-01T11:07:02Z`; see [final focused log](logs/G5-governance-focused-tests-final-20261101.log). The unfiltered suite ran **516 tests**, failed only `test_m0_smoke.M0EnvironmentSmokeTests.test_stockfish_answers_uci_readiness_without_searching` because Stockfish was unavailable, and skipped three private-artifact tests; this is not a passing full suite. See [unfiltered log](logs/G5-governance-full-suite-unfiltered-20261101.log). Excluding exactly that single test with the existing ID-checking runner yielded **515 tests, three skips, zero failures**; see [filtered log](logs/G5-governance-full-suite-filtered-20261101.log). The unfiltered and filtered runs preceded only the final one-line assertion that the recorded merge parents match the accepted base/head; the final focused run included that assertion. A clean-clone full-suite run on the candidate revision is still required.
- **Fresh clean clone at candidate `7a8d1d066f4bcb0c52807a82cc57a32b16326de7`:** before tests, the clone had zero working-tree changes and `videochess_rl` imported from the clone itself. No private artifacts were copied and no dependencies were installed. Clean-clone preflight passed with only `ARTIFACT_MANIFEST_REQUIRED`; see [clean-clone preflight log](logs/G5-governance-clean-clone-preflight-20261101.log). The focused suite passed **89/89**; see [focused log](logs/G5-governance-clean-clone-focused-20261101.log). The unfiltered full suite ran **516 tests**, with one unavailable-Stockfish UCI-readiness failure and three private-artifact skips; see [unfiltered log](logs/G5-governance-clean-clone-full-unfiltered-20261101.log). The unfiltered suite did not pass. Excluding only the exact Stockfish test yielded **515 tests, three skips, zero failures**; see [filtered log](logs/G5-governance-clean-clone-full-filtered-20261101.log). These clean-clone results were run on the committed candidate before adding the retained clean-clone logs and the final PR handover metadata; code/test changes after it are not intended, and final HEAD verification remains required after those evidence-only commits.
- The working-tree `python3 scripts/agent_preflight.py` passed at `2026-11-01T11:10:58Z` with warnings for the uncommitted closeout files and `ARTIFACT_MANIFEST_REQUIRED`; see the [working-tree preflight log](logs/G5-governance-preflight-final-20261101.log). The checkpointed preflight also passed. On the clean clone, the expected artifact-manifest warning was the only warning.
- **Failure/remediation history:** the first focused run exited 1 before a checkpoint refresh. A complete pre-checkpoint rerun recorded three failures: a governance assertion expected an explicit no-release phrase in `next_user_action`; a test required the phrase “no new milestone” while state said “no future milestone”; and fresh-context recovery reported `git_snapshot_matches=false` against the stale checkpoint. The state wording was made explicit and the supported checkpoint script wrote `cp-0b9c4c26-20261101T105639873398Z`; the next 83-test focused run passed. The final expanded 89-test focused run passed. Logs preserve the initial incomplete-capture exit, complete failing rerun, passing checkpoint rerun, and final focused pass; see the `G5-governance-focused-tests-*.log` files. Concrete local interpreter/worktree paths in retained logs were redacted; test output and return codes were preserved.
- One preliminary clean-clone test-launch wrapper was rejected by Bash for an unmatched quote before the Python test process started; the corrected wrapper then completed the 89-test suite successfully. The wrapper failure's exact start time was not separately retained, so none is backfilled and it is not counted as a test run.
- During clean-clone test setup, one shell wrapper was rejected by Bash for an unmatched quote before any test process started. The corrected wrapper then ran the clean-clone 89-test suite successfully. The first invocation's exact timestamp was not separately retained; it is not represented as a test run or pass.
- A read-only release-safety audit at `2026-11-01T11:06:25Z` reported zero GitHub releases, zero deployments, and zero remote tag refs. The task created none. See [release-safety audit](logs/G5-release-safety-audit-20261101.log).
- Privacy scan of all added lines found no concrete local filesystem path, credential pattern, or restricted-payload suffix across 415 lines. A scan of entire modified historical files found two pre-existing absolute-path occurrences in unchanged portions of `BLOCKERS.md` and `BACKLOG.yaml`; comparison with the integration base confirmed they were not introduced by this PR. No ROM, checkpoint, data, raw trace, RGB payload, or credential file was added. The checkpoint-history segments were decompressed and scanned. See the [retained privacy audit](logs/G5-privacy-audit-20261101.log); another final-diff scan is required after adding clean-clone logs and PR metadata.

## G. Canonical state transition proposed on this branch

- `PROJECT_STATE.yaml`: G5 is recorded as approved with limitations; `approved_gates` contains G0–G5; no next governance gate is defined. M7 remains complete, no task is active or next, and no new milestone is authorized. The original M7 Option B authorization is unchanged.
- `BACKLOG.yaml`: M7-001 through M7-005 remain engineering `done`; the verified G5 PM acceptance is linked to M7-004 and M7-005.
- `BLOCKERS.md` and `SESSION_HANDOFF.md`: current pointers now distinguish the verified PR #20 integration from the proposed closeout PR.
- The current `initial-idea` head contains PR #20 but not this feature branch's canonical state update. This PR is the proposal for that update; do not call it integrated before merge.

## H. Release and privacy

**NO RELEASE / NO PUBLICATION AUTHORIZED.** G5 does not authorize model/checkpoint publication, dataset distribution, ROM redistribution, raw-record or RGB publication, third-party access, external upload, deployment, GitHub Release, public benchmark publication, or any license/redistribution right. No restricted artifact was added or uploaded by this governance update. No experiments or training were run. O-06 and other open decisions remain open.

## I. Governance review request

Please independently verify:

1. The source PM comment, exact approved PR #20 head, merge commit, parents, and current integration ancestry.
2. The scoped G5 decision, G5-F01 resolution, preserved M7 scientific/environment qualifications, and accurate historical chronology.
3. The proposed canonical state/backlog values, including no future milestone authorization.
4. The no-release boundary and absence of private experimental payloads.
5. Focused/full/clean-clone test results and exact-head CI scope, including the unavailable Stockfish test and private-artifact skips.
6. That this governance PR itself remains unmerged and G5 approval does not grant release permission.

The repository currently has no branch protection or ruleset for `initial-idea`; the read-only query and the one-time owner-authorized PR #20 integration are documented in the policy exception record. This new PR requires fresh Independent PM review. Codex must not approve or merge it.

## Verification remediation record

`git diff --cached --check` initially exited 2 because the two new evidence headers used trailing Markdown hard-break spaces. The captured failure is in [the formatting-check log](logs/G5-diff-check-format-failure-20261101.log). Those whitespace characters were removed without changing evidence text; the cached diff check was rerun afterward.

The first cached diff check found the evidence headers' hard-break spaces. After those were fixed, a second cached check found the original failure transcript contained those same trailing spaces. Both failure logs were retained with only the echoed trailing spaces removed; the check findings and exit code 2 remain visible. The follow-up check is documented separately.
