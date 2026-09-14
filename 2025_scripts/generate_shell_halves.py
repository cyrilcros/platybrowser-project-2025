#!/usr/bin/env -S uv run --python 3.12
# /// script
# dependencies = ["numpy", "z5py"]
# ///
"""Generate four half-shell N5 images from the shell mask.

The shell is a binary uint8 mask. Cut it with two vertical 45-degree planes
through the origin, in index space:

    sagittal plane  x = y   -> shell_sag_left  (keep x - y >= offset)
                               shell_sag_right (keep x - y <= offset)
    coronal plane   x = -y  -> shell_cor_front (keep x + y >= offset)
                               shell_cor_back  (keep x + y <= offset)

N5 arrays are stored as (z, y, x): axis 1 is y, axis 2 is x, z is untouched.
Every pyramid level is an exact power-of-two downsample aligned to the origin,
so the condition is scale-invariant and each level is masked with its own
global indices. Outputs mirror the shell pyramid (levels, shapes, chunks,
attributes) and use gzip + fillvalue 0.

Usage:
    ./generate_shell_halves.py --mask <shell.n5> --stage-dir <dir> \
        --local-xml-dir data/platybrowser_6dpf/images/local \
        --s3-xml-dir data/platybrowser_6dpf/images/bdv-n5-s3/shell_halves
"""

import argparse
import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import z5py

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_XML_TEMPLATE = (
    REPO_ROOT / "data/platybrowser_6dpf/images/local/"
    "sbem-6dpf-1-whole-segmented-shell.xml"
)
S3_XML_TEMPLATE = (
    REPO_ROOT / "data/platybrowser_6dpf/images/bdv-n5-s3/vergara_2021/"
    "sbem-6dpf-1-whole-segmented-shell.xml"
)

S3_PREFIX = "images/bdv-n5-s3/shell_halves"
S3_BUCKET = "platybrowser-2025"
S3_ENDPOINT = "https://s3.embl.de"
S3_REGION = "us-west-2"

# name -> predicate(global_x, global_y, offset) -> bool array
HALVES = {
    "shell_sag_left": lambda x, y, o: (x - y) >= o,
    "shell_sag_right": lambda x, y, o: (x - y) <= o,
    "shell_cor_front": lambda x, y, o: (x + y) >= o,
    "shell_cor_back": lambda x, y, o: (x + y) <= o,
}
HALF_NAMES = list(HALVES)


def block_slices(shape, chunks):
    """Yield every (z, y, x) block slice of an array in chunk-aligned order."""
    for z0 in range(0, shape[0], chunks[0]):
        for y0 in range(0, shape[1], chunks[1]):
            for x0 in range(0, shape[2], chunks[2]):
                yield (
                    slice(z0, min(z0 + chunks[0], shape[0])),
                    slice(y0, min(y0 + chunks[1], shape[1])),
                    slice(x0, min(x0 + chunks[2], shape[2])),
                )


def mask_block(block, y0, x0, keep, offset=0):
    """Zero out voxels of a (z, y, x) block failing keep(global_x, global_y)."""
    y = np.arange(y0, y0 + block.shape[1])
    x = np.arange(x0, x0 + block.shape[2])
    keep_xy = keep(x[None, None, :], y[None, :, None], offset)  # (1, by, bx)
    return np.where(keep_xy, block, 0).astype(block.dtype, copy=False)


def mirror_level_info(mask_path):
    """Level name, shape, chunks and attrs for every s-level of the mask."""
    with z5py.File(str(mask_path), "r") as f:
        tp = f["setup0/timepoint0"]
        return [
            {
                "name": key,
                "shape": tuple(tp[key].shape),
                "chunks": tuple(tp[key].chunks),
                "attrs": dict(tp[key].attrs),
            }
            for key in sorted(tp.keys())
        ]


def mirror_group_attrs(mask_path):
    """The mask's setup0 and timepoint0 group attributes."""
    with z5py.File(str(mask_path), "r") as f:
        return {
            "setup0": dict(f["setup0"].attrs),
            "timepoint0": dict(f["setup0/timepoint0"].attrs),
        }


def write_halves(mask_path, stage_dir, levels, group_attrs, halves=HALVES,
                 offset=0, gzip_level=1):
    """Write one uint8 N5 per half into stage_dir, mirroring the mask pyramid."""
    stage_dir = Path(stage_dir)
    stage_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name in halves:
        out_path = stage_dir / f"{name}.n5"
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
        written.append(out_path)

    with z5py.File(str(mask_path), "r") as mf:
        mtp = mf["setup0/timepoint0"]
        for name, keep in halves.items():
            with z5py.File(str(stage_dir / f"{name}.n5"), "a") as of:
                otp = of["setup0/timepoint0"]
                for lvl in levels:
                    mds = mtp[lvl["name"]]
                    ods = otp[lvl["name"]]
                    for sl in block_slices(lvl["shape"], lvl["chunks"]):
                        block = mds[sl]
                        if not block.any():
                            continue
                        ods[sl] = mask_block(
                            block, sl[1].start, sl[2].start, keep, offset
                        )
    return written


def _write_xml(template, out_path, name, loader_text, loader_format, s3):
    """Copy a shell XML template, set the setup name and the loader location."""
    tree = ET.parse(template)
    root = tree.getroot()
    setup_name = root.find(".//ViewSetup/name")
    if setup_name is not None:
        setup_name.text = name
    loader = root.find(".//ImageLoader")
    loader.set("format", loader_format)
    if s3:
        for tag in ("n5", "Key", "SigningRegion", "ServiceEndpoint", "BucketName"):
            for el in loader.findall(tag):
                loader.remove(el)
        ET.SubElement(loader, "Key").text = loader_text
        ET.SubElement(loader, "SigningRegion").text = S3_REGION
        ET.SubElement(loader, "ServiceEndpoint").text = S3_ENDPOINT
        ET.SubElement(loader, "BucketName").text = S3_BUCKET
    else:
        n5_el = loader.find("n5")
        n5_el.set("type", "relative")
        n5_el.text = loader_text
    ET.indent(root, space="  ")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(out_path, encoding="utf-8", xml_declaration=False)
    with open(out_path, "a", encoding="utf-8") as f:
        f.write("\n")
    return out_path


def write_local_xmls(names, local_xml_dir, stage_dir, template=LOCAL_XML_TEMPLATE):
    """Write images/local/<name>.xml pointing at the staged <name>.n5."""
    local_xml_dir = Path(local_xml_dir)
    stage_dir = Path(stage_dir)
    written = []
    for name in names:
        n5_rel = os.path.relpath(stage_dir / f"{name}.n5", local_xml_dir)
        written.append(_write_xml(
            template, local_xml_dir / f"{name}.xml", name,
            n5_rel.replace("\\", "/"), "bdv.n5", s3=False,
        ))
    return written


def write_s3_xmls(names, s3_xml_dir, template=S3_XML_TEMPLATE, prefix=S3_PREFIX):
    """Write S3 XMLs with Key <prefix>/<name>.n5 in bucket platybrowser-2025."""
    s3_xml_dir = Path(s3_xml_dir)
    written = []
    for name in names:
        written.append(_write_xml(
            template, s3_xml_dir / f"{name}.xml", name,
            f"{prefix}/{name}.n5", "bdv.n5.s3", s3=True,
        ))
    return written


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mask", required=True,
                   help="Path to the shell N5 (setup0/timepoint0/s*).")
    p.add_argument("--stage-dir", required=True,
                   help="Dir for generated <name>.n5 (gitignored).")
    p.add_argument("--local-xml-dir", required=True,
                   help="Dir for local <name>.xml (repo images/local).")
    p.add_argument("--s3-xml-dir", required=True,
                   help="Dir for S3 <name>.xml (repo images/bdv-n5-s3/shell_halves).")
    p.add_argument("--offset", type=int, default=0,
                   help="Plane offset in voxels (default 0 = through origin).")
    p.add_argument("--gzip-level", type=int, default=1,
                   help="Gzip compression level for the output N5s (default 1).")
    return p.parse_args()


def main():
    args = parse_args()
    levels = mirror_level_info(args.mask)
    group_attrs = mirror_group_attrs(args.mask)
    write_halves(args.mask, Path(args.stage_dir), levels, group_attrs,
                 offset=args.offset, gzip_level=args.gzip_level)
    write_local_xmls(HALF_NAMES, Path(args.local_xml_dir), Path(args.stage_dir))
    write_s3_xmls(HALF_NAMES, Path(args.s3_xml_dir))
    print(f"Wrote {len(HALF_NAMES)} half-shell N5s to {args.stage_dir}")


if __name__ == "__main__":
    main()
