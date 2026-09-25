import time
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from core.engine import analyze
from simulation.qrng_twin import simulate

PAGES=['COMMAND CENTER','DATA INGESTION','INCONSISTENCY EXPLORER','ENTROPY ANALYSIS','NIST VALIDATION','DEGRADATION MONITOR','ENTROPY FORENSICS','FAILURE LAB','WHAT-IF ANALYSIS','QRNG HEALTH PASSPORT','REPORTS','METHODOLOGY']

@pytest.fixture(scope='module')
def payload():
    b=simulate(windows=60,fault='Gradual degradation',start=40,duration=20)
    return b,analyze(b,dict(name='SIMULATED UI test',source='simulation'))

@pytest.mark.parametrize('page',PAGES)
def test_page(page,payload):
    at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=30)
    at.session_state['bits']=payload[0]; at.session_state['result']=payload[1]
    at.run(); at.sidebar.radio[0].set_value(page).run()
    assert not at.exception, [(e.message) for e in at.exception]

def button(at,label): return next(b for b in at.button if b.label==label)

def finish(at):
    job=at.session_state['job']
    if job: job.future.result(timeout=30)
    at.run()
    assert not at.exception

def test_demo_and_lab_controls():
    at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=30).run()
    button(at,'Load healthy demo').click().run(); finish(at)
    assert at.session_state['result']['metadata']['simulated']
    at.sidebar.radio[0].set_value('FAILURE LAB').run()
    button(at,'Start healthy stream').click().run(); finish(at)
    button(at,'Inject Bias').click().run()
    assert at.session_state['live_fault']=='Bias'
    for fault in ['Correlation','Periodicity','Burst noise','Repetition','Gradual degradation','Sudden failure','Mixed failure']:
        button(at,'Inject '+fault).click().run()
        assert at.session_state['live_fault']==fault and not at.exception
    button(at,'Remove injection / observe recovery').click().run()
    assert at.session_state['live_fault']=='Healthy'
    button(at,'Pause stream').click().run(); finish(at)
    assert not at.session_state['live']
    button(at,'Reset lab').click().run()
    assert at.session_state['result'] is None

def test_settings_reset(payload):
    at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=30)
    at.session_state['bits']=payload[0]; at.session_state['result']=payload[1]; at.run()
    next(x for x in at.selectbox if x.label=='Window size').set_value(1000)
    button(at,'Apply settings / reset baseline').click().run()
    assert at.session_state['size']==1000 and at.session_state['result'] is None

def test_what_if_and_passport(payload,tmp_path,monkeypatch):
    # Keep UI persistence isolated from the user's saved sessions.
    import core.persistence as persistence
    original_save=persistence.save; original_sessions=persistence.sessions; original_load=persistence.load
    db=tmp_path/'ui.sqlite3'
    monkeypatch.setattr(persistence,'save',lambda r,bits=None:original_save(r,db,bits))
    monkeypatch.setattr(persistence,'sessions',lambda:original_sessions(db))
    monkeypatch.setattr(persistence,'load',lambda i:original_load(i,db))
    at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=30)
    at.session_state['bits']=payload[0]; at.session_state['result']=payload[1]; at.run()
    at.sidebar.radio[0].set_value('WHAT-IF ANALYSIS').run()
    button(at,'Run scenario').click().run(); finish(at)
    at.sidebar.radio[0].set_value('QRNG HEALTH PASSPORT').run()
    button(at,'Save current health passport').click().run()
    assert len(original_sessions(db))==1
    button(at,'Open saved session').click().run()
    assert at.session_state['bits'] is None and not at.exception
