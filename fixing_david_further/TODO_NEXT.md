# TODO_NEXT — fix David traces (oversized / non-rendering)

Branch: `fixing_david_further`
Status: **viewer-side mitigation DONE; data regeneration TODO.**
Owner: next agent picking up the David-traces fix.

## TL;DR

`david_all_traces` labels **142** and **277** hang MoBIE's 3D meshing; **159** is
empty ("no voxels"). Root cause: the traces are rasterised as a radius-2 disk
**per node** with no connecting lines, so sparse traces have gaps and the 2×2×2
max-pool pyramid erases them by `s2`; `MeshCreator` then fell back toward `s0`
and marched a huge region.

A viewer-side guard was added so this now fails fast instead of hanging:
`mobie-viewer-fiji` branch **`example_configs`** (commits `bb36717c`, `5102b594`).
It does **not** fix the data — the traces still need regenerating to render.

## Read these first

- [`david_traces_oversized_report.md`](david_traces_oversized_report.md) — evidence, provenance, root cause.
- [`david_traces_regen_plan.md`](david_traces_regen_plan.md) — regeneration plan.

## TODO — next actions

1. **Connect consecutive skeleton nodes** during rasterisation in
   `~/transfer_check/nmx2n5/convert_all_david_traces.py` (cluster copy
   `/scratch/cros/phase1/`) — currently only a disk per node is stamped.
2. **Deduplicate** 142/146 (same cell, aka 32.004 / 32.2; identical inflated
   bbox). Audit the 12 source files that produce >1 label
   (`commissural_all_comm_sec_seg*.nmx`, `p0v0_all.nmx`, `sim_hox4.015.nmx`,
   `Pyg_git_pyg.005.nmx`, …).
3. **Recompute `default.tsv` bounding boxes from the actual `s0` voxels**
   (`x, y, z` µm), not from node extents.
4. **Repair or drop empty label 159** (source `Nk6_all/Nk6.285.nmx`).
5. **Presence-preserving pyramid + validation gate**: every label present at
   `s1..s7`, `>0` voxels at `s0`, bbox matches, then mesh-test all traces.
6. **Re-upload** the N5 to `EmblArendtS3/platybrowser-2025/demo-v0/`, update the
   XMLs, and regenerate derived sources / views if labels change
   (`david_all_traces_nuclei`, `combined_all_traces_nuclei`, `traces`,
   `additional_traces`).
7. **Re-run** `examples.OpenDavidTraces` (mobie-viewer-fiji @ `example_configs`)
   and confirm `0` timeouts / failures.

## Key facts

- N5: `/g/arendt/David_Puga_Consolidated_data/processed/n5/david_all_traces.n5`
- grid `(z,y,x) = (2854, 3240, 3438)`, voxel `0.08/0.08/0.1` µm, levels `s0..s7`,
  `int16`, custom 2×2×2 max-pool.
- inputs: `/g/arendt/David_Puga_Consolidated_data/processed/traces/` (2,025 readable nmx)
- handoff: `/g/arendt/David_Puga_Consolidated_data/processed/n5/HANDOFF_david_traces_n5.md`
- local N5 mirror: `.worktrees/add-david-all-traces/data/platybrowser_6dpf/images/local/david_all_traces.n5`
- tables: `data/platybrowser_6dpf/tables/david_all_traces/{default,origin_mapping}.tsv`

## Reproduce the diagnosis

```bash
# from platybrowser-project-2025
uv run --python 3.12 --with z5py --with numpy python - <<'PY'
import z5py, numpy as np
p='.worktrees/add-david-all-traces/data/platybrowser_6dpf/images/local/david_all_traces.n5'
f=z5py.File(p,'r'); tp=f['setup0/timepoint0']
for lvl in ['s4','s3','s2']:
    present=set(int(x) for x in np.unique(tp[lvl][:]) if x!=0)
    print(lvl, 'absent', sorted(set(range(1,285))-present))
PY
# s4 -> [94, 142, 159, 277];  s3/s2 -> [142, 159, 277]
```
