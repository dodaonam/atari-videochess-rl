"""Versioned M3 identities and record validation."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import PurePosixPath
from typing import Any

import chess

DATASET_SCHEMA = "videochess-dataset/1.0"
GAME_SCHEMA = "videochess-game/1.0"
POSITION_SCHEMA = "videochess-position/1.0"
CANDIDATE_SCHEMA = "videochess-candidate/1.0"
TEACHER_SCHEMA = "videochess-teacher/1.0"
SPLIT_SCHEMA = "videochess-split/1.1"
LEGACY_SPLIT_SCHEMA = "videochess-split/1.0"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def canonical_json(value: Any) -> bytes:
    """Serialize identity data exactly as specified by DATASET_SPEC.md."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def require_sha256(value: str, field: str = "sha256") -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise ValueError(f"{field} must be 64 lowercase hexadecimal characters")
    return value


def normalized_text(value: str) -> str:
    return unicodedata.normalize("NFC", value.strip())


def source_identity(publisher_key: str, canonical_source_url: str, collection_key: str) -> str:
    return digest({
        "domain": "videochess-source/v1",
        "publisher_key": normalized_text(publisher_key),
        "canonical_source_url": normalized_text(canonical_source_url),
        "collection_key": normalized_text(collection_key),
    })


def source_game_identity(source_id: str, source_game_ref: str) -> str:
    return digest({
        "domain": "videochess-source-game/v1",
        "source_id": source_id,
        "source_game_ref": normalized_text(source_game_ref),
    })


def fallback_game_identity(
    source_id: str, archive_sha256: str, member_name: str,
    normalized_game_sha256: str, duplicate_occurrence_ordinal: int,
) -> str:
    return digest({
        "domain": "videochess-source-game-fallback/v1",
        "source_id": source_id,
        "archive_sha256": archive_sha256,
        "member_name": member_name,
        "normalized_game_sha256": normalized_game_sha256,
        "duplicate_occurrence_ordinal": duplicate_occurrence_ordinal,
    })


def canonical_fen(board: chess.Board) -> str:
    return board.fen(en_passant="legal")


def normalized_game_identity(initial_fen: str, moves_uci: list[str]) -> str:
    return digest({
        "domain": "videochess-normalized-game/v1",
        "variant": "standard",
        "initial_fen": initial_fen,
        "moves_uci": moves_uci,
    })


def board_position_signature(board: chess.Board) -> str:
    fields = canonical_fen(board).split()
    return digest({
        "domain": "videochess-board-position/v1",
        "variant": "standard",
        "placement": fields[0],
        "side_to_move": fields[1],
        "castling": fields[2],
        "legal_ep": fields[3],
    })


def replay_history_identity(initial_fen: str, moves_uci_prefix: list[str]) -> str:
    return digest({
        "domain": "videochess-replay-state/v1",
        "initial_fen": initial_fen,
        "moves_uci_prefix": moves_uci_prefix,
    })


def sample_identity(
    source_id: str, game_id: str, normalized_game_sha256: str, ply_index: int,
) -> str:
    return digest({
        "domain": "videochess-sample/v1",
        "schema_version": POSITION_SCHEMA,
        "source_id": source_id,
        "game_id": game_id,
        "normalized_game_sha256": normalized_game_sha256,
        "ply_index": ply_index,
    })


def candidate_identity(sample_id: str, action_uci: str) -> str:
    return digest({
        "domain": "videochess-candidate/v1",
        "schema_version": CANDIDATE_SCHEMA,
        "sample_id": sample_id,
        "action_uci": action_uci,
    })


def config_identity(config: dict[str, Any]) -> str:
    return digest({
        "domain": "videochess-config/v1",
        "schema_version": "videochess-config/1.0",
        "config": config,
    })


def sample_set_identity(sample_ids: list[str]) -> str:
    return digest({
        "domain": "videochess-sample-set/v1",
        "sample_ids": sorted(set(sample_ids)),
    })


def game_sample_key(seed: int, normalized_game_sha256: str) -> str:
    return digest({
        "domain": "videochess-game-sample/v1",
        "seed": seed,
        "normalized_game_sha256": normalized_game_sha256,
    })


def ply_sample_key(seed: int, source_id: str, game_id: str, ply_index: int) -> str:
    return digest({
        "domain": "videochess-ply-sample/v1",
        "seed": seed,
        "source_id": source_id,
        "game_id": game_id,
        "ply_index": ply_index,
    })


def assign_game_split(seed: int, normalized_game_sha256: str) -> str:
    value = digest({
        "domain": "videochess-game-split/v1",
        "split_seed": seed,
        "normalized_game_sha256": normalized_game_sha256,
    })
    bucket = int(value[:4], 16)
    return "train" if bucket < 52429 else "validation" if bucket < 58983 else "test"


def board_signature_owner(seed: int, signature: str, present_splits: set[str]) -> str:
    if not present_splits:
        raise ValueError("cannot assign an owner to a board absent from all splits")
    ranks = {
        split: digest({
            "domain": "videochess-board-owner/v1",
            "split_seed": seed,
            "board_position_signature": signature,
            "candidate_split_name": split,
        })
        for split in present_splits
    }
    return min(ranks, key=lambda name: (ranks[name], name))


def split_manifest_identity(
    seed: int, assignments: list[list[str]], owners: list[list[str]],
    purged: list[list[str]],
) -> str:
    return digest({
        "domain": "videochess-split-manifest/v1",
        "split_seed": seed,
        "game_group_assignments": sorted(assignments),
        "board_signature_owners": sorted(owners),
        "purged_sample_partitions": sorted(purged),
    })


def release_identity(
    source_archive_sha256: str, schema_versions: list[str], config_sha256: str,
    code_revision: str, split_assignment_sha256: str,
    outputs: list[list[Any]],
) -> str:
    return digest({
        "domain": "videochess-release/v1",
        "source_archive_sha256": source_archive_sha256,
        "schema_versions": sorted(schema_versions),
        "config_sha256": config_sha256,
        "code_revision": code_revision,
        "split_assignment_sha256": split_assignment_sha256,
        "outputs": sorted(outputs),
    })


def validate_game_record(game: dict[str, Any]) -> None:
    if game.get("schema") != GAME_SCHEMA or game.get("schema_version") != GAME_SCHEMA:
        raise ValueError("unsupported game schema")
    require_sha256(game.get("game_id", ""), "game_id")
    if game.get("record_id") != game.get("game_id"):
        raise ValueError("game record_id must equal game_id")
    require_sha256(game.get("normalized_game_sha256", ""), "normalized_game_sha256")
    if game.get("variant") != "standard":
        raise ValueError("only standard chess game records are supported")
    require_sha256(game.get("source_id", ""), "source_id")
    require_sha256(game.get("source_archive_sha256", ""), "source_archive_sha256")
    if not isinstance(game.get("source_member_name"), str) or not game["source_member_name"].lower().endswith(".pgn"):
        raise ValueError("source_member_name must identify the PGN member")
    if game.get("source_member") != game["source_member_name"]:
        raise ValueError("source_member alias differs from source_member_name")
    if not isinstance(game.get("source_ordinal"), int) or game["source_ordinal"] < 1:
        raise ValueError("source_ordinal must be a positive integer")
    if game.get("pgn_result") not in {"1-0", "0-1", "1/2-1/2"}:
        raise ValueError("pgn_result is unsupported")
    if game.get("result") != game.get("pgn_result"):
        raise ValueError("result alias differs from pgn_result")
    expected_white_result = {"1-0": "win", "0-1": "loss", "1/2-1/2": "draw"}[game["pgn_result"]]
    if game.get("white_result") != expected_white_result:
        raise ValueError("white_result does not match PGN result")
    if "source_game_ref" in game or any(key in game.get("headers", {}) for key in ("White", "Black", "LichessURL", "Site")):
        raise ValueError("game record contains a raw player name or game URL")
    if game.get("source_game_id") is not None:
        require_sha256(game["source_game_id"], "source_game_id")
    if game.get("source_game_ref_sha256") is not None:
        require_sha256(game["source_game_ref_sha256"], "source_game_ref_sha256")
    if game.get("initial_fen") != chess.STARTING_FEN:
        raise ValueError("M3 release requires the standard initial position")
    moves = game.get("moves_uci")
    if not isinstance(moves, list) or not all(isinstance(move, str) for move in moves):
        raise ValueError("moves_uci must be a list of UCI strings")
    board = chess.Board(game["initial_fen"])
    for ply, uci in enumerate(moves):
        if board.is_game_over(claim_draw=False):
            raise ValueError(f"move sequence continues after automatic termination at ply {ply}")
        try:
            move = chess.Move.from_uci(uci)
        except ValueError as exc:
            raise ValueError(f"invalid UCI at ply {ply}: {uci}") from exc
        if move not in board.legal_moves:
            raise ValueError(f"illegal UCI at ply {ply}: {uci}")
        board.push(move)
    outcome = board.outcome(claim_draw=False)
    expected_termination = None
    if outcome is not None:
        expected_winner = (
            ("white" if outcome.winner else "black")
            if outcome.winner is not None else "draw"
        )
        expected_termination = {
            "termination": outcome.termination.name,
            "winner": expected_winner,
        }
        expected_result = {
            "white": "1-0", "black": "0-1", "draw": "1/2-1/2",
        }[expected_winner]
        if game["pgn_result"] != expected_result:
            raise ValueError("PGN result contradicts the reconstructed automatic terminal outcome")
    if game.get("board_termination") != expected_termination:
        raise ValueError("board_termination metadata does not match the reconstructed automatic outcome")
    if normalized_game_identity(game["initial_fen"], moves) != game["normalized_game_sha256"]:
        raise ValueError("normalized game identity does not match moves")
    if game.get("ply_count") != len(moves):
        raise ValueError("ply_count does not match moves_uci")
    if game.get("validation_status") != "accepted" or not isinstance(game.get("diagnostics"), list):
        raise ValueError("accepted game validation status/diagnostics are malformed")


def reconstruct_position(game: dict[str, Any], ply_index: int) -> chess.Board:
    validate_game_record(game)
    if not isinstance(ply_index, int) or not 0 <= ply_index < len(game["moves_uci"]):
        raise ValueError("ply_index must identify a played main-line move")
    board = chess.Board(game["initial_fen"])
    for uci in game["moves_uci"][:ply_index]:
        board.push_uci(uci)
    return board


def validate_position_record(
    position: dict[str, Any], game: dict[str, Any], *, verify_sample_id: bool = True,
) -> chess.Board:
    if position.get("schema") != POSITION_SCHEMA:
        raise ValueError("unsupported position schema")
    if position.get("schema_version") != POSITION_SCHEMA:
        raise ValueError("unsupported position schema version")
    if position.get("record_id") != position.get("sample_id"):
        raise ValueError("position record_id must equal sample_id")
    if position.get("game_id") != game.get("game_id"):
        raise ValueError("position references a different game")
    if position.get("source_id") != game.get("source_id"):
        raise ValueError("position source_id differs from its game")
    if position.get("normalized_game_sha256") != game.get("normalized_game_sha256"):
        raise ValueError("position normalized-game identity differs from its game")
    board = reconstruct_position(game, position.get("ply_index"))
    if position.get("reconstruction_path") != {"game_id": game["game_id"], "ply_index": position["ply_index"]}:
        raise ValueError("position reconstruction reference does not match game/ply")
    legal = sorted(move.uci() for move in board.legal_moves)
    if position.get("fen") != canonical_fen(board):
        raise ValueError("position FEN does not reconstruct")
    if position.get("side_to_move") != ("white" if board.turn else "black"):
        raise ValueError("position side_to_move does not reconstruct")
    if position.get("legal_moves_uci") != legal:
        raise ValueError("legal move set does not reconstruct")
    if position.get("played_move_uci") != game["moves_uci"][position["ply_index"]]:
        raise ValueError("played move does not match source game")
    if position["played_move_uci"] not in legal:
        raise ValueError("played move is not a legal candidate")
    if position.get("board_position_signature") != board_position_signature(board):
        raise ValueError("board signature does not reconstruct")
    if position.get("history_state_id") != replay_history_identity(
        game["initial_fen"], game["moves_uci"][:position["ply_index"]],
    ):
        raise ValueError("history state identity does not reconstruct")
    require_sha256(position.get("sample_id", ""), "sample_id")
    if verify_sample_id:
        expected = sample_identity(
            position["source_id"], game["game_id"], game["normalized_game_sha256"],
            position["ply_index"],
        )
        if position["sample_id"] != expected:
            raise ValueError("sample identity does not match source/game/ply")
    if position.get("candidate_count") != len(legal):
        raise ValueError("candidate count does not match legal moves")
    expected_candidate_set = digest({
        "domain": "videochess-candidate-set/v1",
        "sample_id": position["sample_id"], "legal_moves_uci": legal,
    })
    if position.get("candidate_set_sha256") != expected_candidate_set:
        raise ValueError("candidate set identity does not recompute")
    if position.get("played_candidate_id") != candidate_identity(position["sample_id"], position["played_move_uci"]):
        raise ValueError("played candidate identity does not recompute")
    expected_white_result = {
        "1-0": "win", "0-1": "loss", "1/2-1/2": "draw",
    }[game["pgn_result"]]
    expected_side_result = expected_white_result
    if board.turn == chess.BLACK:
        expected_side_result = {
            "win": "loss", "draw": "draw", "loss": "win",
        }[expected_white_result]
    expected_to_move = {"win": 1, "draw": 0, "loss": -1}[expected_side_result]
    if (
        position.get("pgn_result") != game["pgn_result"]
        or position.get("white_result") != expected_white_result
        or position.get("side_to_move_result") != expected_side_result
        or position.get("result_white") != game["pgn_result"]
        or position.get("result_to_move") != expected_to_move
    ):
        raise ValueError("position game-result perspective does not match its parent game")
    if position.get("sampling_config_sha256") is None or position.get("sampling_id") is None:
        raise ValueError("position sampling provenance is missing")
    require_sha256(position["sampling_config_sha256"], "sampling_config_sha256")
    require_sha256(position["sampling_id"], "sampling_id")
    if position.get("split") != position.get("split_id"):
        raise ValueError("position split_id differs from split")
    return board
