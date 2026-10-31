# M7 Engineering Failure and Remediation History

This record preserves implementation and verification failures encountered while preparing M7 Phase I. No accepted M4/M5/M6 artifact was modified, repaired, or regenerated. The historical M6 analysis error described below was a reader schema-name mismatch, not an artifact hash mismatch.

## Retained exact diagnostics

- The combined focused suite exited 1 at `2026-10-31T16:37:03Z`. Its sanitized log is [M7-focused-tests-20261031.log](logs/M7-focused-tests-20261031.log), SHA-256 `ebb54f396ef2cc8ed6001f4c0a4dbebad4cab4dcbe4121a2835801c04db99e52`. Six link assertions correctly rejected new, not-yet-committed authorization/config references; the remaining assertion expected obsolete G4 wording. The plan/test wording was reconciled, and the link contract is rerun after the targets are committed.
- The initial M7 authorization-state preflight diagnostic is retained in [M7-auth-record-preflight-diagnostic-20261031.log](logs/M7-auth-record-preflight-diagnostic-20261031.log). Its finding was fixed in canonical evidence/state; the subsequent `agent_preflight.py` invocation passed.

## Earlier diagnostics without retained exact logs

These entries are `historical_unverified`: the execution output was visible during implementation, but no timestamped log was preserved at the time.

- Earlier M7 unit-test iterations reported a singular/plural summary key mismatch, missing fixture config path, and undefined resume `events` local. Each defect was fixed; subsequent focused tests passed.
- The first M6 raw reconstruction attempt reported that an attempt-manifest hash field differed. Inspection showed M6 records use `artifact_manifest_sha256` while the new M7 parser first looked for `attempt_manifest_sha256`. The parser now accepts the immutable M6 field and the M7 field. A later read-only verification reconstructed all 35 M6 v1 and 20 M6 v2 scheduled attempts, with the frozen root manifest hashes intact.
- The first synthetic M7 run-reconciliation test exposed an unbound normalized outcome variable and a fixture attempting to overwrite write-once evidence through the production atomic writer. A follow-up exposed that the reconstructed record schema was not passed into the normalization helper. The parser now carries that schema, the fixture uses explicit overwrite only for its temporary synthetic files, and the reconciliation/tamper tests pass.

## Current verification state

The latest pre-registration focused run is [M7-prerun-focused-tests-20261031.log](logs/M7-prerun-focused-tests-20261031.log), 27 tests passed after the symlink-input hardening. The earlier 22-test core and 26-test focused runs remain preserved. A failed run is never removed from the evidence history when a later run passes.

## Post-campaign analysis and review verification

- The first post-run analysis fix suite passed 28 focused M7 tests at source revision `58a604f2bd4bcd9113a047ee709a80ee97bd02a6`; a later report-table change added a started-count check and the final focused M7 suite passed 29 tests at `3f2f1f3cfae4154dd0fc0ff00c59901606590e5f`. Its retained log is [`M7-focused-final-20261101.log`](logs/M7-focused-final-20261101.log), SHA-256 `d91dab7713846571baa118ffe948a1ddd325e0511fb0050a4b65f25eaf9c353d`.
- The first selected-regression invocation used dotted `tests.*` module names. Three M5 test modules have legacy sibling imports and failed during test import (223 tests discovered, 3 import errors; no test assertion failed). The sanitized failure log and diagnosis are retained in [`M7-M1-M4-M5-M6-regression-20261101.json`](M7-M1-M4-M5-M6-regression-20261101.json). Corrected `unittest discover -s tests -p 'test_m[1456]*.py'` passed 230 tests with one opt-in M6 private-roster test skipped; that test then passed separately with the verified M4/M5 artifact roots. Both records are retained.
- The first full-suite run at `fe2cc4cc5e477841ffbc9368235eb9c5675f2f74` ran 491 tests and reported four failures plus one skip. Two context-recovery failures were caused by the stale pre-M7 checkpoint and are addressed by the required checkpoint refresh. One context test still asserted the historical pre-authorization state after the owner's later M7 authorization; its assertion now tests the preserved G4 HOLD and the later authorization as separate facts. The M0 readiness test could not find the already-installed Stockfish binary because its project virtualenv directory was not on this shell's `PATH`; the binary exists at the project venv's `share/stockfish/stockfish`. The final full-suite rerun adds that existing directory to the test process `PATH`, configures the accepted private M4/M5 test paths, and performs no search. Exact sanitized failure details are retained in [`M7-full-suite-first-failure-20261101.json`](M7-full-suite-first-failure-20261101.json) and its linked log.
- The current G4-boundary preflight first exposed malformed task-evidence provenance introduced in the new M7 backlog entries. File evidence was corrected to leave command-only metadata null; retained command logs now carry the recorded command, result, and exit code. The preflight's existing milestone validator also could not represent an authorized milestone after Phase I completion when its next task was waiting at an independent approval gate. It now permits a downstream task only when the authorized task is complete, the dependency chain is present, and the next task remains pending at its declared gate. It does not approve that gate or start the gated task. The targeted test and final full-suite rerun cover this boundary.

Final full-suite outcome is recorded in the later G4 review handover; the first run above remains preserved regardless of the rerun result.
