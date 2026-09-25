"""Held-out evaluation; retains misses and negative early-warning lead times."""
from pathlib import Path
import json,time
import numpy as np
import pandas as pd
from core.engine import analyze
from simulation.qrng_twin import simulate,FAULTS,guided_demo
from reports.generator import pdf,export_json,export_csv

def evaluate():
    output=Path('output'); output.mkdir(exist_ok=True)
    rows=[]; healthy_windows=0; false_events=0; cold=None
    for seed in [1201,1202,1203,1204,1205]:
        for fault in FAULTS:
            for intensity in ([.03,.15] if fault not in ['Healthy','Sudden failure'] else [.15]):
                b=simulate(seed=seed,fault=fault,intensity=intensity)
                r=analyze(b,dict(name='SIMULATED evaluation',source='simulation',seed=seed)); cold=cold or r['elapsed_seconds']
                monitored=r['windows'][30:]
                warning=next((w['window'] for w in monitored if w['window']>=41 and w['state'] in ['Early Warning','Degraded','Critical']),None)
                comparator=None
                for previous,current in zip(monitored,monitored[1:]):
                    if previous['window']>=41 and previous['nist_failures']>=2 and current['nist_failures']>=2: comparator=current['window']; break
                pre=sum(e['kind']!='Change point' and e['state']!='Healthy' and e['window']<41 for e in r['events'])
                if fault=='Healthy':
                    healthy_windows+=len(monitored); false_events+=sum(e['kind']!='Change point' and e['state']!='Healthy' for e in r['events'])
                rows.append(dict(seed=seed,fault=fault,intensity=intensity,onset=41 if fault!='Healthy' else None,first_detection=warning if fault!='Healthy' else None,nist_comparator=comparator,delay=None if warning is None else warning-41,lead_time=None if warning is None or comparator is None else comparator-warning,miss=fault!='Healthy' and warning is None,pre_onset_alerts=pre,seconds=r['elapsed_seconds']))
    df=pd.DataFrame(rows)
    df.loc[df.fault=='Healthy',['delay','lead_time','nist_comparator']]=np.nan
    df.to_csv(output/'evaluation.csv',index=False)
    perf={}
    for count in [100,1000]:
        b=simulate(seed=8123,windows=count); r=analyze(b); perf[str(len(b))]=r['elapsed_seconds']
    report=dict(calibration=r['calibration'],evaluation_seeds=[1201,1202,1203,1204,1205],healthy_windows=healthy_windows,false_alert_events=false_events,false_alert_events_per_1000=1000*false_events/healthy_windows,missed_fault_scenarios=int(df['miss'].sum()),fault_scenarios=int((df.fault!='Healthy').sum()),cold_million_bit_seconds=cold,warm_timings=perf,positive_lead_cases=int((df.lead_time>0).sum()),zero_lead_cases=int((df.lead_time==0).sum()),negative_lead_cases=int((df.lead_time<0).sum()),limitations='Synthetic models only; five seeds; not physical-source validation. Missing comparator is not a measured lead-time win. Thresholds were fixed before held-out evaluation.')
    (output/'evaluation-summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    demo_bits,demo_meta=guided_demo()
    sample=analyze(demo_bits,dict(name='SIMULATED guided degradation and collapse',source='simulation',**demo_meta))
    (output/'sample-report.pdf').write_bytes(pdf(sample)); (output/'sample-passport.json').write_bytes(export_json(sample)); (output/'sample-windows.csv').write_bytes(export_csv(sample))
    print(json.dumps(report,indent=2))

if __name__=='__main__': evaluate()
