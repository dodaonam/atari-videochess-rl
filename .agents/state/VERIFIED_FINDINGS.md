# Verified Findings

**Canonical source for:** evidence-backed facts that future sessions should retain. Proposals belong in plans/requirements; decisions belong in ADRs; live task status belongs in the backlog/state.

## FND-001 — G1-start repository baseline

- **Status:** verified at G1 start
- **Finding:** Branch `initial-idea`, HEAD `c410173ecccc3178ea41b4202ce6a4a437f9aafe`. Only `.gitignore` and `README.md` were tracked. The Python project files, chat history, source HTML, and G0 documents were already untracked. No `.agents/`, scripts, tests, or expanded documentation tree existed at audit time.
- **Evidence:** `.agents/state/PROJECT_STATE.yaml` → `g1_baseline`; command `git status --porcelain=v1 --untracked-files=all` and `git ls-files`.
- **Impact:** Preserve the original user files and do not interpret their untracked status as G1-created work.

## FND-002 — Existing README preserved

- **Status:** verified at G1 start
- **Finding:** `README.md` existed as a one-line project heading and was not modified in G1.
- **Evidence:** `.agents/state/PROJECT_STATE.yaml` → `g1_baseline.preserved_sha256.README.md` and final Git diff/status review.
- **Impact:** Count README as the existing P1 item; do not replace or expand it to satisfy the inventory count.

## FND-003 — G0 roadmap extraction integrity

- **Status:** verified in G0 and rechecked in G1
- **Finding:** `docs/01-foundation/ROADMAP.md` is byte-for-byte equal to the embedded `rawArchive` and displayed source in the HTML. SHA-256: `fc7496b276c72a58a858897e262ff615bb5fea0f5f8a3fe6d1cd24b1397276bf`.
- **Evidence:** G0 extraction check; current preflight source-integrity check compares the embedded archive and extracted Markdown.
- **Impact:** Keep the source HTML unchanged; update derived requirements or plans instead of rewriting the roadmap.

## FND-004 — No technical environment findings in G1

- **Status:** verified during initial G1 bootstrap; rechecked during hardening
- **Finding:** No ALE feasibility, model, dataset, RL training, or Colab GPU experiment has been performed in G1. Their runtime facts and results remain unverified.
- **Evidence:** G1 backlog and scope; no M0/M1 task was started.
- **Impact:** Do not infer installed dependencies, ALE behavior, GPU availability, or model performance from G1 completion.

## FND-005 — Fresh-process recovery contract

- **Status:** reported verified during initial G1; original command output/timestamp not retained
- **Finding:** A fresh Python process using repository files only can recover the project objective and evidence tracks, source-stated constraints and open approvals, current gate/milestone/task, completed/pending/blocked task IDs, relevant ADR, acceptance criterion IDs, next action, and last verified Git state. The recovery contract test reads canonical documents and does not read `chat_history.md`.
- **Evidence:** `tests/test_agent_context.py::test_project_context_can_be_recovered_without_chat_history`; the earlier backlog result `16 tests passed` is retained as `historical_unverified`. Current rerun evidence is recorded under G1-005/G1-006 after final verification.
- **Impact:** The repository and Python tooling can provide the information a new agent needs. This finding does not prove that a separate Codex session can independently read and interpret that information; G1-10 covers that manual acceptance.

## FND-006 — G1 reliability audit findings

- **Status:** reproduced and fixed; automated checks verified
- **Finding:** The audit reproduced unsafe dry-run recovery, a stale one-run checkpoint snapshot, missed bullet-form criterion IDs, duplicate large-file warnings, unreported artifact directories, and baseline warnings caused by comparing historical G1-start hashes with current files. Regression coverage now exercises each behavior and malformed snapshot/task-status cases.
- **Evidence:** `.agents/plans/G1-consistency-hardening.md`; `tests/test_agent_context.py`; `.agents/evidence/G1-hardening-verification.md`.
- **Impact:** Automated G1 hardening is complete. At the time this audit record was written, G1 approval remained open pending the independent Codex-session recovery acceptance G1-10 and user review; both were subsequently completed.

## FND-007 — G1 user approval and M0 hold

- **Status:** verified 2026-10-14
- **Finding:** The user explicitly approved G1 after G1-10 recovery evidence was recorded. M0 is the next engineering milestone and had not started when this finding was recorded; M1 depends on M0.
- **Evidence:** `.agents/evidence/G1-10-recovery-verification.md`; `.agents/evidence/G1-git-baseline-verification.md`; `.agents/state/PROJECT_STATE.yaml`.
- **Impact:** G1 approval does not resolve open confirmations O-01 through O-08. Follow canonical state and latest direct user instructions for milestone start authorization.

## FND-008 — Portable checkpoint recovery and context consistency

- **Status:** verified 2026-10-14
- **Finding:** The checkpoint now separates an index-based portable tracked manifest and semantic-state/handoff checksums from workspace-local Git status and file observations. A real commit-and-clone regression verifies state recovery without chat history, ignored archives, `main.py`, or caches; tracked changes remain detectable.
- **Evidence:** `.agents/evidence/G1-portability-consistency-verification.md` and `tests/test_agent_context.py::test_clean_clone_recovers_portable_baseline_without_local_artifacts`.
- **Impact:** Clean checkouts can recover canonical project state without inheriting local workspace-only artifacts. M0 was pending explicit authorization when this finding was recorded; later authorization is recorded in `.agents/evidence/M0-authorization.md`.

## FND-009 — M0 local bootstrap and remaining M1 prerequisites

- **Status:** verified 2026-10-15
- **Finding:** On Ubuntu 24.04.5 with system Python 3.12.3 and `uv` 0.9.26, the project lock installed Gymnasium 1.4.0, ALE-Py 0.11.2, python-chess 1.11.2, and CPU-only PyTorch 2.14.1+cpu in `.venv`. Five M0 smoke checks and the full 41-test suite passed. Stockfish 19 passed a UCI readiness ping only. Colab CLI 0.7.4 version/help checks passed; no remote session or runtime was used.
- **Evidence:** `.agents/evidence/M0-001-verification.md`; `tests/test_m0_smoke.py`; `uv.lock`.
- **Impact:** M0 bootstrap is complete and user-accepted. At the time of this M0 finding M1 had not started; current M1 authorization and status are in `.agents/evidence/M1-authorization.md`, `.agents/tasks/BACKLOG.yaml`, and `.agents/state/PROJECT_STATE.yaml`. The installed ALE-Py 0.11.2 package includes and resolves `video_chess.bin`; Gymnasium registration and construction without reset are distinct verified checks, and neither establishes gameplay behavior. The ROM absence concern is cleared; O-05 remains open for RAM mapping, modes, difficulty, evaluation settings, and assignment/runtime permissions. Colab authentication/entitlement, O-01–O-08, and permitted Stockfish roles remain unresolved.


## FND-010 — M0 final technical verification

- **Status:** verified 2026-10-14; M0 user-accepted 2026-10-15
- **Finding:** The full 62-test context/export/M0 suite and locked dependency check passed. ALE-Py 0.11.2 contains and resolves the packaged VideoChess ROM under `video_chess`; Gymnasium registration and construction without reset also passed. Historical G1 recovery, current-HEAD recovery, and synthetic G1-to-G2/M1/M2 clone transitions passed. Stockfish 19 archive, executable, and license hashes are reproducible from the pinned official release/source tag.
- **Evidence:** `.agents/evidence/M0-final-technical-verification.md`; `.agents/evidence/M0-001-verification.md`; `tests/test_agent_context.py`; `tests/test_m0_smoke.py`; `docs/05-operations/SETUP.md`.
- **Impact:** M0-01 through M0-04 are user-accepted. At the time of this M0 verification M1 still required separate authorization; the later authorization is recorded in `.agents/evidence/M1-authorization.md`. O-01 through O-08 remain unresolved; O-05 is partially informed by local ROM evidence and M1 observations but remains open for official evaluation details and other confirmations.


## FND-011 — M0 user acceptance

- **Status:** user-accepted 2026-10-15
- **Finding:** The user explicitly accepted M0-001 and M0-01 through M0-04 based on the final technical verification evidence; this approval does not authorize a commit, push, or M1.
- **Evidence:** `.agents/evidence/M0-acceptance.md`; `.agents/evidence/M0-final-technical-verification.md`.
- **Impact:** M0 is accepted. This M0 approval did not itself authorize M1; the later direct M1 authorization is recorded in `.agents/evidence/M1-authorization.md`. G2 remains in progress.

## FND-012 — Real ALE VideoChess observation and control profile

- **Status:** verified 2026-10-15
- **Finding:** ALE-Py 0.11.2 / Gymnasium 1.4.0 resets the bundled VideoChess ROM to a standard visible start layout with RGB `(210,160,3)`, RAM `(128,)`, `Discrete(10)`, modes `[0,1,2,3,4]`, and difficulty `[0]`. The calibrated RGB board occupies x=44–107 and y=36–171; deterministic joystick repeat is one square per 33 ALE frames. RAM is diagnostic-only.
- **Evidence:** `.agents/evidence/M1-feasibility-verification.md`; final run traces and raw frame hashes under ignored `artifacts/m1/`.
- **Impact:** M1-01 and M1-02 pass for the recorded configurations. O-05 remains open for terminal behavior and official evaluation settings.

## FND-013 — RGB-verified player move and Atari reply

- **Status:** verified 2026-10-15
- **Finding:** From the real reset board, Atari actions moved the blue pawn e2–e3. The RGB board then showed the gold Atari pawn move c7–c5. `python-chess` accepted both observed transitions, and the final visible occupancy matched the shadow board under deterministic development settings and two fresh v5-default seeds.
- **Evidence:** `.agents/evidence/M1-feasibility-verification.md`; `videochess_rl/demo.py`; `tests/test_m1_ale_integration.py`; raw RGB frame hashes in the local traces.
- **Impact:** M1-03 passes. No simulator move or hidden-state value is used to claim the Atari transition.

## FND-014 — M1 terminal behavior remains unverified

- **Status:** verified observation; terminal result unverified
- **Finding:** In the initial two-ply demonstrations, each run returned reward 0 and `terminated=false`, `truncated=false`. The real game was not ended, so live terminal reward perspective and game-over behavior were not observed. The later multi-turn evidence is in FND-017; it also did not reach a terminal.
- **Evidence:** `.agents/evidence/M1-feasibility-verification.md`; `.agents/evidence/M1-04-terminal-verification.md`; traces under ignored `artifacts/m1/`.
- **Impact:** M1-04 remains UNVERIFIED; M1 and G2 stay in progress.

## FND-015 — Portable checkpoint transition after the M1 implementation commit

- **Status:** verified 2026-10-15
- **Finding:** A post-implementation full-suite run detected that the first M1 commit did not carry the checkpoint manifest for its staged file contents. The portable state and handoff were refreshed and committed at `c57e39dde883c711548049ba4410c2ec4d397ba2`; the clean-clone regression then recognized the commit transition and the full suite passed.
- **Evidence:** `.agents/evidence/M1-feasibility-verification.md`; `tests/test_agent_context.py::test_clean_clone_recovers_current_committed_state_without_local_artifacts`; commit `c57e39dde883c711548049ba4410c2ec4d397ba2`.
- **Impact:** The portable tracked manifest matches the corrected commit tree. Preserve the checkpoint-before-commit and restage-controls sequence for the next commit.

## FND-016 — M1 multi-turn RGB synchronization and mode resets

- **Status:** verified 2026-10-15
- **Finding:** The observation-driven controller advanced the shadow only after a complete RGB check of the player's move and unique Atari reply. Seven bounded mode-0 episodes verified 24 complete two-ply cycles in aggregate; the longest verified five cycles (10 plies). A new real-ALE test resets supported modes 0–4 and confirms the selected mode byte `0xEA` and RGB shape. This does not establish higher-mode gameplay behavior.
- **Evidence:** `.agents/evidence/M1-04-terminal-verification.md`; `tests/test_m1_ale_integration.py`; `tests/test_m1_environment.py`; selected local traces under ignored `artifacts/m1/m1-04/`.
- **Impact:** M1-01, M1-02, M1-03, and the turn/state-synchronization portion of M1-04 have runtime evidence. Terminal behavior remains unverified.

## FND-017 — Terminal experiment stopped at later-turn input failure

- **Status:** verified observation; cause unresolved
- **Finding:** Seven mode-0 terminal-seeking episodes used 42.870 seconds and 18,673 ALE frames. Each stopped after a later player move was not observed, despite prior RGB-verified turns. Four targeted probes plus one `e2e4` probe did not isolate the cause. Across all 12 traces, ALE reward summed to 0.0 and no trace reported termination or truncation. The traces do not establish whether the failure is source selection, target navigation/FIRE, or turn handoff.
- **Evidence:** `.agents/evidence/M1-04-terminal-verification.md`; `.agents/evidence/M1-04-experiment-budget.md`; local traces under ignored `artifacts/m1/m1-04/`.
- **Impact:** M1-04 remains UNVERIFIED. M1-001 is blocked by BLK-001 and G2 remains in progress; do not begin M2.
