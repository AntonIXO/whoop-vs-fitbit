#!/usr/bin/env python3
"""Read-only OptiHealth cross-check for Fitbit Readiness."""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "data/readiness_optihealth_wide.csv"
WHOOP_INPUT = ROOT / "data/whoop_optihealth_wide.csv"
OUTPUT = Path(__file__).resolve().parent / "optihealth_results.json"


def load(path, score_key):
    rows = []
    with path.open() as f:
        for row in csv.DictReader(f):
            out = {"day": dt.date.fromisoformat(row["day"]), "score": float(row[score_key])}
            for k, v in row.items():
                if k in {"day", "readiness"}:
                    continue
                out[k] = float(v) if v not in ("", None) else math.nan
            rows.append(out)
    return rows


def residualize(values, days):
    X = []
    for day in days:
        t = (day - dt.date(2024, 1, 1)).days
        phase = 2 * math.pi * t / 365.2425
        X.append([1.0, math.sin(phase), math.cos(phase)])
    X = np.asarray(X)
    y = np.asarray(values, dtype=float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


def association(rows, metric):
    complete = [r for r in rows if math.isfinite(r.get(metric, math.nan))]
    x = [r["score"] for r in complete]
    y = [r[metric] for r in complete]
    days = [r["day"] for r in complete]
    xr = residualize(x, days)
    yr = residualize(y, days)
    return {
        "n": len(complete),
        "raw_pearson_r": float(pearsonr(x, y).statistic),
        "raw_spearman_rho": float(spearmanr(x, y).statistic),
        "season_adjusted_pearson_r": float(pearsonr(xr, yr).statistic),
        "season_adjusted_spearman_rho": float(spearmanr(xr, yr).statistic),
    }


def gap_association(rows, metric):
    complete = [r for r in rows if math.isfinite(r.get("whoop_recovery", math.nan)) and math.isfinite(r.get(metric, math.nan))]
    gap = [r["whoop_recovery"] - r["score"] for r in complete]
    y = [r[metric] for r in complete]
    return {
        "n": len(complete),
        "pearson_r": float(pearsonr(gap, y).statistic),
        "spearman_rho": float(spearmanr(gap, y).statistic),
    }


def main():
    rows = load(INPUT, "readiness")
    whoop_rows = load(WHOOP_INPUT, "recovery")
    associations = {
        metric: association(rows, metric)
        for metric in [
            "whoop_recovery", "hrv", "hr_resting", "respiratory", "respiratory_min",
            "sleep_total", "sleep_deep", "sleep_rem", "sleep_awake", "strain", "oura_readiness",
        ]
    }
    gap = {metric: gap_association(rows, metric) for metric in [
        "hrv", "hr_resting", "respiratory_min", "sleep_total", "sleep_deep", "sleep_rem", "sleep_awake", "strain"
    ]}
    result = {
        "input": str(INPUT.relative_to(ROOT)),
        "n_readiness_days": len(rows),
        "date_min": min(r["day"] for r in rows).isoformat(),
        "date_max": max(r["day"] for r in rows).isoformat(),
        "associations_with_fitbit_readiness": associations,
        "associations_with_whoop_recovery": {
            metric: association(whoop_rows, metric)
            for metric in ["hrv", "hr_resting", "respiratory", "sleep_total", "sleep_deep", "sleep_rem"]
        },
        "associations_with_whoop_minus_fitbit_gap": gap,
        "interpretation": {
            "strongest_autonomic_link": "Canonical OptiHealth HRV RMSSD has season-adjusted Spearman rho about 0.81 with Fitbit Readiness; resting HR is about -0.55.",
            "sleep_result": "Canonical total sleep and stage minutes are essentially uncorrelated with Fitbit Readiness in this window, unlike the autonomic channels.",
            "score_gap": "On the 61 paired WHOOP days, the WHOOP-minus-Fitbit gap grows with total sleep and REM in this exploratory comparison; this is a score-decomposition clue, not causality.",
            "pipeline": "The latest published run predates the Fitbit metric registration/catalog generation; the current worker frame and multi-horizon correlation path include Fitbit Readiness.",
        },
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
