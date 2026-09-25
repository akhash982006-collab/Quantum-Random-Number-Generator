import json
import io
import numpy as np
import pandas as pd
import fitz
import pytest

from core.engine import analyze
from core.inconsistencies import extract_inconsistencies, MEASUREMENT_EXPLANATIONS, get_measurement_info
from simulation.qrng_twin import simulate, FAULTS
from reports.generator import pdf, export_json, export_csv

def test_healthy_stream_no_false_inconsistencies():
    b = simulate(seed=42, windows=60, fault='Healthy')
    r = analyze(b)
    assert 'inconsistencies' in r
    assert 'inconsistency_summary' in r
    assert r['inconsistencies'] == []
    assert r['inconsistency_summary']['total_events'] == 0
    assert r['inconsistency_summary']['unique_affected_windows'] == 0
    assert r['inconsistency_summary']['highest_severity'] == 'Healthy'

@pytest.mark.parametrize('val', [0, 1])
def test_constant_streams(val):
    b = np.full(400000, val, dtype=np.uint8)
    r = analyze(b)
    assert len(r['inconsistencies']) >= 1
    inc = r['inconsistencies'][0]
    assert inc['severity'] == 'Critical'
    assert inc['affected_windows_count'] > 0
    # First monitored window is window 31/32 after initial 30 calibration windows
    assert inc['bit_start'] == (inc['first_detected_window'] - 1) * 10000
    assert inc['bit_end'] == (inc['affected_windows'][-1] * 10000) - 1
    assert 'defective individual bit' not in inc['evidence_explanation'].lower()

def test_constant_stream_with_external_reference():
    ref = simulate(seed=50, windows=30)
    b = np.zeros(50000, dtype=np.uint8)
    r = analyze(b, reference=ref)
    assert len(r['inconsistencies']) >= 1
    inc = r['inconsistencies'][0]
    assert inc['severity'] == 'Critical'
    assert inc['first_detected_window'] <= 2
    assert inc['bit_start'] == (inc['first_detected_window'] - 1) * 10000

def test_biased_stream():
    b = simulate(seed=101, windows=60, fault='Bias', intensity=0.25, start=35, duration=20)
    r = analyze(b)
    assert len(r['inconsistencies']) >= 1
    inc = r['inconsistencies'][0]
    assert inc['type'] == 'Bit bias'
    assert 35 <= inc['first_detected_window'] <= 40
    assert inc['diff_from_baseline']['bias_delta'] > 0.15
    assert inc['bit_start'] == (inc['first_detected_window'] - 1) * 10000
    assert 'inspection sample' in inc['measurement_explanation']['disclaimer'].lower() or 'inspection evidence' in inc['evidence_explanation'].lower()

def test_periodic_stream():
    b = simulate(seed=202, windows=60, fault='Periodicity', intensity=0.4, start=35, duration=20)
    r = analyze(b)
    assert len(r['inconsistencies']) >= 1
    inc = r['inconsistencies'][0]
    assert inc['type'] in ['Periodic pattern', 'Mixed failure', 'Serial correlation']
    assert 35 <= inc['first_detected_window'] <= 40

def test_correlated_stream():
    b = simulate(seed=303, windows=60, fault='Correlation', intensity=0.35, start=35, duration=20)
    r = analyze(b)
    assert len(r['inconsistencies']) >= 1
    inc = r['inconsistencies'][0]
    assert inc['type'] in ['Serial correlation', 'Mixed failure', 'Periodic pattern']
    assert 35 <= inc['first_detected_window'] <= 40
    assert inc['observed_values']['autocorrelation'] is not None

def test_repeated_sequence_stream():
    b = simulate(seed=404, windows=60, fault='Repetition', intensity=0.4, start=35, duration=20)
    r = analyze(b)
    assert len(r['inconsistencies']) >= 1
    inc = r['inconsistencies'][0]
    assert inc['first_detected_window'] >= 35

def test_burst_fault_stream():
    b = simulate(seed=505, windows=60, fault='Burst noise', intensity=0.4, start=35, duration=20)
    r = analyze(b)
    assert len(r['inconsistencies']) >= 1
    inc = r['inconsistencies'][0]
    assert inc['first_detected_window'] >= 35
    assert len(inc['flagged_ranges']) >= 1
    for fr in inc['flagged_ranges']:
        assert fr['start'] >= 0
        assert fr['end'] >= fr['start']
        assert fr['length'] == fr['end'] - fr['start'] + 1

def test_gradual_drift_stream():
    b = simulate(seed=606, windows=70, fault='Gradual degradation', intensity=0.3, start=35, duration=35)
    r = analyze(b)
    assert len(r['inconsistencies']) >= 1
    inc = r['inconsistencies'][0]
    assert inc['first_detected_window'] >= 35
    assert r['inconsistency_summary']['total_events'] >= 1

def test_sudden_collapse_stream():
    b = simulate(seed=707, windows=60, fault='Sudden failure', intensity=0.5, start=35, duration=20)
    r = analyze(b)
    assert len(r['inconsistencies']) >= 1
    inc = r['inconsistencies'][0]
    assert inc['severity'] in ['Degraded', 'Critical']
    assert 35 <= inc['first_detected_window'] <= 40

def test_mixed_failure_stream():
    b = simulate(seed=808, windows=60, fault='Mixed failure', intensity=0.4, start=35, duration=20)
    r = analyze(b)
    assert len(r['inconsistencies']) >= 1
    inc = r['inconsistencies'][0]
    assert inc['first_detected_window'] >= 35

def test_insufficient_data_stream():
    b = simulate(seed=909, windows=10)
    r = analyze(b)
    assert r['inconsistencies'] == []
    assert r['inconsistency_summary']['total_events'] == 0

def test_deduplication_and_window_integrity():
    # Degradation across 15 windows should be a unified single event with 15 affected windows
    b = simulate(seed=42, windows=60, fault='Bias', intensity=0.3, start=35, duration=15)
    r = analyze(b)
    # Event count is small and deduplicated
    assert len(r['inconsistencies']) <= 2
    inc = r['inconsistencies'][0]
    assert len(inc['affected_windows']) == len(set(inc['affected_windows']))
    assert inc['affected_windows_count'] == len(inc['affected_windows'])
    assert inc['bit_start'] == (inc['first_detected_window'] - 1) * r['config']['window_size']
    assert inc['bit_end'] == (inc['affected_windows'][-1] * r['config']['window_size']) - 1

def test_exports_contain_inconsistencies():
    b = simulate(seed=42, windows=60, fault='Bias', intensity=0.3, start=35, duration=15)
    r = analyze(b)
    
    # 1. JSON export
    json_bytes = export_json(r)
    parsed = json.loads(json_bytes)
    assert 'inconsistencies' in parsed
    assert len(parsed['inconsistencies']) == len(r['inconsistencies'])
    assert parsed['inconsistency_summary'] == r['inconsistency_summary']
    
    # 2. CSV export
    csv_bytes = export_csv(r)
    df = pd.read_csv(io.BytesIO(csv_bytes))
    assert 'inconsistency_id' in df.columns
    # Check that tagged windows match
    for inc in r['inconsistencies']:
        for w in inc['affected_windows']:
            row_match = df[df['window'] == w]
            assert not row_match.empty
            assert row_match.iloc[0]['inconsistency_id'] == inc['id']
            
    # 3. PDF report
    pdf_bytes = pdf(r)
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    full_text = ' '.join(page.get_text() for page in doc)
    assert 'Inconsistency Explorer Dossier' in full_text
    assert r['inconsistencies'][0]['id'] in full_text
    assert 'Total Inconsistency Events' in full_text
    assert 'physical onset is unknown' in full_text

def test_measurement_explanations():
    types_to_test = ['Bit bias', 'Serial correlation', 'Periodic pattern', 'Burst error', 'Repeated sequence', 'Sudden collapse', 'Gradual drift', 'Mixed failure', 'Unknown / unclassified']
    for t in types_to_test:
        info = get_measurement_info(t)
        assert 'formula' in info
        assert 'how_measured' in info
        assert 'evidence_text' in info
        assert 'recommended_check' in info
        assert 'disclaimer' in info
