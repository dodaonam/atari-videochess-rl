# G1 Consistency and Reliability Hardening Audit

This record is the retained evidence index and cross-file audit matrix for G1 hardening. Current status and next action remain canonical in `PROJECT_STATE.yaml` and `BACKLOG.yaml`; this record does not approve G1.

## Cross-file consistency matrix

| File | Audit result |
|---|---|
| `AGENTS.md` | ADR-0001 owns the G/M crosswalk; execution plan owns sequence/inventory; context recovery distinguishes the checkpoint from the handoff; M0/M1 remain gated. |
| `docs/01-foundation/ROADMAP.md` | Preserved verbatim; preflight compares it with both embedded HTML sources and checks all 19 sections. |
| `docs/01-foundation/REQUIREMENTS.md` | Owns objectives, confirmed baseline, proposals, and O-01–O-08; points crosswalk ownership to ADR-0001; does not resolve technical approvals. |
| `docs/01-foundation/PROJECT_OVERVIEW.md` | Recovery overview only; points live status to state/backlog and crosswalk ownership to ADR-0001. |
| `docs/02-management/EXECUTION_PLAN.md` | Owns milestone sequence, dependencies, deliverables, and fixed P0/P1/P2 inventory; references rather than copies the crosswalk. |
| `docs/02-management/RISK_REGISTER.md` | Risks remain proposed/unverified where M0/M1 evidence does not exist; no technical risk is marked resolved by documentation. |
| `docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md` | Sole crosswalk decision owner; explicitly maps G4 to M6 plus M7 evaluation criteria and G5 to M7 delivery criteria. |
| `docs/05-operations/SETUP.md` | M0 runbook only; no setup, installation, Colab allocation, or external check is claimed. Evidence rules include actual provenance. |
| `docs/06-quality/ACCEPTANCE_CRITERIA.md` | Owns 51 criterion IDs; G1-08 is Python-process recovery, G1-10 is independent Codex-session recovery, and G4/G5 own separate M7 criteria. |
| `docs/06-quality/TEST_STRATEGY.md` | Defines disposable-Git recovery checks, provenance, hashing exclusions, artifact manifests, and the manual Codex-session gate. |
| `.agents/PLANS.md` | Defines canonical ownership, schema v2, task/evidence rules, and links the active G1 task plan. |
| `.agents/plans/M00-bootstrap.md` | M0 plan only; remains unexecuted and does not grant authorization. |
| `.agents/plans/G1-consistency-hardening.md` | Scope and acceptance plan for this G1 reliability task; status remains owned by backlog/state. |
| `.agents/state/PROJECT_STATE.yaml` | Live gate, next task, M0 authorization, checkpoint snapshot, and checksummed historical G1 baseline. |
| `.agents/state/SESSION_HANDOFF.md` | Pointer-only recovery path; does not duplicate current status or task evidence. |
| `.agents/state/BLOCKERS.md` | No technical blocker is inferred from pending review; O-01–O-08 remain in requirements. |
| `.agents/state/VERIFIED_FINDINGS.md` | Separates source-integrity facts and the Python recovery result from the still-unrun Codex-session acceptance. |
| `.agents/tasks/BACKLOG.yaml` | Owns task IDs, dependencies, statuses, plan refs, criteria, and per-entry provenance; historical reports remain explicitly unverified. |
| `scripts/agent_preflight.py` | Validates v2 state/backlog, table and bullet criteria, evidence provenance, links, Git/hash inventory (including unreadable files), and safe malformed-state reporting. |
| `scripts/agent_checkpoint.py` | Dry-run performs no file or Git-index mutation; a real checkpoint snapshots status after state and handoff writes. |
| `tests/test_agent_context.py` | Uses disposable Git repositories for clean/dirty, tracked/untracked, partial-write, dry-run, criteria, evidence/log-provenance, large/artifact/unreadable files, and recovery cases. |
| `README.md` | Existing user file preserved unchanged. |
| `atari-videochess-rl-roadmap.html` | Original source preserved unchanged; used only for exact roadmap verification. |
| `chat_history.md` | Historical source preserved unchanged; never copied into state or evidence logs. |

## Scope boundaries

- Governance gates G0–G5 remain distinct from engineering milestones M0–M7.
- G4 owns M7-01–M7-03 evaluation acceptance; G5 owns M7-04–M7-05 delivery acceptance.
- Supervised pretraining, chess-simulator RL, and actual Atari evaluation remain separate evidence tracks.
- No academic, ALE/ROM, Stockfish, dataset-license, compute, or external-service approval is inferred.
- No M0/M1 work, dependency installation, training, Colab allocation, commit, or push is part of this audit.
- The independent Codex-session acceptance G1-10 is intentionally left pending; no fresh-session result or conversation transcript is fabricated here.

## Verification runs

Command output, UTC execution timestamps, exit codes, and Git revision are retained below. The final preflight ran after G1-007 completed and G1-008 became the active manual acceptance task.

### Full test suite

- **Command:** `python3 -m unittest discover -s tests -v`
- **Executed at (UTC):** 2026-10-14T14:47:24Z
- **Exit code:** 0
- **Git revision:** `c410173ecccc3178ea41b4202ce6a4a437f9aafe`
- **Result:** PASS: 33 tests passed; exit code 0.

```text
Command: python3 -m unittest discover -s tests -v
Result: PASS: 33 tests passed; exit code 0.
Exit code: 0
```

```text
test_blocked_task_must_reference_an_active_blocker (test_agent_context.AgentContextRecoveryTests.test_blocked_task_must_reference_an_active_blocker) ... ok
test_checkpoint_is_consistent_after_one_run_from_clean_worktree (test_agent_context.AgentContextRecoveryTests.test_checkpoint_is_consistent_after_one_run_from_clean_worktree) ... ok
test_checkpoint_repairs_stale_handoff_pointer (test_agent_context.AgentContextRecoveryTests.test_checkpoint_repairs_stale_handoff_pointer) ... ok
test_completed_task_requires_existing_evidence (test_agent_context.AgentContextRecoveryTests.test_completed_task_requires_existing_evidence) ... ok
test_done_task_cannot_rely_only_on_historical_unverified_evidence (test_agent_context.AgentContextRecoveryTests.test_done_task_cannot_rely_only_on_historical_unverified_evidence) ... ok
test_dry_run_with_partial_recovery_does_not_mutate_files (test_agent_context.AgentContextRecoveryTests.test_dry_run_with_partial_recovery_does_not_mutate_files) ... ok
test_future_milestone_bullet_criteria_are_valid_task_references (test_agent_context.AgentContextRecoveryTests.test_future_milestone_bullet_criteria_are_valid_task_references) ... ok
test_g1_cannot_be_ready_with_incomplete_g1_tasks (test_agent_context.AgentContextRecoveryTests.test_g1_cannot_be_ready_with_incomplete_g1_tasks) ... ok
test_git_ignored_zip_is_still_content_hashed (test_agent_context.AgentContextRecoveryTests.test_git_ignored_zip_is_still_content_hashed) ... ok
test_historical_baseline_checksum_detects_record_mutation (test_agent_context.AgentContextRecoveryTests.test_historical_baseline_checksum_detects_record_mutation) ... ok
test_historical_baseline_is_not_recompared_to_current_files (test_agent_context.AgentContextRecoveryTests.test_historical_baseline_is_not_recompared_to_current_files) ... ok
test_json_output_is_machine_readable_and_paths_are_portable (test_agent_context.AgentContextRecoveryTests.test_json_output_is_machine_readable_and_paths_are_portable) ... ok
test_large_files_and_artifact_directories_are_reported_once_and_separately (test_agent_context.AgentContextRecoveryTests.test_large_files_and_artifact_directories_are_reported_once_and_separately) ... ok
test_m0_cannot_be_authorized_before_g1_approval (test_agent_context.AgentContextRecoveryTests.test_m0_cannot_be_authorized_before_g1_approval) ... ok
test_manual_session_evidence_requires_sanitized_record_and_revision (test_agent_context.AgentContextRecoveryTests.test_manual_session_evidence_requires_sanitized_record_and_revision) ... ok
test_partial_state_file_is_detected_and_recovered (test_agent_context.AgentContextRecoveryTests.test_partial_state_file_is_detected_and_recovered) ... ok
test_preflight_detects_content_change_inside_existing_dirty_path (test_agent_context.AgentContextRecoveryTests.test_preflight_detects_content_change_inside_existing_dirty_path) ... ok
test_preflight_detects_roadmap_source_mismatch (test_agent_context.AgentContextRecoveryTests.test_preflight_detects_roadmap_source_mismatch) ... ok
test_preflight_discovers_every_documented_acceptance_criterion (test_agent_context.AgentContextRecoveryTests.test_preflight_discovers_every_documented_acceptance_criterion) ... ok
test_preflight_finds_broken_markdown_link (test_agent_context.AgentContextRecoveryTests.test_preflight_finds_broken_markdown_link) ... ok
test_preflight_recovers_project_state_without_conversation (test_agent_context.AgentContextRecoveryTests.test_preflight_recovers_project_state_without_conversation) ... ok
test_preflight_rejects_dependency_cycle (test_agent_context.AgentContextRecoveryTests.test_preflight_rejects_dependency_cycle) ... ok
test_preflight_rejects_invalid_state_schema (test_agent_context.AgentContextRecoveryTests.test_preflight_rejects_invalid_state_schema) ... ok
test_preflight_reports_dirty_worktree_and_checkpoint_refreshes_it (test_agent_context.AgentContextRecoveryTests.test_preflight_reports_dirty_worktree_and_checkpoint_refreshes_it) ... ok
test_preflight_reports_files_it_could_not_hash (test_agent_context.AgentContextRecoveryTests.test_preflight_reports_files_it_could_not_hash) ... ok
test_preflight_reports_malformed_git_snapshot_without_crashing (test_agent_context.AgentContextRecoveryTests.test_preflight_reports_malformed_git_snapshot_without_crashing) ... ok
test_preflight_reports_malformed_task_status_without_crashing (test_agent_context.AgentContextRecoveryTests.test_preflight_reports_malformed_task_status_without_crashing) ... ok
test_project_context_can_be_recovered_without_chat_history (test_agent_context.AgentContextRecoveryTests.test_project_context_can_be_recovered_without_chat_history) ... ok
test_state_blocker_index_must_match_active_blocker_records (test_agent_context.AgentContextRecoveryTests.test_state_blocker_index_must_match_active_blocker_records) ... ok
test_tracked_content_drift_is_detected_without_a_status_path_change (test_agent_context.AgentContextRecoveryTests.test_tracked_content_drift_is_detected_without_a_status_path_change) ... ok
test_verified_command_evidence_must_match_retained_log (test_agent_context.AgentContextRecoveryTests.test_verified_command_evidence_must_match_retained_log) ... ok
test_verified_command_evidence_requires_timestamp_revision_exit_and_log (test_agent_context.AgentContextRecoveryTests.test_verified_command_evidence_requires_timestamp_revision_exit_and_log) ... ok
test_verified_command_evidence_with_provenance_passes (test_agent_context.AgentContextRecoveryTests.test_verified_command_evidence_with_provenance_passes) ... ok

----------------------------------------------------------------------
Ran 33 tests in 6.449s

OK
```

### Final repository preflight

- **Command:** `python3 scripts/agent_preflight.py`
- **Executed at (UTC):** 2026-10-14T14:47:43Z
- **Exit code:** 0
- **Git revision:** `c410173ecccc3178ea41b4202ce6a4a437f9aafe`
- **Result:** Agent context preflight: PASS

```text
Command: python3 scripts/agent_preflight.py
Result: Agent context preflight: PASS
Exit code: 0
```

```text
Agent context preflight: PASS
Governance: G1 (in_progress); approved: G0
Next engineering milestone: M0 — not started (pending user approval)
Active task: G1-008 — Run independent Codex-session recovery acceptance and request G1 review
Active task next action: In a separate Codex session with no prior conversation, perform the G1-10 checklist, record a sanitized result and provenance, then review and explicitly approve G1. Do not start M0 or M1 before approval.
Next task: G1-008 (in_progress) — Run independent Codex-session recovery acceptance and request G1 review
Next task dependencies: G1-007
Next task acceptance criteria: G1-10, G1-09
Tasks: done=7, in_progress=1, pending=1, blocked=0, cancelled=0
Completed task IDs: G1-001, G1-002, G1-003, G1-004, G1-005, G1-006, G1-007
In progress task IDs: G1-008
Pending task IDs: M0-001
Blocked task IDs: none
Active blockers: none recorded
Open confirmations:
  O-01: Assignment/instructor rules for ALE observation extraction, action wrappers, custom PyTorch RL, Stockfish training use, and any engine use in offline evaluation.
  O-02: Whether full-game performance on actual ALE is a hard submission requirement or a research target with an accepted fallback.
  O-03: Whether the approximate three-week estimate is still the project deadline.
  O-04: Actual Colab entitlement/quota, GPU availability, storage, and whether paid compute is allowed.
  O-05: ALE/ROM version and availability, RAM mapping, game modes, difficulty behavior, and official evaluation settings.
  O-06: PGN/tactical data sources, licenses, permitted use, and expected scale.
  O-07: Stockfish version/search limits and whether it may be a benchmark opponent or offline evaluator.
  O-08: Opponent pool and rating method for any Elo claim.
Relevant decisions: docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md
Acceptance criteria recognized: 51
Last verified Git: initial-idea @ c410173ecccc3178ea41b4202ce6a4a437f9aafe
Roadmap source: exact match; 19 sections; SHA-256 fc7496b276c72a58a858897e262ff615bb5fea0f5f8a3fe6d1cd24b1397276bf
Git status snapshot: matches live worktree
Hashed ordinary-file snapshot: matches
Content hashes: 27 ordinary files verified by SHA-256.
Not content-verified by this hash map: PROJECT_STATE self-reference, chat history/credential-like paths, temp files, symlinks, and the excluded directories listed below.
Excluded directories: .git, scripts/__pycache__, tests/__pycache__
Last verified dirty paths (27): ?? .agents/PLANS.md; ?? .agents/evidence/G1-hardening-verification.md; ?? .agents/plans/G1-consistency-hardening.md; ?? .agents/plans/M00-bootstrap.md; ?? .agents/state/BLOCKERS.md; ?? .agents/state/PROJECT_STATE.yaml; ?? .agents/state/SESSION_HANDOFF.md; ?? .agents/state/VERIFIED_FINDINGS.md; ?? .agents/tasks/BACKLOG.yaml; ?? .python-version; ?? AGENTS.md; ?? atari-videochess-rl-roadmap.html; ?? chat_history.md; ?? docs/01-foundation/PROJECT_OVERVIEW.md; ?? docs/01-foundation/REQUIREMENTS.md; ?? docs/01-foundation/ROADMAP.md; ?? docs/02-management/EXECUTION_PLAN.md; ?? docs/02-management/RISK_REGISTER.md; ?? docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md; ?? docs/05-operations/SETUP.md; ?? docs/06-quality/ACCEPTANCE_CRITERIA.md; ?? docs/06-quality/TEST_STRATEGY.md; ?? main.py; ?? pyproject.toml; ?? scripts/agent_checkpoint.py; ?? scripts/agent_preflight.py; ?? tests/test_agent_context.py
Next user action: Complete G1-10 in a separate Codex session with no prior conversation, then review and explicitly approve G1. Do not start M0 or M1 before approval.
```
