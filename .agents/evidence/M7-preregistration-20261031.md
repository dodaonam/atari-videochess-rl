# M7 Option B Preregistration

**Status:** Frozen before the first official M7 ALE attempt.
**Owner authorization:** `M7-AUTH-20261031-OPTION-B`; see [direct authorization record](M7-001-authorization-20261031.md) and [ADR-0004](../../docs/02-management/decisions/ADR-0004-m7-option-b-execution-authorization.md).
**Scientific basis:** `M7-EVAL/1.0.0`.
**Versioned execution configuration:** [`configs/m7/m7-option-b-1.0.0.json`](../../configs/m7/m7-option-b-1.0.0.json).
**Configuration SHA-256:** `8ec8a42a808f4ffc410c938b4400d02461f96823eb5ac1b16cbd6e0d5e35f255`.
**Schedule SHA-256:** `c479e65f944224ffbc584e15f43086e881e9df1a10c009c478be8ce5119e67d9`.

## Frozen population and schedule

The schedule contains exactly 90 policy × ALE-seed cells: six accepted M5 post-RL Double DQN checkpoints (Warm-start and Scratch at training seeds `20261104`, `20261105`, and `20261106`), accepted M4 r4 behavior-only, RandomLegal, and SimpleHeuristic. Each policy receives the shared ALE seeds `20261201` through `20261210`, exactly once each. The complete ordered roster, M5 run/checkpoint/sidecar identities, M4 checkpoint/metadata/sidecar identities, and machine-readable cell list are in the frozen JSON configuration.

For seed block `i`, the fixed nine-policy base order is offset by `(4*i) mod 9`; even blocks traverse forward and odd blocks backward. The resulting policy order and all 90 cells are included in the schedule hash. No M6 evaluation seed overlaps the new schedule. No policy or seed may be added, removed, substituted, or reordered after the first official attempt.

## Frozen environment and execution limits

- `ALE/VideoChess-v5`, accepted ROM SHA-256 `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`; White agent, mode 4, difficulty 0, RGB observations, frameskip 4, repeat-action probability 0.25.
- The accepted M6 v2 extended-horizon runtime profile: effective ALE horizon 500,000 frames and runner post-reset cap 432,000 frames. The registered default of 108,000 frames is recorded separately; this is not default-horizon evaluation. M6 v2's configuration and 20-cell campaign ceiling are not reused.
- Local CPU only, one ALE process at a time, 1,800 seconds maximum per attempt, 162,000 seconds (45 hours) maximum aggregate gameplay, 8 GiB campaign artifact ceiling, and at least 12 GiB free before the first attempt. Expected gameplay time is approximately 4.4 hours by extrapolation from the accepted M6 v2 mean; this is not guaranteed. No RSS stop ceiling was owner-authorized; peak RSS is measured and reported.
- One global process-start retry is permitted only before ALE reset/action. No post-reset, post-action, partial-game, or outcome-based replacement attempt is allowed. A partial run retains all 90 scheduled cells and classifies every cell by the frozen missingness rules.

## Frozen analysis and interpretation

Primary measures are per-policy terminal W/D/L and terminal-only game score with explicit denominators, schedule completion and missing categories, and RGB-verified initiated moves divided by all initiated player moves. Secondary measures include legal-action validation, verified Atari replies, desynchronization/cursor corrections, controller uncertainty/timeouts, latency, CPU, wall time, frames, RSS, artifact bytes, and resource stops.

White-perspective positive/negative finite ALE terminal rewards map to win/loss. A zero or nonfinite terminal reward is `terminal_unknown`; ALE truncation is `truncated`; runner stops, controller uncertainty, and other nonterminal outcomes are `incomplete`. Incomplete results are never draws. Terminal-only score is `(wins + 0.5 × draws) / known terminal games`, and is null when that denominator is zero. Schedule-level unresolved-score bounds make no imputation.

The frozen bootstrap uses 10,000 resamples and RNG seed `20261290`, resampling complete common ALE seed blocks and retaining the three M5 training-seed pairs as clusters. Paired confidence intervals are withheld when terminal pairing is censored or unknown. The three training-seed pairs are a severe inference limitation. M4 imitation, M5 simulator, M6 v1, M6 v2, and M7 ALE results remain separate evidence tracks. Elo is not reported because no calibrated opponent pool/design is approved or available.

## Inputs and integrity identities

The frozen config records M4 r4 root/checkpoint/metadata/sidecar hashes, the M5 root manifest and all six checkpoint/sidecar hashes, M6 v1 and v2 run/config/root-manifest identities, the ROM identity, runtime parameters, resource envelope, and privacy boundary. The final pre-run raw-input verification is recorded in [`M7-inputs-final-prereg-20261031.json`](M7-inputs-final-prereg-20261031.json) with execution metadata in its adjacent `.meta.json` file. It independently reconstructed both preserved M6 ledgers and verified M4/M5 accepted inputs without modifying them.

The immutable run ID binds the final committed source commit/tree/bundle, configuration SHA-256, and ordered schedule SHA-256. The exact preflight record and prospective run ID must be captured under the ignored local M7 artifact directory before any official attempt. The run manifest and first hash-chained ledger event must precede the first reset. The raw run directory, ROM, checkpoints, RGB traces, and other private artifacts remain owner-local and outside Git.

G4 remains HOLD / NOT APPROVED during Phase I. M7-001–003 are authorized by the owner; M7-004/005 remain gated on verified independent G4 approval. No model training/fine-tuning, extra simulator campaign, Stockfish evaluation/opponent, GPU/cloud use, private artifact transfer, release, or publication is in this preregistered scope.
