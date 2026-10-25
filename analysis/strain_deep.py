"""Strain deep dive: что такое WHOOP Day Strain на самом деле.

WHOOP Strain по документации = логарифмическая шкала 0-21 (Borg-подобная),
построенная на кардионагрузке: время в зонах пульса, взвешенное по интенсивности.
Проверяем ПРОТИВ ЧЕГО он реально коррелирует у Антона.
"""
from __future__ import annotations
import csv, json, sys
import numpy as np
from scipy.stats import spearmanr, pearsonr
sys.path.insert(0, "/opt/optihealth_analysis/src")
from analysis.serial import block_permutation_p  # noqa

D = "/opt/article-fitbit-vs-whoop/data"

def rows(n):
    with open(f"{D}/{n}.csv") as f: return list(csv.DictReader(f))

def num(v): return float(v) if v not in ("", None) else np.nan

def t(x, y, label, out):
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 15:
        out[label] = {"n": int(m.sum()), "note": "n<15"}
        return
    rho, _ = spearmanr(x[m], y[m])
    r, _ = pearsonr(x[m], y[m])
    p = block_permutation_p(x[m], y[m], method="spearman")
    out[label] = dict(n=int(m.sum()), spearman=round(float(rho), 3),
                      pearson=round(float(r), 3), p=round(float(p), 4))

def main():
    out = {}
    w = rows("strain_daily_wide")
    strain = np.array([num(r["strain"]) for r in w])

    for col, lab in [
        ("kcal_total", "strain vs Fitbit total kcal"),
        ("kcal_active", "strain vs Fitbit ACTIVE kcal"),
        ("steps", "strain vs Fitbit steps"),
        ("mod_min", "strain vs Fitbit moderate-intensity min"),
        ("vig_min", "strain vs Fitbit vigorous-intensity min"),
        ("mvpa", "strain vs Fitbit MVPA (mod+vig)"),
        ("hr_mean", "strain vs mean daily HR"),
        ("hr_p95", "strain vs daily HR p95"),
        ("hr_max", "strain vs daily HR max"),
        ("min_above_100", "strain vs minutes HR>100"),
        ("min_above_120", "strain vs minutes HR>120"),
        ("min_above_140", "strain vs minutes HR>140"),
        ("wk_min", "strain vs WHOOP workout minutes"),
        ("wk_kcal", "strain vs WHOOP workout kcal"),
        ("wk_sess", "strain vs WHOOP session count"),
        ("wk_strain_sum", "strain vs sum of session strains"),
        ("wk_strain_max", "strain vs max session strain"),
    ]:
        t(strain, np.array([num(r[col]) for r in w]), lab, out)

    # Логарифмическая природа: strain должен быть ~ log(нагрузка)
    kcal = np.array([num(r["kcal_active"]) for r in w])
    m = np.isfinite(strain) & np.isfinite(kcal) & (kcal > 0)
    if m.sum() > 15:
        r_lin, _ = pearsonr(kcal[m], strain[m])
        r_log, _ = pearsonr(np.log(kcal[m]), strain[m])
        out["log_check_active_kcal"] = dict(
            n=int(m.sum()), pearson_linear=round(float(r_lin), 3),
            pearson_on_log=round(float(r_log), 3))

    m120 = np.array([num(r["min_above_120"]) for r in w])
    m2 = np.isfinite(strain) & np.isfinite(m120) & (m120 > 0)
    if m2.sum() > 15:
        r_lin, _ = pearsonr(m120[m2], strain[m2])
        r_log, _ = pearsonr(np.log1p(m120[m2]), strain[m2])
        out["log_check_min_above_120"] = dict(
            n=int(m2.sum()), pearson_linear=round(float(r_lin), 3),
            pearson_on_log1p=round(float(r_log), 3))

    # дни БЕЗ тренировок: какой strain?
    wk = np.array([num(r["wk_min"]) for r in w])
    nowk = np.isfinite(strain) & (~np.isfinite(wk) | (wk == 0))
    haswk = np.isfinite(strain) & np.isfinite(wk) & (wk > 0)
    out["rest_days"] = dict(
        n_no_workout=int(nowk.sum()),
        strain_no_workout=round(float(np.nanmean(strain[nowk])), 2) if nowk.sum() else None,
        n_with_workout=int(haswk.sum()),
        strain_with_workout=round(float(np.nanmean(strain[haswk])), 2) if haswk.sum() else None,
    )

    print(json.dumps(out, indent=2, ensure_ascii=False))
    with open("/opt/article-fitbit-vs-whoop/analysis/results_strain.json", "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
