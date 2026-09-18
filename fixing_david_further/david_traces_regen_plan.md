# Plan — regenerate `david_all_traces` so every trace renders

Date: 2026-09-18
Companion to: `david_traces_oversized_report.md`
Status: plan only (no HPC run yet)

## Goal

Regenerate `david_all_traces.n5` (+ XML, tables, S3 copy) so that **every one of
the 284 labels is present at every pyramid level and can be meshed**, with
bounding boxes that match the data. Fixes labels 142, 277 (hang) and 159 (empty),
and the class of sparse/overlapped traces behind them.

## Root causes to fix (from the report)

1. **Duplicate trace** — 142 and 146 are the same cell (aka 32.004 / 32.2) kept
   as two labels with an identical, inflated bbox.
2. **Lossy pyramid** — rasterisation draws a radius-2 disk *per node* without
   connecting consecutive nodes, so sparse traces have gaps and 2×2×2 max-pool
   erases them (142/277/159 gone by `s2`).
3. **Wrong bboxes** — `default.tsv` bboxes are derived from node extents, not
   from the N5 voxels; 142/146 share an inflated one.
4. **Empty label** — 159 has no voxels at any level.

## Work items

### 1. Connect nodes during rasterisation (primary fix)
- In the converter (`convert_all_david_traces.py`), rasterise each **edge**
  between consecutive skeleton nodes as a line (Bresenham / `skimage.draw.line`)
  with the radius-2 disk, instead of only stamping disks at nodes.
- This makes traces continuous, so they survive max-pool downsampling.
- Optionally increase the disk radius for very sparse traces (or use an
  isotropic radius in µm rather than z-plane only — the current disk is drawn on
  the node's z-plane, which is anisotropic relative to 80/80/100 nm).

### 2. Deduplicate before labelling
- Detect duplicate cells: identical/overlapping voxel footprints (not just
  first-node fingerprint). Merge 142/146; audit the 12 source files that produce
  >1 label (`commissural_all_comm_sec_seg*.nmx`, `p0v0_all.nmx`,
  `sim_hox4.015.nmx`, `Pyg_git_pyg.005.nmx`, …).
- Keep label ids stable where possible to avoid breaking MoBIE views; where a
  label is dropped, remap and regenerate views that reference it.

### 3. Recompute bounding boxes from voxels
- After writing `s0`, compute each label's bbox by scanning the volume
  (chunked), in `(x, y, z)` µm, and write `default.tsv`.
- Add an assertion that the bbox contains the label at `s0` (catches 142/146-type
  errors).

### 4. Presence-preserving pyramid + validation
- Replace/augment the 2×2×2 max-pool with a downsampler that guarantees each
  label present at the finer level is present at the coarser level (e.g. after
  max-pool, re-stamp one voxel per label per block that contained it).
- Validation gate before upload:
  - every label 1..N has `> 0` voxels at `s0`;
  - every label is present at `s1..s7`;
  - `default.tsv` bbox equals the voxel bbox;
  - render all traces through `examples.OpenDavidTraces` (0 timeouts/failures).

### 5. Repair / drop 159
- If it is genuinely empty (nodes off-grid or overwritten), either re-rasterise
  from its `Nk6.285.nmx` with the connected-node fix, or drop it and renumber.

### 6. Re-upload and rewire
- Re-upload N5 to `EmblArendtS3/platybrowser-2025/demo-v0/david_all_traces.n5`
  (per handoff doc) and update the XMLs
  (`images/local/david_all_traces.xml`, `images/bdv-n5-s3/traces/david_all_traces.xml`).
- Regenerate derived sources if their labels change:
  `david_all_traces_nuclei`, `combined_all_traces_nuclei`.
- Re-validate the MoBIE views (`traces`, `additional_traces`).

## Scripts / locations

| artifact | location |
|---|---|
| converter (to edit) | `~/transfer_check/nmx2n5/convert_all_david_traces.py` (cluster copies `/scratch/cros/phase1/`) |
| inputs (nmx library) | `/g/arendt/David_Puga_Consolidated_data/processed/traces/` (2,025 readable nmx) |
| current N5 + mapping | `/g/arendt/David_Puga_Consolidated_data/processed/n5/` |
| handoff / context | `/g/arendt/David_Puga_Consolidated_data/processed/n5/HANDOFF_david_traces_n5.md` |
| provenance table | `data/platybrowser_6dpf/tables/david_all_traces/origin_mapping.tsv` |

## Open decisions

- **Label-id stability** vs clean renumbering (affects saved MoBIE views/selection).
- **Rasterisation thickness**: connect nodes only, or also enlarge radius — trade
  mesh size vs survival.
- Whether to keep the pure max-pool pyramid and instead rely on connected-node
  rasterisation (simpler) or add the presence re-stamp (stronger guarantee).
- Re-generate `david_all_traces_nuclei` / `combined_all_traces_nuclei` in the same
  pass or separately.
