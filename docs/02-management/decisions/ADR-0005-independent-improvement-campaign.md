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

The coverage audit found that the protected global bottom-k core selected 5,000
games but retained position records for only 4,994. To satisfy actual parent-game
coverage, preserve that core and complete missing parents using one lowest-ranked
leakage-safe candidate from their original per-game reservoirs. Keep existing
retained split ownership, historical holdout protection, the 32-record per-game
cap and the 100,000-record final cap. The six additions restore four previously
purged train records whose competing holdout exposure was removed, and add two
reservoir records beyond the original global cutoff. All 5,000 games are then
represented; the final release has 94,805 records. This is an explicit deterministic
coverage rule, not synthetic data or a relaxation of disjointness.

The eight-trial HPO campaign had already finished before this audit. Its fixed
8,192 training and 8,964 validation inputs are an unchanged projection of the
coverage-completed release, verified by sample identities, complete histories,
FENs, legal actions, labels and splits. Retain that measured study and its original
release provenance; do not relabel it as a rerun on the full 8,965-position final
validation partition or spend additional HPO trials. Official M4 training and
selection use the completed release and its full validation partition. The
interrupted labeling attempt is preserved and does not count as a completed
expert dataset. No official M4 epoch had started when it was stopped.
