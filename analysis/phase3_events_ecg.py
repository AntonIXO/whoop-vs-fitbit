"""Phase 3: workout-detection disagreement + ECG as an independent criterion.

Two questions the agreement literature almost never asks:

  Q6 EVENT DETECTION. Before you can disagree about a workout's numbers, you
     have to agree it happened. Count sessions per day per device.
     This is an ONTOLOGY disagreement, not a measurement error, and it
     propagates into every "active minutes" / "strain" / "calorie" claim.

  Q7 ECG CRITERION. A single-lead ECG measures RR intervals directly, so it is
     an INDEPENDENT instrument, not a third PPG opinion. Which device's
     resting HR tracks the ECG-derived BPM?
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict

import numpy as np
from scipy.stats import spearmanr, wilcoxon

sys.path.insert(0, "/opt/optihealth_analysis/src")
from analysis.serial import block_permutation_p  # noqa: E402

DATA = "/opt/article-fitbit-vs-whoop/data"
FB = "google_health:6302349631570837559"
WH = "whoop:31695515"


def rows(name):
    with open(f"{DATA}/{name}.csv") as f:
        return list(csv.DictReader(f))


def num(v):
    return float(v) if v not in ("", None) else np.nan


def main():
    out = {}

    # ================= Q6 WORKOUT DETECTION =================
    per_day = defaultdict(dict)
    for r in rows("workouts_by_source"):
        if r["source_identifier"] in (FB, WH):
            per_day[r["day"]][r["source_identifier"]] = r

    both = {d: v for d, v in per_day.items() if FB in v and WH in v}
    fb_n = np.array([int(v[FB]["n"]) for v in both.values()])
    wh_n = np.array([int(v[WH]["n"]) for v in both.values()])
    fb_min = np.array([num(v[FB]["min"]) for v in both.values()])
    wh_min = np.array([num(v[WH]["min"]) for v in both.values()])
    fb_kcal = np.array([num(v[FB]["kcal"]) for v in both.values()])
    wh_kcal = np.array([num(v[WH]["kcal"]) for v in both.values()])

    only_fb = sum(1 for v in per_day.values() if FB in v and WH not in v)
    only_wh = sum(1 for v in per_day.values() if WH in v and FB not in v)

    rho_n, _ = spearmanr(fb_n, wh_n)
    p_n = block_permutation_p(fb_n.astype(float), wh_n.astype(float), method="spearman")
    w_stat, w_p = wilcoxon(fb_n, wh_n)

    m = np.isfinite(fb_min) & np.isfinite(wh_min)
    rho_min, _ = spearmanr(fb_min[m], wh_min[m])
    p_min = block_permutation_p(fb_min[m], wh_min[m], method="spearman")

    mk = np.isfinite(fb_kcal) & np.isfinite(wh_kcal)
    rho_kcal, _ = spearmanr(fb_kcal[mk], wh_kcal[mk])
    p_kcal = block_permutation_p(fb_kcal[mk], wh_kcal[mk], method="spearman")

    out["Q6_workout_detection"] = dict(
        days_both_logged=len(both),
        days_only_fitbit=only_fb, days_only_whoop=only_wh,
        fitbit_sessions_per_day=round(float(fb_n.mean()), 2),
        whoop_sessions_per_day=round(float(wh_n.mean()), 2),
        fitbit_total_sessions=int(fb_n.sum()), whoop_total_sessions=int(wh_n.sum()),
        ratio=round(float(fb_n.sum() / wh_n.sum()), 2),
        session_count_rho=round(float(rho_n), 3), session_count_p=round(float(p_n), 5),
        wilcoxon_p=float(w_p),
        active_minutes_fitbit=round(float(np.nanmean(fb_min)), 1),
        active_minutes_whoop=round(float(np.nanmean(wh_min)), 1),
        active_minutes_rho=round(float(rho_min), 3), active_minutes_p=round(float(p_min), 5),
        n_minutes=int(m.sum()),
        kcal_fitbit=round(float(np.nanmean(fb_kcal)), 0),
        kcal_whoop=round(float(np.nanmean(wh_kcal)), 0),
        kcal_rho=round(float(rho_kcal), 3), kcal_p=round(float(p_kcal), 5), n_kcal=int(mk.sum()),
    )

    # ================= Q7 ECG CRITERION =================
    ecg = rows("ecg_paired")
    # keep the RESTING-like readings: exclude obvious post-exercise spikes and
    # low-quality traces (engine rule: artifact fraction gates HRV, not BPM)
    e_bpm = np.array([num(r["derived_bpm"]) for r in ecg])
    e_prov = np.array([num(r["provider_bpm"]) for r in ecg])
    e_rmssd = np.array([num(r["rmssd_ms"]) for r in ecg])
    e_art = np.array([num(r["rr_artifact_fraction"]) for r in ecg])
    f_rhr = np.array([num(r["f_rhr"]) for r in ecg])
    w_rhr = np.array([num(r["w_rhr"]) for r in ecg])
    w_rec = np.array([num(r["w_recovery"]) for r in ecg])

    # sanity: our own R-peak detector vs the provider's own BPM label
    ok = np.isfinite(e_bpm) & np.isfinite(e_prov)
    out["Q7_ecg_selfcheck"] = dict(
        n=int(ok.sum()),
        mean_abs_error_bpm=round(float(np.mean(np.abs(e_bpm[ok] - e_prov[ok]))), 3),
        note="our derived BPM vs the device's own ECG BPM label — validates the pipeline",
    )

    # resting-like subset: drop the one clear exercise reading (99 bpm)
    rest = e_bpm < 70
    res = {}
    for dev, arr in (("Fitbit", f_rhr), ("WHOOP", w_rhr)):
        mm = rest & np.isfinite(arr) & np.isfinite(e_bpm)
        n = int(mm.sum())
        if n >= 5:
            rho, p = spearmanr(e_bpm[mm], arr[mm])
            res[dev] = dict(n=n, rho=round(float(rho), 3), p_iid=round(float(p), 4),
                            mean_ecg=round(float(e_bpm[mm].mean()), 1),
                            mean_device=round(float(arr[mm].mean()), 1),
                            bias=round(float((arr[mm] - e_bpm[mm]).mean()), 1))
        else:
            res[dev] = dict(n=n, note="too few paired readings")
    out["Q7_rhr_vs_ecg"] = res

    mm = rest & np.isfinite(e_rmssd) & np.isfinite(w_rec) & (e_art < 0.2)
    if mm.sum() >= 5:
        rho, p = spearmanr(e_rmssd[mm], w_rec[mm])
        out["Q7_ecg_rmssd_vs_whoop_recovery"] = dict(
            n=int(mm.sum()), rho=round(float(rho), 3), p_iid=round(float(p), 4),
            note="ECG spot RMSSD is a WAKING measure; WHOOP Recovery is built on "
                 "NOCTURNAL HRV. Engine rule: never pool the two. Reported as "
                 "descriptive only.")
    else:
        out["Q7_ecg_rmssd_vs_whoop_recovery"] = dict(n=int(mm.sum()), note="underpowered")

    print(json.dumps(out, indent=2))
    with open("/opt/article-fitbit-vs-whoop/analysis/results_phase3.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    print("\nwrote analysis/results_phase3.json")


if __name__ == "__main__":
    main()
