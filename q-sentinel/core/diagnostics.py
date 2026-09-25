import numpy as np

def signatures(row,z):
    scale=lambda v:float(np.clip(v,0,1)*100)
    scores={'Bit bias':scale(abs(z[0])/10),'Periodic pattern':scale(max(0,z[2])/10),'Serial correlation':scale(abs(z[1])/10),'Burst error':scale((row['longest_streak']-20)/150),'Repeated sequence':scale(row['repetition']*10),'Sudden collapse':scale((.8-row['shannon'])/.8),'Gradual drift':scale(row.get('trend_risk',0))}
    strongest=sorted(scores.values(),reverse=True)
    scores['Mixed failure']=min(strongest[:2]); scores['Unknown / unclassified']=max(0,100-max(scores.values()))
    return scores

def advisor(row,baseline,events):
    if not row: return 'Insufficient data for a diagnostic summary.'
    strongest=sorted(((k,v) for k,v in row['signatures'].items() if k!='Unknown / unclassified'),key=lambda x:x[1],reverse=True)[:2]
    if not strongest: return 'Calibration incomplete. At least 30 complete reference windows are required before diagnostic interpretation.'
    first=next((e['window'] for e in events if e['state'] in ['Early Warning','Degraded','Critical']),None)
    correlation='undefined (constant window)' if row['autocorrelation'] is None else f"{row['autocorrelation']:+.4f}"
    evidence=f"Window {row['window']}: marginal Shannon entropy {row['shannon']:.5f}, signed bias {row['bias']:+.4f}, lag-one correlation {correlation}; {row['nist_failures']} NIST families failed."
    if strongest[0][1]<30: return evidence+' No strong library signature matched. Continue monitoring; this does not establish source security.'
    labels=', '.join(f'{k} ({v:.0f}/100 match)' for k,v in strongest if v>=30)
    recommendation='Compare raw acquisition and post-processed streams.'
    if row['signatures']['Bit bias']>=30: recommendation+=' Inspect detector balance and digitization thresholds.'
    if row['signatures']['Serial correlation']>=30 or row['signatures']['Periodic pattern']>=30: recommendation+=' Inspect acquisition timing and buffering for repeated/dependent samples.'
    return evidence+f' Observed statistical signature is consistent with {labels}. First detected event: window {first if first is not None else "not established"}. '+recommendation+' These are investigation suggestions, not proof of a physical fault.'
