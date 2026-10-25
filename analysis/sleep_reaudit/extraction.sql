-- PGOPTIONS default_transaction_read_only=on; user-scoped; one-day matching boundary buffer
SELECT coalesce(json_agg(t ORDER BY start_ts,source_id),'[]') FROM (
      SELECT id,source_id,start_ts,end_ts,day,is_nap,stages,stage_dur_s,
      minutes_light,minutes_deep,minutes_rem,minutes_awake,time_in_bed_min,
      efficiency_pct,latency_min,awakenings,provider_resource_id,deep_percentage
      FROM sleep_sessions WHERE user_id='9e73d06e-1006-4266-bde7-85659f5de69d' AND source_id IN (35,2754,2757)
      AND ((day BETWEEN '2025-10-07' AND '2025-12-25') OR (day BETWEEN '2026-04-21' AND '2026-05-29'))
    ) t;
