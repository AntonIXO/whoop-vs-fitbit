"""All article figures in a single script. English labels.

Order matches the article:
  fig1  sleep: 4 scatters (TST / TIB / REM / deep)
  fig2  Bland-Altman: TST and deep
  fig3  deep-sleep gap decomposition
  fig4  lab vs free-living
  fig5  Strain: what it does NOT correlate with
  fig6  WHOOP Recovery vs WHOOP resting HR + device RHR agreement
  fig7  steps
  fig8  deep sleep -> next-day resting HR (asymmetry)
"""
import csv, json, os, sys, re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr

D = "/opt/article-fitbit-vs-whoop/data"
F = "/opt/article-fitbit-vs-whoop/figures"
A = "/opt/article-fitbit-vs-whoop/analysis"

plt.rcParams.update({
    "figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
    "savefig.facecolor": "#0d1117", "axes.edgecolor": "#30363d",
    "axes.labelcolor": "#e6edf3", "xtick.color": "#8b949e", "ytick.color": "#8b949e",
    "text.color": "#e6edf3", "font.size": 11, "axes.grid": True,
    "grid.color": "#21262d", "grid.linewidth": 0.8, "font.family": "DejaVu Sans",
})
FB, WH, OK, BAD, PRED = "#58a6ff", "#f78166", "#3fb950", "#f85149", "#a371f7"


def rows(n):
    with open(f"{D}/{n}.csv") as f:
        return [r for r in csv.DictReader(f) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", r.get("day") or "")]


def num(v):
    return float(v) if v not in ("", None) else np.nan


def col(rs, k):
    return np.array([num(r[k]) for r in rs])


def diag(ax, x, y, c=WH, s=30):
    ax.scatter(x, y, s=s, c=c, alpha=0.78, edgecolors="none")
    lo = min(np.nanmin(x), np.nanmin(y)); hi = max(np.nanmax(x), np.nanmax(y))
    pad = (hi - lo) * 0.06
    ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], ls="--", c="#8b949e", lw=1)
    ax.set_xlim(lo - pad, hi + pad); ax.set_ylim(lo - pad, hi + pad)


s1 = [r for r in rows("sleep_paired_staged") if r["period"] == "P1"]

# ============ sleep charts ============
def sleep_chart(items, filename, title):
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.5))
    for ax, (fx, wx, t, rho) in zip(axes, items):
        diag(ax, col(s1, fx), col(s1, wx))
        ax.set_title(f"{t}   ρ = {rho}", fontsize=12.5, fontweight="bold", pad=10)
        ax.set_xlabel("Fitbit, min"); ax.set_ylabel("WHOOP, min")
    fig.suptitle(title, fontsize=14, fontweight="bold", y=1.03)
    fig.tight_layout(); fig.savefig(f"{F}/{filename}", dpi=150, bbox_inches="tight")
    plt.close(fig)

sleep_chart([
    ("f_tst", "w_tst", "Total sleep time", 0.961),
    ("f_tib", "w_tib", "Time in bed", 0.951),
], "fig1_sleep_duration.png", "Sleep duration: two devices track the night together")
sleep_chart([
    ("f_rem", "w_rem", "REM", 0.812),
    ("f_deep", "w_deep", "Deep sleep", 0.523),
], "fig1_sleep_architecture.png", "Sleep architecture: stage estimates diverge")
# Keep the legacy combined figure for downstream consumers of the original package.
sleep_chart([
    ("f_tst", "w_tst", "Total sleep time", 0.961),
    ("f_tib", "w_tib", "Time in bed", 0.951),
    ("f_rem", "w_rem", "REM", 0.812),
    ("f_deep", "w_deep", "Deep sleep", 0.523),
], "fig1_sleep_scatter.png", "68 staged nights: duration and architecture")

# ============ fig2 Bland-Altman ============
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8))
for ax, (fk, wk, t) in zip(axes, [
    ("f_tst", "w_tst", "Total sleep time"),
    ("f_deep", "w_deep", "Deep sleep"),
]):
    f_, w_ = col(s1, fk), col(s1, wk)
    m, d = (f_ + w_) / 2, w_ - f_
    b, sd = d.mean(), d.std(ddof=1)
    ax.scatter(m, d, s=32, c=WH, alpha=0.78, edgecolors="none")
    ax.axhline(b, c=OK, lw=1.8, label=f"bias {b:+.0f} min")
    ax.axhline(b + 1.96 * sd, c=BAD, ls="--", lw=1.3,
               label=f"Estimated limits: {b-1.96*sd:+.0f} … {b+1.96*sd:+.0f}")
    ax.axhline(b - 1.96 * sd, c=BAD, ls="--", lw=1.3)
    ax.axhline(0, c="#8b949e", lw=0.9)
    ax.set_title(f"{t} — agreement", fontweight="bold", pad=8, fontsize=12.5)
    ax.set_xlabel("mean of both devices, min"); ax.set_ylabel("WHOOP − Fitbit, min")
    ax.legend(fontsize=9, framealpha=0.15, loc="upper left")
fig.suptitle("Sleep agreement: small total-sleep offset, larger deep-sleep offset",
             fontsize=14, fontweight="bold", y=1.03)
fig.tight_layout(); fig.savefig(f"{F}/fig2_bland_altman.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ============ fig3 decomposition ============
p4 = json.load(open(f"{A}/results_phase4.json"))
d = p4["decomposition"]
f_sh = 21.31  # deep sleep share for Fitbit, %
w_sh = 27.78
fig, axes = plt.subplots(1, 2, figsize=(13, 4.4),
                         gridspec_kw={"width_ratios": [1.1, 1]})

# left: waterfall
ax = axes[0]
bars = [
    ("if it were only\nabout night length", d["explained_by_longer_night_min"], FB),
    ("residual beyond\nproportional duration", d["reassignment_min"], WH),
    ("total gap", d["total_deep_gap_min"], OK),
]
ypos = np.arange(len(bars))[::-1]
for yp, (lab, val, c) in zip(ypos, bars):
    ax.barh(yp, val, color=c, height=0.55)
    ax.text(val + (1.4 if val > 0 else -1.4), yp, f"{val:+.1f}",
            va="center", ha="left" if val > 0 else "right",
            fontsize=11.5, fontweight="bold", color=c)
ax.axvline(0, c="#8b949e", lw=1.4)
ax.set_yticks(ypos)
ax.set_yticklabels([b[0] for b in bars], fontsize=10.5)
ax.set_xlim(-9, 38)
ax.set_xlabel("minutes of deep sleep", fontsize=11)
ax.set_title("WHOOP records nights 9 min SHORTER,\n"
             "yet finds 26 min MORE deep sleep",
             fontweight="bold", fontsize=12, pad=12)

# right: shares
ax2 = axes[1]
ax2.bar([0, 1], [f_sh, w_sh], color=[FB, WH], width=0.5)
for i, v in enumerate([f_sh, w_sh]):
    ax2.text(i, v + 0.6, f"{v:.1f}%", ha="center", fontsize=13, fontweight="bold",
             color=[FB, WH][i])
ax2.annotate("", xy=(1, w_sh), xytext=(1, f_sh),
             arrowprops=dict(arrowstyle="<->", color=OK, lw=2))
ax2.text(1.13, (f_sh + w_sh) / 2, f"+{w_sh - f_sh:.1f} p.p.",
         color=OK, fontsize=11.5, fontweight="bold", va="center")
ax2.set_xticks([0, 1]); ax2.set_xticklabels(["Fitbit", "WHOOP"], fontsize=12)
ax2.set_ylabel("deep sleep share of total sleep, %")
ax2.set_ylim(0, 34)
ax2.set_title("Same night, same person —\n"
              "but the devices disagree on WHAT it was",
              fontweight="bold", fontsize=12, pad=12)
fig.tight_layout(); fig.savefig(f"{F}/fig3_decomposition.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ============ fig4 lab vs free-living ============
t4 = p4["tests"]
keys, labs = ["deep", "rem", "tst"], ["Deep\nsleep", "REM", "Total\nsleep time"]
obs = [t4[k]["observed_gap_min"] for k in keys]
lo = [t4[k]["ci95"][0] for k in keys]; hi = [t4[k]["ci95"][1] for k in keys]
pred = [t4[k]["predicted_from_lab_charge5"] for k in keys]
fig, ax = plt.subplots(figsize=(10.5, 6))
y = np.arange(3)
ax.errorbar(obs, y - 0.11, xerr=[np.array(obs) - np.array(lo), np.array(hi) - np.array(obs)],
            fmt="o", ms=11, color=WH, ecolor=WH, elinewidth=2.5, capsize=6, capthick=2.5,
            label="Measured in my data: 68 nights, free-living", zorder=3)
ax.scatter(pred, y + 0.11, s=190, marker="D", c=PRED, zorder=3,
           label="Difference of lab point estimates: WHOOP 4.0 − Charge 5\nSchyvens 2025; collected 2023–24; not a fixed prediction")
for i, k in enumerate(keys):
    inside = t4[k]["charge5_prediction_inside_ci"]
    ax.annotate("", xy=(pred[i], y[i] + 0.11), xytext=(obs[i], y[i] - 0.11),
                arrowprops=dict(arrowstyle="-", color=OK if inside else BAD, lw=2, ls=":", alpha=0.85))
    ax.text(max(pred[i], obs[i]) + 2.5, y[i], f"miss {t4[k]['residual_vs_charge5']:+.1f} min",
            va="center", fontsize=10, color=OK if inside else BAD, fontweight="bold")
ax.axvline(0, c="#8b949e", lw=1.2)
ax.set_yticks(y); ax.set_yticklabels(labs, fontsize=12)
ax.set_xlim(-24, 58); ax.set_ylim(2.6, -0.6)
ax.set_xlabel("WHOOP minus Fitbit, minutes", fontsize=12)
ax.legend(fontsize=9.5, framealpha=0.15, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2)
ax.set_title("Published lab offsets versus my paired home differences\n"
             "Different Fitbit model, population and software; lab uncertainty not shown",
             fontweight="bold", fontsize=13.5, pad=14)
fig.tight_layout(); fig.savefig(f"{F}/fig4_lab_vs_life.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ============ fig5 STRAIN ============
st = [r for r in rows("strain_daily_wide") if r["day"] not in ("2025-10-11", "2025-10-12")]
strain = col(st, "strain")
cands = [
    ("sum of WHOOP's own\nworkout strains", "wk_strain_sum"),
    ("max strain of a single\nWHOOP workout", "wk_strain_max"),
    ("WHOOP workout\nminutes", "wk_min"),
    ("WHOOP workout\ncount", "wk_sess"),
    ("minutes HR > 140", "min_above_140"),
    ("minutes HR > 120", "min_above_120"),
    ("MVPA minutes\n(Fitbit)", "mvpa"),
    ("total calories\n(Fitbit)", "kcal_total"),
    ("steps\n(Fitbit)", "steps"),
    ("mean HR\nfor the day", "hr_mean"),
]
rhos, labels = [], []
for lab, c in cands:
    y_ = col(st, c); m = np.isfinite(strain) & np.isfinite(y_)
    rhos.append(float(spearmanr(strain[m], y_[m])[0])); labels.append(f"{lab} (n={m.sum()})")
order = np.argsort(rhos)
rhos = [rhos[i] for i in order]; labels = [labels[i] for i in order]

fig, axes = plt.subplots(1, 2, figsize=(15, 5.4),
                         gridspec_kw={"width_ratios": [1.25, 1]})
ax = axes[0]
cols = [FB for r in rhos]
ax.barh(np.arange(len(rhos)), rhos, color=cols, height=0.62)
ax.axvline(0, c="#8b949e", lw=1.2)
# No arbitrary correlation threshold: these are descriptive associations.
ax.set_yticks(np.arange(len(rhos))); ax.set_yticklabels(labels, fontsize=9.5)
ax.set_xlim(-0.45, 0.45)
ax.set_xlabel("Spearman ρ with Day Strain", fontsize=11)
ax.set_title("WHOOP Day Strain versus exported summaries\n"
             "Calendar-date joins; not a reconstructed TRIMP validation",
             fontweight="bold", fontsize=12, pad=12)

ax2 = axes[1]
ss = strain[np.isfinite(strain)]
ax2.hist(ss, bins=18, color=WH, alpha=0.85, edgecolor="#0d1117")
ax2.axvspan(8, 14, color=PRED, alpha=0.16)
ax2.axvline(np.median(ss), c=OK, lw=2, label=f"median {np.median(ss):.1f}")
ax2.set_xlabel("Day Strain (scale 0–21)"); ax2.set_ylabel("days")
n_band = int(((ss >= 8) & (ss <= 14)).sum())
ax2.set_title(f"Distribution: {n_band} out of {len(ss)} days in the 8–14 range\n"
              f"SD = {ss.std(ddof=1):.1f}; concentration does not establish noise",
              fontweight="bold", fontsize=12, pad=12)
ax2.legend(fontsize=10, framealpha=0.15)
fig.suptitle("Strain: weak daily associations; check the construct and time alignment",
             fontsize=13.5, fontweight="bold", y=1.04)
fig.tight_layout(); fig.savefig(f"{F}/fig5_strain.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ============ fig6 WHOOP RHR + Recovery ============
rhr = [r for r in rows("rhr_paired") if r["period"] == "P1"]
rr = rows("recovery_rhr")
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8))
# RHR: integer bpm values -> points stack up. Light jitter added.
rng = np.random.default_rng(3)
fx, wx = col(rhr, "f_rhr"), col(rhr, "w_rhr")
mr = np.isfinite(fx) & np.isfinite(wx)
fx, wx = fx[mr], wx[mr]
axes[0].scatter(fx + rng.normal(0, 0.11, len(fx)), wx + rng.normal(0, 0.11, len(wx)),
                s=32, c=WH, alpha=0.7, edgecolors="none")
lo_, hi_ = min(fx.min(), wx.min()) - 1.5, max(fx.max(), wx.max()) + 1.5
axes[0].plot([lo_, hi_], [lo_, hi_], ls="--", c="#8b949e", lw=1)
axes[0].set_xlim(lo_, hi_); axes[0].set_ylim(lo_, hi_)
axes[0].set_title(f"Resting HR   ρ = 0.68   (n = {len(fx)})\n"
                  "WHOOP reads 6.7 bpm lower on average",
                  fontweight="bold", pad=8, fontsize=12)
axes[0].set_xlabel("Fitbit, bpm"); axes[0].set_ylabel("WHOOP, bpm")
x_, y_ = col(rr, "rhr"), col(rr, "recovery")
mrr = np.isfinite(x_) & np.isfinite(y_)
x_, y_ = x_[mrr], y_[mrr]
axes[1].scatter(x_ + rng.normal(0, 0.09, len(x_)), y_,
                s=34, c=WH, alpha=0.75, edgecolors="none")
k, b = np.polyfit(x_, y_, 1)
xs = np.linspace(x_.min(), x_.max(), 10)
axes[1].plot(xs, k * xs + b, c=OK, lw=2)
axes[1].set_title("WHOOP Recovery vs WHOOP resting HR   ρ = −0.59",
                  fontweight="bold", pad=8, fontsize=12)
axes[1].set_xlabel("WHOOP resting HR, bpm"); axes[1].set_ylabel("WHOOP Recovery, %")
fig.tight_layout(); fig.savefig(f"{F}/fig6_rhr_recovery.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ============ fig7 steps ============
sp = rows("steps_paired")
fig, ax = plt.subplots(figsize=(7, 5.6))
f_, w_ = col(sp, "f_steps") / 1000, col(sp, "w_steps") / 1000
diag(ax, f_, w_, s=55)
ax.set_title("Steps, May 2026   ρ = 0.03  (n = 25 days)\n"
             "median discrepancy 5,540 steps, maximum 14,000",
             fontweight="bold", fontsize=12, pad=12)
ax.set_xlabel("Fitbit, k steps"); ax.set_ylabel("WHOOP, k steps")
fig.tight_layout(); fig.savefig(f"{F}/fig7_steps.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ============ fig8 predictive asymmetry ============
wide = rows("nightly_wide")
f_deep, w_deep = col(wide, "f_deep"), col(wide, "w_deep")
rhr_next = col(wide, "f_rhr_next")
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.9), sharey=True)
for ax, dev, x, rho, c in [
    (axes[0], "Fitbit", f_deep, -0.319, FB),
    (axes[1], "WHOOP", w_deep, +0.041, WH),
]:
    m = np.isfinite(x) & np.isfinite(rhr_next)
    ax.scatter(x[m], rhr_next[m], s=36, c=c, alpha=0.8, edgecolors="none")
    k, b = np.polyfit(x[m], rhr_next[m], 1)
    xs = np.linspace(x[m].min(), x[m].max(), 10)
    ax.plot(xs, k * xs + b, c=OK if abs(rho) > 0.2 else BAD, lw=2.2)
    ax.set_title(f"{dev}: deep sleep → next-day resting HR\nρ = {rho:+.3f}",
                 fontweight="bold", fontsize=12.5, pad=10)
    ax.set_xlabel(f"deep sleep by {dev}, min")
axes[0].set_ylabel("next-day resting HR, bpm")
fig.suptitle("Exploratory associations with Fitbit RHR — neither establishes predictive validity",
             fontsize=13.5, fontweight="bold", y=1.03)
fig.tight_layout(); fig.savefig(f"{F}/fig8_predictive.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# уборка неактуальных
for old in ["fig3_steps_strain.png", "fig4_rhr_recovery.png", "fig5_predictive_asymmetry.png",
            "fig6_forest.png", "fig7_workout_ontology.png", "fig8_ecg_criterion.png",
            "fig9_lab_vs_freeliving.png", "fig10_decomposition.png"]:
    p = f"{F}/{old}"
    if os.path.exists(p) and old not in ("fig4_rhr_recovery.png",):
        os.remove(p)

print("done:")
for f in sorted(os.listdir(F)):
    print(f"  {f:34s} {os.path.getsize(F+'/'+f)//1024:>4} KB")
