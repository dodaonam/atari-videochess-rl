# M7-005 Failure and Remediation History

This record preserves failures from the M7-005 governance transition and verification. It must not be rewritten to present a later pass as if the failure did not occur.

## Authorization evidence provenance validation — remediated

- **Command:** `python3 scripts/agent_preflight.py`
- **Source revision:** `0f45fa06c235658da48d3d41a9091c06580bfe27` with the M7-005 authorization/state transition in the worktree
- **Execution:** 2026-11-01; exact failing preflight output retained at [authorization transition failure log](logs/M7-005-authorization-transition-preflight-failure-20261101.log)
- **Exit code:** 1
- **Failure:** `TASK_EVIDENCE_PROVENANCE` because the manual authorization evidence lacked a verification timestamp; `TASK_EVIDENCE_LOG_MISMATCH` because the cited result sentence was not present in the retained manual authorization record.
- **Cause:** The authorization has no supplied issue timestamp; the first canonical evidence entry omitted the separate time at which the direct instruction was recorded/verified and its exact result text.
- **Remediation:** Preserve the instruction's missing issuance timestamp honestly; add an actual record/verification timestamp and the exact result sentence to the evidence file and backlog provenance. No authorization timestamp was invented.
- **Rerun:** `python3 scripts/agent_preflight.py` passed after correction; the checkpoint refresh recorded the transition and post-checkpoint preflight also passed. Final M7-005 preflight runs are retained in the acceptance record.

## Release-decision link validation — remediated

- **Command:** `python3 scripts/agent_preflight.py`
- **Source revision:** `0f45fa06c235658da48d3d41a9091c06580bfe27` with the M7-005 documentation draft
- **Execution date:** 2026-11-01; exact output and exit code retained at [broken-link preflight log](logs/M7-005-document-link-preflight-failure-20261101.log)
- **Exit code:** 1
- **Failure:** `LINK_BROKEN` because the G5 dossier referenced the planned owner no-release decision file before it had been created.
- **Cause:** Drafting order created a link before its target.
- **Remediation:** Added `.agents/evidence/M7-005-owner-no-release-decision-20261101.md` with the direct owner decision and truthful provenance.
- **Rerun:** `python3 scripts/agent_preflight.py` exited 0; the broken link was resolved. Sanitized output is retained at [remediation preflight log](logs/M7-005-document-link-preflight-remediation-20261101.log). Expected checkpoint/worktree drift and `ARTIFACT_MANIFEST_REQUIRED` warnings remained while the branch changes were uncommitted.

Other verification failures, if any, will be appended with exact commands, source revision, timestamp when available, exit code, cause and rerun evidence.

## Initial 82-test focused suite — remediated

- **Command:** `<existing project Python 3.12.3 venv>/bin/python -m unittest tests.test_pre_m7_contracts tests.test_agent_context tests.test_m7_delivery_docs tests.test_m7_artifact_manifest_cli tests.test_m7_release_disposition -v`
- **Source revision:** `0f45fa06c235658da48d3d41a9091c06580bfe27` with the M7-005 candidate worktree
- **Execution:** 2026-11-01T05:15:10Z–2026-11-01T05:16:02Z
- **Exit code:** 1; 82 tests ran, three failures. The complete sanitized log is [M7-005 focused-suite failure](logs/M7-005-focused-suite-20261101.log).
- **Failures and causes:** One assertion expected the canonical hold text to contain `M7-005`; the final state wording named G5 but omitted the completed task ID. One owner-decision test expected a phrase that did not match the record's truthful wording (“or separate issuance timestamp”). One current-worktree recovery assertion compared against a stale checkpoint snapshot because governance/documentation files had changed since the checkpoint.
- **Remediation:** Add `M7-005` to the accurate final hold reason; align the test to the actual issuance-timestamp statement; checkpoint the final candidate state before rerunning the worktree recovery test. The corresponding clean-clone recovery test had already passed in this run.
- **Rerun:** After the corrections and checkpoint refresh, the same 82-test focused suite passed with 0 failures at `2026-11-01T05:17:39Z`–`2026-11-01T05:18:32Z`; see [final focused-suite log](logs/M7-005-focused-suite-final-20261101.log). A separate clean-clone run remains part of the final verification.

## Unfiltered full repository suite — environment prerequisite unavailable

- **Command:** `<existing project Python 3.12.3 venv>/bin/python -m unittest discover -s tests -v`
- **Source revision:** `0f45fa06c235658da48d3d41a9091c06580bfe27` with the M7-005 candidate worktree
- **Execution:** 2026-11-01T05:18:57Z–2026-11-01T05:21:44Z
- **Result / exit:** 509 tests ran; one failure, three skips; exit 1. The only failure is `test_m0_smoke.M0EnvironmentSmokeTests.test_stockfish_answers_uci_readiness_without_searching`: the project environment PATH has no Stockfish executable. The test checks readiness without searching. No software was installed and no Stockfish search or benchmark was run.
- **Log:** [unfiltered full-suite result](logs/M7-005-full-suite-unfiltered-20261101.log).
- **Disposition:** Retain and report the failed check. Run the remaining suite in a clean clone excluding exactly this unavailable test; do not claim the unfiltered suite passed.

## First filtered-suite runner attempt — remediated

- **Command:** `<existing project Python 3.12.3 venv>/bin/python -B .agents/evidence/logs/M7-005-exclude-stockfish-test-runner-20261101.py`
- **Source revision:** `0f45fa06c235658da48d3d41a9091c06580bfe27` with the M7-005 candidate worktree
- **Execution:** 2026-11-01T05:22:01Z–2026-11-01T05:23:11Z
- **Result / exit:** 181 selected tests, 42 import errors, one dirty-worktree snapshot failure; exit 1. The initial runner discovered `tests` without setting the repository top-level directory, so modules under test could not import `videochess_rl` or `scripts`; the repository was also dirty during the snapshot assertion.
- **Log:** [initial filtered-runner failure](logs/M7-005-full-suite-excluding-stockfish-initial-failure-20261101.log).
- **Remediation:** Set `top_level_dir="."` so discovery matches the repository's documented command. Final filtered-suite verification will run from a clean clone, where the snapshot assertion is applicable.

## Initial private-path scan — false positives corrected

- **Command:** Candidate-file scan for private paths and credential patterns.
- **Execution:** `2026-11-01T05:24:52Z`, exit 1; retained at [initial scan log](logs/M7-005-private-scan-initial-false-positive-20261101.log).
- **Finding:** The whole-file scanner matched the literal generic path regexes in tests that verify documentation privacy, and historical path text in files whose unchanged lines were scanned. No added documentation/private payload was identified by this output.
- **Cause:** The scan did not distinguish newly added lines from unchanged history and treated regex test patterns as literal machine paths.
- **Remediation:** Re-scanned only added tracked lines and untracked text files using concrete machine-path and credential patterns. At `2026-11-01T05:25:02Z`, exit 0: 153 added tracked lines and 9 untracked text files scanned, zero matches; see [corrected privacy scan](logs/M7-005-private-scan-corrected-20261101.log).

## Focused release-disposition test assertion corrections — remediated

- **Command:** Three focused `M7ReleaseDispositionTests` for the inventory, G5 scientific handover, and private-path exclusion.
- **Source revision:** `0f45fa06c235658da48d3d41a9091c06580bfe27` with the M7-005 candidate worktree
- **Failures:** At `2026-11-01T05:12:30Z`, exit 1 because the test expected a different word order for the documented “G5 pending Independent PM decision” status. At `2026-11-01T05:12:37Z`, exit 1 because the acceptance header did not state `NOT APPROVED` in the form the test checked.
- **Cause:** Two new assertions were initially stricter than the dossier's accurate wording, and the acceptance header could state the G5 boundary more explicitly.
- **Remediation:** Corrected the wording assertion to match the actual governance statement and added an explicit `G5: NOT APPROVED` header to the acceptance record. Neither correction changes PM status or scientific evidence.
- **Failure logs:** [first assertion failure](logs/M7-005-focused-disposition-content-20261101.log) and [second assertion failure](logs/M7-005-focused-disposition-content-remediation-20261101.log); machine-specific checkout paths were sanitized.
- **Rerun:** The same three tests passed, 3 run / 0 failures, at `2026-11-01T05:12:44Z`; see [focused remediation pass](logs/M7-005-focused-disposition-content-final-20261101.log).
