# Phase 2 Verification Ledger

## Revision and source identity

- Base `main`: `7415d821acf11dd3e07e4990c2f5539cfdf31916` (unchanged at final verification).
- Phase 2 source/implementation push before final state checkpoint: `0596698249d74da4dd9184a12975f83efd08bca3`.
- Final Phase 2 checkpoint revision: `17804732a4bd8a11a5e63b17bbc18d8bad242c77`.
- Official training start source revision/tree: `76c898ed0dd8a2e8bf0c76cbd8565f83077284e0` / `b5877036a2e954c085e0da386c0bcb596ff21ab3`.
- Frozen training code/config/M4 digests are in `phase2-training-summary.json` and `phase2-pre-run-freeze.json`.

## Commands and outcomes

| Command / operation | Revision | Result | Evidence |
|---|---|---|---|
| `python3 scripts/agent_checkpoint.py` then `python3 scripts/agent_preflight.py` after implementation commit | `0596698` | Checkpoint written; preflight PASS; artifact-manifest warning is expected because private `artifacts/` are excluded from Git hashes | canonical `.agents/state/PROJECT_STATE.yaml`, checkpoint history |
| `python3 scripts/agent_checkpoint.py` then `python3 scripts/agent_preflight.py` after checkpoint commit | `1780473` | Preflight PASS; clean workspace with expected portable commit/checkout transition; 1,446 ordinary files SHA-256 checked; artifact-manifest warning expected | canonical state and handoff |
| Focused portable-checkout, context recovery, G5/M7 state tests | `1780473` | 6 passed | execution retained in session; clean-clone and governance invariants pass |
| `.venv/bin/python -m unittest discover -s tests -v` | `1780473` | 550 tests: 545 passed, 4 skipped, 1 failed | `.agents/evidence/improvement/phase2-full-tests-final.json`; local raw log SHA-256 `d533f1db5d33c2589b4a1e8c196baf054b794a42c4bf2e8504ab5597830bd477` |
| Focused clean-clone/context/G5 tests, Phase 2 accounting tests, syntax compilation, whitespace check, and fresh M5/demo/Atari-eval CLI help | `66603bc4dc7cf79475445cedcb6b38c4f1082dde` | All 7 command groups passed; clean-clone/context tests 6/6 passed | `.agents/evidence/improvement/phase2-focused-verification.json` |
| Fresh clone from the pushed feature branch at final review verification | `a8d0f36acf6288cac1ff64c71ed2843ca402fc5b` | Clean tree; preflight PASS with expected artifact-manifest warning; 5 tests passed | `.agents/evidence/improvement/phase2-clean-checkout-verification.json` |
| `python3 -m py_compile videochess_rl/episode.py videochess_rl/improvement/{demo,live,policies,atari_eval}.py ...` and `git diff --check` | source worktree before final commit | Passed | commands were run before the implementation commit; `git diff --check` also passed for the staged commit |
| `PYTHONPATH=. .venv/bin/python -m unittest tests.test_phase2_evaluation tests.test_phase2_atari_demo -v` | source worktree before final commit | 5 passed | targeted output retained in local execution history; committed tests are included in the full suite |
| `PYTHONPATH=. .venv/bin/python scripts/improvement/phase2_evaluate.py --mode dev` | evaluator fix commit `de9692582a1fd387f775903bff6e5495868233a4` | 11/11 candidates stage 1; 3 finalists extended; selection completed in 265.98 s | local `.agents/evidence/improvement/phase2-simulator-development.log`; aggregate `phase2-simulator-development.json` |
| `PYTHONPATH=. .venv/bin/python scripts/improvement/phase2_evaluate.py --mode final` | `de969258` | 40 scheduled matched scenarios for selected Q, M4-A, and available historical M5 | local `.agents/evidence/improvement/phase2-simulator-final.log`; aggregate `phase2-simulator-final.json` |
| Corrected six-attempt actual ALE evaluation with `--output-name atari-evaluation-corrected` | `1780473` | Six bounded attempts completed; no terminal W/L/D observed | `phase2-atari-evaluation.json`; private raw traces remain local |
| Live GUI `--auto-smoke`, `double-dqn` and `m4-a` | `1780473` | Both real-ALE smokes showed 2 verified turns/replies, resize and arrow replay; clean exit | `phase2-demo-verification.json`; raw traces/frames remain local |

## Full repository suite detail

The exact full-suite command ran from pushed revision `17804732a4bd8a11a5e63b17bbc18d8bad242c77`. The later revision `66603bc4dc7cf79475445cedcb6b38c4f1082dde` refreshes only canonical checkpoint/archive state; it changes no Python, test, configuration, or evaluation code. One failure remains:

```text
test_stockfish_answers_uci_readiness_without_searching
AssertionError: Stockfish must be available in the project environment PATH.
```

`stockfish` is absent from the current environment (`command -v stockfish` returned no executable). Phase 2 does not use an engine at inference or training time, and the assignment explicitly forbade additional engine labeling/search campaigns. No package or system configuration was changed to satisfy this readiness-only test.

The four skips are private-artifact-dependent historical tests: selected/local M4 initialization in one test; the private M4/M5 roster test class; and two private historical M5 policy compatibility tests. The Phase 2 M4-A, Q snapshot, sidecars, replay journal, and related manifests were verified separately; those skips are not counted as passes.

## Official training integrity

- Official command and start identity: private `official/attempt-0000/official-start.json`.
- Run summary: private `official/attempt-0000/run.json`, SHA-256 recorded in `phase2-artifact-integrity.json`.
- 250,000 journal entries: SHA chain, transition schema, unique IDs, sequential decision indexes, legal move reconstruction, seed/run identity, and action-source event alignment passed a complete streamed semantic check.
- The pinned resume checkpoint at 249,174 decisions verified its sidecar, full journal prefix, config/code identity, optimizer/target counters, and replay state.
- All eleven scheduled snapshots loaded Q-only, had valid sidecars and matching frozen identity metadata, and had finite parameters.
- Run counters: 250,000 valid decisions, 62,245 optimizer updates, 124 target synchronizations, 3,203 completed episodes, 23,417.4 cumulative seconds.
- One attempt directory, one training seed, zero recovery resumes, zero replayed parent-tail decisions.

The full semantic replay audit took 1,977.74 seconds. Its integrity result is retained as aggregate counts and chain head in `phase2-artifact-integrity.json`; transition payloads remain private.

## Evaluation limitations and corrections

- The first simulator command resolved the wrong artifact root and exited before any scenario/output was created. The path fix was committed and tested before candidate scoring.
- The first Atari harness reused one RGB adapter across independent ALE resets. It conservatively rejected later resets as stale frames. All first-run traces were preserved locally; the corrected harness now creates a fresh adapter for every ALE episode and completed all six paired attempts.
- The run-time simulator-final evaluator did not capture an explicit start timestamp. Its configured schedule, evaluation seeds, rows, policy outcomes, and actual evaluator duration are retained; no start timestamp has been reconstructed or invented.
- The actual Atari attempts did not reach a terminal game result. The runner's bounded/control outcomes remain incomplete and are not converted into wins, losses, or draws.

## Publication and scope checks

- Private dataset/model/label/replay/ROM/frame/raw-trace directories are ignored by Git and remain local.
- The public evidence files contain aggregate metrics, repository-relative identity paths, and checksums only.
- The accepted historical M0–M7 results were preserved. No merge, auto-merge, approval, release, deployment, or new training campaign occurred.
- The exact branch push, final clean-checkout verification, PR URL/state/checks, and final tree identity are recorded in the final machine-readable verification record and PR after it is created.

## Pull request

- PR #24: [Post-closeout VideoChess improvement: single-seed warm DDQN, evaluation and live demo](https://github.com/dodaonam/atari-videochess-rl/pull/24).
- Created open and non-draft, targeting `main`; not merged and no auto-merge enabled.
- Repository-preflight check `context` passed on PR head `a8d0f36acf6288cac1ff64c71ed2843ca402fc5b` at 2026-11-03T10:55:45Z; GitHub reports the PR merge state as clean and the PR remains open/unmerged.

## Independent PM review remediation

The original full-suite failure was environmental: the UCI readiness test
searched `PATH` while the already-installed Stockfish 19 executable lived at
`.venv/share/stockfish/`. The remediation run prepended that existing directory,
verified the binary SHA-256 against the accepted Phase 1 identity, passed the
focused UCI test, and reran the complete suite. No package was installed and no
engine search or labeling was performed. See
`.agents/evidence/improvement/phase2-remediation-verification.json` for the
exact command, revision, totals, timestamps, and log digest.

The current tracked Atari aggregate excludes the 63 move-level UCI records and
private trace paths, while retaining per-attempt seeds, aggregate counts,
outcomes, stop categories, policy/checkpoint identities, and private trace
SHA-256 values. The generator now emits only that aggregate schema. The
sequence-bearing evidence was introduced in commit
`0596698249d74da4dd9184a12975f83efd08bca3`, which remains reachable from the PR
branch. No history rewrite was performed. A normal merge commit would include
that history; squash integration of the sanitized tip would not import those
intermediate commits into `main`. The owner/PM must decide the integration
method. The PR remains open and unmerged pending that decision.

The updated head/tree terminology distinguishes the official training source,
implementation/test revisions, the head at PM review, and the revision at
which final verification metadata was written. These identities are separate
in the remediation record; none replaces the frozen training-source or code
digest.

The three target-confirmation failures were traced to the post-FIRE Atari
confirmation stage after legal action selection and RGB-verified source/target
selection. Since no safe fix could be established, the runner still stops
without retrying. The demo now displays a custom Atari reset seed separately
from the model training seed. Development checkpoint selection compares only
the precommitted extended finalists; the existing 250k selection remains
valid. Full finding evidence and limitations are in
[`PM24_REMEDIATION.md`](PM24_REMEDIATION.md).
