# Active Blockers

**Canonical source for:** active/resolved blockers and their impact, evidence, owner, and unblock condition. External approvals remain in `docs/01-foundation/REQUIREMENTS.md`; ordinary pending tasks remain in `.agents/tasks/BACKLOG.yaml`.

## Current status

G0–G3 are approved; M0-001 through M5-001 are complete. M5 was accepted by the independent PM on 2026-10-30 subject to documented M5-03/M5-04 limitations. PR #11 integrated M5; PR #12 recorded the independent G3 approval in `.agents/evidence/G3-final-approval-20261030.md`. M6 is the next engineering milestone and remains not authorized or started. No active blocker is recorded. BLK-002 is resolved by the dated PM amendment and revised input-distinct gate PASS; see the [M4 acceptance report](../evidence/M4-final-acceptance-20261027.md). Its original 126/128 failure and diagnosis remain historical and unchanged. O-01 is closed internally; absence of instructor-policy evidence is informational, is not formal approval, and did not block M4. BLK-001 remains resolved with phase-specific RGB control, explicit runner stop categories, and two repeatable real-ALE terminal/reward traces. The terminal screen does not show a parseable final board, and the exact ROM-level target-FIRE polling mechanism remains unknown; the runner retains the last verified FEN and stops safely. O-02–O-08 retain their scoped status in `REQUIREMENTS.md`; RAM remains diagnostic-only and no formal instructor approval is claimed. BLK-003 is resolved by PM risk acceptance; RSK-014 remains an accepted residual provenance risk because complete historical `cli.py` bytes are unavailable. The six-run M2 simulator campaign and 1,500-game simulator evaluation are complete. These results do not establish Atari performance or authorize M6.

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
- **Resolution:** RGB demonstrated the previously failing source-selection, selected-target-preview, and 16-frame target-confirmation phases; a 20-cycle run and new mode-0/mode-4 runs show extended legal play. The mode-4 runner's ten-mismatch early stop was removed and replaced with bounded waiting plus an RGB reply-source-cursor readiness condition. Two fresh deterministic mode-4 runs then reproduced ALE reward `-1.0`, `terminated=true`, `truncated=false`, and the same terminal RGB hash after the same three verified player/Atari cycles. The final terminal screen clears the chessboard; the runner records the last independently verified FEN before the unconfirmed terminal move and does not advance its shadow. This meets the recorded final verified board-state requirement without claiming a final board parse. The ROM's internal FIRE polling/debounce mechanism remains an implementation limitation, not an unresolved unsafe control state. No further M1 blocker remains. That sentence records the authorization state at BLK-001 closure; M2, M3, and their acceptance are now documented in the later milestone records. G3 was still unapproved at the time of that closure.

## BLK-002 — Fixed M4 sanity sample has conflicting identical-input labels

- **Status:** `resolved`
- **Owner:** Project PM, acting under explicit owner delegation, approved the narrow sample-selection protocol amendment; M4 executor records and runs it.
- **Reported:** 2026-10-27T13:33:05.861961Z
- **Impact:** M4-001; M4-02 fails the required top-1 threshold, so M4-03 and M4-04 have not started and M4 cannot be accepted.
- **Evidence:** `.agents/evidence/M4-02-sanity-gate-blocker-20261027.md`; `.agents/evidence/logs/M4-02-sanity-gate-diagnostic-20261027.json`; `.agents/evidence/logs/M4-sanity-gate-r2-20261027.txt`; `.agents/evidence/logs/M4-02-sanity-gate-diagnostic-20261027.txt`; preserved local run artifacts under `/home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r2/`.
- **Unblock condition:** Satisfied by `.agents/evidence/M4-02-protocol-amendment-20261027.md` and the fresh revised gate PASS recorded in `.agents/evidence/M4-final-acceptance-20261027.md`. The amendment preserved the accepted release, labels, model contract, seed, update cap and thresholds, changing only selection to the first 128 pairwise-distinct complete effective model inputs in ascending train `sample_id` order.
- **Finding:** The exact accepted release and mandated 128 lexical training IDs were verified. Two pairs have identical board/state/history/candidate tensors and UCI identity but different `played_move_uci` targets. Any deterministic legal top-1 scorer receiving the same contract input returns one action for each pair, so at most 126/128 labels can be correct. The gate reached CE 0.02195480 and top-1 126/128 after 500 updates; CE passed and top-1 failed. No dataset, sample, target, threshold, or model-input contract was changed. Full training and evaluation were not run.
- **Resolution:** The explicit PM protocol decision resolved the original sample-selection infeasibility. A fresh revised run passed at update 140 with CE 0.0385448446 and legal top-1 127/128 (99.21875%) under the unchanged thresholds. The corrected bounded training, frozen evaluation, engine-free checkpoint/inference checks, and required simulator evaluation subsequently completed; M4-01 through M4-04 passed and M4-001 is done. The original failed run and diagnostic remain unchanged and are not counted as a pass.

## BLK-003 — M5 training source versions differ; residual CLI bytes accepted by PM

- **Status:** `resolved`
- **Owner:** Independent PM disposition recorded; Codex maintains the evidence and canonical state
- **Reported:** 2026-10-30T04:59:39Z
- **Impact:** M5-001 acceptance and auditability of source differences across the six-run campaign
- **Evidence:** `.agents/evidence/M5-training-campaign-verification-20261029.json`; `.agents/evidence/M5-source-reconciliation-20261030.json`; `.agents/evidence/M5-source-recovery-20261030.json`; `.agents/evidence/M5-source-recovery-verification-20261030.json`; `.agents/evidence/M5-source-semantics-20261030.json`; `.agents/evidence/M5-PM-acceptance-20261030.md`; `.agents/state/checkpoint-history/segments/` snapshots `cp-08f98f9d-20261029T043013180672Z` and `cp-08f98f9d-20261029T143803674896Z`; actual restore logs and the incomplete optional full-history differential log in `.agents/evidence/logs/`.
- **Original finding preserved:** The source aggregates differ (four runs at `093992…`, two at `cdcc1f…`) and three Python files changed. At initial report time, historical source bytes were unavailable and replay sampling changes could not be excluded.
- **Forensic update:** The supplied transcript recovers `checkpoint.py` and `replay.py` byte-for-byte at their recorded earlier SHA-256 values. AST/diff analysis shows replay insertion, eviction, sampling, state methods, and journal append are unchanged; checkpoint changes concern validation/restoration. Full historical CLI bytes remain unavailable, although the transcript records relevant resume-selector changes. Both seed-20261106 runs were fresh `attempt-0000` runs with no resume parent. No learning-distribution change is evidenced. The source groups remain distinct and the three-seed study remains statistically limited.
- **Unblock condition:** Satisfied by the independent PM disposition published 2026-10-30T08:22:10Z in [PR #11 comment 6518394524](https://github.com/dodaonam/atari-videochess-rl/pull/11#issuecomment-6518394524), permanently recorded in `.agents/evidence/M5-PM-acceptance-20261030.md`. The PM accepted M5-03/M5-04 with limitations and authorized resolving BLK-003 by risk acceptance. No additional training/evaluation is required or authorized. This resolution does not claim complete historical CLI recovery, strict source homogeneity, byte-identical reproduction, PR merge, G3 approval, or M6 authorization.
