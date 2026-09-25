"""Two-sided standardized CUSUM with empirical, held-out null calibration."""
from functools import lru_cache
import numpy as np
from core.statistics import metrics

FEATURES=['bias','autocorrelation','spectral','block_entropy']

def vector(row): return np.array([row[k] for k in FEATURES],dtype=float)

def fit(rows,size):
    a=np.array([vector(r) for r in rows])
    mean=np.array([np.mean(c[np.isfinite(c)]) if np.isfinite(c).any() else 0. for c in a.T])
    floors=np.array([.25/np.sqrt(size),.5/np.sqrt(size),1/size,1/size])
    std=np.maximum(np.array([np.std(c[np.isfinite(c)],ddof=1) if np.isfinite(c).sum()>1 else 1. for c in a.T]),floors)
    return mean,std

class Cusum:
    def __init__(self,h): self.h=h; self.positive=np.zeros(4); self.negative=np.zeros(4)
    def step(self,z):
        self.positive=np.maximum(0,self.positive+z-.5)
        self.negative=np.maximum(0,self.negative-z-.5)
        value=float(max(self.positive.max(),self.negative.max()))
        fired=value>=self.h
        if fired: self.positive[:]=0; self.negative[:]=0
        return value,fired

@lru_cache(maxsize=8)
def calibrate(size):
    # Seeds are reserved for calibration and never used by evaluation.
    rng=np.random.default_rng(910001)
    training=[metrics(rng.integers(0,2,size,dtype=np.uint8)) for _ in range(330)]
    mean,std=fit(training[:30],size)
    raw=Cusum(float('inf')); scores=[raw.step((vector(r)-mean)/std)[0] for r in training[30:]]
    threshold=max(12.,float(np.quantile(scores,.995)))
    validation_rng=np.random.default_rng(910002)
    detector=Cusum(threshold); alarms=0
    for _ in range(300):
        row=metrics(validation_rng.integers(0,2,size,dtype=np.uint8))
        alarms+=detector.step((vector(row)-mean)/std)[1]
    return dict(threshold=threshold,allowance=.5,training_windows=300,validation_windows=300,false_alerts=alarms,false_alerts_per_1000=alarms/300*1000,calibration_seeds=[910001,910002],scope='Synthetic balanced IID reference only; not calibrated physical-source confidence.')
