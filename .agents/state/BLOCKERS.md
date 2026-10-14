# Active Blockers

**Canonical source for:** active/resolved blockers and their impact, evidence, owner, and unblock condition. External approvals remain in `docs/01-foundation/REQUIREMENTS.md`; ordinary pending tasks remain in `.agents/tasks/BACKLOG.yaml`.

## Current status

No active technical blocker has been confirmed because M0/M1 have not started. G1 hardening and independent-session acceptance are complete, and the user approved G1 on 2026-10-14. M0 is the next milestone; its live start authorization is owned by `.agents/state/PROJECT_STATE.yaml` and the latest direct user instructions. Open academic and service approvals O-01 through O-08 remain in `REQUIREMENTS.md`; these are unresolved approvals, not technical blockers.

## Record format

Create one section per blocker using a stable ID `BLK-001`, `BLK-002`, etc. Do not recycle IDs.

- **Status:** `active` or `resolved`
- **Owner:** user, Codex, or named role
- **Reported:** date/time UTC
- **Impact:** task/milestone IDs affected
- **Evidence:** repository-relative paths and command/result references
- **Unblock condition:** observable condition or approval required
- **Resolution:** required when status is `resolved`

A task with status `blocked` in `BACKLOG.yaml` must reference an active blocker ID. Do not create a blocker solely because a later milestone is pending an approval gate.
