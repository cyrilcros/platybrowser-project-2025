#!/usr/bin/env -S uv run --python 3.12
# /// script
# dependencies = ["numpy", "z5py"]
# ///
"""Build ``lung_shell``: the shell material of the paired near-axis protrusions.

Keeps only shell voxels within ``--radius`` µm of one of two cylinders: the
segment ``--segment-p0`` → ``--segment-p1`` (µm), and its mirror across the
left/right symmetry plane (normal = the measured ``LR`` axis, through the shell
centroid). The result is the "lungs" of both halves as a standalone source.

The output mirrors the source pyramid (levels, shapes, chunks, group/dataset
attributes) with uint8 + gzip + fillvalue 0.

Usage:
    ./make_lung_shell.py \
        --shell-mask <shell.n5> \
        --out-n5 data/rawdata/shell_halves/lung_shell.n5 \
        --local-xml-dir data/platybrowser_6dpf/images/local \
        --s3-xml-dir data/platybrowser_6dpf/images/bdv-n5-s3/shell_halves \
        --segment-p0 157.0,152.2,47.1 --segment-p1 176.5,157.9,141.7 \
        --radius 25 --mirror
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

NAME = "lung_shell"


def build_segments(args, center, lr):
    """List of ``(p0_um, unit_direction, length_um)`` for the lung cylinders."""
    p0 = np.array([float(v) for v in args.segment_p0.split(",")])
    p1 = np.array([float(v) for v in args.segment_p1.split(",")])
    segments = []
    for a, b in ((p0, p1),):
        delta = b - a
        segments.append((a, delta / np.linalg.norm(delta),
                         float(np.linalg.norm(delta))))
    if args.mirror:
        def reflect(p):
            return p - 2.0 * float((p - center) @ lr) * lr
        a, b = reflect(p0), reflect(p1)
        delta = b - a
        segments.append((a, delta / np.linalg.norm(delta),
                         float(np.linalg.norm(delta))))
    return segments


def keep_block(block, slices, ds_factor, segments, radius, resolution):
    """Keep block voxels within ``radius`` of any cylinder, zero the rest."""
    nz = np.nonzero(block)
    if nz[0].size == 0:
        return block
    off = (ds_factor - 1.0) / 2.0
    x = (slices[2].start + nz[2]) * ds_factor + off
    y = (slices[1].start + nz[1]) * ds_factor + off
    z = (slices[0].start + nz[0]) * ds_factor + off
    points = np.stack([x, y, z], axis=1) * resolution
    keep = np.zeros(nz[0].size, dtype=bool)
    for p0, direction, length in segments:
        t = (points - p0) @ direction
        perp = points - p0[None, :] - t[:, None] * direction[None, :]
        keep |= ((t >= 0.0) & (t <= length)
                 & (np.linalg.norm(perp, axis=1) < radius))
    out = np.zeros_like(block)
    out[nz[0][keep], nz[1][keep], nz[2][keep]] = block[nz[0][keep],
                                                       nz[1][keep],
                                                       nz[2][keep]]
    return out


def make_lung_shell(mask_path, out_path, segments, radius, resolution,
                    gzip_level=1):
    """Write the union of the lung cylinders as a new N5."""
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
                ods[sl] = keep_block(block, sl, ds_factor, segments, radius,
                                     resolution)
    return out_path


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--shell-mask", required=True)
    p.add_argument("--out-n5", required=True)
    p.add_argument("--local-xml-dir", required=True)
    p.add_argument("--s3-xml-dir", required=True)
    p.add_argument("--segment-p0", required=True, help="'x,y,z' in µm.")
    p.add_argument("--segment-p1", required=True, help="'x,y,z' in µm.")
    p.add_argument("--radius", type=float, default=25.0, help="Cylinder radius, µm.")
    p.add_argument("--mirror", action="store_true",
                   help="Also keep the mirror of the segment across the symmetry plane.")
    p.add_argument("--gzip-level", type=int, default=1)
    return p.parse_args()


def main():
    args = parse_args()
    with z5py.File(str(args.shell_mask), "r") as f:
        resolution = np.asarray(
            f["setup0/timepoint0"].attrs["resolution"], dtype=float)
    frame = shell_frame(args.shell_mask)
    segments = build_segments(args, frame["center"], frame["lr"])
    print("cylinders (µm):")
    for p0, direction, length in segments:
        print("  {} -> {} (len {:.1f}, r {})".format(
            np.round(p0, 1), np.round(p0 + direction * length, 1), length,
            args.radius))
    out = make_lung_shell(args.shell_mask, args.out_n5, segments, args.radius,
                          resolution, gzip_level=args.gzip_level)
    write_local_xmls([NAME], Path(args.local_xml_dir), Path(args.out_n5).parent)
    write_s3_xmls([NAME], Path(args.s3_xml_dir))
    print(f"Wrote {out} and {NAME}.xml (local + s3)")


if __name__ == "__main__":
    main()
