# PR #24 Independent PM Review Remediation

## Status and scope

This record covers the targeted remediation requested after the Independent PM's
`REQUEST_CHANGES` decision. It preserves the completed Phase 2 experiment and
does not authorize integration. PR #24 remains the only PR for this campaign;
it must remain open and unmerged pending the PM's final decision.

The accepted official run remains seed `20261103`, 250,000 valid decisions,
62,245 optimizer updates, and 124 target synchronizations. The M4-A and selected
Q checkpoint hashes, training configuration, training-source digest, dataset,
replay, snapshots, and original evaluation results are unchanged.

## Finding disposition

| Finding | Root cause and evidence | Corrective action | Verification | Disposition |
|---|---|---|---|---|
| PM24-F01 | The initial public Atari aggregate copied `verified_atari_opponent_uci` arrays from six private traces: 3 × 9 Q-policy replies and 3 × 12 M4-A replies (63 UCI move records). The records were partial opponent sequences, not complete games, and contained no RGB. `git log -S` identifies commit `0596698249d74da4dd9184a12975f83efd08bca3` as the commit that introduced the field. | Removed move arrays and private raw-trace paths from the tracked aggregate. The generator now emits only per-attempt aggregate fields and the SHA-256 of each private trace. Added a schema regression test. Original detailed traces and frames remain in ignored local artifact storage. | Focused privacy/schema test; JSON recursive scan; changed-path and binary audit; private trace checksums retained. | Tip sanitized. Historical PR exposure remains; see Integration history decision below. |
| PM24-F02 | The recorded full suite failed only because `stockfish` was not on `PATH`. The accepted Stockfish 19 executable was present at `.venv/share/stockfish/stockfish`; its binary SHA-256 matches the Phase 1 identity `0f83d24c…c12da19`. | Added that existing directory to the process `PATH`; no install, relabeling, or engine search was performed. | UCI readiness test passes; the full suite was rerun with the same environment adjustment. Exact totals and log digest are in `phase2-remediation-verification.json`. | Resolved. |
| PM24-F03 | The previous verification record used an ambiguous `final_head` for `a8d0f36…`, while the PR was already at `d35520a…`. | Renamed prior identities as the head/tree verified before the final metadata commit. Added distinct training-source, tested-source, full-suite-tested, clean-checkout-tested, review-baseline, and pushed-head fields. The final remediation record names the commit on which it was written and records the live remote identity separately. | Local/remote refs, PR API state, base SHA, tree, latest check, and clean checkout verified after push. | Resolved without rewriting training provenance. |
| PM24-F04 | All three Q attempts reached the same verified pre-move board and selected the same legal occupied-target capture. RGB verified source selection and selected-piece preview at the intended target. One 16-frame target FIRE press was released; three bounded passive observation windows still showed the selected preview and no committed board transition. The controller stopped without retry. Private raw traces have matching legal state/action evidence across all three seeds. | No controller behavior was changed because the trace does not distinguish an ALE capture-confirmation rule from an input edge/acceptance issue. Retrying FIRE or accepting the candidate move without a changed RGB board would weaken synchronization safety. | Existing private traces and per-attempt checksums inspected; controller phase and stop logic reviewed. No new evaluation attempt was run. | Documented unresolved Atari controller limitation; conservative stop remains. |
| PM24-F05A | The viewer footer hard-coded the default seed `20261103`, even when `--seed` configured a different ALE reset seed. | Pass the actual CLI seed to the viewer and display it as the Atari reset seed separately from model training seed. | Unit test verifies custom seed propagation and distinct labels; a bounded custom-seed ALE GUI smoke records the actual footer text. | Resolved. |
| PM24-F05B | The evaluator stored both 20-game stage-one candidates and 60-game finalists in one ranking and selected from the mixed list. The frozen protocol uses stage one only to choose the top three extension candidates. | Final selection now considers only candidates marked as extended; initial-stage ranking and all candidate summaries remain separately recorded. | Regression test gives an unextended candidate a perfect 20-game score and confirms a lower-scoring extended finalist is selected. Existing results show the 250k snapshot was one of the three finalists and remains first under the frozen 60-game rule. | Resolved; selected checkpoint unchanged. |

## PM24-F04 diagnostic evidence

The three Q attempts share the same first nine player/opponent turns and reach
the same legal state. The next Q action is an ordinary legal capture onto an
occupied Atari square. The trace records one source FIRE, verified source
selection, verified cursor navigation to the target, and one target FIRE held
for the configured 16 frames. After release, the selected-piece preview remains
visible through three passive observation windows; no complete RGB board
transition is observed. The player move is therefore not added to verified
history. This local evidence supports a controller/input-confirmation failure
after policy selection, but it does not establish whether the game rejected the
capture, whether the FIRE event was not accepted, or whether the visual verifier
could not recognize the accepted transition. No neural-policy defect is
inferred from this evidence.

The exact raw traces and PNG frames are private. The sanitized public evidence
retains their SHA-256 values, attempt seeds, counts, stop category, policy and
checkpoint identities, and aggregate outcomes.

## Privacy and Git history

The sanitized tip contains no individual UCI move arrays, raw trace paths,
RGB payloads, ROMs, datasets, checkpoints, replay data, or model weights. The
one originally affected public file was added in commit
`0596698249d74da4dd9184a12975f83efd08bca3`; that commit remains reachable from
the published feature branch and PR commit list. Removing the field at the tip
does not erase that prior exposure, and no force-push or history rewrite was
performed.

The wider proposed PR diff also contained absolute workspace and Downloads
paths in command records, old test logs, and optional legacy-GUI notes. The
current tracked tip now represents repository-root command prefixes as
`${REPO_ROOT}`, redacts the external GUI location while retaining its
SHA-256/smoke result, and rebinds the affected log hashes. The optional GUI
smoke helper now requires an explicit `--script` path and has no machine-local
default. No credentials or private-key markers were found. The previously
published feature history still contains some of those original path values;
the same integration-history decision applies.

The path-bearing records were introduced in reachable feature commits
`2d390fe7df862e998960e8fdc4cdef5f93f2bd5c`,
`5014258afb28ffed045e9f285120c0ae6cce4f53`, and
`964c241080b37951a6b10eb3d891ef227562f1c2`; the sanitizer is in
`1540653b1d6a57a3ffb9b8c0afe7e4666418ea05`. The Atari move-sequence field was
introduced separately in `0596698249d74da4dd9184a12975f83efd08bca3` and removed
at the same sanitizer commit.

A normal merge commit would retain the feature commits in `main` history. A
squash integration of the sanitized final tree would put only the net sanitized
tree change into `main`, without importing the intermediate feature commits.
The branch/PR commit history would still remain visible on GitHub. The
Independent PM/Project Owner must choose and authorize the integration method;
the executor has not merged the PR.

## Revision identity interpretation

The following identities are intentionally separate:

- Official training source commit/tree: `76c898ed0dd8a2e8bf0c76cbd8565f83077284e0` /
  `b5877036a2e954c085e0da386c0bcb596ff21ab3`.
- Frozen official training code digest: `cf329438880a82b7b39b05b8f1f3bc1af21e262edb4143e1035e494f891a5705`.
- Frozen official training config digest: `2cfe2805edd3e05756fd3ef981a6e4441e3b4ad717649d5647085228e837aabd`.
- PR head at the PM's initial review: `d35520a0301a7c5413c26f1792762b51d58a48df`.
- Tested implementation and full-suite-tested revisions are recorded per command
  in `.agents/evidence/improvement/phase2-remediation-verification.json`.
- Final pushed PR head/tree are recorded by the live remote check and in the
  handoff. The machine evidence identifies the revision at which that record
  was written rather than claiming a self-referential hash for its own commit.

No post-training fix changes or relabels the frozen training digest or any
scientific result.

## Remaining decision

The only integration blocker is the required owner/PM decision on how to
integrate a branch whose published intermediate commit contained move-level
metadata. The tip is sanitized, and squash integration can keep the unsanitized
intermediate patch out of `main`, but only the Independent PM/Project Owner may
decide whether that is sufficient. The Atari target-confirmation behavior is a
documented engineering limitation, not a fabricated terminal result.

## Verification results

- The accepted Stockfish 19 binary at `.venv/share/stockfish/stockfish` matches
  the Phase 1 SHA-256 and passed the focused UCI readiness test. No package was
  installed and no analysis/search was run.
- Focused remediation suite: 12 tests passed, zero failed, zero skipped. The
  real-ALE custom-seed smoke displayed the reset seed separately from the
  model seed and verified two player/opponent turns and replay in both
  directions.
- Full repository suite on clean checkpointed commit
  `ee6668b56fefd1678a9f16897fc83da9d9ce43f9`, tree
  `462145abefce566d53e893ddab2d2956b718ce2f`: 556 tests, 552 passed, zero
  failed, four private-artifact tests skipped; exit code 0. The retained log is
  local at `artifacts/improvement/videochess-improvement-20261103-v1/private-logs/pm24-full-tests-clean-final.log`; its digest and timing are in the machine-readable verification record.
- Two earlier full-suite attempts are retained as failed diagnostics: one ran
  with a dirty tree and failed the Git-snapshot context assertion; the next
  exposed the temporary canonical governance-text regression. That text was
  restored, checkpointed, and the clean full suite then passed. Neither failed
  diagnostic is described as a pass.
