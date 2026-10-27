"""Read-only replay, feature cache, and variable-length batching for M4."""

from __future__ import annotations

import hashlib
import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import chess
import numpy as np
import torch

from videochess_rl.action_contract import canonical_model_fen, legal_action_candidates
from videochess_rl.data.contracts import (
    board_position_signature,
    candidate_identity,
    digest,
    replay_history_identity,
    sample_identity,
)
from videochess_rl.data.export import verify_release

from .features import INPUT_SCHEMA, PositionFeatures, encode_board

EXPECTED_RELEASE_ID = "f10a679deddf06f3e1e3c39cf58db4e21176629c26c09034a271bf278189e890"
EXPECTED_MANIFEST_SHA256 = "be1e1f9316fac01be893774cfe09a313de193fbd1a12ab2d219ff5c041104a12"
EXPECTED_SPLIT_SHA256 = "84efed824e57de45c0058b73818bb7a9d740201ead38e9171308cee43bc0934e"
EXPECTED_COUNTS = {"train": 15_196, "validation": 2_015, "test": 2_057}
EXPECTED_GAME_COUNTS = {"train": 795, "validation": 102, "test": 103}
MAX_PHYSICAL_BATCH_POSITIONS = 64
MAX_PADDED_HISTORY_TOKENS = 32_768
MAX_PADDED_CANDIDATE_SLOTS = 8_192
RELEASE_FILES = (
    "config.json",
    "games.jsonl",
    "manifest.json",
    "manifest.sha256",
    "positions.jsonl",
    "rejections.jsonl",
    "source_manifest.json",
    "split.json",
    "stats.json",
)


@dataclass(frozen=True, slots=True)
class M4Dataset:
    train: tuple[PositionFeatures, ...]
    validation: tuple[PositionFeatures, ...]
    test: tuple[PositionFeatures, ...]
    release_id: str
    manifest_sha256: str
    split_assignment_sha256: str
    counts: dict[str, int]
    game_counts: dict[str, int]
    file_inventory: dict[str, dict[str, int | str]]
    feature_payload_bytes: int
    candidate_counts: dict[str, int]
    max_history_length: int
    max_candidate_count: int
    verification_seconds: float
    replay_seconds: float
    total_load_seconds: float


@dataclass(frozen=True, slots=True)
class DistinctInputSelection:
    """A reproducible, label-independent M4-02 sample selection."""

    examples: tuple[PositionFeatures, ...]
    input_sha256: tuple[str, ...]
    rule: str = "m4-02-distinct-effective-input-ascending-sample-id/1.0"
    identity_schema: str = "videochess-effective-model-input/1.0"

    @property
    def sample_ids(self) -> tuple[str, ...]:
        return tuple(row.sample_id for row in self.examples)

    @property
    def sample_ids_sha256(self) -> str:
        return hashlib.sha256("\n".join(self.sample_ids).encode("utf-8")).hexdigest()

    @property
    def input_identities_sha256(self) -> str:
        return hashlib.sha256("\n".join(self.input_sha256).encode("ascii")).hexdigest()


def _sha256_file(path: Path) -> tuple[str, int]:
    digestor = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digestor.update(chunk)
            size += len(chunk)
    return digestor.hexdigest(), size


def _inventory(release_dir: Path) -> dict[str, dict[str, int | str]]:
    result: dict[str, dict[str, int | str]] = {}
    for name in RELEASE_FILES:
        digest_value, size = _sha256_file(release_dir / name)
        result[name] = {"sha256": digest_value, "size_bytes": size}
    return result


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                raise ValueError(f"blank JSONL row in {path.name} at line {line_number}")
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"JSONL row in {path.name} at line {line_number} is not an object")
            rows.append(row)
    return rows


def _validate_position_against_board(
    row: dict[str, Any], game: dict[str, Any], board: chess.Board, assigned_split: str,
) -> tuple[str, ...]:
    ply = row.get("ply_index")
    if isinstance(ply, bool) or not isinstance(ply, int) or not 0 <= ply < len(game["moves_uci"]):
        raise ValueError("position ply_index does not identify a move in its parent game")
    if board.outcome(claim_draw=False) is not None:
        raise ValueError("released behavior position is terminal before its played move")
    if row.get("schema") != "videochess-position/1.0" or row.get("schema_version") != "videochess-position/1.0":
        raise ValueError("unsupported M4 position row schema")
    if row.get("record_id") != row.get("sample_id"):
        raise ValueError("position record identity differs from sample_id")
    if row.get("game_id") != game.get("game_id"):
        raise ValueError("position row references another game")
    if row.get("normalized_game_sha256") != game.get("normalized_game_sha256"):
        raise ValueError("position normalized-game identity differs from its parent")
    if row.get("source_id") != game.get("source_id"):
        raise ValueError("position source identity differs from its parent")
    if row.get("reconstruction_path") != {"game_id": game["game_id"], "ply_index": ply}:
        raise ValueError("position reconstruction path differs from its parent game/ply")
    if row.get("fen") != canonical_model_fen(board):
        raise ValueError("position legal-en-passant FEN does not match replayed history")
    if row.get("side_to_move") != ("white" if board.turn == chess.WHITE else "black"):
        raise ValueError("position side-to-move metadata does not match replay")
    if row.get("split") != assigned_split or row.get("split_id") != assigned_split:
        raise ValueError("position split differs from immutable game-group assignment")

    sample_id = sample_identity(
        game["source_id"], game["game_id"], game["normalized_game_sha256"], ply
    )
    if row.get("sample_id") != sample_id:
        raise ValueError("position sample_id does not recompute from its game and ply")
    if row.get("board_position_signature") != board_position_signature(board):
        raise ValueError("board-position signature does not match replay")
    if row.get("history_state_id") != replay_history_identity(
        game["initial_fen"], game["moves_uci"][:ply]
    ):
        raise ValueError("history-state identity does not match complete prior move history")

    candidates = legal_action_candidates(board)
    candidate_uci = tuple(candidate.uci for candidate in candidates)
    if not candidate_uci or len(candidate_uci) != len(set(candidate_uci)):
        raise ValueError("a played behavior row must have a nonempty, unique legal candidate set")
    if row.get("legal_moves_uci") != list(candidate_uci):
        raise ValueError("released legal UCI candidate set differs from replay")
    target = row.get("played_move_uci")
    if target != game["moves_uci"][ply] or candidate_uci.count(target) != 1:
        raise ValueError("played_move_uci is not the unique historical move in legal candidates")
    if row.get("candidate_count") != len(candidate_uci):
        raise ValueError("released candidate count differs from legal candidate set")
    expected_set_hash = digest({
        "domain": "videochess-candidate-set/v1",
        "sample_id": sample_id,
        "legal_moves_uci": list(candidate_uci),
    })
    if row.get("candidate_set_sha256") != expected_set_hash:
        raise ValueError("candidate set identity does not recompute")
    if row.get("played_candidate_id") != candidate_identity(sample_id, target):
        raise ValueError("played candidate identity does not recompute")
    return candidate_uci


def _features_from_verified_records(
    games: list[dict[str, Any]],
    positions: list[dict[str, Any]],
    split_doc: dict[str, Any],
) -> tuple[dict[str, list[PositionFeatures]], dict[str, int]]:
    assignment_rows = split_doc.get("game_group_assignments")
    if not isinstance(assignment_rows, list):
        raise ValueError("split manifest has no game-group assignments")
    group_splits: dict[str, str] = {}
    for item in assignment_rows:
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError("malformed game-group split assignment")
        group, split = item
        if group in group_splits:
            raise ValueError("duplicate normalized game-group split assignment")
        if split not in EXPECTED_COUNTS:
            raise ValueError("unsupported split name")
        group_splits[group] = split

    games_by_id: dict[str, dict[str, Any]] = {}
    game_counts: Counter[str] = Counter()
    rows_by_game: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for game in games:
        game_id = game.get("game_id")
        if not isinstance(game_id, str) or game_id in games_by_id:
            raise ValueError("duplicate or malformed game_id in verified release")
        # verify_release() has just performed the independent full M3 record
        # validation. Revalidate the state needed by the model boundary here,
        # then replay this game exactly once below while constructing rows.
        assigned = group_splits.get(game.get("normalized_game_sha256"))
        if assigned is None or game.get("split") != assigned or game.get("split_id") != assigned:
            raise ValueError("game split differs from immutable normalized-game assignment")
        if game.get("initial_fen") != chess.STARTING_FEN:
            raise ValueError("model input v1 rejects nonstandard game roots")
        games_by_id[game_id] = game
        game_counts[assigned] += 1
    for row in positions:
        game_id = row.get("game_id")
        if game_id not in games_by_id:
            raise ValueError("position row has no parent game")
        rows_by_game[game_id].append(row)

    result: dict[str, list[PositionFeatures]] = {name: [] for name in EXPECTED_COUNTS}
    seen_sample_ids: set[str] = set()
    for game_id in sorted(games_by_id):
        game = games_by_id[game_id]
        split = group_splits[game["normalized_game_sha256"]]
        rows = sorted(rows_by_game.get(game_id, []), key=lambda row: row.get("ply_index", -1))
        by_ply: dict[int, dict[str, Any]] = {}
        for row in rows:
            ply = row.get("ply_index")
            if isinstance(ply, bool) or not isinstance(ply, int) or ply in by_ply:
                raise ValueError("duplicate or malformed position ply for one game")
            by_ply[ply] = row

        board = chess.Board(game["initial_fen"])
        for ply, uci in enumerate(game["moves_uci"]):
            row = by_ply.get(ply)
            if row is not None:
                _validate_position_against_board(row, game, board, split)
                sample_id = row["sample_id"]
                if sample_id in seen_sample_ids:
                    raise ValueError("duplicate sample_id in M4 feature stream")
                seen_sample_ids.add(sample_id)
                features = encode_board(
                    board,
                    sample_id=sample_id,
                    split=split,
                    target_uci=row["played_move_uci"],
                    ply_index=ply,
                )
                if features.candidate_uci != tuple(row["legal_moves_uci"]):
                    raise ValueError("feature encoder candidate order differs from M3 release")
                result[split].append(features)
            if board.outcome(claim_draw=False) is not None:
                raise ValueError("game history continues after automatic chess termination")
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                raise ValueError(f"illegal UCI encountered during M4 replay at ply {ply}")
            board.push(move)

        if set(by_ply) - set(range(len(game["moves_uci"]))):
            raise ValueError("position row ply exceeds its parent game's move sequence")

    for split in result:
        result[split].sort(key=lambda example: example.sample_id)
    return result, dict(game_counts)


def load_m3_release(release_dir: str | Path) -> M4Dataset:
    """Verify the exact accepted release, replay it once, and cache safe features.

    This calls the project's complete M3 verifier immediately before reading
    any examples. A final nine-file hash pass protects the returned feature set
    against source mutation during parsing/tensorization.
    """
    total_start = time.perf_counter()
    root = Path(release_dir).expanduser().resolve(strict=True)
    verification_start = time.perf_counter()
    verification = verify_release(root)
    verification_seconds = time.perf_counter() - verification_start
    manifest_bytes = (root / "manifest.json").read_bytes()
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    manifest = json.loads(manifest_bytes)
    if verification.get("release_id") != EXPECTED_RELEASE_ID or manifest.get("release_id") != EXPECTED_RELEASE_ID:
        raise ValueError("local M3 release ID differs from the accepted release")
    if manifest_sha != EXPECTED_MANIFEST_SHA256 or verification.get("manifest_sha256") != EXPECTED_MANIFEST_SHA256:
        raise ValueError("local M3 release manifest checksum differs from the accepted manifest")
    split_doc = json.loads((root / "split.json").read_text(encoding="utf-8"))
    split_hash = split_doc.get("split_assignment_sha256")
    if split_hash != EXPECTED_SPLIT_SHA256 or manifest.get("split_assignment_sha256") != EXPECTED_SPLIT_SHA256:
        raise ValueError("local M3 split assignment identity differs from the accepted release")
    before = _inventory(root)

    replay_start = time.perf_counter()
    games = _read_jsonl(root / "games.jsonl")
    positions = _read_jsonl(root / "positions.jsonl")
    feature_splits, game_counts = _features_from_verified_records(games, positions, split_doc)
    replay_seconds = time.perf_counter() - replay_start
    counts = {name: len(feature_splits[name]) for name in EXPECTED_COUNTS}
    if counts != EXPECTED_COUNTS or game_counts != EXPECTED_GAME_COUNTS:
        raise ValueError(f"accepted M3 split counts differ: positions={counts}, games={game_counts}")
    if split_doc.get("board_signatures_cross_split_after") != 0:
        raise ValueError("accepted M3 split manifest does not assert zero post-purge board overlap")
    after = _inventory(root)
    if before != after:
        raise ValueError("accepted M3 release files changed while M4 examples were loaded")
    payload_bytes = sum(
        example.board_planes.nbytes
        + example.state_scalars.nbytes
        + example.history_moves.nbytes
        + example.candidate_squares.nbytes
        + example.candidate_promotion.nbytes
        + example.candidate_flags.nbytes
        + sum(len(action.encode("ascii")) for action in example.candidate_uci)
        for examples in feature_splits.values()
        for example in examples
    )
    candidate_counts = {
        name: sum(example.candidate_count for example in feature_splits[name])
        for name in EXPECTED_COUNTS
    }
    all_features = [example for examples in feature_splits.values() for example in examples]
    return M4Dataset(
        train=tuple(feature_splits["train"]),
        validation=tuple(feature_splits["validation"]),
        test=tuple(feature_splits["test"]),
        release_id=EXPECTED_RELEASE_ID,
        manifest_sha256=EXPECTED_MANIFEST_SHA256,
        split_assignment_sha256=EXPECTED_SPLIT_SHA256,
        counts=counts,
        game_counts=game_counts,
        file_inventory=after,
        feature_payload_bytes=payload_bytes,
        candidate_counts=candidate_counts,
        max_history_length=max(example.history_length for example in all_features),
        max_candidate_count=max(example.candidate_count for example in all_features),
        verification_seconds=verification_seconds,
        replay_seconds=replay_seconds,
        total_load_seconds=time.perf_counter() - total_start,
    )


def smallest_training_sample_ids(
    examples: Iterable[PositionFeatures], count: int = 128,
) -> tuple[str, ...]:
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError("count must be a positive integer")
    train = [example for example in examples if example.split == "train"]
    if len(train) < count:
        raise ValueError(f"need {count} training examples, found {len(train)}")
    return tuple(sorted(example.sample_id for example in train)[:count])


_EFFECTIVE_INPUT_FIELDS = (
    "board_planes",
    "state_scalars",
    "history_moves",
    "history_mask",
    "candidate_squares",
    "candidate_promotion",
    "candidate_flags",
    "candidate_mask",
    "candidate_uci",
)


def _array_identity(value: np.ndarray, *, dtype: str) -> dict[str, Any]:
    array = np.ascontiguousarray(np.asarray(value, dtype=np.dtype(dtype)))
    return {
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "bytes_hex": array.tobytes(order="C").hex(),
    }


def _effective_input_document(
    *,
    board_planes: np.ndarray,
    state_scalars: np.ndarray,
    history_moves: np.ndarray,
    history_mask: np.ndarray,
    candidate_squares: np.ndarray,
    candidate_promotion: np.ndarray,
    candidate_flags: np.ndarray,
    candidate_mask: np.ndarray,
    candidate_uci: Iterable[str],
) -> dict[str, Any]:
    """Canonicalize exactly the unpadded fields consumed by BehaviorScorer."""
    history_moves = np.asarray(history_moves)
    history_mask = np.asarray(history_mask, dtype=np.bool_)
    candidate_squares = np.asarray(candidate_squares)
    candidate_promotion = np.asarray(candidate_promotion)
    candidate_flags = np.asarray(candidate_flags)
    candidate_mask = np.asarray(candidate_mask, dtype=np.bool_)
    uci = tuple(candidate_uci)
    history_length = int(history_mask.sum())
    candidate_count = int(candidate_mask.sum())
    if history_mask.shape != (history_length,) or not np.array_equal(
        history_mask, np.ones(history_length, dtype=np.bool_)
    ):
        raise ValueError("effective history mask must be an unpadded all-valid prefix")
    if candidate_mask.shape != (candidate_count,) or not np.array_equal(
        candidate_mask, np.ones(candidate_count, dtype=np.bool_)
    ):
        raise ValueError("effective candidate mask must be an unpadded all-valid prefix")
    if history_moves.shape != (history_length, 4):
        raise ValueError("history length/mask does not match effective history tokens")
    if candidate_squares.shape != (candidate_count, 2):
        raise ValueError("candidate count/mask does not match candidate square coordinates")
    if candidate_promotion.shape != (candidate_count,):
        raise ValueError("candidate count/mask does not match candidate promotions")
    if candidate_flags.shape != (candidate_count, 4):
        raise ValueError("candidate count/mask does not match candidate flags")
    if len(uci) != candidate_count or any(not isinstance(move, str) for move in uci):
        raise ValueError("candidate UCI identity count does not match candidate mask")
    if len(uci) != len(set(uci)) or tuple(sorted(uci)) != uci:
        raise ValueError("candidate UCI identities must be unique and lexically ordered")

    return {
        "schema": "videochess-effective-model-input/1.0",
        "model_input_schema": INPUT_SCHEMA,
        "history_length": history_length,
        "history_mask_semantics": "valid_prefix_exactly_equal_to_history_length",
        "candidate_count": candidate_count,
        "candidate_mask_semantics": "valid_prefix_exactly_equal_to_candidate_count",
        "fields": {
            "board_planes": _array_identity(board_planes, dtype="<f4"),
            "state_scalars": _array_identity(state_scalars, dtype="<f4"),
            "history_moves": _array_identity(history_moves, dtype="<i8"),
            "history_mask": _array_identity(history_mask, dtype="|b1"),
            "candidate_squares": _array_identity(candidate_squares, dtype="<i8"),
            "candidate_promotion": _array_identity(candidate_promotion, dtype="<i8"),
            "candidate_flags": _array_identity(candidate_flags, dtype="<f4"),
            "candidate_mask": _array_identity(candidate_mask, dtype="|b1"),
            "candidate_uci": list(uci),
        },
    }


def effective_model_input_document(example: PositionFeatures) -> dict[str, Any]:
    """Return label/provenance-free identity of one model input example."""
    return _effective_input_document(
        board_planes=example.board_planes,
        state_scalars=example.state_scalars,
        history_moves=example.history_moves,
        history_mask=np.ones(example.history_length, dtype=np.bool_),
        candidate_squares=example.candidate_squares,
        candidate_promotion=example.candidate_promotion,
        candidate_flags=example.candidate_flags,
        candidate_mask=np.ones(example.candidate_count, dtype=np.bool_),
        candidate_uci=example.candidate_uci,
    )


def effective_model_input_bytes(example: PositionFeatures) -> bytes:
    return json.dumps(
        effective_model_input_document(example),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _effective_model_input_digest(encoded: bytes) -> str:
    return hashlib.sha256(encoded).hexdigest()


def effective_model_input_sha256(example: PositionFeatures) -> str:
    return _effective_model_input_digest(effective_model_input_bytes(example))


def collated_effective_model_input_sha256(batch: dict[str, Any], index: int) -> str:
    """Hash one padded batch row after stripping only mask-declared padding."""
    if not 0 <= index < int(batch["board_planes"].shape[0]):
        raise IndexError("batch row index is out of bounds")
    history_mask = batch["history_mask"][index].detach().cpu().numpy().astype(np.bool_)
    candidate_mask = batch["candidate_mask"][index].detach().cpu().numpy().astype(np.bool_)
    history_length = int(history_mask.sum())
    candidate_count = int(candidate_mask.sum())
    if not np.array_equal(history_mask, np.arange(len(history_mask)) < history_length):
        raise ValueError("collated history mask is not a contiguous valid prefix")
    if not np.array_equal(candidate_mask, np.arange(len(candidate_mask)) < candidate_count):
        raise ValueError("collated candidate mask is not a contiguous valid prefix")
    document = _effective_input_document(
        board_planes=batch["board_planes"][index].detach().cpu().numpy(),
        state_scalars=batch["state_scalars"][index].detach().cpu().numpy(),
        history_moves=batch["history_moves"][index, :history_length].detach().cpu().numpy(),
        history_mask=np.ones(history_length, dtype=np.bool_),
        candidate_squares=batch["candidate_squares"][index, :candidate_count].detach().cpu().numpy(),
        candidate_promotion=batch["candidate_promotion"][index, :candidate_count].detach().cpu().numpy(),
        candidate_flags=batch["candidate_flags"][index, :candidate_count].detach().cpu().numpy(),
        candidate_mask=np.ones(candidate_count, dtype=np.bool_),
        candidate_uci=batch["candidate_uci"][index],
    )
    encoded = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
    ).encode("ascii")
    return _effective_model_input_digest(encoded)


def select_distinct_training_examples(
    examples: Iterable[PositionFeatures], count: int = 128,
) -> DistinctInputSelection:
    """Take the first ascending train IDs with distinct complete model inputs.

    Target labels and provenance are excluded from identity. Hash matches are
    additionally checked against canonical bytes so an identity collision
    cannot silently merge unequal inputs.
    """
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError("count must be a positive integer")
    train = [example for example in examples if example.split == "train"]
    if len({example.sample_id for example in train}) != len(train):
        raise ValueError("training examples contain duplicate sample IDs")
    selected: list[PositionFeatures] = []
    identities: list[str] = []
    canonical_by_hash: dict[str, bytes] = {}
    for example in sorted(train, key=lambda row: row.sample_id):
        canonical = effective_model_input_bytes(example)
        digest = _effective_model_input_digest(canonical)
        prior = canonical_by_hash.get(digest)
        if prior is not None:
            if prior != canonical:
                raise RuntimeError("effective model input SHA-256 identity collision detected")
            continue
        canonical_by_hash[digest] = canonical
        selected.append(example)
        identities.append(digest)
        if len(selected) == count:
            break
    if len(selected) != count:
        raise ValueError(
            f"need {count} distinct train model inputs, found {len(selected)}"
        )
    selection = DistinctInputSelection(tuple(selected), tuple(identities))
    if len(set(selection.sample_ids)) != count or tuple(sorted(selection.sample_ids)) != selection.sample_ids:
        raise RuntimeError("distinct-input sample selection violated sample ID ordering or uniqueness")
    if len(set(selection.input_sha256)) != count:
        raise RuntimeError("distinct-input sample selection contains duplicate effective inputs")
    # Check that batched model tensors represent exactly the unpadded identity
    # that selected the rows. The shared batch includes realistic padding.
    for offset in range(0, len(selection.examples), MAX_PHYSICAL_BATCH_POSITIONS):
        rows = selection.examples[offset:offset + MAX_PHYSICAL_BATCH_POSITIONS]
        verification_batch = collate_examples(rows, require_targets=False)
        for index, example in enumerate(rows):
            expected_hash = selection.input_sha256[offset + index]
            actual_hash = collated_effective_model_input_sha256(verification_batch, index)
            if actual_hash != expected_hash:
                raise RuntimeError(
                    f"collated BehaviorScorer input differs from selector identity for {example.sample_id}"
                )
    return selection


def collate_examples(
    examples: Iterable[PositionFeatures], *, require_targets: bool = True,
) -> dict[str, Any]:
    rows = tuple(examples)
    if not rows:
        raise ValueError("cannot collate an empty example batch")
    batch_size = len(rows)
    max_history = max(row.history_length for row in rows)
    max_candidates = max(row.candidate_count for row in rows)
    if batch_size > MAX_PHYSICAL_BATCH_POSITIONS:
        raise ValueError("physical batch exceeds 64 positions")
    if batch_size * max_history > MAX_PADDED_HISTORY_TOKENS:
        raise ValueError("padded batch exceeds the 32,768-token history budget")
    if batch_size * max_candidates > MAX_PADDED_CANDIDATE_SLOTS:
        raise ValueError("padded batch exceeds the 8,192-slot candidate budget")
    if require_targets and any(row.target_index is None for row in rows):
        raise ValueError("behavior training batches require one legal target per row")
    if require_targets and any(row.candidate_count == 0 for row in rows):
        raise ValueError("terminal empty candidate sets cannot be used as behavior targets")

    board_planes = np.zeros((batch_size, 13, 8, 8), dtype=np.float32)
    state_scalars = np.zeros((batch_size, 6), dtype=np.float32)
    history_moves = np.zeros((batch_size, max_history, 4), dtype=np.int64)
    history_mask = np.zeros((batch_size, max_history), dtype=np.bool_)
    candidate_squares = np.zeros((batch_size, max_candidates, 2), dtype=np.int64)
    candidate_promotion = np.zeros((batch_size, max_candidates), dtype=np.int64)
    candidate_flags = np.zeros((batch_size, max_candidates, 4), dtype=np.float32)
    candidate_mask = np.zeros((batch_size, max_candidates), dtype=np.bool_)
    target_indices = np.full(batch_size, -1, dtype=np.int64)

    for index, row in enumerate(rows):
        board_planes[index] = row.board_planes
        state_scalars[index] = row.state_scalars
        history_len = row.history_length
        if history_len:
            history_moves[index, :history_len] = row.history_moves
            history_mask[index, :history_len] = True
        count = row.candidate_count
        if count:
            candidate_squares[index, :count] = row.candidate_squares
            candidate_promotion[index, :count] = row.candidate_promotion
            candidate_flags[index, :count] = row.candidate_flags
            candidate_mask[index, :count] = True
        if row.target_index is not None:
            target_indices[index] = row.target_index

    return {
        "board_planes": torch.from_numpy(board_planes),
        "state_scalars": torch.from_numpy(state_scalars),
        "history_moves": torch.from_numpy(history_moves),
        "history_mask": torch.from_numpy(history_mask),
        "candidate_squares": torch.from_numpy(candidate_squares),
        "candidate_promotion": torch.from_numpy(candidate_promotion),
        "candidate_flags": torch.from_numpy(candidate_flags),
        "candidate_mask": torch.from_numpy(candidate_mask),
        "candidate_uci": [row.candidate_uci for row in rows],
        "target_indices": torch.from_numpy(target_indices),
        "sample_ids": [row.sample_id for row in rows],
        "splits": [row.split for row in rows],
    }


def model_inputs(batch: dict[str, Any]) -> dict[str, Any]:
    """Select only the versioned model fields, excluding labels/provenance."""
    return {
        key: batch[key]
        for key in (
            "board_planes",
            "state_scalars",
            "history_moves",
            "history_mask",
            "candidate_squares",
            "candidate_promotion",
            "candidate_flags",
            "candidate_mask",
            "candidate_uci",
        )
    }
