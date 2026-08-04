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

## View inventory

- **brain_ACh_MN_mnx_phox2_Lhx15** → `N_mpro__clade11sub51__brain_ACh_MN_mnx_phox2_Lhx15`
  - `_no_markers`: 18 cells, 18 nuclei, 0 traces
  - `_illustrated`: markers [hb9, phox2b, lhx15, asci, ascii]
- **brain_DA_IN_Emx_Six12** → `NMC_mect06__clade10sub7subsub4__brain_DA_IN_Emx_Six12`
  - `_no_markers`: 30 cells, 28 nuclei, 0 traces
  - `_illustrated`: markers [nompc3, asicalpha, th]
- **brain_DA_IN_Emx_Six12_Ant** → `NMC_mect06__clade10sub7subsub4__brain_DA_IN_Emx_Six12_Ant`
  - `_no_markers`: 2 cells, 2 nuclei, 1 traces
  - `_illustrated`: markers [nompc3, th, asicalpha, vglut]
- **brain_Glu_IN_TAL_lhx3** → `N_psin01__clade11sub21__brain_Glu_IN_TAL_lhx3`
  - `_no_markers`: 99 cells, 97 nuclei, 0 traces
  - `_illustrated`: markers [gata123, hand, phox2b, chat, tal, vglut, prox, hb9, asicalpha, lhx3, coe]
- **brain_Glu_LLE-PRC2_FEZF_AP2** → `N_rprc__clade11sub45subsub0__brain_Glu_LLE-PRC2_FEZF_AP2`
  - `_no_markers`: 1 cells, 1 nuclei, 0 traces
  - `_illustrated`: markers [fezf, nk21, ap2]
- **brain_Glu_mechSN_FEZF_PouIV_Vsx_Nkx2-1** → `NMC_mecp__clade10sub9__brain_Glu_mechSN_FEZF_PouIV_Vsx_Nkx2-1`
  - `_no_markers`: 63 cells, 59 nuclei, 0 traces
  - `_illustrated`: markers [fezf, brn3a, chx10, nk21]
- **brain_ls_IN_TAL_GATA_Pax258** → `N_psin02__clade11sub34__brain_ls_IN_TAL_GATA_Pax258`
  - `_no_markers`: 60 cells, 59 nuclei, 0 traces
  - `_illustrated`: markers [pax258, gata123, tal, coe, vglut, prox]
- **brain_ls_pyg_ACh_SN_Phox2_HAND** → `N_visc02__clade11sub22subsub4__brain_ls_pyg_ACh_SN_Phox2_HAND`
  - `_no_markers`: 109 cells, 106 nuclei, 0 traces
  - `_illustrated`: markers [(none — view skipped)]
- **brain_NA_IN_Phox2_Isl_Coe** → `N_casc__clade11sub27subsub8__brain_NA_IN_Phox2_Isl_Coe`
  - `_no_markers`: 17 cells, 16 nuclei, 0 traces
  - `_illustrated`: markers [isl, phox2b, coe, th]
- **brain_or_ls_pyg_Glu_mechSN_POUVI_Lhx3** → `NMC_colr__clade10sub3subsub5-9__brain_or_ls_pyg_Glu_mechSN_POUVI_Lhx3`
  - `_no_markers`: 141 cells, 127 nuclei, 4 traces
  - `_illustrated`: markers [brn3a, lhx3, pkd1 | XLOC_027897 : HCR-spotiflow (AP_011), baiap, coe, isl, barh1, trpv4]
- **brain_palpae_Glu_mechSN_Pax258_Dach** → `NMC_mect02__clade10sub11__brain_palpae_Glu_mechSN_Pax258_Dach`
  - `_no_markers`: 10 cells, 10 nuclei, 0 traces
  - `_illustrated`: markers [dach, nompc3, pax258, vglut, asicalpha]
- **brain_SSN_bsx_COE** → `NAP_cyss6__clade11sub3subsub9__brain_SSN_bsx_COE`
  - `_no_markers`: 23 cells, 22 nuclei, 0 traces
  - `_illustrated`: markers [(none — view skipped)]
- **brain_SSN_six4_PDF_G0-R** → `NAP_cyss11__clade11sub60__brain_SSN_six4_PDF_G0-R`
  - `_no_markers`: 22 cells, 22 nuclei, 0 traces
  - `_illustrated`: markers [six4, allcr1, pdf, hr38]
- **brain_TYR-DA-ACh_NSC_foxA_nk2-1** → `N_mpro03__clade11sub16subsub7__brain_TYR-DA-ACh_NSC_foxA_nk2-1`
  - `_no_markers`: 23 cells, 12 nuclei, 0 traces
  - `_illustrated`: markers [dbx1, for, ptf1, nk21, ap2, eya, chat, lmx1, six4, th]
- **fg_GABA_SN_Dbx_Ptf1a** → `N_ipro01__clade11sub28subsub3__fg_GABA_SN_Dbx_Ptf1a`
  - `_no_markers`: 44 cells, 43 nuclei, 0 traces
  - `_illustrated`: markers [(none — view skipped)]
- **brain_ACh_SSN_bsx_Dlx** → `NAP_mbdclp__clade11sub48__brain_ACh_SSN_bsx_Dlx`
  - `_no_markers`: 57 cells, 0 nuclei, 28 traces
  - `_illustrated`: markers [bsx, dlx, six4]
- **hg_Glu_EN_nkx22_lmx1_mnx** → `NEE_eens01__nocladesub16__hg_Glu_EN_nkx22_lmx1_mnx`
  - `_no_markers`: 4 cells, 4 nuclei, 0 traces
  - `_illustrated`: markers [lmx1, hb9, nk22, vglut, syt7]
- **ls1_5HT_MN_Pitx_GATA123_lhx15** → `N_mser03__clade11sub20subsub0-1-2-4-6__ls1_5HT_MN_Pitx_GATA123_lhx15`
  - `_no_markers`: 41 cells, 38 nuclei, 0 traces
  - `_illustrated`: markers [sert, trph, prox, nk6, lhx15, uncx, fvri, gata123]
- **ls2-3_5HT_MN** → `N_mser04__clade11sub20subsub3__ls2-3_5HT_MN`
  - `_no_markers`: 66 cells, 66 nuclei, 2 traces
  - `_illustrated`: markers [sert, trph, prox, nk6, pitxb, gata123]
- **ls_ACh_MN_Mnx_Lhx3_Pitx** → `N_prem__clade11sub29subsub5__ls_ACh_MN_Mnx_Lhx3_Pitx`
  - `_no_markers`: 50 cells, 48 nuclei, 2 traces
  - `_illustrated`: markers [hb9, lhx3, pitxb]
- **ls_GABA_cSN_Dbx_Ptf1a** → `N_ipro02__clade11sub5subsub10__ls_GABA_cSN_Dbx_Ptf1a`
  - `_no_markers`: 71 cells, 70 nuclei, 3 traces
  - `_illustrated`: markers [gad, dbx1, brn124]
- **ls_HIS_VSN_foxQ2_phox2** → `N_moss__clade11sub6subsub11__ls_HIS_VSN_foxQ2_phox2`
  - `_no_markers`: 56 cells, 54 nuclei, 2 traces
  - `_illustrated`: markers [phox2b, coe, brn3a]
- **ls_pyg_Glu_cIN_Evx** → `N_spro01__clade11sub13subsub5__ls_pyg_Glu_cIN_Evx`
  - `_no_markers`: 76 cells, 72 nuclei, 4 traces
  - `_illustrated`: markers [eve, vglut, brn3a, lhx15, lbx1b, asicalpha, allcr1]
- **pyg_Glu_SN_POU4_BarH1_Isl** → `N_psem02__clade11sub6subsub6__pyg_Glu_SN_POU4_BarH1_Isl`
  - `_no_markers`: 88 cells, 83 nuclei, 0 traces
  - `_illustrated`: markers [barh1, isl, brn3a, coe]

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
  match. Source moved from `detlev_handcrafted_views_questionable/` to
  `detlev_handcrafted_views_deleted/`, view removed from `dataset.json`.

- **ACh_SN_Phox2_HAND family (2026-08-04)**: Three views existed
  (`brain_ls_pyg_*`, `brain__ls_pyg_*`, `brain_pyg_*`). Only
  `brain_ls_pyg_ACh_SN_Phox2_HAND` → `N_visc02__clade11sub22subsub4__brain_ls_pyg_ACh_SN_Phox2_HAND`
  is valid. `brain__ls_pyg_ACh_SN_Phox2_HAND` (112 cells) and
  `brain_pyg_ACh_SN_Phox2_HAND` (53 cells) were deleted — sources moved from
  `detlev_handcrafted_views_questionable/` to
  `detlev_handcrafted_views_deleted/`, views removed from `dataset.json`.
