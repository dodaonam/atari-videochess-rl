"""Fail-closed adapter from verified M1 RGB state to existing frozen policies."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import random
import time
from typing import Any, Sequence

import chess
import numpy as np

from videochess_rl.baselines import RandomLegalAgent, SimpleHeuristicAgent
from videochess_rl.episode import AtariDecisionContext, DecisionResult
from videochess_rl.model.checkpoint import load_checkpoint, verify_artifact_manifest
from videochess_rl.model.features import replay_observation_history
from videochess_rl.model.inference import BehaviorPolicy
from videochess_rl.rl.checkpoint import load_evaluation_snapshot
from videochess_rl.rl.evaluate import QPolicy
from videochess_rl.simulator import Observation
from videochess_rl.vision import BoardEvidenceSet, BoardWindow, VideoChessVision


M5_ROOT_MANIFEST_SHA256 = "a201a254671ad59ae1fecb402abf994d5bf523097f1c3010b5c7fa237ae6dd4c"
M5_WARM_CHECKPOINT_SHA256 = "0b2405017a8e1d539851f0cd278883d3fd23936fb5c2f7962c813590a6fd1767"
M5_WARM_SIDECAR_SHA256 = "80d8689e4b349576c5708bb4dce3451e5a8c64d81470cd6f4273a4746844b682"
M5_SCRATCH_CHECKPOINT_SHA256 = "3749b0c0b6ae44d3ad5d6bf0863b60937a59fbe881e0bdf4932bdce6033ca400"
M5_SCRATCH_SIDECAR_SHA256 = "1c15e5bc4ba2437df113671dc316accbdfe6d8b59069ed29ed187daebf4fff1e"
M4_ROOT_MANIFEST_SHA256 = "f00fde1c59325105e0ffd45bb45eb269dfa303416010c9a0b6c6be47bd9a9921"
M4_CHECKPOINT_SHA256 = "724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4"
M4_SIDECAR_SHA256 = "cc0af4694e45fc23acb740c652dd9a62e1bcaf7851815d179693d09539f0f606"


class PolicyInputError(ValueError):
    """A stale or inconsistent ALE-derived state must not reach inference."""


@dataclass(frozen=True, slots=True)
class PolicyIdentity:
    policy_id: str
    policy_type: str
    checkpoint_sha256: str | None = None
    sidecar_sha256: str | None = None
    artifact_manifest_sha256: str | None = None
    arm: str | None = None
    training_seed: int | None = None
    snapshot_stage: str | None = None
    valid_decisions: int | None = None
    artifact_path: str | None = None


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_manifest_file(root: str | Path, manifest_name: str, expected_sha256: str) -> Path:
    directory = Path(root).expanduser()
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"private artifact root is missing or unsafe: {directory}")
    path = directory / manifest_name
    if path.is_symlink() or not path.is_file() or sha256_file(path) != expected_sha256:
        raise ValueError(f"private artifact manifest identity mismatch: {path}")
    return path


def verify_selected_m5_root(root: str | Path) -> dict[str, Any]:
    """Verify the full M5 inventory once before loading any roster policy."""
    manifest_path = verify_manifest_file(root, "artifact-manifest.json", M5_ROOT_MANIFEST_SHA256)
    from scripts.m5_artifact_manifests import verify_manifest

    return verify_manifest(manifest_path.parent, manifest_path)


def load_m5_policy(
    checkpoint_path: str | Path,
    *,
    policy_id: str,
    arm: str,
    training_seed: int,
    expected_checkpoint_sha256: str,
    expected_sidecar_sha256: str,
    root_manifest_sha256: str = M5_ROOT_MANIFEST_SHA256,
    artifact_root: str | Path,
) -> tuple[QPolicy, PolicyIdentity]:
    root = Path(artifact_root).expanduser()
    if sha256_file(root / "artifact-manifest.json") != root_manifest_sha256:
        raise ValueError("M5 root artifact manifest changed after roster freeze")
    checkpoint = Path(checkpoint_path).expanduser()
    sidecar = checkpoint.with_suffix(checkpoint.suffix + ".manifest.json")
    if checkpoint.is_symlink() or sidecar.is_symlink() or not checkpoint.is_file() or not sidecar.is_file():
        raise ValueError("M5 frozen snapshot or sidecar is missing/unsafe")
    checkpoint_sha = sha256_file(checkpoint)
    sidecar_sha = sha256_file(sidecar)
    if checkpoint_sha != expected_checkpoint_sha256 or sidecar_sha != expected_sidecar_sha256:
        raise ValueError("M5 frozen snapshot or sidecar SHA-256 differs from the predeclared roster")
    model, metadata = load_evaluation_snapshot(checkpoint, device="cpu")
    expected = {
        "schema": "videochess-ddqn-evaluation-snapshot/2.0",
        "arm": arm,
        "training_seed": training_seed,
        "stage": "post_rl",
        "valid_decisions": 50_000,
        "resumable": False,
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise ValueError(f"M5 snapshot metadata mismatch for {key}")
    policy = QPolicy(model, policy_id=policy_id, checkpoint_sha256=checkpoint_sha)
    identity = PolicyIdentity(
        policy_id=policy_id,
        policy_type="frozen_m5_double_dqn_q_policy",
        checkpoint_sha256=checkpoint_sha,
        sidecar_sha256=sidecar_sha,
        artifact_manifest_sha256=root_manifest_sha256,
        arm=arm,
        training_seed=training_seed,
        snapshot_stage="post_rl",
        valid_decisions=50_000,
        artifact_path=checkpoint.as_posix(),
    )
    return policy, identity


def load_m4_policy(
    artifact_root: str | Path,
    *,
    policy_id: str = "m4-behavior-only-seed-20261024",
    expected_root_manifest_sha256: str = M4_ROOT_MANIFEST_SHA256,
    expected_checkpoint_sha256: str = M4_CHECKPOINT_SHA256,
    expected_sidecar_sha256: str = M4_SIDECAR_SHA256,
) -> tuple[BehaviorPolicy, PolicyIdentity]:
    root = Path(artifact_root).expanduser()
    manifest = verify_artifact_manifest(root)
    manifest_path = root / "artifact_manifest.json"
    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != expected_root_manifest_sha256:
        raise ValueError("M4 root artifact manifest differs from the accepted roster")
    checkpoint = root / "pretrained-behavior-only.pt"
    sidecar = checkpoint.with_suffix(checkpoint.suffix + ".manifest.json")
    if sha256_file(checkpoint) != expected_checkpoint_sha256 or sha256_file(sidecar) != expected_sidecar_sha256:
        raise ValueError("M4 frozen checkpoint or sidecar differs from the accepted roster")
    model, bundle = load_checkpoint(checkpoint, device="cpu")
    metadata = bundle["metadata"]
    if metadata.get("checkpoint_role") != "pretrained_behavior_only":
        raise ValueError("M4 checkpoint is not the accepted behavior-only policy")
    policy = BehaviorPolicy(model, checkpoint_sha256=expected_checkpoint_sha256)
    identity = PolicyIdentity(
        policy_id=policy_id,
        policy_type="frozen_m4_supervised_behavior_policy",
        checkpoint_sha256=expected_checkpoint_sha256,
        sidecar_sha256=expected_sidecar_sha256,
        artifact_manifest_sha256=manifest_sha,
        training_seed=20261024,
        snapshot_stage="validation_best_behavior_only",
        artifact_path=checkpoint.as_posix(),
    )
    return policy, identity


def load_baseline(policy_id: str) -> tuple[Any, PolicyIdentity]:
    if policy_id == "simple-material-heuristic":
        return SimpleHeuristicAgent(), PolicyIdentity(policy_id, "simple_heuristic")
    if policy_id == "random-legal":
        return RandomLegalAgent(), PolicyIdentity(policy_id, "random_legal")
    raise ValueError(f"unknown M6 policy ID: {policy_id}")


def validate_decision_context(context: AtariDecisionContext, *, agent_color: chess.Color = chess.WHITE) -> tuple[chess.Board, Observation]:
    if not isinstance(context, AtariDecisionContext):
        raise PolicyInputError("policy input is not a verified Atari decision context")
    if isinstance(context.frame_number, bool) or not isinstance(context.frame_number, int) or context.frame_number < 0:
        raise PolicyInputError("ALE frame identity is missing or invalid")
    frame = context.rgb_frame
    if not isinstance(frame, np.ndarray) or frame.shape != (210, 160, 3) or frame.dtype != np.uint8:
        raise PolicyInputError("policy RGB frame must be uint8 with shape (210,160,3)")
    rgb_sha = hashlib.sha256(frame.tobytes()).hexdigest()
    if rgb_sha != context.rgb_sha256:
        raise PolicyInputError("policy RGB frame hash differs from its observation identity")
    vision_observation = VideoChessVision().observe(frame)
    if vision_observation != context.rgb_observation:
        raise PolicyInputError("RGB observation does not match the supplied vision evidence")

    history = context.history_uci
    if not isinstance(history, tuple) or any(not isinstance(move, str) for move in history):
        raise PolicyInputError("complete ordered UCI history is required")
    if not history and not context.standard_reset_verified:
        raise PolicyInputError("empty history is valid only after RGB confirms the standard reset board")
    try:
        board = replay_observation_history(history)
    except (TypeError, ValueError) as exc:
        raise PolicyInputError(f"verified UCI history is malformed or illegal: {exc}") from exc
    supplied_board = context.board
    if not isinstance(supplied_board, chess.Board) or supplied_board.chess960 or not supplied_board.is_valid():
        raise PolicyInputError("shadow board is invalid or uses an unsupported chess variant")
    if board.fen(en_passant="fen") != context.fen or supplied_board.fen(en_passant="fen") != context.fen:
        raise PolicyInputError("FEN/history/shadow mismatch")
    if tuple(move.uci() for move in supplied_board.move_stack) != history:
        raise PolicyInputError("shadow move stack differs from the complete verified history")
    if board.turn != context.side_to_move or supplied_board.turn != context.side_to_move:
        raise PolicyInputError("side-to-move mismatch")
    if context.side_to_move != agent_color:
        raise PolicyInputError("policy was invoked outside the authorized agent color's turn")
    if board.outcome(claim_draw=False) is not None:
        raise PolicyInputError("terminal chess state has no policy action")

    legal = tuple(sorted(move.uci() for move in board.legal_moves))
    if not legal or len(set(legal)) != len(legal):
        raise PolicyInputError("reconstructed legal candidate set is empty or duplicated")
    if not isinstance(context.legal_moves_uci, tuple) or tuple(sorted(context.legal_moves_uci)) != context.legal_moves_uci:
        raise PolicyInputError("legal UCI candidates must be a sorted tuple")
    if len(set(context.legal_moves_uci)) != len(context.legal_moves_uci):
        raise PolicyInputError("legal UCI candidates contain duplicates")
    for uci in context.legal_moves_uci:
        if not isinstance(uci, str):
            raise PolicyInputError("legal action identity must be a UCI string")
        try:
            parsed = chess.Move.from_uci(uci)
        except ValueError as exc:
            raise PolicyInputError(f"malformed legal candidate UCI: {uci!r}") from exc
        if parsed.uci() != uci:
            raise PolicyInputError(f"noncanonical UCI candidate: {uci!r}")
    if legal != context.legal_moves_uci:
        raise PolicyInputError("legal candidate set differs from the complete verified history")

    evidence = context.rgb_evidence
    if isinstance(evidence, BoardEvidenceSet):
        if not evidence.matches_board(board):
            raise PolicyInputError("stable RGB evidence disagrees with the reconstructed board")
    elif isinstance(evidence, BoardWindow):
        if not evidence.is_stable or not evidence.matches_board_except_cursor(board):
            raise PolicyInputError("RGB window is ambiguous or disagrees with the shadow board")
        if history:
            raise PolicyInputError("noninitial policy input requires complete multi-window RGB coverage")
    else:
        raise PolicyInputError("policy input lacks a supported stable RGB evidence object")
    if not history and not vision_observation.matches_start_position():
        raise PolicyInputError("empty history is not backed by a true RGB-confirmed standard start")
    if history and not vision_observation.matches_board(board):
        # A cursor can mask one square in the last frame, but the supplied
        # stable evidence set must independently cover the full position.
        if not isinstance(evidence, BoardEvidenceSet) or not evidence.matches_board(board):
            raise PolicyInputError("last RGB observation is stale or does not match the current board")

    observation = Observation(
        fen=board.fen(en_passant="fen"),
        board_fen=board.board_fen(),
        turn=board.turn,
        agent_color=agent_color,
        castling_rights=board.castling_xfen(),
        ep_square=chess.square_name(board.ep_square) if board.ep_square is not None else None,
        halfmove_clock=board.halfmove_clock,
        fullmove_number=board.fullmove_number,
        legal_moves_uci=legal,
        history_uci=history,
        opponent_id="ALE/VideoChess-v5",
        opponent_config_json=json.dumps({"agent_color": "white", "observation": "RGB"}, sort_keys=True),
        episode_decisions=(len(history) + 1) // 2,
    )
    return board, observation


class M6PolicyAdapter:
    """Validate one verified Atari context, then call an existing policy once."""

    def __init__(
        self,
        policy: Any,
        identity: PolicyIdentity,
        *,
        rng_seed: int,
        agent_color: chess.Color = chess.WHITE,
    ) -> None:
        self.policy = policy
        self.identity = identity
        self.rng_seed = int(rng_seed)
        self.agent_color = agent_color
        self._last_frame_number = -1
        self._frame_hashes: dict[int, str] = {}
        self._decision_count = 0
        self.model = getattr(policy, "model", None)
        if self.model is not None:
            self.model.eval()

    @property
    def policy_id(self) -> str:
        return self.identity.policy_id

    def __call__(self, context: AtariDecisionContext) -> DecisionResult:
        adapter_started = time.perf_counter()
        validation_started = adapter_started
        board, observation = validate_decision_context(context, agent_color=self.agent_color)
        input_validation_latency = time.perf_counter() - validation_started
        if context.frame_number < self._last_frame_number:
            raise PolicyInputError("stale ALE observation frame")
        prior_hash = self._frame_hashes.get(context.frame_number)
        if prior_hash is not None and prior_hash != context.rgb_sha256:
            raise PolicyInputError("same ALE frame identity was reused with different RGB bytes")
        self._last_frame_number = max(self._last_frame_number, context.frame_number)
        self._frame_hashes[context.frame_number] = context.rgb_sha256
        if len(self._frame_hashes) > 16:
            for frame_number in sorted(self._frame_hashes)[:-16]:
                self._frame_hashes.pop(frame_number, None)

        model_versions: dict[str, int] = {}
        if self.model is not None:
            if self.model.training:
                raise PolicyInputError("frozen inference model is unexpectedly in training mode")
            model_versions = {name: parameter._version for name, parameter in self.model.named_parameters()}
            if any(parameter.grad is not None for parameter in self.model.parameters()):
                raise PolicyInputError("frozen inference model already contains gradients")
        if any(getattr(self.policy, name, None) is not None for name in ("optimizer", "replay", "replay_buffer")):
            raise PolicyInputError("training optimizer/replay state is present in the inference policy")

        digest = hashlib.sha256(
            f"{self.rng_seed}\0{self.identity.policy_id}\0{context.frame_number}\0{context.fen}".encode("utf-8")
        ).digest()
        rng = random.Random(int.from_bytes(digest[:8], "big"))
        legal_moves = tuple(chess.Move.from_uci(uci) for uci in observation.legal_moves_uci)
        choose_started = time.perf_counter()
        selected = self.policy.choose_move(observation, legal_moves, rng)
        choose_move_latency = time.perf_counter() - choose_started
        if isinstance(selected, chess.Move):
            uci = selected.uci()
        elif isinstance(selected, str):
            uci = selected
        else:
            raise PolicyInputError("policy returned an unsupported action type")
        try:
            move = chess.Move.from_uci(uci)
        except (ValueError, TypeError) as exc:
            raise PolicyInputError(f"policy output is malformed UCI: {uci!r}") from exc
        if move.uci() != uci or uci not in observation.legal_moves_uci or move not in board.legal_moves:
            raise PolicyInputError("policy output is illegal or outside the exact verified candidate set")
        if self.model is not None:
            if self.model.training or any(parameter.grad is not None for parameter in self.model.parameters()):
                raise PolicyInputError("frozen model mode or gradient state changed during inference")
            if any(parameter._version != model_versions[name] for name, parameter in self.model.named_parameters()):
                raise PolicyInputError("frozen model weights changed during inference")

        self._decision_count += 1
        metadata: dict[str, object] = {
            "policy_id": self.identity.policy_id,
            "policy_type": self.identity.policy_type,
            "checkpoint_sha256": self.identity.checkpoint_sha256,
            "sidecar_sha256": self.identity.sidecar_sha256,
            "artifact_manifest_sha256": self.identity.artifact_manifest_sha256,
            "frame_number": context.frame_number,
            "rgb_sha256": context.rgb_sha256,
            "fen": observation.fen,
            "side_to_move": observation.side_to_move,
            "history_uci": list(observation.history_uci),
            "legal_candidates_uci": list(observation.legal_moves_uci),
            "selected_uci": uci,
            "input_validation_latency_seconds": input_validation_latency,
            "policy_choose_move_latency_seconds": choose_move_latency,
            "adapter_total_latency_seconds": time.perf_counter() - adapter_started,
            "decision_index": self._decision_count,
            "training": False,
            "optimizer": False,
            "replay_insertion": False,
            "stockfish": False,
        }
        return DecisionResult(uci=uci, metadata=metadata)
