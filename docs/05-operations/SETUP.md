# Environment Setup Runbook

**Status:** Canonical M0 setup runbook. Live execution progress is in `.agents/state/PROJECT_STATE.yaml` and `.agents/tasks/BACKLOG.yaml`.<br>
**Authority:** [`REQUIREMENTS.md`](../01-foundation/REQUIREMENTS.md), [`EXECUTION_PLAN.md`](../02-management/EXECUTION_PLAN.md), and `.agents/plans/M00-bootstrap.md`.

## Safety and scope

This document defines M0 checks and does not authorize out-of-scope operations. M0 requires G1 approval and separate explicit M0 authorization in canonical state. Keep changes inside the project environment; privileged operations, external-account changes, and paid resources require separate approval. Preserve the existing `pyproject.toml`, `.python-version`, and untracked project files while auditing them.

## M0 audit order

1. Inspect Git branch/status/diff and the existing project files. Record the current source revision and dirty paths.
2. Check installed tools without changing them: `git --version`, `python3 --version`, `uv --version`, `colab version`, and `colab --help` where those executables exist.
3. Inspect `pyproject.toml` and `.python-version`; reconcile the declared Python requirement with the runtime before choosing dependencies.
4. Check imports/versions for the planned Python stack only after a dependency plan is approved: PyTorch, Gymnasium, `ale-py`, `python-chess`, Stockfish, and test/lint tools.
5. Record current ALE/ROM registration and Stockfish executable availability. Do not infer that a ROM or executable is installed from a package name.
6. Validate Colab CLI capability using non-allocating/help/status checks. Do not create a runtime or request a GPU in M0 without separate authorization.
7. Propose a reproducible environment/lockfile and low-cost smoke checks. Install only within the authorized project environment; system-wide installation requires separate authorization.
8. Run only M0 acceptance checks and update task evidence. Do not begin M1 cursor control or ALE feasibility work until M0 is accepted and M1 is authorized.

## Reproducible project-local environment

The tested M0 host is Ubuntu 24.04 x86-64 with Python 3.12. `pyproject.toml` records the compatible dependency ranges and CPU-only PyTorch source; `uv.lock` records exact package versions and artifact hashes. A fresh checkout needs Python 3.12 and `uv` available on the host. Verify the committed lock and install only into the project `.venv`:

```bash
uv lock --check --python /usr/bin/python3
uv sync --python /usr/bin/python3 --locked
uv run --locked python -m unittest discover -s tests -v
```

`uv sync` creates `.venv` in the repository and installs only the locked project dependencies there. The smoke suite uses CPU PyTorch and does not train a model. Reproducing the Colab CLI capability check also requires the separate Google Colab CLI on `PATH`; it is not a Python project dependency and no login, token refresh, session query, or runtime creation is part of setup.

### Stockfish 19 (manual host prerequisite)

Stockfish is intentionally not installed by `uv sync`. To reproduce the M0 UCI readiness check on Linux x86-64, obtain the immutable `sf_19` universal release asset from the [official Stockfish release](https://github.com/official-stockfish/Stockfish/releases/tag/sf_19). GitHub's release metadata publishes the archive digest. Fetch the pinned license text from the same source tag and verify both files before use:

```bash
set -eu
mkdir -p .venv/share/stockfish .venv/bin
stockfish_tmp="$(mktemp -d)"
trap 'rm -rf "$stockfish_tmp"' EXIT
curl --fail --location --retry 3 \
  --output "$stockfish_tmp/stockfish.tar.gz" \
  https://github.com/official-stockfish/Stockfish/releases/download/sf_19/stockfish-linux-x86-64-universal.tar.gz
printf '%s  %s\n' \
  '9defc0d4e55d49c65a6d042f3e571a39fcea499ade6dbe741b53b8c65e03611f' \
  "$stockfish_tmp/stockfish.tar.gz" | sha256sum --check
mkdir "$stockfish_tmp/unpacked"
tar -xzf "$stockfish_tmp/stockfish.tar.gz" -C "$stockfish_tmp/unpacked"
stockfish_binary="$(find "$stockfish_tmp/unpacked" -type f -name stockfish -print -quit)"
test -n "$stockfish_binary" && test -x "$stockfish_binary"
install -m 0755 "$stockfish_binary" .venv/share/stockfish/stockfish
curl --fail --location --retry 3 \
  --output .venv/share/stockfish/Copying.txt \
  https://raw.githubusercontent.com/official-stockfish/Stockfish/sf_19/Copying.txt
printf '%s  %s\n' \
  '3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986' \
  '.venv/share/stockfish/Copying.txt' | sha256sum --check
printf '%s  %s\n' \
  '0f83d24cc46d2c66c60f16001af5444873bc112b7d028594513426894c12da19' \
  '.venv/share/stockfish/stockfish' | sha256sum --check
ln -sfn ../share/stockfish/stockfish .venv/bin/stockfish
```

The archive SHA-256 is `9defc0d4e55d49c65a6d042f3e571a39fcea499ade6dbe741b53b8c65e03611f`; the extracted executable SHA-256 is `0f83d24cc46d2c66c60f16001af5444873bc112b7d028594513426894c12da19`. Retain `.venv/share/stockfish/Copying.txt` with the executable. It is GPL-3.0; any later redistribution must also meet the license's source-code or source-pointer terms. The M0 smoke check performs only a UCI handshake/readiness ping and grants no search permission by itself. A separate owner authorization now permits only the bounded M3 offline teacher run documented in [STOCKFISH_TEACHER.md](../04-research/STOCKFISH_TEACHER.md). Engine inference, opponent use, offline evaluation, and expanded M3 labeling remain outside that authorization. This manual fetch requires `curl`, `tar`, `find`, `install`, and `sha256sum` on the host, plus network access to the official release and source-tag URLs.

### ALE-Py ROM and VideoChess environment

Modern `ale-py` packages bundle supported Atari ROM resources ([ALE-Py 0.11.2 release notes](https://ale.farama.org/v0.11.2/release_notes/); ROM bundling began in 0.9.0). In the installed ALE-Py 0.11.2, the packaged ROM is `.venv/lib/python3.12/site-packages/ale_py/roms/video_chess.bin` (4,096 bytes; SHA-256 `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`). `ale_py.roms.get_rom_path("video_chess")` resolves and validates the resource using ALE-Py's ROM manifest; this helper takes the snake-case name. `VideoChess` is the Gymnasium/ALE environment naming form: `gym.register_envs(ale_py)` registers `ALE/VideoChess-v5`, and `gym.make("ALE/VideoChess-v5")` constructs the environment with the expected spaces. Construction does not call `reset`; no observation, action, or gameplay was tested in M0.

The local ROM is present, so absence of a packaged VideoChess ROM is not an M1 readiness blocker. At the time of M0 verification, M1 had not started; see `.agents/state/PROJECT_STATE.yaml` and `.agents/tasks/BACKLOG.yaml` for the current M1 authorization and status. O-05 remains open for runtime/evaluation settings not yet verified. O-01 was open when M0 was verified; it was later closed internally by the owner decision dated 2026-10-27, without a claim of instructor approval. Do not run ALE reset or gameplay as part of M0.

For Colab M0 checks, run only `colab version` and help/config inspection. Do not invoke session creation, runtime execution, account usage, or authentication flows without the specific authorization required for that operation.

Colab CLI token caches are private user configuration, not project files. Protect the local cache with mode `0600`; do not put token contents in this repository or in evidence. A permissions change outside the repository requires the user's explicit approval.

## Recording setup evidence

For every check, record command, result, exit status, actual UTC execution timestamp, timestamp when recorded, source Git revision, and repository-relative path to a sanitized log in the task evidence. File reviews record their checked timestamp and Git revision. Earlier reports without retained logs/timestamps stay explicitly unverified; never backfill invented provenance. Do not record tokens, credentials, full environment dumps, or account-specific data. If a check requires external authentication or allocation, record it as pending and ask for authorization rather than attempting it.

## Pre-M0 baseline observed during G1

G1 has not audited installed Atari/RL dependencies, Stockfish, Colab entitlement, GPU availability, or ALE behavior. Python 3.12.3 was observed while running G1 tooling; that single interpreter check is not an M0 environment audit. See `.agents/state/VERIFIED_FINDINGS.md` and current project state before any setup claim.
