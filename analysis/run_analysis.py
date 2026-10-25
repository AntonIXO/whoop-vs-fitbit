"""Whoop vs Fitbit agreement analysis — OptiHealth engine methods applied to paired tracker data.

Methods mirror /opt/optihealth_analysis:
  - serial.py        : circular block permutation p-values (block len = ceil(T^(1/3)))
  - feed_policy.py   : BH-FDR over the whole family, alpha = q <= 0.10
  - composition gate : stage minutes are shares of the night -> analyse TST + shares, not raw stages
  - verdicts/power   : MDE in SD units from effective n
No i.i.d. analytic p anywhere: every daily series is autocorrelated.
"""
from __future__ import annotations

import csv
import math
import sys

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/opt/optihealth_analysis/src")
from analysis.serial import default_block_len  # noqa: E402
from analysis.serial import block_permutation_p  # noqa: E402

DATA = "/opt/article-fitbit-vs-whoop/data"


def load(name: str) -> list[dict]:
    with open(f"{DATA}/{name}.csv") as f:
        return list(csv.DictReader(f))


def fnum(rows, key):
    return np.array([float(r[key]) for r in rows if r.get(key) not in (None, "")])


def mde_sd(n: int, alpha=0.05, power=0.80) -> float:
    """Minimum detectable effect in SD units (verdicts.silent_family_record)."""
    from scipy.stats import norm
    return (norm.ppf(1 - alpha / 2) + norm.ppf(power)) / math.sqrt(n)


def bh_qvalues(pvals: list[float]) -> np.ndarray:
    """Benjamini-Hochberg step-up q-values (feed_policy)."""
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    ranked = p[order]
    m = len(p)
    q = ranked * m / (np.arange(m) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.clip(q, 0, 1)
    return out


def pair_test(x, y, label, family):
    """Spearman rho + circular block permutation p, appended to the FDR family."""
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    n = len(x)
    if n < 20:
        return None
    rho, _ = spearmanr(x, y)
    ell = default_block_len(n)
    p = block_permutation_p(x, y, method="spearman")
    bias = float(np.median(y - x))
    mad = float(np.median(np.abs(y - x)))
    entry = dict(label=label, n=n, rho=float(rho), p=float(p), block_len=ell,
                 bias=bias, mad=mad, mde_sd=mde_sd(n),
                 pct_bias=float(bias / np.mean(x) * 100) if np.mean(x) else float("nan"))
    family.append(entry)
    return entry


def main():
    family: list[dict] = []
    results: dict[str, dict] = {}

    # ---- Sleep, P1 staged nights only (68) ----------------------------------
    s1 = [r for r in load("sleep_paired_staged") if r["period"] == "P1"]
    for fx, wx, lab in [
        ("f_tst", "w_tst", "P1 sleep: total sleep time"),
        ("f_tib", "w_tib", "P1 sleep: time in bed"),
        ("f_deep", "w_deep", "P1 sleep: deep minutes (raw)"),
        ("f_rem", "w_rem", "P1 sleep: REM minutes (raw)"),
    ]:
        results[lab] = pair_test(fnum(s1, fx), fnum(s1, wx), lab, family)

    # Composition gate: deep and REM as SHARES of the night
    tst_f = fnum(s1, "f_tst"); tst_w = fnum(s1, "w_tst")
    share_ok = (tst_f > 60) & (tst_w > 60)
    results["P1 sleep: deep SHARE"] = pair_test(
        fnum(s1, "f_deep")[share_ok] / tst_f[share_ok],
        fnum(s1, "w_deep")[share_ok] / tst_w[share_ok],
        "P1 sleep: deep SHARE", family)
    results["P1 sleep: REM SHARE"] = pair_test(
        fnum(s1, "f_rem")[share_ok] / tst_f[share_ok],
        fnum(s1, "w_rem")[share_ok] / tst_w[share_ok],
        "P1 sleep: REM SHARE", family)

    # onset difference is a paired one-sample question: blocked sign permutation
    onsets = fnum([r for r in load("sleep_paired") if r["period"] == "P1"], "onset_diff_min")

    def blocked_sign_perm(vals, n_perm=2000, seed=7):
        rng = np.random.default_rng(seed)
        n = len(vals); ell = default_block_len(n)
        blocks = [np.arange(i, min(i + ell, n)) for i in range(0, n, ell)]
        obs = abs(np.mean(vals))
        cnt = 0
        for _ in range(n_perm):
            signs = rng.choice([-1.0, 1.0], size=len(blocks))
            perm = np.concatenate([b * s for b, s in zip(blocks, signs)])
            if abs(np.mean(perm)) >= obs:
                cnt += 1
        return (cnt + 1) / (n_perm + 1)

    p_onset = blocked_sign_perm(onsets)
    family.append(dict(label="P1 sleep: onset offset (whoop later)", n=len(onsets),
                       rho=float("nan"), p=p_onset, block_len=default_block_len(len(onsets)),
                       bias=float(np.mean(onsets)), mad=float(np.median(np.abs(onsets))),
                       mde_sd=mde_sd(len(onsets)), pct_bias=float("nan")))
    results["P1 sleep: onset offset (whoop later)"] = family[-1]

    # ---- P2 (small, descriptive only; below min_points for some metrics) -----
    s2 = [r for r in load("sleep_paired_staged") if r["period"] == "P2"]
    results["P2 sleep: total sleep time (n<20, descriptive)"] = {
        "n": len(s2), "note": "below min_data_points=20 -> no test",
        "fb_tst": float(np.mean([float(r["f_tst"]) for r in s2])),
        "wh_tst": float(np.mean([float(r["w_tst"]) for r in s2])),
        "fb_deep": float(np.mean([float(r["f_deep"]) for r in s2])),
        "wh_deep": float(np.mean([float(r["w_deep"]) for r in s2]))}

    # ---- Resting HR ----------------------------------------------------------
    rhr = load("rhr_paired")
    r1 = [r for r in rhr if r["period"] == "P1"]; r2 = [r for r in rhr if r["period"] == "P2"]
    results["P1 resting HR"] = pair_test(fnum(r1, "f_rhr"), fnum(r1, "w_rhr"), "P1 resting HR", family)
    results["P2 resting HR (descriptive)"] = {"n": len(r2), "note": "n<20 -> no test"}

    # ---- Steps ----------------------------------------------------------------
    st = load("steps_paired")
    results["Steps (May 2026)"] = pair_test(fnum(st, "f_steps"), fnum(st, "w_steps"), "Steps (May 2026)", family)

    # ---- Strain vs kcal, Recovery vs RHR --------------------------------------
    sk = load("strain_kcal")
    results["Strain vs total kcal"] = pair_test(fnum(sk, "kcal"), fnum(sk, "strain"), "Strain vs total kcal", family)
    rr = load("recovery_rhr")
    results["Recovery vs resting HR"] = pair_test(fnum(rr, "rhr"), fnum(rr, "recovery"), "Recovery vs resting HR", family)

    # ---- FDR across the family -------------------------------------------------
    qs = bh_qvalues([e["p"] for e in family])
    for e, q in zip(family, qs):
        e["q"] = round(float(q), 4)
        e["survives_fdr"] = bool(q <= 0.10)

    print(f"{'test':44s} {'n':>4} {'rho':>7} {'p':>9} {'q':>8} {'FDR':>4} "
          f"{'bias':>8} {'MAD':>7} {'blk':>3}")
    for e in sorted(family, key=lambda d: d["q"]):
        rho = f"{e['rho']:.3f}" if math.isfinite(e["rho"]) else "  --"
        print(f"{e['label']:44s} {e['n']:>4} {rho:>7} {e['p']:>9.5f} {e['q']:>8.4f} "
              f"{'PASS' if e['survives_fdr'] else 'fail':>4} {e['bias']:>8.1f} {e['mad']:>7.1f} {e['block_len']:>3}")

    print("\nMDE (SD units, alpha=.05, power=.80):", {e["label"]: round(e["mde_sd"], 2) for e in family})
    print("\nP2 descriptive:", results["P2 sleep: total sleep time (n<20, descriptive)"])

    import json
    with open("/opt/article-fitbit-vs-whoop/analysis/results.json", "w") as f:
        json.dump({"family": family, "results": results}, f, indent=2, default=str)
    print("\nwrote analysis/results.json")


if __name__ == "__main__":
    main()
