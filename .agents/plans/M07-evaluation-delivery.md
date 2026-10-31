# M7 Evaluation and Delivery Plan

**Status:** Proposed Pre-M7 plan; M7 is not started or authorized.
**Acceptance source:** [`ACCEPTANCE_CRITERIA.md`](../../docs/06-quality/ACCEPTANCE_CRITERIA.md), M7-01–M7-05.
**Scientific contract:** [`M7_EVALUATION_PROTOCOL.md`](../../docs/04-research/M7_EVALUATION_PROTOCOL.md).
**Ownership:** ADR-0001 assigns M7-01–M7-03 evaluation evidence to G4 and M7-04–M7-05 delivery evidence to G5.

## 1. Entry boundaries

M7 work starts only after a separate direct owner authorization is recorded in canonical state/backlog and the independent PM has made the applicable G4 decision. This plan and a passing PR do not authorize execution. M7 contains evaluation and delivery only; it does not authorize retraining, fine-tuning, a new simulator/ALE campaign, cloud allocation, Stockfish use, or publication. The protocol and resource choices are proposals pending owner approval. Any new official evaluation needs its own written scope and resource envelope.

The planned task records are `M7-001` through `M7-005`, all `pending`. M7-001 is the next task pointer only; it is not active. M7-001–003 implement the G4 evaluation criteria and therefore do not require G4 approval as a prerequisite to their own acceptance. M7-004/005 depend on completed evaluation and G4 approval. All tasks still require the direct M7 task authorization in canonical state before starting.

## 2. Work breakdown and acceptance

| Order / task | Criterion and gate owner | Dependencies | Deliverables and completion evidence |
|---|---|---|---|
| M7-001 — Reconcile accepted populations and run only the authorized comparison set | M7-01 / G4 | M2-001, M3-001, M4-001, M5-001, M6-001 | Frozen population table; exact policy/checkpoint/config/run identities; environment, opponent, seed, color, schedule, and denominators. Reuse accepted M4/M5/M6 data by default. If and only if separately authorized, execute the protocol's bounded comparison branch and retain immutable raw manifests/logs. No training/fine-tuning. |
| M7-002 — Analyze outcomes, uncertainty, missingness, and claims | M7-02 / G4 | M7-001 | W/D/L and score tables with terminal/truncated/incomplete denominators; legal/controller/synchronization/timeout metrics; runtime/resource accounting; paired estimates and cluster-aware uncertainty; confirmatory/exploratory/post-hoc labels; explicit censoring and limitations. |
| M7-003 — Decide whether a calibrated Elo result is reportable | M7-03 / G4 | M7-002 | Either a pool-approved, calibrated, reproducible rating with conditions and uncertainty, or an explicit “Elo not reported” disposition with the unmet requirements. No assumed 1500 rating. |
| M7-004 — Prepare evidence-linked final report, model card, usage guide, and handover | M7-04 / G5 | M7-003; G4 decision approved | `docs/07-delivery/FINAL_REPORT.md`, `MODEL_CARD.md`, `USER_GUIDE.md`, and `HANDOVER.md` cite actual run IDs, source revisions, configs, checkpoint hashes, raw evidence boundaries, limitations, and reproduction steps. Delivery remains private until separately authorized. |
| M7-005 — Record release/publication disposition | M7-05 / G5 | M7-004; G4 approved | Record explicit owner authorization before any release or publication. If no authorization exists, record a no-release disposition and retain private artifacts locally. G5 approval alone is not publication authorization. |

All tasks have explicit next actions and remain pending/unauthorized in `BACKLOG.yaml`. Criterion ownership remains split: G4 decides M7-01–03; G5 decides M7-04–05. PM gate decisions do not substitute for direct owner task authorization; task authorization does not imply a PM gate decision.

## 3. Execution order and checkpoints

1. Obtain the G4 PM decision and separate direct owner authorization for M7-001. Resolve the owner choices that affect population, protocol, and resources.
2. Reverify frozen inputs read-only against the identities in the approved protocol. Stop on a manifest mismatch; do not repair or regenerate frozen evidence.
3. Use existing accepted measurements first. Run only explicitly authorized new evaluation, with a predeclared schedule and terminal/incomplete policy. No model update or Stockfish evaluation/opponent is allowed under this plan.
4. Freeze the analysis and disclose all scheduled denominators, missing attempts, deviations, and inference limits before writing conclusions.
5. Complete the Elo gate as a reportability decision; absence of a calibrated pool means “not reported.”
6. Obtain G4 disposition before starting the G5 delivery tasks. Draft the four delivery documents with traceable evidence, then request G5 review.
7. Keep any release/publication action out of scope until separate explicit owner authorization. Never self-approve or merge a review PR.

Refresh checkpoints before a long authorized task, after task/gate transitions, and before handoff. Preserve a failed run and its log; do not rerun or replace a scheduled attempt unless a new approved protocol explicitly permits it.

## 4. Resource plan and decision matrix

### Measured baseline

| Workload | Accepted observed use | Planning interpretation |
|---|---|---|
| M5 frozen simulator evaluation | 1,500 rows in 1,983.451 seconds (0.551 CPU-hours); six 400-decision truncations; full M5 root artifacts 6,544,747,450 bytes. | Existing data is reusable. An exact rerun adds little scientific value and is not proposed. This is M2 simulator throughput, not an ALE runtime estimate. |
| M6 v2 ALE | 20 attempts in 3,519.969 gameplay seconds (0.978 hours); peak RSS 620,105,728 bytes; 728,148,524 artifact bytes; v2 caps 1,800 seconds/attempt, 43,200 seconds/campaign, 6 GiB RSS, and 8 GiB artifacts. | Observed duration was 175.998 seconds/attempt, but incomplete/timeouts and long tails make that an expectation only. Keep the accepted 1,800-second stop per attempt. |
| Current local host snapshot | 8 logical CPUs; 33.49 GB RAM total, 24.91 GB available; 50.71 GB filesystem free at 2026-10-31T14:22:18Z. | Local CPU and current free storage exceed the historical M6 v2 preflight minimum of 12 GiB. This is a point-in-time capacity observation, not future reservation. See [resource snapshot](../evidence/PRE-M7-resource-snapshot-20261031.json). |

### Bounded options (none authorized)

| Option | Purpose / expected resource | Maximum / storage / limitation | Decision |
|---|---|---|---|
| Reuse accepted evidence only | Existing M4/M5/M6 data and current read-only audits; no official game or training compute. | Analysis only; preserves all accepted denominators and limitations. | **Recommended default.** No new evaluation is needed to prepare this package. |
| Repeat M2 simulator schedule | Adds little to the existing 1,500 rows; expected about 0.55 CPU-hours at the measured rate. | A rerun would still have three training-seed clusters and would not increase independent training replication. Storage must be measured from its own output; do not infer it from the whole M5 root. | Not recommended; would need separate owner authorization and pre-registration. |
| Optional ALE comparison across the complete frozen population | 9 policy groups: six M5 post-RL snapshots (Warm/Scratch × 3 training seeds), one M4 r4 model, RandomLegal, and SimpleHeuristic; 10 common new ALE seeds per policy = 90 attempts. Agent White; same approved ROM/profile/opponent; no policy selection or replacement. | Expected ≈4.4 gameplay hours if the M6 v2 observed mean repeats; strict max = 90 × 1,800 s = 45 hours, before setup/recovery. Linear storage estimate ≈3.28 GB based on 728,148,524 bytes/20 attempts; cap at 8 GiB plus reserve and recheck free disk before authorization. Three training-seed clusters still limit generalization; 10 ALE seeds per policy is operationally informative, not strong proof of superiority. Current M6 config's 20-attempt ceiling cannot be silently reused; a separately versioned and approved config/budget is required. | Scientifically useful for breadth across all three M5 training seeds, but not justified before the 2026-11-03 presentation deadline without explicit owner approval. Do not run during Pre-M7. |
| Colab CPU/T4 | No current evidence that remote compute improves this serial controller/ALE loop; T4 does not accelerate Atari frame stepping. | Entitlement, quota, storage, privacy pathway, and paid-use permission are unknown. A T4 would be serialized with no concurrent T4 sessions and would add transfer/runtime variance. No Colab CU accounting. | Not proposed. Owner must separately approve any cloud use and verify access first. |

If the optional ALE branch is later authorized, use one local ALE process at a time, no concurrent T4 session, no cloud transfer, and a separately approved 8 GiB artifact ceiling. Before the first reset verify disk reserve, exact checkpoint/ROM/config hashes, and output path. Stop an attempt at 1,800 seconds or any controller/synchronization uncertainty; classify it as incomplete and preserve it. Allow at most one global process-start retry before any ALE action, no reset replacement, and no post-result rerun. Resume only from an independently verified checkpoint/ledger boundary and with explicit approval; otherwise close the campaign as partial with the original schedule denominator. Never overwrite a frozen M4/M5/M6 path.

## 5. Privacy and handling

Raw ALE RGB, ROM files, local M3 source data, M4/M5 checkpoints, and M5 raw game/training records remain in owner-controlled local artifact storage. Commit only sanitized reports, hashes, configs without secrets/private payloads, and logs whose contents are reviewed. Do not upload artifacts to GitHub, Colab, Drive, or another service. Any later artifact transfer, dataset redistribution, model release, or public publication needs separate owner authorization and rights review.

## 6. Closeout and gate criteria

M7-001–003 are complete only when the approved protocol's populations and denominators are traceable, analysis distinguishes all evidence tracks, required uncertainty and censoring limits are reported, deviations are listed, and the G4 PM decision is recorded. M7-003 may validly conclude that Elo is not reportable. M7-004 is complete only when the four delivery documents reproduce actual evidence identities and limitations. M7-005 is complete only with a recorded owner release decision; absent permission, the correct deliverable is an explicit no-release disposition. G4 and G5 evidence/status remain separate throughout.
