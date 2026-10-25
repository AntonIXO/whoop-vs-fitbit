#!/usr/bin/env bash
# Extract PARED Whoop-vs-Fitbit series from the live DB. Read-only SELECTs.
set -euo pipefail
DB=supa-oriole-db
OUT="$(dirname "$0")"
Q() { docker exec "$DB" psql -U postgres -d postgres -qAF',' -c "$1"; }

# P1 = whoop:31695515 (2025-10..12), P2 = whoop:36797758 (2026-04..05)
# fitbit canonical = google_health source 35 (+51 dup era); HC fitbit 49 for May steps

# 1. matched sleep nights (both sources, same local day)
Q "SELECT CASE WHEN w.source_id=2754 THEN 'P1' ELSE 'P2' END period, w.day,
      f.time_in_bed_min f_tib, w.time_in_bed_min w_tib,
      f.minutes_light+f.minutes_deep+f.minutes_rem f_tst, w.minutes_light+w.minutes_deep+w.minutes_rem w_tst,
      f.minutes_deep f_deep, w.minutes_deep w_deep,
      f.minutes_rem f_rem, w.minutes_rem w_rem,
      extract(epoch from (w.start_ts-f.start_ts))/60 onset_diff_min
   FROM sleep_sessions w JOIN sleep_sessions f ON w.day=f.day AND f.source_id=35 AND f.is_nap=false
   WHERE w.source_id IN (2754,2757) AND w.is_nap=false ORDER BY 1,2;" > "$OUT/sleep_paired.csv"

# 1b. staged-only subset (fitbit reported stages)
Q "SELECT CASE WHEN w.source_id=2754 THEN 'P1' ELSE 'P2' END period, w.day,
      f.time_in_bed_min f_tib, w.time_in_bed_min w_tib,
      f.minutes_light+f.minutes_deep+f.minutes_rem f_tst, w.minutes_light+w.minutes_deep+w.minutes_rem w_tst,
      f.minutes_deep f_deep, w.minutes_deep w_deep,
      f.minutes_rem f_rem, w.minutes_rem w_rem
   FROM sleep_sessions w JOIN sleep_sessions f ON w.day=f.day AND f.source_id=35 AND f.is_nap=false
   WHERE w.source_id IN (2754,2757) AND w.is_nap=false
     AND f.minutes_deep+f.minutes_rem>0 ORDER BY 1,2;" > "$OUT/sleep_paired_staged.csv"

# 2. matched resting HR
Q "SELECT CASE WHEN w.source_id=2754 THEN 'P1' ELSE 'P2' END period, w.day, f.value f_rhr, w.value w_rhr
   FROM metric_daily w JOIN metric_daily f ON w.day=f.day AND f.metric_id=w.metric_id
   JOIN metric_definitions d ON d.id=f.metric_id
   WHERE d.metric_name='hr_resting' AND w.source_id IN (2754,2757) AND f.source_id=35 ORDER BY 1,2;" > "$OUT/rhr_paired.csv"

# 3. matched steps (whoop HC app vs fitbit HC app — same transport)
Q "SELECT 'P2' period, w.day, f.value f_steps, w.value w_steps
   FROM metric_daily w JOIN metric_daily f ON w.day=f.day AND f.metric_id=w.metric_id
   JOIN metric_definitions d ON d.id=f.metric_id
   WHERE d.metric_name='activity_steps' AND w.source_id=744 AND f.source_id=49 ORDER BY 2;" > "$OUT/steps_paired.csv"

# 4. strain vs total calories (P1)
Q "SELECT w.day, w.value strain, f.value kcal
   FROM metric_daily w JOIN metric_daily f ON w.day=f.day
   JOIN metric_definitions dw ON dw.id=w.metric_id
   JOIN metric_definitions df ON df.id=f.metric_id
   WHERE dw.metric_name='whoop_strain_daily' AND w.source_id=2754
     AND df.metric_name='calories_burned_total' AND f.source_id=35 ORDER BY 1;" > "$OUT/strain_kcal.csv"

# 5. recovery vs resting HR (P1)
Q "SELECT w.day, w.value recovery, f.value rhr
   FROM metric_daily w JOIN metric_daily f ON w.day=f.day
   JOIN metric_definitions dw ON dw.id=w.metric_id
   JOIN metric_definitions df ON df.id=f.metric_id
   WHERE dw.metric_name='whoop_recovery_score' AND w.source_id=2754
     AND df.metric_name='hr_resting' AND f.source_id=35 ORDER BY 1;" > "$OUT/recovery_rhr.csv"

wc -l "$OUT"/*.csv
