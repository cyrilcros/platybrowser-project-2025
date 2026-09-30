#!/usr/bin/env python3
"""Normalise OME-Zarr root metadata so the zarr can be used as a MoBIE source.

tensorswitch writes label volumes with `--data-type labels`, which (a) sets
`attributes.ome.multiscales[0].name = "segmentation"` and (b) adds the NGFF
`labels` convention (nested `labels/segmentation/s0`, `attributes.ome.labels`).

For MoBIE `ome.zarr.s3` sources the spec requires
`multiscales[0].name` to equal the source name, and we want a plain image
layout, so this rewrites each zarr's root `zarr.json`:

  - `attributes.ome.multiscales[0].name` -> `<basename without .ome.zarr>`
  - drop `attributes.ome.labels`

It does not touch array data or scales, and is a no-op when already normalised.

Usage: normalise_omezarr_metadata.py <mc-alias>/<bucket>/<prefix>
Example:
  normalise_omezarr_metadata.py EmblArendtS3/platybrowser-2025/fibsem/ome-zarr
"""
import json
import os
import subprocess
import sys
import tempfile


def mc(*args):
    return subprocess.run(["mc", *args], capture_output=True, text=True)


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    prefix = argv[1].rstrip("/")

    listing = mc("ls", prefix + "/").stdout.split()
    zarrs = sorted(t for t in listing if t.endswith(".ome.zarr/"))
    if not zarrs:
        print(f"no *.ome.zarr under {prefix}", file=sys.stderr)
        return 1

    rc = 0
    for z in zarrs:
        name = z[:-1].replace(".ome.zarr", "")
        path = f"{prefix}/{z}zarr.json"
        got = mc("cat", path)
        if got.returncode != 0:
            print(f"skip {name}: no zarr.json")
            continue
        doc = json.loads(got.stdout)
        ome = (doc.get("attributes") or {}).get("ome")
        if not ome:
            print(f"skip {name}: no attributes.ome")
            continue
        ms = (ome.get("multiscales") or [{}])[0]
        changed = False
        if ms.get("name") != name:
            ms["name"] = name
            changed = True
        if "labels" in ome:
            del ome["labels"]
            changed = True
        if not changed:
            print(f"ok    {name} (already normalised)")
            continue
        fd, tmp = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        with open(tmp, "w") as fh:
            json.dump(doc, fh, indent=2)
        put = mc("cp", tmp, path)
        os.remove(tmp)
        if put.returncode == 0:
            print(f"fixed {name}: name='{name}', labels attr dropped")
        else:
            print(f"FAIL  {name}: {put.stderr.strip()}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
