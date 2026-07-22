#!/usr/bin/env python3
"""
make_case_v1.py — Build one Celeris case (config.json + waves.txt) for the
canyon-focus run matrix.

Usage:
  python3 make_case_v1.py --period 16 --direction 280 --layer real \
      --forcing mono [--hs 1.0] [--out-root canyon-focus/cases]

Case ID / directory: T{period}_D{direction}_{layer}_{forcing}
The bathymetry grid is NOT copied per case; pass the matching
canyon-focus/grids/bathy_{layer}_v4.txt to run_cases_v1.py --bathy.

Trigger timing (sim seconds), derived per period T with a 9 km wavemaker-
to-coast fetch and deep-water group speed Cg = gT/(4 pi) ~ 0.7806 T m/s:
  t_arrive     = 9000 / Cg(T)          (slowest energy crosses the domain)
  resetMeans   = t_arrive + 8 T        (let the field establish)
  resetWH      = resetMeans + 120 s    (let the mean converge)
  write        = resetWH + 50 T (mono) | 75 T (spread)   (Hs averaging)
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wavegen_v1 import mono_components, tma_components, write_waves_txt

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GRID_DIR = os.path.join(REPO, "canyon-focus", "grids")
FETCH_M = 9000.0
LAYERS = ("real", "fillB", "fillC")


def trigger_times(period, forcing):
    cg = 0.7806 * period
    t_arr = FETCH_M / cg
    t_means = t_arr + 8.0 * period
    t_wh = t_means + 120.0
    n_avg = 50.0 if forcing == "mono" else 75.0
    t_write = t_wh + n_avg * period
    return round(t_means, 1), round(t_wh, 1), round(t_write, 1)


def build_case(period, direction, layer, forcing, hs, out_root, seed_base=777):
    assert layer in LAYERS, f"layer must be one of {LAYERS}"
    assert forcing in ("mono", "spread")
    case_id = f"T{period:g}_D{direction:g}_{layer}_{forcing}"
    case_dir = os.path.join(out_root, case_id)
    os.makedirs(case_dir, exist_ok=True)

    if forcing == "mono":
        comps = mono_components(hs, period, direction)
    else:
        # one seed per (period, direction): SAME phases across bathy layers,
        # so layer differences are never phase noise
        seed = seed_base + int(period * 1000 + direction)
        comps = tma_components(hs, period, direction, seed)
    n = write_waves_txt(os.path.join(case_dir, "waves.txt"), comps)

    t_means, t_wh, t_write = trigger_times(period, forcing)
    config = json.load(open(os.path.join(GRID_DIR, "config_base_v4.json")))
    config.update({
        "friction": 0.0025,            # sandy shelf (Blacks example value)
        "west_boundary_type": 2, "east_boundary_type": 0,
        "south_boundary_type": 1, "north_boundary_type": 1,
        "BoundaryWidth": 20,
        "incident_wave_type": -1,      # custom spectrum from waves.txt
        "GoogleMapOverlay": 0,
        "amplitude": hs / 2.0, "period": period, "direction": 0,
        "trigger_animation": 0,
        "trigger_writesurface": 0,
        "write_eta": 0, "write_u": 0, "write_v": 0, "write_P": 0,
        "write_Q": 0, "write_turb": 0,
        "trigger_writeWaveHeight": 1,
        "trigger_resetMeans_time": t_means,
        "trigger_resetWaveHeight_time": t_wh,
        "trigger_writeWaveHeight_time": t_write,
        "render_step": 100,
    })
    with open(os.path.join(case_dir, "config.json"), "w") as fh:
        json.dump(config, fh, indent=2)

    meta = dict(case_id=case_id, period=period, direction_from=direction,
                layer=layer, forcing=forcing, hs_offshore=hs,
                n_components=n, t_resetMeans=t_means, t_resetWH=t_wh,
                t_write=t_write,
                bathy_file=f"grids/bathy_{layer}_v4.txt")
    with open(os.path.join(case_dir, "case_meta.json"), "w") as fh:
        json.dump(meta, fh, indent=2)
    print(f"{case_id}: {n} components, write at t={t_write:.0f} s "
          f"-> {case_dir}")
    return case_dir


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", type=float, required=True)
    ap.add_argument("--direction", type=float, required=True,
                    help="compass direction waves come FROM (deg)")
    ap.add_argument("--layer", default="real", choices=LAYERS)
    ap.add_argument("--forcing", default="mono", choices=("mono", "spread"))
    ap.add_argument("--hs", type=float, default=1.0)
    ap.add_argument("--out-root",
                    default=os.path.join(REPO, "canyon-focus", "cases"))
    args = ap.parse_args()
    build_case(args.period, args.direction, args.layer, args.forcing,
               args.hs, args.out_root)
