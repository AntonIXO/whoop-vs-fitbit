# Fitbit Readiness versus WHOOP Recovery

## Source coverage

This is a read-only extraction for Anton's user ID. Fitbit Readiness is source `11067` (`custom:fitbit`), metric `fitbit_readiness_score` (ID 537). WHOOP Recovery is metric ID 35, split between WHOOP account identities:

| Source | Identifier | n | Date range |
|---:|---|---:|---|
| Fitbit | `custom:fitbit` | 317 | 2025-10-24–2026-10-21 |
| WHOOP | `whoop:31695515` / 2754 | 71 | 2025-10-14–2025-12-24 |
| WHOOP | `whoop:36797758` / 2757 | 23 | 2026-04-25–2026-05-26 |

The source identities are not pooled as one continuous WHOOP instrument. Same-day pairing produces 61 rows: 57 from source 2754 and 4 from source 2757.

## Paired results

| Cohort | n | Pearson r | Spearman ρ | WHOOP − Fitbit mean | MAE | RMSE |
|---|---:|---:|---:|---:|---:|---:|
| Source 2754 | 57 | 0.759 | 0.812 | +8.25 | 12.98 | 15.96 |
| Source 2757 | 4 | 0.132 | −0.400 | +23.75 | 23.75 | 26.69 |
| Pooled paired rows | 61 | 0.735 | 0.766 | +9.26 | 13.69 | 16.87 |

WHOOP is higher than Fitbit on 48/61 paired days; Fitbit is higher on 11/61; exactly equal on 2/61.

A seven-day moving-block bootstrap, preserving each WHOOP source cohort separately, gives these pooled 95% intervals:

| Statistic | 95% block-bootstrap interval |
|---|---:|
| Spearman ρ | 0.623–0.855 |
| Pearson r | 0.598–0.848 |
| WHOOP − Fitbit mean offset | +5.77 to +12.89 points |
| MAE | 11.54–15.95 points |

The four-day source-2757 cohort is retained as a separate descriptive cohort and is not interpreted as an independent concordance estimate.

## Product-band cross-tabulation

Fitbit: low `<30`, moderate `30–64`, high `65–100`. WHOOP: red `0–33`, yellow `34–66`, green `67–100`.

| Fitbit / WHOOP band | n |
|---|---:|
| High / Green | 20 |
| Moderate / Yellow | 18 |
| Low / Red | 1 |
| Moderate / Green | 13 |
| Low / Yellow | 6 |
| Moderate / Red | 2 |
| High / Yellow | 1 |

Ordinal bands agree on 39/61 days (63.9%). WHOOP green occurs on 33 paired days; Fitbit high occurs on 21. Fitbit low occurs on 7 days; WHOOP red occurs on 3.

## Interpretation

The paired scores have substantial monotonic agreement, especially in the larger source-2754 cohort, but a systematic level offset. WHOOP generally reports a higher Recovery value for the same date. The values should not be aligned with a constant correction or treated as interchangeable scores.

The uploaded data contains no `fitbit_resilience_score` rows. This report therefore makes no Fitbit-resilience-versus-WHOOP claim.

## OptiHealth engine cross-check

The latest published run predates the Fitbit metric registration/catalog generation; the current worker frame and multi-horizon correlation path include Fitbit Readiness. The current read-only probe emits four stable Readiness cards against HRV RMSSD, HR minimum, resting HR and respiratory-rate minimum across the configured horizons.

Over the 317 Fitbit Readiness days:

| OptiHealth series | n | Raw Spearman ρ | Season-adjusted Spearman ρ |
|---|---:|---:|---:|
| HRV RMSSD | 317 | **+0.793** | **+0.809** |
| Resting HR | 317 | **−0.558** | **−0.552** |
| Respiratory rate | 316 | −0.336 | −0.367 |
| Total sleep duration | 316 | −0.015 | −0.007 |
| Deep sleep minutes | 315 | +0.011 | +0.015 |
| REM minutes | 315 | +0.015 | +0.033 |
| WHOOP Recovery | 61 | **+0.766** | **+0.794** |

The interesting result is the separation between **autonomic physiology and sleep quantity**. Fitbit Readiness tracks OptiHealth HRV and resting HR strongly, while it is effectively unrelated to total sleep minutes or stage minutes in this window. That is consistent with a score responding to physiological recovery state rather than simply rewarding a longer night.

The same OptiHealth comparison for WHOOP Recovery is:

| OptiHealth series | n | Raw Spearman ρ | Season-adjusted Spearman ρ |
|---|---:|---:|---:|
| HRV RMSSD | 89 | **+0.681** | **+0.750** |
| Resting HR | 94 | **−0.453** | **−0.473** |
| Respiratory rate | 94 | **−0.483** | **−0.563** |
| Total sleep duration | 94 | +0.352 | **+0.385** |
| Deep sleep minutes | 81 | +0.180 | +0.203 |
| REM minutes | 81 | +0.136 | +0.129 |

The WHOOP-minus-Fitbit score gap also grows with the available sleep measures on the 61 paired days: Pearson `r = +0.60` for total sleep and `r = +0.49` for REM, with weaker rank associations (`ρ = +0.36` and `+0.29`). This is exploratory and serially dependent, but it suggests that the two products may use sleep quantity and architecture differently when converting the same night into a morning score.

The machine-readable outputs are `optihealth_results.json` and `optihealth_run_metadata.json`; the joined daily input is `data/readiness_optihealth_wide.csv`.

## Serial-aware hypothesis scan

I tested 16 pre-specified same-day, one-day-lagged and score-gap hypotheses after removing annual harmonic seasonality. The null used OptiHealth's circular block permutation, with 5,000 resamples and Benjamini–Hochberg correction across the family (`q <= 0.10`). These are association results, not causal effects.

| Hypothesis | n | Season-adjusted ρ | q |
|---|---:|---:|---:|
| Readiness ↔ HRV RMSSD | 317 | **+0.809** | 0.0004 |
| Readiness ↔ resting HR | 317 | **−0.552** | 0.0004 |
| Readiness ↔ respiratory rate | 316 | **−0.367** | 0.0004 |
| Readiness ↔ WHOOP Recovery | 61 | **+0.794** | 0.0004 |
| Readiness ↔ Oura Readiness | 56 | **+0.589** | 0.0004 |
| Readiness today ↔ HRV tomorrow | 293 | +0.380 | 0.0004 |
| HRV today ↔ Readiness tomorrow | 293 | +0.390 | 0.0004 |
| Readiness today ↔ resting HR tomorrow | 293 | **−0.497** | 0.0004 |
| Resting HR today ↔ Readiness tomorrow | 293 | −0.347 | 0.0004 |
| WHOOP−Fitbit gap ↔ total sleep | 61 | +0.330 | **0.0083** |
| WHOOP−Fitbit gap ↔ REM | 61 | +0.313 | **0.0180** |
| Readiness ↔ total sleep | 316 | −0.007 | 0.8858 |
| Readiness ↔ deep sleep | 315 | +0.015 | 0.8391 |
| Readiness ↔ REM minutes | 315 | +0.033 | 0.5985 |

The lagged results are deliberately not narrated as direction: both directions are present. They show a persistent physiological state, not that Readiness causes tomorrow's HRV or that HRV causes tomorrow's Readiness. The strongest robust conclusion is narrower: **Readiness is an autonomic-state composite, with HRV and resting HR carrying the signal; raw sleep duration and stage minutes do not.**

The scan is in `hypothesis_scan.json`, generated by `hypothesis_scan.py`.

