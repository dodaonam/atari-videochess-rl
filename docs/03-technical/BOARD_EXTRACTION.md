# Atari Board Extraction and Validation

**Status:** M1 RGB extraction, cursor observation and shadow validation are implemented and covered by synthetic unit tests plus real-ALE evidence cited below. This document distinguishes pixel evidence from chess-state inference.

**Purpose:** Specify the current RGB-to-board validation boundary for M1 and the state M6 may consume after explicit implementation.

## Input contract and calibrated geometry

[VideoChessVision.observe()](../../videochess_rl/vision.py) requires a NumPy RGB array of shape (210, 160, 3) and dtype uint8. It examines the board region with:

- left x coordinate 44, top y coordinate 36;
- square width 8 pixels, square height 17 pixels;
- board columns a–h from left to right and ranks 8–1 from top to bottom;
- gold piece color (180, 122, 48), associated with Black;
- blue piece color (132, 144, 252), associated with White.

Thus square a8 begins at screen coordinate (44,36); square h1 occupies the final board cell. These values are calibrated M1 constants, not a general Atari screen detector.

For each square the parser counts pixels exactly equal to the gold and blue RGB values. It does not use a learned classifier or infer full piece identity directly from the image.

## Occupancy, cursor and piece identity

A single observation classifies a square as black if it contains gold pixels, white if it contains blue pixels, empty if neither is present, cursor if exactly 19 gold pixels match the cursor glyph, and unknown if both piece colors appear. The cursor glyph can obscure underlying occupancy.

The optional piece-kind heuristic maps sprite counts 8 to pawn, 20 to bishop, 25 to knight, 28 to queen, and 26 to rook_or_king. It intentionally does not distinguish a rook from a king at count 26. Board matching uses side/occupancy, not a claim that every piece identity was read from RGB. Piece identity and move identity are constrained by legal transition reasoning from the previously verified python-chess position.

The start-position check additionally compares known major-piece sprite counts and pawn counts at the expected start squares. This validates the calibrated initial layout; it does not establish a general piece classifier for animations or every position.

## Temporal windows and transient states

VideoChessVision.window() combines RGB observations into a BoardWindow:

- a square is stable as a color when the color is observed in at least three samples and at least 15% of the supplied window;
- an empty square requires at least two empty samples;
- conflicting visible colors remain unknown;
- cursor-only pixels may mark a square as masked-only;
- more than one detected cursor square makes the window unstable.

The episode runner usually observes a 33-frame window under frameskip 1, and uses a 66-frame window when frameskip is greater than 1. These are observation windows chosen by the M1 controller, not extra independent measurements at zero cost: collecting them advances ALE.

Source selection has a phase-specific RGB signature. After a one-frame source FIRE press and release, the selected piece must blink at the source (at least two visible and two absent samples), the cursor must be absent, and the remaining board must match the last verified state except for cursor masking.

Selected-target preview is a different signature: the selected piece’s color is visible both at its source and at the intended target, unrelated squares continue to match the previous board, and any cursor is at the source. Each target navigation step is checked before another direction or target FIRE is issued.

## Board reconstruction and legal-transition inference

The vision layer observes color/occupancy evidence; the M1 shadow board supplies a chess-rule hypothesis. Given a verified prior Board, a requested player Move, or candidate Atari reply:

1. Construct the expected legal python-chess transition without mutating the authoritative shadow.
2. Compare the candidate board’s side/empty occupancy with stable RGB evidence.
3. For an Atari reply, enumerate legal one-move successors and retain only candidates compatible with observed occupancy. No match is desynchronization; more than one match is ambiguous.
4. A partially masked reply window can stage a candidate but cannot by itself advance the shadow.
5. Obtain stable RGB evidence with the cursor in another square. BoardEvidenceSet checks every board square across the windows, requiring known evidence for every expected occupancy.
6. Apply the player move and Atari reply atomically only after the complete evidence set matches. A mismatch leaves the previous shadow unchanged.

The lower-level [ShadowBoard](../../videochess_rl/shadow.py) exposes candidate inference and atomic observed-sequence application. The episode runner uses these methods and records the candidate, windows, cursor positions and resulting FEN. M1’s tests explicitly verify that an ambiguous or cursor-masked board cannot advance the shadow.

## Desynchronization and safe behavior

Unknown or contradictory pixels are not repaired by copying the shadow into the observation. The runner waits only within configured bounded windows, records ambiguity and stops before an unsafe retry. Source FIRE is not repeated if selection is uncertain. Direction or target FIRE is not blindly repeated when the prior action may have succeeded. The last verified board is retained in the trace, and ALE terminal events are captured even when they occur during a control phase.

A move can be legal in python-chess yet fail to be accepted by Atari. Conversely, a temporary animation can obscure a valid transition. The parser’s observations are therefore evidence about visible occupancy, not a guarantee about game-internal state. M6 must preserve the explicit uncertain/desynchronized outcome.

## What M1 established

- Real RGB shape/type, board geometry, color signatures, start layout and cursor were observed.
- Source selection and selected-target preview were detected from RGB in controlled inputs.
- Player and Atari moves were cross-checked against legal python-chess transitions with full board occupancy evidence.
- The shadow advances only after complete RGB-supported transitions.
- The two terminal campaign replays returned genuine ALE terminal flags and reward, but their final transition screens cleared the chessboard. The final game board was not extracted from RGB; the trace retains the last independently verified pre-terminal FEN. A possible mate from a candidate after an unconfirmed input remains a chess-rule inference, not a verified Atari board.

M1 does not establish that RGB identifies every piece type independently, nor that castling, en passant, promotion, every capture animation or all Atari terminal screens are parseable. Synthetic RGB fixtures test parser branches but are not runtime evidence.

## M6 observation boundary

A future inference adapter may receive a validated chess position, its history/perspective metadata and legal candidates only after the current ALE RGB has been parsed and cross-checked. It must receive uncertainty explicitly and stop if no unique valid state is available. Model scores and simulator boards cannot be used to claim that an Atari action was accepted.

## References

- [vision.py](../../videochess_rl/vision.py), [shadow.py](../../videochess_rl/shadow.py), [episode.py](../../videochess_rl/episode.py)
- [Vision tests](../../tests/test_m1_vision.py), [shadow tests](../../tests/test_m1_shadow.py), [episode tests](../../tests/test_m1_episode.py)
- [M1 reproduction guide](../05-operations/M1-ALE-REPRODUCIBILITY.md)
- [M1/G2 final evidence](../../.agents/evidence/M1-G2-final-verification-20261016.md)
