import numpy as np

WEIGHTS=dict(entropy=15,nist=20,bias=15,correlation=20,temporal=20,trend=10)

def health(z, nist_rate, change_ratio, trend_risk=None, weights=None, available=None):
    def score(v): return float(100*np.clip(1-max(0,abs(v)-2)/8,0,1))
    components=dict(entropy=score(z[3]),nist=None if nist_rate is None else 100*nist_rate,bias=score(z[0]),correlation=score(z[1]),temporal=float(100*np.clip(1-change_ratio,0,1)),trend=None if trend_risk is None else float(100*(1-trend_risk)))
    if available is not None:
        for key,index in [('entropy',3),('bias',0),('correlation',1)]:
            if not available[index]: components[key]=None
    weights=weights or WEIGHTS; total=sum(weights[k] for k,v in components.items() if v is not None)
    value=sum(weights[k]*v for k,v in components.items() if v is not None)/total if total else None
    return value,components
