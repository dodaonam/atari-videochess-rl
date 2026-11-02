# M4 Post-Merge Delivery Verification — 2026-10-27

## Result

**PASS — M4 implementation PR #8 is merged into `initial-idea`, and the actual merge commit passed clean-clone verification.** This report records the delivery/integration checks only. The M4 technical criteria and experiment evidence remain in the [M4 final acceptance report](M4-final-acceptance-20261027.md); that report's pre-merge provenance is preserved.

## Integration identity

- Repository: `dodaonam/atari-videochess-rl`
- Pull request: [#8](https://github.com/dodaonam/atari-videochess-rl/pull/8), merged, non-draft, target `initial-idea`
- Final PR head: `1f8f7db986f613818c7f70770d08c2c3a460a1cb`
- Merge commit and verified `initial-idea` HEAD: `c0a284304d602817922772d08f0ff7904af7ae20`
- Merged at: `2026-10-27T17:06:43Z`
- Required GitHub check: Repository preflight / `context`, success; [run/job](https://github.com/dodaonam/atari-videochess-rl/actions/runs/40547210455/job/122340909781). This is a context/preflight workflow, not the Python regression suite.
- A fresh clone at `/tmp/atari-m4-postmerge-clean-c0a2843` checked out the exact merge commit. The captured initial and final worktree states were clean.

## Post-merge verification

All commands below ran in the fresh clone at the exact merge commit. The test interpreter was the already verified project Python 3.12 environment; the clone used it read-only through the recorded absolute interpreter path.

| Check | Result |
|---|---|
| `python3 scripts/agent_preflight.py --json` | Exit 0; `ok: true`, zero errors, portable tracked manifest matched. The only warning was `ARTIFACT_MANIFEST_REQUIRED`; the external M4 artifact was independently verified below. |
| `python3 scripts/migrate_checkpoint_history.py verify` | Exit 0; archive status `verified`, 186 records, logical SHA-256 `59ab0ad59f99aefc7ae5d336e03a9543bc7ee387fbd637b09dd476f7af3c8b71`. |
| `PATH=/home/dodaonam/Projects/atari-videochess-rl/.venv/bin:/usr/bin:/bin PYTHONPATH=. /home/dodaonam/Projects/atari-videochess-rl/.venv/bin/python -m videochess_rl.model.cli verify-artifacts /home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r4` | Exit 0; all 19 artifact files verified. The behavior-only checkpoint is 1,520,046 bytes, SHA-256 `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4`; model schema `videochess-behavior-scorer/1.0`, input schema `videochess-model-input/1.0`, 121,897 parameters. |
| Focused M4 and compatibility suite | Exit 0; 124 tests passed in 45.583 s. |
| Full Python regression suite | Exit 0; 313 tests passed in 99.379 s. |
| Final clone worktree | Clean. |

Exact sanitized outputs and per-command timestamps are in:

- [integrity/preflight/archive/artifact log](logs/M4-postmerge-clean-clone-integrity-c0a2843-20261027.txt), SHA-256 `a59c089c8a4680d3045c6126f4a80ab47008c91eec1d50c98c652b239f560f97`
- [focused-suite log](logs/M4-postmerge-clean-clone-focused-c0a2843-20261027.txt), SHA-256 `adda6f7b274e066894716e8f301ae839907d46f425ca5d1511df4ab65aadfd31`
- [full-suite log](logs/M4-postmerge-clean-clone-full-c0a2843-20261027.txt), SHA-256 `08f9e57cd537c59c94067e662d9c46a70dd164eadc5e0f96563d1423d3d0d3f9`

## Acceptance and limits

M4-01 through M4-04 remain **PASS** on the evidence in the [technical acceptance report](M4-final-acceptance-20261027.md), including the revised M4-02 gate, bounded three-seed behavior-cloning runs, validation-only checkpoint selection, one frozen test evaluation, and the prescribed 40-game simulator evaluation. This post-merge verification additionally establishes that the merged tree, archive, external checkpoint bundle, and regression suite are recoverable/valid at the actual integration SHA.

M4 is supervised PGN played-move behavior cloning. It is not Double DQN, an Elo result, or Atari/VideoChess ALE performance. The model artifact and accepted M3 release remain outside Git at their approved local paths; this report does not claim those external artifacts are portable in a repository-only clone. The preflight artifact warning is expected and is resolved for the M4 checkpoint by the explicit 19-file manifest verification above. G3 remains unapproved; M5 has not started and is not authorized by this M4 task.
