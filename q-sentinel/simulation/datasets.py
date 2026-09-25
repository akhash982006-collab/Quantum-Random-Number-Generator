from pathlib import Path
import json
import numpy as np
from simulation.qrng_twin import simulate
from core.ingestion import digest

def generate(root='data'):
    root=Path(root); manifest=[]
    names={'healthy_qrng':'Healthy','biased_qrng':'Bias','correlated_qrng':'Correlation','periodic_qrng':'Periodicity','burst_noise_qrng':'Burst noise','gradual_degradation_qrng':'Gradual degradation','sudden_failure_qrng':'Sudden failure','mixed_failure_qrng':'Mixed failure'}
    for name,fault in names.items():
        folder=root/('healthy' if fault=='Healthy' else 'failures' if fault=='Sudden failure' else 'degraded'); folder.mkdir(parents=True,exist_ok=True)
        b=simulate(fault=fault,intensity=.2); path=folder/(name+'.csv')
        np.savetxt(path,b,fmt='%d',header='bit',comments='')
        manifest.append(dict(file=str(path),label='SIMULATED DATA',fault=fault,seed=42,windows=100,window_size=10000,start_window=41,duration=60,intensity=.2,sha256=digest(b)))
    (root/'simulation_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

if __name__=='__main__': print(json.dumps(generate(),indent=2))
