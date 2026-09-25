import numpy as np

from core.degradation import analyze_degradation
from core.entropy import metrics, window_metrics
from core.simulator import degrading_stream, generate_stream
from nist.suite import run_suite


def test_uniform_stream_is_high_entropy():
    result = metrics(generate_stream("Ideal random", 8192))
    assert result["shannon"] > 0.98


def test_constant_stream_is_low_entropy():
    result = metrics(np.zeros(1024, dtype=np.int8))
    assert result["shannon"] == 0
    assert result["min_entropy"] == 0


def test_nist_suite_is_data_derived():
    result = run_suite(generate_stream("Ideal random", 4096))
    assert len(result) >= 8
    assert result["p_value"].notna().sum() >= 7


def test_degrading_stream_health_falls():
    timeline = window_metrics(degrading_stream(32768, windows=8), 4096)
    analyzed, _ = analyze_degradation(timeline)
    assert analyzed["health_score"].iloc[-1] < analyzed["health_score"].iloc[0]
