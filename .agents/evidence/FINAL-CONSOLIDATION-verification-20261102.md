# Final consolidation verification ledger

This ledger separates candidate-worktree checks, committed-source checks, fresh-clone checks, and remote CI. Exact final PR HEAD/tree and final clean-clone results are reported in the PR handover to avoid self-referential source hashes. No historical PR #21 result is relabeled as a consolidation run.

Baseline recovery: the original Pre-M4 workspace preflight failed because its pre-existing roadmap deletion made a required file unavailable. No original workspace file was changed. The separate accepted-baseline worktree preflight passed; its only warning was ARTIFACT_MANIFEST_REQUIRED. The required baseline checkpoint refreshed context/archive metadata without changing governance or task status.

Candidate verification: five new landing/status/count/archive/workflow regression tests passed. The first `git diff --check` found one trailing space in PROJECT_OVERVIEW; it was removed. These were candidate checks at accepted HEAD plus uncommitted corrections, not exact committed-source verification. No application/runtime source or experiment was executed by those checks.

The existing environment has Python 3.12.3, torch 2.14.1+cpu, chess 1.11.2, gymnasium 1.4.0, ale-py 0.11.2, and a Stockfish executable on its existing PATH. No dependency or system installation was performed. Full unittest discovery is authorized verification and includes bounded ALE integration tests and a Stockfish readiness ping; it is not a new research campaign or engine search.

Read-only GitHub baseline checks returned no releases/tags/deployments/open PRs. Main branch protection lookup returned HTTP 404 “Branch not protected”; repository rulesets returned an empty list. No settings were changed. The context workflow target filter was extended to main; actual GitHub run behavior remains subject to observation after submission.

Privacy scan coverage: every tracked worktree file, recursive gzip/ZIP members, and proposed-history object path enumeration. Existing historical absolute machine-path references remain in immutable evidence/checkpoint history; no new concrete personal paths are introduced by this assignment's documentation. No new credential-pattern match was identified in the initial scan. This is a pattern/content inventory, not proof of all third-party rights, absence of every possible secret, or availability of private artifact bytes. Final scan details and exact counts belong to the retained logs and PR handover.

## Candidate failure and correction

The first candidate checkpoint/preflight did not pass: the README linked to two directories, while the context validator requires file targets. The checkpoint refused the invalid candidate, so the ensuing preflight also reported expected index/worktree drift from the prior checkpoint. Both links now point to real tracked files. See [failed candidate preflight](logs/FINAL-CONSOLIDATION-candidate-preflight-20261102.log). The initial focused run was started before those corrections/checkpoint refresh and its result is retained separately; it is not substituted for final committed verification.

The first focused candidate run executed 124 tests: 122 passed and two failed (zero skips). One failure detected the expected stale portable checkpoint after the rejected checkpoint command. The other correctly detected that even an appended status note changed the hash-pinned M5_FINAL_REPORT. That report was restored byte-for-byte to the accepted baseline; its stale status is now classified in the separate audit rather than changing the pinned evidence. The integrity test was retained unchanged. See [candidate focused log](logs/FINAL-CONSOLIDATION-candidate-focused-20261102.log).

Corrected candidate preflight passed after the link repair and checkpoint refresh. A subsequent diff whitespace check flagged trailing blank lines in the two newly captured candidate logs; their terminal blank lines were normalized without changing command output content. The runner now writes one terminal newline. These are newly authored consolidation logs, not historical experiment logs.

## Committed-source results

At clean source `2933ae0a5f1d3c604f96ddf42abfb67888f76b3b` (tree `dadff012885efc34c13784b89d4315f3bbc168df`):

| Command | Executed | Passed | Failed | Skipped | Exit | Evidence |
|---|---:|---:|---:|---:|---:|---|
| `python3 scripts/agent_preflight.py` | — | — | — | — | 0 | [Source preflight](logs/FINAL-CONSOLIDATION-source-preflight-20261102.log); expected artifact-manifest warning only |
| `python3 -B -m unittest tests.test_g5_final_closeout tests.test_m7_release_disposition tests.test_m7_delivery_docs tests.test_pre_m7_contracts tests.test_agent_context tests.test_checkpoint_history tests.test_final_consolidation -v` | 124 | 124 | 0 | 0 | 0 | [Source focused log](logs/FINAL-CONSOLIDATION-source-focused-20261102.log) |
| Existing project `python -B -m unittest discover -s tests -v` | 529 | 526 | 0 | 3 | 0 | [Unfiltered source full suite](logs/FINAL-CONSOLIDATION-source-full-20261102.log) |
| `python3 scripts/audit_final_consolidation.py --output /tmp/consolidation-source-inventory.json` | — | — | — | — | 0 | [Source privacy log](logs/FINAL-CONSOLIDATION-source-privacy-20261102.log), [inventory](FINAL-CONSOLIDATION-privacy-inventory-20261102.json) |

Logs retain actual UTC start/end, revision, command, exit code, environment and worktree-diff digest. The focused run used standard-library Python; the full run used the already-existing project interpreter/dependencies and Stockfish PATH. The three skips require unavailable private artifacts; the Stockfish readiness check passed. No private payload was copied into this checkout.

The [frozen-content comparison](FINAL-CONSOLIDATION-frozen-integrity-20261102.json) matched Git blob IDs for all 1,275 selected existing runtime/config/log/scientific-evidence/history paths; zero changed. The privacy inventory covers 1,507 tracked files, 267 gzip streams, 59 ZIP members, and 43 binary PNG leaves inside the exact authorized archive; no high-confidence credential match or unexpected opaque payload. It counts 1,000 existing concrete-home-path occurrences in immutable historical evidence, including decompressed content. These historical references are disclosed rather than falsely described as absent. No new concrete personal path was introduced by the documentation corrections. The proposed-history filename inventory found the exact BLK-001 ZIP as the only image/model/ROM/dataset/archive payload candidate; compressed checkpoint history is independently classified as context metadata. Past versions of all Git blob contents and private stores were not exhaustively scanned.

A final technical-doc sweep after this source run corrected four remaining maturity references (C25); it changed no runtime source, test, frozen config or scientific evidence. Final clean-clone verification at the pushed feature HEAD is required and will be reported in the PR's final handover rather than mislabeled as this source run. The independent PM must inspect that exact HEAD and actual CI before deciding integration. This ledger issues no approval.

## Fresh pushed-source clone and final evidence boundary

A separate `git clone --single-branch --branch feature/final-main-consolidation-20261102` from GitHub checked out `46c789377617f9d366b8efedd4c55619b987ed97`, tree `3fc914313016afefd9c907c6c645f7b29fbe3c9e`. Working tree was clean before and after checks. No private inputs or uncommitted source were copied; only the existing Python dependency environment was reused.

| Check | Executed | Passed | Failed | Skipped | Exit | Retained evidence |
|---|---:|---:|---:|---:|---:|---|
| Preflight | — | — | — | — | 0 | [Clean-source preflight](logs/FINAL-CONSOLIDATION-clean-source-preflight-20261102.log) |
| Same focused suite | 124 | 124 | 0 | 0 | 0 | [Clean-source focused](logs/FINAL-CONSOLIDATION-clean-source-focused-20261102.log) |
| Same unfiltered full suite | 529 | 526 | 0 | 3 | 0 | [Clean-source full](logs/FINAL-CONSOLIDATION-clean-source-full-20261102.log) |
| Recursive privacy/inventory | — | — | — | — | 0 | [Clean-source privacy](logs/FINAL-CONSOLIDATION-clean-source-privacy-20261102.log) |

The source clone scan covered 1,514 tracked files, 268 gzip streams, 59 ZIP members and 43 authorized PNG leaves. No credential-pattern match or unexpected opaque payload; archive SHA unchanged. Historical concrete-path occurrence count remains 1,000. The same three private-artifact prerequisites were skipped; Stockfish readiness passed.

The final evidence commit retains these logs, the [inherited whitespace comparison](FINAL-CONSOLIDATION-whitespace-audit-20261102.json), this ledger, the audit's C26 classification, and a prominent denominator notice in the closure matrix. No runtime source, tests, configurations, frozen scientific evidence, dependency lock, or backlog changes follow `46c7893…`. The last unfiltered full suite above is specifically bound to that revision; it is not relabeled as a later final-HEAD run. A further clean remote clone must verify final-HEAD preflight/focused tests and actual GitHub CI, with immutable HEAD/tree and results in the final PR handover. No recursive evidence-only commit cycle is required to invent a self-referential test SHA.

`git diff origin/main HEAD --check` returned exit 2 with 17 notices in nine inherited files. The accepted initial-idea baseline emits the identical notices after line-number normalization. `git diff origin/initial-idea HEAD --check` returned exit 0 with none. Historical experiment/test logs are preserved; these inherited formatting notices are a documented non-blocking limitation, not a passing check.
