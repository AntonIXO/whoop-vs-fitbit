"""Independent, deterministic checks for the revised English article.

This checks quoted numbers and file integrity, not the truth of vendor claims.
Pass --self-test to confirm a deliberately corrupted sleep table is rejected.
"""
import csv
from datetime import date, timedelta
import json
from pathlib import Path
import re
import sys
import numpy as np
from scipy.stats import spearmanr
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
checks = []

def require(ok, label):
    if not ok:
        raise AssertionError(label)
    checks.append(label)

def rows(name):
    return [r for r in csv.DictReader((ROOT/'data'/name).open())
            if re.fullmatch(r'\d{4}-\d{2}-\d{2}', r.get('day') or '')]

def rho_pairs(rs, x, y):
    pairs = [(float(r[x]), float(r[y])) for r in rs if r.get(x) and r.get(y)]
    a, b = np.array(pairs).T
    return float(spearmanr(a, b).statistic), len(pairs)

def check_sleep_table(text):
    s = [r for r in rows('sleep_paired_staged.csv') if r['period']=='P1']
    assert len(s)==68
    for label,f,w in [('Total sleep time','f_tst','w_tst'),('Time in bed','f_tib','w_tib'),
                      ('REM sleep','f_rem','w_rem'),('Deep sleep','f_deep','w_deep')]:
        a=np.array([float(r[f]) for r in s]); b=np.array([float(r[w]) for r in s])
        lines=[l for l in text.splitlines() if l.startswith('|') and label in l]
        expected=[round(float(a.mean()),1),round(float(b.mean()),1),round(float(spearmanr(a,b).statistic),3)]
        candidates=[[float(n) for n in re.findall(r'\d+\.\d+',l)] for l in lines]
        values=next((v for v in candidates if v==expected), None)
        assert values==expected,(label,values,expected)
    return s

def main():
    text=(ROOT/'draft.md').read_text()
    s=check_sleep_table(text)
    checks.append('sleep table: all four means and correlations independently reproduced')
    if '--self-test' in sys.argv:
        try:
            check_sleep_table(text.replace('473.0 min','999.0 min',1))
        except AssertionError:
            checks.append('negative control: corrupted sleep mean rejected')
        else:
            raise AssertionError('negative control failed to fail')
    for f,w,expected in [('f_tst','w_tst',[-49.8,30.9]),('f_deep','w_deep',[-9.4,61.9])]:
        d=np.array([float(r[w])-float(r[f]) for r in s]); limits=[d.mean()-1.96*d.std(ddof=1),d.mean()+1.96*d.std(ddof=1)]
        require([round(float(v),1) for v in limits]==expected,f'{f} limits reproduced')
    audit=json.loads((ROOT/'analysis/results_trimp_audit.json').read_text())
    rs=[r for r in rows('strain_daily_wide.csv') if r['day'] not in ('2025-10-11','2025-10-12')]
    require(len(rs)==72,'Strain exclusion cohort n=72')
    require(min(r['day'] for r in rs)=='2025-10-08','exclusions are not first exported days')
    for col, rec in audit['draft_correlation_reproduction'].items():
        r,n=rho_pairs(rs,'strain',col)
        require(n==rec['n'] and abs(r-rec['spearman'])<1e-12,f'independent same-day Strain correlation: {col}')
    lookup={date.fromisoformat(r['day']):r for r in rs}
    for lag in range(-2,3):
        pairs=[(float(r['strain']),float(lookup[d+timedelta(days=lag)]['wk_strain_max']))
               for d,r in lookup.items() if d+timedelta(days=lag) in lookup and lookup[d+timedelta(days=lag)]['wk_strain_max']]
        a,b=np.array(pairs).T
        entry=audit['cohorts']['figure5_exclusions']['calendar_lags']['wk_strain_max'][lag+2]['available_pairs']
        require(len(pairs)==entry['n'] and abs(spearmanr(a,b).statistic-entry['spearman'])<1e-12,f'independent calendar lag {lag}')
    common=[d for d in lookup if all(d+timedelta(days=k) in lookup and lookup[d+timedelta(days=k)]['wk_strain_max'] for k in range(-2,3))]
    require(len(common)==38,'common-support dates n=38')
    for k,target in [(0,-.237),(-1,.879)]:
        r=spearmanr([float(lookup[d]['strain']) for d in common],[float(lookup[d+timedelta(days=k)]['wk_strain_max']) for d in common]).statistic
        require(round(float(r),3)==target,f'common support lag {k}')
    sp=rows('steps_paired.csv')
    diffs=[abs(float(r['f_steps'])-float(r['w_steps'])) for r in sp]
    require(len(sp)==25 and np.median(diffs)==5540,'steps n and median absolute difference')
    require(round(rho_pairs(sp,'f_steps','w_steps')[0],2)==.03,'steps correlation')
    rec=rows('recovery_rhr.csv')
    require(len(rec)==70 and round(rho_pairs(rec,'rhr','recovery')[0],2)==-.59,'Recovery correlation and n')
    p2=[r for r in rows('sleep_paired_staged.csv') if r['period']=='P2']
    require(len(p2)==6,'P2 staged nights n=6')
    gap=np.mean([float(r['w_deep'])-float(r['f_deep']) for r in p2])
    require(round(float(gap))==37,'P2 rounded deep-sleep gap')
    sleep_audit=json.loads((ROOT/'analysis/sleep_reaudit/results.json').read_text())
    may=sleep_audit['periods']['P2_MAY']
    require(may['whoop_source_id']==2757 and may['whoop_main_n']==17 and may['whoop_naps']==1 and may['paired_n']==17,'May source-2757 sleep cohort')
    require(may['metrics']['minutes_awake']['n']==17 and may['metrics']['time_in_bed_min']['n']==17,'May boundary metrics n=17')
    require(may['metrics']['minutes_deep']['n']==4 and abs(may['metrics']['minutes_deep']['whoop_mean']-132.25)<1e-12,'May stage availability gate and deep mean')
    require('| May 2026 | Deep sleep | 4 | 93.0 min | 132.3 min | **+39.3 min** | 39.3 min |' in text,'article contains integrated May deep-sleep result')
    require('### The May nights that the canonical view hid' not in text,'article has no retrospective May addendum')
    for name in ['draft.md','GLOSSARY.md']:
        t=(ROOT/name).read_text()
        require(not re.search('[\u0400-\u04ff]',t),f'{name}: no untranslated Cyrillic')
        for link in re.findall(r'\]\(([^)]+)\)',t):
            if not re.match(r'https?://|#',link):
                require((ROOT/link).is_file(),f'{name}: local link {link}')
    for p in sorted((ROOT/'figures').glob('fig*.png')):
        with Image.open(p) as im:
            require(im.width>500 and im.height>300,f'{p.name}: usable dimensions')
            im.verify()
    print(json.dumps({'status':'PASS','checks':len(checks),'details':checks},indent=2))

if __name__=='__main__':
    main()
