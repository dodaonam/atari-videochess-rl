# M4-02 revised overfit sanity result — 2026-10-27

**Protocol:** `M4-02-distinct-effective-inputs/1.0`
**Code revision:** `7988af28f768c203c9cc7e2794785c99df588645`
**Dataset:** accepted M3 release `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`
**Result:** **PASS** for the M4-02 sanity gate. This does not by itself accept M4-01, M4-03, M4-04, or the M4 milestone.

The original `m4-behavior-20261027-r2` result remains failed historical evidence. This new run used fresh weights initialized with seed `20261022`, the existing AdamW configuration, and the unchanged 500-update cap and thresholds.

## Revised selection evidence

- Exactly 128 examples were selected from the train partition only, ordered by ascending `sample_id`.
- The first sample for each pairwise-distinct complete effective model input was retained, independent of target labels.
- All 128 sample IDs are unique and ascending; all 128 effective input identities are distinct.
- The selected identity was verified against actual collated model tensors after removing only batch padding.
- Ordered sample-ID SHA-256: `489a9fca5b9358b40c0ffc4ed649458124ba8803278ea710a4ad5fa556430e53`.
- Aggregate ordered effective-input identity SHA-256: `3064625c698e9eb06f83fe5e8c9e080ad86af821338ee5cc1fda6531dfc6432c`.
- Selection JSON SHA-256: `129c91ed804c02bcb26bfb9263e7c0a0b2bf46cd5bd2e1fee26d5323dc47ffac`.

## Gate measurement

The gate began at `2026-10-27T15:31:54.235586Z` and passed at update 140 at `2026-10-27T15:32:37.348772Z` (43.0428 seconds). Final cross-entropy was `0.03854484462305363`; legal top-1 was `127/128 = 99.21875%`; top-3 was `127/128 = 99.21875%`; MRR was `0.994140625`. Both original numeric thresholds passed without changing the model, data, labels, optimizer, seed, update limit, or resource caps.

The machine-readable gate record SHA-256 is `69b84788fa431b6e1af14729e9982db68d45e6c0d3250aa723593494c03735dc`. The selection and gate JSON, run manifest, and append-only event log are retained in the approved external artifact directory under `m4-behavior-20261027-r3`; the full run was still executing its authorized three-seed training when this gate result was recorded. The final run command and process exit status are therefore recorded in the completed run manifest, not asserted here.

**Command:**

```text
PATH=/home/dodaonam/Projects/atari-videochess-rl/.venv/bin:/usr/bin:/bin PYTHONPATH=. /home/dodaonam/Projects/atari-videochess-rl/.venv/bin/python -m videochess_rl.model.cli run --release-dir /home/dodaonam/Projects/atari-videochess-rl-m3/artifacts/m3/training-support/release-final-closure-r6 --artifact-root /home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4 --run-id m4-behavior-20261027-r3
```

The gate substage is PASS. Full training, frozen test evaluation, simulator evaluation, checkpoint acceptance, and final process completion remain separate work.

Backlog result record: M4-02 sanity gate PASS: fresh seed 20261022 weights, 140/500 updates, CE 0.0385448446, legal top-1 127/128 (99.21875%), top-3 127/128, MRR 0.994140625. Full M4 training and other acceptance criteria remain in_progress.
