"""Phase 2: which device's sleep numbers carry INFORMATION, and what drives disagreement.

Without PSG we cannot say who is "right". But we can ask criterion-free questions
that the validation literature cannot answer from single-night lab studies:

  Q1 CONVERGENT VALIDITY. Each device's deep-sleep estimate should track the
     physiology deep sleep is supposed to reflect (nocturnal HRV, HR nadir).
     A number that correlates with nothing external is a number carrying no
     information, whoever's algorithm produced it.

  Q2 PREDICTIVE VALIDITY. Which device's night better predicts NEXT-DAY resting
     HR / recovery? Nested horizons, one FDR family.

  Q3 WHAT DRIVES THE DISAGREEMENT. Model d = deep_whoop - deep_fitbit against
     night characteristics. If d is a random measurement error it correlates
     with nothing; if it is a systematic algorithmic divergence it will track
     specific night features.

  Q4 DECOMPOSITION. Is the +28 min a genuine stage reassignment or a boundary
     artifact (WHOOP counting a longer night)? Composition-gate logic.

  Q5 RELIABILITY CEILING. What is the maximum correlation ANY downstream finding
     using deep sleep can have, given the two devices only agree at rho=0.52?

Methods identical to the engine: block-permutation p, BH-FDR over one family.
"""
from __future__ import annotations

import csv
import json
import math
import sys

import numpy as np
from scipy.stats import spearmanr, norm

sys.path.insert(0, "/opt/optihealth_analysis/src")
from analysis.serial import block_permutation_p, default_block_len  # noqa: E402

DATA = "/opt/article-fitbit-vs-whoop/data"


def load_wide():
    with open(f"{DATA}/nightly_wide.csv") as f:
        rows = list(csv.DictReader(f))
    cols: dict[str, np.ndarray] = {}
    for k in rows[0]:
        if k == "day":
            cols[k] = np.array([r[k] for r in rows], dtype=object)
        else:
            cols[k] = np.array([float(r[k]) if r[k] not in ("", None) else np.nan for r in rows])
    return cols


FAMILY: list[dict] = []


def test(x, y, label, group):
    m = np.isfinite(x) & np.isfinite(y)
    xx, yy = x[m], y[m]
    n = len(xx)
    if n < 20 or np.std(xx) == 0 or np.std(yy) == 0:
        FAMILY.append(dict(label=label, group=group, n=n, rho=np.nan, p=np.nan,
                           skipped="n<20 or constant"))
        return None
    rho, _ = spearmanr(xx, yy)
    p = block_permutation_p(xx, yy, method="spearman")
    e = dict(label=label, group=group, n=n, rho=float(rho), p=float(p),
             block_len=default_block_len(n))
    FAMILY.append(e)
    return e


def bh(pv):
    p = np.asarray(pv, float)
    ok = np.isfinite(p)
    q = np.full_like(p, np.nan)
    pp = p[ok]
    order = np.argsort(pp)
    ranked = pp[order]
    m = len(pp)
    qq = ranked * m / (np.arange(m) + 1)
    qq = np.minimum.accumulate(qq[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.clip(qq, 0, 1)
    q[ok] = out
    return q


def partial_spearman(x, y, z, n_perm=2000):
    """Rank-residualised partial correlation, engine style (partial_correlation.py)."""
    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    if m.sum() < 20:
        return None, None, int(m.sum())
    from scipy.stats import rankdata, pearsonr
    rx, ry, rz = rankdata(x[m]), rankdata(y[m]), rankdata(z[m])
    Z = np.c_[np.ones(len(rz)), rz]
    res = lambda v: v - Z @ np.linalg.lstsq(Z, v, rcond=None)[0]
    ra, rb = res(rx), res(ry)
    if np.std(ra) == 0 or np.std(rb) == 0:
        return None, None, int(m.sum())
    r, _ = pearsonr(ra, rb)
    p = block_permutation_p(ra, rb, n_perm=n_perm, method="pearson")
    return float(r), float(p), int(m.sum())


def main():
    c = load_wide()
    out: dict = {}

    # =====================================================================
    # Q1 CONVERGENT VALIDITY: does each device's deep sleep track physiology?
    # =====================================================================
    for dev, col in [("Fitbit", "f_deep"), ("WHOOP", "w_deep")]:
        test(c[col], c["hrv_night"], f"Q1 {dev} deep vs nocturnal HRV", "convergent")
        test(c[col], c["hr_night_min"], f"Q1 {dev} deep vs HR nadir", "convergent")
        test(c[col], c["hr_night"], f"Q1 {dev} deep vs mean night HR", "convergent")
        test(c[col], c["spo2_sd"], f"Q1 {dev} deep vs SpO2 instability", "convergent")
    # same for REM and TST as a control: TST should track physiology WEAKLY
    for dev, col in [("Fitbit", "f_rem"), ("WHOOP", "w_rem")]:
        test(c[col], c["hrv_night"], f"Q1 {dev} REM vs nocturnal HRV", "convergent")
    for dev, col in [("Fitbit", "f_tst"), ("WHOOP", "w_tst")]:
        test(c[col], c["hrv_night"], f"Q1 {dev} TST vs nocturnal HRV", "convergent")

    # =====================================================================
    # Q2 PREDICTIVE VALIDITY: next-day outcomes
    # =====================================================================
    for dev, col in [("Fitbit", "f_deep"), ("WHOOP", "w_deep")]:
        test(c[col], c["f_rhr_next"], f"Q2 {dev} deep -> next-day RHR", "predictive")
        test(c[col], c["w_recovery_next"], f"Q2 {dev} deep -> next-day Recovery", "predictive")
        test(c[col], c["f_steps_next"], f"Q2 {dev} deep -> next-day steps", "predictive")
    for dev, col in [("Fitbit", "f_tst"), ("WHOOP", "w_tst")]:
        test(c[col], c["f_rhr_next"], f"Q2 {dev} TST -> next-day RHR", "predictive")
        test(c[col], c["w_recovery_next"], f"Q2 {dev} TST -> next-day Recovery", "predictive")

    # =====================================================================
    # Q3 WHAT DRIVES THE DISAGREEMENT
    # =====================================================================
    d_deep = c["w_deep"] - c["f_deep"]
    d_tst = c["w_tst"] - c["f_tst"]
    for name, v in [
        ("bedtime hour", c["bedtime_h"]),
        ("time in bed (Fitbit)", c["f_tib"]),
        ("Fitbit awakenings", c["f_awakenings"]),
        ("Fitbit efficiency", c["f_eff"]),
        ("onset offset (min)", c["onset_diff"]),
        ("nocturnal HRV", c["hrv_night"]),
        ("mean night HR", c["hr_night"]),
        ("prior-day steps", c["f_steps"]),
        ("prior-day strain", c["w_strain"]),
        ("TST disagreement", d_tst),
    ]:
        test(d_deep, v, f"Q3 deep-sleep gap vs {name}", "disagreement")

    # =====================================================================
    # Q4 DECOMPOSITION: is the deep gap explained by the TST gap?
    # =====================================================================
    r_raw, p_raw, n_raw = partial_spearman(c["w_deep"], c["f_deep"], np.zeros_like(c["f_deep"]) + 1) \
        if False else (None, None, 0)
    r_pc, p_pc, n_pc = partial_spearman(d_deep, c["bedtime_h"], d_tst)
    out["Q4_partial_gap_vs_bedtime_controlling_TSTgap"] = dict(r=r_pc, p=p_pc, n=n_pc)

    # share-based restatement
    m = np.isfinite(c["f_deep"]) & np.isfinite(c["w_deep"]) & (c["f_tst"] > 60) & (c["w_tst"] > 60)
    f_share = c["f_deep"][m] / c["f_tst"][m]
    w_share = c["w_deep"][m] / c["w_tst"][m]
    out["Q4_deep_share"] = dict(
        fitbit_mean_pct=round(float(f_share.mean() * 100), 2),
        whoop_mean_pct=round(float(w_share.mean() * 100), 2),
        share_gap_pp=round(float((w_share - f_share).mean() * 100), 2),
        minutes_gap=round(float(np.nanmean(d_deep)), 2),
        # how much of the minute gap is attributable to TST difference?
        gap_if_only_duration=round(float(np.nanmean(f_share) * np.nanmean(c["w_tst"] - c["f_tst"])), 2),
    )

    # =====================================================================
    # Q5 RELIABILITY CEILING (attenuation)
    # =====================================================================
    # Treat the two devices as parallel measures of latent deep sleep.
    # Spearman-Brown / classical attenuation: an observed correlation between a
    # device's deep sleep and any true outcome is bounded by sqrt(reliability).
    rho_dd, _ = spearmanr(*[a[np.isfinite(c["f_deep"]) & np.isfinite(c["w_deep"])]
                            for a in (c["f_deep"], c["w_deep"])])
    out["Q5_reliability"] = dict(
        inter_device_rho=round(float(rho_dd), 3),
        max_observable_rho=round(float(math.sqrt(max(rho_dd, 0))), 3),
        note=("Any correlation between a single device's deep sleep and a true outcome "
              "is attenuated by sqrt(reliability). With rho_dd as the reliability proxy, "
              "no downstream deep-sleep finding on ONE device can exceed this."),
    )
    # what n would you need to detect the max observable rho?
    r_max = math.sqrt(max(rho_dd, 0))
    for target in (0.3, 0.5):
        z = 0.5 * math.log((1 + target) / (1 - target))
        n_need = int(math.ceil(((norm.ppf(0.975) + norm.ppf(0.8)) / z) ** 2 + 3))
        out.setdefault("Q5_n_required", {})[f"rho={target}"] = n_need

    # =====================================================================
    # FDR over the whole family
    # =====================================================================
    qs = bh([e.get("p", np.nan) for e in FAMILY])
    for e, q in zip(FAMILY, qs):
        e["q"] = None if not np.isfinite(q) else round(float(q), 4)
        e["survives"] = bool(np.isfinite(q) and q <= 0.10)

    print(f"family size m = {sum(1 for e in FAMILY if np.isfinite(e.get('p', np.nan)))}\n")
    for grp in ("convergent", "predictive", "disagreement"):
        print(f"--- {grp.upper()} " + "-" * (58 - len(grp)))
        rows = [e for e in FAMILY if e["group"] == grp]
        for e in sorted(rows, key=lambda d: (d["q"] is None, d["q"] if d["q"] is not None else 9)):
            if not np.isfinite(e.get("p", np.nan)):
                print(f"  {e['label']:48s} n={e['n']:<3} SKIPPED ({e.get('skipped')})")
                continue
            flag = "PASS" if e["survives"] else "    "
            print(f"  {e['label']:48s} n={e['n']:<3} rho={e['rho']:+.3f} "
                  f"p={e['p']:.4f} q={e['q']:.4f} {flag}")
        print()

    print("Q4 decomposition:", json.dumps(out["Q4_deep_share"], indent=2))
    print("Q4 gap vs bedtime | TST-gap controlled:", out["Q4_partial_gap_vs_bedtime_controlling_TSTgap"])
    print("Q5:", json.dumps(out["Q5_reliability"], indent=2))
    print("Q5 n required:", out["Q5_n_required"])

    with open("/opt/article-fitbit-vs-whoop/analysis/results_phase2.json", "w") as f:
        json.dump({"family": FAMILY, "derived": out}, f, indent=2, default=str)
    print("\nwrote analysis/results_phase2.json")


if __name__ == "__main__":
    main()
