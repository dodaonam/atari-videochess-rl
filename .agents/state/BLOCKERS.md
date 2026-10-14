# Active Blockers

**Canonical source for:** active/resolved blockers and their impact, evidence, owner, and unblock condition. External approvals remain in `docs/01-foundation/REQUIREMENTS.md`; ordinary pending tasks remain in `.agents/tasks/BACKLOG.yaml`.

## Current status

No active technical blocker is recorded. G1 is approved; M0-001 completed under G2 after explicit user authorization. M0 has been user-accepted; M1 has not started and awaits separate explicit authorization. ALE-Py 0.11.2 includes an accessible `video_chess.bin` ROM; this removes local ROM absence as a prerequisite concern, while O-05's runtime/evaluation details and O-01 assignment permissions remain open. Colab authentication was not live-verified. O-01 through O-08 remain unresolved in `REQUIREMENTS.md` and are recorded as open approval/setup conditions, not active technical blockers.

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
