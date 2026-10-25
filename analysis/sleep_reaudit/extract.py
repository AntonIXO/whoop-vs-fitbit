#!/usr/bin/env python3
"""Fresh, scoped, read-only extraction. No credentials, sync_state, or other users."""
import subprocess,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent
USER='9e73d06e-1006-4266-bde7-85659f5de69d'
def query(sql):
    p=subprocess.run(['docker','exec','-e','PGOPTIONS=-c default_transaction_read_only=on -c statement_timeout=60000','supa-oriole-db','psql','-X','-qAt','-v','ON_ERROR_STOP=1','-U','postgres','-d','postgres','-c',sql],check=True,text=True,capture_output=True)
    return json.loads(p.stdout)
def main():
    sources=query(f"SELECT coalesce(json_agg(t),'[]') FROM (SELECT id,source_identifier,source_name FROM metric_sources WHERE user_id='{USER}' AND (source_identifier LIKE 'whoop:%' OR source_identifier LIKE 'google_health:%')) t")
    assert any(s['id']==35 and s['source_identifier'].startswith('google_health:') for s in sources)
    ids=','.join(str(s['id']) for s in sources)
    sql=f"""SELECT coalesce(json_agg(t ORDER BY start_ts,source_id),'[]') FROM (
      SELECT id,source_id,start_ts,end_ts,day,is_nap,stages,stage_dur_s,
      minutes_light,minutes_deep,minutes_rem,minutes_awake,time_in_bed_min,
      efficiency_pct,latency_min,awakenings,provider_resource_id,deep_percentage
      FROM sleep_sessions WHERE user_id='{USER}' AND source_id IN ({ids})
      AND ((day BETWEEN '2025-10-07' AND '2025-12-25') OR (day BETWEEN '2026-04-21' AND '2026-05-29'))
    ) t"""
    rows=query(sql)
    (ROOT/'extraction.sql').write_text('-- PGOPTIONS default_transaction_read_only=on; user-scoped; one-day matching boundary buffer\n'+sql+';\n')
    (ROOT/'sessions.json').write_text(json.dumps(rows,indent=2)+'\n')
    (ROOT/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')
    manifest={'extracted_at_utc':datetime.now(timezone.utc).isoformat(),'user_id':USER,'row_count':len(rows),'read_only':True,'sessions_sha256':hashlib.sha256((ROOT/'sessions.json').read_bytes()).hexdigest()}
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest))
if __name__=='__main__': main()
