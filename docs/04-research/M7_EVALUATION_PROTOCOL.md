# M7 Evaluation Protocol

**Protocol ID:** `M7-EVAL/1.0.0`
**Status:** Proposed for owner and independent PM review; not approved for execution.
**Date:** 2026-10-31.
**Acceptance ownership:** M7-01–M7-03 are G4 evaluation evidence; M7-04–M7-05 are G5 delivery evidence. See [ACCEPTANCE_CRITERIA.md](../06-quality/ACCEPTANCE_CRITERIA.md) and [ADR-0001](../02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md).

This contract supports Pre-M7 preparation only. It does not authorize a new simulator/ALE campaign, training, fine-tuning, cloud allocation, Stockfish role, G4/G5 approval, or release. Proposed branches below remain **NOT AUTHORIZED** until the owner separately approves the final protocol, exact populations, and resource envelope and records direct M7 authorization.

## 1. Scientific questions

1. Did Double DQN improve measured M2 simulator performance for Warm-start and Scratch relative to each arm's own initialization?
2. Under controlled conditions, how do final RL policies compare with frozen M4, RandomLegal, and SimpleHeuristic baselines?
3. What does accepted ALE evidence establish about actual RGB observation → legal decision → controller action → verified reply closed-loop execution?
4. Which performance, superiority, independent generalization, and Elo claims remain unsupported or inconclusive?
5. Which additional owner-authorized evaluation, if any, would materially strengthen the academic conclusion within the compute/deadline limits?

## 2. Evidence tracks and populations

Results from the following tracks have different outcomes and denominators. They must be reported in separate sections and cannot be pooled into one performance estimate.

### 2.1 Supervised pretraining (M4)

| Population | Identity and conditions | Valid metric / interpretation |
|---|---|---|
| Accepted frozen model | Run `m4-behavior-20261027-r4`; selected seed `20261024`, epoch 11; checkpoint SHA-256 `724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4`; sidecar SHA-256 `63615d8d0ed27900fdf86d3f3084ca95cd562f9ec2f9a7e94bca4b0f6301e0c8`; root manifest SHA-256 `f00fde1c59325105e0ffd45bb45eb269dfa303416010c9a0b6c6be47bd9a9921`. Input/model contracts are `videochess-model-input/1.0` / `videochess-behavior-scorer/1.0`. | One frozen held-out test pass over 2,057 positions / 61,419 legal-candidate evaluations: legal top-1 29.8979%, top-3 54.3996%, MRR 0.46437. This measures agreement with played historical moves. It is not W/D/L, win rate, Elo, chess strength, RL improvement, or Atari performance. |

The M3 release is the accepted local training data dependency (release ID `f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890`, manifest SHA-256 `be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12`). Its redistribution license remains unstated; no source data is part of M7 output.

### 2.2 M2 simulator RL (M5)

| Population | Identity and conditions | Denominator and limitations |
|---|---|---|
| Warm-start and Scratch RL | Config SHA-256 `84d305084397ad18397dfe395fab58de824fa056729675d0d1cd9ca8bdd06d8d`; root manifest SHA-256 `a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c`; six runs, 3 paired training seeds (`20261104`–`20261106`), 50,000 valid decisions per run. Final checkpoint hashes are recorded per seed in `.agents/evidence/M5-training-campaign-verification-20261029.json`. The M6-selected seed-20261104 post-RL snapshots are Warm `0b2405017a8e1d539851f0cd278883d3fd23936fb5c2f7962c813590a6fd1767` and Scratch `3749b0c0b6ae44d3ad5d6bf0863b60937a59fbe881e0bdf4932bdce6033ca400`. | Frozen schedule: 25 evaluation seeds (`20261130`–`20261154`), RandomLegal and SimpleHeuristic opponents, both agent colors, one game per opponent/color/seed/policy. Fifteen policy groups × 100 rows = 1,500 rows; 1,494 terminal games, 6 time-limit truncations. Rows share training-seed and evaluation-seed clusters; 1,500 is not an independent replication count. |

The 15 policy groups are the M4 behavior-only policy; Warm and Scratch initialization and post-RL policies for each of the three training seeds (12 groups); RandomLegal; and SimpleHeuristic. Existing accepted measurements can be reused without running any new game. The primary terminal-only scores reported for M5 were M4 `0.730`, RandomLegal `0.320`, SimpleHeuristic `0.645`; the six post-RL seed-specific Warm/Scratch scores are in [M5_FINAL_REPORT.md](M5_FINAL_REPORT.md).

M5 reported Warm post-minus-pre score `+0.296` and Scratch `+0.185`; terminal-only Warm-minus-Scratch estimates were `−0.056` pre-RL and `+0.062` post-RL. Six truncated scenarios censor some matched pairs, so the four campaign-level primary comparisons have point estimates without bootstrap intervals. The post-hoc capped-reward sensitivity (10,000 crossed resamples over 3 training-seed and 25 evaluation-seed clusters) is secondary; its post-RL Warm-minus-Scratch 95% interval was `[−0.003, 0.118]`. Three training-seed pairs make the comparison statistically limited; no Warm-start superiority is established. RSK-014 remains an accepted historical CLI-source limitation; do not claim byte-identical whole-campaign source reconstruction.

### 2.3 Real ALE Atari evaluation (M6)

Both versions used `ALE/VideoChess-v5`, agent White, mode 4, difficulty 0, RGB, frameskip 4, repeat-action probability 0.25, and ROM SHA-256 `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`. Report each version separately:

| Protocol | Frozen population / schedule | Horizon and run identity |
|---|---|---|
| Stage 3 v1 | Five policy groups (M5 Warm/Scratch seed 20261104 post-RL, M4 behavior-only, SimpleHeuristic, RandomLegal); 35 scheduled attempts and ten ALE seeds `20261130`–`20261139` (baseline policies on the first five). | Config SHA-256 `05aedeb30efb8b6b97667c44f9d606b58d4da8ae20800d4ef143e629420cebac`; run `m6-stage3-ad3998200e31-c5ff389dc4fe`; 54,000-frame episode limit, 20,000 opponent-wait frames, 900 sec/attempt; 36,000 sec shared M6 diagnostic/evaluation wall budget. Root manifest SHA-256 `22ac6ec7e0f4a48f52b2452654d4adecaf111f38ea37f5d9517f173c838716d7`, 4,540 files / 616,539,017 bytes. |
| Stage 3 v2 | Two frozen M5 post-RL policies from training seed 20261104: Warm checkpoint `0b240501…`, sidecar `80d8689e4b349576c5708bb4dce3451e5a8c64d81470cd6f4273a4746844b682`; Scratch checkpoint `3749b0c…`, sidecar `1c15e5bc4ba2437df113671dc316accbdfe6d8b59069ed29ed187daebf4fff1e`. Ten paired ALE seeds `20261130`–`20261139`, 10 attempts per policy, Warm first on even seeds and Scratch first on odd seeds. | Protocol `M6-Stage3-v2-extended-horizon-frozen-m5`; config SHA-256 `663651050db80ab027b452241c7d39837ec7986927c0aefc7c7be631f459a49b`; run `m6-stage3-v2-91f51b14690e-d05d42400cfc`; registered default frame horizon 108,000, effective ALE horizon 500,000, runner post-reset limit 432,000, 1,800 sec/attempt, 43,200 sec v2-only budget. Root manifest SHA-256 `bc0068aa2254e4c15165247ee299f48940cca9b7c21f6a288fd13812631ea2b2`, 4,159 files / 728,148,524 bytes. |

V2 reused the v1 ALE seeds under a changed extended-horizon protocol. V1 and v2 must never be pooled as an unchanged protocol or described as independent held-out replications. V2 also uses only one of the three M5 training-seed pairs. Its results cannot estimate variability across independent training runs.

The independent raw audit rederived v2's 20 scheduled attempts as 11 ALE-terminal losses (4 Warm, 7 Scratch), 9 incomplete attempts (5 reply timeouts, 2 source-selection uncertainty stops, 2 target-navigation uncertainty stops), and zero terminal wins/draws. Incomplete attempts are not draws. Its operational endpoint was 385 RGB-verified initiated player moves / 405 initiated player moves (95.0617%), with 385 verified Atari replies, zero board desynchronizations, 1,871 unexpected cursor displacements all corrected, no resource stops, and peak recorded RSS 620,105,728 bytes. Wilson intervals over moves are descriptive only because moves cluster within games. These observations demonstrate bounded closed-loop controller execution under the named profile; they do not demonstrate strong Atari play, generalization, or Warm/Scratch superiority.

The original v2 manifest's `gameplay_wall_budget_includes_diagnostics=true` conflicts with the frozen v2-only budget scope. PM6-F06 preserves the immutable original and corrects future serialization behavior; see [the erratum](../../.agents/evidence/M6-PM6-F06-erratum-20261031.md). Do not edit the original manifest or treat the metadata conflict as extra v2 gameplay. PM6C-F01 is a separate provenance correction for the PR #15 closeout record.

## 3. Valid comparisons and proposed future population

### Reuse without rerunning

The M4 held-out imitation metrics, all M5 six-run/1,500-row simulator campaign, and M6 v1/v2 audits are accepted inputs. Reuse them with their original source/config/checkpoint identities and limitations. Do not recompute policy outcomes from summaries in lieu of raw rows. The independent M6 raw audit in this Pre-M7 package is read-only integrity reconstruction, not an ALE campaign.

### Optional, NOT AUTHORIZED, additional ALE evaluation

If the owner decides existing evidence cannot answer the comparison question, the smallest proposed balanced extension across the full frozen policy population is 90 attempts: six M5 post-RL checkpoints (Warm/Scratch × the three accepted training seeds), one accepted M4 r4 model, RandomLegal, and SimpleHeuristic, each evaluated on the same 10 new ALE seeds. The seeds must be selected and frozen before any game; they must not reuse `20261130`–`20261139`. Each policy plays White under the same approved VideoChess ROM/profile/opponent. Use the same seed schedule for all policies, counterbalance policy order, run one ALE process at a time, and execute all scheduled attempts without outcome-based stopping or replacement.

This 90-attempt branch can describe behavior across the three existing training-seed clusters and ten ALE seed blocks. It cannot establish broad generalization or high confidence with only three training runs. It needs a new versioned config (the accepted v2 cap is 20), explicit owner approval, and a separate resource ceiling. The plan estimates 4.4 hours from the observed M6 v2 mean and caps each attempt at 1,800 seconds, so the worst-case gameplay allowance is 45 hours. A linear artifact estimate is 3.28 GB, with a proposed hard cap of 8 GiB and a 12 GiB free-space preflight reserve. These are planning estimates, not authorization or guarantees.

No new simulator comparison is recommended by default: the accepted 1,500-row M5 schedule already contains all 15 declared policy groups and matched colors/opponents. More games against the same three trained seed pairs would reduce evaluation-seed noise without adding independent training replication. A new training campaign is out of scope and must not be added to solve that limitation implicitly.

## 4. Metrics, endpoints, and denominators

Every report must show `scheduled`, `started`, `terminal`, `truncated`, `terminal_unknown`, `incomplete`, and `not_started` counts separately, by policy/protocol/seed stratum. Report denominator next to each rate.

| Measure | Definition and rule |
|---|---|
| W/D/L | Only ALE-authoritative terminal results with valid finite reward/perspective or simulator terminal rules. In ALE, White-perspective reward is mapped consistently. Unknown terminal rewards remain `terminal_unknown`. |
| Game score | `(wins + 0.5 × draws) / terminal games`; explicitly label the terminal-only denominator and show incomplete/censor counts beside it. |
| Truncated | Simulator decision-cap outcomes remain truncated, not terminal draws. Preserve whether the predeclared reward bootstrap rule applied to training; evaluation never fabricates a terminal result. |
| Incomplete / censored | Reply timeout, controller uncertainty, artifact cap, resource stop, process failure, or other nonterminal stop. Never count these as draws or discard them from the schedule denominator. Show terminal-only outcomes and, when helpful, worst/best bounds that classify every incomplete as loss/win; do not use IPCW unless independent censoring is separately justified. |
| Legal/controller success | Report legal action validation separately from action execution. For ALE, primary operational rate is RGB-verified initiated player moves / all initiated player moves; also report proposed legal moves, verified Atari replies, and each stop category. |
| Synchronization | Count board disagreements/desynchronizations and the exact checked-move/attempt denominator. ALE RGB is the observation source of truth; a shadow board cannot override it. Report cursor corrections separately from desynchronizations. |
| Timeouts/uncertainty | Count bounded opponent-response timeouts and source-selection/target-navigation uncertainty stops by policy and attempt. Do not combine a timeout with a terminal loss. |
| Runtime/compute | Record per-attempt wall time, gameplay and setup/recovery time separately, environment steps/frames, policy/adapter latency percentiles, peak RSS, artifact bytes, hardware/runtime/library/ROM/config identities, and stop reason. Do not label adapter total as neural-only inference latency. |

For historical M4 imitation, retain position/candidate denominators and calculate uncertainty by resampling source-game clusters, not individual positions. Sparse special-move strata stay descriptive.

## 5. Pairing, uncertainty, and analysis labels

### Paired comparisons

- M5 pre/post comparisons pair the same training seed, evaluation seed, opponent, and color. Warm/Scratch comparisons pair by the three training-seed pairs and the same simulator scenario. A paired game row is a repeated measurement, not an independent training run.
- M6 v2 Warm/Scratch comparisons pair the ten ALE seed blocks. A seed block is an evaluation cluster, not an independent model-training replication; both policies derive from M5 training seed `20261104`.
- The optional 90-attempt design pairs all nine policy groups by new ALE seed block. Warm/Scratch inference still has only three independent training-seed pairs.

### Confidence intervals and dependence

Report per-seed/per-block point estimates first. Use 95% cluster-bootstrap percentile intervals with 10,000 resamples and a fixed, recorded bootstrap seed: resample whole source games for M4; whole simulator evaluation-seed blocks and training-seed pairs for M5; whole ALE attempts/seed blocks for M6. For a crossed design, resample both training-seed and environment-seed clusters and preserve within-block policy pairings. Never resample individual moves as independent Bernoulli observations. With only three training-seed pairs, show all three paired effects and treat cluster intervals as descriptive; do not use a normal/asymptotic p-value to imply robust generalization. If a valid cluster interval cannot be estimated, report it as unavailable rather than substituting an independent-game interval. Exact seed-level permutation/sign results may be reported only with their coarse resolution (at most 2³ assignments for three pairs).

### Confirmatory, exploratory, and post-hoc

- **Confirmatory:** only comparisons and primary endpoints frozen before the relevant run; preserve the M5 primary terminal-only comparison and its accepted schedule as historical evidence.
- **Exploratory:** additional strata, controller metrics, and cross-track descriptive tables not named as primary endpoints.
- **Post-hoc sensitivity:** M5 capped-reward resampling and any later censoring/bounds or alternate endpoint analyses. Label them and never promote them to the primary result.
- Report every attempted metric/stratum that informed a claim. No checkpoint, seed, policy, or endpoint may be selected from its evaluation outcome.

## 6. Missing data, protocol deviations, and audit

The unit of scheduled evaluation is the predeclared policy × seed × opponent × color cell (or policy × ALE seed attempt). Preserve every cell and raw row, including failures before terminal. A terminal-only metric answers “among observed terminal games”; the schedule-level completion rate answers a separate operational question. Do not impute censored results or replace an inconvenient attempt. Document timeouts, early stops, controller uncertainty, runtime/resource stop, and unavailable artifacts with timestamp and reason. Any deviation is an explicit protocol deviation with owner approval before outcomes are inspected.

Before and after an authorized run, verify source revision/tree, config/schedule hash, model/checkpoint/sidecar hash, dataset/ROM/dependency identities, seed/RNG state, hardware, and local artifact manifest. Keep raw RGB, ROM, private model/data, credentials, and private checkpoints outside Git and external services. Record sanitized commands/log hashes and exact exit codes. The executor cannot self-approve a release or merge.

## 7. Elo: conditional and optional

No Elo value is currently reportable. Existing RandomLegal/SimpleHeuristic simulator results and the single ALE ROM opponent are not a calibrated pool. Before any Elo claim, the owner must approve:

1. A named pool of at least three distinct opponents with rating source/date and a defensible calibration/anchor, all evaluated under the same environment, ROM, mode, difficulty, controller, and color schedule as the target policy. No unapproved Stockfish role is permitted.
2. A frozen match schedule with at least 30 **terminal** games per policy/opponent/color cell, a predeclared maximum attempt/resource cap, and incomplete outcomes kept separate. This minimum is not a power guarantee; a formal power calculation is preferred.
3. A fixed-anchor maximum-likelihood Elo model using the standard 400-point logistic scale and win/draw/loss scores; no adaptive K-factor or post-result opponent selection. State the anchor, rating period, model, opponent uncertainty, and draw treatment.
4. A 95% interval from a match-block bootstrap that respects evaluation seed and training-seed clusters. If the target includes one trained checkpoint only, describe that checkpoint/profile and do not generalize to the training method.

If any requirement is absent, the report must say “Elo not reported: calibrated pool/design not approved or unavailable.” Never assume a 1500 baseline or convert M4 imitation accuracy, M5 simulator score, or M6 move-execution rate into Elo.

## 8. Owner authorization branches and decisions

**All new evaluation is NOT AUTHORIZED.** The owner must separately approve the final populations, protocol version, seed schedule, resource envelope, and M7-001 start after the G4 PM disposition. The 90-attempt ALE option is not a default execution plan. Local CPU is the proposal; Colab access/cost/storage remain unverified. O-02 (ALE requirement/fallback), O-05 (official runtime profile), O-08 (Elo pool), and G5 release scope require the decisions listed in [PRE-M7-readiness.md](../../.agents/plans/PRE-M7-readiness.md). A new training or fine-tuning request needs separate scope and authorization and cannot be smuggled into this evaluation protocol.
