# Tool 2 — 2D cross-shore breaking-wave slice: decision memo

**Status: research only. No build. Awaiting decision.**
Date: 2026-07-22. Prepared for tools.scienceofsurfing.com "First Order" series.

The question this tool answers: *what makes a wave stand up, pitch, and barrel — and why does the same swell spill on one beach and throw on another?* Side-view x–z slice; sliders for wave height, period, and beach/bar profile; shoaling → steepening → overturning.

---

## 0. How claims in this memo were verified

This research session's network policy blocked direct page fetches to almost every non-GitHub host (journals, arXiv, Wikipedia, vendor docs all returned proxy 403). Verification therefore has three tiers, marked throughout:

- **[fetched]** — full text read from a reachable source (GitHub-hosted code, docs, or textbook source files).
- **[snippet]** — claim triangulated across search-result summaries with the URL recorded, but the page itself not read. Treat as probably-right, re-check before quoting in an article.
- **[uncertain]** — could not be verified; do not rely on it.

DOI-resolution checks could not run (network blocked). Nothing below is asserted beyond its tier.

---

## 1. The constraint, verified

The impossible-triangle premise holds up in the literature. Vertical integration forces the free surface to be a single-valued function of x, so **no depth-integrated model (Boussinesq, nonlinear shallow water, non-hydrostatic) can represent an overturning face** — they parameterize breaking with rollers/eddy viscosity instead. Stated as "a restriction shared by all depth-integrated models" in Kazolea & Ricchiuto's review *On wave breaking for Boussinesq-type models* ([math.u-bordeaux.fr/~mricchiu/kr18.pdf](https://www.math.u-bordeaux.fr/~mricchiu/kr18.pdf)) [snippet]; same limitation stated for non-hydrostatic models in Smit et al., *Coastal Engineering* 2013 ([sciencedirect.com](https://www.sciencedirect.com/science/article/abs/pii/S0378383913000215)) [snippet]. Only two-phase Navier–Stokes VOF, particle methods (SPH), or boundary-integral potential-flow codes resolve the curl — and none of those runs live in a browser slider tool at meaningful fidelity. So: **simple + interactive + real breaking physics — pick two.**

---

## 2. Family 1 — Precomputed 2D VOF library (real curl, scrubbed)

**What it is.** Run a small matrix of 2D RANS–VOF surf-zone simulations offline; export the free surface (alpha.water = 0.5 isoline) per timestep; the web page scrubs frames.

**Fidelity: true overturning.** interFoam is OpenFOAM's two-phase incompressible VOF solver (solver header read directly from OpenFOAM-9 source) [fetched]. Published 2D validation against the Ting & Kirby (1994) surf-zone lab experiments exists with a **public, ready-to-run companion repo**: Li, Larsen & Fuhrman (2022), "Reynolds stress turbulence modelling of surf zone breaking waves," *JFM* 937:A7, doi:10.1017/jfm.2022.92 — repo [LiYZPearl/ReynoldsStressTurbulenceModels](https://github.com/LiYZPearl/ReynoldsStressTurbulenceModels) ships `spillingBreaker` and `plungingBreaker` 2D cases run with stock interFoam [fetched]. Case files state: spilling — 212,248 cells, 200 s simulated, max Courant 0.05; plunging — 366,376 cells, 500 s simulated [fetched]. The repo README warns runs "can occasionally blow up" and describes restart procedure [fetched] — this is babysitting-grade CFD, not fire-and-forget.

**Tooling.** [olaFlow](https://github.com/phicau/olaFlow) (successor to IHFOAM) provides wave generation/absorption BCs and flume tutorials; actively maintained — last commit 2025-10-14, compatible through OpenFOAM v2506; GPLv3 per source headers (no top-level LICENSE file) [fetched]. IHCantabria's own [ihFOAM repo](https://github.com/IHCantabria/ihFOAM) is frozen (single commit, 2018) [fetched]; ESI folded equivalent wave BCs into OpenFOAM v1612+ [snippet].

**M1 Mac (16 GB) feasibility.** A native Apple Silicon build exists: [gerlero/openfoam-app](https://github.com/gerlero/openfoam-app) (`brew install gerlero/openfoam/openfoam`, unofficial, macOS 14+) [fetched]. The only M1 benchmark found anywhere is the tiny single-phase pitzDaily tutorial (~6 s native ARM vs ~80 s emulated x86 Docker on an M1 Air) [fetched]. **No source states wall-clock time for a 2D breaking-wave VOF run on Apple Silicon** — one search snippet claimed 2,417–10,364 s per wave period on 0.7–2.6 M-cell meshes but could not be attributed to a paper, so it is unusable [uncertain]. What can be said honestly: a 200,000–370,000-cell case at max Co 0.05 over 200–500 s of simulated time is a long overnight-class run *at minimum*, per case, and every slider combination (H × T × profile) is its own run — the parameter grid multiplies.

**Export.** OpenFOAM's `surfaces` function object with `isoSurface` on `alpha.water = 0.5` writes per-timestep VTK — documented in OpenFOAM source with a verbatim usage example [fetched]. PyVista's `POpenFOAMReader` reads cases per-timestep [fetched]. **VTK → per-frame JSON polyline for the web: no established pipeline exists; it's custom Python scripting** (small, but ours to write and validate). Back-of-envelope (my arithmetic, not sourced): a 2D isoline is a few hundred points per frame; a few hundred frames per clip lands well under 1 MB gzipped per clip — storage is a non-issue.

**Fit.** Real physics, but interactivity collapses to "pick one of N precomputed movies." Pipeline (solver install → case setup → turbulence model choices → stability babysitting → custom exporter) is far above the "one self-contained index.html" bar of the existing tools.

---

## 3. Family 2 — Interactive kinematic/parametric breaker (live schematic)

**What it is.** A canvas-drawn x–z wave whose shape is driven live by published, citable wave-transformation physics — labeled on-page as a schematic, never as CFD.

**Fidelity: schematic — but every driving equation is real and attributable.** Verified components, all implementable in ~100 lines of JS:

- **Dispersion:** ω² = gk·tanh(kh) (Airy) — verified from the LaTeX source of Ardhuin's open textbook *Ocean Waves in Geosciences* ([github.com/ardhuin/waves_in_geosciences](https://github.com/ardhuin/waves_in_geosciences)) [fetched].
- **Shoaling:** energy-flux conservation, Ks = √(Cg0/Cg), shallow limit H ∝ h^(−1/4) (Green's law) — same source [fetched].
- **Breaking onset:** Hb/hb = 0.78 (McCowan 1894) [snippet, corroborated in multiple fetched working codebases]; steepness limit H/L = 0.142·tanh(2πh/L) (Miche 1944) [snippet]; slope-aware γb = 1.56/(1+e^(−19.5m)) (Weggel 1972) [fetched via code].
- **Live breaker-type classifier:** Iribarren number ξ0 = tanβ/√(H0/L0); Battjes (1974, *Proc. 14th ICCE*, doi:10.9753/icce.v14.26) thresholds — spilling ξ0 < 0.5, plunging 0.5–3.3, surging/collapsing > 3.3 (at-breaking variant ξb: 0.4 / 2.0) — definition and thresholds verified from the Ardhuin textbook source [fetched], corroborated by working coastal codes [fetched].
- **The lip itself has analytic pedigree** — this is the surprise of the research. Longuet-Higgins (1982, *JFM* 121:403–424): the forward face of a plunging breaker tends to a **parametric cubic curve** [snippet]. New (1983, *JFM* 130:219–239): the cavity under the overturning crest is "remarkably well approximated" by an **ellipse of aspect ratio √3** [snippet]. Longuet-Higgins (1983): the ejected jet follows a **Dirichlet hyperbola** [snippet]. And from the surfing literature: Mead & Black (2001, *J. Coastal Research* SI 29:51–65) fitted barrel shape from 48 images of 23 surf breaks, defining the **vortex ratio** (length/width) and tying it to seabed gradient [snippet]. A lip drawn from these shapes is not fake CFD — it is *published analytic geometry of plunging breakers*, citable per curve.

**Prior art.** No existing client-side web page doing a physically-annotated side-view shoal→steepen→overturn animation was found [not found — absence claim, searches were extensive but not exhaustive]. Nearest neighbors: Shadertoy 4dy3Dw "2D breaking wave curve" (details unverifiable, site blocked) [uncertain]; joshribakoff/surfsim (browser, top-down, uses ξ and γ=0.78) [fetched]; Thürey et al. 2007 real-time breaking (game-engine technique) [snippet]. Conceptual precedent for the hybrid idea: Mihalef et al. 2004's "Slice Method" (SCA 2004) — animators pick from **a library of 2D Navier–Stokes-simulated breaking-wave slices** [snippet]. Also: GPU Gems ch. 1 documents that Gerstner waves form loops above the steepness sum ΣQωA > 1 [mirror-fetched]; no published case of using that loop deliberately as a breaking lip was found — every source treats it as an artifact to clamp. The New/Longuet-Higgins curves are the better-grounded route anyway.

**Interactivity: fully live.** Every slider drives closed-form math; 60 fps canvas rendering of a polyline is trivial (assessment, not sourced).

**Build cost: near zero.** No solver, no assets, one self-contained index.html — exactly the existing tools' pattern. MATLAB cross-check of the transformation math and Python-generated reference figures fit the house workflow.

**Fit: exact match** — provided the page is labeled schematic and the classifier/annotations carry the real citations.

---

## 4. Family 3 — SPH particle methods

**Fidelity: true overturning, genuinely validated.** Strongest match: Lowe et al. (2019), "Numerical simulations of surf zone wave dynamics using Smoothed Particle Hydrodynamics," *Ocean Modelling* 144:101481 — DualSPHysics vs. lab flume measurements of spilling and plunging breakers ([sciencedirect.com](https://www.sciencedirect.com/science/article/abs/pii/S1463500319301647), [arxiv.org/abs/2002.00827](https://arxiv.org/abs/2002.00827)) [snippet]. Also Makris et al. 2016 (*Ocean Modelling* 98:12–35), De Padova et al. 2019 (*Ocean Engineering* 176), Dalrymple & Rogers 2006 (*Coastal Engineering* 53:141–147) [all snippet].

**M1 Mac feasibility: the deal-breaker.** DualSPHysics GPU acceleration is **CUDA/NVIDIA-only** — wiki: "only an Nvidia CUDA-enabled GPU card is needed" [fetched]; no Metal/OpenCL/SYCL port documented. A CPU/OpenMP mode exists, but official builds and docs cover Windows/Linux only; the sole GitHub issue asking about macOS (#134, 2023) is unanswered [fetched]. So on an M1: CPU-only at best, with an undocumented build [uncertain]. SPHinXsys has macOS CI and 2D wavemaker examples but no surf-zone breaking case [fetched]. Browser-SPH demos (WebGPU-Ocean etc.) are generic splashy fluids — none produces a controlled, physically-meaningful shoaling/overturning wave [fetched/not found].

**Export.** No established pipeline; closest pieces are DualSPHysics' PartVTK/IsoSurface (marching cubes) post-processors [fetched] plus vtk.js in the browser [fetched] — more custom glue than the VOF route, because particles need surface reconstruction first.

**Fit.** Same precomputed-scrub ceiling as VOF, with a weaker toolchain on this specific hardware. Dominated by Family 1 for this project.

---

## 5. Comparison

| | 1 — Precomputed VOF | 2 — Kinematic/parametric | 3 — SPH |
|---|---|---|---|
| **Fidelity** | True curl; published 2D validation vs Ting & Kirby with public case files (Li et al. 2022) | Schematic; every driver (dispersion, shoaling, γ, ξ) and even the lip curves (Longuet-Higgins '82, New '83) are published physics, cited per element | True curl; validated vs lab surf zones (Lowe et al. 2019) |
| **Interactivity** | Scrub a small precomputed matrix; sliders snap to nearest run | Fully live — every slider drives closed-form math at 60 fps | Scrub only; same ceiling as VOF |
| **Build cost (M1, 16 GB)** | Native OpenFOAM exists [fetched]; per-case run time unpublished for M1 [uncertain] but overnight-class at ≥200k cells / maxCo 0.05; custom VTK→JSON exporter; stability babysitting | Hours–days of JS + curve tuning; zero compute; single index.html | Worst path: CUDA GPU unavailable on Apple Silicon [fetched], macOS CPU build undocumented [uncertain] |
| **Fit to "simple demonstration"** | Over the bar's complexity budget as the *primary* tool; viable as a small labeled side-panel later | Exact match to existing tools' pattern | Poor on this hardware; dominated by VOF |

---

## 6. Recommendation (one)

**Build Family 2 as the tool: a live kinematic x–z breaker, labeled "schematic — not a fluid simulation," with every driving element carrying its real citation.** Concretely: sliders for H0, T, and beach/bar profile; the wave transforms via Airy dispersion + shoaling; breaking triggers on γ = Hb/hb (slope-aware via Weggel) and the Miche limit; a live Battjes–Iribarren badge classifies spilling / plunging / surging as you drag; when plunging, the lip is drawn from the published analytic shapes (Longuet-Higgins cubic face, New √3 ellipse cavity, hyperbolic jet), with barrel elongation tied to Mead & Black's vortex-ratio finding. The physics annotations are true; only the *animation* is schematic, and the page says so.

**Optional phase 2 (decide separately, after the tool ships):** a labeled "the real thing" panel with 2–4 precomputed clips from the Li/Larsen/Fuhrman public interFoam cases (one spilling, one plunging), each captioned as RANS–VOF simulation with citation. The cases are public and ready-to-run, and the isoline-export path is documented — but M1 run time is unverified [uncertain], so treat it as an experiment with an abort switch, not a commitment. This mirrors Mihalef's slice-method precedent: a curated library of real 2D slices behind a simple front-end.

**Reject** SPH for this project (CUDA-only GPU path, undocumented macOS builds) and **reject** live CFD of any kind (Section 1 constraint). Do not label the kinematic panel as CFD under any circumstances — the credibility of the series rides on that line staying bright.

---

## 7. Open items / uncertainty register

- M1 wall-clock for a 2D breaking-wave interFoam case: **no published figure exists**; must be measured empirically if phase 2 proceeds [uncertain].
- Shadertoy 4dy3Dw technique/author; the 2009 Gerstner-overturning paper's authors; US Patent 7,561,993 details (title confirmed, contents unread) [uncertain].
- New (1983) √3-ellipse and Longuet-Higgins (1982) cubic verified from abstracts only [snippet] — read the papers before quoting numbers in the article accompanying the tool.
- McCowan 1894 citation volume varies across sources (Phil. Mag. Ser. 5, vol. 38 most common) [uncertain].
- All [snippet]-tier claims should be re-verified from an unrestricted network before any of them appear in published article text.

## Sources (primary, grouped)

**Constraint:** Kazolea & Ricchiuto, [On wave breaking for Boussinesq-type models](https://www.math.u-bordeaux.fr/~mricchiu/kr18.pdf) · Smit et al. 2013, [Coastal Eng.](https://www.sciencedirect.com/science/article/abs/pii/S0378383913000215)
**VOF:** [interFoam solver source](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-9/master/applications/solvers/multiphase/interFoam/interFoam.C) · Li, Larsen & Fuhrman 2022, JFM 937:A7, [companion repo](https://github.com/LiYZPearl/ReynoldsStressTurbulenceModels) · [olaFlow](https://github.com/phicau/olaFlow) · [ihFOAM](https://github.com/IHCantabria/ihFOAM) · [gerlero/openfoam-app](https://github.com/gerlero/openfoam-app) · [OpenFOAM isoSurface sampling](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-9/master/src/sampling/sampledSurface/isoSurface/sampledIsoSurface.H) · [PyVista OpenFOAM reader example](https://github.com/pyvista/pyvista/blob/main/examples/99-advanced/openfoam.py)
**Kinematic:** [Ardhuin, Ocean Waves in Geosciences (source)](https://github.com/ardhuin/waves_in_geosciences) · Battjes 1974, [Surf Similarity, ICCE 14](https://icce-ojs-tamu.tdl.org/icce/article/view/2921) · Galvin 1968, [JGR 73(12)](https://agupubs.onlinelibrary.wiley.com/doi/pdfdirect/10.1029/JB073i012p03651) · Longuet-Higgins 1982, [JFM 121](https://www.cambridge.org/core/journals/journal-of-fluid-mechanics/article/abs/parametric-solutions-for-breaking-waves/6513918A73FA0255C3D51BA2CCDF8DBB) · New 1983, [JFM 130](https://www.cambridge.org/core/journals/journal-of-fluid-mechanics/article/abs/class-of-elliptical-freesurface-flows/A9F414B83321C675C69F9A86F72124DF) · Mead & Black 2001, [JCR SI 29](https://www.researchgate.net/publication/228605528_Predicting_the_breaking_intensity_of_surfing_waves) · Finch, [GPU Gems ch. 1](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models) · Mihalef et al. 2004, [SCA](https://dl.acm.org/doi/10.1145/1028523.1028565) · Thürey et al. 2007, [Pacific Graphics](https://dl.acm.org/doi/10.1109/PG.2007.54) · Miche 1944, [TU Delft record](https://repository.tudelft.nl/record/uuid:6fceef55-d71b-4e3e-a94f-98ff17cb8f91)
**SPH:** [DualSPHysics wiki — running](https://github.com/DualSPHysics/DualSPHysics/wiki/5.-Running-DualSPHysics) · [CPU/GPU implementation](https://github.com/DualSPHysics/DualSPHysics/wiki/4.-CPU-and-GPU-implementation) · [macOS issue #134](https://github.com/DualSPHysics/DualSPHysics/issues/134) · Lowe et al. 2019, [Ocean Modelling 144](https://www.sciencedirect.com/science/article/abs/pii/S1463500319301647) / [arXiv:2002.00827](https://arxiv.org/abs/2002.00827) · [SPHinXsys](https://github.com/Xiangyu-Hu/SPHinXsys) · [VisualSPHysics](https://github.com/EPhysLab-UVigo/VisualSPHysics) · [vtk.js](https://github.com/Kitware/vtk-js)
