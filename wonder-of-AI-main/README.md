# Q-Guard

**Quantum Randomness Intelligence & Entropy Validation Platform**

> Measure randomness. Detect degradation. Trust your entropy.

Q-Guard is a Streamlit MVP for validating the statistical health and entropy quality of raw QRNG output. It deliberately does **not** claim that passing statistical tests proves a source is quantum. Statistical validation is distinct from quantum-origin verification.

## Features

- CSV, TXT, and raw binary ingestion with format detection, invalid-value reporting, duplicate-section checks, and an explicit preprocessing log.
- Deterministic synthetic profiles: ideal random, biased, repeating pattern, correlated, burst error, low entropy, and a healthy-to-degraded entropy attack.
- Shannon, min, collision, bias, runs, autocorrelation, and windowed entropy metrics.
- Implemented MVP tests: Frequency, Block Frequency, Runs, Longest Run, DFT, Approximate Entropy, Serial, and Cumulative Sums. Binary Matrix Rank, template matching, Maurer's Universal, and Random Excursions are marked planned in the UI.
- Explainable degradation scoring, health components, alert windows, root-cause hypotheses, and recommendations.
- Interactive Plotly dashboard plus PDF, CSV results, window metrics, and analyzed-bit exports.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Run tests:

```bash
pytest -q
```

## 5-minute demo

1. Open Overview and show the simulated ideal stream's health score and entropy timeline.
2. Open NIST Test Suite and explain PASS as evidence relative to a null hypothesis, not proof of quantum origin.
3. Open Simulation Lab and click **Run entropy attack**.
4. Open Degradation Monitor to show the first affected window and score decline.
5. Open Root Cause Analysis to show measured evidence and recommendations.
6. Open Reports and download the PDF plus window-wise CSV.
7. Click **Restore health** and verify the timeline returns to a stable profile.

## Architecture

`core/` owns ingestion, simulation, entropy metrics, degradation, diagnostics, and scoring. `nist/` owns statistical tests. `ui/` owns Streamlit presentation helpers. `reports/` produces evidence-based PDFs. A physical QRNG adapter can replace `core.simulator` at the ingestion boundary without changing downstream analysis.

## Limitations and future work

This is an MVP, not a certification tool. Full NIST parameterization, larger sequence requirements, multiple-stream testing, calibration metadata, cryptographic conditioning audits, and quantum-origin verification protocols remain future work. Hardware integration can target an optical photon source, beam splitter, single-photon detector, photon detection electronics, ADC/acquisition system, and USB/serial/network stream.
