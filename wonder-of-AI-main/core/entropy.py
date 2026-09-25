"""Entropy and bitstream metrics used throughout Q-Guard."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _bits(bits: np.ndarray | list[int]) -> np.ndarray:
    values = np.asarray(bits, dtype=np.int8).ravel()
    return values[(values == 0) | (values == 1)]


def shannon_entropy(bits: np.ndarray | list[int]) -> float:
    values = _bits(bits)
    if values.size == 0:
        return 0.0
    counts = np.bincount(values, minlength=2) / values.size
    return float(-sum(p * np.log2(p) for p in counts if p > 0))


def min_entropy(bits: np.ndarray | list[int]) -> float:
    values = _bits(bits)
    if values.size == 0:
        return 0.0
    max_probability = float(np.max(np.bincount(values, minlength=2) / values.size))
    return float(-np.log2(max_probability)) if max_probability else 0.0


def collision_entropy(bits: np.ndarray | list[int]) -> float:
    values = _bits(bits)
    if values.size == 0:
        return 0.0
    probabilities = np.bincount(values, minlength=2) / values.size
    return float(-np.log2(np.sum(probabilities**2)))


def run_metrics(bits: np.ndarray | list[int]) -> dict[str, float]:
    values = _bits(bits)
    if values.size == 0:
        return {"count": 0, "mean_length": 0.0, "max_length": 0.0, "runs": 0.0}
    changes = np.r_[True, values[1:] != values[:-1]]
    starts = np.flatnonzero(changes)
    lengths = np.diff(np.r_[starts, values.size])
    return {"count": float(len(lengths)), "mean_length": float(np.mean(lengths)), "max_length": float(np.max(lengths)), "runs": float(len(lengths))}


def autocorrelation(bits: np.ndarray | list[int], lag: int = 1) -> float:
    values = _bits(bits).astype(float)
    if values.size <= lag or np.std(values) == 0:
        return 0.0
    return float(np.corrcoef(values[:-lag], values[lag:])[0, 1])


def metrics(bits: np.ndarray | list[int]) -> dict[str, float]:
    values = _bits(bits)
    ones = int(values.sum()) if values.size else 0
    zeros = int(values.size - ones)
    return {
        "bits": int(values.size),
        "bytes": int(values.size // 8),
        "zeros": zeros,
        "ones": ones,
        "zero_pct": float(zeros / values.size * 100) if values.size else 0.0,
        "one_pct": float(ones / values.size * 100) if values.size else 0.0,
        "shannon": shannon_entropy(values),
        "min_entropy": min_entropy(values),
        "collision_entropy": collision_entropy(values),
        "bias": float(abs(ones / values.size - 0.5) * 2) if values.size else 1.0,
        "autocorrelation": autocorrelation(values),
        **run_metrics(values),
    }


def window_metrics(bits: np.ndarray, window_size: int = 4096) -> pd.DataFrame:
    values = _bits(bits)
    if window_size < 64:
        raise ValueError("Window size must be at least 64 bits.")
    rows = []
    for start in range(0, len(values), window_size):
        chunk = values[start:start + window_size]
        if len(chunk) < min(window_size, 64):
            continue
        item = metrics(chunk)
        item.update({"window": len(rows) + 1, "start": start, "end": start + len(chunk)})
        rows.append(item)
    return pd.DataFrame(rows)
