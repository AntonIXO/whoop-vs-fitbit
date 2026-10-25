# Fresh source-separated sleep comparison (Anton)

## Scope and provenance

This is a fresh read-only extraction from `sleep_sessions`, restricted to Anton (`9e73d06e-1006-4266-bde7-85659f5de69d`). Fitbit is the Google Health/Fitbit source `id=35`; the autumn WHOOP account is source `id=2754` (`whoop:31695515`), and the active May account is source `id=2757` (`whoop:36797758`). The two WHOOP identities are analysed as separate regimes and are never pooled. The extraction includes a one-day boundary buffer and writes the exact selected rows to `sessions.json`.

`extract.py` sets PostgreSQL `default_transaction_read_only=on` and uses no writes. `compare.py` keeps Fitbit and WHOOP separate until same-night pairing. Pairing uses main sleep only (`is_nap=false`) and nearest start timestamps within six hours; it does not call a timestamp mismatch a physiological effect.

## Article-ready findings

- **P1 (2025-10-08–2025-12-24)** and **P2 (2026-04-22–2026-05-28)** are reported separately in `results.json`; use the exact `paired_n` and metric-specific `n` there rather than treating every metric as having the same sample size.
- **P2_MAY (2026-05-01–2026-05-28)** explicitly analyses the active WHOOP source `2757`: 17 main-sleep sessions and one nap, with 17 source-35 Fitbit/Google Health main-sleep matches. The old P2/source-2754 result remains zero because that is a different WHOOP account identity.
- The comparison distinguishes **onset clock time** (`start_ts`, an instant that can be rendered in a stated timezone) from **sleep latency** (`latency_min`, minutes to fall asleep). A later clock-time onset is not evidence of longer latency, and latency cannot be inferred from the clock time alone.
- For each period, paired output includes mean Fitbit and WHOOP values, paired bias (Fitbit − WHOOP), MAE, and median absolute error for awake minutes, efficiency, light/deep/REM minutes, latency, awakenings, and time in bed. Start/end timestamps and nap counts are retained separately. May stage metrics use only the four matched nights where Fitbit's stage timeline contains recognised `light/deep/REM` stages; the other Fitbit rows contain `unknown`/`awake` epochs and stored zero stage totals, which are treated as unavailable rather than measured zero.
- **WHOOP stages are provider totals, not a true stage timeline**; Fitbit/Health Connect may carry a stage timeline. Thus stage totals are comparable descriptively, but stage ordering/hypnogram agreement is not claimed.
- **Nulls remain nulls.** Ingestion code shows WHOOP's session mapper does not populate `latency_min` or `awakenings`; it does populate awake/stage totals and efficiency. Therefore zero counts for those WHOOP fields are an ingestion/provenance absence, not measured zero latency/zero awakenings. Do not report WHOOP latency or awakenings as available in this run. Fitbit latency is derived from the leading awake/out-of-bed timeline when a positive provider value is absent; derived zero is intentionally null when recording starts after onset.
- Uncertainty is descriptive and paired; nightly rows are serially dependent, so no IID p-values or claims of interchangeable instruments are made.

### May 2026 source-specific paired cohort

The raw table contains **17 WHOOP main-sleep sessions plus one nap** for 1–28 May 2026 under active source `2757` (`whoop:36797758`). The canonical view exposes the Fitbit/Google Health row for the 17 overlapping main sleeps, but the source-specific extraction keeps both rows. All 17 WHOOP main sleeps pair to source-35 rows by matching start time within six hours; the nap is excluded from the paired-night analysis.

The following is the same descriptive paired analysis as P1, expressed as **WHOOP − Fitbit**. `n` is metric-specific:

| Metric | n | Fitbit mean | WHOOP mean | WHOOP − Fitbit | MAE |
|---|---:|---:|---:|---:|---:|
| Awake minutes | 17 | 29.4 | 33.4 | **+4.1 min** | 4.1 min |
| Sleep efficiency | 17 | 92.4% | 92.4% | **+0.1 pp** | 1.4 pp |
| Light sleep | 4 | 324.5 min | 276.0 min | **−48.5 min** | 48.5 min |
| Deep sleep | 4 | 93.0 min | 132.3 min | **+39.3 min** | 39.3 min |
| REM sleep | 4 | 101.5 min | 94.0 min | **−7.5 min** | 11.0 min |
| Time in bed | 17 | 458.4 min | 457.8 min | **−0.5 min** | 1.5 min |

The apparent stage gap is not a 17-night result: **13 of the 17 Fitbit rows have only `unknown`/`awake` epochs and stored zero stage totals**, so their Fitbit stage values are missing semantically. The stage comparison therefore uses only four paired nights. WHOOP latency and awakenings remain unavailable in the stored session mapper; neither is interpreted as zero. This May cohort is a source-specific descriptive analysis, not a replication of the autumn WHOOP account `2754`.

Run:

```bash
cd /opt/article-fitbit-vs-whoop/analysis/sleep_reaudit
/opt/article-fitbit-vs-whoop/.venv/bin/python extract.py
/opt/article-fitbit-vs-whoop/.venv/bin/python compare.py
/opt/article-fitbit-vs-whoop/.venv/bin/python fragmentation.py
```

## Fitbit awake-stage fragmentation

Across 71 P1 Fitbit main sleeps, the provider awakening count and timeline awake-run count both average **3.37/night**. The timeline contains **104 interior awake runs** (**1.46/night**), with a median duration of **10.5 min** and range **5–64.5 min**. Six ≤2-minute awake runs occur at sleep boundaries; no interior awake run is ≤2 minutes. WHOOP stores stage totals rather than an awake-run timeline, so an equivalent WHOOP episode count is unavailable. See `fragmentation.json`.
