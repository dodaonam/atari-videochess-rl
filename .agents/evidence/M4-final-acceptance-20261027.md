# M4 Final Acceptance — 2026-10-27

## Decision and scope

M4-01, M4-02, M4-03, and M4-04 **PASS** for the implementation at source revision `7b3c9074a2d932fec6d7732ee08e99b9de10a135`. `M4-001` is recorded `done` in the canonical backlog. This report records technical acceptance on the existing feature branch; PR #8 integration and clean-clone verification are a separate delivery step and are not claimed by this pre-merge report.

The implementation follows Accepted ADR-0003 and remains a bounded supervised behavior-cloning experiment. It does not implement or train Double DQN, does not claim Elo or chess strength, and does not establish ALE/Atari performance. G3 remains unapproved; M5/M6 have not started. O-01 remains closed for internal execution; no separate instructor approval is claimed.

## M4-02 protocol decision and gate

The original fixed lexical-128 run `m4-behavior-20261027-r2` remains an immutable failure: at 500 updates it reached CE `0.02195480228497465` and legal top-1 `126/128 = 98.4375%`, below the unchanged 99% threshold. Its original sample-ID digest is `cc7c30b0fb6c676ad4bf8b8e9b535af2c8a14a9b302949ac2c375defe4541634`. Independent input reconstruction found two identical-input/different-target pairs, which capped deterministic top-1 at 126/128. The [blocker report](M4-02-sanity-gate-blocker-20261027.md), diagnostic files, and original run artifacts remain preserved; the failed run is not counted as a pass.

The [dated PM amendment](M4-02-protocol-amendment-20261027.md) authorizes only deterministic sample selection to change. Protocol revision `M4-02-distinct-effective-inputs/1.0` orders training rows by ascending `sample_id`, retains the first occurrence of each distinct complete canonical effective model input, excludes target/provenance fields from identity, checks exact identity bytes on digest matches, and verifies agreement with collated model tensors. Model, training labels, fresh initialization, seed `20261022`, AdamW settings, 500-update cap, CE threshold `0.05`, and legal top-1 threshold `99%` are unchanged.

The new gate in run `m4-behavior-20261027-r4` passed from fresh weights at update 140: CE `0.03854484462305363`; legal top-1 `127/128 = 99.21875%`; top-3 `127/128`; MRR `0.994140625`. It selected 128 train-only examples with pairwise-distinct complete effective inputs. Selected-ID SHA-256: `489a9fca5b9358b40c0ffc4ed649458124ba8803278ea710a4ad5fa556430e53`. Aggregate input-identity SHA-256: `3064625c698e9eb06f83fe5e8c9e080ad86af821338ee5cc1fda6531dfc6432c`. The selection, ID list, identities, and trajectory are retained in `sanity_selection.json` and `sanity_gate.json` in the run directory.

## Dataset and architecture

The exact local M3 release was used without modification:

- Path: `/home/dodaonam/Projects/atari-videochess-rl-m3/artifacts/m3/training-support/release-final-closure-r6`
- Release ID: `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`
- Manifest SHA-256: `be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12`
- Split-assignment SHA-256: `84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e`
- Counts: 795/102/103 games and 15,196/2,015/2,057 train/validation/test positions.

The run invoked the independent release verifier before loading, rechecked all nine file identities before and after replay/tensorization, reported zero cross-split board-signature overlap, and recorded `post_load_release_files_unchanged: true`. It trained only against `played_move_uci`; no Stockfish score, teacher target, game result, player metadata, or future move was used.

A fresh read-only verification after training also passed on 2026-10-27: 1,000 games, 19,268 positions, release ID and manifest SHA-256 matched. The exact command, exit code 0, UTC timestamps, and sanitized output are in [the final M3 verification log](logs/M4-final-m3-verification-20261027.txt) (SHA-256 `bdfa1044ae47195b075e30491474ef66bed70359ff30065a8f5b8dae5b067127`). No source or release file was changed.

The implemented contract is `videochess-model-input/1.0` and model schema `videochess-behavior-scorer/1.0`: mover-oriented 13-plane board, six state scalars, full UCI history with masks, per-candidate spatial/symbolic features, masks, and lexical semantic UCI identities. The shared board CNN, history embeddings/GRU, metadata projection, candidate encoder and scorer have **121,897 measured trainable parameters**, below the strict 250,000 cap. The final scalar behavior-logit head is separate and is reinitialized for the documented future M5 Q head; the behavior output is not a Q-value. Shape, special-move, perspective, empty-terminal, mask, gradient, candidate mapping, checkpoint, and transfer-boundary tests are included in the focused test modules.

## Bounded training

Run ID `m4-behavior-20261027-r4`, source revision `7b3c9074a2d932fec6d7732ee08e99b9de10a135`, clean source worktree at run start. The run started `2026-10-27T16:00:40.648769Z`, completed `2026-10-27T16:22:19.931137Z`, and exited 0. The configuration used CPU, AdamW, learning rate `3e-4`, weight decay `1e-4`, physical batch size 64, gradient clipping 1.0, up to 20 epochs, validation-NLL model selection, patience 4, and the fixed seeds below. Each stopped by validation patience.

| Seed | Epochs run | Best epoch | Train NLL at best epoch | Validation NLL | Validation top-1 | Seed runtime | Optimizer updates | Stop |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 20261022 | 14 | 10 | 2.2797661124 | 2.4259302606 | 29.5782% | 367.246 s | 3,332 | validation patience |
| 20261023 | 13 | 9 | 2.3250935632 | 2.4453350601 | 29.8759% | 342.978 s | 3,094 | validation patience |
| 20261024 | 15 | 11 | 2.2753390744 | **2.4127401238** | 29.5782% | 396.497 s | 3,570 | validation patience |

The final model was selected using minimum validation NLL across seeds; ties select the lower seed. The selected model is seed `20261024`, epoch 11. The test split was not used for seed, epoch, configuration, or model selection. Per-epoch train and validation metrics, legal top-k, MRR, throughput, clipping diagnostics, and stop reasons are preserved in the three seed JSON records.

## Frozen test evaluation

The selected checkpoint was evaluated on the held-out test partition **once**, after freeze. The record is bound to checkpoint SHA-256 `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4` and states `selection_used_test_metrics: false`.

| Test metric | Model | Uniform legal baseline |
|---|---:|---:|
| NLL | 2.4232315562 | 3.2400176067 |
| Legal top-1 | 29.8979% | 5.9157% |
| Legal top-3 | 54.3996% | 16.3373% |
| Legal top-5 | 65.5809% | 24.1053% |
| MRR | 0.4643745951 | 0.1720556929 |

The split contained 2,057 positions and 61,419 legal-candidate evaluations. Evaluation took 1.6465 seconds, or 1,249.8 examples/second and 37,317.7 candidates/second. Black-to-move positions: 1,003, NLL 2.36801, top-1 30.41%, top-3 56.83%, top-5 67.70%, MRR 0.47538. White-to-move positions: 1,054, NLL 2.47578, top-1 29.41%, top-3 52.09%, top-5 63.57%, MRR 0.45390. Move-type/phase strata are in `test_evaluation.json`; en passant has only one example and promotions have three, so those category results are descriptive and sparse. These metrics measure imitation of historical moves, not optimality or chess strength.

## Simulator-only evaluation and engine-free confirmation

The full run recorded 40 completed M2 simulator games across the ten required seeds, both colors, and both opponents. Because Stockfish was available on the parent training environment's PATH, a separate full 40-game confirmation was then run with `PATH=/usr/bin:/bin`; it asserted that no Stockfish executable was resolvable and `chess.engine` was not imported. This confirmation used the same frozen checkpoint and schedule, did not alter the immutable r4 run directory, completed in 12.2198 seconds, and is stored at `/home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-simulator-engine-free-20261027.json` (SHA-256 `861b30ecb4819a238764f9a0374920d14c5ceb98824089d2cf3c5fa29f9f1ab9`). It reports `stockfish_available: false`, 40 completed games, zero truncations/failures, 400-decision cap, p50 latency 4.854 ms, and p95 latency 12.220 ms.

| Opponent | Agent color | Wins | Draws | Losses | Games |
|---|---|---:|---:|---:|---:|
| RandomLegalAgent | White | 6 | 4 | 0 | 10 |
| RandomLegalAgent | Black | 10 | 0 | 0 | 10 |
| SimpleHeuristicAgent | White | 5 | 4 | 1 | 10 |
| SimpleHeuristicAgent | Black | 1 | 9 | 0 | 10 |

These are limited M2 simulator behavior checks only; they are not an Elo estimate, Double DQN result, or Atari performance result.

## Checkpoint and resource accounting

- Selected artifact: `/home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r4/pretrained-behavior-only.pt`
- Checkpoint SHA-256: `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4`; size 1,520,046 bytes.
- Checkpoint sidecar metadata SHA-256: `63615d8d0ed27900fdf86d3f3084ca95cd562f9ec2f9a7e94bca4b0f6301e0c8`.
- Artifact manifest SHA-256: `f00fde1c59325105e0ffd45bb45eb269dfa303416010c9a0b6c6be47bd9a9921`; 19 run files verified.
- Run manifest SHA-256: `531f591e28ebdc257ab43945118793accd9e131ba636341ee90e3fc6ff545abe`.
- Engine-free inference subprocess: exit 0 with `PATH=/usr/bin:/bin`, `stockfish_path: null`, `engine_module_loaded: false`; selected legal UCI move `g1f3`.
- Peak process RSS: 628,350,976 bytes (about 599 MiB); feature payload: 26,648,765 bytes; model state tensors: 487,588 bytes.
- The r4 run used 3,234.281 seconds including prior run attempts, release verification, and the conflict diagnostic; adding the separately recorded 12.220-second engine-free simulator confirmation gives 3,246.501 seconds of the 10,800-second aggregate cap. Remaining cap: about 7,553.499 seconds. Each configured seed's cumulative usage including prior attempts remained below 2,700 seconds.
- Runtime: Python 3.12.3, PyTorch 2.14.1+cpu, python-chess 1.11.2, NumPy 2.5.4, Linux x86_64, local CPU; one intra-op and one inter-op thread.

The r4 checkpoint was safely loaded in-process after freeze and again in a separate engine-free inference process. Artifact verification returned exit 0 with all 19 files and the checkpoint hashes above. The earlier r3 failure caused by a non-primitive `TorchVersion` metadata value remains preserved in [its failure report](M4-run-r3-checkpoint-load-failure-20261027.md); the fix records the version as a built-in string and is covered by checkpoint tests.

## Verification record

The final focused suite ran on source revision `7b3c9074a2d932fec6d7732ee08e99b9de10a135` with the repository's pinned Python 3.12 virtual environment because `uv` was unavailable. Command:

```bash
PATH=/home/dodaonam/Projects/atari-videochess-rl/.venv/bin:/usr/bin:/bin PYTHONPATH=. /home/dodaonam/Projects/atari-videochess-rl/.venv/bin/python -m unittest tests.test_m4_model tests.test_m4_data tests.test_m4_training tests.test_m4_checkpoint tests.test_pre_m4_contracts tests.test_m2_simulator tests.test_m3_data -v
```

Result: 124 tests passed, exit 0. Sanitized output: `.agents/evidence/logs/M4-final-focused-7b3c907-20261027.log`, SHA-256 `1d187521424d9c460ceba58b4acbb127d38785f4cecc50a9f509a9eeac2b4a6c`.

The full regression suite ran on the same source revision and environment:

```bash
PATH=/home/dodaonam/Projects/atari-videochess-rl/.venv/bin:/usr/bin:/bin PYTHONPATH=. /home/dodaonam/Projects/atari-videochess-rl/.venv/bin/python -m unittest discover -s tests -v
```

Result: 313 tests passed, exit 0. Sanitized output: `.agents/evidence/logs/M4-final-full-suite-7b3c907-20261027.log`, SHA-256 `7cac9ac00fcff79420df462d0490f1fea8bf4196f32fce2e891457a8c9b08d85`.

The corrected full run command recorded in the run manifest exited 0. `verify-artifacts` exited 0. The focused/full logs are exact command output; final clean-clone, archive, preflight, GitHub checks, and post-merge evidence are recorded by the delivery closeout and are not implied by this pre-merge report.

## Remaining limitations

- The M3 source package's broader redistribution license remains unstated. Dataset and model artifacts stay local and outside Git.
- The 1,000-game curated set may be biased; the model imitates its played moves and the test top-1 result is about 29.90%.
- Sparse move categories (especially one en-passant and three promotion examples) do not support reliable category conclusions.
- M4 does not prove chess strength, RL improvement, M5 transfer performance, or ALE/Atari performance. M5 Double DQN implementation and M6 Atari integration remain future work and are outside this acceptance.
- O-01 is closed internally, but no external instructor approval is claimed; an actual explicit course prohibition, if later discovered, still governs its affected activity.
