from __future__ import annotations

import streamlit as st


def metric_card(label: str, value: str, detail: str = ""):
    st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-detail">{detail}</div></div>', unsafe_allow_html=True)


def status_badge(status: str):
    tone = "good" if status in {"HEALTHY", "PASS"} else "warn" if status in {"WATCH", "STABLE / WATCH", "WARNING"} else "bad"
    st.markdown(f'<span class="badge {tone}">{status}</span>', unsafe_allow_html=True)
