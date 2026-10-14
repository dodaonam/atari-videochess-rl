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
- **Impact:** Clean checkouts can recover canonical project state without inheriting local workspace-only artifacts. M0 remains pending explicit authorization.
