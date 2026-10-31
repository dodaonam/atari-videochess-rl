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
