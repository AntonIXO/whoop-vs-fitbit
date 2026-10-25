#!/opt/article-fitbit-vs-whoop/.venv/bin/python
import csv, json, subprocess, math
from pathlib import Path
from datetime import datetime, date, timedelta, timezone
import numpy as np
from scipy.stats import spearmanr, pearsonr
import matplotlib.pyplot as plt

OUT=Path('/opt/article-fitbit-vs-whoop/analysis/activity_reaudit'); OUT.mkdir(parents=True,exist_ok=True)
UID='9e73d06e-1006-4266-bde7-85659f5de69d'; DB=['docker','exec','supa-oriole-db','psql','-U','postgres','-d','postgres','-X','-A','-F','\t','-P','footer=off']
PERIODS={'P1':('2025-10-08','2025-12-24'),'P2':('2026-04-22','2026-05-28')}

def sql(q):
 r=subprocess.run(DB+['-c','SET default_transaction_read_only=on; '+q],capture_output=True,text=True,check=True)
 lines=[x for x in r.stdout.splitlines() if x and not x.startswith('SET')]
 return list(csv.DictReader(lines,delimiter='\t')) if lines else []
def f(x):
 try:return float(x) if x not in ('',None,'\\N') else None
 except:return None
def q(x): return "'"+x.replace("'","''")+"'"
# Broad inventory, all relevant source IDs and dates.
sources=sql(f"SELECT id,source_identifier,source_name,is_active,sync_state::text FROM metric_sources WHERE user_id={q(UID)} ORDER BY id")
all_defs=sql('SELECT id,metric_name,kind,category,default_unit,beautiful_name,is_hidden FROM metric_definitions ORDER BY id')
defs={int(x['id']):x for x in all_defs}
reports={}; inventory={'user_id':UID,'sources':sources,'metric_definitions':all_defs,'periods':{}}
for pn,(a,b) in PERIODS.items():
 d0=date.fromisoformat(a); d1=date.fromisoformat(b); lo=(d0-timedelta(days=2)).isoformat(); hi=(d1+timedelta(days=2)).isoformat()
 daily=sql(f"SELECT m.day,m.source_id,m.metric_id,m.value,m.is_derived FROM metric_daily m WHERE m.user_id={q(UID)} AND m.day BETWEEN {q(a)} AND {q(b)} ORDER BY m.day,m.source_id,m.metric_id")
 daily=[dict(x,metric_name=defs.get(int(x['metric_id']),{}).get('metric_name')) for x in daily]
 samples=sql(f"SELECT s.source_id,s.metric_id,s.hour_bucket,s.offsets_s,s.vals,s.flags FROM metric_samples s WHERE s.user_id={q(UID)} AND s.hour_bucket >= {q(lo+' 00:00:00+00')}::timestamptz AND s.hour_bucket < {q(hi+' 00:00:00+00')}::timestamptz ORDER BY s.hour_bucket,s.source_id,s.metric_id")
 # decode PostgreSQL arrays simply
 def arr(s):
  if not s or s=='{}':return []
  return [x.strip(' "') for x in s[1:-1].split(',')]
 sample_rows=[]
 for x in samples:
  off=arr(x['offsets_s']); vals=arr(x['vals']); flags=arr(x['flags'])
  for i,v in enumerate(vals):
   try:
    ts=datetime.fromisoformat(x['hour_bucket'].replace(' ','T'))+timedelta(seconds=float(off[i]))
    sample_rows.append({'source_id':int(x['source_id']),'metric_id':int(x['metric_id']),'metric_name':defs.get(int(x['metric_id']),{}).get('metric_name'),'ts':ts.isoformat(),'value':f(v),'flag':flags[i] if i<len(flags) else None})
   except:pass
 workouts=sql(f"SELECT id,source_id,start_ts,duration_s,type,distance_m,kcal,steps,avg_hr,max_hr,strain,provider_resource_id FROM workouts WHERE user_id={q(UID)} AND start_ts >= {q(a+' 00:00:00+00')}::timestamptz AND start_ts < ({q(b)}::date + interval '1 day') ORDER BY start_ts")
 sleeps=sql(f"SELECT source_id,start_ts,end_ts,day,is_nap FROM sleep_sessions_canonical WHERE user_id={q(UID)} AND start_ts < ({q(b)}::date + interval '1 day') AND end_ts >= {q(a)}::date")
 whoop_daily=[x for x in daily if x['metric_name'] in ('whoop_strain_daily','whoop_recovery_score') or x['source_id'] in ('2754','2757')]
 # source/metric coverage
 cov={}
 for x in daily:
  k=f"{x['source_id']}:{x['metric_name']}"; cov.setdefault(k,{'rows':0,'days':[]}); cov[k]['rows']+=1; cov[k]['days'].append(x['day'])
 for v in cov.values():v['days']=sorted(set(v['days']));v['n_days']=len(v['days'])
 sample_cov={}
 for x in sample_rows:
  k=f"{x['source_id']}:{x['metric_name']}"; sample_cov.setdefault(k,{'points':0,'hours':set(),'days':set()}); sample_cov[k]['points']+=1; sample_cov[k]['hours'].add(x['ts'][:13]); sample_cov[k]['days'].add(x['ts'][:10])
 for v in sample_cov.values():v['hours']=len(v['hours']);v['days']=len(v['days'])
 # daily comparison on common calendar days, no imputation
 by={(x['day'],x['source_id'],x['metric_name']):f(x['value']) for x in daily}
 comps={}
 def compare(name,fit_sources,whoop_sources):
  for fs in fit_sources:
   for ws in whoop_sources:
    pairs=[]
    for day in sorted({x['day'] for x in daily}):
     xv=by.get((day,str(fs),name)); y=by.get((day,str(ws),'whoop_strain_daily'))
     if xv is not None and y is not None:pairs.append((xv,y,day))
    if len(pairs)>=3:
     x=np.array([p[0] for p in pairs]);y=np.array([p[1] for p in pairs]); sr=spearmanr(x,y); pr=pearsonr(x,y)
     comps[f'{name}:fit{fs}-whoop{ws}']={'n':len(pairs),'days':[p[2] for p in pairs],'spearman_rho':float(sr.statistic),'spearman_p':float(sr.pvalue),'pearson_r':float(pr.statistic),'pearson_p':float(pr.pvalue)}
  return comps
 compare('activity_steps',[35,49,744],[2754,2757]); compare('calories_burned_active',[35,744],[2754,2757]); compare('activity_intensity_moderate',[35],[2754,2757]); compare('activity_intensity_vigorous',[35],[2754,2757]); compare('calories_burned_total',[35],[2754,2757])
 # Fitbit valid HR-load proxy: sum HR minutes only if intraday HR exists; never invent from daily resting HR.
 hr=[x for x in sample_rows if x['metric_name'] in ('hr','heart_rate','heart_rate_bpm','hr_bpm') and x['value'] is not None]
 intraday_sources=sorted(set(x['source_id'] for x in hr)); hr_by_day={}
 for x in hr:hr_by_day.setdefault(x['ts'][:10],[]).append(x['value'])
 # Hour-of-day summaries are computed in UTC because stored timestamps are timestamptz;
 # they are descriptive and never presented as local-civil phase without a timezone map.
 hod={}; sleep_excluded={}
 for x in hr:
  dt=datetime.fromisoformat(x['ts']); h=dt.hour; sid=str(x['source_id']); hod.setdefault(sid,{}).setdefault(str(h),[]).append(x['value'])
  in_sleep=False
  for sl in sleeps:
   try:
    ss=datetime.fromisoformat(sl['start_ts'].replace(' ','T')); ee=datetime.fromisoformat(sl['end_ts'].replace(' ','T'))
    if ss <= dt <= ee: in_sleep=True; break
   except: pass
  if not in_sleep:sleep_excluded.setdefault(sid,{}).setdefault(str(h),[]).append(x['value'])
 def hod_summary(z): return {sid:{h:{'n':len(v),'mean':float(np.mean(v)),'median':float(np.median(v))} for h,v in hh.items()} for sid,hh in z.items()}
 whoop_hr_points=sum(len(v) for sid,hh in hod.items() if sid in ('2754','2757','744','771') for v in hh.values())
 reports[pn]={'window':{'start':a,'end':b,'calendar_days':(d1-d0).days+1},'daily_metric_inventory':cov,'sample_metric_inventory':sample_cov,'whoop_daily_rows':whoop_daily,'workouts':workouts,'sleep_intervals':sleeps,'intraday_hr':{'rows':len(hr),'sources':intraday_sources,'days':len(hr_by_day),'points_by_day':{k:len(v) for k,v in hr_by_day.items()},'whoop_hr_points_sources_2754_2757':sum(sum(len(v) for v in hh.values()) for sid,hh in hod.items() if sid in ('2754','2757')),'hour_of_day_utc':hod_summary(hod),'hour_of_day_utc_sleep_excluded':hod_summary(sleep_excluded)},'comparisons_vs_whoop_strain':comps,'source_ids_present':sorted(set(int(x['source_id']) for x in daily+sample_rows))}
 inventory['periods'][pn]={'daily_rows':len(daily),'sample_bucket_rows':len(samples),'decoded_sample_points':len(sample_rows),'workout_rows':len(workouts),'sleep_rows':len(sleeps),'daily_metric_inventory':cov,'sample_metric_inventory':sample_cov}
 # Figure: available daily WHOOP strain against Fitbit measures by calendar day
 fig,axs=plt.subplots(2,1,figsize=(12,7),sharex=True)
 for sid,color,label in [(2754,'#202020','WHOOP 2754'),(2757,'#777777','WHOOP 2757')]:
  z=[(date.fromisoformat(day),v) for (day,s,m),v in by.items() if s==str(sid) and m=='whoop_strain_daily' and v is not None]; z.sort()
  if z:axs[0].plot([x[0] for x in z],[x[1] for x in z],'.-',color=color,label=label)
 for sid,color,label in [(35,'#e45756','Fitbit steps'),(744,'#4c78a8','HC steps')]:
  z=[(date.fromisoformat(day),v) for (day,s,m),v in by.items() if s==str(sid) and m=='activity_steps' and v is not None];z.sort()
  if z:axs[1].plot([x[0] for x in z],[x[1] for x in z],'.-',color=color,label=label)
 axs[0].set_ylabel('WHOOP strain');axs[1].set_ylabel('Steps');axs[1].set_xlabel('Calendar day')
 for ax in axs:ax.grid(alpha=.2);ax.legend();
 fig.suptitle(f'{pn}: available daily load/activity (missing remains missing)');fig.tight_layout();fig.savefig(OUT/f'{pn.lower()}_daily_load_activity.png',dpi=160);plt.close(fig)
reports['inventory']=inventory
(OUT/'results.json').write_text(json.dumps(reports,indent=2,default=str))
# Article-ready report, generated from exact result object
lines=['# Fitbit vs WHOOP activity / pulse / strain audit (Anton)','',f'- User restriction: `{UID}` only.','- Fresh read-only extraction from PostgreSQL; no production writes.','- Missing values were not converted to zero. Calendar support was retained explicitly.','']
for pn,r in reports.items():
 if pn=='inventory':continue
 lines += [f'## {pn}: {r["window"]["start"]} to {r["window"]["end"]}',f'- Calendar span: {r["window"]["calendar_days"]} days; daily rows: {len(r["whoop_daily_rows"])} WHOOP-source rows in the filtered view; workouts: {len(r["workouts"])}; canonical sleep intervals: {len(r["sleep_intervals"])}.','', '### Complete metric inventory']
 for k,v in r['daily_metric_inventory'].items(): lines.append(f'- `{k}`: {v["n_days"]} observed days / {v["rows"]} rows; observed days {v["days"][0] if v["days"] else "none"} to {v["days"][-1] if v["days"] else "none"}.')
 lines += ['', '### Intraday samples / pulse coverage']
 if r['sample_metric_inventory']:
  for k,v in r['sample_metric_inventory'].items():lines.append(f'- `{k}`: {v["points"]} decoded points, {v["hours"]} UTC hour buckets, {v["days"]} days.')
 else:lines.append('- No metric_samples rows in the queried window (including ±2-day boundary).')
 lines.append(f'- Direct intraday HR points: {r["intraday_hr"]["rows"]}; sources: {r["intraday_hr"]["sources"]}; days: {r["intraday_hr"]["days"]}. WHOOP source 2754/2757 HR points: {r["intraday_hr"]["whoop_hr_points_sources_2754_2757"]}.')
 lines.append('- Hour-of-day HR summaries (UTC, with and without overlap with canonical sleep intervals) are in `results.json`; a full aligned intraday WHOOP-vs-Fitbit HR validation is not claimed when WHOOP HR point count is zero.')
 lines += ['', '### Strain against Fitbit metrics (all tested compatible daily measures)']
 if r['comparisons_vs_whoop_strain']:
  for k,v in r['comparisons_vs_whoop_strain'].items():lines.append(f'- `{k}`: n={v["n"]}, common days {v["days"][0]}..{v["days"][-1]}, Spearman rho={v["spearman_rho"]:.3f} (p={v["spearman_p"]:.3g}), Pearson r={v["pearson_r"]:.3f} (p={v["pearson_p"]:.3g}).')
 else:lines.append('- No pair met the minimum of 3 observed common calendar days; no correlation was fabricated.')
 lines += ['', '### Interpretation limits','- WHOOP day strain is attributed by the importer to the completed cycle end; workouts use their actual start timestamp. These are different dating constructs and are not silently treated as interchangeable.','- No valid HR-load aggregate is reported without a timestamped HR series and defensible time weighting. Daily resting HR is not a substitute for HR load.','- Correlations are descriptive within one person and serially dependent; p-values are not independent-observation evidence.','']
(OUT/'report.md').write_text('\n'.join(lines))
print(json.dumps({'out':str(OUT),'periods':list(PERIODS),'results':str(OUT/'results.json')}))
