# Active Blockers

**Canonical source for:** active/resolved blockers and their impact, evidence, owner, and unblock condition. External approvals remain in `docs/01-foundation/REQUIREMENTS.md`; ordinary pending tasks remain in `.agents/tasks/BACKLOG.yaml`.

## Current status

G0, G1, and G2 are approved; M0-001 and M1-001 are complete, M2-001 is complete, and M3-001 is accepted and merged. G3 remains unapproved. M4-001 was started under direct owner authorization and is now blocked by BLK-002: two pairs in the mandated fixed 128 training samples have identical complete model inputs but conflicting played-move targets, capping deterministic legal top-1 at 126/128 against 127/128 required. Cross-entropy passed; the accuracy condition did not. Full training, held-out evaluation, and checkpoint acceptance were not started. O-01 is closed internally; absence of instructor-policy evidence remains informational and is not the M4 blocker. BLK-001 is resolved with phase-specific RGB control, explicit runner stop categories, and two repeatable real ALE terminal/reward traces. The terminal screen does not show a parseable final board, and the exact ROM-level target-FIRE polling mechanism remains unknown; the runner retains the last verified FEN and stops safely. O-02–O-08 retain their scoped status in `REQUIREMENTS.md`; RAM remains diagnostic-only and no formal instructor approval is claimed.

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

- **Status:** `resolved`
- **Owner:** Codex
- **Reported:** 2026-10-15T10:22:25Z
- **Impact:** M1-001 and G2; M1-04 was not passable before live terminal/reward evidence existed.
- **Evidence:** Historical diagnosis `.agents/evidence/BLK-001-diagnostic-20261015.md` and `.agents/evidence/BLK-001-diagnostic-20261015-r2.zip`; final campaign and acceptance record `.agents/evidence/M1-G2-final-verification-20261016.md`; terminal bundle `.agents/evidence/M1-04-terminal-success-20261016.zip`; complete local manifest `artifacts/m1/MANIFEST-20261016.sha256`; terminal traces under `artifacts/m1/m1-04/campaign4-mode4-queenmate-seed20261017/` and `campaign5-terminal-replay-seed20261017/`.
- **Unblock condition:** Retain reliable phase-specific RGB control on documented profiles and obtain a genuine ALE terminal/reward event with replayable trace, including flags, mode/configuration, ROM/package metadata, and the final independently verified board state. Do not inject a position or change RAM.
- **Resolution:** RGB demonstrated the previously failing source-selection, selected-target-preview, and 16-frame target-confirmation phases; a 20-cycle run and new mode-0/mode-4 runs show extended legal play. The mode-4 runner's ten-mismatch early stop was removed and replaced with bounded waiting plus an RGB reply-source-cursor readiness condition. Two fresh deterministic mode-4 runs then reproduced ALE reward `-1.0`, `terminated=true`, `truncated=false`, and the same terminal RGB hash after the same three verified player/Atari cycles. The final terminal screen clears the chessboard; the runner records the last independently verified FEN before the unconfirmed terminal move and does not advance its shadow. This meets the recorded final verified board-state requirement without claiming a final board parse. The ROM's internal FIRE polling/debounce mechanism remains an implementation limitation, not an unresolved unsafe control state. No further M1 blocker remains. That sentence records the authorization state at BLK-001 closure; M2, M3, and their acceptance are now documented in the later milestone records. G3 remains unapproved.

## BLK-002 — Fixed M4 sanity sample has conflicting identical-input labels

- **Status:** `active`
- **Owner:** project owner for any protocol change; Codex for preserving evidence and maintaining the current gate without weakening it.
- **Reported:** 2026-10-27T13:33:05.861961Z
- **Impact:** M4-001; M4-02 fails the required top-1 threshold, so M4-03 and M4-04 have not started and M4 cannot be accepted.
- **Evidence:** `.agents/evidence/M4-02-sanity-gate-blocker-20261027.md`; `.agents/evidence/logs/M4-02-sanity-gate-diagnostic-20261027.json`; `.agents/evidence/logs/M4-sanity-gate-r2-20261027.txt`; `.agents/evidence/logs/M4-02-sanity-gate-diagnostic-20261027.txt`; preserved local run artifacts under `/home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r2/`.
- **Unblock condition:** The project owner records an explicit revised M4-02 rule for the conflicting labels while preserving the accepted M3 release and ADR-0003 model contract. Then rerun the authorized gate and do not start full training unless the revised criterion passes.
- **Finding:** The exact accepted release and mandated 128 lexical training IDs were verified. Two pairs have identical board/state/history/candidate tensors and UCI identity but different `played_move_uci` targets. Any deterministic legal top-1 scorer receiving the same contract input returns one action for each pair, so at most 126/128 labels can be correct. The gate reached CE 0.02195480 and top-1 126/128 after 500 updates; CE passed and top-1 failed. No dataset, sample, target, threshold, or model-input contract was changed. Full training and evaluation were not run.
- **Resolution:** Pending the explicit protocol decision and a successful rerun of the applicable sanity gate.
