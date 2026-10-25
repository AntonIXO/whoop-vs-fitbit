#!/usr/bin/env python3
"""Serial-aware hypothesis scan for Fitbit Readiness and OptiHealth signals."""
from __future__ import annotations
import csv, datetime as dt, json, math, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
sys.path.insert(0, "/opt/optihealth_analysis/src")
from analysis.serial import block_permutation_p, default_block_len

ROOT=Path(__file__).resolve().parents[2]
INPUT=ROOT/'data/readiness_optihealth_wide.csv'
OUTPUT=Path(__file__).resolve().parent/'hypothesis_scan.json'


def load():
 rows=[]
 with INPUT.open() as f:
  for r in csv.DictReader(f):
   x={'day':dt.date.fromisoformat(r['day']),'readiness':float(r['readiness'])}
   for k,v in r.items():
    if k in ('day','readiness'):continue
    x[k]=float(v) if v not in ('',None) else math.nan
   rows.append(x)
 return rows

def design(days, controls=()):
 cols=[[1.0] for _ in days]
 for d in days:
  phase=2*math.pi*((d-dt.date(2024,1,1)).days)/365.2425
  cols[len(cols)-len(days):] if False else None
 # construct row-wise to keep readable
 X=[]
 for d in days:
  phase=2*math.pi*((d-dt.date(2024,1,1)).days)/365.2425
  X.append([1.0,math.sin(phase),math.cos(phase)])
 return np.asarray(X,float)

def residual(y, days, controls=()):
 X=design(days)
 if controls:
  X=np.column_stack([X,*[np.asarray(c,float) for c in controls]])
 y=np.asarray(y,float)
 beta=np.linalg.lstsq(X,y,rcond=None)[0]
 return y-X@beta

def test(rows,label,xkey,ykey,controls=(),lag_note=None):
 pairs=[]
 for r in rows:
  if math.isfinite(r.get(xkey,math.nan)) and math.isfinite(r.get(ykey,math.nan)):
   pairs.append(r)
 if len(pairs)<20:return None
 days=[r['day'] for r in pairs]
 x=[r[xkey] for r in pairs]; y=[r[ykey] for r in pairs]
 # calendar-adjust both series before rank association and block null
 xr=residual(x,days,controls)
 yr=residual(y,days,controls)
 rho=float(spearmanr(xr,yr).statistic)
 p=block_permutation_p(xr,yr,n_perm=5000,max_exceedances=None,method='spearman')
 return {'label':label,'n':len(pairs),'rho':rho,'p':float(p),'block_len':default_block_len(len(pairs)),'lag':lag_note,'controls':list(controls and ['hrv','hr_resting'] or [])}

def lag_rows(rows,xkey,ykey,offset):
 ymap={r['day']:r for r in rows}
 out=[]
 for r in rows:
  target=ymap.get(r['day']+dt.timedelta(days=offset))
  if target and math.isfinite(r.get(xkey,math.nan)) and math.isfinite(target.get(ykey,math.nan)):
   out.append({'day':r['day'],'x':r[xkey],'y':target[ykey]})
 return out

def test_custom(pairs,label):
 if len(pairs)<20:return None
 days=[r['day'] for r in pairs];x=[r['x'] for r in pairs];y=[r['y'] for r in pairs]
 xr=residual(x,days);yr=residual(y,days);rho=float(spearmanr(xr,yr).statistic)
 p=block_permutation_p(xr,yr,n_perm=5000,max_exceedances=None,method='spearman')
 return {'label':label,'n':len(pairs),'rho':rho,'p':float(p),'block_len':default_block_len(len(pairs))}

def bh(entries):
 order=sorted(range(len(entries)),key=lambda i:entries[i]['p']);m=len(entries);q=[1.0]*m;running=1.0
 for rank,i in reversed(list(enumerate(order,1))):
  running=min(running,entries[i]['p']*m/rank);q[i]=min(1.0,running)
 for e,v in zip(entries,q):e['q']=v;e['survives_q_0_10']=v<=.10

def main():
 rows=load(); tests=[]
 for key,label in [('hrv','Fitbit Readiness vs OptiHealth HRV RMSSD'),('hr_resting','Fitbit Readiness vs OptiHealth resting HR'),('respiratory','Fitbit Readiness vs OptiHealth respiratory rate'),('sleep_total','Fitbit Readiness vs total sleep'),('sleep_deep','Fitbit Readiness vs deep sleep minutes'),('sleep_rem','Fitbit Readiness vs REM minutes'),('sleep_awake','Fitbit Readiness vs awake minutes'),('strain','Fitbit Readiness vs WHOOP Strain'),('whoop_recovery','Fitbit Readiness vs WHOOP Recovery'),('oura_readiness','Fitbit Readiness vs Oura Readiness')]:
  e=test(rows,label,'readiness',key)
  if e:tests.append(e)
 # Directional one-day tests. Positive offset means y is next calendar day.
 for x,y,label in [('readiness','hrv','Readiness today vs HRV tomorrow'),('hrv','readiness','HRV today vs Readiness tomorrow'),('readiness','hr_resting','Readiness today vs resting HR tomorrow'),('hr_resting','readiness','resting HR today vs Readiness tomorrow')]:
  e=test_custom(lag_rows(rows,x,y,1),label+' (lag +1d)')
  if e:tests.append(e)
 # Score-gap hypotheses on same-day WHOOP paired rows.
 gaprows=[r for r in rows if math.isfinite(r.get('whoop_recovery',math.nan))]
 for key,label in [('sleep_total','WHOOP−Fitbit score gap vs total sleep'),('sleep_rem','WHOOP−Fitbit score gap vs REM')]:
  pairs=[{'day':r['day'],'x':r['whoop_recovery']-r['readiness'],'y':r[key]} for r in gaprows if math.isfinite(r.get(key,math.nan))]
  e=test_custom(pairs,label)
  if e:tests.append(e)
 bh(tests)
 result={'input':str(INPUT.relative_to(ROOT)),'family_size':len(tests),'tests':tests,'method':{'season_adjustment':'intercept + annual sin/cos on each paired ordered cohort','null':'OptiHealth circular block permutation','n_perm':5000,'max_exceedances':None,'fdr':'Benjamini-Hochberg q <= 0.10','serial_warning':'p-values are block-exchangeability surrogates, not iid or causal tests'}}
 OUTPUT.write_text(json.dumps(result,indent=2)+'\n')
 for e in sorted(tests,key=lambda e:e['q']):print(f"{e['q']:.4f}\t{e['p']:.4f}\t{e['rho']:+.3f}\tn={e['n']}\t{e['label']}")
 print('wrote',OUTPUT)
if __name__=='__main__':main()
