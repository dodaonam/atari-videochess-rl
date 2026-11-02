# Accepted M3 Release — Local Read-Only Verification (2026-10-27)

## Result

**PASS.** The owner-specified release was reverified at `/home/dodaonam/Projects/atari-videochess-rl-m3/artifacts/m3/training-support/release-final-closure-r6`. The project verifier exited 0 in 112.014 seconds using Python 3.12.3, python-chess 1.11.2, and `PYTHONPATH` set to this PR worktree (`/tmp/atari-pre-m4-work`). The nine required files were hashed before and after verification, match the 2026-10-23 accepted file inventory, and were unchanged.

This path is local and is not a portable repository dependency. The exact release is outside Git and absent from a clean clone; future use must configure this local path and rerun the verifier before loading. No M4 neural data loader consumed the release in this mission. No file was copied, regenerated, split, modified, uploaded, or committed.

## Identity and quantities

- Release ID: `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`
- `manifest.json` SHA-256: `be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12`
- Semantic split-assignment SHA-256: `84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e`
- Games: 1,000; positions before purge: 20,000; retained: 19,268; purged: 732; rejection records: 182.
- Retained positions: train 15,196; validation 2,015; test 2,057.
- Cross-split board signatures after purge: 0; invalid/missing target-in-candidate rows: 0.

All nine file sizes and SHA-256 digests are in the [machine-readable report](M3-release-local-verification-20261027.json). The sanitized verifier output is in [the log](logs/M3-release-local-verification-20261027.log).

## Command and provenance

Executed 2026-10-27T10:36:31Z–2026-10-27T10:38:23Z UTC at source revision `a41d6f14014727570f55dfa2d015d4ad80250445` (the verifier module paths were unchanged from that revision):

```text
/home/dodaonam/Projects/atari-videochess-rl/.venv/bin/python -m videochess_rl.data.cli verify --release /home/dodaonam/Projects/atari-videochess-rl-m3/artifacts/m3/training-support/release-final-closure-r6
```

Exit code: 0. The verifier replayed and checked the release rows, schemas, manifest outputs, split/leakage conditions, chess state, and legal candidate/played-move contracts. The supplementary scan confirmed unique game/sample IDs and the expected quantities.

## Provenance and limits

- Source decision: `M3-SOURCE-ELITE-2022-05-LOCAL-20261020`.
- The third-party filtered package license remains unstated; owner scope remains local/internal research with no upload or redistribution.
- This verifies M3 data integrity and chess semantics; it does not establish model feature parity, implement an M4 loader, or produce training/performance evidence.
