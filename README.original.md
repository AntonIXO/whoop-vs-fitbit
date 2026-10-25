# Lab validation does not survive contact with the real world

**68 nights wearing a Fitbit Charge 6 and a WHOOP 4.0 simultaneously, tested
against what the polysomnography literature predicts.**

Article project. All data extracted read-only from the live OptiHealth DB;
all statistics reuse the OptiHealth engine's own methods
(`/opt/optihealth_analysis/src/analysis/`). Every number in `draft.md` is
produced by a script and machine-verified against the JSON outputs.

## The thesis

Lab validation studies report each device's **bias vs PSG**. Those biases make a
prediction that lab studies cannot test themselves: two devices worn at the same
time should differ by the *difference of their biases*. This project tests that.

| Quantity | Lab predicts (WHOOP−Fitbit) | Observed (68 nights) | 95% CI | verdict |
|---|---|---|---|---|
| Deep sleep | +33.7 min | **+26.3** | [22.5, 32.0] | 78% transfers |
| REM | +15.5 min | **−2.3** | [−6.5, +2.7] | **sign flips** |
| Total sleep | +13.3 min | **−9.5** | [−13.5, −2.9] | **sign flips** |

Lab reference: Schyvens et al. 2025, *SLEEP Advances* 6(2):zpaf021, n=62.

## Layout

```
data/
  extract.sh           phase 1 — paired sleep/RHR/steps/strain series
  extract_phase2.sh    wide nightly frame + nocturnal HRV/SpO2/HR + next-day outcomes
  extract_phase3.sh    ECG criterion + per-source workout logs
  *.csv                extracted data (read-only SELECTs, no PII)
analysis/
  run_analysis.py            phase 1 — agreement statistics
  phase2_information.py      Q1-Q5: convergent/predictive validity, gap drivers,
                             decomposition, reliability ceiling
  phase3_events_ecg.py       Q6-Q7: workout ontology, ECG as criterion instrument
  phase4_literature_test.py  the core test: does the lab bias transfer?
  make_figures*.py           figures 1-10
  results*.json              full statistical families with q-values
figures/fig1..fig10.png
draft.md                     the paper
```

## Reproduce

```bash
PY=/opt/optihealth_analysis/src/.venv/bin/python
bash data/extract.sh && bash data/extract_phase2.sh && bash data/extract_phase3.sh
$PY analysis/run_analysis.py
$PY analysis/phase2_information.py
$PY analysis/phase3_events_ecg.py
$PY analysis/phase4_literature_test.py
$PY analysis/make_figures.py
$PY analysis/make_figures_phase2.py
$PY analysis/make_figures_phase4.py
```

## Methods (inherited from the engine)

| Engine module | Applied here |
|---|---|
| `serial.py` | every p is a **circular block permutation**, ℓ=⌈T^{1/3}⌉=5 — daily series are autocorrelated and i.i.d. nulls over-reject |
| `feed_policy.py` | all 32 phase-2 hypotheses are **one BH-FDR family**, ship only q ≤ 0.10 |
| `composition.py` | stage minutes are compositional → tested raw **and** as share of TST |
| `partial_correlation.py` | rank-residualised partial correlation for gap-vs-bedtime controlling the TST gap |
| `verdicts.py` / `power.py` | MDE ≈ 0.34 SD at n=68, stated up front so nulls are informative |
| moving-block bootstrap | 20 000 resamples for CIs on paired gaps |

## Headline findings

1. **Lab bias transfer is quantity-dependent.** Stage classification (deep
   sleep) transfers at 78%; boundary detection (TST, REM) inverts.
2. **The +26 min deep gap is 108% stage reassignment.** WHOOP records 9.5 min
   *less* total sleep and still finds 26 min more deep sleep. Fitbit calls 21.3%
   of the night deep; WHOOP calls 27.8%.
3. **Zero of 32 hypotheses survive FDR.** Best q = 0.139 (Fitbit deep → next-day
   RHR, ρ=−0.32, p=0.006). Reported as hypothesis-generating, not as a finding.
4. **The devices disagree a workout happened**: 202 vs 144 sessions over 44 days,
   Wilcoxon p=3.8e-06; workout kcal ρ=0.11; 31 days WHOOP-only.
5. **Both read low vs single-lead ECG**: Fitbit −4.1 bpm, WHOOP −8.3 bpm.
   Our R-peak detector matches the device's own ECG label to 0.79 bpm.
6. **Reliability ceiling**: inter-device ρ=0.52 on deep sleep caps any
   single-device downstream correlation at ≈0.72. Detecting a true ρ=0.3 needs
   85 nights.

## Verification

`analysis/` outputs are checked by a script that re-reads every quoted figure
from the JSON and compares it to the draft — 16/16 PASS. No number in the paper
is hand-transcribed.

## Not included, deliberately

- **Oura**: 5 nights in the DB. No statistics possible.
- **Epoch-level Cohen's κ**: only 4 nights carry both hypnograms, and WHOOP
  writes only `unknown`/`awake` to Health Connect — no stage detail.
- **P2 (Apr–May 2026)**: 6 staged nights, used only for directional replication.
