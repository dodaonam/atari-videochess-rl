# Active Blockers

**Canonical source for:** active/resolved blockers and their impact, evidence, owner, and unblock condition. External approvals remain in `docs/01-foundation/REQUIREMENTS.md`; ordinary pending tasks remain in `.agents/tasks/BACKLOG.yaml`.

## Current status

G0, G1, and G2 are approved; M0-001 and M1-001 are complete, M2-001 is complete, M3-001 is accepted and merged, and M4-001 is complete with M4-01 through M4-04 evidence. G3 remains unapproved. BLK-002 is resolved by the dated PM amendment and the revised input-distinct gate PASS; see the [M4 acceptance report](../evidence/M4-final-acceptance-20261027.md). The original 126/128 failure and its diagnosis remain historical and unchanged. No active M4 blocker remains. O-01 is closed internally; absence of instructor-policy evidence remains informational, is not formal approval, and did not block M4. BLK-001 remains resolved with phase-specific RGB control, explicit runner stop categories, and two repeatable real ALE terminal/reward traces. The terminal screen does not show a parseable final board, and the exact ROM-level target-FIRE polling mechanism remains unknown; the runner retains the last verified FEN and stops safely. O-02–O-08 retain their scoped status in `REQUIREMENTS.md`; RAM remains diagnostic-only and no formal instructor approval is claimed. M5-001 was directly owner-authorized and resumed. The six-run simulator campaign and 1,500-game evaluation completed; active BLK-003 records an unresolved training source-version comparison. G3 remains unapproved and M6 has not started.

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

- **Status:** `resolved`
- **Owner:** Project PM, acting under explicit owner delegation, approved the narrow sample-selection protocol amendment; M4 executor records and runs it.
- **Reported:** 2026-10-27T13:33:05.861961Z
- **Impact:** M4-001; M4-02 fails the required top-1 threshold, so M4-03 and M4-04 have not started and M4 cannot be accepted.
- **Evidence:** `.agents/evidence/M4-02-sanity-gate-blocker-20261027.md`; `.agents/evidence/logs/M4-02-sanity-gate-diagnostic-20261027.json`; `.agents/evidence/logs/M4-sanity-gate-r2-20261027.txt`; `.agents/evidence/logs/M4-02-sanity-gate-diagnostic-20261027.txt`; preserved local run artifacts under `/home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r2/`.
- **Unblock condition:** Satisfied by `.agents/evidence/M4-02-protocol-amendment-20261027.md` and the fresh revised gate PASS recorded in `.agents/evidence/M4-final-acceptance-20261027.md`. The amendment preserved the accepted release, labels, model contract, seed, update cap and thresholds, changing only selection to the first 128 pairwise-distinct complete effective model inputs in ascending train `sample_id` order.
- **Finding:** The exact accepted release and mandated 128 lexical training IDs were verified. Two pairs have identical board/state/history/candidate tensors and UCI identity but different `played_move_uci` targets. Any deterministic legal top-1 scorer receiving the same contract input returns one action for each pair, so at most 126/128 labels can be correct. The gate reached CE 0.02195480 and top-1 126/128 after 500 updates; CE passed and top-1 failed. No dataset, sample, target, threshold, or model-input contract was changed. Full training and evaluation were not run.
- **Resolution:** The explicit PM protocol decision resolved the original sample-selection infeasibility. A fresh revised run passed at update 140 with CE 0.0385448446 and legal top-1 127/128 (99.21875%) under the unchanged thresholds. The corrected bounded training, frozen evaluation, engine-free checkpoint/inference checks, and required simulator evaluation subsequently completed; M4-01 through M4-04 passed and M4-001 is done. The original failed run and diagnostic remain unchanged and are not counted as a pass.

## BLK-003 — M5 training source versions cannot be reconstructed

- **Status:** `active`
- **Owner:** Independent PM for experimental disposition; Codex for evidence preservation and remediation
- **Reported:** 2026-10-30T04:59:39Z
- **Impact:** M5-001, M5-03 replay/provenance interpretation, M5-04 pooled cross-seed comparison and engineering acceptance
- **Evidence:** `.agents/evidence/M5-training-campaign-verification-20261029.json`; `.agents/evidence/M5-source-reconciliation-20261030.json`; `docs/04-research/M5_REMEDIATION_AUDIT.md`; `.agents/evidence/logs/M5-source-reconciliation-20261030.log`; `.agents/evidence/logs/M5-source-backup-search-20261030.log`; `.agents/state/checkpoint-history/segments/` snapshots `cp-08f98f9d-20261029T043013180672Z` and `cp-08f98f9d-20261029T143803674896Z`.
- **Finding:** Four runs record source `093992c50e893a7fdd92f2f95faafe28d4f1e73c7351a4a8179a3056c4e63b00`; both seed-20261106 runs record `cdcc1fdc0ca0b324e49cfb8b0ff571496a554e9892dfb3620d6454a65ee16da0`. Checkpoint history identifies changed files `checkpoint.py`, `cli.py`, and `replay.py`. Their earlier source snapshots and the later seed-20261106 CLI snapshot are absent from available Git blobs and searched local backups. The old replay implementation cannot be diffed, so a sampling/learning-distribution change cannot be excluded. Both seed-20261106 arms are internally source-matched; source version is confounded with that training-seed cluster in pooled inference.
- **Unblock condition:** Recover authentic source snapshots and verify the exact diffs/semantics, or obtain an independent PM experimental disposition that explicitly addresses the missing source and pooled-analysis limitation. Any additional training requires separate PM authorization. Preserve all original artifacts; no rerun has started.
