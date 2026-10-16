# Project Overview

**Audience:** Project owner, instructors/reviewers, and engineering agents.<br>
**Status:** Project overview; normative constraints remain in [`REQUIREMENTS.md`](REQUIREMENTS.md). M0–M2 implementation is present on the integration branch. Live gate, task, and authorization status are owned by canonical state and backlog.

## Purpose

Build and study a chess-playing reinforcement-learning agent for ALE `VideoChess-v5`. The roadmap's research direction combines expert/Stockfish-supervised pretraining with separately measured RL and evaluation on actual Atari Video Chess.

## Research evidence tracks

1. **Supervised pretraining:** train from expert-derived labels. This alone is not RL.
2. **Simulator RL:** learn from chess-game rewards and transitions in a `python-chess` simulator. This is not evidence of Atari interaction.
3. **Atari evaluation/fine-tuning:** use real ALE observations, actions, and outcomes. A chess shadow board may track or validate, but may not replace the emulator state.

## Project boundaries

- The roadmap states that custom RL should use PyTorch, excludes Stable-Baselines/Ray RLlib, and forbids Stockfish from the inference path. Assignment-specific permissions still require confirmation in `REQUIREMENTS.md`.
- ALE board extraction and action wrapping are the target integration path, subject to runtime and assignment checks.
- A full-game Atari agent is the roadmap's technical target. The simulator fallback is a disclosed limitation, not an assumed waiver.
- Approximate 1500 Elo is aspirational, not guaranteed. Any Elo claim requires a defined calibrated opponent pool.

## Current status source

This overview does not own live phase or task status. Read `.agents/state/PROJECT_STATE.yaml` and `.agents/tasks/BACKLOG.yaml`. [`ADR-0001`](../02-management/decisions/ADR-0001-governance-crosswalk-and-file-priorities.md) is the sole canonical G/M crosswalk; `EXECUTION_PLAN.md` owns engineering order, dependencies, deliverables, and the fixed-file inventory.

## Implementation boundary

The integrated repository includes the technical bootstrap, verified ALE feasibility layer, and accepted python-chess simulator/baselines. Expert-data contracts are proposed in `docs/04-research/`; no production M3 dataset, supervised model, Double DQN trainer, or learned Atari inference path is implemented. The source, Stockfish, assignment, compute, evaluation, and M3 authorization questions remain in `REQUIREMENTS.md`.
