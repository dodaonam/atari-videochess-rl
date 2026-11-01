# Model Card — Atari VideoChess RL

**Status:** Research artifacts; no champion model selected; public distribution not authorized

**Governance:** G4 approved with scientific limitations; G5 not approved

**Scope:** accepted M4 behavior model and six M5 post-RL checkpoints


**M7 policy-evaluation run:** m7-option-b-20261031-v1-8387b289432f

**Protocol:** M7-Option-B/1.0.0

**Configuration SHA-256:** 8ec8a42a808f4ffc410c938b4400d02461f96823eb5ac1b16cbd6e0d5e35f255


## Model identity

The repository contains two model families with different objectives. M4 ranks supplied legal moves from symbolic chess state. M5 estimates simulator reward with Double DQN. Neither is a calibrated chess engine or a learned raw-pixel Atari model. M7 evaluates each frozen policy together with the RGB interpretation, controller, and verification pipeline.

| Family | Run, training identity | Interface and role | Identity |
|---|---|---|---|
| M4 behavior-only | m4-behavior-20261027-r4; seed 20261024; selected epoch 11 | videochess-model-input/1.0; uncalibrated behavior logits over supplied legal candidates | Source revision 7b3c9074a2d932fec6d7732ee08e99b9de10a135; checkpoint SHA-256 724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4; sidecar file SHA-256 cc0af4694e45fc23acb740c652dd9a62e1bcaf7851815d179693d09539f0f606; root manifest f00fde1c59325105e0ffd45bb45eb269dfa303416010c9a0b6c6be47bd9a9921 |
| M5 Double DQN | Six frozen post-RL checkpoints; Warm/Scratch × seeds 20261104–06 | Symbolic state and legal UCI candidates; scalar Q-value per candidate | Root manifest a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c; individual checkpoint and sidecar hashes below |

The M4 scorer has 121,897 measured trainable parameters. M5 retains the state/candidate representation with a fresh scalar Q head. Warm-start copies shared representation weights only; it does not transfer M4 logits/head, optimizer state, or teacher scores. Scratch uses the matched architecture and paired initialization.

### Accepted M5 post-RL checkpoint inventory

| Policy | Training seed | Checkpoint SHA-256 | Sidecar file SHA-256 |
|---|---:|---|---|
| Warm | 20261104 | 0b2405017a8e1d539851f0cd278883d3fd23936fb5c2f7962c813590a6fd1767 | 80d8689e4b349576c5708bb4dce3451e5a8c64d81470cd6f4273a4746844b682 |
| Warm | 20261105 | e864d8351cb03b7e671e7a061226711b2d33b23bbaca97e899c09f1d2eb59670 | dceb8c11c3ebd239048ba6e51bb8fd1ea26d72f9129ec6e4ed3bc4847cffabf0 |
| Warm | 20261106 | c037adc652a00ea131366c5f15ac78811a223459312f9bac5f676f267cf36bcd | cf52cc191543ddcdfa460b1a1a07c6e9d941d09eee69fb673b09c18f97037b8d |
| Scratch | 20261104 | 3749b0c0b6ae44d3ad5d6bf0863b60937a59fbe881e0bdf4932bdce6033ca400 | 1c15e5bc4ba2437df113671dc316accbdfe6d8b59069ed29ed187daebf4fff1e |
| Scratch | 20261105 | e63ab18289135e411fb4c00a025d2985446475e5b70881ca7e9190559c20b3f8 | d0bc5b1e08ede42282a9c921b4da6181341f9c7c4d633454642e7fe9312cc2e6 |
| Scratch | 20261106 | 94838bc8c3547a5b8ce9e1d8c1dde66b86163defb868b18be6185895acf9663c | 7335dce64b7d070271ed490828022851f42232c1aacc7eed9014e360cd7e6779 |

These six checkpoints are the predeclared M7 RL population. The table does not select a champion or a release model.

Their full frozen M5 run IDs are:

| Policy | M5 run ID |
|---|---|
| Warm 20261104 | m5-e072011a58411f4ff26040013ba2e8c71212e6c83acf755337c2d7e1e01378d7__warm__attempt-0001 |
| Warm 20261105 | m5-75b4300109faf28e59770a022ee13435ab4c92c6ab19750a83ad79ed9bbc581c__warm__attempt-0000 |
| Warm 20261106 | m5-89235d5a197920cce40c4a52a034f68e27a6ecc3e5eb2ab0bef80b037ffef870__warm__attempt-0000 |
| Scratch 20261104 | m5-e072011a58411f4ff26040013ba2e8c71212e6c83acf755337c2d7e1e01378d7__scratch__attempt-0000 |
| Scratch 20261105 | m5-75b4300109faf28e59770a022ee13435ab4c92c6ab19750a83ad79ed9bbc581c__scratch__attempt-0000 |
| Scratch 20261106 | m5-89235d5a197920cce40c4a52a034f68e27a6ecc3e5eb2ab0bef80b037ffef870__scratch__attempt-0000 |

M5 run manifests identify two training-source aggregates: 093992c50e893a7fdd92f2f95faafe28d4f1e73c7351a4a8179a3056c4e63b00 for the first four runs (seeds 20261104 and 20261105), and cdcc1fdc0ca0b324e49cfb8b0ff571496a554e9892dfb3620d6454a65ee16da0 for both 20261106 runs. This source-identity change is retained under RSK-014; no single byte-identical M5 training source revision is claimed. The separately audited M5 evaluation source aggregate is ccb7d76be64c55ae4c4519da3a5647a5a2da86924a00d9490a7e807cc7497848, reconciled at PR source head 575dce5978567417d2915d5dd36a47873293b607.

The M7 ALE run source is commit 58a604f2bd4bcd9113a047ee709a80ee97bd02a6, tree 18d4d93270665a1c2e90eb459381958e407c441f. Its raw-derived analysis source is commit fe2cc4cc5e477841ffbc9368235eb9c5675f2f74, tree 94f37d775b5a62f09c2502fcfd8caf58622397bf.

## Training provenance

M4 used the accepted M3 historical move dataset. Its selected model used seed 20261024 and epoch 11 selected by validation NLL; the 2,057-position test metrics were evaluated after freeze. M4 legal top-1 was 29.8979% and top-3 was 54.3996%. These describe imitation agreement.

M5 used the M2 chess simulator and custom PyTorch Double DQN. Six runs completed at 50,000 valid decisions each: Warm-start and Scratch for training seeds 20261104, 20261105, and 20261106. The accepted source limitation RSK-014 remains: strict byte-identical source provenance for all six runs is not established.

The accepted M3 release has 1,000 games and 19,268 positions, manifest SHA-256 be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12. The third-party source license remains unstated/unverified. Dataset files and teacher scores are not included in the model package or inference path.

## Inputs, outputs, and use

- **M4 input:** reconstructed chess board, rule metadata, full UCI history, and current legal UCI candidates.
- **M4 output:** uncalibrated preference logit per supplied legal candidate.
- **M5 input:** same symbolic state/history/legal-candidate contract.
- **M5 output:** scalar Q estimate per legal candidate; the frozen policy selects among legal semantic UCI actions.
- **ALE integration:** ALE RGB is the observation source of truth. A shadow board may track/cross-check verified history but cannot replace emulator observations. Cursor execution and move verification are separate controller components.

Intended use is research, education, reproducibility, and controlled evaluation under the accepted protocol. The models are not intended as competitive/production chess engines and do not guarantee full-game performance.

## Evaluation summary

| Track | Result | What it means |
|---|---|---|
| M4 imitation | Legal top-1 29.8979%, top-3 54.3996%; 2,057 test positions | Historical move agreement, not game strength |
| M5 simulator | 1,500 rows; 1,494 terminal, six truncations; three paired training seeds | Simulator outcomes do not establish ALE performance |
| M6 v1 | Three terminal losses, 32 incomplete / 35 scheduled | Separate 54,000-frame / 900-second integration profile |
| M6 v2 | 11 terminal losses, nine incomplete / 20 scheduled; 385/405 RGB-verified; zero desynchronizations | Distinct extended-horizon profile; reused v1 seeds |
| M7 Option B | 60 terminal losses, 30 incomplete / 90 scheduled; zero wins/draws | White-only, one built-in ALE opponent; no superiority conclusion |

M7 terminal-only scores are 0.000 for groups with terminal games because every observed terminal result was a White loss. Warm seed 20261105 had zero terminal games, so its score is undefined. Incomplete attempts are not draws. Only 9/30 Warm/Scratch matched cells had terminal outcomes; a paired interval is unavailable. Elo is not reported.

## Limitations and out-of-scope use

- No claim of Elo, 1500 rating, strong chess ability, RL superiority, Warm-start superiority, equivalence, or broad generalization.
- No guarantee of complete games; M7 had 30 incomplete attempts and controller uncertainty/timeouts.
- M7 covered White against one built-in ALE opponent, not a calibrated diverse pool or Black-side play.
- Three training-seed pairs severely limit method-level inference; evaluation seeds do not add independent trained policies.
- Simulator-to-ALE transfer is not established.
- O-02 remains open; no confirmed academic submission criterion is claimed.
- RSK-014 and PM6-F06 remain disclosed.
- Do not retrain, fine-tune, replace checkpoints, or add opponents without separate authorization.

## Artifacts and distribution

Checkpoint binaries are owner-controlled local artifacts and are not stored in this repository. Sidecars and accepted root/run manifests provide integrity identities. M4/M5/M6/M7 artifact hashes are summarized in accepted evidence; committed hashes do not imply that private files are present in a clone. Access must be supplied by the Project Owner through an authorized local path.

**No public model release is authorized.** G4 evaluation approval does not approve G5 or publication.


## Evidence

- [M4 final acceptance](../../.agents/evidence/M4-final-acceptance-20261027.md)
- [M5 final report](../04-research/M5_FINAL_REPORT.md) and [M5 PM acceptance](../../.agents/evidence/M5-PM-acceptance-20261030.md)
- [M6 v1 report](../../.agents/evidence/M6-001-final-report-20261031.md), [M6 v2 report](../../.agents/evidence/M6-001-final-report-v2-20261031.md), and [PM6-F06 erratum](../../.agents/evidence/M6-PM6-F06-erratum-20261031.md)
- [M7 frozen population and campaign](../../.agents/evidence/M7-001-acceptance-20261101.md), [raw-derived analysis](../../.agents/evidence/M7-analysis-final-r2-20261101/M7_ANALYSIS.md), [Elo disposition](../../.agents/evidence/M7-003-acceptance-20261101.md)
