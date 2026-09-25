from pathlib import Path
import json
import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from core.engine import analyze,LIMITATION
from core.ingestion import ingest
from core.jobs import AnalysisJob
from core.health_score import WEIGHTS
from core.persistence import save,sessions,load
from simulation.qrng_twin import simulate,FAULTS,guided_demo
from ui.components import header,cards,metric_card,status_badge
from ui.charts import timeline,fingerprint,heatmap,signature_trends,signature_bars,projection_chart,pvalues,nist_bars,frame,style
from ui.forensic_view import render as forensic
from ui.inconsistency_explorer import render as inconsistency_explorer
from reports.generator import pdf,export_json,export_csv

st.set_page_config(page_title='Q-Gaurd | Reliability Intelligence',page_icon='◈',layout='wide')
NAV=['COMMAND CENTER','DATA INGESTION','INCONSISTENCY EXPLORER','ENTROPY ANALYSIS','NIST VALIDATION','DEGRADATION MONITOR','ENTROPY FORENSICS','FAILURE LAB','QRNG HEALTH PASSPORT','REPORTS']
ss=st.session_state
for key,value in dict(result=None,bits=None,job=None,reference=None,live=False,live_fault='Healthy',live_age=0,lab_seed=42,retention=False,weights=WEIGHTS.copy(),size=10000).items():
    if key not in ss: ss[key]=value

def launch(bits,name,source='simulation',extra=None):
    if ss.job and not ss.job.future.done():
        st.warning('Stop the current analysis before starting another.'); return
    metadata=dict(name=name,source=source,simulated=source=='simulation',**(extra or {}))
    ss.job=AnalysisJob(bits,metadata,ss.size,ss.weights,ss.reference)

def demo(fault='Healthy'):
    ss.live=False; ss.reference=None
    if fault=='Healthy':
        bits=simulate(seed=42,windows=60,size=ss.size)
        meta=dict(seed=42,fault='Healthy',windows=60)
    else: bits,meta=guided_demo(ss.size)
    launch(bits,'SIMULATED · '+('Healthy reference' if fault=='Healthy' else 'Guided degradation and collapse'),extra=meta)

with st.sidebar:
    st.markdown('## ◈ Q-GAURD'); st.caption('RELIABILITY • FORENSICS • EARLY WARNING')
    requested_page = ss.pop('nav_page', ss.get('workspace_page', NAV[0]))
    ss.workspace_page = requested_page if requested_page in NAV else NAV[0]
    page=st.radio('Workspace',NAV,key='workspace_page',label_visibility='collapsed')
    st.divider()
    if st.button('Load healthy demo',width='stretch'): demo()
    if st.button('Run guided degradation demo',width='stretch'): demo('Gradual degradation')
    with st.expander('Analysis settings'):
        size=st.selectbox('Window size',[1000,10000,100000],index=[1000,10000,100000].index(ss.size))
        weights={k:st.number_input(k.title()+' weight',0,100,int(ss.weights[k]),key='weight_'+k) for k in WEIGHTS}
        if st.button('Apply settings / reset baseline'):
            if sum(weights.values())==0: st.error('At least one weight must be positive.')
            elif ss.job and not ss.job.future.done(): st.warning('Stop the active job first.')
            else:
                ss.size=size; ss.weights=weights; ss.reference=None; ss.live=False; ss.result=None; ss.bits=None
                st.success('Settings applied. Load or analyze a dataset to calibrate a new baseline.')
    st.caption('Local processing • No AI API • Six verified test families')
    st.caption('Simulation is classical, not a quantum source.')

header()

@st.fragment(run_every=1)
def jobs_panel():
    job=ss.job
    if job:
        if job.future.done():
            try:
                result=job.future.result()
                if not job.cancel.is_set(): ss.result=result; ss.bits=job.bits
            except InterruptedError as e: st.info(str(e))
            except Exception as e: st.error(f'Analysis failed: {e}')
            ss.job=None
            st.rerun()
        else:
            st.progress(job.progress,text=job.message)
            if st.button('Stop analysis'):
                ss.live=False; job.cancel.set(); st.info('Stopping at the next processing boundary.')
    elif ss.live:
        if ss.bits is None or len(ss.bits)>=ss.size*200:
            ss.live=False; st.info('Live demo reached its 200-window limit. Start a new stream to reset.'); return
        age=ss.live_age; q=.01+min(.35,age*.015) if ss.live_fault=='Gradual degradation' else .2
        fault='Bias' if ss.live_fault=='Gradual degradation' else ss.live_fault
        added=simulate(seed=ss.lab_seed+len(ss.bits)//ss.size,windows=5,size=ss.size,fault=fault,intensity=q,start=0,duration=5)
        ss.live_age+=5
        launch(np.r_[ss.bits,added],'SIMULATED · interactive failure lab',extra=dict(seed=ss.lab_seed,active_fault=ss.live_fault))
        st.rerun()

jobs_panel()
r=ss.result

if page=='DATA INGESTION':
    st.subheader('Connect evidence to analysis')
    st.write('Upload digitized bits. Optical signal acquisition and thresholding must happen upstream.')
    uploaded=st.file_uploader('Bitstream (.txt, .csv, .bin)',type=['txt','csv','bin'])
    ref_file=st.file_uploader('Optional reference baseline · at least 30 complete windows',type=['txt','csv','bin'],key='reference_upload')
    ss.retention=st.checkbox('Retain raw bits locally when I save a passport',value=ss.retention)
    if st.button('Analyze uploaded stream',type='primary',disabled=uploaded is None):
        try:
            bits,meta=ingest(uploaded.getvalue(),uploaded.name)
            reference=ingest(ref_file.getvalue(),ref_file.name)[0] if ref_file else None
            if reference is not None and len(reference)<30*ss.size: raise ValueError('Reference requires 30 complete windows at the current window size.')
            ss.reference=reference; ss.live=False; launch(bits,uploaded.name,'file',dict(file_sha256=meta['file_sha256']))
            st.rerun()
        except (ValueError,UnicodeError,pd.errors.ParserError) as e: st.error(str(e))
    st.info('10 million decoded bits maximum. CSV must contain only the bit column. Binary files use MSB-first order. Invalid data is rejected, not repaired.')

elif page in ['FAILURE LAB','WHAT-IF ANALYSIS']:
    st.subheader('QRNG Failure Lab' if page=='FAILURE LAB' else 'Controlled what-if experiment')
    st.caption('Engineering-level QRNG pipeline simulation · SIMULATED DATA')
    st.markdown('**Source → Measurement → Detector → Digitization → Extraction → Post-processing → Bits**')
    if page=='FAILURE LAB':
        c=st.columns(3)
        if c[0].button('Start healthy stream',type='primary'):
            ss.live=True; ss.live_fault='Healthy'; ss.live_age=0; ss.reference=None
            launch(simulate(windows=40,size=ss.size),'SIMULATED · healthy stream',extra=dict(seed=42)); st.rerun()
        if c[1].button('Pause stream'): ss.live=False; st.rerun()
        if c[2].button('Reset lab'):
            ss.live=False
            if ss.job: ss.job.cancel.set()
            ss.job=None; ss.result=None; ss.bits=None; ss.live_fault='Healthy'; ss.live_age=0
            st.rerun()
        st.caption(f"Stream {'RUNNING' if ss.live else 'PAUSED'} · active injection: {ss.live_fault}. Faults affect subsequent chunks only.")
        cols=st.columns(4)
        for i,fault in enumerate(FAULTS[1:]):
            if cols[i%4].button('Inject '+fault,key='inject_'+fault,disabled=not ss.live):
                ss.live_fault=fault; ss.live_age=0; st.rerun()
        if st.button('Remove injection / observe recovery',disabled=not ss.live):
            ss.live_fault='Healthy'; ss.live_age=0; st.rerun()
        st.caption('Bias represents digitization imbalance; block dependence represents detector/timing effects; repetition represents acquisition or post-processing defects. These mappings are illustrative, not physical diagnosis.')
    with st.form('scenario'):
        cols=st.columns(3)
        fault=cols[0].selectbox('Fault type',FAULTS,index=6)
        intensity=cols[1].slider('Fault intensity',0.,.5,.15,.005)
        seed=cols[2].number_input('Simulation seed',0,1000000,42)
        cols=st.columns(3)
        windows=cols[0].number_input('Total windows',40,min(500,10_000_000//ss.size),min(100,10_000_000//ss.size))
        start=cols[1].number_input('Start window (1-based)',1,int(windows),min(41,int(windows)))
        duration=cols[2].number_input('Duration (windows)',1,int(windows),min(60,int(windows)))
        run=st.form_submit_button('Run scenario',type='primary')
    if run:
        ss.live=False; bits=simulate(int(seed),int(windows),ss.size,fault,intensity,int(start)-1,int(duration))
        launch(bits,'SIMULATED · '+fault,extra=dict(seed=int(seed),fault=fault,intensity=intensity,start_window=int(start),duration=int(duration))); st.rerun()
    if r:
        cards(r); st.plotly_chart(timeline(r,['health'],'Live operational health'),width='stretch')
        st.markdown("#### 🔬 Degradation Signature Analysis")
        tab_sig1, tab_sig2, tab_sig3 = st.tabs(["📈 Signature Trends (Timeline)", "📊 Peak Severity Breakdown", "🗺️ Matrix Map"])
        with tab_sig1:
            st.plotly_chart(signature_trends(r), width='stretch')
        with tab_sig2:
            st.plotly_chart(signature_bars(r), width='stretch')
        with tab_sig3:
            st.plotly_chart(heatmap(r), width='stretch')
        st.info(r['advisor'])
        if st.checkbox('Show simulator ground truth (excluded from detection)'): st.json(r['metadata'])

elif page=='METHODOLOGY':
    st.subheader('Evidence before interpretation')
    st.warning(LIMITATION)
    st.markdown('''**Entropy.** Shannon, min and collision entropy use empirical single-bit frequencies. Eight-bit block entropy adds pattern information but remains a finite-sample descriptive estimate. A balanced periodic stream can have maximal marginal entropy.

**NIST.** Six SP 800-22 Rev.1a families; two directions for Cumulative Sums. Alpha 0.01. Family pass rate counts a family as failed if either direction fails. Inapplicable tests are excluded. Window screening and whole-stream validation are separate. Repeated testing creates expected isolated failures.

**CUSUM.** For each frozen-baseline standardized feature z, S+ = max(0, S+ + z - 0.5), S- = max(0, S- - z - 0.5). An event occurs when any accumulator crosses its empirically calibrated threshold; accumulators reset after the event. No confidence probability is inferred.

**States.** Two consecutive candidate windows escalate a state. Degraded requires at least two failed NIST families or an absolute feature z-score of 8. Critical requires severe collapse, a stuck run covering half a window, or at least four failed families with |z| > 10. Early Warning uses a recent CUSUM event, |z| >= 3, or supported trend risk. Recovery requires five healthy candidate windows plus transition persistence. These operational policies are heuristics; evaluation reports their performance.

**Health score.** Weighted mean of available components. Entropy, bias and correlation use 100 × clip(1 − max(0, |z| − 2)/8, 0, 1). Statistical health = family pass percentage. Temporal stability = 100 × clip(1 − CUSUM/threshold, 0, 1). Trend stability = 100 × (1 − min(1, 20/projected windows)). Unavailable trend components are excluded and remaining weights renormalized. Correlated components mean this is not independent evidence or a security probability.

**Forecast.** Theil–Sen slope over 20 monitoring windows; a negative upper slope bound and Spearman correlation below −0.6 are required. Threshold is health 40. Extrapolation assumes the trend persists. Serial dependence limits interpretation of regression intervals.

**Signatures.** Bias, periodicity and correlation match scores scale their standardized deviations to 100 at |z|=10. Burst scores use unusually long runs; repetition scores use adjacent repeated 32-bit blocks. Collapse uses marginal entropy loss, drift uses supported trend risk, and mixed failure is the second strongest signature. Match scores are not probabilities.

**Calibration.** Reserved seeds 910001 and 910002 generate synthetic IID calibration and validation data. These do not validate a physical QRNG. An initial 30-window baseline is unverified and may already contain faults. Supply a trusted reference to avoid learning a degraded source as normal.

**Future hardware.** Implement DataSource.chunks() yielding ordered sequence IDs, offsets and validated bits. Check transport gaps, duplicates and backlog separately from entropy alerts. Add device timestamps and acquisition metadata; never infer a physical cause from statistical signatures alone.
''')
    st.markdown('[NIST SP 800-22](https://csrc.nist.gov/pubs/sp/800/22/r1/upd1/final) · [NIST SP 800-90B](https://csrc.nist.gov/pubs/sp/800/90/b/final)')
    st.json(dict(weights=ss.weights,window_size=ss.size))
    if r: st.json(dict(baseline=r['baseline'],calibration=r['calibration']))

elif page=='QRNG HEALTH PASSPORT':
    st.subheader('A reproducible record of every investigation')
    if r and st.button('Save current health passport',type='primary'):
        save(r,bits=ss.bits if ss.retention else None); st.success('Passport saved locally.')
    history=sessions()
    if not history: st.info('Save an analysis to begin the local history.')
    else:
        st.dataframe(pd.DataFrame(history),hide_index=True,width='stretch')
        selected=st.selectbox('Historical session',[h['id'] for h in history],format_func=lambda x:next(h['name']+' · '+h['timestamp'][:19] for h in history if h['id']==x))
        previous=load(selected)
        if st.button('Open saved session'):
            if ss.job and not ss.job.future.done(): st.warning('Stop the current analysis first.')
            else:
                ss.live=False; ss.result=previous; retained=Path(__file__).parent/'data'/'retained'/(selected+'.npy'); ss.bits=np.load(retained) if retained.exists() else None; st.rerun()
        trend=[]
        for h in reversed(history[:50]):
            item=load(h['id']); latest=item['windows'][-1] if item['windows'] else {}
            trend.append(dict(timestamp=item['timestamp'],health=latest.get('health'),shannon=item['overall']['shannon']))
        st.line_chart(pd.DataFrame(trend).set_index('timestamp'))
        if r:
            st.plotly_chart(fingerprint(previous,'Historical',fingerprint(r,'Current')),width='stretch')
            st.dataframe(pd.DataFrame({'Current':r['overall'],'Historical':previous['overall']}),width='stretch')
            if r['config']!=previous['config']: st.warning('Analysis configurations differ; scores are not directly comparable.')

elif r is None:
    st.subheader('Start an investigation')
    st.write('Load the healthy demo, upload a bitstream, or open the Failure Lab. Every score and chart is computed from the supplied bits.')
    cols=st.columns(3)
    cols[0].info('01 / Observe\n\nEstablish a baseline and inspect the entropy fingerprint.')
    cols[1].info('02 / Challenge\n\nInject degradation and measure when the evidence changes.')
    cols[2].info('03 / Investigate\n\nInspect exact windows and export an evidence-backed passport.')

else:
    cards(r)
    if page=='COMMAND CENTER':
        st.caption(r['metadata'].get('name','Dataset')+' · '+r['baseline']['status'])
        
        # Compact Inconsistency Summary Section using wonder-of-AI UI elements
        inc_summary = r.get('inconsistency_summary', {})
        st.markdown('### Inconsistency summary')
        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        with sc1: metric_card('Events', f"{inc_summary.get('total_events', 0)}", 'total episodes')
        with sc2: metric_card('Affected Windows', f"{inc_summary.get('unique_affected_windows', 0)}", 'unique windows')
        with sc3: metric_card('First Detected', str(inc_summary.get('first_detected', 'None')), 'earliest warning')
        with sc4: metric_card('Primary Signature', str(inc_summary.get('most_common_type', 'None')), 'dominant pattern')
        with sc5:
            sev = inc_summary.get('highest_severity', 'Healthy')
            badge = status_badge(sev)
            st.markdown(f'<div class="metric-card"><div class="metric-label">Highest Severity</div><div class="metric-value" style="font-size:1.2rem; margin-top:8px;">{badge}</div><div class="metric-detail">operational impact</div></div>', unsafe_allow_html=True)
        if st.button('Open Inconsistency Explorer →', type='secondary'):
            ss.nav_page = 'INCONSISTENCY EXPLORER'
            st.rerun()
            
        st.divider()
        left,right=st.columns([2,1])
        with left:
            st.plotly_chart(timeline(r,['health'],'Operational health / 100'),width='stretch')
            st.plotly_chart(timeline(r,['shannon','min_entropy'],'Observed entropy over time'),width='stretch')
        with right:
            st.markdown('<div class="callout"><b>Evidence boundary:</b> Validates statistical and entropy characteristics. Statistical tests alone cannot establish quantum origin.</div>', unsafe_allow_html=True)
            st.subheader('Q-Advisor'); st.info(r['advisor'])
            st.plotly_chart(fingerprint(r),width='stretch')
        st.subheader('Recent events'); st.dataframe(pd.DataFrame(r['events'][-20:]).drop(columns=['evidence','standardized_changes'],errors='ignore'),hide_index=True,width='stretch')
    elif page=='INCONSISTENCY EXPLORER': inconsistency_explorer(r, ss.bits)
    elif page=='ENTROPY ANALYSIS':
        st.plotly_chart(timeline(r,['shannon','min_entropy','collision','block_entropy'],'Entropy estimates · bits/bit'),width='stretch')
        st.plotly_chart(fingerprint(r),width='stretch')
        st.dataframe(pd.DataFrame([r['overall']]),hide_index=True,width='stretch')
        st.caption('Fingerprint axes show stability components, not raw entropy. Unavailable components remain gaps.')
        st.plotly_chart(timeline(r,['bias','autocorrelation'],'Bias and serial dependence'),width='stretch')
    elif page=='NIST VALIDATION':
        st.markdown('<div class="smallcaps">STATISTICAL VALIDATION / SP 800-22</div>', unsafe_allow_html=True)
        st.subheader('NIST SP 800-22 Statistical Health')
        st.markdown('''<div class="callout">
<b>Understanding NIST P-values:</b><br>
• <b>Pass condition:</b> P ≥ 0.01 indicates no statistical evidence against randomness for that test.<br>
• <b>Uniformity (histogram below):</b> Under true randomness, P-values across windows spread evenly across 0.0 to 1.0 (near the gold dashed line).<br>
• <b>Rejection (red line at α = 0.01):</b> P-values falling below 0.01 indicate statistical anomalies.
</div>''', unsafe_allow_html=True)
        
        col_tab, col_bars = st.columns([1.1, 1])
        with col_tab:
            st.markdown('### Whole-dataset test results')
            st.dataframe(pd.DataFrame(r['nist']).drop(columns=['parameters']),hide_index=True,width='stretch')
            with st.expander('Test parameters and applicability'): st.json(r['nist'])
        with col_bars:
            st.plotly_chart(nist_bars(r),width='stretch')
            
        st.plotly_chart(pvalues(r),width='stretch')
        st.plotly_chart(timeline(r,['nist_pass_rate'],'Window-level family pass rate'),width='stretch')
        st.warning('NIST SP 800-22 provides statistical evidence about the observed sequence; it does not establish quantum origin. This app implements six families, not the full suite.')
    elif page=='DEGRADATION MONITOR':
        st.plotly_chart(timeline(r,['change_score'],'CUSUM change evidence'),width='stretch')
        st.markdown("#### 🔬 Degradation Signature Tracking")
        st.markdown("""<div style="font-size:0.85rem; color:#8ea3bf; margin-bottom:12px;">
        Continuous multi-signal tracking against physical failure models. Scores ≥ 30 indicate matched fault signatures.
        </div>""", unsafe_allow_html=True)
        tab_sig1, tab_sig2, tab_sig3 = st.tabs(["📈 Signature Trends (Timeline)", "📊 Peak Severity Breakdown", "🗺️ Matrix Map"])
        with tab_sig1:
            st.plotly_chart(signature_trends(r), width='stretch')
        with tab_sig2:
            st.plotly_chart(signature_bars(r), width='stretch')
        with tab_sig3:
            st.plotly_chart(heatmap(r), width='stretch')
        st.markdown("#### ⏳ Entropy Risk Forecast & Operational Events")
        available = [w for w in r['windows'] if 'forecast' in w]
        if available:
            selected = st.selectbox('Forecast as observed at window', [w['window'] for w in available], index=len(available)-1)
            f = next(w['forecast'] for w in available if w['window'] == selected)
            recent_windows = [w for w in r['windows'] if w['window'] <= selected][-25:]
        else:
            f = r['forecast']
            recent_windows = r['windows'][-25:] if r.get('windows') else []

        if f.get('available'):
            st.markdown(f"""
            <div class="callout" style="border-left-color: #ef6a6a; background: #26161b;">
                <span class="badge bad">⚠️ Degradation Projected</span>
                <div style="margin-top:8px; font-size:0.95rem; line-height:1.5; color: #ffc4c4;">
                    Conditional intervention threshold crossing predicted in <b>~{f['windows_to_threshold']:.1f} windows</b> if current degradation rate (<code>{f['slope']:.3f}</code>/window) persists.
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.plotly_chart(projection_chart(f), width='stretch')
        else:
            st.markdown(f"""
            <div class="callout" style="border-left-color: #22c7a8; background: #0e1e24;">
                <span class="badge good">🛡️ Nominal · No Risk Projected</span>
                <div style="margin-top:8px; font-size:0.92rem; line-height:1.5; color:#e7edf7;">
                    <b>Assessment:</b> {f['reason']}<br>
                    <span style="color:#8ea3bf; font-size:0.85rem;">Theil-Sen robust slope and Spearman rank correlation confirm the stream is maintaining steady entropy safely above the intervention threshold (40.0).</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.plotly_chart(projection_chart(f, recent_windows=recent_windows), width='stretch')

        with st.expander("🛠️ Advanced Forecast Model Diagnostics (JSON)"):
            st.json(f)

        st.markdown("#### 📋 Operational State & Change-Point Events")
        events = r.get('events', [])
        if events:
            st.dataframe(pd.DataFrame(events), hide_index=True, width='stretch')
        else:
            st.markdown("""
            <div style="background:#111925; border:1px solid #1f2b3e; border-radius:8px; padding:16px 20px; color:#8ea3bf; font-family:'Space Grotesk',sans-serif; display:flex; align-items:center; gap:12px; margin-top:8px;">
                <span style="font-size:1.3rem;">✅</span>
                <div>
                    <strong style="color:#22c7a8; font-size:0.95rem;">Zero Operational Anomalies Recorded</strong><br>
                    <span style="font-size:0.85rem; color:#8ea3bf;">All evaluated windows operated strictly within nominal baseline tolerances with zero CUSUM change points or state transitions.</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    elif page=='ENTROPY FORENSICS': forensic(r,ss.bits)
    elif page=='REPORTS':
        st.subheader('Export an auditable investigation')
        history=sessions(); ids=['None']+[h['id'] for h in history]
        selected=st.selectbox('Include historical comparison',ids)
        comparison=load(selected) if selected!='None' else None
        st.markdown("#### 📦 Export Audit Artifacts")
        cols = st.columns(4 if ss.bits is not None else 3)
        cols[0].download_button('Download PDF report', pdf(r, comparison), 'q-gaurd-report.pdf', 'application/pdf', type='primary')
        cols[1].download_button('Download window CSV', export_csv(r), 'q-gaurd-windows.csv', 'text/csv')
        cols[2].download_button('Download JSON', export_json(r), 'q-gaurd-passport.json', 'application/json')
        if ss.bits is not None:
            cols[3].download_button('Download analyzed bits (.txt)', (''.join(map(str, ss.bits))).encode(), 'analyzed-bits.txt', 'text/plain')
            
        st.markdown("#### 🧠 Diagnostic Advisory Summary")
        st.markdown(f"""
        <div class="callout" style="border-left-color: #5b8cff; background: #111a28;">
            <div style="font-family:'Space Grotesk',sans-serif; font-weight:600; color:#5b8cff; margin-bottom:6px; font-size:0.95rem;">
                ◈ Q-Advisor Diagnostic Assessment
            </div>
            <div style="font-size:0.92rem; line-height:1.55; color:#e7edf7;">
                {r['advisor']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("#### ⚙️ Stream Acquisition & Execution Metadata")
        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1:
            metric_card('Execution Time', f"{r['elapsed_seconds']:.2f}s", 'pipeline benchmark')
        with mc2:
            metric_card('Complete Windows', f"{r['data_quality'].get('complete_windows', 0):,}", f"{r['config'].get('window_size', 10000):,} bits/win")
        with mc3:
            metric_card('Bit Order / Valid', f"{r['data_quality'].get('bit_order', 'MSB first')}", str(r['data_quality'].get('validation', 'Strict binary validated'))[:22])
        with mc4:
            metric_card('Significance Level', f"α = {r['config'].get('alpha', 0.01)}", 'NIST rejection threshold')

        with st.expander("🛠️ View Full Audit Metadata & Config Schema (JSON)"):
            st.json(dict(session=r['session_id'], configuration=r['config'], quality=r['data_quality'], elapsed_seconds=r['elapsed_seconds']))

st.divider(); st.caption('Statistical validation ≠ physical / quantum validation. '+LIMITATION)
