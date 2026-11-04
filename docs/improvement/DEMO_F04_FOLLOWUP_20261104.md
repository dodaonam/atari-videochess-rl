# DEMO-F04 Follow-up Diagnosis and Live Demo Remediation

**Verdict:** `DEMO_F04_UNRESOLVED_FAIL_CLOSED_DIAGNOSTICS_IMPROVED`

**Scope:** Diagnose the November 4 selected Double DQN session, compare it with
the accepted DEMO-F04 evidence, retain fail-closed Atari control, and provide a
single supported live-demo entrypoint with truthful diagnostics and replay.
No training, model, dataset, reward, evaluation, or accepted scientific result
was changed.

## A. Verified baseline and runtime

- Repository: `https://github.com/dodaonam/atari-videochess-rl`.
- At task start, local `main`, fetched `origin/main`, and the supplied baseline
  all matched commit `bdfb8a36dd98d8dc06dc6e4e05790c9bd4e1d0cf`, tree
  `7bf93de99c791d4652a1ff1377c69e4a1cb5f67e`. The initial worktree was clean.
- Work was moved to the dedicated branch
  `fix/demo-f04-live-diagnostics-20261104`.
- Runtime: Python 3.12.3, uv 0.9.26, ALE-Py 0.11.2, Gymnasium 1.4.0,
  python-chess 1.11.2, PyTorch 2.14.1+cpu, Tk 8.6.
- Preflight verified `ALE/VideoChess-v5`, ROM SHA-256
  `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`, mode
  4, RGB `(210, 160, 3)`, frameskip 1, and sticky-action probability 0.
- The selected Q checkpoint on disk matches SHA-256
  `48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293`.
  The available M4-A checkpoint matches
  `cf5e437ff4e2d6a8e85739df751dec33f16b7bc4c92268f996ec4c612d62feed` and was
  not used for this Double DQN diagnosis.
- The user-local standalone GUI file was read without modification; its
  observed SHA-256 was
  `057c886eeda16c50acfad9012e26dac527cd84df5859e579c44f63d5da014df7`.
- The supplied November 4 trace and summary identities are respectively
  `26abcfe12fdf3a77cff6ef4f4e15588cad00946505b1c6a4aa908a5a3b594433` and
  `09e31f5eaf7c8f280a36ed5c41893461273d795fa1750e0c2d5a82ef17e1e830`.
  The original session directory and standalone GUI file were left unchanged.

The supplied last verified position and selected move were independently
checked with the locked python-chess version. The FEN is valid and the move is
legal: it is a rook capture onto an occupied destination. This confirms the
occupied-target capture geometry without publishing a move sequence or FEN.

## B. Independent fact check

| Supplied observation | Finding |
|---|---|
| The policy produced a tenth decision. | Confirmed by turn 10 and policy decision index 10. |
| Nine player moves and nine Atari replies were verified. | Confirmed by both terminal counters and the nine complete verified transitions. |
| ALE did not terminate or truncate. | Confirmed; both flags are false. |
| The session ended as partial. | Confirmed. |
| Replay retained 18 verified half-moves and 19 snapshots. | Confirmed in the supplied summary. |
| The missing turn-10 candidate produced a replay warning. | Confirmed. The move stopped before the candidate-observation stage. |
| The cause was the same occupied-target confirmation condition as DEMO-F04. | Confirmed at the recorded stop-path level; underlying Atari acceptance versus RGB recognition remains unresolved. |
| The selected capture was legally available from the last verified state. | Confirmed independently with python-chess. |

## C. November 4 stop reconstruction

The trace records the following sequence, with no inference from the policy's
intent alone:

1. The tenth decision began from a stable RGB position matching the verified
   shadow board. The current cursor was identified before source navigation.
2. The controller issued the recorded direction inputs to the source and
   recorded RGB confirmation there. It issued one source FIRE for one ALE
   frame, released FIRE, and observed the selected-piece blink. Source
   selection is explicitly recorded as verified.
3. It navigated toward the occupied capture destination using three direction
   inputs, each followed by a release and observation window. The RGB verifier
   recorded the selected-piece preview at the requested destination. That
   destination preview window was itself marked unstable; the cursor detector
   continued to report the source square. Thus the trace supports the preview
   classification but does not show a separately located cursor at the target.
4. The controller issued exactly one target FIRE press, held for 16 ALE frames,
   then released it for one frame. The action ledger confirms that the target
   FIRE action actually ran.
5. The first post-FIRE observation window ended at frame 22,004. It did not
   match the expected full player-move board and still matched the
   selected-piece-preview heuristic. Two further passive NOOP windows ended at
   frames 22,037 and 22,070. They recorded the same final RGB digest and the
   same selected-preview signature. No FIRE retry was sent.
6. At frame 22,070 the controller raised the target-confirmation stop. The
   runner recorded `CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN`, reason
   “Target FIRE did not produce a board transition after bounded passive
   settling; selected-piece preview remained visible, so no retry was issued,”
   one incomplete final move, and category
   `target_confirmation_uncertainty`.

The run stopped after 49.371 seconds, 22,066 environment steps, and ALE frame
22,070. The configured limits were 200 player moves, 1,800 seconds, 150,000
frames, 150,000 environment steps, and 512 MiB of artifacts. ALE did not
terminate or truncate. Therefore wall-clock, frame, step, artifact, user, and
ALE terminal stops do not explain the interruption.

The final authoritative shadow FEN equals the pre-attempt last verified state.
No target move was counted, and no Atari reply was inferred for the attempt.
The candidate image is absent because `run_episode` did not reach the candidate
observation/save stage. It is not evidence of a missing verified move.

The immediate stop condition is established with high confidence. The trace
does not establish the underlying cause: it cannot distinguish an Atari input
rejection from a successful game-state change whose RGB evidence remained
ambiguous.

## D. Differential diagnosis

| Hypothesis | Evidence and disposition |
|---|---|
| H1: Atari rejected target FIRE. | Persistent selected-preview RGB after the single target FIRE supports this possibility. No emulator state signal in the trace establishes rejection. **Not eliminated; plausible, not proven.** |
| H2: Atari accepted the move but RGB recognition did not resolve it. | The occupied target and selected-piece overlay can make source/target RGB ambiguous. The trace has no stable expected board and no independent accepted-state evidence. **Not eliminated; plausible, not proven.** |
| H3: Source selection was not confirmed. | Source cursor observation, source FIRE, and selected-piece blink are recorded as verified. **Eliminated for this attempt with high confidence.** |
| H4: Target navigation was wrong or uncertain. | Three target-direction actions were issued and the requested-target preview was observed. The target window was unstable and cursor observations remained at the source, so independent target-cursor confirmation is absent. **No evidence of a wrong destination; not fully eliminated.** |
| H5: Controller and shadow had already diverged. | Before the attempt, stable RGB matched the shadow state and no unexpected cursor displacement was recorded. After FIRE, the observed board remained ambiguous. **Pre-attempt divergence eliminated; post-FIRE state unknown.** |
| H6: A runner or ALE limit interrupted the game. | Exact stop category is controller uncertainty; elapsed time, frame and step counts were below configured caps; ALE termination/truncation were false. **Eliminated.** |
| H7: Failure depends on occupied-target capture geometry. | The attempted move is a legal capture onto an occupied target. All three historical selected-Q cases have the same pre-move position, attempted move/destination, final RGB digest, and stop category. **This exact capture geometry reproduces; other capture geometries remain untested.** |

## E. RGB and shadow-state review

`_selected_target_evidence()` combines source-piece and target-piece visibility
across a `BoardWindow`, checks unrelated-square consistency, and allows cursor
observations on the source. Unlike source-selection confirmation, it does not
require `window.is_stable` for the preview signature. A deterministic synthetic
capture fixture now covers the consequence: a mixed window containing a brief
selected preview followed by candidate-board frames can still report preview
evidence, while the window does not match the complete candidate board. A
subsequent stable complete-board window is accepted. `ShadowBoard` rejects the
mixed window and advances only on the stable full-board window.

This demonstrates a possible transient preview classification during a valid
capture transition. It can delay recognition and contribute to a false stop if
the signature persists across the bounded windows. It does not authorize a
shadow advance: complete-board RGB matching remains required. The November 4
trace itself contains three repeated unstable preview windows and does not show
that Atari accepted the move. The controller was not modified to retry, relax
stability, extend timing, or advance on the preview heuristic.

The shadow implementation still advances on complete RGB evidence only. No
observed Atari reply is synthesized from policy intent, RAM, or expected
position.

## F. Historical comparison and reproduction

The three earlier selected-Q raw traces were present locally and their
SHA-256 values match the sanitized evidence ledger:

- `813e51a293cd0afa479968090f07c17ca7a19154c7ff10879ad104353c9738cc`
- `a70c1e1ac9d311a9b2733aaac3006c83c7304cee50aea698d7e786bccd1caadf`
- `2ef10284c9fb7e0bfde263a3cf73860f1db3b82307aacf775e94aa12e9989ad6`

Each historical trace and the supplied November 4 trace has the same attempted
pre-move position and capture, source-selection result, requested-destination
preview, one 16-frame target FIRE, three settling/uncertainty windows, final RGB
digest, stop category, and retained pre-attempt shadow state. The reproduction
is exact at the recorded trace/RGB level. The private move history and frames
remain local.

The available one-frame target-FIRE diagnostic is at a different position and
stops at a different attempted move after four verified player/reply pairs. It
also ends in target-confirmation uncertainty. It does not establish that a
16-frame hold caused or fixed DEMO-F04.

An independent `run_episode` reproduction used the same locked environment,
Q checkpoint, reset seed, and mode-4 configuration. It stopped with the same
category after 10 attempted moves, 9 verified player moves, and 9 verified
Atari replies. Its trace SHA-256 is
`02432f4a2c6a66e90852fafddb4070f800a15eda890d7ed493cc4a1ebcca6234`. This
reproduces the failure; it does not resolve whether Atari accepted the move.

## G. Standalone viewer and supported entrypoint

The user-local standalone viewer imports the repository's
`VideoChessEnv`, `run_episode`, `load_demo_policy`, and `M6PolicyAdapter`; it
does not contain a second Atari controller. For Double DQN, both it and the
repository module load the same checkpoint contract and invoke the same
episode runner. Their environment profile for the supplied run matches the
repository mode-4 RGB profile.

The duplicated standalone GUI/replay layer has two confirmed reporting defects:

- `episode_finished` is queued before the worker's final `done` event. The
  `episode_finished` branch includes stop category, but the later `done`
  branch overwrites the footer with counts and trace path.
- `build_replay_entries()` checks for a candidate PNG before checking whether
  the move reached RGB verification. It warns when an unverified move never
  reached the candidate-save stage. A missing verified Atari snapshot is also
  warned about while replay construction continues.

That file was not overwritten. The supported replacement is
`videochess_rl.improvement.demo`, which uses repository-owned `demo.py` and
`live.py`. Its live GUI retains stop category/reason after worker completion,
shows separate White/Black columns, labels pending or unverified actions, and
replays verified White candidate and Atari reply RGB snapshots after stop.
For partial cursor-masked candidates, the actual candidate image is included in
replay only after the complete two-ply transition is RGB-verified.

Optional absent candidates for unverified moves produce `INFO`; missing RGB
artifacts for verified moves produce `WARNING`; mismatches between move
verification metadata and replay artifacts produce `ERROR`. No synthetic
verified snapshot is created, and replay metadata errors fail automated smoke
acceptance. `live_summary.json` and the console summary include outcome class,
stop category/reason, incomplete-move fields, ALE terminal flags, counts,
checkpoint identity, and distinct model-training/ALE-reset seeds. They contain
no frame arrays or move-level trace.

Running the new replay-artifact classifier read-only against the supplied
November 4 trace produced exactly one `INFO` for the absent unverified turn-10
candidate, with no warnings or errors.

Supported interactive command, run from the repository root:

```bash
uv run --locked --no-sync python -m videochess_rl.improvement.demo \
  --policy double-dqn \
  --checkpoint artifacts/improvement/videochess-improvement-20261103-v1/official/attempt-0000/snapshot-250000.pt \
  --checkpoint-sha256 48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293 \
  --seed 20261103 \
  --max-player-moves 200 \
  --max-seconds 1800
```

The same entrypoint was tested with `--auto-smoke` on real ALE. That mode
forces a two-player-move bound, verifies the live GUI, tests replay in both
directions and layout, and exits automatically.

## H. Verification

### Automated tests

The final focused command was `uv run --locked --no-sync python -m unittest
tests.test_demo_reliability tests.test_m1_episode tests.test_m1_vision
tests.test_m1_shadow tests.test_phase2_atari_demo -v`: 110 tests, exit 0.

The first complete-suite run executed 612 tests: 607 passed, one failed, and
four skipped (exit 1). Its only failure was
`test_project_context_can_be_recovered_without_chat_history`, which found
`git_snapshot_matches == false` because the canonical checkpoint predated this
authorized branch/worktree. The failed result and log digest are retained; it
is not counted as a pass. After refreshing the checkpoint, repository preflight
reported the workspace and Git snapshots matching. The verbose complete-suite
rerun executed 612 tests: 608 passed, zero failed, four skipped (exit 0, 204.305
seconds). The four skips were:

- The accepted local M4 transfer artifact was unavailable to that test fixture.
- Private M4/M5 artifact roots were not configured for the M6 policy-roster test.
- The private M5 artifact root was not configured for one compatibility test.
- The private M5 policy path was not configured for another compatibility test.

The suite emitted non-failing `ResourceWarning`s from the existing
`improvement/common.py` helper that reads `/proc/meminfo` without closing its
file handle. The successful full-suite log digest and all command provenance
are in the companion evidence file.

`python -m compileall -q videochess_rl tests`, `git diff --check`, and the
changed-file privacy pattern scan passed. Preflight returned PASS with no
errors; the only remaining warning is the repository-wide requirement for
independent manifests under ignored `artifacts/`. The two new diagnostic/live
smoke sessions have local manifests; no raw frames or trace were added to Git.
After updating the evidence ledger, the checkpoint was refreshed again,
preflight still passed, and
`test_project_context_can_be_recovered_without_chat_history` passed on that
refreshed state.

### Real ALE

The canonical GUI smoke used the verified Double DQN checkpoint and actual
VideoChess ROM with Atari reset seed `20261103`; the model training seed was
also `20261103` and remains a distinct identity. It verified two player moves
and two Atari replies from RGB, then stopped at
`RUNNER_MAX_PLAYER_MOVES`. ALE did not terminate or truncate. GUI replay passed
Left and Right stepping; the 1100×680 layout check passed without overlap or
clipped labels. The console returned `SMOKE_PASS` with exit code 0. This is a
bounded smoke only, not evidence of a complete Atari game or of passing the
problematic occupied capture.

## I. Remaining limitations

- Atari input acceptance and RGB recognition remain indistinguishable in the
  repeated occupied-target capture trace.
- Target preview evidence can be transient; stable complete-board evidence
  remains required before shadow advancement.
- No post-change real-ALE run has verified the problematic capture. No full
  game or ALE terminal chess outcome was demonstrated.
- The independent two-move GUI smoke verifies the supported path and replay,
  not multi-turn reliability beyond the historical failure.
- The repository preflight retains its expected artifact-manifest warning for
  ignored `artifacts/`; new diagnostic/smoke sessions have local integrity
  manifests, while original private session files were left untouched.

## J. Pull-request handoff

Final branch, tested HEAD/tree, pull-request URL, CI status, and worktree state
are recorded after push in the companion machine-readable evidence and final
handoff. The PR remains open for independent PM review; it is not merged and no
self-approval or release was performed.
