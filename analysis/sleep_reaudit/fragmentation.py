"""Quantify Fitbit awake-stage fragmentation in the fresh P1 sleep extraction.

This distinguishes interior awake runs from boundary awake time. WHOOP's local
sleep_sessions rows contain stage totals, not an epoch/run timeline, so WHOOP
awake-episode counts cannot be reconstructed from them.
"""
from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROWS = ROOT / "analysis" / "sleep_reaudit" / "sessions.json"
OUT = ROOT / "analysis" / "sleep_reaudit" / "fragmentation.json"

rows = json.loads(ROWS.read_text())
fb = [
    r for r in rows
    if r["source_id"] == 35 and not r["is_nap"]
    and "2025-10-08" <= r["day"] <= "2025-12-24"
]

records = []
interior_durations = []
for r in fb:
    stages = r.get("stages") or []
    durations = r.get("stage_dur_s") or []
    if not isinstance(stages, list) or not isinstance(durations, list) or len(stages) != len(durations):
        continue
    awake = [float(d) for s, d in zip(stages, durations) if s == "awake"]
    interior = [
        float(d) for i, (s, d) in enumerate(zip(stages, durations))
        if s == "awake" and i > 0 and i < len(stages) - 1
    ]
    interior_durations.extend(interior)
    records.append({
        "day": r["day"],
        "provider_awakenings": r.get("awakenings"),
        "awake_minutes_from_timeline": sum(awake) / 60,
        "awake_runs": len(awake),
        "interior_awake_runs": len(interior),
        "interior_awake_minutes": sum(interior) / 60,
        "short_boundary_runs_le_2min": sum(d <= 120 for d in awake),
    })

provider = [r["provider_awakenings"] for r in records if r["provider_awakenings"] is not None]
all_runs = [r["awake_runs"] for r in records]
short = [r["short_boundary_runs_le_2min"] for r in records]
summary = {
    "n_fitbit_p1_main": len(records),
    "provider_awakenings": {
        "mean": statistics.mean(provider), "median": statistics.median(provider),
        "min": min(provider), "max": max(provider),
    },
    "timeline_awake_runs": {
        "mean": statistics.mean(all_runs), "median": statistics.median(all_runs),
        "distribution": dict(sorted(Counter(all_runs).items())),
    },
    "interior_awake_runs": {
        "total": sum(r["interior_awake_runs"] for r in records),
        "mean_per_night": statistics.mean(r["interior_awake_runs"] for r in records),
        "median_per_night": statistics.median(r["interior_awake_runs"] for r in records),
    },
    "interior_awake_duration_min": {
        "mean": statistics.mean(interior_durations) / 60,
        "median": statistics.median(interior_durations) / 60,
        "min": min(interior_durations) / 60,
        "max": max(interior_durations) / 60,
        "n_runs": len(interior_durations),
    },
    "short_boundary_runs_le_2min": {
        "n_nights_with_any": sum(x > 0 for x in short),
        "total_runs": sum(short),
        "note": "These short runs occur at sleep boundaries in this extraction; no interior awake run is <=2 minutes.",
    },
    "whoop": {
        "awake_episode_count": "unavailable: WHOOP source stores stage totals, not an awake-run timeline",
        "awake_minutes_are_available": True,
    },
}
OUT.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
