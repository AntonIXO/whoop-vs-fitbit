#!/usr/bin/env python3
"""Read-only audit of local article exports. No database calls; writes only the audit JSON.
Run: /opt/article-fitbit-vs-whoop/.venv/bin/python /opt/article-fitbit-vs-whoop/analysis/strain_trimp_audit.py
All correlations are descriptive; no inferential p-values or selected-lag corrections.
"""
from pathlib import Path
from datetime import date, timedelta
import csv
import hashlib
import json
import re
import sys
import platform
import numpy as np
import scipy
from scipy.stats import rankdata

ROOT = Path('/opt/article-fitbit-vs-whoop')
OUT = ROOT / 'analysis'
REMOVED = {'2025-10-11', '2025-10-12'}
FOOTER = re.compile(r'^\((\d+) rows?\)$')
ISO = re.compile(r'^\d{4}-\d{2}-\d{2}$')
manifest = {}

def read_csv(name):
    path = ROOT / 'data' / name
    data = list(csv.DictReader(path.open()))
    valid, discarded, declared = [], [], []
    for r in data:
        if ISO.fullmatch(r.get('day') or ''):
            date.fromisoformat(r['day'])
            valid.append(r)
        else:
            discarded.append(r)
            for value in r.values():
                if isinstance(value, str) and (m := FOOTER.fullmatch(value)):
                    declared.append(int(m.group(1)))
    assert not declared or declared == [len(valid)], (name, declared, len(valid))
    manifest[str(path)] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                           'valid_rows': len(valid), 'discarded_non_date_records': discarded,
                           'declared_row_counts': declared}
    return valid

def number(v):
    return float(v) if v not in ('', None) else np.nan

def corr(x, y, dates=None):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    def r(a, b):
        if len(a) < 3 or np.ptp(a) == 0 or np.ptp(b) == 0:
            return None
        return float(np.corrcoef(a, b)[0, 1])
    result = {'n': len(x), 'spearman': r(rankdata(x), rankdata(y)), 'pearson': r(x, y)}
    if dates is not None:
        result['strain_dates'] = [d for d, keep in zip(dates, m) if keep]
    return result

def coverage(days):
    days = sorted(set(days))
    if not days:
        return {'n_unique_dates': 0}
    first, last = map(date.fromisoformat, [days[0], days[-1]])
    calendar = [(first + timedelta(days=i)).isoformat() for i in range((last-first).days+1)]
    runs = []
    for d in days:
        if not runs or date.fromisoformat(d) - date.fromisoformat(runs[-1]['end']) != timedelta(days=1):
            runs.append({'start': d, 'end': d, 'n': 1})
        else:
            runs[-1]['end'] = d
            runs[-1]['n'] += 1
    return {'n_unique_dates': len(days), 'start': days[0], 'end': days[-1],
            'calendar_span_days_inclusive': len(calendar), 'missing_dates_within_span': sorted(set(calendar)-set(days)),
            'contiguous_observed_runs': runs, 'observed_dates': days}

all_csv = {p.name: read_csv(p.name) for p in sorted((ROOT/'data').glob('*.csv'))}
raw = all_csv['strain_daily_wide.csv']
assert len({r['day'] for r in raw}) == len(raw), 'duplicate strain dates'
columns = [k for k in raw[0] if k != 'day']
raw = [{k: (v if k == 'day' else number(v)) for k, v in r.items()} for r in raw]
filtered = [r for r in raw if r['day'] not in REMOVED]
cohorts = {'all_exported': raw, 'figure5_exclusions': filtered}

# No assumptions about actual physical wear: bounds refer only to observed exports.
inventory = {}
period_unions = {}
for name, rows in all_csv.items():
    groups = sorted({r.get('period', 'unlabelled') for r in rows})
    inventory[name] = {}
    for group in groups:
        rr = [r for r in rows if r.get('period', 'unlabelled') == group]
        inventory[name][group] = {'rows': len(rr), **coverage([r['day'] for r in rr])}
        if group in ('P1', 'P2'):
            period_unions.setdefault(group, set()).update(r['day'] for r in rr)

# Cross-check duplicated day strain in independent local exports, never silently repair.
cross_checks = {}
rawmap = {r['day']: r for r in raw}
for filename, key in [('strain_kcal.csv', 'strain'), ('nightly_wide.csv', 'w_strain'), ('ecg_paired.csv', 'w_strain')]:
    paired, conflicts = 0, []
    for r in all_csv[filename]:
        if r['day'] in rawmap and np.isfinite(v := number(r[key])):
            paired += 1
            if abs(v - rawmap[r['day']]['strain']) > 1e-6:
                conflicts.append({'day': r['day'], 'other': v, 'wide': rawmap[r['day']]['strain']})
    cross_checks[filename] = {'paired_records': paired, 'disagreements_gt_1e-6': conflicts}

fig_cols = ['wk_strain_sum', 'wk_strain_max', 'wk_min', 'wk_sess', 'min_above_140',
            'min_above_120', 'mvpa', 'kcal_total', 'steps', 'hr_mean']
draft_values = {'kcal_total': .06, 'steps': .07, 'mvpa': .03, 'min_above_120': .09,
                'min_above_140': .09, 'wk_min': .09, 'hr_mean': .19, 'wk_strain_sum': -.02,
                'wk_strain_max': -.20}

# Fixed illustrative nonnegative bin weights, not optimized against strain.
# Bins are (100,120], (120,140], (140,infinity), not personal HRR zones.
proxy_specs = {'weighted_threshold_minutes_123': [1,2,3],
               'weighted_threshold_minutes_124': [1,2,4],
               'weighted_threshold_minutes_135': [1,3,5]}
for r in raw:
    a, b, c = [r[f'min_above_{t}'] for t in (100,120,140)]
    for name, weights in proxy_specs.items():
        r[name] = float(np.dot([a-b, b-c, c], weights)) if np.all(np.isfinite([a,b,c])) and a >= b >= c >= 0 else np.nan

results = {'method': {'scope': 'Local CSV and source audit; no DB access; writes analysis/results_trimp_audit.json.',
                      'python': sys.version, 'platform': platform.platform(), 'numpy': np.__version__, 'scipy': scipy.__version__,
                      'command': '/opt/article-fitbit-vs-whoop/.venv/bin/python /opt/article-fitbit-vs-whoop/analysis/strain_trimp_audit.py',
                      'correlations': 'Pairwise finite values, Pearson and Spearman with average ranks for ties; all descriptive. No p-values.',
                      'lag_convention': 'corr(Day Strain at calendar day d, comparator at d + lag). +1 means comparator is one day AFTER strain; -1 means comparator is one day BEFORE. Both endpoints come from the specified cohort; no row shifts, wraparound, or imputation.',
                      'lag_selection': 'All -2..+2 lags reported. Extremum is exploratory, NOT validated correction. No confirmatory p after selection.'},
           'export_inventory': inventory, 'period_bounds_from_labelled_exports': {p: coverage(ds) for p, ds in period_unions.items()},
           'cross_export_strain_checks': cross_checks,
           'figure5': {'source': 'analysis/make_all_figures.py:175-225', 'removed_dates': sorted(REMOVED),
                       'removed_records': [{k: (None if isinstance(v,float) and not np.isfinite(v) else v) for k,v in r.items()} for r in raw if r['day'] in REMOVED],
                       'retained_before_removed_dates': [r['day'] for r in filtered if r['day'] < min(REMOVED)],
                       'exclusion_warning': 'The removed dates are NOT the first two exported strain days. No local calibration metadata establish their calibration status.',
                       'hardcoded_n_in_title': 72, 'candidate_columns': fig_cols},
           'proxy': {'label': 'Exploratory nonstandard absolute-HR weighted-threshold-minutes proxy; NOT TRIMP.',
                     'bins_bpm': ['(100,120]', '(120,140]', '(140,infinity)'], 'fixed_bin_weights': proxy_specs,
                     'formula_123': '(M100-M120) + 2*(M120-M140) + 3*M140 = M100 + M120 + M140',
                     'fit': 'No weights fitted; all three illustrative sensitivity choices reported, none selected as best.',
                     'threshold_integrity_violations': [r['day'] for r in raw if np.all(np.isfinite([r[f'min_above_{t}'] for t in (100,120,140)])) and not r['min_above_100'] >= r['min_above_120'] >= r['min_above_140'] >= 0]},
           'cohorts': {}}

for label, rows in cohorts.items():
    ds = [r['day'] for r in rows]
    smap = {r['day']: r for r in rows}
    strain = [r['strain'] for r in rows]
    out = {'coverage': coverage(ds), 'columns': {}, 'same_day_correlations': {}, 'calendar_lags': {}, 'violations_by_lag': {}}
    for col in columns:
        out['columns'][col] = {'n_finite': sum(np.isfinite(r[col]) for r in rows),
                              'missing_dates': [r['day'] for r in rows if not np.isfinite(r[col])],
                              'zero_dates': [r['day'] for r in rows if r[col] == 0]}
    for col in columns[1:] + list(proxy_specs):
        out['same_day_correlations'][col] = corr(strain, [r[col] for r in rows], ds)
        out['calendar_lags'][col] = []
        common = [r for r in rows if np.isfinite(r['strain']) and all(
            (key := (date.fromisoformat(r['day'])+timedelta(days=lag)).isoformat()) in smap and np.isfinite(smap[key][col]) for lag in range(-2,3))]
        for lag in range(-2,3):
            def shifted(rr):
                return [smap.get((date.fromisoformat(r['day'])+timedelta(days=lag)).isoformat(), {}).get(col, np.nan) for r in rr]
            out['calendar_lags'][col].append({'lag_days': lag,
                'available_pairs': corr(strain, shifted(rows), ds),
                'common_strain_dates_across_all_five_lags': corr([r['strain'] for r in common], shifted(common), [r['day'] for r in common])})
    for lag in range(-2,3):
        pairs = []
        for r in rows:
            wd = (date.fromisoformat(r['day'])+timedelta(days=lag)).isoformat()
            maximum = smap.get(wd, {}).get('wk_strain_max', np.nan)
            if np.isfinite(maximum) and np.isfinite(r['strain']):
                pairs.append({'strain_day': r['day'], 'workout_day': wd, 'day_strain': r['strain'],
                              'max_workout_strain': maximum, 'workout_minus_day': maximum-r['strain']})
        bad = [p for p in pairs if p['workout_minus_day'] > 1e-6]
        out['violations_by_lag'][str(lag)] = {'n_pairs': len(pairs), 'n_day_strain_below_workout': len(bad),
                                          'fraction': len(bad)/len(pairs) if pairs else None, 'flagged_pairs': bad}
    ss = np.asarray(strain)
    no_record = [r['strain'] for r in rows if not np.isfinite(r['wk_min'])]
    zero = [r['strain'] for r in rows if r['wk_min'] == 0]
    yes = [r['strain'] for r in rows if np.isfinite(r['wk_min']) and r['wk_min'] > 0]
    out['distribution'] = {'n': len(ss), 'mean': float(ss.mean()), 'median': float(np.median(ss)),
                           'sd_sample': float(ss.std(ddof=1)), 'min': float(ss.min()), 'max': float(ss.max()),
                           'n_in_8_to_14_inclusive': int(((ss>=8)&(ss<=14)).sum()),
                           'row_adjacent_autocorrelation_NOT_daily': corr(ss[:-1], ss[1:]),
                           'true_calendar_day_plus_1_autocorrelation': corr(ss, [smap.get((date.fromisoformat(r['day'])+timedelta(days=1)).isoformat(), {}).get('strain', np.nan) for r in rows], ds)}
    def summ(x):
        return {'n': len(x), 'mean_strain': float(np.mean(x)) if x else None}
    out['workout_record_groups'] = {'positive_minutes': summ(yes), 'explicit_zero_minutes': summ(zero), 'missing_minutes_NOT_confirmed_rest': summ(no_record)}
    out['mvpa_zero_with_both_components_missing_dates'] = [r['day'] for r in rows if r['mvpa']==0 and not np.isfinite(r['mod_min']) and not np.isfinite(r['vig_min'])]
    valid_mvpa = [r for r in rows if np.isfinite(r['mod_min']) and np.isfinite(r['vig_min'])]
    out['mvpa_complete_components_sensitivity'] = corr([r['strain'] for r in valid_mvpa], [r['mvpa'] for r in valid_mvpa], [r['day'] for r in valid_mvpa])
    results['cohorts'][label] = out

results['draft_correlation_reproduction'] = {c: {'draft_rho': v, **results['cohorts']['figure5_exclusions']['same_day_correlations'][c],
    'matches_draft_at_2dp': round(results['cohorts']['figure5_exclusions']['same_day_correlations'][c]['spearman'],2) == v} for c,v in draft_values.items()}
results['limitations'] = [
    'Exact observed date ranges and gaps are reported, but actual physical wear start/end and daily wear duration cannot be established from paired/selected aggregate exports.',
    'strain_daily_wide covers P1 only. P2 dates in sleep, RHR, and steps exports are not a P2 strain replication.',
    'The local data/extract*.sh scripts do not contain the query that generated strain_daily_wide.csv. HR source, threshold duration weighting, sampling cadence, coverage denominator, timezone, and day-boundary semantics cannot be verified for that file.',
    'Only aggregate HR means/percentiles/maxima and absolute-threshold minutes are available. No raw time-stamped HR, valid per-sample duration, personal HRmax, HRR trajectory, lactate-derived coefficients, or workout-specific time-in-zones. True HRR/Banister or individualized TRIMP is not identifiable.',
    'Absolute-HR proxy omits all HR<=100 exposure and uses arbitrary nonnegative intensity weights; it is not physiological validation or WHOOP formula reconstruction.',
    'Workout strain sum is descriptive only: strain on a nonlinear scale is not additive. Same-day max exceeding day strain is an exported-data consistency flag conditional on correctly aligned complete day/cycle boundaries, not proof of a device-algorithm failure.',
    'Lag search may expose a date-boundary/export mismatch, but selection, autocorrelation, shared-device inputs and incomplete day coverage preclude interpreting the selected lag as a validated correction or physiological relationship.',
    'No p-values or significance claims computed. Multiple predictors, lags, proxies and exclusion sensitivities are exploratory in one person; 0.2 is not a validated no-association threshold, and small lag-1 correlation is not evidence of white noise.',
    'Missing workout minutes are not confirmed no-workout/rest days; missing active calories are not zero. Exported zero MVPA with missing component minutes is separately flagged.',
    'CSV files contain PostgreSQL row-count footer records. The published source readers do not skip them; this audit validates and removes them. Existing scripts are not executed because they write inside the article project.',
    'The figure excludes 2025-10-11 and 2025-10-12 but keeps 2025-10-08 and 2025-10-09. Treat calibration justification as unverified; both inclusion/exclusion cohorts are reported.'
]
for path in list((ROOT/'analysis').glob('*.py')) + list((ROOT/'data').glob('*.sh')) + [ROOT/'draft.md']:
    manifest[str(path)] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
results['input_manifest'] = manifest

def clean(obj):
    if isinstance(obj, dict): return {k: clean(v) for k,v in obj.items()}
    if isinstance(obj, (list,tuple)): return [clean(v) for v in obj]
    if isinstance(obj, (np.integer,)): return int(obj)
    if isinstance(obj, (np.bool_,)): return bool(obj)
    if isinstance(obj, (float, np.floating)): return float(obj) if np.isfinite(obj) else None
    return obj

OUT.mkdir(parents=True, exist_ok=True)
(OUT/'results_trimp_audit.json').write_text(json.dumps(clean(results), indent=2, allow_nan=False)+'\n')
# Strict serialization plus invariants exercised, not just an artifact write.
assert len(filtered) == len(raw)-len(REMOVED)
assert not results['proxy']['threshold_integrity_violations']
for cohort in results['cohorts'].values():
    for col, r in cohort['same_day_correlations'].items():
        assert r == cohort['calendar_lags'][col][2]['available_pairs']
summary = {'artifact': str(OUT/'results_trimp_audit.json'), 'raw_n': len(raw), 'figure_n': len(filtered),
           'figure_correlations': {c: {k:v for k,v in results['draft_correlation_reproduction'][c].items() if k!='strain_dates'} for c in draft_values},
           'lag_max_workout': [{ 'lag': v['lag_days'], **{k:v2 for k,v2 in v['available_pairs'].items() if k!='strain_dates'}} for v in results['cohorts']['figure5_exclusions']['calendar_lags']['wk_strain_max']],
           'violations': {k:{kk:vv for kk,vv in v.items() if kk!='flagged_pairs'} for k,v in results['cohorts']['figure5_exclusions']['violations_by_lag'].items()},
           'verified': 'Strict JSON serialized; footer counts, unique strain dates, exclusion count, nested thresholds and zero-lag/same-day equality asserted.'}
print(json.dumps(clean(summary), indent=2, allow_nan=False))
