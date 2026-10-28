# Pre-M5 Readiness Engineering Report — 2026-10-28

**Scope:** Engineering preparation for M5 only. This is not M5 authorization, M5 implementation/training, PM acceptance, G3 approval, or permission to merge. The PR author must stop at the PM review handoff under [PR_REVIEW_AND_INTEGRATION.md](../../docs/02-management/PR_REVIEW_AND_INTEGRATION.md).

## 1. Executive result

Pre-M5 engineering deliverables are prepared for independent PM review. The source baseline was `initial-idea` `906178775d48e98e64c709673bfe73177dd15c02`, matching the verified integration head at mission start. PRs #8 and #9 are merged there; this work is on a dedicated `feature/pre-m5-readiness` branch and does not write to `initial-idea` or `main`.

The exact M3 release and M4 checkpoint were found at the recorded local-only paths and independently verified. The M4-to-M5 representation-transfer dry-run used the real checkpoint and passed without Stockfish. Local CPU profiling stayed within its 15-minute and 2-GiB allowances. The algorithm, transition, experiment, checkpoint, test, resource, and future execution contracts are documented. No Double DQN learner, RL training, ALE learning, M5 authorization, PM acceptance, or G3 approval is claimed.

Final PR handoff details are recorded after pushing in the concluding PR section and in the final execution report. The PR must remain open and unmerged.

## 2. Starting repository and retrospective M4 audit (PM5-R01)

- Canonical remote at inspection: `origin/initial-idea` = `906178775d48e98e64c709673bfe73177dd15c02`; feature worktree `/tmp/atari-pre-m5-work`, branch `feature/pre-m5-readiness`.
- PR #8: [M4 implementation](https://github.com/dodaonam/atari-videochess-rl/pull/8), merged at `c0a284304d602817922772d08f0ff7904af7ae20`, implementation head `1f8f7db986f613818c7f70770d08c2c3a460a1cb`.
- PR #9: [M4 post-merge closeout](https://github.com/dodaonam/atari-videochess-rl/pull/9), merged at `906178775d48e98e64c709673bfe73177dd15c02`, head `19629ad3eecc4f16ccf5921ad28566a9b26e1744`.
- Read-only GitHub inspection reported no review submissions for PRs #8 or #9. Thus their merge is an integration fact, not evidence of the intended independent PM review. Record this as a **retrospective review-process exception**. This engineering audit is not independent PM approval; PM review of the historical implementation remains available and separate.
- Code was reviewed directly in `videochess_rl/model/{dataset,features,network,inference,checkpoint,training,cli}.py`, `simulator.py`, `action_contract.py`, `baselines.py`, and `benchmark.py`. Relevant focused tests and the full suite are rerun in this mission; earlier M4 test counts below are clearly labeled historical.
- Historical M4 records remain immutable, including the original 126/128 conflicting-input failure and diagnosis, the revised PM-approved selector and passing run, the r3 safe-load failure and fix, and the accepted final r4 run. M4 acceptance and post-merge records remain `.agents/evidence/M4-final-acceptance-20261027.md` and `.agents/evidence/M4-postmerge-delivery-verification-20261027.md`.

## 3. M3/M4 artifacts and transfer (PM5-R06)

Accepted M3 release: `/home/dodaonam/Projects/atari-videochess-rl-m3/artifacts/m3/training-support/release-final-closure-r6`.

- Release ID `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`.
- Manifest SHA-256 `be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12`.
- Split assignment SHA-256 `84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e`.
- 1,000 games; 19,268 retained positions; 15,196/2,015/2,057 train/validation/test; 732 purged positions; 182 rejected records. Exact identity was reverified during this mission and the nine-file inventory is retained in `logs/PRE-M5-M3-immutable-check-20261028.log`.
- The accepted curated source's broader redistribution license remains unstated. Data and derived records stay local/outside Git; no regeneration, resplitting, upload, or redistribution occurred.

Accepted M4 checkpoint: `/home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r4/pretrained-behavior-only.pt`, SHA-256 `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4`, 1,520,046 bytes. The read-only M4 artifact verifier accepted all 19 files; the run artifact inventory SHA-256 is `f00fde1c59325105e0ffd45bb45eb269dfa303416010c9a0b6c6be47bd9a9921`. Model/input schemas are `videochess-behavior-scorer/1.0` and `videochess-model-input/1.0`; the historical accepted parameter count is 121,897.

The transfer verifier was run in a separate process with `PATH=/usr/bin:/bin`. It loaded the real artifact through the safe loader, checked all 19 artifact files, transferred only shared representation weights, initialized a new Q head with seed `20261028`, copied the resulting online network to the target network, and scored representative legal UCI candidates through both the frozen behavior policy and untrained Q scorer. Both chosen moves were legal (`g1f3` and `a2a4`); `stockfish_path` was null and `chess.engine` was absent. The Q scorer is random-initialized and is not claimed as trained Q-values. Checkpoint and run bundle were verified unchanged before/after. See `scripts/verify_m5_transfer.py` and `logs/PRE-M5-transfer-verification-20261028.log`.

## 4. PM5 readiness matrix

| ID | Status | Work/evidence | Limitations / PM distinction |
|---|---|---|---|
| PM5-R01 | PASS | PR #8/#9 identities, source audit, M4 final/post-merge reports, and fresh M2–M4 focused regression evidence. | The full suite is being rerun from a clean clone after the canonical checkpoint is committed. No historical PR review submissions were found. The retrospective engineering record is not PM acceptance; PM should review M4 evidence independently if desired. |
| PM5-R02 | PASS | `docs/02-management/PR_REVIEW_AND_INTEGRATION.md`, `AGENTS.md`, requirements, test, and handoff define implement → verify → PR → independent PM decision → authorized human/operator merge. | Branch protection and repository settings are not modified. GitHub reported `initial-idea` unprotected and no rulesets; documentation/tests cannot enforce API permission. |
| PM5-R03 | PASS | M4-001 stale `next_action` cleared; preflight now rejects nonempty `next_action` on done/cancelled tasks with regression coverage. M5-001 is pending and references only M5-01–05. State remains inactive/unauthorized, G3 unapproved. | M5 direct authorization remains a future decision. |
| PM5-R04 | PASS | `docs/03-technical/RL_ALGORITHM.md` specifies input/output, semantic UCI, target equation, terminal/truncation, reward, replay, exploration, updates, numerical failures, transfer, and checkpoint contract; exact online/target disagreement fixture supplied. Automatic-draw terminal semantics distinguish raw Board moves from the empty bootstrap candidate set. | No Double DQN implementation or learner test is claimed. |
| PM5-R05 | PASS | M2 source and tests verify fixed agent color, Black reset opening, action+reply boundary, agent-perspective reward, terminal priority, valid truncation next state, failure rollback, history and legal UCI. The seventy-five-move test confirms a draw Board may still have legal chess moves. | Actual Double DQN bootstrap implementation remains untested until M5. |
| PM5-R06 | PASS | Real checkpoint manifest/load/transfer/inference dry-run; exact hash and unchanged bundle; engine-free child process. | Local external artifact paths are not available from repository-only clean clones; no artifacts were copied to Git. |
| PM5-R07 | PASS | `docs/04-research/M5_EXPERIMENT_PROTOCOL.md` and versioned `configs/rl/m5-double-dqn-v1.json` predeclare frozen M4, warm DDQN, scratch DDQN, two fixed M2 baselines, pairing, seeds, budgets, evaluation and statistics. | Values remain proposals pending PM review and separate M5 authorization; small profile is not proof of reward learning. |
| PM5-R08 | PASS | `scripts/profile_m5_feasibility.py` and final JSON log provide bounded local CPU measurements. | 32-transition/profile sample and synthetic backward only; replay size is JSON wire estimate, not heap measurement. The proposed budget includes explicit hard stops and uncertainty. |
| PM5-R09 | PASS | `RL_ALGORITHM.md` defines `videochess-ddqn-checkpoint/1.0`, episode-boundary resume, state ownership, atomic update, integrity and previous-good retention. | Actual M5 serialization/resume code remains M5 work. |
| PM5-R10 | PASS | `docs/06-quality/M5_TEST_MATRIX.md`, hand-calculated fixture, fixture regression test, and bounded standard-library CI addition. | Existing CI remains context/preflight plus fixture only, not PyTorch or DDQN correctness; full M5 tests are required in future. |
| PM5-R11 | PASS | `.agents/plans/M05-double-dqn.md` has prerequisites, baseline, modules, sequence, resources, tests, acceptance, recovery and stop conditions. | Plan is not authorization. |
| PM5-R12 | NOT_RUN | Candidate commit `83301abf6b85441d4fa63eab1376127066c4cdb1` passed clean-clone preflight/archive, 81 context/recovery tests, 124 focused M2–M4 tests, and all 318 full tests. The M3/M4 artifacts were reverified unchanged. Final verification is still required after the remaining protocol/fixture clarifications and PR creation. | `uv` is unavailable; use the already-present Python 3.12 project venv. One initial engine-free clean-clone invocation selected system Python and failed to import `chess`; the corrected run using the explicit venv interpreter passed with Stockfish absent. |

## 5. Resource feasibility profile (PM5-R08)

Command: `PATH=/home/dodaonam/Projects/atari-videochess-rl/.venv/bin:/usr/bin:/bin PYTHONPATH=. /home/dodaonam/Projects/atari-videochess-rl/.venv/bin/python scripts/profile_m5_feasibility.py --checkpoint /home/dodaonam/Projects/atari-videochess-rl-m4/artifacts/m4/m4-behavior-20261027-r4/pretrained-behavior-only.pt --max-seconds 300`.

On baseline source SHA `906178775d48e98e64c709673bfe73177dd15c02`, profile script SHA-256 `c7dab9b842e138f657424064dc375bfdf68b3a21b84d45ff61f9b380f5381e97`; executed 2026-10-28 03:47:05–03:47:08 UTC, exit 0. Python 3.12.3, PyTorch 2.14.1+cpu, NumPy 2.5.4, python-chess 1.11.2, Linux x86_64, CPU and one intra/inter-op thread.

- 32 verified simulator transitions: 1,418.23 steps/s for `ChessSimulator.step()` only (not end-to-end learned-policy throughput).
- Full-history replay p50/p95/max 0.438/0.970/1.141 ms; feature encode p50/p95/max 0.616/0.746/0.863 ms.
- Sampled history plies min/p50/max 0/15/38; legal candidate count 4/37/51. These are a short random-play sample, not M3 corpus percentiles.
- Batch 8 online+target forward p50/p95/max 3.981/5.257/8.054 ms; 82,166 legal candidate scores/s for the sampled batch; one synthetic AdamW backward/clip/update 12.435 ms.
- Online tensor state 487,588 bytes; online+target tensors 975,176 bytes; temporary online+target state serialization 997,385 bytes in 2.81 ms (excludes optimizer and replay).
- Sampled compact transition JSON wire size p50/max 744/1,121 bytes; 4,096 × max = 4,591,616 wire bytes only, not Python heap or encoded tensor cache.
- The final profile used 1.144 s and peaked at 333,541,376 bytes RSS. Including the earlier instrumentation iteration (1.139 s; 333,582,336 bytes peak), total active profiling time was 2.284 s and the overall observed peak was 333,582,336 bytes, below the 900 s mission cap and 2 GiB RSS limit. Neither run created a persistent replay artifact or performed RL training. Both logs are retained locally; the final measurements are in `logs/PRE-M5-feasibility-profile-final-20261028.log`.

These measurements support a conservative CPU-first starting proposal; they do not guarantee useful learning or completion of paired training. The protocol proposes 10,000 valid decisions per arm/seed, 45 minutes per run, 6 hours aggregate, 2 GiB RSS, 4,096 replay transitions, three paired seeds; recheck feasibility after M5 authorization and stop symmetrically when a hard cap applies.

## 6. Governance, state and integration boundary

- `G0/G1/G2` remain approved; `G3` remains unapproved. M4 is complete. M5-001 is pending, `next_milestone_status: pending_user_approval`, `start_authorized: false`, and no active milestone/task exists. M5 has not started.
- The stale completed M4 task action is cleared; its evidence is retained. M5-001 is not marked in progress and does not create a new PRE-M5 criterion ID.
- GitHub reported no `initial-idea` branch protection (`404: Branch not protected`) and an empty repository ruleset list. This mission changes no GitHub settings. The PR-only governance is explicit but not an administrative branch rule.
- This work is not merged. The PM independently reviews the PR and decides; only an authorized human/operator performs any merge. Do not enable auto-merge.

## 7. Verification results

Complete the table with exact final run times, final PR HEAD, exit codes, counts, CI URL and clean-clone status after the final commits:

| Check | Command / method | Result | Evidence |
|---|---|---|---|
| M3 release | `PYTHONPATH=. <pinned Python 3.12> -m videochess_rl.data.cli verify --release <accepted r6 path>` with before/after nine-file SHA list | PASS; 1,000 games, 19,268 positions, expected release/manifest; unchanged files | `logs/PRE-M5-M3-immutable-check-20261028.log` |
| M4 run bundle/checkpoint | `python -m videochess_rl.model.cli verify-artifacts <r4 path>` | PASS; 19 files; checkpoint hash `724ac…90a4`; 121,897 params | Output in Pre-M5 command log |
| Dependency/lock check | Pinned venv Python reads `pyproject.toml` and `uv.lock` and compares all four direct runtime package versions | PASS; Python 3.12.3, `ale-py 0.11.2`, `chess 1.11.2`, `gymnasium 1.4.0`, `torch 2.14.1+cpu`; no package changes. `uv` is unavailable, so the verified existing venv was used | `logs/PRE-M5-toolchain-check-20261028.log` |
| M4-to-M5 dry-run | `PATH=/usr/bin:/bin PYTHONPATH=. <venv>/python scripts/verify_m5_transfer.py` | PASS; legal behavior/Q actions, exact shared transfer, fresh head, target copy, Stockfish absent | `logs/PRE-M5-transfer-verification-20261028.log` |
| Feasibility profile | `scripts/profile_m5_feasibility.py ... --max-seconds 300` | PASS; 1.144 s, RSS 333,541,376 bytes | `logs/PRE-M5-feasibility-profile-final-20261028.log` |
| Context/recovery and history archive | `python3 scripts/migrate_checkpoint_history.py verify`; `python3 scripts/agent_preflight.py --json`; focused context/history tests | Candidate clean clone passed preflight with no errors and archive verification at 190 records, logical SHA-256 `f7d54e552d953dfcffd9b7fcbf9548cda003f9b1a6b092165237d048bc81a9b5`. The first dirty-worktree context run had three failures; two fixture/assertion issues were corrected and the remaining snapshot mismatch passed in the clean clone | Precommit diagnostics plus `logs/PRE-M5-cleanclone-preflight-83301ab.log`, `logs/PRE-M5-cleanclone-archive-83301ab.log`, `logs/PRE-M5-cleanclone-context-83301ab.log`; final exact-PR clone still required |
| Focused and full Python suites | Pinned Python 3.12 venv commands; exact test counts/exit codes below | Candidate clean clone passed focused 124/124 and full 318/318 (101.153 s); final exact-PR clone still required after the latest documentation/oracle updates | `logs/PRE-M5-cleanclone-focused-83301ab.log`; `logs/PRE-M5-cleanclone-full-83301ab.log` |
| Terminal/action oracles | `tests.test_m5_contract_fixtures` plus `tests.test_m2_simulator.ChessSimulatorTests.test_seventyfive_move_rule_is_automatic_after_full_transition` | PASS; 3 tests; the automatic-draw Board has 19 raw legal moves while the MDP bootstrap candidate set is empty and target equals draw reward 0 | `logs/PRE-M5-terminal-draw-oracle-20261028.log` |
| M3/M4 artifact and transfer checks | M3 release verifier; M4 bundle verifier; engine-free transfer verifier with explicit venv interpreter and Stockfish-free PATH | PASS on candidate clone: M3 identity/counts match; M4 19-file bundle and exact checkpoint verify; transfer copy semantics, legal actions, target initialization, no engine import, and source immutability pass. One initial wrong-interpreter invocation failed and is preserved separately | `logs/PRE-M5-cleanclone-m3-83301ab.log`, `logs/PRE-M5-cleanclone-m4_bundle-83301ab.log`, `logs/PRE-M5-cleanclone-transfer-engine-free-wrong-python-83301ab.log`, `logs/PRE-M5-cleanclone-transfer-engine-free-corrected-83301ab.log`, `logs/PRE-M5-cleanclone-artifact-inventory-83301ab.json` |
| GitHub CI | Exact workflow/run URL for PR head | Pending; PR has not yet been opened | Recorded after push |
| Clean clone | Fresh clone of exact final PR HEAD; preflight/archive/focused/full suite and clean status | Pending; must run after the final branch commit | Logs recorded after commit |

Captured test logs preserve test names, statuses, summaries, and exit codes. A whitespace-only trailing-space cleanup was applied to one captured diagnostic line after `git diff --check` identified it; the original semantic failure output remains intact.

## 8. Next step and limitations

Next action: independent PM review of the open Pre-M5 PR. A PM decision does not itself authorize M5; a separate direct M5 authorization and canonical state transition remain necessary. This report does not claim instructor approval, G3, M5 implementation, M5 training, or ALE learning.

Nonblocking limitations: the M3 dataset license remains unresolved for redistribution; M3/M4 artifacts are local-only; `initial-idea` lacks configured branch protection; M4 #8/#9 lack GitHub review submissions in the available record; recurrent compression and DDQN target parity have not been tested in a learner; the small profile does not establish M5 learning quality or throughput at scale; M6 simulator-to-ALE parity remains future work.
