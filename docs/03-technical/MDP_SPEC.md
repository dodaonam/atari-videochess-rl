# Chess Simulator MDP Specification

**Status (2026-10-28):** Accepted M2 contract under ADR-0002. Simulator implementation and M2-01 through M2-04 are verified in [the M2 acceptance record](../../.agents/evidence/M2-acceptance-20261016.md). The ADR-0003 action-conditioned model interface is accepted and implemented for M4: M4-01 through M4-04 passed, with 121,897 measured parameters and the frozen behavior-only checkpoint identified in the [M4 acceptance report](../../.agents/evidence/M4-final-acceptance-20261027.md). These M4 results do not establish M5 Q-learning. The M5 Bellman/transition specification is in [RL_ALGORITHM.md](RL_ALGORITHM.md); implementation and training remain future and unauthorized work.

**Purpose:** Specify the smallest standard-chess decision process needed for M2 while preserving clear interfaces to M3 PGN/teacher data, the accepted ADR-0003 M4 behavior scorer and M5 Double DQN Q head, and M6 ALE integration. The accepted foundational choices are recorded in [ADR-0002](../02-management/decisions/ADR-0002-chess-mdp-action-and-perspective.md); implementation and acceptance evidence are recorded in the linked M2 acceptance record.

## 1. Decision process

For a fixed opponent policy and configuration, use the agent-centered process `(S, A, P, R, γ, ρ₀)`:

- **State `S`:** the full standard-chess `python-chess.Board`, including its move stack, plus the episode's fixed agent color and opponent policy identity/configuration. The seeded random generator is episode execution state used to reproduce stochastic opponent choices.
- **Actions `A(s)`:** exactly the legal `python-chess.Move` values in `Board.legal_moves`. Their stable serialized identity is UCI; a move's meaning never depends on its index in a position-specific list. No other action types are part of the simulator.
- **Transition `P`:** apply one legal agent move. If it ends the game, return the terminal result. Otherwise the configured opponent selects and applies one legal reply. If that ends the game, return the terminal result; otherwise return the next decision state for the same agent. The opponent move is part of the transition and is not chosen by the agent.
- **Reward `R`:** terminal result only, from the fixed agent-color perspective. Nonterminal reward is zero. A simulator limit is truncation with zero reward, not a chess result.
- **Discount `γ`:** one discount applies per agent-decision transition, including its opponent reply when one occurs. M2 does not select a numeric discount; that is a later learning experiment.
- **Initial distribution `ρ₀`:** standard initial board, recorded agent color, opponent identity/configuration, and explicit episode/opponent seeds when randomness is used. If the agent is Black, the opponent makes White's opening move during reset, and the move is recorded before the first agent decision.

The stochastic opponent and its fixed policy configuration define the transition distribution. Policies without an episode reset hook must be stateless across episodes. A stateful policy may implement `reset_episode(seed=...)`; the simulator calls it before each episode. `ChessSimulator.reset(seed=..., opponent_seed=...)` accepts an optional opponent RNG seed separate from the episode seed; when omitted, the episode seed continues to seed both the simulator's opponent-action RNG and the policy reset hook, preserving existing callers. Paired experiments may supply both named seeds so domain-separated opponent randomness does not depend on a run ID. Policy identity and configuration must stay stable for the simulator lifetime so observation and benchmark records remain accurate. If a reset hook fails, the episode is invalidated because external policy state may be partially changed. Simulator results do not describe ALE/VideoChess behavior; the separate real-environment contract is in [ALE_ENVIRONMENT.md](ALE_ENVIRONMENT.md).

## 2. Rules state and agent observation

### Simulator state

Use one `python-chess.Board` as the source of truth for simulated chess rules and transitions. It owns piece placement and colors, side to move, castling rights, en passant state, move counters, and the move stack needed for history-dependent automatic outcomes. Do not keep a second mutable chess rules state.

FEN is useful for position logs and position-field round trips, but it does not preserve prior move history. Recreate a history-sensitive game from its initial position and recorded legal moves; do not treat a FEN-only restore as a complete simulator state.

### Agent observation

At each agent decision, provide a read-only position snapshot with piece placement/colors, side to move, fixed agent color, castling rights, en passant state, relevant move counters, and the current legal moves represented by stable UCI keys. This is an interface contract, not a neural tensor or network design.

The full Board/history remains the rules state. A compact observation that omits repetition-relevant history is not guaranteed to be Markov, even though it may be sufficient for ordinary move selection. M2 keeps the move history in simulator observation metadata but does not require a future model to consume the raw move list. The simple M2 heuristic rebuilds its one-ply candidate board from FEN and ignores that history; this can affect its move preference around repetitions but cannot change simulator legality or termination. Before M5, validate the chosen observation or document the partial-observation approximation.

## 3. Legal move identity and handling

The M2 action is a standard `python-chess.Move`; serialize it with its UCI move string for traces and stable references. UCI distinguishes all four promotion choices. Castling and en passant are ordinary legal moves whose interpretation and legality come from the current Board. Generate the candidate set directly from `Board.legal_moves`; deterministic UCI sorting may be used for reproducible logs, but candidate ordering has no action semantics.

When a serialized move is received, parse it and verify that the resulting move is in the current Board's legal move set before mutation. Reject an invalid or stale move with a clear error and leave the Board unchanged. Do not persist a legal-list offset as an action identity.

M2 needs only this semantic move contract; it does not need the neural action encoder, candidate batching, or Q-network. A fixed global from/to/promotion vocabulary remains a deferred alternative because it adds many position-invalid outputs. ADR-0003 accepts a shared action-conditioned legal-candidate architecture: M4 scores supplied legal UCI moves with behavior logits, while M5 uses a separately initialized Q head. Online Double DQN selection chooses one legal semantic move and the target network evaluates that same UCI action, independent of candidate-list order. This is an accepted interface, not implemented code or evidence of empirical optimality.

## 4. Player perspective and transition boundary

Keep board colors absolute (`WHITE`/`BLACK`) and choose one fixed agent color per episode. Episodes may use either color. All simulator rewards and returns use that episode's agent-color perspective; do not switch perspective between turns. Convert White-perspective PGN/Stockfish/ALE values only at a documented boundary with a tested sign conversion. Teacher evaluations are not ALE rewards or calibrated RL returns.

One simulator step represents one agent decision and, if the game remains live, at most one opponent reply:

1. Validate and apply the agent's legal move.
2. If an automatic game outcome exists, return it without requesting an opponent move.
3. Otherwise ask the configured opponent for one legal move and apply it.
4. Return its terminal outcome if the game ended; otherwise return the next agent decision state.

The opponent's policy identity/configuration and opponent RNG seed are recorded because they affect transitions and reproducibility; M5 additionally records the pair-derived episode seed. The simulator checks that the opponent descriptor remains stable before a transition and after its callback. Rejected agent actions leave state unchanged. If an opponent error or interruption occurs after the agent move has been tentatively applied, the simulator restores the prior chess Board and stops the episode; policy-local state and consumed random numbers are not rolled back. This is a single-agent simulator, not a multi-agent learner.

## 5. Reward, termination, and truncation

Use terminal-outcome reward only:

| Event | Agent-perspective reward | `terminated` | `truncated` |
|---|---:|---:|---:|
| Nonterminal agent move and opponent reply | 0 | false | false |
| Agent wins | +1 | true | false |
| Agent loses | -1 | true | false |
| Automatic draw | 0 | true | false |
| Simulator decision limit at a valid agent-decision boundary | 0 | false | true |
| Invalid move | No transition; reject without mutation | — | — |

Use the pinned `python-chess` rules engine's automatic outcome check, equivalent to `Board.outcome(claim_draw=False)`. This includes checkmate, stalemate, insufficient material, automatic fivefold repetition, and the automatic seventy-five-move rule. Voluntary draw-claim actions are excluded from the project's active scope; there is no action, interface, or planned extension for them. Do not write custom chess adjudication when the library supplies the required automatic outcomes. The locked library behavior is exercised by the M2 simulator tests.

M2 uses an agent-decision limit checked after a complete transition, so truncation returns the valid next-agent state. Any separately added total-ply or wall-clock cap must also report truncation (or an external runner stop for host interruption); it must never fabricate a chess result. Preserve the final valid Board, flags, and explicit stop reason separately.

For later Double DQN, do not bootstrap from a genuine terminal outcome. A valid time-limit truncation is not a chess result; retain its final observation and apply the separately tested time-limit bootstrap treatment. M2 does not implement learning targets or choose a discount value.

No material reward, check bonus, step penalty, teacher-score reward, or positional shaping belongs in the baseline. Any later reward change requires a separately authorized experiment and result identity.

## 6. Simulator and ALE boundary

The M2 Board and outcome come from `python-chess` and the configured simulator opponent. They are evidence about simulator rules and baselines only. They do not establish Atari move acceptance, opponent behavior, reward, terminal flags, or transfer.

For M6, the current ALE RGB observation and verified move history remain the source of Atari state. The model may propose a semantic chess move; the existing controller translates it to joystick/FIRE actions and RGB evidence must confirm the resulting transition. Do not emulate Atari cursor timing in M2 or substitute simulator state for a failed ALE observation. Standard-chess moves that remain unverified in Atari, including special moves, stay integration limitations rather than changes to the simulator rules.

## 7. M2 verification contracts

The implementation and focused tests cover these contracts; see the [M2 acceptance record](../../.agents/evidence/M2-acceptance-20261016.md) for exact commands, results, and retained logs:

1. Position serialization is deterministic; the observation FEN uses `en_passant="fen"` and round trips position fields, while replay from the appropriate initial position preserves the move history used by the rules engine. FEN alone cannot restore repetition history.
2. Generated actions equal `Board.legal_moves`; stable UCI identities round-trip for ordinary moves, captures, all four promotions, castling, and en passant, regardless of candidate enumeration order.
3. A legal move produces the expected Board transition. An invalid or stale move is rejected before mutation.
4. Checkmate, stalemate, insufficient material, automatic fivefold repetition, and the automatic seventy-five-move outcome match the locked `python-chess` API.
5. Agent-color reward signs are correct for both colors. A terminal agent move skips the opponent reply; an opponent terminal reply returns without another agent step.
6. Simulator truncation retains a valid final state and is distinct from a chess terminal and an external interruption.
7. Same seed, color, opponent identity/configuration, and initial state reproduce the move/outcome record.
8. Random-legal and lightweight heuristic baselines select only legal moves; benchmark records identify policies, colors, seeds, outcomes, lengths, completion/truncation, configuration, and source revision.
9. Simulator results remain separately labeled from ALE observations, reward, terminal flags, and metrics.

## References

- M2 scope and order: [M02 plan](../../.agents/plans/M02-chess-foundation.md).
- M2 pass conditions: [ACCEPTANCE_CRITERIA.md](../06-quality/ACCEPTANCE_CRITERIA.md).
- Project constraints and proposed later model choices: [REQUIREMENTS.md](../01-foundation/REQUIREMENTS.md).
- Existing ALE shadow boundary: [shadow.py](../../videochess_rl/shadow.py).
- Decision maturity: [ADR-0002](../02-management/decisions/ADR-0002-chess-mdp-action-and-perspective.md).
