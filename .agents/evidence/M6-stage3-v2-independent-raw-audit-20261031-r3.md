# M6 Stage 3 v2 Independent Raw-Evidence Audit (portable report)

**Run:** `m6-stage3-v2-91f51b14690e-d05d42400cfc`
**Disposition:** `PASS_WITH_IMMUTABLE_PM6_F06_ERRATUM_REQUIRED`
**Audit implementation revision:** `fbcc9826032bb390acb91b240787ba4b0d3409a0`
**Audit implementation SHA-256:** `e8c365ef04ac78ee655492016dbb11b56e0b057ab21d502926fc369f0fa56b26`
**Started / completed (UTC):** `2026-10-31T05:19:10.269584Z` / `2026-10-31T05:20:15.353505Z`
**Machine report:** [M6-stage3-v2-independent-raw-audit-20261031-r3.json](M6-stage3-v2-independent-raw-audit-20261031-r3.json), SHA-256 `e25855108441e8ed11fa2950943f9a6ffa1209064cff102de6432babf0ba56fb`
**Execution log:** [M6-v2-independent-raw-audit-fbcc982.log](logs/M6-v2-independent-raw-audit-fbcc982.log)

This was a read-only verification of already retained v1/v2 gameplay. No ALE reset or step was executed; no policy inference, training, checkpoint mutation, or attempt replacement occurred. The audit uses a separate standard-library implementation and does not import the original campaign, summary, or ledger verifier.

## Evidence roots and immutable identities

The original raw roots were found in the isolated M6 execution worktree at the repository-relative paths `artifacts/m6/` (v1) and `artifacts/m6/v2/` (v2). A local preservation copy was created only after verifying the originals, under `artifacts/m6-preserved-20261031/`. Both roots remain in place on the local ext4 artifact filesystem; the copy is ignored by Git and was not uploaded. Copying consumed 1,346,893,054 filesystem bytes; free space remained 48,549,822,464 bytes, above 12 GiB. After copying, the same r3 verifier was run again directly against the original source roots; [the original-root machine report](M6-stage3-v2-original-root-audit-20261031-r3.json), SHA-256 `ef7063ff639db34c0d39abe13b5e55e0c9dbf9e727ccbf97c6c4f4872313393e`, and [execution log](logs/M6-v2-original-root-audit-fbcc982.log), SHA-256 `29e46ac6478c9155e963f678588ac27e237a1b089a719c5afd979ddd6dd9fc2b`, confirm the same v1/v2 manifest, ledger, schedule, outcome, move, cursor and resource identities as the persistent-copy run.

| Identity | Stage 3 v1 | Stage 3 v2 |
|---|---|---|
| Run ID | `m6-stage3-ad3998200e31-c5ff389dc4fe` | `m6-stage3-v2-91f51b14690e-d05d42400cfc` |
| Execution source | `ad3998200e31e77b292ffc1138d02354f188bf5f` | `91f51b14690eba12e9e4fd25a4fc1671801fac0d`; tree `4d6ed616971c8f5606a0a7250fe68fa2eea40949` |
| Raw run-manifest SHA-256 | `17491f1a82eacffda9189179cc63b2ebff422136d07925de1fb39a2bcff897e8` | `e5870bdc4c1aa05108ed58eacc6ec95123ab2b4bc9436d43c9c9640113eabd83` |
| Config SHA-256 | `05aedeb30efb8b6b97667c44f9d606b58d4da8ae20800d4ef143e629420cebac` | `663651050db80ab027b452241c7d39837ec7986927c0aefc7c7be631f459a49b` |
| Schedule SHA-256 | Original v1 schedule preserved | `be4e6548e6fd3e3db4605e6b55fbe860848dccb2df87d8a7122145bdabe22ffc` |
| Root artifact-manifest SHA-256 | `22ac6ec7e0f4a48f52b2452654d4adecaf111f38ea37f5d9517f173c838716d7` | `bc0068aa2254e4c15165247ee299f48940cca9b7c21f6a288fd13812631ea2b2` |
| Files / manifest total bytes | 4,540 / 616,539,017 | 4,159 / 728,148,524 |
| Ledger SHA-256 / event count | `c8ad5b26c28bb8f934a8541c4b69846afedd3ad4a3eb8c302ac835b20fdf27d3` / 839,785 | `c8364fa194a65c8de6d90bf9165743a411d0a63eba2459f3023821f3d0d838cb` / 968,132 |

The v1 verifier independently checked all 4,540 manifest paths, hashes and sizes; its 839,785-event hash chain; all 35 starts, resets and finishes; and the original v1 config, run-manifest, ledger and artifact-manifest identities. The v2 verifier checked every one of 4,159 file paths, sizes and SHA-256 digests, plus the 968,132-event hash chain (head `cab519a452728b9b2b388d5517e8e1bc34ec612a0162c338210ee57d36b4480f`). It found zero missing/unexpected files, unsafe paths or symlinks. It verified all 20 per-attempt manifests, `attempt.json`/ledger equality, trace file hashes and trace-internal hash chains.

The v2 raw `run_started` event binds the immutable run-manifest and 20-row schedule. The schedule was independently regenerated from the frozen seed/order rules: seeds `20261130`–`20261139`, Warm first on even seeds, Scratch first on odd seeds. Every slot has exactly one attempt ID, start, RGB reset, and finish; there are no duplicate resets, retries, substitutions, omitted slots, or resource-stop events.

The frozen M5 root manifest is `a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c`. Warm and Scratch checkpoint/sidecar hashes are in the machine report and match the actual v2 attempt/decision records. A separate read-only M5 artifact verifier passed at M5 HEAD `c9df9db36c6146a34ef301052a206fe8a3512ffc`, covering seven manifests and 6,544,747,450 bytes; see [M5 verification log](logs/M6-v2-m5-artifact-recheck-20261031.log). M4 r4 manifest/checkpoint/sidecar hashes were also verified against the accepted M4 roster and exercised by the corrected full suite.

## Independent v2 outcomes and operational metrics

The v2 profile is `ALE/VideoChess-v5`, White, mode 4, difficulty 0, RGB, frameskip 4, sticky-action probability 0.25. Runtime evidence distinguishes the 108,000-frame registration default from the effective 500,000-frame ALE horizon; the runner cap is 432,000 post-reset action frames. Each reset's frame origin is independently verified as 4, and post-reset frames are recomputed as final ALE counter minus that origin.

| Policy | Attempts | ALE-terminal W/D/L | Terminal unknown | Incomplete | Attempted / RGB-verified moves | Verified replies | Unexpected cursor displacements (corrected) | Board desync |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Warm | 10 | 0 / 0 / 4 | 0 | 6 | 232 / 222 | 222 | 1,157 (1,157) | 0 |
| Scratch | 10 | 0 / 0 / 7 | 0 | 3 | 173 / 163 | 163 | 714 (714) | 0 |
| **Total** | **20** | **0 / 0 / 11** | **0** | **9** | **405 / 385** | **385** | **1,871 (1,871)** | **0** |

The primary endpoint remains RGB-verified initiated player moves / all initiated player moves. Warm is `222/232 = 95.6897%` with descriptive Wilson 95% interval `92.2488%`–`97.6421%`; Scratch is `163/173 = 94.2197%` with interval `89.6879%`–`96.8303%`. Combined, `385/405 = 95.0617%` with interval `92.4959%`–`96.7808%`. These intervals are descriptive because moves within a game are correlated.

Every attempt has one pending final move and exactly one mutually exclusive category: 11 ALE-terminal, five Atari-reply timeouts, two source-selection uncertainty stops, and two target-navigation uncertainty stops. There are no runner/ALE truncations or terminal-unknown outcomes. Incomplete attempts are not draws.

| Resource | Reconstructed use | Authorized v2 ceiling |
|---|---:|---:|
| Gameplay wall time | 3519.969 s | 43,200 s |
| ALE frame-counter sum | 1,936,199 | — |
| Post-reset action-frame sum | 1,936,119 | 432,000 per attempt |
| Environment steps | 484,035 | — |
| Peak recorded RSS | 620,105,728 bytes | 6,442,450,944 bytes |
| Retained v2 artifact bytes | 728,148,524 | 8,589,934,592 bytes |
| Resource stops / retries | 0 / 0 | 0 / ≤1 |

The 405 policy decisions are bound to their trace inputs, exact legal-candidate set, selected UCI, and frozen checkpoint identity. All decisions record training, optimizer, replay insertion, and Stockfish as false. Per-policy validation, chooser, and adapter-total latency distributions appear in the machine report; adapter-total timing is not labeled neural-only latency.

## All twenty schedule slots

`Attempted / verified` is initiated player moves / RGB-verified player moves. A terminal loss requires authoritative ALE flags (`terminated=true`, `truncated=false`), finite White-perspective reward -1.0, and a matching last ALE action/reward trace. Stops remain distinct.

| Slot | Seed | Policy | Attempt ID | Result | Stop | Attempted / verified | Replies | Pending final move |
|---:|---:|---|---|---|---|---:|---:|---|
| 00 | 20261130 | Warm | `m5-warm-seed-20261104-post-rl-seed-20261130-slot-000-attempt-0000-v2` | loss (-1.0) | ALE_TERMINATED | 26/25 | 25 | 1 (ale_terminal) |
| 01 | 20261130 | Scratch | `m5-scratch-seed-20261104-post-rl-seed-20261130-slot-001-attempt-0000-v2` | loss (-1.0) | ALE_TERMINATED | 19/18 | 18 | 1 (ale_terminal) |
| 02 | 20261131 | Scratch | `m5-scratch-seed-20261104-post-rl-seed-20261131-slot-002-attempt-0000-v2` | loss (-1.0) | ALE_TERMINATED | 19/18 | 18 | 1 (ale_terminal) |
| 03 | 20261131 | Warm | `m5-warm-seed-20261104-post-rl-seed-20261131-slot-003-attempt-0000-v2` | incomplete | OPPONENT_RESPONSE_TIMEOUT | 23/22 | 22 | 1 (opponent_response_timeout) |
| 04 | 20261132 | Warm | `m5-warm-seed-20261104-post-rl-seed-20261132-slot-004-attempt-0000-v2` | incomplete | CONTROLLER_SOURCE_SELECTION_UNCERTAIN | 17/16 | 16 | 1 (source_selection_uncertainty) |
| 05 | 20261132 | Scratch | `m5-scratch-seed-20261104-post-rl-seed-20261132-slot-005-attempt-0000-v2` | loss (-1.0) | ALE_TERMINATED | 19/18 | 18 | 1 (ale_terminal) |
| 06 | 20261133 | Scratch | `m5-scratch-seed-20261104-post-rl-seed-20261133-slot-006-attempt-0000-v2` | loss (-1.0) | ALE_TERMINATED | 12/11 | 11 | 1 (ale_terminal) |
| 07 | 20261133 | Warm | `m5-warm-seed-20261104-post-rl-seed-20261133-slot-007-attempt-0000-v2` | loss (-1.0) | ALE_TERMINATED | 26/25 | 25 | 1 (ale_terminal) |
| 08 | 20261134 | Warm | `m5-warm-seed-20261104-post-rl-seed-20261134-slot-008-attempt-0000-v2` | loss (-1.0) | ALE_TERMINATED | 26/25 | 25 | 1 (ale_terminal) |
| 09 | 20261134 | Scratch | `m5-scratch-seed-20261104-post-rl-seed-20261134-slot-009-attempt-0000-v2` | loss (-1.0) | ALE_TERMINATED | 12/11 | 11 | 1 (ale_terminal) |
| 10 | 20261135 | Scratch | `m5-scratch-seed-20261104-post-rl-seed-20261135-slot-010-attempt-0000-v2` | loss (-1.0) | ALE_TERMINATED | 19/18 | 18 | 1 (ale_terminal) |
| 11 | 20261135 | Warm | `m5-warm-seed-20261104-post-rl-seed-20261135-slot-011-attempt-0000-v2` | incomplete | OPPONENT_RESPONSE_TIMEOUT | 23/22 | 22 | 1 (opponent_response_timeout) |
| 12 | 20261136 | Warm | `m5-warm-seed-20261104-post-rl-seed-20261136-slot-012-attempt-0000-v2` | loss (-1.0) | ALE_TERMINATED | 21/20 | 20 | 1 (ale_terminal) |
| 13 | 20261136 | Scratch | `m5-scratch-seed-20261104-post-rl-seed-20261136-slot-013-attempt-0000-v2` | incomplete | CONTROLLER_SOURCE_SELECTION_UNCERTAIN | 13/12 | 12 | 1 (source_selection_uncertainty) |
| 14 | 20261137 | Scratch | `m5-scratch-seed-20261104-post-rl-seed-20261137-slot-014-attempt-0000-v2` | incomplete | CONTROLLER_TARGET_NAVIGATION_UNCERTAIN | 24/23 | 23 | 1 (target_navigation_uncertainty) |
| 15 | 20261137 | Warm | `m5-warm-seed-20261104-post-rl-seed-20261137-slot-015-attempt-0000-v2` | incomplete | OPPONENT_RESPONSE_TIMEOUT | 23/22 | 22 | 1 (opponent_response_timeout) |
| 16 | 20261138 | Warm | `m5-warm-seed-20261104-post-rl-seed-20261138-slot-016-attempt-0000-v2` | incomplete | OPPONENT_RESPONSE_TIMEOUT | 24/23 | 23 | 1 (opponent_response_timeout) |
| 17 | 20261138 | Scratch | `m5-scratch-seed-20261104-post-rl-seed-20261138-slot-017-attempt-0000-v2` | loss (-1.0) | ALE_TERMINATED | 19/18 | 18 | 1 (ale_terminal) |
| 18 | 20261139 | Scratch | `m5-scratch-seed-20261104-post-rl-seed-20261139-slot-018-attempt-0000-v2` | incomplete | CONTROLLER_TARGET_NAVIGATION_UNCERTAIN | 17/16 | 16 | 1 (target_navigation_uncertainty) |
| 19 | 20261139 | Warm | `m5-warm-seed-20261104-post-rl-seed-20261139-slot-019-attempt-0000-v2` | incomplete | OPPONENT_RESPONSE_TIMEOUT | 23/22 | 22 | 1 (opponent_response_timeout) |

## Eleven ALE-terminal losses

Every terminal game has a hash-verified terminal PNG in the artifact manifest, a raw-RGB hash matching the last ALE observation event, finite reward -1.0, and no later ALE action. The image file SHA covers encoded PNG bytes; the separate raw-RGB SHA covers the observation array. These independent digests are not expected to match. The game result is classified only from the authoritative ALE flags/reward, not from screenshot or shadow checkmate. The final screen may clear the board, so the FEN below is the last actually verified position before the pending terminal move.

| Slot | Attempt ID | Terminated / truncated | White reward/result | Terminal PNG path / PNG file SHA-256 | Raw RGB SHA-256 | Last verified FEN |
|---:|---|---|---|---|---|---|
| 00 | `m5-warm-seed-20261104-post-rl-seed-20261130-slot-000-attempt-0000-v2` | `true / false` | -1.0 (White loss) | `attempts/m5-warm-seed-20261104-post-rl-seed-20261130-slot-000-attempt-0000-v2/frames/ale-terminal.png`<br>`1c2385720712765f07ca5d38d19ddaa85e15aa262326f74d0b602d3762ec9264` | `f0e7985ca01acd7e188a2e6bab7e222ce067d300ebacfb8a16877cf0ab596fef` | `r4b1r/p2k1pp1/5n1p/n1p5/8/3pPP2/1p1P1P2/3K1R2 w - - 0 26` |
| 01 | `m5-scratch-seed-20261104-post-rl-seed-20261130-slot-001-attempt-0000-v2` | `true / false` | -1.0 (White loss) | `attempts/m5-scratch-seed-20261104-post-rl-seed-20261130-slot-001-attempt-0000-v2/frames/ale-terminal.png`<br>`b6eaa9699e40b2d0864303a95454a60edf8e6f2da744bc975703100f723cdf08` | `30600248ca06ca70f54c180e5baa57b071d2f890555d6571939135f22be5f485` | `1r3rk1/p4ppp/2nqb3/8/2p5/2n1Bp2/5PPP/R3KBR1 w Q - 0 19` |
| 02 | `m5-scratch-seed-20261104-post-rl-seed-20261131-slot-002-attempt-0000-v2` | `true / false` | -1.0 (White loss) | `attempts/m5-scratch-seed-20261104-post-rl-seed-20261131-slot-002-attempt-0000-v2/frames/ale-terminal.png`<br>`acd1b54296c6ccc27e9647b77dd22386a9429d660ce1470d3e1fc73a939d6f88` | `856dcaeafdbb1b5b1295578d3a6173431e7930b0202bd505b3aadf8c441be571` | `1r3rk1/p4ppp/2nqb3/8/2p5/2n1Bp2/5PPP/R3KBR1 w Q - 0 19` |
| 05 | `m5-scratch-seed-20261104-post-rl-seed-20261132-slot-005-attempt-0000-v2` | `true / false` | -1.0 (White loss) | `attempts/m5-scratch-seed-20261104-post-rl-seed-20261132-slot-005-attempt-0000-v2/frames/ale-terminal.png`<br>`b6eaa9699e40b2d0864303a95454a60edf8e6f2da744bc975703100f723cdf08` | `30600248ca06ca70f54c180e5baa57b071d2f890555d6571939135f22be5f485` | `1r3rk1/p4ppp/2nqb3/8/2p5/2n1Bp2/5PPP/R3KBR1 w Q - 0 19` |
| 06 | `m5-scratch-seed-20261104-post-rl-seed-20261133-slot-006-attempt-0000-v2` | `true / false` | -1.0 (White loss) | `attempts/m5-scratch-seed-20261104-post-rl-seed-20261133-slot-006-attempt-0000-v2/frames/ale-terminal.png`<br>`f9730e269207879b71b85a0a462dda0544afbaf6833e14d5859c78a088830dfe` | `7453ba4aa76181074623c6e4fb5598f2c689c60dcd90fd6cc03a58651a3d3405` | `r2q1rk1/pp3ppp/2n5/P1bppb2/1p2n3/2P2N1P/3PNPP1/R1BQKBR1 w Q - 1 12` |
| 07 | `m5-warm-seed-20261104-post-rl-seed-20261133-slot-007-attempt-0000-v2` | `true / false` | -1.0 (White loss) | `attempts/m5-warm-seed-20261104-post-rl-seed-20261133-slot-007-attempt-0000-v2/frames/ale-terminal.png`<br>`1c2385720712765f07ca5d38d19ddaa85e15aa262326f74d0b602d3762ec9264` | `f0e7985ca01acd7e188a2e6bab7e222ce067d300ebacfb8a16877cf0ab596fef` | `r4b1r/p2k1pp1/5n1p/n1p5/8/3pPP2/1p1P1P2/3K1R2 w - - 0 26` |
| 08 | `m5-warm-seed-20261104-post-rl-seed-20261134-slot-008-attempt-0000-v2` | `true / false` | -1.0 (White loss) | `attempts/m5-warm-seed-20261104-post-rl-seed-20261134-slot-008-attempt-0000-v2/frames/ale-terminal.png`<br>`1c2385720712765f07ca5d38d19ddaa85e15aa262326f74d0b602d3762ec9264` | `f0e7985ca01acd7e188a2e6bab7e222ce067d300ebacfb8a16877cf0ab596fef` | `r4b1r/p2k1pp1/5n1p/n1p5/8/3pPP2/1p1P1P2/3K1R2 w - - 0 26` |
| 09 | `m5-scratch-seed-20261104-post-rl-seed-20261134-slot-009-attempt-0000-v2` | `true / false` | -1.0 (White loss) | `attempts/m5-scratch-seed-20261104-post-rl-seed-20261134-slot-009-attempt-0000-v2/frames/ale-terminal.png`<br>`5603a2e84a895755b1ef7a15f731f26687f50b2d063917509b32cde24731ffaa` | `4647d73d6b0be55c6ae0b483fb35336dc4f352622eff183586066f7d9a0bcae1` | `r2q1rk1/pp3ppp/2n5/P1bppb2/1p2n3/2P2N1P/3PNPP1/R1BQKBR1 w Q - 1 12` |
| 10 | `m5-scratch-seed-20261104-post-rl-seed-20261135-slot-010-attempt-0000-v2` | `true / false` | -1.0 (White loss) | `attempts/m5-scratch-seed-20261104-post-rl-seed-20261135-slot-010-attempt-0000-v2/frames/ale-terminal.png`<br>`acd1b54296c6ccc27e9647b77dd22386a9429d660ce1470d3e1fc73a939d6f88` | `856dcaeafdbb1b5b1295578d3a6173431e7930b0202bd505b3aadf8c441be571` | `1r3rk1/p4ppp/2nqb3/8/2p5/2n1Bp2/5PPP/R3KBR1 w Q - 0 19` |
| 12 | `m5-warm-seed-20261104-post-rl-seed-20261136-slot-012-attempt-0000-v2` | `true / false` | -1.0 (White loss) | `attempts/m5-warm-seed-20261104-post-rl-seed-20261136-slot-012-attempt-0000-v2/frames/ale-terminal.png`<br>`17641cbe9131e39cc23dadbbba05763a2198fe6f934a3ada584fae9dc5a1f0a1` | `ca1b4d4aed9b9c3298c86282e85a6729f7ecf9c7ada7787ec1b0dfa3cc37bec1` | `r3r1k1/ppp1bpp1/2nn4/8/7p/P1P1PP2/1P1PRP2/q1B1K3 w - - 0 21` |
| 17 | `m5-scratch-seed-20261104-post-rl-seed-20261138-slot-017-attempt-0000-v2` | `true / false` | -1.0 (White loss) | `attempts/m5-scratch-seed-20261104-post-rl-seed-20261138-slot-017-attempt-0000-v2/frames/ale-terminal.png`<br>`cdb121bbbb2730f8013379736f423600d3f48a75a30e8828122c41a417fed8ad` | `fe87d48ba88e6514977f89636a30a6cc740611bf0a52f3ba920d5a5edd0db229` | `1r3rk1/p4ppp/2nqb3/8/2p5/2n1Bp2/5PPP/R3KBR1 w Q - 0 19` |

## Nine incomplete attempts and retained state

The UCI history shown is rederived only from RGB-verified moves/replies. It excludes any selected but unverified final move. The two source uncertainty attempts each pressed source FIRE once and stopped before target navigation/FIRE; the two target-navigation uncertainty attempts pressed source FIRE once and withheld target FIRE. The five reply timeouts preserve the last verified player move and were never replayed or replaced.

| Slot | Attempt ID | Stop | Pending category | Last verified FEN | Verified UCI history | Safe-stop check |
|---:|---|---|---|---|---|---|
| 03 | `m5-warm-seed-20261104-post-rl-seed-20261131-slot-003-attempt-0000-v2` | OPPONENT_RESPONSE_TIMEOUT | opponent_response_timeout | `r4b1r/pp1k1pp1/5n2/2pp4/8/P1N1P3/1P1P1P1p/R1BKn3 w - - 0 23` | g1f3 c7c5 b1c3 b8c6 e2e3 e7e5 h2h4 d7d5 h4h5 g8f6 h1g1 c8g4 f1d3 e5e4 g1f1 g4f3 g2f3 e4d3 c2d3 f6h5 d1b3 c6e5 b3a4 d8d7 a4d7 e8d7 a2a3 e5d3 e1d1 h5f6 c3e2 h7h5 a1b1 h5h4 e2c3 h4h3 d1c2 d3e5 f1e1 e5f3 b1a1 f3e1 c2d1 h3h2 | last player move RGB-verified; no reply retry or attempt replacement |
| 04 | `m5-warm-seed-20261104-post-rl-seed-20261132-slot-004-attempt-0000-v2` | CONTROLLER_SOURCE_SELECTION_UNCERTAIN | source_selection_uncertainty | `r4b1r/pp1k1ppp/8/2p4n/4p3/P2PPP2/1P1P1P2/n1BK1R2 w - - 0 17` | g1f3 c7c5 b1c3 b8c6 e2e3 e7e5 h2h4 d7d5 h4h5 g8f6 h1g1 c8g4 f1d3 e5e4 g1f1 g4f3 g2f3 e4d3 c2d3 f6h5 d1b3 c6b4 b3a4 d8d7 a4d7 e8d7 a2a3 b4c2 e1d1 c2a1 c3e4 d5e4 | one source FIRE; target FIRE withheld; no retry |
| 11 | `m5-warm-seed-20261104-post-rl-seed-20261135-slot-011-attempt-0000-v2` | OPPONENT_RESPONSE_TIMEOUT | opponent_response_timeout | `r4b1r/pp1k1pp1/5n2/2pp4/8/P1N1P3/1P1P1P1p/R1BKn3 w - - 0 23` | g1f3 c7c5 b1c3 b8c6 e2e3 e7e5 h2h4 d7d5 h4h5 g8f6 h1g1 c8g4 f1d3 e5e4 g1f1 g4f3 g2f3 e4d3 c2d3 f6h5 d1b3 c6e5 b3a4 d8d7 a4d7 e8d7 a2a3 e5d3 e1d1 h5f6 c3e2 h7h5 a1b1 h5h4 e2c3 h4h3 d1c2 d3e5 f1e1 e5f3 b1a1 f3e1 c2d1 h3h2 | last player move RGB-verified; no reply retry or attempt replacement |
| 13 | `m5-scratch-seed-20261104-post-rl-seed-20261136-slot-013-attempt-0000-v2` | CONTROLLER_SOURCE_SELECTION_UNCERTAIN | source_selection_uncertainty | `r3k1nr/ppp2ppp/2n5/3p4/P2P4/2Q1P3/1BP1BPbq/R3K3 w Qkq - 0 13` | b1c3 e7e5 a2a4 b8c6 g1f3 d7d5 h1g1 e5e4 e2e3 e4f3 d2d4 f3g2 f1e2 c8h3 g1g2 h3g2 b2b4 f8b4 c1b2 d8h4 d1d2 b4c3 d2c3 h4h2 | one source FIRE; target FIRE withheld; no retry |
| 14 | `m5-scratch-seed-20261104-post-rl-seed-20261137-slot-014-attempt-0000-v2` | CONTROLLER_TARGET_NAVIGATION_UNCERTAIN | target_navigation_uncertainty | `r4rk1/p4ppp/2n5/2b1p3/2b1K3/8/5PPP/nq3BR1 w - - 4 24` | b1c3 c7c5 a2a4 b8c6 g1f3 e7e5 h1g1 d7d5 e2e4 g8f6 c3e2 f6e4 c2c3 f8d6 b2b3 e8g8 c3c4 c8e6 b3b4 c5b4 e2c3 b4c3 d2c3 e4c3 c1e3 c3d1 a4a5 d1e3 a5a6 e3c2 e1d2 c2a1 a6b7 d6b4 d2e3 d8b6 e3e2 b6b7 f3d2 d5c4 d2c4 e6c4 e2e3 b4c5 e3e4 b7b1 | one source FIRE; target FIRE withheld; no retry |
| 15 | `m5-warm-seed-20261104-post-rl-seed-20261137-slot-015-attempt-0000-v2` | OPPONENT_RESPONSE_TIMEOUT | opponent_response_timeout | `r4b1r/pp1k1pp1/5n2/2pp4/8/P1N1P3/1P1P1P1p/R1BKn3 w - - 0 23` | g1f3 c7c5 b1c3 b8c6 e2e3 e7e5 h2h4 d7d5 h4h5 g8f6 h1g1 c8g4 f1d3 e5e4 g1f1 g4f3 g2f3 e4d3 c2d3 f6h5 d1b3 c6e5 b3a4 d8d7 a4d7 e8d7 a2a3 e5d3 e1d1 h5f6 c3e2 h7h5 a1b1 h5h4 e2c3 h4h3 d1c2 d3e5 f1e1 e5f3 b1a1 f3e1 c2d1 h3h2 | last player move RGB-verified; no reply retry or attempt replacement |
| 16 | `m5-warm-seed-20261104-post-rl-seed-20261138-slot-016-attempt-0000-v2` | OPPONENT_RESPONSE_TIMEOUT | opponent_response_timeout | `r4b1r/pp1k1pp1/5n2/3p4/P7/1KN1PP2/3P3p/1RBn4 w - - 0 24` | g1f3 c7c5 b1c3 b8c6 e2e3 e7e5 h2h4 d7d5 h4h5 g8f6 h1g1 c8g4 f1d3 e5e4 g1f1 g4f3 g2f3 e4d3 c2d3 f6h5 d1b3 c6e5 b3a4 d8d7 a4d7 e8d7 a2a3 e5d3 e1d1 h5f6 c3e2 h7h5 a1b1 h5h4 e2c3 h4h3 d1c2 c5c4 f1d1 d3f2 b2b3 c4b3 c2b3 f2d1 a3a4 h3h2 | last player move RGB-verified; no reply retry or attempt replacement |
| 18 | `m5-scratch-seed-20261104-post-rl-seed-20261139-slot-018-attempt-0000-v2` | CONTROLLER_TARGET_NAVIGATION_UNCERTAIN | target_navigation_uncertainty | `r4rk1/pp3ppp/3b4/3pp3/P7/2q1BN2/R1b1BPPP/4K1R1 w - - 0 17` | b1c3 c7c5 a2a4 b8c6 g1f3 e7e5 h1g1 d7d5 e2e4 g8f6 c3e2 f6e4 c2c3 f8d6 b2b3 c8f5 b3b4 c5b4 c3b4 c6b4 e2c3 e4c3 d2c3 b4c2 d1c2 f5c2 c1e3 e8g8 f1e2 d8a5 a1a2 a5c3 | one source FIRE; target FIRE withheld; no retry |
| 19 | `m5-warm-seed-20261104-post-rl-seed-20261139-slot-019-attempt-0000-v2` | OPPONENT_RESPONSE_TIMEOUT | opponent_response_timeout | `r4b1r/pp1k1pp1/5n2/2pp4/8/P1N1P3/1P1P1P1p/R1BKn3 w - - 0 23` | g1f3 c7c5 b1c3 b8c6 e2e3 e7e5 h2h4 d7d5 h4h5 g8f6 h1g1 c8g4 f1d3 e5e4 g1f1 g4f3 g2f3 e4d3 c2d3 f6h5 d1b3 c6e5 b3a4 d8d7 a4d7 e8d7 a2a3 e5d3 e1d1 h5f6 c3e2 h7h5 a1b1 h5h4 e2c3 h4h3 d1c2 d3e5 f1e1 e5f3 b1a1 f3e1 c2d1 h3h2 | last player move RGB-verified; no reply retry or attempt replacement |

## PM6-F06 and nearby consistency checks

The immutable raw v2 manifest reports `budget.gameplay_wall_budget_includes_diagnostics = true` while its textual scope and the frozen config exclude historical v1 and M6 diagnostics. The sanitized review manifest and derived execution record repeat that same incorrect boolean. Exact hashes and the source fallback are in [PM6-F06 erratum](M6-PM6-F06-erratum-20261031.md); no original bytes were changed.

The audit independently verified that the flag did not drive the run: v2 used an isolated artifact root, prohibited diagnostic runs, and enforced the 43,200-second limit from config. The run manifest records zero v2 use before start; the verified campaign used 3519.969 seconds and recorded no resource stop. V1's `true` is consistent with its separate diagnostic-inclusive scope. No related v1/v2 fallback, horizon, schedule, or runtime-arithmetic inconsistency was found.

V1 and v2 remain separate protocols. V2 reused the same ALE seeds with a different horizon and is an extended-horizon re-evaluation, not independent held-out evidence. These results do not establish Warm superiority or Elo.

## Reproduction

The original v2 raw directory was `artifacts/m6/v2/m6-stage3-v2-91f51b14690e-d05d42400cfc/` relative to the isolated execution worktree. Its verified persistent local copy is `artifacts/m6-preserved-20261031/v2/m6-stage3-v2-91f51b14690e-d05d42400cfc/`; the corresponding v1 copy is `artifacts/m6-preserved-20261031/v1/m6-stage3-ad3998200e31-c5ff389dc4fe/`. Exact command, environment, timestamp, return code, report checksum, and verifier-source revision are recorded in [the audit log](logs/M6-v2-independent-raw-audit-fbcc982.log). This verifier uses only the standard library and reads the evidence without opening ALE.

M6 remains in progress pending independent PM acceptance. This audit does not accept M6, approve G4, or authorize M7.
