# M7 Option B Evaluation Analysis

Generated from raw records at `2026-10-31T20:07:10Z` using analysis source `fe2cc4cc5e477841ffbc9368235eb9c5675f2f74` (tree `94f37d775b5a62f09c2502fcfd8caf58622397bf`).

Protocol: `M7-Option-B/1.0.0`; scientific basis: `M7-EVAL/1.0.0`.
M7 run: `m7-option-b-20261031-v1-8387b289432f`; config SHA-256 `8ec8a42a808f4ffc410c938b4400d02461f96823eb5ac1b16cbd6e0d5e35f255`; schedule SHA-256 `c479e65f944224ffbc584e15f43086e881e9df1a10c009c478be8ce5119e67d9`.
Environment: `ALE/VideoChess-v5`, White, mode 4, difficulty 0, RGB, frameskip 4, sticky probability 0.25; seeds `[20261201, 20261202, 20261203, 20261204, 20261205, 20261206, 20261207, 20261208, 20261209, 20261210]`.
ALE registered horizon 108000 frames; M7 effective horizon 500000 frames; runner cap 432000 post-reset frames.
Raw M7 artifacts are owner-local under `artifacts/m7-option-b/m7-option-b-20261031-v1-8387b289432f`. They are not included in this report bundle.

## Evidence tracks

The five tracks below remain separate. M4 imitation accuracy is not game score; M5 simulator results are not ALE results; M6 v1 and v2 retain different configurations; cross-protocol M6/M7 differences are descriptive only.

### M4 supervised imitation

Accepted run `m4-behavior-20261027-r4`, seed `20261024`, epoch `11`, checkpoint SHA-256 `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4`.
Held-out test: 2057 positions; legal top-1 `0.298979`; legal top-3 `0.543996`. These are imitation metrics. The accepted root retains an aggregate evaluation record, not per-position predictions.

### M5 simulator Double DQN

The accepted raw evaluation was independently read as 1,500 rows (15 policy groups × 100 rows); terminal-only game score uses only known W/D/L outcomes.

### M5 policy outcomes

| Policy | Scheduled | Started | W / D / L | Unknown | Truncated | Incomplete | Not started | Terminal score (n) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `baseline:random_legal` | 100 | 100 | 3 / 58 / 39 | 0 | 0 | 0 | 0 | 0.320 (100) |
| `baseline:simple_heuristic` | 100 | 100 | 33 / 63 / 4 | 0 | 0 | 0 | 0 | 0.645 (100) |
| `m4_behavior_only` | 100 | 100 | 48 / 50 / 2 | 0 | 0 | 0 | 0 | 0.730 (100) |
| `scratch:20261104:post_rl` | 100 | 100 | 12 / 86 / 2 | 0 | 0 | 0 | 0 | 0.550 (100) |
| `scratch:20261104:pre_rl` | 100 | 100 | 0 / 64 / 35 | 0 | 1 | 0 | 0 | 0.323 (99) |
| `scratch:20261105:post_rl` | 100 | 100 | 3 / 91 / 6 | 0 | 0 | 0 | 0 | 0.485 (100) |
| `scratch:20261105:pre_rl` | 100 | 100 | 0 / 72 / 28 | 0 | 0 | 0 | 0 | 0.360 (100) |
| `scratch:20261106:post_rl` | 100 | 100 | 8 / 90 / 1 | 0 | 1 | 0 | 0 | 0.535 (99) |
| `scratch:20261106:pre_rl` | 100 | 100 | 0 / 66 / 33 | 0 | 1 | 0 | 0 | 0.333 (99) |
| `warm:20261104:post_rl` | 100 | 100 | 16 / 78 / 5 | 0 | 1 | 0 | 0 | 0.556 (99) |
| `warm:20261104:pre_rl` | 100 | 100 | 2 / 85 / 13 | 0 | 0 | 0 | 0 | 0.445 (100) |
| `warm:20261105:post_rl` | 100 | 100 | 19 / 79 / 2 | 0 | 0 | 0 | 0 | 0.585 (100) |
| `warm:20261105:pre_rl` | 100 | 100 | 3 / 39 / 56 | 0 | 2 | 0 | 0 | 0.230 (98) |
| `warm:20261106:post_rl` | 100 | 100 | 24 / 74 / 2 | 0 | 0 | 0 | 0 | 0.610 (100) |
| `warm:20261106:pre_rl` | 100 | 100 | 0 / 37 / 63 | 0 | 0 | 0 | 0 | 0.185 (100) |

#### Paired M5 comparisons

| Comparison | Matched terminal pairs | Censored pairs | Point difference | 95% interval |
|---|---:|---:|---:|---|
| `warm_pre_vs_post` | 297 | 3 | 0.296 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `scratch_pre_vs_post` | 297 | 3 | 0.185 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `warm_vs_scratch_pre_rl` | 296 | 4 | -0.056 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `warm_vs_scratch_post_rl` | 298 | 2 | 0.062 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `scratch:20261104:post_rl_minus_m4_behavior_only` | 100 | 0 | -0.180 | [-0.260, -0.100] |
| `scratch:20261104:post_rl_minus_random_legal` | 100 | 0 | 0.230 | [0.190, 0.270] |
| `scratch:20261104:post_rl_minus_simple_heuristic` | 100 | 0 | -0.095 | [-0.145, -0.045] |
| `scratch:20261104:pre_rl_minus_m4_behavior_only` | 99 | 1 | -0.409 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `scratch:20261104:pre_rl_minus_random_legal` | 99 | 1 | 0.000 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `scratch:20261104:pre_rl_minus_simple_heuristic` | 99 | 1 | -0.323 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `scratch:20261105:post_rl_minus_m4_behavior_only` | 100 | 0 | -0.245 | [-0.325, -0.170] |
| `scratch:20261105:post_rl_minus_random_legal` | 100 | 0 | 0.165 | [0.115, 0.210] |
| `scratch:20261105:post_rl_minus_simple_heuristic` | 100 | 0 | -0.160 | [-0.215, -0.110] |
| `scratch:20261105:pre_rl_minus_m4_behavior_only` | 100 | 0 | -0.370 | [-0.450, -0.290] |
| `scratch:20261105:pre_rl_minus_random_legal` | 100 | 0 | 0.040 | [-0.020, 0.100] |
| `scratch:20261105:pre_rl_minus_simple_heuristic` | 100 | 0 | -0.285 | [-0.335, -0.235] |
| `scratch:20261106:post_rl_minus_m4_behavior_only` | 99 | 1 | -0.192 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `scratch:20261106:post_rl_minus_random_legal` | 99 | 1 | 0.217 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `scratch:20261106:post_rl_minus_simple_heuristic` | 99 | 1 | -0.111 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `scratch:20261106:pre_rl_minus_m4_behavior_only` | 99 | 1 | -0.399 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `scratch:20261106:pre_rl_minus_random_legal` | 99 | 1 | 0.015 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `scratch:20261106:pre_rl_minus_simple_heuristic` | 99 | 1 | -0.308 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `warm:20261104:post_rl_minus_m4_behavior_only` | 99 | 1 | -0.172 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `warm:20261104:post_rl_minus_random_legal` | 99 | 1 | 0.237 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `warm:20261104:post_rl_minus_simple_heuristic` | 99 | 1 | -0.091 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `warm:20261104:pre_rl_minus_m4_behavior_only` | 100 | 0 | -0.285 | [-0.355, -0.215] |
| `warm:20261104:pre_rl_minus_random_legal` | 100 | 0 | 0.125 | [0.070, 0.175] |
| `warm:20261104:pre_rl_minus_simple_heuristic` | 100 | 0 | -0.200 | [-0.245, -0.160] |
| `warm:20261105:post_rl_minus_m4_behavior_only` | 100 | 0 | -0.145 | [-0.220, -0.070] |
| `warm:20261105:post_rl_minus_random_legal` | 100 | 0 | 0.265 | [0.205, 0.320] |
| `warm:20261105:post_rl_minus_simple_heuristic` | 100 | 0 | -0.060 | [-0.110, -0.015] |
| `warm:20261105:pre_rl_minus_m4_behavior_only` | 98 | 2 | -0.495 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `warm:20261105:pre_rl_minus_random_legal` | 98 | 2 | -0.082 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `warm:20261105:pre_rl_minus_simple_heuristic` | 98 | 2 | -0.418 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `warm:20261106:post_rl_minus_m4_behavior_only` | 100 | 0 | -0.120 | [-0.195, -0.045] |
| `warm:20261106:post_rl_minus_random_legal` | 100 | 0 | 0.290 | [0.235, 0.340] |
| `warm:20261106:post_rl_minus_simple_heuristic` | 100 | 0 | -0.035 | [-0.090, 0.015] |
| `warm:20261106:pre_rl_minus_m4_behavior_only` | 100 | 0 | -0.545 | [-0.630, -0.460] |
| `warm:20261106:pre_rl_minus_random_legal` | 100 | 0 | -0.135 | [-0.200, -0.080] |
| `warm:20261106:pre_rl_minus_simple_heuristic` | 100 | 0 | -0.460 | [-0.515, -0.400] |

M5 bootstrap intervals are withheld when a comparison contains censored pairs. The historical M5 provenance limitation RSK-014 remains in force.

### M6 Stage 3 v1 — `m6-stage3-ad3998200e31-c5ff389dc4fe`

Configuration SHA-256 `05aedeb30efb8b6b97667c44f9d606b58d4da8ae20800d4ef143e629420cebac`; root manifest `22ac6ec7e0f4a48f52b2452654d4adecaf111f38ea37f5d9517f173c838716d7`; 35 scheduled attempts.

### M6 v1 outcomes

| Policy | Scheduled | Started | W / D / L | Unknown | Truncated | Incomplete | Not started | Terminal score (n) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `m4-behavior-only-seed-20261024` | 5 | 5 | 0 / 0 / 0 | 0 | 0 | 5 | 0 | — (0) |
| `m5-scratch-seed-20261104-post-rl` | 10 | 10 | 0 / 0 / 0 | 0 | 0 | 10 | 0 | — (0) |
| `m5-warm-seed-20261104-post-rl` | 10 | 10 | 0 / 0 / 0 | 0 | 0 | 10 | 0 | — (0) |
| `random-legal` | 5 | 5 | 0 / 0 / 2 | 0 | 0 | 3 | 0 | 0.000 (2) |
| `simple-material-heuristic` | 5 | 5 | 0 / 0 / 1 | 0 | 0 | 4 | 0 | 0.000 (1) |

### M6 Stage 3 v2 — `m6-stage3-v2-91f51b14690e-d05d42400cfc`

Configuration SHA-256 `663651050db80ab027b452241c7d39837ec7986927c0aefc7c7be631f459a49b`; root manifest `bc0068aa2254e4c15165247ee299f48940cca9b7c21f6a288fd13812631ea2b2`; 20 scheduled attempts.

### M6 v2 outcomes

| Policy | Scheduled | Started | W / D / L | Unknown | Truncated | Incomplete | Not started | Terminal score (n) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `m5-scratch-seed-20261104-post-rl` | 10 | 10 | 0 / 0 / 7 | 0 | 0 | 3 | 0 | 0.000 (7) |
| `m5-warm-seed-20261104-post-rl` | 10 | 10 | 0 / 0 / 4 | 0 | 0 | 6 | 0 | 0.000 (4) |

M6 v2 raw reconstruction totals: 11 terminal losses; 9 incomplete; 0 wins, 0 draws, 0 terminal-unknown, 0 truncated; 385/405 initiated moves RGB-verified; 0 board desynchronizations. PM6-F06 remains an immutable metadata erratum.

### M7 Option B ALE — 90 scheduled cells

Run reconstruction: 90 attempt processes, 90 reset-observed cells; run resource stop: `none`.
Root artifact manifest SHA-256 `25a8b6bcfbf1d948bed886a0a4964cf48210fb1be12809c72bf122157b8d05e4`; run-manifest SHA-256 `93d941f5b1c4f876ea66c62d30f66b873b61e59acbacd25534d66920bbbb3431`.

### M7 policy outcomes

| Policy | Scheduled | Started | W / D / L | Unknown | Truncated | Incomplete | Not started | Terminal score (n) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `m4-behavior-only-seed-20261024` | 10 | 10 | 0 / 0 / 8 | 0 | 0 | 2 | 0 | 0.000 (8) |
| `m5-scratch-seed-20261104-post-rl` | 10 | 10 | 0 / 0 / 9 | 0 | 0 | 1 | 0 | 0.000 (9) |
| `m5-scratch-seed-20261105-post-rl` | 10 | 10 | 0 / 0 / 9 | 0 | 0 | 1 | 0 | 0.000 (9) |
| `m5-scratch-seed-20261106-post-rl` | 10 | 10 | 0 / 0 / 5 | 0 | 0 | 5 | 0 | 0.000 (5) |
| `m5-warm-seed-20261104-post-rl` | 10 | 10 | 0 / 0 / 4 | 0 | 0 | 6 | 0 | 0.000 (4) |
| `m5-warm-seed-20261105-post-rl` | 10 | 10 | 0 / 0 / 0 | 0 | 0 | 10 | 0 | — (0) |
| `m5-warm-seed-20261106-post-rl` | 10 | 10 | 0 / 0 / 9 | 0 | 0 | 1 | 0 | 0.000 (9) |
| `random-legal` | 10 | 10 | 0 / 0 / 6 | 0 | 0 | 4 | 0 | 0.000 (6) |
| `simple-heuristic` | 10 | 10 | 0 / 0 / 10 | 0 | 0 | 0 | 0 | 0.000 (10) |

| Policy | RGB-verified moves / initiated | Verified move rate | Legal selections valid / proposals | Desyncs | Cursor corrections | Median process wall s | Median machine CPU % |
|---|---:|---:|---:|---:|---:|---:|---:|
| `m4-behavior-only-seed-20261024` | 247 / 256 | 96.48% | 256 / 256 | 0 | 1122 | 127.455 | 8.047 |
| `m5-scratch-seed-20261104-post-rl` | 179 / 189 | 94.71% | 189 / 189 | 0 | 785 | 199.632 | 7.892 |
| `m5-scratch-seed-20261105-post-rl` | 155 / 165 | 93.94% | 165 / 165 | 0 | 551 | 85.363 | 8.080 |
| `m5-scratch-seed-20261106-post-rl` | 120 / 130 | 92.31% | 130 / 130 | 0 | 576 | 53.110 | 7.898 |
| `m5-warm-seed-20261104-post-rl` | 212 / 222 | 95.50% | 222 / 222 | 0 | 1098 | 126.124 | 7.577 |
| `m5-warm-seed-20261105-post-rl` | 122 / 132 | 92.42% | 132 / 132 | 0 | 599 | 70.396 | 8.038 |
| `m5-warm-seed-20261106-post-rl` | 257 / 267 | 96.25% | 267 / 267 | 0 | 1171 | 160.828 | 7.812 |
| `random-legal` | 141 / 151 | 93.38% | 151 / 151 | 0 | 670 | 115.524 | 7.953 |
| `simple-heuristic` | 148 / 158 | 93.67% | 158 / 158 | 0 | 653 | 84.837 | 7.878 |

| Policy | Input-validation latency median s | Choose-move latency median s | Adapter-total latency median s | Stop categories | Uncertainty categories |
|---|---:|---:|---:|---|---|
| `m4-behavior-only-seed-20261024` | 0.005 | 0.003 | 0.009 | `{"ALE_TERMINATED": 8, "OPPONENT_RESPONSE_TIMEOUT": 1, "POLICY_INPUT_INVALID": 1}` | `{"ale_terminal": 8, "opponent_response_timeout": 1}` |
| `m5-scratch-seed-20261104-post-rl` | 0.005 | 0.003 | 0.008 | `{"ALE_TERMINATED": 9, "CONTROLLER_TARGET_NAVIGATION_UNCERTAIN": 1}` | `{"ale_terminal": 9, "target_navigation_uncertainty": 1}` |
| `m5-scratch-seed-20261105-post-rl` | 0.005 | 0.003 | 0.008 | `{"ALE_TERMINATED": 9, "CONTROLLER_SOURCE_SELECTION_UNCERTAIN": 1}` | `{"ale_terminal": 9, "source_selection_uncertainty": 1}` |
| `m5-scratch-seed-20261106-post-rl` | 0.005 | 0.002 | 0.007 | `{"ALE_TERMINATED": 5, "CONTROLLER_TARGET_NAVIGATION_UNCERTAIN": 5}` | `{"ale_terminal": 5, "target_navigation_uncertainty": 5}` |
| `m5-warm-seed-20261104-post-rl` | 0.005 | 0.003 | 0.008 | `{"ALE_TERMINATED": 4, "CONTROLLER_SOURCE_SELECTION_UNCERTAIN": 2, "OPPONENT_RESPONSE_TIMEOUT": 3, "UNKNOWN": 1}` | `{"ale_terminal": 4, "opponent_response_timeout": 3, "other_interrupted_or_unknown": 1, "source_selection_uncertainty": 2}` |
| `m5-warm-seed-20261105-post-rl` | 0.004 | 0.002 | 0.007 | `{"CONTROLLER_TARGET_NAVIGATION_UNCERTAIN": 9, "UNKNOWN": 1}` | `{"other_interrupted_or_unknown": 1, "target_navigation_uncertainty": 9}` |
| `m5-warm-seed-20261106-post-rl` | 0.005 | 0.003 | 0.009 | `{"ALE_TERMINATED": 9, "CONTROLLER_SOURCE_SELECTION_UNCERTAIN": 1}` | `{"ale_terminal": 9, "source_selection_uncertainty": 1}` |
| `random-legal` | 0.005 | 0.000 | 0.005 | `{"ALE_TERMINATED": 6, "CONTROLLER_TARGET_NAVIGATION_UNCERTAIN": 1, "OPPONENT_RESPONSE_TIMEOUT": 3}` | `{"ale_terminal": 6, "opponent_response_timeout": 3, "target_navigation_uncertainty": 1}` |
| `simple-heuristic` | 0.005 | 0.001 | 0.006 | `{"ALE_TERMINATED": 10}` | `{"ale_terminal": 10}` |

#### Paired M7 comparisons

Warm-start minus Scratch post-RL: 9/30 matched terminal training-seed × ALE-seed cells; 21 censored/unknown; point difference `0.000`; 95% interval unavailable (unavailable_incomplete_or_censored_pair_set).

| RL policy vs baseline | Training seed | Matched blocks | Censored/unknown | Point difference | 95% interval |
|---|---:|---:|---:|---:|---|
| `m5-scratch-seed-20261104-post-rl_minus_m4-behavior-only-seed-20261024` | 20261104 | 8 | 2 | 0.000 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `m5-scratch-seed-20261104-post-rl_minus_random-legal` | 20261104 | 5 | 5 | 0.000 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `m5-scratch-seed-20261104-post-rl_minus_simple-heuristic` | 20261104 | 9 | 1 | 0.000 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `m5-scratch-seed-20261105-post-rl_minus_m4-behavior-only-seed-20261024` | 20261105 | 7 | 3 | 0.000 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `m5-scratch-seed-20261105-post-rl_minus_random-legal` | 20261105 | 5 | 5 | 0.000 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `m5-scratch-seed-20261105-post-rl_minus_simple-heuristic` | 20261105 | 9 | 1 | 0.000 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `m5-scratch-seed-20261106-post-rl_minus_m4-behavior-only-seed-20261024` | 20261106 | 3 | 7 | 0.000 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `m5-scratch-seed-20261106-post-rl_minus_random-legal` | 20261106 | 4 | 6 | 0.000 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `m5-scratch-seed-20261106-post-rl_minus_simple-heuristic` | 20261106 | 5 | 5 | 0.000 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `m5-warm-seed-20261104-post-rl_minus_m4-behavior-only-seed-20261024` | 20261104 | 4 | 6 | 0.000 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `m5-warm-seed-20261104-post-rl_minus_random-legal` | 20261104 | 3 | 7 | 0.000 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `m5-warm-seed-20261104-post-rl_minus_simple-heuristic` | 20261104 | 4 | 6 | 0.000 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `m5-warm-seed-20261105-post-rl_minus_m4-behavior-only-seed-20261024` | 20261105 | 0 | 10 | — | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `m5-warm-seed-20261105-post-rl_minus_random-legal` | 20261105 | 0 | 10 | — | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `m5-warm-seed-20261105-post-rl_minus_simple-heuristic` | 20261105 | 0 | 10 | — | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `m5-warm-seed-20261106-post-rl_minus_m4-behavior-only-seed-20261024` | 20261106 | 7 | 3 | 0.000 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `m5-warm-seed-20261106-post-rl_minus_random-legal` | 20261106 | 6 | 4 | 0.000 | unavailable (unavailable_incomplete_or_censored_pair_set) |
| `m5-warm-seed-20261106-post-rl_minus_simple-heuristic` | 20261106 | 9 | 1 | 0.000 | unavailable (unavailable_incomplete_or_censored_pair_set) |

#### Shadow-terminal policy-input stops

These stops came from the frozen adapter validating the replayed python-chess history. They remain incomplete because ALE had not emitted a terminal flag; they are not ALE draws or terminal results.

| Policy | ALE seed | Shadow termination | Legal moves available in shadow | ALE terminated/truncated | ALE reward |
|---|---:|---|---|---|---:|
| `m4-behavior-only-seed-20261024` | 20261201 | FIVEFOLD_REPETITION | True | False/False | 0.0 |

### Resource accounting

Device profile: local CPU; one serialized ALE process. Free disk before campaign: 50056785920; after campaign: 47532662784.
Artifact-parent bytes after finalization (including preregistration/preflight logs): 2463748628; run-manifest inventory bytes excluding its manifest file: 2459601127; peak process RSS: 368812032.
Frozen limits: 1800 seconds/attempt; 8589934592 artifact bytes; at least 12884901888 free bytes before start; aggregate gameplay cap 162000 seconds.
Expected gameplay duration was approximately 4.4 hours from M6 v2 observed mean of approximately 176 seconds per attempt; 90-attempt extrapolation only; this is a planning estimate, not a guarantee. The aggregate cap equals 45 hours, plus separately measured setup/recovery.
Aggregate process CPU seconds: 6519.449083568; observed process wall seconds: 10393.156784160998; whole campaign session seconds: 10426.961690529999.
Per-policy latency and per-attempt resource distributions are available in `m7-analysis.json`.

### Interpretation and limitations

- All W/D/L and terminal game-score denominators include only ALE-authoritative known terminal outcomes. Incomplete, truncated, terminal-unknown, and not-started cells are retained separately; no incomplete result is scored as a draw.
- Full-schedule score bounds classify every unresolved cell as a loss or as a win, without imputing an outcome.
- Paired intervals are suppressed when a pair set contains censored/unknown outcomes. Per-policy seed intervals are suppressed unless every scheduled seed has a usable outcome/metric.
- Three M5 training-seed pairs and ten M7 ALE seed blocks provide limited inference. The paired seed blocks are not independent trained policies, and no broad Warm-start superiority or generalization claim follows.
- The M7 campaign uses White only and the built-in Atari opponent. M6/M7 comparisons are across different schedules/runtime profiles and are descriptive.
- The M4 accepted aggregate is imitation agreement, not playing strength. The M5 track is a simulator. M6/M7 are actual ALE but measure the frozen controller-policy system together.
- Elo not reported: calibrated opponent pool/design not approved or unavailable. No rating anchor, diverse calibrated pool, or approved Elo match schedule exists.
- M5 RSK-014 and M6 v2 PM6-F06 remain disclosed historical limitations.

### Reproducibility and integrity

Analysis source commit `fe2cc4cc5e477841ffbc9368235eb9c5675f2f74`; analysis source tree `94f37d775b5a62f09c2502fcfd8caf58622397bf`. Raw M5, M6 v1/v2, M7 ledgers, trace files, root manifests, and the accepted M4 aggregate evaluation were verified before summarization.
Summary reconciliation: `{"attempt_process_started_cells_from_raw": 90, "reset_observed_cells_from_raw": 90, "summary_matches_verified_schedule": true, "summary_resource_rows_match_hash_chained_ledger": true}`.
The machine-readable JSON retains per-seed cells, status categories, denominators, paired comparisons, bootstrap configuration, and resource observations. Raw traces/checkpoints/ROM/RGB remain local and are excluded from this bundle.
