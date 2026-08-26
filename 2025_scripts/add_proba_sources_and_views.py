#!/usr/bin/env -S uv run
# /// script
# dependencies = ["numpy", "z5py"]
# ///
"""Add per-subtype probability sources and views to dataset.json.

Reads the subtype columns from the detailed cluster probability table and adds
one image source ({subtype}_proba, bdv.n5 + bdv.n5.s3) and one additive view
per subtype to dataset.json under the nuclei_probabilities uiSelectionGroup.

Views are named WITHOUT the _proba suffix (view key and display name =
{subtype}, source = {subtype}_proba) and the group's views are kept naturally
sorted so the MoBIE dropdown is ordered. Idempotent: existing names are left
untouched. Dry-run by default; use --write to apply.

Usage:
    ./add_proba_sources_and_views.py --dataset-json <dataset.json> --table <tsv> [--subtypes a,b,c] [--write]
"""

import argparse
import json
import re
import sys
from pathlib import Path

from generate_nuclei_proba_images import read_subtype_columns

UI_GROUP = "nuclei_probabilities"
S3_PREFIX = "images/bdv-n5-s3/celltype_proba"


def natural_key(s):
    return tuple(
        (0, int(p)) if p.isdigit() else (1, p)
        for p in re.split(r"(\d+)", s) if p
    )


def source_definition(name):
    return {
        "image": {
            "imageData": {
                "bdv.n5": {"relativePath": f"images/local/{name}.xml"},
                "bdv.n5.s3": {"relativePath": f"{S3_PREFIX}/{name}.xml"},
            }
        }
    }


def view_definition(subtype):
    return {
        "uiSelectionGroup": UI_GROUP,
        "sourceDisplays": [{
            "imageDisplay": {
                "sources": [f"{subtype}_proba"],
                "contrastLimits": [0.0, 1000.0],
                "name": subtype,
            }
        }],
    }


def reorder_group(views):
    """Keep the group's views contiguous and naturally sorted (dropdown order)."""
    group = {k: v for k, v in views.items() if v.get("uiSelectionGroup") == UI_GROUP}
    if not group:
        return
    for k in group:
        del views[k]
    for k in sorted(group, key=natural_key):
        views[k] = group[k]


def add_sources_and_views(dataset, subtypes, with_views=True):
    sources = dataset.setdefault("sources", {})
    views = dataset.setdefault("views", {})
    for subtype in subtypes:
        name = f"{subtype}_proba"
        if name not in sources:
            sources[name] = source_definition(name)
        if with_views and subtype not in views:
            views[subtype] = view_definition(subtype)
    if with_views:
        reorder_group(views)
    return dataset


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset-json", required=True,
                   help="Path to data/platybrowser_6dpf/dataset.json")
    p.add_argument("--table", required=True,
                   help="Path to detailed_cell_types_cluster_probability.tsv")
    p.add_argument("--subtypes", default=None,
                   help="Comma-separated subtypes (default: all from the table)")
    p.add_argument("--no-views", action="store_true",
                   help="Add only the sources, skip the views/dropdown items")
    p.add_argument("--write", action="store_true",
                   help="Apply changes to dataset.json (default: dry-run)")
    return p.parse_args()


def main():
    args = parse_args()
    subtypes = args.subtypes.split(",") if args.subtypes else read_subtype_columns(args.table)
    if not subtypes:
        sys.exit("No subtypes selected")
    ds_path = Path(args.dataset_json)
    with open(ds_path, encoding="utf-8") as f:
        dataset = json.load(f)
    before_sources = set(dataset.get("sources", {}))
    before_views = set(dataset.get("views", {}))
    add_sources_and_views(dataset, subtypes, with_views=not args.no_views)
    new_sources = set(dataset["sources"]) - before_sources
    new_views = set(dataset["views"]) - before_views
    if args.no_views:
        print(f"{len(new_sources)} new sources (views skipped: --no-views)",
              file=sys.stderr)
    else:
        print(f"{len(new_sources)} new sources, {len(new_views)} new views "
              f"(group '{UI_GROUP}')", file=sys.stderr)
    if args.write:
        with open(ds_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2)
            f.write("\n")
        print(f"Wrote {ds_path}", file=sys.stderr)
    else:
        print("Dry run: no changes written. Use --write to apply.", file=sys.stderr)


if __name__ == "__main__":
    main()
