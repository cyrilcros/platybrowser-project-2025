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


def main():
    print("generate_nuclei_proba_images: table helpers loaded", file=sys.stderr)


if __name__ == "__main__":
    main()
