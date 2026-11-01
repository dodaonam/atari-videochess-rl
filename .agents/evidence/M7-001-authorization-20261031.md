# M7-001 Direct Owner Authorization — Option B

**Recorded at:** 2026-10-31T16:02:51Z
**Authority:** Project owner, direct instruction in this Codex session
**Source reference:** “MASTER EXECUTION ORDER — COMPLETE M7 EVALUATION AND DELIVERY,” owner-authorized Option B. The direct instruction contains no external URL, signature, or separately stated issuance timestamp; this record does not invent one.
**Authorization ID:** `M7-AUTH-20261031-OPTION-B`
**Authorized task:** M7 / M7-001
**Integration baseline:** `initial-idea` at `257fff94c64bc584797e0d191920a57befcae62c` (PR #16 merge)

## Decision

The project owner directly authorizes Phase I of M7 now: M7-001, M7-002, and M7-003. This supersedes the earlier Pre-M7 proposal's requirement to wait for a separate G4 decision before starting this evaluation work. The independent PM's G4 disposition remains **HOLD / NOT APPROVED**; this authorization is not a G4 decision or acceptance.

M7-001 is authorized to reverify accepted M4/M5/M6 inputs and execute one local CPU ALE/VideoChess campaign of exactly 90 scheduled attempts: the six accepted M5 post-RL checkpoints (Warm-start and Scratch for training seeds `20261104`, `20261105`, `20261106`), accepted M4 r4 behavior-only policy, RandomLegal, and SimpleHeuristic, each on the same ten ALE evaluation seeds `20261201`–`20261210`. Use the exact accepted VideoChess ROM and the M6 v2 extended-horizon profile, with one ALE process at a time, no more than 1,800 seconds per attempt, an 8 GiB new-artifact ceiling, and at least 12 GiB free before execution. Freeze the separately versioned configuration and immutable run identity before the first official attempt.

M7-002 is authorized for analysis of the accepted historical evidence and the complete M7-001 record. M7-003 is authorized to conclude Elo is not reported because no calibrated opponent pool/design has been approved. No retraining, fine-tuning, replacement checkpoints, simulator campaign, Stockfish opponent/evaluation, cloud/GPU resource, private artifact transfer, or public distribution is authorized.

M7-004 and M7-005 remain gated. Do not start either until the independent PM has approved G4 and that decision is represented and verified in canonical state. The owner has not authorized release or publication; the required M7-005 disposition is no release unless a later direct owner decision changes that boundary.

## Review and integration boundaries

PR #16 is verified merged into `initial-idea` at the baseline above. Its independent PM review separately recorded G4 as HOLD / NOT APPROVED. M7 engineering completion does not change that disposition. The M7 evaluation package may be committed, pushed on its feature branch, and submitted as an open, non-draft PR for G4 review. It must remain unmerged and may not be self-approved. No commit, push, or publication to `initial-idea`/`main`, no merge, and no release is authorized.

## Canonical status

This evidence is referenced by `.agents/state/PROJECT_STATE.yaml` and the M7-001 record in `.agents/tasks/BACKLOG.yaml`. Approval of G4/G5, PR integration, and publication remain separate status dimensions.
