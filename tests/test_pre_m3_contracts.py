"""Synthetic Pre-M3 contract vectors; deliberately not a production data pipeline."""

from __future__ import annotations

import hashlib
import json
import unicodedata
import unittest
from pathlib import Path

import chess

FIXTURE = Path(__file__).parent / "fixtures" / "pre_m3_identity_vectors.json"


def digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def board_signature(board: chess.Board) -> str:
    fields = board.fen(en_passant="legal").split()
    return digest({
        "domain": "videochess-board-position/v1",
        "variant": "standard",
        "placement": fields[0],
        "side_to_move": fields[1],
        "castling": fields[2],
        "legal_ep": fields[3],
    })


def replay_state_id(initial_fen: str, moves: list[str]) -> str:
    return digest({
        "domain": "videochess-replay-state/v1",
        "initial_fen": initial_fen,
        "moves_uci_prefix": moves,
    })


def normalized_game_id(initial_fen: str, moves: list[str]) -> str:
    return digest({
        "domain": "videochess-normalized-game/v1",
        "variant": "standard",
        "initial_fen": initial_fen,
        "moves_uci": moves,
    })


def normalized_game_from_record(record: dict[str, object]) -> str:
    """Hash only identity-bearing fields; headers remain provenance metadata."""
    return normalized_game_id(str(record["initial_fen"]), list(record["moves_uci"]))


def source_game_id(source_id: str, source_game_ref: str) -> str:
    return digest({
        "domain": "videochess-source-game/v1",
        "source_id": source_id,
        "source_game_ref": unicodedata.normalize("NFC", source_game_ref),
    })


def fallback_game_id(
    source: str, archive_sha256: str, member_name: str,
    normalized_game_sha256: str, duplicate_occurrence_ordinal: int,
) -> str:
    return digest({
        "domain": "videochess-source-game-fallback/v1",
        "source_id": source,
        "archive_sha256": archive_sha256,
        "member_name": member_name,
        "normalized_game_sha256": normalized_game_sha256,
        "duplicate_occurrence_ordinal": duplicate_occurrence_ordinal,
    })


def game_sample_key(seed: int, normalized_game_sha256: str) -> str:
    return digest({
        "domain": "videochess-game-sample/v1",
        "seed": seed,
        "normalized_game_sha256": normalized_game_sha256,
    })


def ply_sample_key(seed: int, source: str, game: str, ply_index: int) -> str:
    return digest({
        "domain": "videochess-ply-sample/v1",
        "seed": seed,
        "source_id": source,
        "game_id": game,
        "ply_index": ply_index,
    })


def source_id(publisher_key: str, canonical_url: str, collection_key: str) -> str:
    return digest({
        "domain": "videochess-source/v1",
        "publisher_key": unicodedata.normalize("NFC", publisher_key.strip()),
        "canonical_source_url": unicodedata.normalize("NFC", canonical_url.strip()),
        "collection_key": unicodedata.normalize("NFC", collection_key.strip()),
    })


def sample_id(source_id: str, game_id: str, normalized_game_sha256: str, ply_index: int) -> str:
    return digest({
        "domain": "videochess-sample/v1",
        "schema_version": "videochess-position/1.0",
        "source_id": source_id,
        "game_id": game_id,
        "normalized_game_sha256": normalized_game_sha256,
        "ply_index": ply_index,
    })


def candidate_id(sample: str, action_uci: str) -> str:
    return digest({
        "domain": "videochess-candidate/v1",
        "schema_version": "videochess-candidate/1.0",
        "sample_id": sample,
        "action_uci": action_uci,
    })


def config_id(config: dict[str, object]) -> str:
    return digest({
        "domain": "videochess-config/v1",
        "schema_version": "videochess-config/1.0",
        "config": config,
    })


def sample_set_id(sample_ids: list[str]) -> str:
    return digest({"domain": "videochess-sample-set/v1", "sample_ids": sorted(set(sample_ids))})


def teacher_run_id(
    release_id: str, teacher_config_sha256: str, engine_sha256: str, engine_license_sha256: str,
    code_revision: str, sample_ids: list[str],
) -> str:
    return digest({
        "domain": "videochess-teacher-run/v1",
        "teacher_schema_version": "videochess-teacher/1.0",
        "dataset_release_id": release_id,
        "teacher_config_sha256": teacher_config_sha256,
        "engine_sha256": engine_sha256,
        "engine_license_sha256": engine_license_sha256,
        "code_revision": code_revision,
        "sample_ids_sha256": sample_set_id(sample_ids),
    })


def split_manifest_id(
    seed: int, assignments: list[list[str]], owners: list[list[str]], purged: list[list[str]],
) -> str:
    return digest({
        "domain": "videochess-split-manifest/v1",
        "split_seed": seed,
        "game_group_assignments": sorted(assignments),
        "board_signature_owners": sorted(owners),
        "purged_sample_partitions": sorted(purged),
    })


def release_id(
    source_archive_sha256: str, schema_versions: list[str], config_sha256: str,
    code_revision: str, split_sha256: str, outputs: list[list[object]],
) -> str:
    return digest({
        "domain": "videochess-release/v1",
        "source_archive_sha256": source_archive_sha256,
        "schema_versions": sorted(schema_versions),
        "config_sha256": config_sha256,
        "code_revision": code_revision,
        "split_assignment_sha256": split_sha256,
        "outputs": sorted(outputs),
    })


def game_split(seed: int, normalized_game_sha256: str) -> str:
    value = digest({
        "domain": "videochess-game-split/v1",
        "split_seed": seed,
        "normalized_game_sha256": normalized_game_sha256,
    })
    bucket = int(value[:4], 16)
    return "train" if bucket < 52429 else "validation" if bucket < 58983 else "test"


def board_owner(seed: int, signature: str, splits: set[str]) -> str:
    ranked = {
        split: digest({
            "domain": "videochess-board-owner/v1",
            "split_seed": seed,
            "board_position_signature": signature,
            "candidate_split_name": split,
        })
        for split in splits
    }
    return min(ranked, key=lambda split: (ranked[split], split))


def purge_cross_split_board_overlap(rows: list[dict[str, str]], seed: int) -> list[dict[str, str]]:
    by_signature: dict[str, set[str]] = {}
    for row in rows:
        by_signature.setdefault(row["signature"], set()).add(row["split"])
    owners = {
        signature: board_owner(seed, signature, splits)
        for signature, splits in by_signature.items()
    }
    return [row for row in rows if row["split"] == owners[row["signature"]]]


def inherit_candidate_splits(
    candidate_rows: list[dict[str, str]], position_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    split_by_sample = {row["sample_id"]: row["split"] for row in position_rows}
    return [
        {**candidate, "split": split_by_sample[candidate["sample_id"]]}
        for candidate in candidate_rows
    ]


def holdout_valid(before: int, after: int, minimum: int, retention_minimum: float) -> bool:
    retention = after / before if before else 0.0
    return after >= minimum and retention >= retention_minimum


class PreM3ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vectors = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_canonical_identity_hash_reference_vectors(self) -> None:
        expected = self.vectors["expected_sha256"]
        self.assertEqual(board_signature(chess.Board()), expected["start_board_signature"])
        self.assertEqual(
            replay_state_id(chess.STARTING_FEN, []), expected["start_replay_state"],
        )
        self.assertEqual(
            normalized_game_id(chess.STARTING_FEN, ["e2e4", "e7e5"]),
            expected["e2e4_e7e5_normalized_game"],
        )
        self.assertEqual(
            sample_id("src-v1", "game-a", expected["e2e4_e7e5_normalized_game"], 1),
            expected["src_v1_game_a_ply_1_sample"],
        )

    def test_source_config_teacher_split_and_release_hash_vectors(self) -> None:
        expected = self.vectors["expected_sha256"]
        examples = self.vectors["hash_examples"]
        source = examples["source"]
        self.assertEqual(
            source_id(source["publisher_key"], source["canonical_source_url"], source["collection_key"]),
            expected["source_id"],
        )
        self.assertEqual(
            source_game_id("src-v1", "lichess-game-abc"), expected["source_game_id"],
        )
        normalized = expected["e2e4_e7e5_normalized_game"]
        self.assertEqual(
            fallback_game_id("src-v1", "f" * 64, "games.pgn", normalized, 2),
            expected["fallback_game_id"],
        )
        self.assertNotEqual(
            fallback_game_id("src-v1", "f" * 64, "games.pgn", normalized, 2),
            fallback_game_id("src-v1", "e" * 64, "games.pgn", normalized, 2),
        )
        self.assertEqual(game_sample_key(42, normalized), expected["game_sample_id"])
        self.assertEqual(ply_sample_key(42, "src-v1", "game-a", 1), expected["ply_sample_id"])
        self.assertEqual(
            source_id("lichess", " https://database.lichess.org/ ", "café"),
            source_id("lichess", "https://database.lichess.org/", "cafe\u0301"),
        )
        self.assertEqual(
            source_game_id("src-v1", "game-café"),
            source_game_id("src-v1", "game-cafe\u0301"),
        )
        config_hash = config_id(examples["config"])
        self.assertEqual(config_hash, expected["config_sha256"])
        samples = examples["sample_ids"]
        self.assertEqual(sample_set_id(samples), expected["sample_set_sha256"])
        teacher = examples["teacher"]
        teacher_hash = teacher_run_id(
            teacher["dataset_release_id"], teacher["teacher_config_sha256"],
            teacher["engine_sha256"], teacher["engine_license_sha256"],
            teacher["code_revision"], samples,
        )
        self.assertEqual(teacher_hash, expected["teacher_run_id"])
        split = examples["split_manifest"]
        split_hash = split_manifest_id(
            split["split_seed"], split["game_group_assignments"],
            split["board_signature_owners"], split["purged_sample_partitions"],
        )
        self.assertEqual(split_hash, expected["split_manifest_sha256"])
        release = examples["release"]
        self.assertEqual(
            release_id(
                release["source_archive_sha256"], release["schema_versions"],
                release["config_sha256"], release["code_revision"],
                release["split_assignment_sha256"], release["outputs"],
            ),
            expected["release_id"],
        )

    def test_clock_and_repetition_context_are_not_lost_in_state_identity(self) -> None:
        vector = self.vectors["chess"]["halfmove_clock"]
        before, after = chess.Board(vector["fen_0"]), chess.Board(vector["fen_150"])
        self.assertEqual(board_signature(before), board_signature(after))
        self.assertNotEqual(
            replay_state_id(vector["fen_0"], []), replay_state_id(vector["fen_150"], []),
        )
        self.assertEqual(before.is_game_over(claim_draw=False), vector["fen_0_game_over"])
        self.assertEqual(after.is_game_over(claim_draw=False), vector["fen_150_game_over"])

        repetition = self.vectors["chess"]["repetition"]
        repeated = chess.Board()
        for move in repetition["moves_uci"]:
            repeated.push_uci(move)
        initial = chess.Board()
        self.assertEqual(board_signature(repeated) == board_signature(initial), repetition["same_board_signature_as_start"])
        self.assertNotEqual(replay_state_id(chess.STARTING_FEN, repetition["moves_uci"]), replay_state_id(chess.STARTING_FEN, []))
        self.assertTrue(repeated.is_game_over(claim_draw=False))

    def test_castling_and_en_passant_semantics_are_in_board_signature(self) -> None:
        vectors = self.vectors["chess"]
        castles = vectors["castling"]
        self.assertNotEqual(board_signature(chess.Board(castles["fen_with_rights"])), board_signature(chess.Board(castles["fen_without_rights"])))

        ep = vectors["en_passant"]
        legal = chess.Board(ep["fen_legal_ep"])
        absent = chess.Board(ep["fen_no_ep"])
        self.assertIn(chess.Move.from_uci(ep["legal_ep_move"]), legal.legal_moves)
        self.assertNotEqual(board_signature(legal), board_signature(absent))
        phantom = chess.Board(ep["fen_phantom_ep"])
        no_legal_ep = chess.Board(phantom.fen(en_passant="legal"))
        self.assertEqual(board_signature(phantom), board_signature(no_legal_ep))

    def test_transposition_and_header_duplicates_have_distinct_identity_layers(self) -> None:
        vector = self.vectors["chess"]["transposition"]
        board_a, board_b = chess.Board(), chess.Board()
        for move in vector["moves_a"]:
            board_a.push_uci(move)
        for move in vector["moves_b"]:
            board_b.push_uci(move)
        self.assertEqual(board_signature(board_a), board_signature(board_b))
        self.assertNotEqual(
            replay_state_id(chess.STARTING_FEN, vector["moves_a"]),
            replay_state_id(chess.STARTING_FEN, vector["moves_b"]),
        )

        duplicate = self.vectors["chess"]["duplicate_game_headers"]
        record_a = {"headers": duplicate["headers_a"], "initial_fen": chess.STARTING_FEN, "moves_uci": duplicate["moves_uci"]}
        record_b = {"headers": duplicate["headers_b"], "initial_fen": chess.STARTING_FEN, "moves_uci": duplicate["moves_uci"]}
        self.assertNotEqual(record_a["headers"], record_b["headers"])
        normalized_a = normalized_game_from_record(record_a)
        normalized_b = normalized_game_from_record(record_b)
        self.assertEqual(normalized_a, normalized_b)
        source_a = source_game_id("src-v1", duplicate["source_game_refs"][0])
        source_b = source_game_id("src-v1", duplicate["source_game_refs"][1])
        self.assertNotEqual(source_a, source_b)
        normalized_hash = normalized_game_id(chess.STARTING_FEN, duplicate["moves_uci"])
        self.assertNotEqual(
            sample_id("src-v1", source_a, normalized_hash, 1),
            sample_id("src-v1", source_b, normalized_hash, 1),
        )

    def test_promotion_uci_identity_preserves_all_underpromotions(self) -> None:
        vector = self.vectors["chess"]["promotion"]
        board = chess.Board(vector["fen"])
        promotions = sorted(move.uci() for move in board.legal_moves if move.promotion)
        self.assertEqual(promotions, vector["legal_promotion_uci"])
        self.assertEqual(len(promotions), len(set(promotions)))

    def test_candidate_identity_is_bound_to_parent_sample_and_uci(self) -> None:
        expected = self.vectors["expected_sha256"]["synthetic_position_1_e2e4_candidate"]
        self.assertEqual(
            candidate_id("synthetic-position-1", "e2e4"),
            expected,
        )
        self.assertNotEqual(
            candidate_id("synthetic-position-1", "e2e4"),
            candidate_id("synthetic-position-1", "e7e5"),
        )
        self.assertNotEqual(
            candidate_id("synthetic-position-1", "e2e4"),
            candidate_id("synthetic-position-2", "e2e4"),
        )

    def test_split_vectors_keep_candidate_rows_together_and_detect_holdout_collapse(self) -> None:
        vector = self.vectors["split"]
        self.assertEqual(game_split(vector["seed"], vector["train_group_sha256"]), vector["train_group_assignment"])
        self.assertEqual(game_split(vector["seed"], vector["validation_group_sha256"]), vector["validation_group_assignment"])
        signature = board_signature(chess.Board())
        self.assertEqual(board_owner(vector["seed"], signature, {"train", "validation"}), vector["start_board_signature_owner"])
        candidate_sample = vector["candidate_sample_id"]
        position_rows = [
            {"sample_id": candidate_sample, "split": vector["candidate_split"], "signature": signature},
            {"sample_id": "train-open-1", "split": "train", "signature": signature},
        ]
        candidate_rows = [{"sample_id": candidate_sample, "uci": move} for move in vector["candidate_rows"]]
        inherited = inherit_candidate_splits(candidate_rows, position_rows)
        self.assertEqual({row["split"] for row in inherited}, {"validation"})

        # Three held-out rows share the opening board with train; a unique row remains.
        unique = chess.Board("7k/P7/8/8/8/8/8/7K w - - 0 1")
        rows = [
            {"sample_id": "train-open-1", "split": "train", "signature": signature},
            {"sample_id": "held-open-1", "split": "validation", "signature": signature},
            {"sample_id": "held-open-2", "split": "validation", "signature": signature},
            {"sample_id": "held-open-3", "split": "validation", "signature": signature},
            {"sample_id": "held-unique", "split": "validation", "signature": board_signature(unique)},
        ]
        kept = purge_cross_split_board_overlap(rows, vector["seed"])
        before = vector["holdout_collapse"]["pre_purge_validation_positions"]
        after = sum(row["split"] == "validation" for row in kept)
        self.assertEqual(after, vector["holdout_collapse"]["post_purge_validation_positions"])
        self.assertFalse(holdout_valid(
            before, after,
            vector["holdout_collapse"]["min_holdout_positions"],
            vector["holdout_collapse"]["minimum_retention_fraction"],
        ))

        all_candidates = [
            {"sample_id": row["sample_id"], "uci": move}
            for row in rows if row["sample_id"].startswith("held-open-")
            for move in vector["candidate_rows"]
        ]
        inherited_candidates = inherit_candidate_splits(all_candidates, rows)
        retained_sample_ids = {row["sample_id"] for row in kept}
        retained_candidates = [
            row for row in inherited_candidates if row["sample_id"] in retained_sample_ids
        ]
        self.assertEqual(retained_candidates, [])


if __name__ == "__main__":
    unittest.main()
