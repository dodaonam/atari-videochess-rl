# Active Blockers

**Canonical source for:** active/resolved blockers and their impact, evidence, owner, and unblock condition. External approvals remain in `docs/01-foundation/REQUIREMENTS.md`; ordinary pending tasks remain in `.agents/tasks/BACKLOG.yaml`.

## Current status

No external approval or infrastructure blocker is recorded. G0 and G1 are approved; M0-001 is completed and user-accepted. M1-001 is authorized under `.agents/evidence/M1-authorization.md`. Multi-turn RGB evidence exists, but later player input failed to produce a verified board transition and no terminal state was observed. See active technical blocker BLK-001 below. G2 remains in progress. O-01 through O-08 remain unresolved in `REQUIREMENTS.md`; M1 evidence keeps RAM diagnostic-only and makes no assignment-compliance claim.

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

## BLK-001 — Reliable later-turn player input and terminal evidence

- **Status:** `active`
- **Owner:** Codex
- **Reported:** 2026-10-15T10:22:25Z
- **Impact:** M1-001 and G2; M1-04 cannot pass and G2 cannot close.
- **Evidence:** `.agents/evidence/M1-04-terminal-verification.md`; retained mode-0 traces under ignored `artifacts/m1/m1-04/`. Seven terminal-seeking episodes verified between three and five complete player/Atari cycles, then stopped when the next player action was not reflected in RGB. Repeated probes after `d7d5` reproduced the same class of failure. All traces report zero reward and `terminated=false`, `truncated=false`.
- **Unblock condition:** Identify and fix or bound the later-turn input failure; demonstrate stable RGB-verified control from an evolving position and obtain a genuine ALE terminal/reward event with replayable trace. Do not inject a position or change RAM.
