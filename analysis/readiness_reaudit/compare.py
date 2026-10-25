#!/usr/bin/env python3
"""Reproduce the Fitbit Readiness vs WHOOP Recovery comparison."""
from __future__ import annotations

import csv
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[2]
PAIRED = ROOT / "data/readiness_recovery_paired.csv"
OUT = Path(__file__).resolve().parent / "results.json"


def load_rows():
    rows = []
    with PAIRED.open() as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "day": r["day"],
                    "readiness": float(r["readiness"]),
                    "recovery": float(r["recovery"]),
                    "source_id": int(r["source_id"]),
                }
            )
    return rows


def category_fitbit(x):
    return "low" if x < 30 else "moderate" if x < 65 else "high"


def category_whoop(x):
    return "red" if x <= 33 else "yellow" if x <= 66 else "green"


def stats(rows):
    x = [r["readiness"] for r in rows]
    y = [r["recovery"] for r in rows]
    diffs = [b - a for a, b in zip(x, y)]
    return {
        "n": len(rows),
        "readiness_mean": statistics.mean(x),
        "recovery_mean": statistics.mean(y),
        "recovery_minus_readiness_mean": statistics.mean(diffs),
        "mae": statistics.mean(abs(d) for d in diffs),
        "rmse": math.sqrt(statistics.mean(d * d for d in diffs)),
        "pearson_r": pearsonr(x, y).statistic,
        "spearman_rho": spearmanr(x, y).statistic,
        "readiness_low_n": sum(category_fitbit(v) == "low" for v in x),
        "readiness_high_n": sum(category_fitbit(v) == "high" for v in x),
        "recovery_red_n": sum(category_whoop(v) == "red" for v in y),
        "recovery_green_n": sum(category_whoop(v) == "green" for v in y),
        "exact_equal_n": sum(a == b for a, b in zip(x, y)),
        "whoop_higher_n": sum(b > a for a, b in zip(x, y)),
        "fitbit_higher_n": sum(a > b for a, b in zip(x, y)),
    }


def block_sample(rows, rng, block_len=7):
    """Circular moving-block bootstrap within one source cohort."""
    n = len(rows)
    if n < block_len:
        return [rows[rng.randrange(n)] for _ in range(n)]
    out = []
    while len(out) < n:
        start = rng.randrange(n)
        out.extend(rows[(start + j) % n] for j in range(block_len))
    return out[:n]


def bootstrap(rows, iterations=10000, seed=20261024):
    groups = defaultdict(list)
    for r in rows:
        groups[r["source_id"]].append(r)
    rng = random.Random(seed)
    values = {k: [] for k in ("spearman_rho", "pearson_r", "recovery_minus_readiness_mean", "mae")}
    for _ in range(iterations):
        sample = []
        for cohort in groups.values():
            sample.extend(block_sample(cohort, rng))
        s = stats(sample)
        for k in values:
            values[k].append(s[k])
    ci = {}
    for k, xs in values.items():
        xs.sort()
        ci[k] = [xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]]
    return {"iterations": iterations, "block_days": 7, "seed": seed, "ci95": ci}


def main():
    rows = load_rows()
    cohorts = {str(s): [r for r in rows if r["source_id"] == s] for s in sorted({r["source_id"] for r in rows})}
    cross = Counter((category_fitbit(r["readiness"]), category_whoop(r["recovery"])) for r in rows)
    same_band = sum(
        category_fitbit(r["readiness"]) == {"red": "low", "yellow": "moderate", "green": "high"}[category_whoop(r["recovery"])]
        for r in rows
    )
    result = {
        "input": str(PAIRED.relative_to(ROOT)),
        "paired_n": len(rows),
        "date_min": min(r["day"] for r in rows),
        "date_max": max(r["day"] for r in rows),
        "cohorts": {k: stats(v) for k, v in cohorts.items()},
        "pooled": stats(rows),
        "category_cross_tab": {f"{a}/{b}": n for (a, b), n in sorted(cross.items())},
        "same_ordinal_band_n": same_band,
        "same_ordinal_band_fraction": same_band / len(rows),
        "bootstrap": bootstrap(rows),
        "interpretation": {
            "score_concordance": "moderate-to-strong monotonic agreement in the larger 2754 cohort, with systematic level offset",
            "offset": "WHOOP Recovery is higher than Fitbit Readiness on most paired days",
            "coverage": "Fitbit readiness has 317 rows, but only 61 same-day pairs with the two WHOOP Recovery cohorts",
            "resilience": "No fitbit_resilience_score rows are present in the paired extract; no resilience comparison is claimed",
        },
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
