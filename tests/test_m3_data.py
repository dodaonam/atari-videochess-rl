"""Synthetic and bounded regressions for the M3 data pipeline."""

from __future__ import annotations

import hashlib
import io
import json
import os
import random
import shutil
import sys
import tempfile
import textwrap
import time
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import chess
import chess.pgn
import videochess_rl.data.teacher as teacher_module

from videochess_rl.data.contracts import (
    assign_game_split, board_position_signature, canonical_fen, candidate_identity, config_identity,
    digest, normalized_game_identity, release_identity, replay_history_identity,
    sample_identity, source_identity, validate_game_record, validate_position_record,
)
from videochess_rl.data.export import ExportError, verify_release, write_batches
from videochess_rl.data.pgn import SourceLimitError, iter_pgn_games
from videochess_rl.data.pipeline import PipelineError, _validate_config, build_dataset
from videochess_rl.data.sampling import BottomKGroups, sample_positions
from videochess_rl.data.source import (
    SourceError, download_archive, hash_member, inspect_zip, validate_source_manifest,
)
from videochess_rl.data.split import SplitError, board_signature_owner, split_and_purge
from videochess_rl.data.stats import summarize_dataset
from videochess_rl.data.teacher import (
    TeacherError, _cp_transform, _score_data, _wdl_data, run_teacher, verify_teacher_run,
)
from videochess_rl.data import cli as cli_module
from videochess_rl.data import split as split_module
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
    if relative_name == "config.json":
        config_doc = json.loads(target.read_text(encoding="utf-8"))
        config_payload = dict(config_doc)
        config_payload.pop("config_sha256", None)
        config_doc["config_sha256"] = config_identity(config_payload)
        target.write_text(
            json.dumps(config_doc, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        manifest["config_sha256"] = config_doc["config_sha256"]
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


def rewrite_teacher_rows(teacher_dir: Path, rows: list[dict]) -> None:
    data = b"".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
        for row in rows
    )
    (teacher_dir / "teacher.jsonl").write_bytes(data)
    manifest_path = teacher_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["results"]["bytes"] = len(data)
    manifest["results"]["sha256"] = hashlib.sha256(data).hexdigest()
    encoded = json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    manifest_path.write_bytes(encoded)
    (teacher_dir / "manifest.sha256").write_text(
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


def build_synthetic_release(temp: Path, *, max_positions: int = 200) -> Path:
    """Build a small source-backed release for adversarial verifier tests."""
    source_id = source_identity("test", "https://example.invalid/", "synthetic")
    texts = [pgn_for_moves(
        ["e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6", "h5f7"], "1-0",
    )]
    texts.extend(make_game(index, plies=20)[0] for index in range(1, 120))
    archive_path = temp / "synthetic.zip"
    member_sha, member_bytes = pgn_zip(archive_path, "\n".join(texts))
    archive_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    inspected = inspect_zip(
        archive_path, max_archive_bytes=1_000_000,
        max_member_bytes=1_000_000, max_total_uncompressed_bytes=1_000_000,
    )
    source_manifest = {
        "schema": "videochess-source-manifest/1.0", "source_id": source_id,
        "test_fixture": True, "publisher": "synthetic test fixture",
        "archive_sha256": archive_sha, "archive_bytes": archive_path.stat().st_size,
        "archive_path": archive_path.name, "source_decision_id": SOURCE_DECISION_ID,
        "authorization_id": AUTHORIZATION_ID, "license_status": RIGHTS_STATUS,
        "member": inspected["member"], "member_name": "games.pgn",
        "member_sha256": member_sha, "member_bytes": member_bytes,
    }
    source_path = temp / "source.json"
    source_path.write_text(json.dumps(source_manifest), encoding="utf-8")
    config = {
        "schema_version": "videochess-dataset/1.0", "sampling_mode": "source_window",
        "seed": 42, "sampling_seed": 43, "split_seed": 44,
        "max_games": 120, "max_input_games_seen": 200,
        "max_positions": max_positions, "max_positions_per_game": 2,
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
    build_dataset(
        archive_path, source_path, config_path, output,
        run_id="synthetic-run-001", repository_root=ROOT,
        source_decision_path=SOURCE_DECISION, authorization_path=AUTHORIZATION,
        confirm_write=True, allow_synthetic_source_for_test=True,
    )
    return output


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

    def test_holdout_retention_policy_cannot_be_lowered_by_config_or_split_call(self) -> None:
        base = {
            "sampling_mode": "bottom_k", "seed": 1, "sampling_seed": 2, "split_seed": 3,
            "max_games": 1, "max_input_games_seen": 2, "max_positions": 1,
            "max_positions_per_game": 1, "min_holdout_positions": 1,
            "max_archive_bytes": 1, "max_member_bytes": 1,
            "max_total_decompressed_bytes": 1, "max_output_bytes": 1,
            "max_elapsed_seconds": 1, "max_workers": 1, "memory_mib": 128,
            "max_game_bytes": 1, "max_header_bytes": 1,
            "max_header_value_bytes": 1, "max_comment_bytes": 1, "batch_size": 1,
        }
        _validate_config(base)  # Omitted optional setting means the documented 50% minimum.
        for threshold in (5000, 6000, 10000):
            with self.subTest(threshold=threshold):
                _validate_config(dict(base, min_holdout_retention_basis_points=threshold))
        for threshold in (0, -1, 4999, 10001, True, False, 5000.0, "5000", None):
            with self.subTest(invalid_threshold=threshold):
                with self.assertRaisesRegex(PipelineError, "min_holdout_retention_basis_points"):
                    _validate_config(dict(base, min_holdout_retention_basis_points=threshold))
        with self.assertRaisesRegex(PipelineError, "min_holdout_positions"):
            _validate_config(dict(base, min_holdout_positions=True))

        seed = 91
        games = []
        positions = []
        present: set[str] = set()
        index = 0
        while len(present) < 3:
            normalized = hashlib.sha256(f"retention-policy-game-{index}".encode()).hexdigest()
            split_name = assign_game_split(seed, normalized)
            if split_name not in present:
                game_id = hashlib.sha256(f"retention-policy-source-{normalized}".encode()).hexdigest()
                games.append({"game_id": game_id, "normalized_game_sha256": normalized})
                positions.append({
                    "sample_id": hashlib.sha256(f"retention-policy-sample-{normalized}".encode()).hexdigest(),
                    "game_id": game_id, "normalized_game_sha256": normalized,
                    "board_position_signature": hashlib.sha256(f"retention-policy-board-{normalized}".encode()).hexdigest(),
                    "history_state_id": hashlib.sha256(f"retention-policy-history-{normalized}".encode()).hexdigest(),
                    "legal_moves_uci": ["e2e4"], "candidate_count": 1,
                    "played_move_uci": "e2e4", "side_to_move": "white",
                    "white_result": "draw", "pgn_result": "1/2-1/2",
                    "side_to_move_result": "draw", "ply_index": 0, "split": None,
                })
                present.add(split_name)
            index += 1
        _, retained = split_and_purge(
            games, positions, seed=seed, min_holdout_positions=1,
            min_holdout_retention=0.75,
        )
        self.assertEqual(retained["holdout_minimum_retention"], 0.75)
        for threshold in (0, -0.1, 0.4999, 1.0001, float("nan"), float("inf"), True, "0.5"):
            with self.subTest(invalid_split_threshold=threshold):
                with self.assertRaisesRegex(ValueError, "holdout"):
                    split_and_purge(
                        [], [], seed=seed, min_holdout_positions=1,
                        min_holdout_retention=threshold,
                    )

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

    def test_teacher_cli_returns_nonzero_for_partial_and_preserves_partial_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            engine = temp / "stockfish"
            engine.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            engine.chmod(0o755)
            license_path = temp / "license.txt"
            license_path.write_text("fixture license\n", encoding="utf-8")
            engine_sha = hashlib.sha256(engine.read_bytes()).hexdigest()
            license_sha = hashlib.sha256(license_path.read_bytes()).hexdigest()

            def partial_run(*args, **kwargs):
                output_dir = Path(args[2])
                output_dir.mkdir(parents=True)
                (output_dir / "teacher.partial.jsonl").write_text('{"status":"ok"}\n', encoding="utf-8")
                return {"status": "partial", "positions_selected": 2, "positions_analyzed": 1}

            common = [
                "teacher", "--release", str(temp / "release"), "--engine", str(engine),
                "--engine-sha256", engine_sha, "--license", str(license_path),
                "--license-sha256", license_sha, "--max-positions", "2", "--confirm-write",
            ]
            partial_output = temp / "partial-run"
            stdout = io.StringIO()
            with (
                patch.object(cli_module, "repository_root", return_value=ROOT),
                patch.object(cli_module, "_set_memory_limit"),
                patch.object(cli_module, "run_teacher", side_effect=partial_run),
                patch("sys.stdout", stdout),
            ):
                partial_exit = cli_module.main(common + ["--output", str(partial_output)])
            self.assertEqual(partial_exit, 3)
            self.assertTrue((partial_output / "teacher.partial.jsonl").is_file())
            self.assertEqual(json.loads(stdout.getvalue())["status"], "partial")

            stdout = io.StringIO()
            with (
                patch.object(cli_module, "repository_root", return_value=ROOT),
                patch.object(cli_module, "_set_memory_limit"),
                patch.object(cli_module, "run_teacher", return_value={"status": "complete", "positions_analyzed": 2}),
                patch("sys.stdout", stdout),
            ):
                complete_exit = cli_module.main(common + ["--output", str(temp / "complete-run")])
            self.assertEqual(complete_exit, 0)
            self.assertEqual(json.loads(stdout.getvalue())["status"], "complete")

            with (
                patch.object(cli_module, "repository_root", return_value=ROOT),
                patch.object(cli_module, "_set_memory_limit"),
                patch.object(cli_module, "run_teacher", return_value={"status": "error"}),
                patch("sys.stdout", io.StringIO()),
            ):
                with self.assertRaisesRegex(TeacherError, "unsupported final status"):
                    cli_module.command_teacher(cli_module.parser().parse_args(common + ["--output", str(temp / "bad-status")]))

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
        white_wdl = chess.engine.PovWdl(chess.engine.Wdl(700, 200, 100), chess.WHITE)
        self.assertEqual(
            _wdl_data({"wdl": white_wdl}, chess.WHITE),
            ({"wins": 700, "draws": 200, "losses": 100}, {"wins": 700, "draws": 200, "losses": 100}),
        )
        self.assertEqual(
            _wdl_data({"wdl": white_wdl}, chess.BLACK),
            ({"wins": 100, "draws": 200, "losses": 700}, {"wins": 700, "draws": 200, "losses": 100}),
        )
        self.assertEqual(_wdl_data({}, chess.WHITE), (None, None))
        with self.assertRaisesRegex(TeacherError, "WDL values"):
            _wdl_data({"wdl": chess.engine.PovWdl(chess.engine.Wdl(800, 300, 100), chess.WHITE)}, chess.WHITE)

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

    def test_release_verifier_recomputes_game_group_split_rule(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = build_synthetic_release(root)
            verify_release(release, allow_synthetic_source_for_test=True)
            games_path = release / "games.jsonl"
            positions_path = release / "positions.jsonl"
            games = [json.loads(line) for line in games_path.read_text(encoding="utf-8").splitlines()]
            config = json.loads((release / "config.json").read_text(encoding="utf-8"))
            split = json.loads((release / "split.json").read_text(encoding="utf-8"))
            stats = json.loads((release / "stats.json").read_text(encoding="utf-8"))
            source = json.loads((release / "source_manifest.json").read_text(encoding="utf-8"))
            positions_before = sample_positions(
                games, source_id=config["source_id"], seed=config["sampling_seed"],
                max_positions_per_game=config["max_positions_per_game"],
                max_positions=config["max_positions"],
                sampling_config_sha256=config["config_sha256"],
            )
            original_assignments = dict(split["game_group_assignments"])
            target_group = next(
                group for group, partition in sorted(original_assignments.items())
                if partition == "train"
            )
            forged_assignments = dict(original_assignments)
            forged_assignments[target_group] = "validation"
            altered_before = deepcopy(positions_before)
            with patch.object(
                split_module, "assign_game_split",
                side_effect=lambda seed, group: forged_assignments[group],
            ):
                retained, forged_split = split_and_purge(
                    games, altered_before, seed=config["split_seed"],
                    min_holdout_positions=config["min_holdout_positions"],
                    min_holdout_retention=config.get("min_holdout_retention_basis_points", 5000) / 10_000,
                )
            for game in games:
                game["split"] = game["split_id"] = forged_assignments[game["normalized_game_sha256"]]
            forged_stats = summarize_dataset(
                games, altered_before, retained, forged_split, stats["scan"],
                sampling=stats["sampling"], resources=stats["resource_measurements"],
                config_sha256=config["config_sha256"], source_manifest=source,
            )
            games_path.write_bytes(b"".join(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"
                for row in games
            ))
            positions_path.write_bytes(b"".join(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"
                for row in retained
            ))
            (release / "split.json").write_text(
                json.dumps(forged_split, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            (release / "stats.json").write_text(
                json.dumps(forged_stats, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            manifest_path = release / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["split_assignment_sha256"] = forged_split["split_assignment_sha256"]
            manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            for name in ("games.jsonl", "positions.jsonl", "split.json", "stats.json"):
                rewrite_release_file_manifest(release, name)
            with self.assertRaisesRegex(ExportError, "deterministic normalized-game split"):
                verify_release(release, allow_synthetic_source_for_test=True)

    def test_release_verifier_rejects_boolean_split_seed_even_with_consistent_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            release = build_synthetic_release(Path(directory))
            verify_release(release, allow_synthetic_source_for_test=True)
            config_path = release / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["split_seed"] = True
            config_path.write_text(
                json.dumps(config, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            rewrite_release_file_manifest(release, "config.json")
            config = json.loads(config_path.read_text(encoding="utf-8"))
            sampling_id = digest({
                "domain": "videochess-sampling-run/v1", "source_id": config["source_id"],
                "seed": config["sampling_seed"],
                "sampling_config_sha256": config["config_sha256"],
            })
            positions_path = release / "positions.jsonl"
            rows = [json.loads(line) for line in positions_path.read_text(encoding="utf-8").splitlines()]
            for row in rows:
                row["sampling_config_sha256"] = config["config_sha256"]
                row["sampling_id"] = sampling_id
            positions_path.write_bytes(b"".join(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"
                for row in rows
            ))
            rewrite_release_file_manifest(release, "positions.jsonl")
            stats_path = release / "stats.json"
            stats = json.loads(stats_path.read_text(encoding="utf-8"))
            stats["sampling"]["split_seed"] = True
            stats_path.write_text(
                json.dumps(stats, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            rewrite_release_file_manifest(release, "stats.json")
            with self.assertRaisesRegex(ExportError, "split_seed must be a positive integer"):
                verify_release(release, allow_synthetic_source_for_test=True)

    def test_release_verifier_binds_sampling_fields_to_release_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            release = build_synthetic_release(Path(directory))
            verify_release(release, allow_synthetic_source_for_test=True)
            altered = Path(directory) / "altered-provenance"
            shutil.copytree(release, altered)
            positions_path = altered / "positions.jsonl"
            rows = [json.loads(line) for line in positions_path.read_text(encoding="utf-8").splitlines()]
            rows[0]["sampling_config_sha256"] = "1" * 64
            rows[0]["sampling_id"] = "2" * 64
            rows[1]["sampling_config_sha256"] = "3" * 64
            rows[1]["sampling_id"] = "4" * 64
            positions_path.write_bytes(b"".join(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"
                for row in rows
            ))
            rewrite_release_file_manifest(altered, "positions.jsonl")
            with self.assertRaisesRegex(ExportError, "sampling provenance"):
                verify_release(altered, allow_synthetic_source_for_test=True)

    def test_release_verifier_reconstructs_sampled_ply_membership(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            release = build_synthetic_release(Path(directory))
            verify_release(release, allow_synthetic_source_for_test=True)
            altered = Path(directory) / "altered-sampling-seed"
            shutil.copytree(release, altered)
            config_path = altered / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["sampling_seed"] += 1
            config["config_sha256"] = config_identity({k: v for k, v in config.items() if k != "config_sha256"})
            sampling_id = digest({
                "domain": "videochess-sampling-run/v1", "source_id": config["source_id"],
                "seed": config["sampling_seed"], "sampling_config_sha256": config["config_sha256"],
            })
            config_path.write_text(json.dumps(config, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            positions_path = altered / "positions.jsonl"
            rows = [json.loads(line) for line in positions_path.read_text(encoding="utf-8").splitlines()]
            for row in rows:
                row["sampling_config_sha256"] = config["config_sha256"]
                row["sampling_id"] = sampling_id
            positions_path.write_bytes(b"".join(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"
                for row in rows
            ))
            games = [json.loads(line) for line in (altered / "games.jsonl").read_text(encoding="utf-8").splitlines()]
            positions_before = sample_positions(
                games, source_id=config["source_id"], seed=config["sampling_seed"] - 1,
                max_positions_per_game=config["max_positions_per_game"],
                max_positions=config["max_positions"],
                sampling_config_sha256="0" * 64,
            )
            split = json.loads((altered / "split.json").read_text(encoding="utf-8"))
            assignments = dict(split["game_group_assignments"])
            for row in positions_before:
                row["split"] = row["split_id"] = assignments[row["normalized_game_sha256"]]
            retained_ids = {row["sample_id"] for row in rows}
            purged_ids = {row["sample_id"] for row in split["purged_samples"]}
            positions_after = [row for row in positions_before if row["sample_id"] in retained_ids]
            stats = json.loads((altered / "stats.json").read_text(encoding="utf-8"))
            source = json.loads((altered / "source_manifest.json").read_text(encoding="utf-8"))
            stats = summarize_dataset(
                games, positions_before, positions_after, split, stats["scan"],
                sampling={**stats["sampling"], "seed": config["sampling_seed"]},
                resources=stats["resource_measurements"], config_sha256=config["config_sha256"],
                source_manifest=source,
            )
            (altered / "stats.json").write_text(
                json.dumps(stats, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
            )
            rewrite_release_file_manifest(altered, "config.json")
            rewrite_release_file_manifest(altered, "positions.jsonl")
            rewrite_release_file_manifest(altered, "stats.json")
            with self.assertRaisesRegex(ExportError, "deterministic position sampling selection"):
                verify_release(altered, allow_synthetic_source_for_test=True)

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

            legacy_release = temp / "release-legacy-split-v1"
            shutil.copytree(output, legacy_release)
            legacy_split_path = legacy_release / "split.json"
            legacy_split = json.loads(legacy_split_path.read_text(encoding="utf-8"))
            legacy_split["schema"] = "videochess-split/1.0"
            legacy_split.pop("holdout_warnings", None)
            for row in legacy_split["purged_samples"]:
                row.pop("pgn_result", None)
                row.pop("side_to_move_result", None)
            legacy_split_path.write_text(
                json.dumps(legacy_split, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            legacy_stats_path = legacy_release / "stats.json"
            legacy_stats = json.loads(legacy_stats_path.read_text(encoding="utf-8"))
            legacy_stats["schema"] = "videochess-dataset-stats/1.0"
            legacy_stats["quality_report_version"] = 1
            legacy_stats["splits"] = legacy_split
            legacy_stats_path.write_text(
                json.dumps(legacy_stats, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            legacy_manifest = json.loads((legacy_release / "manifest.json").read_text(encoding="utf-8"))
            legacy_manifest["schema_versions"] = [
                "videochess-game/1.0", "videochess-position/1.0", "videochess-split/1.0",
            ]
            (legacy_release / "manifest.json").write_text(
                json.dumps(legacy_manifest, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            rewrite_release_file_manifest(legacy_release, "split.json")
            rewrite_release_file_manifest(legacy_release, "stats.json")
            # Refresh the release schema list and all dependent hashes after the
            # controlled v1 conversion so the verifier exercises compatibility,
            # not a superficial checksum failure.
            legacy_manifest = json.loads((legacy_release / "manifest.json").read_text(encoding="utf-8"))
            legacy_manifest["schema_versions"] = [
                "videochess-game/1.0", "videochess-position/1.0", "videochess-split/1.0",
            ]
            (legacy_release / "manifest.json").write_text(
                json.dumps(legacy_manifest, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            from videochess_rl.data.contracts import release_identity
            legacy_outputs = []
            for item in legacy_manifest["outputs"]:
                content = (legacy_release / item["path"]).read_bytes()
                item["bytes"] = len(content)
                item["sha256"] = hashlib.sha256(content).hexdigest()
                legacy_outputs.append([item["path"], item["bytes"], item["sha256"]])
            legacy_manifest["release_id"] = release_identity(
                legacy_manifest["source_archive_sha256"], legacy_manifest["schema_versions"],
                legacy_manifest["config_sha256"], legacy_manifest["code_revision"],
                legacy_manifest["split_assignment_sha256"], legacy_outputs,
            )
            legacy_manifest_bytes = json.dumps(
                legacy_manifest, sort_keys=True, indent=2, ensure_ascii=False,
            ).encode("utf-8") + b"\n"
            (legacy_release / "manifest.json").write_bytes(legacy_manifest_bytes)
            (legacy_release / "manifest.sha256").write_text(
                hashlib.sha256(legacy_manifest_bytes).hexdigest() + "  manifest.json\n",
                encoding="ascii",
            )
            legacy_verified = verify_release(legacy_release, allow_synthetic_source_for_test=True)
            self.assertEqual(legacy_verified["games"], verified["games"])
            self.assertEqual(legacy_verified["positions"], verified["positions"])

            lowered_policy = temp / "release-lowered-holdout-policy"
            shutil.copytree(output, lowered_policy)
            lowered_config_path = lowered_policy / "config.json"
            lowered_config = json.loads(lowered_config_path.read_text(encoding="utf-8"))
            lowered_config["min_holdout_retention_basis_points"] = 1000
            lowered_config["config_sha256"] = config_identity({
                key: value for key, value in lowered_config.items() if key != "config_sha256"
            })
            lowered_config_path.write_text(
                json.dumps(lowered_config, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            lowered_sampling_id = digest({
                "domain": "videochess-sampling-run/v1",
                "source_id": lowered_config["source_id"],
                "seed": lowered_config["sampling_seed"],
                "sampling_config_sha256": lowered_config["config_sha256"],
            })
            lowered_position_path = lowered_policy / "positions.jsonl"
            lowered_positions = [
                json.loads(line) for line in lowered_position_path.read_text(encoding="utf-8").splitlines()
            ]
            for position in lowered_positions:
                position["sampling_config_sha256"] = lowered_config["config_sha256"]
                position["sampling_id"] = lowered_sampling_id
            lowered_position_path.write_bytes(b"".join(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"
                for row in lowered_positions
            ))
            lowered_split_path = lowered_policy / "split.json"
            lowered_split = json.loads(lowered_split_path.read_text(encoding="utf-8"))
            lowered_split["holdout_minimum_retention"] = 0.1
            lowered_split_path.write_text(
                json.dumps(lowered_split, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            lowered_stats_path = lowered_policy / "stats.json"
            lowered_stats = json.loads(lowered_stats_path.read_text(encoding="utf-8"))
            lowered_stats["splits"] = lowered_split
            lowered_stats_path.write_text(
                json.dumps(lowered_stats, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            for changed_name in ("config.json", "positions.jsonl", "split.json", "stats.json"):
                rewrite_release_file_manifest(lowered_policy, changed_name)
            with self.assertRaisesRegex(ExportError, "5000 through 10000 basis points"):
                verify_release(lowered_policy, allow_synthetic_source_for_test=True)

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

            # Parsing and selection run on real input before this injected
            # statistics delay. Give those setup stages a load-tolerant budget
            # while keeping the artificial delay beyond the total deadline.
            expired_config = dict(config, max_elapsed_seconds=5)
            expired_config_path = temp / "expired-config.json"
            expired_config_path.write_text(json.dumps({"dataset": expired_config}), encoding="utf-8")
            expired_output = temp / "releases" / "expired-release"
            from videochess_rl.data import pipeline as pipeline_module
            original_summary = pipeline_module.summarize_dataset

            def delayed_summary(*args, **kwargs):
                time.sleep(5.05)
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
                            print(f"info depth 1 seldepth 1 multipv {{rank}} score cp 32 nodes 95 wdl 500 400 100 pv {{move.uci()}}")
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
            original_teacher_verify = teacher_module.verify_teacher_run

            def delayed_teacher_verify(*args, **kwargs):
                verified_result = original_teacher_verify(*args, **kwargs)
                time.sleep(0.2)
                return verified_result

            teacher_started = time.monotonic()
            original_finalized_check = teacher_module._verify_finalized_teacher_artifacts

            def delayed_finalized_check(*args, **kwargs):
                checked = original_finalized_check(*args, **kwargs)
                time.sleep(0.15)
                return checked

            with (
                patch("videochess_rl.data.teacher.verify_teacher_run", side_effect=delayed_teacher_verify),
                patch("videochess_rl.data.teacher._verify_finalized_teacher_artifacts", side_effect=delayed_finalized_check),
            ):
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
            teacher_wall_elapsed = time.monotonic() - teacher_started
            self.assertLessEqual(
                teacher_wall_elapsed, teacher_manifest["command_elapsed_projection_seconds"] + 0.1,
                "ordinary finalization should fit within its planned reserve projection",
            )
            self.assertEqual(
                teacher_manifest["command_elapsed_measurement_boundary"],
                "after_semantic_verification_before_final_manifest_publication",
            )
            self.assertEqual(teacher_manifest["status"], "complete")
            teacher_verified = verify_teacher_run(
                teacher_dir, output, allow_synthetic_source_for_test=True,
            )
            self.assertEqual(teacher_manifest["positions_analyzed"], 2)
            self.assertEqual(teacher_verified["positions_analyzed"], 2)
            self.assertEqual(teacher_manifest["schema"], "videochess-teacher-run-manifest/1.2")
            self.assertEqual(teacher_manifest["multipv_score_types"]["cp"], 6)
            self.assertTrue(all(
                line["wdl_side_to_move"] is not None
                and sum(line["wdl_side_to_move"].values()) == 1000
                and line["wdl_perspective"] == "side_to_move"
                and line["wdl_scale"] == "permille-total-1000/v1"
                and line["wdl_method"] == "UCI_ShowWDL"
                for line in json.loads((teacher_dir / "teacher.jsonl").read_text().splitlines()[0])["multipv_lines"]
            ))

            previous_manifest_dir = temp / "teacher-manifest-v1.1"
            shutil.copytree(teacher_dir, previous_manifest_dir)
            previous_manifest_path = previous_manifest_dir / "manifest.json"
            previous_manifest = json.loads(previous_manifest_path.read_text(encoding="utf-8"))
            previous_manifest["schema"] = "videochess-teacher-run-manifest/1.1"
            previous_manifest["command_elapsed_upper_bound_seconds"] = previous_manifest.pop(
                "command_elapsed_projection_seconds",
            )
            previous_manifest.pop("command_elapsed_projection_semantics")
            previous_manifest_bytes = json.dumps(
                previous_manifest, sort_keys=True, indent=2, ensure_ascii=False,
            ).encode("utf-8") + b"\n"
            previous_manifest_path.write_bytes(previous_manifest_bytes)
            (previous_manifest_dir / "manifest.sha256").write_text(
                hashlib.sha256(previous_manifest_bytes).hexdigest() + "  manifest.json\n",
                encoding="ascii",
            )
            self.assertEqual(
                verify_teacher_run(
                    previous_manifest_dir, output, allow_synthetic_source_for_test=True,
                )["positions_analyzed"],
                2,
            )

            legacy_teacher_dir = temp / "teacher-legacy-v1"
            shutil.copytree(teacher_dir, legacy_teacher_dir)
            legacy_manifest_path = legacy_teacher_dir / "manifest.json"
            legacy_manifest = json.loads(legacy_manifest_path.read_text(encoding="utf-8"))
            legacy_config = dict(legacy_manifest["teacher_config"])
            legacy_config["schema"] = "videochess-teacher/1.0"
            legacy_config.pop("finalization_reserve_seconds", None)
            legacy_config_sha = config_identity(legacy_config)
            legacy_run_id = digest({
                "domain": "videochess-teacher-run/v1",
                "teacher_schema_version": "videochess-teacher/1.0",
                "dataset_release_id": legacy_manifest["dataset_release_id"],
                "teacher_config_sha256": legacy_config_sha,
                "engine_sha256": legacy_manifest["engine"]["binary_sha256"],
                "engine_license_sha256": legacy_manifest["engine"]["license_sha256"],
                "code_revision": legacy_manifest["code_revision"],
                "code_tree_sha256": legacy_manifest["code_tree_sha256"],
                "sample_ids_sha256": legacy_manifest["sample_ids_sha256"],
            })
            legacy_rows = [
                json.loads(line)
                for line in (teacher_dir / "teacher.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            for row in legacy_rows:
                row["schema"] = "videochess-teacher/1.0"
                row["teacher_run_id"] = legacy_run_id
                row["teacher_config_sha256"] = legacy_config_sha
                for line in row.get("multipv_lines", []):
                    for key in ("wdl_white", "wdl_perspective", "wdl_scale", "wdl_method"):
                        line.pop(key, None)
            legacy_rows_bytes = b"".join(
                json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
                for row in legacy_rows
            )
            (legacy_teacher_dir / "teacher.jsonl").write_bytes(legacy_rows_bytes)
            legacy_manifest.update({
                "schema": "videochess-teacher-run-manifest/1.0",
                "teacher_run_id": legacy_run_id,
                "teacher_config": legacy_config,
                "teacher_config_sha256": legacy_config_sha,
                "results": {
                    "path": "teacher.jsonl", "bytes": len(legacy_rows_bytes),
                    "sha256": hashlib.sha256(legacy_rows_bytes).hexdigest(),
                },
            })
            for key in (
                "command_elapsed_seconds", "command_elapsed_measurement_boundary",
                "command_elapsed_upper_bound_seconds", "finalization_reserve_seconds",
                "command_elapsed_projection_seconds", "command_elapsed_projection_semantics",
                "finalization_observed_elapsed_seconds", "status", "wall_budget_status",
            ):
                legacy_manifest.pop(key, None)
            legacy_manifest_bytes = json.dumps(
                legacy_manifest, sort_keys=True, indent=2, ensure_ascii=False,
            ).encode("utf-8") + b"\n"
            legacy_manifest_path.write_bytes(legacy_manifest_bytes)
            (legacy_teacher_dir / "manifest.sha256").write_text(
                hashlib.sha256(legacy_manifest_bytes).hexdigest() + "  manifest.json\n",
                encoding="ascii",
            )
            legacy_verified = verify_teacher_run(
                legacy_teacher_dir, output, allow_synthetic_source_for_test=True,
            )
            self.assertEqual(legacy_verified["positions_analyzed"], 2)

            valid_teacher_rows = [
                json.loads(line)
                for line in (teacher_dir / "teacher.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            valid_result_bytes = (teacher_dir / "teacher.jsonl").read_bytes()
            valid_manifest_bytes = (teacher_dir / "manifest.json").read_bytes()
            valid_checksum_bytes = (teacher_dir / "manifest.sha256").read_bytes()
            valid_teacher_manifest = json.loads(valid_manifest_bytes)

            def verify_tampered_teacher_manifest(mutator, message: str) -> None:
                manifest = deepcopy(valid_teacher_manifest)
                mutator(manifest)
                encoded = json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False).encode() + b"\n"
                (teacher_dir / "manifest.json").write_bytes(encoded)
                (teacher_dir / "manifest.sha256").write_text(
                    hashlib.sha256(encoded).hexdigest() + "  manifest.json\n", encoding="ascii",
                )
                with self.assertRaisesRegex(TeacherError, message):
                    verify_teacher_run(teacher_dir, output, allow_synthetic_source_for_test=True)
                (teacher_dir / "manifest.json").write_bytes(valid_manifest_bytes)
                (teacher_dir / "manifest.sha256").write_bytes(valid_checksum_bytes)

            verify_tampered_teacher_manifest(
                lambda manifest: manifest.__setitem__(
                    "command_elapsed_projection_seconds",
                    manifest["command_elapsed_projection_seconds"] + 0.1,
                ),
                "finalization projection metadata",
            )
            verify_tampered_teacher_manifest(
                lambda manifest: manifest.__setitem__(
                    "command_elapsed_projection_semantics", "guaranteed upper bound",
                ),
                "finalization projection metadata",
            )

            def verify_tampered_teacher(mutator, message: str) -> None:
                rows = json.loads(json.dumps(valid_teacher_rows))
                mutator(rows)
                rewrite_teacher_rows(teacher_dir, rows)
                with self.assertRaisesRegex(TeacherError, message):
                    verify_teacher_run(teacher_dir, output, allow_synthetic_source_for_test=True)
                (teacher_dir / "teacher.jsonl").write_bytes(valid_result_bytes)
                (teacher_dir / "manifest.json").write_bytes(valid_manifest_bytes)
                (teacher_dir / "manifest.sha256").write_bytes(valid_checksum_bytes)

            def first_wdl(rows):
                return rows[0]["multipv_lines"][0]

            verify_tampered_teacher(
                lambda rows: first_wdl(rows).__setitem__("wdl_side_to_move", {"wins": "500", "draws": 400, "losses": 100}),
                "WDL must use integer",
            )
            verify_tampered_teacher(
                lambda rows: first_wdl(rows).__setitem__("wdl_side_to_move", {"wins": -1, "draws": 400, "losses": 601}),
                "WDL must use integer",
            )
            verify_tampered_teacher(
                lambda rows: first_wdl(rows).__setitem__("wdl_side_to_move", {"wins": 500, "draws": 400, "losses": 101}),
                "WDL must use integer",
            )
            verify_tampered_teacher(
                lambda rows: first_wdl(rows).__setitem__("wdl_perspective", "white"),
                "WDL perspective/scale/method",
            )
            verify_tampered_teacher(
                lambda rows: first_wdl(rows).__setitem__(
                    "wdl_white",
                    {"wins": first_wdl(rows)["wdl_white"]["losses"],
                     "draws": first_wdl(rows)["wdl_white"]["draws"],
                     "losses": first_wdl(rows)["wdl_white"]["wins"]},
                ),
                "WDL color perspective conversion",
            )
            verify_tampered_teacher(
                lambda rows: rows[0]["multipv_lines"][1].update({
                    "pv_uci": list(rows[0]["multipv_lines"][0]["pv_uci"]),
                    "first_move_uci": rows[0]["multipv_lines"][0]["first_move_uci"],
                    "candidate_id": candidate_identity(
                        rows[0]["sample_id"], rows[0]["multipv_lines"][0]["first_move_uci"],
                    ),
                }),
                "MultiPV root actions are duplicated",
            )
            verify_tampered_teacher(
                lambda rows: rows[0]["multipv_lines"][1].__setitem__("rank", 1),
                "ranks are not unique and contiguous",
            )
            verify_tampered_teacher(
                lambda rows: (
                    rows[0]["multipv_lines"][0].__setitem__("rank", 2),
                    rows[0]["multipv_lines"][1].__setitem__("rank", 1),
                ),
                "ranks are not unique and contiguous",
            )

            missing_optional_wdl = json.loads(json.dumps(valid_teacher_rows))
            for row in missing_optional_wdl:
                for line in row.get("multipv_lines", []):
                    for key in ("wdl_side_to_move", "wdl_white", "wdl_perspective", "wdl_scale", "wdl_method"):
                        line.pop(key, None)
            rewrite_teacher_rows(teacher_dir, missing_optional_wdl)
            verify_teacher_run(teacher_dir, output, allow_synthetic_source_for_test=True)
            (teacher_dir / "teacher.jsonl").write_bytes(valid_result_bytes)
            (teacher_dir / "manifest.json").write_bytes(valid_manifest_bytes)
            (teacher_dir / "manifest.sha256").write_bytes(valid_checksum_bytes)

            original_manifest_publisher = teacher_module._publish_teacher_manifest

            def slow_manifest_publisher(*args, **kwargs):
                time.sleep(0.15)
                return original_manifest_publisher(*args, **kwargs)

            slow_publish_dir = temp / "teacher-slow-manifest-publication"
            slow_publish_started = time.monotonic()
            with patch.object(teacher_module, "_publish_teacher_manifest", side_effect=slow_manifest_publisher):
                slow_publish_manifest = run_teacher(
                    output, output / "games.jsonl", slow_publish_dir,
                    engine_path=fake_engine, expected_engine_sha256=engine_sha,
                    license_path=license_path, expected_license_sha256=license_sha,
                    max_positions=1, sample_seed=9, nodes_per_position=500,
                    multipv=3, threads=1, hash_mib=64, timeout_seconds=5,
                    max_wall_seconds=30, authorization_id=AUTHORIZATION_ID,
                    source_decision_id=SOURCE_DECISION_ID, confirm_write=True,
                    code_revision="a" * 40, allow_synthetic_source_for_test=True,
                )
            slow_publish_elapsed = time.monotonic() - slow_publish_started
            self.assertEqual(slow_publish_manifest["status"], "complete")
            self.assertLessEqual(
                slow_publish_elapsed,
                slow_publish_manifest["command_elapsed_projection_seconds"] + 0.1,
            )
            self.assertEqual(
                verify_teacher_run(slow_publish_dir, output, allow_synthetic_source_for_test=True)["positions_analyzed"],
                1,
            )

            delayed_finalize_dir = temp / "teacher-finalization-longer-than-reserve"

            def finalize_past_reserve(*args, **kwargs):
                checked = original_finalized_check(*args, **kwargs)
                time.sleep(2.2)
                return checked

            delayed_finalize_started = time.monotonic()
            with patch.object(
                teacher_module, "_verify_finalized_teacher_artifacts",
                side_effect=finalize_past_reserve,
            ):
                delayed_finalize_manifest = run_teacher(
                    output, output / "games.jsonl", delayed_finalize_dir,
                    engine_path=fake_engine, expected_engine_sha256=engine_sha,
                    license_path=license_path, expected_license_sha256=license_sha,
                    max_positions=1, sample_seed=9, nodes_per_position=500,
                    multipv=3, threads=1, hash_mib=64, timeout_seconds=5,
                    max_wall_seconds=60, authorization_id=AUTHORIZATION_ID,
                    source_decision_id=SOURCE_DECISION_ID, confirm_write=True,
                    code_revision="a" * 40, allow_synthetic_source_for_test=True,
                )
            delayed_finalize_elapsed = time.monotonic() - delayed_finalize_started
            self.assertEqual(delayed_finalize_manifest["status"], "complete")
            self.assertNotIn("command_elapsed_upper_bound_seconds", delayed_finalize_manifest)
            self.assertLess(
                delayed_finalize_manifest["command_elapsed_projection_seconds"],
                delayed_finalize_elapsed,
                "the explicit projection may be exceeded without implying a guarantee",
            )
            self.assertEqual(
                delayed_finalize_manifest["command_elapsed_projection_semantics"],
                "semantic_elapsed_plus_finalization_reserve_and_return_margin; estimate_only_not_a_guaranteed_upper_bound",
            )
            self.assertEqual(
                verify_teacher_run(
                    delayed_finalize_dir, output, allow_synthetic_source_for_test=True,
                )["positions_analyzed"],
                1,
            )

            original_semantic_verify = teacher_module.verify_teacher_run

            def slow_semantic_verify(*args, **kwargs):
                checked = original_semantic_verify(*args, **kwargs)
                time.sleep(1.4)
                return checked

            reserve_dir = temp / "teacher-finalization-reserve-exhausted"
            with patch.object(teacher_module, "verify_teacher_run", side_effect=slow_semantic_verify):
                reserve_manifest = run_teacher(
                    output, output / "games.jsonl", reserve_dir,
                    engine_path=fake_engine, expected_engine_sha256=engine_sha,
                    license_path=license_path, expected_license_sha256=license_sha,
                    max_positions=1, sample_seed=9, nodes_per_position=500,
                    multipv=3, threads=1, hash_mib=64, timeout_seconds=5,
                    max_wall_seconds=3, authorization_id=AUTHORIZATION_ID,
                    source_decision_id=SOURCE_DECISION_ID, confirm_write=True,
                    code_revision="a" * 40, allow_synthetic_source_for_test=True,
                )
            self.assertEqual(reserve_manifest["positions_analyzed"], 1)
            self.assertEqual(reserve_manifest["status"], "partial")
            self.assertEqual(reserve_manifest["wall_budget_status"], "finalization_reserve_exhausted")
            self.assertEqual(
                verify_teacher_run(reserve_dir, output, allow_synthetic_source_for_test=True)["positions_analyzed"],
                1,
            )

            finalization_calls = 0

            def slow_finalized_check(*args, **kwargs):
                nonlocal finalization_calls
                finalization_calls += 1
                checked = original_finalized_check(*args, **kwargs)
                if finalization_calls == 1:
                    # Leave ample setup/search time for slower full-suite hosts;
                    # the injected delay still exceeds the run's wall budget.
                    time.sleep(12.1)
                return checked

            overrun_dir = temp / "teacher-finalization-overrun"
            overrun_started = time.monotonic()
            with patch.object(teacher_module, "_verify_finalized_teacher_artifacts", side_effect=slow_finalized_check):
                overrun_manifest = run_teacher(
                    output, output / "games.jsonl", overrun_dir,
                    engine_path=fake_engine, expected_engine_sha256=engine_sha,
                    license_path=license_path, expected_license_sha256=license_sha,
                    max_positions=1, sample_seed=9, nodes_per_position=500,
                    multipv=3, threads=1, hash_mib=64, timeout_seconds=5,
                    max_wall_seconds=12, authorization_id=AUTHORIZATION_ID,
                    source_decision_id=SOURCE_DECISION_ID, confirm_write=True,
                    code_revision="a" * 40, allow_synthetic_source_for_test=True,
                )
            overrun_wall_elapsed = time.monotonic() - overrun_started
            self.assertGreater(overrun_wall_elapsed, 12)
            self.assertEqual(overrun_manifest["status"], "partial")
            self.assertEqual(overrun_manifest["wall_budget_status"], "overrun")
            self.assertGreater(overrun_manifest["finalization_observed_elapsed_seconds"], 12)
            self.assertEqual(
                verify_teacher_run(overrun_dir, output, allow_synthetic_source_for_test=True)["positions_analyzed"],
                1,
            )

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
            with self.assertRaises(TeacherError) as bounded_error:
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
            self.assertEqual(bounded_partial["status"], "not_attempted")
            bounded_failure = json.loads((bounded_dir / "failure.json").read_text(encoding="utf-8"))
            self.assertTrue(
                bounded_failure["reason"] == "teacher run produced no successful positions"
                or "teacher wall-time" in bounded_failure["reason"],
                str(bounded_error.exception),
            )
            if bounded_failure["reason"] == "teacher run produced no successful positions":
                self.assertIn("reserve", bounded_partial["reason"])
            else:
                self.assertIn("stopped before analysis", bounded_partial["reason"])
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

            engine_error = temp / "fake-stockfish-engine-error"
            error_script = fake_engine.read_text(encoding="utf-8").replace(
                "import sys\nimport chess",
                "import sys\nimport os\nimport chess",
            ).replace(
                "multipv = 1\nboard = chess.Board()",
                "multipv = 1\ngo_count = 0\nboard = chess.Board()",
            ).replace(
                'elif command == "go":\n        moves = sorted(board.legal_moves, key=lambda move: move.uci())',
                'elif command == "go":\n        go_count += 1\n        if go_count > 1:\n            os._exit(7)\n        moves = sorted(board.legal_moves, key=lambda move: move.uci())',
            )
            self.assertIn("os._exit(7)", error_script)
            engine_error.write_text(error_script, encoding="utf-8")
            engine_error.chmod(0o755)
            engine_error_sha = hashlib.sha256(engine_error.read_bytes()).hexdigest()
            engine_error_dir = temp / "teacher-engine-error"
            engine_error_manifest = run_teacher(
                output, output / "games.jsonl", engine_error_dir,
                engine_path=engine_error, expected_engine_sha256=engine_error_sha,
                license_path=license_path, expected_license_sha256=license_sha,
                max_positions=3, sample_seed=9, nodes_per_position=500,
                multipv=3, threads=1, hash_mib=64, timeout_seconds=5,
                max_wall_seconds=30, authorization_id=AUTHORIZATION_ID,
                source_decision_id=SOURCE_DECISION_ID, confirm_write=True,
                code_revision="a" * 40, allow_synthetic_source_for_test=True,
            )
            error_rows = [
                json.loads(line)
                for line in (engine_error_dir / "teacher.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(engine_error_manifest["status"], "partial")
            self.assertEqual(engine_error_manifest["positions_analyzed"], 1)
            self.assertEqual([row["status"] for row in error_rows], ["ok", "error", "not_attempted"])
            self.assertEqual(
                verify_teacher_run(engine_error_dir, output, allow_synthetic_source_for_test=True)["positions_analyzed"],
                1,
            )

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
