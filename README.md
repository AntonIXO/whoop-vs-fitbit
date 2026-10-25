# Fitbit vs WHOOP: paired-wear article

English article: **[draft.md](draft.md)**. English definitions: **[GLOSSARY.md](GLOSSARY.md)**.

This is a revised translation with a TRIMP-focused Strain audit and a primary-source algorithm timeline. Original Russian text is preserved in `draft.ru.original.md` and `GLOSSARY.ru.original.md`; the earlier project overview is `README.original.md`.

## What the local data cover

| Export | Observations | Observed date bounds |
|---|---:|---|
| P1 original paired staged sleep CSV | 68 nights | 2025-10-11–2025-12-23 |
| P1 fresh source-separated sleep DB audit | 70 pairs (71 Fitbit / 74 WHOOP main sleeps) | 2025-10-08–2025-12-24 |
| P2 fresh source-separated sleep DB audit | 28 Fitbit / 0 WHOOP source 2754; 17 WHOOP source 2757 main sleeps + 1 nap in May | 2026-04-22–2026-05-28 |
| P2 historical paired steps CSV | 25 days | 2026-05-01–2026-05-28 |
| P1 historical Strain wide table | 74 days | 2025-10-08–2025-12-24 |
| Fresh activity/pulse audit | source-specific P1/P2 inventories | Same windows |

These are bounds of observations in selected exports, not proof of continuous physical wear. The fresh audit keeps P1/source 2754 and P2/source 2757 separate; P2 is not a replication of P1.

## Main findings

- The fresh source-separated P1 audit finds 70 main-sleep pairs. Fitbit reports 12.6 more awake minutes, 35.0 more light-sleep minutes, 26.7 fewer deep-sleep minutes, and 24.7 more minutes in bed than WHOOP on average. WHOOP latency and awakenings are absent from the ingestion path; they are not zeros.
- P2 includes 28 Fitbit main sleeps and 17 main May nights plus one nap from active WHOOP source 2757. The old WHOOP source 2754 has no sessions in this window; the two source identities remain separate cohorts and are not pooled with P1.
- Fresh P1 Strain correlations with Fitbit source 35 are +0.046 steps, +0.089 moderate minutes, −0.020 vigorous minutes and +0.091 total calories. P2 source-specific results are reported separately and are not a replication.
- No timestamped WHOOP HR points were present in either fresh period, so no direct intraday pulse comparison or HR-based TRIMP reconstruction is claimed.
- The local aggregate HR columns cannot reconstruct actual Banister/Edwards TRIMP. Nonstandard weighted-threshold proxies are labelled as such.
- The year-long Fitbit upload contains 317 Readiness scores. Against 61 same-day WHOOP Recovery pairs, Spearman ρ = 0.766, mean WHOOP−Fitbit offset = +9.3 points, MAE = 13.7 points, and ordinal product-band agreement = 39/61 (63.9%). WHOOP is higher on 48/61 days. No Fitbit resilience values were uploaded, so no resilience comparison is claimed.
- Inter-device correlation does not identify a reliability ceiling; the previous square-root claim was withdrawn.
- WHOOP documented relevant 2026 muscular-load, HR-processing and activity-detection updates. Fitbit's March 2026 sleep-staging announcement was for Public Preview users. Account-level rollout, historical versions and Preview enrolment remain unknown. Details and sources are in the article.

## Reproduce the revision from existing local data

No live DB access is required:

```bash
cd /opt/article-fitbit-vs-whoop
.venv/bin/python analysis/strain_trimp_audit.py
.venv/bin/python analysis/expanded_metrics.py
.venv/bin/python analysis/sleep_reaudit/extract.py
.venv/bin/python analysis/sleep_reaudit/compare.py
.venv/bin/python analysis/activity_reaudit/run_activity_reaudit.py
.venv/bin/python analysis/make_all_figures.py
.venv/bin/python analysis/make_figures_trimp.py
.venv/bin/python analysis/verify_revision.py
```

Citation checks (Hermes source-ledger utility):

```bash
S=/root/.hermes/skills/research/grounded-citations/scripts/sources.py
python "$S" --ledger research/citations.json verify draft.md
python "$S" --ledger research/citations.json verify GLOSSARY.md
```

The audit writes `analysis/results_trimp_audit.json`, including both cohorts, all −2…+2-day lags, matched-support comparisons, missingness, consistency flags and input hashes. It contains **no inferential p-values**. The figure generator ignores PostgreSQL row-count footers rather than counting them as observations.

## Files

- `draft.md`: English revised article with cited algorithm timeline and nine figures.
- `GLOSSARY.md`: English definitions, including TRIMP, internal load and calibration.
- `analysis/strain_trimp_audit.py`: reproducible local-data audit.
- `analysis/expanded_metrics.py`: complete metric audit for sleep latency, awakenings, awake time, pulse/HRV/SpO₂, Recovery, and Strain versus every available activity summary.
- `analysis/results_expanded_metrics.json`: machine-readable output of the expanded audit.
- `analysis/sleep_reaudit/`: fresh source-separated `sleep_sessions` extraction, latency/awakenings provenance audit, and P1/P2/P2_MAY paired results.
- `analysis/activity_reaudit/`: fresh source-specific activity, intraday pulse, WHOOP Strain, workout and metric inventory audit, including figures.
- `analysis/current_optihealth_insights_2026-10-12.json`: read-only snapshot of current production WHOOP-related cards and the three article-period cross-domain episodes.
- `analysis/current_whoop_reaudit_2026-10-15.json`: latest WHOOP datatype inventory, engine associations/curves, and May hidden-Fitbit correlations.
- `analysis/results_engine_source_isolation_2026-10-17.json`: read-only source-isolated replays of the deployed engine for Fitbit/Google Health and WHOOP.
- `analysis/results_sleep_predictive_matrix.json`: deep-sleep associations against both Fitbit and WHOOP next-day resting HR outcomes.
- `data/readiness_fitbit.csv`: full Fitbit Readiness export (317 rows) used by the article.
- `data/readiness_fitbit_components.csv`: earlier component-level Fitbit export retained for provenance.
- `data/readiness_recovery_paired.csv`: same-day Fitbit Readiness / WHOOP Recovery pairs extracted from the database.
- `data/whoop_optihealth_wide.csv`: WHOOP Recovery joined to the same OptiHealth daily series.
- `analysis/readiness_reaudit/compare.py`: reproducible paired comparison and moving-block bootstrap.
- `analysis/readiness_reaudit/figure.py`: paired Readiness / Recovery figure generator.
- `analysis/readiness_reaudit/optihealth.py`: read-only cross-check against the latest published OptiHealth daily series.
- `analysis/readiness_reaudit/results.json`: machine-readable Readiness / Recovery results.
- `analysis/readiness_reaudit/optihealth_results.json`: machine-readable OptiHealth cross-check.
- `analysis/readiness_reaudit/optihealth_run_metadata.json`: published-run provenance and series coverage.
- `analysis/readiness_reaudit/engine_readiness_probe.json`: current worker proof that the engine loads and emits Fitbit Readiness cards.
- `analysis/readiness_reaudit/hypothesis_scan.py`: serial-aware, season-adjusted Readiness hypothesis scan with BH correction.
- `analysis/readiness_reaudit/hypothesis_scan.json`: 16-hypothesis scan results.
- `analysis/readiness_reaudit/report.md`: paired comparison report and interpretation boundary.
- `figures/fig10_readiness_recovery.png`: Readiness / Recovery scatter and paired level-offset figure.
- `analysis/results_trimp_audit.json`: audit results, per-comparison sample sizes and limitations.
- `analysis/make_all_figures.py`: the original eight figures, with corrected interpretive captions.
- `analysis/make_figures_trimp.py`: calendar-lag sensitivity figure.
- `analysis/verify_revision.py`: independent checks of quoted numeric values, article links and language.
- `research/citations.json`: source ledger.
- `research/schyvens-full.md`: paper text recovered through Europe PMC after the publisher extraction was incomplete; study tables remain accessible through the cited XML endpoint.
- `research/trimp-review.md`: retrieved TRIMP review.
- `research/revision-notes.md`: corrections and unresolved issues.
- `data/*.csv`, `analysis/results*.json`, older analysis scripts: original inputs and analysis outputs retained.

## Original analysis provenance

The pre-existing project extracted data using read-only SELECTs from OptiHealth. Older scripts import statistical helpers from `/opt/optihealth_analysis/src`. The original phases cover paired agreement, exploratory associations, workout/ECG comparisons and descriptive comparisons with the Schyvens laboratory study. **This revision did not re-extract data, modify OptiHealth or alter the database.**

`analysis/results_strain.json` is the older **74-day** analysis; it is not the source of the revised **72-day** table. Use `results_trimp_audit.json` to reproduce that table. Earlier JSON interpretive strings and superseded README claims are historical artefacts, not the revised article's conclusions.

## Remaining requirements for a genuine TRIMP validation

1. Original physiological-cycle IDs and start/end timestamps, time zones and final score states.
2. Workout timestamps and completeness, not just a daily maximum/sum.
3. Timestamped HR with sampling intervals, coverage, and source provenance; historical HRmax/RHR calibration or a specified fixed reference.
4. Muscular-load activity classification and Strength Trainer usage.
5. Fitbit Public Preview participation and historical app/firmware/model records, if available.
6. A reference HR instrument for external validation; WHOOP's own HR would only establish internal consistency.

No selected lag has been applied to the raw data, no algorithm-change effect has been causally estimated, and no publication or deployment was performed.
