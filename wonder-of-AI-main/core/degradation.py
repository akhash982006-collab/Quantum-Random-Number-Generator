"""Window-based degradation detection and alert generation."""
from __future__ import annotations

import pandas as pd


def analyze_degradation(timeline: pd.DataFrame, baseline_windows: int = 2) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    if timeline.empty:
        return timeline.assign(degradation_score=[]), []
    frame = timeline.copy()
    baseline = frame.head(min(baseline_windows, len(frame)))
    baseline_entropy = float(baseline["shannon"].mean())
    baseline_bias = float(baseline["bias"].mean())
    baseline_corr = float(baseline["autocorrelation"].abs().mean())
    frame["entropy_delta"] = baseline_entropy - frame["shannon"]
    frame["degradation_score"] = (frame["entropy_delta"].clip(lower=0) * 70 + (frame["bias"] - baseline_bias).clip(lower=0) * 100 + (frame["autocorrelation"].abs() - baseline_corr).clip(lower=0) * 30).clip(0, 100)
    frame["health_score"] = (100 - frame["degradation_score"]).round(1)
    frame["status"] = frame["health_score"].map(lambda score: "HEALTHY" if score >= 90 else "WATCH" if score >= 75 else "WARNING" if score >= 50 else "DEGRADED" if score >= 25 else "CRITICAL")
    alerts = []
    for _, row in frame.iterrows():
        if row["status"] != "HEALTHY":
            alerts.append({"window": str(int(row["window"])), "status": str(row["status"]), "message": f"Window {int(row['window'])}: entropy {row['shannon']:.3f}, bias {row['bias'] * 100:.2f}%, autocorrelation {row['autocorrelation']:.3f}."})
    return frame, alerts
