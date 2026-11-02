# M4-001 Conditional Owner Authorization — 2026-10-23

- **Authorization ID:** `M4-001-owner-conditional-20261023`
- **Recorded:** 2026-10-22T17:44:36Z (2026-10-23 Asia/Ho_Chi_Minh)
- **Authority:** Direct project-owner instruction in the current mission, “Post-Pre-M4 Closure, Lossless Checkpoint Migration, and Conditional M4-001 Execution.”
- **Task:** `M4-001`
- **Status at original record (2026-10-23):** Conditional authorization recorded; not operational because then-current entry conditions and owner decisions remained outstanding. The O-01-only activation condition was superseded by the dated 2026-10-27 addendum below; that addendum owns the current internal authorization status.
- **G3:** Unapproved; this record does not approve or close G3.
- **ADR-0003 at the original conditional-authorization decision:** Proposed; this record did not itself accept the ADR. The project owner accepted it on 2026-10-23; see [acceptance evidence](ADR-0003-acceptance-20261023.md).

At the time this record was created, the owner had directly requested and conditionally authorized M4-001. The conditions below preserve that historical decision context. The dated 2026-10-27 addendum supersedes the O-01-only condition and records the current internal authorization; consult canonical state and backlog for its live status.

**Recorded result:** Conditional authorization recorded but not operational; M4-001 remains pending and no implementation or training may start until all conditions are verified and the authorization is activated in canonical state.

## Conditions before activation

1. The lossless RSK-010 migration PR is reviewed and merged into `initial-idea`; a clean clone of the resulting integration commit passes archive verification and canonical preflight.
2. The exact accepted M3 release `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890` is available at an owner-authorized local path. Its manifest, all nine listed files, split identities, and train/validation/test separation are verified without modifying the artifacts.
3. O-01 is resolved with authoritative assignment/instructor guidance for ALE observation/action wrappers, custom PyTorch RL, behavior cloning, and applicable engine-evaluation limits.
4. The owner explicitly decides ADR-0003 (accept, accept with modifications, or reject and replace). Implementation must follow the resulting recorded decision.
5. The task plan, data-use boundary, local CPU/time/memory budgets, and current canonical M4/M3 dependencies are rechecked. No new dataset, Stockfish role, external compute, storage, ROM activity, or scope expansion is authorized here.

## Authorized scope after activation

If these conditions are met and this instruction remains in force, this authorization covers only the bounded M4-001 behavior-cloning implementation, verification, CPU experiment, and evidence described in `.agents/plans/M04-supervised-pretraining.md` and `docs/04-research/TRAINING_PROTOCOL.md`. It does not authorize M5/M6, Stockfish in the initial behavior-only run or inference, cloud/GPU spending, new data acquisition, ROM changes, G3 approval, or PR merging.

No M4 implementation or training had started as of the 2026-10-23 verification update. The 2026-10-27 addendum and current `.agents/state/PROJECT_STATE.yaml` / `.agents/tasks/BACKLOG.yaml` supersede this historical status statement.

## Verification update — 2026-10-23

Against integration commit `d9f0872c120fb2408343859c938257e3962f2e09`, condition 1 (PR #5 integration plus archive/recovery verification), condition 2 (owner-specified exact local M3 release availability and identity), and condition 4 (ADR-0003 owner decision) are evidenced in [the final Pre-M4 closure report](PRE-M4-final-closure-20261023.md), [checkpoint migration evidence](RSK-010-checkpoint-history-migration-20261023.md), [M3 local release verification](M3-release-local-verification-20261023.md), and [ADR-0003 acceptance](ADR-0003-acceptance-20261023.md). The bounded plan, data-use boundary, local CPU/time/memory budgets, and M3 dependency were rechecked for condition 5.

Condition 3 remains unmet: this repository review found no authoritative external assignment/instructor policy document or response for the applicable O-01 questions. Owner-confirmed technical choices are recorded separately and are not treated as instructor approval. Therefore this conditional authorization is still **not operational**: keep M4-001 pending, `engineering.active_milestone: null`, `engineering.start_authorized: false`, `task_refs.active_task_id: null`, and G3 unapproved. No M4 implementation or training has started.


## Supersession addendum — 2026-10-27

- **Decision ID:** O-01-owner-close-20261027.
- **Decision authority:** Project owner, by direct instruction dated 2026-10-27; see [O-01 owner-decision evidence](O-01-owner-decision-20261027.md).
- **Direct authorization evidence:** Direct project-owner authorization for bounded M4-001 is recorded here. Canonical state marks it `ready_to_start` after the documented Pre-M4 conditions and PR #6 integration checks pass.
- **Recorded at:** 2026-10-27T10:26:30Z.
- **Superseded condition:** Condition 3 above, which required authoritative external course-policy evidence as an M4-001 activation prerequisite for the owner-selected wrappers, custom PyTorch, behavior cloning, and applicable teacher role.

The owner closes O-01 for internal project planning and execution authorization and confirms the selected technical decisions are final. No additional owner confirmation is required. This dated decision supersedes the O-01-only external-confirmation prerequisite above. Conditions 1, 2, 4, and 5 remain subject to their stated factual checks; this mission records those checks separately in the final Pre-M4 evidence.

No instructor or assignment-policy approval has been evidenced by this decision, and none is claimed. The absence of an external response is an informational residual, not a blocker to M4-001. If an actual authoritative course instruction explicitly contradicting an owner-selected activity is discovered, stop only that affected activity and record the concrete rule.

After the other applicable Pre-M4 conditions and integration checks pass, the conditional authorization is operational for the scope below. Canonical state records M4 as ready_to_start with start_authorized true, active_milestone null, and no active task; M4-001 remains pending until an executor actually begins implementation. G3 remains unapproved and is not an M4 start prerequisite. This mission does not start the neural implementation or training, pass M4 acceptance, authorize M5/M6, or expand the data, Stockfish, compute, storage, or ROM scope.

The bounded M4-001 scope remains the behavior-cloning model, tests, local CPU training/evaluation, and evidence defined by .agents/plans/M04-supervised-pretraining.md, MODEL_DESIGN.md, and TRAINING_PROTOCOL.md. The first run uses only played_move_uci behavior targets; Stockfish scores and teacher targets are excluded. Reverify the exact accepted local M3 release before loading it. No external compute/runtime or new data is authorized.

This supersession changes only the operative internal O-01 activation condition. The original conditional record and its 2026-10-23 context above remain preserved as historical authorization history.
