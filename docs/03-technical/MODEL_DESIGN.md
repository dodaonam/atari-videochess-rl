# Accepted M4 Model Design and M5 Interface

**Status:** Accepted M4/M5 architecture under [ADR-0003](../02-management/decisions/ADR-0003-pretraining-model-interface.md). M4-001 is directly authorized and ready to start under the dated owner decision; the task remains pending and no M4 implementation or training has started. Acceptance fixes the interface but does not prove tensor parity, a measured parameter count, or performance. Instructor-policy approval has not been evidenced and is not claimed.

**Purpose:** Define a deterministic input/action boundary from M3 PGN positions and M2 simulator decisions, while keeping M4 behavior logits separate from M5 Double DQN values.

## 1. Decision summary

Use a small action-conditioned network. It encodes the current chess board, the complete move history from the standard initial position, a few exact rule-state scalars, and each currently legal move. A shared state representation is scored once per legal candidate. The candidate's UCI string remains its semantic identity; candidate array offsets are temporary batch layout only.

This design fits the 19,268 retained M3 examples and CPU execution better than a large fixed output vocabulary or a large board-only network. It also exposes an input path that M5 can use for state-action values. The approximately 121,897 parameters stated in ADR-0003 remain a design estimate until measured on an implementation. Acceptance is not evidence that this architecture is optimal.

## 2. Model boundary and canonicalization

M2 and M3 preserve different FEN conventions for valid reasons:

- M2 `Observation.fen` uses `Board.fen(en_passant="fen")`, retaining the raw target square after a double pawn push.
- M3 `canonical_fen` uses `Board.fen(en_passant="legal")`, retaining that square only if at least one legal en-passant capture exists.

The M4 boundary follows the M3 legal-target convention through `canonical_model_fen(board)` for comparison and serialization checks; FEN is not passed as a model feature. Tensor features are built directly from the authoritative Board reconstructed from full history. This does not rewrite M2 observations, accepted M3 records, release identities, or split signatures. Castling rights and both move counters remain in the audit FEN; tensors encode castling rights and the halfmove clock explicitly, while fullmove number is recoverable from complete history and is not a separate model feature. A legal en-passant target is also represented as one board plane and candidate flags are derived from the authoritative Board.

The helper is implemented in [`videochess_rl/action_contract.py`](../../videochess_rl/action_contract.py) and tested against the current simulator and M3 FEN contract. FEN is a position serialization, not a complete game state: it does not preserve repetition history.

## 3. Input schema: `videochess-model-input/1.0`

For a batch of `B` positions and `T` preceding plies:

| Field | Shape and type | Definition |
|---|---|---|
| `board_planes` | `[B, 13, 8, 8]`, float32/binary | Channels 0–5 are the current side's pawns, knights, bishops, rooks, queens, kings; 6–11 are the opponent's same piece order; channel 12 marks a legally available en-passant target square. Each piece plane is binary. |
| `state_scalars` | `[B, 6]`, float32 | In order: `side_to_move_is_white` (0/1); own kingside right; own queenside right; opponent kingside right; opponent queenside right (all 0/1); then `min(halfmove_clock, 150) / 150`. |
| `history_moves` | `[B, T, 4]`, integer IDs | One token per prior main-line ply from the game's standard initial board: absolute python-chess origin square 0–63; destination square 0–63; promotion ID (0 none, 1 knight, 2 bishop, 3 rook, 4 queen); mover color (0 Black, 1 White). The target move is excluded. `T=0` is a valid empty history. |
| `history_mask` | `[B, T]`, bool | True for actual history tokens and false for batch padding. Full history is retained; do not truncate to a fixed recent window. |
| `candidate_squares` | `[B, N, 2]`, integer IDs | Candidate origin and destination, each 0–63, after rank flip for Black-to-move (`square ^ 56`). |
| `candidate_promotion` | `[B, N]`, integer IDs | 0 none, 1 knight, 2 bishop, 3 rook, 4 queen. |
| `candidate_flags` | `[B, N, 4]`, float32/binary | In order: capture, castling, en passant, gives check. Derived from the current authoritative `python-chess.Board`. |
| `candidate_mask` | `[B, N]`, bool | True only for a real legal candidate. Padded entries never participate in loss, argmax, or a Q target. |
| `candidate_uci` | one ordered UCI list per row | Original-orientation UCI keys, sorted lexically. This list maps each score back to a legal `python-chess.Move`; it is not a fixed action vocabulary. |

Board planes and candidate squares use mover-oriented rank coordinates: White-to-move retains rank order and Black-to-move flips ranks while preserving files. This keeps the mover's home rank at the bottom and leaves kingside/queenside semantics stable. The explicit color scalar is retained because history tokens use absolute board coordinates.

The model is queried only when a chess move is to be selected. In the accepted M2 single-agent step contract, `side_to_move == agent_color` at each agent decision; the adapter must assert this equality. `agent_color` is therefore not a second model input. If a later caller scores opponent moves or changes the transition boundary, it needs a new input contract.

### History and root assumptions

M3 accepted game records start from `chess.STARTING_FEN`; normal M2 episodes also start there. Their complete UCI move prefixes reconstruct castling rights, clocks, legal moves, and repetition-sensitive Board history. M2's `history_uci` provides the sequence to an inference adapter. In M6, the sequence may be extended only with moves validated from actual ALE RGB; a missed or uncertain move stops inference.

Version 1 rejects nonstandard roots. The existing `Observation` does not expose a separate root FEN for arbitrary `initial_board` episodes. Before using this model with such an episode, M5 must either supply and test a root-position feature or explicitly constrain that evaluation to standard-start games. FEN alone must never be used as a substitute for history.

For M2 inference, rebuild the Board from standard start and `Observation.history_uci`; verify its legal UCI set against `Observation.legal_moves_uci` and its legal-target FEN against the observation's raw-EP FEN. Assert `side_to_move == agent_color` before scoring. For M3, rebuild from the game's initial FEN and move prefix, then compare against the stored row. Neither path uses the FEN alone as complete rules state.

The neural caller also receives terminal status from `Board.outcome(claim_draw=False)` and the current legal set from the same Board. Check, automatic terminal outcome, and an empty legal set are rules-layer facts; they are not inferred from model scores. A terminal state has `N=0` and no action is scored. M4 behavior examples are nonterminal played positions. M3 result fields and M2 reward are not model inputs or behavior targets; M2 terminal reward remains from the fixed agent's perspective.

## 4. Candidate identity and legality

`legal_action_candidates(board)` returns the complete legal set in stable UCI order. UCI includes promotion suffixes, and the action fields distinguish each promotion. Castling uses ordinary UCI king moves; en passant is identified from the Board and remains a capture; check flags are computed by the Board. An illegal move never enters the candidate tensor.

The target is an exact UCI move copied from M3 `played_move_uci`. At collation time only, the target UCI is resolved to its index in that row's candidate list. The loader fails if the target is absent or duplicated. M3 `played_candidate_id` remains an audit identity; the temporary row index is not stored as an action label.

Batching pads the variable candidate count `N` and history length `T`. Loss and selection apply `candidate_mask`; checkmate, stalemate, fivefold repetition, and the seventy-five-move automatic draw have `N=0` and are handled by the caller, never reduced with `max()` over an empty tensor. `legal_action_candidates()` checks `Board.outcome(claim_draw=False)` before enumerating moves, because an automatic draw can be terminal while legal moves remain on the board. The raw candidate scorer should return finite scores; padding is excluded by the mask rather than by assigning an infinite model output.

## 5. Accepted network specification and output

Recommended small implementation:

1. Board encoder: `Conv2d(13,32,3,padding=1)` + ReLU; `Conv2d(32,64,3,padding=1)` + ReLU. Preserve the spatial output `[B,64,8,8]`; concatenate global average and max pools to `[B,128]`, then `Linear(128,128)` + ReLU to get the state vector. The spatial feature map remains available for each candidate's origin and destination squares.
2. History encoder: factorized embeddings for origin (64×16), destination (64×16), promotion (5×8), and mover color (2×4); concatenate to 44 dimensions, project to 64, and run a one-layer GRU with hidden size 64 over the full masked sequence. Output `[B,64]`. Rows with no prior moves use a zero vector; nonempty rows use packed sequences so padding cannot change the final hidden state. With absolute history tokens, the recurrent state can be extended one validated move at a time without changing prior token encodings.
3. State metadata projection: `Linear(6,16)` + ReLU. Output `[B,16]`.
4. Candidate encoder: gather the board feature at each candidate's mover-oriented origin and destination squares and concatenate to 128 local board features; project to 64 with ReLU. Separately concatenate origin/destination embeddings (64×16 each), promotion embedding (5×8), and four binary flags (44 total); project to 32 with ReLU. Concatenate those two candidate vectors and project `Linear(96,64)` + ReLU. Output `[B,N,64]`.
5. Shared scorer: concatenate the 128 pooled board, 64 history, 16 scalar, and 64 candidate features; apply `Linear(272,128)` + ReLU, then one scalar output layer per candidate.

With the listed biases enabled, this design has an estimated 121,897 trainable parameters: board encoder 38,784; history encoder 29,936; state metadata 112; candidate embeddings/projections 17,992; shared scorer and logit head 35,073. M4 tests must assert the implemented count against the chosen module configuration. Set a 250,000-parameter hard cap for the initial model. Expected work per decision includes authoritative Board reconstruction/history checks, terminal-outcome and legal-move enumeration, one board-encoder pass and one history-encoder pass, then an independent small scoring pass per legal candidate. The neural portion is `O(8×8 board encoding + T history tokens + N candidate scores)`; actual feature-building and inference latency must be measured. At most the supplied legal candidates are scored; no fixed global move table or Stockfish call is involved. M5 can cache the absolute-history GRU state while appending verified plies, then score the next legal candidate list.

M4 returns `policy_logits [B,N]`: each scalar is an uncalibrated preference within that position's supplied legal set. Softmax is applied only over valid candidates when computing behavior probabilities. These logits are not a value estimate, reward, teacher centipawn score, or Q-value.

## 6. M4 objective and checkpoint contract

Train behavior cloning with one target move per PGN position and cross-entropy over that row's legal candidate logits. A target mismatch, empty candidate list, data identity failure, or nonfinite loss is a hard data/run error. Do not add a ranking/teacher loss to this first baseline.

Checkpoint bundle metadata must include:

- format/schema identifier, model/input version, constructor configuration and parameter count;
- state dict and training code revision;
- accepted dataset release ID, release-manifest SHA-256, split-manifest identity, and train/validation/test record counts;
- label semantics (`played_move_uci` behavior target), excluded teacher fields, and feature/normalization rules;
- seed, optimizer state, epoch/selected epoch, Python and PyTorch RNG state, optimizer config and early-stop state;
- Python, PyTorch and `python-chess` versions, platform/hardware, command, run ID, measured memory/time/throughput, metrics and artifact checksums.

Do not place PGN records, source archives, Stockfish binaries, or credentials inside the model bundle. Loading a model for action selection must work with Stockfish absent.

## 7. M4 to M5 Double DQN transfer

M5 may reuse the board convolution stack, history move embeddings and GRU, metadata projection, candidate embeddings and candidate hidden scorer. Replace and reinitialize the final `Linear(128,1)` layer as a Q head, then initialize/synchronize the target network from the resulting Q network. The default path does not copy M4 policy probabilities or interpret the M4 scalar as Q.

At an M5 decision, supply the same state/history/candidate features and compute a scalar `Q(s,a)` for each current legal UCI action. Action selection masks all nonlegal/padded moves and maps `argmax` back to UCI. For Double DQN, the online network selects `argmax` over the next state's legal UCI candidates; the target network evaluates that same semantic UCI action. A chess terminal has no bootstrap term. The proposed M5 rule for an M2 time-limit truncation with a valid final observation is to bootstrap from that final state and its legal candidates; an external interruption or invalid final observation discards the incomplete transition rather than inventing a terminal result. M5 must implement and test this rule before training.

The paired M5 experiment compares this transferred initialization with the same Q architecture randomly initialized. It holds M5 transition/update budget, replay, target schedule, exploration, opponents, colors, seeds, and evaluation settings constant where feasible; reports pretraining compute separately; and does not call the warm-start checkpoint a trained DDQN agent.

## 8. Alternatives and limits

- **Fixed global move vocabulary:** deferred. It produces many position-illegal logits and adds an unnecessary persistent action-index contract.
- **Board-only CNN without history:** rejected for this initial shared interface because the simulator preserves repetition history and FEN cannot reconstruct it. A history-aware recurrent input is still a learned compression and is not a proof of perfect chess strength.
- **Large residual/transformer model:** deferred because M3 provides only 15,196 train examples and the initial compute target is laptop CPU.
- **Teacher-score head or mixed supervision:** excluded from the first M4 run. The sidecar covers only 128 positions, is not the PGN move label, and broader Stockfish use requires separate authorization.
- **Custom Atari image encoder:** excluded. M4 receives symbolic chess state; M6 must derive state from verified ALE RGB using the existing observation pipeline.

Known limits: one 1,000-game source package; possible PGN selection bias; limited history examples; full-history sequence length and recurrent numerical behavior require implementation tests. The accepted M3 artifacts remain outside Git; the exact owner-specified local release was independently reverified read-only during Pre-M4 and must be reverified before future use. No M4 neural loader has consumed it. Simulator legal state does not establish that every move is representable in Atari. The parameter count remains a design estimate; no model performance or inference latency has been measured.
