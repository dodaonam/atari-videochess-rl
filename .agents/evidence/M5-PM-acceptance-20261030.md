# Independent PM Acceptance — M5 / PR #11

**Decision authority:** Independent Project Manager disposition published by the project owner in the PR review thread.
**Decision timestamp:** 2026-10-30T08:22:10Z.
**Decision link:** [PR #11 PM disposition](https://github.com/dodaonam/atari-videochess-rl/pull/11#issuecomment-6518394524).
**Reviewed feature HEAD:** `35a99f0eaf14039a94c199e51da370ec2b2e7fec`.
**PR target:** `initial-idea`; PR #11 remains open and unmerged.

Independent PM accepted M5-01 through M5-05 for the completed simulator campaign, with documented limitations on M5-03/M5-04.

## Acceptance dispositions

| Criterion | PM disposition | Scope and limitation |
|---|---|---|
| M5-01 | ACCEPT | Double DQN online selection, target evaluation and legal semantic UCI handling accepted on the reviewed evidence. |
| M5-02 | ACCEPT | Fixed agent perspective and transition/reward semantics accepted on the reviewed evidence. |
| M5-03 | ACCEPT WITH DOCUMENTED LIMITATION | Replay, target network, exploration, checkpoint/resume and opponent provenance accepted. Whole-file historical CLI provenance remains unavailable; byte-identical campaign reproduction is not established. |
| M5-04 | ACCEPT WITH DOCUMENTED LIMITATION | Completed controlled simulator comparison accepted. Only three training-seed clusters and six evaluation truncations limit precision; Warm-start superiority over Scratch remains inconclusive. |
| M5-05 | ACCEPT | The approved baseline did not silently combine curriculum learning, reward shaping or auxiliary losses. |

## BLK-003 and RSK-014

The PM authorizes closing **BLK-003 by independent PM risk acceptance**. The recovered historical `replay.py` and `checkpoint.py` match their recorded hashes; replay insertion, eviction, sampling, state handling and journal append were audited as unchanged. The recorded changes relate to checkpoint validation/recovery and CLI resume selection. Both seed-20261106 training runs were fresh `attempt-0000` starts with no resume parent. The available evidence shows no learning-distribution change that warrants invalidating the completed campaign or repeating training.

**RSK-014 remains an accepted residual auditability risk.** The first four and final two training runs retain different aggregate source identities. Complete whole-file historical `cli.py` bytes remain unavailable. The PM did not accept a claim of strict source homogeneity or byte-identical whole-campaign reproduction. This disposition accepts the risk for M5; it does not erase the source difference or establish stronger provenance than the available evidence supports.

## Scientific scope and limits

The accepted evidence concerns the M2 chess simulator only. It does not establish performance in Atari ALE VideoChess. The campaign used three paired training seeds; Warm-start versus Scratch post-training superiority is statistically inconclusive. Frozen M4 and SimpleHeuristic were stronger overall on the reported benchmark. Six evaluation scenarios reached the approved 400-decision truncation limit and remain separately identified.

The PM reviewed `.agents/evidence/M5-source-recovery-20261030.json`, `.agents/evidence/M5-source-semantics-20261030.json`, the recovery/semantic reports, the campaign and manifest verification records, the final research report, 383-test local and clean-clone evidence, and GitHub Actions run 41023855357 on the exact reviewed HEAD. The PM explicitly notes that private multi-gigabyte artifacts were not independently rehashed remotely; local read-only verifier records and preserved hashes are the available evidence for those private files.

## Governance boundary

This record documents **technical/scientific M5 acceptance only**. It does not mean PR #11 has been merged, does not approve G3, and does not authorize M6. PR integration and G3 review remain reserved for the PM. Additional official training and evaluation are not required or authorized by this decision.
