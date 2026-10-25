"""Expanded, reproducible audit for the Fitbit-vs-WHOOP article.

This deliberately separates:
- metrics both devices expose (paired agreement);
- Fitbit-only sleep-detail fields in this export;
- WHOOP recovery/strain fields;
- daily pulse/activity associations with WHOOP Day Strain.

All associations are descriptive Spearman rank correlations. Missing values are
pairwise omitted. This is not a claim that a vendor score is a ground truth.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path("/opt/article-fitbit-vs-whoop")
DATA = ROOT / "data"
OUT = ROOT / "analysis" / "results_expanded_metrics.json"


def rows(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(newline="") as f:
        return list(csv.DictReader(f))


def values(rs: list[dict[str, str]], col: str) -> np.ndarray:
    return np.array([float(r[col]) if r.get(col) not in (None, "") else np.nan for r in rs], dtype=float)


def summary(x: np.ndarray) -> dict:
    ok = np.isfinite(x)
    if not ok.any():
        return {"n": 0}
    return {
        "n": int(ok.sum()),
        "mean": round(float(np.mean(x[ok])), 3),
        "median": round(float(np.median(x[ok])), 3),
        "sd": round(float(np.std(x[ok], ddof=1)), 3) if ok.sum() > 1 else None,
        "min": round(float(np.min(x[ok])), 3),
        "max": round(float(np.max(x[ok])), 3),
    }


def rho(x: np.ndarray, y: np.ndarray) -> dict:
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 3 or np.nanstd(x[ok]) == 0 or np.nanstd(y[ok]) == 0:
        return {"n": int(ok.sum()), "rho": None, "note": "constant or too few complete pairs"}
    return {"n": int(ok.sum()), "rho": round(float(spearmanr(x[ok], y[ok]).statistic), 3)}


def main() -> None:
    night = rows("nightly_wide.csv")
    strain = rows("strain_daily_wide.csv")
    out: dict = {
        "method": "Descriptive Spearman rho; pairwise complete observations; no causal interpretation.",
        "nightly_metric_summary": {},
        "paired_sleep_agreement": {},
        "whoop_vs_fitbit_sleep_and_pulse": {},
        "strain_vs_fitbit_activity_and_pulse": {},
        "data_quality": {},
    }

    for c in [
        "f_tst", "f_tib", "f_deep", "f_rem", "f_light", "f_awake", "f_eff",
        "f_latency", "f_awakenings", "f_rhr", "hr_night", "hr_night_min",
        "hrv_night", "spo2_night", "spo2_sd", "w_rhr", "w_recovery", "w_strain",
    ]:
        out["nightly_metric_summary"][c] = summary(values(night, c))

    for f, w, label in [
        ("f_tst", "w_tst", "total_sleep_min"),
        ("f_tib", "w_tib", "time_in_bed_min"),
        ("f_deep", "w_deep", "deep_sleep_min"),
        ("f_rem", "w_rem", "rem_sleep_min"),
    ]:
        x, y = values(night, f), values(night, w)
        m = np.isfinite(x) & np.isfinite(y)
        d = y[m] - x[m]
        out["paired_sleep_agreement"][label] = {
            **rho(x, y),
            "fitbit_mean": round(float(np.mean(x[m])), 3),
            "whoop_mean": round(float(np.mean(y[m])), 3),
            "whoop_minus_fitbit_mean": round(float(np.mean(d)), 3),
            "whoop_minus_fitbit_median": round(float(np.median(d)), 3),
        }

    # WHOOP's core nightly outputs versus Fitbit sleep detail and independent-ish pulse summaries.
    for a, aname in [("w_recovery", "WHOOP Recovery"), ("w_strain", "WHOOP Day Strain"), ("w_rhr", "WHOOP sleep RHR")]:
        for b, bname in [
            ("f_tst", "Fitbit total sleep"), ("f_deep", "Fitbit deep sleep"),
            ("f_rem", "Fitbit REM"), ("f_awake", "Fitbit awake minutes"),
            ("f_awakenings", "Fitbit awakenings"), ("f_eff", "Fitbit efficiency"),
            ("f_rhr", "Fitbit RHR"), ("hr_night", "night mean HR"),
            ("hr_night_min", "night minimum HR"), ("hrv_night", "night HRV"),
            ("spo2_night", "night SpO2"),
        ]:
            out["whoop_vs_fitbit_sleep_and_pulse"][f"{aname} vs {bname}"] = rho(values(night, a), values(night, b))

    for c, label in [
        ("kcal_total", "Fitbit total calories"), ("steps", "Fitbit steps"),
        ("mod_min", "Fitbit moderate minutes"), ("vig_min", "Fitbit vigorous minutes"),
        ("mvpa", "Fitbit MVPA"), ("hr_mean", "Fitbit daily mean HR"),
        ("hr_p95", "Fitbit daily HR p95"), ("hr_max", "Fitbit daily HR max"),
        ("min_above_100", "Fitbit minutes HR>100"), ("min_above_120", "Fitbit minutes HR>120"),
        ("min_above_140", "Fitbit minutes HR>140"), ("wk_min", "WHOOP workout minutes"),
        ("wk_kcal", "WHOOP workout calories"), ("wk_sess", "WHOOP session count"),
        ("wk_strain_sum", "WHOOP session Strain sum"), ("wk_strain_max", "WHOOP max session Strain"),
    ]:
        out["strain_vs_fitbit_activity_and_pulse"][label] = rho(values(strain, "strain"), values(strain, c))

    out["data_quality"] = {
        "fitbit_sleep_latency": summary(values(night, "f_latency")),
        "fitbit_sleep_latency_interpretation": "All 68 values are zero; this export does not contain usable latency variation.",
        "fitbit_awakenings": summary(values(night, "f_awakenings")),
        "whoop_wake_events": "Not present in the local nightly export; do not infer them from Fitbit awakenings.",
        "daily_pulse": "The strain export contains daily mean, p95, max HR and threshold minutes; these are not a raw continuous HR trace.",
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {OUT}")
    print(json.dumps(out["data_quality"], indent=2))


if __name__ == "__main__":
    main()
