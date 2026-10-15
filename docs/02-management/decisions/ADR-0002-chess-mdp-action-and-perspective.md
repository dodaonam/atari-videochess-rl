# ADR-0002: Proposed Chess MDP Action and Perspective

- **Status:** Proposed; not user-approved
- **Date:** 2026-10-16
- **Decision owner:** Project user for acceptance; Codex prepared the technical recommendation
- **Scope:** M2 chess simulator contract and compatibility constraints for M3–M6. This ADR does not authorize M2 implementation, data use, Stockfish use, model training, or ALE experiments.
- **Evidence:** [REQUIREMENTS.md](../../01-foundation/REQUIREMENTS.md), [ROADMAP.md](../../01-foundation/ROADMAP.md), [M2 MDP specification](../../03-technical/MDP_SPEC.md), [M2 plan](../../../.agents/plans/M02-chess-foundation.md), and the existing python-chess dependency/lock.

## Context

M2 must define legal actions and transitions for a chess simulator. Later M5 plans Double DQN, where the learner must select the highest-value legal action at the next state and have the target network evaluate that same action. A position’s legal-move list has variable length, so a list offset is not a stable action identity across states. The existing proposal in REQUIREMENTS.md favors an action-conditioned afterstate scorer but did not define move identity, player perspective, draw claims or the decision boundary around an opponent reply.

## Proposed decision

1. Keep semantic action identities: standard python-chess Move fields (from square, to square and promotion piece), plus `CLAIM_DRAW_NOW` or `CLAIM_DRAW_AFTER(move)` when the current or announced-move rules state permits a claim. Record the claim basis and announced move; an accepted claim terminates as a draw without an opponent response. Never store the index of a legal candidate list as the action.
2. Provisionally score only the state’s legal candidates with an action-conditioned/afterstate Q function. Enumerate candidates deterministically for trace reproducibility. For Double DQN, the online scorer selects the maximum-Q legal semantic action at the next decision state; the target scorer evaluates that same action. A fixed global action vocabulary remains a valid alternative if later model constraints justify it.
3. Provisionally use a single decision-making agent with one fixed color per episode. Sample both colors across separately seeded episodes. Reward is from that episode’s agent-color perspective: win +1, loss −1, draw 0. Preserve White/Black board colors and keep teacher-score conversions explicit.
4. Provisionally make one MDP transition one agent action followed, while the game remains live, by one complete configured opponent reply. This returns control at the next decision by the same agent. The opponent policy and identity are part of the transition configuration; record the reply in episode data. Do not model current-player sign flips in the initial Double DQN formulation.
5. Use terminal-outcome reward only for the baseline. Checkmate is win/loss; draw is zero. Treat a simulator decision/ply cap as truncation with a valid final state, not as a chess result. Reject invalid/masked actions without board mutation.
6. Preserve python-chess move history or an equivalent sufficient history representation for claimable and automatic repetition outcomes. FEN is not by itself a complete history-sensitive state. Verify current-position and announced-move claims against pinned python-chess and FIDE rules before implementation.

Every point above remains a proposal until reviewed. The exact model feature encoding, numerical discount, opponent mixture, benchmark schedule and any reward shaping remain open decisions for their relevant milestones.

## Alternatives considered

- **Global fixed move head:** a complete source×target×promotion vocabulary is stable and directly supports a fixed DQN output layer. It has 20,480 chess-move IDs; representing claim-now and claim-after-move actions as fixed IDs can raise the total to 40,961, with many illegal outputs per position. Retain it as a viable alternative only if later model constraints justify its mask and output costs.
- **Variable legal list index:** rejected as a persistent action ID because candidate order and list length vary by position. It may be used only as a temporary tensor row within one batch if each row retains its semantic move key.
- **Action-conditioned legal candidate scorer:** recommended provisionally because it scores only legal moves, avoids a large mostly-invalid head, aligns with the current afterstate proposal, and supports current PGN move/teacher candidate mapping. It requires explicit state/action features and candidate batching tests.
- **Alternating current-player value:** not selected for the initial design because reward signs and Bellman targets would change perspective each ply or require a zero-sum/negamax formulation.
- **White-only agent:** simpler sign bookkeeping but limits color coverage. Prefer both colors across episodes with a fixed agent color within each episode.
- **Opponent reply as a separate learner action:** not selected for the initial single-agent DQN because it would let the agent choose the opponent move unless a distinct multi-agent model were added.
- **Automatic acceptance of every claimable draw:** not selected because a claim is a player decision in standard chess. The proposal exposes typed current-position and announced-move claim actions; an invalid claim is rejected without mutation because this simulator does not model chess clocks or the penalty for an incorrect claim.

## Consequences and validation

- M2 will use python-chess legality and history, while M1 shadow state continues to advance only on real ALE RGB evidence.
- Candidate action count is state-dependent but identifiers are not. Replay records can reconstruct the intended action without preserving a transient candidate index.
- A Q scorer must evaluate a candidate consistently from its state and semantic key. The selected action must be in the legal set; a bad action is an error, not a synthetic reward.
- The opponent policy changes the transition distribution. Benchmark results must identify opponent and policy version and must not be summarized as environment-independent chess strength.
- State encoders that omit repetition history may be partially observable even when the simulator Board is Markov. Validate history representation before M5.
- Reward signs must be tested for both agent colors and remain distinct from White-perspective ALE reward and White-perspective Stockfish scores.

## Required review before implementation

Before M2 source changes, review and accept or revise:

1. Legal-candidate action-conditioned scorer with semantic Move keys versus a fixed global action vocabulary.
2. Fixed agent color per episode and agent-perspective outcomes.
3. Agent-move-plus-opponent-reply transition boundary.
4. Typed current-position/announced-move draw claims and retained repetition history, including accepted-claim transition semantics.
5. Terminal-only reward and environment truncation contract.

This review does not replace the separate explicit M2 authorization required by canonical project state. O-01 through O-08 remain open; this ADR cannot resolve them.

## References

- [M2 MDP specification](../../03-technical/MDP_SPEC.md)
- [M2 implementation plan](../../../.agents/plans/M02-chess-foundation.md)
- [Project requirements and proposed action direction](../../01-foundation/REQUIREMENTS.md)
- [M2 acceptance criteria](../../06-quality/ACCEPTANCE_CRITERIA.md)
