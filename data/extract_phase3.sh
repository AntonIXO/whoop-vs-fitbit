#!/usr/bin/env bash
# Phase 3: ECG as an INDEPENDENT criterion instrument + workout-load context.
set -euo pipefail
DB=supa-oriole-db
OUT="$(dirname "$0")"
Q() { docker exec "$DB" psql -U postgres -d postgres -qAF',' -c "$1"; }

# ECG spot readings paired with same-day device numbers.
Q "
WITH dm AS (SELECT m.day, d.metric_name, m.source_id, m.value
            FROM metric_daily m JOIN metric_definitions d ON d.id=m.metric_id)
SELECT DISTINCT ON (e.recorded_at) e.day, e.recorded_at,
       e.derived_bpm, e.rmssd_ms, e.sdnn_ms, e.median_rr_ms,
       e.rr_artifact_fraction, e.beat_count, e.provider_bpm,
       (SELECT value FROM dm WHERE dm.day=e.day AND metric_name='hr_resting' AND source_id=35)   AS f_rhr,
       (SELECT value FROM dm WHERE dm.day=e.day AND metric_name='hr_resting' AND source_id=2754) AS w_rhr,
       (SELECT value FROM dm WHERE dm.day=e.day AND metric_name='whoop_recovery_score' AND source_id=2754) AS w_recovery,
       (SELECT value FROM dm WHERE dm.day=e.day AND metric_name='whoop_strain_daily' AND source_id=2754) AS w_strain
FROM ecg_recordings e
WHERE e.recorded_at BETWEEN '2025-10-08' AND '2025-12-26'
  AND e.quality_status='analyzable'
ORDER BY e.recorded_at, e.source_id;" > "$OUT/ecg_paired.csv"

# Nightly Fitbit HRV mean per day (series) to pair against ECG spot RMSSD
Q "
SELECT ms.hour_bucket::date AS day, avg(v) AS hrv_daily, count(*) AS n
FROM metric_samples ms
JOIN metric_definitions d ON d.id=ms.metric_id AND d.metric_name='hrv_rmssd'
CROSS JOIN LATERAL unnest(ms.vals) AS v
WHERE ms.source_id=35 AND ms.hour_bucket BETWEEN '2025-10-08' AND '2025-12-26'
GROUP BY 1 ORDER BY 1;" > "$OUT/hrv_daily.csv"

# Workout load in the window (both devices' view of the same sessions)
Q "
SELECT w.start_ts::date AS day, s.source_identifier, count(*) n,
       sum(w.kcal) kcal, sum(w.duration_s)/60.0 min, avg(w.avg_hr) avg_hr, sum(w.steps) steps, avg(w.strain) strain
FROM workouts w JOIN metric_sources s ON s.id=w.source_id
WHERE w.start_ts BETWEEN '2025-10-08' AND '2025-12-26'
GROUP BY 1,2 ORDER BY 1,2;" > "$OUT/workouts_by_source.csv"

wc -l "$OUT/ecg_paired.csv" "$OUT/hrv_daily.csv" "$OUT/workouts_by_source.csv"
