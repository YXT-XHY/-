"""One preprocessing definition shared by training and deployment."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import io
import math
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly
import soundfile as sf
import torch


@dataclass(frozen=True)
class AudioConfig:
    sample_rate: int = 16000
    seconds: float = 6.0
    n_fft: int = 512
    hop_length: int = 160
    n_mels: int = 64
    f_min: float = 60.0
    f_max: float = 7600.0

    def to_dict(self):
        return asdict(self)


def load_audio(source: Path | bytes, sample_rate: int = 16000) -> np.ndarray:
    data, rate = sf.read(io.BytesIO(source) if isinstance(source, bytes) else source,
                         dtype="float32", always_2d=True)
    if not len(data) or not np.isfinite(data).all():
        raise ValueError("音频为空或包含无效数值")
    if len(data) / rate > 900:
        raise ValueError("单个音频最长 15 分钟，请先分段")
    mono = data.mean(axis=1)
    if rate != sample_rate:
        divisor = math.gcd(rate, sample_rate)
        mono = resample_poly(mono, sample_rate // divisor, rate // divisor).astype(np.float32)
    return mono


def mel_filter(config: AudioConfig) -> torch.Tensor:
    to_mel = lambda hz: 2595 * np.log10(1 + hz / 700)
    to_hz = lambda mel: 700 * (10 ** (mel / 2595) - 1)
    edges = to_hz(np.linspace(to_mel(config.f_min), to_mel(config.f_max), config.n_mels + 2))
    frequencies = np.linspace(0, config.sample_rate / 2, config.n_fft // 2 + 1)
    bank = np.zeros((config.n_mels, len(frequencies)), np.float32)
    for i in range(config.n_mels):
        left, center, right = edges[i:i + 3]
        bank[i] = np.maximum(0, np.minimum((frequencies-left)/(center-left),
                                           (right-frequencies)/(right-center)))
        bank[i] *= 2 / (right-left)
    return torch.from_numpy(bank)


def log_mel(samples: np.ndarray, config: AudioConfig) -> torch.Tensor:
    """Fixed duration, DC removal, log-mel, per-clip standardization."""
    count = round(config.seconds * config.sample_rate)
    audio = np.asarray(samples, dtype=np.float32)[:count]
    audio = audio - audio.mean() if len(audio) else audio
    audio = np.pad(audio, (0, max(0, count - len(audio))))
    tensor = torch.from_numpy(audio)
    power = torch.stft(tensor, config.n_fft, config.hop_length,
                        window=torch.hann_window(config.n_fft), return_complex=True,
                        center=True, pad_mode="constant").abs().square()
    mel = torch.log(torch.clamp(mel_filter(config) @ power, min=1e-8))
    return (mel - mel.mean()) / mel.std(unbiased=False).clamp_min(.01)


def segment_audio(samples: np.ndarray, config: AudioConfig, *, max_segments: int = 20):
    """Non-overlapping windows; cover a long recording evenly without prefix bias."""
    length = round(config.seconds * config.sample_rate)
    if len(samples) < config.sample_rate * 3:
        raise ValueError("有效音频至少需要 3 秒")
    starts = list(range(0, max(1, len(samples)-length+1), length))
    if len(samples) > length and starts[-1] + length < len(samples):
        starts.append(len(samples)-length)
    if len(starts) > max_segments:
        starts = [starts[i] for i in np.linspace(0, len(starts)-1, max_segments).astype(int)]
    chunks = []
    for start in starts:
        chunk = samples[start:start+length]
        if np.sqrt(np.mean(chunk.astype(np.float64)**2)) < .003:
            continue
        chunks.append((start / config.sample_rate, chunk))
    if not chunks:
        raise ValueError("音频接近静音，请重新录制")
    return chunks
