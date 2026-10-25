"""Phase 4: does a LAB PSG bias predict a FREE-LIVING device-vs-device gap?

Schyvens et al. 2025 (SLEEP Advances 6(2):zpaf021, n=62, single-night in-lab PSG)
reports each device's bias against PSG. If those biases are real device
properties rather than lab artifacts, they should be ADDITIVE and predict the
gap between the two devices worn simultaneously in the wild:

    E[whoop - fitbit] = bias_whoop(PSG) - bias_fitbit(PSG)

That is a falsifiable, pre-specified prediction with no free parameters, and it
is testable ONLY with simultaneous paired wear. Nobody can run it from a lab
study, because lab studies rarely wear two devices for 68 nights.

We test it with a bootstrap CI on our observed gap and ask whether the
literature-predicted value falls inside.

Literature values (Schyvens 2025, Table 12 + Bland-Altman table):
    WHOOP 4.0      N3 +31.49 min   REM +15.28   TST +24.46
    Fitbit Charge5 N3  -2.19 min   REM  -0.24   TST +11.12
    Fitbit Sense   N3  -3.89 min   REM  +2.86   TST  +6.31
Anton wore a Charge 6 (not in that study); Charge 5 is the nearest validated
sibling and the two Fitbit models agree with each other closely there.
"""
from __future__ import annotations

import csv
import json

import numpy as np

DATA = "/opt/article-fitbit-vs-whoop/data"

LIT = {
    "deep": {"whoop": 31.49, "fitbit_c5": -2.19, "fitbit_sense": -3.89},
    "rem":  {"whoop": 15.28, "fitbit_c5": -0.24, "fitbit_sense": 2.86},
    "tst":  {"whoop": 24.46, "fitbit_c5": 11.12, "fitbit_sense": 6.31},
}
CITE = "Schyvens et al. 2025, SLEEP Advances 6(2):zpaf021, n=62 in-lab PSG"


def load():
    with open(f"{DATA}/nightly_wide.csv") as f:
        rows = list(csv.DictReader(f))
    g = lambda k: np.array([float(r[k]) if r[k] else np.nan for r in rows])
    return g


def boot_ci(v, n_boot=20000, seed=11):
    """Moving-block bootstrap CI of the mean (engine style: preserve serial dep)."""
    rng = np.random.default_rng(seed)
    v = v[np.isfinite(v)]
    n = len(v)
    ell = max(int(np.ceil(n ** (1 / 3))), 2)
    n_blocks = int(np.ceil(n / ell))
    starts_max = n - ell
    means = np.empty(n_boot)
    for b in range(n_boot):
        st = rng.integers(0, starts_max + 1, size=n_blocks)
        idx = (st[:, None] + np.arange(ell)[None, :]).ravel()[:n]
        means[b] = v[idx].mean()
    return float(np.mean(v)), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main():
    g = load()
    out = {"citation": CITE, "tests": {}}

    for key, (wcol, fcol) in {
        "deep": ("w_deep", "f_deep"),
        "rem": ("w_rem", "f_rem"),
        "tst": ("w_tst", "f_tst"),
    }.items():
        gap = g(wcol) - g(fcol)
        obs, lo, hi = boot_ci(gap)
        pred_c5 = LIT[key]["whoop"] - LIT[key]["fitbit_c5"]
        pred_sense = LIT[key]["whoop"] - LIT[key]["fitbit_sense"]
        out["tests"][key] = dict(
            n=int(np.isfinite(gap).sum()),
            observed_gap_min=round(obs, 2),
            ci95=[round(lo, 2), round(hi, 2)],
            predicted_from_lab_charge5=round(pred_c5, 2),
            predicted_from_lab_sense=round(pred_sense, 2),
            charge5_prediction_inside_ci=bool(lo <= pred_c5 <= hi),
            sense_prediction_inside_ci=bool(lo <= pred_sense <= hi),
            residual_vs_charge5=round(obs - pred_c5, 2),
        )

    # How much of the deep gap is a REASSIGNMENT vs extra sleep?
    # If WHOOP simply records a longer night, the extra deep minutes should be
    # proportional to the extra total minutes at Fitbit's own deep share.
    f_deep, w_deep = g("f_deep"), g("w_deep")
    f_tst, w_tst = g("f_tst"), g("w_tst")
    m = np.isfinite(f_deep) & np.isfinite(w_deep) & (f_tst > 60) & (w_tst > 60)
    share_f = (f_deep[m] / f_tst[m]).mean()
    duration_component = share_f * (w_tst[m] - f_tst[m]).mean()
    total_gap = (w_deep[m] - f_deep[m]).mean()
    out["decomposition"] = dict(
        n=int(m.sum()),
        total_deep_gap_min=round(float(total_gap), 2),
        explained_by_longer_night_min=round(float(duration_component), 2),
        reassignment_min=round(float(total_gap - duration_component), 2),
        pct_reassignment=round(float((total_gap - duration_component) / total_gap * 100), 1),
        note=("WHOOP records a SHORTER night here, so duration explains a negative "
              "amount: 100%+ of the deep-sleep gap is stage REASSIGNMENT, not extra sleep."),
    )

    # Literature context on the reliability ceiling
    out["kappa_context"] = dict(
        whoop4_kappa=0.37, fitbit_charge5_kappa=0.41, fitbit_sense_kappa=0.42,
        apple_watch8_kappa=0.53,
        interpretation=("4-stage kappa 0.37-0.42 is 'fair' agreement with PSG. Two "
                        "devices each at kappa~0.4 against truth CANNOT agree with "
                        "each other better than that, which is what our rho=0.52 on "
                        "deep sleep shows from the other direction."),
        source=CITE,
    )

    print(json.dumps(out, indent=2))
    with open("/opt/article-fitbit-vs-whoop/analysis/results_phase4.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\nwrote analysis/results_phase4.json")


if __name__ == "__main__":
    main()
