# Atari VideoChess RL — Final Research Report

**Evidence scope:** accepted M3–M7 evidence through G4 review

**Repository baseline:** PR #18 merge, d7332b91128d3daf919421db2e71a9f2ee4b48ec

**M7 run:** m7-option-b-20261031-v1-8387b289432f

**G4:** APPROVED WITH SCIENTIFIC LIMITATIONS for M7-01 through M7-03

**G5:** NOT APPROVED


> G4 accepts the bounded evaluation evidence and its analysis. It does not establish that the agent plays strong chess, that RL improved Atari performance, or that an academic requirement has been met.

## Executive summary

The project evaluated a supervised behavior model, custom Double DQN policies trained in a chess simulator, and a closed-loop controller for actual ALE/VideoChess. M7 compared six frozen post-RL checkpoints with the accepted M4 supervised model and two non-learning policies in one preregistered ALE campaign.

M4 reached 29.8979% legal top-1 imitation accuracy on 2,057 held-out positions. This measures agreement with recorded moves, not game outcomes or playing strength. M5 completed six simulator training runs (three paired Warm-start/Scratch seeds, 50,000 valid decisions each) and 1,500 simulator evaluation rows: 1,494 terminal games and six time-limit truncations. M6 retained two distinct ALE profiles: v1 had three terminal losses among 35 attempts; v2 had 11 terminal losses and nine incomplete attempts among 20. M7 accounted for all 90 scheduled policy × ALE-seed attempts, all started and reset-observed: 60 terminal White losses, 30 incomplete, zero terminal wins or draws.

M7 accepted 1,670/1,670 proposed legal actions; 1,581/1,670 initiated player moves were RGB-verified (94.67%). It recorded 1,581 verified Atari replies and no board desynchronizations. These are integration measurements, not chess-strength metrics.

The evidence supports that the frozen policy/controller system executed a complete, documented closed-loop ALE schedule under the frozen rules. It does not support RL superiority over M4 or the baselines, Warm-start superiority over Scratch, equivalence, broad generalization, or an Elo rating. Incomplete outcomes are common and policy-dependent. Elo is not reported because a calibrated opponent pool and rating design were not approved or available. Whether full-game ALE performance is a hard academic submission requirement remains open under O-02.

## Research questions and system

| Track | Measurement | Interpretation limit |
|---|---|---|
| M4 supervised imitation | Legal top-k accuracy and reciprocal rank on held-out positions | Not W/D/L, RL improvement, Atari performance, or Elo |
| M5 simulator RL | Simulator W/D/L, terminal score, truncations, paired comparisons | Not ALE performance; only three paired training seeds |
| M6 Atari integration | ALE terminal outcomes, incomplete reasons, RGB verification, desynchronization, resources | Not broad chess strength; v1 and v2 differ |
| M7 ALE gameplay | ALE-authoritative W/D/L, incomplete counts, terminal-only score, common seed blocks | One built-in opponent, White only, censored outcomes |
| Elo reportability | Audit against M7-EVAL/1.0.0 §7 | No rating inferred from other metrics |

M3 processed a bounded Lichess Elite May 2022 source release. M4's action-conditioned behavior scorer takes a symbolic mover-oriented board, rule metadata, full UCI history, and current legal candidates; its outputs are uncalibrated within-position preferences, not Q-values or win probabilities. M5 reuses shared representation with a fresh scalar Q head. Warm-start transfers shared representation weights only; Scratch uses matched architecture and paired initialization. Custom PyTorch Double DQN selects a legal semantic UCI action with the online network and values that action with the target network. Stockfish is not in the inference path.

M5 uses the M2 chess simulator. M6/M7 control actual ALE/VideoChess. ALE RGB is the observation source of truth; the python-chess shadow tracks and cross-checks verified history but never replaces ALE. The closed loop observes, validates, decides, executes cursor input, and verifies the board and Atari reply. M7 evaluates the combined frozen policy/controller; the model does not consume raw RGB as a learned pixel encoder.

## Design and provenance

| Stage | Environment/population | Design |
|---|---|---|
| M3 | Historical chess source and teacher sidecar | 1,000 games; 19,268 positions |
| M4 | Behavior cloning; held-out source positions | Selected seed 20261024, epoch 11; 2,057 test positions |
| M5 | M2 simulator; Warm, Scratch, M4, RandomLegal, SimpleHeuristic | Training seeds 20261104–06; 50,000 valid decisions × six runs; 1,500 evaluation rows |
| M6 v1 | ALE/VideoChess-v5, White, mode 4, difficulty 0, RGB, frameskip 4, sticky .25 | 35 attempts; 54,000-frame / 900-second profile |
| M6 v2 | Same game settings, separate extended-horizon configuration | 20 attempts; effective 500,000 ALE frames, runner 432,000 post-reset frames, 1,800 seconds/attempt |
| M7 Option B | Same ALE game settings; built-in opponent | Nine policies × seeds 20261201–20261210 = 90 attempts; extended 500,000 / 432,000 frame profile; 1,800 seconds/attempt |

M6 v1, M6 v2, and M7 are not pooled: their populations, schedules, and runtime profiles differ. ALE's registered default horizon is 108,000 frames. M6 v2/M7 used an explicit extended horizon, not the default. M7 used one ALE opponent and White only.

M7 classifies outcomes from ALE terminal/truncation flags and White-perspective reward. Positive finite terminal reward is a White win; negative finite reward is a White loss; zero or nonfinite terminal reward is terminal-unknown. Incomplete attempts and runner truncations are not draws. Terminal-only score is (wins + 0.5 × draws) / terminal games and is undefined when terminal games is zero.

## M3 and M4 results

Accepted M3 release ID: f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890; manifest SHA-256: be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12. It retains 1,000 games and 19,268 positions: 15,196 train, 2,015 validation, and 2,057 test positions. M3 acceptance records 182 rejected games. The bounded Stockfish 19 teacher sidecar is provenance, not an inference component. The source's third-party license remains unstated/unverified; no redistribution right is implied.

Accepted M4 run m4-behavior-20261027-r4 used training seed 20261024 and selected epoch 11. Checkpoint SHA-256: 724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4. Root manifest SHA-256: f00fde1c59325105e0ffd45bb45eb269dfa303416010c9a0b6c6be47bd9a9921.

| Held-out metric | Result | Denominator |
|---|---:|---:|
| Legal top-1 accuracy | 29.8979% | 2,057 positions |
| Legal top-3 accuracy | 54.3996% | 2,057 positions |
| Mean reciprocal rank | 0.4643745951 | 2,057 positions |

The test set contains 61,419 legal-candidate evaluations. These are historical-move imitation metrics, not evidence of optimal play, wins, rating, RL improvement, or Atari performance. The accepted record retains aggregate evaluation, not per-position predictions.

## M5 Double DQN simulator results

M5 completed six 50,000-valid-decision runs (300,000 decisions total) with three paired Warm/Scratch training seeds. Its frozen simulator evaluation crossed 15 policy groups with 25 shared seeds, two opponents, and both colors: 1,500 rows, 1,494 terminal games, and six valid time-limit truncations.

| Policy | W / D / L | Truncated | Terminal score (n) |
|---|---:|---:|---:|
| M4 behavior-only | 48 / 50 / 2 | 0 | .730 (100) |
| Warm 20261104 pre-RL | 2 / 85 / 13 | 0 | .445 (100) |
| Warm 20261104 post-RL | 16 / 78 / 5 | 1 | .556 (99) |
| Scratch 20261104 pre-RL | 0 / 64 / 35 | 1 | .323 (99) |
| Scratch 20261104 post-RL | 12 / 86 / 2 | 0 | .550 (100) |
| Warm 20261105 pre-RL | 3 / 39 / 56 | 2 | .230 (98) |
| Warm 20261105 post-RL | 19 / 79 / 2 | 0 | .585 (100) |
| Scratch 20261105 pre-RL | 0 / 72 / 28 | 0 | .360 (100) |
| Scratch 20261105 post-RL | 3 / 91 / 6 | 0 | .485 (100) |
| Warm 20261106 pre-RL | 0 / 37 / 63 | 0 | .185 (100) |
| Warm 20261106 post-RL | 24 / 74 / 2 | 0 | .610 (100) |
| Scratch 20261106 pre-RL | 0 / 66 / 33 | 1 | .333 (99) |
| Scratch 20261106 post-RL | 8 / 90 / 1 | 1 | .535 (99) |
| RandomLegal | 3 / 58 / 39 | 0 | .320 (100) |
| SimpleHeuristic | 33 / 63 / 4 | 0 | .645 (100) |

Warm post-minus-pre was +0.296 (297 matched terminal pairs, 3 censored); Scratch post-minus-pre was +0.185 (297 matched, 3 censored). Their preregistered intervals are unavailable. Warm-minus-Scratch was −0.056 before RL (296 matched, 4 censored) and +0.062 after RL (298 matched, 2 censored); campaign-level intervals are unavailable. The 1,500 rows are not independent trained policies. Only three training-seed pairs exist; no Warm-start superiority claim follows.

Training consumed 77,899.281 seconds within a 216,000-second cap; simulator evaluation used 1,983.451 seconds within a 43,200-second cap. The accepted M5 artifact inventory was 6,544,747,450 bytes. M5 root-manifest SHA-256 is a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c. The six frozen checkpoint and sidecar identities are in the [M7 frozen population record](../../.agents/evidence/M7-001-acceptance-20261101.md) and [model card](MODEL_CARD.md).

RSK-014 remains: source identities differ across run groups and complete historical CLI bytes are unavailable. Accepted forensic analysis found no evidence of a seed-correlated learning-method change, but byte-identical provenance is not established. Historical results were not modified.

## M6 Atari integration

| Stage | Run | Config SHA-256 | Scheduled | Terminal W / D / L | Incomplete | RGB-verified / initiated | Desynchronizations |
|---|---|---|---:|---:|---:|---:|---:|
| M6 Stage 3 v1 | m6-stage3-ad3998200e31-c5ff389dc4fe | 05aedeb30efb8b6b97667c44f9d606b58d4da8ae20800d4ef143e629420cebac | 35 | 0 / 0 / 3 | 32 | 455 / 490 | 0 |
| M6 Stage 3 v2 | m6-stage3-v2-91f51b14690e-d05d42400cfc | 663651050db80ab027b452241c7d39837ec7986927c0aefc7c7be631f459a49b | 20 | 0 / 0 / 11 | 9 | 385 / 405 | 0 |

V1 used the 54,000-frame / 900-second profile; 26 attempts ended at the frame cap, and six other incomplete stops were three source-selection uncertainty, two target-navigation uncertainty, and one opponent-response timeout. V2 used a separately authorized extended horizon; its nine incompletes were five opponent-response timeouts, two source-selection uncertainty stops, and two target-navigation uncertainty stops. Incomplete attempts are not draws. V2 reused v1 ALE seeds; the stages are not independent replications. The accepted PM6-F06 metadata erratum remains unchanged.

V1 root-manifest SHA-256 is 22ac6ec7e0f4a48f52b2452654d4adecaf111f38ea37f5d9517f173c838716d7; v2 root-manifest SHA-256 is bc0068aa2254e4c15165247ee299f48940cca9b7c21f6a288fd13812631ea2b2. The v2 report records 3,519.969 seconds cumulative gameplay wall time, 620,105,728-byte peak RSS, and 728,148,524 artifact bytes.

## M7 Option B ALE results

Protocol M7-Option-B/1.0.0; scientific basis M7-EVAL/1.0.0. Run ID m7-option-b-20261031-v1-8387b289432f. Configuration SHA-256 8ec8a42a808f4ffc410c938b4400d02461f96823eb5ac1b16cbd6e0d5e35f255; frozen schedule SHA-256 c479e65f944224ffbc584e15f43086e881e9df1a10c009c478be8ce5119e67d9. ALE seeds were 20261201, 20261202, 20261203, 20261204, 20261205, 20261206, 20261207, 20261208, 20261209, and 20261210. ROM SHA-256 d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7.

The recorded runtime was Python 3.12.3, Gymnasium 1.4.0, ALE-Py 0.11.2, PyTorch 2.14.1+cpu, python-chess 1.11.2, and NumPy 2.5.4. Runtime identity and configuration are frozen in the config and run manifest.

The nine groups were Warm post-RL at seeds 20261104–06; Scratch post-RL at the same training seeds; M4 behavior-only; RandomLegal; and SimpleHeuristic. Each had ten attempts across shared ALE seeds 20261201–20261210. All 90 attempts were scheduled, started, and reset-observed; none were not-started, replaced, terminal-unknown, or ALE-truncated.

| Policy | Scheduled / started | Terminal W / D / L | Incomplete | Terminal score |
|---|---:|---:|---:|---:|
| M4 behavior-only | 10 / 10 | 0 / 0 / 8 | 2 | 0.000 (8) |
| Warm 20261104 post-RL | 10 / 10 | 0 / 0 / 4 | 6 | 0.000 (4) |
| Warm 20261105 post-RL | 10 / 10 | 0 / 0 / 0 | 10 | Undefined (0) |
| Warm 20261106 post-RL | 10 / 10 | 0 / 0 / 9 | 1 | 0.000 (9) |
| Scratch 20261104 post-RL | 10 / 10 | 0 / 0 / 9 | 1 | 0.000 (9) |
| Scratch 20261105 post-RL | 10 / 10 | 0 / 0 / 9 | 1 | 0.000 (9) |
| Scratch 20261106 post-RL | 10 / 10 | 0 / 0 / 5 | 5 | 0.000 (5) |
| RandomLegal | 10 / 10 | 0 / 0 / 6 | 4 | 0.000 (6) |
| SimpleHeuristic | 10 / 10 | 0 / 0 / 10 | 0 | 0.000 (10) |
| **Total** | **90 / 90** | **0 / 0 / 60** | **30** | **0.000 (60 terminal games only)** |

Terminal-only scores of 0.000 describe observed terminal games only. They are not full-schedule scores under censoring. Warm 20261105 has no terminal games, so its terminal score is undefined, not zero. If all 30 unresolved attempts are treated as losses and then as wins, the full-schedule sensitivity range is [0.000, 0.333]; this is a bound, not an imputation.

The 30 incompletes were 16 target-navigation uncertainty stops, four source-selection uncertainty stops, seven opponent-response timeouts, two other unknown interruptions, and one policy-input stop after fivefold repetition in the shadow history while ALE remained nonterminal. The last attempt remains incomplete because ALE is authoritative. The raw M7 root manifest SHA-256 is 25a8b6bcfbf1d948bed886a0a4964cf48210fb1be12809c72bf122157b8d05e4; the run-manifest SHA-256 is 93d941f5b1c4f876ea66c62d30f66b873b61e59acbacd25534d66920bbbb3431.

Across M7, 1,670/1,670 proposed legal selections were valid; 1,581/1,670 initiated player moves were RGB-verified (94.67%); 1,581 Atari replies were verified; zero board desynchronizations and 7,225 cursor corrections were recorded. The raw-derived report records 2,463,748,628 artifact-parent bytes after finalization; process wall 10,393.157 seconds; CPU 6,519.449 seconds; peak RSS 368,812,032 bytes; session wall 10,426.962 seconds. Free disk was 50,056,785,920 bytes before and 47,532,662,784 bytes after the campaign. Limits were 90 × 1,800 seconds, 8 GiB campaign artifacts, and at least 12 GiB free before the first attempt; these limits were respected.

### Paired uncertainty

The preregistered 10,000-resample analysis used RNG seed 20261290 and preserved shared ALE-seed blocks and the three training-seed pairs as clusters. Only 9/30 Warm/Scratch matched training-seed × ALE-seed cells had terminal outcomes; 21 were censored or unknown. The complete-pair point difference was 0.000; no paired confidence interval is available under the frozen censoring rule. This is not evidence of equivalence.

All 18 M7 RL-policy-versus-baseline comparisons contain censored or unknown seed blocks. The table reports the raw-derived complete-pair point estimates and matched/censored block counts; every interval is unavailable under the frozen rule. The rows are descriptive matched terminal-only contrasts, not independent training replications.

| RL policy vs baseline | Training seed | Matched terminal blocks | Censored/unknown | Point difference | 95% interval |
|---|---:|---:|---:|---:|---|
| Scratch 20261104 vs M4 | 20261104 | 8 | 2 | 0.000 | unavailable |
| Scratch 20261104 vs RandomLegal | 20261104 | 5 | 5 | 0.000 | unavailable |
| Scratch 20261104 vs SimpleHeuristic | 20261104 | 9 | 1 | 0.000 | unavailable |
| Scratch 20261105 vs M4 | 20261105 | 7 | 3 | 0.000 | unavailable |
| Scratch 20261105 vs RandomLegal | 20261105 | 5 | 5 | 0.000 | unavailable |
| Scratch 20261105 vs SimpleHeuristic | 20261105 | 9 | 1 | 0.000 | unavailable |
| Scratch 20261106 vs M4 | 20261106 | 3 | 7 | 0.000 | unavailable |
| Scratch 20261106 vs RandomLegal | 20261106 | 4 | 6 | 0.000 | unavailable |
| Scratch 20261106 vs SimpleHeuristic | 20261106 | 5 | 5 | 0.000 | unavailable |
| Warm 20261104 vs M4 | 20261104 | 4 | 6 | 0.000 | unavailable |
| Warm 20261104 vs RandomLegal | 20261104 | 3 | 7 | 0.000 | unavailable |
| Warm 20261104 vs SimpleHeuristic | 20261104 | 4 | 6 | 0.000 | unavailable |
| Warm 20261105 vs M4 | 20261105 | 0 | 10 | undefined | unavailable |
| Warm 20261105 vs RandomLegal | 20261105 | 0 | 10 | undefined | unavailable |
| Warm 20261105 vs SimpleHeuristic | 20261105 | 0 | 10 | undefined | unavailable |
| Warm 20261106 vs M4 | 20261106 | 7 | 3 | 0.000 | unavailable |
| Warm 20261106 vs RandomLegal | 20261106 | 6 | 4 | 0.000 | unavailable |
| Warm 20261106 vs SimpleHeuristic | 20261106 | 9 | 1 | 0.000 | unavailable |

Per training seed, Warm-minus-Scratch had four matched terminal ALE blocks and six censored/unknown blocks for 20261104; zero matched and ten censored/unknown for 20261105; five matched and five censored/unknown for 20261106. All observed complete-pair point differences are 0.000; the seed-20261105 estimate is undefined. Pooled across the 30 planned pairs, only 9 were terminal-matched and 21 censored/unknown.

ALE seeds are not independent trained policies. Zero point differences do not establish equivalence. No interval is fabricated, and moves are not treated as independent games.

## Interpretation and threats to validity

**Supported:** the frozen integration executed its full 90-cell ALE schedule; results retained all terminal and incomplete cells; legal selections were valid; RGB move/reply verification was recorded without board desynchronization in these runs.


**Observed but not enough for broad conclusions:** M5 simulator point estimates changed from initialization; M7 terminal and controller outcomes varied by policy. M5 has only three paired training seeds; M7 has substantial policy-dependent censoring.


**Not established:** RL superiority over M4 or either M7 baseline; Warm-start superiority or equivalence; strong chess play; broad generalization; simulator-to-Atari transfer; any Elo rating; or satisfaction of O-02/course requirements.


Limitations include small training replication, 30/90 M7 incomplete outcomes, one ALE opponent, White-only play, controller uncertainty/timeouts, extended rather than registered-default ALE horizon, protocol differences across M6/M7, M5 source limitation RSK-014, M6 v2 erratum PM6-F06, and owner-local raw artifacts. Private raw evidence cannot be independently rerun without owner-authorized access. O-02 remains open.

## Reproducibility and evidence

| Evidence | Source |
|---|---|
| M3 source and teacher provenance | [M3 acceptance](../../.agents/evidence/M3-acceptance-20261021.md), [M3 final closure](../../.agents/evidence/M3-final-closure-20261021.md) |
| M4 model and results | [M4 final acceptance](../../.agents/evidence/M4-final-acceptance-20261027.md), [machine-readable acceptance](../../.agents/evidence/M4-final-acceptance-20261027.json) |
| M5 simulator | [M5 final report](../04-research/M5_FINAL_REPORT.md), [M5 PM acceptance](../../.agents/evidence/M5-PM-acceptance-20261030.md) |
| M6 v1/v2 | [v1 report](../../.agents/evidence/M6-001-final-report-20261031.md), [v2 report](../../.agents/evidence/M6-001-final-report-v2-20261031.md), [PM6-F06 erratum](../../.agents/evidence/M6-PM6-F06-erratum-20261031.md) |
| M7 | [M7-001](../../.agents/evidence/M7-001-acceptance-20261101.md), [M7-002](../../.agents/evidence/M7-002-acceptance-20261101.md), [M7-003](../../.agents/evidence/M7-003-acceptance-20261101.md), [frozen config](../../configs/m7/m7-option-b-1.0.0.json), [analysis](../../.agents/evidence/M7-analysis-final-r2-20261101/M7_ANALYSIS.md), [machine-readable analysis](../../.agents/evidence/M7-analysis-final-r2-20261101/m7-analysis.json), [analysis manifest](../../.agents/evidence/M7-analysis-final-r2-20261101/manifest.json) |
| G4 decision | [G4 PM acceptance](../../.agents/evidence/G4-PM-acceptance-20261101.md), [Independent PM decision on PR #17](https://github.com/dodaonam/atari-videochess-rl/pull/17#issuecomment-6552570969) |
| M7-004 provenance | [Engineering completion evidence](../../.agents/evidence/M7-004-acceptance-20261101.md), [claim/evidence inventory](../../.agents/evidence/M7-004-evidence-inventory-20261101.json), [failure/remediation history](../../.agents/evidence/M7-004-failure-history-20261101.md) |

M7 run source was commit 58a604f2bd4bcd9113a047ee709a80ee97bd02a6 (tree 18d4d93270665a1c2e90eb459381958e407c441f). Analysis source was fe2cc4cc5e477841ffbc9368235eb9c5675f2f74 (tree 94f37d775b5a62f09c2502fcfd8caf58622397bf). M7-002 reports a historical full suite of 492 passed, zero skipped at cbf4b27d4c9eb65108ee17c3138cf020c8c8ade9; these are not M7-004 verification results.

The repository includes sanitized reports, configs, code, hashes, and approved evidence summaries. ROM, source data, checkpoints, raw RGB, and raw ledgers remain owner-local. The Independent PM reviewed the committed implementation, protocol, analysis, and evidence records, but did not independently access and rerun private raw M7 artifacts. Authorized local access is required to reverify private manifests or reproduce historical analysis. Routine setup does not require repeating any campaign.

## Conclusion

The project delivered a traceable path from move imitation through simulator Double DQN to actual ALE closed-loop evaluation. M7's result is negative/inconclusive: all observed terminal outcomes were White losses and one-third of attempts did not reach an ALE terminal result. Operational integration evidence does not establish chess strength or RL advantage. Elo remains unreportable; O-02 and other open requirement questions remain unresolved. Any new training or opponent campaign requires separate authorization. The Project Owner's current distribution decision is **NO RELEASE / NO PUBLICATION AUTHORIZED**; see the [release disposition](RELEASE_DISPOSITION.md). This is separate from G5 review and does not alter the scientific findings.
