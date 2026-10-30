# M6-001 Direct Owner Authorization

**Recorded:** 2026-10-30T14:39:05Z
**Authorized milestone/task:** M6 / M6-001
**Integration baseline:** `initial-idea` at `e6d444e475e447e9f37951f16585bf496f804c9d`, tree `6f17d57125b55fb3e3b5d963c03385e8f588d33e`

## Authority and entry decision

The project owner directly authorized M6-001 and its bounded implementation, local ALE experiments, and PR delivery. M6 is active; acceptance remains with the independent PM. The current-session instruction authorizes the complete **M6 End-to-End Execution Mission**. The instruction states that the independent Project Manager completed the Pre-M6 review and issued a CONDITIONAL GO; it also directly authorizes the engineering executor to satisfy remaining entry checks, activate M6-001, implement the M5-to-ALE path, perform the bounded local ALE experiments, retain local evidence, and open one PR against `initial-idea`.

The live GitHub record independently confirms PR #13 was accepted for Pre-M6 with documented limitations and merged at the baseline above. Its recorded PM disposition said M6 still required separate start authorization. This current owner authorization supplies that separate authorization. No separate PM M6 conditional-go record was found in the repository or PR #13 discussion during recovery; the conditional-go statement is retained here as reported in the owner's direct instruction, not represented as an independently fetched PM record.

## Authorized scope

- Implement and test the frozen M5/M4/baseline policy integration with the existing RGB vision, shadow, controller, and ALE `VideoChess-v5` environment.
- Run genuine local CPU ALE diagnostics and the predeclared Stage 3 roster: 10 Warm, 10 paired Scratch, and 5 each frozen M4, SimpleHeuristic, and RandomLegal attempts; White side, mode 4, difficulty 0, `frameskip=4`, `repeat_action_probability=0.25` for Stage 3.
- Use debug profile `frameskip=1`, `repeat_action_probability=0.0` only for Stages 1–2 diagnostics.
- Enforce at most 35 Stage 3 attempts, 900 seconds and 54,000 ALE frames per game, 10 hours total gameplay wall time, one serialized ALE process, 2 GiB retained compact evidence, and only one retry for a process-start failure before any Atari action.
- Read and verify the accepted private artifacts without modifying them; retain M6 outputs locally outside ordinary Git history.
- Add tests, sanitized evidence, documentation, commits, push the feature branch, and open one non-draft PR targeting `initial-idea`.

## Explicit exclusions

This authorization does not permit M5 retraining, Atari fine-tuning, changes to accepted M4/M5 weights or results, Stockfish inference/opponent/evaluation use, private artifact upload or redistribution, cloud resource allocation, exceeding the stated campaign envelope, PR merge, self-approval, release, G4 approval, or G4/M7 work. G4 remains a separate governance decision. Engineering completion and PR submission are not PM acceptance.

## Entry checks at authorization

- Remote `origin` is `https://github.com/dodaonam/atari-videochess-rl.git`; fetched `initial-idea` is the approved merge commit/tree above.
- G3 approval and M2–M5 acceptance are recorded in the canonical evidence; PR #13 is merged and its reviewed tree equals the integration tree.
- Baseline preflight passed, with only the expected external artifact manifest warning; the 253-record checkpoint-history archive verified.
- M1, M4, and M5 dependencies are complete, with no active blockers. Exact selected checkpoint bytes and schemas are verified separately in the entry verification record before gameplay.
- `O-02` and `O-05` remain open as external/assignment confirmations. This mission fixes the internal M6 scope and numeric runtime profile only; it does not claim instructor confirmation or human-readable difficulty semantics.

**Authorization status:** M6-001 is authorized and may be activated.
**Engineering status:** in progress; not completed or accepted.
**G4:** not approved.
