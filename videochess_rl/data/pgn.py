"""Streaming standard-chess PGN parsing and legal replay."""

from __future__ import annotations

import hashlib
import io
import json
import logging
from dataclasses import dataclass, field
from typing import Any, BinaryIO, Iterator

import chess
import chess.pgn

from .contracts import canonical_fen, normalized_game_identity, normalized_text, source_game_identity


class SourceLimitError(ValueError):
    """A source stream exceeded a hard read or per-game budget."""


class BoundedBinaryReader(io.RawIOBase):
    """Raw stream wrapper enforcing a decompressed-byte cap in fixed chunks."""

    def __init__(self, raw: BinaryIO, max_bytes: int):
        self.raw = raw
        self.max_bytes = max_bytes
        self.total_bytes = 0
        self.member_digest = hashlib.sha256()

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: bytearray | memoryview) -> int:
        if self.closed:
            raise ValueError("I/O operation on closed bounded reader")
        remaining = self.max_bytes - self.total_bytes
        request = min(len(buffer), max(remaining + 1, 1))
        chunk = self.raw.read(request)
        if not chunk:
            return 0
        if len(chunk) > remaining:
            raise SourceLimitError("PGN member exceeded streaming decompressed-byte cap")
        buffer[:len(chunk)] = chunk
        self.total_bytes += len(chunk)
        self.member_digest.update(chunk)
        return len(chunk)

    def close(self) -> None:
        if not self.closed:
            super().close()


class GameBudgetText:
    """Per-read_game text adapter that stops pathological PGN blocks."""

    def __init__(self, text_stream: io.TextIOBase, max_game_bytes: int):
        self.text_stream = text_stream
        self.max_game_bytes = max_game_bytes
        self.used = 0

    def readline(self, size: int = -1) -> str:
        remaining = self.max_game_bytes - self.used
        request = remaining + 1 if size < 0 else min(size, remaining + 1)
        line = self.text_stream.readline(request)
        encoded_bytes = len(line.encode("utf-8"))
        self.used += encoded_bytes
        if self.used > self.max_game_bytes:
            raise SourceLimitError("PGN game block exceeded max_game_bytes")
        return line


@dataclass
class ParseResult:
    status: str
    reason_code: str | None
    detail: str | None
    game: dict[str, Any] | None = None
    stats: dict[str, Any] = field(default_factory=dict)


class TrackingGameBuilder(chess.pgn.GameBuilder):
    """Capture the movetext result token separately from the Result header."""

    def __init__(self) -> None:
        super().__init__()
        self.movetext_result: str | None = None

    def visit_result(self, result: str) -> None:
        self.movetext_result = result
        super().visit_result(result)


def _header_hash(headers: dict[str, str]) -> str:
    packed = json.dumps(
        list(headers.items()), ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(packed).hexdigest()


def _result_for_side(result: str, white_to_move: bool) -> str:
    if result == "1/2-1/2":
        return "draw"
    if result == "1-0":
        return "win" if white_to_move else "loss"
    if result == "0-1":
        return "loss" if white_to_move else "win"
    raise ValueError("unsupported game result")


def _validate_headers(headers: dict[str, str]) -> tuple[str | None, str | None]:
    variant = headers.get("Variant", "Standard").strip().casefold()
    if variant not in ("standard", "chess"):
        return "unsupported_variant", f"Variant header is {headers.get('Variant')!r}"
    setup = headers.get("SetUp", "0").strip()
    fen = headers.get("FEN")
    if setup not in ("0", "1"):
        return "malformed_setup_header", "SetUp must be 0 or 1"
    if setup == "1" or fen is not None:
        return "custom_initial_position", "M3 first release accepts only the standard initial position"
    if headers.get("Result") not in ("1-0", "0-1", "1/2-1/2"):
        return "unknown_or_malformed_result", f"Result header is {headers.get('Result')!r}"
    return None, None


def _integer_header(value: str | None) -> int | None:
    if value is None or not value.isascii() or not value.isdigit():
        return None
    parsed = int(value)
    return parsed if 0 <= parsed <= 10000 else None


_RETAINED_HEADERS = {
    "Event", "Date", "Round", "WhiteElo", "BlackElo", "TimeControl",
    "Termination", "Opening", "ECO", "Variant", "Result",
}


def parse_one_game(
    game: chess.pgn.Game, *, source_id: str, archive_sha256: str,
    member_name: str, source_ordinal: int, duplicate_occurrence_ordinal: int,
    movetext_result: str | None,
    max_header_bytes: int = 256 * 1024, max_header_value_bytes: int = 64 * 1024,
    max_comment_bytes: int = 1024 * 1024,
) -> ParseResult:
    """Validate one parsed PGN and return a game record without fixing errors."""
    headers = dict(game.headers)
    header_bytes = len(json.dumps(headers, ensure_ascii=False).encode("utf-8"))
    if header_bytes > max_header_bytes:
        return ParseResult("quarantined", "header_bytes_exceeded", None, stats={"header_bytes": header_bytes})
    if any(len(value.encode("utf-8")) > max_header_value_bytes for value in headers.values()):
        return ParseResult("quarantined", "header_value_bytes_exceeded", None, stats={"header_bytes": header_bytes})
    reason, detail = _validate_headers(headers)
    if reason:
        status = "rejected" if reason in {"unsupported_variant", "custom_initial_position"} else "quarantined"
        return ParseResult(status, reason, detail, stats={"header_bytes": header_bytes})
    if game.errors:
        # python-chess omits a malformed token from the recovered main line. If
        # the valid prefix already ended by automatic rules, retain the more
        # actionable distinction that the PGN continued beyond termination.
        recovered_board = game.board()
        for recovered_move in game.mainline_moves():
            if recovered_board.is_game_over(claim_draw=False):
                return ParseResult(
                    "quarantined", "moves_after_automatic_terminal",
                    "PGN parser reported an error after the recovered line reached automatic termination",
                    stats={"header_bytes": header_bytes},
                )
            if recovered_move not in recovered_board.legal_moves:
                break
            recovered_board.push(recovered_move)
        if recovered_board.is_game_over(claim_draw=False):
            return ParseResult(
                "quarantined", "moves_after_automatic_terminal",
                "PGN parser reported a trailing token after automatic termination",
                stats={"header_bytes": header_bytes},
            )
        return ParseResult(
            "quarantined", "pgn_parser_error", str(game.errors[0])[:240],
            stats={"header_bytes": header_bytes},
        )
    if movetext_result not in ("1-0", "0-1", "1/2-1/2"):
        return ParseResult(
            "quarantined", "missing_or_incomplete_movetext_result",
            "PGN has no completed result token", stats={"header_bytes": header_bytes},
        )
    if movetext_result != headers.get("Result"):
        return ParseResult(
            "quarantined", "pgn_result_header_mismatch",
            "PGN Result header differs from its movetext result token",
            stats={"header_bytes": header_bytes},
        )
    for node in game.mainline():
        if len(node.comment.encode("utf-8")) > max_comment_bytes:
            return ParseResult("quarantined", "comment_bytes_exceeded", None, stats={"header_bytes": header_bytes})
    board = game.board()
    if board.chess960 or not board.is_valid() or canonical_fen(board) != chess.STARTING_FEN:
        return ParseResult("rejected", "nonstandard_initial_board", None, stats={"header_bytes": header_bytes})
    moves: list[str] = []
    for ply, move in enumerate(game.mainline_moves()):
        if board.is_game_over(claim_draw=False):
            return ParseResult(
                "quarantined", "moves_after_automatic_terminal",
                f"main line continues after automatic termination at ply {ply}",
                stats={"header_bytes": header_bytes, "plies_before_error": ply},
            )
        if move not in board.legal_moves:
            return ParseResult(
                "quarantined", "illegal_move", f"illegal main-line move at ply {ply}",
                stats={"header_bytes": header_bytes, "plies_before_error": ply},
            )
        moves.append(move.uci())
        board.push(move)
    if not moves:
        return ParseResult("quarantined", "empty_game", None, stats={"header_bytes": header_bytes})
    result = headers["Result"]
    termination = headers.get("Termination")
    source_ref = headers.get("LichessURL") or headers.get("Site")
    normalized_ref = normalized_text(source_ref) if source_ref else None
    norm_id = normalized_game_identity(chess.STARTING_FEN, moves)
    board_outcome = board.outcome(claim_draw=False)
    board_termination = None
    if board_outcome is not None:
        board_termination = {
            "termination": board_outcome.termination.name,
            "winner": ("white" if board_outcome.winner else "black") if board_outcome.winner is not None else "draw",
        }
    return ParseResult(
        "accepted", None, None,
        game={
            "schema": "videochess-game/1.0",
            "schema_version": "videochess-game/1.0",
            "game_id": None,
            "record_id": None,
            "source_id": source_id,
            # Do not persist player names or raw game URLs in the bulk release.
            # The opaque source-game identity and reference hash retain auditability.
            "source_game_id": source_game_identity(source_id, normalized_ref) if normalized_ref else None,
            "source_game_ref_sha256": hashlib.sha256(normalized_ref.encode("utf-8")).hexdigest() if normalized_ref else None,
            "source_game_ref_present": normalized_ref is not None,
            "source_ordinal": source_ordinal,
            "source_game_ordinal": source_ordinal,
            "duplicate_occurrence_ordinal": duplicate_occurrence_ordinal,
            "normalized_game_sha256": norm_id,
            "variant": "standard",
            "initial_fen": chess.STARTING_FEN,
            "moves_uci": moves,
            "ply_count": len(moves),
            "pgn_result": result,
            "result": result,
            "white_result": {"1-0": "win", "0-1": "loss", "1/2-1/2": "draw"}[result],
            "validation_status": "accepted",
            "diagnostics": [],
            "termination_header": termination,
            "board_termination": board_termination,
            "header_keys": sorted(headers),
            "headers": {key: value for key, value in headers.items() if key in _RETAINED_HEADERS},
            "header_sha256": _header_hash(headers),
            "white_elo": _integer_header(headers.get("WhiteElo")),
            "black_elo": _integer_header(headers.get("BlackElo")),
            "white_rating": _integer_header(headers.get("WhiteElo")),
            "black_rating": _integer_header(headers.get("BlackElo")),
            "time_control": headers.get("TimeControl"),
            "date": headers.get("Date"),
            "event_date": headers.get("Date"),
            "event": headers.get("Event"),
            "opening": headers.get("Opening"),
        },
        stats={"header_bytes": header_bytes},
    )


def iter_pgn_games(
    binary_stream: BinaryIO, *, source_id: str, archive_sha256: str,
    member_name: str, max_games_seen: int, max_game_bytes: int,
    max_total_decompressed_bytes: int, max_header_bytes: int = 256 * 1024,
    max_header_value_bytes: int = 64 * 1024,
    max_comment_bytes: int = 1024 * 1024,
    stream_stats: dict[str, Any] | None = None,
    complete_scan: bool = True,
) -> Iterator[tuple[int, ParseResult]]:
    """Parse a bounded PGN stream one game at a time with strict UTF-8."""
    limited = BoundedBinaryReader(binary_stream, max_total_decompressed_bytes)
    buffered = io.BufferedReader(limited, buffer_size=64 * 1024)
    # Preserve CRLF bytes in the per-game byte budget while still splitting PGN
    # records on universal line endings.
    text = io.TextIOWrapper(buffered, encoding="utf-8", errors="strict", newline="")
    source_ref_counts: dict[str, int] = {}
    normalized_occurrences: dict[str, int] = {}
    ordinal = 0
    try:
        while ordinal < max_games_seen:
            budget = GameBudgetText(text, max_game_bytes)
            visitor_holder: list[TrackingGameBuilder] = []

            def make_visitor() -> TrackingGameBuilder:
                visitor = TrackingGameBuilder()
                visitor_holder.append(visitor)
                return visitor

            prior_log_disabled = chess.pgn.LOGGER.disabled
            chess.pgn.LOGGER.disabled = True
            try:
                game = chess.pgn.read_game(budget, Visitor=make_visitor)
            except UnicodeDecodeError as exc:
                raise SourceLimitError(f"unsupported or invalid PGN encoding near source game {ordinal + 1}") from exc
            finally:
                chess.pgn.LOGGER.disabled = prior_log_disabled
            if game is None:
                break
            ordinal += 1
            headers = dict(game.headers)
            # A canonical identity can be computed after legal replay. Occurrence
            # ordinals are source-order-bound only for the documented fallback.
            result = parse_one_game(
                game, source_id=source_id, archive_sha256=archive_sha256,
                member_name=member_name, source_ordinal=ordinal,
                duplicate_occurrence_ordinal=1,
                movetext_result=visitor_holder[0].movetext_result,
                max_header_bytes=max_header_bytes,
                max_header_value_bytes=max_header_value_bytes,
                max_comment_bytes=max_comment_bytes,
            )
            result.stats["header_keys"] = sorted(headers)
            result.stats["header_sha256"] = _header_hash(headers)
            if result.status == "accepted" and result.game is not None:
                record = result.game
                occurrence = normalized_occurrences.get(record["normalized_game_sha256"], 0) + 1
                normalized_occurrences[record["normalized_game_sha256"]] = occurrence
                record["duplicate_occurrence_ordinal"] = occurrence
                if record["source_game_ref_sha256"]:
                    ref = record["source_game_ref_sha256"]
                    source_ref_counts[ref] = source_ref_counts.get(ref, 0) + 1
                    record["source_game_ref_occurrence"] = source_ref_counts[ref]
                result.stats["duplicate_occurrence_ordinal"] = occurrence
            yield ordinal, result
        # A bounded source window is explicitly incomplete but has an independently
        # CRC-checked member hash. Complete scans fail rather than truncate at a cap.
        if ordinal == max_games_seen and complete_scan:
            for chunk in iter(lambda: text.read(64 * 1024), ""):
                if chunk.strip():
                    raise SourceLimitError("PGN stream contains more games than max_games_seen")
        elif complete_scan:
            for chunk in iter(lambda: text.read(64 * 1024), ""):
                pass
    finally:
        if stream_stats is not None:
            stream_stats.update({
                "decompressed_bytes_read": limited.total_bytes,
                "stream_sha256": limited.member_digest.hexdigest(),
            })
        text.close()
