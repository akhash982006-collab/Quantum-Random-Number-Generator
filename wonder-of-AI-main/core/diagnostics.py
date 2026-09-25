"""Explainable diagnostics based on measured evidence, not hardware claims."""
from __future__ import annotations

import pandas as pd


def diagnose(summary: dict[str, float], nist: pd.DataFrame, timeline: pd.DataFrame) -> dict[str, object]:
    findings: list[str] = []
    causes: list[str] = []
    recommendations: list[str] = []
    if summary.get("bias", 0) > 0.03:
        findings.append(f"Bit bias is {summary['bias'] * 100:.2f}% from a balanced source.")
        causes.append("Bit bias")
        recommendations.append("Inspect detector thresholding and optical intensity balance before post-processing.")
    if abs(summary.get("autocorrelation", 0)) > 0.08:
        findings.append(f"Lag-1 autocorrelation is {summary['autocorrelation']:.3f}.")
        causes.append("Increased correlation")
        recommendations.append("Check acquisition timing, clock coupling, and conditioning stages.")
    if summary.get("shannon", 0) < 0.92:
        findings.append(f"Shannon entropy is {summary['shannon']:.3f} bits/bit.")
        causes.append("Reduced entropy")
    failed = nist.loc[nist["status"] == "FAIL", "test"].tolist() if not nist.empty else []
    if failed:
        findings.append("Failed statistical tests: " + ", ".join(failed) + ".")
        causes.append("Statistical instability")
        recommendations.append("Capture a longer raw sample and compare failures across adjacent windows.")
    if not findings:
        findings.append("No configured threshold exceeded in the current sample.")
        recommendations.append("Continue windowed monitoring and retain raw samples for traceability.")
    if timeline is not None and len(timeline) > 2 and timeline["shannon"].iloc[-1] < timeline["shannon"].iloc[0] - 0.05:
        causes.append("Gradual degradation")
        recommendations.append("Investigate environmental drift and detector stability over the degradation interval.")
    return {"findings": findings, "likely_causes": list(dict.fromkeys(causes)), "recommendations": list(dict.fromkeys(recommendations))}
