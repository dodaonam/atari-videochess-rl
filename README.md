# Atari VideoChess RL

This repository studies a chess-playing reinforcement-learning agent for ALE **VideoChess-v5**. The research direction separates expert-game behavior, optional Stockfish teacher signals, learning in a python-chess simulator, and actual Atari evaluation.

The current integration branch is **initial-idea**. GitHub currently defaults to **main**, which is an older ancestor. Clone the integration branch explicitly:

    git clone --branch initial-idea https://github.com/dodaonam/atari-videochess-rl.git
    cd atari-videochess-rl

## Implementation maturity

The integrated codebase contains the accepted M0–M2 foundation: a locked Python environment, ALE/VideoChess RGB and control interfaces, observation-driven shadow checks, a history-preserving standard-chess simulator, stable UCI move identities, lightweight baselines, and seeded simulator benchmarks.

The project does not yet contain a production PGN dataset pipeline, supervised model, Double DQN trainer, or learned-agent Atari policy. M3 research and schema contracts are prepared, but M3 source acquisition and implementation require separate owner approval. See **.agents/state/PROJECT_STATE.yaml** for current gate, task, and authorization status.

## Architecture

- **videochess_rl/environment.py, vision.py, controller.py, shadow.py, episode.py:** ALE environment wrapper, RGB board observations, cursor/input control, shadow transition validation, and bounded episode runner. ALE observations and actual step outcomes remain authoritative.
- **videochess_rl/simulator.py:** python-chess rules and move history, legal UCI actions, agent/opponent transitions, perspective-aware reward, terminal outcomes, and explicit truncation.
- **videochess_rl/baselines.py, benchmark.py:** engine-free random and transparent heuristic agents and bounded simulator-only comparisons.
- **docs/04-research/**: proposed M3 dataset, Stockfish teacher, experiment, and owner decision contracts.
- **tests/**: context/recovery, M0, M1 synthetic and real ALE, M2 simulator, baseline, and benchmark checks.

Simulator performance is not Atari performance. A python-chess Board may track or cross-check an ALE transition, but it must not replace the emulator observation or conceal desynchronization.

## Local setup

Use Python 3.12 and uv. The committed lockfile pins project dependencies and directs PyTorch to the CPU wheel index.

    uv sync --locked

Stockfish is a separate host prerequisite, not a Python dependency. **docs/05-operations/SETUP.md** records the Stockfish 19 UCI readiness installation and binary/license checks. A readiness ping is not permission to search positions, label data, play as an opponent, evaluate offline, or include Stockfish in inference. O-01/O-07 remain separate approvals.

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

- **docs/01-foundation/ROADMAP.md** preserves the original research plan; **REQUIREMENTS.md** owns project constraints and open approvals.
- **docs/02-management/EXECUTION_PLAN.md** owns milestone order and deliverables; **docs/02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md** owns the governance crosswalk; **ADR-0002** owns the accepted M2 chess contract.
- **docs/03-technical/** holds the ALE, board extraction, action adapter, architecture, and MDP specifications.
- **docs/04-research/** contains the proposed M3 data/teacher/experiment contracts and owner decisions.
- **docs/05-operations/** contains setup, ALE reproduction, and artifact/recovery rules.
- **docs/06-quality/ACCEPTANCE_CRITERIA.md** owns pass conditions; **TEST_STRATEGY.md** describes test layers.
- **.agents/state/PROJECT_STATE.yaml**, **.agents/tasks/BACKLOG.yaml**, **BLOCKERS.md**, **VERIFIED_FINDINGS.md**, and **SESSION_HANDOFF.md** are the canonical live context records. Run preflight before selecting work.

## Evidence and data handling

For experiments, record the source revision, config and dataset hashes, command, seeds, runtime/library/ALE/ROM/engine versions, hardware, raw metrics, checkpoint hash, and artifact location. Keep large source data, generated datasets, and model checkpoints outside ordinary Git history under an approved persistent artifact location. The agent preflight does not hash ignored artifact directories; verify their SHA-256 manifests separately.

No top-level repository LICENSE is present. Do not assume that project code or third-party datasets are licensed for redistribution. The proposed Elite PGN package has no license statement on its listing; its use remains an owner decision. The official Lichess database exports publish CC0 terms, while official broadcast PGNs publish CC BY-SA 4.0; these are distinct sources and licenses. Do not download the full dataset until O-06 is resolved.

## Known limitations

- M3 data acquisition, parsing, supervised training, and Stockfish labeling are not implemented.
- O-01 through O-08 remain open; see **docs/01-foundation/REQUIREMENTS.md**.
- ALE special-move parity, all game modes, and official evaluation settings remain unverified beyond the recorded M1 evidence.
- The default branch **main** is behind **initial-idea**; repository settings have not been changed.
- Simulator results do not establish Atari gameplay, and no learned Atari performance or Elo claim is currently established.
