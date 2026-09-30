#!/usr/bin/env python3
"""Structural validation of an OME-Zarr v3 (NGFF 0.5) dataset.

Checks the root zarr.json (zarr_format 3, ome.version 0.5, multiscales with
axis names and per-level scales) and that each referenced level exists and has
a matching rank. Exits non-zero on any problem.

Usage: validate_omezarr.py <dataset.ome.zarr> [more.ome.zarr ...]
"""
import json
import os
import sys


def load_json(path):
    with open(path) as fh:
        return json.load(fh)


def check_dataset(root):
    errors = []
    zj = os.path.join(root, "zarr.json")
    if not os.path.isfile(zj):
        return [f"{root}: no zarr.json (not zarr v3)"]
    meta = load_json(zj)
    if meta.get("zarr_format") != 3:
        errors.append(f"{root}: zarr_format={meta.get('zarr_format')} (expected 3)")

    ome = (meta.get("attributes") or {}).get("ome")
    if not ome:
        return errors + [f"{root}: no attributes.ome"]
    version = ome.get("version")
    if version not in ("0.5", "0.6"):
        errors.append(f"{root}: ome.version={version} (expected 0.5)")

    ms = (ome.get("multiscales") or [{}])[0]
    axes = [a.get("name") for a in ms.get("axes", [])]
    if not axes:
        errors.append(f"{root}: multiscales[0] has no axes")

    for ds in ms.get("datasets", []):
        p = ds.get("path")
        lvl = os.path.join(root, p, "zarr.json")
        if not p or not os.path.isfile(lvl):
            errors.append(f"{root}: level {p!r} missing zarr.json")
            continue
        lmeta = load_json(lvl)
        shape = lmeta.get("shape")
        if axes and shape and len(shape) != len(axes):
            errors.append(f"{root}: level {p} rank {len(shape)} != axes {len(axes)}")
        scale = None
        for ct in ds.get("coordinateTransformations", []):
            if ct.get("type") == "scale":
                scale = ct.get("scale")
        if axes and scale and len(scale) != len(axes):
            errors.append(f"{root}: level {p} scale rank {len(scale)} != axes {len(axes)}")

    return errors


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    all_errors = []
    for root in argv[1:]:
        errs = check_dataset(root)
        n_levels = 0
        zj = os.path.join(root, "zarr.json")
        if os.path.isfile(zj):
            ome = (load_json(zj).get("attributes") or {}).get("ome") or {}
            n_levels = len((ome.get("multiscales") or [{}])[0].get("datasets", []))
        status = "OK" if not errs else "FAIL"
        print(f"{status}  {root}  ({n_levels} levels)")
        all_errors += errs
    for e in all_errors:
        print("  -", e, file=sys.stderr)
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
