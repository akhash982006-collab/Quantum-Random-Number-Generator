import streamlit as st

CSS='''<style>
.stApp {background:#090f1d;color:#e3eafb}
[data-testid="stSidebar"] {background:#0e1628;border-right:1px solid #25314b}
[data-testid="stMetric"] {background:#121c30;border:1px solid #283551;border-radius:12px;padding:16px}
[data-testid="stMetricLabel"] {color:#91a6c9;letter-spacing:.06em}
[data-testid="stMetricValue"] {font-size:1.6rem}
h1 {letter-spacing:-.035em} h2,h3 {color:#e3eafb}
.eyebrow {color:#8aafff;font-size:12px;letter-spacing:.2em;font-weight:600}
.hero {background:linear-gradient(115deg,#14223e,#1e1938);border:1px solid #354367;border-radius:16px;padding:25px;margin-bottom:24px}
.hero p {color:#aebbd3;margin-bottom:0}
.stButton>button {border-radius:8px;border-color:#3b4b70}
</style>'''

def header():
    st.markdown(CSS,unsafe_allow_html=True)
    st.markdown('<div class="hero"><div class="eyebrow">Q-GAURD / RELIABILITY INTELLIGENCE</div><h1>QRNG Reliability Command Center</h1><p>Detect the change. Trace the evidence. Investigate with confidence.</p></div>',unsafe_allow_html=True)

def cards(result):
    rows=result['windows']; latest=rows[-1] if rows else {}
    cols=st.columns(6); overall=result['overall']; health=latest.get('health'); rate=latest.get('nist_pass_rate')
    values=[('HEALTH SCORE','—' if health is None else f'{health:.1f}/100'),('SHANNON',f"{latest.get('shannon',overall['shannon']):.4f}"),('MARGINAL MIN',f"{latest.get('min_entropy',overall['min_entropy']):.4f}"),('WINDOW NIST','—' if rate is None else f'{rate:.0%}'),('STATE',latest.get('state','Insufficient Data')),('CHANGE EVENTS',str(sum(e['kind']=='Change point' for e in result['events'])))]
    for c,(label,value) in zip(cols,values): c.metric(label,value)
    st.caption('Latest complete window. Entropies are empirical bits/bit; marginal estimates do not establish usable cryptographic entropy.')
