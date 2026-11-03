# Post-Merge Atari Demo Reliability Remediation

**Status:** Implemented and undergoing final verification. This is a later
engineering reliability change against the squash-merged improvement campaign;
it does not modify or reattribute the completed experiment.

## Scope and preserved experiment

The remediation branch is based on `main` commit
`a5515c8b006c65e38c61086883f1c83ba377e62a` (tree
`e4d767c445eed212ca54587fe622a18881fb6854`). The official run, its selected
checkpoints, and all accepted dataset, simulator, and Atari evaluation records
remain unchanged. No training, new seed, HPO, Stockfish labeling, or scientific
evaluation campaign was run.

The accepted models remain identified by their original SHA-256 values:

- M4-A: `cf5e437ff4e2d6a8e85739df751dec33f16b7bc4c92268f996ec4c612d62feed`.
- Double DQN at 250,000 decisions: `48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293`.
- Frozen Double DQN training-code digest: `cf329438880a82b7b39b05b8f1f3bc1af21e262edb4143e1035e494f891a5705`.
- Frozen official training-config digest: `2cfe2805edd3e05756fd3ef981a6e4441e3b4ad717649d5647085228e837aabd`.

## Finding dispositions

| Finding | Root cause | Correction and verification | Disposition |
|---|---|---|---|
| DEMO-F01 | The CLI reset seed was also treated as immutable checkpoint training metadata. | The loader now validates M4 and Q checkpoint provenance against fixed accepted metadata and the official run record. The independent `policy_rng_seed` seeds the adapter; `--reset-seed`/legacy `--seed` controls ALE. GUI and preflight report both identities. Mocked hash/metadata tests and real custom-seed preflight/smoke cover M4-A and Q. | Resolved. |
| DEMO-F02 | Auto-smoke shutdown depended on a saved trace; worker exceptions could produce no trace and leave Tk running. | The worker always emits terminal lifecycle status, preserves exception type/message/traceback, reports trace-write failures separately, and closes automated mode on failure. The UI detects unexpected worker death. CLI checks verification/trace files defensively and returns nonzero on failure. Injected environment/ROM/reset/policy/frame exceptions and trace-write failure are tested. | Resolved in tested paths. A native ALE call that never returns remains bounded only by the documented outer process timeout. |
| DEMO-F03 | Trace-save events overwrote episode stop details; early blocked returns omitted terminal progress. | Episode, trace persistence, and worker state are separate. Trace-save notifications update a separate field; one guarded `episode_finished` event now covers early ROM/profile and artifact-budget returns as well as normal completion. Terminal/truncation/cancellation categories remain distinct. | Resolved. |
| DEMO-F04 | The accepted Q attempts stop on an occupied-target capture after target FIRE; existing evidence cannot distinguish Atari input acceptance from recognition. | Rechecked the private deterministic traces and reproduced the conservative stop with an isolated one-frame target-FIRE diagnostic. That diagnostic verified four player turns and replies before a separate target-confirmation stop; it did not verify the original capture and does not establish press duration as cause. No unsafe correction was made: there is no blind retry and the shadow advances only on RGB verification. Existing and new M1 safety tests pass. | Unresolved Atari controller limitation; safe behavior retained. Do not claim full-game Atari capability. |
| DEMO-F05 | No single preflight validated prerequisites before a GUI session. | `--preflight-only` checks Python/dependencies, memory, Tk/display, actual ALE/Gymnasium construction and profile, ROM SHA, action/RGB contract, policy SHA and immutable metadata, and writable output/disk. It does not reset or step ALE. Stockfish is not a requirement and is not checked. Failures include observation and remedy. | Resolved for checked prerequisites. |
| DEMO-F06 | Runner frame cap (150,000) exceeded the observed ALE profile horizon (108,000) without an upfront explanation. | The viewer now reports both caps, environment-step cap, move/wall-clock limits, opponent response timeout, and artifact-byte limit. ALE termination, ALE truncation, and runner stops are displayed separately; truncation is incomplete. Existing episode-limit tests and new GUI status test cover these distinctions. | Resolved as reporting/accounting; active ALE horizon remains profile-controlled. |
| DEMO-F07 | Second-resolution policy directories could collide. | Session directories are allocated with a timestamp plus random session token using atomic `mkdir(exist_ok=False)` and bounded collision handling. Concurrent allocation and pre-existing directory preservation are tested. | Resolved. |

During remediation, a real M4-A smoke exposed a narrow Tk race: the worker
could publish `trace_saved` and `worker_finished` just after the GUI drained its
queue, while the poll then saw the thread exit and prematurely classified it
as unexpected. The trace had been written, but the GUI missed the queued
completion events. A single bounded 10 ms grace poll now drains those final
events before treating a silent exit as unexpected. A regression injects the
same interleaving. Both policies were re-smoked after this correction and
finished with successful trace, replay, and layout checks.

## Bounded real-ALE verification

The local environment provided ALE-Py 0.11.2, Gymnasium 1.4.0, the verified
VideoChess ROM (`d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`),
Tk 8.6, and a display. `--preflight-only` passed for M4-A and the selected
Double DQN snapshot with Atari reset seed `123456`; the models retained training
seed `20261103` and the expected checkpoint hashes.

Bounded `--auto-smoke` sessions using each policy ran in real ALE with reset
seed `123456`. Each completed two player moves and two Atari replies verified
from RGB, resized the live window, and stepped replay backward and forward.
These are GUI/integration smoke tests, not full-game outcomes or new scientific
evaluation attempts. The detailed raw trace/frame files remain ignored local
artifacts.

An additional private controller diagnostic used the same deterministic reset
and the previously recorded action prefix with one target FIRE frame. It
verified four moves/replies and then stopped on target-confirmation uncertainty
at a different move. No result was accepted without RGB verification. Its
private trace is retained locally only.

## Presentation layout reference

The owner-provided local GUI reference was read without modification. The
repository viewer now uses its useful presentation pattern: a reserved
side-by-side information panel, a White/Black move scorecard, a visible pending
agent move, scrollable history, explicit replay buttons, and keyboard replay.
The implementation remains repository-contained and uses this campaign's
strict checkpoint loader, verified live runner, and path/configuration
contracts; no external script is required. The demo verification additionally
checks the 1100×680 resized layout for board/panel overlap and clipped labels
or move table.

## Verification and known limits

The machine-readable command/test ledger is
`.agents/evidence/improvement/reliability-hardening.json`. The final test
counts and source revision there are updated after the committed clean-source
verification. Full repository regression includes the existing M1 RGB,
controller, episode, policy, RL and phase-2 evaluation suites. Private-artifact
tests may be skipped in a clean checkout and are reported as skips rather than
passes.

The Double DQN controller's occupied-target confirmation issue remains
unresolved. The accepted actual-ALE campaign observed no terminal win, loss, or
draw. The remediated GUI does not change those outcomes. The live demo is
bounded, and no full-game capability is claimed.
