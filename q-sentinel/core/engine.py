import time
from datetime import datetime,timezone
import uuid
from core.ingestion import validate,digest
from core.statistics import metrics
from core.sources import FileSource,checked_chunks
from core.changepoint import calibrate
from core.degradation import monitor
from core.health_score import WEIGHTS
from core.diagnostics import advisor
from nist.suite import suite,summary

from core.inconsistencies import extract_inconsistencies

VERSION='1.0.0'
LIMITATION='This analysis evaluates statistical and entropy characteristics of the supplied bitstream. It does not independently establish that the source is quantum. Marginal entropy is not certified usable cryptographic entropy. Signature scores are not probabilities of hardware failure.'

def analyze(bits,metadata=None,size=10000,weights=None,reference=None,progress=None,cancel=None):
    started=time.perf_counter(); bits=validate(bits)
    if size<1000 or size>100000: raise ValueError('Window size must be between 1,000 and 100,000 bits.')
    weights=weights or WEIGHTS.copy()
    if set(weights)!=set(WEIGHTS) or any(v<0 for v in weights.values()) or sum(weights.values())<=0:
        raise ValueError('Weights must contain all six components, be nonnegative, and sum above zero.')
    rows=[]; total=len(bits)//size
    if progress: progress(0,'Calibrating detector on synthetic reference data')
    calibration=calibrate(size) if total>=30 else {}
    for chunk in checked_chunks(FileSource(bits),size):
        if cancel and cancel.is_set(): raise InterruptedError('Analysis stopped; incomplete results were not saved.')
        if len(chunk.bits)<size: break
        tests=suite(chunk.bits)
        rows.append(dict(window=chunk.sequence+1,bit_offset=chunk.offset,**metrics(chunk.bits),**summary(tests),tests=tests))
        if progress: progress((chunk.sequence+1)/max(1,total)*.9,'Analyzing windows')
    reference_rows=None
    if reference is not None:
        reference=validate(reference)
        reference_rows=[metrics(reference[i:i+size]) for i in range(0,len(reference)-size+1,size)]
        if len(reference_rows)<30: raise ValueError('Reference requires at least 30 complete windows.')
    if rows and (total>=30 or reference_rows):
        calibration=calibrate(size)
    events,baseline,prediction=monitor(rows,size,calibration,weights,reference_rows)
    if cancel and cancel.is_set(): raise InterruptedError('Analysis stopped.')
    whole=suite(bits)
    sid=str(uuid.uuid4())
    ts=datetime.now(timezone.utc).isoformat()
    inconsistencies,inconsistency_summary=extract_inconsistencies(rows,events,baseline,calibration,sid,ts,size,bits)
    # Tag each window with inconsistency ID if present
    inc_map = {}
    for inc in inconsistencies:
        for w in inc['affected_windows']:
            inc_map[w] = inc['id']
    for r in rows:
        r['inconsistency_id'] = inc_map.get(r['window'], None)
    result=dict(session_id=sid,timestamp=ts,version=VERSION,metadata=dict(metadata or {},bits=len(bits),sha256=digest(bits)),config=dict(window_size=size,alpha=.01,weights=weights,reference_hash=digest(reference) if reference is not None else None),data_quality=dict(complete_windows=total,trailing_bits=len(bits)%size,bit_order='MSB first',validation='Strict binary input validated'),overall=metrics(bits),nist=whole,nist_summary=summary(whole),windows=rows,events=events,baseline=baseline,calibration=calibration,forecast=prediction,inconsistencies=inconsistencies,inconsistency_summary=inconsistency_summary,limitations=LIMITATION)
    result['advisor']=advisor(rows[-1] if rows else None,baseline,events)
    result['elapsed_seconds']=time.perf_counter()-started
    if progress: progress(1.,'Complete')
    return result
