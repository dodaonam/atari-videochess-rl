# Atari VideoChess RL

**PROJECT CLOSED WITH DOCUMENTED LIMITATIONS.** M0–M7 engineering is complete; G0–G5 are approved within their recorded scopes. The Project Owner accepts the recorded research results as final. This is completed research with documented limitations, without demonstrated strong chess-playing performance or external academic certification.

This project studies a chess-playing agent for ALE **VideoChess-v5**. It implements Double DQN directly in PyTorch and separates three evidence tracks: supervised behavior cloning, reinforcement learning in a `python-chess` simulator, and genuine Atari evaluation driven by ALE observations. Stockfish supplied only bounded offline M3 teacher evidence and is absent from inference.

## What was implemented

| Milestone | Completed work |
|---|---|
| M0 | Locked Python environment and environment/tool verification. |
| M1 | Genuine ALE feasibility: RGB board observations, cursor/input control, observation-checked transitions, and terminal evidence. |
| M2 | History-preserving chess simulator, legal UCI actions, perspective-aware rewards, baselines, and simulator benchmarks. |
| M3 | Provenance-aware PGN pipeline, leakage-safe splits, accepted final r6/r7 dataset identity, and bounded Stockfish teacher evidence. |
| M4 | Action-conditioned supervised behavior model, training/checkpoint tools, and engine-free inference. This is behavior cloning, not RL. |
| M5 | Custom Double DQN, replay, target networks, training/checkpoint recovery, and six-run/1,500-game simulator evaluation. |
| M6 | Frozen learned-policy integration with ALE RGB/control; separate immutable v1/v2 integration records. |
| M7 | Frozen Option B comparative ALE evaluation, analysis, scientific delivery, release disposition, and governance closeout. |

## Results and limitations

The final M7 campaign scheduled and started **90 reset-observed attempts**: **60 genuine terminal White losses, 30 incomplete attempts, zero observed wins, and zero observed draws**. Incomplete attempts remain incomplete; they are not completed games or losses. Only **9/30 Warm/Scratch matched cells** had both terminal outcomes, so no valid paired confidence interval was available for the principal comparison.

No calibrated Elo, RL superiority, Warm-start superiority, equivalence, or broad generalization was established. Evaluation used White only, one built-in ALE opponent, and an extended horizon. M4 imitation accuracy and M5 simulator scores are separate measurements and must not be presented as Atari strength. RSK-014 preserves incomplete historical M5 CLI provenance; PM6-F06 preserves the M6 v2 metadata erratum.

Read the [final report](docs/07-delivery/FINAL_REPORT.md), [model card](docs/07-delivery/MODEL_CARD.md), [historical M5 simulator report](docs/04-research/M5_FINAL_REPORT.md), and [frozen M7 analysis](.agents/evidence/M7-analysis-final-r2-20261101/M7_ANALYSIS.md). The [final project closure matrix](.agents/evidence/M0-M7-final-project-closure-20261101.md) and [final G5 PM decision](.agents/evidence/G5-PM-final-decision-20261101.md) record acceptance and qualifications. G5-F01 and G5-F02 are resolved. Open external questions O-02–O-08 remain documented in [requirements](docs/01-foundation/REQUIREMENTS.md).

## Source and integration provenance

The accepted completed project baseline is `initial-idea` commit `0ceab36c6dcdcbde169d578657d851c0106cf518`, tree `1a42dfffc92ce88954e9db248ef4ec38db5f6dcc` (PR #22). This consolidation proposes its complete history plus documentation corrections for integration into `main`; it does not assert that integration has occurred. Use the accepted immutable revision to inspect the completed baseline before or after a future merge:

```bash
git clone https://github.com/dodaonam/atari-videochess-rl.git
cd atari-videochess-rl
git checkout 0ceab36c6dcdcbde169d578657d851c0106cf518
```

To inspect consolidation corrections, select the final PR head identified in its handover. The [consolidation audit](.agents/evidence/FINAL-CONSOLIDATION-audit-20261102.md) distinguishes those corrections from the existing project history. PR #22 used a disclosed one-time owner instruction for PM-operated governance integration; it had no independent GitHub review submission. That exception supplies no merge authority for this consolidation PR.

## Setup and safe verification

Use Python 3.12. The committed `uv.lock` pins dependencies and selects CPU PyTorch. For a new environment, `uv sync --locked` installs dependencies; the consolidation used the already-existing environment without installing anything. See [setup](docs/05-operations/SETUP.md) and the [user guide](docs/07-delivery/USER_GUIDE.md).

Repository-only checks need no private artifacts:

```bash
python3 scripts/agent_preflight.py
python3 -B -m unittest tests.test_agent_context tests.test_g5_final_closeout tests.test_m7_delivery_docs tests.test_m7_release_disposition tests.test_pre_m7_contracts tests.test_final_consolidation -v
```

With the existing project dependencies, the unfiltered suite is:

```bash
python -B -m unittest discover -s tests -v
```

The full suite includes bounded real ALE integration tests and a Stockfish UCI readiness ping without search. It is separate from historical campaign reproduction. Private-artifact tests can skip when their prerequisites are absent; report executed, passed, failed, and skipped counts separately. The historical PR #21 C2 result was **524 executed: 521 passed, 3 skipped, 0 failures**; see the [count erratum](.agents/evidence/FINAL-CONSOLIDATION-test-count-erratum-20261102.md). GitHub's bounded preflight workflow is not the full Python suite.

`agent_checkpoint.py` writes context/checkpoint metadata. Training CLIs, `benchmark`, `run_m1_terminal_experiment.py`, and the M6/M7 campaign scripts are historical experiment runners, not setup or routine verification commands. No new training, fine-tuning, evaluation campaign, Stockfish search, or automatic future experiment is authorized.

## Code and documentation

- [videochess_rl](videochess_rl/__init__.py): separate ALE environment/vision/controller/shadow interfaces, simulator, data, model, RL, and M6/M7 integration modules. ALE observations remain authoritative; a shadow board only validates history/transitions.
- [Technical architecture](docs/03-technical/ARCHITECTURE.md), [model design](docs/03-technical/MODEL_DESIGN.md), and [RL algorithm](docs/03-technical/RL_ALGORITHM.md) explain the implemented contracts.
- [Acceptance criteria](docs/06-quality/ACCEPTANCE_CRITERIA.md), [test strategy](docs/06-quality/TEST_STRATEGY.md), and [delivery regression tests](tests/test_m7_delivery_docs.py) describe verification.
- [Delivery handover](docs/07-delivery/HANDOVER.md) maps reports, evidence, risks, and artifact identities.
- [PROJECT_STATE.yaml](.agents/state/PROJECT_STATE.yaml) and [BACKLOG.yaml](.agents/tasks/BACKLOG.yaml) own live status and task evidence. The [roadmap](docs/01-foundation/ROADMAP.md) preserves the original research plan rather than current status.

## Artifacts, rights, and release boundary

ROMs, M3 datasets/teacher payloads, M4/M5 model weights and checkpoints, and M6/M7 raw frames/traces remain outside Git. Their committed manifests and hashes identify private payloads; a clone does not provide those payloads or byte-identical historical campaign reproduction.

One existing historical M1 controller-diagnostic archive, `.agents/evidence/BLK-001-diagnostic-20261015-r2.zip`, contains diagnostic RGB frames/traces. The Project Owner explicitly authorized preserving this exact unchanged archive and its existing history for this consolidation (CONSOLIDATION-01). This exception grants no third-party rights and authorizes no additional artifact, separate package, release, or deployment. See the [audit disposition](.agents/evidence/FINAL-CONSOLIDATION-audit-20261102.md).

No top-level project LICENSE is present; the curated M3 package license remains unstated/unverified. G5 approval grants no distribution rights. Affirmative authorization to distribute restricted artifacts is not established; an attributed blanket owner prohibition was not independently verified. See the corrected [release disposition](docs/07-delivery/RELEASE_DISPOSITION.md) and [G5-F02 erratum](.agents/evidence/G5-F02-provenance-erratum-20261101.md).
