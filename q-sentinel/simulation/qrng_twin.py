"""Classical engineering-level pipeline simulation; not quantum physics."""
import numpy as np
from core.ingestion import validate

FAULTS=['Healthy','Bias','Correlation','Periodicity','Burst noise','Repetition','Gradual degradation','Sudden failure','Mixed failure']

def guided_demo(size=10000):
    """Fixed illustrative scenario; no detector outputs are prescribed."""
    bits=simulate(seed=42,windows=100,size=size,fault='Gradual degradation',intensity=.03,start=40,duration=60)
    bits[90*size:]=0
    return bits,dict(seed=42,scenario='Gradual bias followed by stuck-output collapse',schedule=[dict(fault='Gradual degradation',start_window=41,duration=60,intensity=.03),dict(fault='Sudden failure',start_window=91,duration=10)])

def simulate(seed=42, windows=100, size=10000, fault='Healthy', intensity=.15, start=40, duration=60):
    rng=np.random.default_rng(seed); u=rng.random(windows*size); bits=(u<.5).astype(np.uint8)
    for w in range(max(0,start),min(windows,start+duration)):
        a=w*size; c=bits[a:a+size]; q=float(np.clip(intensity,0,1))
        if fault in ['Bias','Gradual degradation','Mixed failure']:
            strength=q*((w-start+1)/max(1,duration) if fault=='Gradual degradation' else 1)
            c[:]=(u[a:a+size]<min(1,.5+strength)).astype(np.uint8)
        if fault in ['Correlation','Mixed failure']:
            # Replace selected disjoint blocks with their first bit (explicit dependence model).
            blocks=c[:size//8*8].reshape(-1,8); selected=rng.random(len(blocks))<q
            blocks[selected]=blocks[selected,:1]
        if fault=='Periodicity':
            mask=rng.random(size)<q; pattern=np.resize(np.array([0,0,1,1],dtype=np.uint8),size); c[mask]=pattern[mask]
        if fault=='Burst noise':
            length=max(1,int(size*q)); pos=int(rng.integers(0,size-length+1)); c[pos:pos+length]=1
        if fault=='Repetition':
            length=int(size*q)//32*32; c[:length]=np.tile(c[:32],length//32)
        if fault=='Sudden failure': c[:]=0
    return validate(bits)
