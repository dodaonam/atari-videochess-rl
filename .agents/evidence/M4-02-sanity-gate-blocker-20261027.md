# M4-02 fixed sanity-gate blocker — 2026-10-27

**Status:** M4-02 did not pass. The fixed 128-example gate is blocked by contradictory targets on identical complete model inputs in the accepted M3 training data. No full training, held-out test evaluation, simulator benchmark, or pretrained checkpoint was produced.

## Executed gate

- Run: `m4-behavior-20261027-r2`; source revision `4562dddd80d302bdbb49e1191c97bd71ac7e9938`; artifact directory `/home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r2`.
- Command: `/home/dodaonam/Projects/atari-videochess-rl/.venv/bin/python -m videochess_rl.model.cli run --release-dir /home/dodaonam/Projects/atari-videochess-rl-m3/artifacts/m3/training-support/release-final-closure-r6 --artifact-root /home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4 --run-id m4-behavior-20261027-r2`.
- Time: 2026-10-27T13:33:05.861961Z to 2026-10-27T13:37:52.900009Z (287.038 seconds for this invocation; 398.289 seconds including prior release verification and the earlier failed start).
- Environment: Python 3.12.3; PyTorch 2.14.1+cpu; python-chess 1.11.2; NumPy 2.5.4; local CPU; Stockfish absent from the M4 inference path.
- Gate seed: `20261022`. The 128 lexically smallest train `sample_id`s were persisted; SHA-256 `cc7c30b0fb6c676ad4bf8b8e9b535af2c8a14a9b302949ac2c375defe4541634`.
- At 500 updates: cross-entropy 0.02195480 (limit ≤ 0.05); legal top-1 98.437500% (required ≥ 99%); MRR 0.992188; top-3 100.000000%.
- Result: CE passed; top-1 failed (126/128 correct; the threshold requires at least 127/128). CLI exit code 2. Peak process RSS was 606,011,392 bytes.

## Verified data identity

The M4 loader independently verified, replayed, and tensorized the exact local release at `/home/dodaonam/Projects/atari-videochess-rl-m3/artifacts/m3/training-support/release-final-closure-r6`. Release ID `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`, manifest SHA-256 `be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12`, and split-assignment SHA-256 `84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e` match the accepted M3 release. Counts were 15,196 train, 2,015 validation, and 2,057 test positions from 795/102/103 games. The loader and subsequent read-only diagnostic confirmed all nine release files were unchanged. Cross-split board-signature overlap remained zero. No release data was repaired, regenerated, or written.

## Structural upper bound

The read-only diagnostic at revision `e5e42f703bfd3386c94de17b607aa5102b60201f` reran release verification and history replay, checked the persisted fixed sample IDs, and compared the exact unpadded tensor fields plus ordered candidate UCI identities. Under `videochess-model-input/1.0`, the target label is not a model input. History and candidate lengths are identical within each pair; the collator derives masks from those lengths, and any extra batch padding is masked. For each pair, a deterministic scorer receives the same state/history/candidate inputs and must return the same legal top-1 action; it cannot match two different labels.

The exact-input groups have hashes `1b30fcb96d85e9533f789e8a8e07d7111faddf60cc71b40aff17f4e0e5ff0da3` and `e82e9da38607b337f5597e2fa444bf7ca86905f8b26dd84f58e6bd70b75a4a37`:

| Identical input group | Sample ID | Target UCI | History length | Legal candidates |
|---|---|---|---:|---:|
| `1b30fcb96d85…` | `008d0d9e411e3db4b5f012c35685a2b93d276bb56d3626c2636420bf7c3743dc` | `c7c6` | 1 | 20 |
| `1b30fcb96d85…` | `013c134d9852e3ab32f80fdb8e011d603f3dd5b9306d478a3d79570bca62fbec` | `e7e5` | 1 | 20 |
| `e82e9da38607…` | `00caca2ae4c70b8d55286ae750415a2e660c8464e1b4eaaf0bd78dc963f89349` | `c1g5` | 2 | 28 |
| `e82e9da38607…` | `016746307b00a2f651c0266d57b88f8b0b4d3bc8f8b07825801d3a1b5d02f055` | `c2c4` | 2 | 28 |

Within each pair the ordered legal candidate identity sets and all model input arrays are exactly equal; the two played moves differ. Thus at most one label in each pair can be correct. The diagnostic computed a maximum of **126/128 = 98.4375%**, a minimum of two errors, against the required 127/128. The observed model reached exactly that upper bound. The machine-readable report records the full 128 IDs, input hashes, dataset file hashes, masks-by-length facts, and the computation.

## Disposition and unblock condition

This is not evidence of a tensor, gradient, optimizer, or candidate-mask implementation defect. Satisfying the gate would require changing the fixed sample selection, target interpretation/acceptance rule, or model input identity so that identical positions can be distinguished. Those changes would alter the owner-authorized M4 protocol or accepted ADR-0003 input contract. They were not made. The threshold was not weakened, no sample or label was removed, and no training work was started beyond the required gate.

**Unblock condition:** The project owner must issue a revised, explicit M4-02 protocol decision that resolves these conflicting-label examples while preserving the accepted M3 source data and model contract (for example, by authorizing a defined conflict-aware gate or a revised fixed-sample rule). Until that decision is recorded, the existing 128-example criterion remains binding and M4-001 stays blocked. No M4-03 or M4-04 result is claimed.

## Evidence

- `.agents/evidence/logs/M4-sanity-gate-r2-20261027.txt` — command, captured run summary, and observed exit code 2.
- `.agents/evidence/logs/M4-02-sanity-gate-diagnostic-20261027.json` — complete machine-readable read-only report, exact selected IDs, all nine release file hashes/sizes, conflicts, ceiling, runtime, environment, and resource measurement.
- `.agents/evidence/logs/M4-02-sanity-gate-diagnostic-20261027.txt` — captured diagnostic output and observed exit code 0.
- Preserved external run artifacts: `/home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r2` (failed gate only; no checkpoint).
- Diagnostic command: `/home/dodaonam/Projects/atari-videochess-rl/.venv/bin/python /tmp/atari-m4-work/scripts/diagnose_m4_gate_conflicts.py --gate-run /home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r2 --release-dir /home/dodaonam/Projects/atari-videochess-rl-m3/artifacts/m3/training-support/release-final-closure-r6 --output .agents/evidence/logs/M4-02-sanity-gate-diagnostic-20261027.json` (exit code 0).

## Verification after diagnosis

At source revision `e5e42f703bfd3386c94de17b607aa5102b60201f`, the focused M4, context/recovery, M2/M3 and semantic-contract suite passed **191 tests** (exit 0, 93.922 seconds). The full standard-library regression suite passed **304 tests** (exit 0, 97.278 seconds; Python 3.12.3, PyTorch 2.14.1+cpu, python-chess 1.11.2, NumPy 2.5.4, with configured Stockfish available for the repository UCI readiness smoke test). Logs are `.agents/evidence/logs/M4-focused-tests-20261027.txt` and `.agents/evidence/logs/M4-full-suite-pass-20261027.txt`. An earlier full-suite attempt failed only because the test detected tracked evidence written after its checkpoint; that failure is preserved in `.agents/evidence/logs/M4-full-suite-20261027.txt` and was followed by the passing 304-test rerun.

The M4 model contract tests measure 121,897 trainable parameters (<250,000) and verify finite outputs/gradients, candidate masking, semantic UCI selection, model transfer, and checkpoint round-trip. The focused suite passed these checks. This is M4-01 contract/test evidence only; it is not a pretrained checkpoint or end-to-end engine-free trained-model acceptance. The 128-example gate and read-only diagnosis stayed under the 2 GiB RSS cap. Full training, frozen test evaluation, simulator evaluation, and M4 checkpoint creation were deliberately not started after the hard gate failed.

No PR was merged because the M4-02 acceptance condition failed. The current feature branch is a reviewable implementation/evidence branch; passing unit and regression tests do not override the failed fixed-sample gate. G3 remains unapproved; M5 has not started.
