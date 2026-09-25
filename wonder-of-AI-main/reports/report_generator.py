"""Generate a compact, evidence-based PDF validation report."""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd


def generate_pdf(summary: dict[str, float], nist: pd.DataFrame, timeline: pd.DataFrame, diagnostics: dict[str, object], source_name: str, source_type: str, score: float, status: str) -> bytes:
    buffer = BytesIO()
    with PdfPages(buffer) as pdf:
        fig = plt.figure(figsize=(11.7, 8.3))
        fig.text(0.08, 0.88, "Q-GUARD", fontsize=28, weight="bold", color="#4f7cff")
        fig.text(0.08, 0.82, "Quantum Randomness Intelligence & Entropy Validation Platform", fontsize=13)
        fig.text(0.08, 0.74, f"Validation report | {datetime.now(timezone.utc).isoformat(timespec='seconds')}", fontsize=10, color="#566070")
        lines = [f"Source: {source_name} ({source_type})", f"QRNG health score: {score:.1f}/100  |  {status}", f"Bits analyzed: {summary.get('bits', 0):,}", f"Shannon entropy: {summary.get('shannon', 0):.4f} bits/bit", f"Min-entropy: {summary.get('min_entropy', 0):.4f} bits/bit", f"Bias: {summary.get('bias', 0) * 100:.3f}%", "", "Scientific limitation:", "Statistical tests validate observed statistical characteristics. They do not establish quantum origin."]
        fig.text(0.08, 0.62, "\n".join(lines), fontsize=13, linespacing=1.65, va="top")
        pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)
        fig, axes = plt.subplots(1, 2, figsize=(11.7, 8.3))
        if not timeline.empty:
            axes[0].plot(timeline["window"], timeline["shannon"], color="#4f7cff", label="Shannon")
            axes[0].plot(timeline["window"], timeline["min_entropy"], color="#21c7a8", label="Min entropy")
            axes[0].set_title("Windowed entropy"); axes[0].set_xlabel("Window"); axes[0].set_ylabel("bits/bit"); axes[0].legend()
        plotted = nist[nist["p_value"].notna()]
        axes[1].barh(plotted["test"], plotted["p_value"], color=["#21c7a8" if s == "PASS" else "#ef6a6a" for s in plotted["status"]])
        axes[1].axvline(0.01, color="#ef6a6a", linestyle="--"); axes[1].set_title("NIST p-values"); axes[1].set_xlabel("p-value")
        pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)
        fig = plt.figure(figsize=(11.7, 8.3)); fig.text(0.08, 0.9, "Diagnostics and recommendations", fontsize=22, weight="bold")
        body = ["Evidence:"] + [f"- {item}" for item in diagnostics.get("findings", [])] + ["", "Likely causes:"] + [f"- {item}" for item in diagnostics.get("likely_causes", [])] + ["", "Recommendations:"] + [f"- {item}" for item in diagnostics.get("recommendations", [])]
        fig.text(0.08, 0.82, "\n".join(body), fontsize=12, va="top", linespacing=1.55); pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)
    return buffer.getvalue()
