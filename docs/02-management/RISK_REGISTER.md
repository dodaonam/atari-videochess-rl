# Risk Register

**Canonical source for:** project risks and response plans. A risk is a possible failure, not evidence that it has occurred. Blockers are maintained separately in `.agents/state/BLOCKERS.md`; current progress is in `.agents/state/PROJECT_STATE.yaml`.

| ID | Risk | Initial severity | Status | Planned response / evidence needed |
|---|---|---:|---|---|
| RSK-001 | ALE board extraction or state synchronization is unreliable, especially while Atari is thinking. | High | Open; untested | M1: compare RGB/RAM and shadow-board transitions, detect desync, stop/recover rather than continue on unverified state. |
| RSK-002 | Atari Video Chess and `python-chess` differ in rules, turn behavior, or terminal conditions. | High | Open; untested | M1/M2: test special moves and endings; document supported behavior and any mismatch. |
| RSK-003 | Stockfish evaluations have a different perspective/scale/meaning from Double DQN Q-values. | High | Open; design concern | M3–M5: record perspective and target transform, unit-test signs/scales, verify reward alignment before TD updates. |
| RSK-004 | Sparse terminal rewards or unstable updates cause RL to regress the pretraining baseline. | High | Open; not measured | Keep pretraining and RL checkpoints; compare under the same benchmark; report regressions honestly. |
| RSK-005 | Colab free GPU availability or session duration is insufficient for planned workloads. | Medium | Open; not checked | M0: inspect current quota/runtime capability; checkpoint/resume and persistent artifacts; no paid compute without authorization. |
| RSK-006 | Dataset licensing, source-game overlap, or candidate-level splits cause invalid use or leakage. | High | Open; no dataset selected | Confirm sources/licenses before ingestion; split by source game/position group and retain provenance. |
| RSK-007 | Simulator skill does not transfer to actual Atari play. | High | Open; not measured | Keep simulator and Atari results distinct; require M1 before substantial learning and closed-loop M6 evaluation. |
| RSK-008 | Source-described ALE defaults, RAM addressing, mode mapping, or ROM availability differ from the installed version. | Medium | Open; not checked | Verify against the installed release and primary sources in M0/M1; record exact versions/settings. |

Do not mark a risk resolved based only on a proposed mitigation. Link verified findings, test evidence, or an ADR when the underlying uncertainty is actually resolved.
