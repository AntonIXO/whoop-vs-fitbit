#!/usr/bin/env bash
# Phase 2: build a WIDE nightly frame for P1 (Oct-Dec 2025) joining both devices
# with independent next-day physiology. Read-only.
set -euo pipefail
DB=supa-oriole-db
OUT="$(dirname "$0")"
Q() { docker exec "$DB" psql -U postgres -d postgres -qAF',' -c "$1"; }

# Nightly frame: both devices' sleep + Fitbit-side night quality + next-day outcomes.
# hrv_rmssd and spo2 are SERIES metrics -> aggregate the sleep-window mean per day.
Q "
WITH fb AS (
  SELECT day, start_ts, end_ts,
         minutes_light+minutes_deep+minutes_rem AS tst,
         time_in_bed_min AS tib, minutes_deep AS deep, minutes_rem AS rem,
         minutes_light AS light, minutes_awake AS awake,
         efficiency_pct AS eff, latency_min AS latency, awakenings
  FROM sleep_sessions WHERE source_id=35 AND is_nap=false AND minutes_deep+minutes_rem>0
),
wh AS (
  SELECT day, start_ts, end_ts,
         minutes_light+minutes_deep+minutes_rem AS tst,
         time_in_bed_min AS tib, minutes_deep AS deep, minutes_rem AS rem,
         minutes_light AS light, minutes_awake AS awake, efficiency_pct AS eff
  FROM sleep_sessions WHERE source_id=2754 AND is_nap=false
),
-- nightly HRV: Fitbit rmssd samples falling inside the Fitbit sleep window
hrv AS (
  SELECT f.day, avg(v) AS hrv_night, count(*) AS hrv_n
  FROM fb f
  JOIN metric_samples ms ON ms.source_id=35 AND ms.hour_bucket >= date_trunc('hour', f.start_ts)
                        AND ms.hour_bucket <= f.end_ts
  JOIN metric_definitions d ON d.id=ms.metric_id AND d.metric_name='hrv_rmssd'
  CROSS JOIN LATERAL unnest(ms.vals) AS v
  GROUP BY 1
),
spo2 AS (
  SELECT f.day, avg(v) AS spo2_night, stddev_samp(v) AS spo2_sd
  FROM fb f
  JOIN metric_samples ms ON ms.source_id=35 AND ms.hour_bucket >= date_trunc('hour', f.start_ts)
                        AND ms.hour_bucket <= f.end_ts
  JOIN metric_definitions d ON d.id=ms.metric_id AND d.metric_name='blood_oxygen_spo2'
  CROSS JOIN LATERAL unnest(ms.vals) AS v
  GROUP BY 1
),
-- nightly mean HR inside the Fitbit sleep window (independent of both stagers)
hrn AS (
  SELECT f.day, avg(v) AS hr_night, min(v) AS hr_night_min
  FROM fb f
  JOIN metric_samples ms ON ms.source_id=35 AND ms.hour_bucket >= date_trunc('hour', f.start_ts)
                        AND ms.hour_bucket <= f.end_ts
  JOIN metric_definitions d ON d.id=ms.metric_id AND d.metric_name='hr'
  CROSS JOIN LATERAL unnest(ms.vals) AS v
  GROUP BY 1
),
dm AS (
  SELECT m.day, d.metric_name, m.source_id, m.value
  FROM metric_daily m JOIN metric_definitions d ON d.id=m.metric_id
)
SELECT fb.day,
  fb.tst  AS f_tst,  wh.tst  AS w_tst,
  fb.tib  AS f_tib,  wh.tib  AS w_tib,
  fb.deep AS f_deep, wh.deep AS w_deep,
  fb.rem  AS f_rem,  wh.rem  AS w_rem,
  fb.light AS f_light, wh.light AS w_light,
  fb.awake AS f_awake, wh.awake AS w_awake,
  fb.eff AS f_eff, wh.eff AS w_eff,
  fb.latency AS f_latency, fb.awakenings AS f_awakenings,
  extract(epoch from (wh.start_ts-fb.start_ts))/60 AS onset_diff,
  extract(epoch from (wh.end_ts-fb.end_ts))/60 AS offset_diff,
  extract(hour from fb.start_ts) + extract(minute from fb.start_ts)/60.0 AS bedtime_h,
  hrv.hrv_night, hrv.hrv_n, spo2.spo2_night, spo2.spo2_sd,
  hrn.hr_night, hrn.hr_night_min,
  (SELECT value FROM dm WHERE dm.day=fb.day AND metric_name='hr_resting' AND source_id=35) AS f_rhr,
  (SELECT value FROM dm WHERE dm.day=fb.day AND metric_name='hr_resting' AND source_id=2754) AS w_rhr,
  (SELECT value FROM dm WHERE dm.day=fb.day AND metric_name='whoop_recovery_score' AND source_id=2754) AS w_recovery,
  (SELECT value FROM dm WHERE dm.day=fb.day AND metric_name='whoop_strain_daily' AND source_id=2754) AS w_strain,
  (SELECT value FROM dm WHERE dm.day=fb.day AND metric_name='activity_steps' AND source_id=35) AS f_steps,
  (SELECT value FROM dm WHERE dm.day=fb.day AND metric_name='calories_burned_total' AND source_id=35) AS f_kcal,
  (SELECT value FROM dm WHERE dm.day=fb.day+1 AND metric_name='hr_resting' AND source_id=35) AS f_rhr_next,
  (SELECT value FROM dm WHERE dm.day=fb.day+1 AND metric_name='whoop_recovery_score' AND source_id=2754) AS w_recovery_next,
  (SELECT value FROM dm WHERE dm.day=fb.day+1 AND metric_name='whoop_strain_daily' AND source_id=2754) AS w_strain_next,
  (SELECT value FROM dm WHERE dm.day=fb.day+1 AND metric_name='activity_steps' AND source_id=35) AS f_steps_next
FROM fb JOIN wh ON fb.day=wh.day
LEFT JOIN hrv ON hrv.day=fb.day
LEFT JOIN spo2 ON spo2.day=fb.day
LEFT JOIN hrn ON hrn.day=fb.day
ORDER BY fb.day;" > "$OUT/nightly_wide.csv"

wc -l "$OUT/nightly_wide.csv"; head -1 "$OUT/nightly_wide.csv"
