# Active Blockers

**Canonical source for:** active/resolved blockers and their impact, evidence, owner, and unblock condition. External approvals remain in `docs/01-foundation/REQUIREMENTS.md`; ordinary pending tasks remain in `.agents/tasks/BACKLOG.yaml`.

## Current status

No external approval or infrastructure blocker is recorded. G0 and G1 are approved; M0-001 is completed and user-accepted. M1-001 is authorized under `.agents/evidence/M1-authorization.md`. The controller now verifies source selection and each selected-target preview from RGB; a 16-frame deterministic replay completed 20 full player/Atari cycles, and v5 defaults completed two cycles. Shorter target FIRE profiles and one 12-frame later-turn input still stopped safely at target confirmation. No real terminal or nonzero reward was observed. See active technical blocker BLK-001 below. G2 remains in progress. O-01 through O-08 remain unresolved in `REQUIREMENTS.md`; M1 evidence keeps RAM diagnostic-only and makes no assignment-compliance claim.

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
- **Evidence:** `.agents/evidence/BLK-001-diagnostic-20261015.md`; `.agents/evidence/BLK-001-diagnostic-20261015-r2.zip`; `.agents/evidence/M1-04-terminal-verification.md`; local ignored traces indexed by `artifacts/m1/MANIFEST-20261015.sha256`. The baseline `a2a3` failure was localized to target confirmation: source selection and target preview were visible, but a one-frame target FIRE left the board unchanged. A duration comparison supports target-input timing sensitivity. The 16-frame profile completed 20 consecutive RGB-verified cycles, including the previously failing move categories; v5 defaults completed two cycles. A later 12-frame terminal-seeking run completed 18 cycles and safely stopped at `a2a1` when the selected preview remained after FIRE. Across the authorized eight terminal-seeking attempts no terminal, truncation, or nonzero reward was observed. The ROM-level polling/readiness mechanism remains unresolved.
- **Unblock condition:** Retain reliable phase-specific RGB control on the documented profiles and obtain a genuine ALE terminal/reward event with replayable trace, including flags, mode/configuration, ROM/package metadata, and final board. Do not inject a position or change RAM.
