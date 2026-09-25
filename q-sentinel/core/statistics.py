import numpy as np
from core.entropy import entropy_metrics

def metrics(b):
    values=entropy_metrics(b); x=b.astype(float); centered=x-x.mean(); variance=np.dot(centered,centered)
    ac=float(np.dot(centered[:-1],centered[1:])/variance) if variance else None
    power=np.abs(np.fft.rfft(centered))**2; power[0]=0
    spectral=float(power.max()/power.sum()) if power.sum() else None
    changes=np.flatnonzero(np.diff(b.astype(np.int8)))+1
    lengths=np.diff(np.r_[0,changes,len(b)])
    count=len(b)//32
    words=np.packbits(b[:count*32].reshape(count,32),axis=1) if count else np.empty((0,4))
    repetition=float(np.mean(np.all(words[1:]==words[:-1],axis=1))) if count>1 else 0.
    return dict(values,autocorrelation=ac,spectral=spectral,runs=int(len(lengths)),longest_streak=int(max(lengths)),repetition=repetition)
