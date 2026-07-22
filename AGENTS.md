# AGENTS.md — PlatyBrowser Project

## Project overview

This is a fork of the [PlatyBrowser](https://github.com/mobie/platybrowser-project) MoBIE project — a resource for exploring a full EM volume of a 6-day-old *Platynereis* larva combined with a gene expression atlas and tissue, cellular, and ultra-structure segmentations.

The upstream is `mobie/platybrowser-project`. This fork currently uses the GitHub repo URL `https://github.com/cyrilcros/platybrowser-project-2025` as the MoBIE project entry point. Current work focuses on the `platybrowser_6dpf` dataset only.

## Active vs legacy

**Only `data/platybrowser_6dpf/` is actively maintained.** Everything else is legacy from the original 2019–2020 publication and should not be modified:

| Directory | Author | Last touched | Status |
|-----------|--------|-------------|--------|
| `segmentation/` | Constantin Pape | 2019 | Legacy — original paper |
| `registration/` | Constantin Pape | 2019 | Legacy — original paper |
| `mmpb/` | Constantin Pape | Feb 2020 | Legacy — original backend library |
| `analysis/` (all subdirs) | Constantin Pape | 2020 | Legacy — original paper analyses |
| `misc/` | Constantin Pape | 2019–2020 | Legacy — original bookmarks |
| `software/` | Constantin Pape | 2020 | Legacy — original conda envs |
| `data/0.0.0` through `data/1.0.1` | Constantin Pape | 2019–2021 | Legacy — old versioned datasets |
| `data/platybrowser_6dpf/` | Cyril Cros | Aug 2025 | **Active** — current dataset |

**Snakemake** was used for the original 2020 publication analyses (gene clustering, morphology clustering). It is no longer used. The Snakefiles, rules, and scripts in `analysis/` are kept for reference only — do not run or modify them.

Do not edit the legacy directories unless explicitly asked. Treat them as read-only historical artifacts.

## Data structure

### MoBIE project layout

The project follows the [MoBIE specification v0.3.0](https://mobie.github.io/specs/mobie_spec.html). A MoBIE project is organized around four key concepts:

**Project** — top-level container grouping datasets. Defined by `data/project.json`, which lists available datasets, the default dataset, a description, references, and the spec version. The current `project.json` lists all historical versioned datasets but defaults to `platybrowser_6dpf`.

**Dataset** — a self-contained collection of sources, views, images, and tables. Defined by `dataset.json` in the dataset root. Must contain `images/` (BDV XML metadata), `tables/` (derived tabular data), and optionally `misc/` (bookmarks, extra views).

**Source** — a single image, segmentation, spots, or regions dataset. Four types exist:
- `image` — intensity images (EM, light microscopy)
- `segmentation` — label masks with integer-labeled objects, plus an associated table directory
- `spots` — point-like data (e.g., gene detections), defined purely by a table
- `regions` — region annotations referencing a region table

Supported image data formats: `bdv.n5`, `bdv.n5.s3`, `bdv.hdf5`, `bdv.ome.zarr`, `bdv.ome.zarr.s3`, `ome.zarr`, `ome.zarr.s3`, `openOrganelle.s3`.

**View** — a complete viewer state. Defined in `dataset.json` under `views` (or in `misc/views/` as separate JSON files). Contains:
- `sourceDisplays` — arrays of `imageDisplay`, `segmentationDisplay`, `spotDisplay`, or `regionDisplay` specifying which sources to show with what color maps, opacity, LUT, contrast limits, and table settings
- `sourceTransforms` — affine, crop, mergedGrid, transformedGrid, and timepoints transformations applied to sources
- `viewerTransform` — the initial viewer camera position, rotation, and timepoint
- `uiSelectionGroup` — which UI menu group to show this view under (e.g. `"bookmark"`)

A dataset must contain a `default` view. Views can be exclusive (replace current state) or additive (layer on top).

### Active dataset: `data/platybrowser_6dpf/`

```
data/platybrowser_6dpf/
├── dataset.json          # Sources, views, defaultLocation
├── images/
│   └── local/            # BDV XML metadata for local images
├── tables/               # TSV tables keyed by source name
│   ├── sbem-6dpf-1-whole-segmented-cells/    # Cells (default table + genes, regions, morphology, clusters, etc.)
│   ├── sbem-6dpf-1-whole-segmented-nuclei/   # Nuclei
│   ├── sbem-6dpf-1-whole-segmented-ganglia/  # Ganglia
│   ├── prospr-6dpf-1-whole-virtual-cells/   # ProSPr virtual cells
│   └── ...
└── misc/
    ├── dynamic_segmentations.json
    └── ...
```

### Table conventions

- Every table directory must contain a `default.tsv` (or `default.csv`) with at minimum: `label_id`, `anchor_x`, `anchor_y`, `anchor_z`, `bb_min_x/y/z`, `bb_max_x/y/z`.
- Additional tables must contain `label_id` and may contain arbitrary extra columns. Label IDs in additional tables must be a subset of those in the default table.
- Label ID `0` is reserved for background and must not appear in tables.
- Use TSV (tab-separated) by preference per the MoBIE spec, though CSV is also supported.

### Image naming convention

```
MODALITY-STAGE-ID-REGION
```

Examples: `sbem-6dpf-1-whole-segmented-cells`, `prospr-6dpf-1-whole`

## Do not touch

- **Raw image data on network drives or S3** — never modify, delete, or move actual image data (N5, HDF5) on network drives (`W:/`, `Z:/`) or the S3 bucket. These are read-only references. Only metadata in git may be edited.
- **Legacy directories** — `segmentation/`, `registration/`, `mmpb/`, `analysis/`, `misc/`, `software/`, and old `data/` version directories (`0.0.0`–`1.0.1`) are historical artifacts. Do not edit.
- **MoBIE-breaking structural changes** — validate against the [MoBIE spec](https://mobie.github.io/specs/mobie_spec.html) before any changes to `data/project.json`, `dataset.json`, or table/image structure.
- **Upstream divergence** — this is a fork of `mobie/platybrowser-project`. Avoid changes that would make future merging impossible.

## When you can edit

- `data/platybrowser_6dpf/dataset.json` — add or modify sources, views, sourceTransforms, sourceDisplays
- `data/platybrowser_6dpf/tables/` — add new tables, update table contents following the MoBIE table spec
- `data/platybrowser_6dpf/images/local/` — add new BDV XML metadata files for new image sources
- `data/platybrowser_6dpf/misc/` — add bookmarks, additional view JSON files
- `data/project.json` — only if adding a new dataset to the list

## Verification

- MoBIE structural validity: the viewer will fail to load if `dataset.json`, table columns, or BDV XML references are broken. Validate manually with the MoBIE Fiji plugin.
- Table integrity: ensure `label_id` columns are consistent across all tables for a source, and that `default.tsv` always has the mandatory spatial columns.
