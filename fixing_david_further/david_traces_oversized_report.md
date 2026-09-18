# Oversized / non-rendering David traces — provenance & root-cause report

Date: 2026-09-18
Scope: `david_all_traces` (284 labels) in `platybrowser_6dpf`
Trigger: MoBIE 3D render of all traces stalled on `david_all_traces` labels **142** and **277**; label **159** reported "no voxels".

## 1. Summary

Three labels misbehave in the 3D viewer:

| label | symptom | what it is | n_nodes | source nmx |
|---|---|---|---|---|
| **142** | mesh creation hangs (30 s timeout) | non-commissural: big-chain extra cell | 1669 | `david/Common/PyKnossos/Tracing/Nk6_all/Nk6.502.nmx` (aka 32.004) |
| **277** | mesh creation hangs (30 s timeout) | non-commissural: TF-biased sim_hox4 | 109 | `david/1_Commissures/Tracing/biased/sim_hox4/sim_hox4.013.nmx` (aka 25220) |
| **159** | "no voxels at any level" (skipped) | non-commissural: big-chain extra cell | 95 | `david/Common/PyKnossos/Tracing/Nk6_all/Nk6.285.nmx` (aka 39) |

The hang is **not** a single corrupt nmx file. It is the combination of four
issues in the `nmx → N5 → MoBIE` pipeline plus the mesher's level fallback:

1. **Duplicate trace not deduplicated** — labels 142 and 146 are the *same cell*
   traced twice (see §3).
2. **Lossy max-pool pyramid** — thin/sparse labels are erased by 2×2×2 max-pool
   by `s2` (see §4).
3. **Wrong/inflated table bounding boxes** for the affected labels (see §3).
4. **Mesher falls back to `s0` without a voxel-count guard** — it steps to finer
   levels until the label appears, and at `s0` the (wrong, huge) bbox is up to
   ~1.6 × 10⁹ voxels → marching cubes + smoothing grind until the 30 s timeout.

## 2. Evidence — labels vanish in the pyramid

Global presence scan of `david_all_traces.n5` (local worktree
`.worktrees/add-david-all-traces/data/platybrowser_6dpf/images/local/david_all_traces.n5`):

| level | present / 284 | absent |
|---|---|---|
| s6 | 216 | many (thin traces) |
| s5 | 264 | 142, 277, 159, … |
| s4 | 280 | **94, 142, 159, 277** |
| s3 | 281 | **142, 159, 277** |
| s2 | 281 | **142, 159, 277** |
| s1 / s0 | not found inside the table bbox for 142/277/159 | — |

Normal traces persist across levels (e.g. label 100 present at s2/s3/s4/s5).
142, 277 and 159 exist only at the finest levels — and for 159 not even there
within its bbox ("no voxels" = empty label).

## 3. Duplicate trace and wrong bounding boxes

`default.tsv` has exactly **one pair of labels with an identical bbox**:

```
142, 146  bb = (90.61, 49.94, 81.26) .. (153.16, 158.26, 234.18)
  142: aka 32.004  big-chain extra cell  Nk6.502.nmx  n_nodes=1669
  146: aka 32.2    commissural finished  Nk6.495.nmx  n_nodes=1971
```

Two different nmx files (Nk6.502 / Nk6.495) of the same cell were kept as two
labels. The first-node-fingerprint dedupe did not merge them (different starting
nodes). They occupy the same region, so at coarse levels **max-pool keeps the
higher label (146) and erases 142**.

The shared bbox is also **not the true bbox**: the actual label-146 footprint at
`s3` is `(90.2, 99.2, 80.8) .. (139.5, 158.1, 164.0)` — z_max is 164, not the
234 in the table. The table bbox is inflated (probably a union of node extents
for both traces, or one trace's extent assigned to both). The doc's earlier
"bb x/z swapped" fix did not catch this.

## 4. Why the pyramid erases them

The conversion rasterises each skeleton node as a **radius-2 disk on its
z-plane** (`skimage.draw.circle`), then builds the pyramid with a custom
**2×2×2 max-pool**. Consequences:

- A sparse trace (few nodes spread over a large span — 277 has 109 nodes over
  ~50 µm; 159 has 95 nodes) leaves single-voxel dots that a 2×2×2 block can miss
  entirely → the label disappears after 2–3 downsamplings.
- Where two labels overlap, max-pool keeps only the larger label value → the
  lower one (142) is erased as soon as they collide in a block.
- `MeshCreator` selects a level from the **table bbox** voxel count
  (`maxNumSegmentVoxels = 10⁶`), i.e. a coarse level for these large bboxes —
  exactly where the label is absent. Its loop then steps *down* to finer levels
  (`if (mesh.length == 0) continue;`) with no cap. At `s0` the region is
  ~1.6 × 10⁹ voxels for 142 → hang.

`159` is absent at every level, so the loop exhausts and throws "no voxels" — an
**empty label** produced by the rasterisation (its nodes were presumably all
overwritten, or off-grid).

## 5. Answer to "was the nmx → N5 conversion messed up?"

Partly, yes — three data defects, plus a viewer-side amplifier:

- **Dedup failure**: 142/146 are one cell stored twice (and 12 source files
  produce >1 label — worth auditing).
- **Empty label**: 159 has no voxels.
- **Inaccurate bboxes**: at least 142/146 share an inflated bbox that does not
  match the data.
- **Lossy max-pool pyramid** for thin traces (a design property, not corruption).
- **Viewer amplifier**: `MeshCreator`'s unguarded fallback to `s0` turns those
  into a hang instead of a fast, labelled failure.

## 6. Recommendations

Viewer (already partially applied on branch `example_configs`):
- per-trace mesh-creation timeout + per-trace progress/size logging (done);
- add a deterministic guard: when the label is absent at the auto-selected
  level, cap the fallback by voxel count and throw a clear "region too large"
  instead of marching `s0`.

Data (proper fix):
- deduplicate 142/146 (and audit the 12 multi-label source files);
- recompute `default.tsv` bboxes from the **actual N5 voxels** (verify x/z order);
- repair/drop the empty label 159;
- make the pyramid presence-preserving (or rasterise traces thicker), so every
  label exists at every level — or record per-level presence and use it when
  choosing the mesh level.

QC:
- assert every table label has >0 voxels at `s0` and is present at the coarsest
  level used for meshing.

## 7. Reproduce

```bash
# from platybrowser-project-2025
uv run --python 3.12 --with z5py --with numpy python - <<'PY'
import z5py, numpy as np
p='.worktrees/add-david-all-traces/data/platybrowser_6dpf/images/local/david_all_traces.n5'
f=z5py.File(p,'r'); tp=f['setup0/timepoint0']
for lvl in ['s6','s5','s4','s3','s2']:
    present=set(int(x) for x in np.unique(tp[lvl][:]) if x!=0)
    print(lvl, 'present', len(present), 'absent', sorted(set(range(1,285))-present))
PY
```

Minor unrelated observation: `CustomTriangleMesh.getVolume()` is negative for
every trace (inverted triangle winding) — cosmetic here, worth a separate look.
