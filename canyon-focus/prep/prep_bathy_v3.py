#!/usr/bin/env python3
"""
prep_bathy_v3.py — Phase 1 bathymetry prep for the Blacks canyon-focusing tool.

v3 changes vs v2:
  - Fill mask suppressed within EDGE_MARGIN_M of all domain edges so sponge
    and wavemaker zones are identical between real and counterfactual grids
    (also removes a closing-filter artifact strip along the west edge). The
    unfilled canyon stub left at the west boundary lies in >400 m water,
    which is dynamically deep (kh > 3) for all periods in the run matrix.
  - Canyon seeds snap to the maximum closing anomaly within 500 m, so a
    seed cannot miss the mask by a cell.

v2 changes vs v1:
  - Fill mask restricted to the connected component(s) of the closing mask
    that contain seed points in the Scripps and La Jolla canyon branches, so
    only the canyon system is filled (v1 also filled unrelated shelf lows
    and parts of the deep basin).
  - Counterfactual composed as z_filled = max(z_real, fill_surface) inside
    the (slightly dilated) mask at each output resolution, with the smooth
    fill surface bilinearly upsampled from the 15 m grid. v1 added a coarse
    fill *delta* to the fine grids, which produced small sawtooth artifacts
    at the canyon rims.

Source: USGS CoNED Southern California 1-m Topobathy DEM (2016 compilation),
tiles I_14 + I_15, NAVD88 / EPSG:26911, downloaded from the official NOAA
Digital Coast S3 bucket (noaa-nos-coastal-lidar-pds).

Pipeline:
  1. Mosaic the two tiles over the model AOI at native 1 m.
  2. Report nodata/void cells inside the AOI (no gap-filling is performed).
  3. Datum shift NAVD88 -> local MSL: subtract 0.775 m
     (La Jolla station 9410230: MSL 0.833 m, NAVD88 0.058 m above MLLW).
  4. Resample (area average) to the 5 m working grid and 7.5 m Celeris grid.
  5. Counterfactual "canyon filled" bed:
       a. Grey-scale morphological closing (separable max-then-min filter,
          800 m square window) of the 15 m grid raises the floor of incisions
          narrower than ~800 m to the level of the surrounding shelf.
       b. Fill mask = submerged cells raised by > 2 m by the closing.
       c. Fill surface = Laplace interpolation (SOR) over the mask with the
          real bed at the mask rim as boundary values, initialized from the
          closing surface. This is the "smooth interpolation from the
          surrounding shelf" surface.
       d. z_filled = max(z_real, fill surface) on the mask; identical to the
          real bed everywhere else. Fill delta is defined on the 15 m grid,
          bilinearly upsampled, and added to the real grid at each output
          resolution, so real and filled grids are bit-identical off-canyon.
  6. Export Celeris bathy.txt (line 0 = south row, west->east values, MSL,
     depth clamped at -BASE_DEPTH, land clamped at +LAND_CLAMP) for both
     bathymetries, plus a draft config.json based on examples/Scripps_Canyon.
  7. QC figures: real, filled, difference, cross-sections.

Model domain (UTM 11N / EPSG:26911, axis-aligned, north-up):
  E 468500..477500 (9.0 km), N 3632000..3644000 (12.0 km)
  Celeris grid: dx = dy = 7.5 m -> WIDTH 1200 x HEIGHT 1600
"""

import json
import os

import numpy as np
import rasterio
from rasterio.merge import merge as rio_merge
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from scipy.ndimage import (binary_dilation, label, maximum_filter1d,
                           minimum_filter1d, zoom)

SCRATCH = "/tmp/claude-0/-home-user-SoS-tools/b524ccc4-9c8e-5d25-8f78-8de7632b580a/scratchpad"
TILE_DIR = os.path.join(SCRATCH, "bathy")
OUT_DIR = os.path.join(TILE_DIR, "derived")
FIG_DIR = os.path.join(TILE_DIR, "figs")

TILES = [os.path.join(TILE_DIR, f"coned_{t}.tif") for t in ("I_14", "I_15")]
NODATA = -32767.0

# Domain (EPSG:26911)
XMIN, XMAX = 468500.0, 477500.0
YMIN, YMAX = 3632000.0, 3644000.0

NAVD88_TO_MSL = -0.775  # m; La Jolla 9410230 (MSL 0.833, NAVD88 0.058 above MLLW)

DX_WORK = 5.0     # working grid for QC/plots
DX_FILL = 15.0    # grid on which the fill is computed
DX_MODEL = 7.5    # Celeris grid
BASE_DEPTH = 500.0  # m; clamp depth like examples/Scripps_Canyon (base_depth)
LAND_CLAMP = 20.0   # m; cap subaerial elevation (never touched by waves)

CLOSE_WIN_M = 800.0  # closing window (m); fills incisions narrower than this
FILL_THRESH = 2.0    # m; minimum raise by closing to count as canyon
SOR_OMEGA = 1.8
SOR_TOL = 0.01       # m; max update at convergence
SOR_MAX_IT = 20000

# Seed points inside the canyon system (EPSG:26911); the fill mask keeps only
# closing-mask components containing at least one seed.
CANYON_SEEDS = [
    (475900.0, 3637300.0),  # Scripps branch, near head
    (475000.0, 3635600.0),  # La Jolla branch axis
    (473900.0, 3637000.0),  # merged trunk
]
SEED_SNAP_M = 500.0   # snap each seed to max closing anomaly within this radius
EDGE_MARGIN_M = 600.0  # no fill within this distance of any domain edge


def mosaic_aoi():
    srcs = [rasterio.open(p) for p in TILES]
    arr, transform = rio_merge(srcs, bounds=(XMIN, YMIN, XMAX, YMAX),
                               res=1.0, nodata=NODATA)
    for s in srcs:
        s.close()
    z = arr[0].astype(np.float32)
    nvoid = int((z == NODATA).sum())
    zv = np.where(z == NODATA, np.nan, z)
    print(f"1m mosaic: shape {z.shape}, nodata cells {nvoid} "
          f"({100.0 * nvoid / z.size:.4f}%)")
    print(f"  elev range (NAVD88): {np.nanmin(zv):.1f} .. {np.nanmax(zv):.1f} m")
    if nvoid:
        rows, cols = np.where(z == NODATA)
        print(f"  void bbox rows {rows.min()}..{rows.max()} cols {cols.min()}..{cols.max()}")
    return z, transform, nvoid


def resample(z1m, transform1m, dx):
    ny = int(round((YMAX - YMIN) / dx))
    nx = int(round((XMAX - XMIN) / dx))
    dst = np.full((ny, nx), np.nan, dtype=np.float32)
    dst_transform = from_origin(XMIN, YMAX, dx, dx)
    reproject(
        source=z1m, destination=dst,
        src_transform=transform1m, src_crs="EPSG:26911",
        dst_transform=dst_transform, dst_crs="EPSG:26911",
        src_nodata=NODATA, dst_nodata=np.nan,
        resampling=Resampling.average)
    return dst, dst_transform


def separable_closing(z, win_px):
    """Grey closing with a win_px x win_px square structuring element."""
    d = maximum_filter1d(maximum_filter1d(z, win_px, axis=0), win_px, axis=1)
    return minimum_filter1d(minimum_filter1d(d, win_px, axis=0), win_px, axis=1)


def laplace_fill(z, mask, init):
    """SOR Laplace interpolation of z over mask, rim values as BCs."""
    f = z.copy()
    f[mask] = init[mask]
    interior = mask.copy()
    interior[0, :] = interior[-1, :] = interior[:, 0] = interior[:, -1] = False
    ii, jj = np.where(interior)
    checker = ((ii + jj) % 2).astype(bool)
    for it in range(SOR_MAX_IT):
        dmax = 0.0
        for phase in (0, 1):
            sel = checker if phase else ~checker
            i, j = ii[sel], jj[sel]
            upd = 0.25 * (f[i - 1, j] + f[i + 1, j] + f[i, j - 1] + f[i, j + 1])
            delta = upd - f[i, j]
            f[i, j] += SOR_OMEGA * delta
            dmax = max(dmax, float(np.abs(delta).max()) if delta.size else 0.0)
        if dmax < SOR_TOL:
            print(f"  SOR converged in {it + 1} iterations (max update {dmax:.4f} m)")
            break
    else:
        print(f"  SOR hit max iterations, last max update {dmax:.4f} m")
    return f


def build_fill_surface(z1m, transform1m):
    """Smooth fill surface + canyon mask on the 15 m grid (MSL datum)."""
    z15, _ = resample(z1m, transform1m, DX_FILL)
    z15 = z15 + NAVD88_TO_MSL
    win = int(round(CLOSE_WIN_M / DX_FILL)) | 1
    closed = separable_closing(z15, win)
    raw_mask = (closed - z15 > FILL_THRESH) & (z15 < 0.0)

    # suppress fill near domain edges (identical sponge/wavemaker strips)
    m = int(round(EDGE_MARGIN_M / DX_FILL))
    raw_mask[:m, :] = raw_mask[-m:, :] = False
    raw_mask[:, :m] = raw_mask[:, -m:] = False

    labels, nlab = label(raw_mask)
    anom = closed - z15
    r = int(round(SEED_SNAP_M / DX_FILL))
    keep = set()
    for e, n in CANYON_SEEDS:
        j = int((e - XMIN) / DX_FILL)
        i = int((YMAX - n) / DX_FILL)
        w = anom[i - r:i + r + 1, j - r:j + r + 1]
        di, dj = np.unravel_index(np.argmax(w), w.shape)
        i2, j2 = i - r + di, j - r + dj
        if labels[i2, j2] == 0:
            print(f"WARNING: canyon seed E{e:.0f} N{n:.0f} (snapped, anomaly "
                  f"{w[di, dj]:.1f} m) still outside closing mask")
        else:
            keep.add(labels[i2, j2])
    mask = np.isin(labels, sorted(keep))
    print(f"fill: closing window {win} px ({win * DX_FILL:.0f} m); raw mask "
          f"{int(raw_mask.sum())} cells in {nlab} components; canyon-seeded "
          f"mask {int(mask.sum())} cells "
          f"({mask.sum() * DX_FILL**2 / 1e6:.2f} km^2), max raise "
          f"{float((closed - z15)[mask].max()):.1f} m")
    fill = laplace_fill(z15, mask, closed)
    return fill.astype(np.float32), mask


def fill_at(fill15, mask15, dx):
    """Upsample fill surface and mask from 15 m to grid spacing dx."""
    factor = DX_FILL / dx
    ny = int(round((YMAX - YMIN) / dx))
    nx = int(round((XMAX - XMIN) / dx))

    def up(a, order):
        b = zoom(a, factor, order=order, grid_mode=True, mode="nearest")
        b = b[:ny, :nx]
        if b.shape != (ny, nx):
            b = np.pad(b, ((0, ny - b.shape[0]), (0, nx - b.shape[1])),
                       mode="edge")
        return b

    fs = up(fill15, 1)
    # dilate one 15 m cell so the fine-grid rim is fully covered; max() with
    # the real bed keeps the extra ring inert where the shelf is higher
    mk = up(binary_dilation(mask15, iterations=1).astype(np.float32), 1) > 0.25
    return fs, mk


def apply_fill(z, fs, mk):
    return np.where(mk, np.maximum(z, fs), z).astype(np.float32)


def write_celeris_bathy(z, path):
    """z: north-up raster (row 0 = north). Celeris wants line 0 = south."""
    zz = np.clip(z, -BASE_DEPTH, LAND_CLAMP)
    with open(path, "w") as fh:
        for row in zz[::-1]:  # south row first
            fh.write("".join(f"{v:15.7e}" for v in row) + "\n")
    return zz


def write_geotiff(z, transform, path):
    prof = dict(driver="GTiff", height=z.shape[0], width=z.shape[1], count=1,
                dtype="float32", crs="EPSG:26911", transform=transform,
                compress="deflate", predictor=3)
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(z.astype(np.float32), 1)


def make_figures(z5, zf5, t5):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm

    x = XMIN + (np.arange(z5.shape[1]) + 0.5) * DX_WORK
    y = YMAX - (np.arange(z5.shape[0]) + 0.5) * DX_WORK
    ext = [x[0] / 1000, x[-1] / 1000, y[-1] / 1000, y[0] / 1000]
    norm = TwoSlopeNorm(vmin=-550, vcenter=0, vmax=120)
    levels = [-500, -400, -300, -200, -150, -100, -75, -50, -30, -20, -10]

    def panel(ax, zz, title):
        im = ax.imshow(zz, cmap="terrain", norm=norm, extent=ext, origin="upper")
        ax.contour(x / 1000, y / 1000, zz, levels=levels,
                   colors="k", linewidths=0.3, alpha=0.5)
        ax.contour(x / 1000, y / 1000, zz, levels=[0],
                   colors="k", linewidths=1.0)
        ax.set_title(title)
        ax.set_xlabel("UTM 11N Easting (km)")
        ax.set_aspect("equal")
        return im

    fig, axes = plt.subplots(1, 3, figsize=(19, 9), constrained_layout=True)
    panel(axes[0], z5, "Real bathymetry (CoNED 1 m, MSL)")
    im = panel(axes[1], zf5, "Canyon-filled counterfactual")
    fig.colorbar(im, ax=axes[:2], label="elevation rel. MSL (m)",
                 shrink=0.8, aspect=40)
    d = zf5 - z5
    imd = axes[2].imshow(np.where(d > 0.01, d, np.nan), cmap="magma_r",
                         extent=ext, origin="upper", vmin=0, vmax=300)
    axes[2].contour(x / 1000, y / 1000, z5, levels=[0], colors="k",
                    linewidths=1.0)
    axes[2].set_title("Fill thickness (m)")
    axes[2].set_xlabel("UTM 11N Easting (km)")
    axes[2].set_aspect("equal")
    axes[0].set_ylabel("UTM 11N Northing (km)")
    fig.colorbar(imd, ax=axes[2], label="z_filled - z_real (m)",
                 shrink=0.8, aspect=40)
    fig.suptitle("Blacks / Scripps-La Jolla canyon domain "
                 "(9 x 12 km, EPSG:26911) - Phase 1 checkpoint", fontsize=14)
    fig.savefig(os.path.join(FIG_DIR, "bathy_checkpoint_maps_v3.png"), dpi=140)
    plt.close(fig)

    # cross-sections
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), constrained_layout=True)
    n_head = 3637000.0  # ~32.87 N, Scripps Canyon head
    i = int((YMAX - n_head) / DX_WORK)
    axes[0].plot(x / 1000, z5[i], "b-", lw=1.2, label="real")
    axes[0].plot(x / 1000, zf5[i], "r--", lw=1.2, label="canyon filled")
    axes[0].set_title(f"E-W section at N {n_head:.0f} (Scripps Canyon head, ~32.87N)")
    axes[0].set_xlabel("Easting (km)")
    e_sec = 475600.0
    j = int((e_sec - XMIN) / DX_WORK)
    axes[1].plot(y / 1000, z5[:, j], "b-", lw=1.2, label="real")
    axes[1].plot(y / 1000, zf5[:, j], "r--", lw=1.2, label="canyon filled")
    axes[1].set_title(f"N-S section at E {e_sec:.0f} (across canyon branches)")
    axes[1].set_xlabel("Northing (km)")
    for ax in axes:
        ax.set_ylabel("elev rel MSL (m)")
        ax.grid(alpha=0.3)
        ax.legend()
        ax.axhline(0, color="k", lw=0.5)
    fig.savefig(os.path.join(FIG_DIR, "bathy_checkpoint_sections_v3.png"), dpi=140)
    plt.close(fig)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(FIG_DIR, exist_ok=True)

    z1m, t1m, nvoid = mosaic_aoi()
    tif1m = os.path.join(OUT_DIR, "coned_aoi_1m_navd88_v1.tif")
    if not os.path.exists(tif1m):
        write_geotiff(z1m, t1m, tif1m)

    fill15, mask15 = build_fill_surface(z1m, t1m)

    grids = {}
    for name, dx in (("work", DX_WORK), ("model", DX_MODEL)):
        z, t = resample(z1m, t1m, dx)
        z = z + NAVD88_TO_MSL
        nn = int(np.isnan(z).sum())
        if nn:
            print(f"WARNING: {name} grid has {nn} NaN cells after resampling")
        fs, mk = fill_at(fill15, mask15, dx)
        zf = apply_fill(z, fs, mk)
        grids[name] = (z, zf, t)
        print(f"{name} grid dx={dx}: {z.shape[1]}x{z.shape[0]} "
              f"(WIDTHxHEIGHT), z {np.nanmin(z):.1f}..{np.nanmax(z):.1f} m, "
              f"max fill {np.nanmax(zf - z):.1f} m")

    z5, zf5, t5 = grids["work"]
    write_geotiff(z5, t5, os.path.join(OUT_DIR, "blacks_real_5m_msl_v3.tif"))
    write_geotiff(zf5, t5, os.path.join(OUT_DIR, "blacks_filled_5m_msl_v3.tif"))

    zm, zfm, tm = grids["model"]
    zr = write_celeris_bathy(zm, os.path.join(OUT_DIR, "bathy_real_v3.txt"))
    zc = write_celeris_bathy(zfm, os.path.join(OUT_DIR, "bathy_filled_v3.txt"))
    print(f"Celeris grids written: WIDTH={zm.shape[1]} HEIGHT={zm.shape[0]} "
          f"dx=dy={DX_MODEL}")
    print(f"  clamped range real: {zr.min():.1f}..{zr.max():.1f}  "
          f"filled: {zc.min():.1f}..{zc.max():.1f}")

    # sanity checks at known landmarks (values printed for human review)
    def probe(zz, e, n, label):
        j = int((e - XMIN) / DX_MODEL)
        i = int((YMAX - n) / DX_MODEL)
        print(f"  probe {label}: E{e:.0f} N{n:.0f} -> real "
              f"{zm[i, j]:.1f} m, filled {zfm[i, j]:.1f} m")
    probe(zm, 475900, 3637300, "Scripps Canyon head axis")
    probe(zm, 475000, 3635600, "La Jolla Canyon branch axis")
    probe(zm, 473900, 3637000, "merged trunk")
    probe(zm, 475500, 3640000, "Blacks surf zone approach")
    probe(zm, 470000, 3641000, "offshore NW (deep, outside mask)")

    from rasterio.warp import transform as crs_transform
    lons, lats = crs_transform("EPSG:26911", "EPSG:4326",
                               [XMIN, XMAX], [YMIN, YMAX])
    config = json.load(open(
        "/home/user/celeris-webgpu/examples/Scripps_Canyon/config.json"))
    config.update({
        "WIDTH": zm.shape[1], "HEIGHT": zm.shape[0],
        "dx": DX_MODEL, "dy": DX_MODEL,
        "base_depth": BASE_DEPTH, "seaLevel": 0,
        "lat_LL": round(lats[0], 8), "lon_LL": round(lons[0], 8),
        "lat_UR": round(lats[1], 8), "lon_UR": round(lons[1], 8),
    })
    for k in ("run_example", "exampleDirs"):
        config.pop(k, None)
    with open(os.path.join(OUT_DIR, "config_base_v3.json"), "w") as fh:
        json.dump(config, fh, indent=2)
    print("Draft config written (wave forcing left as placeholders for Phase 2).")

    make_figures(z5, zf5, t5)
    print("Figures written to", FIG_DIR)


if __name__ == "__main__":
    main()
