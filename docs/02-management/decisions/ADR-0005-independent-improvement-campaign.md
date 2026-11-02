# ADR-0005 — Independent post-closeout improvement campaign

- Status: Accepted for Phase 1 by direct Project Owner assignment dated 2026-11-03.
- Authority: the current Phase 1 execution assignment; no independent PM approval is implied.
- Experiment: `videochess-improvement-20261103-v1`.

The completed historical M0–M7 program, G0–G5 approvals, and its final scientific
results remain attributable and unchanged. The prior canonical engineering
closeout stated that no further campaign was authorized. The owner has now
explicitly authorized a separate campaign. These statements describe different
authorization times; the current assignment supersedes the earlier blanket
restriction only within its Phase 1 scope. Historical gate and experiment
ceilings are not imported into this campaign. Current campaign execution status
is recorded separately under `improvement_campaign` in project state.

Phase 1 selects a new disjoint 5,000-game dataset, performs bounded fixed-seed
Optuna GP HPO and offline Stockfish supervision, fine-tunes the accepted M4,
and prepares a single warm Double DQN run. The accepted architecture remains
unchanged. M4 behavior logits are not Q values: only the shared representation
transfers, with a fresh Q head. A frozen M4 guides a decaying portion of
exploration; final Q evaluation is independent. The selected schedules and
numerical budgets come from the assignment, not a claim of scientific optimality.

Source/configuration changes and feature-branch commits/pushes are authorized.
The owner separately authorized local Optuna and necessary GP dependency
installation. All datasets, labels, checkpoints, ROMs, RGB frames and move-level
traces remain private local artifacts. No additional compute allocation or
external storage is authorized or used. The third-party source license remains
unstated; local internal use does not establish redistribution rights.

The single official 250,000-decision run belongs to a separately assigned Phase 2.
Phase 1 permits only disposable readiness probes. It does not authorize a scratch
arm, multiple official training seeds, final consolidation PR, merge, auto-merge,
release, deployment or publication of restricted artifacts. Phase 1 readiness,
repository integration and Phase 2 authorization are distinct.

The handoff owns the concrete selected artifacts, measured results, feasibility
projection, reproducibility commands and next-session prerequisites; this ADR
does not duplicate their evolving identities.
