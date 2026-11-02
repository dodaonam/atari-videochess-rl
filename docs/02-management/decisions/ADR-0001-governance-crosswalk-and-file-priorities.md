# ADR-0001: Governance Crosswalk and File Priorities

- **Status:** Accepted for project governance
- **Date:** 2026-10-14
- **Decision owner:** Project user, through the authorized G1 request; technical mapping is recorded by Codex
- **Scope:** Internal project workflow only. This ADR does not approve academic constraints, external services, compute costs, or any M0/M1 work.
- **Evidence:** `chat_history.md` final inventory and phase descriptions; `docs/02-management/EXECUTION_PLAN.md`; current user authorization to resolve G/M and priority inconsistencies.

## Context

The conversation uses two different label systems. `G0–G5` describe documentation/governance rollout; `M0–M7` describe technical work. Earlier messages also disagree about whether milestone plans are P0 or P2. Leaving the mapping implicit makes state and task handoffs ambiguous.

## Decision

1. Keep governance gates and engineering milestones as distinct identifiers and status fields.
2. Use this crosswalk:

   | Governance gate | Engineering coverage |
   |---|---|
   | G0 — Documentation foundation | No engineering milestone. |
   | G1 — Persistent context and governance | No engineering milestone. |
   | G2 — Technical feasibility | M0 technical bootstrap, followed by M1 ALE feasibility. |
   | G3 — Chess foundation and learning | M2–M5. |
   | G4 — Atari integration and evaluation | M6 and the evaluation portion of M7. |
   | G5 — Delivery | The delivery portion of M7. |

3. M0 is the next engineering milestone after G1 review approval. M1 depends on M0. Neither milestone is active or authorized by this ADR.
4. Adopt the latest fixed-file classification recorded in `EXECUTION_PLAN.md`. The older chat entry that classified all M-plans as P0 remains historical and is superseded for future planning; the execution plan is the canonical inventory.
5. Create P2 materials only when a milestone or decision requires them. This ADR was created during G1 because the user explicitly requested a durable record of the governance decision; defer other P2 materials according to `EXECUTION_PLAN.md`.

## Alternatives considered

- **Merge G and M labels:** rejected because they represent different kinds of gates and would obscure whether a governance review or technical acceptance passed.
- **Leave the crosswalk unresolved:** rejected because the user explicitly asked G1 to resolve it and future state needs a stable next-milestone pointer.
- **Keep milestone plans in P0:** rejected in favor of the latest detailed inventory in `EXECUTION_PLAN.md`, which creates milestone plans only when their work approaches.

## Consequences

- This ADR is the sole owner of the accepted crosswalk and its classification rationale. `EXECUTION_PLAN.md` owns engineering order, dependencies, deliverables, and the fixed-file inventory; `ACCEPTANCE_CRITERIA.md` owns pass conditions and allocates M7-01–M7-03 to G4 evaluation and M7-04–M7-05 to G5 delivery; `PROJECT_STATE.yaml` owns live status.
- G1 closes at user review. M0 remains not started until the user separately approves proceeding after G1.
- G2–G5 and M0–M7 remain separate in future plans, tasks, reports, and validation.
- Academic/external approvals O-01–O-08 in `REQUIREMENTS.md` were open when this 2026-10-14 process ADR was accepted and were not resolved by it. The project owner later closed O-01 for internal execution on 2026-10-27; this ADR does not establish instructor approval. See the current requirements register.

## Supersession

A later user-approved decision may replace this mapping or inventory. Preserve this ADR and mark it `superseded`, linking to the replacement.
