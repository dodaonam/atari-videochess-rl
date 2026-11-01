# G4 Governance Verification Failure and Remediation History

This record preserves encountered failures during the G4 governance update. A failure is not deleted because a later run passes.

## Focused contract assertion — corrected

- An early `tests.test_pre_m7_contracts` invocation failed because the test expected the literal substring `G5 review`, while the canonical M7-005 action described it as a `G5-owned task` requiring independent G5 acceptance.
- The assertion did not reflect the contract: G5 owns the M7-05 acceptance criterion, while requiring G5 approval before producing the G5-owned deliverable would be circular. The test now checks the `G5-owned` designation and verifies that no G5 entry prerequisite is set. M7-005 remains pending, downstream of M7-004, and its next action preserves both independent G5 acceptance and the separate Project Owner release restriction.
- The first console output was not retained as a log and its execution timestamp was not recorded. This occurrence is therefore `historical_unverified`; no timestamp or log path is backfilled. The failure was observed in the tool output during this task.
- A corrected 10-test focused rerun passed in the tool output but was not separately persisted; it is not the retained acceptance evidence. The final 64-test run below includes the same governance contracts and transition checks, with a retained log.

## Context suite on the uncheckpointed worktree — rerun required

- `tests.test_pre_m7_contracts` plus `tests.test_agent_context` ran 64 tests and reported one failure in `test_project_context_can_be_recovered_without_chat_history`: its expected `git_snapshot_matches` value was false while canonical governance and other files had uncheckpointed local edits.
- The output is retained in [`G4-governance-tests-20261101.log`](logs/G4-governance-tests-20261101.log). This does not establish a source defect; the test exercised recovery from a checkpoint that predated the current worktree changes. The worktree will be checkpointed, preflighted, and the suite rerun before acceptance.
- This is a recorded failed attempt, not a pass. The final report will cite only the rerun result for completion.

## Checkpointed context/governance suite — passed

- After checkpoint `cp-2bca7900-20261101T031707747079Z` and a passing preflight, the same command ran 64 tests and passed. The full output and UTC start/finish times are retained in [`G4-governance-tests-rerun-20261101.log`](logs/G4-governance-tests-rerun-20261101.log).
- All eight Pre-M7/M7 contract tests, current G4 task-state checks, checkpoint/recovery tests, and clean-clone fixture checks passed. The separate final no-local clone will still be checked at the final PR HEAD.
