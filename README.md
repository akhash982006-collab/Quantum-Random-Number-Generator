# Q-Gaurd

**Intelligent QRNG Reliability, Forensics & Early-Warning System**

A local research prototype that turns digitized bitstreams into reproducible investigations. It detects observed statistical changes, identifies when they were detected, shows their signatures, and recommends what an engineer should inspect. It does not certify a quantum source or cryptographic security.

## Install and run

Python 3.12 is the tested version. From a fresh checkout:

```powershell
cd q-sentinel
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open http://127.0.0.1:8501. No account, API key, cloud service, or quantum hardware is required. On this workspace the ready-to-use environment is in the parent folder:

```powershell
cd D:\PRO\kalasalingam\q-sentinel
..\.venv\Scripts\python.exe -m streamlit run app.py
```

`Launch-Q-Sentinel.cmd` also starts the installed environment. To install development dependencies, use `requirements-dev.txt` in place of `requirements.txt`.

## What works

- Strict TXT/CSV/BIN ingestion, optional external reference, 10-million-bit limit, and content hashes.
- Six NIST SP 800-22 families: Frequency, Block Frequency, Runs, Longest Run, DFT, and Cumulative Sums in both directions.
- Windowed entropy, 8-bit patterns, signed bias, runs, dependence, spectral concentration and repetition.
- Frozen-baseline CUSUM detection, persistent state transitions, explainable signatures, and conditional trend projections.
- **Dedicated Inconsistency Explorer** providing unified event-level records, flagged-bit ranges, plain-language measurement formulas, and interactive binary/hex inspection.
- Interactive streaming Failure Lab, configurable what-if scenarios, healthy/degraded comparison through saved passports, and exact bit/hex inspection.
- Transparent health components, deterministic Q-Advisor explanations, local SQLite history, JSON/CSV/PDF exports, and opt-in raw-bit retention.
- Full multi-page navigation suite with scientific boundaries and clear physical-onset distinctions.

## Five-minute demonstration

Read `DEMO.md` for the timed presentation script and judging pitch.

1. Select **Load healthy demo**. Inspect the computed health, NIST results and fingerprint; save this passport.
2. Select **Run guided degradation demo**. The reproducible scenario uses 30 calibration windows, drift beginning at window 41, and a stuck-output fault at window 91. These are simulation inputs, not prescribed detector outputs.
3. Inspect the first detected event and the CUSUM/signature timelines.
4. Open **Entropy Forensics**, select the suspicious window, and inspect measurements, p-values and actual bits.
5. Open **Degradation Monitor** and choose an earlier forecast window. Projections disappear when the evidence does not support extrapolation.
6. Save a new passport, compare it with the healthy session, and export the report.

For a judge-driven demonstration, open **Failure Lab**, start the healthy stream, and inject a fault. New chunks arrive in five-window batches; pause before discussing results. Remove the injection to examine recovery. The live demo stops at 200 windows. For complete reproducibility, use **What-if Analysis** or the fixed guided demo; interactive sessions preserve their bits only if retention is selected.

## Architecture

```text
FileSource / SimulatorSource -> ordered BitChunk contract -> strict validation
    -> complete windows -> entropy + statistics + NIST
    -> frozen baseline -> calibrated CUSUM + persistent states
    -> signatures + transparent health + conditional forecast
    -> dashboard / forensic viewer / Q-Advisor / SQLite passport / PDF
```

`core/` contains pure analysis, source contracts, monitoring, job management and storage. `nist/` centralizes the six closely related test implementations in `suite.py`. `simulation/` contains the classical engineering model and dataset generator. `ui/` contains shared views and Plotly charts. `reports/` generates exports. `app.py` composes the navigation and controls.

Analysis workers never call Streamlit. The main thread polls job progress, applies completed results, and renders controls. A four-entry in-memory cache uses the bitstream hash, reference hash, window size and score weights. Stopped jobs do not replace the visible completed result. The bounded live demo reanalyzes its accumulated stream to keep historical results reproducible; it is not a production high-throughput acquisition service.

## Methodology

- Windows: default 10,000 bits, non-overlapping. Incomplete trailing bits are excluded from window comparisons but included in whole-stream analysis.
- Baseline: an external reference of at least 30 complete windows, or the first 30 windows labeled **unverified**. A baseline can already contain faults. Initial calibration windows do not receive health scores.
- Detector: two-sided CUSUM over signed bias, lag-one autocorrelation, non-DC spectral concentration and 8-bit block entropy. Standardize with frozen baseline mean and sample standard deviation, with finite-sample variance floors. Allowance 0.5; threshold is at least 12 and calibrated on synthetic IID windows. Accumulators reset after a crossing.
- Status: two consistent windows to escalate; five consistent windows to reduce severity. Thresholds and formulas are visible on the Methodology page. Operational states are heuristics, not physical-source certifications.
- Entropy: Shannon, min and collision entropy are **empirical marginal** measures. Block entropy is an uncorrected descriptive finite-sample estimate. A balanced repeating stream can score 1 bit/bit marginal entropy while being predictable.
- NIST: alpha 0.01. Minimum lengths/prerequisites are enforced. Runs is inapplicable if its frequency prerequisite fails. A family fails when either applicable Cumulative Sums direction fails; inapplicable families are excluded. Pooled p-value charts are descriptive, not an independence-based uniformity test.
- Forecast: Theil-Sen trend over 20 comparable windows, negative upper slope bound, and Spearman correlation below -0.6. Extrapolate to operational health 40 only while above it. Serial dependence limits interval interpretation; no probability of failure is claimed.
- Health: weighted mean of available stability components. Default relative weights are entropy 15, NIST 20, bias 15, correlation 20, temporal 20, trend 10. Formula and unavailable components are exposed. Correlated components are not independent evidence.
- Diagnostics: signature match scores are explainable heuristics, not calibrated probabilities. Q-Advisor is deterministic and uses actual measurements. No LLM or scikit-learn model is necessary for this release.

The DFT toy example in SP 800-22 section 2.6.4 has a numerical inconsistency: the supplied ten bits give five, rather than four, magnitudes below the printed threshold. Tests check the actual transform using an independent direct DFT rather than force the printed p-value. The production DFT requires at least 1,000 bits. Cumulative Sums uses the reference implementation's truncation-toward-zero loop bounds.

## Verification and evaluation

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests -q --basetemp=output/test-temp
python -m simulation.datasets
python evaluate.py
```

Tests cover analytical entropy cases, published NIST examples (with the documented DFT discrepancy), symmetry, applicability, parsing failures, source ordering, deterministic simulation, onset localization, metadata independence, forecasting, cancellation, cache isolation, persistence, exports, PDF bounds, and all major pages. Numerical validation is not NIST certification.

The evaluation uses calibration seeds 910001/910002 and separate evaluation seeds 1201-1205. It retains missed faults and negative lead times. The fixed NIST-only comparator requires two applicable families to fail in two consecutive windows. Positive lead time means Q-Sentinel detected a monitored state before that comparator; a missing comparator is not counted as a lead-time win.

See `VALIDATION.md` and `output/evaluation-summary.json` for measured results. The eight generated CSVs are explicitly identified as **SIMULATED DATA** by `data/simulation_manifest.json`. No actual optical QRNG dataset is bundled.

## Storage and privacy

Only **Save current health passport** persists a session. SQLite contains metrics, events, configuration and provenance, not raw input by default. Opt-in retention writes a NumPy bit array under `data/retained/`. Raw bit downloads are available for the current in-memory session. Local files are not encrypted; this is a single-user research prototype. The server binds only to localhost. Uploaded strings are escaped in PDF output.

## Future hardware integration

Implement `DataSource.chunks()` yielding `BitChunk(sequence, offset, bits)`. Validate values before processing and use `checked_chunks` to reject discontinuities. A real adapter should attach source ID, hardware timestamps, acquisition settings, sample-to-bit conversion metadata and transport counters. Serial/USB/TCP/WebSocket/MQTT implementations should enforce bounded buffers and report loss, duplicates, reordering and backlog separately from statistical degradation. Adapters are extension points, not implemented hardware connections.

Future research: paired raw/post-processed comparison, SP 800-90B source assessment, independently reviewed full SP 800-22 coverage, physical QRNG datasets, calibrated signature probabilities and uncertainty-aware nonstationary models.

## Scientific boundaries

This analysis evaluates statistical and entropy characteristics of the supplied bitstream. It does not independently establish that the source is quantum. A NIST pass does not prove true randomness, physical security, or usable cryptographic entropy. The simulator models engineering signatures, not quantum mechanics. Early warning is demonstrated only where measured; some faults are detected simultaneously with or after NIST, and some are missed.

References: [NIST SP 800-22 Rev.1a](https://csrc.nist.gov/pubs/sp/800/22/r1/upd1/final), [NIST SP 800-90B](https://csrc.nist.gov/pubs/sp/800/90/b/final), [NIST CUSUM control charts](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm).
