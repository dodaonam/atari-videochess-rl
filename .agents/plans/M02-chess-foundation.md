# M02 — Chess Foundation Plan

- **Plan ID:** M02
- **Milestone:** M2 — Chess foundation, associated with G3
- **Plan status:** draft; prepared for review, not active
- **Task:** M2-001 in [.agents/tasks/BACKLOG.yaml](../tasks/BACKLOG.yaml), pending explicit user authorization
- **Dependencies:** M1-001 is complete; G2 is approved. M2 implementation still requires a separate explicit user authorization.
- **Requirements:** B-03, B-05, B-06, B-07, B-08 and unresolved approvals O-01, O-06, O-07, O-08 in [REQUIREMENTS.md](../../docs/01-foundation/REQUIREMENTS.md)
- **Acceptance:** M2-01 through M2-04 in [ACCEPTANCE_CRITERIA.md](../../docs/06-quality/ACCEPTANCE_CRITERIA.md)
- **Architecture references:** [ARCHITECTURE.md](../../docs/03-technical/ARCHITECTURE.md), [MDP_SPEC.md](../../docs/03-technical/MDP_SPEC.md), proposed [ADR-0002](../../docs/02-management/decisions/ADR-0002-chess-mdp-action-and-perspective.md)
- **Existing ALE references:** [ALE_ENVIRONMENT.md](../../docs/03-technical/ALE_ENVIRONMENT.md), [BOARD_EXTRACTION.md](../../docs/03-technical/BOARD_EXTRACTION.md), [ACTION_ADAPTER.md](../../docs/03-technical/ACTION_ADAPTER.md)

## Objective

Build and verify a standard-chess simulator foundation using the pinned project chess library. Define a decision process whose state, legal actions, transitions, rewards, terminal outcomes, truncation, opponent behavior, and player perspective are explicit. Provide reproducible random-legal and transparent heuristic baselines and seeded simulator benchmarks.

This plan and the specifications are planning artifacts. No M2 implementation or M2 acceptance test has been run. A plan marked draft or ready never grants permission to start its milestone.

## Scope

- Define and implement the simulator contract using standard chess rules and the project’s existing python-chess dependency.
- Preserve complete game history needed for claimable repetition draws.
- Define a stable semantic action key, action generation and legal-action handling; do not use a legal-list position as a cross-state action identifier.
- Define one player perspective, an opponent policy boundary, reward signs, terminal outcomes and environment truncation.
- Add a random-legal baseline and a small, deterministic, documented heuristic baseline.
- Run seeded simulator episodes and record policy/opponent identity, color, seed, result, moves, configuration and source revision.
- Keep every simulator result distinct from ALE observations, rewards, terminal flags and metrics.

## Explicit exclusions

- This plan does not authorize implementation. Wait for explicit M2 authorization and review of proposed ADR-0002.
- No M3 PGN ingestion, dataset construction, Stockfish labeling/search, or data download.
- No M4 supervised training, M5 Double DQN training, model or replay-buffer implementation.
- No new ALE gameplay, changes to the M1 controller/vision/shadow system, or claim that simulator results establish Atari performance.
- No Colab, GPU, paid compute, external service, or resolution of O-01 through O-08.
- No model tensor shape, network size, reward shaping, discount value, training schedule, Elo claim, or opponent pool is frozen by this plan.

## Proposed implementation boundaries

Keep additions small and under the existing package unless implementation evidence requires another boundary:

| Proposed module | Future responsibility | Boundary |
|---|---|---|
| videochess_rl/simulator.py | Reset, agent decision, opponent response, reward and Gymnasium-style termination/truncation. | Uses python-chess; has no ALE or RGB dependency. |
| videochess_rl/chess_actions.py | Semantic move keys, legal candidate construction, deterministic mapping and optional legal mask. | Standard chess moves and claim-draw action only; no Atari joystick encoding. |
| videochess_rl/baselines.py | Seeded random-legal and transparent heuristic move selectors. | Selects only from the simulator’s legal candidates. |
| videochess_rl/benchmark.py | Seeded games, opponent/color schedule and result records. | Labels records as simulator metrics. |
| tests/test_m2_*.py | Focused rule, contract, seeded integration and benchmark-record tests. | Does not replace M1 ALE integration coverage. |

These are proposals, not files that exist today. Reuse python-chess for rules and preserve M1’s ShadowBoard as an ALE cross-check; do not turn the M1 shadow into the simulator or merge their sources of truth.

## Proposed interfaces and dependencies

- A simulator owns a full standard-chess board plus its history, a fixed agent color for the episode, the opponent-policy identity/configuration, and a seeded random generator where needed.
- A decision state is returned only when the agent is to move. The agent action is a python-chess move represented by a stable semantic key, or a legal claim-draw action.
- Applying an agent action first checks legality. If the game remains live, the configured opponent chooses one legal reply. The transition returns the next agent decision state, or a terminal outcome.
- A transition record retains agent action, opponent reply, reward, terminated/truncated flags, result reason, seed and configuration. An invalid or masked action fails without changing the board; it is not a fabricated chess loss.
- The state contract retains the move stack or equivalent repetition history. A FEN alone is not a complete game state for repetition adjudication.
- Future M3 PGN samples can map their played move to the same semantic move key. A played move is behavior evidence, not automatically an optimal move. Stockfish scores, if separately authorized, are a different label with explicit source and perspective.
- Future M4/M5 action scoring can evaluate only current legal candidates. The selected action is stored semantically, never as an index into a transient candidate list.
- Future M6 consumes a move proposed from an ALE-validated observation and sends it to the existing controller. It must observe and confirm the real Atari transition before the M1 shadow advances.

The detailed MDP, candidate-action alternatives, perspective and reward contract are owned by [MDP_SPEC.md](../../docs/03-technical/MDP_SPEC.md) and proposed ADR-0002. This plan does not duplicate those specifications.

## Acceptance evidence mapping

| Criterion | Evidence to collect when M2 is authorized |
|---|---|
| M2-01 | Reviewed MDP specification and implementation contract covering state/history, legal actions, transition boundary, agent/opponent perspective, reward, terminal and truncation. |
| M2-02 | Unit tests for deterministic state serialization, legal-action mapping, standard transitions and supported special moves, check, mate, stalemate, automatic draws and claimable draws. |
| M2-03 | Reproducible seeded games by random-legal and heuristic policies; retained per-game records, seeds, colors, opponent identities and aggregate W/D/L, game length and truncation counts. Report only games actually completed. |
| M2-04 | Separate simulator result schema and ALE result schema; tests and report checks proving simulator metrics are never labeled as ALE metrics. |

These are expected evidence types, not claims that M2-01 through M2-04 have passed. The canonical wording remains in ACCEPTANCE_CRITERIA.md.

## Implementation sequence after authorization

1. Review ADR-0002 and the open technical questions in MDP_SPEC.md. Confirm the chosen simulator action, agent-color and transition contract before source changes.
2. Confirm that the selected python-chess version and APIs are the locked project versions. Define the public reset/state/step/result schema and error behavior before coding.
3. Add focused state and action contract tests first: FEN/normalization round trips, history retention, legal actions, deterministic key mapping, mask correctness, promotions, castling and en passant.
4. Implement the simulator transition boundary and reward/outcome conversion. Test a terminal result after the agent move and after an opponent reply, plus claimable and automatic draws.
5. Implement bounded truncation with a valid final observation. Keep truncation distinct from a chess outcome and from an external runner interruption.
6. Add seeded random-legal and heuristic policies. Validate returned moves against the current legal set and make randomness explicit.
7. Add seeded simulator match records and small benchmark runs. Exercise both colors and identified opponent policies; disclose any incomplete or truncated games.
8. Run focused M2 tests, the context/preflight checks, and the applicable full suite. Preserve logs with timestamps, exit codes and the exact committed revision.
9. Review M2-01 through M2-04 separately against actual evidence; update task/state only after criteria are met. Do not proceed to M3 or later without its own authorization.

## Verification commands and expected evidence

Commands below are for the future authorized M2 implementation and have not been run for this preparation task:

- **Focused tests:** uv run --locked --no-sync python -m unittest tests.test_m2_simulator tests.test_m2_actions tests.test_m2_baselines -v
- **Complete suite:** uv run --locked --no-sync python -m unittest discover -s tests -v
- **Context and governance:** python3 scripts/agent_preflight.py
- **Seeded benchmark:** the exact command/config must be added with the implementation; preserve raw per-game records and a compact summary.

Use the locked project environment already documented in [SETUP.md](../../docs/05-operations/SETUP.md). Do not install packages merely to begin M2. Save generated run artifacts under the ignored run/artifact area with unique IDs, and retain a small committed manifest/report only when supported by the project’s artifact policy.

## Risks and approvals

- RSK-002 remains open: standard simulator rules may differ from Atari VideoChess; M1 evidence does not establish special-move or draw-rule parity.
- RSK-003 remains open: Stockfish scores and RL returns use different meanings, scales and possibly perspectives.
- RSK-006 remains open: the proposed third-party filtered Lichess archive has unresolved licensing/provenance and reuse terms. O-06 must be resolved before M3 ingestion.
- Proposed ADR-0002 requires review because action identity, agent perspective and transition boundary affect M2 and later learning.
- O-01 governs assignment permissions for custom PyTorch RL, Stockfish training/use, and ALE extraction. M2’s rule simulator and baselines do not need Stockfish or training; verify applicable course rules before later restricted work.
- O-07 governs Stockfish versions and permitted roles; no Stockfish operation is part of M2.
- O-08 governs opponent pools and rating claims; M2 records identified opponents and does not claim calibrated Elo.
- O-02, O-03, O-04 and O-05 remain open. They must be reviewed before work that depends on submission fallback, deadline, cloud resources, or unverified ALE settings.

## Checkpoint and recovery

Before any future M2 implementation, refresh the canonical checkpoint and preflight. Read the live state and M2-001 task rather than relying on this plan’s status. Preserve untracked files and local ALE artifacts. If an implementation session is interrupted, leave the task in progress only when work has actually begun, record the exact next action and evidence, and do not mark acceptance from documentation alone.
