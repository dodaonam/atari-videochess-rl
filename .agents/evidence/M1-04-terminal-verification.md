# M1-04 Terminal, Reward, Turn, and Mode Verification

- **Recorded at:** 2026-10-15T10:45:37Z.
- **Branch / source revision:** `initial-idea` at `dd67267ff85670c674d0d6d08c129ce10692798f`; working tree contained authorized M1 changes.
- **Authorization:** `.agents/evidence/M1-authorization.md` and the current direct user task.
- **Plan:** `.agents/plans/M01-ale-feasibility.md`.
- **Verdict:** **PARTIAL. M1-04 remains UNVERIFIED; M1-001 and G2 are not complete.**

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

### Final remote clean-clone recovery

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
