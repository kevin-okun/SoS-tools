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
  Kirby-style flume (54k cells, laminar, 4 MPI ranks) in **8.1 min wall-clock on a
  laptop i9-9980HK** (expect variability — sustained load thermally throttles that
  CPU). The first crest shoals, steepens, and breaks at x ≈ 9.5–10.5 m (t ≈ 15 s);
  at this pilot resolution it's a spilling/weakly-plunging crumble, not a clean
  plunging jet. 320 interface frames at even 0.05 s spacing →
  `web-pipeline/frames-shoaling.json` (4.4 MB raw, ~14 KB/frame). Pre-wave surface
  noise ≤ ~0.7 mm rms (was ~4 mm before the two fixes below).
- **Refined surf zone DOES capture overturning** (the headline result). Two
  `refineMesh` passes over x > 6.5 m (0.5 cm × 0.22 cm cells, 158k cells total) turn
  the spilling crumble into a genuine plunging breaker: the lip curls forward at
  t ≈ 14.85 s and **seals an air pocket ≈ 15 × 5 cm** at t ≈ 14.95 s (x ≈ 9.8 m),
  collapsing into splash-up and bubble entrainment by 15.05 s. The coarse mesh never
  closes a pocket. Cost: 80 min for 16 s on 4 ranks (vs 8 min coarse).
- **Multi-breaker clip**: with the absorbing outlet and endTime 30 s (coarse mesh,
  37 min) the flume delivers four breaking events at t ≈ 14.1, 18.9, 23.5, 29.3 s.
- **Flagship run** (`web-pipeline/frames-plunging.json`): refined surf zone +
  absorbing outlet, reached t = 27.6 s of 30 in ~3.5 h on 4 ranks before being
  stopped at the overnight deadline — **three breaking events, all overturning**.
  Peak structure at t = 19.65 s (the second, largest breaker): 9 stacked surface
  layers and 38 sealed air pockets. After the first breaker the surf zone stays
  aerated for the rest of the run, so the timestep never fully recovers — budget
  ~5 h for a full 30 s at this resolution, or refine a narrower band.
- **Web payload**: `decimate_frames.py` (Douglas–Peucker + fragment culling +
  mm rounding) takes a 30 s clip from 8.5 MB to 0.6 MB raw, **~100 KB gzipped**, with
  no visible change to the profile (1009 → 131 points on a breaking frame).

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
  factor shown in the time label), `decimate_frames.py` (web-sizing pass — run this
  before shipping a clip), `frames.json` (Basilisk deep-water run),
  `frames-shoaling.json` (coarse flume, 16 s, 320 frames),
  `frames-plunging.json` (**the good one**: refined + absorbing outlet, 27.6 s,
  552 frames, decimated to 1.4 MB / 352 KB gzipped).
- `figures/` — overnight campaign figures: `fig0` first plunging jet at true aspect
  ratio, `fig1` coarse-vs-refined breaking sequence, `fig2` strongest-overhang frames,
  `fig3` multi-breaker timeline, `fig4` surface-noise comparison, `fig5` decimation
  before/after.

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
- **Surf-zone ripple noise — two stacked causes, both fixed** (A/B-verified in short
  runs, then a full rerun):
  1. *Stair-step initial condition*: `setFields` fills alpha cell-by-cell; on the
     sloped block the waterline crosses cell rows diagonally, seeding ~2 mm rms
     ripples from t = 0. Fixed: `setAlphaField` plane fill (exact sub-cell fractions;
     needs `libs (waveModels);` in controlDict so utilities can parse the wave BCs).
  2. *Spurious air jet along the interface*: interFoam's shared-velocity interface
     cells let tiny pressure imbalances accelerate the 1000×-lighter air to ~3.5 m/s
     in the first 1–2 cells above still water; that laminar "wind" continuously pumps
     ripples onto the shallow surface (isoAdvector/interIsoFoam does NOT help — it's
     momentum-side, not alpha-advection). Fixed: air `nu` raised 100× to 1.48e-3
     (water untouched; air dynamics irrelevant here). Side effect: the air jet was
     what limited the Courant number, so the fix also cut the 16 s run from 36 min to
     8.1 min. Net: slope-region noise 0.17 mm rms at t = 2 s vs 2.9 mm before.
- Parallel interFoam divergence does **not** crash: deltaT collapses to ~1e-50 and the
  run grinds at a fixed sim-time forever. Watchdogs should monitor deltaT, not just
  fatal errors (serial runs die properly with SIGFPE).
- The wet/dry shoreline needs care in interFoam: keep ≥ ~6 cells of water depth at the
  domain end or handle the contact line properly (the committed case truncates at 12 m).
- **End-wall reflection turned out NOT to matter** (tested, contrary to expectation):
  swapping `endWall` for a `shallowWaterAbsorption` outlet leaves the wave-height
  envelope essentially unchanged (6% spatial variation either way, no node/antinode
  pattern) — because breaking dissipates the wave before it reaches the wall. The
  absorbing outlet is still the better setup for long runs, just not a prerequisite.
  Note the naive test — surface rms in the "deep" section — is useless here: that
  window contains the incident wave itself. Use the standing-wave envelope instead.
- **Measuring overturning**: count how many distinct surface heights stack up over a
  1 cm x-bin (1 = single-valued; ≥2 = overturning) plus closed-polyline detection for
  air pockets. Do *not* measure "how far the surface doubles back in x" — the
  extractor's chained polylines are not ordered monotonically in x, so that metric
  reports the whole domain span for every frame, including flat ones.

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
