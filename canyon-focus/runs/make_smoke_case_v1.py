#!/usr/bin/env python3
"""
make_smoke_case_v1.py — Build a coarse end-to-end validation case for the
canyon-focus harness, small enough to run on this container's SwiftShader
(CPU) WebGPU fallback.

NOT a production case: 30 m grid (300x400), one monochromatic component,
short averaging window. Its only purpose is to prove the full pipeline —
bathy/config/waves generation -> headless Celeris -> Hs export -> readback —
before the real 7.5 m matrix runs on a hardware GPU.
"""

import json
import os
import sys

import numpy as np
import rasterio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wavegen_v1 import mono_components, write_waves_txt

SCRATCH = "/tmp/claude-0/-home-user-SoS-tools/b524ccc4-9c8e-5d25-8f78-8de7632b580a/scratchpad"
SRC_TIF = os.path.join(SCRATCH, "bathy", "derived", "blacks_real_5m_msl_v4.tif")
CASE_DIR = os.path.join(SCRATCH, "smoke_case")

DECIMATE = 6          # 5 m -> 30 m
BASE_DEPTH = 500.0
LAND_CLAMP = 20.0

T = 16.0              # s
HS = 1.0              # m
COMPASS_FROM = 272.0  # deg

# timing: 9 km fetch / deep-water Cg(16 s) ~ 12.5 m/s -> ~720 s arrival
T_RESET_MEANS = 800.0
T_RESET_WH = 880.0
T_WRITE = 1040.0      # 10 waves of averaging - smoke only


def main():
    os.makedirs(CASE_DIR, exist_ok=True)
    with rasterio.open(SRC_TIF) as src:
        z5 = src.read(1)
    ny5, nx5 = z5.shape
    ny, nx = ny5 // DECIMATE, nx5 // DECIMATE
    z = z5[:ny * DECIMATE, :nx * DECIMATE].reshape(ny, DECIMATE, nx,
                                                   DECIMATE).mean(axis=(1, 3))
    z = np.clip(z, -BASE_DEPTH, LAND_CLAMP)
    dx = 5.0 * DECIMATE

    bathy_path = os.path.join(CASE_DIR, "bathy.txt")
    with open(bathy_path, "w") as fh:
        for row in z[::-1]:          # line 0 = south
            fh.write("".join(f"{v:15.7e}" for v in row) + "\n")

    n = write_waves_txt(os.path.join(CASE_DIR, "waves.txt"),
                        mono_components(HS, T, COMPASS_FROM))

    config = json.load(open(
        "/home/user/celeris-webgpu/examples/Scripps_Canyon/config.json"))
    for k in ("run_example", "exampleDirs"):
        config.pop(k, None)
    config.update({
        "WIDTH": nx, "HEIGHT": ny, "dx": dx, "dy": dx,
        "base_depth": BASE_DEPTH, "seaLevel": 0,
        "NLSW_or_Bous": 1, "Courant_num": 0.2, "friction": 0.0025,
        "west_boundary_type": 2, "east_boundary_type": 0,
        "south_boundary_type": 1, "north_boundary_type": 1,
        "BoundaryWidth": 12,
        "incident_wave_type": -1,
        "GoogleMapOverlay": 0,
        "amplitude": HS / 2.0, "period": T, "direction": 0,
        # automation triggers (same keys the stock Selenium harness injects)
        "trigger_animation": 0,
        "trigger_writesurface": 0,
        "write_eta": 0, "write_u": 0, "write_v": 0, "write_P": 0,
        "write_Q": 0, "write_turb": 0,
        "trigger_writeWaveHeight": 1,
        "trigger_resetMeans_time": T_RESET_MEANS,
        "trigger_resetWaveHeight_time": T_RESET_WH,
        "trigger_writeWaveHeight_time": T_WRITE,
        "render_step": 100,
    })
    with open(os.path.join(CASE_DIR, "config.json"), "w") as fh:
        json.dump(config, fh, indent=2)

    print(f"smoke case: {nx}x{ny} at dx={dx} m, {n} wave component(s), "
          f"sim to t={T_WRITE:.0f} s -> {CASE_DIR}")


if __name__ == "__main__":
    main()
