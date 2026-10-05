# Rail Lab

How much does rail shape matter? This tool lets you change a surfboard rail's apex, bottom edge,
thickness, and lean, and shows the lift and drag on it, with error bars, from 51 free-surface CFD
simulations of a rail cross-section.

Live: **https://tools.scienceofsurfing.com/rail-lab/**

## What it shows

- **Explore.** One rail. Lift, drag, and lift-to-drag as you move the sliders, as a percentage of a
  baseline you set and in newtons per 10 cm of rail. The chart plots lift against lean, with the
  simulated cases as green dots and the uncertainty as a band.
- **Compare A / B.** Two rails side by side. Lock sliders to change one variable at a time; the
  readout says whether the difference is larger than the measurement noise.
- **Badges.** Each reading is marked as a simulated case, interpolated between simulated cases, or
  estimated from the deep-water simulations.

The model is a 2D slice held 5.5 cm deep at one speed (3.4 m/s). Percentage differences between
rails transfer to other planing speeds better than absolute forces do. Rocker, outline, and 3D flow
along the rail are not modeled.

## Data and references

- **Simulations:** 51 free-surface RANS runs in [OpenFOAM](https://www.openfoam.com) (interFoam,
  volume-of-fluid) of a 47 cm rail cross-section. Fourteen shape-and-lean combinations were simulated
  directly; values between them are interpolated. Edge and thickness effects come from separate
  deep-water simulations and are applied as adjustments.
- **Validation:** Rezaei, A., Ghassemi, H. & Noshadi, E. (2015), "Determination of the lift and drag
  of 2D planing flat plate riding on the free surface," *Journal of Ocean, Mechanical and Aerospace
  -Science and Engineering-* 26.
- **Validation:** Kramer, M. R., Maki, K. J. & Young, Y. L. (2013), "Numerical prediction of the flow
  past a 2-D planing plate at low Froude number," *Ocean Engineering* 70.
  https://doi.org/10.1016/j.oceaneng.2013.06.004

## License

Code: [AGPL-3.0](../LICENSE). The Science of Surfing name, logo, and article content are © Kevin Okun,
all rights reserved, and are not covered by that license.
