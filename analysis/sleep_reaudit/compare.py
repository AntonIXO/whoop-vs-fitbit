#!/usr/bin/env python3
import json,math
from pathlib import Path
from datetime import datetime,timedelta,timezone
ROOT=Path(__file__).resolve().parent
P={
 'P1': {'lo':datetime(2025,10,8),'hi':datetime(2025,12,24),'whoop_source':2754},
 'P2': {'lo':datetime(2026,4,22),'hi':datetime(2026,5,28),'whoop_source':2754},
 # The active account's May nights were hidden by canonical source arbitration.
 'P2_MAY': {'lo':datetime(2026,5,1),'hi':datetime(2026,5,28),'whoop_source':2757},
}
STAGE_METRICS={'minutes_light','minutes_deep','minutes_rem'}
KNOWN_STAGES={'awake','light','deep','rem'}
def dt(s): return datetime.fromisoformat(s.replace('Z','+00:00')).replace(tzinfo=None)
def mean(a): return sum(a)/len(a) if a else None
def med(a): return sorted(a)[len(a)//2] if a else None
def stage_totals_available(r, source_id):
 # Fitbit/Google Health rows with only unknown+awake epochs carry zero stage totals
 # as a storage artefact; do not treat those zeros as measured stage values.
 if source_id != 35:
  return all(r[k] is not None for k in STAGE_METRICS)
 stages=r.get('stages') or []
 return bool(stages) and all(s in KNOWN_STAGES for s in stages) and all(r[k] is not None for k in STAGE_METRICS)
def metrics(a,b,fitbit_source,whoop_source):
 out={}
 for k in ['minutes_awake','efficiency_pct','minutes_light','minutes_deep','minutes_rem','latency_min','awakenings','time_in_bed_min']:
  pairs=[]
  for x,y in zip(a,b):
   if k in STAGE_METRICS and (not stage_totals_available(x,fitbit_source) or not stage_totals_available(y,whoop_source)):
    continue
   if x[k] is not None and y[k] is not None:
    pairs.append((x[k],y[k]))
  d=[x-y for x,y in pairs]
  out[k]={'n':len(pairs),'fitbit_mean':mean([x for x,y in pairs]),'whoop_mean':mean([y for x,y in pairs]),'bias_fitbit_minus_whoop':mean(d),'mae':mean([abs(v) for v in d]),'median_abs_error':med([abs(v) for v in d])}
 return out
def main():
 rows=json.loads((ROOT/'sessions.json').read_text()); sources={s['id']:s['source_name'] for s in json.loads((ROOT/'sources.json').read_text())}
 out={'method':{'matching':'same local wake-day (day), main sleep only (is_nap=false), nearest start within 6h; no source mixing','clock_time':'start_ts/end_ts are UTC instants; onset clock time is separate from latency_min','uncertainty':'descriptive paired bias/MAE; serial dependence retained by night; no iid p-values'},'periods':{}}
 for name,spec in P.items():
  lo,hi=spec['lo'],spec['hi']; whoop_source=spec['whoop_source']
  rr=[r for r in rows if lo<=dt(r['day'])<=hi]
  f=[r for r in rr if r['source_id']==35 and not r['is_nap']]; w=[r for r in rr if r['source_id']==whoop_source and not r['is_nap']]
  # The two WHOOP account identities are never pooled; P2_MAY is explicit.
  pairs=[]; used=set()
  for x in f:
   cand=[y for y in w if y['id'] not in used and abs((dt(x['start_ts'])-dt(y['start_ts'])).total_seconds())<=6*3600]
   if cand:
    y=min(cand,key=lambda z:abs((dt(x['start_ts'])-dt(z['start_ts'])).total_seconds()));used.add(y['id']);pairs.append((x,y))
  a,b=zip(*pairs) if pairs else ([],[])
  def availability(rs,source_id):
   return {k:{'rows':len(rs),'non_null':sum(r[k] is not None for r in rs),'null':sum(r[k] is None for r in rs)} for k in ['latency_min','awakenings','minutes_awake','efficiency_pct','minutes_light','minutes_deep','minutes_rem','time_in_bed_min']} | {'stage_totals_valid':sum(stage_totals_available(r,source_id) for r in rs)}
  out['periods'][name]={'fitbit_main_n':len(f),'whoop_main_n':len(w),'whoop_source_id':whoop_source,'paired_n':len(pairs),'fitbit_naps':sum(r['is_nap'] for r in rr if r['source_id']==35),'whoop_naps':sum(r['is_nap'] for r in rr if r['source_id']==whoop_source),'availability':{'fitbit':availability(f,35),'whoop':availability(w,whoop_source)},'metrics':metrics(a,b,35,whoop_source),'paired_nights':[{'fitbit_id':x['id'],'whoop_id':y['id'],'fitbit_start_ts':x['start_ts'],'whoop_start_ts':y['start_ts'],'fitbit_end_ts':x['end_ts'],'whoop_end_ts':y['end_ts']} for x,y in pairs]}
 (ROOT/'results.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'periods':{k:{q:v for q,v in z.items() if q!='metrics'} for k,z in out['periods'].items()}},indent=2))
if __name__=='__main__': main()
