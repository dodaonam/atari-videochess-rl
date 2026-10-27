# ADR-0003: Pretraining Model and State/Action Interface

- **Status:** Accepted.
- **Proposed:** 2026-10-22.
- **Accepted:** 2026-10-23.
- **Decision authority:** Project owner, by direct instruction in the 2026-10-23 Pre-M4 closure mission; see [ADR-0003 acceptance evidence](../../../.agents/evidence/ADR-0003-acceptance-20261023.md).
- **Scope:** M4 behavior-cloning input/output recommendation and its intended M5 Double DQN interface. This ADR does not approve G3, start M4/M5, authorize training/data acquisition/Stockfish use/compute allocation, or define Atari perception.
- **Evidence:** [M2 accepted action/perspective contract](ADR-0002-chess-mdp-action-and-perspective.md); [M3 accepted release evidence](../../../.agents/evidence/M3-acceptance-20261021.md); [verified local M3 release](../../../.agents/evidence/M3-release-local-verification-20261023.md); [model specification](../../03-technical/MODEL_DESIGN.md); [Pre-M4 closure record](../../../.agents/evidence/PRE-M4-final-closure-20261023.md).

## Context

M3 provides 19,268 retained PGN positions and one played UCI move per position, with game-grouped train/validation/test splits. M2 owns simulator rules and history, and represents legal moves semantically as UCI rather than fixed action indices. M2's FEN serializer retains raw en-passant targets; M3 canonical identity includes only legally available targets. FEN alone omits repetition history. M5 must evaluate the same semantic action it selects over the legal next-action set.

M4 should be small enough for a laptop CPU and support the project's Double DQN objective. A behavior-cloning score cannot be treated as a Q-value, reward, or measured playing strength.

## Accepted decision

Use a shared state encoder plus action-conditioned legal-candidate scorer:

1. At the model boundary, serialize positions with legal-en-passant semantics while leaving accepted M2/M3 serializers unchanged.
2. Encode a mover-oriented 13-plane 8×8 board, six explicit state scalars, the full prior UCI move sequence from standard start, and each legal candidate's canonical squares, promotion and move flags.
3. Sort current candidates by UCI for deterministic batching. Retain the original UCI key with every score; list offsets are never persistent action IDs.
4. Train M4 with cross-entropy against only the M3 played PGN move. Produce a finite, uncalibrated preference logit per candidate; do not mix the limited M3 teacher subset into this initial run.
5. In M5, reuse the board/history/state/candidate encoder and hidden scorer, reinitialize the scalar output as a Q head, and apply Double DQN selection and target evaluation over the same legal UCI candidates. Do not copy behavior probabilities as Q-values.
6. Keep the first network below 250,000 parameters. The approximately 121,897-parameter figure is a design estimate, not a measured implementation result. CPU-only initial budgets are defined in `TRAINING_PROTOCOL.md`.

The complete input tensors, exact fields, history assumptions, loss/masks, checkpoint content, complexity, limitations, and M5 tests are specified in `MODEL_DESIGN.md`. Training controls and budgets are specified in `TRAINING_PROTOCOL.md`.

## Alternatives considered

- **Fixed global move vocabulary:** deferred because it introduces many illegal output slots and a persistent index mapping that the M2 contract avoids.
- **Board-only encoder:** rejected for this recommendation because identical FENs can have different repetition history in the M2 rules state. The proposed input contains the complete move sequence, although its learned recurrent representation is still an approximation.
- **Large residual or transformer model:** deferred because the train split is 15,196 positions and the initial resource target is laptop CPU.
- **Immediate Q-head reuse:** rejected. M4 behavior logits are relative within a candidate set and have no return scale; M5 must initialize a distinct Q output head.
- **Teacher-score supervision:** excluded from the initial behavior-only run; the 128-position Stockfish sidecar is limited and further M4 use needs separate owner direction.

## Consequences and required implementation checks

- M2 observations and M3 records remain unchanged; only the model-input adapter canonicalizes FEN and creates tensors.
- M4's mainline dataset is PGN behavior, not teacher optimality, RL, or Atari data.
- The M2 episode boundary must ensure `side_to_move == agent_color` when the single-agent policy is queried.
- Version 1 assumes standard-start games. Any M5 custom initial position needs an explicit root-state feature or must be rejected by the adapter.
- M5 must test legal masking, terminal empty sets, truncation/bootstrap, reward perspective, same-UCI target evaluation, and transfer with a reinitialized Q head before learning.
- M6 must source current board occupancy from actual ALE RGB and history only from verified moves. This ADR does not resolve special-move controllability or ROM/runtime questions.
- M3 artifacts are not included in this Git checkout. The exact owner-specified local release was independently reverified read-only during Pre-M4 on 2026-10-27; reverify it before any future use. That check does not mean an M4 neural loader has consumed the data.

## Acceptance and authorization boundary

The project owner accepted this architecture on 2026-10-23. Acceptance records a design decision; it does not by itself prove training performance or approve G3. On 2026-10-27, the owner closed O-01 for internal project execution and authorized M4-001; see the dated supersession addendum in `.agents/evidence/M4-001-authorization-conditional-20261023.md` and the direct execution record. M4-001 passed M4-01 through M4-04 technical acceptance, and PR #8 is merged at `c0a284304d602817922772d08f0ff7904af7ae20`; clean-clone post-merge verification passed (see the M4 acceptance and delivery reports). External instructor-policy approval has not been evidenced and is not claimed. G3 is not approved, and this M4 work does not authorize M5.
