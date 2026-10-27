"""ADR-0003 action-conditioned behavior scorer and M5 transfer boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import torch
from torch import nn

INPUT_SCHEMA = "videochess-model-input/1.0"
MODEL_SCHEMA = "videochess-behavior-scorer/1.0"


@dataclass(frozen=True, slots=True)
class ModelConfig:
    input_schema: str = INPUT_SCHEMA
    board_channels: int = 13
    conv_widths: tuple[int, int] = (32, 64)
    board_state_dim: int = 128
    history_embedding_dims: tuple[int, int, int, int] = (16, 16, 8, 4)
    history_project_dim: int = 64
    history_hidden_dim: int = 64
    metadata_dim: int = 16
    square_embedding_dim: int = 16
    promotion_embedding_dim: int = 8
    candidate_local_dim: int = 64
    candidate_symbolic_dim: int = 32
    candidate_dim: int = 64
    scorer_hidden_dim: int = 128
    output_dim: int = 1
    model_schema: str = MODEL_SCHEMA

    def as_json(self) -> dict[str, object]:
        result = asdict(self)
        for key, value in tuple(result.items()):
            if isinstance(value, tuple):
                result[key] = list(value)
        return result


class BoardEncoder(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        first, second = config.conv_widths
        self.conv1 = nn.Conv2d(config.board_channels, first, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(first, second, kernel_size=3, padding=1)
        self.state_projection = nn.Linear(second * 2, config.board_state_dim)

    def forward(self, board_planes: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        spatial = torch.relu(self.conv1(board_planes))
        spatial = torch.relu(self.conv2(spatial))
        pooled = torch.cat((spatial.mean(dim=(-2, -1)), spatial.amax(dim=(-2, -1))), dim=-1)
        state = torch.relu(self.state_projection(pooled))
        return spatial, state


class HistoryEncoder(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        origin_dim, destination_dim, promotion_dim, mover_dim = config.history_embedding_dims
        self.origin_embedding = nn.Embedding(64, origin_dim)
        self.destination_embedding = nn.Embedding(64, destination_dim)
        self.promotion_embedding = nn.Embedding(5, promotion_dim)
        self.mover_embedding = nn.Embedding(2, mover_dim)
        self.input_projection = nn.Linear(sum(config.history_embedding_dims), config.history_project_dim)
        self.gru = nn.GRU(config.history_project_dim, config.history_hidden_dim, batch_first=True)

    def forward(self, history_moves: torch.Tensor, history_mask: torch.Tensor) -> torch.Tensor:
        batch_size, time_steps, _ = history_moves.shape
        result = history_moves.new_zeros((batch_size, self.gru.hidden_size), dtype=torch.float32)
        if time_steps == 0:
            return result
        lengths = history_mask.sum(dim=1).to(dtype=torch.long)
        nonempty = torch.nonzero(lengths > 0, as_tuple=False).flatten()
        if nonempty.numel() == 0:
            return result

        moves = history_moves.index_select(0, nonempty).long()
        selected_lengths = lengths.index_select(0, nonempty)
        encoded = torch.cat(
            (
                self.origin_embedding(moves[:, :, 0]),
                self.destination_embedding(moves[:, :, 1]),
                self.promotion_embedding(moves[:, :, 2]),
                self.mover_embedding(moves[:, :, 3]),
            ),
            dim=-1,
        )
        encoded = torch.relu(self.input_projection(encoded))
        packed = nn.utils.rnn.pack_padded_sequence(
            encoded, selected_lengths.cpu(), batch_first=True, enforce_sorted=False
        )
        _, hidden = self.gru(packed)
        return result.index_copy(0, nonempty, hidden[-1])


class CandidateEncoder(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        square_dim = config.square_embedding_dim
        self.origin_embedding = nn.Embedding(64, square_dim)
        self.destination_embedding = nn.Embedding(64, square_dim)
        self.promotion_embedding = nn.Embedding(5, config.promotion_embedding_dim)
        self.local_projection = nn.Linear(config.conv_widths[-1] * 2, config.candidate_local_dim)
        symbolic_input = square_dim * 2 + config.promotion_embedding_dim + 4
        self.symbolic_projection = nn.Linear(symbolic_input, config.candidate_symbolic_dim)
        self.output_projection = nn.Linear(
            config.candidate_local_dim + config.candidate_symbolic_dim, config.candidate_dim
        )

    def forward(
        self,
        spatial: torch.Tensor,
        candidate_squares: torch.Tensor,
        candidate_promotion: torch.Tensor,
        candidate_flags: torch.Tensor,
    ) -> torch.Tensor:
        batch_size, _, candidates = candidate_squares.shape[0], spatial.shape[1], candidate_squares.shape[1]
        if candidates == 0:
            return spatial.new_empty((batch_size, 0, self.output_projection.out_features))

        origin = candidate_squares[:, :, 0].long()
        destination = candidate_squares[:, :, 1].long()
        flat_spatial = spatial.flatten(2)
        origin_local = flat_spatial.gather(
            2, origin.unsqueeze(1).expand(-1, flat_spatial.shape[1], -1)
        ).transpose(1, 2)
        destination_local = flat_spatial.gather(
            2, destination.unsqueeze(1).expand(-1, flat_spatial.shape[1], -1)
        ).transpose(1, 2)
        local = torch.relu(self.local_projection(torch.cat((origin_local, destination_local), dim=-1)))
        symbolic = torch.cat(
            (
                self.origin_embedding(origin),
                self.destination_embedding(destination),
                self.promotion_embedding(candidate_promotion.long()),
                candidate_flags.float(),
            ),
            dim=-1,
        )
        symbolic = torch.relu(self.symbolic_projection(symbolic))
        return torch.relu(self.output_projection(torch.cat((local, symbolic), dim=-1)))


class BehaviorScorer(nn.Module):
    """One behavior-preference logit for each supplied candidate UCI action."""

    def __init__(self, config: ModelConfig | None = None) -> None:
        super().__init__()
        self.config = config or ModelConfig()
        if self.config.input_schema != INPUT_SCHEMA or self.config.model_schema != MODEL_SCHEMA:
            raise ValueError("unsupported model/input schema version")
        if self.config.output_dim != 1:
            raise ValueError("the M4/M5 transfer contract requires a scalar candidate head")
        self.board_encoder = BoardEncoder(self.config)
        self.history_encoder = HistoryEncoder(self.config)
        self.metadata_projection = nn.Linear(6, self.config.metadata_dim)
        self.candidate_encoder = CandidateEncoder(self.config)
        scorer_input = (
            self.config.board_state_dim
            + self.config.history_hidden_dim
            + self.config.metadata_dim
            + self.config.candidate_dim
        )
        self.shared_scorer = nn.Linear(scorer_input, self.config.scorer_hidden_dim)
        self.behavior_head = nn.Linear(self.config.scorer_hidden_dim, 1)

    def forward(
        self,
        *,
        board_planes: torch.Tensor,
        state_scalars: torch.Tensor,
        history_moves: torch.Tensor,
        history_mask: torch.Tensor,
        candidate_squares: torch.Tensor,
        candidate_promotion: torch.Tensor,
        candidate_flags: torch.Tensor,
        candidate_mask: torch.Tensor,
        candidate_uci: list[tuple[str, ...]] | None = None,
    ) -> torch.Tensor:
        batch_size, candidate_count = candidate_mask.shape
        if board_planes.shape != (batch_size, 13, 8, 8):
            raise ValueError("board_planes must have shape [B,13,8,8]")
        if state_scalars.shape != (batch_size, 6):
            raise ValueError("state_scalars must have shape [B,6]")
        if candidate_squares.shape != (batch_size, candidate_count, 2):
            raise ValueError("candidate_squares must have shape [B,N,2]")
        if candidate_promotion.shape != (batch_size, candidate_count):
            raise ValueError("candidate_promotion must have shape [B,N]")
        if candidate_flags.shape != (batch_size, candidate_count, 4):
            raise ValueError("candidate_flags must have shape [B,N,4]")
        if history_moves.ndim != 3 or history_moves.shape[0] != batch_size or history_moves.shape[2] != 4:
            raise ValueError("history_moves must have shape [B,T,4]")
        if history_mask.shape != history_moves.shape[:2]:
            raise ValueError("history_mask must have shape [B,T]")
        if candidate_mask.dtype != torch.bool or history_mask.dtype != torch.bool:
            raise TypeError("history_mask and candidate_mask must be boolean")
        if history_mask.shape[1] > 1 and torch.any(history_mask[:, 1:] & ~history_mask[:, :-1]):
            raise ValueError("history_mask must contain a true prefix followed by padding")
        if candidate_count > 1 and torch.any(candidate_mask[:, 1:] & ~candidate_mask[:, :-1]):
            raise ValueError("candidate_mask must contain a legal prefix followed by padding")
        if candidate_uci is not None:
            if len(candidate_uci) != batch_size:
                raise ValueError("candidate_uci must contain one semantic UCI list per batch row")
            for row_index, actions in enumerate(candidate_uci):
                valid_count = int(candidate_mask[row_index].sum().item())
                if len(actions) != valid_count:
                    raise ValueError("candidate UCI list length differs from its legal mask")
                if len(set(actions)) != len(actions) or tuple(actions) != tuple(sorted(actions)):
                    raise ValueError("candidate UCI identities must be unique and lexically ordered")
        if candidate_count == 0:
            return board_planes.new_empty((batch_size, 0), dtype=torch.float32)

        spatial, board_state = self.board_encoder(board_planes.float())
        history_state = self.history_encoder(history_moves, history_mask)
        metadata = torch.relu(self.metadata_projection(state_scalars.float()))
        candidate = self.candidate_encoder(
            spatial, candidate_squares, candidate_promotion, candidate_flags
        )
        shared = torch.cat(
            (
                board_state[:, None, :].expand(-1, candidate_count, -1),
                history_state[:, None, :].expand(-1, candidate_count, -1),
                metadata[:, None, :].expand(-1, candidate_count, -1),
                candidate,
            ),
            dim=-1,
        )
        return self._score_hidden(torch.relu(self.shared_scorer(shared))).squeeze(-1)

    def _score_hidden(self, hidden: torch.Tensor) -> torch.Tensor:
        return self.behavior_head(hidden)

    @property
    def trainable_parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters() if parameter.requires_grad)

    def m5_transfer_state(self) -> dict[str, torch.Tensor]:
        """Return reusable representation weights; deliberately omit behavior_head."""
        return {
            key: value.detach().cpu().clone()
            for key, value in self.state_dict().items()
            if not key.startswith("behavior_head.")
        }


class M5TransferScorer(BehaviorScorer):
    """Untrained M5-compatible scorer with a separately initialized scalar head.

    This is only a representation-transfer boundary. It does not implement
    Double DQN, rewards, replay, or training, and its output is not a learned
    Q-value until future M5 code trains it under that objective.
    """

    def __init__(self, config: ModelConfig | None = None, *, seed: int) -> None:
        super().__init__(config)
        del self.behavior_head
        self.q_head = nn.Linear(self.config.scorer_hidden_dim, 1)
        _initialize_scalar_head(self.q_head, seed)

    def _score_hidden(self, hidden: torch.Tensor) -> torch.Tensor:
        return self.q_head(hidden)


def _initialize_scalar_head(head: nn.Linear, seed: int) -> nn.Linear:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        nn.init.kaiming_uniform_(head.weight, a=5**0.5)
        if head.bias is not None:
            fan_in, _ = nn.init._calculate_fan_in_and_fan_out(head.weight)
            bound = 1 / fan_in**0.5
            nn.init.uniform_(head.bias, -bound, bound)
    return head


def initialize_q_head(model: BehaviorScorer, *, seed: int) -> M5TransferScorer:
    """Transfer shared M4 representation and create a fresh, separate Q head."""
    if not isinstance(model, BehaviorScorer) or isinstance(model, M5TransferScorer):
        raise TypeError("source must be an M4 BehaviorScorer")
    value_model = M5TransferScorer(model.config, seed=seed)
    missing, unexpected = value_model.load_state_dict(model.m5_transfer_state(), strict=False)
    if missing != ["q_head.weight", "q_head.bias"] or unexpected:
        raise RuntimeError(f"M4-to-M5 shared-layer transfer mismatch: missing={missing}, unexpected={unexpected}")
    return value_model
