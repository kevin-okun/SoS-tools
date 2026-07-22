# Breaking-wave pilot: real CFD → web pipeline (2026-07-22)

Proof-of-concept from the cloud-session pilot: a **real two-phase Navier–Stokes/VOF
breaking wave**, its free-surface interface exported frame by frame, converted to JSON,
and played back in a web scrubber. Companion to `../breaking-wave-decision-memo.md`
(phase-2 "the real thing" route).

## Headline results (measured in a 4-core cloud container)

- **Basilisk NS-VOF breaking Stokes wave** (`basilisk-case/mywave.c`, derived from the
  distribution test `src/test/stokes-ns.c`): adaptive level 9 (512² effective), 3 wave
  periods, 121 interface frames — **402 s wall-clock on 4 OpenMP threads** (4,002 steps;
  see `basilisk-case/run-stats.log`). The lip genuinely overturns, seals an air pocket,
  and entrains bubbles (`lip_zoom.png`, `overturn.png`).
- **JSON payload**: 121 frames → 1.3 MB raw (`web-pipeline/frames.json`), ~11 KB/frame
  before gzip/decimation. Well within static-site budget per clip.
- **Caveat**: this clip is a deep-water Stokes-instability breaker, not a shoaling
  surf-zone breaker. The shoaling (Ting & Kirby) case is built but needs a working
  OpenFOAM (below) or a Basilisk bathymetry setup (next step).

## What's in here

- `basilisk-case/` — `mywave.c` (compile: `qcc -O2 -fopenmp mywave.c -o mywave -lm`,
  needs `stokes.h` from the Basilisk source tree next to it; source mirror:
  https://github.com/comphy-lab/basilisk-C, build `basilisk-source/src` with
  `ln -s config.gcc config && make qcc`).
- `openfoam-case/` — 2D Ting & Kirby-style flume for **interFoam** (ESI v1912-flavor
  dictionaries): H = 0.128 m, T = 5.0 s, depth 0.4 m, 1:35 slope (published plunging
  parameters from the Li/Larsen/Fuhrman JFM 2022 companion repo,
  https://github.com/LiYZPearl/ReynoldsStressTurbulenceModels); ESI `cnoidal` wave
  generation with active absorption; laminar; ~54k cells; domain truncated at x = 12 m
  (depth 5.7 cm) before the waterline — see "known issues" below.
- `web-pipeline/` — `facets_to_json.py` (Basilisk facets → chained-polyline JSON frames;
  keeps multivalued loops/bubbles), `extract_isolines.py` (same idea for OpenFOAM cases
  via PyVista contouring, works on decomposed cases), `scrubber.html` (prototype player;
  serve the folder and open, or drag a frames JSON onto it), `frames.json` (the real run).

## Known issues found during the pilot

- **Ubuntu 24.04 apt package `openfoam` (v1912.200626) is broken**: (1) any use of the
  function-object machinery dies in an OSHA1stream error — workaround
  `-noFunctionObjects`; (2) fatal: **any non-rectilinear mesh blows up** (still water on
  a tilted-bottom box diverges with velocity growing ~3× per step; flat box identical
  settings runs clean). Bathymetry needs tilted cells, so this package cannot run the
  flume. Use upstream OpenFOAM (Docker image or source build) instead.
- The wet/dry shoreline needs care in interFoam: keep ≥ ~6 cells of water depth at the
  domain end or handle the contact line properly (the committed case truncates at 12 m).

## Reproducing / continuing

1. **Basilisk** (fastest): clone the mirror, build `qcc`, compile `mywave.c`, run
   `OMP_NUM_THREADS=<n> ./mywave 9 2> facets.txt`, then
   `python3 web-pipeline/facets_to_json.py facets.txt frames.json '{...meta...}'`.
2. **OpenFOAM in Docker** (for the shoaling flume): run `openfoam-case/` with an
   upstream image. Dictionaries are ESI-flavor (v1912+); for Foundation-flavor images
   (9/10/11/12) the wave BC names/syntax differ and need a one-time port.
3. Next simulation step per the memo: sloped-bathymetry breaker (the surf-zone story) —
   either the OpenFOAM flume above, or a Basilisk beach case, then the same pipeline.

All measured claims above come from this pilot's own runs; solver/version citations are
in the decision memo.
