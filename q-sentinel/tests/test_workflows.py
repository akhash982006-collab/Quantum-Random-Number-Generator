import json
from threading import Event
import numpy as np
import pandas as pd
import fitz
import pytest
from core.engine import analyze
from core.persistence import save,load,sessions
from core.jobs import AnalysisJob
from core.health_score import WEIGHTS
from core.sources import FileSource,BitChunk,checked_chunks
from simulation.qrng_twin import simulate
from reports.generator import pdf,export_json,export_csv

@pytest.fixture(scope='module')
def result(): return analyze(simulate(windows=60,fault='Bias',start=40,duration=20))

def test_reports_and_passport(result,tmp_path):
    db=tmp_path/'sessions.db'; save(result,db); save(result,db)
    assert len(sessions(db))==1 and load(result['session_id'],db)==result
    assert json.loads(export_json(result))==result
    import io
    assert len(pd.read_csv(io.BytesIO(export_csv(result))))==60
    doc=fitz.open(stream=pdf(result),filetype='pdf')
    text=' '.join(p.get_text() for p in doc)
    assert len(doc)>=3 and 'Scientific Interpretation' in text and result['session_id'] in text
    assert 'not independently establish' in text
    for page in doc:
        for block in page.get_text('blocks'):
            assert block[0]>=0 and block[2]<=page.rect.width+1 and block[3]<=page.rect.height

def test_stop_and_cache():
    b=simulate(windows=40); stop=Event(); stop.set()
    with pytest.raises(InterruptedError): analyze(b,cancel=stop)
    a=AnalysisJob(b,dict(name='A'),10000,WEIGHTS); first=a.future.result(timeout=30)
    second=AnalysisJob(b,dict(name='B'),10000,WEIGHTS).future.result(timeout=30)
    assert first['windows']==second['windows'] and first['session_id']!=second['session_id']
    assert second['metadata']['name']=='B'

def test_transport():
    assert len(list(checked_chunks(FileSource(np.zeros(25000,dtype=np.uint8)))))==3
    class Broken(FileSource):
        def chunks(self,size=10000): yield BitChunk(1,0,self.bits)
    with pytest.raises(ValueError): list(checked_chunks(Broken(np.zeros(10))))
