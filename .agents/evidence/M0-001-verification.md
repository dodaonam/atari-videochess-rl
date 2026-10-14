# M0-001 — Technical Project Bootstrap Verification

- **Governance:** M0-001 was authorized under G2 by the user on 2026-10-15. G0 and G1 remain approved; G2 remains in progress through M1.
- **Source revision:** `9449b3f3508c55e1a34893a49c2670498310f78f` on `initial-idea`, pushed to `origin/initial-idea` before M0 work.
- **Environment:** Ubuntu 24.04.5 LTS, x86_64, system Python 3.12.3, `uv` 0.9.26, Git 2.43.0. `.python-version` is `3.12`; `requires-python` is `>=3.12`.
- **Isolation:** Project dependencies are locked in `uv.lock` and installed in ignored `.venv`; PyTorch is pinned to the CPU wheel index. No system package or global Python package was installed. The Stockfish binary and license are stored inside `.venv`.

## M0 acceptance assessment

- **M0-01 — PASS:** The existing Ubuntu, Python, Git, uv, Colab CLI, relevant installed packages, Stockfish executable, disk space, and repository state were audited before installation. No requested Python dependencies or Stockfish executable were present before setup.
- **M0-02 — PASS:** `pyproject.toml` defines bounded dependencies and the CPU-only PyTorch source; `uv.lock` resolves 18 packages. A project-local sync installed 16 packages. A later offline locked sync audited all 16 successfully. The full context and M0 smoke suites passed.
- **M0-03 — PASS for non-allocating CLI capability:** Colab CLI 0.7.4 `version` and `--help` checks passed without creating a session. Earlier token-structure and expiry claims are withdrawn because their sanitized command output and provenance were not retained; they are not used as verified facts. No remote API/session query, login/refresh flow, GPU allocation, or training job was attempted, so live account entitlement/authentication remains unverified under O-04.
- **M0-04 — PASS:** Setup gaps and unresolved approvals are recorded below. No required M0 test failed. M1 remains unstarted and unauthorized pending review; the local VideoChess ROM is present, while O-01/O-05 assignment and runtime details remain open.

## Dependency and tool versions

| Component | Verified version/result |
|---|---|
| Python | 3.12.3 (`/usr/bin/python3`) |
| Gymnasium | 1.4.0 |
| ALE-Py | 0.11.2 |
| `chess` / python-chess | 1.11.2 |
| PyTorch | 2.14.1+cpu; `torch.version.cuda` is `None` |
| Stockfish | 19 universal Linux x86-64 binary; UCI identifies `Stockfish 19` |
| Colab CLI | 0.7.4; local version/help checks pass |

The Stockfish archive came from the official Stockfish 19 universal Linux x86-64 release and was kept out of Git. Archive SHA-256: `9defc0d4e55d49c65a6d042f3e571a39fcea499ade6dbe741b53b8c65e03611f`; extracted binary SHA-256: `0f83d24cc46d2c66c60f16001af5444873bc112b7d028594513426894c12da19`. The official `sf_19` release metadata publishes the matching archive digest. The `Copying.txt` license is retained beside the executable in `.venv`; its SHA-256 is `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`.

## Smoke checks and limitations

- `tests/test_m0_smoke.py`: the original 5-test M0 run is retained below as historical evidence. The final verification adds a direct package-ROM resource assertion; see `.agents/evidence/M0-final-technical-verification.md`.
- Full `uv run --locked python -m unittest discover -s tests -v`: 41 tests passed, including the G1 recovery suite and M0 smoke tests. The clean-clone regression passed against the committed baseline.
- **Correction, verified 2026-10-15:** the earlier statement that the installed ROM registry lacked VideoChess was incorrect. The probe used the Gymnasium-style `VideoChess` spelling with ALE-Py's ROM helper, which expects snake case. ALE-Py 0.11.2 packages `ale_py/roms/video_chess.bin` (4,096 bytes; SHA-256 `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`; package MD5 manifest value `f0b7db930ca0e548c41a97160b9f6275`). `get_rom_path("video_chess")` resolves the file; lookups `VideoChess`, `videochess`, and `video chess` do not. `gymnasium.make("ALE/VideoChess-v5")` constructs and exposes `Discrete(10)` and RGB `(210, 160, 3)` spaces, but no reset, observation, action, or gameplay was attempted. No separate ROM download or AutoROM install was performed. Local ROM availability is verified; M1 remains unstarted and awaits user review/authorization, while O-01 and the remaining O-05 permissions/runtime/evaluation details remain open.
- The Stockfish UCI ping is an availability check only. O-01/O-07 remain open; Stockfish was not used for labels, evaluation, opponent play, or inference.
- Colab CLI version/help checks were offline only. No conclusion about OAuth cache contents or validity is used for M0 acceptance; the earlier token-state claims are `historical_unverified`. The mode and ownership check is recorded separately in `.agents/evidence/M0-finalization-verification.md`. No token refresh or remote session/usage query was made. O-04 remains unresolved.
- O-01 through O-08 remain unresolved. No M1 reset/observation/control work, dataset generation, RL implementation, training, or Colab runtime was performed.

The earlier ROM-lookup result and its timestamped command summary are retained as historical evidence; the correction above supersedes the mistaken absence conclusion without erasing the prior record.

## Verified command results

All commands below used revision `9449b3f3508c55e1a34893a49c2670498310f78f`; output summaries are retained in this sanitized record.

- Executed `2026-10-14T17:53:18Z` — `uv --cache-dir .venv/.cache/uv lock --check --python /usr/bin/python3`.
- Executed `2026-10-14T17:53:18Z` — `uv --cache-dir .venv/.cache/uv sync --python /usr/bin/python3 --locked --offline`.
- Executed `2026-10-14T17:53:34Z` — `colab version`.
- Executed `2026-10-14T17:53:35Z` — `colab --help`.
- Executed `2026-10-14T17:47:24Z` — `uv --cache-dir .venv/.cache/uv run --locked python -m unittest discover -s tests -p test_m0_smoke.py -v`.
- Executed `2026-10-14T17:49:53Z` — `uv --cache-dir .venv/.cache/uv run --locked python -m unittest discover -s tests -v`.
- Executed `2026-10-14T17:58:06Z` — local Stockfish UCI handshake/readiness ping; no position/search command sent.
- Executed `2026-10-14T17:58:07Z` — read-only ALE ROM registry check; VideoChess ROM ID/path unavailable.
- Historical record `2026-10-14T17:58:07Z` — offline Colab auth-cache structure check; output/provenance was not retained, so token-state conclusions are `historical_unverified` and withdrawn from acceptance.

### Sanitized command log

Command: `uv --cache-dir .venv/.cache/uv lock --check --python /usr/bin/python3`
Result: `Resolved 18 packages in 3ms`
Exit code: 0

Command: `uv --cache-dir .venv/.cache/uv sync --python /usr/bin/python3 --locked --offline`
Result: `Resolved 18 packages in 2ms | Audited 16 packages in 0.17ms`
Exit code: 0

Command: `colab version`
Result: `Version: 0.7.4`
Exit code: 0

Command: `colab --help`
Result: `usage and command capability list available`
Exit code: 0

Command: `uv --cache-dir .venv/.cache/uv run --locked python -m unittest discover -s tests -p test_m0_smoke.py -v`
Result: `Ran 5 tests in 2.327s; OK`
Exit code: 0

Command: `uv --cache-dir .venv/.cache/uv run --locked python -m unittest discover -s tests -v`
Result: `Ran 41 tests in 19.586s; OK`
Exit code: 0

Final post-completion-state rerun, executed `2026-10-14T18:04:18Z`:

Command: `uv --cache-dir .venv/.cache/uv run --locked python -m unittest discover -s tests -v`
Result: `Ran 41 tests in 19.984s; OK`
Exit code: 0

Final suite after recording the M0 evidence, executed `2026-10-14T18:05:48Z`:

Command: `uv --cache-dir .venv/.cache/uv run --locked python -m unittest discover -s tests -v`
Result: `Ran 41 tests in 19.575s; OK`
Exit code: 0

Command: `python3 scripts/agent_preflight.py`
Result: `Agent context preflight: PASS; no validation errors; one expected WORKTREE_CONTENT_DRIFT warning for uncommitted M0 tracked changes.`
Exit code: 0

Command: `python3 scripts/agent_preflight.py`
Result: `Agent context preflight: PASS; no validation errors; one expected WORKTREE_CONTENT_DRIFT warning for uncommitted M0 tracked changes.`
Exit code: 0

The initial `uv sync` output showed 16 packages installed with exit code 0, but its execution timestamp was not retained. The timestamped offline sync above independently confirmed that the lock and all 16 installed packages match.

## Primary documentation consulted

- [ALE VideoChess environment](https://ale.farama.org/environments/video_chess/) for the environment ID, action/observation spaces, and default v5 settings.
- [Gymnasium Atari ROM guidance](https://gymnasium.farama.org/v1.0.0a1/environments/atari/) for the distinction between `ale-py` and ROM installation/AutoROM licensing.
- [PyTorch local installation guidance](https://pytorch.org/get-started/locally/) for selecting a CPU-only Linux build.
- [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/) for lockfile-backed environment setup.
- [python-chess documentation](https://python-chess.readthedocs.io/en/latest/) for legal move generation and UCI engine interface.
- [Official Stockfish releases](https://github.com/official-stockfish/Stockfish/releases) for the Stockfish 19 universal binary.
- [Official Colab CLI operator guidance](https://github.com/googlecolab/google-colab-cli/blob/main/skills/colab-operator/SKILL.md) and [session configuration documentation](https://github.com/googlecolab/google-colab-cli/blob/main/docs/01_session_management.md) for local token/client configuration and non-allocating CLI boundaries.
