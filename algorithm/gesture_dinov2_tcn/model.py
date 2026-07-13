"""Deployment model for fused DINOv2, hand geometry and causal TCN."""
from __future__ import annotations

import math

import torch
from torch import nn
from torch.nn import functional as F
from transformers import Dinov2Config, Dinov2Model

from .geometry import GEOMETRY_FEATURE_DIM


def dinov2_small_config() -> Dinov2Config:
    """Construct DINOv2-S/14 without requiring a network or HF cache."""
    return Dinov2Config(
        hidden_size=384,
        num_hidden_layers=12,
        num_attention_heads=6,
        intermediate_size=1536,
        hidden_act="gelu",
        # facebook/dinov2-small stores a 37x37 patch position table (518px)
        # and interpolates it for the 224px fine-tuning/inference input.
        image_size=518,
        patch_size=14,
        num_channels=3,
        qkv_bias=True,
        layerscale_value=1.0,
        layer_norm_eps=1e-6,
    )


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
        tensor = self.dropout(F.gelu(self.norm1(self._causal_conv(tensor, self.conv1))))
        tensor = self.dropout(F.gelu(self.norm2(self._causal_conv(tensor, self.conv2))))
        return residual + tensor


class GesturePrototypeNetwork(nn.Module):
    def __init__(
        self,
        *,
        geometry_dim: int = GEOMETRY_FEATURE_DIM,
        fusion_dim: int = 256,
        embedding_dim: int = 128,
        tcn_dilations: tuple[int, ...] = (1, 2, 4, 8),
        dropout: float = 0.20,
        dino_frame_chunk: int = 12,
    ) -> None:
        super().__init__()
        self.dino = Dinov2Model(dinov2_small_config())
        self.dino_frame_chunk = dino_frame_chunk
        hidden_size = int(self.dino.config.hidden_size)
        self.dino_projection = nn.Sequential(
            nn.LayerNorm(hidden_size * 2), nn.Linear(hidden_size * 2, fusion_dim), nn.GELU(), nn.Dropout(dropout)
        )
        self.geometry_encoder = nn.Sequential(
            nn.LayerNorm(geometry_dim * 3), nn.Linear(geometry_dim * 3, fusion_dim), nn.GELU(),
            nn.Dropout(dropout), nn.Linear(fusion_dim, fusion_dim),
        )
        self.fusion_gate = nn.Sequential(nn.Linear(fusion_dim * 2, fusion_dim), nn.Sigmoid())
        self.tcn = nn.ModuleList(
            [CausalResidualBlock(fusion_dim, kernel_size=3, dilation=value, dropout=dropout) for value in tcn_dilations]
        )
        self.temporal_attention = nn.Linear(fusion_dim, 1)
        self.projection_head = nn.Sequential(
            nn.LayerNorm(fusion_dim), nn.Linear(fusion_dim, fusion_dim), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(fusion_dim, embedding_dim),
        )
        self.log_temperature = nn.Parameter(torch.tensor(math.log(0.10), dtype=torch.float32))

    def _encode_dino(self, frames: torch.Tensor) -> torch.Tensor:
        batch, steps, channels, height, width = frames.shape
        flattened = frames.reshape(batch * steps, channels, height, width)
        encoded: list[torch.Tensor] = []
        for start in range(0, len(flattened), self.dino_frame_chunk):
            output = self.dino(pixel_values=flattened[start : start + self.dino_frame_chunk])
            encoded.append(
                self.dino_projection(
                    torch.cat([output.last_hidden_state[:, 0], output.last_hidden_state[:, 1:].mean(dim=1)], dim=-1)
                )
            )
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
        temporal = (gate * dino_features + (1.0 - gate) * geometry_features).transpose(1, 2)
        for block in self.tcn:
            temporal = block(temporal)
        temporal = temporal.transpose(1, 2)
        weights = torch.softmax(self.temporal_attention(temporal).squeeze(-1), dim=1)
        pooled = torch.sum(temporal * weights.unsqueeze(-1), dim=1)
        return F.normalize(self.projection_head(pooled), dim=-1)
