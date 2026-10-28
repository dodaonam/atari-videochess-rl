"""Versioned deterministic RNG identities for the future M5 paired runs.

This module defines the M5 seed contract only; it does not implement a learner.
Run IDs are deliberately absent from the derivation API so warm/scratch arms
with distinct artifact identities retain the same pair-level seed schedule.
"""

from __future__ import annotations

import hashlib
import re
import struct

SEED_DERIVATION_SCHEMA = "videochess-m5-seed-derivation/1.0"
PAIR_ID_DOMAIN = b"videochess-m5-pair-id/v1\x00"
SEED_DOMAIN = b"videochess-m5-seed/v1\x00"
EXPERIMENT_ID = "m5-double-dqn-paired-v1"
RNG_DOMAINS = (
    "episode_seed",
    "opponent_rng",
    "exploration_rng",
    "replay_sampling_rng",
    "q_head_initialization",
    "scratch_representation_initialization",
)

_MAX_U64 = (1 << 64) - 1
_DOMAIN_HASH_MASK = (1 << 60) - 1
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*\Z", re.ASCII)


def _u64(value: int, *, name: str) -> bytes:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if not 0 <= value <= _MAX_U64:
        raise ValueError(f"{name} must be in the unsigned 64-bit range")
    return struct.pack(">Q", value)


def _identifier_bytes(value: str, *, name: str) -> bytes:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{name} must be a non-empty ASCII identifier")
    encoded = value.encode("ascii")
    if len(encoded) > 0xFFFFFFFF:
        raise ValueError(f"{name} is too long")
    return encoded


def pair_identity(experiment_id: str, training_seed: int) -> str:
    """Return the stable lowercase SHA-256 identity shared by a warm/scratch pair."""
    experiment = _identifier_bytes(experiment_id, name="experiment_id")
    payload = PAIR_ID_DOMAIN + struct.pack(">I", len(experiment)) + experiment + _u64(
        training_seed, name="training_seed"
    )
    return hashlib.sha256(payload).hexdigest()


def run_identity(pair_id: str, arm: str, attempt_index: int) -> str:
    """Return a unique per-arm attempt identity for provenance, never seed input."""
    if not isinstance(pair_id, str) or not re.fullmatch(r"[0-9a-f]{64}", pair_id):
        raise ValueError("pair_id must be a lowercase 64-character SHA-256 hex digest")
    if arm not in ("warm", "scratch"):
        raise ValueError("arm must be 'warm' or 'scratch'")
    if isinstance(attempt_index, bool) or not isinstance(attempt_index, int):
        raise TypeError("attempt_index must be an integer")
    if attempt_index < 0:
        raise ValueError("attempt_index must be non-negative")
    return f"m5-{pair_id}__{arm}__attempt-{attempt_index:04d}"


def derive_seed(
    master_seed: int,
    pair_id: str,
    domain: str,
    index: int = 0,
) -> int:
    """Derive a portable non-negative 63-bit seed from canonical fields.

    ``pair_id`` must be a lowercase SHA-256 hex digest returned by
    :func:`pair_identity`. Domain and index identify a named stream or an
    indexed per-episode seed. The unique run ID is provenance only and is not
    accepted here.
    """
    if not isinstance(pair_id, str) or not re.fullmatch(r"[0-9a-f]{64}", pair_id):
        raise ValueError("pair_id must be a lowercase 64-character SHA-256 hex digest")
    if domain not in RNG_DOMAINS:
        raise ValueError(f"domain must be one of the configured M5 RNG domains: {RNG_DOMAINS}")
    domain_bytes = _identifier_bytes(domain, name="domain")
    payload = (
        SEED_DOMAIN
        + _u64(master_seed, name="master_seed")
        + bytes.fromhex(pair_id)
        + struct.pack(">I", len(domain_bytes))
        + domain_bytes
        + _u64(index, name="index")
    )
    digest_prefix = hashlib.sha256(payload).digest()[:8]
    domain_code = RNG_DOMAINS.index(domain)
    # Reserve the high three bits for the canonical domain code. This makes
    # seed values from different configured domains disjoint, not merely
    # overwhelmingly likely to differ after hashing.
    return (domain_code << 60) | (int.from_bytes(digest_prefix, "big") & _DOMAIN_HASH_MASK)


def paired_seed_schedule(
    experiment_id: str,
    training_seed: int,
    episode_index: int,
) -> dict[str, int | str]:
    """Build the arm-independent seed schedule for one paired episode.

    The episode and opponent seeds are indexed from zero. The remaining values
    are stream initializers (index zero); their evolving RNG states are saved
    in episode-boundary checkpoints. Callers persist each returned seed and
    the resulting RNG states, but keep run IDs separately in provenance.
    """
    _u64(episode_index, name="episode_index")
    pair_id = pair_identity(experiment_id, training_seed)
    return {
        "schema": SEED_DERIVATION_SCHEMA,
        "pair_id": pair_id,
        "episode_seed": derive_seed(training_seed, pair_id, "episode_seed", episode_index),
        "opponent_rng_seed": derive_seed(training_seed, pair_id, "opponent_rng", episode_index),
        "exploration_rng_seed": derive_seed(training_seed, pair_id, "exploration_rng"),
        "replay_sampling_rng_seed": derive_seed(training_seed, pair_id, "replay_sampling_rng"),
        "q_head_initialization_seed": derive_seed(training_seed, pair_id, "q_head_initialization"),
        "scratch_representation_initialization_seed": derive_seed(
            training_seed, pair_id, "scratch_representation_initialization"
        ),
    }
