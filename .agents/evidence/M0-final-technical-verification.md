# M0 Final Technical Verification & Reproducibility Hardening

- **Status:** Technical verification passed; M0-001 awaits user acceptance. M1 was not started and remains unauthorized.
- **Repository revision:** `9449b3f3508c55e1a34893a49c2670498310f78f` (`initial-idea`). All work is uncommitted; no commit or push was performed.
- **Execution window:** 2026-10-14 UTC. Command-specific start times are recorded below.
- **Scope limits:** No ALE reset, observation/action/gameplay, training, dataset generation, Colab authentication/session/API request, or GPU allocation was performed.

## ALE-Py 0.11.2 VideoChess ROM

The old statement that the installed ALE-Py package had no VideoChess ROM was incorrect. The probe looked up the Gymnasium spelling `VideoChess` with an ALE-Py ROM helper that expects snake case.

- Installed resource: `.venv/lib/python3.12/site-packages/ale_py/roms/video_chess.bin`.
- Size: 4,096 bytes. SHA-256: `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`.
- ALE-Py `roms/md5.json` entry: `video_chess.bin` → `f0b7db930ca0e548c41a97160b9f6275`.
- `get_rom_path("video_chess")` returned the packaged file and validated it against the manifest. `get_rom_path("VideoChess")`, `get_rom_path("videochess")`, and `get_rom_path("video chess")` returned no resource.
- `gym.register_envs(ale_py)` exposed `ALE/VideoChess-v5`; `gym.make("ALE/VideoChess-v5")` constructed with 10 actions and observation shape `(210, 160, 3)`. No reset was called.
- The older `ALEInterface.getAvailableGames()` method is absent from this binding. Resource presence was verified through the packaged resource API and Gymnasium construction instead.

This verifies local ROM presence/accessibility, registration, and construction as separate facts. It does not verify gameplay, RAM mapping, controls, game modes, difficulty behavior, evaluation settings, or assignment permission. Local ROM absence is no longer an M1 prerequisite concern. O-05 remains open for the remaining runtime/evaluation details; O-01 and assignment-specific permissions remain unresolved.

## Clean-clone recovery regression

`tests/test_agent_context.py` now keeps the current-HEAD clean-clone test dynamic: it compares preflight output to the cloned state and backlog instead of expecting a G1 gate or pending M0 task. Historical G1 expectations are retained in `tests/fixtures/g1-recovery-baseline.json` and pinned to revision `9449b3f3508c55e1a34893a49c2670498310f78f`. A separate disposable Git fixture checkpoints and clones G1 → G2/M0 complete → M1 in progress → M2 pending approval. The fixture tests state transitions only and does not authorize milestone work.

## Stockfish setup reproducibility

Stockfish 19 universal Linux x86-64 remains the M0 UCI-only executable. The official `sf_19` release metadata identifies `stockfish-linux-x86-64-universal.tar.gz` at the pinned release URL and reports archive digest `sha256:9defc0d4e55d49c65a6d042f3e571a39fcea499ade6dbe741b53b8c65e03611f` (metadata checked 2026-10-14T19:15:36Z). The installed executable SHA-256 is `0f83d24cc46d2c66c60f16001af5444873bc112b7d028594513426894c12da19`.

The `sf_19/Copying.txt` license fetched from the official source tag is 35,149 bytes with SHA-256 `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986` (checked 2026-10-14T19:15:41Z); the local retained license has the same digest. `docs/05-operations/SETUP.md` now gives the pinned URL, archive and license checks, extraction/install commands, and the project-local path. A fresh checkout still needs host-provided Python 3.12, `uv`, `curl`, `tar`, `find`, `install`, `sha256sum`, and network access. The separate Colab CLI is also a manual host prerequisite for its version/help check. No Stockfish inference, analysis, opponent, labeler, or evaluation use is approved by this verification.

## Colab token-cache permissions

Metadata-only `stat` checks reported mode `0664`; no credential content was read. The safer recommended mode is `0600`. The cache was not changed because it is outside the repository and requires explicit user approval. Its reported size changed from 930 to 938 bytes between two metadata-only observations while mode remained `0664`; the cause was not inspected.

## Verification commands and results

Command: `uv --cache-dir .venv/.cache/uv run --locked python -m unittest discover -s tests -v`
Executed: `2026-10-14T19:14:09Z`
Result: `Ran 62 tests in 27.924s; OK` (38 context, 18 export, 6 M0 smoke).
Exit code: 0. Includes current-state clone recovery, pinned historical G1 recovery, synthetic G1→G2→M1→M2 clone transitions, ALE-Py ROM lookup, Gymnasium registration/construction without reset, and Stockfish UCI ping without search.

Command: `uv lock --check --python /usr/bin/python3`
Executed: `2026-10-14T19:14:50Z`
Result: `Resolved 18 packages in 1ms`
Exit code: 0.

Command: read-only ALE-Py ROM/name/Gymnasium probe using the installed `.venv/bin/python`
Executed: `2026-10-14T19:14:50Z`
Result: ALE-Py `0.11.2`; packaged `video_chess.bin` exists (4,096 bytes); `video_chess` resolves; PascalCase/compact/spaced variants do not; `ALE/VideoChess-v5` spec exists and construction succeeds without reset.
Exit code: 0.

Command: `sha256sum .venv/share/stockfish/stockfish .venv/share/stockfish/Copying.txt`
Executed: `2026-10-14T19:14:51Z`
Result: executable `0f83d24cc46d2c66c60f16001af5444873bc112b7d028594513426894c12da19`; license `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`.
Exit code: 0.

Command: metadata-only `stat` of the Colab CLI token cache
Executed: `2026-10-14T19:14:51Z`
Result: mode `0664`; content was not read.
Exit code: 0.

An initial full-suite invocation using `.venv/bin/python` directly, before refreshing the checkpoint, had two failures: the recovery test observed the intentionally stale workspace snapshot, and the Stockfish lookup lacked `.venv/bin` on `PATH`. After checkpoint refresh, the documented `uv run --locked` invocation passed all 62 tests. The failed preliminary invocation is not used as acceptance evidence.

## Acceptance and next action

M0-01 through M0-04 have passing technical evidence, including the non-allocating Colab CLI capability check. Colab authentication/entitlement is not claimed. M0 is ready for user approval; this record does not itself approve M0 or authorize M1. O-01 through O-08 remain open; O-05 is partially informed by local ROM evidence but remains unresolved overall.

Next user action: review the M0-001 final verification and explicitly approve M0. M1 remains not started and requires separate explicit authorization.

Final post-evidence rerun:

Command: `uv --cache-dir .venv/.cache/uv run --locked python -m unittest discover -s tests -v`
Executed: `2026-10-14T19:16:51Z`
Result: `Ran 62 tests in 27.559s; OK`
Exit code: 0.
