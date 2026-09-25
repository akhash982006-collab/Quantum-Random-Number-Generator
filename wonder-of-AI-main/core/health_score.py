"""Transparent health scoring; each component is derived from observed metrics."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _clamp(value: float) -> float:
    return float(np.clip(value, 0, 100))


def score_components(summary: dict[str, float], nist: pd.DataFrame, timeline: pd.DataFrame | None = None) -> dict[str, float]:
    nist_run = float((nist["status"] == "PASS").mean() * 100) if len(nist) else 0.0
    entropy = _clamp(summary.get("shannon", 0) * 55 + summary.get("min_entropy", 0) * 45)
    bias = _clamp(100 - summary.get("bias", 1) * 200)
    correlation = _clamp(100 - abs(summary.get("autocorrelation", 1)) * 100)
    stability = 100.0
    if timeline is not None and len(timeline) > 1:
        volatility = float(timeline["shannon"].diff().abs().mean())
        stability = _clamp(100 - volatility * 500)
    return {"Statistical Health": _clamp(nist_run), "Entropy Health": entropy, "Bias Health": bias, "Correlation Health": correlation, "Stability Health": stability}


def overall_score(components: dict[str, float]) -> float:
    weights = {"Statistical Health": 0.25, "Entropy Health": 0.30, "Bias Health": 0.15, "Correlation Health": 0.15, "Stability Health": 0.15}
    return round(sum(components.get(key, 0) * weight for key, weight in weights.items()), 1)


def status_for(score: float) -> str:
    if score >= 90:
        return "HEALTHY"
    if score >= 75:
        return "STABLE / WATCH"
    if score >= 50:
        return "WARNING"
    if score >= 25:
        return "DEGRADED"
    return "CRITICAL"
