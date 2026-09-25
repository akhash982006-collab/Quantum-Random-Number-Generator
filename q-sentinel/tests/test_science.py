import math
import numpy as np
import pytest
from nist.suite import frequency,block_frequency,runs,longest_run,dft,cumulative_sums,suite,summary
from core.entropy import entropy_metrics
from core.statistics import metrics
from core.ingestion import ingest,validate,digest
from core.engine import analyze
from core.forecasting import forecast
from core.health_score import health,WEIGHTS
from simulation.qrng_twin import simulate,FAULTS

def bits(s): return np.array(list(s),dtype=np.uint8)

# Published small illustrative examples intentionally bypass production minimums.
# NIST SP800-22rev1a sections 2.1.4, 2.2.4, 2.3.4, 2.4.8, 2.6.4, 2.13.4.
def test_nist_published_examples():
    assert frequency(bits('1011010101'),False)['p_value']==pytest.approx(.527089,abs=1e-6)
    assert block_frequency(bits('0110011010'),3,False)['p_value']==pytest.approx(.801252,abs=1e-6)
    assert runs(bits('1001101011'),False)['p_value']==pytest.approx(.147232,abs=1e-6)
    sequence='11001100 00010101 01101100 01001100 11100000 00000010 01001101 01010001 00010011 11010110 10000000 11010111 11001100 11100110 11011000 10110010'
    assert longest_run(bits(sequence.replace(' ','')))['p_value']==pytest.approx(.180598,abs=2e-5)
    # The printed DFT toy example gives N1=4, but its supplied bits have five
    # magnitudes below sqrt(10*log(20)). Verify by independent direct DFT.
    b=bits('1001010011'); x=b.astype(float)*2-1
    magnitudes=[abs(sum(x[j]*complex(math.cos(-2*math.pi*k*j/10),math.sin(-2*math.pi*k*j/10)) for j in range(10))) for k in range(5)]
    count=sum(v<math.sqrt(10*math.log(20)) for v in magnitudes)
    assert count==5
    expected=math.erfc(abs((count-4.75)/math.sqrt(10*.95*.05/4))/math.sqrt(2))
    assert dft(b,False)['p_value']==pytest.approx(expected)
    assert cumulative_sums(bits('1011010111'),enforce=False)['p_value']==pytest.approx(.4116588,abs=1e-6)

def test_cumsum_reverse_and_complement_symmetry():
    b=simulate(windows=1)
    assert cumulative_sums(b,True)['p_value']==cumulative_sums(b[::-1])['p_value']
    assert cumulative_sums(1-b)['p_value']==pytest.approx(cumulative_sums(b)['p_value'])

def test_dft_production_against_direct_transform():
    b=np.random.default_rng(789).integers(0,2,1000,dtype=np.uint8)
    x=b.astype(float)*2-1; k=np.arange(500)[:,None]; j=np.arange(1000)[None,:]
    magnitudes=np.abs(np.exp(-2j*np.pi*k*j/1000)@x)
    count=np.sum(magnitudes<np.sqrt(np.log(20)*1000))
    expected=math.erfc(abs((count-475)/math.sqrt(1000*.95*.05/4))/math.sqrt(2))
    assert dft(b)['p_value']==pytest.approx(expected,abs=1e-12)

def test_constant_pipeline_has_no_invented_correlation():
    result=analyze(np.zeros(400000,dtype=np.uint8))
    assert result['windows'][-1]['components']['correlation'] is None
    assert result['windows'][-1]['state']=='Critical'
    from reports.generator import export_json
    assert b'NaN' not in export_json(result)

@pytest.mark.parametrize('value',[0,1])
def test_constant(value):
    b=np.full(10000,value,dtype=np.uint8); e=entropy_metrics(b)
    assert e['shannon']==0 and e['min_entropy']==0 and e['collision']==0
    assert metrics(b)['autocorrelation'] is None and metrics(b)['spectral'] is None
    s=suite(b); assert s[0]['status']=='FAIL' and s[2]['status']=='NOT APPLICABLE'

def test_balanced_predictable():
    b=np.tile([0,1],5000).astype(np.uint8); e=metrics(b)
    assert e['shannon']==1 and e['min_entropy']==1 and e['collision']==1
    assert e['block_entropy']==0 and e['autocorrelation']<-.99
    assert runs(b)['status']=='FAIL'

def test_entropy_analytical():
    b=np.r_[np.zeros(750,dtype=np.uint8),np.ones(250,dtype=np.uint8)]
    e=entropy_metrics(b)
    assert e['shannon']==pytest.approx(-.25*math.log2(.25)-.75*math.log2(.75))
    assert e['min_entropy']==pytest.approx(-math.log2(.75))
    assert e['collision']==pytest.approx(-math.log2(.625))

@pytest.mark.parametrize('raw,name',[(b'0102','x.txt'),(b'bit\n0\n2\n','x.csv'),(b'other\n1\n','x.csv'),(b'bit,extra\n0,1','x.csv'),(b'','x.bin'),(b'bit\n0\n\n1','x.csv'),(b'bit\n0.0\n','x.csv')])
def test_bad_inputs(raw,name):
    with pytest.raises(ValueError): ingest(raw,name)

def test_input_order_and_hash():
    b,_=ingest(b'\x81','x.bin'); assert b.tolist()==[1,0,0,0,0,0,0,1]
    a,_=ingest(b'1 0\n1\t0','x.txt'); assert a.tolist()==[1,0,1,0]
    c,_=ingest(b'bit\n1\n0\n1\n0','x.csv'); assert digest(a)==digest(c)
    with pytest.raises(ValueError): validate(np.zeros(10_000_001,dtype=np.uint8))

@pytest.mark.parametrize('fault',FAULTS)
def test_simulation_reproducible(fault):
    a=simulate(77,50,1000,fault,.3,35,15); b=simulate(77,50,1000,fault,.3,35,15)
    assert np.array_equal(a,b)
    healthy=simulate(77,50,1000)
    assert np.array_equal(a[:35000],healthy[:35000])
    if fault!='Healthy': assert not np.array_equal(a[35000:],healthy[35000:])

def test_pipeline_onset_and_metadata_independence():
    b=simulate(fault='Sudden failure',windows=65,start=40,duration=10)
    r=analyze(np.r_[b,[1,0,1]],dict(fault='deliberately incorrect label'))
    assert r['data_quality']['trailing_bits']==3
    assert all(w['state']=='Calibrating' for w in r['windows'][:30])
    critical=next(e for e in r['events'] if e['state']=='Critical')
    assert 41<=critical['window']<=43
    assert any(e['kind']=='Recovery' for e in r['events'])
    other=analyze(np.r_[b,[1,0,1]],dict(fault='Healthy'))
    assert r['windows']==other['windows'] and r['events']==other['events']

def test_short_and_external_reference():
    short=analyze(np.zeros(17,dtype=np.uint8)); assert short['baseline']['status']=='Insufficient Data'
    partial=analyze(simulate(windows=10)); assert 'Calibration incomplete' in partial['advisor']
    reference=simulate(seed=700,windows=30)
    result=analyze(simulate(seed=701,windows=4),reference=reference)
    assert result['baseline']['status']=='External reference supplied'
    assert all(w['state']!='Calibrating' for w in result['windows'])
    with pytest.raises(ValueError): analyze(reference,reference=reference[:100])

def test_forecast_and_score():
    f=forecast(list(np.linspace(95,65,20)))
    assert f['available'] and f['windows_to_threshold']>0 and f['slope']<0
    assert not forecast([95]*30)['available']
    assert not forecast(list(range(60,90)))['available']
    score,components=health(np.zeros(4),1,0,None)
    assert score==100 and components['trend'] is None
    assert 0<=health(np.full(4,15),0,1,1)[0]<=100
