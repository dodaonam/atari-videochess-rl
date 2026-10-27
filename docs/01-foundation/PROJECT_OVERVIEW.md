# Project Overview

**Audience:** Project owner, instructors/reviewers, and engineering agents.<br>
**Status:** Project overview; normative constraints remain in [`REQUIREMENTS.md`](REQUIREMENTS.md). M0–M3 are implemented and accepted on the integration branch. M3 artifacts are outside Git; the exact accepted local release was independently verified read-only during Pre-M4 and must be reverified before future use. Live status is owned by canonical state and backlog.

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

The integration branch contains the accepted M0–M3 work. The M4 feature branch implements the accepted ADR-0003 model, feature/data loader, trainer, inference adapter, checkpoint tools, CLI, and focused tests. Its M4 loader reverified and tensorized the exact local M3 release; all nine files remained unchanged. The fixed 128-example overfit gate then failed at 126/128 top-1. A read-only diagnosis proved two pairs of identical model inputs have conflicting played-move labels, so the required 127/128 cannot be reached under the current input contract. M4-01 source checks pass; M4-02 failed; full training, checkpoint acceptance, and M4-03/M4-04 evidence were not started. M4-001 is blocked by BLK-002 pending an explicit owner protocol decision. No Double DQN trainer or learned Atari inference path is implemented. G3 remains unapproved. The third-party package license is still unstated and bulk artifacts remain non-redistributable.
