# Active Blockers

**Canonical source for:** active/resolved blockers and their impact, evidence, owner, and unblock condition. External approvals remain in `docs/01-foundation/REQUIREMENTS.md`; ordinary pending tasks remain in `.agents/tasks/BACKLOG.yaml`.

## Current status

No external approval or infrastructure blocker is recorded. G0 and G1 are approved; M0-001 is completed and user-accepted. M1-001 is in progress under the direct authorization in `.agents/evidence/M1-authorization.md`. Real RGB closed-loop evidence exists for one player move and an Atari reply. M1-04 terminal behavior remains an evidence gap because no real game-ending state was observed; G2 therefore remains in progress. O-01 through O-08 remain unresolved in `REQUIREMENTS.md`; the M1 evidence keeps RAM diagnostic-only and makes no assignment-compliance claim.

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
