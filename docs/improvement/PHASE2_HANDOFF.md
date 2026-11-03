# Phase 2 Handoff

## Current state

The authorized Phase 2 work is complete through one official training run, snapshot selection, reserved simulator evaluation, bounded actual-ALE evaluation, two live GUI smoke tests, and implementation. The feature branch must remain unmerged. The final state is awaiting the independent PM's review of one open PR targeting `main`.

PR #24: [Post-closeout VideoChess improvement](https://github.com/dodaonam/atari-videochess-rl/pull/24). It is open, non-draft, targets `main`, and is unmerged. The current PR head and clean-clone verification are recorded in `.agents/evidence/improvement/phase2-final-verification.json`; check status is also visible on the PR.

The branch now includes [`PM24_REMEDIATION.md`](PM24_REMEDIATION.md). The
current evidence tip is sanitized, but the original sequence-bearing commit
remains reachable from the PR history. A squash integration can keep that
intermediate patch out of `main`; the Independent PM/Project Owner must decide
and authorize the integration method. The PR must remain open and unmerged
until that history decision is resolved.

| Identity | Value |
|---|---|
| Experiment | `videochess-improvement-20261103-v1` |
| Base `main` | `7415d821acf11dd3e07e4990c2f5539cfdf31916` |
| Feature branch | `feature/videochess-performance-improvement-20261103` |
| Initial Phase 2 implementation push | `5b9f93f3092a8e9b97c4061813bbd150bdd1b837` / `03346066361e7a14a3396bee2bea00282604a2c9` |
| Training seed | `20261103` |
| M4 source SHA-256 | `cf5e437ff4e2d6a8e85739df751dec33f16b7bc4c92268f996ec4c612d62feed` |
| Training config SHA-256 | `2cfe2805edd3e05756fd3ef981a6e4441e3b4ad717649d5647085228e837aabd` |
| Training code SHA-256 | `cf329438880a82b7b39b05b8f1f3bc1af21e262edb4143e1035e494f891a5705` |
| Selected Q snapshot | 250,000 decisions; `48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293` |

The code digest is the frozen identity recorded in the official attempt. Later commits only add bounded evaluation, GUI progress hooks, demo loaders, tests, and reporting. They do not change or relabel the official training source.

## Private artifacts

Private assets remain in the ignored local path namespace `artifacts/improvement/videochess-improvement-20261103-v1/`:

- Dataset release `dataset-v4`, identity `f2b3b52724958ffa845894681013cdc40915da179bbec3ae011087fe8a8ce0cc`.
- Stockfish labels and M4-A artifact recorded in the Phase 1 handoff.
- Official attempt `official/attempt-0000/` with run summary, replay journal, action-source events, resource telemetry, 11 Q-only snapshots, 249 resumable episode-boundary checkpoints, and integrity sidecars.
- Simulator development selection and raw scenario rows under `official/simulator-development/`.
- Reserved simulator results and private raw rows under `official/simulator-final/`.
- Corrected Atari traces and captured frames under `official/atari-evaluation-corrected/`.
- Local actual-ALE GUI traces/frames under `live-demo/`.

Do not copy these payloads into Git. The tracked `.agents/evidence/improvement/phase2-*.json` records aggregate identities and outcomes without raw games or image data.

## Selected models and findings

- Official M4 source: M4-A, SHA `cf5e437ff4e2d6a8e85739df751dec33f16b7bc4c92268f996ec4c612d62feed`.
- Selected Double DQN: snapshot at 250,000 decisions, SHA `48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293`.
- Simulator development: selected Q score 0.9083 over 60 games.
- Reserved simulator final: selected Q 0.8750 (30 wins, 10 draws); M4-A 0.8875 (31 wins, 9 draws); historical M5 0.4750 (3 wins, 32 draws, 4 losses, 1 truncation), 40 games each.
- Actual Atari: no terminal result was observed. Q attempts stopped at target-confirmation uncertainty after nine verified turns; M4-A reached a 12-turn cap in each attempt.
- Demo: both families loaded and completed a two-turn live smoke with verified opponent replies, resize, backward/forward replay, and clean exit.

Simulator scores are not Atari scores. The Q model's actual Atari moves are legal and Q-only; no Stockfish process or M4 exploration assistance is used at inference.

## Reproduction commands

Run the repository suite:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Use the M4-A live demo fallback:

```bash
PYTHONPATH=. .venv/bin/python -m videochess_rl.improvement.demo \
  --policy m4-a --max-player-moves 24 --max-seconds 900
```

Run the selected Double DQN snapshot explicitly:

```bash
PYTHONPATH=. .venv/bin/python -m videochess_rl.improvement.demo \
  --policy double-dqn \
  --checkpoint artifacts/improvement/videochess-improvement-20261103-v1/official/attempt-0000/snapshot-250000.pt \
  --checkpoint-sha256 48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293 \
  --max-player-moves 24 --max-seconds 900
```

The official training command is preserved in `official/attempt-0000/official-start.json` and this report records that it completed; **do not run it again**. Its target has been met. There is no Phase 2 recovery/resume action required.

The accepted Stockfish 19 executable is already present in this local virtual
environment and matches the recorded Phase 1 SHA-256. To run the full suite,
include its directory in the process path:

```bash
PATH="$PWD/.venv/share/stockfish:$PATH" .venv/bin/python -m unittest discover -s tests -v
```

This enables only the existing UCI readiness test. No Stockfish search or
labeling is part of Phase 2.

## Recovery and artifact interpretation

The official run ended at the requested valid-decision target with an incomplete final episode. The latest resumable checkpoint is at decision 249,174; the last 826 transitions exist in the full verified journal but follow that completed-episode checkpoint. The final evaluation snapshot at 250,000 contains the learned Q weights at the target. Since the training objective completed, do not resume or launch a second attempt.

The run used one seed and one warm arm. No scratch comparison, additional seed, additional HPO, further Stockfish labelling, or new training campaign was run.

## Remaining action

Independent PM review is the next action after the feature branch and its single non-draft PR are verified. Do not merge, approve on behalf of the PM, enable auto-merge, release, deploy, or publish private artifacts.
