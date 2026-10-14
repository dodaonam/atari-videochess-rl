# Environment Setup Runbook

**Status:** M0 runbook prepared during G1; no M0 environment setup has been performed.<br>
**Authority:** [`REQUIREMENTS.md`](../01-foundation/REQUIREMENTS.md), [`EXECUTION_PLAN.md`](../02-management/EXECUTION_PLAN.md), and `.agents/plans/M00-bootstrap.md`.

## Safety and scope

This document describes future M0 checks. It is not permission to install packages, modify system configuration, start Colab sessions, or incur costs. M0 begins only after the user approves G1. Preserve the existing `pyproject.toml`, `.python-version`, and untracked project files while auditing them.

## M0 audit order

1. Inspect Git branch/status/diff and the existing project files. Record the current source revision and dirty paths.
2. Check installed tools without changing them: `git --version`, `python3 --version`, `uv --version`, `colab version`, and `colab --help` where those executables exist.
3. Inspect `pyproject.toml` and `.python-version`; reconcile the declared Python requirement with the runtime before choosing dependencies.
4. Check imports/versions for the planned Python stack only after a dependency plan is approved: PyTorch, Gymnasium, `ale-py`, `python-chess`, Stockfish, and test/lint tools.
5. Record current ALE/ROM registration and Stockfish executable availability. Do not infer that a ROM or executable is installed from a package name.
6. Validate Colab CLI capability using non-allocating/help/status checks. Do not create a runtime or request a GPU in M0 without separate authorization.
7. Propose a reproducible environment/lockfile and low-cost smoke checks. Install only within the authorized project environment; system-wide installation requires separate authorization.
8. Run only M0 acceptance checks and update task evidence. Do not begin M1 cursor control or ALE feasibility work until M0 is accepted and M1 is authorized.

## Recording setup evidence

For every check, record command, result, exit status, actual UTC execution timestamp, timestamp when recorded, source Git revision, and repository-relative path to a sanitized log in the task evidence. File reviews record their checked timestamp and Git revision. Earlier reports without retained logs/timestamps stay explicitly unverified; never backfill invented provenance. Do not record tokens, credentials, full environment dumps, or account-specific data. If a check requires external authentication or allocation, record it as pending and ask for authorization rather than attempting it.

## Current verified setup state

G1 has not audited installed Atari/RL dependencies, Stockfish, Colab entitlement, GPU availability, or ALE behavior. Python 3.12.3 was observed while running G1 tooling; that single interpreter check is not an M0 environment audit. See `.agents/state/VERIFIED_FINDINGS.md` and current project state before any setup claim.
