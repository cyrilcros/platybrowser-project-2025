#!/usr/bin/env -S uv run
# /// script
# dependencies = ["numpy", "z5py"]
# ///
"""Generate per-subtype nuclei probability N5 images.

For each detailed cell type (subtype) column in the detailed cluster
probability table, repaint the nuclei segmentation mask: every nucleus voxel
keeps its geometry but its value becomes round(p * 1000) for that subtype.
Background stays 0. Output N5s mirror the mask's pyramid exactly (levels,
shapes, chunking, resolution/downsamplingFactors/offset attributes) and use
gzip + fillvalue 0 so images are sparse and small.

Usage:
    ./generate_nuclei_proba_images.py --mask <nuclei.n5> --table <tsv> \
        --stage-dir <dir> --local-xml-dir <dir> [--subtypes a,b,c]
"""

import argparse
import csv
import json
import os
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import z5py

SUBSTYPE_PREFIXES = ("clade", "nocladesub")
EXCLUDED_COLUMNS = {"label_id", "zero", "autofluorescence", "most probable cluster"}
SCALE = 1000
DEFAULT_XML_TEMPLATE = Path(__file__).resolve().parent.parent / \
    "data" / "platybrowser_6dpf" / "images" / "local" / \
    "sbem-6dpf-1-whole-segmented-nuclei.xml"


def read_subtype_columns(tsv_path):
    """Return subtype probability columns in table order (clade*/nocladesub* only)."""
    with open(tsv_path, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f, delimiter="\t"))
    return [c for c in header
            if c.startswith(SUBSTYPE_PREFIXES) and c not in EXCLUDED_COLUMNS]


def read_probabilities(tsv_path, subtype):
    """Return {label_id: probability} for one subtype column."""
    probs = {}
    with open(tsv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            label = int(float(row["label_id"]))
            probs[label] = float(row[subtype])
    return probs


def build_value_table(probs, scale=SCALE):
    """uint16 lookup table indexed by label: value = round(p * scale), label 0 -> 0."""
    max_label = max(probs.keys(), default=0)
    table = np.zeros(max_label + 1, dtype=np.uint16)
    for label, p in probs.items():
        table[label] = int(round(p * scale))
    return table


def mirror_level_info(mask_path):
    """Introspect the mask pyramid: level name, shape, chunks, attrs per s-level."""
    with z5py.File(str(mask_path), "r") as f:
        tp = f["setup0/timepoint0"]
        levels = []
        for key in sorted(tp.keys()):
            ds = tp[key]
            levels.append({
                "name": key,
                "shape": tuple(ds.shape),
                "chunks": tuple(ds.chunks),
                "attrs": dict(ds.attrs),
            })
    return levels


def relabel_block(mask_block, value_table):
    """Map a uint32 label block through the value table (labels beyond table -> 0)."""
    out = np.zeros(mask_block.shape, dtype=np.uint16)
    idx = mask_block <= value_table.shape[0] - 1
    out[idx] = value_table[mask_block[idx].astype(np.intp)]
    return out


def write_outputs(mask_path, value_tables, stage_dir, levels):
    """Write one uint16 N5 per subtype into stage_dir, mirroring the mask pyramid.

    Single block-wise pass over each mask level. All-zero blocks are skipped;
    the N5 fillvalue 0 covers them, keeping the outputs sparse and small.
    """
    stage_dir = Path(stage_dir)
    stage_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for subtype in value_tables:
        out_path = stage_dir / f"{subtype}_proba.n5"
        if out_path.exists():
            shutil.rmtree(out_path)
        with z5py.File(str(out_path), "a") as f:
            g = f.create_group("setup0").create_group("timepoint0")
            for level in levels:
                ds = g.create_dataset(
                    level["name"],
                    shape=level["shape"],
                    chunks=level["chunks"],
                    dtype="uint16",
                    compression="gzip",
                    fillvalue=0,
                )
                for k, v in level["attrs"].items():
                    ds.attrs[k] = v
        written.append(out_path)

    with z5py.File(str(mask_path), "r") as mask_f:
        tp = mask_f["setup0/timepoint0"]
        for level in levels:
            name, shape, chunks = level["name"], level["shape"], level["chunks"]
            mask_ds = tp[name]
            out_dss = {
                subtype: z5py.File(str(stage_dir / f"{subtype}_proba.n5"), "a")[
                    "setup0/timepoint0"][name]
                for subtype in value_tables
            }
            for z0 in range(0, shape[0], chunks[0]):
                for y0 in range(0, shape[1], chunks[1]):
                    for x0 in range(0, shape[2], chunks[2]):
                        sl = (slice(z0, min(z0 + chunks[0], shape[0])),
                              slice(y0, min(y0 + chunks[1], shape[1])),
                              slice(x0, min(x0 + chunks[2], shape[2])))
                        block = mask_ds[sl]
                        if not block.any():
                            continue
                        for subtype, value_table in value_tables.items():
                            out_dss[subtype][sl] = relabel_block(block, value_table)
    return written


def main():
    print("generate_nuclei_proba_images: table helpers loaded", file=sys.stderr)


if __name__ == "__main__":
    main()
