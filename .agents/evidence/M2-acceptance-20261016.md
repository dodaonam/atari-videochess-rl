# M2 acceptance review — 2026-10-16

**Scope:** M2-01 through M2-04 only. This engineering milestone is within G3; this record does not approve G3 or resolve O-01 through O-08.

## Acceptance matrix

| Criterion | Requirement | Implementation and verification | Result | Evidence |
|---|---|---|---|---|
| M2-01 | State, legal actions, transition boundaries, player perspective, reward, terminal, and truncation are explicitly specified. | `videochess_rl/simulator.py` uses one history-preserving `chess.Board`; immutable observations and copied board views; legal `chess.Move` actions with UCI identity; fixed episode color; agent move plus at most one opponent reply; terminal-only agent-perspective rewards; automatic outcomes; decision-boundary truncation. Focused and full suites passed. | PASS | `docs/03-technical/MDP_SPEC.md`; `tests/test_m2_simulator.py`; focused/full logs below. |
| M2-02 | Rule and transition tests cover special moves and game-ending conditions supported by the selected simulator. | Tests cover ordinary moves, capture, castling, en passant, all four promotions, checkmate, stalemate, insufficient material, fivefold repetition, 75-move outcome, illegal/stale action atomicity, perspective, both terminal boundaries, precedence, reset, opponent errors, and seeded history. | PASS | `tests/test_m2_simulator.py`; 41 focused M2 tests and 163 repository tests passed. |
| M2-03 | Random-legal and heuristic agents complete simulator games; tournament metrics are saved with seeds/opponent identities. | Both seeded engine-free baselines played four games each across White and Black. All 8 games completed; per-game seeds, identities, color, outcome, length, termination reason, and moves are retained. Repeat semantic records match. | PASS | `videochess_rl/baselines.py`; `videochess_rl/benchmark.py`; `M2-baseline-results-20261016.md`; JSON and benchmark logs. |
| M2-04 | Simulator results and ALE integration metrics remain separate. | Benchmark records `metric_source=chess_simulator`, `ale_metrics_included=false`, and `rating_claim=null`; tests assert the distinction. M1/ALE modules were not changed. | PASS | `videochess_rl/benchmark.py`; `tests/test_m2_benchmark.py`; benchmark JSON and result report. |

## Verification executions

All test commands used the existing locked virtual environment with Python 3.12.3 and python-chess 1.11.2. No dependency was installed.

| Check | Command | Result | Provenance |
|---|---|---|---|
| Focused M2 suite | `/home/dodaonam/Projects/atari-videochess-rl/.venv/bin/python -m unittest tests.test_m2_simulator tests.test_m2_baselines tests.test_m2_benchmark -v` | PASS; 41 tests, 0.117 s, exit 0 | `.agents/evidence/logs/M2-focused-suite-final-20261016.log`; source revision `74008b8c8705809330ef218ba3d5bd9e1b5335ab`; finished `2026-10-16T07:39:04Z` |
| Full repository suite, including M0/M1 and context recovery | `PATH=/home/dodaonam/Projects/atari-videochess-rl/.venv/bin:$PATH /home/dodaonam/Projects/atari-videochess-rl/.venv/bin/python -m unittest discover -s tests -v` | PASS; 163 tests, 82.274 s, exit 0 | `.agents/evidence/logs/M2-full-suite-postcheckpoint-20261016.log`; revision `f5987e09d3cfa3f7ab5a50f401ec8e41329f0316`; finished `2026-10-16T07:45:27Z` |
| Completed-state full repository suite | Same full-suite command | PASS; 163 tests, 81.679 s, exit 0, including clean-clone recovery against M2-001 done and M3 pending authorization | `.agents/evidence/logs/M2-full-suite-complete-state-20261016.log`; revision `a4d015c2a272daab165666bbe886240a65e32a4e`; finished `2026-10-16T07:48:07Z` |
| Pre-checkpoint clean-clone regression attempt | Same full-suite command | FAIL; 162 passed. The recovery assertion found that documentation/state edits had not yet been checkpointed. After refreshing the checkpoint, the same full-suite command passed all 163 tests, including clean-clone recovery. The raw failed result is retained. | `.agents/evidence/logs/M2-full-suite-final-20261016.log`; resolved by the passing post-checkpoint run below. |
| Context consistency | `python3 scripts/agent_preflight.py` | PASS at revision `a4d015c2a272daab165666bbe886240a65e32a4e`; next milestone M3 is pending user approval; generic artifact-directory warning reviewed and M2 manifest retained | `.agents/evidence/logs/M2-preflight-complete-state-20261016.log` |
| Baseline benchmark | See exact command in results report | PASS; 8/8 completed; exit 0 | `M2-baseline-benchmark-20261016.json`, `.agents/evidence/logs/M2-baseline-benchmark-final-20261016.log` |
| Benchmark replay comparison | Compare configuration, summary, and semantic per-game fields for official and repeat JSON | PASS; exact match | `.agents/evidence/logs/M2-baseline-reproducibility-20261016.log` |

## Limitations and boundary

The baseline sample is intentionally small and does not establish general playing strength. Standard `python-chess` outcomes do not prove parity with the Atari ROM. No ALE metrics, Elo, Stockfish evaluation, data labeling, model training, or M3–M7 work is claimed. G3 remains unapproved and O-01 through O-08 remain open. The completed-state post-checkpoint full-suite and preflight both passed. GitHub branch/PR delivery is independently recorded in [M2 GitHub delivery verification](M2-github-delivery-20261016.md). The repository continues to report the generic `ARTIFACT_MANIFEST_REQUIRED` notice because `artifacts/` is excluded from content hashing; `artifacts/m2/MANIFEST-20261016.sha256` and the tracked evidence manifest provide the independent M2 hashes.
