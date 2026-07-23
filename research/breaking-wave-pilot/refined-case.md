# Refined surf-zone variant (how to reproduce the plunging jet)

The committed `openfoam-case/` is the coarse (2 cm) flume: fast, clean, spilling
breaker. To get the **overturning jet** add two local refinement passes before
`decomposePar`. Cells go to ~0.5 cm x 0.22 cm in the surf zone (158k total).

Add these two dictionaries to `system/`:

`topoSetDict.1` — box over the whole slope:
    actions ( { name refineBox; type cellSet; action new; source boxToCell;
                box (6.5 -1 -0.2) (12.1 1 0.2); } );

`topoSetDict.2` — tighter box around the breaking region:
    actions ( { name refineBox; type cellSet; action new; source boxToCell;
                box (8.0 -1 -0.15) (12.1 1 0.15); } );

`refineMeshDict`:
    set refineBox;
    coordinateSystem global;
    globalCoeffs { tan1 (1 0 0); tan2 (0 0 1); }
    directions ( tan1 tan2 );    // x and z only; y is the empty slab
    useHexTopology yes;
    geometricCut no;
    writeMesh no;

Then, in place of the plain `blockMesh` in `Allrun`:

```bash
blockMesh
topoSet -dict system/topoSetDict.1 && refineMesh -dict system/refineMeshDict -overwrite
topoSet -dict system/topoSetDict.2 && refineMesh -dict system/refineMeshDict -overwrite
```

Two further changes are required:

- `system/fvSolution`: `nNonOrthogonalCorrectors 1;` (refinement hanging nodes push
  max non-orthogonality from 1.6 to 42 degrees; with 0 correctors the pressure
  solution degrades).
- `system/decomposeParDict`: `method scotch;` (drop the `coeffs` block). The `simple`
  2x2 split cuts the refined band unevenly and starves one rank.

Cost, measured on 4 ranks of a laptop i9-9980HK: **80 min for 16 s** (vs 8 min coarse).
After the first breaker the surf zone stays aerated and the timestep never fully
recovers, so a 30 s run is ~5 h. The overnight flagship reached t = 27.6 s in 3.5 h.
