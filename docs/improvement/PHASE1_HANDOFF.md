# Phase 1 improvement campaign — execution in progress

Experiment: `videochess-improvement-20261103-v1`. Base accepted main:
`7415d821acf11dd3e07e4990c2f5539cfdf31916`. Feature branch:
`feature/videochess-performance-improvement-20261103`.

This campaign is authorized by the Project Owner's Phase 1 assignment on
2026-11-03 and is independent of completed M0–M7 governance. The historical
results remain final and attributable. Phase 1 authorizes local dataset
construction, bounded offline Stockfish supervision, M4 fine-tuning, and
short disposable M5 readiness probes. It excludes the official 250,000-decision
run, scratch or multi-seed training comparisons, merging, and artifact publication.

Current work is incomplete. Do not start Phase 2 from this interim document.
The final handoff will replace this execution pointer after verification.

Private outputs are retained under the ignored repository-relative directory
`artifacts/improvement/videochess-improvement-20261103-v1/`. They are not
transferred by Git. Required historical source files remain under
`artifacts/m3/`, `artifacts/m4/`, and the existing `.venv/` runtime.

The owner separately authorized local Optuna installation. Additional package
pins are in `configs/improvement/requirements.txt`; the historical `uv.lock`
and base dependencies remain unchanged. Recorded command evidence is under
`.agents/evidence/improvement/`; live RGB, move-level traces, source archive,
position records, engine labels, and model files remain local private artifacts.

The source provides independent dataset, M4, M5, benchmarking, recovery, and
local demo modules in `videochess_rl/improvement/`. The initial focused suite
passed 23 tests; the first full regression suite is still running. Completed
Atari smoke probes observed two player moves and two opponent replies. The
owner's existing Downloads GUI was preserved and additionally verified for
checkpoint loading, live display, verified history, and snapshot replay.

No official 250,000-decision training run or merge has occurred.
