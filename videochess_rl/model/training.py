"""Deterministic behavior-cloning objective, metrics, and bounded CPU trainer."""

from __future__ import annotations

import copy
import math
import random
import resource
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Callable, Iterable

import numpy as np
import torch
from torch.nn import functional as F
from torch.nn.utils import clip_grad_norm_

from .dataset import (
    MAX_PADDED_CANDIDATE_SLOTS,
    MAX_PADDED_HISTORY_TOKENS,
    MAX_PHYSICAL_BATCH_POSITIONS,
    PositionFeatures,
    collate_examples,
    model_inputs,
)
from .network import BehaviorScorer


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    optimizer: str = "AdamW"
    learning_rate: float = 3e-4
    weight_decay: float = 1e-4
    batch_size: int = 64
    gradient_clip_norm: float = 1.0
    maximum_epochs: int = 20
    early_stopping_patience: int = 4
    seeds: tuple[int, ...] = (20261022, 20261023, 20261024)
    device: str = "cpu"
    max_seconds_per_seed: int = 45 * 60
    max_aggregate_seconds: int = 3 * 60 * 60

    def as_json(self) -> dict[str, Any]:
        value = asdict(self)
        value["seeds"] = list(self.seeds)
        return value


class TrainingBudgetExceeded(RuntimeError):
    pass


def peak_rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def _bounded_index_batches(
    rows: tuple[PositionFeatures, ...], indices: Iterable[int], batch_size: int,
) -> list[list[int]]:
    if not 1 <= batch_size <= MAX_PHYSICAL_BATCH_POSITIONS:
        raise ValueError("physical batch size must be between 1 and 64")
    batches: list[list[int]] = []
    current: list[int] = []
    max_history = 0
    max_candidates = 0
    for index in indices:
        row = rows[index]
        next_count = len(current) + 1
        next_history = max(max_history, row.history_length)
        next_candidates = max(max_candidates, row.candidate_count)
        exceeds = (
            next_count > batch_size
            or next_count * next_history > MAX_PADDED_HISTORY_TOKENS
            or next_count * next_candidates > MAX_PADDED_CANDIDATE_SLOTS
        )
        if exceeds and current:
            batches.append(current)
            current = []
            max_history = 0
            max_candidates = 0
            next_count = 1
            next_history = row.history_length
            next_candidates = row.candidate_count
        if next_count * next_history > MAX_PADDED_HISTORY_TOKENS or next_count * next_candidates > MAX_PADDED_CANDIDATE_SLOTS:
            raise ValueError("one example exceeds the fixed padded tensor budget")
        current.append(index)
        max_history = next_history
        max_candidates = next_candidates
    if current:
        batches.append(current)
    return batches


def _bucketed_training_batches(
    rows: tuple[PositionFeatures, ...], *, seed: int, batch_size: int,
) -> list[list[int]]:
    indices = list(range(len(rows)))
    random.Random(seed).shuffle(indices)
    bucket_width = max(batch_size * 8, batch_size)
    batches: list[list[int]] = []
    for offset in range(0, len(indices), bucket_width):
        bucket = indices[offset:offset + bucket_width]
        bucket.sort(key=lambda index: (rows[index].history_length, rows[index].candidate_count, rows[index].sample_id))
        # Preserve the configured effective batch size. fit_seed() divides
        # each logical batch into memory-safe physical microbatches and
        # accumulates their weighted gradients before one optimizer step.
        batches.extend(
            bucket[start:start + batch_size]
            for start in range(0, len(bucket), batch_size)
        )
    random.Random(seed ^ 0x5A17).shuffle(batches)
    return batches


def configure_determinism(seed: int, *, threads: int = 1) -> dict[str, Any]:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    if isinstance(threads, bool) or not isinstance(threads, int) or threads < 1:
        raise ValueError("threads must be a positive integer")
    random.seed(seed)
    np.random.seed(seed % (2**32))
    torch.manual_seed(seed)
    torch.set_num_threads(threads)
    try:
        torch.set_num_interop_threads(threads)
    except RuntimeError:
        # PyTorch permits this only before its inter-op pool is initialized.
        # The actual pool size is recorded by callers, not silently assumed.
        pass
    torch.use_deterministic_algorithms(True)
    return {
        "python_seed": seed,
        "numpy_seed": seed % (2**32),
        "torch_seed": seed,
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "intraop_threads": torch.get_num_threads(),
        "interop_threads": torch.get_num_interop_threads(),
    }


def masked_behavior_logits(logits: torch.Tensor, candidate_mask: torch.Tensor) -> torch.Tensor:
    if logits.shape != candidate_mask.shape:
        raise ValueError("logits and candidate_mask must have identical shapes")
    if candidate_mask.dtype != torch.bool:
        raise TypeError("candidate_mask must be boolean")
    if logits.ndim != 2:
        raise ValueError("candidate logits must have shape [B,N]")
    if logits.shape[1] == 0 or torch.any(~candidate_mask.any(dim=1)):
        raise ValueError("behavior loss/selection requires at least one legal candidate per row")
    if not torch.isfinite(logits[candidate_mask]).all():
        raise FloatingPointError("a legal candidate has a non-finite behavior logit")
    return logits.masked_fill(~candidate_mask, -torch.inf)


def behavior_cross_entropy(
    logits: torch.Tensor,
    candidate_mask: torch.Tensor,
    target_indices: torch.Tensor,
) -> torch.Tensor:
    if target_indices.shape != (logits.shape[0],):
        raise ValueError("target_indices must contain one candidate index per row")
    if target_indices.dtype not in (torch.int32, torch.int64):
        raise TypeError("target_indices must be integer candidate indices")
    masked = masked_behavior_logits(logits, candidate_mask)
    if torch.any(target_indices < 0) or torch.any(target_indices >= logits.shape[1]):
        raise ValueError("behavior target index is outside the candidate batch")
    if not candidate_mask.gather(1, target_indices.long().unsqueeze(1)).all():
        raise ValueError("behavior target points to a padded or illegal candidate")
    loss = F.cross_entropy(masked, target_indices.long())
    if not torch.isfinite(loss):
        raise FloatingPointError("behavior cross-entropy is non-finite")
    return loss


def _metric_accumulator() -> dict[str, float | int]:
    return {
        "examples": 0,
        "candidates": 0,
        "nll_sum": 0.0,
        "top1_sum": 0.0,
        "top3_sum": 0.0,
        "top5_sum": 0.0,
        "mrr_sum": 0.0,
        "uniform_nll_sum": 0.0,
        "uniform_top1_sum": 0.0,
        "uniform_top3_sum": 0.0,
        "uniform_top5_sum": 0.0,
        "uniform_mrr_sum": 0.0,
    }


def _add_row_metrics(
    accumulator: dict[str, float | int],
    row_logits: torch.Tensor,
    valid_mask: torch.Tensor,
    target_index: int,
) -> None:
    count = int(valid_mask.sum().item())
    if count < 1:
        raise ValueError("cannot evaluate an empty legal candidate set")
    if not 0 <= target_index < len(valid_mask) or not bool(valid_mask[target_index]):
        raise ValueError("evaluation target is not a legal candidate")
    valid_logits = row_logits[valid_mask]
    if not torch.isfinite(valid_logits).all():
        raise FloatingPointError("evaluation found a non-finite legal logit")
    valid_target = int(valid_mask[:target_index].sum().item())
    order = torch.argsort(valid_logits, descending=True, stable=True)
    rank_positions = torch.nonzero(order == valid_target, as_tuple=False).flatten()
    if rank_positions.numel() != 1:
        raise RuntimeError("target rank could not be mapped to its legal UCI candidate")
    rank = int(rank_positions.item()) + 1
    nll = float(F.cross_entropy(valid_logits.unsqueeze(0), torch.tensor([valid_target])).item())
    top1 = float(rank <= 1)
    top3 = float(rank <= 3)
    top5 = float(rank <= 5)
    mrr = 1.0 / rank
    harmonic = sum(1.0 / value for value in range(1, count + 1))
    values = {
        "examples": 1,
        "candidates": count,
        "nll_sum": nll,
        "top1_sum": top1,
        "top3_sum": top3,
        "top5_sum": top5,
        "mrr_sum": mrr,
        "uniform_nll_sum": math.log(count),
        "uniform_top1_sum": 1.0 / count,
        "uniform_top3_sum": min(3, count) / count,
        "uniform_top5_sum": min(5, count) / count,
        "uniform_mrr_sum": harmonic / count,
    }
    for key, value in values.items():
        accumulator[key] = accumulator[key] + value


def _finish_metrics(accumulator: dict[str, float | int]) -> dict[str, Any]:
    examples = int(accumulator["examples"])
    if examples == 0:
        raise ValueError("no examples were evaluated")
    return {
        "examples": examples,
        "candidate_evaluations": int(accumulator["candidates"]),
        "nll": float(accumulator["nll_sum"]) / examples,
        "top1_accuracy": float(accumulator["top1_sum"]) / examples,
        "top3_accuracy": float(accumulator["top3_sum"]) / examples,
        "top5_accuracy": float(accumulator["top5_sum"]) / examples,
        "mrr": float(accumulator["mrr_sum"]) / examples,
        "uniform_legal_baseline": {
            "nll": float(accumulator["uniform_nll_sum"]) / examples,
            "top1_accuracy": float(accumulator["uniform_top1_sum"]) / examples,
            "top3_accuracy": float(accumulator["uniform_top3_sum"]) / examples,
            "top5_accuracy": float(accumulator["uniform_top5_sum"]) / examples,
            "mrr": float(accumulator["uniform_mrr_sum"]) / examples,
        },
    }


def _strata_for_example(example: PositionFeatures) -> tuple[list[str], list[str]]:
    sides = ["white_to_move" if float(example.state_scalars[0]) == 1.0 else "black_to_move"]
    if example.target_index is None:
        raise ValueError("stratified evaluation requires a behavior target")
    flags = example.candidate_flags[example.target_index]
    categories: list[str] = []
    names = ("capture", "castling", "en_passant", "check")
    for index, name in enumerate(names):
        if bool(flags[index]):
            categories.append(name)
    if int(example.candidate_promotion[example.target_index]) != 0:
        categories.append("promotion")
    if not categories:
        categories.append("quiet")
    if example.ply_index is not None:
        if example.ply_index < 20:
            categories.append("opening_plies_0_19")
        elif example.ply_index < 60:
            categories.append("middle_plies_20_59")
        else:
            categories.append("late_plies_60_plus")
    return sides, categories


@torch.no_grad()
def evaluate_examples(
    model: BehaviorScorer,
    examples: Iterable[PositionFeatures],
    *,
    batch_size: int = 64,
    device: str | torch.device = "cpu",
    include_strata: bool = True,
    max_seconds: float | None = None,
) -> dict[str, Any]:
    rows = tuple(examples)
    if not rows or any(row.target_index is None for row in rows):
        raise ValueError("evaluation requires nonempty labeled examples")
    if len({row.split for row in rows}) != 1:
        raise ValueError("an evaluation pass cannot mix data splits")
    split = rows[0].split
    model = model.to(device)
    model.eval()
    aggregate = _metric_accumulator()
    side_aggregates: dict[str, dict[str, float | int]] = defaultdict(_metric_accumulator)
    category_aggregates: dict[str, dict[str, float | int]] = defaultdict(_metric_accumulator)
    candidate_count = 0
    start = time.perf_counter()
    for batch_indices in _bounded_index_batches(rows, range(len(rows)), batch_size):
        if max_seconds is not None and time.perf_counter() - start >= max_seconds:
            raise TrainingBudgetExceeded("evaluation time budget reached between bounded batches")
        if peak_rss_bytes() > 2 * 1024**3:
            raise TrainingBudgetExceeded("process peak RSS exceeded the 2 GiB M4 cap during evaluation")
        batch_rows = tuple(rows[index] for index in batch_indices)
        batch = collate_examples(batch_rows)
        inputs = model_inputs(batch)
        inputs = {key: (value.to(device) if isinstance(value, torch.Tensor) else value) for key, value in inputs.items()}
        logits = model(**inputs)
        _ = masked_behavior_logits(logits, inputs["candidate_mask"])
        for index, example in enumerate(batch_rows):
            target_index = int(batch["target_indices"][index].item())
            _add_row_metrics(aggregate, logits[index], inputs["candidate_mask"][index], target_index)
            candidate_count += example.candidate_count
            if include_strata:
                sides, categories = _strata_for_example(example)
                for name in sides:
                    _add_row_metrics(side_aggregates[name], logits[index], inputs["candidate_mask"][index], target_index)
                for name in categories:
                    _add_row_metrics(category_aggregates[name], logits[index], inputs["candidate_mask"][index], target_index)
    elapsed = time.perf_counter() - start
    result = _finish_metrics(aggregate)
    result.update({
        "split": split,
        "duration_seconds": elapsed,
        "examples_per_second": len(rows) / elapsed if elapsed else None,
        "candidate_evaluations_per_second": candidate_count / elapsed if elapsed else None,
    })
    if include_strata:
        result["by_side_to_move"] = {key: _finish_metrics(value) for key, value in sorted(side_aggregates.items())}
        result["by_target_move_type_or_phase"] = {
            key: _finish_metrics(value) for key, value in sorted(category_aggregates.items())
        }
    return result


@dataclass(slots=True)
class FitResult:
    seed: int
    epoch_history: list[dict[str, Any]]
    best_epoch: int | None
    best_validation_nll: float | None
    stop_reason: str
    duration_seconds: float
    optimizer_updates: int
    best_model_state: dict[str, torch.Tensor] | None
    best_optimizer_state: dict[str, Any] | None


def _clone_state_dict(state: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value.detach().cpu().clone() if isinstance(value, torch.Tensor) else copy.deepcopy(value)
        for key, value in state.items()
    }


def fit_seed(
    model: BehaviorScorer,
    train_examples: Iterable[PositionFeatures],
    validation_examples: Iterable[PositionFeatures],
    *,
    seed: int,
    config: TrainingConfig | None = None,
    on_best: Callable[[int, BehaviorScorer, torch.optim.Optimizer, dict[str, Any]], None] | None = None,
) -> FitResult:
    settings = config or TrainingConfig()
    train_rows = tuple(train_examples)
    validation_rows = tuple(validation_examples)
    if not train_rows or any(row.split != "train" or row.target_index is None for row in train_rows):
        raise ValueError("fit_seed accepts labeled training-split rows only")
    if not validation_rows or any(row.split != "validation" or row.target_index is None for row in validation_rows):
        raise ValueError("fit_seed accepts labeled validation-split rows only")
    if settings.device != "cpu":
        raise ValueError("the initial M4 protocol is local CPU only")
    if settings.batch_size > MAX_PHYSICAL_BATCH_POSITIONS:
        raise ValueError("the accepted physical batch cap is 64 positions")
    if settings.optimizer != "AdamW":
        raise ValueError("the accepted initial optimizer is AdamW")

    model.to(settings.device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=settings.learning_rate, weight_decay=settings.weight_decay
    )
    start = time.monotonic()
    deadline = start + settings.max_seconds_per_seed
    history: list[dict[str, Any]] = []
    best_epoch: int | None = None
    best_nll = math.inf
    best_model: dict[str, torch.Tensor] | None = None
    best_optimizer: dict[str, Any] | None = None
    no_improvement = 0
    update_total = 0
    stop_reason = "maximum_epochs"

    if peak_rss_bytes() > 2 * 1024**3:
        raise TrainingBudgetExceeded("process peak RSS already exceeds the 2 GiB M4 cap")
    for epoch in range(1, settings.maximum_epochs + 1):
        if time.monotonic() >= deadline:
            stop_reason = "seed_time_limit_before_epoch"
            break
        batches = _bucketed_training_batches(train_rows, seed=seed + epoch, batch_size=settings.batch_size)
        train_accumulator = _metric_accumulator()
        epoch_start = time.monotonic()
        updates_this_epoch = 0
        physical_microbatches_this_epoch = 0
        preclip_norm_max = 0.0
        postclip_norm_max = 0.0
        max_history_tokens = 0
        max_candidate_slots = 0
        model.train()
        try:
            for logical_batch_indices in batches:
                if time.monotonic() >= deadline:
                    raise TrainingBudgetExceeded("per-seed 45-minute budget reached during epoch")
                optimizer.zero_grad(set_to_none=True)
                logical_count = len(logical_batch_indices)
                microbatch_indices = _bounded_index_batches(
                    train_rows, logical_batch_indices, settings.batch_size
                )
                for batch_indices in microbatch_indices:
                    if time.monotonic() >= deadline:
                        raise TrainingBudgetExceeded("per-seed 45-minute budget reached during microbatch accumulation")
                    selected = [train_rows[index] for index in batch_indices]
                    batch = collate_examples(selected)
                    inputs = model_inputs(batch)
                    logits = model(**inputs)
                    target_indices = batch["target_indices"]
                    loss = behavior_cross_entropy(logits, batch["candidate_mask"], target_indices)
                    (loss * (len(selected) / logical_count)).backward()
                    physical_microbatches_this_epoch += 1
                    max_history_tokens = max(
                        max_history_tokens,
                        len(selected) * max(row.history_length for row in selected),
                    )
                    max_candidate_slots = max(
                        max_candidate_slots,
                        len(selected) * max(row.candidate_count for row in selected),
                    )
                    with torch.no_grad():
                        for index, row in enumerate(selected):
                            _add_row_metrics(
                                train_accumulator,
                                logits[index],
                                batch["candidate_mask"][index],
                                int(target_indices[index].item()),
                            )
                if any(parameter.grad is not None and not torch.isfinite(parameter.grad).all() for parameter in model.parameters()):
                    raise FloatingPointError("training produced a non-finite gradient")
                preclip_norm = clip_grad_norm_(
                    model.parameters(), settings.gradient_clip_norm, error_if_nonfinite=True
                )
                if not torch.isfinite(preclip_norm):
                    raise FloatingPointError("gradient norm is non-finite")
                postclip_square = sum(
                    float(parameter.grad.detach().norm(2).item()) ** 2
                    for parameter in model.parameters() if parameter.grad is not None
                )
                preclip_norm_max = max(preclip_norm_max, float(preclip_norm.item()))
                postclip_norm_max = max(postclip_norm_max, math.sqrt(postclip_square))
                optimizer.step()
                if any(not torch.isfinite(parameter).all() for parameter in model.parameters()):
                    raise FloatingPointError("optimizer produced a non-finite model parameter")
                if peak_rss_bytes() > 2 * 1024**3:
                    raise TrainingBudgetExceeded("process peak RSS exceeded the 2 GiB M4 cap")
                updates_this_epoch += 1
                update_total += 1
        except TrainingBudgetExceeded as exc:
            stop_reason = "peak_rss_cap_during_epoch" if "RSS" in str(exc) else "seed_time_limit_during_epoch"
            if int(train_accumulator["examples"]) > 0:
                partial_train = _finish_metrics(train_accumulator)
                partial_seconds = time.monotonic() - epoch_start
                history.append({
                    "epoch": epoch,
                    "status": "budget_interrupted_partial_train_metrics",
                    "train": partial_train,
                    "validation": None,
                    "optimizer_updates": updates_this_epoch,
                    "physical_microbatches": physical_microbatches_this_epoch,
                    "duration_seconds": partial_seconds,
                    "train_duration_seconds": partial_seconds,
                    "examples_per_second": partial_train["examples"] / partial_seconds if partial_seconds else None,
                    "candidate_evaluations_per_second": (
                        partial_train["candidate_evaluations"] / partial_seconds if partial_seconds else None
                    ),
                    "stop_reason": stop_reason,
                    "stop_detail": str(exc),
                    "metrics_scope": "completed physical microbatches; any incomplete logical-batch gradients were not applied",
                    "selection_metric": "validation_nll_only; incomplete epoch not eligible",
                })
            break

        train_metrics = _finish_metrics(train_accumulator)
        train_seconds = time.monotonic() - epoch_start
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            stop_reason = "seed_time_limit_before_validation"
            history.append({
                "epoch": epoch,
                "status": "train_complete_validation_not_run_budget",
                "train": train_metrics,
                "validation": None,
                "optimizer_updates": updates_this_epoch,
                "physical_microbatches": physical_microbatches_this_epoch,
                "train_duration_seconds": train_seconds,
                "validation_duration_seconds": 0.0,
                "duration_seconds": time.monotonic() - epoch_start,
                "examples_per_second": len(train_rows) / train_seconds if train_seconds else None,
                "candidate_evaluations_per_second": (
                    train_metrics["candidate_evaluations"] / train_seconds if train_seconds else None
                ),
                "stop_reason": stop_reason,
                "selection_metric": "validation_nll_only; validation not run",
            })
            break
        validation_start = time.monotonic()
        try:
            validation_metrics = evaluate_examples(
                model, validation_rows, batch_size=settings.batch_size, device=settings.device,
                include_strata=False, max_seconds=remaining,
            )
        except TrainingBudgetExceeded as exc:
            stop_reason = "peak_rss_cap_during_validation" if "RSS" in str(exc) else "seed_time_limit_during_validation"
            history.append({
                "epoch": epoch,
                "status": "train_complete_validation_incomplete_budget",
                "train": train_metrics,
                "validation": None,
                "optimizer_updates": updates_this_epoch,
                "physical_microbatches": physical_microbatches_this_epoch,
                "train_duration_seconds": train_seconds,
                "validation_duration_seconds": time.monotonic() - validation_start,
                "duration_seconds": time.monotonic() - epoch_start,
                "examples_per_second": len(train_rows) / train_seconds if train_seconds else None,
                "candidate_evaluations_per_second": (
                    train_metrics["candidate_evaluations"] / train_seconds if train_seconds else None
                ),
                "stop_reason": stop_reason,
                "stop_detail": str(exc),
                "selection_metric": "validation_nll_only; incomplete validation not eligible",
            })
            break
        validation_seconds = time.monotonic() - validation_start
        epoch_seconds = time.monotonic() - epoch_start
        epoch_record = {
            "epoch": epoch,
            "train": train_metrics,
            "validation": validation_metrics,
            "optimizer_updates": updates_this_epoch,
            "physical_microbatches": physical_microbatches_this_epoch,
            "train_duration_seconds": train_seconds,
            "validation_duration_seconds": validation_seconds,
            "duration_seconds": epoch_seconds,
            "examples_per_second": len(train_rows) / train_seconds if train_seconds else None,
            "candidate_evaluations_per_second": (
                train_metrics["candidate_evaluations"] / train_seconds if train_seconds else None
            ),
            "gradient_clip_norm": settings.gradient_clip_norm,
            "max_preclip_gradient_norm": preclip_norm_max,
            "max_postclip_gradient_norm": postclip_norm_max,
            "max_padded_history_tokens": max_history_tokens,
            "max_padded_candidate_slots": max_candidate_slots,
            "selection_metric": "validation_nll",
        }
        history.append(epoch_record)

        # Strict comparison keeps the earlier epoch when validation NLL ties.
        if validation_metrics["nll"] < best_nll:
            best_nll = validation_metrics["nll"]
            best_epoch = epoch
            no_improvement = 0
            best_model = _clone_state_dict(model.state_dict())
            best_optimizer = _clone_state_dict(optimizer.state_dict())
            if on_best is not None:
                on_best(epoch, model, optimizer, epoch_record)
        else:
            no_improvement += 1
            if no_improvement >= settings.early_stopping_patience:
                stop_reason = "validation_patience"
                break

    duration = time.monotonic() - start
    if best_model is not None:
        model.load_state_dict(best_model, strict=True)
    return FitResult(
        seed=seed,
        epoch_history=history,
        best_epoch=best_epoch,
        best_validation_nll=None if best_epoch is None else best_nll,
        stop_reason=stop_reason,
        duration_seconds=duration,
        optimizer_updates=update_total,
        best_model_state=best_model,
        best_optimizer_state=best_optimizer,
    )


def run_overfit_gate(
    model: BehaviorScorer,
    examples: Iterable[PositionFeatures],
    *,
    seed: int = 20261022,
    max_updates: int = 500,
    max_seconds: float = 45 * 60,
    learning_rate: float = 3e-4,
    weight_decay: float = 1e-4,
    gradient_clip_norm: float = 1.0,
) -> dict[str, Any]:
    rows = tuple(examples)
    if len(rows) != 128 or any(row.split != "train" or row.target_index is None for row in rows):
        raise ValueError("the sanity gate requires the fixed 128 labeled training examples")
    ids = tuple(row.sample_id for row in rows)
    if ids != tuple(sorted(ids)) or len(set(ids)) != 128:
        raise ValueError("sanity-gate IDs must be 128 unique lexicographically sorted sample IDs")
    if max_seconds <= 0:
        raise ValueError("sanity-gate time budget must be positive")
    settings = configure_determinism(seed)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    measurements: list[dict[str, Any]] = []
    started = time.monotonic()
    model.train()

    def measure(update: int) -> dict[str, Any]:
        remaining = max_seconds - (time.monotonic() - started)
        if remaining <= 0:
            raise TrainingBudgetExceeded("sanity-gate time budget reached")
        metrics = evaluate_examples(
            model, rows, batch_size=MAX_PHYSICAL_BATCH_POSITIONS,
            include_strata=False, max_seconds=remaining,
        )
        loss = metrics["nll"]
        row = {
            "updates": update,
            "cross_entropy": float(loss),
            "legal_top1_accuracy": metrics["top1_accuracy"],
            "top3_accuracy": metrics["top3_accuracy"],
            "mrr": metrics["mrr"],
            "elapsed_seconds": time.monotonic() - started,
        }
        measurements.append(row)
        return row

    current: dict[str, Any] | None = None
    passed_at: int | None = None
    updates = 0
    total_norm = 0.0
    budget_stop_reason: str | None = None
    try:
        current = measure(0)
        passed_at = 0 if current["cross_entropy"] <= 0.05 and current["legal_top1_accuracy"] >= 0.99 else None
        model.train()
        while passed_at is None and updates < max_updates:
            if time.monotonic() - started >= max_seconds:
                raise TrainingBudgetExceeded("sanity-gate time budget reached during optimization")
            optimizer.zero_grad(set_to_none=True)
            for micro_indices in _bounded_index_batches(
                rows, range(len(rows)), MAX_PHYSICAL_BATCH_POSITIONS,
            ):
                micro_rows = tuple(rows[index] for index in micro_indices)
                batch = collate_examples(micro_rows)
                inputs = model_inputs(batch)
                logits = model(**inputs)
                loss = behavior_cross_entropy(logits, batch["candidate_mask"], batch["target_indices"])
                (loss * (len(micro_rows) / len(rows))).backward()
            if any(parameter.grad is not None and not torch.isfinite(parameter.grad).all() for parameter in model.parameters()):
                raise FloatingPointError("sanity gate produced a non-finite gradient")
            preclip = clip_grad_norm_(model.parameters(), gradient_clip_norm, error_if_nonfinite=True)
            if not torch.isfinite(preclip):
                raise FloatingPointError("sanity gate gradient norm is non-finite")
            total_norm = float(preclip.item())
            optimizer.step()
            if peak_rss_bytes() > 2 * 1024**3:
                raise TrainingBudgetExceeded("sanity gate exceeded the 2 GiB M4 process RSS cap")
            updates += 1
            if updates % 5 == 0 or updates == max_updates:
                current = measure(updates)
                if current["cross_entropy"] <= 0.05 and current["legal_top1_accuracy"] >= 0.99:
                    passed_at = updates
                model.train()
    except TrainingBudgetExceeded as exc:
        budget_stop_reason = str(exc)
    return {
        "status": "PASS" if passed_at is not None else "BUDGET_EXCEEDED" if budget_stop_reason else "FAIL",
        "seed": seed,
        "determinism": settings,
        "sample_ids": list(ids),
        "sample_id_count": len(ids),
        "updates": updates,
        "passed_at_update": passed_at,
        "thresholds": {"cross_entropy_max": 0.05, "legal_top1_accuracy_min": 0.99, "max_updates": max_updates},
        "final": current,
        "measurements": measurements,
        "duration_seconds": time.monotonic() - started,
        "max_preclip_gradient_norm": total_norm,
        "optimizer": {"name": "AdamW", "learning_rate": learning_rate, "weight_decay": weight_decay, "gradient_clip_norm": gradient_clip_norm},
        "budget_stop_reason": budget_stop_reason,
    }


def _collect_metrics(logits: torch.Tensor, mask: torch.Tensor, targets: torch.Tensor) -> dict[str, float | int]:
    accumulator = _metric_accumulator()
    for index in range(logits.shape[0]):
        _add_row_metrics(accumulator, logits[index], mask[index], int(targets[index].item()))
    return accumulator
