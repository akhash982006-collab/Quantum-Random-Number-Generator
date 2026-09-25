import numpy as np
from core.changepoint import FEATURES, Cusum, fit, vector
from core.health_score import health
from core.forecasting import forecast
from core.diagnostics import signatures

def monitor(rows,size,calibration,weights,reference=None):
    ref=reference or rows[:30]
    if len(ref)<30:
        for r in rows:
            r.update(state='Insufficient Data',health=None,components={},z=[0]*4,change_score=0.,change_point=False,trend_risk=0.,signatures={})
        return [],dict(status='Insufficient Data',reason='30 complete baseline windows required.'),dict(available=False,reason='Insufficient data.')
    mean,std=fit(ref,size); detector=Cusum(calibration['threshold'])
    enabled=np.any(np.isfinite(np.array([vector(r) for r in ref])),axis=0)
    baseline=dict(status='External reference supplied' if reference else 'Unverified initial baseline',mean=dict(zip(FEATURES,mean.tolist())),std=dict(zip(FEATURES,std.tolist())),windows=len(ref))
    baseline['unavailable_features']=[FEATURES[i] for i in range(4) if not enabled[i]]
    state='Healthy'; pending=None; streak=0; events=[]; history=[]; recent_alerts=[]; first_monitor=0 if reference else 30
    ranks={'Healthy':0,'Early Warning':1,'Degraded':2,'Critical':3}
    for i,row in enumerate(rows):
        observed=vector(row); available=np.isfinite(observed)&enabled
        z=np.where(available,(observed-mean)/std,0.)
        if i<first_monitor:
            row.update(state='Calibrating',health=None,components={},z=z.tolist(),change_score=0.,change_point=False,trend_risk=0.,signatures={})
            continue
        score,fired=detector.step(z); recent_alerts=(recent_alerts+[fired])[-3:]
        trend=forecast(history); risk=min(1.,20/max(1.,trend['windows_to_threshold'])) if trend['available'] else None
        h,components=health(z,row['nist_pass_rate'],min(1,score/calibration['threshold']),risk,weights,available)
        history.append(h); row['trend_risk']=risk or 0.
        row['forecast']=forecast(history)
        # Persistent, observed evidence; isolated failures never determine a status alone.
        severe=(row['shannon']<.5 or row['longest_streak']>size*.5 or (row['nist_failures']>=4 and np.max(abs(z))>10))
        degraded=row['nist_failures']>=2 or np.max(abs(z))>=8
        warning=any(recent_alerts) or np.max(abs(z))>=3 or (risk is not None and risk>.5)
        target='Critical' if severe else 'Degraded' if degraded else 'Early Warning' if warning else 'Healthy'
        if target==pending: streak+=1
        else: pending=target; streak=1
        required=2 if ranks[target]>ranks[state] else 5
        if target!=state and streak>=required:
            previous=state; state=target
            events.append(dict(window=row['window'],bit_offset=row['bit_offset'],state=state,previous=previous,kind='Recovery' if state=='Healthy' else 'First detection' if not events else 'State transition',evidence={k:row[k] for k in FEATURES},standardized_changes=dict(zip(FEATURES,z.tolist()))))
        if fired:
            events.append(dict(window=row['window'],bit_offset=row['bit_offset'],state=state,kind='Change point',score=score,threshold=calibration['threshold'],evidence={k:row[k] for k in FEATURES}))
        row.update(state=state,health=h,components=components,z=[float(v) if available[j] else None for j,v in enumerate(z)],change_score=score,change_point=fired)
        row['signatures']=signatures(row,z)
    return events,baseline,forecast(history)
