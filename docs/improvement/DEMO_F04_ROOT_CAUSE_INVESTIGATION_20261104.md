# DEMO-F04 Root-Cause Investigation

**Verdict:** `DEMO_F04_UNRESOLVED_WITH_EVIDENCE_BLOCKER`
**Investigation date:** 2026-11-04
**Base:** `main` at `b7bbd8a6e64373dfe8b81ca88ad23184dff802d4`, tree `b3eac5aba1a427f40824648c18b9b3a7a5a00a8f`
**Investigation branch:** `investigate/demo-f04-root-cause-20261104`

## 1. Executive finding

The failure was independently reproduced with the selected Double DQN snapshot and the historical deterministic ALE profile. The supported GUI entrypoint and the direct episode runner both stopped themselves on the tenth attempted player move, `h1h4`, after nine RGB-verified player moves and nine RGB-verified Atari replies. ALE had neither terminated nor truncated. The shadow remained at the last verified position, the move was left incomplete, and the runner sent no retry.

The non-auto GUI run used the configured 200-move/1,800-second limits and was not manually stopped while gameplay was active: the controller itself returned the uncertainty stop. The trace and summary were written and checked before the viewer was closed. The shell then reported exit 130 because Ctrl+C closed the still-open GUI process; that exit code is not the episode result.

The strongest confirmed controller defect is at the target-evidence boundary: the code records a selected-piece preview as **target position verified** without establishing a unique cursor at that target. In the reproduced `h1h4` attempt, the final `h4` preview window was unstable, the cursor detector reported `h1`, and the preview classifier still returned positive. The controller then sent one target FIRE. This proves the controller did not independently establish its target location before FIRE.

That observation does **not** prove why Atari did not produce a verified transition. A one-frame FIRE experiment failed at the same move. Eight additional passive windows and a separate 30,000-frame NOOP observation produced no stable expected board or legal opponent reply. Those results strongly disfavor a short settling delay, but do not distinguish an unaccepted Atari input or incorrect Atari interaction state from a state change the available RGB verifier could not recognize. A previously verified occupied-square capture in the same deterministic run had the same unstable-preview/source-cursor pattern and succeeded, so simply requiring every capture preview window to be stable would regress a known working interaction.

No source or test change was made: the available evidence does not justify a safe change that both processes `h1h4` and preserves the verified-state contract. DEMO-F04 remains open. The raw traces, RGB frames, GUI sessions, and logs remain in ignored local artifacts; this report contains only sanitized identities and aggregate findings.

## 2. Repository, model, and runtime identity

- Repository identity was verified as `https://github.com/dodaonam/atari-videochess-rl`; `origin/main` was fetched before work. At start, local `main` and fetched `origin/main` were both `b7bbd8a6e64373dfe8b81ca88ad23184dff802d4`, tree `b3eac5aba1a427f40824648c18b9b3a7a5a00a8f`.
- Initial worktree was clean. No unrelated modified or untracked user files were present.
- Selected policy: `double_dqn_250000`, Q-only evaluation snapshot, training seed `20261103`, policy RNG seed `20261103`. Snapshot SHA-256: `48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293`. The demo loader and read-only CLI preflight both verified the selected identity and immutable metadata.
- Environment: `ALE/VideoChess-v5`, ROM `video_chess.bin`, SHA-256 `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`, ALE-Py `0.11.2`, Gymnasium `1.4.0`, Python `3.12.3`, mode 4, RGB `(210, 160, 3)`, registered ALE horizon 108,000 frames.
- Historical failure profile: frameskip `1`, repeat-action probability `0.0`; runner target FIRE hold `16` ALE frames, release `1`, direction hold `33`, source/target observation windows `33`, three post-FIRE settling windows of `33` frames each. At frameskip 1, requested and effective ALE frames are equal.
- Source history was checked. The interaction modules listed in the assignment (`controller.py`, `vision.py`, `shadow.py`, `environment.py`, `m6/adapter.py`, `m6/campaign.py`, and `rl/evaluate.py`) are unchanged across the pre-improvement and PR #24 commits. The PR #24 `episode.py` diff adds live progress/cancellation plumbing; it does not change target-preview or target-confirmation logic. PR #25 and #26 diffs also do not change those target-evidence branches. The improved policy is not established as the cause.
- Project preflight passed before and after the blocker checkpoint. The project state still records M7 and the separately authorized improvement campaign complete; no M0/M1 or new research campaign was started.

## 3. Reproduction and frame-level evidence

### Direct runner reproduction

The current accepted code was run with the selected checkpoint, reset seed `20261103`, mode 4, frameskip 1, repeat probability 0, 200-player-move limit, 1,800-second wall limit, 150,000-frame/step caps, and the repository's `run_episode` implementation. It ran for 47.365 seconds and stopped at ALE frame 22,070 / 22,066 environment steps:

| Measure | Result |
|---|---:|
| Player moves attempted | 10 |
| Player moves RGB-verified | 9 |
| Atari replies RGB-verified | 9 |
| Final attempted move | `h1h4` |
| Stop | `CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN` |
| ALE terminated / truncated | No / No |
| Shadow advancement for `h1h4` | No |

The direct reproduction trace SHA-256 is `8d3e9d4c540d9e73dd3cfae52e9ac914822d5560a9e75a07bc3287275b9bf382`; its private raw-frame bundle SHA-256 is `83683060d7d98e61efaff0a663a758ed0dc3ccf674410d78093dc0cc8d107951`. The earlier supplied session trace SHA-256 `26abcfe12fdf3a77cff6ef4f4e15588cad00946505b1c6a4aa908a5a3b594433` and the accepted local repeat trace SHA-256 `02432f4a2c6a66e90852fafddb4070f800a15eda890d7ed493cc4a1ebcca6234` were also present and their recorded result was rechecked.

### Target navigation and FIRE

At the last target-navigation window, the requested preview was at `h4`, but that 33-frame window was unstable. The selected-target evidence reported the source as `h1`, target-piece pixels in 9 of 33 frames, and `verified: true`. The code consequently logged `target_position_verified` and sent a single 16-frame target FIRE followed by a one-frame NOOP release.

The target FIRE ran from ALE frame 21,954 through 21,970. In the captured individual RGB frames, the source and target alternated between the pre-move board composition and the selected-piece preview. The preview did not become a stable complete post-capture board. The three normal post-FIRE windows ended at frames 22,004, 22,037, and 22,070; all had the same final RGB digest and remained unstable. The controller did not retry FIRE and did not advance the shadow.

### Safe diagnostic interventions

1. **Single-frame target FIRE:** The same checkpoint, seed, profile, and preceding policy trajectory were retained; only the target FIRE for `h1h4` was changed from 16 frames to 1. It still stopped at the same capture with 9 verified player moves and 9 verified replies. This does not support a simple “16 frames was too long” explanation.
2. **Eight passive windows:** A diagnostic wrapper suppressed only the selected-preview early-stop predicate after the first `h1h4` target preview. Normal complete-board checks remained in force. No additional FIRE or direction input was sent. All eight 33-frame windows remained unstable, ended with the same RGB digest, and failed to match the expected board. The run stopped without changing shadow state.
3. **Extended passive observation:** The exact deterministic action ledger was replayed from seed `20261103`; the emulator frame number and final RGB digest matched the baseline trace before any added input. After the single recorded target FIRE, the only input was 30,000 NOOP frames. Across 909 33-frame windows, there were zero stable pre-move windows, zero stable expected-capture windows, and zero legal Atari-reply candidates. ALE remained unterminated and untruncated through frame 52,070. Wall time was 72.312 seconds; peak process RSS was 245,792,768 bytes.

One first attempt at the eight-window instrumentation aborted before target FIRE because the diagnostic wrapper accessed a nonexistent per-frame field. That run is excluded from causal evidence; the corrected wrapper produced the result above. The passive extension is diagnostic only and does not alter the accepted operational RGB contract.

## 4. Interaction-path audit

- **Policy and legal move:** `M6PolicyAdapter` validates the verified decision context, history, shadow FEN, and legal UCI set before inference. `run_episode` validates the selected UCI against the current shadow board. Policy intention is not used to advance state.
- **Source cursor:** `move_cursor_to()` uses stable RGB, unique cursor localization, and board-agreement checks while routing to the source. Source FIRE is issued once, released, and followed by selected-piece RGB confirmation.
- **Target cursor:** `plan_move()` constructs the target route from the source, but selected-target navigation does not use the cursor-routing verifier. `_selected_target_evidence()` checks source/target piece visibility, unrelated-square occupancy, and cursor observations; it does not require `window.is_stable`. For the historical attempt, this conflated a selected-piece preview with independent target-cursor confirmation.
- **Target FIRE and move verification:** target FIRE is issued once. After release, `run_episode()` tests selected-preview evidence before stable complete-board evidence and stops after three preview-positive windows. A player move advances `ShadowBoard` only after strict expected-board RGB matching. Atari replies are inferred only from RGB-compatible legal moves and are verified before the two-ply state is finalized.
- **Vision/shadow limit:** `BoardWindow.matches_board()` primarily verifies side/color occupancy. Piece-kind pixel classification is partial and ambiguous for rook/king sprites. It cannot independently prove the full internal Atari piece identity at every square. This leaves a possible hidden state/type mismatch as an unresolved alternative.
- **Environment/profile:** `VideoChessEnv.step()` executes Gymnasium actions and records ALE frame counters. `ceil(requested_frames / frameskip)` determines environment calls. The deterministic failure profile had no sticky action probability. `demo.py` validates the checkpoint/environment, invokes the same `run_episode()`, and `live.py` presents/persists its events; neither changes target control semantics. The M6 campaign records the same runner's trace and limits.

The existing synthetic regression `test_capture_preview_can_be_transient_but_only_stable_board_advances_shadow` demonstrates that a mixed window can be preview-positive while not matching the candidate board. It establishes algorithmic susceptibility, not that this synthetic mixture caused the real `h1h4` failure.

## 5. Hypothesis ledger

| ID | Status and confidence | Evidence, contrary evidence, and remaining uncertainty | Safe next diagnostic; risk of a premature fix |
|---|---|---|---|
| H1 — Cursor did not reach `h4` | **Supported, not proven; medium** | Three UP commands produced previews for `h2`, `h3`, then `h4`; the target preview was visible. The cursor detector remained at `h1`, and the final preview window was unstable. A preview does not independently locate the physical Atari cursor. | Validate a cursor/target visual marker against known successful and failed actions. Treating the preview as exact cursor state risks another misdirected FIRE. |
| H2 — Insufficient/unstable target-preview evidence | **Confirmed code weakness; causal role unproven; high for weakness, medium for cause** | `_selected_target_evidence()` can return positive without a stable window. It did so on the unstable `h4` window. The actual board still failed to verify. | Add a validated temporal/cursor feature only after testing against real successful capture frames. A blanket stability requirement would block the successful capture noted below. |
| H3 — Atari rejected target FIRE | **Supported, not proven; medium** | The FIRE action executed once; 16-frame and 1-frame versions both failed. No expected board or reply appeared through 30,000 passive frames. The available trace has no validated “input accepted” signal. | Use a non-mutating ALE/ROM debugger or validated state probe strictly as separate diagnostics. Using unmapped RAM as operational proof would risk false advancement. |
| H4 — Atari accepted FIRE but RGB missed the transition | **Unresolved; low-to-medium** | No stable expected capture board appeared in 30,000 frames, which weighs against a brief delay. No independently validated Atari state/acceptance signal is available, so a visual-recognition failure cannot be excluded. | Compare a validated emulator-side transition signal with RGB, including a known successful capture. Replacing RGB acceptance with the side channel would violate the current contract. |
| H5 — Mixed/selected preview was mistaken for persistent selection | **Classifier behavior confirmed; root-cause role unresolved; medium** | The preview predicate remained positive for all eight diagnostic windows even though each window was unstable. Suppressing that early stop still produced no candidate board. The real state may genuinely have remained selected. | Validate a temporal classifier against raw real-ALE sequences. Removing the stop without such validation risks treating a transient as a move. |
| H6 — Selected-target and cursor state disagreed | **Evidence mismatch confirmed; physical mismatch unresolved; medium** | The runner called the `h4` target verified while the only reported cursor square was `h1`. The `h1` gold pixels may be selection blinking rather than the physical cursor, so this does not prove the cursor was actually wrong. | Establish an independent target cursor/selection-state observation. Assuming either square from current evidence risks a wrong target action. |
| H7 — Frameskip/timing/sticky action changed semantics | **Sticky action contradicted as cause; frameskip unresolved/confounded** | The failing profile used frameskip 1 and repeat probability 0. A one-frame target FIRE did not help. A frameskip-4/repeat-0.25 run followed a different trajectory and reached 15 verified pairs before its 50,000-frame cap. | Paired profile tests at the same reset seed are diagnostic only because trajectories diverge. Random timing changes risk masking rather than fixing the fault. |
| H8 — Settling window was too short | **Contradicted through 30,000 passive frames; high** | Eight extra 33-frame windows and a separate 30,000-frame NOOP run found no stable expected board or reply. | A longer/infinite wait has no current evidence-based justification and risks consuming resources while state remains unknown. |
| H9 — Another defect, including hidden shadow/Atari piece-type divergence | **Unresolved; low-to-medium** | RGB matching mostly checks occupancy/colors and has partial piece-kind classification. Earlier legal verified transitions support alignment but do not prove every hidden piece identity. | Validate piece identity or ROM state independently on known positions. Replacing the shadow with inferred internal state risks concealing desynchronization. |

### Root-cause verdict

The immediate **controller stop** is reproduced and explained: after target FIRE, no complete expected board was RGB-verified, so the runner stopped fail-closed. The earliest confirmed reliability gap is that the controller's target-position claim rests on a selected-piece preview without independent target-cursor evidence. The underlying reason Atari did not transition remains indistinguishable between an unaccepted/wrong-state input and a transition unavailable to the RGB verifier. It is therefore not supportable to claim a single confirmed emulator-level root cause.

## 6. Controlled profile and interaction comparison

| Run | Profile | Result | Interpretation |
|---|---|---|---|
| Deterministic reproduction, checkpoint Q-only, seed `20261103` | mode 4, frameskip 1, repeat 0 | 10 attempted; 9 player moves and 9 replies verified; stopped at `h1h4` | Exact historical failure reproduced. |
| Same trajectory, target FIRE changed only to 1 frame at `h1h4` | mode 4, frameskip 1, repeat 0 | Same stop and verified counts | Does not support target FIRE hold length as a sufficient fix. |
| Default-style profile, same Q checkpoint and reset seed | mode 4, frameskip 4, repeat 0.25; 50,000-frame cap | 16 attempted; 15 player moves and 15 replies verified; stopped at `RUNNER_MAX_ALE_FRAMES` after 50,004 actual frames / 12,500 environment steps | This profile produced a different trajectory and did not reach the same `h1h4` state. It does not prove frameskip caused the failure. The run did not terminate. |
| Supported GUI entrypoint, no `--auto-smoke`, same Q checkpoint and seed | mode 4, frameskip 1, repeat 0; configured 200 moves / 1,800 seconds | 10 attempted; 9 + 9 verified; controller uncertainty; trace and summary persisted | The episode itself stopped on the same failure before any configured cap. The GUI was closed only after persistence was confirmed. |
| Supported GUI `--auto-smoke` | mode 4, frameskip 1, repeat 0; intentionally capped at 2 moves | `SMOKE_PASS`, 2 player moves and 2 Atari replies verified; replay/layout passed; no terminal | GUI/replay integration check only. It is not evidence for `h1h4` or complete-game play. |

The deterministic reproduction also contained an earlier occupied-square capture and verified Atari reply before the failure. Its target preview was unstable and the cursor detector reported the source square, like the later failure. This is why a broad “require stable preview before every capture” change is not justified: it would reject a real interaction that already completed under the same controller/profile.

The supported non-auto GUI invocation used the task's selected checkpoint and 200-move/1,800-second caps:

```bash
DISPLAY=:1 PYTHONPATH=. uv run --locked --no-sync python \
  -m videochess_rl.improvement.demo \
  --policy double-dqn \
  --checkpoint artifacts/improvement/videochess-improvement-20261103-v1/official/attempt-0000/snapshot-250000.pt \
  --checkpoint-sha256 48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293 \
  --seed 20261103 --max-player-moves 200 --max-seconds 1800
```

The shell did not have `uv` on `PATH`, so the installed `uv` executable was invoked directly; the command arguments and locked environment are as shown.

### Evidence identities

The following SHA-256 values identify the local ignored diagnostic evidence; the artifacts themselves are not in Git:

- Historical supplied trace: `26abcfe12fdf3a77cff6ef4f4e15588cad00946505b1c6a4aa908a5a3b594433`; prior exact-repeat trace: `02432f4a2c6a66e90852fafddb4070f800a15eda890d7ed493cc4a1ebcca6234`.
- Current direct baseline reproduction trace: `8d3e9d4c540d9e73dd3cfae52e9ac914822d5560a9e75a07bc3287275b9bf382`.
- One-frame target-FIRE diagnostic trace: `c8be5d187a60601f79c8507a9e0170542589ac84f58e22f018b652d9c6fe632e`.
- Eight-window passive diagnostic trace: `9f21cc44425c0e90010d2e6840d56067656d3739917e01a5236f15ebac070ae8`.
- Thirty-thousand-NOOP observation report: `c583a36959cc4bd058582d60927e5136a9eb7e0777705760e494386d1e131773`.
- Frameskip-4/repeat-0.25 diagnostic trace: `017b88ef5ffef6faa002e804dc15dcc57bf3aed272052151b9bb01c47613c6ac`.
- Supported non-auto GUI trace / summary: `b5801c43c6b858044d4187dccfbf86ca0f90b38b29fed6a61893842ae58ffda4` / `5900fdafd4c519b6bb4833b321c8d3cb41cb8fdc609cc08cb00422f1b8702289`.
- Bounded GUI smoke trace / verification: `2107c76d504da39767e73283f8506f3d1dd15c6b5a2e9af7b75c3eb34db4fb3a` / `207e1cfd08332e69c5053785ee3a5a9e27e011564edfac9153eefbe6b5431369`.
- Focused/full test logs: `53a16586d5d572d3073dac76ad06ef0f9b6d9d8cd83e97f4c1e3b94a0584d2a9` / `222d5597b007d3abb480a2b734af949982fe6ad2c74467d091fbaffacd1f7281`.
- Private local evidence-index SHA-256: `1773431697c1be0e73149f26472a988581aa30274d16c310928e5ca9d3d93a9c`.

The requested M5 Scratch versus improved Double DQN comparison was not run. No M5 checkpoint was loaded, no M5 Warm policy was substituted, and no model comparison or scientific campaign was started because a controller correction was not established.

## 7. Automated and runtime verification

Commands were run with the locked project environment. `uv` was not on the shell `PATH`, so its installed executable was invoked directly; no dependency was installed or changed.

```bash
uv run --locked --no-sync python -m unittest \
  tests.test_m1_control tests.test_m1_episode tests.test_m1_vision \
  tests.test_m1_shadow tests.test_demo_reliability \
  tests.test_phase2_atari_demo -v
```

Result: **115 passed, 0 failed, 0 skipped**, exit 0. This is unchanged baseline coverage; no new test was added because no safe implementation correction was justified.

```bash
uv run --locked --no-sync python -m unittest discover -s tests -v
```

Result: **612 run, 608 passed, 0 failed, 4 skipped**, exit 0, 272.117 seconds. Skips were the accepted M4 transfer artifact, unconfigured private M4/M5 policy-roster roots, private M5 artifact root, and private M5 policy path. An initial `unittest discover -v` invocation found zero tests and exited 5 because the repository's discovery root is `tests/`; that result is retained and not counted as a test pass.

After adding this report, the Markdown/context recovery regression command `uv run --locked --no-sync python -m unittest tests.test_pre_m7_contracts tests.test_agent_context.AgentContextRecoveryTests -v` ran **66 tests, all passed**, including local Markdown-link validation and fresh context recovery.

The selected-demo read-only preflight passed: exact Q checkpoint identity, ROM identity, ALE profile, dependencies, RGB/action contract, Tk display, and writable output. The supported GUI auto-smoke passed with 2 verified player moves, 2 verified Atari replies, replay stepping in both directions, and the layout check. The separate non-auto GUI run's final trace and summary report the controller stop, not a terminal result.

The local preflight command `python3 scripts/agent_preflight.py` passed at task start and after the required blocker checkpoint. `python -m compileall -q videochess_rl tests` passed. `git diff --check` passed, and a manual privacy/whitespace scan of all changed files and the new checkpoint archive segment found no credential patterns, absolute local paths, or trailing whitespace. The final preflight passed with the repository's expected `ARTIFACT_MANIFEST_REQUIRED` warning for ignored `artifacts/`; the new diagnostic sessions and test logs have local integrity manifests/indexing.

## 8. Safety and scientific preservation

- No controller, vision, shadow, environment, policy, ALE, or model code changed. The fail-closed checks were not weakened.
- No shadow advancement occurred on policy intention or preview evidence. The attempted `h1h4` remained unverified; no Atari reply was inferred; no terminal outcome was claimed.
- No blind retry was sent. The one-frame FIRE variation was a separate reset-seed reproduction, not a retry in an ambiguous live state. The 30,000-frame diagnostic sent only NOOP after replaying the recorded action ledger.
- No replay snapshot was fabricated. The GUI replay remained at 18 verified half-moves and reported the absent unverified turn-10 candidate as informational.
- No selected model changed; no M4-A substitution, training, dataset regeneration, Stockfish use, or model comparison occurred. Accepted M5/M6/M7 artifacts, metrics, seeds, and results were not changed.
- All new raw RGB, traces, replay files, and run logs are ignored local artifacts with integrity manifests. No ROM, checkpoint, raw RGB, raw trace, or replay was added to Git or published.

## 9. Acceptance gates and PM handoff

| Gate | Status | Evidence |
|---|---|---|
| A — Diagnosis | **Not passed** | The immediate stop and controller evidence gap are reproduced, but Atari input acceptance versus target-state/vision failure remains unresolved. |
| B — Corrective safety | **Preserved, no correction** | No implementation change; current shadow and no-retry invariants remain intact. |
| C — Automated verification | **Passed on unchanged implementation** | 115 focused tests, 66 post-report documentation/context tests, and the 612-test full suite passed with four disclosed private-artifact skips; compilation, privacy/whitespace scan, `git diff --check`, and final preflight passed. |
| D — Historical capture | **Failed** | Real ALE did not verify `h1h4`; it remained an incomplete move. |
| E — Continued play after correction | **Failed / not demonstrated** | No correction was available to test. The alternate-profile and two-move GUI runs do not establish continuation from `h1h4`. |
| F — Broader reliability | **Partial only** | Ordinary moves, an earlier capture, Atari replies, replay, and GUI state were observed on unmodified code; no post-correction regression evidence exists. |
| G — Delivery | **Not ready** | No corrective implementation or test exists, so no remediation PR was opened. This is an investigation report, not a DEMO-F04 completion claim. |

The exact unresolved evidence blocker is the absence of an independently validated observation of Atari's target cursor/selection state or input-acceptance state at the moment of FIRE. A minimal next diagnostic should compare one known successful capture and the failed `h1h4` interaction with a non-mutating ALE/ROM state probe or a validated RGB cursor marker, while keeping full RGB board matching as the only operational shadow-advance contract. Unmapped RAM values must remain diagnostic only.

**Independent PM decision requested:** review the controller evidence gap, the hypothesis ledger, the private artifact integrity index, and the reason no code fix or PR was produced. DEMO-F04 must remain unresolved unless a later safe correction verifies the historical capture in real ALE and demonstrates continued play from that verified state.
