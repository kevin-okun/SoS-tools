#!/usr/bin/env python3
"""
prep_bathy_v4.py — Phase 1 bathymetry prep for the Blacks canyon-focusing tool.

Produces THREE bathymetry layers on the same grid:
  A "real"   — CoNED 1-m mosaic, datum-shifted to MSL.
  B "fillB"  — shallow canyon legs filled (800 m closing scale): the incised
               Scripps/La Jolla branches and upper trunk are removed; the
               wide deep trough remains. (= v3 counterfactual)
  C "fillC"  — full canyon removal. Computed by NESTING on layer B: the
               4 km closing scale is applied to the B-filled bed, and the
               resulting deep-trough mask is Laplace-filled from B rim
               values. C is therefore bit-identical to B outside the deep
               mask (so B-vs-C isolates exactly the deep portion), and the
               fill extends offshore to the domain edge.

Method per layer (as in v3): grey-scale morphological closing (separable
max/min square window) -> anomaly threshold -> connected components seeded
in the canyon -> Laplace interpolation (SOR) of the bed over the mask with
real rim values as boundary conditions -> z_fill = max(z_real, fill).

Edge handling: no fill within EDGE_MARGIN_M of the N/S/E edges. At the WEST
edge (which layer C's fill legitimately reaches), the fill is instead
blended: bit-identical to real within WEST_HOLD_M of the boundary (so the
wavemaker and sponge see identical depths in every layer), ramping linearly
to full fill by WEST_HOLD_M + WEST_RAMP_M. The held strip lies in ~500 m
water, dynamically deep (kh > 3) for all periods in the run matrix, so the
residual unfilled canyon stub there is physically inert.

Source: USGS CoNED Southern California 1-m Topobathy DEM (2016), tiles
I_14 + I_15 (NAVD88, EPSG:26911), NOAA Digital Coast S3 bucket. Datum shift
NAVD88 -> local MSL = -0.775 m (NOAA station 9410230: MSL 0.833 m, NAVD88
0.058 m above MLLW).

Model domain (EPSG:26911, north-up): E 468500..477500, N 3632000..3644000
Celeris grid: dx = dy = 7.5 m -> WIDTH 1200 x HEIGHT 1600, line 0 = south.
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

XMIN, XMAX = 468500.0, 477500.0
YMIN, YMAX = 3632000.0, 3644000.0

NAVD88_TO_MSL = -0.775

DX_WORK = 5.0
DX_FILL = 15.0
DX_MODEL = 7.5
BASE_DEPTH = 500.0
LAND_CLAMP = 20.0

CLOSE_WIN_B_M = 800.0    # shallow-leg fill scale
CLOSE_WIN_C_M = 4000.0   # deep-trough fill scale
FILL_THRESH_B = 2.0      # m
FILL_THRESH_C = 5.0      # m
SOR_OMEGA = 1.8
SOR_TOL = 0.01
SOR_MAX_IT = 20000

CANYON_SEEDS = [
    (475900.0, 3637300.0),  # Scripps branch, near head
    (475000.0, 3635600.0),  # La Jolla branch axis
    (473900.0, 3637000.0),  # merged trunk
]
DEEP_SEEDS = [
    (470000.0, 3640500.0),  # deep trough / fan valley
    (473000.0, 3638000.0),  # mid trunk below B fill
]
SEED_SNAP_M = 500.0
EDGE_MARGIN_M = 600.0    # N/S/E edges: no fill
WEST_HOLD_M = 300.0      # west edge: bit-identical strip
WEST_RAMP_M = 900.0      # west edge: linear blend to full fill


def mosaic_aoi():
    srcs = [rasterio.open(p) for p in TILES]
    arr, transform = rio_merge(srcs, bounds=(XMIN, YMIN, XMAX, YMAX),
                               res=1.0, nodata=NODATA)
    for s in srcs:
        s.close()
    z = arr[0].astype(np.float32)
    nvoid = int((z == NODATA).sum())
    print(f"1m mosaic: shape {z.shape}, nodata cells {nvoid}")
    return z, transform


def resample(z1m, transform1m, dx):
    ny = int(round((YMAX - YMIN) / dx))
    nx = int(round((XMAX - XMIN) / dx))
    dst = np.full((ny, nx), np.nan, dtype=np.float32)
    dst_transform = from_origin(XMIN, YMAX, dx, dx)
    reproject(source=z1m, destination=dst,
              src_transform=transform1m, src_crs="EPSG:26911",
              dst_transform=dst_transform, dst_crs="EPSG:26911",
              src_nodata=NODATA, dst_nodata=np.nan,
              resampling=Resampling.average)
    return dst, dst_transform


def separable_closing(z, win_px):
    d = maximum_filter1d(maximum_filter1d(z, win_px, axis=0), win_px, axis=1)
    return minimum_filter1d(minimum_filter1d(d, win_px, axis=0), win_px, axis=1)


def laplace_fill(z, mask, init):
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
            print(f"  SOR converged in {it + 1} iterations")
            break
    else:
        print(f"  SOR hit max iterations, last max update {dmax:.4f} m")
    return f


def seeded_mask(z15, closed, thresh, seeds, edge_margin_west=None):
    """Anomaly mask restricted to components containing canyon seeds."""
    raw = (closed - z15 > thresh) & (z15 < 0.0)
    m = int(round(EDGE_MARGIN_M / DX_FILL))
    raw[:m, :] = raw[-m:, :] = False           # north, south
    raw[:, -m:] = False                        # east
    if edge_margin_west is not None:
        mw = int(round(edge_margin_west / DX_FILL))
        raw[:, :mw] = False                    # west (layer B only)
    labels, nlab = label(raw)
    anom = closed - z15
    r = int(round(SEED_SNAP_M / DX_FILL))
    keep = set()
    for e, n in seeds:
        j = int((e - XMIN) / DX_FILL)
        i = int((YMAX - n) / DX_FILL)
        w = anom[i - r:i + r + 1, j - r:j + r + 1]
        di, dj = np.unravel_index(np.argmax(w), w.shape)
        i2, j2 = i - r + di, j - r + dj
        if labels[i2, j2] == 0:
            print(f"  note: seed E{e:.0f} N{n:.0f} outside this mask "
                  f"(anomaly {w[di, dj]:.1f} m)")
        else:
            keep.add(labels[i2, j2])
    return np.isin(labels, sorted(keep))


def build_fill_surfaces(z1m, transform1m):
    z15, _ = resample(z1m, transform1m, DX_FILL)
    z15 = z15 + NAVD88_TO_MSL

    win_b = int(round(CLOSE_WIN_B_M / DX_FILL)) | 1
    closed_b = separable_closing(z15, win_b)
    mask_b = seeded_mask(z15, closed_b, FILL_THRESH_B, CANYON_SEEDS,
                         edge_margin_west=EDGE_MARGIN_M)
    print(f"layer B: closing {win_b * DX_FILL:.0f} m, mask "
          f"{mask_b.sum() * DX_FILL**2 / 1e6:.2f} km^2")
    fill_b = laplace_fill(z15, mask_b, closed_b)
    zb15 = np.where(mask_b, np.maximum(z15, fill_b), z15)

    # layer C nests on the B-filled bed: only the deep trough remains as an
    # anomaly at the 4 km scale, so C == B outside the deep mask
    win_c = int(round(CLOSE_WIN_C_M / DX_FILL)) | 1
    closed_c = separable_closing(zb15, win_c)
    mask_c = seeded_mask(zb15, closed_c, FILL_THRESH_C, DEEP_SEEDS)
    print(f"layer C: closing {win_c * DX_FILL:.0f} m, deep mask "
          f"{mask_c.sum() * DX_FILL**2 / 1e6:.2f} km^2")
    fill_c = laplace_fill(zb15, mask_c, closed_c)

    return (fill_b.astype(np.float32), mask_b,
            fill_c.astype(np.float32), mask_c)


def upsample_to(dx, a, order):
    factor = DX_FILL / dx
    ny = int(round((YMAX - YMIN) / dx))
    nx = int(round((XMAX - XMIN) / dx))
    b = zoom(a, factor, order=order, grid_mode=True, mode="nearest")
    b = b[:ny, :nx]
    if b.shape != (ny, nx):
        b = np.pad(b, ((0, ny - b.shape[0]), (0, nx - b.shape[1])),
                   mode="edge")
    return b


def west_ramp(nx, dx):
    """0 within WEST_HOLD_M of west edge, ramps to 1 by HOLD+RAMP."""
    x = (np.arange(nx) + 0.5) * dx
    return np.clip((x - WEST_HOLD_M) / WEST_RAMP_M, 0.0, 1.0)[None, :]


def apply_fill(z, fill15, mask15, dx, west_blend):
    fs = upsample_to(dx, fill15, 1)
    mk = upsample_to(dx, binary_dilation(mask15, iterations=1)
                     .astype(np.float32), 1) > 0.25
    zf = np.where(mk, np.maximum(z, fs), z)
    if west_blend:
        w = west_ramp(z.shape[1], dx)
        zf = z + w * (zf - z)
    return zf.astype(np.float32)


def write_celeris_bathy(z, path):
    zz = np.clip(z, -BASE_DEPTH, LAND_CLAMP)
    with open(path, "w") as fh:
        for row in zz[::-1]:
            fh.write("".join(f"{v:15.7e}" for v in row) + "\n")
    return zz


def write_geotiff(z, transform, path):
    prof = dict(driver="GTiff", height=z.shape[0], width=z.shape[1], count=1,
                dtype="float32", crs="EPSG:26911", transform=transform,
                compress="deflate", predictor=3)
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(z.astype(np.float32), 1)


def make_figures(z5, zb5, zc5):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm

    x = XMIN + (np.arange(z5.shape[1]) + 0.5) * DX_WORK
    y = YMAX - (np.arange(z5.shape[0]) + 0.5) * DX_WORK
    ext = [x[0] / 1000, x[-1] / 1000, y[-1] / 1000, y[0] / 1000]
    norm = TwoSlopeNorm(vmin=-550, vcenter=0, vmax=120)
    levels = [-500, -400, -300, -200, -150, -100, -75, -50, -30, -20, -10]

    fig, axes = plt.subplots(1, 4, figsize=(24, 9), constrained_layout=True)

    def panel(ax, zz, title):
        im = ax.imshow(zz, cmap="terrain", norm=norm, extent=ext,
                       origin="upper")
        ax.contour(x / 1000, y / 1000, zz, levels=levels, colors="k",
                   linewidths=0.3, alpha=0.5)
        ax.contour(x / 1000, y / 1000, zz, levels=[0], colors="k",
                   linewidths=1.0)
        ax.set_title(title)
        ax.set_xlabel("Easting (km)")
        ax.set_aspect("equal")
        return im

    panel(axes[0], z5, "A: real (CoNED 1 m, MSL)")
    panel(axes[1], zb5, "B: shallow legs filled (800 m scale)")
    im = panel(axes[2], zc5, "C: canyon fully removed (4 km scale)")
    fig.colorbar(im, ax=axes[:3], label="elevation rel. MSL (m)",
                 shrink=0.75, aspect=45)
    d = zc5 - z5
    imd = axes[3].imshow(np.where(d > 0.01, d, np.nan), cmap="magma_r",
                         extent=ext, origin="upper", vmin=0, vmax=300)
    db = zb5 - z5
    axes[3].contour(x / 1000, y / 1000, np.where(db > 0.01, 1.0, 0.0),
                    levels=[0.5], colors="c", linewidths=0.8)
    axes[3].contour(x / 1000, y / 1000, z5, levels=[0], colors="k",
                    linewidths=1.0)
    axes[3].set_title("C fill thickness (cyan: B extent)")
    axes[3].set_xlabel("Easting (km)")
    axes[3].set_aspect("equal")
    axes[0].set_ylabel("Northing (km)")
    fig.colorbar(imd, ax=axes[3], label="z_C - z_real (m)",
                 shrink=0.75, aspect=45)
    fig.suptitle("Blacks / Scripps-La Jolla canyon domain: three bathymetry "
                 "layers (9 x 12 km, EPSG:26911)", fontsize=14)
    fig.savefig(os.path.join(FIG_DIR, "bathy_checkpoint_maps_v4.png"), dpi=130)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(13, 8), constrained_layout=True)
    n_sec = 3637000.0
    i = int((YMAX - n_sec) / DX_WORK)
    for zz, st, lab in ((z5, "b-", "A real"), (zb5, "r--", "B shallow fill"),
                        (zc5, "g-.", "C full fill")):
        axes[0].plot(x / 1000, zz[i], st, lw=1.2, label=lab)
    axes[0].set_title(f"E-W section at N {n_sec:.0f} (through canyon trunk "
                      f"and Scripps branch)")
    axes[0].set_xlabel("Easting (km)")
    e_sec = 471000.0
    j = int((e_sec - XMIN) / DX_WORK)
    for zz, st, lab in ((z5, "b-", "A real"), (zb5, "r--", "B shallow fill"),
                        (zc5, "g-.", "C full fill")):
        axes[1].plot(y / 1000, zz[:, j], st, lw=1.2, label=lab)
    axes[1].set_title(f"N-S section at E {e_sec:.0f} (across the deep trough)")
    axes[1].set_xlabel("Northing (km)")
    for ax in axes:
        ax.set_ylabel("elev rel MSL (m)")
        ax.grid(alpha=0.3)
        ax.legend()
        ax.axhline(0, color="k", lw=0.5)
    fig.savefig(os.path.join(FIG_DIR, "bathy_checkpoint_sections_v4.png"),
                dpi=140)
    plt.close(fig)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(FIG_DIR, exist_ok=True)

    z1m, t1m = mosaic_aoi()
    fill_b15, mask_b15, fill_c15, mask_c15 = build_fill_surfaces(z1m, t1m)

    grids = {}
    for name, dx in (("work", DX_WORK), ("model", DX_MODEL)):
        z, t = resample(z1m, t1m, dx)
        z = z + NAVD88_TO_MSL
        zb = apply_fill(z, fill_b15, mask_b15, dx, west_blend=False)
        zc = apply_fill(zb, fill_c15, mask_c15, dx, west_blend=True)
        grids[name] = (z, zb, zc, t)
        print(f"{name} dx={dx}: {z.shape[1]}x{z.shape[0]}, "
              f"max fill B {np.nanmax(zb - z):.1f} m, "
              f"C {np.nanmax(zc - z):.1f} m")

    z5, zb5, zc5, t5 = grids["work"]
    for arr, nm in ((z5, "real"), (zb5, "fillB"), (zc5, "fillC")):
        write_geotiff(arr, t5, os.path.join(OUT_DIR, f"blacks_{nm}_5m_msl_v4.tif"))

    zm, zbm, zcm, tm = grids["model"]
    for arr, nm in ((zm, "real"), (zbm, "fillB"), (zcm, "fillC")):
        write_celeris_bathy(arr, os.path.join(OUT_DIR, f"bathy_{nm}_v4.txt"))
    print(f"Celeris grids written: WIDTH={zm.shape[1]} HEIGHT={zm.shape[0]} "
          f"dx=dy={DX_MODEL}")

    # west-boundary identity check (wavemaker column must match across layers)
    hold_px = int(WEST_HOLD_M / DX_MODEL)
    same_b = np.array_equal(zm[:, :hold_px], zbm[:, :hold_px])
    same_c = np.array_equal(zm[:, :hold_px], zcm[:, :hold_px])
    print(f"west {WEST_HOLD_M:.0f} m strip identical: B={same_b} C={same_c}")

    def probe(e, n, lab):
        j = int((e - XMIN) / DX_MODEL)
        i = int((YMAX - n) / DX_MODEL)
        print(f"  probe {lab}: real {zm[i, j]:8.1f}  B {zbm[i, j]:8.1f}  "
              f"C {zcm[i, j]:8.1f}")
    probe(475900, 3637300, "Scripps head axis  ")
    probe(473900, 3637000, "merged trunk       ")
    probe(470000, 3640500, "deep trough        ")
    probe(469200, 3640800, "trough nr west edge")
    probe(475500, 3640000, "Blacks surf zone   ")

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
    with open(os.path.join(OUT_DIR, "config_base_v4.json"), "w") as fh:
        json.dump(config, fh, indent=2)

    make_figures(z5, zb5, zc5)
    print("Figures written to", FIG_DIR)


if __name__ == "__main__":
    main()
