# Breaking Wave

What makes a wave spill, plunge, or surge? This tool shows **one wave from deep water to the
sand**, seen from the side: it shortens, stands up, and breaks — as a gentle spill, a pitching
barrel, or a surge up the beach face — depending on the swell you dial in and the beach you
shape.

Live: **https://tools.scienceofsurfing.com/breaking-wave/**

## What it shows

- **Shoaling (first order).** As the wave runs into shallower water its wavelength shortens
  (linear dispersion, ω² = gk·tanh kh) and its height grows (conservation of energy flux,
  Ks = √(Cg₀/Cg)).
- **The break point.** The wave breaks where its height first hits a limit: the depth limit
  H = γh (γ = 0.78 on a flat bottom, slope-adjusted after Weggel) or the steepness limit
  H/L = 0.142·tanh(2πh/L) (Miche), whichever binds first. A dashed line marks the spot and
  names the limit that tripped.
- **Breaker type, live.** The surf similarity parameter ξ₀ = tanβ/√(H₀/L₀) classifies the
  break as the sliders move: spilling below 0.5, plunging from 0.5 to 3.3, surging above
  (Battjes 1974). With the sandbar on, ξ uses the local bottom slope at the break point —
  which is why the same swell plunges harder on the bar.
- **The sandbar.** Toggle it to watch the wave break on the bar, reform across the deep
  trough (a broken wave never grows; it releases when the depth opens back up), and break
  again at the shore — the classic two-stage beach-break day.

## Honesty line: numbers real, drawing schematic

The **numbers** — wavelength, height growth, break location, breaker classification — come
from the published first-order physics above; the JavaScript implementation is cross-checked
against an independent Python solver to machine precision.

The **moving picture** is a labeled schematic, not a fluid simulation. Depth-integrated wave
models cannot represent an overturning surface at all, and two-phase CFD cannot run live in a
web page, so the sharpening crest, the pitching lip, the foam and splash are *drawn* — the
curl's shape follows published descriptions of real plunging breakers (an elliptical cavity
after New 1983; the overturning face after Longuet-Higgins 1982), but no water is being
simulated. The page says so on its face.

Vertical scale is exaggerated (the factor is shown on the canvas, capped at ×18); the breaking
crest itself is drawn in true proportions.

## References

- **Linear dispersion & shoaling:** Airy wave theory; see F. Ardhuin, *Ocean Waves in
  Geosciences* (open textbook). https://github.com/ardhuin/waves_in_geosciences
- **Breaker classification:** Battjes, J. A. (1974), "Surf similarity," *Proc. 14th Int. Conf.
  Coastal Engineering*, 466–480. https://doi.org/10.9753/icce.v14.26 — thresholds on the
  Iribarren number of Iribarren, C. R. & Nogales, C. (1949), "Protection des ports," *XVIIth
  Int. Navigation Congress*, Lisbon.
- **Depth-limited breaking:** McCowan, J. (1894), "On the highest wave of permanent type,"
  *Philosophical Magazine* Ser. 5; slope adjustment: Weggel, J. R. (1972), "Maximum breaker
  height," *J. Waterways, Harbors and Coastal Eng. Div.* 98(4). https://doi.org/10.1061/JWHEAU.0000367
- **Steepness-limited breaking:** Miche, R. (1944), "Mouvements ondulatoires de la mer en
  profondeur constante ou décroissante," *Annales des Ponts et Chaussées* 114.
- **Plunging-lip geometry (shape reference for the drawing):** Longuet-Higgins, M. S. (1982),
  "Parametric solutions for breaking waves," *J. Fluid Mech.* 121: 403–424.
  https://doi.org/10.1017/S0022112082001980 — New, A. L. (1983), "A class of elliptical
  free-surface flows," *J. Fluid Mech.* 130: 219–239. https://doi.org/10.1017/S0022112083001068
- **Barrel shape vs. seabed (surfing literature):** Mead, S. & Black, K. (2001), "Predicting
  the breaking intensity of surfing waves," *J. Coastal Research* SI 29: 51–65.

Model choices and their verification status (including which claims were checked against
which sources) are documented in the research memo at
[`research/breaking-wave-decision-memo.md`](../research/breaking-wave-decision-memo.md).

## License

Code: [AGPL-3.0](../LICENSE). The Science of Surfing name, logo, and article content are © Kevin Okun,
all rights reserved, and are not covered by that license.
