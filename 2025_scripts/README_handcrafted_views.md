# Handcrafted Views

## Source

These views were handcrafted by Detlev Arendt for the 2025 6dpf cell type atlas paper.
Each view contains preselected cells with gene marker overlays, annotated to a specific
scLocator cell type.

## Cross-referencing

Views were matched against the cell type master list
(`6dpf_atlas_paper-v1 - cell_types_masterlist.csv`) using the "old cell type name" column.

Results are in `2025_scripts/cross_reference/`:
- `confirmed_or_good_match.tsv` — views with CSV matches (exact or safe fuzzy)
- `dubious.tsv` — double assignments in CSV, suspect fuzzy matches
- `clearly_missing.tsv` — views without CSV matches, CSV entries without view files

## Directory structure

| Directory | Count | Content |
|-----------|-------|---------|
| `detlev_handcrafted_views_valid/` | 24 | Original handcrafted JSONs (archival) |
| `detlev_handcrafted_views_valid_cells_only/` | 24 | Seg-only views, no camera, non-exclusive |
| `detlev_handcrafted_views_valid_illustrated/` | 20 | Marker overlays + cells, non-exclusive |
| `detlev_handcrafted_views_questionable/` | 13 | Unmatched or problematic views |
| `detlev_handcrafted_views_multiple_versions/` | 2 | Multiple versions of same cell type |

## Naming convention

```
{family_types}__{subclade}__{descriptive_name}
```

The prefix comes from the master list columns `family_types` and `subclade`.
Each view produces two variants in `dataset.json`:

- `{name}_cells_only` — segmentation display only (cells + nuclei + traces if present),
  no camera transform, non-exclusive. Quick toggle for cell positions.

- `{name}_illustrated` — gene marker imageDisplays (no raw EM) + segmentation,
  non-exclusive. For exploring the markers used to annotate the cell type.
  Only created when the view has non-raw markers.

## Syncing

When a JSON file is placed in `detlev_handcrafted_views_valid_cells_only/` or
`detlev_handcrafted_views_valid_illustrated/`, the corresponding view in
`dataset.json` should be updated to match. The JSON files in these directories
are the canonical source for these views.
