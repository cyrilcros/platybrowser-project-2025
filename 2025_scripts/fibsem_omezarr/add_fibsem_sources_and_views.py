#!/usr/bin/env python3
"""Add the fibsem FIB-SEM OME-Zarr volumes as MoBIE sources + `parapodia` views.

The zarrs live on EMBL S3 (bucket `platybrowser-2025`, prefix
`fibsem/ome-zarr/`) as NGFF 0.5 / Zarr v3. They are declared with the
`ome.zarr.s3` format key and an `s3Address` (path-style HTTPS URL); no XML is
read for this format, so the registration lives in `sourceTransforms`.

Registration: the source BDV XMLs carry a `voxel index -> world µm` affine
`A_xml = voxel_size * R` with translation `t`. MoBIE applies a view's
`sourceTransforms.affine` as `A ∘ S` in world space (verified), so with the
store's own transform `S = diag(voxel_size)` and no translation the matrix to
write is `M_A = A_xml | diag(1/voxel_size)` — i.e. divide the 3x3 part by the
voxel size and keep the world translation.

Two registrations exist for the raw (`_g`, `_cg`); the 20 nm cell labels and
the three `-parapod-fib` masks share the `_g` placement. The remaining volumes
are in their own grids (pure scale, t=0) and get no transform.

Dry-run by default; pass --write to edit dataset.json.
"""
import argparse
import json

S3_BASE = "https://s3.embl.de/platybrowser-2025/fibsem/ome-zarr"
GROUP = "parapodia"

# Registration affines (voxel index -> world µm) from the source BDV XMLs.
RAW_VOXEL = 0.01
A_XML_G = [-0.0050, 0.0071, -0.0051, 184.7922,
           -0.0050, 0.0038, 0.0083, 35.4883,
           0.0074, 0.0073, 0.0003, 112.2924]
A_XML_CG = [-0.0053, 0.0078, -0.0057, 186.5283,
            -0.0044, 0.0056, 0.0096, 23.1917,
            0.0090, 0.0069, -0.0013, 118.2384]

# zARR groups that share the `_g` placement (all "parapod-fib" family).
FIB_G = "g"
FIB_CG = "cg"


def world_affine(a_xml, voxel):
    """M_A = A_xml | diag(1/voxel): divide the 3x3 part, keep the translation."""
    return [round(a_xml[i] / voxel if i % 4 != 3 else a_xml[i], 6) for i in range(12)]


# (source name, registration key or None)
VOLUMES = [
    ("em-raw-parapod-fib", FIB_G),
    ("em-raw-parapod-fib", FIB_CG),          # same zarr, other registration
    ("em-raw-parapod-fib", None),            # unregistered baseline
    ("em-segmented-parapod-cells-labels", FIB_G),
    ("em-segmented-ganglion-parapod-fib", FIB_G),
    ("em-segmented-muscles-parapod-fib", FIB_G),
    ("em-segmented-small-cirrus-parapod-fib", FIB_G),
    ("em-segmented-ganglion", None),
    ("em-segmented-small-cirrus", None),
    ("em-segmented-parapod-cells-aligned-labels", None),
    ("em-segmented-parapod-cells-labels-2019_06_18-cg", None),
    ("em-segmented-parapod-cells-labels-2019_06_18-g", None),
    ("em-segmented-parapod-cells-labels-2019_06_18-r", None),
]

LABELS = {n for n, _ in VOLUMES if n != "em-raw-parapod-fib"}

# Human view label per (source, registration).
VIEW_LABEL = {
    (FIB_G, "em-raw-parapod-fib"): "raw EM | registration g",
    (FIB_CG, "em-raw-parapod-fib"): "raw EM | registration cg",
    (None, "em-raw-parapod-fib"): "raw EM | unregistered",
    (FIB_G, "em-segmented-parapod-cells-labels"): "parapod cells (20 nm) | g",
    (FIB_G, "em-segmented-ganglion-parapod-fib"): "ganglion mask (FIB) | g",
    (FIB_G, "em-segmented-muscles-parapod-fib"): "muscles mask (FIB) | g",
    (FIB_G, "em-segmented-small-cirrus-parapod-fib"): "small cirrus mask (FIB) | g",
    (None, "em-segmented-ganglion"): "ganglion (0.5 µm, own grid)",
    (None, "em-segmented-small-cirrus"): "small cirrus (0.5 µm, own grid)",
    (None, "em-segmented-parapod-cells-aligned-labels"): "cells aligned (160/160/200 nm)",
    (None, "em-segmented-parapod-cells-labels-2019_06_18-cg"): "cells 2019-06-18 cg",
    (None, "em-segmented-parapod-cells-labels-2019_06_18-g"): "cells 2019-06-18 g",
    (None, "em-segmented-parapod-cells-labels-2019_06_18-r"): "cells 2019-06-18 r",
}


def registration_matrix(key):
    if key == FIB_G:
        return world_affine(A_XML_G, RAW_VOXEL)
    if key == FIB_CG:
        return world_affine(A_XML_CG, RAW_VOXEL)
    return None


def source_definition(name):
    return {"image": {"imageData": {"ome.zarr.s3": {"s3Address": f"{S3_BASE}/{name}.ome.zarr"}}}}


def display(src_or_out, label, is_label):
    d = {"sources": [src_or_out], "name": label}
    if is_label:
        d["color"] = "r=255,g=0,b=255,a=255"
        d["contrastLimits"] = [0.0, 1.0]
    return {"imageDisplay": d}


def view_definition(name, reg, label, out_name):
    is_label = name in LABELS
    v = {
        "uiSelectionGroup": GROUP,
        "sourceDisplays": [display(out_name, label, is_label)],
    }
    matrix = registration_matrix(reg)
    if matrix is not None:
        v["sourceTransforms"] = [{
            "affine": {
                "name": label,
                "parameters": matrix,
                "sources": [name],
                "sourceNamesAfterTransform": [out_name],
            }
        }]
    return v


def add(dataset):
    sources = dataset.setdefault("sources", {})
    views = dataset.setdefault("views", {})
    added_sources = added_views = 0
    seen = set()
    for name, reg in VOLUMES:
        if name not in sources:
            sources[name] = source_definition(name)
            added_sources += 1
        out = f"{name}__{reg}" if reg else name
        label = VIEW_LABEL[(reg, name)]
        if label in views:
            continue
        views[label] = view_definition(name, reg, label, out)
        added_views += 1
        seen.add(label)
    return added_sources, added_views


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset-json", required=True)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    with open(args.dataset_json) as fh:
        dataset = json.load(fh)
    s, v = add(dataset)
    print(f"sources added: {s}, views added: {v}")
    if args.write:
        with open(args.dataset_json, "w") as fh:
            json.dump(dataset, fh, indent=2)
            fh.write("\n")
        print(f"wrote {args.dataset_json}")
    else:
        print("dry run (use --write)")


if __name__ == "__main__":
    main()
