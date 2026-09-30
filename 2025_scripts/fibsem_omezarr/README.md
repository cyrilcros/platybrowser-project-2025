# fibsem → OME-Zarr v3 (for MoBIE)

Convert the backup FIB-SEM volumes under
`s3://platybrowser-n5-generic/platybrowser/bkp/fibsem/` from **BDV HDF5**
(`bdv.hdf5`, `t00000/s00/0/cells`) to **OME-Zarr v3 / NGFF 0.5** so MoBIE can load
them.

Background: these are *separate* FIB-SEM volumes of the **parapod** (10 nm raw,
plus ~10 small segmentations at 0.5 µm / 20 nm / 160×160×200 nm), affinely
registered into the main SBEM coordinate space. They are not part of the main
whole-animal volume and are not referenced by `dataset.json`.

Tooling: [tensorswitch](https://github.com/JaneliaSciComp/tensorswitch) v2 —
its `readers/hdf5.py` reads the BDV HDF5 array and `writers/zarr3.py` writes
NGFF 0.5. (Tensorstore has no HDF5 driver, so it cannot be used directly.)

## Files

| File | Purpose |
|------|---------|
| `manifest.tsv` | one row per volume: name, h5, dataset path, voxel size (z,y,x), unit, kind |
| `convert_fibsem.sh` | download (resumable, anonymous) + `tensorswitch-v2` convert |
| `convert_fibsem.sbatch` | Slurm wrapper (logs under `/scratch/cros/fibsem_omezarr/logs`) |
| `validate_omezarr.py` | structural check of the produced NGFF 0.5 dataset |

## Run (on the EMBL cluster)

```bash
mkdir -p /scratch/cros/fibsem_omezarr/logs
# segmentations first (cheap), then the 42 GB raw
sbatch convert_fibsem.sbatch em-segmented-ganglion-parapod-fib em-segmented-small-cirrus-parapod-fib
```

`convert_fibsem.sh <manifest> <src> <out> [name ...]` — with no names it converts
every row; names select a subset. Downloads land in `<src>`, zarrs in `<out>`
(default `/scratch/cros/fibsem_omezarr/{src,out}`).

Env overrides: `BASE_URL`, `TENSORSWITCH_BIN`, `CHUNK` (default `32,256,256`),
`SHARD` (default `64,512,512`).

## Notes / conventions

- `--auto_multiscale` regenerates the pyramid from `t00000/s00/0/cells` using the
  data type: `labels` → `mode` downsample, `image` → `mean`. Integer label
  pyramids must not be averaged (that would create spurious label ids).
- Axes are `z,y,x` (native BDV order); `--voxel_size` is given `z,y,x` in µm.
- Output name is `<row name>.ome.zarr`; MoBIE would reference it as
  `ome.zarr.s3` (Zarr version is auto-detected from the store).
- The two raw affine variants (`…-affine_g`, `…-affine_cg`) share the same
  `em-raw-parapod-fib.h5`; the affine registration belongs in the MoBIE source
  transform, not in the pixel data, so it is not baked in here.

## Run record (2026-09-30)

Run on the EMBL cluster (`login1`, user `cros`), env
`/g/arendt/Cyril/envs/conda_env/tensorswitch` (Python 3.12, tensorswitch v2).

| Stage | Slurm | Elapsed | Notes |
|-------|-------|---------|-------|
| smoke test (2 tiny vols) | `62527209`(fail), `62527360`(fail), `62527678`(cancelled), `62527788` (ok) | — | fixed spool-dir `HERE` + conda-env activation |
| segmentations (10) | `62527969` | 01:02:10 | MaxRSS 12.8 GB |
| raw 42 GB (1) | `62527970` | 01:09:00 | MaxRSS 11.4 GB; 6-level pyramid |

All 11 outputs validated (`validate_omezarr.py`, NGFF 0.5 OK). Uploaded with
`mc mirror --overwrite --retry` to Minio:

```
s3.embl.de/platybrowser-2025/fibsem/ome-zarr/<name>.ome.zarr
```

Raw verified byte-identical (5239 objects / 41,827,665,917 B, src == dst).
Raw zarr is 39 GB (6 levels); the segmentations are single-level (below the
pyramid min-size threshold) and 46 KiB – 162 MiB.

> Note: the dataset's `bdv.n5.s3` sources were re-pointed to
> `buckets.embl.de/platybrowser-n5-generic` (branch `s3-netapp-sources`), so an
> `ome.zarr.s3` source pointing at Minio would need the old endpoint. Decide the
> final host when wiring these as sources.

