# M4-001 Conditional Owner Authorization — 2026-10-23

- **Authorization ID:** `M4-001-owner-conditional-20261023`
- **Recorded:** 2026-10-22T17:44:36Z (2026-10-23 Asia/Ho_Chi_Minh)
- **Authority:** Direct project-owner instruction in the current mission, “Post-Pre-M4 Closure, Lossless Checkpoint Migration, and Conditional M4-001 Execution.”
- **Task:** `M4-001`
- **Status:** Conditional authorization recorded; **not operational** because mandatory entry conditions and owner decisions remain outstanding.
- **G3:** Unapproved; this record does not approve or close G3.
- **ADR-0003:** Proposed; this record does not accept the ADR.

The owner directly requested and conditionally authorized M4-001. The authorization becomes operational only after every mandatory entry condition below is verified and applicable owner decisions are recorded. Until then, `engineering.start_authorized` must remain `false`, `engineering.active_milestone` and `task_refs.active_task_id` must remain `null`, and the backlog task must remain `pending`.

**Recorded result:** Conditional authorization recorded but not operational; M4-001 remains pending and no implementation or training may start until all conditions are verified and the authorization is activated in canonical state.

## Conditions before activation

1. The lossless RSK-010 migration PR is reviewed and merged into `initial-idea`; a clean clone of the resulting integration commit passes archive verification and canonical preflight.
2. The exact accepted M3 release `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890` is available at an owner-authorized local path. Its manifest, all nine listed files, split identities, and train/validation/test separation are verified without modifying the artifacts.
3. O-01 is resolved with authoritative assignment/instructor guidance for ALE observation/action wrappers, custom PyTorch RL, behavior cloning, and applicable engine-evaluation limits.
4. The owner explicitly decides ADR-0003 (accept, accept with modifications, or reject and replace). Implementation must follow the resulting recorded decision.
5. The task plan, data-use boundary, local CPU/time/memory budgets, and current canonical M4/M3 dependencies are rechecked. No new dataset, Stockfish role, external compute, storage, ROM activity, or scope expansion is authorized here.

## Authorized scope after activation

If these conditions are met and this instruction remains in force, this authorization covers only the bounded M4-001 behavior-cloning implementation, verification, CPU experiment, and evidence described in `.agents/plans/M04-supervised-pretraining.md` and `docs/04-research/TRAINING_PROTOCOL.md`. It does not authorize M5/M6, Stockfish in the initial behavior-only run or inference, cloud/GPU spending, new data acquisition, ROM changes, G3 approval, or PR merging.

No M4 implementation or training has started under this conditional record. The current hold conditions are summarized in `.agents/state/PROJECT_STATE.yaml` and `.agents/tasks/BACKLOG.yaml`.
