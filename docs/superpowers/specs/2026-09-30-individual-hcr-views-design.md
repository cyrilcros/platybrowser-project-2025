# Individual HCR samples → `all_HCRs` dropdown (design)

Date: 2026-09-30
Branch: `individual_HCRs` (worktree `.worktrees/individual_HCRs`, based on `main` @ `4881da6`)

## Goal

Expose the 351 individual HCR-spotiflow samples — already present as BDV/N5 XMLs
in the repo and already uploaded to the Minio→NetApp bucket — as MoBIE sources
and views, so they can be browsed in the viewer from one dropdown, grouped by
gene, with each replicate shown in its own colour.

## Scope

In scope: `data/platybrowser_6dpf/dataset.json` only, plus a new committed
generator script and its unit test under `2025_scripts/`.

Non-goals / constraints:

- **S3 is read-only.** No object is uploaded, moved, or modified on
  `buckets.embl.de` (or anywhere else). This change is git metadata only.
- No XML edits. The 351 `HCR_individual` XMLs already exist on `main` and already
  point at `https://buckets.embl.de` / bucket `platybrowser-n5-generic` / key
  prefix `platybrowser-all-hcrs-temp/`.
- No change to any existing source or view.
- No camera transform, no `raw` EM layer on these views.

## Data model

### Sources (351)

One `image` source per `HCR_individual/*.xml`. Source **key = raw XML stem**
(e.g. `Ache2_AP155--vsx2-ache2_pl1-2`); the source body is:

```json
{
  "image": {
    "imageData": {
      "bdv.n5.s3": {
        "relativePath": "images/bdv-n5-s3/HCR_individual/<stem>.xml"
      }
    }
  }
}
```

The raw stem is the key so the JSON is unambiguous and stable; a friendly label
is used only for display.

### Views (79) — dropdown `all_HCRs`

One view per leading gene token; the view name is the gene (e.g. `Ache2`).
`uiSelectionGroup` = `all_HCRs`, additive (`isExclusive` omitted = false).

Each view's `sourceDisplays` is **one `imageDisplay` per replicate**, because
`ImageDisplay.color` in `mobie-viewer-fiji` is a single `String` shared by all
sources of a display (verified in
`src/main/java/org/embl/mobie/lib/serialize/display/ImageDisplay.java`). Each
entry:

```json
{
  "imageDisplay": {
    "sources": ["Ache2_AP155--vsx2-ache2_pl1-2"],
    "color": "r=255,g=0,b=255,a=255",
    "contrastLimits": [0.0, 1.0],
    "name": "Ache2 (AP155) | vsx2-ache2 | pl1-2"
  }
}
```

### Labels

Display `name` = `{gene} ({APprobe}) | {panel} | pl{rep}-{run}`, with the probe
segment omitted when the stem has no `_AP{probe}` and `-{run}` omitted when the
stem has no run. Examples:

- `Ache2 (AP155) | vsx2-ache2 | pl1-2`
- `Arx | ptf1-arx | pl1-1`

### Colours

A fixed 12-entry palette indexed by replicate number, so the same replicate
number has the same colour in every gene view. Explicit ARGB strings
(`r=..,g=..,b=..,a=255`) avoid any dependence on named-colour parsing and on
`randomFromGlasbey`.

| # | colour | RGB |
|---|--------|-----|
| 1 | magenta | 255,0,255 |
| 2 | green | 0,255,0 |
| 3 | cyan | 0,255,255 |
| 4 | yellow | 255,255,0 |
| 5 | red | 255,0,0 |
| 6 | blue | 0,128,255 |
| 7 | orange | 255,128,0 |
| 8 | purple | 160,32,240 |
| 9 | teal | 0,190,160 |
| 10 | pink | 255,105,180 |
| 11 | brown | 165,90,40 |
| 12 | grey | 160,160,160 |

Max replicates per gene is 9 (`Ptf1`), so 12 is sufficient with headroom.

## Parsing, sorting, grouping

Stem grammar:

```
{gene}[_AP{probe}]--{panel}_[Pp][Ll]{rep}[-{run}]
```

Rules:

- `pl`/`Pl` are treated identically (case-insensitive).
- `_AP{probe}`, `panel` and `-{run}` are optional.
- Fallback: a stem that does not match (only `Prox_prox-brn3-sfg_pl3`, which uses
  `_` instead of `--`) is normalised by treating the first `_` as the `--`
  separator, so it folds into `Prox` as an extra replicate.
- Ordering: gene groups A→Z; within a group, replicate ascending, then run
  ascending, then raw stem as a stable tie-break.
- `C-Opsin2` vs `C-Opsin2-2`, `Otx` vs `OTX`, `NeoDCC` vs `NeoDCC2`,
  `Or1L8-1` vs `Or1L8-2` remain separate groups — they are distinct probes/panels.
- Expected result: 351 samples → 79 gene views (80 groups before folding the one
  fallback into `Prox`).

## Implementation

New script `2025_scripts/add_individual_hcr_sources_and_views.py`, following the
existing pattern of `add_sources_and_views_to_n5_s3_data.py` /
`add_proba_sources_and_views.py`:

- Input: `--dataset-json`, `--xml-dir` (default
  `data/platybrowser_6dpf/images/bdv-n5-s3/HCR_individual`), `--group` (default
  `all_HCRs`), `--write` (default dry-run that prints a summary only).
- Emits concise views: omit every field equal to a viewer default
  (`isExclusive: false`, `opacity`, `visible`, `invert`, `showImagesIn3d`, …), per
  AGENTS.md "Writing concise views".
- Idempotent: re-running on an already-populated `dataset.json` makes no change
  (sources and views keyed by stem/gene; skip existing).
- Preserves the order of all pre-existing keys; appends new sources at the end of
  `sources` and new views at the end of `views`.

Unit test `2025_scripts/tests/test_add_individual_hcr_sources_and_views.py`:

- grouping/sorting on a small synthetic XML set, including the `Pl` casing, a
  missing probe, a missing run, and the `_`-separator fallback;
- one `imageDisplay` per replicate, correct palette colour per replicate;
- no default-valued keys emitted;
- idempotency (second run is a no-op).

## Verification

- `python3 -m pytest 2025_scripts/tests/test_add_individual_hcr_sources_and_views.py`
  passes.
- After generation:
  - `python3 2025_scripts/validate_dataset_json.py` passes;
  - `python3 2025_scripts/compress_dataset_json.py` is a no-op (generator already
    emits concise views).
- Counts: 351 new sources, 79 new views, 351 `imageDisplay` entries total, and
  every `HCR_individual/*.xml` referenced exactly once; no existing source/view
  changed.
- Manual MoBIE check: open the branch → `platybrowser_6dpf` → `all_HCRs` dropdown;
  a gene view (e.g. `Ptf1`, 9 replicates) shows each replicate in a distinct
  palette colour.
- `git diff --stat` touches only `dataset.json` (+ the generator/test/spec).

## Risks

- `dataset.json` grows by roughly 150–250 KB (351 sources + 351 displays). This is
  inherent to exposing the data; the concise-view convention keeps it as small as
  possible.
- Two near-duplicate `Prox … _pl3` stems exist; both are included (one folds in via
  the fallback rule) and labelled so they remain distinguishable.
