# Accepted M3 Release — Local Read-Only Verification (2026-10-23)

## Result

**PASS.** The exact owner-specified release was found at the local sibling-worktree path `../atari-videochess-rl-m3/artifacts/m3/training-support/release-final-closure-r6` (relative to the repository directory under `Projects`). It was not copied into this repository or modified. All nine files were hashed before and after the verifier; sizes and hashes were unchanged.

This is local execution provenance, not a portable dependency path. A future authorized run must configure the local path and re-run the verifier before loading data. The release remains outside Git and is subject to the existing local/internal academic-use boundary, with no upload or redistribution.

## Identity and quantities

- Release ID: `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`
- `manifest.json` SHA-256: `be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12`
- Split-assignment SHA-256: `84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e`
- Selected games: 1,000; positions before purge: 20,000; retained: 19,268; purged: 732; rejection rows: 182.
- Games by split: train 795, validation 102, test 103.
- Retained positions by split: train 15,196, validation 2,015, test 2,057.
- Cross-split board signatures after purge: 0.

The split-assignment digest is the canonical semantic assignment identity and is distinct from the raw SHA-256 of `split.json`.

## Verification performed

At integration baseline `d9f0872c120fb2408343859c938257e3962f2e09`, Python 3.12.3 and `python-chess` 1.11.2 were used.

Command template (from repository root, with the owner's local path supplied through `M3_RELEASE_PATH`):

```bash
PYTHONPATH="$PWD" <pinned-python>/bin/python -m videochess_rl.data.cli verify --release "$M3_RELEASE_PATH"
```

Exit code: **0**. The project verifier reported the expected release ID, manifest hash, 1,000 games, 19,268 positions, 182 rejections, and seven manifest-listed outputs verified (39,994,522 output bytes). It validated release identities, schemas, record relationships, split integrity, and chess-position contracts by replaying the release. A supplementary read-only pass parsed the JSONL files, confirmed unique game/sample IDs, the split counts above, and that every `played_move_uci` occurs exactly once in its legal candidate list. Before/after file inventories matched.

Sanitized execution details, UTC interval, exact nine-file byte sizes/SHA-256 values, verifier output, and structural checks are in [the machine-readable report](M3-release-local-verification-20261023.json) and [sanitized log](logs/M3-release-local-verification-20261023.log). No raw dataset row is stored in those records.

## Provenance and limits

- Source decision: `M3-SOURCE-ELITE-2022-05-LOCAL-20261020`.
- Source archive SHA-256: `ad374c8fd9fb2fe5f03c1297aa1d47cbbce5caedf6e6e2d387ee816930afdb11`.
- PGN member SHA-256: `0f88f18836be7e321aa1e0211b618e78d4e92065c126c45c95a6a55c1500a8e6`.
- The curated third-party package license remains unstated. The recorded owner boundary is bounded internal academic use with local retention, no upload, and no redistribution.
- This verifies M3 records and their chess semantics. It does not implement an M4 tensor loader, prove model feature parity, or train a model.
- No release file was changed, copied into Git, or uploaded.
