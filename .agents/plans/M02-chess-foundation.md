# M02 — Chess Foundation Plan

- **Plan ID:** M02
- **Milestone:** M2 — Chess foundation, associated with G3
- **Plan status:** draft; prepared for review, not active
- **Task:** M2-001 in [BACKLOG.yaml](../tasks/BACKLOG.yaml), pending separate explicit user authorization
- **Dependencies:** M1-001 complete; G2 approved
- **Requirements:** B-03, B-05, B-06, B-07, B-08; unresolved approvals O-01, O-06, O-07, O-08 in [REQUIREMENTS.md](../../docs/01-foundation/REQUIREMENTS.md)
- **Acceptance:** M2-01 through M2-04 in [ACCEPTANCE_CRITERIA.md](../../docs/06-quality/ACCEPTANCE_CRITERIA.md)
- **Specifications:** [ARCHITECTURE.md](../../docs/03-technical/ARCHITECTURE.md), [MDP_SPEC.md](../../docs/03-technical/MDP_SPEC.md), proposed [ADR-0002](../../docs/02-management/decisions/ADR-0002-chess-mdp-action-and-perspective.md)

## Objective

When M2 is separately authorized, implement and verify a small standard-chess simulator using the locked `python-chess` dependency. Establish stable legal-move identity, the agreed agent/opponent transition, agent-perspective terminal rewards, automatic chess outcomes, and explicit truncation. Add two lightweight baselines and a small seeded benchmark. This plan is preparation only; no M2 implementation or acceptance test has been run.

## Scope

1. **Correct simulator:** One `python-chess.Board` owns rules and move history. A step applies one legal agent move and, if still live, one legal opponent reply. Record reward, terminal/truncation flags, outcome reason, and final state.
2. **Legal moves and focused tests:** Actions are exclusively legal `python-chess.Move` values, serialized with stable UCI keys. Cover ordinary moves, captures, castling, en passant, promotions, automatic endings, invalid-action safety, and simulator truncation.
3. **Two lightweight baselines:** A seeded random-legal selector and a transparent heuristic that may prioritize immediate mate, captures, and basic material. Keep any evaluation bounded and simple. No Stockfish, search engine, MCTS, deep alpha-beta, opening book, or tablebase.
4. **Reproducible benchmark:** Run a small seeded set of games between identified baselines, vary agent color, and retain per-game outcomes and settings. Report W/D/L, episode lengths, completed games, truncations, policy/opponent identities, seeds, and Git revision. Do not claim calibrated Elo.

The active action scope permanently excludes voluntary draw claims and other non-move player actions. Automatic game-ending outcomes remain supported through `python-chess`.

## Exclusions

- This plan does not authorize implementation; await separate explicit M2 authorization.
- No M3 PGN download/ingestion, dataset construction, or Stockfish labeling/search.
- No M4 model or supervised training; no M5 Double DQN, replay buffer, or training code.
- No new ALE gameplay or changes to M1 controller/vision/shadow code. Simulator metrics are not Atari results.
- No Colab, GPU, paid compute, external service, or resolution of O-01 through O-08.
- No neural tensor shape, network architecture, fixed output head, action scorer, numeric discount, reward shaping, training schedule, Elo claim, or opponent pool is required or frozen by M2.

## Proposed implementation boundaries

Keep additions small under the existing package; these are proposed future files, not existing modules:

| Proposed module | Future responsibility | Boundary |
|---|---|---|
| `videochess_rl/simulator.py` | Reset, Board/history ownership, legal agent move, opponent reply, reward and terminal/truncation result. | Uses `python-chess`; no ALE, RGB, or joystick timing. |
| `videochess_rl/baselines.py` | Seeded random-legal and simple heuristic move selectors. | Returns only a move from the supplied current legal set; no engine dependency. |
| `videochess_rl/benchmark.py` | Small seeded baseline games and per-game/aggregate simulator records. | Identifies policy, opponent, color, seed, result, length, truncation, settings, and revision. |
| `tests/test_m2_*.py` | Focused rule, transition, baseline, seeded-game, and metric-separation tests. | Adds coverage without replacing M0/M1 tests. |

Stable UCI conversion can remain at the simulator boundary; a separate action-encoder module is not needed for M2. Reuse python-chess for legality and preserve M1's `ShadowBoard` solely as a real-ALE transition cross-check.

## Proposed contracts and later-milestone compatibility

- The simulator owns the full Board and history needed for automatic outcomes. FEN is a position serialization, not a complete history restore.
- At agent decision boundaries, expose a read-only position observation with the fields and stable legal-move keys defined in [MDP_SPEC.md](../../docs/03-technical/MDP_SPEC.md). If a downstream model omits history required for Markov behavior, identify that limitation before M5; no raw-history tensor is required in M2.
- Validate a submitted UCI move against the current legal set before mutation. Reject illegal/stale actions without changing the Board.
- Keep agent color fixed per episode and reward from that color's perspective. A Black episode receives the opponent's White opening move during reset.
- Use automatic `python-chess` outcomes (`Board.outcome(claim_draw=False)`). Simulator caps produce truncation with a final valid state and reason; they do not fabricate a chess result.
- M3 PGN played moves map to the same stable move identity and remain distinct from any separately authorized Stockfish label. Preserve source-game provenance and leakage-safe splits; O-06 remains open.
- M4/M5 may later compare legal-candidate action-conditioned scoring with a fixed global move vocabulary. M2 implements neither neural scorer nor output head.
- M6 consumes semantic move intent only after an ALE state is validated; the M1 controller executes it and RGB evidence remains authoritative. Simulator outcomes never substitute for ALE results.

## Acceptance evidence mapping

| Criterion | Minimum future evidence |
|---|---|
| M2-01 | Reviewed simulator contract covering complete rules state/history, legal `Move` actions, agent/opponent boundary, fixed perspective, terminal reward, automatic outcomes, truncation, and simulator/ALE separation. |
| M2-02 | Focused tests for ordinary and supported special moves, legal-action identity, invalid-action non-mutation, checkmate, stalemate, insufficient material, automatic fivefold/75-move outcomes, and truncation. |
| M2-03 | Completed seeded games by both random-legal and heuristic baselines, with per-game policy/opponent, color, seed, outcome, length, and reproducibility evidence; disclose truncated runs. |
| M2-04 | Result records/tests that label simulator metrics separately and prevent them from being reported as ALE performance. |

These are evidence expectations, not M2 results. Canonical acceptance wording remains in `ACCEPTANCE_CRITERIA.md`.

## Implementation sequence after authorization

1. Re-read canonical state/backlog, this plan, MDP specification, ADR-0002, and acceptance criteria. Confirm the M2 authorization is current.
2. Verify the locked `python-chess` API for `Board.outcome(claim_draw=False)` and standard move UCI semantics. Define a small reset/step/result interface before coding.
3. Add focused simulator tests for state/history, legal UCI moves, ordinary/special moves, automatic outcomes, and invalid-action safety.
4. Implement the agent-move/opponent-reply transition with terminal checks after each move; test reward signs for both agent colors.
5. Add decision-boundary truncation with a valid final observation and a reason distinct from external interruption.
6. Add seeded random-legal and simple heuristic selectors; verify both return legal moves.
7. Run a small seeded benchmark across both colors, retaining per-game records and reporting completed/truncated counts without Elo claims.
8. Run focused and full applicable tests, preflight, and reproducibility checks. Preserve actual command, duration, exit code, revision, and sanitized evidence.
9. Evaluate M2-01 through M2-04 against evidence independently. Do not start M3 or later without separate authorization.

## Verification commands after implementation

These commands are for future authorized M2 implementation and were not run for this preparation task:

- **Focused tests:** `uv run --locked --no-sync python -m unittest tests.test_m2_simulator tests.test_m2_baselines -v`
- **Full suite:** `uv run --locked --no-sync python -m unittest discover -s tests -v`
- **Context/preflight:** `python3 scripts/agent_preflight.py`
- **Seeded benchmark:** add the exact CLI/config with implementation; retain per-game records and a compact summary.

Use the existing locked environment documented in [SETUP.md](../../docs/05-operations/SETUP.md). Do not install dependencies merely to begin M2. Store raw run artifacts under the ignored artifact area with unique IDs; commit only a small sanitized report/manifest where project policy permits.

## Risks and approvals

- RSK-002 remains open: standard simulator rules may differ from Atari VideoChess; M1 does not establish special-move or draw-rule parity.
- RSK-003 remains open: Stockfish scores and RL returns differ in perspective, scale, and meaning.
- RSK-006 remains open: the proposed third-party Lichess archive has unresolved licensing/provenance; resolve O-06 before M3 ingestion.
- RSK-009 remains open: a compact model observation may omit Board history needed for an exact Markov representation; validate or explicitly bound that approximation before M5.
- O-01 governs assignment permissions for custom PyTorch RL, Stockfish use, and ALE extraction. M2 simulator/baselines do not need Stockfish or training.
- O-07 governs Stockfish versions/roles; no Stockfish operation is part of M2. O-08 governs opponent pools and rating claims; M2 does not claim calibrated Elo.
- O-02, O-03, O-04, and O-05 remain open for future work that depends on submission fallback, deadline, cloud resources, or unverified ALE settings.

## Checkpoint and recovery

Before future M2 implementation, refresh the approved checkpoint and preflight; use current canonical state rather than this plan's status. Preserve untracked files and local ALE evidence. Mark M2 in progress only after implementation actually starts, and do not mark acceptance from documentation alone.
