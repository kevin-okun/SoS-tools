#!/usr/bin/env python3
"""Convert Basilisk output_facets streams (with '# t <val>' frame headers) into
JSON frames of chained polylines. Facets arrive as disconnected 2-point
segments; we chain them by endpoint proximity so overturning loops survive.

Usage: facets_to_json.py <facets.txt> <out.json> [meta_json]
"""
import json, sys
from collections import defaultdict


def chain_segments(segs, tol=1e-4):
    """Chain 2-point segments into polylines by snapping endpoints."""
    def key(p):
        return (round(p[0]/tol), round(p[1]/tol))
    adj = defaultdict(list)          # endpoint-key -> list of (seg_idx, end_idx)
    for i, (a, b) in enumerate(segs):
        adj[key(a)].append((i, 0))
        adj[key(b)].append((i, 1))
    used = [False]*len(segs)
    chains = []
    for i in range(len(segs)):
        if used[i]:
            continue
        used[i] = True
        chain = [segs[i][0], segs[i][1]]
        # grow forward from tail, then backward from head
        for endsel, append in ((1, True), (0, False)):
            while True:
                p = chain[-1] if append else chain[0]
                cands = [(j, e) for (j, e) in adj[key(p)] if not used[j]]
                if not cands:
                    break
                j, e = cands[0]
                used[j] = True
                nxt = segs[j][1-e]
                if append:
                    chain.append(nxt)
                else:
                    chain.insert(0, nxt)
        chains.append(chain)
    return chains


def main():
    src, dst = sys.argv[1], sys.argv[2]
    meta = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    frames = []
    t, segs, pts = None, [], []

    def flush_seg():
        nonlocal pts
        if len(pts) >= 2:
            for a, b in zip(pts, pts[1:]):
                segs.append((a, b))
        pts = []

    def flush_frame():
        nonlocal segs
        flush_seg()
        if t is not None and segs:
            chains = chain_segments(segs)
            lines = [[(round(x, 5), round(y, 5)) for x, y in c] for c in chains if len(c) >= 2]
            frames.append({'t': round(t, 4), 'lines': lines})
        segs = []

    with open(src) as f:
        for line in f:
            line = line.strip()
            if line.startswith('# t'):
                flush_frame()
                t = float(line.split()[2])
            elif not line:
                flush_seg()
            else:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        pts.append((float(parts[0]), float(parts[1])))
                    except ValueError:
                        pass
    flush_frame()
    out = dict(meta)
    out['frames'] = frames
    with open(dst, 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    import os
    print(f'{len(frames)} frames, {sum(len(fr["lines"]) for fr in frames)} polylines total '
          f'-> {dst} ({os.path.getsize(dst)//1024} KB)')


if __name__ == '__main__':
    main()
