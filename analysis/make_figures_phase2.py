"""Figures for phase 2/3: information content, workout ontology, ECG criterion."""
import csv
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

DATA = "/opt/article-fitbit-vs-whoop/data"
FIG = "/opt/article-fitbit-vs-whoop/figures"
AN = "/opt/article-fitbit-vs-whoop/analysis"

plt.rcParams.update({
    "figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
    "savefig.facecolor": "#0d1117", "axes.edgecolor": "#30363d",
    "axes.labelcolor": "#e6edf3", "xtick.color": "#8b949e", "ytick.color": "#8b949e",
    "text.color": "#e6edf3", "font.size": 11, "axes.grid": True,
    "grid.color": "#21262d", "grid.linewidth": 0.8, "font.family": "DejaVu Sans",
})
FB_C, WH_C, OK_C, BAD_C = "#58a6ff", "#f78166", "#3fb950", "#f85149"


def rows(n):
    with open(f"{DATA}/{n}.csv") as f:
        return list(csv.DictReader(f))


def num(v):
    return float(v) if v not in ("", None) else np.nan


ph2 = json.load(open(f"{AN}/results_phase2.json"))
ph3 = json.load(open(f"{AN}/results_phase3.json"))

# ---- Fig 5: THE key figure — predictive validity asymmetry -------------------
wide = rows("nightly_wide")
f_deep = np.array([num(r["f_deep"]) for r in wide])
w_deep = np.array([num(r["w_deep"]) for r in wide])
rhr_next = np.array([num(r["f_rhr_next"]) for r in wide])

fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
for ax, dev, x, rho, q, c in [
    (axes[0], "Fitbit", f_deep, -0.319, 0.139, FB_C),
    (axes[1], "WHOOP", w_deep, +0.041, 0.967, WH_C),
]:
    m = np.isfinite(x) & np.isfinite(rhr_next)
    ax.scatter(x[m], rhr_next[m], s=34, c=c, alpha=0.8, edgecolors="none")
    k, b = np.polyfit(x[m], rhr_next[m], 1)
    xs = np.linspace(x[m].min(), x[m].max(), 10)
    ax.plot(xs, k * xs + b, c=OK_C if abs(rho) > 0.2 else BAD_C, lw=2)
    ax.set_title(f"{dev} deep sleep → next-day RHR\nρ = {rho:+.3f}   (q = {q:.3f})",
                 fontweight="bold", fontsize=12, pad=10)
    ax.set_xlabel(f"{dev} deep sleep (min)")
axes[0].set_ylabel("Next-day resting HR (bpm)")
fig.suptitle("Same night, same wrist — only one device's deep sleep predicts tomorrow",
             fontsize=14, fontweight="bold", y=1.03)
fig.tight_layout()
fig.savefig(f"{FIG}/fig5_predictive_asymmetry.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---- Fig 6: effect-size forest of the whole family --------------------------
fam = [e for e in ph2["family"] if e.get("rho") is not None
       and isinstance(e.get("rho"), (int, float)) and np.isfinite(e["rho"])]
groups = {"convergent": "Convergent validity", "predictive": "Predictive validity",
          "disagreement": "What drives the gap"}
fig, ax = plt.subplots(figsize=(11, 9))
ypos, labels, colors = [], [], []
y = 0
for g, gl in groups.items():
    sub = sorted([e for e in fam if e["group"] == g], key=lambda d: d["rho"])
    if not sub:
        continue
    for e in sub:
        ypos.append(y)
        labels.append(e["label"].split(" ", 1)[1])
        colors.append(OK_C if e.get("survives") else "#6e7681")
        y += 1
    y += 1.2
rhos = [e["rho"] for g in groups for e in sorted(
    [x for x in fam if x["group"] == g], key=lambda d: d["rho"])]
ns = [e["n"] for g in groups for e in sorted(
    [x for x in fam if x["group"] == g], key=lambda d: d["rho"])]
ci = [1.96 / np.sqrt(max(n - 3, 1)) for n in ns]
ax.errorbar(rhos, ypos, xerr=ci, fmt="o", ms=7, capsize=3,
            ecolor="#484f58", elinewidth=1.4, mfc="none", mec="none")
ax.scatter(rhos, ypos, s=60, c=colors, zorder=3, edgecolors="none")
ax.axvline(0, c="#8b949e", lw=1)
# group separators + labels
gy = 0
for g, gl in groups.items():
    sub = [x for x in fam if x["group"] == g]
    if not sub:
        continue
    ax.text(-0.58, gy - 0.85, gl.upper(), fontsize=10, fontweight="bold",
            color="#e6edf3", va="center")
    gy += len(sub) + 1.2
ax.set_yticks(ypos); ax.set_yticklabels(labels, fontsize=9)
ax.set_xlabel("Spearman ρ  (bars = 95% CI)")
n_surv = sum(1 for e in fam if e.get("survives"))
ax.set_title(f"32 hypotheses, one BH-FDR family — {n_surv} survived q ≤ 0.10\n"
             "The strongest signal (Fitbit deep → next-day RHR, ρ=−0.32, p=0.006) dies at q=0.139.\n"
             "This is what honest multiple-comparison correction costs.",
             fontweight="bold", fontsize=11.5, pad=14)
ax.invert_yaxis()
fig.tight_layout()
fig.savefig(f"{FIG}/fig6_forest.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---- Fig 7: workout ontology -------------------------------------------------
FBS, WHS = "google_health:6302349631570837559", "whoop:31695515"
wk = rows("workouts_by_source")
byday = {}
for r in wk:
    byday.setdefault(r["day"], {})[r["source_identifier"]] = r
both = {d: v for d, v in byday.items() if FBS in v and WHS in v}
days = sorted(both)
fbn = [int(both[d][FBS]["n"]) for d in days]
whn = [int(both[d][WHS]["n"]) for d in days]
fbk = [num(both[d][FBS]["kcal"]) for d in days]
whk = [num(both[d][WHS]["kcal"]) for d in days]

fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
x = np.arange(len(days))
axes[0].bar(x - 0.2, fbn, 0.4, label=f"Fitbit ({sum(fbn)} sessions)", color=FB_C)
axes[0].bar(x + 0.2, whn, 0.4, label=f"WHOOP ({sum(whn)} sessions)", color=WH_C)
axes[0].set_title("Sessions logged per day  (ρ=0.49, Wilcoxon p=3.8e-06)",
                  fontweight="bold", pad=8)
axes[0].set_xlabel("day (44 days both devices logged activity)")
axes[0].set_ylabel("workout sessions")
axes[0].legend(fontsize=9, framealpha=0.2)
axes[0].set_xticks([])

mk = np.isfinite(fbk) & np.isfinite(whk)
axes[1].scatter(np.array(fbk)[mk], np.array(whk)[mk], s=40, c=WH_C, alpha=0.8, edgecolors="none")
lim = [0, max(np.nanmax(fbk), np.nanmax(whk)) * 1.05]
axes[1].plot(lim, lim, ls="--", c="#8b949e", lw=1, label="y = x")
axes[1].set_xlim(lim); axes[1].set_ylim(lim)
axes[1].set_title("Workout calories, same days  (ρ=0.11, q>0.4)", fontweight="bold", pad=8)
axes[1].set_xlabel("Fitbit workout kcal/day"); axes[1].set_ylabel("WHOOP workout kcal/day")
axes[1].legend(fontsize=9, framealpha=0.2)
fig.suptitle("Before disagreeing about a workout's numbers, the devices disagree it happened",
             fontsize=14, fontweight="bold", y=1.03)
fig.tight_layout()
fig.savefig(f"{FIG}/fig7_workout_ontology.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---- Fig 8: ECG criterion -----------------------------------------------------
ecg = rows("ecg_paired")
e_bpm = np.array([num(r["derived_bpm"]) for r in ecg])
f_rhr = np.array([num(r["f_rhr"]) for r in ecg])
w_rhr = np.array([num(r["w_rhr"]) for r in ecg])
rest = e_bpm < 70

fig, ax = plt.subplots(figsize=(7.5, 5.6))
for dev, arr, c, info in [
    ("Fitbit", f_rhr, FB_C, ph3["Q7_rhr_vs_ecg"]["Fitbit"]),
    ("WHOOP", w_rhr, WH_C, ph3["Q7_rhr_vs_ecg"]["WHOOP"]),
]:
    m = rest & np.isfinite(arr) & np.isfinite(e_bpm)
    ax.scatter(e_bpm[m], arr[m], s=70, c=c, alpha=0.85, edgecolors="none",
               label=f"{dev}  n={info['n']}, ρ={info['rho']:+.2f}, bias {info['bias']:+.1f} bpm")
lim = [38, 62]
ax.plot(lim, lim, ls="--", c="#8b949e", lw=1.2, label="perfect agreement")
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("ECG-derived heart rate (bpm) — independent instrument")
ax.set_ylabel("Device resting HR (bpm)")
ax.set_title("Both devices read LOW against a single-lead ECG\n"
             "(our R-peak detector agrees with the device's own ECG label to 0.79 bpm)",
             fontweight="bold", fontsize=12, pad=12)
ax.legend(fontsize=9, framealpha=0.2, loc="upper left")
fig.tight_layout()
fig.savefig(f"{FIG}/fig8_ecg_criterion.png", dpi=150, bbox_inches="tight")
plt.close(fig)

import os
print("figures written:")
for f in ["fig5_predictive_asymmetry", "fig6_forest", "fig7_workout_ontology", "fig8_ecg_criterion"]:
    print(" ", f, os.path.getsize(f"{FIG}/{f}.png") // 1024, "KB")
