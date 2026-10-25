"""Fig 9: lab-PSG prediction vs free-living observation — the paper's core claim."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

FIG = "/opt/article-fitbit-vs-whoop/figures"
AN = "/opt/article-fitbit-vs-whoop/analysis"

plt.rcParams.update({
    "figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
    "savefig.facecolor": "#0d1117", "axes.edgecolor": "#30363d",
    "axes.labelcolor": "#e6edf3", "xtick.color": "#8b949e", "ytick.color": "#8b949e",
    "text.color": "#e6edf3", "font.size": 11, "axes.grid": True,
    "grid.color": "#21262d", "grid.linewidth": 0.8, "font.family": "DejaVu Sans",
})
OK, BAD, PRED = "#3fb950", "#f85149", "#a371f7"

ph4 = json.load(open(f"{AN}/results_phase4.json"))
t = ph4["tests"]

labels = ["Deep sleep\n(N3)", "REM", "Total sleep\ntime"]
keys = ["deep", "rem", "tst"]
obs = [t[k]["observed_gap_min"] for k in keys]
lo = [t[k]["ci95"][0] for k in keys]
hi = [t[k]["ci95"][1] for k in keys]
pred = [t[k]["predicted_from_lab_charge5"] for k in keys]

fig, ax = plt.subplots(figsize=(10, 6))
y = np.arange(len(keys))

# observed with CI
err = np.array([np.array(obs) - np.array(lo), np.array(hi) - np.array(obs)])
ax.errorbar(obs, y - 0.12, xerr=err, fmt="o", ms=11, color="#f78166",
            ecolor="#f78166", elinewidth=2.5, capsize=6, capthick=2.5,
            label="Observed: 68 paired nights, free-living (this study)", zorder=3)
# lab prediction
ax.scatter(pred, y + 0.12, s=190, marker="D", c=PRED, zorder=3,
           label="Predicted from lab PSG: bias(WHOOP) − bias(Fitbit)\nSchyvens et al. 2025, n=62")

for i, k in enumerate(keys):
    inside = t[k]["charge5_prediction_inside_ci"]
    ax.annotate("", xy=(pred[i], y[i] + 0.12), xytext=(obs[i], y[i] - 0.12),
                arrowprops=dict(arrowstyle="-", color=OK if inside else BAD,
                                lw=2, ls=":", alpha=0.85))
    resid = t[k]["residual_vs_charge5"]
    ax.text(max(pred[i], obs[i]) + 2.2, y[i], f"Δ {resid:+.1f} min",
            va="center", fontsize=10, color=OK if inside else BAD, fontweight="bold")

ax.axvline(0, c="#8b949e", lw=1.2)
ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=12)
ax.set_xlabel("WHOOP minus Fitbit (minutes)", fontsize=12)
ax.set_xlim(-24, 56)
ax.set_ylim(2.6, -0.6)
ax.legend(fontsize=9.5, framealpha=0.15, loc="upper center",
          bbox_to_anchor=(0.5, -0.16), ncol=2)
ax.set_title("Does a lab PSG bias survive contact with the real world?\n"
             "Deep sleep: 78% transfers. REM and total sleep: the sign FLIPS.",
             fontweight="bold", fontsize=13.5, pad=14)
fig.tight_layout()
fig.savefig(f"{FIG}/fig9_lab_vs_freeliving.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---- Fig 10: deep-sleep decomposition ----------------------------------------
d = ph4["decomposition"]
fig, ax = plt.subplots(figsize=(9, 3.4))
ax.barh([0], [d["explained_by_longer_night_min"]], color="#58a6ff", height=0.55,
        label=f"explained by night length ({d['explained_by_longer_night_min']:+.1f} min)")
ax.barh([0], [d["reassignment_min"]], left=[max(d["explained_by_longer_night_min"], 0)],
        color="#f78166", height=0.55,
        label=f"stage REASSIGNMENT ({d['reassignment_min']:+.1f} min)")
ax.axvline(0, c="#8b949e", lw=1.2)
ax.axvline(d["total_deep_gap_min"], c=OK, lw=2, ls="--",
           label=f"total gap {d['total_deep_gap_min']:+.1f} min")
ax.set_yticks([]); ax.set_xlabel("minutes")
ax.set_title("The +26 min deep-sleep gap is NOT a longer night\n"
             "WHOOP records 9 min LESS total sleep and still finds 26 min more deep sleep",
             fontweight="bold", fontsize=12, pad=12)
ax.legend(fontsize=9.5, framealpha=0.15, loc="upper left")
fig.tight_layout()
fig.savefig(f"{FIG}/fig10_decomposition.png", dpi=150, bbox_inches="tight")
plt.close(fig)

import os
for f in ["fig9_lab_vs_freeliving", "fig10_decomposition"]:
    print(f, os.path.getsize(f"{FIG}/{f}.png") // 1024, "KB")
