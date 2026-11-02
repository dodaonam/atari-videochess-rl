# ADR-0002: Chess MDP Action and Perspective

- **Status:** Accepted for the M2 foundational simulator contract on 2026-10-16. At that decision the M4/M5 neural interface remained open; the project owner later accepted that interface in ADR-0003 on 2026-10-23. The dated follow-up below records this later decision without changing ADR-0002's original M2 contract.
- **Date:** 2026-10-16
- **Decision owner:** Project user, who explicitly delegated the technical acceptance decision in the conversation on 2026-10-16; Codex prepared the technical recommendation.
- **Scope:** Accepted M2 foundational simulator contract and compatibility boundaries for M3–M6. At the 2026-10-16 decision, later neural model and scoring choices remained proposals. This record itself did not change M2 task status or authorize M3+, dataset use, Stockfish use, model training, or ALE experiments.
- **Evidence:** [REQUIREMENTS.md](../../01-foundation/REQUIREMENTS.md), [MDP_SPEC.md](../../03-technical/MDP_SPEC.md), [M02 plan](../../../.agents/plans/M02-chess-foundation.md), and the project dependency lock.

## Dated follow-up — 2026-10-27

The neural action-scoring option was provisional when this M2 decision was accepted. The project owner later accepted ADR-0003 on 2026-10-23, which now owns the M4/M5 shared-encoder and legal-candidate-scoring architecture. This supersedes only the earlier provisional M4/M5 model-interface wording; ADR-0002's accepted M2 state, action, reward, and transition contract is unchanged. ADR-0003 acceptance is design evidence, not implementation or performance evidence.

## Context

M2 needs ordinary legal chess moves with stable identity, reproducible transitions, and clear separation from the real Atari state. A legal-move list has a variable length and ordering; its temporary index is not a stable action identity. The simulator must also retain the Board history required by automatic chess outcomes, while future model input need not contain the full raw move list.

## User-authorized scope decision

The user explicitly removed all voluntary draw-claim functionality from active project scope. The simulator action space contains legal chess moves only. No claim actions, claim interfaces, claim encoding, claim-policy output, claim supervision, claim tests, or later extension are planned. That earlier scope decision is preserved; the M2 foundational technical contract below was subsequently accepted under the user's delegated authority. This acceptance does not extend to M4/M5 model architecture.

## Accepted M2 foundational technical contract

1. **Move identity:** Use only legal `python-chess.Move` actions. Serialize them as UCI for stable records and references, including promotion choice. Validate against the current Board before mutation; reject an illegal/stale action without changing state. Candidate-list ordering is never an action ID.
2. **Rules state and observation:** One `python-chess.Board` with its move stack owns simulator rules and history. FEN records position fields but cannot restore full repetition history. Define a read-only agent observation separately from this rules state; if a compact model view omits history, mark and test the resulting partial-observation limitation. Do not prescribe a neural tensor in M2.
3. **Agent perspective:** Keep one agent color fixed within an episode and sample both colors across episodes. Board colors remain absolute. Reward is always from the episode agent's perspective; convert White-perspective PGN, teacher, or ALE values only at explicit tested boundaries.
4. **Transition boundary:** One agent move followed, while the game remains live, by at most one configured opponent reply. Return control at the next decision by the same agent. If the agent is Black, the opponent plays White's opening move during reset. The opponent policy/configuration is fixed and recorded for the episode.
5. **Reward and outcomes:** Use terminal-only reward: agent win `+1`, loss `-1`, automatic draw `0`, otherwise `0`. Use the locked library's automatic outcomes, equivalent to `Board.outcome(claim_draw=False)`: checkmate, stalemate, insufficient material, automatic fivefold repetition, and automatic seventy-five-move rule. Simulator limits are truncations with a valid final state, not chess results.
6. **Deferred model option, not accepted as part of this M2 decision:** At the 2026-10-16 decision, an action-conditioned legal-candidate scorer `Q(s,a)` was a provisional M4/M5 architecture candidate. ADR-0003 later accepted that architecture on 2026-10-23; the fixed global move vocabulary remains deferred. Neither scoring architecture is required by M2, and ADR-0003 acceptance is not implementation or performance evidence.

The accepted M2 contract and its implementation verification requirements are detailed in [MDP_SPEC.md](../../03-technical/MDP_SPEC.md). M2 defines stable move semantics only; neural heads, candidate batching, replay, target networks, and Double DQN targets belong to later authorized milestones.

## Alternatives considered

- **Position-specific legal-list index:** rejected as a persistent action identity because list order and length change by position. A local list position may be used internally only while paired with its semantic move.
- **Fixed global move vocabulary:** viable for a later fixed-output model, but introduces many position-invalid outputs and is not needed by the M2 simulator.
- **Action-conditioned legal-move scoring:** the preferred future proposal at the time of the 2026-10-16 decision because it evaluated only legal semantic moves and mapped naturally to played PGN moves and teacher candidates. ADR-0003 later accepted its interface; computational and learning performance remain unvalidated.
- **Changing player perspective every ply:** not selected for the initial single-agent Double DQN formulation because it requires sign-changing returns or a separate zero-sum target design.
- **Opponent move as an agent action:** rejected for the single-agent contract because it would make the agent select the opponent's move.

## Consequences and validation

- M2 uses the Board and its history for simulated transitions; the M1 shadow advances only after real ALE RGB evidence.
- Traces and future data can refer to moves by UCI without relying on candidate ordering. Promotion, castling, and en passant use standard `python-chess` Move semantics.
- The opponent policy defines part of the transition distribution; simulator benchmarks identify its policy, configuration, seed, and color.
- Any future model observation that omits history relevant to automatic repetition outcomes may be partially observable. Validate this boundary before M5; the later ADR-0003 interface carries full history, but its implementation remains unverified.
- Confirm automatic outcome behavior against the locked python-chess version during M2. Keep those simulator results separate from Atari terminal/reward evidence.

## Acceptance and implementation boundary

The project user explicitly delegated technical approval responsibility on 2026-10-16. Following independent review, the M2 foundational choices in items 1–5 above are accepted: stable UCI move identity, one authoritative Board/history state, distinct observations, fixed agent color, agent-move/opponent-reply transitions, terminal-only agent-perspective rewards, automatic outcomes, and explicit truncation. Their correctness must still be established by actual M2 implementation tests and acceptance evidence. Model observation tensorization and the preferred neural action-scoring architecture remain open for M4/M5.

ADR acceptance is not an M2-01–M2-04 acceptance result. M2 implementation must follow the repository's separately recorded task authorization and canonical checkpoint workflow; the 2026-10-16 decision did not itself mark M2 started or modify G3 gate approval. ADR-0003 later accepted the M4/M5 interface and the project owner closed O-01 for internal M4-001 execution on 2026-10-27; neither decision claims external instructor approval. No permission is granted here for paid compute or scope beyond the separately recorded authorizations.

## References

- [M2 MDP specification](../../03-technical/MDP_SPEC.md)
- [M2 implementation plan](../../../.agents/plans/M02-chess-foundation.md)
- [Project requirements and future model proposals](../../01-foundation/REQUIREMENTS.md)
- [M2 acceptance criteria](../../06-quality/ACCEPTANCE_CRITERIA.md)
