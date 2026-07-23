# Breaking-wave tool: plan for a real-CFD parameter explorer (2026-07-23)

Goal (from Kevin): let people vary **wave size, wavelength, and beach steepness** and
watch how the break changes — spilling, plunging, surging — to build intuition. The
existing `breaking-wave/index.html` already does this with a *schematic* drawing. This
plan replaces the drawing with real CFD while keeping the tool's structure.

Companion to `breaking-wave-decision-memo.md` (why CFD at all) and
`breaking-wave-pilot/README.md` (what we learned making one clip work).

## What already exists and is right

The tool computes the surf-similarity (Iribarren) number
**ξ₀ = tanβ / √(H₀/L₀)**, classifies spilling (< 0.5) / plunging (0.5–3.3) /
surging (> 3.3), and drives sliders for H₀ (0.3–4 m), period, and beach slope
(1:125 → 1:7.7, log scale). Its badge says *"numbers real · drawing schematic"*.
**The work is to make the drawing real.** Physics framing needs no change.

## Two facts that make this affordable

1. **ξ₀ collapses the parameter space.** Breaker *shape* is governed by ξ₀; slope
   additionally sets the visible bathymetry. So the clip library is 2-D
   (slope × ξ₀), ~9 clips — not a 3-D grid over height × period × slope.
2. **Froude similarity: lab-scale runs serve field-scale sliders.** A 7 cm lab wave
   and a 2 m swell at the same ξ₀ break in the same shape, and cost is unchanged
   (cells, timestep and duration all scale together). So we keep running at lab
   scale where Ting & Kirby give us something to check against, and let the tool
   scale the picture.
   *Caveat to state in the UI: air entrainment and foam do NOT Froude-scale — real
   ocean waves are whiter and bubblier than these clips.*

Corollary worth knowing: the pilot's case (1:35, T = 5 s) is the **most expensive
configuration in the whole space** — gentlest slope means the longest ramp, longest
period means the longest domain and most simulated time. Everything in the library
below is cheaper than what we have already run.

## Clip library (9 runs, all ξ₀ < 3.3)

| Slope | T (s) | H₀ (cm) | ξ₀ | Type |
|-------|-------|---------|------|------|
| 1:50  | 1.5 / 2.5 / 4.0 | 7 | 0.14 / 0.24 / 0.38 | spilling ×3 |
| 1:20  | 1.5 / 2.5 / 4.0 | 7 | 0.35 / 0.59 / 0.94 | spilling → plunging |
| 1:8   | 1.5 / 2.5 / 4.0 | 7 / 5 / 4 | 0.89 / 1.75 / 3.12 | plunging, increasingly violent |

Within each slope row, changing the period walks across breaker types — which is the
intuition the tool is meant to deliver.

## Decisions taken (2026-07-23)

- **Snap to nearest clip.** Sliders stay continuous; the clip jumps to the nearest
  computed (slope, ξ₀) case. The jumps themselves reinforce that breaker type comes
  in regimes.
- **Ship spilling + plunging first.** Surging needs the wet/dry shoreline solved
  (the current case deliberately truncates *before* the waterline to dodge it —
  see pilot README). All 9 clips above are ξ₀ < 3.3, so nothing is blocked. Surge
  stays schematic, clearly labelled, until runup works.
- **One overnight, 9 clips**, moderate resolution.

## Must fix before the batch (from the 2026-07-23 audit)

1. **Air viscosity.** Currently ν = 1.48e-3, i.e. dynamic viscosity 148% of water's
   (physical air is 1.5%). Prime suspect for shredding the plunging jet. Test
   physical and 10× (10× keeps the surface clean at ~15% of water's μ).
2. **Sharper numerics.** Euler + `linearUpwind` (tutorial defaults) are diffusive and
   blunt a thin jet; breaking-wave literature uses Crank–Nicolson 0.9 and a less
   diffusive momentum scheme.
3. **Resolution tied to the wave**, not absolute: target ~H/30 in the surf zone so
   every clip in the library is equally resolved.

## New capability needed

- **Parametric case generator**: (H, T, slope) → mesh sized to the wave, refinement
  boxes at the *predicted* break point, wave BCs, timings. Hand-building nine cases
  would repeat exactly the class of subtle error that cost us two days (wrong
  coordinate plane, wrong air viscosity).
- **Wet/dry shoreline** — deferred with the surge regime, but required eventually.

## Sequence

1. **Calibration**: fix viscosity + numerics, verify on the existing refined case
   that the jet becomes coherent. Establishes cost per run.
2. **Generator**: parametric script; check one generated case reproduces the
   calibrated one.
3. **Batch**: 9 runs overnight; extract, decimate to ~200 KB each.
4. **Tool rewrite**: swap the schematic renderer for a clip player keyed on
   (slope, ξ₀); badge becomes "real CFD".
5. *(later)* wet/dry runup → surge clips.

## Verification rules (learned the hard way)

- Never report "air pockets" or "surface layers" as evidence of overturning — a
  numerically shattered interface scores high on both. Filter by cell size first
  (structures < 4 cells across are debris), and check that a feature persists across
  consecutive frames.
- Never measure "how far the surface doubles back in x" — extracted polylines are not
  x-monotonic.
- Check wave-height envelopes on the *main connected surface only*; spray inflates
  the maxima and looks like a mesh artefact.
