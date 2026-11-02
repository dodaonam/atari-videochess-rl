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
