# M1/G2 Final Mission Verification

- **Recorded:** 2026-10-15T18:16:37Z (2026-10-16 local, Asia/Ho_Chi_Minh); final checks and Git results are appended below.
- **Repository:** `atari-videochess-rl`, branch `initial-idea`.
- **Experiment code revision:** `f2f2065c5da991394eba9204cb481daceeeba904` plus the local controller, runner, and test changes identified by SHA-256 below. The raw traces retain this starting HEAD and dirty-path list.
- **Authorization:** direct user authorization for the complete M1/G2 task, additional bounded campaign, conditional G2 acceptance, commit, and push.
- **Outcome:** **FULL SUCCESS** for the canonical M1 acceptance criteria. M1-001 is complete, BLK-001 is resolved for its documented scope, and G2 is approved. The final terminal board is not RGB-parseable; only the last verified pre-terminal FEN is claimed. M2 remains pending explicit user authorization.

## 1. Stop-reason findings

The earlier 20-cycle experiment stopped at its configured `max_player_moves=20`; its `terminated=false`, `truncated=false`, and reward `0.0` establish that it had not reached an ALE ending. The prior runner used `status="complete"` for that cap, so its status field was ambiguous. This implementation reports `runner_stopped` with `RUNNER_MAX_PLAYER_MOVES` instead.

The earlier 18-cycle experiment stopped safely on target FIRE confirmation for `a2a1`: RGB still showed the selected-piece preview, so the runner did not repeat FIRE and did not advance the shadow. ALE remained live with reward `0.0`. Earlier short episodes stopped at controller/RGB uncertainty. None of these stops was caused by an Atari human game clock, Python thinking time, an ALE terminal, or an ALE truncation.

The new mode-4 campaign exposed a second runner issue. The first mode-4 attempt stopped after ten transient/non-board visual windows, at roughly 330 opponent-wait frames, even though its configured reply wait was 20,000 frames. That was an implementation early-stop/misclassification, not an Atari timeout or a reply-budget exhaustion. The correction removed the ten-mismatch stop for modes 3–4 and requires a unique legal RGB reply with the cursor on its source square. Genuine Atari replies then appeared after 594, 660, 858, and 1,221 ALE frames.

The runner uses distinct categories: `ALE_TERMINATED`, `ALE_TRUNCATED`, `RUNNER_MAX_PLAYER_MOVES`, `RUNNER_MAX_ALE_FRAMES`, `RUNNER_MAX_ENV_STEPS`, `RUNNER_MAX_WALL_CLOCK`, `RUNNER_ARTIFACT_LIMIT`, `CONTROLLER_SOURCE_SELECTION_UNCERTAIN`, `CONTROLLER_TARGET_NAVIGATION_UNCERTAIN`, `CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN`, `CONTROLLER_BOARD_DESYNCHRONIZED`, `OPPONENT_RESPONSE_TIMEOUT`, `CHESS_RULE_INCOMPATIBILITY`, `EXCEPTION_OR_EXTERNAL_INTERRUPTION`, and `UNKNOWN`. Every ALE step contributes its reward and terminal flags before further control logic. The runner captures the terminal screen and pre-terminal frame, does not step after terminal, and leaves the shadow at the last verified board when a move is not RGB-confirmed.

The 1979 Atari manual describes opponent skill and thinking time but no human move clock. ALE advances emulated frames only through `env.step()`; Python move selection and image processing consume host wall time counted by the runner's wall-clock cap, but do not advance emulator frames. The registered environment reports a generic 108,000-frame episode limit; the terminal experiments used a stricter 54,000-frame runner limit. No truncation occurred.

## 2. BLK-001 diagnosis and timing

For the repeated `a2a3` failure, source cursor and selected-source blink were RGB-confirmed and the selected-piece preview appeared at `a3`; a one-frame target FIRE left the board unchanged through frame 2,279. Target confirmation was the observed failure boundary. Duration comparisons at 1, 4, 6, 8, 12, and 16 frames show that longer target FIRE improved later input completion, but do not establish the ROM's internal polling, debounce, or readiness implementation. That internal mechanism remains unknown.

The calibrated controller keeps source FIRE at one frame, target FIRE at 16 frames, direction holds at 33 frames, and one-frame release intervals. It observes source selection and every target preview, uses the observed cursor location to recover from one-square/diagonal movement irregularities, and never retries an uncertain FIRE. A deterministic 16-frame run completed 20 RGB-verified player/Atari cycles; the new mode-0 campaign completed 12 cycles before a configured move cap; mode 4 completed three verified cycles and then reached the terminal during the next Atari reply. Existing v5-default integration evidence still records two complete cycles at frameskip 4 and sticky-action probability 0.25.

Timing values above 16 frames (20, 24, 32, 48) were not tested after two matching authentic terminal outcomes were obtained at 16 frames. More timing optimization would not improve the M1 feasibility evidence. Sample sizes are small and repeated same-seed episodes are correlated; these results establish reproducibility and demonstrated control, not a population reliability estimate.

## 3. Terminal-seeking policy and real ALE outcome

The selected strategy was a transparent legal cooperative-loss diagnostic using a Fool's Mate trap. It requires no engine or model. A mode-0 attempt with a less focused blunder line completed 12 cycles but did not approach mate; the policy was changed to preserve the `f`- and `g`-pawn attack while keeping the legal `b`-pawn escape line. Mode 4 was then used because its actual replies and longer thinking windows were observed. No win-seeking engine, Stockfish, model, supervised data, or RL policy was used; after the loss-seeking line produced a real terminal twice, additional policies were unnecessary for M1-04.

Both final runs started from fresh ALE resets with the same seed `20261017` and settings:

| Setting | Value |
|---|---|
| Environment | `ALE/VideoChess-v5` |
| Mode / difficulty | 4 / 0 |
| Profile | deterministic development |
| Frameskip / sticky-action probability | 1 / 0.0 |
| Observation / action space | RGB `(210,160,3)` `uint8`; `Discrete(10)` |
| Python / Gymnasium / ALE-Py | 3.12.3 / 1.4.0 / 0.11.2 |
| ROM / SHA-256 | `video_chess.bin` / `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7` |
| Source / target FIRE | 1 / 16 ALE frames |
| Direction hold / release | 33 / 1 ALE frames |
| Per-episode bounds | 8 player moves; 20,000 opponent-wait frames; 54,000 ALE frames; 600 wall seconds; 32 MiB RGB artifacts |
| Move selector | legal cooperative-loss diagnostic |

The verified opening sequence was White `f2f3`, Atari `c7c5`; White `g2g4`, Atari `b8c6`; White `a2a3`, Atari `e7e5`. Each of the first three player moves and replies was confirmed by RGB board evidence. White then submitted legal `b2b3`. During Atari's subsequent thinking/reply observation, the environment returned `reward=-1.0`, `terminated=true`, and `truncated=false`. Cumulative ALE reward and White-agent reward were both `-1.0`. The event occurred at frame 4,613 and environment step 4,609; wall times were 9.883 and 9.711 seconds. No ALE step was made after termination.

The final RGB is a uniform purple game-over transition; the preceding saved RGB is a gray transition. Neither exposes a parseable chessboard. The last RGB-verified position before `b2b3` was `r1bqkbnr/pp1p1ppp/2n5/2p1p3/6P1/P4P2/1PPPP2P/RNBQKBNR w KQkq - 0 4`. The trace marks `b2b3` as attempted but not RGB-verified, and the shadow board remains at that FEN. `d8h4#` is the unique legal checkmate after the candidate `b2b3` position; this is a `python-chess` inference consistent with the authentic ALE white-loss terminal, not a visually observed move or a verified shadow transition. The ALE wrapper's pinned source describes `0xEE=1` as White checkmated / reward `−1`; the live returned reward and flags are the primary runtime evidence. The complementary `+1` sign is source-documented but was not observed live.

The two terminal traces reproduce identical verified move/reply sequences, sparse reward event, terminal flags, frame and environment-step counts, all shared frame pixel hashes, and terminal RGB pixel hash `024b23b1c9295ba28cf1c8dd716934262a5d5eabade513eaf96a95c03cd4809c`. Trace SHA-256 values:

- `artifacts/m1/m1-04/campaign4-mode4-queenmate-seed20261017/trace.json`: `9d16fca4c12c42398b286f488b1521d1cfba1ef169b53a1bfccde1dd90c99231`.
- `artifacts/m1/m1-04/campaign5-terminal-replay-seed20261017/trace.json`: `78264f381049c70b4daf195f1de5c85d1e5756325d94c134158ac30bda62fc9b`.

## 4. Campaign and resource accounting

Five new terminal-seeking episodes used 23,903 ALE frames and 48.175 episode wall seconds. The per-run configuration, verified moves, stops, and timing are in `.agents/evidence/M1-04-experiment-campaign-20261016.md`. Campaign directories contain 1,517,440 bytes across 173 files. Counting the 75.620-second baseline full suite, 43.657 seconds of focused regression work, the final 65-test M0/M1 suite (15.142 seconds), and the final full suite (80.413 seconds) conservatively, total campaign charge is 263.007 seconds. This is below the authorized limits of 12 hours, 200 episodes, and 2 GiB. All work used local CPU; no paid compute, GPU, Colab, external chess service, Stockfish gameplay, or training was used.

## 5. M1 acceptance matrix

| Criterion | Verdict | Evidence |
|---|---|---|
| M1-01 | **PASS** | Genuine ALE reset RGB/RAM shapes, action space, ROM/package metadata, and supported modes in `.agents/evidence/M1-feasibility-verification.md` and raw traces. |
| M1-02 | **PASS** | RGB-calibrated cursor, source selection, target preview, FIRE timing/release; 20-cycle run, new 12-cycle run, and terminal replay. Exact internal ROM timing cause remains unknown. |
| M1-03 | **PASS** | Legal evolving player moves and Atari replies with complete RGB board checks, including captures and previously failing input categories. Shadow state advances only after full RGB evidence. |
| M1-04 | **PASS** | Two authentic ALE mode-4 terminal/reward traces, actual flags, turns, runtime settings, package versions, ROM hash, final transition RGB, and source-backed reward perspective. Only the `−1` sign was observed live; terminal board is not parseable. |
| M1-05 | **PASS** | Safe stop on ambiguous input; no unsafe retry or unverified shadow advancement; unit/integration coverage for termination during input and thinking, truncation, budgets, and no post-terminal step. |
| M1-06 | **PASS** | Reproduction guide, stop taxonomy, bounded campaign accounting, historical/new evidence, complete raw manifest, portable bundle, and limitations are documented. |

## 6. Governance decision

M0 remains completed and user-accepted. M1-001 is complete. BLK-001 is resolved for its documented scope: phase-specific RGB control is reliable on the recorded profiles, the earlier runner stops are classified correctly, and genuine replayable ALE terminal/reward evidence now exists. The exact ROM-side FIRE mechanism and final terminal board pixels remain limitations, not unverified M1 acceptance criteria. G2 is approved under the user's conditional delegation; G3 is the next governance stage. O-01 through O-08 remain unresolved. M2 is pending separate explicit authorization and has not started.

## 7. Artifacts and integrity

- Portable M1-04 bundle retained locally (not committed): `.agents/evidence/M1-04-terminal-success-20261016.zip`, 128,574 bytes, 24 members, SHA-256 `340ba2da7ff6eeea4fc71e8769c3eb5e32b2039997870d61f8a42290c1c8f81a`. The committed report and README carry its hash, description, and reproduction information; raw traces remain outside Git.
- Bundle README: `.agents/evidence/M1-04-terminal-success-20261016-README.md`.
- Full local artifact manifest: `artifacts/m1/MANIFEST-20261016.sha256`, 1,388 files, SHA-256 `c70e611b6b24de02a30dce64037f38c2b3c3894f828de79628f3df3e33afbe9a`; local ignored raw files are not committed.
- Bundle ZIP CRC, manifest coverage/hashes, and sensitive-pattern checks passed. A decoder checked 1,039 trace-linked RGB hashes across the M1 artifact tree; 1,036 unique PNGs decoded, with zero missing files or hash mismatches. Logs: `.agents/evidence/logs/M1-terminal-evidence-integrity-20261016.log` and `.agents/evidence/logs/M1-all-artifact-rgb-integrity-20261016.log`.
- An initial ad hoc mate-verification script applied `b2b3` twice because its candidate FEN already reflected that move. The check was corrected to apply the move once from the last verified FEN; it then confirmed `b2b3` was legal and `d8h4` was the unique mate in the inferred candidate. The system Python lacks `python-chess`; the corrected audit used the existing locked `.venv`. This validation-script error did not change source or experimental evidence.
- Implementation SHA-256: `videochess_rl/episode.py` `de5df684201cbba9a72310691b4fbab09e4fb6f5d2e75b4cc024e92ac632c069`; `scripts/run_m1_terminal_experiment.py` `c9519d149c4bacf9c1e0ef8fcb99c1f8b292c5688f0ad97c5baf99bfe021338e`; `scripts/run_m1_demo.py` `8b6d9651896abe1fd320a45479101be48e5b624809ad3450c4c03e4bd44276b5`.

## 8. Tests, lock, and preflight

The following verification ran on the current M1 implementation before commit, using the locked project environment:

| Command | Result | Retained log |
|---|---|---|
| `/home/dodaonam/.local/bin/uv --offline --cache-dir .venv/.cache/uv run --locked --no-sync python -m unittest tests.test_m0_smoke tests.test_m1_control tests.test_m1_episode tests.test_m1_ale_integration tests.test_m1_environment tests.test_m1_shadow tests.test_m1_vision tests.test_m1_terminal_cli -v` | PASS, 65 tests in 15.142 s, exit 0 | `.agents/evidence/logs/M1-final-focused-suite-20261016.log` |
| `/home/dodaonam/.local/bin/uv --offline --cache-dir .venv/.cache/uv run --locked --no-sync python -m unittest discover -s tests -v` | PASS, 122 tests in 80.413 s, exit 0 | `.agents/evidence/logs/M1-full-suite-final-20261016.log` |
| `/home/dodaonam/.local/bin/uv --offline --cache-dir .venv/.cache/uv lock --check --python /usr/bin/python3` | PASS; lockfile consistent, no installation, exit 0 | `.agents/evidence/logs/M1-final-lock-check-20261016.log` |
| `python3 scripts/agent_preflight.py` | PASS, exit 0; reports expected worktree-content drift while authorized files are being changed and an artifact-manifest advisory for ignored data | `.agents/evidence/logs/M1-final-preflight-20261016.log` |

The baseline full suite before implementation changes passed 117 tests in 75.620 seconds. The increase to 122 tests is from five added episode/terminal-safety regressions; the focused M0/M1 suite contains 65 tests. `uv` is installed at `/home/dodaonam/.local/bin/uv` but is absent from the default `PATH`. The existing `.venv/bin/stockfish` symlink and UCI readiness test pass when tests run through `uv run --locked --no-sync`, which supplies the project-local executable path; no dependency installation, system change, or test weakening was needed. Staged checks, post-commit preflight, clean-clone recovery, and the final review bundle are appended below after execution.

## 9. GitHub and clean-clone recovery

The authorized remote is `origin` (`https://github.com/dodaonam/atari-videochess-rl.git`), branch `initial-idea`; initial local and remote HEAD was `f2f2065c5da991394eba9204cb481daceeeba904`, with no divergence. Final commit, push, remote HEAD, clean-clone recovery, and review-bundle results will be appended after execution. `main.py`, credentials, `.venv`, raw ROM, and ignored raw artifacts are excluded from commits; the pre-existing untracked `main.py` is preserved.

## 10. Residual limitations

1. The internal ROM polling/debounce/readiness mechanism for target FIRE is unobservable and unproven; the controller uses the measured 16-frame profile and safe RGB-gated stopping.
2. The terminal transition clears the chessboard, so the final board cannot be parsed from RGB. The last verified FEN is retained, and the proposed mating move is explicitly labeled as an inference.
3. Runtime reward evidence confirms White's loss sign (`−1`) only. The complementary sign is documented by the pinned wrapper but not observed live.
4. Mode 4 produced the terminal; modes 1–3 were reset/configuration tested but not exercised through complete gameplay. Registered v5-default gameplay has prior two-cycle evidence, not a terminal run.
5. The deterministic replay is strong repeatability evidence for one seed/configuration, not a statistical estimate of broad gameplay reliability.

## 11. Next action

G2 is technically accepted. M2 has not started; it requires a separate explicit user authorization, and O-01 through O-08 remain open.

## 12. Post-push verification

The implementation/evidence commit `f3d45923a4f183e671bdcdd6a5e29a95471b879c` was pushed to `origin/initial-idea` with a normal fast-forward. `git ls-remote origin refs/heads/initial-idea` returned the same SHA as local HEAD. The full-history clean clone at that revision reported preflight `ok=true`, zero errors, and only the expected artifact-manifest advisory because ignored raw `artifacts/` are not part of Git. The context-recovery and review-bundle exporter suite passed 57 tests in 65.321 seconds (exit 0). The first depth-1 clone could not satisfy a history-dependent test (`fatal: not a tree object`); after fetching full history, the suite passed. Full retained output: `.agents/evidence/logs/M1-post-push-cleanclone-20261016.log`.

The committed-mode M1 review bundle was generated from the pushed implementation revision. The bundle passed ZIP CRC and all 74 manifest file SHA-256 checks, with no unlisted members, raw artifacts, or nested ZIPs. It contains 75 members and is 358,635 bytes. Bundle SHA-256: `86b0023c09ba86629b5ea269db47b63a5e33efa130cb6983637ad84590b23267`. The bundle excludes ignored raw experimental files by design; the separate local terminal ZIP remains uncommitted.

The pre-existing untracked `main.py` and the local terminal evidence ZIP remain unchanged and unstaged. No `main` branch changes were made.
