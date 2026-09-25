from __future__ import annotations
import streamlit as st

CSS = '''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --ink: #e7edf7;
    --muted: #8d9ab0;
    --panel: #111925;
    --panel2: #172334;
    --line: #26364b;
    --blue: #5b8cff;
    --mint: #22c7a8;
    --gold: #e6b85c;
    --red: #ef6a6a;
}

html, body, [class*="css"] {
    font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
}

.stApp {
    background: radial-gradient(circle at 75% 0%, #1b2d4a 0, #0a1019 38%, #080d14 100%);
    color: var(--ink);
}

[data-testid="stSidebar"] {
    background: #0b121d;
    border-right: 1px solid var(--line);
}

[data-testid="stSidebar"] * {
    color: var(--ink);
}

h1, h2, h3 {
    letter-spacing: -0.01em;
    color: var(--ink);
}

h1 {
    font-size: 2.4rem;
}

h2 {
    margin-top: 1rem;
}

.metric-card {
    background: linear-gradient(145deg, #152235, #101824);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 16px 18px;
    min-height: 110px;
    box-shadow: 0 8px 30px rgba(5, 9, 16, 0.4);
    transition: transform 0.15s ease, border-color 0.15s ease;
}

.metric-card:hover {
    border-color: rgba(91, 140, 255, 0.4);
}

.metric-label {
    color: var(--muted);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 500;
}

.metric-value {
    font-size: 1.65rem;
    font-weight: 600;
    margin-top: 8px;
    color: var(--ink);
}

.metric-detail {
    color: var(--muted);
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    margin-top: 5px;
}

.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 20px;
    font-family: 'DM Mono', monospace;
    font-size: 0.75rem;
    font-weight: 500;
    letter-spacing: 0.04em;
}

.good {
    color: #91f0d5;
    background: #123c3a;
    border: 1px solid #1a5653;
}

.warn {
    color: #f4d88d;
    background: #433919;
    border: 1px solid #665726;
}

.bad {
    color: #ff9e9e;
    background: #4a2027;
    border: 1px solid #73313d;
}

.callout {
    border-left: 3px solid var(--gold);
    background: #1c2735;
    padding: 14px 16px;
    border-radius: 0 6px 6px 0;
    color: #cad4e3;
    margin: 12px 0;
}

.smallcaps {
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 0.72rem;
    font-weight: 600;
}

.mono {
    font-family: 'DM Mono', monospace;
}

div[data-testid="stMetric"] {
    background: linear-gradient(145deg, #152235, #101824);
    border: 1px solid var(--line);
    padding: 16px 18px;
    border-radius: 8px;
    box-shadow: 0 6px 20px rgba(5, 9, 16, 0.3);
}

div[data-testid="stMetricLabel"] {
    color: var(--muted) !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

div[data-testid="stMetricValue"] {
    font-size: 1.65rem !important;
    font-weight: 600 !important;
    color: var(--ink) !important;
}

.stButton > button, .stDownloadButton > button {
    border-radius: 6px;
    border: 1px solid #385987;
    background: #17315a;
    color: #eaf1ff;
    font-weight: 500;
    transition: background 0.15s ease, border-color 0.15s ease;
}

.stButton > button:hover, .stDownloadButton > button:hover {
    border-color: var(--blue);
    background: #204177;
    color: white;
}
</style>'''

def metric_card(label: str, value: str, detail: str = ""):
    """Render a styled metric card from wonder-of-AI design system."""
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-detail">{detail}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

def status_badge(status: str) -> str:
    """Return HTML string for a colored status badge."""
    s_upper = status.upper()
    tone = "good" if s_upper in {"HEALTHY", "PASS", "NORMAL"} else "warn" if any(w in s_upper for w in ["WARN", "WATCH", "STABLE", "EARLY"]) else "bad"
    return f'<span class="badge {tone}">{status}</span>'

def header(title: str = "QRNG Reliability Command Center", eyebrow: str = "Q-GAURD / RELIABILITY INTELLIGENCE"):
    """Render top header banner with wonder-of-AI typography."""
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        f'<div style="margin-bottom:24px;">'
        f'<div class="smallcaps">{eyebrow}</div>'
        f'<h1 style="margin:4px 0 6px 0;">{title}</h1>'
        f'<p style="color:var(--muted); margin:0; font-size:1.02rem;">Detect the change. Trace the evidence. Investigate with confidence.</p>'
        f'</div>',
        unsafe_allow_html=True
    )

def cards(result):
    """Render top 6 summary metrics with wonder-of-AI metric cards and badges."""
    rows = result['windows']
    latest = rows[-1] if rows else {}
    cols = st.columns(6)
    overall = result['overall']
    health = latest.get('health')
    rate = latest.get('nist_pass_rate')
    state = latest.get('state', 'Insufficient Data')
    
    items = [
        ('HEALTH SCORE', '—' if health is None else f'{health:.1f}/100', 'operational health'),
        ('SHANNON', f"{latest.get('shannon', overall['shannon']):.4f}", 'bits per bit'),
        ('MARGINAL MIN', f"{latest.get('min_entropy', overall['min_entropy']):.4f}", 'worst-case estimate'),
        ('WINDOW NIST', '—' if rate is None else f'{rate:.0%}', 'family pass rate'),
        ('CURRENT STATUS', state, 'observed stream'),
        ('CHANGE EVENTS', str(sum(e['kind'] == 'Change point' for e in result['events'])), 'cusum trigger count')
    ]
    
    for col, (label, val, detail) in zip(cols, items):
        with col:
            if label == 'CURRENT STATUS' and state != 'Insufficient Data':
                badge_html = status_badge(state)
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-label">{label}</div>'
                    f'<div class="metric-value" style="font-size:1.25rem; margin-top:8px;">{badge_html}</div>'
                    f'<div class="metric-detail">{detail}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            else:
                metric_card(label, val, detail)
                
    st.caption('Latest complete window. Entropies are empirical bits/bit; marginal estimates do not establish usable cryptographic entropy.')
