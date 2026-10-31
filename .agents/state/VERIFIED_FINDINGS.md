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
- **Impact:** At the Pre-M3 review time, no archive had been downloaded or ingested. The owner later authorized bounded local/internal use of the exact May 2022 package and M3 produced a measured local artifact; package rights uncertainty remains. See FND-037 and the M3 execution report.

## FND-028 — Locked runtime and local artifact manifests

- **Status:** verified 2026-10-16
- **Finding:** Offline uv lock check passed with no installation. The inspected host reported Python 3.12.3, python-chess 1.11.2, Gymnasium 1.4.0, ALE-Py 0.11.2, and CPU PyTorch 2.14.1. Its local Stockfish binary identifies as version 19 and matches the M0 executable SHA-256; its retained GPL text matches the M0 license hash. The dated local M1 manifests for 2026-10-15 and 2026-10-16 verified 1,214 and 1,388 entries. The older unversioned manifest lists 327 absent paths and was not treated as current.
- **Evidence:** PRE-M3-readiness-20261017.md; M0-final-technical-verification.md; local ignored artifact manifests in the primary checkout.
- **Impact:** At the 2026-10-16 review, no M3 search had been authorized or run. The owner later authorized one bounded M3 teacher run; broader O-01/O-07 roles remain separate. Local data/engine evidence stays distinct from clean-clone tracked evidence.

## FND-029 — Checkpointed-tree recovery and PR validation

- **Status:** verified 2026-10-16
- **Finding:** A clean clone of feature commit 843a0bc728370ff9bc8e7a21884c7e05b82eb7c1 passed agent preflight with the portable tracked manifest matching. GitHub Actions run 38944551579 passed the same checkpointed commit with preflight and the bounded standard-library context/export suite. PR #2 was later merged into `initial-idea` at `2271b836f4dcf52e62e84413a4c456899138e953` on 2026-10-16; GitHub records the merge at 2026-10-16T19:52:29Z.
- **Evidence:** PRE-M3-readiness-20261017.md; logs/pre-m3-final-tip-cleanclone-preflight-20261017.log; GitHub Actions https://github.com/dodaonam/atari-videochess-rl/actions/runs/38944551579; PR https://github.com/dodaonam/atari-videochess-rl/pull/2.
- **Impact:** Pre-M3 readiness and delivery checks pass, and PR #2 is integrated. At the finding date M3 was not yet authorized; direct owner authorization on 2026-10-20 subsequently started M3 while G3 remained unapproved.

## FND-030 — Milestone authorization is distinct from gate closure

- **Status:** verified by focused regression tests (2026-10-17)
- **Finding:** G3 covers M2–M5 and G4 covers M6 plus only the evaluation portion of M7; neither gate's final closure is required to start the engineering work it covers. A covered milestone still requires a separate direct authorization record, active task/evidence match, and in-progress state before preflight permits it. At the finding date M3 remained unauthorized; the owner authorized M3-001 on 2026-10-20 while G3 remained unapproved.
- **Evidence:** `scripts/agent_preflight.py`; `tests/test_agent_context.py::test_preflight_detects_gate_coverage_used_as_its_own_start_prerequisite`; `tests/test_agent_context.py::test_m3_can_be_explicitly_authorized_while_g3_remains_unapproved`; `tests/test_agent_context.py::test_start_authorized_boolean_without_direct_record_is_rejected`; `.agents/evidence/PRE-M3-readiness-20261017.md` corrective-hardening section.
- **Impact:** The explicit M3 authorization is now represented in canonical state and task evidence without marking G3 complete. Plans and Boolean status alone still cannot authorize work.

## FND-031 — M3 identities and split behavior have deterministic synthetic oracles

- **Status:** contract and regression checks verified (2026-10-17)
- **Finding:** The proposed data contract distinguishes board-position signatures, replay-history state, source-game identity, normalized-game identity, position samples, and materialized UCI candidate identity. The synthetic suite verifies clock/repetition distinctions, castling/en-passant, transpositions, changed headers, promotions, deterministic hashes, candidate split inheritance/purge, and a holdout-collapse failure. These checks do not implement or profile a production dataset.
- **Evidence:** `docs/04-research/DATASET_SPEC.md`; `tests/fixtures/pre_m3_identity_vectors.json`; `tests/test_pre_m3_contracts.py`; retained full-suite log `.agents/evidence/logs/pre-m3-corrective-full-suite-20261017.log`.
- **Impact:** The synthetic identity/split vectors remain the contract checks; the authorized source distribution and purge effects have since been measured and are recorded in FND-037.

## FND-032 — Current M3-02 cannot pass from PGN-only or mock-teacher work

- **Status:** canonical acceptance alignment verified by document audit (2026-10-17)
- **Finding:** Under the unchanged M3-02 criterion, a separately authorized real bounded Stockfish run with actual version/options/score semantics is required. PGN-only output may be an intermediate artifact; mock-UCI tests establish interface behavior only. If assignment policy prohibits teacher use, M3-02 remains pending until canonical acceptance is formally changed.
- **Evidence:** `docs/06-quality/ACCEPTANCE_CRITERIA.md`; `docs/04-research/STOCKFISH_TEACHER.md`; `.agents/plans/M03-expert-dataset.md`; `docs/06-quality/TEST_STRATEGY.md`.
- **Impact:** Stockfish 19 remains the reference. The owner later authorized and completed the bounded real M3 run recorded in FND-037; unrelated engine roles remain unauthorized.

## FND-033 — M5 Double DQN can start before supervised pretraining completes

- **Status:** RL-first planning alignment verified (2026-10-17)
- **Finding:** The PM-directed contract keeps simulator-trained Double DQN as the central academic contribution. M5 core implementation and its first sanity run need not wait for a behavior-cloning M4 checkpoint; current M5-04 still requires a small pretraining-only checkpoint for the final paired comparison. Data breadth and teacher coverage are bounded, and the architecture remains open.
- **Evidence:** `docs/04-research/RL_FIRST_ALIGNMENT.md`; `docs/04-research/EXPERIMENT_PROTOCOL.md`; `docs/02-management/EXECUTION_PLAN.md`; `docs/04-research/DECISION_REGISTER.md`.
- **Impact:** The supervised-scope drift risk is mitigated, not eliminated. The presentation date is 2026-11-03 and the M3 local workload is measured; M4/M5 permissions and schedule remain to be handled before those milestones. No M4/M5 implementation or experiment was run.

## FND-034 — M3 source processing measured and release repeated

- **Status:** source-backed builds and verified repeat completed; synthetic recovery tests passed (2026-10-20)
- **Finding:** The authorized 97,163,552-byte ZIP and its 326,476,031-byte PGN member passed archive identity, CRC, streaming, and source-hash checks. Two clean builds at the same committed code/config completed in about 31 minutes each with about 289 MiB peak RSS and 39.9 MB output-directory size. The files, release identity, and source/config/code identities matched byte-for-byte. Interruption/resume invariants were exercised on synthetic fixtures; the production source release itself was generated as two fresh runs, not resumed.
- **Evidence:** `.agents/evidence/M3-reproducibility-r3-r4-20261020.json`; `.agents/evidence/M3-release-manifest-r3-20261020.json`; `.agents/evidence/logs/M3-source-teacher-repro-20261020.log`.
- **Impact:** The measured profile supports this bounded local tier; it does not authorize larger sources, broader roles, or cloud processing. Resume remains guarded by immutable source/config/code identity and verified batch journals.

## FND-035 — Checkpoint growth remains an operational follow-up, not corruption

- **Status:** verified and dispositioned (2026-10-17)
- **Finding:** At corrective-hardening recovery, `PROJECT_STATE.yaml` was 2,229,784 bytes with 96 history entries. Existing semantic checksum and portable manifest validation pass; historical entries remain intact. The historical plan called for a lossless migration design before sustained checkpoint-heavy M3 work, with earlier triggers at 4 MiB, 128 entries, or a measured checkpoint taking over 5 seconds.
- **Evidence:** `docs/02-management/RISK_REGISTER.md` RSK-010; `docs/05-operations/REPRODUCIBILITY.md`; final corrective preflight/checkpoint evidence in `.agents/evidence/PRE-M3-readiness-20261017.md`.
- **Impact:** No history was truncated or migrated. M3 completed its full source scans without per-batch canonical checkpoints; the file measured 2,810,555 bytes / 107 entries before final handoff. The 2 MiB ordinary content-hash boundary is covered by the semantic-state checksum. No M3 measurement demonstrated that risky history migration was required; retain a lossless migration design as follow-up before future checkpoint-heavy work.

## FND-036 — Stockfish teacher search and failure handling are time-bounded

- **Status:** verified by focused synthetic UCI tests and real bounded run (2026-10-20)
- **Finding:** A regression test confirmed that python-chess's engine timeout alone does not cap a UCI search when the search limit contains only nodes. M3 teacher searches now apply a node cap and `movetime`, kill an unresponsive process with a separate watchdog, record the per-root time/grace, clear the transposition hash between roots, reject a missing root PV action, and preserve partial/error records. Synthetic UCI coverage exercises successful MultiPV output, malformed PV, a process that ignores the time command, and a missing binary; the hardened implementation then passed a separate real Stockfish 19 run.
- **Evidence:** `videochess_rl/data/teacher.py`; `tests/test_m3_data.py::M3ContractTests.test_synthetic_end_to_end_release_is_reconstructible_and_hashed`; implementation commit `953c1924372ee5a153c78308c4fab44e0d104ebf`.
- **Impact:** The failure path is testable and bounded. The hardened runner completed the real authorized 128-position Stockfish 19 subset with zero failed/unattempted positions, and the teacher sidecar passed verification against both byte-identical dataset releases; see FND-037.

## FND-037 — M3 source-backed dataset, teacher, and reproducibility evidence completed

- **Status:** verified by source-backed full runs and release checks (2026-10-20)
- **Finding:** The selected May 2022 archive was downloaded only after the source decision; archive/member sizes, SHA-256, HTTP metadata, ZIP CRC, and license uncertainty are recorded. A full 355,535-record stream scan accepted 355,353 games, quarantined 182 empty records, selected 1,000 games and 20,000 positions, then purged 732 positions for cross-split board-signature overlap. The final 19,268 positions retain zero cross-split board signatures and pass the configured holdout minimum/retention checks. Two clean builds at revision `29c411bfd48dca8f1d463c758078175092639ccb` produced byte-identical files and release ID `9e3944e1e35ca0d774e479a49d9b93eb769d14e52ffec4bc6f886bd4695b8991`. The hardened Stockfish 19 run analyzed 128/128 deterministic samples; 377 MultiPV lines were typed centipawn and 3 mate, with zero failed/unattempted positions. The third-party source package license remains unstated; source and bulk data remain local and non-redistributable.
- **Evidence:** `.agents/evidence/M3-authorization-20261020.md`; `.agents/evidence/M3-source-decision-20261020.md`; `.agents/evidence/M3-source-terms-20261020.md`; `.agents/evidence/M3-source-manifest-20261020.json`; `.agents/evidence/M3-release-manifest-r3-20261020.json`; `.agents/evidence/M3-teacher-manifest-r2-20261020.json`; `.agents/evidence/M3-reproducibility-r3-r4-20261020.json`; `.agents/evidence/logs/M3-source-teacher-repro-20261020.log`; `.agents/evidence/M3-execution-20261020.md`.
- **Impact:** The four M3 criteria have runtime evidence for independent PM review. The task remains in progress until that independent review; G3 remains unapproved, and no M4–M7 work was started.

## FND-038 — M3 corrective review findings resolved and release regenerated

- **Status:** F-01 through F-08 corrected or dispositioned, with adjacent F-09 through F-11 regressions fixed and source-backed evidence regenerated (2026-10-21).
- **Finding:** Corrective review reproduced terminal/result and position-label validation gaps, watchdog/total-wall-budget semantics, incomplete full-source result-conflict auditing and bottom-K replacement/tie ordering, an ineffective overwrite test, a machine-specific Stockfish path fallback, and missing retention/quality reporting. A provenance audit found historical artifacts needed to remain distinguishable from corrected artifacts. Adjacent tests found global hash-tie ordering, source-order ranking, and zero-count rating categories needed explicit behavior. Corrections are covered by independent terminal/game/position validators, fake-UCI watchdog and cleanup tests, a full-information bottom-K oracle over permutations and late conflicts, actual overwrite refusal checks, path-resolution tests, retention-warning serialization, and zero-category statistics assertions.
- **Evidence:** `.agents/evidence/M3-corrective-hardening-20261021.md`; `.agents/evidence/M3-corrective-run-records-20261021.json`; `.agents/evidence/M3-corrective-release-manifest-r4-20261021.json`; `.agents/evidence/M3-corrective-reproducibility-r4-r5-20261021.json`; `.agents/evidence/M3-corrective-teacher-manifest-r2-20261021.json`; sanitized run logs under `.agents/evidence/logs/M3-corrective-*-20261021.log`; `tests/test_m3_data.py`.
- **Impact:** Corrected release r4/r5, built from clean revision `fbdd14d6bed487e5b1388034048eccdbe952ab48`, match byte-for-byte across nine files. The full-source scan reports 33 normalized-result conflict groups, none selected; 19,268 retained positions, zero cross-split board signatures, and 94.96%/95.63% validation/test retention. A new bounded real Stockfish 19 run analyzed 128/128 samples and is independently verified against that corrected release. M3-01 through M3-04 have technical evidence for PM review. M3-001 remains `in_progress` pending independent acceptance; the third-party package license remains unstated, PR #3 remains open/unmerged, and G3 remains unapproved.

## FND-039 — Final M3 closure hardening, regeneration, and historical compatibility

- **Status:** NEW-01 through NEW-04 reproduced and corrected; final source-backed closure releases and teacher verified (2026-10-21). E-01's final exact-PR-SHA clean-clone verification is the remaining delivery check; its non-self-referential record will be placed in the PR description after the final push.
- **Finding:** The final review confirmed that configuration could weaken the 50% holdout-retention floor; teacher CLI partial output could exit successfully; the reported wall-time boundary preceded final artifact closure; and WDL/MultiPV semantic checks were incomplete. Corrections enforce the threshold in config/split/release validation, return nonzero for partial CLI status while preserving partial artifacts, reserve and measure finalization time with post-closure overrun status, and validate WDL scale/domain/perspective plus unique rank/root actions and PV semantics. A related compatibility check found legitimate v1.0 teacher manifests do not carry run-level `status`; schema-aware validation preserves those historical runs while requiring the field in v1.1.
- **Evidence:** `.agents/evidence/M3-final-closure-20261021.md`; `.agents/evidence/M3-final-closure-record-20261021.json`; sanitized logs under `.agents/evidence/logs/M3-final-closure-*`; regression coverage in `tests/test_m3_data.py`; artifact-producing revision `40cd4e88bcaf987033a27f5f73995c5f44f21fb5`.
- **Impact:** Releases `release-final-closure-r6` and `r7` share release ID `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`; all nine files match byte-for-byte and each independently verifies against the authorized archive. The release contains 1,000 games and 19,268 retained positions with zero post-purge cross-split board signatures and >94% validation/test retention. A real Stockfish 19 run analyzed 128/128 samples with 377 cp and 3 mate lines, zero failures, validated WDL, and correct release linkage. Original schema 1.0 and corrective schema 1.1 releases verify under the final code. M3-01 through M3-04 are technically ready for independent PM acceptance; M3-001 remains in progress, PR #3 open/unmerged, G3 unapproved. The third-party curated package license remains unstated; no bulk source or derived records were redistributed.

## FND-040 — Final release verification independently recomputes split and sampling rules

- **Status:** R-01 and R-02 reproduced and fixed; R-03 corrected with versioned metadata semantics (2026-10-21).
- **Finding:** The previous verifier accepted internally hash-consistent but semantically forged game-group split assignments and sampling provenance. The verifier now recomputes canonical split assignments from the configured seed, validates seed types/equality, binds position sampling hashes to the release config, recomputes the sampling-run identity, and reconstructs the selected position IDs from game histories and configured bottom-K caps. The expected selected set must equal retained rows plus the purge ledger. A related JSON boolean/int equivalence edge is rejected explicitly. Teacher schema 1.1's elapsed “upper bound” was a reserve projection that could be exceeded by finalization; new schema 1.2 names and marks it as an estimate while observed post-closure elapsed still determines the final run status.
- **Evidence:** `.agents/evidence/M3-premerge-final-verification-20261021.md`; `tests/test_m3_data.py::M3ContractTests.test_release_verifier_recomputes_game_group_split_rule`; `...test_release_verifier_binds_sampling_fields_to_release_config`; `...test_release_verifier_reconstructs_sampled_ply_membership`; `...test_release_verifier_rejects_boolean_split_seed_even_with_consistent_hashes`; teacher finalization timing, tamper, and schema compatibility checks in the same suite; source-backed r6 and teacher verification logs under `.agents/evidence/logs/M3-premerge-*`.
- **Impact:** Historical split-schema 1.0 and 1.1 releases and final schema 1.1 r6/r7 remain verifiable without changing their stored identities. The current final-release check confirms archive/member hashes, CRC, 1,000 games, and 19,268 positions. No dataset or teacher regeneration was required because this pass changes verification and elapsed-field semantics only; the producer revision remains explicitly recorded. M3-001 remains in progress pending independent PM acceptance, PR #3 remains open/unmerged, and G3 remains unapproved.

## FND-041 — Current merged baseline and M4 authorization boundary verified

- **Status:** verified from integration history, accepted M3 evidence, canonical state/backlog, and clean-clone preflight (2026-10-22).
- **Finding:** The latest `initial-idea` baseline is `aba04d7b30fa614e2e7e74789dd610a162dd2cf0`, with M3 integration commit `2867bd58f29331a7429c649fe9e82fe620157a4d` and PR #3 merged. M0–M3 tasks are complete; M3-01 through M3-04 are accepted. M4-001 is a pending task depending on M3-001, with plan reference `.agents/plans/M04-supervised-pretraining.md`; no active milestone/task or start authorization exists, and G3 remains unapproved. Older dated pre-merge records that say M3 is pending/in progress remain historical evidence and were not rewritten.
- **Evidence:** `.agents/evidence/M3-acceptance-20261021.md`; `.agents/evidence/M3-postmerge-integration-verification-20261021.md`; `.agents/evidence/PRE-M4-readiness-20261022.md`; current `PROJECT_STATE.yaml` and `BACKLOG.yaml`; final `PRE-M4-*.log` entries under `.agents/evidence/logs/`; open review PR #4 and successful exact-head context/preflight run [39805987282](https://github.com/dodaonam/atari-videochess-rl/actions/runs/39805987282).
- **Impact:** Pre-M4 prepares M4 interfaces and bounded experiment instructions without changing milestone/gate acceptance or authorization. PR #4 is open and unmerged. The exact accepted M3 artifact identity is known, but the raw files are not present in this checkout; verify them before any future training.

## FND-042 — Checkpoint growth is bounded by controls; lossless migration remains open

- **Status:** measured and regression-tested in an isolated clean worktree (2026-10-22).
- **Finding:** The merged baseline state measured 3,431,959 bytes / 131 history-array entries. Compact serialization and unchanged-checkpoint detection retain every record and make a no-op repeat. A clean-worktree changed snapshot added 58,132 bytes and one entry in 0.905 seconds; the unchanged repeat took 0.400 seconds and changed neither file nor history. The first feature-branch checkpoint took 0.809 seconds and produced a 3,551,699-byte state with 133 history-array entries, retaining the prior record. A projected write above 4 MiB including a 64 KiB reserve is refused before writing state/handoff or creating a workspace identity. History record IDs and checkpoint metadata remain intact in the tests.
- **Evidence:** `scripts/agent_checkpoint.py`; `tests/test_agent_context.py` checkpoint compaction/no-op/size-guard tests; `.agents/evidence/PRE-M4-readiness-20261022.md`; `docs/02-management/RISK_REGISTER.md` RSK-010; final portable clean-clone recovery log in `.agents/evidence/logs/`.
- **Impact:** No historical checkpoint was discarded and recovery remains readable. RSK-010 is still open because changed checkpoints continue to grow the state and the guard is a ceiling, not archival capacity. Design and test a lossless backward-compatible history migration before sustained checkpoint-heavy work or before a required checkpoint approaches the guard.

## FND-043 — Model candidate helper represents automatic terminal states

- **Status:** deterministic synthetic contract tests pass (2026-10-22).
- **Finding:** M2's automatic-outcome boundary includes checkmate, stalemate, fivefold repetition, and the seventy-five-move rule. Fivefold repetition and the seventy-five-move rule can leave legal moves in `Board.legal_moves`; therefore `legal_action_candidates()` checks `Board.outcome(claim_draw=False)` before listing candidates. Automatic terminal positions yield an empty candidate set while claim-only draws remain outside the M2 action contract.
- **Evidence:** `videochess_rl/action_contract.py`; `tests/test_pre_m4_contracts.py::PreM4ChessContractTests.test_automatic_repetition_and_seventy_five_move_terminals_have_no_candidates`; `.agents/evidence/PRE-M4-readiness-20261022.md`.
- **Impact:** A future inference/Double DQN adapter will not score legal moves after an automatic terminal outcome. The simulator Board remains the rules/terminal source of truth; no terminal condition is inferred from a neural score.

## FND-044 — Caught post-provisional checkpoint failures restore the prior pair

- **Status:** verified by fault injection on code revision `181d6b2e9eb8e49b8cd5cf7aa0401f763d5678f8` (2026-10-22).
- **Finding:** A final workspace-snapshot exception and a final serialized-size overflow, each injected after provisional state/handoff writes, both return failure and restore the exact original `PROJECT_STATE.yaml` and `SESSION_HANDOFF.md` bytes. The prior checkpoint IDs and full history remain unchanged; a workspace identity created for the failed attempt is restored to its original absence; no agent temp files remain. Actual preflight on the fixture succeeds with only expected dirty-source drift.
- **Evidence:** `scripts/agent_checkpoint.py`; `tests/test_agent_context.py::AgentContextRecoveryTests.test_checkpoint_rolls_back_provisional_files_after_final_snapshot_failure`; `tests/test_agent_context.py::AgentContextRecoveryTests.test_checkpoint_rolls_back_provisional_files_after_final_size_guard_failure`; `.agents/evidence/logs/PRE-M4-hardening-checkpoint-20261022.log`.
- **Impact:** Caught operational exceptions no longer leave a half-refreshed checkpoint pair. Separate atomic file replacements are still not a transaction against process/power loss; preflight detects a stale handoff marker, and incomplete rollback requires inspection before further work.

## FND-045 — Synthetic M2 observations match validated M3 replay at the semantic boundary

- **Status:** verified with deterministic synthetic records on code revision `181d6b2e9eb8e49b8cd5cf7aa0401f763d5678f8` (2026-10-22).
- **Finding:** Two integration fixtures construct M3-style game and position records, replay matching UCI sequences through the M2 observation history, and compare canonical model FEN, mover, legal UCI set, and played-candidate identity. Coverage includes White/Black to move and legal en passant. The 12 Pre-M4 boundary tests pass; no real accepted M3 release, tensor encoder, neural adapter, or M5 execution is exercised.
- **Evidence:** `tests/test_pre_m4_contracts.py::PreM4ChessContractTests.test_m2_observation_history_matches_m3_positions_for_white_and_black`; `tests/test_pre_m4_contracts.py::PreM4ChessContractTests.test_m2_and_m3_history_reconstruction_preserves_en_passant_target`; `.agents/evidence/logs/PRE-M4-hardening-contracts-20261022.log`.
- **Impact:** R03 is PASS for the implemented semantic boundary only. R03 does not establish tensor feature parity or neural/M5 compatibility by execution.

## FND-046 — Lossless checkpoint-history archive verified on a dependent branch

- **Status:** migration and synthetic recovery suite verified on `feature/rsk010-lossless-checkpoint-history` (2026-10-23); integration is pending owner review and merge.
- **Finding:** At merged PR #4 baseline `16fc01a3fe731c0a0be127026cc64d049c0cf550`, the canonical state was 3,919,833 bytes with 139 inline records plus the current checkpoint. The migration preserves the exact source-state bytes in a verified backup and reconstructs 140 unique ordered logical records in a versioned SHA-256 archive; compact state measured 65,811 bytes. The archive validates independently in preflight and from a clean clone. History remains lossless and total archive storage continues to grow linearly.
- **Evidence:** `.agents/evidence/RSK-010-checkpoint-history-migration-20261023.md`; `docs/05-operations/CHECKPOINT_HISTORY.md`; `scripts/checkpoint_history.py`; `scripts/migrate_checkpoint_history.py`; `tests/test_checkpoint_history.py`.
- **Impact:** The merged `initial-idea` branch still uses legacy inline history until this migration is reviewed, merged, and clean-clone verified. M4 remains pending because migration integration, ADR-0003 decision, O-01 clarification, and exact M3 artifact access are not yet satisfied. No G3 or M4 authorization is implied.

  **Final implementation-code verification update (2026-10-22 UTC; tested revision `71c623cb31cee9b476d679a870aa5765d05e12ef`):** archive verification reports 143 unique archived records plus the separate current checkpoint (144 represented identities); canonical state is 67,156 bytes and archive storage is 1,808,362 bytes across 14 files. Focused checkpoint/context suite: 75/75 passed. Full suite: 268/269 passed, with only the existing Stockfish UCI-readiness smoke test failing because no executable is installed in the environment. A clean clone verified the archive and passed preflight with no errors; evidence logs are linked from the migration record. RSK-010 remains open until the PR is merged and the integration branch is independently verified.

## FND-047 — Checkpoint-history migration integrated and verified

- **Status:** verified on integration commit `d9f0872c120fb2408343859c938257e3962f2e09` (2026-10-23).
- **Finding:** PR #5 is merged into `initial-idea`. The integrated archive verifier reports 148 ordered archived records with logical SHA-256 `da88335f4091c2b8a95c15d70e7cd7951c3705d47a7dd921aa2cfc0ff803302a`; the canonical state separately represents the current checkpoint, for 149 checkpoint identities. `PROJECT_STATE.yaml` is 70,382 bytes and the 19 archive files total 1,924,692 bytes at this baseline. Archive verification and canonical preflight pass. The 2026-10-22 branch-only status in FND-046 is historical and is superseded here.
- **Evidence:** `.agents/evidence/RSK-010-checkpoint-history-migration-20261023.md`; `.agents/evidence/PRE-M4-final-closure-20261023.md`; `docs/05-operations/CHECKPOINT_HISTORY.md`; PR #5 merge `d9f0872c120fb2408343859c938257e3962f2e09`.
- **Impact:** The former canonical-state capacity failure mode is resolved by lossless archive storage. Total archive growth and non-transactional crash boundaries remain monitored operational limitations; do not truncate history.

## FND-048 — Accepted M3 release locally available and verified

- **Status:** verified read-only on integration code revision `d9f0872c120fb2408343859c938257e3962f2e09` (2026-10-23).
- **Finding:** The exact accepted release ID, manifest SHA-256 and split-assignment digest match. The project verifier checked all seven manifest outputs and replayed 1,000 games / 19,268 retained positions; supplementary checks confirmed all nine file sizes/hashes unchanged before and after, 182 rejections, split counts, unique IDs, each played move exactly once in its legal candidate list, and zero post-purge cross-split board signatures.
- **Evidence:** `.agents/evidence/M3-release-local-verification-20261023.md`; `.agents/evidence/M3-release-local-verification-20261023.json`; `.agents/evidence/logs/M3-release-local-verification-20261023.log`.
- **Impact:** M3 data availability is no longer a readiness blocker. Reverify immediately before future use; keep artifacts local and non-redistributed under the owner authorization and third-party license uncertainty.

## FND-049 — ADR-0003 accepted; O-01 remains an external-policy question

- **Status:** owner decision recorded 2026-10-23; external course-policy evidence not found in the repository review.
- **Finding:** The owner accepted ADR-0003 according to its proposed action-conditioned legal-candidate architecture. Owner-confirmed choices of custom PyTorch, Double DQN, ALE target/wrappers, supporting behavior cloning, and bounded Stockfish teacher assistance are distinguished from instructor rules. No course brief/instructor response establishing those permissions was found in the reviewed repository. The conditional M4-001 record still requires applicable authoritative O-01 evidence before activation.
- **Evidence:** `.agents/evidence/ADR-0003-acceptance-20261023.md`; `docs/02-management/decisions/ADR-0003-pretraining-model-interface.md`; `docs/04-research/DECISION_REGISTER.md`; `.agents/evidence/M4-001-authorization-conditional-20261023.md`.
- **Impact:** ADR-0003 is not pending, but M4-001 remains pending and unauthorized until O-01 is evidenced and the conditional authorization is activated in canonical state/backlog. G3 remains unapproved.

**Current-status update (2026-10-27):** The M4-001/O-01 impact above records the state on 2026-10-23. The project owner's dated decision now closes O-01 for internal planning and execution authorization and supersedes that O-01-only activation condition. It does not claim instructor approval. See FND-051 and the 2026-10-27 final closure report.

## FND-050 — Final Pre-M4 verification and handoff completed

- **Status:** full suite passed on PR-head revision `16cea814e623021cccce8ff05ac698c3c0d6afc9`; clean-clone recovery, preflight, and CI also passed on that exact head (2026-10-23).
- **Finding:** `uv run --locked --no-sync --project /home/dodaonam/Projects/atari-videochess-rl python -m unittest discover -s tests` passed 269/269. A prior direct Python invocation failed only the M0 Stockfish UCI smoke test because that invocation did not add the configured venv `bin` directory to PATH. The existing Stockfish 19 executable and GPL text SHA-256 values match pinned M0 evidence; the correct `uv` invocation exposed the existing executable. No engine was installed, no test was changed, and the smoke test only performed UCI readiness/ping. A clean clone at the same PR head verified 152 archive records, passed preflight with no errors and the expected artifact warning, and passed 47/47 context/recovery tests. GitHub `Repository preflight` run 39971527886 passed on that head; it is not the full Python suite.
- **Evidence:** `.agents/evidence/PRE-M4-final-verification-20261023.json`; `.agents/evidence/logs/PRE-M4-final-verification-20261023.log`; `.agents/evidence/logs/PRE-M4-full-suite-uv-20261023.log`; `.agents/evidence/logs/PRE-M4-stockfish-env-20261023.log`; `.agents/evidence/logs/PRE-M4-pr6-final-clean-clone-20261023.log`; [PR #6](https://github.com/dodaonam/atari-videochess-rl/pull/6).
- **Impact:** R08 is PASS. The full-suite failure report from the direct invocation remains as historical diagnostic evidence, superseded by the successful configured-environment run. PR #6 is open for owner review. M4-001 remains pending because authoritative external O-01 course-policy evidence is still required; G3 remains unapproved.

**Current-status update (2026-10-27):** The PR, O-01, and M4-001 statements above describe the 2026-10-23 state. PR #6 is being completed under the current mission; O-01 is closed internally, and its external-evidence limitation is informational. Current integration and post-merge results are linked from the 2026-10-27 final closure report.

## FND-051 — O-01 closed internally; M4-001 can be handed off without another owner confirmation

- **Status:** verified from the direct project-owner decision and canonical records (2026-10-27).
- **Finding:** The owner closed O-01 for internal project planning and execution authorization and confirmed the selected technical scope: ALE/VideoChess-v5 with existing wrappers; independently implemented PyTorch Double DQN as the principal RL algorithm; bounded supporting behavior cloning; and only the previously approved bounded Stockfish teacher/pretraining scope. The initial M4 behavior-only run excludes Stockfish scores and teacher targets. The decision supersedes the O-01-only external-confirmation prerequisite in the earlier conditional M4-001 authorization. No separate instructor-policy approval is evidenced or claimed; any actual authoritative prohibition remains binding for the affected activity.
- **Evidence:** `.agents/evidence/O-01-owner-decision-20261027.md`; dated addendum in `.agents/evidence/M4-001-authorization-conditional-20261023.md`; `.agents/state/PROJECT_STATE.yaml`; `.agents/tasks/BACKLOG.yaml`; `tests/test_agent_context.py::AgentContextRecoveryTests.test_m4_authorization_can_be_ready_without_claiming_implementation_started`.
- **Impact:** After all Pre-M4 checks and PR integration pass, M4-001 is `pending` and ready to start, with `start_authorized: true`, `active_milestone: null`, and no active task. G3 remains unapproved and is not an entry prerequisite. O-02–O-08 remain scoped separately; the absence of instructor-policy evidence alone does not block M4-001.

## FND-052 — Accepted M3 release reverified read-only in the owner-specified worktree

- **Status:** verifier and supplementary artifact checks passed (2026-10-27).
- **Finding:** The exact nine-file release at the owner-specified sibling-worktree path matches release ID `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`, manifest SHA-256 `be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12`, and semantic split-assignment SHA-256 `84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e`. It contains 1,000 games, 19,268 retained positions (15,196/2,015/2,057 split), 732 purged positions, and 182 rejections; cross-split board-signature overlap is zero. All nine sizes and hashes were unchanged before/after inspection and match the accepted 2026-10-23 inventory.
- **Evidence:** `.agents/evidence/M3-release-local-verification-20261027.md`; its machine-readable JSON and sanitized verifier log.
- **Impact:** The exact accepted release is locally available and verified but remains outside Git. Reverify it before future loading. This does not prove neural feature parity, create a neural loader, or provide M4 training evidence. The third-party package license remains unstated; preserve the local-only/no-redistribution boundary.

## FND-053 — RSK-010 archive integrity reverified on the Pre-M4 candidate

- **Status:** archive verifier passed on the `feature/pre-m4-final-closure` candidate worktree at base revision `a41d6f14014727570f55dfa2d015d4ad80250445` (2026-10-27 11:02 UTC).
- **Finding:** `python3 scripts/migrate_checkpoint_history.py verify` verified 155 ordered archived records with logical SHA-256 `d543d1debe05bd6f55eeb23bd0df28751f41b1191a99f4efcafb2ad0100706c3`; manifest SHA-256 is `cd9ee9d6c7cc37cd3bd6e58a08eb8d30181819fce7864398cafb293dc98d314f`. The source-state backup hash matched the state pointer. The current checkpoint `cp-a41d6f14-20261027T104833810611Z` is separate from and not duplicated in the archive. The verifier checks record identity/order, segment and backup hashes, and logical digest; its output is retained.
- **Evidence:** `.agents/evidence/logs/RSK-010-pre-m4-verify-20261027.log`; `.agents/state/PROJECT_STATE.yaml`; `.agents/state/checkpoint-history/manifest.json`.
- **Impact:** The existing PR #5 migration remains lossless and verifies on the current Pre-M4 candidate. A clean-clone verification at the final PR/merged revision is still required before closeout. Archive storage and verification I/O grow with retained records; multi-file updates remain non-crash-atomic as documented.

## FND-054 — Pre-M4 PR candidate recovers in a clean clone

- **Status:** verified on clean clone of PR #6 candidate `7ba2a21d2436941c5a57bad41628738149a8ea1d` (2026-10-27).
- **Finding:** The clone passed `agent_preflight.py` with zero errors and only the expected artifact-manifest warning; it verified 157 ordered archive records with logical SHA-256 `17a29916db981da71f0b55ac41d13ff319e56f4a263ea73d677e84d3638440f4`; focused context/archive tests passed 76/76; the full Python suite passed 270/270 in 96.687 seconds. The installed Python 3.12.3 direct dependencies matched `uv.lock`, and the Stockfish 19 UCI readiness smoke test passed with the configured executable on `PATH`. The clone remained clean. GitHub Actions run 40494322054 passed on the same SHA; that workflow covers preflight/context/bundle tests, not the full suite.
- **Evidence:** `.agents/evidence/PRE-M4-final-closure-20261027.md`; `.agents/evidence/PRE-M4-final-closure-20261027.json`; clean-clone logs under `.agents/evidence/logs/PRE-M4-pr6-7ba2a21-clean-*`.
- **Impact:** Pre-merge recovery and regression checks are evidenced on this PR candidate. PR #6 merge and a fresh clean-clone check of the resulting integration commit remain required. This finding does not claim M4 implementation, training, M4 acceptance, or G3 approval.

## FND-055 — PR #6 merge and post-merge recovery verified

- **Status:** verified from a fresh clean clone of `initial-idea` at PR #6 merge commit `89d085d1865d07b10660e82119488960f766d819` (2026-10-27).
- **Finding:** Archive verification passed for 158 ordered records, manifest SHA-256 `7ef79d51d0084c791ce355f8040a093ed51ebdfbfab90de68a7ac439e4d74386`, logical SHA-256 `1e91619d8dff846c7753aa305447a7d812a1c0592db994679c1d03bea738bf12`, and verified source backup. Current checkpoint `cp-7ba2a21d-20261027T112212896594Z` is separate from the archived records. Canonical preflight passed with no errors and only the expected artifact-manifest warning; portable content/index matched and the clone had no dirty paths. Focused recovery tests passed 76/76 and the full suite passed 270/270. GitHub Actions run `40495781206` passed on the exact PR head `4bde469bc5199ccac3e87d75db205bcc2d9d53c4`.
- **Evidence:** `.agents/evidence/PRE-M4-final-closure-20261027.md` and `.json`; `.agents/evidence/RSK-010-checkpoint-history-migration-20261023.md`; sanitized post-merge logs `.agents/evidence/logs/PRE-M4-postmerge-89d085d-*.log`; PR #6 merge record.
- **Impact:** Pre-M4 is integrated and independently verified. M4-001 remains pending but authorized and ready to start; no model, training, M4 acceptance, M5 implementation, or G3 approval is claimed.

**Current-status update (2026-10-27):** M4-001 has since started under the direct owner authorization and is currently blocked by BLK-002 after the fixed sanity gate failed. See FND-056 and the canonical task/state records. The Pre-M4 `ready_to_start` state above is retained as historical context.

## FND-056 — Fixed M4 sanity gate has a structural top-1 ceiling below threshold

- **Status:** exact accepted M3 release verification/replay and fixed-gate conflict diagnosis completed read-only on 2026-10-27; gate result failed on source revision `4562dddd80d302bdbb49e1191c97bd71ac7e9938`.
- **Finding:** The M4 loader verified release ID `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`, manifest SHA-256 `be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12`, and split-assignment SHA-256 `84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e`, then replayed and tensorized the prescribed fixed 128 lexical training samples. After 500 updates at seed `20261022`, cross-entropy was `0.02195480228497465` (threshold `<=0.05`) and legal top-1 was `126/128 = 0.984375` (required `>=0.99`, i.e. 127/128). A read-only diagnostic compared all complete unpadded input feature arrays and ordered legal UCI identities and found two pairs of identical model inputs with conflicting `played_move_uci` labels. The maximum deterministic top-1 accuracy on the fixed set is therefore 126/128, so the current gate cannot pass under the accepted input contract. All nine release files remained unchanged. No full training, held-out evaluation, simulator evaluation, or pretrained checkpoint was produced.
- **Evidence:** `.agents/evidence/M4-02-sanity-gate-blocker-20261027.md`; `.agents/evidence/logs/M4-02-sanity-gate-diagnostic-20261027.json`; `.agents/evidence/logs/M4-sanity-gate-r2-20261027.txt`; `.agents/evidence/logs/M4-02-sanity-gate-diagnostic-20261027.txt`; preserved run artifact directory `/home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r2/`.
- **Impact:** M4-02 failed; do not start full training under the unchanged criterion. M4-03 and M4-04 remain not run. M4-001 is blocked by BLK-002; G3 remains unapproved and M5 has not started. A new explicit owner protocol decision is needed to resolve the fixed-sample label conflict without modifying the accepted M3 source release or silently changing ADR-0003.

**Superseding status update (2026-10-27):** The PM, acting under explicit project-owner delegation, issued the authorized narrow M4-02 sample-selection amendment recorded at `.agents/evidence/M4-02-protocol-amendment-20261027.md`. BLK-002 is resolved as a protocol blocker, and canonical M4-001/milestone state returned to `in_progress`. The original gate remains failed historical evidence; the revised gate has not yet run. The M4-02 pass thresholds remain unchanged.

## FND-057 — M4-02 input-distinct sanity protocol authorized

- **Status:** PM decision recorded on 2026-10-27; implementation and the new gate are pending at this finding's creation.
- **Finding:** Protocol revision `M4-02-distinct-effective-inputs/1.0` selects the first 128 training examples with distinct complete effective `videochess-model-input/1.0` identities in ascending `sample_id` order. Identity excludes labels and provenance, includes unpadded tensors, mask/length semantics, and ordered semantic UCI candidates, and is checked against actual collated inputs. SHA-256 matches are verified against canonical bytes. The accepted M3 release, labels, model/input contract, seed `20261022`, AdamW settings, 500-update cap, CE `<=0.05`, top-1 `>=99%`, and all resource limits are unchanged. This resolves only the infeasible old fixed-selection rule; it does not pass M4-02 or authorize full training before a successful revised gate.
- **Evidence:** `.agents/evidence/M4-02-protocol-amendment-20261027.md`; original diagnosis and failed-run chain in `.agents/evidence/M4-02-sanity-gate-blocker-20261027.md` and `.agents/evidence/logs/M4-02-sanity-gate-diagnostic-20261027.json`; code in `videochess_rl/model/dataset.py` and `videochess_rl/model/cli.py`; selector regressions in `tests/test_m4_data.py` and `tests/test_m4_training.py`.
- **Impact:** BLK-002 is resolved as an activation blocker. M4-001 is authorized/in progress, but the revised sanity gate remains mandatory before full training. M4-03/M4-04 remain unverified; G3 remains unapproved; M5/M6 have not started.

**Final status update (2026-10-27):** The PM-amended gate passed on fresh weights at 140 updates, and the corrected three-seed training, validation-only selection, one frozen test evaluation, engine-free checkpoint reload, and 40-game simulator evaluation completed within cumulative limits. M4-01 through M4-04 passed; see `.agents/evidence/M4-final-acceptance-20261027.md` and its machine-readable companion. The original gate failure and r3 safe-load failure remain unchanged historical failures.

## FND-058 — M4 acceptance evidence completed

- **Status:** M4-01 through M4-04 verified on source revision `7b3c9074a2d932fec6d7732ee08e99b9de10a135` (2026-10-27); PR #8 integration remains a separate delivery check.
- **Finding:** The revised M4-02 input-distinct selection passed at update 140 with CE `0.03854484462305363` and legal top-1 `127/128`. The accepted three-seed run selected seed `20261024`, epoch 11, by validation NLL `2.4127401237590953`; the selected behavior-only checkpoint is SHA-256 `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4`, with 121,897 parameters. The frozen test split was evaluated once; checkpoint reload/inference succeeded with Stockfish absent; the 40-game simulator schedule completed with zero truncations/failures. Focused tests passed 124/124 and the full suite passed 313/313.
- **Evidence:** `.agents/evidence/M4-final-acceptance-20261027.md`, `.agents/evidence/M4-final-acceptance-20261027.json`, `.agents/evidence/M4-02-protocol-amendment-20261027.md`, and sanitized test/run verification logs under `.agents/evidence/logs/`. Local model and experiment artifacts remain outside Git at the run path in the acceptance report.
- **Impact:** M4-001 can be recorded complete with all four criteria supported. G3 remains unapproved; M5 has not started or been authorized by this M4 mission. The local-only M3/M4 artifact availability and third-party license limitation remain relevant to future use.

## FND-059 — M4 integration and post-merge verification completed

- **Status:** PR #8 merged into `initial-idea`; exact merge commit `c0a284304d602817922772d08f0ff7904af7ae20` passed fresh clean-clone verification on 2026-10-27.
- **Finding:** The final PR head `1f8f7db986f613818c7f70770d08c2c3a460a1cb` passed the GitHub Repository preflight `context` check. A fresh clone of the merge commit passed agent preflight with zero errors and a matching portable manifest (only expected `ARTIFACT_MANIFEST_REQUIRED` warning), RSK-010 archive verification (186 records; logical SHA-256 `59ab0ad59f99aefc7ae5d336e03a9543bc7ee387fbd637b09dd476f7af3c8b71`), all 19 external M4 artifact manifest checks, 124 focused tests, and 313 full tests; final clone worktree was clean.
- **Evidence:** `.agents/evidence/M4-postmerge-delivery-verification-20261027.md`, its JSON companion, and the three logs under `.agents/evidence/logs/M4-postmerge-clean-clone-*-c0a2843-20261027.txt`.
- **Impact:** M4-001/M4 are complete and integrated. G3 remains unapproved; M5 has not started and remains pending separate authorization. The dataset and trained checkpoint remain outside Git at their approved local paths; the context CI workflow is not represented as a regression-suite run.

## FND-060 — Pre-M5 retrospective review and artifact-transfer evidence

- **Status:** Pre-M5 engineering audit completed against `initial-idea` baseline `906178775d48e98e64c709673bfe73177dd15c02` (2026-10-28); see final report for exact final feature revision and per-command logs.
- **Finding:** PR #8 integrated M4 implementation at `c0a284304d602817922772d08f0ff7904af7ae20`; PR #9 integrated post-merge evidence at the baseline. The available GitHub review records for both PRs contained no review submissions. This is recorded as a historical review-process exception, not PM acceptance. The accepted M3 r6 release and M4 r4 19-file bundle were locally reverified read-only. The real M4 checkpoint (`724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4`) transferred shared representation weights into a fresh seeded Q head in a separate process; target initialization matched online; representative behavior and Q actions were legal; Stockfish was absent; source artifacts were unchanged. A bounded CPU profile was performed without RL learning.
- **Evidence:** `.agents/evidence/PRE-M5-readiness-20261028.md`; `.agents/evidence/logs/PRE-M5-M3-immutable-check-20261028.log`; `.agents/evidence/logs/PRE-M5-transfer-verification-20261028.log`; `.agents/evidence/logs/PRE-M5-feasibility-profile-final-20261028.log`.
- **Impact:** The real M4 representation-transfer boundary is verified on the available accepted artifact. M5 itself remains not started and unauthorized. The retrospective engineering audit does not replace independent PM review of the historical PRs or the new Pre-M5 PR.

## FND-061 — Completed task next-action invariant enforced

- **Status:** confirmed and corrected in the Pre-M5 feature worktree (2026-10-28); fresh preflight and regression results are recorded in the final readiness report.
- **Finding:** `M4-001` was `done` while retaining a nonempty `next_action`, contrary to `.agents/PLANS.md`. The stale action was cleared without changing its completion evidence. `scripts/agent_preflight.py` now rejects a nonempty action for `done` or `cancelled` tasks, and `tests/test_agent_context.py` contains a regression that exercises this invariant. `M5-001` is represented as `pending`, depends on the completed M2/M3/M4 tasks, and requires a separate direct M5 authorization; it is the canonical next task while active milestone/task remain null.
- **Evidence:** `.agents/tasks/BACKLOG.yaml`; `.agents/state/PROJECT_STATE.yaml`; `scripts/agent_preflight.py`; `tests/test_agent_context.py`; `.agents/evidence/PRE-M5-readiness-20261028.md` and its verification logs.
- **Impact:** Completed M4 evidence remains intact; M5 remains pending and unauthorized; G3 remains unapproved. Preflight now protects the task action invariant against regression.

## FND-062 — Terminal bootstrap candidates are distinct from raw Board legal moves

- **Status:** M2 terminal behavior re-executed and the M5 boundary clarified in the Pre-M5 candidate (2026-10-28).
- **Finding:** An automatic seventy-five-move draw can end an episode while the reconstructed terminal `python-chess.Board` still has syntactically legal moves. `tests/test_m2_simulator.py::test_seventyfive_move_rule_is_automatic_after_full_transition` verifies the simulator reports termination and draw reward. M5 replay validation must still verify that Board outcome and terminal reason, but the model-boundary next-candidate set is empty and no argmax is evaluated. This differs from valid nonterminal/time-limit truncation states, whose bootstrap candidate list must equal the Board's legal UCI set.
- **Evidence:** `docs/03-technical/RL_ALGORITHM.md`; `docs/06-quality/M5_TEST_MATRIX.md`; `tests/fixtures/m5_double_dqn_targets.json`; `.agents/evidence/logs/PRE-M5-terminal-draw-oracle-20261028.log`.
- **Impact:** This prevents a terminal draw with available chess moves from accidentally bootstrapping. No M5 learner has been implemented or tested; the fixture is a future algorithm oracle only.

## FND-063 — M5 evaluation game-count mismatch corrected

- **Status:** Corrected during final Pre-M5 consistency review (2026-10-28); exact-head regression and final PR checks are recorded in the readiness evidence.
- **Finding:** The initial M5 config assigned ten games to each opponent/color pair while the protocol described ten evaluation seeds × two opponents × two colors as a 40-game checkpoint schedule. The count was ambiguous and inconsistent. The versioned proposal now runs one game per `(evaluation seed, opponent, agent color)`, yielding 40 games per frozen policy checkpoint. Nine policy checkpoints (M4-only, three warm-start seeds, three scratch seeds, and two fixed baselines) yield 360 planned games; the cap is 20 minutes per checkpoint and three hours aggregate. No M5 benchmark was run.
- **Evidence:** `configs/rl/m5-double-dqn-v1.json`; `docs/04-research/M5_EXPERIMENT_PROTOCOL.md`; `docs/06-quality/M5_TEST_MATRIX.md`; `tests/test_m5_contract_fixtures.py`; `.agents/evidence/PRE-M5-readiness-20261028.md` and its exact-head verification logs.
- **Impact:** A standard-library regression now derives the game count from seeds/opponents/colors/checkpoints and checks config/protocol agreement, preventing this schedule ambiguity from reappearing. M5 remains unauthorized and unstarted.

## FND-064 — Complete M5 evaluation and training-feasibility limits reconciled

- **Status:** PM findings remediated in the Pre-M5 feature candidate (2026-10-28); exact-head verification and independent PM disposition are recorded separately.
- **Finding:** The prior nine-checkpoint/360-game schedule omitted six DDQN initialization snapshots, so it could not support the declared before/after-RL comparison. Its checkpoint wording also conflated decision-milestone evaluation snapshots with episode-boundary resumable state. The prior resource profile did not bracket variable history or sufficiently characterize the update-time consequence of a 45-minute per-run cap.
- **Resolution:** The operative schedule now contains 15 policy snapshots and 600 planned games, retains warm/scratch and paired pre/post comparisons, and defines crossed seed/evaluation-seed uncertainty without claiming identical independent-agent trajectories. Algorithm/configuration contracts distinguish exact decision snapshots from complete episode-boundary resume bundles and define honest mid-episode hard-stop behavior. CPU-only v2.1 and observed-range profiles quantify the 600-game projection and expose that a 10,000-decision run's measured p95 projection exceeds the 45-minute cap before overhead. The proposed post-authorization actual-replay probe must halt before paired runs and seek PM direction if p95 remains over cap.
- **Evidence:** [Pre-M5 remediation report](../evidence/PRE-M5-remediation-20261028.md); [v2.1 profile](../evidence/logs/PRE-M5-feasibility-profile-v2.1-20261028.json); [observed-range update profile](../evidence/logs/PRE-M5-history-budget-20261028.json); `docs/03-technical/RL_ALGORITHM.md`; `docs/04-research/M5_EXPERIMENT_PROTOCOL.md`; `configs/rl/m5-double-dqn-v1.json`; `tests/test_m5_contract_fixtures.py`.
- **Impact:** Future evaluation has a valid intended comparison design, but full CPU training feasibility remains marginal and is not guaranteed. No M5 campaign was started, no cap was changed, and the finding does not authorize M5. FND-063 remains intact as historical evidence of the earlier nine-checkpoint correction; this finding supersedes its schedule numbers for current use.

## FND-065 — M5 source-version changes recovered and semantically assessed

- **Status at finding publication:** Historical checkpoint and replay sources recovered byte-for-byte; training/replay/checkpoint differences audited; independent PM disposition was pending (2026-10-30). That pending status was superseded by the later M5 PM acceptance and G3 approval.
- **Finding:** The recovered earlier `checkpoint.py` SHA-256 is `19ab713b5a1450c2e4506d9d761768317e0b48fb96a3cb0083965d6a037bc410`; earlier `replay.py` SHA-256 is `5ae4d3d928c524539bcf6b29f4102f09b246d5703b66539f2fad4aa7e2aaa278`. Replay buffer insertion/eviction/sampling/state operations and journal append are AST-identical to the later code. Checkpoint changes are limited to verification and restoration. The full historical CLI files remain unavailable, but the complete continuation transcript contains the old selector excerpt and four relevant patch events; the two final-seed runs were fresh `attempt-0000` attempts with no resume parent. No learning-distribution change is evidenced. An optional historical full-history restore differential was stopped after 20:16.95 and is explicitly incomplete; actual later-code checkpoint restoration and deterministic old/current restore tests passed.
- **Evidence:** `.agents/evidence/M5-source-recovery-20261030.json`; `.agents/evidence/M5-source-recovery-verification-20261030.json`; `.agents/evidence/M5-source-semantics-20261030.json`; `docs/04-research/M5_REMEDIATION_AUDIT.md`; `.agents/evidence/logs/M5-source-focused-tests-20261030.log`; `.agents/evidence/logs/M5-authentic-source-restore-equivalence-20261030-r2.log`; the two successful actual restoration logs listed in the forensic audit.
- **Impact:** The previously unverified replay-sampling concern is not supported by the recovered implementation. The source aggregate remains different across seed groups, whole CLI bytes remain a provenance limitation, and the campaign has only three independent training-seed clusters. The evidence is ready for independent PM disposition; no supplemental training/evaluation is authorized or indicated. G3 remains unapproved and M6 has not started.

- **Dated G3 disposition:** The PM accepted M5-03/M5-04 with the disclosed limitation, resolved BLK-003 by risk acceptance, verified PR #11 merge, and approved G3. RSK-014 remains an accepted residual. See `.agents/evidence/M5-PM-acceptance-20261030.md` and `.agents/evidence/G3-final-approval-20261030.md`; M6 remains unauthorized.

## FND-066 — G3 approved after verified M5 integration

- **Status:** Independently approved and integration identity verified on 2026-10-30.
- **Finding:** The PM approved G3, covering M2–M5 under ADR-0001, after PR #11 merged into `initial-idea`. Merge commit `e0b434530df51b08595e3896c175f81b4a8f8c64` and reviewed feature HEAD `c9df9db36c6146a34ef301052a206fe8a3512ffc` have identical tree `793c3e9268d188a7673feb0b680554f94b902fd9`. The clean-clone merge-commit preflight and checkpoint-history verification passed; the complete available test suite passed with one expected skip because private M4 artifacts are unavailable in the clone.
- **Evidence:** `.agents/evidence/G3-final-approval-20261030.md`; PM decision `https://github.com/dodaonam/atari-videochess-rl/pull/11#issuecomment-6519216543`; merge PR #11; `.agents/evidence/logs/G3-postmerge-checkpoint-e0b.log`; `.agents/evidence/logs/G3-postmerge-suite-e0b.log`.
- **Impact:** Canonical state records G3 approved and G4 as the next governance gate. M6 is only the next engineering milestone; it remains pending separate direct authorization and is not started. The M5 simulator scope, accepted M5-03/M5-04 limitations, and accepted residual RSK-014 are unchanged.

## FND-067 — M6 Stage 3 v2 corrective execution and post-run verification

- **Status:** Owner-authorized Stage 3 v2 completed on frozen source commit `91f51b14690eba12e9e4fd25a4fc1671801fac0d`; independent PM acceptance remains pending.
- **Finding:** The 20-entry paired M5 schedule ran exactly once per policy/seed. Eleven attempts reached authoritative ALE termination with finite White-perspective reward -1.0 (four Warm, seven Scratch); nine incomplete attempts remain separately classified. The verified primary endpoint is 222/232 Warm and 163/173 Scratch. All 1,871 unexpected cursor displacements were corrected; board desynchronization count is zero. The final run artifact manifest covers 4,159 files / 728,148,524 bytes. The v1 manifest, ledger, and run-manifest identities remain unchanged.
- **Evidence:** [M6 final report](../evidence/M6-001-final-report-v2-20261031.md); [execution record](../evidence/M6-stage3-v2-execution-record-20261031.json); [post-run verification](../evidence/M6-stage3-v2-postrun-verification-20261031.json); [artifact manifest](../evidence/M6-stage3-v2-artifact-manifest-20261031.json); focused/full test logs under `../evidence/logs/`. Raw v2 traces and RGB remain local-only at `artifacts/m6/v2/m6-stage3-v2-91f51b14690e-d05d42400cfc/`.
- **Impact:** M6-01 through M6-05 have engineering evidence ready for independent PM review; no PM acceptance or G4 approval is claimed. V2 uses the same seeds as v1 with a changed horizon, so results are not pooled and are not independent held-out evidence. No Elo or Warm/Scratch superiority claim is made.
