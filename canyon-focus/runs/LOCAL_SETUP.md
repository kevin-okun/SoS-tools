# Running the canyon-focus Celeris cases on your local machine

The cloud container has no GPU (WebGPU falls back to CPU emulation at
~1000x slower than a real GPU), so production runs happen locally. Your
machine needs a GPU-capable browser — that's it, plus Python.

## One-time setup

1. **Prereqs**: git, Python 3.10+, and Google Chrome 113+ (or Edge).
   Python packages: `pip install numpy playwright`
   (numpy for case generation; playwright only drives your installed
   Chrome over CDP — no browser download needed.)

2. **Clone both repos**, side by side:

   ```
   git clone https://github.com/kevin-okun/SoS-tools
   cd SoS-tools && git checkout claude/nice-rubin-oa2gnl && cd ..
   git clone https://github.com/plynett/plynett.github.io celeris-webgpu
   ```

   The stock Celeris clone is used unmodified (its CDN scripts load fine
   outside the sandbox).

3. **Unpack the bathymetry grids** (committed gzipped, ~23 MB):

   ```
   cd SoS-tools
   python canyon-focus/runs/unpack_grids_v1.py
   ```

   This produces `canyon-focus/grids/bathy_{real,fillB,fillC}_v4.txt`
   (1200x1600 at 7.5 m, MSL datum).

## Run the first case (checkpoint 3)

The showcase case `T16_D280_real_mono` (16 s swell from 280 deg, real
bathymetry, monochromatic, offshore Hs 1 m) is already committed under
`canyon-focus/cases/`. Run it:

```
python canyon-focus/runs/run_cases_v1.py ^
    --celeris ..\celeris-webgpu ^
    --case canyon-focus\cases\T16_D280_real_mono ^
    --bathy canyon-focus\grids\bathy_real_v4.txt ^
    --out-root canyon-focus\outputs ^
    --headful
```

(macOS/Linux: same command with `/` paths and `\` line continuations.)

Notes:
- `--headful` opens a visible Chrome window so you can watch the waves
  propagate — recommended for the first run. Drop it for batches.
- The driver prints `sim t=... speed=...x realtime ETA ...` every 10 s.
  Sim runs to t=1769 s; on a decent GPU expect ~5-15 min wall time.
- If Chrome isn't found automatically, set `CELERIS_CHROMIUM` to the
  browser executable path.
- Outputs land in `canyon-focus/outputs/T16_D280_real_mono/`:
  `current_Hs.bin` (the significant-wave-height field, float32
  1200x1600), `current_bathytopo.bin`, `current_Hrms.bin`,
  `current_FSmean.bin`, dx/dy/nx/ny.txt, and `run_result.json`.

## QC plot + hand results back for review

```
python canyon-focus/runs/plot_case_v1.py canyon-focus/outputs/T16_D280_real_mono ^
    --bathy canyon-focus/grids/bathy_real_v4.txt ^
    --fig canyon-focus/outputs/T16_D280_real_mono/hs_field.png
```

Then commit the reviewable pieces (not the full binary set) and push:

```
git add canyon-focus/outputs/T16_D280_real_mono/current_Hs.bin ^
        canyon-focus/outputs/T16_D280_real_mono/current_bathytopo.bin ^
        canyon-focus/outputs/T16_D280_real_mono/run_result.json ^
        canyon-focus/outputs/T16_D280_real_mono/hs_field.png
git commit -m "First case output: T16_D280_real_mono"
git push origin claude/nice-rubin-oa2gnl
```

(~15 MB; the cloud session picks it up from there for verification and
the checkpoint review. The full matrix's raw outputs will stay on your
machine — only postprocessed, decimated fields go into the repo.)

## Generating more cases

```
python canyon-focus/runs/make_case_v1.py --period 14 --direction 285 \
    --layer fillB --forcing spread
```

Case IDs follow `T{period}_D{direction}_{layer}_{forcing}`; pass the
matching `--bathy canyon-focus/grids/bathy_{layer}_v4.txt` when running.
`run_cases_v1.py` accepts multiple `--case` arguments per bathy grid and
runs them sequentially. The full matrix generator (and its batching
script) comes after the first-case checkpoint is approved.

## Container-only notes (not needed locally)

The cloud sandbox needed: vendored CDN libraries in the Celeris clone,
`CELERIS_SWIFTSHADER=1` to force the CPU adapter, and the driver's
`index.html` target (that one applies everywhere: `index_headless.html`
has an init bug — an unguarded `refresh-button` listener at
main.js:4851 — that kills its module setup).
