# DEMO-F04 Root Cause and Permanent Remediation

**Status:** Corrective implementation and real-ALE validation completed. The PM27-F01 bookkeeping follow-up is included; its full suite has 631 tests with 4 private-artifact skips. Pull request review is pending.

**Claim boundary:** The selected Double DQN now passes the historical capture and has completed multiple actual ALE games in this environment. This evidence supports the identified timing defect and the correction. It does not establish universal reliability over all games, ROM revisions, ALE profiles, or positions.

## 1. Repository and runtime identity

- Repository: `dodaonam/atari-videochess-rl`.
- Verified base: `main` / `origin/main`, commit `b7bbd8a6e64373dfe8b81ca88ad23184dff802d4`, tree `b3eac5aba1a427f40824648c18b9b3a7a5a00a8f`.
- Work branch: `fix/demo-f04-permanent-remediation-20261104`.
- Selected policy: `double_dqn_250000`, Q-only Double DQN, immutable training seed `20261103`, 250,000 accepted decisions.
- Checkpoint: `artifacts/improvement/videochess-improvement-20261103-v1/official/attempt-0000/snapshot-250000.pt`; SHA-256 `48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293`.
- Environment: `ALE/VideoChess-v5`, mode 4, RGB, frameskip 1, repeat-action probability 0, difficulty 0.
- ROM SHA-256: `d44f2a115393b0a6cbcd5398d62369e652f3670a9ee585883d183e740edad0f7`.
- Runtime: Python 3.12.3, ALE-Py 0.11.2, Gymnasium 1.4.0, python-chess 1.11.2, CPU PyTorch 2.14.1+cpu.
- The official policy checkpoint, ROM, training data, accepted evaluations, and model configuration were not changed.

## 2. End-to-end interaction audit

The audited path is reset RGB/RAM → board reconstruction → policy decision → legal UCI validation → observed cursor route → source selection → selected-target navigation → target FIRE → RGB move verification → Atari reply → RGB reply verification → next policy context. For the exact pinned ROM, the runner now also checks the full RAM piece map against the verified shadow board at reset and before every policy decision.

| Boundary | Required evidence and behavior | Failure handling |
|---|---|---|
| Reset → initial board | Stable RGB start board and exact `$80-$BF` piece/color map agree with the standard chess start. ROM SHA must match the validated ROM. | Stop before policy input if either source disagrees or RAM is absent. |
| Policy → move | Policy receives the last verified board; returned UCI is parsed and checked against that board's legal moves. The latest RGB frame and full RAM board are cross-checked before selection. | Stop on malformed/illegal move or any state mismatch. |
| Source navigation → source | Route is recalculated from observed RGB cursor position. A stable board and unique cursor must identify the source. One source FIRE press is sent, then selection requires both selected-piece RGB evidence and the validated ROM interaction state/source registers. | Stop before target input if source selection is uncertain. |
| Target navigation → target | Every direction is followed by a release/observation. The selected preview, ROM target register, ROM legal flag, and exact unchanged squares are checked. The validated cursor/source/target registers distinguish target position from an action merely requested. | Stop before target FIRE if preview or independent target register is uncertain. |
| Target FIRE → Atari acceptance | One FIRE press is held for at most 32 ALE frames. The runner checks each ALE step and releases early only when ROM `$F3` enters search state, source/target registers still name the pending move, and `$F5` marks it valid. One release follows; FIRE is never retried. | If there is no matching acknowledgement by the cap, release once and fail closed. Acknowledgement alone does not update shadow state. |
| Move → RGB state | A complete legal candidate board (or the existing cursor-masked RGB candidate) is observed, then the Atari reply must itself be uniquely identified and verified. | No shadow advancement from policy intent, RAM preview, or selected-piece preview. Stop on unresolved/mismatched state. |
| Next policy context | Stable RGB board, unique cursor, and full exact ROM piece map match the current shadow. | Stop on any disagreement, preventing hidden divergence from becoming a later policy input. |
| ALE terminal | ALE termination/reward are recorded separately from chess-result interpretation. When the final rendered frame is the ROM's blank terminal screen, terminal RAM must match one unique legal pending player move plus one unique legal Atari reply; the resulting position must be checkmate and the reward must match the winner. | Otherwise keep the final transition incomplete. The terminal screen is not stored or displayed as a fabricated board snapshot. |

The primary ROM layout and interaction-state definitions were compared with the [Video Chess disassembly and commentary](https://nanochess.org/video_chess.html): `$80-$BF` is the 64-square board; low nibbles encode piece and color; `$F3` distinguishes cursor, selected, moving, and search states; `$F5` is the move-validity flag; and `$E4` counts half-moves. The disassembly also documents RAM reuse across code paths. Therefore, `$D9/$DA` source/target meanings are enabled only for the pinned ROM and selected interaction path, and were independently verified across RGB-checked live positions and the exact h1h4 reproduction rather than treated as globally stable RAM fields.

## 3. Root-cause verdict and hypothesis ledger

### Confirmed cause

The historical controller held target FIRE for 16 ALE frames and released it before the ROM acknowledged the h1h4 capture. Replaying the recorded pre-FIRE state and inspecting RAM at every frame showed `$F3=1` (piece still selected), the board unchanged, and the source/target registers still h1/h4 through held frame 21. A single continuous hold entered `$F3=$C0` (ROM chessboard-search state) at held frame 22. This matched target/source state and valid-move flag. The baseline trace proves the 16-frame press was executed by the ALE API; it does not mean the ROM had accepted the move.

The ROM disassembly describes the transition from selected-piece state to move/search state and a frame counter before search. In this recorded interaction the fixed 16-frame press ended too soon for that transition. The controller then correctly refused to advance its shadow board. A separate successful capture reached the same unstable RGB-preview/source-cursor signature, so the RGB preview heuristic could not by itself distinguish an accepted capture from a still-pending selection.

### Candidate causes

| ID | Mechanism and evidence | Disposition / confidence | Action and residual risk |
|---|---|---|---|
| H1 — cursor missed target | In the failing pre-FIRE state, the ROM source/target registers decoded to h1/h4; target register advanced to h4 before FIRE. | Contradicted for the historical attempt; high confidence. | Independently validate target registers and RGB preview before FIRE. Other cursor states still stop if ambiguous. |
| H2 — weak target preview | The synthetic mixed-window regression proves the RGB heuristic can be positive in an unstable window. Historical RAM and control state independently showed h1/h4 selected, so this was not the immediate capture failure. | General susceptibility supported; not causal in this run. | Keep RGB evidence and require independent, ROM-pinned target evidence. A different ROM is rejected. |
| H3 — target FIRE not accepted | Baseline press ended at frame 16 with `$F3=1`, unchanged board, and no move transition. Continuous hold from the same state entered `$F3=$C0` at frame 22. | Confirmed as insufficient hold duration for the observed game phase; high confidence. | Increase maximum one-shot hold to 32, stop early on matching ROM acknowledgement, then release once. No retry. |
| H4 — accepted move missed by RGB | No target move was committed in the historical 16-frame attempt; source/target remained selected and the exact board remained unchanged. | Contradicted as the immediate h1h4 cause. Later terminal RGB absence is a separate, observed blank-screen condition. | RGB remains required for ordinary advancement; terminal-only exact-RAM rule is explicit. |
| H5 — transient mixed preview stuck positive | Synthetic mixed-window test demonstrated susceptibility. Real failing preview was unstable but RAM showed the move remained selected, not committed. | A real algorithmic risk, but not proven as the cause of DEMO-F04. | Use exact unaffected-square RAM preview check; never let preview alone advance shadow. |
| H6 — cursor and selected state inconsistent | F3 and target/source registers agreed with h1h4 at the actual target FIRE boundary. | Contradicted for the historical attempt. | Recheck all fields immediately before FIRE and record them with the action. |
| H7 — frameskip/sticky action semantics | Historical configuration was frameskip 1 and repeat probability 0. The target press had one release and no sticky repeat. The hold-length intervention changed only press duration. | Frameskip/sticky action did not cause the historical stop; duration was causal. | Keep the selected profile. A frameskip-4 comparison is not interpreted causally because its game trajectory differed. |
| H8 — insufficient post-FIRE settling | Passive windows after release did not help because the game had not accepted the move during the expired press. | Contradicted as the primary cause. | Observe the ROM acknowledgement while FIRE is still held; keep bounded post-FIRE RGB verification. |
| H9 — earlier hidden board divergence | Full RAM piece identities matched the shadow at the reset and policy-decision contexts in the reproduced game; the exact h1/h4 registers and move-valid flag matched the intended legal capture. | No evidence of earlier divergence in the reproduced trajectory; medium-high confidence. | Recheck exact board map at every later decision; any mismatch stops play. |

The policy itself was not changed. The evidence does not establish that every possible controller ambiguity is eliminated; failures still stop rather than guess.

## 4. Before/after historical capture

**Before:** Historical trace SHA-256 `26abcfe12fdf3a77cff6ef4f4e15588cad00946505b1c6a4aa908a5a3b594433`. Attempt 10 selected `h1h4`; 10 attempted player moves, 9 RGB-verified player moves, 9 RGB-verified Atari replies; stop `CONTROLLER_TARGET_CONFIRMATION_UNCERTAIN`; ALE was neither terminated nor truncated; shadow remained at the pre-capture state. The target FIRE action ran for 16 frames, but the ROM stayed in selected-piece state.

**Controlled reproduction and intervention:** Private frame/RAM diagnostic SHA-256 is recorded in local `artifacts/demo/f04-ram-investigation/long-fire-probe.json`. It replays the exact historical pre-FIRE state; the held press remains unaccepted through frame 21 and is acknowledged at frame 22. ALE-Py exposes `cloneState`/`restoreState`; the cloned state was restored twice and both independent 22-frame branches produced identical RGB and full-RAM SHA-256 values. The 16-frame branch remained selected and had the same RGB and board-piece hash as the pre-FIRE state. Clone/replay evidence SHA-256: `5208e96fedbc7e28b8ab46932ad6f4267392bad836b3bbaf293c2f7d5b8b5fd3`. The probe did not edit ALE state and did not count as an operational game move.

**After:** The exact seed/policy/profile trajectory chose `h1h4` at attempt 10. ALE acknowledged its one target FIRE press on frame 22; the move and subsequent Atari reply were RGB verified, and play continued to the configured cap. A separate complete-game run verified 14 player moves and 14 Atari replies (13 pairs via RGB, final pair via the strict terminal-RAM checkmate contract). No move was avoided by changing model, seed, profile, or policy.

## 5. Implementation and safety

- `videochess_rl/atari_ram.py` decodes the pinned ROM's exact board piece identities, source/target indices, interaction mode, move-valid flag, and half-move counter; it rejects malformed snapshots and mismatched/unvalidated ROM use.
- `videochess_rl/environment.py` attaches a copied 128-byte ALE RAM snapshot to each in-memory frame. RAM arrays are not written to action traces or public evidence.
- `videochess_rl/controller.py` sets the live runner's default target-FIRE maximum to 32 frames. It remains one press followed by one release.
- `videochess_rl/episode.py` verifies reset/decision boards, selection and target state, and matching target-FIRE acknowledgement. It checks each ALE frame and releases after acknowledgment. Explicit caller timings are honored as declared; the existing M6 and M7 protocol records that specify 16 frames remain unchanged and are not represented as receiving this remediation. Normal shadow advancement still requires established RGB verification of player move and Atari reply. Its terminal-only RAM reconciliation is limited to a uniquely matching legal mate sequence after actual ALE termination and matching result reward.
- `videochess_rl/shadow.py` adds a terminal-only sequence application API with legal-move, exact terminal board, checkmate, reward, and ALE termination preconditions.
- `videochess_rl/improvement/demo.py` exposes separate RGB/terminal-RAM counts and validates the terminal sequence in the saved replay trace. `--close-on-finish` closes only after ALE and artifacts finish.
- `videochess_rl/improvement/live.py` labels terminal-RAM moves distinctly, represents the blank terminal screen as terminal evidence without a chessboard snapshot, and preserves replay/summary before optional close.

Safety invariants retained:

1. No policy-intention-only shadow advancement.
2. No selected-preview-only advancement.
3. No inferred Atari reply.
4. No RAM substitution for ordinary RGB move verification.
5. No blind FIRE retry or repeated non-idempotent action.
6. No fabricated game result, trace snapshot, or replay frame.
7. No model/checkpoint switch or model/training/evaluation changes.
8. Unknown ROMs, malformed RAM, mismatched board, invalid target, missing acknowledgment, ambiguous RGB, and ambiguous terminal sequence fail closed.

## 6. Real-ALE verification

All runs use the verified checkpoint and ROM listed above, mode 4, frameskip 1, sticky-action probability 0, and the repository's real ALE environment. Each full-game invocation used the supported command (only `--seed` changes):

```bash
uv run --locked --no-sync python -m videochess_rl.improvement.demo \
  --policy double-dqn \
  --checkpoint artifacts/improvement/videochess-improvement-20261103-v1/official/attempt-0000/snapshot-250000.pt \
  --checkpoint-sha256 48dbbb860c8f997105b7bd30863892294e68ef489185ac6172fb7b459df5c293 \
  --seed 20261103 \
  --max-player-moves 200 \
  --max-seconds 1800 \
  --close-on-finish
```

The exact executable used for recorded repository-entrypoint runs was `.venv/bin/python` with the command above; it was created from the locked project environment. The GUI uses the registered ALE horizon (108,000 frames); supplemental controlled direct-run traces used an explicit 500,000-frame emulator horizon. The GUI seed-20261103 run completed below the registered horizon, so the larger direct-run horizon did not create the observed terminal outcome.

| ALE reset seed | Entrypoint and relevant limits | ALE result | Verified interactions | Evidence SHA-256 |
|---|---|---|---|---|
| `20261103` | Repository GUI command above; 200 moves, 1,800 seconds; default 108,000 ALE frames. | `ALE_TERMINATED`, not truncated; reward `-1`; 35,342 ALE frames; White loss by checkmate. | 14 player moves and 14 Atari replies; 13 + 13 RGB, final player/reply pair +2 terminal-RAM; zero incomplete moves. | Trace `d7ffc65aa20a21b42a30dce903b484ae4a7a2a8942497a126dba10516d1ab56e`; summary `e046324483ed392e7b902703053a9a56f21e2d1cc55ed35eec5a2707b7f20cd2`. |
| `20261210` | Repository GUI command above; 200 moves, 1,800 seconds; default 108,000 ALE frames. | `ALE_TERMINATED`, not truncated; reward `-1`; 35,342 ALE frames; White loss by checkmate. | 14 player moves and 14 Atari replies; 13 + 13 RGB, final player/reply pair +2 terminal-RAM; zero incomplete moves. | Trace `a85f18f402dc1df01617d15226c9547b36289abeb5df53f867f849ab4ac77c4c`; summary `3d5d832c2214626659b99c13aa814ef5660fcb04f1e9999061a9febd603335f9`. |
| `20261211` | Repository GUI command above; 200 moves, 1,800 seconds; default 108,000 ALE frames. | `ALE_TERMINATED`, not truncated; reward `-1`; 35,342 ALE frames; White loss by checkmate. | 14 player moves and 14 Atari replies; 13 + 13 RGB, final pair +2 terminal-RAM; zero incomplete moves. | Trace `7adc3892d4b7b0b140acca0db348381bbae93f10f8a26033fa4603dacee89907`; summary `3683d4ea0dc40fda558a7fdc37fa95f2078593221673f803fd859ef969f07795`. |

These different reset seeds produced the same deterministic trajectory and result in this setup; they are repeated runs, not evidence of diverse game-state coverage. The historical failing capture appears on the same trajectory and was processed after the fix. A prior first terminal-RAM implementation did reach ALE termination but left the final two moves unverified; that run is retained as a failed iteration, not counted above. The terminal rule and trace/UI accounting were corrected, and successful complete runs were repeated. Existing M6/M7 timing contracts that explicitly specify 16 frames were preserved to avoid silently changing an accepted scientific protocol; those paths need their own versioned evaluation decision before claiming this fix applies to them.

The private local evidence integrity manifest is `artifacts/demo/f04-remediation-real-ale/evidence-integrity-20261104-v2.json`, SHA-256 `cf3ab8205c0a8e82a1265d2eca1f9430b5e7b493a51af3fb27260bd79b08b8eb`. It records only file identities, sizes, and hashes; no raw evidence is included in Git.

## 7. GUI, replay, and terminal reporting

The supported repository GUI completed a full ALE game with the selected Q checkpoint. Its persisted summary records `worker_status=completed`, `outcome=ale_game_terminated`, `ALE_TERMINATED`, ALE reward `-1`, no incomplete move, no worker error, 27 available RGB replay snapshots, 26 RGB-verified half-moves, two separately identified terminal-RAM moves, and zero replay diagnostics. The final terminal frame is not counted as a chessboard snapshot. The trace retains the last RGB-verified FEN separately from the terminal-RAM-verified checkmate FEN.

The post-game summary, replay diagnostics, scorecard labels, and `--close-on-finish` behavior were verified through the supported GUI session. A separate `--auto-smoke` run at seed `20261103` passed with two RGB-verified move/reply pairs, a saved trace, a clean replay diagnostic result, successful Left/Right replay, and a valid 1100×680 layout. The PM27-F01 follow-up GUI/replay run's private verification record SHA-256 is `6bf7aae66eb88feb3e4e4c5f9ef5454da79d5b54477e880598f1fe9382dab434`. This is supplemental UI evidence and is not used as full-game evidence.

## 8. Automated verification and repository checks

- PM27-F01 focused command: `.venv/bin/python -m unittest tests.test_m1_episode tests.test_m1_shadow tests.test_demo_reliability -v` — **100 passed**.
- Full command on the committed follow-up: `PATH="$PWD/.venv/share/stockfish:$PATH" .venv/bin/python -m unittest discover -s tests -v` — **631 tests, OK, 4 skipped** (`188.984s`; 627 passed). The skips require unavailable private M4/M5 artifact roots/checkpoints: `test_accepted_m4_shared_transfer_and_fresh_paired_q_head`, `M6PrivatePolicyRosterTests`, and two frozen M5 policy-compatibility tests. The repository's existing Stockfish 19 executable was used from `.venv/share/stockfish`; no dependency was installed.
- Follow-up full-suite log SHA-256 (local `/tmp` record): `9023d412e160a7d20b37a13633224d48bed40dd300754638bfe1a640e9384229`.
- `python3 -m compileall -q videochess_rl tests` — passed.
- `git diff --check` — passed.
- `python3 scripts/agent_preflight.py` on code commit `b0890ea` and report commit `64ee346` — **PASS**. It recognized both clean commit transitions and matching portable snapshots; only the expected note remains that ignored artifacts need an independent manifest.
- `python3 scripts/audit_final_consolidation.py --output /tmp/atari-videochess-f04-pm27f01-privacy-head.json` on HEAD `64ee346` — passed with zero high-confidence credential matches, zero unexpected opaque payloads, and the historical authorized archive unchanged.

No raw frames, RAM arrays, complete move-level Atari traces, screenshots, ROMs, or checkpoints are included in Git. The new public report contains sanitized findings and artifact hashes only.

### PM27-F01 final-move verification-method bookkeeping

The player move's `verified_from_terminal_ram` flag now reflects whether terminal RAM had to verify that move. If RGB had already verified the player move, its terminal-RAM flag and count remain false/zero while the pending Atari reply is terminal-RAM verified. The summary therefore reports one terminal-RAM half-move, and replay keeps the RGB player move in its RGB count while applying only the missing Atari reply. If the player move had only a partial RGB candidate, both final player move and Atari reply are terminal-RAM verified; the summary reports two terminal-RAM half-moves and replay appends those two missing plies.

GUI scorecard reporting follows the same counts: it preserves an already RGB-verified player row and labels only the terminal-RAM reply. Tests cover both method paths, summary counts, legal replay reconstruction without duplicate plies, and GUI row labels. This follow-up changes bookkeeping and presentation only; it does not change ALE actions, state-acceptance conditions, or terminal safeguards, so no additional full-game ALE run was needed. The updated GUI/replay auto-smoke passed.

## 9. Scientific preservation and limits

- No training was started and no model, policy, reward, dataset, training seed, accepted M5/M6/M7 metric, prior evaluation record, or official checkpoint was modified.
- The live loss is a genuine ALE outcome for this trained policy and profile; it is not a claim that the policy is stronger or strategically sound.
- The target hold threshold is measured on the pinned ROM/runtime. Unsupported ROM hashes stop at reset. Other ALE profiles still need specific repeated validation before being described as equally reliable.
- The earlier frameskip-4 / repeat-probability-0.25 run reached 15 verified move/reply pairs before its diagnostic frame cap, but took a different trajectory. It does not isolate frameskip or sticky actions as causal. The h1h4 hold-duration intervention on the exact same pre-FIRE state is the causal comparison used here. No M5 Scratch/M5 Warm comparison was run; the selected Q-only checkpoint remained fixed.
- A terminal sequence can only be closed with the exact full RAM board, unique legal pending player move/reply, checkmate, genuine ALE termination, and matching reward. Other terminal positions with no usable RGB remain incomplete.
- More varied legal positions, all promotion/castling/en-passant variants, arbitrary Atari modes, hardware timing, and comprehensive game-level reliability remain untested.
- No merge, self-approval, release, or deployment is performed. The branch is intended for a focused non-draft pull request after final checks.
