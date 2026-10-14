# Acceptance Criteria

**Status:** Canonical gate criteria. Current pass/fail status lives in `.agents/state/PROJECT_STATE.yaml` and `.agents/tasks/BACKLOG.yaml`.<br>
**Authority:** Project constraints are in [`REQUIREMENTS.md`](../01-foundation/REQUIREMENTS.md); [`ADR-0001`](../02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md) owns the G/M crosswalk; [`EXECUTION_PLAN.md`](../02-management/EXECUTION_PLAN.md) owns milestone order and dependencies.

## Gate rules

- A criterion passes only when its evidence exists and can be inspected or rerun.
- Record criterion IDs at task level and link them to an evidence set. Each evidence item records a result/detail and provenance. Verified commands/tests require the actual UTC execution timestamp, result, exit code, Git revision, and repository-relative sanitized log path. Verified file reviews record when they were checked and the Git revision. Historical claims with missing original timestamps/logs remain explicitly `historical_unverified`; never invent provenance or overwrite the report as if it had been rerun.
- `not run`, `blocked`, and `failed` are distinct from `passed`.
- A later gate cannot waive a failed prerequisite. A fallback demo is not evidence that an ALE requirement passed.
- G gates and M milestones have separate status. The crosswalk does not make their criteria interchangeable.

## G0 — Documentation Foundation Bootstrap

| ID | Pass condition | Evidence |
|---|---|---|
| G0-01 | `ROADMAP.md` is byte-for-byte equal to the embedded original Markdown in the source HTML and preserves all 19 numbered sections. | Exact source comparison and content hash. |
| G0-02 | `REQUIREMENTS.md` distinguishes source-stated baseline, proposed designs, and open confirmations without resolving open items silently. | Document review against the roadmap and chat history. |
| G0-03 | `AGENTS.md` sets source hierarchy, boundaries, evidence, and user approval gates. | Document review. |
| G0-04 | User reviews and approves all three documents. | Direct user approval. |

G0-04 was approved by the user before G1 was authorized. G0 is historical and is not re-evaluated by later technical milestones.

## G1 — Persistent Agent Context and Governance Bootstrap

| ID | Pass condition | Evidence |
|---|---|---|
| G1-01 | The P0/P1 inventory matches the canonical counts and classification in `EXECUTION_PLAN.md`; existing README is audited and preserved. | File inventory, Git status, README hash. |
| G1-02 | The G/M crosswalk and the P0/P1/P2 plan classification have one recorded decision. | `ADR-0001` and execution plan cross-reference. |
| G1-03 | Project state and backlog parse against their documented schemas; IDs are unique, dependencies resolve and are acyclic, and completed tasks cite existing evidence. | `python3 scripts/agent_preflight.py`; unit tests. |
| G1-04 | Local Markdown links in governed documentation resolve. External URLs are not fetched by preflight. | `agent_preflight.py` link report and broken-link tests. |
| G1-05 | Blocked tasks reference active blocker IDs; active blocker IDs correspond to canonical blocker records; open requirement approvals are reported from `REQUIREMENTS.md`. | Preflight consistency report and tests. |
| G1-06 | A stale handoff pointer is detected and can be refreshed from canonical state; partial writes are reported/recoverable; `--dry-run --recover-partials` makes no filesystem changes; one checkpoint invocation produces an immediately consistent snapshot. | Recovery tests using temporary committed and dirty fixture repositories, including a filesystem-metadata comparison around dry-run. |
| G1-07 | The checkpoint records workspace-local Git/file observations separately from a portable tracked-file manifest and semantic-state/handoff checksums. A clean clone accepts a verified commit transition without local-only files or caches, while tracked edits and integrity problems remain detectable. | State snapshot, clean-clone commit regression, legacy migration coverage, cache and tracked-drift tests, and JSON preflight inventory. |
| G1-08 | A fresh Python process recovers the project objective, current gate, next milestone/task, task statuses, blockers, unresolved approvals, last verified Git state, exact next action, and acceptance path using only repository files and scripts. | Recovery subprocess test and checklist below. This does not claim an independent Codex session was tested. |
| G1-09 | After G1-10 is complete, G1 is marked ready for user review; M0 and M1 remain not started and unauthorized until explicit user approval. | `PROJECT_STATE.yaml`, `BACKLOG.yaml`, and the verified manual recovery record. |
| G1-10 | A new Codex session with no access to the prior conversation can recover the project, identify the current task and exact next action, and correctly keep M0/M1 unauthorized. | Sanitized manual recovery record with timestamp and Git revision; do not store a conversation transcript. |

### Fresh-session recovery checklist

A fresh agent with no conversation history must be able to:

1. Read `AGENTS.md` and `REQUIREMENTS.md` to identify project purpose, constraints, and unresolved approvals.
2. Run `python3 scripts/agent_preflight.py` to inspect schemas, links, dependencies, blockers, handoff pointer, Git drift, and current task summary.
3. Follow the handoff links to the canonical state, backlog, execution plan, acceptance criteria, ADRs, blocker records, and verified findings.
4. Identify the next action from `PROJECT_STATE.yaml` and its referenced backlog task; do not infer it from the handoff prose.
5. Verify the reported Git snapshot against the live worktree. If it differs, review the diff and do not silently replace user state.
6. See that M0 is not started and requires G1 review approval, and that M1 remains gated on M0 and its own acceptance evidence.

For G1-10, repeat this checklist in a new Codex session with no transcript or prior-turn summary. A Python subprocess test only covers G1-08. Keep G1-10 pending until the independent session result is recorded.

## M0 — Technical project bootstrap

| ID | Pass condition | Evidence |
|---|---|---|
| M0-01 | Current local Python/tooling/repository state is audited before installation. | Sanitized preflight record. |
| M0-02 | Dependencies and project commands are reproducible and documented; no system-wide changes are made without authorization. | Lock/config files and local smoke checks. |
| M0-03 | Colab CLI availability/workflow is checked without allocating GPU or starting expensive training. | CLI/version/capability evidence; no runtime allocation. |
| M0-04 | Setup gaps and external approvals are recorded; M0 is not reported as passing when any required smoke check fails. | Updated state, task evidence, blocker record if needed. |

## M1 — ALE feasibility

| ID | Pass condition | Evidence |
|---|---|---|
| M1-01 | Reset ALE and capture RGB/RAM observations; actual shapes and action space are recorded. | Reproducible local runtime log and sanitized observation artifacts. |
| M1-02 | Cursor movement, piece selection, FIRE timing, and input repetition are calibrated. | Repeatable control checks. |
| M1-03 | The agent executes a controlled legal move such as `e2e4`, detects the Atari reply, and extracts/cross-checks the resulting board. | Closed-loop trace and state comparison. |
| M1-04 | Reward perspective, terminal behavior, turn detection, and relevant game modes are verified against runtime evidence. | Controlled outcome checks and environment notes. |
| M1-05 | Desynchronization is detected and stops or recovers the episode; no unverified state is used as training data. | Negative-path integration checks. |
| M1-06 | Findings, limitations, and local ALE configuration are documented. | Verified findings and acceptance report. |

No model training is required for M1. M1 must pass before substantial M3–M5 work.

## M2 — Chess foundation

- **M2-01:** State, legal actions, transition boundaries, player perspective, reward, terminal, and truncation are explicitly specified.
- **M2-02:** Rule and transition tests cover special moves and game-ending conditions supported by the selected simulator.
- **M2-03:** Random-legal and heuristic agents complete simulator games; tournament metrics are saved with seeds/opponent identities.
- **M2-04:** Simulator results and ALE integration metrics remain separate.

## M3 — Expert dataset

- **M3-01:** Source data and licenses are documented before ingestion.
- **M3-02:** Stockfish version, search settings, score perspective, score normalization, and mate-score handling are recorded.
- **M3-03:** Dataset generation is reproducible and each sample has provenance.
- **M3-04:** Train/validation/test splits prevent leakage between related positions/candidates; dataset statistics and hashes are recorded.

## M4 — Supervised pretraining

- **M4-01:** Encoder/model shape, legal-action candidate handling, finite outputs, gradients, and checkpoint round-trip are tested.
- **M4-02:** A small-sample overfit/sanity check passes before expanding training.
- **M4-03:** The pretraining-only checkpoint is preserved and evaluated with Stockfish absent from the inference path.
- **M4-04:** Validation, ranking/gameplay metrics, configs, seeds, and artifacts are recorded; no illustrative value is reported as measured.

## M5 — Double DQN and curriculum

- **M5-01:** Double DQN action selection and target evaluation are independently tested, including terminal/truncation and legal next actions.
- **M5-02:** Reward/player perspective and teacher-score-to-Q initialization assumptions are documented and checked.
- **M5-03:** Replay, target network, exploration, checkpoint/resume, and opponent identity are recorded and tested.
- **M5-04:** Pretraining-only and RL checkpoints are evaluated under the same approved benchmark conditions; report whether RL improves or regresses performance.
- **M5-05:** Curriculum/reward shaping/auxiliary losses are separately configured experiments, not silently combined.

## M6 — Atari integration

- **M6-01:** Inference uses real ALE-derived observations; a `python-chess` shadow board may only track/cross-check state.
- **M6-02:** Every decision follows observe → validate → decide → execute → verify, with desynchronization detection.
- **M6-03:** No Stockfish process participates in inference.
- **M6-04:** Complete-game W/D/L, move success, desynchronization, runtime settings, and replayable traces are retained.
- **M6-05:** Debug settings are not reported as default ALE evaluation; the verified evaluation configuration is recorded.

## M7 — Evaluation and delivery

M7 remains one engineering milestone, with its acceptance evidence split across governance gates: G4 owns the evaluation criteria M7-01–M7-03; G5 owns the delivery criteria M7-04–M7-05. G4 cannot be closed by delivery evidence, and G5 cannot be closed by evaluation metrics alone.

- **M7-01:** Baselines, pretraining, RL, and Atari evaluation are compared on identified environments and approved opponent pools.
- **M7-02:** Seeds, colors, compute limits, uncertainty, raw metrics, and deviations are reported.
- **M7-03:** Elo is reported only relative to a defined/calibrated pool and stated conditions; 1500 Elo is not assumed.
- **M7-04:** Report, model card, usage guide, and handover reference actual checkpoints, run IDs, artifact hashes, limitations, and reproduction steps.
- **M7-05:** Release or publication occurs only after explicit user authorization.
