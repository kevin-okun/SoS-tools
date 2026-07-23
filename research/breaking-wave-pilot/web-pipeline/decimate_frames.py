#!/usr/bin/env python3
"""Shrink a frames JSON for web delivery without changing what the eye sees.

Three levers, in order of payoff:
  1. drop sub-visual fragments  (spray droplets a few cells across; --min-span)
  2. simplify each polyline     (Douglas-Peucker; --tol)
  3. round coordinates          (--dp, default 3 = mm precision)

Usage: decimate_frames.py <in.json> <out.json> [--tol 0.002] [--min-span 0.01]
                          [--dp 3] [--every 1]
"""
import json, os, sys


def rdp(pts, tol):
    """Douglas-Peucker simplification, iterative (recursion blows the stack on
    the 1000-point polylines these cases produce)."""
    n = len(pts)
    if n < 3:
        return pts
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        ax, az = pts[i]
        bx, bz = pts[j]
        dx, dz = bx - ax, bz - az
        norm = (dx * dx + dz * dz) ** 0.5
        worst, wi = -1.0, -1
        for k in range(i + 1, j):
            px, pz = pts[k]
            if norm == 0:
                d = ((px - ax) ** 2 + (pz - az) ** 2) ** 0.5
            else:
                d = abs(dx * (az - pz) - (ax - px) * dz) / norm
            if d > worst:
                worst, wi = d, k
        if worst > tol:
            keep[wi] = True
            stack.append((i, wi))
            stack.append((wi, j))
    return [p for p, k in zip(pts, keep) if k]


def span(line):
    xs = [p[0] for p in line]; zs = [p[1] for p in line]
    return max(max(xs) - min(xs), max(zs) - min(zs))


def main():
    src, dst = sys.argv[1], sys.argv[2]

    def opt(name, default, cast=float):
        return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default

    tol = opt("--tol", 0.002)
    min_span = opt("--min-span", 0.01)
    dp = opt("--dp", 3, int)
    every = opt("--every", 1, int)

    d = json.load(open(src))
    frames_in = d["frames"][::every]
    pts_before = sum(len(l) for fr in frames_in for l in fr["lines"])
    lines_before = sum(len(fr["lines"]) for fr in frames_in)

    out = []
    for fr in frames_in:
        lines = []
        for line in fr["lines"]:
            if min_span > 0 and span(line) < min_span:
                continue
            simple = rdp(line, tol)
            simple = [[round(x, dp), round(z, dp)] for x, z in simple]
            # drop consecutive duplicates created by rounding
            dedup = [simple[0]]
            for p in simple[1:]:
                if p != dedup[-1]:
                    dedup.append(p)
            if len(dedup) >= 2:
                lines.append(dedup)
        out.append({"t": fr["t"], "lines": lines})

    d["frames"] = out
    d.setdefault("decimation", {}).update(
        {"tol_m": tol, "min_span_m": min_span, "decimals": dp, "frame_stride": every})
    json.dump(d, open(dst, "w"), separators=(",", ":"))

    pts_after = sum(len(l) for fr in out for l in fr["lines"])
    lines_after = sum(len(fr["lines"]) for fr in out)
    print(f"{len(frames_in)} frames | polylines {lines_before} -> {lines_after} | "
          f"points {pts_before} -> {pts_after} ({pts_after/pts_before*100:.0f}%)")
    print(f"{os.path.getsize(src)//1024} KB -> {os.path.getsize(dst)//1024} KB")


if __name__ == "__main__":
    main()
