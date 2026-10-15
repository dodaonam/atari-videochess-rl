# Chess Simulator MDP Specification

**Status:** Proposed M2 design. No chess simulator, state encoder, action encoder, baseline or RL environment has been implemented or tested.

**Purpose:** Define a standard-chess simulator contract that can support M2 baselines and remain compatible with separately scoped M3 PGN/teacher data, M4 pretraining, M5 Double DQN and M6 ALE evaluation.

The architecture recommendation is recorded as proposed, not accepted, in [ADR-0002](../02-management/decisions/ADR-0002-chess-mdp-action-and-perspective.md). M2-01 through M2-04 remain unverified.

## 1. Environment definition

For a fixed opponent policy and configuration, define the proposed agent-decision MDP as

**(S, A, P, R, γ, ρ₀)**.

- **S — state:** a standard chess position, complete game-history information needed by the selected draw rules, fixed agent color, and fixed opponent-policy identity/configuration. The agent receives decisions only when it is its turn.
- **A — actions:** a legal python-chess move identified by its semantic move key, plus `CLAIM_DRAW_NOW` when the current position is claimable and `CLAIM_DRAW_AFTER(move)` when announcing that legal move would make the position claimable. A claim action ends the game only when its claim basis is valid; an announced move is recorded as the claim basis and is not pushed as an ordinary agent move after an accepted claim. The available set A(s) is state-dependent. See “Action representation” and “Game ending, claims and truncation.”
- **P — transition:** validate and apply one agent action. If that move ends the game, return the terminal state. Otherwise, invoke exactly one legal opponent response from the configured opponent policy; if that reply ends the game, return the terminal state. Otherwise return the state at the next agent turn. Opponent behavior is part of P, not a second action chosen by the agent.
- **R — reward:** zero on nonterminal transitions; terminal win/loss/draw reward from the fixed agent’s perspective. Truncation has no chess outcome and no terminal reward.
- **γ — discount:** one discount per agent decision transition, including the integrated opponent response. The numeric value is a later M5 experiment decision; no value is selected here. M2 rule/benchmark code does not require learning discounting.
- **ρ₀ — initial distribution:** standard initial board, an explicitly selected agent color, and an identified opponent policy/configuration. If the agent is Black, the opponent makes White’s opening move during reset so the first returned decision state is still the agent’s turn. Record the opening move in reset info and the episode trace.

For a given stationary opponent policy π, the transition is P(s′|s,a,π). A stochastic policy’s identity and configuration are fixed and recorded for the episode; its random choices use an explicit seeded generator. If opponent choice is switched within an episode, that opponent identity or the switching state must be represented so the transition law remains defined.

This is a chess simulator with a policy-controlled opponent. It is not ALE/VideoChess. The real ALE environment has its own opponent, RGB observations, joystick timing, reward, terminal and truncation behavior; those facts are specified in [ALE_ENVIRONMENT.md](ALE_ENVIRONMENT.md).

## 2. State and Markov sufficiency

### Rules state

Use a standard python-chess Board as the simulator’s rules engine. The transition-relevant position contains at least:

- piece placement and piece colors;
- side to move;
- castling rights;
- en passant target/capture availability;
- halfmove clock;
- prior position history needed to adjudicate repetition;
- fixed agent color and opponent policy identity/configuration.

FEN is useful for readable logs and position round trips. Its fields include piece placement, side to move, castling rights, en passant square, halfmove clock and fullmove number. A FEN does not encode the full prior move stack. A FEN-only restore can therefore lose the history needed for threefold/fivefold repetition and draw claims. Preserve the root position plus move history, or a validated sufficient repetition-history representation. Do not clear the python-chess stack when history-sensitive rules are enabled.

The fullmove counter is useful for notation and logs; the move history and halfmove clock affect history-sensitive outcomes. A compact neural representation is not selected in this document. Piece-plane or structured encodings must additionally represent side to move, castling/en-passant state, the halfmove clock and sufficient repetition context. Board occupancy alone is not Markov for this rule set.

The observation/action mask supplied to a future policy must be deterministic for the same full state. If the model omits information needed to distinguish draw rights, document that as a partial-observation approximation and validate its effect before M5.

### Episode context

Keep agent color and opponent identity fixed during one episode. They may vary between episodes. Store them in the simulator state or in explicit episode context supplied to the policy and transition. This prevents a single value function from silently mixing reward signs or opponent transition distributions.

## 3. Action representation

The action object is a chess move, not one of ALE’s ten joystick buttons. Standard castling is represented by python-chess as the king’s from/to move; en passant is determined from the Board’s legal state; promotion must include the selected piece. The move’s semantic identity must survive candidate reordering and serialization.

| Representation | Stable identity and size | Strengths | Costs and failure modes |
|---|---|---|---|
| Fixed global from/to/promotion vocabulary | One global ID per source square, destination square and promotion choice: 64 × 64 × 5 = 20,480 move IDs. Full claim semantics add one claim-now ID and up to 20,480 claim-after-move IDs, for a 40,961-ID space; a different typed action scorer could avoid a monolithic output head. | Stable output index; easy to save in replay, label PGN moves, and produce a fixed DQN head. Promotion types remain distinct. Legal masks can be derived by mapping Board.legal_moves to IDs. | Most move IDs are geometrically or positionally impossible. Full intended-move claims add another large action family. Mask generation and exact encoding must be tested. Invalid actions must never be silently pushed. |
| Board-dependent legal candidate set | Candidates are the actual legal Move keys in the current state, sorted by a deterministic semantic key, plus typed claim actions: claim now or claim after a specific legal announced move. Candidate-list positions are temporary and have no global meaning. | Computes scores only for valid actions; directly uses python-chess legal move generation; compact per decision; natural for PGN played-move mapping and pairwise teacher candidate labels. | Variable number of candidates; implementations must not persist list indices. A conventional fixed-output DQN cannot consume candidate position as a global output dimension. It needs an action-conditioned Q scorer Q(s,a) or an explicit mapping to a fixed vocabulary. |
| Established plane-based chess encoding | A fixed spatial move vocabulary, such as the 8×8×73 action planes used in AlphaZero-style chess systems. | Smaller fixed head than a full from/to cross-product; spatial parameter sharing is natural for convolutional encoders. | Requires careful color/orientation canonicalization, action-plane mapping, promotions and special-move round trips. This adds model/action-encoding coupling before M2 needs it. |

### Provisional recommendation

Retain the project’s existing proposed action-conditioned afterstate Q direction, and use a stable semantic move key such as (from square, to square, promotion piece) as the action identity. Generate candidates from the current Board’s legal moves and score each legal candidate with the same scorer. Represent a draw claim as a typed semantic action: `CLAIM_DRAW_NOW`, or `CLAIM_DRAW_AFTER` with the announced legal move key. Include the claim basis and announced UCI move in the transition trace. Do not store a candidate-list index in replay or evidence.

This recommendation resolves the changing-list-index problem without requiring a 20,481-logit move head (or a larger fixed head that also enumerates intended-move claims). For Double DQN, enumerate legal candidates at s′, have the online scorer choose the highest-scoring legal semantic action, then have the target scorer evaluate that same action at s′. For a terminal state there is no next-action maximization. For a truncation with a valid final observation, bootstrap according to the later approved algorithm contract.

The proposed action-conditioned scorer still needs a deterministic state/action feature contract and batching tests. Its tensor structure belongs to future model design, not this specification. If M4/M5 instead choose a fixed output head, adopt a global action-ID mapping and test every legal special-move round trip before training. The recommendation and alternatives remain subject to review in ADR-0002.

### Legal actions and invalid actions

- Candidate generation must match python-chess legal_moves for the current full Board.
- Promotions to queen, rook, bishop and knight are distinct semantic actions.
- Castling and en passant are ordinary standard-chess Move keys whose legality depends on Board state.
- A legal draw claim is a separate action; it is not encoded as a chess Move. Distinguish a claim based on the current position from one based on a specific announced legal move.
- A mask, when materialized, is true exactly for generated legal move keys and claim actions whose basis is valid in the current full-history state. It is derived from the simulator, not predicted by the model.
- An attempted key absent from the current legal set is a programming/policy boundary error. Reject it before mutation. Do not assign a synthetic loss reward or push an illegal move.
- Enumerate candidates deterministically for reproducible traces, while ensuring Q values are associated with semantic actions and not their current enumeration order.

## 4. Player perspective and opponent boundary

### Alternatives

- **Absolute White/Black values:** keep the board and reward in White’s perspective. White wins are positive and Black wins negative; a Black agent must negate values. This aligns naturally with White-perspective Stockfish and observed ALE reward, but invites sign mistakes when mixing data and agent rewards.
- **Agent-color perspective:** fix one agent color per episode and define all simulator reward and learned return from that agent’s perspective. Include agent color in episode state/config. Convert explicitly at data boundaries. This avoids changing the Q sign between the agent’s turns.
- **Current-player perspective / alternating actor:** change perspective each ply or let one learner control both sides. It requires sign-flipped/negamax targets or a multi-agent formulation and careful opponent/model ownership; a plain single-agent DQN target cannot be copied without defining this change.

### Provisional recommendation

Use a single decision-making agent with fixed color per episode; sample both colors across separate seeded episodes. The opponent is an explicit policy inside the environment transition. At every decision the agent acts once, then a live game receives one opponent reply before the next agent decision.

Use agent-color rewards: +1 for agent win, −1 for agent loss, and 0 for draw. The board remains absolute White/Black python-chess state. A future model may use agent-relative features, but must retain an explicit color/perspective contract. Keep teacher scores in their documented source perspective until a separately tested conversion produces an agent-relative target. Never treat a Stockfish centipawn score as an ALE reward or calibrated Q value.

For Double DQN targets, rewards are consistently from the fixed agent’s perspective and each transition begins and ends at the same agent-to-move boundary. The opponent move is included in the transition distribution and trace. If an alternate alternating-player design is selected, it requires a revised Bellman target and ADR before implementation.

## 5. Transition and reward contract

The preferred transition is one agent decision followed by at most one complete opponent reply. It lets a conventional agent-centric DQN keep the same decision maker at each state. The reward discount is per such decision transition, not independently per hidden opponent ply. A terminal result immediately after the agent move has no opponent reply. A result after the opponent reply is returned as terminal; the simulator must not request another agent move.

| Event | Reward | terminated | truncated |
|---|---:|---:|---:|
| Nonterminal agent move and legal opponent reply | 0 | false | false |
| Agent wins by checkmate | +1 | true | false |
| Agent loses by checkmate | −1 | true | false |
| Automatic draw or accepted legal claim | 0 | true | false |
| Simulator decision/ply cap reached at a fully observed boundary | 0 | false | true |
| Invalid/masked action | No transition; raise a clear error and preserve state | — | — |
| External benchmark wall-time/process stop | No fabricated chess result; runner records interruption separately | — | — |

Use terminal-outcome reward as the baseline. Nonterminal reward is zero. Material, check, teacher score, shaping and step penalties are not silently added. Any shaping, including potential-based shaping, must be a separately configured later experiment with a separate result identity.

For Double DQN, do not bootstrap from a true terminal result. A time/decision-limit truncation is not a chess result; if the final state is valid and the algorithm permits it, bootstrap from that final state. Preserve the final observation before any auto-reset. An external process interruption is not itself an MDP reward or terminal flag.

## 6. Game ending, claims and truncation

Use standard chess rules as implemented by the pinned python-chess dependency; verify exact APIs and behavior in tests before accepting M2. The project currently permits chess package versions ≥1.11,<2; the lock file selects the runtime version.

- Checkmate, stalemate, insufficient material, fivefold repetition and the seventy-five-move rule are automatic outcome checks. Checkmate precedence must match the library result.
- Threefold repetition and the fifty-move rule are claimable, not automatically terminal by default in python-chess. A claim may be based on the current position or on a specific legal move announced in advance that would produce the claim condition. Model those as `CLAIM_DRAW_NOW` and `CLAIM_DRAW_AFTER(move)` respectively. For the latter, validate the announced move against the full-history Board, record its semantic key/UCI as claim evidence, and do not treat it as an ordinary completed move when the claim is accepted. Reject an invalid claim without mutating the Board; clocks and penalties for an incorrect claim are outside this no-clock MDP and are not simulated. Verify this action contract against the pinned API and FIDE claim rules before accepting M2.
- The Board’s move stack/history is required for repetition checks; FEN alone cannot reconstruct that history.
- A maximum episode length is an environment truncation with the final live board retained. It is not checkmate, a draw, or ALE termination.
- Simulator draw rules are not evidence of Atari VideoChess rules or terminal flags. Compare them to Atari only with separate authoritative documentation and genuine M1/M6 runtime evidence.

The official python-chess core API documents that the default outcome check excludes claimable fifty-move/threefold draws unless claim_draw is requested, and that claims may be based on a legal next move. FIDE rules specify claims based on a position about to appear or an indicated move; M2 must validate the exact accepted-claim trace semantics against both sources and the locked library: [python-chess Core](https://python-chess.readthedocs.io/en/latest/core.html), [FIDE Laws of Chess, Articles 9.2–9.5](https://handbook.fide.com/chapter/e012023).

## 7. Simulator and ALE separation

M2 board states and outcomes are generated by python-chess and the selected opponent policy. They are useful for testing chess rules, baselines and learning transitions. They are not evidence of Atari move acceptance, Atari opponent behavior, real reward, complete-game Atari performance or transfer.

M6 must take its decision state from current ALE RGB and validated move history. It may use python-chess legal moves to constrain candidate moves and use the M1 shadow to check transitions, but the real screen and actual ALE reward/flags remain authoritative for Atari. A mismatch, unreadable special move, unready turn or failed controller phase must stop or use a tested safe recovery. Never substitute a simulator transition for a failed ALE action.

Compatibility risks include Atari-specific rule behavior; piece identity not fully visible in RGB; cursor and blink overlays; captures/animations; castling, en passant and promotion not established by M1; target-FIRE timing sensitivity; opponent thinking time; and terminal screens that clear the final board. These risks remain open in [RISK_REGISTER.md](../02-management/RISK_REGISTER.md) and the M1 records.

## 8. M2 verification contracts

These are required future checks, not passing tests:

1. Same full state serializes deterministically; FEN round trip preserves rule position while a history round trip preserves repetition context.
2. Generated candidates exactly match the legal move set. No illegal candidate is mask-valid.
3. Semantic action encode/decode round trips for ordinary moves, all promotions, castling, en passant, `CLAIM_DRAW_NOW` and `CLAIM_DRAW_AFTER(move)`; candidate reordering does not change action identity. A valid announced-move claim records its basis and ends as a draw without an opponent response; invalid claims leave the Board unchanged.
4. Applying a legal action produces the expected python-chess state and side to move. An illegal action raises without changing the state.
5. Agent-perspective terminal rewards are correct for White and Black wins/losses and draws.
6. Checkmate after the agent action skips the opponent reply; checkmate after opponent reply is returned as terminal without another agent step.
7. Automatic draws, claimable draws, terminal and truncation are distinct and tested.
8. Seeded games reproduce move/outcome records for the same environment, policies, color schedule and seed.
9. Random-legal and heuristic selectors return legal semantic actions and complete bounded games under recorded conditions.
10. Benchmark records identify simulator metrics and cannot be merged with or labeled as ALE results.

## Sources

- Project constraints and proposed afterstate direction: [REQUIREMENTS.md](../01-foundation/REQUIREMENTS.md), [ROADMAP.md](../01-foundation/ROADMAP.md).
- M2 acceptance: [ACCEPTANCE_CRITERIA.md](../06-quality/ACCEPTANCE_CRITERIA.md).
- Existing M1 shadow boundary: [shadow.py](../../videochess_rl/shadow.py).
- Proposed plan: [.agents/plans/M02-chess-foundation.md](../../.agents/plans/M02-chess-foundation.md).
- Decision maturity: [ADR-0002](../02-management/decisions/ADR-0002-chess-mdp-action-and-perspective.md).
