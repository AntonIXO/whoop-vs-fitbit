#!/usr/bin/env python3
from __future__ import annotations
import csv
from datetime import date
from pathlib import Path
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

plt.rcParams.update({
    "figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
    "savefig.facecolor": "#0d1117", "axes.edgecolor": "#30363d",
    "axes.labelcolor": "#e6edf3", "xtick.color": "#8b949e", "ytick.color": "#8b949e",
    "text.color": "#e6edf3", "font.size": 11, "axes.grid": True,
    "grid.color": "#21262d", "grid.linewidth": 0.8, "font.family": "DejaVu Sans",
})

ROOT = Path(__file__).resolve().parents[2]
rows=[]
with (ROOT/'data/readiness_recovery_paired.csv').open() as f:
    for r in csv.DictReader(f):
        rows.append({**r,'day':date.fromisoformat(r['day']),'readiness':float(r['readiness']),'recovery':float(r['recovery']),'source_id':int(r['source_id'])})
rows.sort(key=lambda r:r['day'])
colors={2754:'#58a6ff',2757:'#f78166'}
labels={2754:'WHOOP account 2754 (n=57)',2757:'WHOOP account 2757 (n=4)'}
fig,(ax,ax2)=plt.subplots(1,2,figsize=(12,4.8),dpi=180)
for sid in sorted(colors):
    rs=[r for r in rows if r['source_id']==sid]
    ax.scatter([r['readiness'] for r in rs],[r['recovery'] for r in rs],s=28,alpha=.8,color=colors[sid],label=labels[sid],edgecolors='none')
lo,hi=0,105
ax.plot([lo,hi],[lo,hi],color='#6b7280',linestyle='--',linewidth=1,label='identity line')
ax.set(xlim=(0,105),ylim=(0,105),xlabel='Fitbit Readiness',ylabel='WHOOP Recovery',title='Same-day paired scores')
ax.grid(alpha=.2);ax.legend(fontsize=8,loc='upper left')
rho=spearmanr([r['readiness'] for r in rows],[r['recovery'] for r in rows]).statistic
ax.text(.98,.04,f'pooled ρ = {rho:.3f}\nWHOOP − Fitbit = +9.3',transform=ax.transAxes,ha='right',va='bottom',fontsize=9,bbox=dict(facecolor='#161b22',alpha=.92,edgecolor='#30363d'))
for sid in sorted(colors):
    rs=[r for r in rows if r['source_id']==sid]
    ax2.scatter([r['day'] for r in rs],[r['recovery']-r['readiness'] for r in rs],s=27,alpha=.8,color=colors[sid],label=labels[sid],edgecolors='none')
ax2.axhline(0,color='#374151',linewidth=1)
ax2.set(xlabel='Date',ylabel='WHOOP Recovery − Fitbit Readiness',title='The level offset is usually positive')
ax2.grid(alpha=.2);ax2.tick_params(axis='x',rotation=35);ax2.legend(fontsize=8,loc='upper left')
fig.suptitle('Fitbit Readiness versus WHOOP Recovery',fontsize=14,fontweight='bold')
fig.tight_layout()
out=ROOT/'figures/fig10_readiness_recovery.png';fig.savefig(out,bbox_inches='tight');print(out)
