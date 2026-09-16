#!/usr/bin/env -S uv run --python 3.12
# /// script
# dependencies = ["numpy", "z5py", "scipy"]
# ///
"""Remove the central mass from the ``shell_left`` half-shell.

The ``shell`` mask is a thin folded surface (2 erosion passes already kill it),
but its convex hull encloses a large solid central mass: shell voxels reach a
depth of up to 176 full-resolution voxels inside the hull (median 32). At a
depth threshold of 15 full-res voxels that deep material is a single connected
component centred on the shell.

This script computes the convex hull of the ORIGINAL shell mask, then writes a
new ``shell_left_clean`` N5 = the existing ``shell_left`` half with every voxel
deeper than ``--depth`` inside that hull zeroed. The output mirrors the input
half's pyramid (levels, shapes, chunks, group/dataset attributes) and uses
uint8 + gzip + fillvalue 0, exactly like ``generate_shell_halves.py``.

The level/chunk/attribute mirroring and the XML writers are reused from
``generate_shell_halves`` (which is not modified).

Usage:
    ./clean_shell_left.py \
        --shell-mask tmp_shell_halves_src/sbem-6dpf-1-whole-segmented-shell.n5 \
        --half data/rawdata/shell_halves/shell_left.n5 \
        --out-n5 data/rawdata/shell_halves/shell_left_clean.n5 \
        --local-xml-dir data/platybrowser_6dpf/images/local \
        --s3-xml-dir data/platybrowser_6dpf/images/bdv-n5-s3/shell_halves \
        --depth 15
"""

import argparse
import shutil
from pathlib import Path

import numpy as np
import z5py
from scipy.spatial import ConvexHull

from generate_shell_halves import (
    _finest_level,
    _level_ds_factor,
    block_slices,
    mirror_group_attrs,
    mirror_level_info,
    write_local_xmls,
    write_s3_xmls,
)

NAME = "shell_left_clean"


def hull_planes(shell_mask_path, stride=4):
    """Convex hull of the shell mask as ``(A, b)`` unit outward plane equations.

    Nonzero voxel coordinates of the finest level are collected as full-res
    ``(x, y, z)`` points and subsampled with ``stride`` in every axis before the
    hull is fitted. Returns ``(equations[:, :3], equations[:, 3])``: a point is
    inside the hull when ``A @ p + b <= 0`` for every plane.
    """
    step = 16
    xs, ys, zs = [], [], []
    with z5py.File(str(shell_mask_path), "r") as f:
        tp = f["setup0/timepoint0"]
        ds = tp[_finest_level(tp)]
        shape = ds.shape
        for z0 in range(0, shape[0], step):
            blk = ds[z0:z0 + step]
            nz = np.nonzero(blk)
            if nz[0].size == 0:
                continue
            xs.append(nz[2].astype(np.float64))
            ys.append(nz[1].astype(np.float64))
            zs.append(nz[0].astype(np.float64) + z0)
    if not xs:
        raise ValueError(f"shell mask {shell_mask_path} has no nonzero voxels")
    points = np.stack(
        [np.concatenate(xs), np.concatenate(ys), np.concatenate(zs)], axis=1
    )[::stride]
    equations = ConvexHull(points).equations
    return equations[:, :3], equations[:, 3]


def depth_of(points, A, b):
    """Depth of ``(N, 3)`` full-res points inside the hull ``(A, b)``.

    Depth is the distance to the closest hull plane: 0 on the hull surface and
    positive inside.
    """
    points = np.asarray(points, dtype=np.float64)
    return -np.max(A @ points.T + b[:, None], axis=0)


def clean_block(block, slices, ds_factor, A, b, threshold, axis_width=None,
                segment=None):
    """Zero the nonzero voxels of a level block selected for removal.

    Level voxel index ``i`` maps to full-res coordinate
    ``i * ds_factor + (ds_factor - 1) / 2``. Only nonzero voxels are tested, so
    the geometry is evaluated on the mask's sparse point set.

    Two mutually exclusive criteria are supported:

    * default: remove voxels deeper than ``threshold`` inside the hull ``(A, b)``;
      when ``axis_width`` is given, additionally require ``|x - y| < axis_width``
      (keeps the lateral shell, removes the central near-axis mass);
    * ``segment``: remove voxels within a cylinder around a line segment. The
      tuple is ``(p0_um, unit_direction, length_um, radius_um, resolution)``;
      voxels whose projection onto the segment lies within ``[0, length]`` and
      whose perpendicular distance is ``< radius`` are removed.
    """
    nz = np.nonzero(block)
    if nz[0].size == 0:
        return block
    off = (ds_factor - 1.0) / 2.0
    x = (slices[2].start + nz[2]) * ds_factor + off
    y = (slices[1].start + nz[1]) * ds_factor + off
    z = (slices[0].start + nz[0]) * ds_factor + off
    if segment is not None:
        p0, direction, length, radius, resolution = segment
        points = np.stack([x, y, z], axis=1) * resolution
        t = (points - p0) @ direction
        perp = points - p0[None, :] - t[:, None] * direction[None, :]
        remove = ((t >= 0.0) & (t <= length)
                  & (np.linalg.norm(perp, axis=1) < radius))
    else:
        depth = depth_of(np.stack([x, y, z], axis=1), A, b)
        remove = depth > threshold
        if axis_width is not None:
            remove = remove & (np.abs(x - y) < axis_width)
    out = block.copy()
    out[nz[0][remove], nz[1][remove], nz[2][remove]] = 0
    return out


def clean_half(half_path, out_path, A, b, threshold, axis_width=None,
               segment=None, gzip_level=1):
    """Write ``half_path`` with the selected voxels removed.

    The output mirrors the input half's levels, chunks and group attributes and
    uses uint8 + gzip + fillvalue 0. See ``clean_block`` for the criteria.
    Returns the output path.
    """
    levels = mirror_level_info(half_path)
    group_attrs = mirror_group_attrs(half_path)
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

    with z5py.File(str(half_path), "r") as sf, z5py.File(str(out_path), "a") as of:
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
                ods[sl] = clean_block(block, sl, ds_factor, A, b, threshold,
                                      axis_width, segment)
    return out_path


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--shell-mask", required=True,
                   help="Original shell mask N5 (for the convex hull).")
    p.add_argument("--half", required=True,
                   help="Input half-shell N5 (e.g. shell_left.n5).")
    p.add_argument("--out-n5", required=True,
                   help="Output cleaned half-shell N5 (gitignored).")
    p.add_argument("--local-xml-dir", required=True,
                   help="Dir for local <name>.xml (repo images/local).")
    p.add_argument("--s3-xml-dir", required=True,
                   help="Dir for S3 <name>.xml (repo images/bdv-n5-s3/shell_halves).")
    p.add_argument("--depth", type=float, default=15.0,
                   help="Depth threshold in full-res voxels (default 15).")
    p.add_argument("--axis-width", type=float, default=None,
                   help="Only remove voxels with |x - y| < AXIS_WIDTH "
                        "(distance*2 from the symmetry plane x = y). Default: "
                        "no restriction.")
    p.add_argument("--segment-p0", default=None,
                   help="Cylinder mode: start of the segment, 'x,y,z' in µm.")
    p.add_argument("--segment-p1", default=None,
                   help="Cylinder mode: end of the segment, 'x,y,z' in µm.")
    p.add_argument("--segment-radius", type=float, default=None,
                   help="Cylinder mode: removal radius around the segment, µm.")
    p.add_argument("--stride", type=int, default=4,
                   help="Subsampling stride for the hull points (default 4).")
    p.add_argument("--gzip-level", type=int, default=1,
                   help="Gzip compression level for the output N5 (default 1).")
    return p.parse_args()


def _resolution(half_path):
    """Voxel size (x, y, z) in µm, from the half's timepoint attributes."""
    with z5py.File(str(half_path), "r") as f:
        return np.asarray(f["setup0/timepoint0"].attrs["resolution"], dtype=float)


def _segment(args, half_path):
    """Build the cylinder-mode segment tuple, or None if not requested."""
    if not (args.segment_p0 and args.segment_p1 and args.segment_radius):
        return None
    p0 = np.array([float(v) for v in args.segment_p0.split(",")])
    p1 = np.array([float(v) for v in args.segment_p1.split(",")])
    delta = p1 - p0
    length = float(np.linalg.norm(delta))
    if length == 0.0:
        raise ValueError("segment endpoints coincide")
    return (p0, delta / length, length, args.segment_radius,
            _resolution(half_path))


def main():
    args = parse_args()
    segment = _segment(args, args.half)
    if segment is not None:
        A = b = None
        print("segment cylinder: p0={} p1={} radius={} µm".format(
            np.round(segment[0], 2),
            np.round(segment[0] + segment[1] * segment[2], 2), segment[3]))
    else:
        A, b = hull_planes(args.shell_mask, stride=args.stride)
        print(f"convex hull: {A.shape[0]} planes from {args.shell_mask}")
    out = clean_half(
        args.half, args.out_n5, A, b, args.depth,
        axis_width=args.axis_width, segment=segment,
        gzip_level=args.gzip_level)
    write_local_xmls([NAME], Path(args.local_xml_dir), Path(args.out_n5).parent)
    write_s3_xmls([NAME], Path(args.s3_xml_dir))
    print(f"Wrote {out} and {NAME}.xml (local + s3)")


if __name__ == "__main__":
    main()
