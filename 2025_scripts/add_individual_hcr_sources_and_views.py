#!/usr/bin/env -S uv run
# /// script
# dependencies = []
# ///
"""Expose the individual HCR-spotiflow samples as MoBIE sources + views.

Every ``*.xml`` in ``--xml-dir`` (default the 351 files in
``data/platybrowser_6dpf/images/bdv-n5-s3/HCR_individual``) becomes one ``image``
source whose key is the raw XML stem and whose ``bdv.n5.s3`` relative path points
at that XML. The stems are grouped by leading gene token; each gene becomes one
additive view under the ``--group`` dropdown (default ``all_HCRs``), with one
``imageDisplay`` per replicate so every replicate can carry its own colour.

Stem grammar::

    {gene}[_AP{probe}]--{panel}_[Pp][Ll]{rep}[-{run}]

``pl``/``Pl`` are equivalent; the probe, panel and run are optional. Stems that
do not match (there is exactly one, ``Prox_prox-brn3-sfg_pl3``) are normalised by
treating the first ``_`` as the ``--`` separator.

Views are emitted in concise form (no field equal to a viewer default) per
AGENTS.md "Writing concise views". A gene whose bare name is already used by a
view in another group gets the `" (individual)"` suffix so existing views are
never touched. Views already in the target group are refreshed in place (so
colour fixes land) and the operation stays idempotent. Dry-run by default; use
``--write`` to apply.

Usage:
    ./add_individual_hcr_sources_and_views.py --dataset-json <dataset.json> \
        [--xml-dir <dir>] [--group all_HCRs] [--write]
"""

import argparse
import json
import re
import sys
import warnings
from pathlib import Path

DEFAULT_XML_DIR = "data/platybrowser_6dpf/images/bdv-n5-s3/HCR_individual"
DEFAULT_UI_GROUP = "all_HCRs"
HCR_S3_PREFIX = "images/bdv-n5-s3/HCR_individual"

# Fixed palette indexed by replicate number (same colour for the same replicate
# in every gene view). Rep 1..12; see the design spec.
PALETTE = {
    1: (255, 0, 255),
    2: (0, 255, 0),
    3: (0, 255, 255),
    4: (255, 255, 0),
    5: (255, 0, 0),
    6: (0, 128, 255),
    7: (255, 128, 0),
    8: (160, 32, 240),
    9: (0, 190, 160),
    10: (255, 105, 180),
    11: (165, 90, 40),
    12: (160, 160, 160),
}

STEM_RE = re.compile(
    r"^(?P<gene>.+?)(?:_AP(?P<probe>\d+))?--(?P<panel>.+?)_[Pp][Ll](?P<rep>\d+)"
    r"(?:-(?P<run>\d+))?$"
)


def parse_stem(stem):
    """Parse an HCR XML stem into gene/probe/panel/rep/run.

    Falls back to treating the first ``_`` as the ``--`` separator for the one
    stem that does not match (``Prox_prox-brn3-sfg_pl3``).
    """
    match = STEM_RE.match(stem)
    if match is None:
        match = STEM_RE.match(stem.replace("_", "--", 1))
    if match is None:
        raise ValueError(f"cannot parse HCR XML stem: {stem!r}")
    groups = match.groupdict()
    return {
        "gene": groups["gene"],
        "probe": groups["probe"],
        "panel": groups["panel"],
        "rep": int(groups["rep"]),
        "run": int(groups["run"]) if groups["run"] is not None else None,
    }


def sort_key(stem, parsed):
    """Order within a gene: replicate, then run (absent = -1), then stem."""
    run = parsed["run"] if parsed["run"] is not None else -1
    return (parsed["rep"], run, stem)


def display_label(parsed):
    """Display name: ``{gene} ({probe}) | {panel} | pl{rep}[-{run}]``."""
    if parsed["probe"] is not None:
        label = f"{parsed['gene']} ({parsed['probe']}) | {parsed['panel']} | pl{parsed['rep']}"
    else:
        label = f"{parsed['gene']} | {parsed['panel']} | pl{parsed['rep']}"
    if parsed["run"] is not None:
        label += f"-{parsed['run']}"
    return label


def disambiguate(labels):
    """Make labels unique within a view by appending `` [2]``, `` [3]``, …

    Input order is the view's display order; the first occurrence keeps the bare
    label and each later collision gets the next suffix.
    """
    counts = {}
    unique = []
    for label in labels:
        n = counts.get(label, 0) + 1
        counts[label] = n
        unique.append(label if n == 1 else f"{label} [{n}]")
    return unique


def color_for_rep(rep):
    """ARGB string for a replicate number; raises if outside the palette."""
    try:
        red, green, blue = PALETTE[rep]
    except KeyError:
        raise ValueError(
            f"no palette colour for replicate {rep} (palette covers 1..{max(PALETTE)})"
        ) from None
    return f"r={red},g={green},b={blue},a=255"


def distinct_colors(reps):
    """ARGB colours for a view's displays, one per replicate, all distinct.

    The palette is indexed by replicate number, so a view with a single panel
    is exactly replicate-indexed. Within one view a colour already used by an
    earlier display is advanced to the next unused palette entry (wrapping
    around), so no two layers of a multi-panel view share a colour. Raises if
    the view has more displays than palette entries.
    """
    order = list(PALETTE)  # palette indices in order, e.g. [1..12]
    start = {rep: index for index, rep in enumerate(order)}
    used = set()
    colors = []
    for rep in reps:
        if rep not in start:
            raise ValueError(
                f"no palette colour for replicate {rep} (palette covers 1..{max(PALETTE)})"
            )
        chosen = None
        for step in range(len(order)):
            candidate = order[(start[rep] + step) % len(order)]
            if candidate not in used:
                chosen = candidate
                break
        if chosen is None:
            raise ValueError(
                f"view has more displays ({len(reps)}) than palette entries ({len(order)})"
            )
        used.add(chosen)
        colors.append(color_for_rep(chosen))
    return colors


def source_definition(stem, s3_prefix=HCR_S3_PREFIX):
    return {
        "image": {
            "imageData": {
                "bdv.n5.s3": {"relativePath": f"{s3_prefix}/{stem}.xml"},
            }
        }
    }


def build_groups(stems):
    """Group stems by gene, genes A→Z, stems sorted within each gene."""
    groups = {}
    for stem in sorted(stems):
        parsed = parse_stem(stem)
        groups.setdefault(parsed["gene"], []).append((stem, parsed))
    for entries in groups.values():
        entries.sort(key=lambda entry: sort_key(entry[0], entry[1]))
    return groups


def view_definition(entries, ui_group):
    """One imageDisplay per replicate, with a distinct colour per display."""
    labels = disambiguate([display_label(parsed) for _, parsed in entries])
    colors = distinct_colors([parsed["rep"] for _, parsed in entries])
    displays = []
    for (stem, _), label, color in zip(entries, labels, colors):
        displays.append({
            "imageDisplay": {
                "sources": [stem],
                "color": color,
                "contrastLimits": [0.0, 0.1],
                "name": label,
            }
        })
    return {"uiSelectionGroup": ui_group, "sourceDisplays": displays}


def add_sources_and_views(dataset, xml_dir, ui_group=DEFAULT_UI_GROUP,
                          s3_prefix=HCR_S3_PREFIX):
    """Add/refresh HCR sources + views in ``dataset``; return summary counts."""
    stems = sorted(
        path.stem for path in Path(xml_dir).glob("*.xml")
    )
    groups = build_groups(stems)

    sources = dataset.setdefault("sources", {})
    views = dataset.setdefault("views", {})

    sources_added = 0
    views_added = 0
    views_updated = 0
    for gene in sorted(groups):
        entries = groups[gene]
        for stem, _ in entries:
            if stem not in sources:
                sources[stem] = source_definition(stem, s3_prefix)
                sources_added += 1

        # Bare name unless it is already used by a different group, in which
        # case use the " (individual)" suffix (never touch the other view).
        if gene not in views or views[gene].get("uiSelectionGroup") == ui_group:
            name = gene
        else:
            name = f"{gene} (individual)"

        new_view = view_definition(entries, ui_group)
        existing = views.get(name)
        if existing is None:
            views[name] = new_view  # appended
            views_added += 1
        elif existing.get("uiSelectionGroup") == ui_group:
            if existing != new_view:
                views[name] = new_view  # replaced in place (key position kept)
                views_updated += 1
        else:
            warnings.warn(
                f"view {name!r} exists in group "
                f"{existing.get('uiSelectionGroup')!r}; not overwriting",
                stacklevel=2,
            )

    return {
        "xmls": len(stems),
        "genes": len(groups),
        "sources_added": sources_added,
        "views_added": views_added,
        "views_updated": views_updated,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dataset-json", required=True,
                        help="Path to data/platybrowser_6dpf/dataset.json")
    parser.add_argument("--xml-dir", default=DEFAULT_XML_DIR,
                        help=f"Directory of HCR *.xml files (default: {DEFAULT_XML_DIR})")
    parser.add_argument("--group", default=DEFAULT_UI_GROUP,
                        help=f"uiSelectionGroup for the views (default: {DEFAULT_UI_GROUP})")
    parser.add_argument("--write", action="store_true",
                        help="Apply changes to dataset.json (default: dry-run)")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    ds_path = Path(args.dataset_json)
    with open(ds_path, encoding="utf-8") as f:
        dataset = json.load(f)

    summary = add_sources_and_views(
        dataset, args.xml_dir, ui_group=args.group
    )

    print(
        f"{summary['xmls']} XMLs, {summary['genes']} genes, "
        f"{summary['sources_added']} sources added, "
        f"{summary['views_added']} views added, "
        f"{summary['views_updated']} views updated",
        file=sys.stderr,
    )

    if args.write:
        with open(ds_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2)
            f.write("\n")
        print(f"Wrote {ds_path}", file=sys.stderr)
    else:
        print("Dry run: no changes written. Use --write to apply.", file=sys.stderr)


if __name__ == "__main__":
    main()
