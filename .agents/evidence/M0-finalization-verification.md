# M0 Finalization Verification

- **Acceptance:** M0-001 and M0-01 through M0-04 were explicitly accepted by the user on 2026-10-15 (Asia/Ho_Chi_Minh); see `.agents/evidence/M0-acceptance.md`.
- **Repository at precommit evidence capture:** `initial-idea` at `9449b3f3508c55e1a34893a49c2670498310f78f`; M0 changes were staged and uncommitted at that time. A subsequent direct user task separately authorized the M0 baseline commit, the review-tooling commit, and a standard push; consult live Git refs for those later outcomes.
- **Governance:** G0/G1 approved; G2 in progress; M1 not started and still requires separate authorization. O-01 through O-08 remain open.
- **Boundaries:** No ALE reset/gameplay, model training, dataset generation, Colab authentication/API access, or runtime/GPU allocation.

## Credential-cache permission verification

The specific Colab CLI OAuth token cache was verified by metadata only. Immediately before the permission change it was owned by the current local user `dodaonam`, a regular file, not a symlink, and had one hard link. Its mode was `0664`. The permission bits were changed on a no-follow file descriptor with `fchmod(0600)`; no file contents were read. The final metadata check at `2026-10-14T19:49:32Z` confirmed owner `dodaonam`, regular file, not a symlink, mode `0600`. No other external file or account setting was changed.

## Environment and reproducibility checks

| Check | Execution (UTC) | Result | Exit |
|---|---|---|---:|
| `python3 --version`; `.venv/bin/python --version`; `uv --version`; `git --version` | 2026-10-14T19:52:48Z | Python 3.12.3 for both interpreters; uv 0.9.26; Git 2.43.0 | 0 |
| `uv lock --check --python /usr/bin/python3` | 2026-10-14T19:48:06Z | Resolved 18 packages in 1ms; lock consistent | 0 |
| `uv sync --python /usr/bin/python3 --locked --offline` | 2026-10-14T19:48:11Z | Resolved 18 packages; audited 16 installed packages; no network access | 0 |
| Locked import/runtime probe | 2026-10-14T19:48:18Z | Gymnasium 1.4.0; ALE-Py 0.11.2; python-chess 1.11.2; PyTorch 2.14.1+cpu; CUDA `None`; tensor device CPU; `video_chess.bin` present (4,096 bytes); `ALE/VideoChess-v5` registered | 0 |
| `colab version` | 2026-10-14T19:48:18Z | Version 0.7.4 | 0 |
| `colab --help` | 2026-10-14T19:48:18Z | Help/capability list returned offline; no authentication command invoked | 0 |
| Stockfish UCI identity and `ping()` | 2026-10-14T19:49:32Z | Engine identifies as Stockfish 19; ping passed; no position or search command issued | 0 |
| Stockfish binary and retained `Copying.txt` SHA-256 | 2026-10-14T19:48:18Z | Binary `0f83d24cc46d2c66c60f16001af5444873bc112b7d028594513426894c12da19`; license `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986` | 0 |

## Test suite

Command: `uv --cache-dir .venv/.cache/uv run --locked python -m unittest discover -s tests -v`
Executed: `2026-10-14T19:48:25Z`
Result: `Ran 62 tests in 27.640s; OK` (38 context, 18 export, 6 M0 smoke).
Exit code: 0.

The suite includes the M0 CPU/PyTorch, python-chess, bundled ROM, Gymnasium registration/construction without reset, and Stockfish UCI checks; current-HEAD clean-clone recovery; a pinned historical G1 fixture; and synthetic G1→G2→M1→M2 state-transition recovery. Synthetic transitions do not perform or authorize milestone work.

Final staged-state rerun: `uv --cache-dir .venv/.cache/uv run --locked python -m unittest discover -s tests -v`, executed `2026-10-14T19:57:01Z`; `Ran 62 tests in 28.224s; OK`; exit code 0.

## Acceptance and limitations

M0-01 through M0-04 have accepted evidence. Colab version/help checks passed, but account entitlement/authentication remains unverified under O-04. The local VideoChess ROM is accessible; gameplay and the remaining O-05 runtime/evaluation details remain unverified. M1 remains unauthorized. The secured token cache is private user configuration and is not part of the repository or Git staging.
