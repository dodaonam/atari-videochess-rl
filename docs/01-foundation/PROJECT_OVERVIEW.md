# Project Overview

**Audience:** Project owner, instructors/reviewers, and engineering agents.<br>
**Current disposition (2026-11-02): PROJECT CLOSED WITH DOCUMENTED LIMITATIONS.** M0–M7 engineering is complete and G0–G5 are approved within their recorded scopes. No new research or artifact release is authorized. See [final handover](../07-delivery/HANDOVER.md) and canonical state/backlog.

## Purpose

Build and study a chess-playing reinforcement-learning agent for ALE `VideoChess-v5`. Independently implemented Double DQN learning from simulator transitions is the central course deliverable. Expert-game data and optional Stockfish-supervised preparation are bounded support experiments; they must not displace implementation, evaluation, and explanation of RL. The roadmap's research direction and actual Atari evaluation remain preserved as separate evidence tracks.

## Research evidence tracks

1. **Supervised pretraining:** train from expert-derived labels. This alone is not RL.
2. **Simulator RL:** learn from chess-game rewards and transitions in a `python-chess` simulator. This is not evidence of Atari interaction.
3. **Atari evaluation/fine-tuning:** use real ALE observations, actions, and outcomes. A chess shadow board may track or validate, but may not replace the emulator state.

## Project boundaries

- The owner-selected project direction uses custom PyTorch Double DQN, excludes Stable-Baselines/Ray RLlib, and forbids Stockfish in inference. The 2026-10-27 owner decision closes O-01 for internal planning and execution; no instructor approval is claimed, and any actual explicit course prohibition must be followed.
- ALE board extraction and action wrapping remain the target path. External instructor-policy evidence has not been established in the repository; that residual uncertainty is informational for M4-001 and does not require repeated owner confirmation.
- A full-game Atari agent is the roadmap's technical target. The simulator fallback is a disclosed limitation, not an assumed waiver.
- Approximate 1500 Elo is aspirational, not guaranteed. Any Elo claim requires a defined calibrated opponent pool.

## Current status source

This overview does not own live phase or task status. Read `.agents/state/PROJECT_STATE.yaml` and `.agents/tasks/BACKLOG.yaml`. [`ADR-0001`](../02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md) is the sole canonical G/M crosswalk; `EXECUTION_PLAN.md` owns engineering order, dependencies, deliverables, and the fixed-file inventory.

## Implementation boundary

M4-001 is complete and merged by PR #8 at `c0a284304d602817922772d08f0ff7904af7ae20`; its acceptance and post-merge evidence remain in the linked reports. The model follows accepted ADR-0003, the exact local M3 release was reverified during M4, the PM-amended distinct-input sanity gate passed, and a validation-selected behavior-only checkpoint was frozen and evaluated without Stockfish. The original fixed 128-example gate failure remains historical evidence. M5 subsequently implemented and evaluated Double DQN in the M2 simulator and was integrated by PR #11; the independent PM approved G3 on 2026-10-30. M5 does not implement learned Atari inference and its simulator scores are not Atari performance. M6 subsequently integrated frozen policies with genuine ALE, and M7 completed the frozen Option B evaluation and delivery. G0–G5 are approved with documented limitations; see the final handover. The third-party package license is still unstated and bulk artifacts remain non-redistributable.
