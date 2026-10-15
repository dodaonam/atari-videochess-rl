# M1-001 — ALE Feasibility Verification

> Historical verification snapshot from 2026-10-15T08:29:19Z. The later multi-turn controller work, mode reset checks, bounded terminal-seeking runs, and current M1-04 verdict are recorded in [M1-04-terminal-verification.md](M1-04-terminal-verification.md). This record is retained unchanged as the earlier baseline.

- **Recorded at:** 2026-10-15T08:29:19Z
- **Branch:** `initial-idea`
- **Implementation revision:** `61c169d02c91ac495dc8fb9c5d20691f0fdf0ada`
- **Current checkpoint revision at recording:** `c57e39dde883c711548049ba4410c2ec4d397ba2`
- **Authorization:** `.agents/evidence/M1-authorization.md`
- **Plan:** `.agents/plans/M01-ale-feasibility.md`
- **Reproduction guide:** `docs/05-operations/M1-ALE-REPRODUCIBILITY.md`

## Runtime and environment findings

The packaged `video_chess.bin` ROM was loaded through `ALE/VideoChess-v5`. The runtime reported Python 3.12.3, Gymnasium 1.4.0, ALE-Py 0.11.2, ROM SHA-256 `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`, RGB `(210, 160, 3)` `uint8`, diagnostic RAM `(128,)` `uint8`, and `Discrete(10)`. Runtime mode values were `[0,1,2,3,4]`; difficulty values were `[0]`. The registered v5 defaults are RGB, frameskip 4, sticky-action probability 0.25, and reduced action space.

The reset RGB hash was `22841a4f2778529efa4ff5d22c286742ce48ccb6e9f8858084601729fbfc864c`; the image parser verified the standard start occupancy and a cursor at d4. The board spans x=44–107 and y=36–171 in 8-by-17-pixel squares. It uses observed gold `(180,122,48)` and blue `(132,144,252)` piece pixels. Cursor/blink overlays remain ambiguous and are excluded from the board comparison. The sprite counter identifies pawns, bishops, knights, and queens; count 26 is explicitly ambiguous between rook and king.

Action calibration found a one-square directional repeat every 33 ALE frames under `frameskip=1`, `repeat_action_probability=0.0`. A short one-frame FIRE pulse after a 33-frame neutral settle selected/released reliably in that profile. Longer FIRE holds could deselect or cancel, so the controller uses the short pulse and verifies the resulting board from RGB. Under v5 defaults, each 33-frame direction request is rounded to nine four-frame steps; the stochastic profile still completed the same verified transition in fresh seeded runs.

RAM was read only through `diagnostic_ram()` for selected wrapper-documented addresses `0xE1`, `0xE4`, and `0xEA`. Those values are recorded separately in the local traces and never enter action selection, move inference, or shadow-board updates. No full RAM dump is committed.

## Closed-loop RGB evidence

Three CLI runs from the committed implementation completed with exit code 0 and status `complete`:

| Profile | Seed | Player move | Atari reply | Wait for reply | Trace SHA-256 |
|---|---:|---|---|---:|---|
| Deterministic development | 20261015 | `e2e3` | `c7c5` | 297 ALE frames | `227fd9f37749f08cc4a98917bc640c9dd00f7c2682450b2e865e4b0a8da13e9c` |
| Registered v5 defaults | 20261015 | `e2e3` | `c7c5` | 288 ALE frames | `a76eb0b6e7e85edf1f56c7c4f89f391017edd2a2caa98a15fab3972b5a90d322` |
| Registered v5 defaults | 20261016 | `e2e3` | `c7c5` | 288 ALE frames | `5ac35241d32fa29c467a47ca7e985d4b08771948e77cc248ffe879c8e86cab0d` |

The trace captures the player pawn absent from e2 and visible on e3, then the Atari pawn absent from c7 (with the cursor overlay at the source) and visible on c5. The shadow FEN after both observed transitions was `rnbqkbnr/pp1ppppp/8/2p5/8/4P3/PPPP1PPP/RNBQKBNR w KQkq - 0 2`. Each position was accepted only after RGB occupancy matched the legal `python-chess` transition. Raw frame files and full run JSON remain under ignored `artifacts/m1/`; key reset/player/final frame hashes are retained in those traces and the reproduction command regenerates them.

An early `e2e4` attempt was not accepted during initial FIRE calibration. It is retained under ignored `artifacts/m1/e2e4-attempt*` and is not counted as a successful move. The verified demonstration uses `e2e3`; no claim is made that the failed attempt established `e2e4` to be unsupported.

## M1 acceptance matrix

| Criterion | Verdict | Evidence and limit |
|---|---|---|
| M1-01 | **PASS** | Real reset and observations; RGB/RAM shapes, action space, ROM hash, versions, modes, and difficulty recorded above and in the CLI traces. |
| M1-02 | **PASS** | Direction repeat, cursor route, short FIRE selection/release, frameskip, and sticky-action behavior calibrated. Real traces pass under deterministic and v5-default profiles. |
| M1-03 | **PASS** | Real ALE action sequence moved the player pawn e2–e3; RGB then showed the Atari reply c7–c5. Both transitions matched legal shadow-board moves. The result reproduces across three fresh runs. |
| M1-04 | **UNVERIFIED** | Real runs returned reward 0 and neither terminated nor truncated. The official ALE wrapper describes white-centric checkmate reward handling, but no live checkmate/nonzero reward was observed. Modes/difficulty and a full turn cycle were observed; terminal behavior remains unverified, so this criterion is not passed. |
| M1-05 | **PASS** | Negative-path tests reject illegal moves and RGB/shadow mismatch without mutating the shadow state. A real reset observation also rejects an unobserved move. The runner stops when a directional action produces no RGB change and never silently resets/reconstructs state. |
| M1-06 | **PASS** | Configuration, implementation entry points, reproduction commands, findings, limitations, and local-artifact policy are documented in the linked M1 reproduction guide. |

Key RGB frames are retained locally under ignored `artifacts/m1/`:

- Reset: `artifacts/m1/final-deterministic-c57/frames/reset.png`, SHA-256 `22841a4f2778529efa4ff5d22c286742ce48ccb6e9f8858084601729fbfc864c`.
- After player move: `artifacts/m1/final-deterministic-c57/frames/after-player-move.png`, SHA-256 `cc8d9d953218c419065ea5c4a6eca75a0dc664c3f4a02a721bfd01baeb263b5e`.
- After opponent reply: `artifacts/m1/final-deterministic-c57/frames/final.png`, SHA-256 `9bc4e2fde2815086807484ee4f96f81cf9f62b68d094318e526492d9ab60a0cc`.
- v5-default final board, seeds 20261015 and 20261016: SHA-256 `da5d885e0004c180ed5c43c3729abf887fe96fd6b8fe12d87e79cfb058670e00` for both.
- Local artifact manifest: `artifacts/m1/MANIFEST.sha256`, 327 generated files, manifest SHA-256 `fa8459bc1dfa7b7a613f6a9c9a429fcf65dce75c4136170b5dae7303dc2d54eb`. The manifest and raw frames are ignored and not part of Git history.

**Milestone verdict:** M1 remains `in_progress` because M1-04 is unverified. G2 remains `in_progress`; the conditional G2 approval is not exercised. G0/G1 remain approved, M0 remains accepted, M2–M7 remain not started, and M2 still requires separate explicit authorization. O-01 through O-08 remain open. No RL training, dataset generation, Stockfish search, Colab access, or GPU allocation occurred.

## Verification commands

| Command | Result |
|---|---|
| `uv --offline --cache-dir .venv/.cache/uv run --locked --no-sync python -m unittest discover -s tests -v` | **PASS**, exit 0, 84 tests, 36.942 s. Executed 2026-10-15T08:26:14Z–2026-10-15T08:26:52Z at `c57e39dde883c711548049ba4410c2ec4d397ba2`. Includes context, export, M0 smoke, M1 unit, and real ALE integration tests. |
| `uv --offline --cache-dir .venv/.cache/uv lock --check --python /usr/bin/python3` | **PASS**, exit 0, executed 2026-10-15T08:28:33Z. Lockfile unchanged; no dependency installation performed. |
| `python3 scripts/agent_preflight.py` | **PASS**, exit 0, executed 2026-10-15T08:27:17Z. No errors; one expected `ARTIFACT_MANIFEST_REQUIRED` warning for ignored raw ALE artifacts under `artifacts/`. |
| `git diff --cached --check` | **PASS**, exit 0 before the implementation commit; the final evidence-stage check is repeated before commit. |

## Portable staged-index recovery check

- **Executed:** 2026-10-15T08:28:33Z.
- **Fixture revision:** `928b20c33c7aa447ae35269316955d150ddcb9aa` in a temporary repository materialized from the staged index; this is not a project commit.
- **Method:** Exported the current Git index into an isolated source directory, created a temporary local Git commit, cloned it into a second clean directory, and ran `python3 scripts/agent_preflight.py` there.
- **Result:** PASS, exit 0. Preflight classified the HEAD change as an expected commit/checkout transition and reported that the portable tracked-file manifest matches.
- **Recovered state:** G2 `in_progress`; G0/G1 approved; M1 active and `in_progress`; M1-001 depends on completed M0-001; M1-01 through M1-06 are present; M1-04 remains unverified; the next action is to observe terminal/reward behavior or retain that limitation and not begin M2. O-01 through O-08 remain open.
- **Local-only files:** `main.py`, `chat_history.md`, `.venv/`, and `artifacts/` were absent from the clean clone and caused no content-corruption finding.

The first post-implementation clean-clone test caught an incomplete portable checkpoint: staged source/document blobs had changed after the recorded index manifest. The checkpoint was refreshed and committed in `c57e39dde883c711548049ba4410c2ec4d397ba2`; the clean-clone regression and full suite then passed. This preserves the G1 portable-commit-transition contract.

## Outstanding M1 evidence

No actual game-ending position was reached in these bounded two-ply runs. A real terminal/reward observation is still required to pass M1-04. Until it is obtained, keep M1 and G2 in progress and do not begin M2.

## Machine-verifiable command records

Sanitized retained records matching the command evidence in `.agents/tasks/BACKLOG.yaml`:

### Test evidence

Command: `uv --offline --cache-dir .venv/.cache/uv run --locked --no-sync python -m unittest discover -s tests -v`
Result: `PASS: 84 tests in 36.942s, including context, export, M0 smoke, M1 unit, and real ALE integration checks.`
Exit code: 0

### Command evidence

Command: `uv --offline --cache-dir .venv/.cache/uv run --locked --no-sync python3 scripts/run_m1_demo.py --profile deterministic-dev --seed 20261015 --max-opponent-wait-frames 10000 --trace artifacts/m1/final-deterministic-c57/trace.json`
Result: `PASS: RGB-verified e2e3 and Atari reply c7c5; trace SHA-256 227fd9f37749f08cc4a98917bc640c9dd00f7c2682450b2e865e4b0a8da13e9c.`
Exit code: 0

### Command evidence

Command: `uv --offline --cache-dir .venv/.cache/uv run --locked --no-sync python3 scripts/run_m1_demo.py --profile v5-default --seed 20261015 --max-opponent-wait-frames 10000 --trace artifacts/m1/final-v5-default-seed-20261015/trace.json`
Result: `PASS: RGB-verified e2e3 and Atari reply c7c5; trace SHA-256 a76eb0b6e7e85edf1f56c7c4f89f391017edd2a2caa98a15fab3972b5a90d322.`
Exit code: 0

### Command evidence

Command: `uv --offline --cache-dir .venv/.cache/uv run --locked --no-sync python3 scripts/run_m1_demo.py --profile v5-default --seed 20261016 --max-opponent-wait-frames 10000 --trace artifacts/m1/final-v5-default-c57-seed-20261016/trace.json`
Result: `PASS: RGB-verified e2e3 and Atari reply c7c5; trace SHA-256 5ac35241d32fa29c467a47ca7e985d4b08771948e77cc248ffe879c8e86cab0d.`
Exit code: 0

### Command evidence

Command: `python3 scripts/agent_preflight.py`
Result: `PASS: no errors; one expected ARTIFACT_MANIFEST_REQUIRED warning for ignored local ALE frames.`
Exit code: 0

### Command evidence

Command: `uv --offline --cache-dir .venv/.cache/uv lock --check --python /usr/bin/python3`
Result: `PASS: lockfile consistent; no dependency installation performed.`
Exit code: 0
