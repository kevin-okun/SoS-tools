# Swell Window Explorer

Which swell directions can actually reach your break? This tool maps the **swell window**, the
arc of open ocean a break can see, for ten well-known Southern California spots between Point
Conception and San Diego, computed over the real seafloor.

Live: **https://tools.scienceofsurfing.com/swell-window/**

## What it shows

- **Swell window (first order).** Straight sight lines from each break out to open water, using the
  real island and coastline outlines traced from bathymetry. Whatever sits inside the arc (an
  island, a headland, the coast) blocks the swell behind it.
- **Refraction.** Turn it on to trace every path a swell of a given period can take to reach the
  break, bent by the seafloor. Longer-period swells feel the bottom sooner and bend more, so the
  fan of paths reshapes with period.
- **Along-coast window.** The window computed every 2 km of shoreline, measured from a standard
  3 km offshore.

It is geometry, not a forecast. The rays show how waves turn, not how big they get; diffraction is
described in the article but not drawn here.

## Data and references

- **Seafloor:** Global Multi-Resolution Topography (GMRT) synthesis. Ryan, W. B. F., et al. (2009),
  *Geochemistry, Geophysics, Geosystems* 10, Q03014. https://www.gmrt.org
- **Island blocking / bight wave model:** O'Reilly, W. C. & Guza, R. T. (1993), "A comparison of two
  spectral wave models in the Southern California Bight," *Coastal Engineering* 19(3): 263–282.
  https://doi.org/10.1016/0378-3839(93)90032-4 — run operationally by the Coastal Data Information
  Program ([CDIP](https://cdip.ucsd.edu), Scripps Institution of Oceanography).
- **Diffraction:** Penney, W. G. & Price, A. T. (1952), "The diffraction theory of sea waves and the
  shelter afforded by breakwaters," *Phil. Trans. R. Soc. A* 244(882): 236–253.
  https://royalsocietypublishing.org/doi/10.1098/rsta.1952.0003

Companion article: [Which swell directions can actually reach your break?](https://scienceofsurfing.com)

## License

Code: [AGPL-3.0](../LICENSE). The Science of Surfing name, logo, and article content are © Kevin Okun,
all rights reserved, and are not covered by that license.
