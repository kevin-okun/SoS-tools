#!/usr/bin/env python3
"""Decompress canyon-focus/grids/bathy_*_v4.txt.gz next to themselves.

Cross-platform stand-in for gunzip; run once after cloning:
  python3 canyon-focus/runs/unpack_grids_v1.py
"""

import glob
import gzip
import os
import shutil

GRID_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "grids")

for gz in sorted(glob.glob(os.path.join(GRID_DIR, "*.txt.gz"))):
    out = gz[:-3]
    if os.path.exists(out):
        print(f"exists, skipping: {os.path.basename(out)}")
        continue
    with gzip.open(gz, "rb") as fin, open(out, "wb") as fout:
        shutil.copyfileobj(fin, fout)
    print(f"unpacked {os.path.basename(out)} "
          f"({os.path.getsize(out) / 1e6:.0f} MB)")
