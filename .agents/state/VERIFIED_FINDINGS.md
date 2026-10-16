# Verified Findings

**Canonical source for:** evidence-backed facts that future sessions should retain. Proposals belong in plans/requirements; decisions belong in ADRs; live task status belongs in the backlog/state.

Findings are append-only historical observations. FND-021 and FND-022 record the final M1 results and supersede the earlier in-progress M1/BLK-001 status statements in FND-014, FND-016 through FND-020; those earlier experiment observations remain valid for their recorded dates.

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


## FND-018 — BLK-001 failure localized to target confirmation

- **Status:** observable failure stage confirmed; internal ROM mechanism unresolved (2026-10-15)
- **Finding:** A genuine same-seed replay of `e2e3`, `e3e4`, `d2d3`, then `a2a3` reproduced the later-turn failure. RGB showed a stable source cursor, the selected-piece blink after source FIRE, and the selected pawn preview at `a3`. One-frame target FIRE did not change the board through frame 2279, including 132 subsequent no-op frames. This rejects source-selection failure, target-navigation failure, and a parser-only false negative for this replay. Target confirmation is the observed failure boundary. Controlled target FIRE durations correlate longer holds with more successful move categories, but the specific ROM-side polling/debounce/readiness cause is not established.
- **Evidence:** `.agents/evidence/BLK-001-diagnostic-20261015.md`; `.agents/evidence/BLK-001-diagnostic-20261015-r2.zip`; full local per-frame source trace `artifacts/m1/blk001-frame-replay-20261015/trace.json`.
- **Impact:** The controller now records explicit input phases, verifies source selection and each selected target from RGB, uses a separate 16-frame target FIRE, and stops without retry when the preview remains after confirmation. Keep BLK-001 active until M1-04 terminal/reward evidence is obtained.

## FND-019 — Phase-verified controller completed 20 real ALE cycles

- **Status:** verified 2026-10-15
- **Finding:** With deterministic mode 0, seed `20261015`, frameskip 1, sticky-action probability 0, and 16-frame target FIRE, the real ALE controller completed 20 consecutive legal player moves and 20 Atari replies from reset, all verified from RGB. Additional real traces accepted `e2e4`, `g1f3`, `f1b5`, one-square pawn moves including `h2h3`, and the `d3d4` / Atari `c5d4` / `d1d4` capture line. The registered v5-default profile completed two full cycles with frameskip 4 and sticky-action probability 0.25. These runs improve on the prior five-cycle ceiling, but do not prove an unbounded success rate or terminal behavior.
- **Evidence:** `.agents/evidence/BLK-001-diagnostic-20261015.md`; `.agents/evidence/BLK-001-diagnostic-20261015-r2.zip`; raw traces in ignored `artifacts/m1/` covered by `artifacts/m1/MANIFEST-20261015.sha256`.
- **Impact:** M1-02 control calibration and M1-03 legal player/Atari transitions are supported by broader runtime evidence. Keep the shadow-board RGB gate strict and retain safe-stop behavior.

## FND-020 — M1-04 remains unverified after the eighth terminal attempt

- **Status:** verified observation; terminal/reward result unverified (2026-10-15)
- **Finding:** The eighth authorized mode-0 terminal-seeking episode used the phase-verified controller with 12-frame target FIRE, ran 14,081 ALE frames in 37.973 seconds, and completed 18 full RGB-verified cycles. It stopped on a later `a2a1` because the selected-piece preview remained after target FIRE. ALE reported reward `0.0`, `terminated=false`, and `truncated=false`; no terminal event was observed. A separate 16-frame 20-cycle control replay also ended without terminal or reward.
- **Evidence:** `.agents/evidence/M1-04-terminal-verification.md`; `.agents/evidence/BLK-001-diagnostic-20261015-r2.zip`; trace `artifacts/m1/blk001-terminal-12f-20261015/trace.json`.
- **Impact:** M1-04 remains UNVERIFIED; M1-001 remains blocked by BLK-001; G2 remains in progress. Do not begin M2.

## FND-021 — Episode stop reasons and mode-4 reply readiness

- **Status:** verified and corrected 2026-10-15
- **Finding:** The previous 20-cycle experiment ended at `max_player_moves=20` with ALE reward zero and both ALE flags false; the prior runner's `status="complete"` was ambiguous. The previous 18-cycle episode ended at safe target-confirmation uncertainty, also without an ALE ending. A new mode-4 attempt stopped after ten transient RGB mismatch windows at approximately 330 reply-wait frames despite a 20,000-frame bound. After removing that early stop and requiring the unique legal reply's source cursor in RGB, actual Atari replies were observed after 594, 660, 858, and 1,221 frames. Python computation consumes host wall time but advances no emulator frames; only ALE stepping does.
- **Evidence:** `.agents/evidence/M1-G2-final-verification-20261016.md`; `.agents/evidence/M1-04-experiment-campaign-20261016.md`; mode-4 traces and RGB frames under ignored `artifacts/m1/m1-04/`; `videochess_rl/episode.py` stop categories and readiness logic.
- **Impact:** Runner caps, controller uncertainty, and actual ALE terminal/truncation are now recorded as distinct categories. Long-thinking modes wait within explicit bounds without interpreting transient visual states as game endings.

## FND-022 — Genuine ALE terminal and white-loss reward reproduced

- **Status:** verified 2026-10-15
- **Finding:** Two fresh deterministic `ALE/VideoChess-v5` mode-4 runs with seed `20261017` returned ALE reward `-1.0`, `terminated=true`, and `truncated=false` at frame 4,613 / environment step 4,609. The three verified Atari replies, terminal reward event, terminal flags, and terminal RGB pixels matched on replay. The last independently verified FEN is preserved; the attempted final `b2b3` move and inferred `d8h4#` are explicitly not presented as RGB-confirmed transitions. The live negative reward confirms White-perspective loss; the positive sign is source-documented but not observed.
- **Evidence:** `.agents/evidence/M1-G2-final-verification-20261016.md`; `.agents/evidence/M1-04-terminal-success-20261016.zip`; `.agents/evidence/logs/M1-terminal-evidence-integrity-20261016.log`; traces `artifacts/m1/m1-04/campaign4-mode4-queenmate-seed20261017/trace.json` and `campaign5-terminal-replay-seed20261017/trace.json`.
- **Impact:** M1-04 now has genuine terminal/reward, turn, and mode evidence. M1-001 is complete, BLK-001 is resolved, G2 is approved, and M2 remains pending separate authorization. O-01 through O-08 remain open.


## FND-023 — M2 simulator contract and acceptance verified

- **Status:** verified 2026-10-16
- **Finding:** The history-preserving `python-chess` simulator, fixed agent perspective, validated semantic moves, one-reply transition, automatic outcomes, decision-boundary truncation, and rollback on opponent errors are implemented. M2-01 and M2-02 pass; the focused M2 suite passed 41 tests. The full repository suite also passed 163 tests before final checkpoint synchronization; a subsequent clean-clone recovery test exposed only that the final documentation edits needed a refreshed checkpoint, retained as a failed run and rerun after checkpointing.
- **Evidence:** `videochess_rl/simulator.py`; `tests/test_m2_simulator.py`; `.agents/evidence/M2-acceptance-20261016.md`; `.agents/evidence/logs/M2-focused-suite-final-20261016.log`; `.agents/evidence/logs/M2-full-suite-precheckpoint-pass-20261016.log`; retained failure `.agents/evidence/logs/M2-full-suite-final-20261016.log`.
- **Impact:** The M2-specific behavior, focused tests, post-checkpoint 163-test suite, clean-clone recovery, and final preflight pass. M2-001 is complete; G3 remains unapproved and M3 is not authorized.

## FND-024 — Seeded baseline benchmark completed and replayed

- **Status:** verified 2026-10-16
- **Finding:** With two base seeds and both agent colors, Random Legal completed four games at W/D/L 0/2/2 and Simple Material Heuristic completed four at 3/1/0. All eight games ended by chess termination (five checkmates, three insufficient-material draws); there were no truncations, failures, or interruptions. A second run matched the configuration, aggregate summary, and all semantic per-game fields including UCI histories. This small sample is not a calibrated strength estimate.
- **Evidence:** `.agents/evidence/M2-baseline-results-20261016.md`; `.agents/evidence/M2-baseline-benchmark-20261016.json`; `.agents/evidence/M2-baseline-benchmark-repeat-20261016.json`; `.agents/evidence/M2-artifact-manifest-20261016.sha256`; `.agents/evidence/logs/M2-baseline-reproducibility-20261016.log`.
- **Impact:** M2-03 and M2-04 pass for simulator metrics only. No ALE performance, Elo, or learned competence is inferred.

## FND-025 — M2 post-review hardening verified

- **Status:** verified 2026-10-16
- **Finding:** Independent PM reviews identified eight simulator, heuristic, benchmark, serialization, provenance, and documentation concerns. The corrective cycle classified and resolved each one, fixed the confirmed P2 defects, retained the FEN-only heuristic history limitation as a bounded baseline-quality issue, and added deterministic regression coverage. The focused suite passed 58 tests on implementation revision `b3fc810`; the full repository suite passed 180 tests on final clean committed snapshot `f420bd8`, including clean-clone recovery. The regenerated two-seed/two-color benchmark and independent repeat matched semantically and all 8 game histories replayed legally. The hardening preserves ADR-0002 and the M2/ALE boundary.
- **Evidence:** `.agents/evidence/M2-post-review-hardening-20261016.md`; `.agents/evidence/M2-post-review-hardening-benchmark-20261016.json`; `.agents/evidence/M2-post-review-hardening-benchmark-repeat-20261016.json`; `.agents/evidence/M2-post-review-hardening-manifest-20261016.sha256`; source commit `b3fc8105a5dbf543267a77be77f6a8c6c76ab8e2`; full-suite verification snapshot `f420bd8a80b6f9f5edc4ae9ce40961ac76d3a581`.
- **Impact:** M2-01 through M2-04 remain supported. M2-001 remains done; G3 remains unapproved; M3 remains pending separate user authorization; O-01 through O-08 remain open.
## FND-026 — M2 squash merge reconciled

- **Status:** verified 2026-10-16
- **Finding:** GitHub reports PR #1 merged to initial-idea at 27dd9f73d2bf7545e194fe40391d0cae5f9b9003 at 2026-10-16T16:34:50Z. The remote branch matches that merge commit. main remains at its original ancestor and is 26 commits behind. There were no open PRs at verification.
- **Evidence:** POST-M2-INTEGRATION-VERIFICATION-20261017.md; GitHub PR #1 metadata; remote refs.
- **Impact:** M2-001 and M2-01 through M2-04 remain complete and integrated; G2 remains approved. G3 is unapproved and M3 remains pending separate authorization. The old handoff action to keep PR #1 unmerged is superseded by the merge fact.

## FND-027 — Candidate PGN rights and archive facts

- **Status:** verified by current source-page inspection; terms remain unresolved
- **Finding:** The third-party Lichess Elite listing reports May 2022 as 355,535 games/93 MB and describes standard games, no bullet, and a post-December-2021 2500+ versus 2300+ threshold. Its page does not state a license or archive checksum. Official Lichess database exports publish CC0 terms; official broadcast PGNs publish CC BY-SA 4.0. None of those official terms automatically establishes rights for the third-party filtered package.
- **Evidence:** https://database.nikonoel.fr/; https://database.lichess.org/; DATASET_SPEC.md; DECISION_REGISTER.md.
- **Impact:** O-06 remains open. No archive was downloaded or ingested; source selection and permitted use require owner approval.

## FND-028 — Locked runtime and local artifact manifests

- **Status:** verified 2026-10-16
- **Finding:** Offline uv lock check passed with no installation. The inspected host reported Python 3.12.3, python-chess 1.11.2, Gymnasium 1.4.0, ALE-Py 0.11.2, and CPU PyTorch 2.14.1. Its local Stockfish binary identifies as version 19 and matches the M0 executable SHA-256; its retained GPL text matches the M0 license hash. The dated local M1 manifests for 2026-10-15 and 2026-10-16 verified 1,214 and 1,388 entries. The older unversioned manifest lists 327 absent paths and was not treated as current.
- **Evidence:** PRE-M3-readiness-20261017.md; M0-final-technical-verification.md; local ignored artifact manifests in the primary checkout.
- **Impact:** No dependency addition or Stockfish search is needed for the proposed parser design. Local artifact evidence remains separate from clean-clone tracked evidence. O-01/O-07 still govern engine use.
