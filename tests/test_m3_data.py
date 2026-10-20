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
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import chess
import chess.pgn

from videochess_rl.data.contracts import (
    assign_game_split, board_position_signature, canonical_fen, candidate_identity, config_identity,
    digest, normalized_game_identity, release_identity, replay_history_identity,
    sample_identity, source_identity, validate_game_record, validate_position_record,
)
from videochess_rl.data.export import ExportError, verify_release, write_batches
from videochess_rl.data.pgn import SourceLimitError, iter_pgn_games
from videochess_rl.data.pipeline import PipelineError, build_dataset
from videochess_rl.data.sampling import BottomKGroups, sample_positions
from videochess_rl.data.source import (
    SourceError, download_archive, hash_member, inspect_zip, validate_source_manifest,
)
from videochess_rl.data.split import SplitError, board_signature_owner, split_and_purge
from videochess_rl.data.stats import summarize_dataset
from videochess_rl.data.teacher import TeacherError, _cp_transform, _score_data, run_teacher, verify_teacher_run
from videochess_rl.data.cli import _resolve_engine_path
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


def pgn_for_moves(moves: list[str], result: str) -> str:
    game = chess.pgn.Game()
    game.headers.update({
        "Event": "Terminal semantics fixture", "Site": "local",
        "Date": "2026.01.01", "Round": "1", "White": "A", "Black": "B",
        "Result": result,
    })
    board = game.board()
    node = game
    for uci in moves:
        move = board.parse_uci(uci)
        node = node.add_variation(move)
        board.push(move)
    return game.accept(chess.pgn.StringExporter(headers=True, variations=False, comments=False)) + "\n"


def validation_game(record: dict) -> dict:
    game = dict(record)
    game["game_id"] = game.get("source_game_id") or "a" * 64
    game["record_id"] = game["game_id"]
    game["source_archive_sha256"] = "b" * 64
    game["source_member_name"] = game.get("source_member_name") or "games.pgn"
    game["source_member"] = game["source_member_name"]
    return game


def rewrite_release_file_manifest(release_dir: Path, relative_name: str) -> None:
    manifest_path = release_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target = release_dir / relative_name
    file_bytes = target.read_bytes()
    for item in manifest["outputs"]:
        if item["path"] == relative_name:
            item["bytes"] = len(file_bytes)
            item["sha256"] = hashlib.sha256(file_bytes).hexdigest()
            break
    else:
        raise AssertionError(f"release manifest has no {relative_name}")
    manifest["release_id"] = release_identity(
        manifest["source_archive_sha256"], manifest["schema_versions"],
        manifest["config_sha256"], manifest["code_revision"],
        manifest["split_assignment_sha256"],
        [[item["path"], item["bytes"], item["sha256"]] for item in manifest["outputs"]],
    )
    encoded = json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    manifest_path.write_bytes(encoded)
    (release_dir / "manifest.sha256").write_text(
        hashlib.sha256(encoded).hexdigest() + "  manifest.json\n", encoding="ascii",
    )


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
                sampler.observe(row)
            sampler.begin_selection()
            for row in rows:
                sampler.select(row)
            sampler.verify_selection_complete()
            return [row["normalized_game_sha256"] for row in sampler.selected_records()]
        self.assertEqual(selected(games), selected(list(reversed(games))))
        self.assertEqual(len(selected(games)), 7)

    def test_bottom_k_matches_full_information_oracle_after_late_conflicts(self) -> None:
        source, base_games = parsed_records(count=32, plies=20)
        seed, limit = 71, 9
        archive_hash = "b" * 64
        def oracle_rank(norm):
            payload = json.dumps({
                "domain": "videochess-game-sample/v1", "seed": seed,
                "normalized_game_sha256": norm,
            }, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
            return hashlib.sha256(payload).hexdigest()

        ranked = sorted(base_games, key=lambda row: (oracle_rank(row["normalized_game_sha256"]), row["normalized_game_sha256"]))
        late_conflict = ranked[0]
        ref_conflict_a, ref_conflict_b = ranked[limit + 2], ranked[limit + 3]
        rows = [dict(row) for row in base_games]
        duplicate = dict(late_conflict, source_game_id="c" * 64)
        rows.extend((dict(late_conflict, source_game_id="d" * 64), duplicate))
        rows.append(dict(late_conflict, pgn_result="1-0", source_game_id="e" * 64))
        shared_ref = "f" * 64
        for row in rows:
            if row["normalized_game_sha256"] in {
                ref_conflict_a["normalized_game_sha256"], ref_conflict_b["normalized_game_sha256"],
            }:
                row["source_game_ref_sha256"] = shared_ref

        def oracle(records):
            result_values = {}
            ref_groups = {}
            for row in records:
                norm = row["normalized_game_sha256"]
                result_values.setdefault(norm, set()).add(row["pgn_result"])
                ref = row.get("source_game_ref_sha256")
                if ref:
                    ref_groups.setdefault(ref, set()).add(norm)
            conflicted = {norm for norm, values in result_values.items() if len(values) > 1}
            for groups in ref_groups.values():
                if len(groups) > 1:
                    conflicted.update(groups)
            eligible = {
                norm for norm in result_values if norm not in conflicted
            }
            return set(sorted(
                eligible, key=lambda norm: (oracle_rank(norm), norm),
            )[:limit])

        expected = oracle(rows)
        permutations = [list(rows), list(reversed(rows))]
        rng = random.Random(2026)
        for _ in range(6):
            shuffled = list(rows)
            rng.shuffle(shuffled)
            permutations.append(shuffled)
        for order_index, order in enumerate(permutations):
            sampler = BottomKGroups(
                seed=seed, max_games=limit, source_id=source,
                archive_sha256=archive_hash, member_name="games.pgn",
            )
            for row in order:
                sampler.observe(row)
            sampler.begin_selection()
            for row in order:
                sampler.select(row)
            sampler.verify_selection_complete()
            actual = {row["normalized_game_sha256"] for row in sampler.selected_records()}
            with self.subTest(permutation=order_index):
                self.assertEqual(actual, expected)
                self.assertEqual(sampler.normalized_duplicate_observations, 3)
                self.assertEqual(sampler.normalized_duplicate_groups, 1)
                self.assertEqual(len(sampler.conflicting_source_refs), 1)
                self.assertNotIn(late_conflict["normalized_game_sha256"], actual)
                self.assertNotIn(ref_conflict_a["normalized_game_sha256"], actual)
                self.assertNotIn(ref_conflict_b["normalized_game_sha256"], actual)
                self.assertEqual(len(actual), limit)

    def test_bottom_k_tie_break_is_globally_lexicographic(self) -> None:
        source, games = parsed_records(count=8, plies=20)
        expected = sorted(row["normalized_game_sha256"] for row in games)[:3]
        selected = []
        for order in (games, list(reversed(games))):
            sampler = BottomKGroups(
                seed=3, max_games=3, source_id=source,
                archive_sha256="b" * 64, member_name="games.pgn",
            )
            for row in order:
                sampler.observe(row)
            sampler.begin_selection()
            # Force equal primary ranks to exercise the deterministic
            # secondary ordering and worst-item eviction in the heap.
            with patch("videochess_rl.data.sampling.game_sample_key", return_value="0" * 64):
                for row in order:
                    sampler.select(row)
            sampler.verify_selection_complete()
            selected.append(sorted(row["normalized_game_sha256"] for row in sampler.selected_records()))
        self.assertEqual(selected, [expected, expected])

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
            sampler.observe(row)
        sampler.begin_selection()
        for row in games:
            sampler.select(row)
        sampler.verify_selection_complete()
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

    def test_automatic_terminal_results_match_board_outcome_but_external_results_remain_valid(self) -> None:
        white_mate = ["e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6", "h5f7"]
        black_mate = ["f2f3", "e7e5", "g2g4", "d8h4"]
        for label, moves, correct, wrong in (
            ("white_mates", white_mate, "1-0", "0-1"),
            ("black_mates", black_mate, "0-1", "1-0"),
        ):
            with self.subTest(label=label, result="correct"):
                parsed = parse_text(pgn_for_moves(moves, correct), max_games=1)[0][1]
                self.assertEqual(parsed.status, "accepted")
                game = validation_game(parsed.game)
                self.assertEqual(game["board_termination"]["termination"], "CHECKMATE")
                validate_game_record(game)
            with self.subTest(label=label, result="contradictory"):
                parsed = parse_text(pgn_for_moves(moves, wrong), max_games=1)[0][1]
                self.assertEqual(parsed.status, "quarantined")
                self.assertEqual(parsed.reason_code, "pgn_terminal_result_mismatch")

        cycle = ["g1f3", "g8f6", "f3g1", "f6g8"]
        automatic_draw = cycle * 4
        correct_draw = parse_text(pgn_for_moves(automatic_draw, "1/2-1/2"), max_games=1)[0][1]
        self.assertEqual(correct_draw.status, "accepted")
        draw_game = validation_game(correct_draw.game)
        self.assertEqual(draw_game["board_termination"]["termination"], "FIVEFOLD_REPETITION")
        validate_game_record(draw_game)
        wrong_draw = parse_text(pgn_for_moves(automatic_draw, "1-0"), max_games=1)[0][1]
        self.assertEqual(wrong_draw.reason_code, "pgn_terminal_result_mismatch")

        resignation = parse_text(pgn_for_moves(["e2e4", "e7e5"], "1-0"), max_games=1)[0][1]
        self.assertEqual(resignation.status, "accepted")
        resignation_game = validation_game(resignation.game)
        self.assertIsNone(resignation_game["board_termination"])
        validate_game_record(resignation_game)

    def test_game_validator_checks_result_and_board_termination_independently(self) -> None:
        moves = ["f2f3", "e7e5", "g2g4", "d8h4"]
        valid = validation_game(parse_text(pgn_for_moves(moves, "0-1"), max_games=1)[0][1].game)
        contradictory = dict(valid, pgn_result="1-0", result="1-0", white_result="win")
        with self.assertRaisesRegex(ValueError, "contradicts the reconstructed automatic terminal outcome"):
            validate_game_record(contradictory)
        missing_terminal = dict(valid)
        missing_terminal.pop("board_termination")
        with self.assertRaisesRegex(ValueError, "board_termination metadata"):
            validate_game_record(missing_terminal)
        nonterminal = validation_game(parse_text(pgn_for_moves(["e2e4"], "1-0"), max_games=1)[0][1].game)
        nonterminal["board_termination"] = {"termination": "CHECKMATE", "winner": "white"}
        with self.assertRaisesRegex(ValueError, "board_termination metadata"):
            validate_game_record(nonterminal)

    def test_position_result_perspectives_are_derived_from_parent_game_and_board(self) -> None:
        _, parsed = parsed_records(count=1, plies=8)
        base = validation_game(parsed[0])
        for result, white_label in (("1-0", "win"), ("0-1", "loss"), ("1/2-1/2", "draw")):
            game = dict(base, pgn_result=result, result=result, white_result=white_label)
            rows_all = sample_positions(
                [game], source_id=game["source_id"], seed=2,
                max_positions_per_game=8, max_positions=8,
            )
            rows = [next(row for row in rows_all if row["side_to_move"] == side) for side in ("white", "black")]
            for row in rows:
                validate_position_record(row, game)
                expected_side = white_label if row["side_to_move"] == "white" else {
                    "win": "loss", "loss": "win", "draw": "draw",
                }[white_label]
                self.assertEqual(row["side_to_move_result"], expected_side)
                for field in ("pgn_result", "white_result", "side_to_move_result", "result_white", "result_to_move"):
                    corrupted = dict(row)
                    if field == "pgn_result":
                        corrupted[field] = "0-1" if result != "0-1" else "1-0"
                    elif field == "white_result":
                        corrupted[field] = "loss" if white_label != "loss" else "win"
                    elif field == "side_to_move_result":
                        corrupted[field] = "loss" if expected_side != "loss" else "win"
                    elif field == "result_white":
                        corrupted[field] = "0-1" if result != "0-1" else "1-0"
                    else:
                        corrupted[field] = 1 if row[field] != 1 else -1
                    with self.subTest(result=result, side=row["side_to_move"], field=field):
                        with self.assertRaisesRegex(ValueError, "game-result perspective"):
                            validate_position_record(corrupted, game)

        game = dict(base, pgn_result="1-0", result="1-0", white_result="win")
        row = next(
            item for item in sample_positions(
                [game], source_id=game["source_id"], seed=2,
                max_positions_per_game=game["ply_count"], max_positions=game["ply_count"],
            ) if item["side_to_move"] == "white"
        )
        self.assertEqual(row["side_to_move_result"], "win")
        row["side_to_move_result"] = "loss"
        row["result_to_move"] = -1
        with self.assertRaisesRegex(ValueError, "game-result perspective"):
            validate_position_record(row, game)

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
                "side_to_move": "white", "white_result": "draw", "pgn_result": "1/2-1/2",
                "side_to_move_result": "draw", "ply_index": index,
                "split": None,
            })
        kept, manifest = split_and_purge(games, positions, seed=22, min_holdout_positions=1)
        self.assertEqual(len(kept), len(positions))
        self.assertEqual(manifest["holdout_warnings"], [])
        self.assertEqual(manifest["board_signatures_cross_split_after"], 0)
        assignments = dict(manifest["game_group_assignments"])
        self.assertTrue(all(row["split"] == assignments[row["normalized_game_sha256"]] for row in kept))
        shared = "f" * 64
        collapsed_positions = [dict(row, board_position_signature=shared) for row in positions]
        with self.assertRaises(SplitError) as caught:
            split_and_purge(games, collapsed_positions, seed=22, min_holdout_positions=1)
        self.assertIsNotNone(caught.exception.manifest)
        self.assertGreater(caught.exception.manifest["purged_candidate_count"], 0)

    def test_holdout_retention_warning_is_retained_without_rejecting_a_valid_release(self) -> None:
        seed = 73
        groups: dict[str, list[str]] = {name: [] for name in ("train", "validation", "test")}
        index = 0
        while min(map(len, groups.values())) < 10:
            normalized = hashlib.sha256(f"retention-game-{index}".encode()).hexdigest()
            groups[assign_game_split(seed, normalized)].append(normalized)
            index += 1
        shared = next(
            hashlib.sha256(f"shared-board-{candidate}".encode()).hexdigest()
            for candidate in range(1000)
            if board_signature_owner(seed, hashlib.sha256(f"shared-board-{candidate}".encode()).hexdigest(), {"train", "validation"}) == "train"
        )
        games = []
        positions = []
        for split_name, normalized_groups in groups.items():
            for offset, normalized in enumerate(normalized_groups[:10]):
                game_id = hashlib.sha256(f"retention-source-{normalized}".encode()).hexdigest()
                games.append({"game_id": game_id, "normalized_game_sha256": normalized})
                signature = shared if split_name in {"train", "validation"} and offset < 4 else hashlib.sha256(f"unique-{normalized}".encode()).hexdigest()
                positions.append({
                    "sample_id": hashlib.sha256(f"retention-sample-{normalized}".encode()).hexdigest(),
                    "game_id": game_id, "normalized_game_sha256": normalized,
                    "board_position_signature": signature,
                    "history_state_id": hashlib.sha256(f"retention-history-{normalized}".encode()).hexdigest(),
                    "legal_moves_uci": ["e2e4", "d2d4"], "candidate_count": 2,
                    "played_move_uci": "e2e4", "side_to_move": "white",
                    "white_result": "draw", "pgn_result": "1/2-1/2",
                    "side_to_move_result": "draw", "ply_index": 0, "split": None,
                })
        kept, manifest = split_and_purge(
            games, positions, seed=seed, min_holdout_positions=5,
            min_holdout_retention=0.5,
        )
        self.assertTrue(manifest["release_valid"])
        self.assertEqual(manifest["position_retention"]["validation"], 0.6)
        self.assertGreaterEqual(manifest["position_retention"]["validation"], 0.5)
        self.assertEqual(len(manifest["holdout_warnings"]), 1)
        self.assertIn("validation", manifest["holdout_warnings"][0])
        self.assertEqual(len(kept), sum(manifest["position_counts_after_purge"].values()))

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

    def test_teacher_cli_engine_paths_are_portable_and_unambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository_engine = root / "bin" / "stockfish"
            repository_engine.parent.mkdir()
            repository_engine.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            repository_engine.chmod(0o755)
            absolute = root / "absolute-engine"
            absolute.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            absolute.chmod(0o755)
            self.assertEqual(_resolve_engine_path(absolute, root), absolute.resolve())
            self.assertEqual(_resolve_engine_path("bin/stockfish", root), repository_engine.resolve())

            path_dir = root / "path-bin"
            path_dir.mkdir()
            path_engine = path_dir / "stockfish"
            path_engine.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            path_engine.chmod(0o755)
            self.assertEqual(_resolve_engine_path("stockfish", root, search_path=str(path_dir)), path_engine.resolve())
            with self.assertRaisesRegex(ValueError, "not found on PATH"):
                _resolve_engine_path("missing-engine", root, search_path=str(path_dir))
            with self.assertRaisesRegex(ValueError, "ambiguous on PATH"):
                _resolve_engine_path("stockfish", root, search_path=os.pathsep.join((str(path_dir), str(repository_engine.parent))))
            with self.assertRaisesRegex(ValueError, "escapes the repository root"):
                _resolve_engine_path("../outside/stockfish", root)

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

    def test_rating_metadata_reports_zero_count_categories(self) -> None:
        game = {
            "game_id": "a" * 64, "moves_uci": ["e2e4"], "ply_count": 1,
            "white_elo": 2400, "black_elo": 2300,
            "time_control": "300+0", "date": "2026.01.01", "header_keys": [],
        }
        source = {
            "source_id": "test-source", "publisher": "synthetic",
            "archive_sha256": "b" * 64, "archive_bytes": 1,
            "member": {"name": "games.pgn"}, "member_sha256": "c" * 64,
            "member_bytes": 1,
        }
        summary = summarize_dataset(
            [game], [], [], {}, {}, sampling={}, resources={},
            config_sha256="d" * 64, source_manifest=source,
        )
        self.assertEqual(summary["rating_metadata"], {
            "one_or_more_missing": 0, "both_present": 1,
        })

    def test_synthetic_end_to_end_release_is_reconstructible_and_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            source_id = source_identity("test", "https://example.invalid/", "synthetic")
            texts = [pgn_for_moves(["e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6", "h5f7"], "1-0")]
            texts.extend(make_game(index, plies=20)[0] for index in range(1, 120))
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

            split_path = output / "split.json"
            stats_path = output / "stats.json"
            original_split_bytes = split_path.read_bytes()
            original_stats_bytes = stats_path.read_bytes()
            split_doc = json.loads(original_split_bytes)
            stats_doc = json.loads(original_stats_bytes)
            split_doc.pop("holdout_warnings", None)
            stats_doc["splits"] = split_doc
            split_path.write_text(json.dumps(split_doc, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            stats_path.write_text(json.dumps(stats_doc, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            rewrite_release_file_manifest(output, "split.json")
            rewrite_release_file_manifest(output, "stats.json")
            with self.assertRaisesRegex(ExportError, "holdout retention warnings"):
                verify_release(output, allow_synthetic_source_for_test=True)
            split_path.write_bytes(original_split_bytes)
            stats_path.write_bytes(original_stats_bytes)
            rewrite_release_file_manifest(output, "split.json")
            rewrite_release_file_manifest(output, "stats.json")
            self.assertEqual(verify_release(output, allow_synthetic_source_for_test=True), verified)

            stats_doc = json.loads(original_stats_bytes)
            stats_doc["distribution_shift_after_purge_fraction"]["side_to_move"]["white"] = 0.123
            stats_path.write_text(json.dumps(stats_doc, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            rewrite_release_file_manifest(output, "stats.json")
            with self.assertRaisesRegex(ExportError, "distribution shifts"):
                verify_release(output, allow_synthetic_source_for_test=True)
            stats_path.write_bytes(original_stats_bytes)
            rewrite_release_file_manifest(output, "stats.json")
            self.assertEqual(verify_release(output, allow_synthetic_source_for_test=True), verified)

            stats_doc = json.loads(original_stats_bytes)
            ply_band = next(iter(stats_doc["positions_by_ply_band_before_purge"]))
            stats_doc["positions_by_ply_band_before_purge"][ply_band] += 1
            stats_path.write_text(json.dumps(stats_doc, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            rewrite_release_file_manifest(output, "stats.json")
            with self.assertRaisesRegex(ExportError, "dataset statistics do not recompute"):
                verify_release(output, allow_synthetic_source_for_test=True)
            stats_path.write_bytes(original_stats_bytes)
            rewrite_release_file_manifest(output, "stats.json")
            self.assertEqual(verify_release(output, allow_synthetic_source_for_test=True), verified)

            expired_config = dict(config, max_elapsed_seconds=1)
            expired_config_path = temp / "expired-config.json"
            expired_config_path.write_text(json.dumps({"dataset": expired_config}), encoding="utf-8")
            expired_output = temp / "releases" / "expired-release"
            from videochess_rl.data import pipeline as pipeline_module
            original_summary = pipeline_module.summarize_dataset

            def delayed_summary(*args, **kwargs):
                time.sleep(1.05)
                return original_summary(*args, **kwargs)

            with patch("videochess_rl.data.pipeline.summarize_dataset", side_effect=delayed_summary):
                with self.assertRaisesRegex(PipelineError, "max elapsed seconds exceeded during quality statistics"):
                    build_dataset(
                        archive_path, source_path, expired_config_path, expired_output,
                        run_id="synthetic-run-over-wall-cap", repository_root=ROOT,
                        source_decision_path=SOURCE_DECISION, authorization_path=AUTHORIZATION,
                        confirm_write=True, allow_synthetic_source_for_test=True,
                    )
            self.assertFalse(expired_output.exists())

            original_release_bytes = {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in output.iterdir() if path.is_file()
            }
            for resume in (False, True):
                with self.subTest(overwrite_resume=resume):
                    with self.assertRaisesRegex(PipelineError, "refusing to overwrite existing release"):
                        build_dataset(
                            archive_path, source_path, config_path, output,
                            run_id="overwrite-protection-regression", repository_root=ROOT,
                            source_decision_path=SOURCE_DECISION, authorization_path=AUTHORIZATION,
                            confirm_write=True, resume=resume, allow_synthetic_source_for_test=True,
                        )
            self.assertEqual(original_release_bytes, {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in output.iterdir() if path.is_file()
            })
            self.assertFalse((output.parent.parent / "runs" / "overwrite-protection-regression.staging").exists())
            self.assertFalse((output.parent / f".{output.name}.overwrite-protection-regression.staging").exists())
            dangling_target = output.parent / "dangling-release-link"
            dangling_target.symlink_to(temp / "missing-target")
            with self.assertRaisesRegex(PipelineError, "refusing to overwrite existing release"):
                build_dataset(
                    archive_path, source_path, config_path, dangling_target,
                    run_id="dangling-symlink-protection", repository_root=ROOT,
                    source_decision_path=SOURCE_DECISION, authorization_path=AUTHORIZATION,
                    confirm_write=True, allow_synthetic_source_for_test=True,
                )
            self.assertTrue(dangling_target.is_symlink())

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
            timeout_pid_file = temp / "timeout-engine.pid"
            timeout_script = fake_engine.read_text(encoding="utf-8").replace(
                "import chess\n\nmultipv = 1",
                "import chess\nimport time\nimport os\n\nmultipv = 1",
            ).replace(
                '    elif command == "go":\n        moves = sorted(board.legal_moves, key=lambda move: move.uci())',
                f'    elif command == "go":\n        open({str(timeout_pid_file)!r}, "w").write(str(os.getpid()))\n        time.sleep(3)\n        moves = sorted(board.legal_moves, key=lambda move: move.uci())',
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
            timeout_pid = int(timeout_pid_file.read_text(encoding="utf-8"))
            with self.assertRaises(ProcessLookupError):
                os.kill(timeout_pid, 0)

            missing_bestmove_engine = temp / "fake-stockfish-no-bestmove"
            missing_bestmove_pid = temp / "no-bestmove-engine.pid"
            missing_bestmove_script = fake_engine.read_text(encoding="utf-8").replace(
                "import chess\n\nmultipv = 1",
                "import chess\nimport os\n\nmultipv = 1",
            ).replace(
                '    elif command == "go":\n        moves = sorted(board.legal_moves, key=lambda move: move.uci())',
                f'    elif command == "go":\n        open({str(missing_bestmove_pid)!r}, "w").write(str(os.getpid()))\n        moves = sorted(board.legal_moves, key=lambda move: move.uci())',
            ).replace(
                'print(f"bestmove {moves[0].uci()}", flush=True)',
                'print("info string intentionally omitted bestmove", flush=True)',
            )
            self.assertIn("intentionally omitted bestmove", missing_bestmove_script)
            self.assertNotIn('print(f"bestmove', missing_bestmove_script)
            missing_bestmove_engine.write_text(missing_bestmove_script, encoding="utf-8")
            missing_bestmove_engine.chmod(0o755)
            missing_bestmove_sha = hashlib.sha256(missing_bestmove_engine.read_bytes()).hexdigest()
            missing_bestmove_dir = temp / "teacher-missing-bestmove"
            with self.assertRaisesRegex(TeacherError, "no successful position records"):
                run_teacher(
                    output, output / "games.jsonl", missing_bestmove_dir,
                    engine_path=missing_bestmove_engine, expected_engine_sha256=missing_bestmove_sha,
                    license_path=license_path, expected_license_sha256=license_sha,
                    max_positions=1, sample_seed=9, nodes_per_position=500,
                    multipv=3, threads=1, hash_mib=64, timeout_seconds=0.5,
                    max_wall_seconds=60, authorization_id=AUTHORIZATION_ID,
                    source_decision_id=SOURCE_DECISION_ID, confirm_write=True,
                    code_revision="a" * 40, allow_synthetic_source_for_test=True,
                )
            missing_bestmove_row = json.loads(
                (missing_bestmove_dir / "teacher.partial.jsonl").read_text(encoding="utf-8").splitlines()[0]
            )
            self.assertEqual(missing_bestmove_row["status"], "error")
            self.assertIn("watchdog", missing_bestmove_row["reason"])
            missing_bestmove_process = int(missing_bestmove_pid.read_text(encoding="utf-8"))
            with self.assertRaises(ProcessLookupError):
                os.kill(missing_bestmove_process, 0)

            bounded_dir = temp / "teacher-total-budget"
            timeout_pid_file.unlink(missing_ok=True)
            bounded_started = time.monotonic()
            with self.assertRaisesRegex(TeacherError, "no successful position records"):
                run_teacher(
                    output, output / "games.jsonl", bounded_dir,
                    engine_path=timeout_engine, expected_engine_sha256=timeout_sha,
                    license_path=license_path, expected_license_sha256=license_sha,
                    max_positions=1, sample_seed=9, nodes_per_position=500,
                    multipv=3, threads=1, hash_mib=64, timeout_seconds=5,
                    max_wall_seconds=1, authorization_id=AUTHORIZATION_ID,
                    source_decision_id=SOURCE_DECISION_ID, confirm_write=True,
                    code_revision="a" * 40, allow_synthetic_source_for_test=True,
                )
            bounded_elapsed = time.monotonic() - bounded_started
            self.assertLess(bounded_elapsed, 3.5)
            bounded_partial = json.loads((bounded_dir / "teacher.partial.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(bounded_partial["status"], "error")
            if timeout_pid_file.exists():
                bounded_pid = int(timeout_pid_file.read_text(encoding="utf-8"))
                with self.assertRaises(ProcessLookupError):
                    os.kill(bounded_pid, 0)

            for invalid_timeout, invalid_wall in (
                (0.0, 10), (-1.0, 10), (0.0001, 10), (float("nan"), 10), (float("inf"), 10),
                (1.0, 0), (1.0, -1), (1.0, float("nan")), (1.0, float("inf")),
            ):
                with self.subTest(invalid_timeout=invalid_timeout, invalid_wall=invalid_wall):
                    with self.assertRaisesRegex(TeacherError, "timeout|wall-time budget"):
                        run_teacher(
                            output, output / "games.jsonl", temp / f"invalid-time-{len(list(temp.iterdir()))}",
                            engine_path=fake_engine, expected_engine_sha256=engine_sha,
                            license_path=license_path, expected_license_sha256=license_sha,
                            max_positions=1, sample_seed=9, nodes_per_position=500,
                            multipv=3, threads=1, hash_mib=64, timeout_seconds=invalid_timeout,
                            max_wall_seconds=invalid_wall, authorization_id=AUTHORIZATION_ID,
                            source_decision_id=SOURCE_DECISION_ID, confirm_write=True,
                            code_revision="a" * 40, allow_synthetic_source_for_test=True,
                        )

            partial_engine = temp / "fake-stockfish-partial"
            partial_script = timeout_script.replace("multipv = 1\nboard =", "multipv = 1\ngo_count = 0\nboard =")
            partial_script = partial_script.replace(
                f'    elif command == "go":\n        open({str(timeout_pid_file)!r}, "w").write(str(os.getpid()))\n        time.sleep(3)',
                f'    elif command == "go":\n        go_count += 1\n        open({str(timeout_pid_file)!r}, "w").write(str(os.getpid()))\n        if go_count > 1:\n            time.sleep(3)',
            )
            self.assertIn("go_count > 1", partial_script)
            partial_engine.write_text(partial_script, encoding="utf-8")
            partial_engine.chmod(0o755)
            partial_sha = hashlib.sha256(partial_engine.read_bytes()).hexdigest()
            partial_dir = temp / "teacher-partial-timeout"
            partial_manifest = run_teacher(
                output, output / "games.jsonl", partial_dir,
                engine_path=partial_engine, expected_engine_sha256=partial_sha,
                license_path=license_path, expected_license_sha256=license_sha,
                max_positions=3, sample_seed=9, nodes_per_position=500,
                multipv=3, threads=1, hash_mib=64, timeout_seconds=0.4,
                max_wall_seconds=30, authorization_id=AUTHORIZATION_ID,
                source_decision_id=SOURCE_DECISION_ID, confirm_write=True,
                code_revision="a" * 40, allow_synthetic_source_for_test=True,
            )
            partial_verified = verify_teacher_run(partial_dir, output, allow_synthetic_source_for_test=True)
            self.assertEqual(partial_manifest["status"], "partial")
            self.assertEqual(partial_manifest["positions_analyzed"], 1)
            self.assertEqual(partial_verified["positions_analyzed"], 1)
            partial_rows = [json.loads(line) for line in (partial_dir / "teacher.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["status"] for row in partial_rows], ["ok", "error", "not_attempted"])
            timeout_pid = int(timeout_pid_file.read_text(encoding="utf-8"))
            with self.assertRaises(ProcessLookupError):
                os.kill(timeout_pid, 0)

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

            original_positions = (output / "positions.jsonl").read_bytes()
            position_rows = [json.loads(line) for line in original_positions.decode("utf-8").splitlines()]
            position_rows[0]["pgn_result"] = "0-1" if position_rows[0]["pgn_result"] != "0-1" else "1-0"
            changed_positions = b"".join(
                json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
                for row in position_rows
            )
            (output / "positions.jsonl").write_bytes(changed_positions)
            rewrite_release_file_manifest(output, "positions.jsonl")
            with self.assertRaisesRegex(ValueError, "game-result perspective"):
                verify_release(output, allow_synthetic_source_for_test=True)
            (output / "positions.jsonl").write_bytes(original_positions)
            rewrite_release_file_manifest(output, "positions.jsonl")
            self.assertEqual(verify_release(output, allow_synthetic_source_for_test=True), verified)

            original_games = (output / "games.jsonl").read_bytes()
            game_rows = [json.loads(line) for line in original_games.decode("utf-8").splitlines()]
            terminal_game = next(row for row in game_rows if row["board_termination"] is not None)
            terminal_game["pgn_result"] = "0-1"
            terminal_game["result"] = "0-1"
            terminal_game["white_result"] = "loss"
            changed_games = b"".join(
                json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
                for row in game_rows
            )
            (output / "games.jsonl").write_bytes(changed_games)
            rewrite_release_file_manifest(output, "games.jsonl")
            with self.assertRaisesRegex(ValueError, "contradicts the reconstructed automatic terminal outcome"):
                verify_release(output, allow_synthetic_source_for_test=True)
            (output / "games.jsonl").write_bytes(original_games)
            rewrite_release_file_manifest(output, "games.jsonl")
            self.assertEqual(verify_release(output, allow_synthetic_source_for_test=True), verified)

if __name__ == "__main__":
    unittest.main()
