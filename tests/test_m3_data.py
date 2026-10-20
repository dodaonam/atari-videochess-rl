"""Synthetic and bounded regressions for the M3 data pipeline."""

from __future__ import annotations

import hashlib
import io
import json
import os
import random
import sys
import tempfile
import textwrap
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import chess
import chess.pgn

from videochess_rl.data.contracts import (
    board_position_signature, canonical_fen, candidate_identity, config_identity,
    digest, normalized_game_identity, replay_history_identity, sample_identity,
    source_identity, validate_game_record, validate_position_record,
)
from videochess_rl.data.export import ExportError, verify_release, write_batches
from videochess_rl.data.pgn import SourceLimitError, iter_pgn_games
from videochess_rl.data.pipeline import build_dataset
from videochess_rl.data.sampling import BottomKGroups, sample_positions
from videochess_rl.data.source import (
    SourceError, download_archive, hash_member, inspect_zip, validate_source_manifest,
)
from videochess_rl.data.split import SplitError, split_and_purge
from videochess_rl.data.teacher import TeacherError, _cp_transform, _score_data, run_teacher, verify_teacher_run
from tests.test_pre_m3_contracts import FIXTURE

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DECISION = ROOT / ".agents/evidence/M3-source-decision-20261020.md"
AUTHORIZATION = ROOT / ".agents/evidence/M3-authorization-20261020.md"
SOURCE_URL = "https://database.nikonoel.fr/lichess_elite_2022-05.zip"
SOURCE_DECISION_ID = "M3-SOURCE-ELITE-2022-05-LOCAL-20261020"
AUTHORIZATION_ID = "M3-001-owner-20261020"
RIGHTS_STATUS = "third_party_license_unstated_internal_use_owner_authorized_no_redistribution"


def make_game(index: int, *, seed: int | None = None, plies: int = 16) -> tuple[str, dict[str, str], list[str]]:
    game = chess.pgn.Game()
    game.headers["Event"] = f"Synthetic {index}"
    game.headers["Site"] = f"https://lichess.org/synthetic-{index}"
    game.headers["LichessURL"] = f"https://lichess.org/synthetic-{index}"
    game.headers["Date"] = "2026.01.01"
    game.headers["Round"] = "1"
    game.headers["White"] = f"SyntheticWhite{index}"
    game.headers["Black"] = f"SyntheticBlack{index}"
    game.headers["WhiteElo"] = str(2400 + index % 100)
    game.headers["BlackElo"] = str(2300 + index % 100)
    game.headers["TimeControl"] = "300+0"
    game.headers["Result"] = "1/2-1/2"
    board = game.board()
    node = game
    rng = random.Random(index + 17 if seed is None else seed)
    moves = []
    for _ in range(plies):
        legal = sorted(board.legal_moves, key=lambda move: move.uci())
        move = legal[rng.randrange(len(legal))]
        moves.append(move.uci())
        node = node.add_variation(move)
        board.push(move)
        if board.is_game_over(claim_draw=False):
            break
    text = game.accept(chess.pgn.StringExporter(headers=True, variations=False, comments=False))
    return text + "\n", dict(game.headers), moves


def parse_text(text: str, *, max_games: int = 20, **kwargs):
    source = source_identity("test", "https://example.invalid/", "synthetic")
    return list(iter_pgn_games(
        io.BytesIO(text.encode("utf-8")), source_id=source,
        archive_sha256="a" * 64, member_name="games.pgn",
        max_games_seen=max_games, max_game_bytes=8 * 1024 * 1024,
        max_total_decompressed_bytes=16 * 1024 * 1024, **kwargs,
    ))


def parsed_records(count: int = 12, plies: int = 16) -> tuple[str, list[dict]]:
    texts = []
    records = []
    source = source_identity("test", "https://example.invalid/", "synthetic")
    for index in range(count):
        text, _, _ = make_game(index, plies=plies)
        texts.append(text)
    output = parse_text("\n".join(texts), max_games=count)
    for ordinal, result in output:
        if result.status != "accepted":
            raise AssertionError((ordinal, result.status, result.reason_code, result.detail))
        records.append(result.game)
    return source, records


def pgn_zip(path: Path, pgn_text: str, name: str = "games.pgn") -> tuple[str, int]:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, pgn_text.encode("utf-8"))
    return hash_member(path, name, max_decompressed_bytes=16 * 1024 * 1024)


class M3ContractTests(unittest.TestCase):
    def test_existing_reference_vectors_are_preserved(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        expected = fixture["expected_sha256"]
        self.assertEqual(board_position_signature(chess.Board()), expected["start_board_signature"])
        self.assertEqual(
            normalized_game_identity(chess.STARTING_FEN, ["e2e4", "e7e5"]),
            expected["e2e4_e7e5_normalized_game"],
        )
        self.assertEqual(
            sample_identity("src-v1", "game-a", expected["e2e4_e7e5_normalized_game"], 1),
            expected["src_v1_game_a_ply_1_sample"],
        )
        self.assertEqual(
            candidate_identity("synthetic-position-1", "e2e4"),
            expected["synthetic_position_1_e2e4_candidate"],
        )
        source = fixture["hash_examples"]["source"]
        self.assertEqual(
            source_identity(
                source["publisher_key"],
                f" {source['canonical_source_url']} ",
                source["collection_key"],
            ),
            expected["source_id"],
        )

    def test_valid_stream_parses_two_games_and_reconstructs_all_labels(self) -> None:
        first, _, _ = make_game(1, plies=20)
        second, _, _ = make_game(2, plies=18)
        stream_stats = {}
        output = parse_text(first + "\n" + second, max_games=10, stream_stats=stream_stats)
        self.assertEqual(len(output), 2)
        self.assertEqual([item[1].status for item in output], ["accepted", "accepted"])
        game = output[0][1].game
        self.assertEqual(game["variant"], "standard")
        self.assertNotIn("White", game["headers"])
        self.assertNotIn("Black", game["headers"])
        self.assertIn("White", game["header_keys"])
        self.assertEqual(game["white_result"], "draw")
        source = game["source_id"]
        game["game_id"] = game["source_game_id"]
        game["record_id"] = game["game_id"]
        game["source_archive_sha256"] = "a" * 64
        game["source_member_name"] = "games.pgn"
        game["source_member"] = "games.pgn"
        rows = sample_positions([game], source_id=source, seed=42, max_positions_per_game=8, max_positions=8)
        self.assertEqual(len(rows), 8)
        for row in rows:
            board = validate_position_record(row, game)
            self.assertEqual(row["fen"], canonical_fen(board))
            self.assertIn(row["played_move_uci"], row["legal_moves_uci"])
            self.assertEqual(row["candidate_count"], sum(1 for _ in board.legal_moves))
            self.assertEqual(row["history_state_id"], replay_history_identity(chess.STARTING_FEN, game["moves_uci"][:row["ply_index"]]))
        self.assertEqual(stream_stats["decompressed_bytes_read"], len((first + "\n" + second).encode("utf-8")))

    def test_castling_en_passant_promotion_and_repetition_replay(self) -> None:
        def game_text(uci_moves: list[str], result: str = "1/2-1/2") -> str:
            game = chess.pgn.Game()
            game.headers.update({
                "Event": "Rules fixture", "Site": "https://example.invalid/rules",
                "Date": "2026.01.01", "Round": "1", "White": "W", "Black": "B",
                "Result": result,
            })
            node = game
            board = game.board()
            for uci in uci_moves:
                move = board.parse_uci(uci)
                node = node.add_variation(move)
                board.push(move)
            return game.accept(chess.pgn.StringExporter(headers=True, variations=False, comments=False)) + "\n"

        special_lines = [
            ("castle", ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "g8f6", "e1g1"], "e1g1"),
            ("ep", ["e2e4", "a7a6", "e4e5", "d7d5", "e5d6"], "e5d6"),
            ("promotion", ["a2a4", "h7h5", "a4a5", "h5h4", "a5a6", "h4h3", "a6b7", "h3g2", "b7a8q"], "b7a8q"),
            ("repetition", ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"], "f6g8"),
        ]
        for name, moves, final_move in special_lines:
            with self.subTest(name=name):
                records = parse_text(game_text(moves))
                self.assertEqual(records[0][1].status, "accepted")
                self.assertEqual(records[0][1].game["moves_uci"][-1], final_move)
                self.assertIn(final_move, records[0][1].game["moves_uci"])

    def test_source_order_independent_bottom_k_group_selection(self) -> None:
        source, games = parsed_records(count=25, plies=20)
        archive_hash = "b" * 64
        def selected(rows):
            sampler = BottomKGroups(
                seed=123, max_games=7, source_id=source,
                archive_sha256=archive_hash, member_name="games.pgn",
            )
            for row in rows:
                sampler.add(row)
            return [row["normalized_game_sha256"] for row in sampler.selected_records()]
        self.assertEqual(selected(games), selected(list(reversed(games))))
        self.assertEqual(len(selected(games)), 7)

    def test_conflicting_reuse_of_one_source_reference_is_excluded(self) -> None:
        source, games = parsed_records(count=3, plies=20)
        shared_ref = "e" * 64
        games[0]["source_game_ref_sha256"] = shared_ref
        games[1]["source_game_ref_sha256"] = shared_ref
        games[1]["source_game_id"] = games[0]["source_game_id"]
        sampler = BottomKGroups(
            seed=2, max_games=3, source_id=source,
            archive_sha256="b" * 64, member_name="games.pgn",
        )
        for row in games:
            sampler.add(row)
        self.assertEqual(len(sampler.conflicting_source_refs), 1)
        self.assertEqual(len(sampler.conflicting_groups), 2)
        self.assertEqual(len(sampler.selected_records()), 1)

    def test_incomplete_result_variant_and_custom_initial_position_are_reason_coded(self) -> None:
        missing = "[Event \"No result\"]\n[Site \"local\"]\n[Date \"2026.01.01\"]\n[Round \"1\"]\n[White \"A\"]\n[Black \"B\"]\n\n1. e4 *\n"
        variant = missing.replace("No result", "Variant").replace("[Event", "[Variant \"Crazyhouse\"]\n[Event").replace("1. e4 *", "1. e4 1-0")
        custom = missing.replace("No result", "Custom").replace("[Event", "[SetUp \"1\"]\n[FEN \"4k3/8/8/8/8/8/8/4K3 w - - 0 1\"]\n[Event").replace("1. e4 *", "1. e4 1-0")
        rows = parse_text("\n".join((missing, variant, custom)), max_games=10)
        self.assertEqual(rows[0][1].reason_code, "unknown_or_malformed_result")
        self.assertEqual(rows[1][1].reason_code, "unsupported_variant")
        self.assertEqual(rows[1][1].status, "rejected")
        self.assertEqual(rows[2][1].reason_code, "custom_initial_position")
        self.assertEqual(rows[2][1].status, "rejected")

    def test_result_header_must_match_a_completed_movetext_result_token(self) -> None:
        base = "[Event \"Result check\"]\n[Site \"local\"]\n[Date \"2026.01.01\"]\n[Round \"1\"]\n[White \"A\"]\n[Black \"B\"]\n[Result \"1-0\"]\n\n1. e4 {comment with 0-1 text}\n"
        mismatch = base.replace("comment with 0-1 text}\n", "comment with 0-1 text} 0-1\n")
        missing = parse_text(base, max_games=2)[0][1]
        different = parse_text(mismatch, max_games=2)[0][1]
        self.assertEqual(missing.reason_code, "missing_or_incomplete_movetext_result")
        self.assertEqual(different.reason_code, "pgn_result_header_mismatch")

    def test_illegal_move_and_automatic_terminal_trailing_moves_are_quarantined(self) -> None:
        illegal = "[Event \"Illegal\"]\n[Site \"local\"]\n[Date \"2026.01.01\"]\n[Round \"1\"]\n[White \"A\"]\n[Black \"B\"]\n[Result \"1-0\"]\n\n1. e4 e5 2. e5 1-0\n"
        mate_then_move = "[Event \"Trailing\"]\n[Site \"local\"]\n[Date \"2026.01.01\"]\n[Round \"1\"]\n[White \"A\"]\n[Black \"B\"]\n[Result \"0-1\"]\n\n1. f3 e5 2. g4 Qh4# 3. a3 0-1\n"
        rows = parse_text(illegal + "\n" + mate_then_move, max_games=10)
        self.assertEqual(rows[0][1].status, "quarantined")
        self.assertIn(rows[0][1].reason_code, {"pgn_parser_error", "illegal_move"})
        self.assertEqual(rows[1][1].reason_code, "moves_after_automatic_terminal")

    def test_comments_headers_and_source_stream_limits_fail_safely(self) -> None:
        long_comment = "[Event \"Comment\"]\n[Site \"local\"]\n[Date \"2026.01.01\"]\n[Round \"1\"]\n[White \"A\"]\n[Black \"B\"]\n[Result \"1-0\"]\n\n1. e4 {" + ("x" * 128) + "} 1-0\n"
        row = parse_text(long_comment, max_games=2, max_comment_bytes=64)[0][1]
        self.assertEqual(row.reason_code, "comment_bytes_exceeded")
        with self.assertRaises(SourceLimitError):
            list(iter_pgn_games(
                io.BytesIO(long_comment.encode()), source_id="a", archive_sha256="b" * 64,
                member_name="games.pgn", max_games_seen=2, max_game_bytes=64,
                max_total_decompressed_bytes=1000,
            ))
        with self.assertRaises(SourceLimitError):
            list(iter_pgn_games(
                io.BytesIO(long_comment.encode()), source_id="a", archive_sha256="b" * 64,
                member_name="games.pgn", max_games_seen=2, max_game_bytes=1000,
                max_total_decompressed_bytes=32,
            ))

    def test_board_identity_preserves_castling_en_passant_and_history(self) -> None:
        board = chess.Board()
        start_sig = board_position_signature(board)
        moves = ["g1f3", "g8f6", "f3g1", "f6g8"] * 4
        for uci in moves:
            board.push_uci(uci)
        self.assertEqual(board_position_signature(board), start_sig)
        self.assertNotEqual(replay_history_identity(chess.STARTING_FEN, moves), replay_history_identity(chess.STARTING_FEN, []))
        castle = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        no_castle = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1")
        self.assertNotEqual(board_position_signature(castle), board_position_signature(no_castle))
        ep = chess.Board("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2")
        no_ep = chess.Board("4k3/8/8/3pP3/8/8/8/4K3 w - - 0 2")
        self.assertNotEqual(board_position_signature(ep), board_position_signature(no_ep))
        self.assertIn(chess.Move.from_uci("e5d6"), ep.legal_moves)

    def test_split_purge_inherits_game_split_and_detects_holdout_collapse(self) -> None:
        games = []
        positions = []
        for index in range(120):
            normalized = hashlib.sha256(f"game-{index}".encode()).hexdigest()
            game_id = hashlib.sha256(f"source-game-{index}".encode()).hexdigest()
            games.append({"game_id": game_id, "normalized_game_sha256": normalized})
            signature = hashlib.sha256(f"board-{index}".encode()).hexdigest()
            positions.append({
                "sample_id": hashlib.sha256(f"sample-{index}".encode()).hexdigest(),
                "game_id": game_id, "normalized_game_sha256": normalized,
                "board_position_signature": signature,
                "history_state_id": hashlib.sha256(f"history-{index}".encode()).hexdigest(),
                "legal_moves_uci": ["e2e4", "d2d4"], "candidate_count": 2,
                "played_move_uci": "e2e4",
                "side_to_move": "white", "white_result": "draw", "ply_index": index,
                "split": None,
            })
        kept, manifest = split_and_purge(games, positions, seed=22, min_holdout_positions=1)
        self.assertEqual(len(kept), len(positions))
        self.assertEqual(manifest["board_signatures_cross_split_after"], 0)
        assignments = dict(manifest["game_group_assignments"])
        self.assertTrue(all(row["split"] == assignments[row["normalized_game_sha256"]] for row in kept))
        shared = "f" * 64
        collapsed_positions = [dict(row, board_position_signature=shared) for row in positions]
        with self.assertRaises(SplitError) as caught:
            split_and_purge(games, collapsed_positions, seed=22, min_holdout_positions=1)
        self.assertIsNotNone(caught.exception.manifest)
        self.assertGreater(caught.exception.manifest["purged_candidate_count"], 0)

    def test_zip_source_validation_checks_member_identity_size_and_path_safety(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid = root / "valid.zip"
            text, _, _ = make_game(3)
            pgn_zip(valid, text)
            info = inspect_zip(
                valid, max_archive_bytes=10_000_000, max_member_bytes=1_000_000,
                max_total_uncompressed_bytes=1_000_000,
            )
            self.assertEqual(info["member"]["name"], "games.pgn")
            self.assertEqual(hash_member(valid, "games.pgn", max_decompressed_bytes=1_000_000)[1], len(text.encode()))
            with self.assertRaises(SourceError):
                inspect_zip(valid, max_archive_bytes=100, max_member_bytes=1_000_000, max_total_uncompressed_bytes=1_000_000)
            traversal = root / "traversal.zip"
            with zipfile.ZipFile(traversal, "w") as archive:
                archive.writestr("../games.pgn", text)
            with self.assertRaises(SourceError):
                inspect_zip(traversal, max_archive_bytes=1_000_000, max_member_bytes=1_000_000, max_total_uncompressed_bytes=1_000_000)
            extra = root / "extra.zip"
            with zipfile.ZipFile(extra, "w") as archive:
                archive.writestr("games.pgn", text)
                archive.writestr("other.txt", "not a PGN")
            with self.assertRaises(SourceError):
                inspect_zip(extra, max_archive_bytes=1_000_000, max_member_bytes=1_000_000, max_total_uncompressed_bytes=1_000_000)

    def test_zip_crc_corruption_and_symlink_members_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.zip"
            text, _, _ = make_game(9)
            pgn_zip(source, text)
            with zipfile.ZipFile(source) as archive:
                info = archive.getinfo("games.pgn")
            data = bytearray(source.read_bytes())
            data_offset = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
            data[data_offset + 3] ^= 0x40
            corrupted = root / "corrupted.zip"
            corrupted.write_bytes(data)
            with self.assertRaises(SourceError):
                hash_member(corrupted, "games.pgn", max_decompressed_bytes=1_000_000)
            symlink = root / "symlink.zip"
            with zipfile.ZipFile(symlink, "w") as archive:
                item = zipfile.ZipInfo("games.pgn")
                item.create_system = 3
                item.external_attr = (0o120777 << 16)
                archive.writestr(item, text)
            with self.assertRaises(SourceError):
                inspect_zip(symlink, max_archive_bytes=1_000_000, max_member_bytes=1_000_000, max_total_uncompressed_bytes=1_000_000)

    def test_source_manifest_keeps_rights_uncertainty_and_rejects_invented_license(self) -> None:
        archive_sha = "a" * 64
        member_sha = "b" * 64
        source_id_value = source_identity("lichess-elite", "https://database.nikonoel.fr/", "lichess-elite-2022-05")
        manifest = {
            "schema": "videochess-source-manifest/1.0", "schema_version": "videochess-source-manifest/1.0",
            "source_id": source_id_value,
            "publisher": "Lichess Elite Database (third-party curated package)",
            "original_data_provenance": "Lichess games selected and repackaged by the third-party publisher",
            "canonical_source_url": "https://database.nikonoel.fr/",
            "archive_url": SOURCE_URL,
            "archive_filename": "archive.zip",
            "archive_sha256": archive_sha, "archive_bytes": 100,
            "member_sha256": member_sha, "member_bytes": 1000,
            "member_name": "games.pgn", "crc_verified": True,
            "member": {"name": "games.pgn", "compressed_bytes": 100,
                       "uncompressed_bytes": 1000, "crc32": "1234abcd"},
            "archive_member": {"name": "games.pgn", "compressed_bytes": 100,
                               "uncompressed_bytes": 1000, "crc32": "1234abcd"},
            "member_crc": "1234abcd",
            "source_decision_id": SOURCE_DECISION_ID, "authorization_id": AUTHORIZATION_ID,
            "approval_id": AUTHORIZATION_ID,
            "license_status": RIGHTS_STATUS,
            "rights_boundary": "bounded internal academic research; local retention; no upload or redistribution of archive or bulk derived game records",
            "license_name": None, "license_url": None,
            "license_unknown_reason": "publisher page does not state a license for this filtered third-party package",
            "published_archive_checksum": None,
            "retrieved_at_utc": "2026-10-20T14:53:45Z",
            "retrieval": {"url": SOURCE_URL, "final_url": SOURCE_URL,
                          "http_status": 200, "retrieved_at_utc": "2026-10-20T14:53:45Z",
                          "archive_path": "archive.zip", "archive_bytes": 100, "archive_sha256": archive_sha},
            "source_terms_evidence": {"path": ".agents/evidence/M3-source-terms-20261020.md",
                                      "sha256": "c" * 64,
                                      "publisher_page_sha256": "d" * 64,
                                      "upstream_terms_page_sha256": "e" * 64},
            "source_page_sha256": "d" * 64,
            "rights_evidence_path": ".agents/evidence/M3-source-terms-20261020.md",
            "rights_evidence_sha256": "c" * 64,
            "approval_evidence": {"source_decision_path": ".agents/evidence/M3-source-decision-20261020.md",
                                  "source_decision_sha256": "f" * 64,
                                  "authorization_path": ".agents/evidence/M3-authorization-20261020.md",
                                  "authorization_sha256": "0" * 64},
            "retrieval_limits": {"max_archive_bytes": 1000, "max_member_bytes": 2000,
                                 "max_total_decompressed_bytes": 2000, "max_compression_ratio": 200},
            "compression_ratio": 10.0,
            "python_version": "3.12.0", "python_chess_version": "1.11.2",
            "filter_config_sha256": None,
            "filter_config_unknown_reason": "not published",
            "code_revision": "1" * 40,
        }
        validate_source_manifest(manifest)
        manifest["license_name"] = "CC0"
        with self.assertRaises(SourceError):
            validate_source_manifest(manifest)

    def test_download_is_capped_and_refuses_to_overwrite(self) -> None:
        class FakeResponse(io.BytesIO):
            status = 200
            headers = {"Content-Length": "4", "Content-Type": "application/zip", "ETag": '"fixed"'}

            def geturl(self):
                return SOURCE_URL

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "archive.zip"
            with patch("videochess_rl.data.source.urllib.request.urlopen", return_value=FakeResponse(b"data")):
                result = download_archive(SOURCE_URL, target, max_bytes=8, retries=0)
            self.assertEqual(target.read_bytes(), b"data")
            self.assertEqual(result["archive_bytes"], 4)
            with self.assertRaises(SourceError):
                with patch("videochess_rl.data.source.urllib.request.urlopen", return_value=FakeResponse(b"data")):
                    download_archive(SOURCE_URL, target, max_bytes=8, retries=0)
            with self.assertRaises(SourceError):
                with patch("videochess_rl.data.source.urllib.request.urlopen", return_value=FakeResponse(b"data")):
                    download_archive(SOURCE_URL, Path(directory) / "small.zip", max_bytes=3, retries=0)

    def test_stockfish_score_signs_and_mate_type_are_explicit(self) -> None:
        white_board = chess.Board()
        white_info = {"score": chess.engine.PovScore(chess.engine.Cp(75), chess.WHITE)}
        side_white, white_score = _score_data(white_info, white_board)
        self.assertEqual(side_white, {"type": "cp", "value": 75, "unit": "centipawn", "perspective": "side_to_move"})
        self.assertEqual(white_score["value"], 75)
        black_board = chess.Board()
        black_board.push_uci("e2e4")
        black_info = {"score": chess.engine.PovScore(chess.engine.Cp(75), chess.WHITE)}
        side_black, white_score = _score_data(black_info, black_board)
        self.assertEqual(side_black["value"], -75)
        self.assertEqual(white_score["value"], 75)
        mate_info = {"score": chess.engine.PovScore(chess.engine.Mate(-3), chess.WHITE)}
        raw_mate, white_mate = _score_data(mate_info, black_board)
        self.assertEqual(raw_mate, {"type": "mate", "value": 3, "perspective": "side_to_move"})
        self.assertEqual(white_mate, {"type": "mate", "value": -3, "perspective": "white"})
        self.assertEqual(_cp_transform(0), "0.00000000")

    def test_batch_journal_resume_and_hash_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            games = [
                {"game_id": hashlib.sha256(f"g{i}".encode()).hexdigest(), "source_ordinal": i + 1}
                for i in range(2)
            ]
            positions = [
                {"sample_id": hashlib.sha256(f"s{i}".encode()).hexdigest(), "game_id": game["game_id"]}
                for i, game in enumerate(games)
            ]
            identity = {"source": "a" * 64, "config": "b" * 64, "code": "c" * 40}
            write_batches(run_dir, games[:1], positions[:1], input_identity=identity, batch_size=1)
            write_batches(run_dir, games, positions, input_identity=identity, batch_size=1, resume=True)
            self.assertEqual(len(list(run_dir.glob("batch-*"))), 2)
            with self.assertRaises(ExportError):
                write_batches(run_dir, games, positions, input_identity={**identity, "source": "d" * 64}, batch_size=1, resume=True)
            batch = run_dir / "batch-000000" / "games.jsonl"
            batch.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(ExportError):
                write_batches(run_dir, games, positions, input_identity=identity, batch_size=1, resume=True)

    def test_synthetic_end_to_end_release_is_reconstructible_and_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            source_id = source_identity("test", "https://example.invalid/", "synthetic")
            texts = [make_game(index, plies=20)[0] for index in range(120)]
            member_text = "\n".join(texts)
            archive_path = temp / "synthetic.zip"
            member_sha, member_bytes = pgn_zip(archive_path, member_text)
            archive_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()
            inspected = inspect_zip(
                archive_path, max_archive_bytes=1_000_000,
                max_member_bytes=1_000_000, max_total_uncompressed_bytes=1_000_000,
            )
            source_manifest = {
                "schema": "videochess-source-manifest/1.0", "source_id": source_id,
                "test_fixture": True,
                "publisher": "synthetic test fixture", "archive_sha256": archive_sha,
                "archive_bytes": archive_path.stat().st_size,
                "archive_path": archive_path.name,
                "source_decision_id": SOURCE_DECISION_ID,
                "authorization_id": AUTHORIZATION_ID,
                "license_status": RIGHTS_STATUS,
                "member": inspected["member"], "member_name": "games.pgn",
                "member_sha256": member_sha, "member_bytes": member_bytes,
            }
            source_path = temp / "source.json"
            source_path.write_text(json.dumps(source_manifest), encoding="utf-8")
            config = {
                "schema_version": "videochess-dataset/1.0", "sampling_mode": "source_window",
                "seed": 42, "sampling_seed": 43, "split_seed": 44,
                "max_games": 120, "max_input_games_seen": 200,
                "max_positions": 240, "max_positions_per_game": 2,
                "min_holdout_positions": 2, "min_holdout_retention_basis_points": 5000,
                "max_archive_bytes": 1_000_000, "max_member_bytes": 1_000_000,
                "max_total_decompressed_bytes": 1_000_000, "max_compression_ratio": 200,
                "max_output_bytes": 10_000_000, "max_elapsed_seconds": 600,
                "max_workers": 1, "memory_mib": 1024,
                "max_game_bytes": 1_000_000, "max_header_bytes": 100_000,
                "max_header_value_bytes": 10_000, "max_comment_bytes": 100_000,
                "batch_size": 25,
            }
            config_path = temp / "config.json"
            config_path.write_text(json.dumps({"dataset": config}), encoding="utf-8")
            output = temp / "releases" / "synthetic-release"
            result = build_dataset(
                archive_path, source_path, config_path, output,
                run_id="synthetic-run-001", repository_root=ROOT,
                source_decision_path=SOURCE_DECISION, authorization_path=AUTHORIZATION,
                confirm_write=True, allow_synthetic_source_for_test=True,
            )
            verified = verify_release(output, allow_synthetic_source_for_test=True)
            self.assertEqual(result["verification"], verified)
            self.assertGreater(verified["games"], 100)
            self.assertGreater(verified["positions"], 100)
            self.assertEqual((output / "rejections.jsonl").stat().st_size, 0)
            with (output / "positions.jsonl").open(encoding="utf-8") as stream:
                row = json.loads(next(stream))
            game_rows = [json.loads(line) for line in (output / "games.jsonl").read_text(encoding="utf-8").splitlines()]
            game = next(item for item in game_rows if item["game_id"] == row["game_id"])
            board = validate_position_record(row, game)
            self.assertEqual(canonical_fen(board), row["fen"])
            self.assertTrue(result["run_metrics"]["peak_rss_mib"] is None or result["run_metrics"]["peak_rss_mib"] > 0)
            self.assertEqual(result["release"]["source_decision_id"], SOURCE_DECISION_ID)

            fake_engine = temp / "fake-stockfish-19"
            fake_engine.write_text(textwrap.dedent(f"""\
                #!{sys.executable}
                import sys
                import chess

                multipv = 1
                board = chess.Board()
                for raw in sys.stdin:
                    fields = raw.strip().split()
                    if not fields:
                        continue
                    command = fields[0]
                    if command == "uci":
                        print("id name Stockfish 19 test fixture")
                        print("id author M3 tests")
                        print("option name Threads type spin default 1 min 1 max 1")
                        print("option name Hash type spin default 16 min 1 max 256")
                        print("option name MultiPV type spin default 1 min 1 max 3")
                        print("option name UCI_Chess960 type check default false")
                        print("option name UCI_ShowWDL type check default false")
                        print("option name Clear Hash type button")
                        print("uciok", flush=True)
                    elif command == "setoption":
                        if "name" in fields and "value" in fields:
                            name = fields[fields.index("name") + 1]
                            value = fields[fields.index("value") + 1]
                            if name == "MultiPV":
                                multipv = int(value)
                    elif command == "isready":
                        print("readyok", flush=True)
                    elif command == "position":
                        if len(fields) > 1 and fields[1] == "fen":
                            fen_end = fields.index("moves") if "moves" in fields else len(fields)
                            board = chess.Board(" ".join(fields[2:fen_end]))
                            move_start = fen_end + 1 if "moves" in fields else len(fields)
                        else:
                            board = chess.Board()
                            move_start = fields.index("moves") + 1 if "moves" in fields else len(fields)
                        for uci in fields[move_start:]:
                            board.push_uci(uci)
                    elif command == "go":
                        moves = sorted(board.legal_moves, key=lambda move: move.uci())
                        for rank, move in enumerate(moves[:multipv], 1):
                            print(f"info depth 1 seldepth 1 multipv {{rank}} score cp 32 nodes 95 pv {{move.uci()}}")
                        print(f"bestmove {{moves[0].uci()}}", flush=True)
                    elif command == "quit":
                        break
            """), encoding="utf-8")
            fake_engine.chmod(0o755)
            license_path = temp / "fake-license.txt"
            license_path.write_text("Synthetic engine fixture; no redistribution.\n", encoding="utf-8")
            engine_sha = hashlib.sha256(fake_engine.read_bytes()).hexdigest()
            license_sha = hashlib.sha256(license_path.read_bytes()).hexdigest()
            teacher_dir = temp / "teacher"
            teacher_manifest = run_teacher(
                output, output / "games.jsonl", teacher_dir,
                engine_path=fake_engine, expected_engine_sha256=engine_sha,
                license_path=license_path, expected_license_sha256=license_sha,
                max_positions=2, sample_seed=9, nodes_per_position=500,
                multipv=3, threads=1, hash_mib=64, timeout_seconds=5,
                max_wall_seconds=60, authorization_id=AUTHORIZATION_ID,
                source_decision_id=SOURCE_DECISION_ID, confirm_write=True,
                code_revision="a" * 40, allow_synthetic_source_for_test=True,
            )
            teacher_verified = verify_teacher_run(
                teacher_dir, output, allow_synthetic_source_for_test=True,
            )
            self.assertEqual(teacher_manifest["positions_analyzed"], 2)
            self.assertEqual(teacher_verified["positions_analyzed"], 2)
            self.assertEqual(teacher_manifest["multipv_score_types"]["cp"], 6)

            invalid_engine = temp / "fake-stockfish-invalid-pv"
            invalid_script = fake_engine.read_text(encoding="utf-8")
            invalid_script = invalid_script.replace("multipv = 1\nboard =", "multipv = 1\ngo_count = 0\nboard =")
            invalid_script = invalid_script.replace(
                'elif command == "go":\n',
                'elif command == "go":\n        go_count += 1\n',
            ).replace(
                'pv {move.uci()}")',
                'pv {"a1a1" if go_count == 1 else move.uci()}")',
            )
            self.assertIn('"a1a1" if go_count == 1', invalid_script)
            self.assertNotEqual(invalid_script, fake_engine.read_text(encoding="utf-8"))
            invalid_engine.write_text(invalid_script, encoding="utf-8")
            invalid_engine.chmod(0o755)
            invalid_sha = hashlib.sha256(invalid_engine.read_bytes()).hexdigest()
            invalid_dir = temp / "teacher-invalid-pv"
            with self.assertRaisesRegex(TeacherError, "no successful position records"):
                run_teacher(
                    output, output / "games.jsonl", invalid_dir,
                    engine_path=invalid_engine, expected_engine_sha256=invalid_sha,
                    license_path=license_path, expected_license_sha256=license_sha,
                    max_positions=1, sample_seed=9, nodes_per_position=500,
                    multipv=3, threads=1, hash_mib=64, timeout_seconds=5,
                    max_wall_seconds=60, authorization_id=AUTHORIZATION_ID,
                    source_decision_id=SOURCE_DECISION_ID, confirm_write=True,
                    code_revision="a" * 40, allow_synthetic_source_for_test=True,
                )
            invalid_partial = json.loads((invalid_dir / "teacher.partial.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(invalid_partial["status"], "error")
            self.assertIn("no usable principal variation/root action", invalid_partial["reason"])
            self.assertTrue((invalid_dir / "failure.json").is_file())

            timeout_engine = temp / "fake-stockfish-timeout"
            timeout_script = fake_engine.read_text(encoding="utf-8").replace(
                "import chess\n\nmultipv = 1",
                "import chess\nimport time\n\nmultipv = 1",
            ).replace(
                '    elif command == "go":\n        moves = sorted(board.legal_moves, key=lambda move: move.uci())',
                '    elif command == "go":\n        time.sleep(3)\n        moves = sorted(board.legal_moves, key=lambda move: move.uci())',
            )
            self.assertIn("time.sleep(3)", timeout_script)
            timeout_engine.write_text(timeout_script, encoding="utf-8")
            timeout_engine.chmod(0o755)
            timeout_sha = hashlib.sha256(timeout_engine.read_bytes()).hexdigest()
            timeout_dir = temp / "teacher-timeout"
            with self.assertRaisesRegex(TeacherError, "no successful position records"):
                run_teacher(
                    output, output / "games.jsonl", timeout_dir,
                    engine_path=timeout_engine, expected_engine_sha256=timeout_sha,
                    license_path=license_path, expected_license_sha256=license_sha,
                    max_positions=1, sample_seed=9, nodes_per_position=500,
                    multipv=3, threads=1, hash_mib=64, timeout_seconds=0.5,
                    max_wall_seconds=60, authorization_id=AUTHORIZATION_ID,
                    source_decision_id=SOURCE_DECISION_ID, confirm_write=True,
                    code_revision="a" * 40, allow_synthetic_source_for_test=True,
                )
            self.assertTrue((timeout_dir / "teacher.partial.jsonl").is_file())
            self.assertTrue((timeout_dir / "failure.json").is_file())
            timeout_partial = json.loads((timeout_dir / "teacher.partial.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(timeout_partial["status"], "error")

            with self.assertRaisesRegex(TeacherError, "binary is missing"):
                run_teacher(
                    output, output / "games.jsonl", temp / "teacher-missing-engine",
                    engine_path=temp / "missing-stockfish", expected_engine_sha256="0" * 64,
                    license_path=license_path, expected_license_sha256=license_sha,
                    max_positions=1, sample_seed=9, nodes_per_position=500,
                    multipv=3, threads=1, hash_mib=64, timeout_seconds=5,
                    max_wall_seconds=60, authorization_id=AUTHORIZATION_ID,
                    source_decision_id=SOURCE_DECISION_ID, confirm_write=True,
                    code_revision="a" * 40, allow_synthetic_source_for_test=True,
                )

    def test_release_refuses_existing_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "release"
            target.mkdir()
            self.assertTrue(target.exists())


if __name__ == "__main__":
    unittest.main()
