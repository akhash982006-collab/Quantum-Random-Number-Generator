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
from ui.components import header,cards
from ui.charts import timeline,fingerprint,heatmap,pvalues,frame,style
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
        st.plotly_chart(heatmap(r),width='stretch'); st.info(r['advisor'])
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
        
        # Compact Inconsistency Summary Section
        inc_summary = r.get('inconsistency_summary', {})
        st.markdown('### Inconsistency summary')
        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        sc1.metric('Events', f"{inc_summary.get('total_events', 0)} events")
        sc2.metric('Affected Windows', f"{inc_summary.get('unique_affected_windows', 0)} windows")
        sc3.metric('First Detected', str(inc_summary.get('first_detected', 'None')))
        sc4.metric('Primary Signature', str(inc_summary.get('most_common_type', 'None')))
        sc5.metric('Highest Severity', str(inc_summary.get('highest_severity', 'Healthy')))
        if st.button('Open Inconsistency Explorer →', type='secondary'):
            ss.nav_page = 'INCONSISTENCY EXPLORER'
            st.rerun()
            
        st.divider()
        left,right=st.columns([2,1])
        with left:
            st.plotly_chart(timeline(r,['health'],'Operational health / 100'),width='stretch')
            st.plotly_chart(timeline(r,['shannon','min_entropy'],'Observed entropy over time'),width='stretch')
        with right:
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
        st.subheader('Whole-dataset validation')
        st.dataframe(pd.DataFrame(r['nist']).drop(columns=['parameters']),hide_index=True,width='stretch')
        with st.expander('Test parameters and applicability'): st.json(r['nist'])
        st.plotly_chart(pvalues(r),width='stretch')
        st.plotly_chart(timeline(r,['nist_pass_rate'],'Window-level family pass rate'),width='stretch')
        st.warning('NIST SP 800-22 provides statistical evidence about the observed sequence; it does not establish quantum origin. This app implements six families, not the full suite.')
    elif page=='DEGRADATION MONITOR':
        st.plotly_chart(timeline(r,['change_score'],'CUSUM change evidence'),width='stretch')
        st.plotly_chart(heatmap(r),width='stretch')
        st.subheader('Entropy risk forecast')
        available=[w for w in r['windows'] if 'forecast' in w]
        if available:
            selected=st.selectbox('Forecast as observed at window',[w['window'] for w in available],index=len(available)-1)
            f=next(w['forecast'] for w in available if w['window']==selected)
        else: f=r['forecast']
        if f['available']:
            st.warning(f"Conditional threshold crossing in approximately {f['windows_to_threshold']:.1f} windows if the observed trend persists.")
            end=min(100,int(np.ceil(f['windows_to_threshold']))+5); x=np.arange(end+1)
            fig=go.Figure(go.Scatter(x=x,y=f['current']+f['slope']*x,name='Conditional projection')); fig.add_hline(y=40,annotation_text='Operational threshold'); st.plotly_chart(style(fig,'Health trend projection · not a guaranteed prediction'),width='stretch')
        else: st.info(f['reason'])
        st.json(f); st.dataframe(pd.DataFrame(r['events']),hide_index=True,width='stretch')
    elif page=='ENTROPY FORENSICS': forensic(r,ss.bits)
    elif page=='REPORTS':
        st.subheader('Export an auditable investigation')
        history=sessions(); ids=['None']+[h['id'] for h in history]
        selected=st.selectbox('Include historical comparison',ids)
        comparison=load(selected) if selected!='None' else None
        cols=st.columns(3)
        cols[0].download_button('Download JSON',export_json(r),'q-gaurd-passport.json','application/json')
        cols[1].download_button('Download window CSV',export_csv(r),'q-gaurd-windows.csv','text/csv')
        cols[2].download_button('Download PDF report',pdf(r,comparison),'q-gaurd-report.pdf','application/pdf')
        st.write(r['advisor']); st.json(dict(session=r['session_id'],configuration=r['config'],quality=r['data_quality'],elapsed_seconds=r['elapsed_seconds']))
        if ss.bits is not None:
            st.download_button('Download analyzed bits (.txt)',(''.join(map(str,ss.bits))).encode(),'analyzed-bits.txt','text/plain')

st.divider(); st.caption('Statistical validation ≠ physical / quantum validation. '+LIMITATION)
