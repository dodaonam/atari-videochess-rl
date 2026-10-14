# M00 — Technical Project Bootstrap Plan

- **Plan ID:** M00
- **Status:** M0-001 was completed and user-accepted under G2 on 2026-10-15. Acceptance evidence covers M0-01 through M0-04. Current Git state and any next-milestone authorization are owned by `PROJECT_STATE.yaml` and the latest direct user instructions.
- **Task:** `M0-001` in `.agents/tasks/BACKLOG.yaml`
- **Governance gate:** G2 (see [`EXECUTION_PLAN.md`](../../docs/02-management/EXECUTION_PLAN.md))
- **Acceptance:** M0-01 through M0-04 in [`ACCEPTANCE_CRITERIA.md`](../../docs/06-quality/ACCEPTANCE_CRITERIA.md)
- **Current project status:** Read `.agents/state/PROJECT_STATE.yaml`; do not infer status from this plan.

## Goal

Audit and establish a reproducible local development environment and low-cost smoke-check workflow without changing system configuration or consuming Colab GPU resources without authorization.

## Scope

- Inspect repository state and existing Python/tooling configuration.
- Check available command versions and current dependency/import state.
- Prepare a dependency/lockfile proposal that respects the existing project and verifies compatibility before pinning.
- Define local smoke checks and a non-allocating Colab CLI capability check.
- Record sanitized environment evidence and update canonical task/state records.

## Exclusions

- Do not implement ALE controls, board extraction, or M1 feasibility tests.
- Do not install system packages or change machine configuration without separate authorization.
- Do not allocate Colab runtimes, request a GPU, launch training, or incur paid compute.
- Do not begin RL/model implementation or dataset generation.

## Dependencies and approvals

1. G1 must be reviewed and explicitly approved by the user.
2. M0-001 authorization and progress are recorded in canonical state and backlog.
3. If a check requires credentials, external account changes, system privileges, or paid resources, stop that check and obtain the required authorization.

## Planned checks

1. Record `git status --porcelain=v1 --untracked-files=all`, branch, and HEAD; preserve all existing paths.
2. Inspect `.python-version` and `pyproject.toml`; compare the declared Python floor with `python3 --version`.
3. Check `git`, `python3`, `uv`, and Colab CLI availability using version/help commands; report missing tools without installing them.
4. Inspect installed imports/executables only after confirming they are relevant; record actual versions and avoid network or system changes.
5. Prepare reproducible project-local dependency configuration only after a compatibility review; do not invent pinned versions.
6. Run the low-cost checks listed in the approved M0 task; validate Colab command capability without provisioning a runtime.
7. Record results and failures in the backlog; update state only from observed evidence.

## Completion condition

M0 passes only when M0-01 through M0-04 have evidence and `agent_preflight.py` reports a consistent state. A missing GPU entitlement or a setup failure remains explicit; it is not replaced with an assumed success. M1 is a separate milestone and does not begin automatically when M0 passes.
