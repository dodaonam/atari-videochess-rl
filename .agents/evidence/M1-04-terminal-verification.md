# M1-04 Terminal, Reward, Turn, and Mode Verification

- **Recorded at:** 2026-10-15T10:55:03Z.
- **Branch / source revision:** `initial-idea` at `dd67267ff85670c674d0d6d08c129ce10692798f`; working tree contained authorized M1 changes.
- **Authorization:** `.agents/evidence/M1-authorization.md` and the current direct user task.
- **Plan:** `.agents/plans/M01-ale-feasibility.md`.
- **Verdict:** **PARTIAL. M1-04 remains UNVERIFIED; M1-001 and G2 are not complete.**

## Latest BLK-001 continuation (2026-10-15)

This section supersedes the earlier attempt counts and unresolved-stage description below. The earlier evidence is retained as the historical baseline and is not rewritten.

- **Current diagnosis:** A same-seed later-turn `a2a3` replay localized the observable failure to target confirmation. RGB verified the source cursor, the selected-piece blink after source FIRE, and the selected piece's preview at `a3`. A one-frame target FIRE produced no board transition through frame 2279, including 132 subsequent no-op frames. Controlled target FIRE durations (1, 4, 6, 8, 12, and 16 frames) show that a longer target press correlates with more successful inputs. This does not prove the ROM-side poll/debounce/readiness mechanism. See [BLK-001 diagnostic evidence](BLK-001-diagnostic-20261015.md) and the [portable diagnostic ZIP](BLK-001-diagnostic-20261015-r2.zip).
- **Controller change:** The controller now records input phases, verifies source selection and each selected-target preview from RGB, uses a separate 16-frame target FIRE, and stops without retry if the selected preview remains after FIRE. The full-board shadow transition check is unchanged.
- **Reliability:** The 16-frame deterministic mode-0 replay completed 20 player moves and 20 Atari replies over 15,356 ALE frames in 41.255 seconds. A 12-frame terminal-seeking episode completed 18 full cycles over 14,081 frames in 37.973 seconds and then safely stopped on `a2a1`. A registered v5-default run completed two cycles at frameskip 4 and sticky-action probability 0.25. Targeted traces also verified `e2e4`, `g1f3`, `f1b5`, `d3d4`, Atari `c5d4`, and `d1d4` capture inputs.
- **Terminal result:** The eighth authorized terminal-seeking episode (seed `20261015`, mode 0, difficulty 0, frameskip 1, sticky-action probability 0.0) returned cumulative ALE reward `0.0`, `terminated=false`, and `truncated=false`; no live terminal was observed. The trace records ROM SHA-256 `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`, ALE-Py 0.11.2, Gymnasium 1.4.0, frame number 14,081, and 14,081 environment steps. The last verified FEN is `r2r2k1/3n1ppp/2nbb3/ppp1p3/8/PqPp1PPP/R7/1NBQKBNR w K - 0 19`.

### Current M1 decision

| Criterion | Current verdict | Evidence |
|---|---|---|
| M1-01 | **PASS** | Genuine ALE RGB observations, runtime configuration, ROM hash, and package versions are retained in the real traces. |
| M1-02 | **PASS** | Source selection, selected-target preview, direction holds, and target FIRE duration are calibrated against real RGB outcomes; deterministic and v5-default runs are present. |
| M1-03 | **PASS** | Real legal player moves and Atari replies were verified from full-board RGB evidence across the 20-cycle run and targeted move categories. |
| M1-04 | **UNVERIFIED** | No real terminal or nonzero reward was observed; zero reward alone cannot establish reward-sign behavior. |
| M1-05 | **PASS** | Ambiguous source/target/confirmation states stop without unsafe retries or shadow advancement; regression tests and real safe-stop trace cover the behavior. |
| M1-06 | **PASS** | Reproduction guide, diagnostic report, per-frame evidence, manifests, and portable bundle are retained. |

**Current gate decision:** M1 remains in progress and G2 remains in progress because M1-04 is unverified. BLK-001 stays active. The eight-episode terminal budget is exhausted. Do not begin M2, do not approve G2, and do not close O-01 through O-08.

Recorded current result: M1-04 remains UNVERIFIED; M1-001 remains blocked by BLK-001; G2 remains in progress.

## Evidence classification

This report separates source facts, synthetic/unit-test evidence, and real ALE observations. Only the real runtime observations can establish a real terminal or reward event. No simulator position, mocked terminal flag, or source comment is counted as a live terminal result.

## Official ALE and installed Gymnasium behavior

The [ALE-Py 0.11.2 `VideoChess.cpp` wrapper](https://github.com/Farama-Foundation/Arcade-Learning-Environment/blob/v0.11.2/src/ale/games/supported/VideoChess.cpp) defines `TURN_WHITE` as `0x82` and reads RAM `0xE1` for the current player. When that value is `0x82`, the wrapper checks `0xEE`: `0` adds `+1` and marks terminal (black checkmated); `1` adds `-1` and marks terminal (white checkmated); `3` is documented as ongoing. During the other player's search/move computation the wrapper sets reward to zero. The wrapper resets reward to zero and terminal to false on reset. This describes white-perspective ALE reward semantics; the live tests below did not observe either nonzero case.

The same pinned source returns supported modes `[0, 1, 2, 3, 4]` and reads `0xEA` when applying a mode. Installed runtime checks reset each of these five modes and read back the selected `0xEA` value; difficulty is `[0]`. Only mode 0 received gameplay testing. Other modes were not tested for complete turns, terminal behavior, or reliability.

The installed Gymnasium/ALE-Py `AtariEnv.step` source returns `is_terminal = ale.game_over(with_truncation=False)` separately from `is_truncated = ale.game_truncated()`. The runtime smoke check confirms those are distinct returned booleans. Source inspection establishes the interface semantics, not that VideoChess actually reached terminal in these runs.

## Real ALE runtime

- Python `3.12.3`; Gymnasium `1.4.0`; ALE-Py `0.11.2`.
- Environment `ALE/VideoChess-v5`, packaged ROM `video_chess.bin`, SHA-256 `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`.
- Terminal-seeking profile: mode `0`, difficulty `0`, deterministic development settings (`frameskip=1`, sticky-action probability `0.0`).
- Observation: RGB `(210,160,3)` `uint8`; diagnostic RAM `(128,)` `uint8`; action space `Discrete(10)`.
- RAM values `0xE1`, `0xE4`, `0xEA`, and `0xEE` were recorded only as diagnostics. Move selection and shadow advancement used RGB and legal `python-chess` transitions, not RAM.
- The registered v5-default profile remains separately covered by the real integration tests (frameskip `4`, sticky-action probability `0.25`). The terminal-seeking runs did not use it.

## Bounded terminal-seeking results

Seven terminal-seeking episodes were run. Each completed the listed number of full player/Atari cycles through RGB before the next player action could not be verified. The longest trace verified 5 cycles (10 plies) and stopped at `h2h3`.

| Attempt | Seed | Full RGB-verified cycles | Next player move not verified | Frames | Wall seconds |
|---|---:|---:|---|---:|---:|
| `attempt-001` | 20261015 | 3 | `g1f3` | 2,611 | 5.135 |
| `attempt-002` | 20261016 | 4 | `d1d4` | 3,104 | 6.164 |
| `attempt-003` | 20261017 | 5 | `h2h3` | 3,922 | 9.039 |
| `attempt-004` | 20261018 | 3 | `d3d4` | 2,199 | 7.085 |
| `attempt-005` | 20261019 | 3 | `a2a3` | 2,279 | 4.539 |
| `attempt-008` | 20261015 | 3 | `a2a3` | 2,279 | 4.914 |
| `attempt-009` | 20261022 | 3 | `a2a3` | 2,279 | 5.994 |

Across those seven episodes, 24 complete two-ply cycles (48 verified plies) were recorded, consuming 18,673 ALE frames and 42.870 seconds. Every episode ended as a partial controller run, not an ALE ending. All 12 retained episode/probe traces together used 26,161 frames and 60.583 seconds. The trace directory contains 1,384,023 bytes, below the 250 MiB artifact cap. No per-episode or total budget cap was reached; the terminal-seeking runs stopped after repeated failure at the same input boundary made another same-profile run unlikely to add evidence.

The same early sequence repeatedly verified `e2e3`, an observed Atari reply, and further legal turns. Atari replies were observed from RGB and were not predetermined; for example, the opponent varied between `c7c5`, `b8c6`, `e7e5`, `c5d4`, and `d7d5` across the traces. Three additional targeted probes after `d7d5` (`b2b3`, `d3d4`, and `e4xd5`), one knight-route probe, and one `e2e4` control probe also failed to establish a complete later move. These are control probes, not additional terminal-seeking episodes.

Every retained trace reports cumulative ALE reward `0.0`, `terminated=false`, and `truncated=false`. No checkmate, timeout, or other game-ending position was observed. The exact failure cause remains unresolved: the cursor route can be observed, but RGB does not expose a reliable selected-target state; the failed action could be source selection, selected-target navigation/FIRE, or a turn-handoff issue. The evidence does not distinguish these explanations. The runner stops and keeps the last verified shadow board rather than guessing.

## Unit and integration test evidence

`tests/test_m1_episode.py` tests the transparent diagnostic selector, current-position legality, safe stop on failed target FIRE, missing Atari replies, bounded wait/frame budgets, unexpected cursor displacement, reward sign conversion, and separate termination/truncation handling using an environment double. Those tests establish code behavior only. Real ALE integration tests verify reset, RGB observations, action calibration, the original `e2e3` closed loop, an evolving-board player move, and the registered v5-default profile. A new real-ALE mode test resets each mode 0–4 and confirms RGB shape and diagnostic mode byte `0xEA`.

## M1 acceptance matrix

| Criterion | Verdict | Evidence and limit |
|---|---|---|
| M1-01 | **PASS** | Real reset, ROM hash, RGB/RAM shapes, action space, supported modes/difficulty; each mode reset was checked. |
| M1-02 | **PASS** | Real cursor movement and one-frame FIRE calibration; deterministic and v5-default closed loops remain covered. Later-turn reliability is still a separate blocker. |
| M1-03 | **PASS** | Real RGB-observed player moves and Atari replies matched legal evolving shadow positions; longest terminal attempt verified five complete cycles. |
| M1-04 | **UNVERIFIED** | Wrapper reward semantics are source-verified and synthetic reward/flag handling is tested, but no real ALE terminal, truncation, or nonzero reward occurred. Gameplay beyond mode 0 is untested. |
| M1-05 | **PASS** | RGB mismatch and failed input leave the shadow at the last verified state; negative paths stop without using an unverified position. |
| M1-06 | **PASS** | Runtime settings, source/test/runtime evidence categories, trace limits, failure diagnosis, and reproduction steps are recorded here and in the M1 guide. |

Because M1-04 is a mandatory composite criterion, M1 remains **in progress/blocked**, G2 remains **in progress**, and conditional G2 approval is not exercised. M2–M7 remain not started; M2 still requires separate explicit authorization. O-01 through O-08 remain open.

## Task evidence-log mismatch audit

At the start of this continuation the reported six `TASK_EVIDENCE_LOG_MISMATCH` errors were not reproducible. The six existing verified command/test entries in `BACKLOG.yaml` each matched their retained report's exact command, result, and `Exit code` line. No duplicate historical log was added. `python3 scripts/agent_checkpoint.py` completed at checkpoint `cp-dd67267f-20261015T101338477281Z`; its post-checkpoint preflight passed with one expected `ARTIFACT_MANIFEST_REQUIRED` warning for ignored `artifacts/`. A direct preflight also returned no errors. Final fresh command records are below.

## Retained verification command records

### Initial full-suite run before checkpoint refresh

- **Executed:** 2026-10-15T10:25:28Z–10:26:06Z.
- Command: `uv --offline --cache-dir .venv/.cache/uv run --locked --no-sync python -m unittest discover -s tests -v`
- Result: `FAIL: 111 tests; one failure in test_project_context_can_be_recovered_without_chat_history because the recorded Git snapshot predated the intentional state/evidence edits.`
Exit code: 1
- **Resolution:** Refreshed the checkpoint at `cp-dd67267f-20261015T102644531118Z` and reran the same complete suite; the rerun passed.

### Full suite after checkpoint refresh

- **Executed:** 2026-10-15T10:26:50Z–10:27:30Z.
- Command: `uv --offline --cache-dir .venv/.cache/uv run --locked --no-sync python -m unittest discover -s tests -v`
- Result: `PASS: 111 tests in 39.759s.`
Exit code: 0
- **Coverage:** context and recovery, export security/manifest, M0 smoke, M1 controls, RGB/shadow, episode safety, real ALE integration, and real reset checks for modes 0–4.

### Final staged-snapshot full suite

- **Executed:** 2026-10-15T10:33:22Z–10:34:52Z, after checkpoint `cp-dd67267f-20261015T103311916852Z` and staging the checkpoint control files.
- Command: `uv --offline --cache-dir .venv/.cache/uv run --locked --no-sync python -m unittest discover -s tests -v`
- Result: `PASS: 111 tests in 89.626s.`
Exit code: 0
- **Coverage:** same full context/export/M0/M1 suite; `test_project_context_can_be_recovered_without_chat_history` passed against the final staged checkpoint snapshot.

### Lock check

- **Executed:** 2026-10-15T10:27:56Z.
- Command: `uv --offline --cache-dir .venv/.cache/uv lock --check --python /usr/bin/python3`
- Result: `PASS: lockfile consistent; no dependency installation performed.`
Exit code: 0

### Checkpoint

- **Executed:** 2026-10-15T10:26:44Z.
- Command: `python3 scripts/agent_checkpoint.py`
- Result: `PASS: wrote checkpoint cp-dd67267f-20261015T102644531118Z; its post-checkpoint preflight passed with one expected ARTIFACT_MANIFEST_REQUIRED warning for ignored artifacts.`
Exit code: 0

### Experiment evidence bundle

- **Path:** `artifacts/m1/m1-04-evidence-20261015.zip` (ignored local artifact).
- **Contents:** 2 sanitized traces and 5 genuine RGB frames, plus README and SHA-256 manifest; ZIP CRC, member hashes, and credential/path scan passed.
- **Size:** 24,503 bytes.
- **SHA-256:** `d9c341b6130572325e0b8f4a156414753f03eeb23386ed452416079f920eb42f`.
- **Scope limit:** The bundle demonstrates multi-turn progress and a failed later input, not terminal/reward success.

### Final staged pre-commit checks

- **Executed:** 2026-10-15T10:32:22Z.
- Command: `python3 scripts/agent_preflight.py`
- Result: `PASS: no errors; one expected ARTIFACT_MANIFEST_REQUIRED warning for ignored artifacts.`
Exit code: 0
- Command: `git diff --cached --check`
- Result: `PASS: no whitespace or conflict-marker errors.`
Exit code: 0
- **Checkpoint before these checks:** `cp-dd67267f-20261015T103132462083Z`; checkpoint postflight passed with the same expected artifact warning.
- **Staged inventory:** 23 authorized paths, listed below. The untracked `main.py`, private chat history, ignored `.venv`, caches, and local artifacts/ZIPs are excluded.

```text
.agents/evidence/M1-04-experiment-budget.md
.agents/evidence/M1-04-terminal-verification.md
.agents/evidence/M1-feasibility-verification.md
.agents/state/BLOCKERS.md
.agents/state/PROJECT_STATE.yaml
.agents/state/SESSION_HANDOFF.md
.agents/state/VERIFIED_FINDINGS.md
.agents/tasks/BACKLOG.yaml
docs/02-management/RISK_REGISTER.md
docs/05-operations/M1-ALE-REPRODUCIBILITY.md
docs/06-quality/TEST_STRATEGY.md
scripts/run_m1_terminal_experiment.py
tests/test_m1_ale_integration.py
tests/test_m1_control.py
tests/test_m1_environment.py
tests/test_m1_episode.py
tests/test_m1_shadow.py
tests/test_m1_vision.py
videochess_rl/controller.py
videochess_rl/demo.py
videochess_rl/episode.py
videochess_rl/shadow.py
videochess_rl/vision.py
```

Recorded result: M1-04 remains UNVERIFIED; M1-001 is blocked by BLK-001; G2 remains in progress.

## Clean-clone portability regression and correction

After the first push, a fresh clone of remote `initial-idea` at `cd9bd56cd3ac41eedd603a933d6886935a70e361` recovered G2/M1/BLK-001 correctly with `python3 scripts/agent_preflight.py` (exit 0); `main.py`, `chat_history.md`, `.venv`, and `artifacts/` were absent. The environment-independent context/export suite then ran 57 tests and had one failure in `test_clean_clone_recovers_current_committed_state_without_local_artifacts`.

The failure was in that test's synthetic Git fixture: it copied committed file bytes with `write_bytes()` but did not preserve executable mode `100755` for the new terminal runner. The fixture committed it as `100644`, so the synthetic tree did not match the portable manifest and preflight correctly reported `unexplained_git_transition`. The real clone retained Git mode and preflight classified the transition as portable. The fixture now reads modes from `git ls-tree` and reapplies executable mode when materializing files. The focused regression test and context/export suite passed after this correction.

### Context/export rerun after mode-preserving fixture correction

- **Executed:** 2026-10-15T10:40:20Z–10:41:41Z.
- Command: `python3 -m unittest tests.test_agent_context tests.test_export_review_bundle -v`
- Result: `PASS: 57 tests in 80.487s.`
Exit code: 0
- **Coverage:** the current-committed-state clean-clone regression, portable milestone transitions, checkpoint/cache recovery, and export security/manifest behavior.
- **Note:** this rerun was performed in the source checkout after correcting the synthetic fixture.

### Focused recovery tests after final follow-up checkpoint

- **Executed:** 2026-10-15T10:42:28Z–10:42:56Z.
- Command: `python3 -m unittest tests.test_agent_context.AgentContextRecoveryTests.test_clean_clone_recovers_current_committed_state_without_local_artifacts tests.test_agent_context.AgentContextRecoveryTests.test_project_context_can_be_recovered_without_chat_history -v`
- Result: `PASS: 2 recovery tests in 27.118s.`
Exit code: 0

### Remote clean-clone recovery after mode-fix push

- **Executed:** 2026-10-15T10:44:19Z–10:45:37Z.
- **Clone source/revision:** `https://github.com/dodaonam/atari-videochess-rl.git`, branch `initial-idea`, HEAD `5e97f71b6c1100b01e4e6f5a9617836eb0f18d19`.
- **Command:** `git clone --quiet --branch initial-idea --single-branch https://github.com/dodaonam/atari-videochess-rl.git <temporary-directory>`.
- **Local-only absence:** `main.py`, `chat_history.md`, `.venv`, and `artifacts/` were absent.
- **Recovered state:** G2 `in_progress`; G0/G1 approved; M1 in progress; M1-001 blocked by BLK-001 and dependent on M0-001; M2 still requires separate authorization; O-01 through O-08 remain open.
- **Preflight command:** `python3 scripts/agent_preflight.py`.
- **Preflight result:** `PASS`; portable manifest matched the clone commit transition; exit code `0`.
- **Context/export test command:** `python3 -m unittest tests.test_agent_context tests.test_export_review_bundle -v`.
- **Context/export test result:** `PASS: 57 tests in 74.401s.`; exit code `0`.
- **Limit:** The clean clone did not install dependencies and did not run M0/M1 ALE/PyTorch/Stockfish smoke tests. Those environment-dependent checks ran in the locked local environment instead.

Recorded result: Clean clone 5e97f71: preflight passed and 57 context/export tests passed; no local-only files were present.

## Final verification at published HEAD

- **Revision:** `7f4c6f5b7d5129f41d324979302012df8a3699d5` on `origin/initial-idea`.

### Full local suite

- **Executed:** 2026-10-15T10:48:13Z–10:49:44Z.
- Command: `uv --offline --cache-dir .venv/.cache/uv run --locked --no-sync python -m unittest discover -s tests -v`
- Result: `PASS: 111 tests in 89.692s.`
Exit code: 0
- This run includes the corrected executable-mode clone fixture and the M1 mode-reset test.

### Final remote clean clone

- **Executed:** 2026-10-15T10:50:04Z–10:55:03Z.
- **Clone HEAD:** `7f4c6f5b7d5129f41d324979302012df8a3699d5`.
- **Local-only absence:** `main.py`, `chat_history.md`, `.venv`, and `artifacts/` were absent.
- Preflight command: `python3 scripts/agent_preflight.py`.
- Preflight result: `PASS: no errors; portable baseline matched remote clean-clone commit.`
- Preflight exit code: `0`.
- Context/export test command: `python3 -m unittest tests.test_agent_context tests.test_export_review_bundle -v`.
- Context/export test result: `PASS: 57 tests in 75.281s.`
- Context/export test exit code: `0`.
- Recovered G2 `in_progress`, G0/G1 approved, M1 active with M1-001 blocked by BLK-001, M2 still separately gated, and O-01 through O-08 open. No dependencies were installed in the clone.

The full clean-clone suite covers context and export behavior only. M0/M1 runtime smoke tests remained in the locked local environment and were not repeated in the dependency-free clone.


## BLK-001 continuation: final test results (2026-10-15)

- **M1-focused command:** `./.venv/bin/python -m unittest tests.test_m1_control tests.test_m1_episode tests.test_m1_ale_integration tests.test_m1_environment tests.test_m1_shadow tests.test_m1_vision -v`
- **M1-focused result:** `PASS: 50 M1 unit and real ALE integration tests in 13.238s.` Exit code `0`; executed 2026-10-15T16:13:50Z–16:14:03Z.
- **Full-suite command:** `./.venv/bin/python -m unittest discover -s tests -v`
- **Full-suite result:** 113 tests in 67.098s; 112 passed, 1 failed, exit code `1`. The sole failure was the M0 Stockfish readiness check because no Stockfish executable was available in PATH. The checkpoint-related context recovery test passed. Executed 2026-10-15T16:12:15Z–16:13:23Z.
- Sanitized retained logs: [`BLK-001-m1-suite-20261015.log`](logs/BLK-001-m1-suite-20261015.log) and [`BLK-001-full-suite-20261015.log`](logs/BLK-001-full-suite-20261015.log).
- `uv` and the venv's `pip` module were unavailable, so lock-check and `pip check` could not be run. No dependencies were installed. `git diff --check` passed.


### CLI output collision safety

The terminal experiment CLI now refuses an existing trace path, an existing `frames/` directory, or a trace symlink. Four focused regression tests cover fresh paths, existing traces, prior frame output, and a broken trace symlink. The expanded M1-focused suite passed 54 tests in 14.383 seconds with real ALE integration checks; see [`BLK-001-m1-suite-final2-20261015.log`](logs/BLK-001-m1-suite-final2-20261015.log).


### Final full-suite rerun with output-collision guard

- **Executed:** 2026-10-15T16:18:25Z–16:19:31Z.
- **Command:** `./.venv/bin/python -m unittest discover -s tests -v`
- **Result:** 117 tests in 64.894s; 116 passed; one failed; exit code `1`. The sole failure remained `test_stockfish_answers_uci_readiness_without_searching` because the Stockfish executable is unavailable in PATH. The M1-focused 54-test suite, all four new CLI safety checks, and the context recovery check passed.
- **Log:** [`BLK-001-full-suite-final2-20261015.log`](logs/BLK-001-full-suite-final2-20261015.log).


### Portable clean-clone fixture correction and final context/export run

The recovery test initially failed because its synthetic Git repository copied ignored-but-committed evidence files, then ordinary `git add --all` omitted those files. This made the fixture's commit differ from the checked-in portable manifest and caused valid relative evidence links to appear broken. The fixture now force-adds the copied HEAD tree, preserving ignored paths that are already committed. It does not change runtime code or weaken preflight checks.

- **Source revision:** `75498a61b258f293a77d4059088004b647a1c75f`.
- **Executed:** 2026-10-15T16:29:07Z–16:30:02Z.
- **Command:** `python3 -m unittest tests.test_agent_context tests.test_export_review_bundle -v`.
- **Result:** PASS, 57 tests in 54.451s; exit code `0`. This includes the committed-state synthetic clean-clone recovery test and the source-checkout context recovery test.
- **Log:** [`BLK-001-context-export-final-20261015.log`](logs/BLK-001-context-export-final-20261015.log), SHA-256 `37e091c00350cc962aac2115b2c1a522fa2ffebd71b03f2bd12e45a9f8aff4a6`.
- **Artifact manifest:** `artifacts/m1/MANIFEST-20261015.sha256`, 1,214 entries; `sha256sum --check --status` passed.
- **M1 decision:** M1-04 remains UNVERIFIED because no real ALE terminal or nonzero reward was observed. G2 remains in progress and BLK-001 remains active.


### GitHub clean-clone verification

- **Executed:** 2026-10-15T16:32:32Z–16:33:40Z.
- **Remote:** `https://github.com/dodaonam/atari-videochess-rl.git`, branch `initial-idea`, cloned HEAD `3cded0908ae17b598f31f7674a4fbe3d9a078c8c` (the pushed revision at verification time).
- **Preflight:** `python3 scripts/agent_preflight.py --json` passed with no errors; the expected `ARTIFACT_MANIFEST_REQUIRED` warning remained because raw local experiment artifacts are not in Git.
- **Modes and local files:** all 71 tracked file modes matched Git; only `scripts/run_m1_terminal_experiment.py` has mode `100755`. `main.py`, `chat_history.md`, `.venv`, and raw experiment artifacts were absent; only the tracked `artifacts/m1/MANIFEST-20261015.sha256` was present.
- **Tests:** `python3 -m unittest tests.test_agent_context tests.test_export_review_bundle -v` passed all 57 tests in 65.196 seconds, exit code `0`. No dependencies were installed.
- **Retained sanitized log:** [`BLK-001-remote-cleanclone-20261015.log`](logs/BLK-001-remote-cleanclone-20261015.log), SHA-256 `69264bd7f358dfb10e160120c46a94bbc609b79d201287bc71f098ce1473110e`.
