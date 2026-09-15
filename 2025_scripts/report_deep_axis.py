#!/usr/bin/env -S uv run --python 3.12
# /// script
# dependencies = ["numpy", "z5py", "scipy"]
# ///
"""Report how the deep (inside-hull) shell material is distributed around the
bilateral symmetry plane x = y.

For the deep material (depth > --depth inside the convex hull of the shell) this
prints a histogram of |x - y| (twice the distance to the x = y plane) and the
number of deep voxels within candidate |x-y| half-widths A. Used to choose the
``--axis-width`` of ``clean_shell_left.py`` so that only the central near-axis
mass ("lungs") is removed, not the lateral shell ("arms").

Usage:
    ./report_deep_axis.py --mask <shell.n5> [--depth 15]
"""

import argparse

import numpy as np
import z5py

from clean_shell_left import _finest_level, depth_of, hull_planes

BINS = np.array([0, 50, 100, 150, 200, 250, 300, 400, 600, 10**9])


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mask", required=True, help="Shell mask N5 (finest level used).")
    p.add_argument("--depth", type=float, default=15.0,
                   help="Depth threshold in full-res voxels (default 15).")
    a = p.parse_args()

    A, b = hull_planes(a.mask)
    hist = np.zeros(len(BINS) - 1, dtype=np.int64)
    n_tot = n_deep = 0
    with z5py.File(a.mask, "r") as f:
        tp = f["setup0/timepoint0"]
        ds = tp[_finest_level(tp)]
        for z0 in range(0, ds.shape[0], 32):
            blk = ds[z0:z0 + 32]
            nz = np.nonzero(blk)
            if not nz[0].size:
                continue
            x = nz[2].astype(np.float64)
            y = nz[1].astype(np.float64)
            z = (nz[0] + z0).astype(np.float64)
            d = depth_of(np.stack([x, y, z], axis=1), A, b)
            m = d > a.depth
            n_tot += nz[0].size
            n_deep += int(m.sum())
            hist += np.histogram(np.abs(x[m] - y[m]), bins=BINS)[0]

    print(f"mask={a.mask}")
    print(f"voxels={n_tot} deep(depth>{a.depth:g})={n_deep}")
    print("deep |x-y| histogram, bins 0-50-100-150-200-250-300-400-600-inf:")
    print(" ", hist.tolist())
    cum = np.cumsum(hist)
    for i, width in enumerate((50, 100, 150, 200, 250, 300, 400, 600)):
        print(f"  |x-y|<{width:3d}: {int(cum[i]):9d} deep voxels "
              f"({100.0 * cum[i] / max(1, n_deep):5.1f}% of deep)")


if __name__ == "__main__":
    main()
