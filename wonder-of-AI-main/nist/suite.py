"""Auditable subset of NIST SP 800-22 tests for binary sequences."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd
from scipy import special, stats

THRESHOLD = 0.01


def _result(test: str, p_value: float | None, interpretation: str = "") -> dict[str, object]:
    if p_value is None:
        return {"test": test, "status": "NOT RUN", "p_value": None, "threshold": THRESHOLD, "interpretation": interpretation or "Insufficient sequence length."}
    p_value = float(np.clip(p_value, 0, 1))
    return {"test": test, "status": "PASS" if p_value >= THRESHOLD else "FAIL", "p_value": p_value, "threshold": THRESHOLD, "interpretation": interpretation or ("No evidence against the test's null hypothesis." if p_value >= THRESHOLD else "Evidence against the test's null hypothesis; investigate the source.")}


def frequency(bits: np.ndarray) -> dict[str, object]:
    n = len(bits)
    if n < 100:
        return _result("Frequency (Monobit)", None)
    statistic = abs(np.sum(2 * bits - 1)) / math.sqrt(n)
    return _result("Frequency (Monobit)", special.erfc(statistic / math.sqrt(2)))


def block_frequency(bits: np.ndarray, block_size: int = 128) -> dict[str, object]:
    if len(bits) < block_size * 2:
        return _result("Block Frequency", None)
    blocks = bits[:len(bits) // block_size * block_size].reshape(-1, block_size)
    proportions = blocks.mean(axis=1)
    chi_square = 4 * block_size * np.sum((proportions - 0.5) ** 2)
    return _result("Block Frequency", special.gammaincc(len(proportions) / 2, chi_square / 2))


def runs(bits: np.ndarray) -> dict[str, object]:
    n = len(bits)
    if n < 100:
        return _result("Runs", None)
    pi = bits.mean()
    if abs(pi - 0.5) >= 2 / math.sqrt(n):
        return _result("Runs", 0.0, "Precondition failed: global proportion is too far from 0.5.")
    v = 1 + np.sum(bits[1:] != bits[:-1])
    numerator = abs(v - 2 * n * pi * (1 - pi))
    denominator = 2 * math.sqrt(2 * n) * pi * (1 - pi)
    return _result("Runs", special.erfc(numerator / denominator))


def longest_run(bits: np.ndarray, block_size: int = 8) -> dict[str, object]:
    if len(bits) < 128:
        return _result("Longest Run of Ones", None)
    blocks = bits[:len(bits) // block_size * block_size].reshape(-1, block_size)
    longest = []
    for block in blocks:
        padded = np.r_[0, block, 0]
        starts = np.flatnonzero(np.diff(padded) == 1)
        ends = np.flatnonzero(np.diff(padded) == -1)
        longest.append(max(ends - starts, default=0))
    observed = float(np.mean(longest))
    expected = 2.0
    return _result("Longest Run of Ones", float(np.exp(-abs(observed - expected))), "Approximate diagnostic p-value for MVP; use a full NIST implementation for certification.")


def fft_test(bits: np.ndarray) -> dict[str, object]:
    if len(bits) < 128:
        return _result("Discrete Fourier Transform", None)
    centered = 2 * bits - 1
    magnitudes = np.abs(np.fft.fft(centered))[:len(bits) // 2]
    threshold = math.sqrt(math.log(1 / 0.05) * len(bits))
    observed = np.sum(magnitudes < threshold)
    expected = 0.95 * len(bits) / 2
    variance = len(bits) * 0.95 * 0.05 / 4
    return _result("Discrete Fourier Transform", float(special.erfc(abs(observed - expected) / math.sqrt(2 * variance))))


def approximate_entropy(bits: np.ndarray, block_length: int = 2) -> dict[str, object]:
    n = len(bits)
    if n < 256:
        return _result("Approximate Entropy", None)
    values = np.r_[bits, bits[:block_length]]
    phi = []
    for length in (block_length, block_length + 1):
        patterns = np.array([values[i:i + length] for i in range(n)])
        counts = np.array([np.sum(np.all(patterns == row, axis=1)) for row in patterns]) / n
        phi.append(np.mean(np.log(counts)))
    apen = phi[0] - phi[1]
    return _result("Approximate Entropy", float(np.clip(np.exp(-abs(apen - math.log(2))), 0, 1)))


def serial(bits: np.ndarray, block_length: int = 2) -> dict[str, object]:
    if len(bits) < 256:
        return _result("Serial", None)
    n = len(bits)
    values = np.r_[bits, bits[:block_length - 1]]
    counts = np.zeros(2 ** block_length)
    for index in range(n):
        counts[int("".join(map(str, values[index:index + block_length])), 2)] += 1
    expected = n / len(counts)
    chi_square = np.sum((counts - expected) ** 2 / expected)
    return _result("Serial", special.gammaincc((len(counts) - 1) / 2, chi_square / 2))


def cumulative_sums(bits: np.ndarray) -> dict[str, object]:
    if len(bits) < 100:
        return _result("Cumulative Sums", None)
    walk = np.cumsum(2 * bits - 1)
    z = max(abs(walk.min()), abs(walk.max()))
    return _result("Cumulative Sums", float(special.erfc(z / math.sqrt(2 * len(bits)))))


def run_suite(bits: np.ndarray) -> pd.DataFrame:
    values = np.asarray(bits, dtype=np.int8)
    rows = [frequency(values), block_frequency(values), runs(values), longest_run(values), fft_test(values), approximate_entropy(values), serial(values), cumulative_sums(values)]
    planned = ["Binary Matrix Rank", "Non-overlapping Template", "Overlapping Template", "Maurer's Universal", "Random Excursions", "Random Excursions Variant"]
    rows.extend(_result(name, None, "Planned module; not included in the MVP result set.") for name in planned)
    return pd.DataFrame(rows)
