"""DINOv2 + hand geometry + causal TCN prototype network."""
from __future__ import annotations

import math
from typing import Any

import torch
from torch import nn
from torch.nn import functional as F
from transformers import Dinov2Model

from .geometry import GEOMETRY_FEATURE_DIM


class CausalResidualBlock(nn.Module):
    def __init__(self, channels: int, kernel_size: int, dilation: int, dropout: float) -> None:
        super().__init__()
        self.left_padding = (kernel_size - 1) * dilation
        self.conv1 = nn.Conv1d(channels, channels, kernel_size, dilation=dilation)
        self.conv2 = nn.Conv1d(channels, channels, kernel_size, dilation=dilation)
        self.norm1 = nn.GroupNorm(1, channels)
        self.norm2 = nn.GroupNorm(1, channels)
        self.dropout = nn.Dropout(dropout)

    def _causal_conv(self, tensor: torch.Tensor, convolution: nn.Conv1d) -> torch.Tensor:
        return convolution(F.pad(tensor, (self.left_padding, 0)))

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        residual = tensor
        tensor = self._causal_conv(tensor, self.conv1)
        tensor = self.dropout(F.gelu(self.norm1(tensor)))
        tensor = self._causal_conv(tensor, self.conv2)
        tensor = self.dropout(F.gelu(self.norm2(tensor)))
        return residual + tensor


class GesturePrototypeNetwork(nn.Module):
    def __init__(
        self,
        *,
        model_name: str = "facebook/dinov2-small",
        geometry_dim: int = GEOMETRY_FEATURE_DIM,
        fusion_dim: int = 256,
        embedding_dim: int = 128,
        tcn_dilations: tuple[int, ...] = (1, 2, 4, 8),
        dropout: float = 0.20,
        unfrozen_dino_blocks: int = 2,
        dino_frame_chunk: int = 16,
        local_files_only: bool = False,
    ) -> None:
        super().__init__()
        self.dino = Dinov2Model.from_pretrained(model_name, local_files_only=local_files_only)
        self.dino_frame_chunk = dino_frame_chunk
        hidden_size = int(self.dino.config.hidden_size)
        self.dino_projection = nn.Sequential(
            nn.LayerNorm(hidden_size * 2),
            nn.Linear(hidden_size * 2, fusion_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.geometry_encoder = nn.Sequential(
            nn.LayerNorm(geometry_dim * 3),
            nn.Linear(geometry_dim * 3, fusion_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(fusion_dim, fusion_dim),
        )
        self.fusion_gate = nn.Sequential(nn.Linear(fusion_dim * 2, fusion_dim), nn.Sigmoid())
        self.tcn = nn.ModuleList(
            [CausalResidualBlock(fusion_dim, kernel_size=3, dilation=dilation, dropout=dropout) for dilation in tcn_dilations]
        )
        self.temporal_attention = nn.Linear(fusion_dim, 1)
        self.projection_head = nn.Sequential(
            nn.LayerNorm(fusion_dim),
            nn.Linear(fusion_dim, fusion_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(fusion_dim, embedding_dim),
        )
        self.log_temperature = nn.Parameter(torch.tensor(math.log(0.10), dtype=torch.float32))
        self.set_unfrozen_dino_blocks(unfrozen_dino_blocks)

    def set_unfrozen_dino_blocks(self, count: int) -> None:
        layers = list(self.dino.encoder.layer)
        count = max(0, min(int(count), len(layers)))
        for parameter in self.dino.parameters():
            parameter.requires_grad = False
        for layer in layers[-count:] if count else []:
            for parameter in layer.parameters():
                parameter.requires_grad = True
        if count:
            for parameter in self.dino.layernorm.parameters():
                parameter.requires_grad = True
        self.unfrozen_dino_blocks = count

    def train(self, mode: bool = True):
        super().train(mode)
        layers = list(self.dino.encoder.layer)
        frozen_count = len(layers) - self.unfrozen_dino_blocks
        self.dino.embeddings.eval()
        for layer in layers[:frozen_count]:
            layer.eval()
        return self

    def _encode_dino(self, frames: torch.Tensor) -> torch.Tensor:
        batch, steps, channels, height, width = frames.shape
        flattened = frames.reshape(batch * steps, channels, height, width)
        encoded: list[torch.Tensor] = []
        for start in range(0, len(flattened), self.dino_frame_chunk):
            output = self.dino(pixel_values=flattened[start : start + self.dino_frame_chunk])
            cls_token = output.last_hidden_state[:, 0]
            patch_mean = output.last_hidden_state[:, 1:].mean(dim=1)
            encoded.append(self.dino_projection(torch.cat([cls_token, patch_mean], dim=-1)))
        return torch.cat(encoded, dim=0).reshape(batch, steps, -1)

    @staticmethod
    def _geometry_with_motion(geometry: torch.Tensor) -> torch.Tensor:
        velocity = F.pad(geometry[:, 1:] - geometry[:, :-1], (0, 0, 1, 0))
        acceleration = F.pad(velocity[:, 1:] - velocity[:, :-1], (0, 0, 1, 0))
        return torch.cat([geometry, velocity, acceleration], dim=-1)

    def forward(self, frames: torch.Tensor, geometry: torch.Tensor, detected: torch.Tensor | None = None) -> torch.Tensor:
        dino_features = self._encode_dino(frames)
        geometry_features = self.geometry_encoder(self._geometry_with_motion(geometry))
        if detected is not None:
            geometry_features = geometry_features * (0.25 + 0.75 * detected.unsqueeze(-1))
        gate = self.fusion_gate(torch.cat([dino_features, geometry_features], dim=-1))
        fused = gate * dino_features + (1.0 - gate) * geometry_features
        temporal = fused.transpose(1, 2)
        for block in self.tcn:
            temporal = block(temporal)
        temporal = temporal.transpose(1, 2)
        weights = torch.softmax(self.temporal_attention(temporal).squeeze(-1), dim=1)
        pooled = torch.sum(temporal * weights.unsqueeze(-1), dim=1)
        return F.normalize(self.projection_head(pooled), dim=-1)

    def optimizer_groups(self, encoder_lr: float, head_lr: float, weight_decay: float) -> list[dict[str, Any]]:
        dino_ids = {id(parameter) for parameter in self.dino.parameters()}
        encoder_parameters = [parameter for parameter in self.parameters() if id(parameter) in dino_ids]
        head_parameters = [parameter for parameter in self.parameters() if id(parameter) not in dino_ids]
        return [
            {"params": encoder_parameters, "lr": encoder_lr, "weight_decay": weight_decay},
            {"params": head_parameters, "lr": head_lr, "weight_decay": weight_decay},
        ]


def split_support_query(labels: torch.Tensor, n_support: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    support_indices: list[torch.Tensor] = []
    query_indices: list[torch.Tensor] = []
    classes = torch.unique(labels, sorted=True)
    for label in classes:
        indices = torch.nonzero(labels == label, as_tuple=False).flatten()
        support_indices.append(indices[:n_support])
        query_indices.append(indices[n_support:])
    return torch.cat(support_indices), torch.cat(query_indices), classes


def prototypical_loss(
    embeddings: torch.Tensor,
    labels: torch.Tensor,
    *,
    n_support: int,
    temperature: torch.Tensor | float,
) -> tuple[torch.Tensor, torch.Tensor]:
    support_indices, query_indices, classes = split_support_query(labels, n_support)
    prototypes = torch.stack(
        [embeddings[support_indices][labels[support_indices] == label].mean(dim=0) for label in classes]
    )
    queries = embeddings[query_indices]
    query_labels = labels[query_indices]
    targets = torch.stack([torch.nonzero(classes == label, as_tuple=False)[0, 0] for label in query_labels])
    distances = torch.cdist(queries.float(), prototypes.float(), p=2).square()
    temperature_tensor = torch.as_tensor(temperature, device=distances.device).clamp(0.02, 1.0)
    logits = -distances / temperature_tensor
    loss = F.cross_entropy(logits, targets)
    accuracy = (logits.argmax(dim=1) == targets).float().mean()
    return loss, accuracy
