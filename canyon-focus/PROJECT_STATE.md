# Canyon-focus tool — project state handoff

Purpose of this file: full working context for continuing this project in
a fresh Claude Code session (originally developed in a cloud session;
continuing locally on Kevin's Mac in `~/SoS-canyon`). Read this before
doing anything.

## What is being built

A static web tool for tools.scienceofsurfing.com answering "How do
underwater canyons make some breaks bigger?" at Blacks Beach (Scripps /
La Jolla submarine canyon). Same architecture as the existing First Order
tools: PRECOMPUTED Celeris-WebGPU (extended Boussinesq, MIT, Lynett/USC)
runs -> stored reduced fields -> client-side snap-slider explorer. No live
solver in the browser.

Displayed metric: amplification factor Hs_local / Hs_offshore
(dimensionless). Controls: period slider, direction slider (both SNAP to
computed cases, never interpolate fields), bathymetry 3-way toggle +
difference mode, monochromatic/spread forcing toggle. Nothing else.

## Locked decisions (do not relitigate)

- Bathymetry source: USGS CoNED SoCal 1-m Topobathy DEM (2016), tiles
  I_14+I_15, from NOAA's noaa-nos-coastal-lidar-pds S3 bucket.
- Domain: UTM 11N (EPSG:26911) E 468500-477500, N 3632000-3644000
  (9x12 km); Celeris grid 1200x1600 at dx=dy=7.5 m; MSL datum
  (NAVD88 -0.775 m per NOAA station 9410230); depth clamp -500 m,
  land clamp +20 m.
- THREE bathymetry layers (user-approved): A real; B shallow canyon legs
  filled (800 m morphological closing scale); C canyon fully removed
  (4 km scale nested on B, fill reaches domain edge). West 300 m strip
  bit-identical across layers (+900 m ramp) so wavemaker depths match.
- All analysis in PYTHON (no MATLAB anywhere).
- Run matrix (pending final bins): periods ~8-20 s x directions across
  the Blacks window (~250-290 deg compass-from) x 3 layers x
  {mono, spread}. All three layers confirmed in matrix by user.
- Offshore Hs = 1.0 m for all runs (linear-regime choice).
- Licensing: our code AGPL-3.0; preserve Celeris MIT notice; cite
  Tavakkol & Lynett 2017 (Comput. Phys. Commun. 217:117-127) and the
  2026 Celeris-WebGPU JWPED paper (PDF in celeris repo docs/).

## Phase status

- Phase 0 (bathy research): DONE. CoNED chosen (user pick, "Option A").
  Notable negatives: CUDEM has NO SoCal tiles; USGS CSMP 2-m map series
  was never published for La Jolla; CDIP publishes no open bathy grid.
- Phase 1 (grids): DONE and user-approved at checkpoint. Builder:
  prep/prep_bathy_v4.py (v1-v3 kept for method history). Products
  committed gzipped in grids/ (bathy_{real,fillB,fillC}_v4.txt.gz +
  config_base_v4.json).
- Phase 2 (runs): IN PROGRESS. Harness done: runs/{wavegen_v1, make_case_v1,
  run_cases_v1, plot_case_v1, unpack_grids_v1}.py + LOCAL_SETUP.md.
  Cloud container has no GPU (SwiftShader ~1000x too slow for real cases)
  so ALL production runs happen on Kevin's Mac.
  CURRENT TASK: get first case T16_D280_real_mono (committed under
  cases/) running locally. Debug history below. After it succeeds:
  QC plot, checkpoint review with Kevin, THEN matrix generator + batch.
- Phase 3 (post-process, Python): NOT STARTED. Amplification field per
  case; Hs_offshore normalization from the model's own field (offshore
  strip away from canyon influence — exact definition TBD); decimate to
  <=400x400; compact storage (float16/PNG); manifest JSON; report total
  size BEFORE committing (STOP if >~50 MB).
- Phase 4 (web tool): NOT STARTED. Static HTML/JS, GitHub Pages, reuse
  swell-window rendering approach; footer: AGPL-3.0 + Celeris MIT +
  both citations.

## Local-run debug state (the immediate task)

Sequence so far on the Mac (~/SoS-canyon clone, branch
claude/nice-rubin-oa2gnl; stock celeris clone at ~/celeris-webgpu):
1. ECONNREFUSED on CDP connect -> fixed (readiness poll, first-run flags).
2. set_input_files("#bathymetryFile") timed out at 30 s — first attempt
   to upload the 29 MB bathy.txt (container smoke case was only 2 MB).
   Fix pushed (untested yet): 300 s upload timeout, auto-dismiss dialogs,
   screenshot saved to the case output dir on any exception.
If uploads still stall: suspect Playwright file-payload transfer over
connect_over_cdp; alternatives — serve the case+grids dirs over the
local HTTP server and inject files via in-page fetch()+DataTransfer, or
drive Chrome via playwright's own launch() (must verify WebGPU works in
Playwright-managed headless=new; in the cloud it only worked via manual
launch + connect_over_cdp; --headful sidesteps headless issues).

## Hard-won technical facts (verified from Celeris source, do not re-derive)

- Automation contract (matches stock automation/run_WebGPU.py): upload
  config.json / bathy.txt / waves.txt via input IDs configFile,
  bathymetryFile, waveFile; click start-simulation-btn (dispatch via JS —
  actionability fails on hidden panels). Trigger keys go INSIDE
  config.json. Progress: browser downloads current_time*.txt; completion:
  completed.txt; outputs downloaded to the browser download dir (driver
  routes via CDP Browser.setDownloadBehavior).
- Drive index.html, NOT index_headless.html (the latter dies at
  main.js:4851 — unguarded refresh-button listener kills module init).
- Export trigger sequence (all inside config.json): trigger_writeWaveHeight=1,
  trigger_resetMeans_time < trigger_resetWaveHeight_time <
  trigger_writeWaveHeight_time; at write time the page downloads
  dx/dy/nx/ny.txt + 12 .bin surfaces + completed.txt.
- current_Hs.bin = 4*sigma of demeaned eta (true spectral Hs, Rayleigh),
  float32 WIDTH*HEIGHT, row-major, row 0 = SOUTH (same as bathy.txt line
  order). current_Hrms.bin = 2.829*sigma. Channel indexing is 1-based
  rgba (ch3=b=Hs).
- bathy.txt: HEIGHT lines (south->north), WIDTH values per line
  (west->east), bed elevation (negative = submerged), rel. seaLevel=0.
- waves.txt: "[NumberOfWaves] N" + separator + per line: amplitude(m),
  period(s), direction(rad, math CCW from +x=east), phase(rad).
  incident_wave_type=-1 in config = use uploaded file.
- Direction mapping: compass-from D -> theta_math_deg = 270 - D
  (D=280 -> -10 deg). West wavemaker (type 2); east wall (0); N/S sponges
  (type 1, OUR choice — the author's Scripps_Canyon example uses walls);
  BoundaryWidth 20.
- TMA spread generator (wavegen_v1.py) replicates js/Wave_Generator.js
  exactly: JONSWAP gamma 3.3, 100 freqs on [fp/3,3fp], 1% truncation,
  Mitsuyasu s=50(f/fp)^5 / 50(f/fp)^-2.5, dirs peak±20 deg step 5,
  a=sqrt(2 E df); phases seeded per (period,direction) so bathy layers
  see identical component phases.
- Trigger timing rule (make_case_v1.py): Cg=0.7806T; t_arr=9000/Cg;
  resetMeans=t_arr+8T; resetWH=+120 s; write=+50T (mono) / +75T (spread).
- Oblique-case shadow wedges: at theta=+/-20 deg a ~3.3 km triangular
  wedge along the S (resp. N) boundary lacks full wave exposure. Blacks +
  Scripps pier region stays clean; crop display region in Phase 3/4.
- Cloud-only workarounds (NOT needed locally): vendored gl-matrix/gif.js/
  chart.js in celeris clone (proxy blocks CDNs), CELERIS_SWIFTSHADER=1.

## Cost model for the matrix (to finalize with Kevin)

~95k timesteps/case at 7.5 m (dt~0.021 s, sim ~1800-2100 s). On an
Apple-silicon GPU expect minutes/case (measure the first case!). Full
7 periods x 9 dirs x 3 layers x 2 forcings = 378 cases. Options if too
slow: fewer direction bins for short periods, base_depth clamp 300 m
(+23% dt), dx=15 m for a pilot matrix (author's own resolution for this
site), trim west margin. Present numbers to Kevin after first case.

## Workflow protocol with Kevin

- Checkpoints (STOP and wait): after first single case (show Hs field);
  before batch; report total stored size before committing binaries
  (>~50 MB = stop); show grids before new runs.
- Never claim a run/export succeeded without verifying the file on disk
  (sizes: Hs.bin must be 4*1200*1600 = 7,680,000 bytes).
- Never interpolate between cases; never fabricate bathymetry; flag gaps.
- Versioned filenames (script_v2.py etc.) for meaningful method changes.
- Raw run outputs stay on the Mac (gitignored except reviewed pieces);
  only postprocessed compact fields enter the repo.
