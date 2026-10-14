# Project Execution Plan

**Version:** 1<br>
**Status:** Canonical gate/milestone sequence. Live phase and completion status are owned by `.agents/state/PROJECT_STATE.yaml`.<br>
**Scope:** Governance gates, engineering milestones, dependencies, deliverables, and the approved P0/P1/P2 inventory. Live status is owned by `.agents/state/PROJECT_STATE.yaml` and task status by `.agents/tasks/BACKLOG.yaml`.

## 1. Governing rules

- Governance gates (`G0–G5`) control project readiness and review. Engineering milestones (`M0–M7`) describe technical deliverables. They have separate IDs and statuses.
- ADR-0001 owns the accepted G/M crosswalk and resolution history. This plan owns engineering milestone order, dependencies, deliverables, and the fixed-file inventory.
- A future gate or milestone is not authorization to start it. The current user authorization and the `PROJECT_STATE.yaml` gate fields control execution.
- Every milestone must pass the evidence in [`ACCEPTANCE_CRITERIA.md`](../06-quality/ACCEPTANCE_CRITERIA.md). A failed gate stays incomplete or blocked.
- Open assignment, data-use, compute, and evaluation approvals remain in [`REQUIREMENTS.md`](../01-foundation/REQUIREMENTS.md); this plan does not resolve them.

## 2. Governance gate purposes

The accepted mapping from governance gates to engineering milestones is recorded only in [ADR-0001](decisions/ADR-0001-governance-crosswalk-and-file-priorities.md). This table defines gate purpose and exit condition; it does not duplicate the crosswalk.

| Governance gate | Purpose | Exit condition |
|---|---|---|
| G0 — Documentation foundation | Preserve the original roadmap and establish project requirements and agent rules. | User reviews and approves `AGENTS.md`, `ROADMAP.md`, and `REQUIREMENTS.md`. |
| G1 — Persistent agent context and governance | Establish canonical state, tasks, plans, decisions, blockers, findings, handoff, and recovery automation. | P0/P1 bootstrap inventory audited; scripts and recovery checks pass; project state is consistent; user reviews G1. |
| G2 — Technical feasibility | Establish a reproducible local technical baseline and prove the Atari interface is feasible. | Engineering coverage is specified in ADR-0001; each milestone meets its separate acceptance criteria. |
| G3 — Chess foundation and learning | Define the chess simulator, baselines, expert data, supervised pretraining, and simulator RL. | Engineering coverage is specified in ADR-0001; pretraining and RL evidence remain separate. |
| G4 — Atari integration and evaluation | Integrate the learned agent with ALE and measure actual Atari behavior. | Engineering coverage is specified in ADR-0001; closed-loop ALE and comparable evaluation evidence is recorded. |
| G5 — Delivery | Prepare the final report, model card, usage/reproduction guidance, and handover. | Engineering coverage is specified in ADR-0001; artifacts and reports trace to verified runs. |

### Engineering milestone sequence

| Milestone | Depends on | Purpose and deliverable |
|---|---|---|
| M0 — Technical project bootstrap | G1 review and explicit user approval | Audit and establish a reproducible local environment; run low-cost checks; validate Colab CLI workflow without allocating a GPU or launching costly training. |
| M1 — ALE feasibility | M0 | Verify ALE observations, board extraction, cursor/input timing, move execution, opponent response detection, synchronization, reward, and terminal behavior on actual ALE. |
| M2 — Chess foundation | M1 | Specify and test the simulator MDP; establish random and heuristic baselines. |
| M3 — Expert data | M2 | Build a reproducible Stockfish labeling and dataset pipeline with provenance and leakage-safe splits. |
| M4 — Supervised pretraining | M3 | Train and evaluate a standalone pretraining baseline with no Stockfish in inference. |
| M5 — Double DQN and curriculum | M4 | Train in the chess simulator, preserve pre/post-RL checkpoints, and measure whether RL changes performance. |
| M6 — Atari integration | M1 and M4/M5 as applicable | Evaluate closed-loop gameplay using ALE observations and actions; report Atari evidence separately from simulator results. |
| M7 — Evaluation and delivery | M2–M6 | Run the approved comparisons and prepare evidence-backed reports, demo, reproduction steps, and handover. |

M1 feasibility is a prerequisite to substantial M3–M5 work. Atari fine-tuning is optional and only considered after stable M6 integration and throughput evidence. G1 is approved and M0 follows it in the sequence. Canonical state and the latest direct user instructions determine whether M0 may start.

## 3. Canonical information ownership

| Information category | Canonical source | Other files may do |
|---|---|---|
| Project constraints, objectives, external approvals | [`REQUIREMENTS.md`](../01-foundation/REQUIREMENTS.md) | Link to relevant requirement IDs. |
| Original research plan | [`ROADMAP.md`](../01-foundation/ROADMAP.md) | Preserve its source wording; do not copy it into status files. |
| Governance-to-engineering crosswalk and resolution | [ADR-0001](decisions/ADR-0001-governance-crosswalk-and-file-priorities.md) | Link to the decision; do not copy the crosswalk. |
| Engineering sequence, dependencies, and fixed-file inventory | This `EXECUTION_PLAN.md` | Link to sections; do not maintain duplicate inventories elsewhere. |
| Acceptance tests and pass/fail evidence expected | [`ACCEPTANCE_CRITERIA.md`](../06-quality/ACCEPTANCE_CRITERIA.md) | Reference criterion IDs. |
| Current phase, next milestone, last verified Git snapshot | `.agents/state/PROJECT_STATE.yaml` | The handoff points to state; it does not repeat it. |
| Task IDs, dependencies, status, acceptance evidence | `.agents/tasks/BACKLOG.yaml` | Plans and handoff reference task IDs only. |
| Active blockers and their resolution conditions | `.agents/state/BLOCKERS.md` | State/backlog may reference blocker IDs. |
| Verified technical/project findings | `.agents/state/VERIFIED_FINDINGS.md` | Other files cite finding IDs and evidence paths. |
| Approved architecture/process decisions | `docs/02-management/decisions/ADR-*.md` | Plan and state cite ADR IDs. |
| Session resume pointers | `.agents/state/SESSION_HANDOFF.md` | Link to canonical state, backlog, plan, blockers, findings, and ADRs. |
| Actual code and working-tree changes | Git and repository files | State stores only a timestamped snapshot for recovery. |
| Experiment outcomes | Per-run manifests, configs, metrics, logs, and artifacts | Reports cite run IDs and artifact paths; never infer results from plans. |

When a category changes, update its canonical source and then refresh references. Do not keep parallel status tables in the handoff, README, or chat history.

## 4. G1 exit gate

Use criteria `G1-01` through `G1-10` in [`ACCEPTANCE_CRITERIA.md`](../06-quality/ACCEPTANCE_CRITERIA.md) as the single pass/fail source. Task-level progress and evidence are recorded by ID in `.agents/tasks/BACKLOG.yaml`; the current state/handoff is finalized only after those criteria have evidence. G1-10 requires an independent Codex session without prior conversation. G1 closes after explicit user approval; M0 is a separate milestone whose authorization and live status are recorded in canonical state and backlog.

## 5. Approved fixed-file inventory

The counts below are the static target inventory from the latest approved architecture in `chat_history.md`. Dynamic configs, tests, source modules, run directories, experiment manifests, model artifacts, CI files, and additional future ADRs are not included.

The task-specific `.agents/plans/G1-consistency-hardening.md` and `.agents/evidence/G1-hardening-verification.md` are operational records for this audit, not changes to the fixed P0/P1/P2 inventory. No future engineering P2 plan or specification is created by this hardening work.

### P0 — Required before technical implementation (9 files)

| File | G1 disposition |
|---|---|
| `AGENTS.md` | Existing G0 file; updated for G1. |
| `docs/01-foundation/ROADMAP.md` | Existing G0 file; preserved verbatim. |
| `docs/01-foundation/REQUIREMENTS.md` | Existing G0 file; updated for G1 approval and current scope. |
| `docs/02-management/EXECUTION_PLAN.md` | Created in G1. |
| `docs/06-quality/ACCEPTANCE_CRITERIA.md` | Created in G1. |
| `.agents/PLANS.md` | Created in G1. |
| `.agents/state/PROJECT_STATE.yaml` | Created in G1. |
| `.agents/state/SESSION_HANDOFF.md` | Created in G1. |
| `.agents/tasks/BACKLOG.yaml` | Created in G1. |

### P1 — Bootstrap support (10 items)

| File | G1 disposition |
|---|---|
| `README.md` | Audited; preserved unchanged. |
| `docs/01-foundation/PROJECT_OVERVIEW.md` | Created in G1. |
| `docs/02-management/RISK_REGISTER.md` | Created in G1. |
| `docs/05-operations/SETUP.md` | Created as an M0 runbook; no setup executed. |
| `docs/06-quality/TEST_STRATEGY.md` | Created in G1. |
| `.agents/state/BLOCKERS.md` | Created in G1. |
| `.agents/state/VERIFIED_FINDINGS.md` | Created in G1. |
| `.agents/plans/M00-bootstrap.md` | Created as a plan only; M0 not started. |
| `scripts/agent_preflight.py` | Created and tested in G1. |
| `scripts/agent_checkpoint.py` | Created and tested in G1. |

### P2 — Created only when the relevant milestone or decision needs them (38 files)

The inventory is 34 Markdown files and four Python scripts:

- Foundation: `docs/01-foundation/GLOSSARY.md`.
- Decision records: `docs/02-management/decisions/README.md` and `ADR-0001-governance-crosswalk-and-file-priorities.md`. `ADR-0001` is created in G1 because the requested G1 work resolves this governance decision; it is the only P2 artifact created now.
- Technical specifications (7): `ARCHITECTURE.md`, `ALE_ENVIRONMENT.md`, `BOARD_EXTRACTION.md`, `ACTION_ADAPTER.md`, `MDP_SPEC.md`, `MODEL_DESIGN.md`, and `RL_ALGORITHM.md` under `docs/03-technical/`.
- Research specifications (5): `DATASET_SPEC.md`, `STOCKFISH_TEACHER.md`, `TRAINING_PROTOCOL.md`, `EXPERIMENT_PROTOCOL.md`, and `EVALUATION_PROTOCOL.md` under `docs/04-research/`.
- Operations (3): `COLAB_WORKFLOW.md`, `REPRODUCIBILITY.md`, and `TROUBLESHOOTING.md` under `docs/05-operations/`.
- Quality (1): `docs/06-quality/VALIDATION_REPORT.md`.
- Delivery (4): `FINAL_REPORT.md`, `MODEL_CARD.md`, `USER_GUIDE.md`, and `HANDOVER.md` under `docs/07-delivery/`.
- Engineering plans (7): `.agents/plans/M01-ale-feasibility.md` through `.agents/plans/M07-evaluation-delivery.md`.
- Reusable agent skills (4): `.agents/skills/resume-project/SKILL.md`, `checkpoint-progress/SKILL.md`, `validate-milestone/SKILL.md`, and `colab-experiment/SKILL.md`.
- Later recovery/runtime scripts (4): `scripts/recover_experiment.py`, `scripts/smoke_test.py`, `scripts/colab_bootstrap.py`, and `scripts/colab_train.py`.

`M00-bootstrap.md` is P1. `M01–M07` plans are P2 and are created as each milestone approaches. This is the canonical classification; the older chat entry that called all `Mxx` plans P0 is retained as history but superseded by ADR-0001.
