# Atari VideoChess RL

This repository studies a chess-playing reinforcement-learning agent for ALE **VideoChess-v5**. Independently implemented Double DQN learning from simulator transitions is the central course objective; expert-game behavior and optional Stockfish signals are bounded supporting experiments. The project separates supervised baselines, simulator RL, and actual Atari evaluation.

The current integration branch is **initial-idea**. GitHub currently defaults to **main**, which is an older ancestor. Clone the integration branch explicitly:

    git clone --branch initial-idea https://github.com/dodaonam/atari-videochess-rl.git
    cd atari-videochess-rl

## Implementation maturity

The integrated codebase contains accepted M0–M3 work: a locked Python environment, ALE/VideoChess RGB and control interfaces, observation-driven shadow checks, a history-preserving standard-chess simulator, stable UCI move identities, lightweight baselines, seeded simulator benchmarks, and a provenance-aware PGN dataset pipeline. M3-001 was accepted and merged in PR #3; its release identity and post-merge evidence are recorded under `.agents/evidence/`.

The accepted M3 source, release, and teacher sidecar are outside Git and are not included in a clean clone. The exact release is available at the owner-specified local sibling-worktree path and was independently reverified read-only during Pre-M4; see [the local verification evidence](.agents/evidence/M3-release-local-verification-20261027.md) and [final Pre-M4 readiness report](.agents/evidence/PRE-M4-final-closure-20261027.md). M4-001 began under direct owner authorization and is now blocked by BLK-002. The ADR-0003 model, feature loader, trainer, engine-free inference adapter, checkpoint tools, CLI, and focused tests are implemented on the M4 feature branch. The M4 loader reverified and tensorized the exact release, then the fixed 128-example gate failed at 126/128 legal top-1 after 500 updates; a read-only diagnosis proved two pairs of identical inputs have conflicting targets, making the required 127/128 unreachable under the accepted input contract. M4-01 source tests pass; M4-02 failed; full training, checkpoint acceptance, and M4-03/M4-04 evaluation were not started. See [the blocker evidence](.agents/evidence/M4-02-sanity-gate-blocker-20261027.md). The curated package license remains unstated, so the source and bulk derived data remain local and non-redistributable. No Double DQN trainer or learned Atari policy is implemented, and G3 remains unapproved. See **.agents/state/PROJECT_STATE.yaml** for canonical status.

## Architecture

- **videochess_rl/environment.py, vision.py, controller.py, shadow.py, episode.py:** ALE environment wrapper, RGB board observations, cursor/input control, shadow transition validation, and bounded episode runner. ALE observations and actual step outcomes remain authoritative.
- **videochess_rl/simulator.py:** python-chess rules and move history, legal UCI actions, agent/opponent transitions, perspective-aware reward, terminal outcomes, and explicit truncation.
- **videochess_rl/baselines.py, benchmark.py:** engine-free random and transparent heuristic agents and bounded simulator-only comparisons.
- **docs/03-technical/MODEL_DESIGN.md**: accepted symbolic model inputs, complete move-history interface, legal candidate scores, and M5 Q-head transfer contract.
- **docs/04-research/**: accepted M3 dataset contracts, RL-first Double DQN alignment, and the bounded M4 training protocol. `.agents/plans/M03-expert-dataset.md` records completed M3 work; `.agents/plans/M04-supervised-pretraining.md` records the blocked M4-001 implementation and evidence path.
- **tests/**: context/recovery, M0, M1 synthetic and real ALE, M2/M3, Pre-M4 semantic contracts, and M4 model/data/training/checkpoint contracts.

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

## Documentation map

- **docs/01-foundation/ROADMAP.md** preserves the original research plan; **REQUIREMENTS.md** owns project constraints, O-01's closed internal decision, and remaining open approvals.
- **docs/02-management/EXECUTION_PLAN.md** owns milestone order and deliverables; **ADR-0001** owns the G/M crosswalk; **ADR-0002** owns the accepted M2 chess contract; **ADR-0003** owns the Accepted M4/M5 model interface.
- **docs/03-technical/** holds the ALE, board extraction, action adapter, architecture, MDP, and accepted model specification.
- **docs/04-research/** contains the accepted M3 data/teacher contracts, ready M4 training protocol, experiment guidance, and owner decisions.
- **docs/05-operations/** contains setup, ALE reproduction, and artifact/recovery rules.
- **docs/06-quality/ACCEPTANCE_CRITERIA.md** owns pass conditions; **TEST_STRATEGY.md** describes test layers.
- **.agents/state/PROJECT_STATE.yaml**, **.agents/tasks/BACKLOG.yaml**, **BLOCKERS.md**, **VERIFIED_FINDINGS.md**, and **SESSION_HANDOFF.md** are the canonical live context records. Run preflight before selecting work.

## Evidence and data handling

For experiments, record the source revision, config and dataset hashes, command, seeds, runtime/library/ALE/ROM/engine versions, hardware, raw metrics, checkpoint hash, and artifact location. Keep large source data, generated datasets, and model checkpoints outside ordinary Git history under an approved persistent artifact location. The agent preflight does not hash ignored artifact directories; verify their SHA-256 manifests separately.

No top-level repository LICENSE is present. Do not assume that project code or third-party datasets are licensed for redistribution. M3's exact curated Elite package was owner-authorized for local/internal academic processing; its own package license remains unstated, and the source and bulk derived records must not be uploaded or redistributed. The upstream official Lichess database terms do not establish the curated package's separate license. Do not replace the accepted release or acquire new data without the applicable owner decision.

## Known limitations

- The M3 source/release artifacts are not in Git or a clean checkout. The M4 CLI reverified and tensorized the exact release on the feature branch, with unchanged file hashes; see the M4 gate diagnostic. The third-party package remains local and non-redistributable.
- M4-001 is blocked by BLK-002. M4-01 source/contract checks pass; the fixed gate failed at its mathematically verified 126/128 ceiling. Full training, checkpoint acceptance, frozen evaluation, and M4-03/M4-04 were not run. No Double DQN trainer or learned Atari policy exists, and G3 remains unapproved.
- O-01 is closed for internal execution; independent instructor-policy evidence remains unverified and informational. O-02–O-08 retain their scoped open status; see **docs/01-foundation/REQUIREMENTS.md**.
- ALE special-move parity, all game modes, and official evaluation settings remain unverified beyond the recorded M1 evidence.
- The default branch **main** is behind **initial-idea**; repository settings have not been changed.
- Simulator results do not establish Atari gameplay, and no learned Atari performance or Elo claim is currently established.
