# Q-Sentinel: five-minute judge presentation

## Preparation

Launch locally, load the healthy demo, save its passport, and verify the guided demo once. Return to the healthy session. Close unrelated applications. Keep the sample PDF available as a fallback. Use the default 10,000-bit windows and weights. Numbers below are intentionally not scripted: read the computed values on screen.

## 0:00-0:40 — The engineering problem

“A pass/fail result is useful, but an engineer investigating a failing randomness source needs more: when did it change, what changed, and where should we look? Q-Sentinel connects statistical testing with temporal evidence and explainable investigation.”

Show the healthy Command Center. Point out the **unverified baseline** label. Explain that the data is simulated and does not establish quantum origin.

## 0:40-1:20 — Establish the evidence

Open NIST Validation. “We implement six verified test families with applicability checks. A test can be inapplicable; that is different from a pass. We prioritize correct calculations over claiming the full suite.”

Open Entropy Analysis. “This fingerprint summarizes several dimensions. Balanced bits alone are insufficient: a repeated 0101 stream can have maximal marginal entropy.”

## 1:20-2:10 — Introduce degradation

Click **Run guided degradation demo**. “This reproducible engineering scenario introduces slow bias after the reference interval, then a stuck-output fault. The analysis engine sees only the resulting bits, not the fault label.”

Show the health timeline, first detected event and signature map. Read the actual detected window. Distinguish injected onset from first detection. Do not promise every scenario traverses every status.

For audience interaction, open Failure Lab and briefly show the injection controls. Use the guided scenario for consistent timing; the judge can try interactive injection after the pitch.

## 2:10-3:00 — Explain the change

Open Entropy Forensics. Select the first flagged window. Show its bias, baseline difference, CUSUM evidence, test results and exact bit offsets. Then select a collapse window to show the stuck bits.

“Our conclusion is a statistical signature consistent with bias or dependence. It is not a claim that a particular detector is broken.”

## 3:00-3:40 — Conditional early warning

Open Degradation Monitor and choose an earlier window with a supported forecast. Explain the projected crossing and its assumptions. If no forecast is available, show the explicit reason rather than invent one.

“The key question is whether we warn earlier at an acceptable false-alert rate. Our evaluation measures this against a fixed NIST-only policy and retains the failures, missed cases and negative results.”

Use the actual counts from VALIDATION.md. Do not confuse zero events in a small calibration sample with a zero false-alarm probability.

## 3:40-4:30 — Preserve the investigation

Save the degraded passport. Compare its fingerprint with the healthy record. Export the PDF and JSON. Point out the input hash, configuration, method limitations and evidence-linked Q-Advisor summary.

“This is an investigation record that another engineer can reproduce, not just a screenshot of a dashboard.”

## 4:30-5:00 — Differentiation and honest scope

“Our contribution is the connected workflow: controlled fault injection, sequential evidence, exact-window forensics, explainable recommendations and reproducible passports. Hardware adapters can plug into an ordered chunk interface. Formal source validation and full NIST coverage remain future work.”

Close: “Q-Sentinel moves QRNG analysis from a pass/fail result toward continuous reliability intelligence—with the evidence and limitations visible.”

## Short judging pitch

Q-Sentinel is a local QRNG reliability investigation platform. It combines correct statistical screening with temporal monitoring, interactive fault injection, explainable signatures and traceable reports. Its early-warning claims are measured against a fixed baseline rather than staged. The result is useful to an engineer asking when a stream changed and what to investigate next, while keeping statistical evidence separate from physical or quantum certification.
