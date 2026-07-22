#!/usr/bin/env python3
"""Extract the alpha.water = 0.5 free-surface isoline from an OpenFOAM case,
one JSON frame per saved timestep. The surface is kept as a list of polyline
segments (NOT a height function) so overturning/multivalued shapes survive.

Usage: extract_isolines.py <case_dir> <out_json> [--every N]
"""
import json, sys, os
import numpy as np
import pyvista as pv


def polylines_from_slice(sl):
    """Order the VTK line cells of a slice-contour into connected polylines."""
    pts = sl.points
    lines = sl.lines  # vtk encoding: [n, i0, i1, n, i0, i1, ...]
    segs = []
    i = 0
    while i < len(lines):
        n = lines[i]
        segs.append(tuple(lines[i+1:i+1+n]))
        i += n + 1
    # build adjacency and walk chains
    from collections import defaultdict
    adj = defaultdict(list)
    for a, b in [(s[0], s[-1]) for s in segs if len(s) >= 2]:
        adj[a].append(b)
        adj[b].append(a)
    unused = set((s[0], s[-1]) for s in segs if len(s) >= 2)
    chains = []
    while unused:
        a, b = unused.pop()
        chain = [a, b]
        grew = True
        while grew:
            grew = False
            for (c, d) in list(unused):
                if c == chain[-1]:
                    chain.append(d); unused.discard((c, d)); grew = True
                elif d == chain[-1]:
                    chain.append(c); unused.discard((c, d)); grew = True
                elif d == chain[0]:
                    chain.insert(0, c); unused.discard((c, d)); grew = True
                elif c == chain[0]:
                    chain.insert(0, d); unused.discard((c, d)); grew = True
        chains.append(chain)
    out = []
    for ch in chains:
        xy = [(round(float(pts[i][0]), 4), round(float(pts[i][1]), 4)) for i in ch]
        if len(xy) >= 2:
            out.append(xy)
    return out


def main():
    case, out_json = sys.argv[1], sys.argv[2]
    every = int(sys.argv[sys.argv.index('--every')+1]) if '--every' in sys.argv else 1
    foam = os.path.join(case, 'case.foam')
    open(foam, 'a').close()
    reader = pv.POpenFOAMReader(foam)
    reader.case_type = 'decomposed'
    reader.cell_to_point_creation = True
    times = [t for t in reader.time_values if t > 0][::every]
    frames = []
    for t in times:
        reader.set_active_time_value(t)
        mesh = reader.read()['internalMesh']
        sl = mesh.slice(normal='z', origin=(0, 0, 0.05))
        try:
            iso = sl.contour([0.5], scalars='alpha.water')
        except Exception:
            continue
        if iso.n_points == 0:
            continue
        frames.append({'t': round(float(t), 3), 'lines': polylines_from_slice(iso)})
        print(f'  t={t:7.3f}  segments={len(frames[-1]["lines"])}  pts={iso.n_points}', flush=True)
    meta = {
        'case': os.path.basename(os.path.abspath(case)),
        'wave': {'H': 0.128, 'T': 5.0, 'depth': 0.4, 'slope': '1:35',
                 'reference': 'Ting & Kirby (1994) plunging case parameters; ESI cnoidal generation'},
        'solver': 'interFoam (OpenFOAM v1912), laminar, 2D, pilot resolution',
        'frames': frames,
    }
    with open(out_json, 'w') as f:
        json.dump(meta, f, separators=(',', ':'))
    print(f'{len(frames)} frames -> {out_json} ({os.path.getsize(out_json)//1024} KB)')


if __name__ == '__main__':
    main()
