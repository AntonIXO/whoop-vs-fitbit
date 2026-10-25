"""Plot every explored calendar lag; do not present a selected lag as a correction."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
r = json.loads((ROOT / 'analysis/results_trimp_audit.json').read_text())
entries = r['cohorts']['figure5_exclusions']['calendar_lags']['wk_strain_max']
plt.rcParams.update({'figure.facecolor': '#0d1117', 'axes.facecolor': '#0d1117',
    'savefig.facecolor': '#0d1117', 'text.color': '#e6edf3', 'axes.labelcolor': '#e6edf3',
    'xtick.color': '#8b949e', 'ytick.color': '#8b949e', 'axes.edgecolor': '#30363d',
    'font.family': 'DejaVu Sans', 'font.size': 11})
fig, axes = plt.subplots(1, 2, figsize=(12.8, 5))
for ax, key, title in zip(axes,
        ['available_pairs', 'common_strain_dates_across_all_five_lags'],
        ['Available pairs at each lag', 'Identical Day Strain dates across all lags']):
    xs = [e['lag_days'] for e in entries]
    ys = [e[key]['spearman'] for e in entries]
    ax.bar(xs, ys, color='#58a6ff', width=.65)
    ax.axhline(0, color='#8b949e', linewidth=.8)
    for e, x, y in zip(entries, xs, ys):
        ax.text(x, y + (.035 if y >= 0 else -.04), f"{y:+.3f}\nn={e[key]['n']}",
                ha='center', va='bottom' if y >= 0 else 'top', fontsize=10)
    ax.set_xticks(xs)
    ax.set_ylim(-.55, 1.08)
    ax.set_xlabel('Workout date minus Day Strain date (calendar days)')
    ax.set_ylabel('Spearman ρ: Day Strain vs maximum workout Strain')
    ax.set_title(title, fontweight='bold')
fig.suptitle('Date alignment changes the result — exploratory, not a validated correction',
             fontweight='bold', fontsize=13)
fig.tight_layout()
out = ROOT / 'figures/fig9_strain_alignment.png'
fig.savefig(out, dpi=150, bbox_inches='tight')
plt.close(fig)
print(out)
