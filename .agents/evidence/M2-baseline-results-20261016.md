# M2 baseline benchmark results — 2026-10-16

## Run provenance

- **Run ID:** `m2-baseline-20261016T073553Z`
- **Source revision:** `74008b8c8705809330ef218ba3d5bd9e1b5335ab`
- **Command:** `/home/dodaonam/Projects/atari-videochess-rl/.venv/bin/python -m videochess_rl.benchmark --seeds 20261016 20261017 --max-decisions 400 --output .agents/evidence/M2-baseline-benchmark-20261016.json`
- **Started:** `2026-10-16T07:35:51Z`; **finished:** `2026-10-16T07:35:53Z`; **exit code:** `0`
- **Runtime:** Python 3.12.3; python-chess 1.11.2; Linux 7.0.0-38-generic, x86_64; 8 CPUs.
- **Configuration:** standard initial position; two base seeds; both colors; 400 agent decisions maximum; each baseline played the other baseline. Derived policy and episode seeds are recorded in the JSON.
- **Structured result SHA-256:** `681e795b613630d55a2e470bd0887a7975407db9d849b319ae09d4e1c995893a`

## Results

| Agent policy | Color | Games | Wins | Draws | Losses | Mean decisions | Completed | Truncated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Random Legal | White | 2 | 0 | 1 | 1 | — | 2 | 0 |
| Random Legal | Black | 2 | 0 | 1 | 1 | — | 2 | 0 |
| Random Legal | Both | 4 | 0 | 2 | 2 | 90.5 | 4 | 0 |
| Simple Material Heuristic | White | 2 | 1 | 1 | 0 | — | 2 | 0 |
| Simple Material Heuristic | Black | 2 | 2 | 0 | 0 | — | 2 | 0 |
| Simple Material Heuristic | Both | 4 | 3 | 1 | 0 | 51.0 | 4 | 0 |

Across all eight games, all completed by chess termination: five checkmates and three insufficient-material draws. There were zero truncations, external failures, or interruptions. Per-game agent/opponent identities, color, seeds, outcomes, move counts, termination reasons, and UCI histories are in the structured report. The harness excludes non-completed episodes from W/D/L.

## Reproducibility and limits

An independent repeat used the same revision and configuration and matched the official run on configuration, aggregate summary, and all semantic per-game fields including UCI history. Runtime durations and run metadata are intentionally excluded from semantic equality. Repeat JSON SHA-256: `b08f856b33804529fd147f1a028998a7ec8cd0c7c0bbf98fbf17d3c86caeb1f2`.

The repeat is preserved at `M2-baseline-benchmark-repeat-20261016.json`; the official per-game report is `M2-baseline-benchmark-20261016.json`. A SHA-256 manifest records these and the ignored raw run artifacts. This is a small deterministic baseline comparison, not a strength study: only two seeds per color and policy were used. No Elo or learned competence is inferred. These are `python-chess` simulator results only; no ALE environment, ROM, Stockfish, dataset, or neural model was used.

## Reproduction

From the repository root in the locked project environment:

```bash
python -m videochess_rl.benchmark --seeds 20261016 20261017 --max-decisions 400 --output artifacts/m2/<new-run-id>.json
```

Use the recorded derived seeds/configuration and compare semantic fields; wall-clock and run IDs naturally differ.
