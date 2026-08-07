# Handcrafted Views

## Source

These views were handcrafted by Detlev Arendt for the 2025 6dpf cell type atlas paper.
Each view contains preselected cells with gene marker overlays, annotated to a specific
scLocator cell type.

## Cross-referencing

Views were matched against the cell type master list
(`6dpf_atlas_paper-v1 - cell_types_masterlist.tsv`) using the "old cell type name" column.

Results are in `2025_scripts/cross_reference/`:
- `confirmed_or_good_match.tsv` — views with CSV matches (exact or safe fuzzy)
- `dubious.tsv` — double assignments in CSV, suspect fuzzy matches
- `clearly_missing.tsv` — views without CSV matches, CSV entries without view files

## Directory structure

| Directory | Count | Content |
|-----------|-------|---------|
| `detlev_handcrafted_views_valid_no_markers/` | 26 | Detlev naked views (cells + nuclei + traces, no camera, non-exclusive) |
| `detlev_handcrafted_views_valid_illustrated/` | 23 | Detlev illustrated views (markers + cells, non-exclusive) |
| `detlev_handcrafted_views_questionable/` | 8 | Unmatched or problematic views |
| `sam_naked_views/` | 6 | Sam's naked views (cells + nuclei + traces where provided) |

## Naming convention

```
{subclade}__{descriptive_name}
```

The `subclade` comes from the master list column `subclade` (the `family_types`
prefix was dropped in 2026-08-06 while the cell types are being renamed).
The producer of a view is marked by a suffix: `_detlev` or `_sam`. Each curated
cell type produces two view variants, shown in two separate dropdowns
(uiSelectionGroups):

- `{name}_detlev` / `{name}_sam` — naked views, group `curated_views`:
  segmentation only (cells + nuclei + traces if present), no camera transform,
  non-exclusive. Quick toggle for cell positions.
- `{name}_illustrated_detlev` — illustrated views, group
  `curated_views_probes_on`: gene marker imageDisplays (no raw EM) +
  segmentation, non-exclusive. For exploring the markers used to annotate the
  cell type. Only created when the view has non-raw markers.

Unresolved/questionable views live in the `status_unclear_curated_views` group.

## Syncing

When a JSON file is placed in `detlev_handcrafted_views_valid_no_markers/` or
`detlev_handcrafted_views_valid_illustrated/`, the corresponding view in
`dataset.json` should be updated to match. The JSON files in these directories
are the canonical source for these views.

## View inventory

- **brain_ACh_MN_mnx_phox2_Lhx15** → `clade11sub51__brain_ACh_MN_mnx_phox2_Lhx15`
  - `_detlev` (naked): 18 cells, 18 nuclei, 0 traces
  - `_illustrated_detlev`: markers [hb9, phox2b, lhx15, asci, ascii]
- **brain_DA_IN_Emx_Six12** → `brain_DA_IN_Emx_Six12`
  - `_detlev` (naked): 30 cells, 28 nuclei, 0 traces
  - `_illustrated_detlev`: markers [nompc3, asicalpha, th]
- **brain_DA_IN_Emx_Six12_Ant** → `brain_DA_IN_Emx_Six12_Ant`
  - `_detlev` (naked): 2 cells, 2 nuclei, 1 traces
  - `_illustrated_detlev`: markers [nompc3, th, asicalpha, vglut]
- **brain_Glu_IN_TAL_lhx3** → `brain_Glu_IN_TAL_lhx3`
  - `_detlev` (naked): 99 cells, 97 nuclei, 0 traces
  - `_illustrated_detlev`: markers [gata123, hand, phox2b, chat, tal, vglut, prox, hb9, asicalpha, lhx3, coe]
- **brain_Glu_LLE-PRC2_FEZF_AP2** → `brain_Glu_LLE-PRC2_FEZF_AP2`
  - `_detlev` (naked): 1 cells, 1 nuclei, 0 traces
  - `_illustrated_detlev`: markers [fezf, nk21, ap2]
- **brain_Glu_mechSN_FEZF_PouIV_Vsx_Nkx2-1** → `brain_Glu_mechSN_FEZF_PouIV_Vsx_Nkx2-1`
  - `_detlev` (naked): 63 cells, 59 nuclei, 0 traces
  - `_illustrated_detlev`: markers [fezf, brn3a, chx10, nk21]
- **brain_ls_IN_TAL_GATA_Pax258** → `brain_ls_IN_TAL_GATA_Pax258`
  - `_detlev` (naked): 60 cells, 59 nuclei, 0 traces
  - `_illustrated_detlev`: markers [pax258, gata123, tal, coe, vglut, prox]
- **brain_ls_pyg_ACh_SN_Phox2_HAND** → `brain_ls_pyg_ACh_SN_Phox2_HAND`
  - `_detlev` (naked): 109 cells, 106 nuclei, 0 traces
  - `_illustrated_detlev`: markers [(none — view skipped)]
- **brain_NA_IN_Phox2_Isl_Coe** → `brain_NA_IN_Phox2_Isl_Coe`
  - `_detlev` (naked): 17 cells, 16 nuclei, 0 traces
  - `_illustrated_detlev`: markers [isl, phox2b, coe, th]
- **brain_or_ls_pyg_Glu_mechSN_POUVI_Lhx3** → `brain_or_ls_pyg_Glu_mechSN_POUVI_Lhx3`
  - `_detlev` (naked): 141 cells, 127 nuclei, 4 traces
  - `_illustrated_detlev`: markers [brn3a, lhx3, pkd1 | XLOC_027897 : HCR-spotiflow (AP_011), baiap, coe, isl, barh1, trpv4]
- **brain_palpae_Glu_mechSN_Pax258_Dach** → `brain_palpae_Glu_mechSN_Pax258_Dach`
  - `_detlev` (naked): 10 cells, 10 nuclei, 0 traces
  - `_illustrated_detlev`: markers [dach, nompc3, pax258, vglut, asicalpha]
- **brain_SSN_bsx_COE** → `brain_SSN_bsx_COE`
  - `_detlev` (naked): 23 cells, 22 nuclei, 0 traces
  - `_illustrated_detlev`: markers [(none — view skipped)]
- **brain_SSN_six4_PDF_G0-R** → `brain_SSN_six4_PDF_G0-R`
  - `_detlev` (naked): 22 cells, 22 nuclei, 0 traces
  - `_illustrated_detlev`: markers [six4, allcr1, pdf, hr38]
- **brain_TYR-DA-ACh_NSC_foxA_nk2-1** → `clade11sub16subsub7` (see errata: replaced by the dubious view cell set, 2026-08-06)
  - `_detlev` (naked): 23 cells, 12 nuclei, 0 traces
  - `_illustrated_detlev`: markers [dbx1, for, ptf1, nk21, ap2, eya, chat, lmx1, six4, th]
- **fg_GABA_SN_Dbx_Ptf1a** → `fg_GABA_SN_Dbx_Ptf1a`
  - `_detlev` (naked): 44 cells, 43 nuclei, 0 traces
  - `_illustrated_detlev`: markers [(none — view skipped)]
- **brain_ACh_SSN_bsx_Dlx** → `brain_ACh_SSN_bsx_Dlx`
  - `_detlev` (naked): 57 cells, 0 nuclei, 28 traces
  - `_illustrated_detlev`: markers [bsx, dlx, six4]
- **hg_Glu_EN_nkx22_lmx1_mnx** → `hg_Glu_EN_nkx22_lmx1_mnx`
  - `_detlev` (naked): 4 cells, 4 nuclei, 0 traces
  - `_illustrated_detlev`: markers [lmx1, hb9, nk22, vglut, syt7]
- **ls1_5HT_MN_Pitx_GATA123_lhx15** → `ls1_5HT_MN_Pitx_GATA123_lhx15`
  - `_detlev` (naked): 41 cells, 38 nuclei, 0 traces
  - `_illustrated_detlev`: markers [sert, trph, prox, nk6, lhx15, uncx, fvri, gata123]
- **ls2-3_5HT_MN** → `ls2-3_5HT_MN`
  - `_detlev` (naked): 66 cells, 66 nuclei, 2 traces
  - `_illustrated_detlev`: markers [sert, trph, prox, nk6, pitxb, gata123]
- **ls_ACh_MN_Mnx_Lhx3_Pitx** → `ls_ACh_MN_Mnx_Lhx3_Pitx`
  - `_detlev` (naked): 50 cells, 48 nuclei, 2 traces
  - `_illustrated_detlev`: markers [hb9, lhx3, pitxb]
- **ls_GABA_cSN_Dbx_Ptf1a** → `ls_GABA_cSN_Dbx_Ptf1a`
  - `_detlev` (naked): 71 cells, 70 nuclei, 3 traces
  - `_illustrated_detlev`: markers [gad, dbx1, brn124]
- **ls_HIS_VSN_foxQ2_phox2** → `ls_HIS_VSN_foxQ2_phox2`
  - `_detlev` (naked): 56 cells, 54 nuclei, 2 traces
  - `_illustrated_detlev`: markers [phox2b, coe, brn3a]
- **ls_pyg_Glu_cIN_Evx** → `ls_pyg_Glu_cIN_Evx`
  - `_detlev` (naked): 76 cells, 72 nuclei, 4 traces
  - `_illustrated_detlev`: markers [eve, vglut, brn3a, lhx15, lbx1b, asicalpha, allcr1]
- **pyg_Glu_SN_POU4_BarH1_Isl** → `pyg_Glu_SN_POU4_BarH1_Isl`
  - `_detlev` (naked): 88 cells, 83 nuclei, 0 traces
  - `_illustrated_detlev`: markers [barh1, isl, brn3a, coe]

## Errata

- **brain_ACh_SSN_bsx_Dlx (2024-08-04)**: This cell type was originally named
  `Fig2_prediction_brain_ACh_SSN_bsx_Dlx` with the `Fig2_prediction_` prefix,
  which obscured the match to the CSV cell type entry in
  `cross_reference/clearly_missing.tsv`. The prefix has been dropped and the
  view now follows the standard `{family_types}__{subclade}__{descriptive_name}`
  convention. The legacy exclusive view `brain_ACh_SSN_bsx_Dlx` in
  `dataset.json` (with camera, raw EM, and markers) has been removed — it is
  superseded by the curated `_no_markers` + `_illustrated` pair.

- **brain_LLE-PC2 (2026-08-04)**: Deleted — only 2 selected cells, no CSV
  match. View removed from `dataset.json`.

- **ACh_SN_Phox2_HAND family (2026-08-04)**: Three views existed
  (`brain_ls_pyg_*`, `brain__ls_pyg_*`, `brain_pyg_*`). Only
  `brain_ls_pyg_ACh_SN_Phox2_HAND` → `brain_ls_pyg_ACh_SN_Phox2_HAND`
  is valid. `brain__ls_pyg_ACh_SN_Phox2_HAND` (112 cells) and
  `brain_pyg_ACh_SN_Phox2_HAND` (53 cells) were deleted — views removed from
  `dataset.json`.

- **dubious_clade11sub16subsub7 (2026-08-04)**: Unresolved view placed at the
  top of the curated-cell-types dropdown for inspection. 149 cells, markers
  [lmx1, for, nk21, dbx1, gad, ptf1]. The cell set does not match the
  `brain_TYR-DA-ACh_NSC_foxA_nk2-1` view
  (13/149 overlap) nor the old 8-cell `fg_GABA_MN_lmx1_sim_mnx` view
  (0 overlap). Produced as the standard `_no_markers` + `_illustrated` pair;
  source files in `detlev_handcrafted_views_valid_no_markers/` and
  `detlev_handcrafted_views_valid_illustrated/`.

- **Masterlist family renames (2026-08-06)**: The cell types masterlist was
  updated (see `platy-6dpf-inspections` commit "Update to the cell types
  masterlist"). Three curated views were renamed to the new family prefixes:
  - `...` → `...`
    (brain_SSN_six4_PDF_G0-R)
  - `...` → `...`
    (brain_or_ls_pyg_Glu_mechSN_POUVI_Lhx3)
  - `...` → `...`
    (brain_Glu_LLE-PRC2_FEZF_AP2)
  All file and `dataset.json` view names updated (9 JSON files, 6 views).

- **N_mpro03 view replacement (2026-08-06)**: The `dubious_clade11sub16subsub7`
  view (148 cells) is now the canonical view for `clade11sub16subsub7`
  (no descriptive `brain_FOO_bar` name). The old 23-cell
  `brain_TYR-DA-ACh_NSC_foxA_nk2-1` views were
  deleted (13/148 overlap with the new cell set).

- **Promoted views (2026-08-06)**: Two views previously unmatched now match the
  updated masterlist and were promoted to curated views:
  - `ls2-3_Glu_SN_Pou4_lbx` (42 cells) → `ls2-3_Glu_SN_Pou4_lbx`
    (masterlist now splits the collar-receptor family into `NMC_colr1` and `NMC_colr2`)
  - `brain_ACh_LLE_PRC3-4_rx_foxq2` (2 cells) → `brain_ACh_LLE_PRC3-4_rx_foxq2`
    (masterlist renamed family `NAP` → `NAP_cPRC3-4` for this subclade)
  Each as a standard `_no_markers` + `_illustrated` pair; the superseded legacy
  exclusive views were removed from `dataset.json`.

- **PTF1A (2026-08-06)**: `PTF1A` old-name removed from the masterlist
  (`EE_eexd`/`clade1sub19`); the view is removed intentionally. No curated view
  referenced it.

- **Cleanup (2026-08-06)**: `detlev_handcrafted_views_valid/` (archival
  originals) removed — all views are now represented by the
  `_no_markers` + `_illustrated` pairs. `detlev_handcrafted_views_deleted/`
  removed. The solved `_NOTE_brain_ACh_SSN_bsx_Dlx.txt` and
  `Fig2_prediction_brain_ACh_SSN_bsx_Dlx.json`
  removed from `detlev_handcrafted_views_multiple_versions/`.

- **multiple_versions removed (2026-08-07)**: The last file,
  `clade10sub7subsub4__brain_DA_IN_Emx_Six12_Ant.json`, was a legacy duplicate
  of the curated `clade10sub7subsub4__brain_DA_IN_Emx_Six12_Ant` view pair
  (same 2 cells: `cells;0;3535`, `cells;0;3576`) and has been deleted; the
  directory is gone.
