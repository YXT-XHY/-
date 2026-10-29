"""Small spectrogram CNN + positional Transformer + learned temporal pooling."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import torch
from torch import nn


@dataclass(frozen=True)
class ModelConfig:
    n_mels: int = 64
    dimension: int = 64
    heads: int = 4
    layers: int = 2
    dropout: float = .25

    def to_dict(self):
        return asdict(self)


class SpeechTransformer(nn.Module):
    def __init__(self, config: ModelConfig = ModelConfig()):
        super().__init__()
        self.config = config
        self.convolution = nn.Sequential(
            nn.Conv2d(1, 8, 3, padding=1), nn.GroupNorm(2, 8), nn.GELU(), nn.MaxPool2d(2),
            nn.Conv2d(8, 16, 3, padding=1), nn.GroupNorm(4, 16), nn.GELU(), nn.MaxPool2d(2),
            nn.Dropout(config.dropout),
        )
        self.projection = nn.Linear(16 * (config.n_mels // 4), config.dimension)
        layer = nn.TransformerEncoderLayer(config.dimension, config.heads,
                                            dim_feedforward=config.dimension*2,
                                            dropout=config.dropout, batch_first=True,
                                            activation="gelu", norm_first=True)
        self.transformer = nn.TransformerEncoder(layer, config.layers, enable_nested_tensor=False)
        self.norm = nn.LayerNorm(config.dimension)
        self.attention = nn.Linear(config.dimension, 1)
        self.classifier = nn.Sequential(nn.Dropout(config.dropout), nn.Linear(config.dimension, 1))

    def forward(self, mel: torch.Tensor, return_attention: bool = False):
        # [batch, mel, time] -> [batch, channels, freq, time] -> temporal tokens
        encoded = self.convolution(mel.unsqueeze(1))
        sequence = encoded.permute(0, 3, 1, 2).flatten(2)
        sequence = self.projection(sequence)
        steps, dimension = sequence.shape[1:]
        position = torch.arange(steps, device=sequence.device, dtype=sequence.dtype).unsqueeze(1)
        scales = torch.exp(torch.arange(0, dimension, 2, device=sequence.device,
                                        dtype=sequence.dtype) * (-math.log(10000) / dimension))
        positional = torch.zeros((steps, dimension), device=sequence.device, dtype=sequence.dtype)
        positional[:, 0::2] = torch.sin(position * scales)
        positional[:, 1::2] = torch.cos(position * scales)
        sequence = self.norm(self.transformer(sequence + positional.unsqueeze(0)))
        weights = torch.softmax(self.attention(sequence).squeeze(-1), dim=1)
        pooled = (sequence * weights.unsqueeze(-1)).sum(dim=1)
        logits = self.classifier(pooled).squeeze(-1)
        return (logits, weights) if return_attention else logits
