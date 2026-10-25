"""Figures for the Whoop-vs-Fitbit article. Dark theme, publication-ready."""
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

DATA = "/opt/article-fitbit-vs-whoop/data"
FIG = "/opt/article-fitbit-vs-whoop/figures"

plt.rcParams.update({
    "figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
    "savefig.facecolor": "#0d1117",
    "axes.edgecolor": "#30363d", "axes.labelcolor": "#e6edf3",
    "xtick.color": "#8b949e", "ytick.color": "#8b949e",
    "text.color": "#e6edf3", "font.size": 11,
    "axes.grid": True, "grid.color": "#21262d", "grid.linewidth": 0.8,
    "font.family": "DejaVu Sans",
})

FB_C, WH_C = "#58a6ff", "#f78166"


def load(name):
    with open(f"{DATA}/{name}.csv") as f:
        return list(csv.DictReader(f))


def fnum(rows, key):
    return np.array([float(r[key]) for r in rows if r.get(key) not in (None, "")])


def scatter_panel(ax, x, y, title, xlabel, ylabel, color=WH_C):
    ax.scatter(x, y, s=28, c=color, alpha=0.75, edgecolors="none")
    lims = [min(x.min(), y.min()), max(x.max(), y.max())]
    pad = (lims[1] - lims[0]) * 0.05
    lims = [lims[0] - pad, lims[1] + pad]
    ax.plot(lims, lims, ls="--", c="#8b949e", lw=1, label="y = x")
    ax.set_xlim(lims); ax.set_ylim(lims)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)


s1 = [r for r in load("sleep_paired_staged") if r["period"] == "P1"]
st = load("steps_paired")

# ---- Fig 1: the four sleep panels -------------------------------------------
fig, axes = plt.subplots(1, 4, figsize=(17, 4.4))
panels = [
    ("f_tst", "w_tst", "Total sleep time", "Fitbit min", "Whoop min", 0.961),
    ("f_tib", "w_tib", "Time in bed", "Fitbit min", "Whoop min", 0.951),
    ("f_rem", "w_rem", "REM", "Fitbit min", "Whoop min", 0.812),
    ("f_deep", "w_deep", "Deep sleep", "Fitbit min", "Whoop min", 0.523),
]
for ax, (fx, wx, t, xl, yl, rho) in zip(axes, panels):
    scatter_panel(ax, fnum(s1, fx), fnum(s1, wx), f"{t}  (ρ={rho})", xl, yl)
fig.suptitle("68 nights, two wearables, one wrist — Fitbit vs WHOOP (Oct–Dec 2025)",
             fontsize=14, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(f"{FIG}/fig1_sleep_scatter.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---- Fig 2: deep-sleep Bland-Altman ------------------------------------------
deep_f = fnum(s1, "f_deep"); deep_w = fnum(s1, "w_deep")
mean_d = (deep_f + deep_w) / 2
diff_d = deep_w - deep_f
bias, sd = diff_d.mean(), diff_d.std(ddof=1)

tst_f = fnum(s1, "f_tst"); tst_w = fnum(s1, "w_tst")
mean_t = (tst_f + tst_w) / 2
diff_t = tst_w - tst_f
bias_t, sd_t = diff_t.mean(), diff_t.std(ddof=1)

fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
for ax, m, d, b, s, t in [
    (axes[0], mean_t, diff_t, bias_t, sd_t, "Total sleep time — agreement"),
    (axes[1], mean_d, diff_d, bias, sd, "Deep sleep — agreement"),
]:
    ax.scatter(m, d, s=30, c=WH_C, alpha=0.75, edgecolors="none")
    ax.axhline(b, c="#3fb950", lw=1.6, label=f"bias {b:+.0f} min")
    ax.axhline(b + 1.96 * s, c="#f85149", ls="--", lw=1.2, label=f"±1.96 SD ({b + 1.96*s:+.0f}, {b - 1.96*s:+.0f})")
    ax.axhline(b - 1.96 * s, c="#f85149", ls="--", lw=1.2)
    ax.axhline(0, c="#8b949e", lw=0.8)
    ax.set_title(t, fontweight="bold", pad=8)
    ax.set_xlabel("mean of both devices (min)")
    ax.set_ylabel("Whoop − Fitbit (min)")
    ax.legend(loc="upper left" if b < 0 else "lower left", fontsize=9, framealpha=0.2)
fig.suptitle("Bland–Altman: the devices agree on duration, not on architecture",
             fontsize=14, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(f"{FIG}/fig2_bland_altman.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---- Fig 3: steps scatter + strain -------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
scatter_panel(axes[0], fnum(st, "f_steps") / 1000, fnum(st, "w_steps") / 1000,
              "Steps, May 2026  (ρ=0.03)", "Fitbit (k steps)", "WHOOP (k steps)")
sk = load("strain_kcal")
axes[1].scatter(fnum(sk, "kcal") / 1000, fnum(sk, "strain"), s=30, c=WH_C, alpha=0.75, edgecolors="none")
axes[1].set_title("WHOOP Strain vs Fitbit kcal  (ρ=0.09)", fontweight="bold", pad=8)
axes[1].set_xlabel("Fitbit total kcal (k)")
axes[1].set_ylabel("WHOOP Day Strain (0–21)")
fig.suptitle("Where the trackers disagree with THEMSELVES: steps and strain",
             fontsize=14, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(f"{FIG}/fig3_steps_strain.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---- Fig 4: RHR + recovery ----------------------------------------------------
rr = load("recovery_rhr")
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
rhr = load("rhr_paired")
r1 = [r for r in rhr if r["period"] == "P1"]
scatter_panel(axes[0], fnum(r1, "f_rhr"), fnum(r1, "w_rhr"),
              "Resting HR  (ρ=0.68)", "Fitbit bpm", "WHOOP bpm")
axes[1].scatter(fnum(rr, "rhr"), fnum(rr, "recovery"), s=30, c=WH_C, alpha=0.75, edgecolors="none")
k, b = np.polyfit(fnum(rr, "rhr"), fnum(rr, "recovery"), 1)
xs = np.linspace(fnum(rr, "rhr").min(), fnum(rr, "rhr").max(), 10)
axes[1].plot(xs, k * xs + b, c="#3fb950", lw=1.6)
axes[1].set_title("Recovery vs Fitbit RHR  (ρ=−0.59)", fontweight="bold", pad=8)
axes[1].set_xlabel("Fitbit resting HR (bpm)")
axes[1].set_ylabel("WHOOP Recovery (%)")
fig.tight_layout()
fig.savefig(f"{FIG}/fig4_rhr_recovery.png", dpi=150, bbox_inches="tight")
plt.close(fig)

print("figures written")
for f in ["fig1_sleep_scatter", "fig2_bland_altman", "fig3_steps_strain", "fig4_rhr_recovery"]:
    import os
    print(f, os.path.getsize(f"{FIG}/{f}.png") // 1024, "KB")
