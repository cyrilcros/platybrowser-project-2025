# Nuclei Probability Dropdown (`proba_as_dropdown`)

Date: 2026-08-25
Status: Approved design (pending spec review)
Branch: `proba_as_dropdown`

## Goal

Let users browse cell-type assignment probabilities for nuclei in MoBIE through a
dropdown: one entry per detailed cell type (clade subtype), rendered as a
viridis probability overlay on the nuclei segmentation. The overlay is additive —
it layers on top of whatever the user already has open (typically the EM).

## Approach (chosen)

MoBIE-native **segmentation views**: one additive view per subtype that colors
the existing `nuclei` segmentation source by that subtype's probability column,
using the `viridisZeroTransparent` LUT. No new image data is generated or
stored.

This was chosen after verifying in the `mobie-viewer-fiji` source
(`org/embl/mobie/lib/serialize/display/ImageDisplay.java`,
`org/embl/mobie/lib/color/ColorHelper.java`, and the MoBIE spec) that
`imageDisplay` has only a `color` field (single color / ARGB / named color) and
**no** `lut` field — colormap LUTs (`viridis`, `glasbey`, `blueWhiteRed`,
`argbColumn`, `viridisZeroTransparent`) exist only on
`segmentationDisplay`/`spotDisplay`/`regionDisplay`. Therefore per-cell-type
probability *images* cannot render as viridis in dataset.json. The alternative
of baking the viridis colormap into ARGB image sources was considered and
rejected by the user in favour of the segmentation-view approach.

## Data source

`data/platybrowser_6dpf/tables/sbem-6dpf-1-whole-segmented-nuclei/detailed_cell_types_cluster_probability.tsv`

- 11,382 nuclei (one row per `label_id`)
- **275 subtype probability columns** (all `clade*` / `nocladesub*` columns;
  excludes `label_id`, `zero`, `autofluorescence`, `most probable cluster`)
- Values are floats in [0, 1]; the raw column values are used directly for
  coloring (no quantization needed in this approach)

The same idiom already exists in `dataset.json`:
`Fig2_prediction_brain_ACh_SSN_bsx_Dlx` colors `nuclei` by a subtype column
(`clade11sub48`) with `lut: "viridisZeroTransparent"` and
`additionalTables: ["master_top_10_ranks.tsv"]`.

## Deliverable

1. **`2025_scripts/generate_proba_views.py`** — generator script (uv inline
   script metadata, following the existing `2025_scripts/` pattern).
   - Reads the detailed probability table header.
   - Emits one view per subtype column (275 views).
   - Writes the views into `data/platybrowser_6dpf/dataset.json` under the
     `nuclei_probabilities` uiSelectionGroup, preserving all existing content.
   - `--dry-run` prints the generated views without editing (default), and a
     flag/argument writes them into `dataset.json`.

2. **275 views in `dataset.json`** under the `nuclei_probabilities` group.

### Exact view shape (concise form)

```json
{
  "uiSelectionGroup": "nuclei_probabilities",
  "sourceDisplays": [
    {
      "segmentationDisplay": {
        "sources": ["nuclei"],
        "lut": "viridisZeroTransparent",
        "colorByColumn": "<subtype>",
        "valueLimits": [0.0, 1.0],
        "additionalTables": ["detailed_cell_types_cluster_probability.tsv"],
        "name": "<subtype>"
      }
    }
  ]
}
```

Field rationale (all defaults omitted per "Writing concise views"):

| Field | Value | Why |
|---|---|---|
| `uiSelectionGroup` | `nuclei_probabilities` | Dropdown menu label |
| `isExclusive` | omitted (= false) | Additive toggle, layers on existing state |
| `viewerTransform` | omitted | Toggling must not move the camera |
| `sourceDisplays` | one `segmentationDisplay` | No `raw` imageDisplay — non-exclusive views must not add a second `raw` layer (handcrafted-view convention) |
| `sources` | `["nuclei"]` | Probability columns live on the nuclei table |
| `lut` | `viridisZeroTransparent` | Probability 0 → invisible; nonzero → viridis ramp (purple→yellow) |
| `colorByColumn` | `<subtype>` | The probability column to color by |
| `valueLimits` | `[0.0, 1.0]` | Probability range; 1.0 = brightest |
| `additionalTables` | `["detailed_cell_types_cluster_probability.tsv"]` | Makes the probability columns available for coloring |
| `name` | `<subtype>` | Required; UI panel label |

View key naming: `<subtype>_proba` (e.g. `clade1sub1_proba`), so entries sort
by subtype in the dropdown.

## Workflow

1. **Pilot (5 views first).** Representative subtypes spanning the space:
   one abundant (`clade6sub19`), one rare, one `nocladesubX`, a CNS subtype,
   and a midgut subtype (e.g. `clade1sub2`). Generate only these 5, validate
   in the MoBIE Fiji viewer:
   - correct coloring (nonzero nuclei graded, zero invisible)
   - additive behavior (no camera jump, no duplicate `raw`)
   - dropdown entry appears under `nuclei_probabilities`
2. **Full run (275 views).** Generate all views in one commit.
3. **Post-commit checks.** The pre-commit hook runs
   `2025_scripts/compress_dataset_json.py` (strips default keys, auto-stages)
   and `2025_scripts/validate_dataset_json.py`. GitHub Actions enforces both on
   `main`.

## Verification

- `python 2025_scripts/validate_dataset_json.py` passes after the view edits.
- `git diff` on `dataset.json` shows only added views (no existing content
  altered, no key reordering of unrelated entries).
- Manual MoBIE validation by the user in Fiji (pilot step above).
- Confirm view count: 275 new views under `nuclei_probabilities` (pilot: 5).

## Constraints / non-goals

- No new image sources, N5 files, BDV XML, or S3 uploads. The earlier idea of
  per-subtype probability images at `images/bdv-n5-s3/celltype_proba/` is
  dropped.
- No changes to tables: `detailed_cell_types_cluster_probability.tsv` already
  exists and is referenced as an additional table.
- No changes to the `nuclei` source definition or the default table.
- Do not touch legacy directories or raw image data (AGENTS.md rules).
- Views are generated (not handcrafted) — they live in `dataset.json` directly,
  not in `2026_views_curated/`, and are not synced from there.

## Rejected alternatives (record)

1. **Per-subtype probability image sources** (copy nuclei N5, write
   `round(p × 1000)` uint16 per nucleus). Rejected because `imageDisplay`
   cannot render viridis; also would store ~275 copies of a
   3438×3240×2854 volume (compression-friendly but heavy to generate/upload).
2. **ARGB images with baked-in viridis.** Rejected by the user in favour of the
   segmentation-view approach.
3. **Broad types (17) instead of detailed (~275).** Rejected by the user —
   detailed subtypes wanted.
