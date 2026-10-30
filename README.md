# Atari VideoChess RL

This repository studies a chess-playing reinforcement-learning agent for ALE **VideoChess-v5**. Independently implemented Double DQN learning from simulator transitions is the central course objective; expert-game behavior and optional Stockfish signals are bounded supporting experiments. The project separates supervised baselines, simulator RL, and actual Atari evaluation.

The current integration branch is **initial-idea**. GitHub currently defaults to **main**, which is an older ancestor. Clone the integration branch explicitly:

    git clone --branch initial-idea https://github.com/dodaonam/atari-videochess-rl.git
    cd atari-videochess-rl

## Implementation maturity

The M5 candidate is under post-review remediation in [PR #11](https://github.com/dodaonam/atari-videochess-rl/pull/11), targeting `initial-idea`. It contains an independent PyTorch Double DQN, semantic legal-UCI action scoring, paired Warm-start/Scratch training, deterministic replay and recovery, and frozen simulator evaluation. Six official 50,000-decision runs and the 1,500-game evaluation have evidence. At candidate `026d41b`, the 368-test local suite passed, the clean-clone suite passed with one expected skip for the private M4 artifact, clean-clone preflight passed, and GitHub CI passed. Training source-version provenance remains unresolved: the old replay/CLI source versions are missing, so the source effect on pooled cross-seed results is not established. The PR is unmerged and not PM-accepted. See the [M5 final report](docs/04-research/M5_FINAL_REPORT.md), [remediation audit](docs/04-research/M5_REMEDIATION_AUDIT.md), and [PR review authority](docs/02-management/PR_REVIEW_AND_INTEGRATION.md). G3 remains unapproved and M6 has not started.

The integrated codebase contains accepted M0–M4 work: a locked Python environment, ALE/VideoChess RGB and control interfaces, observation-driven shadow checks, a history-preserving standard-chess simulator, stable UCI move identities, lightweight baselines, seeded simulator benchmarks, and a provenance-aware PGN dataset pipeline. M3-001 was accepted and merged in PR #3; its release identity and post-merge evidence are recorded under `.agents/evidence/`.

The accepted M3 source, release, and teacher sidecar are outside Git and are not included in a clean clone. The exact release is available at the owner-specified local sibling-worktree path and was independently reverified read-only during Pre-M4 and again by the M4 loader before training; see [the local verification evidence](.agents/evidence/M3-release-local-verification-20261027.md) and [M4 acceptance evidence](.agents/evidence/M4-final-acceptance-20261027.md). M4-001 is merged in PR #8 at integration commit `c0a284304d602817922772d08f0ff7904af7ae20` and passed clean-clone post-merge verification: the ADR-0003 model, feature loader, trainer, engine-free inference adapter, checkpoint tools, CLI, and tests are implemented and verified. The original fixed 128-example gate failed at 126/128 because identical inputs had conflicting labels; that result remains preserved as historical evidence. The dated PM amendment changed only deterministic sanity-sample selection to the first 128 distinct complete effective training inputs in ascending `sample_id` order. The revised gate passed its unchanged thresholds, and the bounded three-seed run completed with validation-only checkpoint selection, one frozen test evaluation, and a 40-game simulator benchmark. The frozen behavior-only checkpoint and run artifacts remain outside Git at the documented local artifact path; they are not Q-values or an RL-trained agent. The curated package license remains unstated, so source and bulk derived data remain local and non-redistributable. No Double DQN trainer or learned Atari policy is implemented, and G3 remains unapproved. See **.agents/state/PROJECT_STATE.yaml** for canonical status, the [M4 final acceptance report](.agents/evidence/M4-final-acceptance-20261027.md) for training/evaluation evidence, and the [post-merge delivery report](.agents/evidence/M4-postmerge-delivery-verification-20261027.md) for integration and clean-clone verification.

## Architecture

- **videochess_rl/environment.py, vision.py, controller.py, shadow.py, episode.py:** ALE environment wrapper, RGB board observations, cursor/input control, shadow transition validation, and bounded episode runner. ALE observations and actual step outcomes remain authoritative.
- **videochess_rl/simulator.py:** python-chess rules and move history, legal UCI actions, agent/opponent transitions, perspective-aware reward, terminal outcomes, and explicit truncation.
- **videochess_rl/baselines.py, benchmark.py:** engine-free random and transparent heuristic agents and bounded simulator-only comparisons.
- **docs/03-technical/MODEL_DESIGN.md**: accepted symbolic model inputs, complete move-history interface, legal candidate scores, and M5 Q-head transfer contract.
- **docs/03-technical/RL_ALGORITHM.md** and `videochess_rl/rl/`: the executable Double DQN, transition, replay, checkpoint, and training contracts implemented for M5.
- **docs/04-research/**: accepted M3 contracts, completed M4 behavior-cloning protocol, the fixed [M5 experiment protocol](docs/04-research/M5_EXPERIMENT_PROTOCOL.md), and [M5 measured results](docs/04-research/M5_FINAL_REPORT.md). `.agents/plans/M03-expert-dataset.md`, `.agents/plans/M04-supervised-pretraining.md`, and `.agents/plans/M05-double-dqn.md` identify the distinct milestone scopes.
- **tests/**: context/recovery, M0, M1 synthetic and real ALE, M2/M3, M4 model/data/training/checkpoint contracts, and M5 learner, replay, recovery, evaluation, provenance, and artifact tests.

Simulator performance is not Atari performance. A python-chess Board may track or cross-check an ALE transition, but it must not replace the emulator observation or conceal desynchronization.

## Local setup

Use Python 3.12 and uv. The committed lockfile pins project dependencies and directs PyTorch to the CPU wheel index.

    uv sync --locked

Stockfish is a separate host prerequisite, not a Python dependency. **docs/05-operations/SETUP.md** records the Stockfish 19 UCI readiness installation and binary/license checks. A readiness ping is not permission to expand engine searches or use Stockfish in inference. The owner authorized only the bounded offline M3 teacher scope; the initial M4 behavior-only run excludes teacher scores and targets. O-01 is closed for internal execution by the 2026-10-27 owner decision; instructor-policy evidence remains unverified and is not represented as formal approval. Broader Stockfish roles under O-07 remain separate.

## Useful commands

Run the full repository suite, including real ALE integration checks:

    uv run --locked python -m unittest discover -s tests -v

Run the accepted M2 simulator, baseline, and benchmark tests:

    uv run --locked python -m unittest tests.test_m2_simulator tests.test_m2_baselines tests.test_m2_benchmark -v

Run agent-context preflight and checkpoint:

    python3 scripts/agent_preflight.py
    python3 scripts/agent_checkpoint.py
    python3 scripts/agent_preflight.py

Run the small recorded simulator benchmark:

    uv run --locked python -m videochess_rl.benchmark --seeds 20261016 20261017 --max-decisions 400 --output artifacts/m2/baseline.json

The M1 demo and terminal experiment write traces and RGB data under ignored artifacts. Run those only when the current task explicitly calls for an ALE runtime check; they are not routine CI jobs.

The M5 training CLI reads the accepted private M4 and M3 artifacts from the original local defaults. To run the transfer/profile/training commands from another authorized checkout, set `VIDEOCHESS_M5_M4_DIR` to the directory containing `pretrained-behavior-only.pt` and its accepted manifest, and `VIDEOCHESS_M5_M3_RELEASE_DIR` to the accepted M3 release directory. The M4 checkpoint SHA and M3 release/manifest identities remain pinned and are verified after path resolution. The private artifacts themselves are not part of this repository or a clean clone.

## Documentation map

- **docs/01-foundation/ROADMAP.md** preserves the original research plan; **REQUIREMENTS.md** owns project constraints, O-01's closed internal decision, and remaining open approvals.
- **docs/02-management/EXECUTION_PLAN.md** owns milestone order and deliverables; **ADR-0001** owns the G/M crosswalk; **ADR-0002** owns the accepted M2 chess contract; **ADR-0003** owns the Accepted M4/M5 model interface.
- **docs/03-technical/** holds the ALE, board extraction, action adapter, architecture, MDP, and accepted model specification.
- **docs/04-research/** contains the accepted M3 data/teacher contracts, completed M4 evidence, and the fixed M5 protocol and final report.
- **docs/05-operations/** contains setup, ALE reproduction, and artifact/recovery rules.
- **docs/06-quality/ACCEPTANCE_CRITERIA.md** owns pass conditions; **TEST_STRATEGY.md** describes test layers.
- **.agents/state/PROJECT_STATE.yaml**, **.agents/tasks/BACKLOG.yaml**, **BLOCKERS.md**, **VERIFIED_FINDINGS.md**, and **SESSION_HANDOFF.md** are the canonical live context records. Run preflight before selecting work.

## Evidence and data handling

For experiments, record the source revision, config and dataset hashes, command, seeds, runtime/library/ALE/ROM/engine versions, hardware, raw metrics, checkpoint hash, and artifact location. Keep large source data, generated datasets, and model checkpoints outside ordinary Git history under an approved persistent artifact location. The agent preflight does not hash ignored artifact directories; verify their SHA-256 manifests separately.

No top-level repository LICENSE is present. Do not assume that project code or third-party datasets are licensed for redistribution. M3's exact curated Elite package was owner-authorized for local/internal academic processing; its own package license remains unstated, and the source and bulk derived records must not be uploaded or redistributed. The upstream official Lichess database terms do not establish the curated package's separate license. Do not replace the accepted release or acquire new data without the applicable owner decision.

## Known limitations

- The M3 source/release artifacts are not in Git or a clean checkout. M4 reverified and tensorized the exact accepted release with all nine file identities unchanged; the third-party package remains local and non-redistributable.
- M4-01 through M4-04 are accepted with evidence in the final M4 report. The original fixed gate failure and the dated PM amendment are preserved. M5's learned policies are evaluated only in the M2 chess simulator; they are not Atari ALE results. M5 PR #11 awaits independent review; G3 remains unapproved and M6 has not started.
- O-01 is closed for internal execution; independent instructor-policy evidence remains unverified and informational. O-02–O-08 retain their scoped open status; see **docs/01-foundation/REQUIREMENTS.md**.
- ALE special-move parity, all game modes, and official evaluation settings remain unverified beyond the recorded M1 evidence.
- The default branch **main** is behind **initial-idea**; repository settings have not been changed.
- Simulator results do not establish Atari gameplay, and no learned Atari performance or Elo claim is currently established.
