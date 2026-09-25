from __future__ import annotations

import io
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.degradation import analyze_degradation
from core.diagnostics import diagnose
from core.entropy import metrics, window_metrics
from core.health_score import overall_score, score_components, status_for
from core.preprocessing import ingest_bytes
from core.simulator import degrading_stream, generate_stream
from nist.suite import run_suite
from reports.report_generator import generate_pdf
from ui.charts import entropy_chart, health_chart
from ui.components import metric_card, status_badge

st.set_page_config(page_title="Q-Guard | Entropy Validation", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root { --ink:#e7edf7; --muted:#8d9ab0; --panel:#111925; --panel2:#172334; --line:#26364b; --blue:#5b8cff; --mint:#22c7a8; --gold:#e6b85c; --red:#ef6a6a; }
html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
.stApp { background: radial-gradient(circle at 75% 0%, #1b2d4a 0, #0a1019 38%, #080d14 100%); color:var(--ink); }
[data-testid="stSidebar"] { background:#0b121d; border-right:1px solid var(--line); }
[data-testid="stSidebar"] * { color:var(--ink); }
h1,h2,h3 { letter-spacing:0; } h1 { font-size:2.6rem; } h2 { margin-top:1rem; }
.metric-card { background:linear-gradient(145deg,#152235,#101824); border:1px solid var(--line); border-radius:8px; padding:17px 18px; min-height:112px; box-shadow:0 8px 30px #05091055; }
.metric-label { color:var(--muted); font-size:.77rem; text-transform:uppercase; letter-spacing:.08em; } .metric-value { font-size:1.7rem; font-weight:600; margin-top:10px; } .metric-detail { color:var(--muted); font-family:'DM Mono'; font-size:.72rem; margin-top:5px; }
.badge { display:inline-block; padding:5px 10px; border-radius:20px; font-family:'DM Mono'; font-size:.75rem; } .good { color:#91f0d5; background:#123c3a; } .warn { color:#f4d88d; background:#433919; } .bad { color:#ff9e9e; background:#4a2027; }
.callout { border-left:3px solid var(--gold); background:#1c2735; padding:14px 16px; border-radius:0 6px 6px 0; color:#cad4e3; }
.smallcaps { color:var(--muted); text-transform:uppercase; letter-spacing:.12em; font-size:.72rem; } .mono { font-family:'DM Mono'; }
div[data-testid="stMetric"] { background:var(--panel); border:1px solid var(--line); padding:14px; border-radius:8px; }
.stButton > button, .stDownloadButton > button { border-radius:5px; border:1px solid #385987; background:#17315a; color:#eaf1ff; } .stButton > button:hover { border-color:var(--blue); color:white; }
</style>
""", unsafe_allow_html=True)


def initialize():
    if "bits" not in st.session_state:
        st.session_state.bits = generate_stream("Ideal random", 65536)
        st.session_state.source_name = "SIMULATED / ideal random"
        st.session_state.source_type = "simulated data"
    if "window_size" not in st.session_state:
        st.session_state.window_size = 4096


def analyze():
    bits = st.session_state.bits
    summary = metrics(bits)
    timeline = window_metrics(bits, st.session_state.window_size)
    timeline, alerts = analyze_degradation(timeline)
    nist = run_suite(bits)
    components = score_components(summary, nist, timeline)
    score = overall_score(components)
    diagnostics = diagnose(summary, nist, timeline)
    st.session_state.analysis = {"summary": summary, "timeline": timeline, "alerts": alerts, "nist": nist, "components": components, "score": score, "status": status_for(score), "diagnostics": diagnostics}
    return st.session_state.analysis


def get_analysis():
    return st.session_state.get("analysis") or analyze()


def sidebar():
    with st.sidebar:
        st.markdown("# ◈ Q-GUARD")
        st.caption("Quantum Randomness Intelligence")
        st.markdown("---")
        page = st.radio("Navigate", ["Overview", "Data Ingestion", "Entropy Analysis", "NIST Test Suite", "Degradation Monitor", "Root Cause Analysis", "Simulation Lab", "Reports", "Methodology"], label_visibility="collapsed")
        st.markdown("---")
        st.markdown('<div class="smallcaps">Data provenance</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="mono">{st.session_state.source_name}</div>', unsafe_allow_html=True)
        st.caption("Statistical validation ≠ proof of quantum origin.")
    return page


def header(title: str, eyebrow: str):
    st.markdown(f'<div class="smallcaps">{eyebrow}</div>', unsafe_allow_html=True)
    st.title(title)


def overview(analysis):
    header("Entropy validation, at a glance", "CONTROL ROOM / OVERVIEW")
    summary = analysis["summary"]
    cols = st.columns(6)
    cards = [("Bits analyzed", f"{summary['bits']:,}", st.session_state.source_type), ("Shannon entropy", f"{summary['shannon']:.4f}", "bits per bit"), ("Min entropy", f"{summary['min_entropy']:.4f}", "worst-case estimate"), ("NIST pass rate", f"{(analysis['nist']['status'] == 'PASS').mean() * 100:.0f}%", "implemented tests"), ("Health score", f"{analysis['score']:.1f}/100", analysis['status']), ("Current status", analysis['status'], "observed stream")]
    for col, (label, value, detail) in zip(cols, cards):
        with col: metric_card(label, value, detail)
    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns([1.55, 1])
    with left: st.plotly_chart(entropy_chart(analysis["timeline"]), use_container_width=True)
    with right:
        st.markdown("### Evidence boundary")
        st.markdown('<div class="callout"><b>This platform validates statistical and entropy characteristics.</b><br><br>Statistical tests alone cannot establish that the randomness originated from a quantum process.</div>', unsafe_allow_html=True)
        st.markdown("### Health components")
        for name, value in analysis["components"].items(): st.progress(value / 100, text=f"{name}  {value:.0f}")
    st.plotly_chart(health_chart(analysis["timeline"]), use_container_width=True)


def ingestion_page():
    header("Bring your raw stream into the lab", "PIPELINE / DATA INGESTION")
    st.markdown("Upload CSV, TXT, or raw bytes. Q-Guard reports invalid values and preprocessing instead of silently repairing the source.")
    uploaded = st.file_uploader("Raw QRNG feed", type=["csv", "txt", "bin", "dat"])
    if uploaded and st.button("Analyze uploaded stream", type="primary"):
        result = ingest_bytes(uploaded.getvalue(), uploaded.name)
        if result.bits.size:
            st.session_state.bits = result.bits; st.session_state.source_name = uploaded.name; st.session_state.source_type = result.source_type; st.session_state.ingestion = result; st.session_state.analysis = None; st.rerun()
        else: st.error("No usable 0/1 values were found in the uploaded input.")
    result = st.session_state.get("ingestion")
    if result:
        st.markdown("### Validation report")
        cols = st.columns(4)
        for col, label, value in zip(cols, ["Status", "Source type", "Invalid values", "Repeated sections"], [result.status, result.source_type, result.invalid_values, result.duplicate_sections]):
            with col: metric_card(label, str(value), "reported from raw input")
        st.markdown("**Preprocessing performed**"); st.write("\n".join(f"- {item}" for item in result.preprocessing))
        st.markdown("**Preview (first 256 analyzed bits)**"); st.code(result.preview or "No bits")
    else: st.info("No external stream loaded. Use Simulation Lab for a deterministic demo dataset.")


def entropy_page(analysis):
    header("Where entropy changes over time", "ANALYSIS / WINDOWED ENTROPY")
    st.plotly_chart(entropy_chart(analysis["timeline"]), use_container_width=True)
    frame = analysis["timeline"]
    if frame.empty: return
    cols = st.columns(4)
    for col, label, value in zip(cols, ["Lowest Shannon", "Lowest min entropy", "Peak bias", "Peak correlation"], [frame.shannon.min(), frame.min_entropy.min(), frame.bias.max() * 100, frame.autocorrelation.abs().max()]):
        with col: metric_card(label, f"{value:.4f}", "windowed measurement")
    st.dataframe(frame[["window", "start", "end", "shannon", "min_entropy", "bias", "autocorrelation", "health_score", "status"]], use_container_width=True, hide_index=True)


def nist_page(analysis):
    header("NIST SP 800-22 test suite", "VALIDATION / STATISTICAL HEALTH")
    st.markdown('<div class="callout">A PASS means the observed sequence did not provide evidence against that test\'s null hypothesis at p ≥ 0.01. It does not prove true randomness or quantum origin.</div>', unsafe_allow_html=True)
    st.dataframe(analysis["nist"].style.format({"p_value": lambda v: "—" if pd.isna(v) else f"{v:.4f}", "threshold": "{:.2f}"}), use_container_width=True, hide_index=True)
    plotted = analysis["nist"].dropna(subset=["p_value"])
    fig = go.Figure(go.Bar(x=plotted.p_value, y=plotted.test, orientation="h", marker_color=["#22c7a8" if x == "PASS" else "#ef6a6a" for x in plotted.status]))
    fig.add_vline(x=0.01, line_dash="dash", line_color="#e6b85c"); fig.update_layout(template="plotly_dark", height=420, title="Observed p-values | threshold = 0.01")
    st.plotly_chart(fig, use_container_width=True)


def degradation_page(analysis):
    header("Catch degradation before it becomes an outage", "MONITOR / DEGRADATION")
    status_badge(analysis["status"])
    st.markdown(f"### Current score: {analysis['score']:.1f} / 100")
    st.plotly_chart(health_chart(analysis["timeline"]), use_container_width=True)
    if analysis["alerts"]:
        st.warning(f"Degradation detected across {len(analysis['alerts'])} window(s). First signal: window {analysis['alerts'][0]['window']}.")
        st.dataframe(pd.DataFrame(analysis["alerts"]), use_container_width=True, hide_index=True)
    else: st.success("No configured degradation threshold exceeded in the current stream.")


def root_cause_page(analysis):
    header("Turn anomalies into evidence", "DIAGNOSTICS / ROOT CAUSE")
    diagnostic = analysis["diagnostics"]
    st.markdown("### Evidence"); [st.markdown(f"- {item}") for item in diagnostic["findings"]]
    left, right = st.columns(2)
    with left:
        st.markdown("### Likely causes"); [st.markdown(f"**{index}.** {item}") for index, item in enumerate(diagnostic["likely_causes"], 1)]
    with right:
        st.markdown("### Recommendations"); [st.markdown(f"- {item}") for item in diagnostic["recommendations"]]
    st.caption("These are data-supported hypotheses, not claims of physical hardware failure.")


def simulation_page():
    header("Make degradation visible", "LAB / SIMULATION")
    st.markdown("Every generated stream is synthetic and labeled as such. This lab demonstrates the validation pipeline; it does not produce quantum randomness.")
    tab1, tab2 = st.tabs(["Stream generator", "Entropy attack demo"])
    with tab1:
        mode = st.selectbox("Simulation profile", ["Ideal random", "Biased", "Repeating pattern", "Correlated", "Burst error", "Low entropy"])
        size = st.slider("Bits", 4096, 262144, 65536, step=4096)
        if st.button("Generate simulated stream", type="primary"):
            st.session_state.bits = generate_stream(mode, size); st.session_state.source_name = f"SIMULATED / {mode}"; st.session_state.source_type = "simulated data"; st.session_state.analysis = None; st.rerun()
    with tab2:
        st.markdown("Healthy windows gradually become biased and correlated, then the dashboard surfaces the exact start of degradation.")
        if st.button("Run entropy attack", type="primary"):
            st.session_state.bits = degrading_stream(); st.session_state.source_name = "SIMULATED / entropy attack"; st.session_state.source_type = "simulated data"; st.session_state.analysis = None; st.rerun()
        if st.button("Restore health"):
            st.session_state.bits = generate_stream("Ideal random", 65536); st.session_state.source_name = "SIMULATED / restored ideal"; st.session_state.source_type = "simulated data"; st.session_state.analysis = None; st.rerun()
    st.markdown("### Current stream preview"); st.code("".join(map(str, st.session_state.bits[:512])))


def reports_page(analysis):
    header("Package the evidence", "OUTPUT / REPORTS")
    st.markdown("Generate a PDF report and export the measured tables used in this session.")
    pdf = generate_pdf(analysis["summary"], analysis["nist"], analysis["timeline"], analysis["diagnostics"], st.session_state.source_name, st.session_state.source_type, analysis["score"], analysis["status"])
    st.download_button("Download validation report (PDF)", pdf, "qguard_validation_report.pdf", "application/pdf", type="primary")
    st.download_button("Download NIST results (CSV)", analysis["nist"].to_csv(index=False), "qguard_nist_results.csv", "text/csv")
    st.download_button("Download window metrics (CSV)", analysis["timeline"].to_csv(index=False), "qguard_window_metrics.csv", "text/csv")
    st.download_button("Download analyzed bits (CSV)", pd.DataFrame({"bit": st.session_state.bits}).to_csv(index=False), "qguard_analyzed_bits.csv", "text/csv")


def methodology_page():
    header("Methodology and limits", "REFERENCE / SCIENTIFIC INTEGRITY")
    st.markdown("""
### What Q-Guard measures
**Entropy** quantifies uncertainty in the observed output. Shannon entropy describes average uncertainty; min-entropy describes the strongest single-value concentration. Bias, runs, autocorrelation, and sliding windows expose structure that a single aggregate score can hide.

### What the NIST results mean
Q-Guard implements Frequency, Block Frequency, Runs, Longest Run, DFT, Approximate Entropy, Serial, and Cumulative Sums tests for this MVP. Tests marked **NOT RUN** are planned because their full parameterization and sequence-length requirements are not included yet. A p-value below 0.01 flags evidence against the test's null hypothesis for this sample; it is not a proof of failure or of quantum origin.

### What this can and cannot prove
This platform validates statistical and entropy characteristics of a QRNG output. Statistical tests alone cannot establish that the randomness originated from a quantum process. Quantum-origin verification requires trusted physical design, calibration, provenance, and an appropriate experimental protocol.

### Architecture boundary
A future optical integration can replace the simulator with an acquisition adapter for a photon source, beam splitter, single-photon detector, photon electronics, ADC, and USB/serial/network stream. The validation pipeline remains downstream of ingestion.
""")

initialize()
page = sidebar()
analysis = get_analysis()
if page == "Overview": overview(analysis)
elif page == "Data Ingestion": ingestion_page()
elif page == "Entropy Analysis": entropy_page(analysis)
elif page == "NIST Test Suite": nist_page(analysis)
elif page == "Degradation Monitor": degradation_page(analysis)
elif page == "Root Cause Analysis": root_cause_page(analysis)
elif page == "Simulation Lab": simulation_page()
elif page == "Reports": reports_page(analysis)
elif page == "Methodology": methodology_page()
