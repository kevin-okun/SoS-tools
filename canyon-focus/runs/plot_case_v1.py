#!/usr/bin/env python3
"""
plot_case_v1.py — Read back and QC-plot one Celeris case output.

Reads nx/ny/dx/dy.txt + current_Hs.bin + current_bathytopo.bin from a case
output dir, verifies the bathytopo readback against the input bathy grid
(orientation + values), and plots the Hs field with depth contours.

Binary layout (File_Writer.js readTextureData): float32, row-major by
texture row; texture y = model y with row 0 = SOUTH (same as bathy.txt
line order). Arrays are flipped to north-up for plotting.

Usage: python3 plot_case_v1.py OUTPUT_DIR [--bathy BATHY_TXT] [--fig FIG_PNG]
"""

import argparse
import os

import numpy as np


def read_case(out_dir):
    def scalar(name):
        return float(open(os.path.join(out_dir, name)).read().strip())
    nx, ny = int(scalar("nx.txt")), int(scalar("ny.txt"))
    dx, dy = scalar("dx.txt"), scalar("dy.txt")

    def field(name):
        raw = np.fromfile(os.path.join(out_dir, name), dtype=np.float32)
        if raw.size != nx * ny:
            raise ValueError(f"{name}: {raw.size} floats != {nx}x{ny}")
        return raw.reshape(ny, nx)   # row 0 = south
    return dict(nx=nx, ny=ny, dx=dx, dy=dy,
                Hs=field("current_Hs.bin"),
                bathy=field("current_bathytopo.bin"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--bathy", default=None,
                    help="input bathy.txt to cross-check readback")
    ap.add_argument("--fig", default=None)
    args = ap.parse_args()

    c = read_case(args.out_dir)
    Hs, bathy = c["Hs"], c["bathy"]
    wet = bathy < 0
    print(f"grid {c['nx']}x{c['ny']} dx={c['dx']} dy={c['dy']}")
    print(f"bathy readback range: {bathy.min():.1f}..{bathy.max():.1f} m")
    print(f"Hs: min {np.nanmin(Hs):.3f}  max {np.nanmax(Hs):.3f}  "
          f"wet-mean {Hs[wet].mean():.3f} m")

    if args.bathy:
        zin = np.loadtxt(args.bathy)          # line 0 = south
        rms = np.sqrt(np.mean((zin - bathy) ** 2))
        print(f"bathy.txt vs readback RMS diff: {rms:.4f} m "
              f"({'OK' if rms < 0.1 else 'MISMATCH - check orientation'})")

    if args.fig:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        Hp = np.flipud(np.where(wet, Hs, np.nan))
        Bp = np.flipud(bathy)
        km_x = c["nx"] * c["dx"] / 1000
        km_y = c["ny"] * c["dy"] / 1000
        ext = [0, km_x, 0, km_y]
        fig, ax = plt.subplots(figsize=(8, 10), constrained_layout=True)
        im = ax.imshow(Hp, cmap="turbo", extent=ext, origin="upper",
                       vmin=0, vmax=np.nanpercentile(Hp, 99.5))
        x = np.linspace(0, km_x, c["nx"])
        y = np.linspace(km_y, 0, c["ny"])
        ax.contour(x, y, Bp, levels=[-500, -300, -200, -100, -50, -20],
                   colors="k", linewidths=0.4, alpha=0.6)
        ax.contour(x, y, Bp, levels=[0], colors="k", linewidths=1.2)
        ax.set_title(os.path.basename(os.path.dirname(args.out_dir)) or
                     args.out_dir)
        ax.set_xlabel("x (km, west->east)")
        ax.set_ylabel("y (km, south->north)")
        fig.colorbar(im, ax=ax, label="Hs (m)", shrink=0.7)
        fig.savefig(args.fig, dpi=140)
        print(f"figure -> {args.fig}")


if __name__ == "__main__":
    main()
