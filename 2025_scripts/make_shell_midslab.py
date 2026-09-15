#!/usr/bin/env -S uv run --python 3.12
# /// script
# dependencies = ["numpy", "z5py"]
# ///
"""Extract a thin slab of the shell around the left/right (symmetry) plane.

Keeps only shell voxels within ``--half-width`` full-res voxels of the cut plane
that produced the left/right halves (normal = the measured ``LR`` axis, through
the shell centroid). Viewed along ``LR`` the slab projects to the shell's
mid-sagittal cross-section: the outer "egg" outline plus any central "lungs".

The output mirrors the source pyramid (levels, shapes, chunks, group/dataset
attributes) with uint8 + gzip + fillvalue 0, exactly like
``generate_shell_halves.py``.

Usage:
    ./make_shell_midslab.py \
        --shell-mask <shell.n5> \
        --out-n5 data/rawdata/shell_halves/shell_midslab.n5 \
        --local-xml-dir data/platybrowser_6dpf/images/local \
        --s3-xml-dir data/platybrowser_6dpf/images/bdv-n5-s3/shell_halves \
        --half-width 15
"""

import argparse
import shutil
from pathlib import Path

import numpy as np
import z5py

from generate_shell_halves import (
    _level_ds_factor,
    block_slices,
    mirror_group_attrs,
    mirror_level_info,
    shell_frame,
    write_local_xmls,
    write_s3_xmls,
)

NAME = "shell_midslab"


def slab_block(block, slices, ds_factor, center, normal, half_width):
    """Zero block voxels farther than ``half_width`` from the plane.

    Level voxel index ``i`` maps to full-res coordinate
    ``i * ds_factor + (ds_factor - 1) / 2``; the signed distance to the plane
    is ``(p - center) . normal``.
    """
    nz = np.nonzero(block)
    if nz[0].size == 0:
        return block
    off = (ds_factor - 1.0) / 2.0
    x = (slices[2].start + nz[2]) * ds_factor + off
    y = (slices[1].start + nz[1]) * ds_factor + off
    z = (slices[0].start + nz[0]) * ds_factor + off
    dist = ((x - center[0]) * normal[0]
            + (y - center[1]) * normal[1]
            + (z - center[2]) * normal[2])
    keep = np.abs(dist) < half_width
    out = np.zeros_like(block)
    out[nz[0][keep], nz[1][keep], nz[2][keep]] = block[nz[0][keep],
                                                       nz[1][keep],
                                                       nz[2][keep]]
    return out


def make_slab(mask_path, out_path, center, normal, half_width, gzip_level=1):
    """Write the slab of ``mask_path`` within ``half_width`` of the plane."""
    levels = mirror_level_info(mask_path)
    group_attrs = mirror_group_attrs(mask_path)
    out_path = Path(out_path)
    if out_path.exists():
        shutil.rmtree(out_path)
    with z5py.File(str(out_path), "a") as f:
        setup = f.create_group("setup0")
        for k, v in group_attrs.get("setup0", {}).items():
            setup.attrs[k] = v
        tp = setup.create_group("timepoint0")
        for k, v in group_attrs.get("timepoint0", {}).items():
            tp.attrs[k] = v
        for lvl in levels:
            ds = tp.create_dataset(
                lvl["name"], shape=lvl["shape"], chunks=lvl["chunks"],
                dtype="uint8", compression="gzip", level=gzip_level,
                fillvalue=0,
            )
            for k, v in lvl["attrs"].items():
                ds.attrs[k] = v

    with z5py.File(str(mask_path), "r") as sf, z5py.File(str(out_path), "a") as of:
        stp = sf["setup0/timepoint0"]
        otp = of["setup0/timepoint0"]
        for lvl in levels:
            ds_factor = _level_ds_factor(lvl)
            sds = stp[lvl["name"]]
            ods = otp[lvl["name"]]
            for sl in block_slices(lvl["shape"], lvl["chunks"]):
                block = sds[sl]
                if not block.any():
                    continue
                ods[sl] = slab_block(block, sl, ds_factor, center, normal,
                                     half_width)
    return out_path


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--shell-mask", required=True)
    p.add_argument("--out-n5", required=True)
    p.add_argument("--local-xml-dir", required=True)
    p.add_argument("--s3-xml-dir", required=True)
    p.add_argument("--half-width", type=float, default=15.0,
                   help="Half-thickness of the slab in full-res voxels (default 15).")
    p.add_argument("--gzip-level", type=int, default=1)
    return p.parse_args()


def main():
    args = parse_args()
    frame = shell_frame(args.shell_mask)
    center, normal = frame["center"], frame["lr"]
    print("plane center={} normal={}".format(np.round(center, 2),
                                             np.round(normal, 4)))
    out = make_slab(args.shell_mask, args.out_n5, center, normal,
                    args.half_width, gzip_level=args.gzip_level)
    write_local_xmls([NAME], Path(args.local_xml_dir), Path(args.out_n5).parent)
    write_s3_xmls([NAME], Path(args.s3_xml_dir))
    print(f"Wrote {out} and {NAME}.xml (local + s3)")


if __name__ == "__main__":
    main()
