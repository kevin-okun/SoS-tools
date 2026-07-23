# Breaking-wave pilot: real CFD → web pipeline (2026-07-22)

Proof-of-concept: a **real two-phase Navier–Stokes/VOF breaking wave**, its
free-surface interface exported frame by frame, converted to JSON, and played back in
a web scrubber. Companion to `../breaking-wave-decision-memo.md` (phase-2 "the real
thing" route). Started in a cloud session (Basilisk deep-water clip); completed
locally in Docker (OpenFOAM shoaling flume, same day).

## Headline results (measured)

- **Basilisk NS-VOF breaking Stokes wave** (`basilisk-case/mywave.c`, derived from the
  distribution test `src/test/stokes-ns.c`): adaptive level 9 (512² effective), 3 wave
  periods, 121 interface frames — **402 s wall-clock on 4 OpenMP threads** (4,002 steps;
  see `basilisk-case/run-stats.log`). The lip genuinely overturns, seals an air pocket,
  and entrains bubbles (`lip_zoom.png`, `overturn.png`).
- **JSON payload**: 121 frames → 1.3 MB raw (`web-pipeline/frames.json`), ~11 KB/frame
  before gzip/decimation. Well within static-site budget per clip.
- **OpenFOAM interFoam shoaling breaker** (`openfoam-case/`, run in the
  `opencfd/openfoam-default:2412` Docker image): the full 16 s of the Ting &
  Kirby-style flume (54k cells, laminar, 4 MPI ranks) in **36 min wall-clock on a
  laptop i9-9980HK** (expect variability — sustained load thermally throttles that
  CPU). The first crest shoals, steepens, and breaks at x ≈ 9.5–10.5 m (t ≈ 15 s);
  at this pilot resolution it's a spilling/weakly-plunging crumble, not a clean
  plunging jet. 320 interface frames at even 0.05 s spacing →
  `web-pipeline/frames-shoaling.json` (4.6 MB raw, ~14 KB/frame).
- **Timing note**: with the 5 s ramp and 22 m of propagation, endTime 16 s captures
  exactly one breaking event, ending just as the bore reaches the end wall. For a
  multi-breaker loopable clip, set endTime ≈ 26–30 s (~2× the compute).

## What's in here

- `basilisk-case/` — `mywave.c` (compile: `qcc -O2 -fopenmp mywave.c -o mywave -lm`,
  needs `stokes.h` from the Basilisk source tree next to it; source mirror:
  https://github.com/comphy-lab/basilisk-C, build `basilisk-source/src` with
  `ln -s config.gcc config && make qcc`).
- `openfoam-case/` — 2D Ting & Kirby-style flume for **interFoam** (ESI-flavor
  dictionaries, verified on v2412): H = 0.128 m, T = 5.0 s, depth 0.4 m, 1:35 slope
  (published plunging parameters from the Li/Larsen/Fuhrman JFM 2022 companion repo,
  https://github.com/LiYZPearl/ReynoldsStressTurbulenceModels); ESI `cnoidal` wave
  generation with active absorption; laminar; ~54k cells; domain truncated at x = 12 m
  (depth 5.7 cm) before the waterline — see "known issues" below. Built in the **x–z
  plane (vertical = z)** — this is load-bearing, see known issues.
- `web-pipeline/` — `facets_to_json.py` (Basilisk facets → chained-polyline JSON frames;
  keeps multivalued loops/bubbles), `extract_isolines.py` (same idea for OpenFOAM cases
  via PyVista contouring, works on decomposed cases), `scrubber.html` (prototype player;
  serve the folder and open, or drag a frames JSON onto it — auto vertical exaggeration,
  factor shown in the time label), `frames.json` (Basilisk deep-water run),
  `frames-shoaling.json` (OpenFOAM flume run, 320 frames × 0.05 s).

## Known issues found during the pilot

- **ESI waveModels hard-code vertical = z.** The wave-generation BCs (`waveVelocity` /
  `waveAlpha`) measure the water column from the *z-coordinates* of the inlet patch
  (`src/waveModels/waveModel/waveModel.C`: `zMin_`/`zMax_`/`zSpan_`). A 2D flume built
  in the x–y plane (z as the thin empty direction) gets nonsense paddle levels, grows
  an exponential air jet at the inlet's top corner, and diverges — deterministically at
  t ≈ 0.32 s for this case, on flat *and* sloped meshes, serial and parallel. The cloud
  session's first diagnosis (broken apt package / "tilted meshes blow up") was wrong;
  the shipped `laminar/waves/cnoidal` tutorial (x–z, same BCs and numerics) runs clean
  in the same image. The committed case is now correctly x–z with g = (0 0 −9.81).
  (The apt v1912 OSHA1stream function-object bug was real, but moot in Docker.)
- **Stair-step initial condition on the slope**: `setFields` fills alpha cell-by-cell,
  and on the sloped block the waterline crosses cell rows diagonally, so the run starts
  with ~4 mm ripples trapped over the slope (visible at high vertical exaggeration,
  ~5% of the incoming wave height). Fix for a production run: initialise with the
  `setAlphaField` utility (exact fractional fill) instead.
- Parallel interFoam divergence does **not** crash: deltaT collapses to ~1e-50 and the
  run grinds at a fixed sim-time forever. Watchdogs should monitor deltaT, not just
  fatal errors (serial runs die properly with SIGFPE).
- The wet/dry shoreline needs care in interFoam: keep ≥ ~6 cells of water depth at the
  domain end or handle the contact line properly (the committed case truncates at 12 m).
  The end wall reflects — fine for one breaker in 16 s; for longer runs consider a
  `shallowWaterAbsorption` outlet like the tutorial's.

## Reproducing / continuing

1. **Basilisk** (fastest): clone the mirror, build `qcc`, compile `mywave.c`, run
   `OMP_NUM_THREADS=<n> ./mywave 9 2> facets.txt`, then
   `python3 web-pipeline/facets_to_json.py facets.txt frames.json '{...meta...}'`.
2. **OpenFOAM in Docker** (for the shoaling flume; verified end to end):
   `docker run --rm -v "$PWD/openfoam-case":/case opencfd/openfoam-default:2412 bash -c 'cd /case && ./Allrun'`
   (the image entrypoint ignores `docker run -w`, hence the `cd`). Then extract frames:
   `python3 web-pipeline/extract_isolines.py openfoam-case web-pipeline/frames-shoaling.json`
   (needs `pip install pyvista`; reads the decomposed case directly, no reconstructPar).
   Dictionaries are ESI-flavor; for Foundation-flavor images (9/10/11/12) the wave BC
   names/syntax differ and need a one-time port.
3. Next simulation step per the memo: sloped-bathymetry breaker (the surf-zone story) —
   either the OpenFOAM flume above, or a Basilisk beach case, then the same pipeline.

All measured claims above come from this pilot's own runs; solver/version citations are
in the decision memo.
