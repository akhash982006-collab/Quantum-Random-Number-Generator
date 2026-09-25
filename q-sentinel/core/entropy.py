import numpy as np

def entropy_metrics(b):
    p=float(np.mean(b)); probs=np.array([1-p,p]); positive=probs[probs>0]
    m=8; count=len(b)//m
    if count:
        words=np.packbits(b[:count*m].reshape(count,m),axis=1).ravel()
        freq=np.bincount(words,minlength=256)/count; freq=freq[freq>0]
        block=float(-np.sum(freq*np.log2(freq))/m)
    else: block=None
    return dict(shannon=max(0.,float(-np.sum(positive*np.log2(positive)))),min_entropy=max(0.,float(-np.log2(max(p,1-p)))),collision=max(0.,float(-np.log2(np.sum(probs**2)))),block_entropy=block,bias=p-.5)
