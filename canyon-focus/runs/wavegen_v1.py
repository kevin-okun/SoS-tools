#!/usr/bin/env python3
"""
wavegen_v1.py — Celeris waves.txt generation for the canyon-focus run matrix.

Two forcing modes:
  mono(Hs, T, compass_from) -> single sine component, amplitude Hs/2.
  tma(Hs, Tp, compass_from, seed) -> directional-spread spectrum replicating
    Celeris's own Wave_Generator.js TMA scheme exactly (verified against
    js/Wave_Generator.js in the Celeris-WebGPU repo):
      - JONSWAP shape, gamma = 3.3, beta from Yamaguchi's approximation
      - 100 frequencies on [fp/3, 3 fp], truncated at 1% of peak center-
        direction energy
      - Mitsuyasu-type spreading: s = 50 (f/fp)^5 below peak, 50 (f/fp)^-2.5
        above; weights cos^(2s)(dtheta/2) normalized per frequency
      - direction grid: peak +/- 20 deg in 5 deg steps (9 directions)
      - component amplitude a = sqrt(2 E df); random phase (seeded here for
        reproducibility, unlike the JS Math.random())
      - energies rescaled so 4.004 sqrt(m0) matches the requested Hs

waves.txt format (File_Loader.js): header "[NumberOfWaves] N", separator
line, then one component per line: amplitude [m], period [s], direction
[rad, math convention: CCW from +x/east], phase [rad].

Direction convention: compass_from D (deg, direction waves COME from) maps
to math direction theta_deg = 270 - D for a west wavemaker with x=east,
y=north (D=270 -> 0, D=250 -> +20, D=290 -> -20).
"""

import math

import numpy as np

GAMMA_S = 3.3
SPREAD_O = 50.0
DIR_STEP = 5.0
DIR_HALF_RANGE = 20.0
TRUNCATION_RATIO = 0.01
FREQ_COUNT = 100
FREQ_START_FACTOR = 1.0 / 3.0
FREQ_END_FACTOR = 3.0


def compass_to_math_deg(compass_from):
    return 270.0 - compass_from


def jonswap_energy(f, fp, hs):
    beta = 0.0624 / (0.23 + 0.033 * GAMMA_S - 0.185 / (1.9 + GAMMA_S))
    r = f / fp
    sigma = 0.07 if f <= fp else 0.09
    r4 = r ** 4
    gamma_exp = math.exp(-((r - 1.0) ** 2) / (2.0 * sigma * sigma))
    return (beta * hs * hs / (f * r4) * math.exp(-1.25 / r4)
            * GAMMA_S ** gamma_exp)


def direction_weights(f, fp, dirs_deg, peak_deg):
    r = f / fp
    s = SPREAD_O * (r ** 5.0 if r < 1.0 else r ** -2.5)
    log_beta_s = ((2.0 * s - 1.0) * math.log(2.0) - math.log(math.pi)
                  + 2.0 * math.lgamma(s + 1.0) - math.lgamma(2.0 * s + 1.0))
    beta_s = math.exp(log_beta_s)
    w = np.array([beta_s * max(0.0, math.cos(0.5 * math.radians(d - peak_deg)))
                  ** (2.0 * s) for d in dirs_deg])
    tot = w.sum()
    if tot <= 0.0:
        w = np.zeros(len(dirs_deg))
        w[(len(dirs_deg) - 1) // 2] = 1.0
        return w
    return w / tot


def tma_components(hs, tp, compass_from, seed):
    peak_deg = compass_to_math_deg(compass_from)
    fp = 1.0 / tp
    f0, f1 = FREQ_START_FACTOR * fp, FREQ_END_FACTOR * fp
    df = (f1 - f0) / (FREQ_COUNT - 1)
    freqs = f0 + df * np.arange(FREQ_COUNT)
    dirs = peak_deg + np.arange(-DIR_HALF_RANGE, DIR_HALF_RANGE + DIR_STEP,
                                DIR_STEP)

    rows = []
    for f in freqs:
        e_f = jonswap_energy(f, fp, hs)
        rows.append((f, e_f * direction_weights(f, fp, dirs, peak_deg)))

    total = sum(en.sum() * df for _, en in rows)
    full_hs = math.sqrt(max(0.0, total)) * 4.004
    scale = (hs / full_hs) ** 2 if full_hs > 0 else 0.0
    rows = [(f, en * scale) for f, en in rows]

    center = (len(dirs) - 1) // 2
    peak_center = max(en[center] for _, en in rows)
    rows = [(f, en) for f, en in rows if en[center] > TRUNCATION_RATIO * peak_center]
    df_kept = rows[1][0] - rows[0][0] if len(rows) > 1 else df

    rng = np.random.default_rng(seed)
    comps = []
    for f, en in rows:
        for d, e in zip(dirs, en):
            a = math.sqrt(max(0.0, 2.0 * e * df_kept))
            comps.append((a, 1.0 / f, math.radians(d),
                          rng.uniform(0.0, 2.0 * math.pi)))
    return comps


def mono_components(hs, t, compass_from):
    theta = math.radians(compass_to_math_deg(compass_from))
    return [(hs / 2.0, t, theta, 0.0)]


def write_waves_txt(path, comps):
    with open(path, "w") as fh:
        fh.write(f"[NumberOfWaves] {len(comps)}\n")
        fh.write("=================================\n")
        for a, t, th, ph in comps:
            fh.write(f"{a:12.7g} {t:12.6g} {th:12.7g} {ph:12.7g}\n")
    return len(comps)


if __name__ == "__main__":
    import sys
    mode, hs, t, d = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
    out = sys.argv[5]
    if mode == "mono":
        n = write_waves_txt(out, mono_components(hs, t, d))
    else:
        seed = int(sys.argv[6]) if len(sys.argv) > 6 else 12345
        n = write_waves_txt(out, tma_components(hs, t, d, seed))
    print(f"wrote {out}: {n} components")
