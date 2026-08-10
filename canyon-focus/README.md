# Canyon Explorer — Scripps & La Jolla

How much of Blacks is the canyon? This tool runs every swell through a wave model **twice**, once
over the real seafloor off La Jolla and once with the submarine canyon smoothed away, and maps the
difference: where the canyon makes the surf bigger, where it makes it smaller, for every break from
Torrey Pines to Windansea.

Live: **https://tools.scienceofsurfing.com/canyon-focus/**

## What it shows

- **The canyon effect.** Wave height over the real seafloor divided by wave height with the canyon
  erased, for twenty swells (14–20 s periods across five directions from due south to
  west-northwest). Red where the canyon amplifies that swell, blue where it shadows it. Between the
  five modelled directions the map blends neighbouring runs.
- **Refracting wave rays.** Linear-theory ray paths traced live over the packed seafloor, the
  construction first applied to this exact canyon by Munk & Traylor (1947), plus depth contours.
- **Spot readings.** Thirteen named waypoints, including the Blacks entrances and South Peak, each
  with an exact effect reading and a direction sparkline. Grey means the modelled swell arrives too
  weak to read honestly.
- **The experiment.** The real, half-filled, and erased seafloors, and the raw wave-height field of
  each run for the swell you have dialled in.

It shows the shape of the canyon's effect, not a wave-size forecast. All numbers are ratios between
the two oceans; the model's absolute heights are not meaningful by design.

## Data and references

- **Seafloor:** [USGS CoNED Southern California 1 m topobathymetric DEM](https://www.usgs.gov/data/topobathymetric-model-southern-coast-california-and-channel-islands-1930-2014).
- **Wave model:** Celeris, a GPU-accelerated phase-resolving Boussinesq solver. Tavakkol, S. &
  Lynett, P. (2017), *Computer Physics Communications* 217: 117–127.
- **Rays:** Munk, W. H. & Traylor, M. A. (1947), "Refraction of ocean waves: a process linking
  underwater topography to beach erosion," *Journal of Geology* 55(1): 1–26.
- **Canyon wave observations:** Magne, R., et al. (2007), "Evolution of surface gravity waves over a
  submarine canyon," *JGR Oceans* 112, C01002. https://doi.org/10.1029/2005JC003035
- **Land imagery:** Esri World Imagery (Esri, Maxar, Earthstar Geographics, and the GIS User
  Community).

Companion article: [Why is Black's Beach bigger than surrounding breaks?](https://scienceofsurfing.com)

## License

Code: [AGPL-3.0](../LICENSE). The Science of Surfing name, logo, and article content are © Kevin Okun,
all rights reserved, and are not covered by that license.
