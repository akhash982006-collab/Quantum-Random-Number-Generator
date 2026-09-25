# Validation record

This record describes local prototype verification, not certification of a QRNG or a NIST-accredited implementation.

## Numerical checks

Analytical zero/one, biased and balanced-periodic sequences validate entropy calculations. Published SP 800-22 worked examples validate Frequency, Block Frequency, Runs, Longest Run and Cumulative Sums. DFT is checked against an independent direct-transform calculation; the printed ten-bit example has the discrepancy documented in README.md. Production input-length guards remain enabled outside those illustrative reference tests.

Undefined correlation and normalized spectral concentration in constant windows are represented as unavailable, not zero. Unavailable health components are excluded from the weighted mean. JSON exports reject non-finite numeric values.

## Held-out simulation benchmark

Fixed calibration seeds: 910001 and 910002. Held-out evaluation seeds: 1201-1205. Default window length: 10,000 bits. Each scenario: 100 windows; first 30 form the unverified baseline; injected faults start at window 41. Fault strengths: 0.03 and 0.15, except full collapse. Eight fault categories, 75 fault scenarios total, plus five healthy runs.

The NIST-only comparator requires at least two applicable families failing in two consecutive windows. Detection means entering Early Warning, Degraded or Critical; lead time is comparator detection window minus Q-Sentinel detection window. Detection and change-point onset estimation are not synonymous.

Measured results are reproducible in `output/evaluation.csv` and `output/evaluation-summary.json`:

| Measure | Result |
|---|---:|
| Fault scenarios detected | 71 / 75 |
| Missed fault scenarios | 4 |
| Earlier than NIST comparator | 16 |
| Same detection window | 41 |
| Later than NIST comparator | 3 |
| Remaining cases | 15 without a joint detection time; not counted as early-warning wins |
| Healthy monitored windows | 350 |
| False alert transition events | 2 |
| False alert events per 1,000 healthy windows | 5.71 |

The separate 300-window synthetic CUSUM calibration check observed zero threshold crossings. This differs from the end-to-end alert policy and does not imply a zero false-alert probability. The sample is small; more independent seeds and physical-source datasets are necessary.

## Performance

On the available Windows environment, the measured complete warm analysis was approximately 0.9 seconds for one million bits and 10.3 seconds for ten million bits. These are measurements, not guarantees; calibration, CPU contention, selected windows and Streamlit/report rendering affect latency. See the generated output for rerun timings.

## Application and artifact checks

Automated Streamlit tests exercise all eleven pages, healthy and guided scenarios, every injection type, pause/reset, what-if execution, configuration reset, passport saving/loading, and history comparisons. Engine tests cover strict ingestion, hash consistency, ordered source chunks, metadata independence, incomplete windows, references, worker cancellation, cache isolation, forecasts and health weighting.

JSON and CSV are parsed back and compared with computed results. PDF tests check content and page bounds; rendered pages are visually inspected. A localhost browser smoke test confirms the app starts and computes visible results. Hardware adapters, multi-user deployment, formal SP 800-90B assessment and the remaining NIST families are outside this release.

## Demo observations

The fixed guided scenario produces an Early Warning at window 56, a temporary recovery at window 64, Degraded at window 66, and Critical at window 92 with default settings. Conditional projections are available at windows 52-59. These are recorded observations of the selected demo, not hardcoded output or a claim about every degradation scenario.
