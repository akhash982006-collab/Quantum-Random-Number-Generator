"""Transparent synthetic streams for demos; none represent quantum-origin data."""
from __future__ import annotations

import numpy as np

MODES = ["Ideal random", "Biased", "Repeating pattern", "Correlated", "Burst error", "Low entropy"]


def generate_stream(mode: str, bits: int = 65536, seed: int = 42, bias: float = 0.12, correlation: float = 0.8, pattern_length: int = 8, burst_rate: float = 0.03) -> np.ndarray:
    if bits < 64:
        raise ValueError("Generate at least 64 bits.")
    rng = np.random.default_rng(seed)
    if mode == "Ideal random":
        return rng.integers(0, 2, bits, dtype=np.int8)
    if mode == "Biased":
        return (rng.random(bits) < min(max(0.5 + bias, 0), 1)).astype(np.int8)
    if mode == "Repeating pattern":
        pattern = rng.integers(0, 2, max(2, pattern_length), dtype=np.int8)
        return np.resize(pattern, bits)
    if mode == "Correlated":
        values = np.empty(bits, dtype=np.int8)
        values[0] = rng.integers(0, 2)
        for index in range(1, bits):
            values[index] = values[index - 1] if rng.random() < correlation else rng.integers(0, 2)
        return values
    if mode == "Burst error":
        values = rng.integers(0, 2, bits, dtype=np.int8)
        burst_length = max(8, int(bits * burst_rate))
        for start in range(0, bits, max(burst_length * 8, 1)):
            if rng.random() < 0.65:
                values[start:start + burst_length] = rng.integers(0, 2)
        return values
    if mode == "Low entropy":
        return (rng.random(bits) < 0.96).astype(np.int8)
    raise ValueError(f"Unknown simulation mode: {mode}")


def degrading_stream(bits: int = 131072, windows: int = 32, seed: int = 42) -> np.ndarray:
    """Healthy-to-degraded stream with explicit, deterministic window progression."""
    rng = np.random.default_rng(seed)
    chunks = []
    window_size = bits // windows
    for index in range(windows):
        level = index / max(windows - 1, 1)
        if level < 0.35:
            chunk = rng.integers(0, 2, window_size, dtype=np.int8)
        elif level < 0.65:
            bias = 0.5 + 0.16 * (level - 0.35) / 0.3
            chunk = (rng.random(window_size) < bias).astype(np.int8)
        else:
            corr = min(0.97, 0.35 + 0.6 * (level - 0.65) / 0.35)
            chunk = generate_stream("Correlated", window_size, seed + index, correlation=corr)
        chunks.append(chunk)
    return np.concatenate(chunks)[:bits]
