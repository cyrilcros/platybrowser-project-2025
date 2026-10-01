#!/usr/bin/env python3
"""Add the OME-Zarr v3 volumes as additive views in the top dropdown.

Sources are all `ome.zarr.s3` (so no XML is read; placement comes from the store
metadata):

  - the 11 fibsem zarrs on `s3.embl.de/platybrowser-2025/fibsem/ome-zarr/`
  - the 2 TB SBEM whole-raw on `s3.embl.de/hic-arendt/sbem-6dpf-1-whole-raw.zarr`

Each gets one **additive, non-3D** view in the `0 ome-zarr views` group. The
leading `0` forces the group to the top: MoBIE sorts dropdowns with
`compareToIgnoreCase` (UserInterfaceHelper), so a leading digit comes first.
Styling mirrors the N5 dataset's `default` view (white, `contrastLimits`
[0, 255]). The superseded `parapodia` and `ome_zarr_test` groups are removed.

Dry-run by default; pass --write to edit dataset.json.
"""
import argparse
import json

S3 = "https://s3.embl.de"
GROUP = "0 ome-zarr views"
SUPERSEDED_GROUPS = {"parapodia", "ome_zarr_test"}

FIB = [
    "em-raw-parapod-fib",
    "em-segmented-parapod-cells-labels",
    "em-segmented-parapod-cells-aligned-labels",
    "em-segmented-parapod-cells-labels-2019_06_18-cg",
    "em-segmented-parapod-cells-labels-2019_06_18-g",
    "em-segmented-parapod-cells-labels-2019_06_18-r",
    "em-segmented-ganglion",
    "em-segmented-ganglion-parapod-fib",
    "em-segmented-muscles-parapod-fib",
    "em-segmented-small-cirrus",
    "em-segmented-small-cirrus-parapod-fib",
]

# (source name, s3Address)
VOLUMES = [(n, f"{S3}/platybrowser-2025/fibsem/ome-zarr/{n}.ome.zarr") for n in FIB]
VOLUMES.append(
    ("sbem-6dpf-1-whole-raw-omezarr", f"{S3}/hic-arendt/sbem-6dpf-1-whole-raw.zarr")
)


def source_definition(url):
    return {"image": {"imageData": {"ome.zarr.s3": {"s3Address": url}}}}


def view_definition(name):
    return {
        "uiSelectionGroup": GROUP,
        "sourceDisplays": [
            {"imageDisplay": {"sources": [name], "contrastLimits": [0.0, 255.0], "name": name}}
        ],
    }


def add(dataset):
    sources = dataset.setdefault("sources", {})
    views = dataset.setdefault("views", {})

    removed = 0
    for view_name in list(views):
        if views[view_name].get("uiSelectionGroup") in SUPERSEDED_GROUPS:
            del views[view_name]
            removed += 1

    added_sources = added_views = 0
    for name, url in VOLUMES:
        if name not in sources:
            sources[name] = source_definition(url)
            added_sources += 1
        if views.get(name, {}).get("uiSelectionGroup") != GROUP:
            views[name] = view_definition(name)
            added_views += 1
    return removed, added_sources, added_views


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset-json", required=True)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    with open(args.dataset_json) as fh:
        dataset = json.load(fh)
    removed, s, v = add(dataset)
    print(f"superseded views removed: {removed}; sources added: {s}; views added: {v}")
    if args.write:
        with open(args.dataset_json, "w") as fh:
            json.dump(dataset, fh, indent=2)
            fh.write("\n")
        print(f"wrote {args.dataset_json}")
    else:
        print("dry run (use --write)")


if __name__ == "__main__":
    main()
