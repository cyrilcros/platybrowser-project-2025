# Shell half-objects (sagittal + coronal) — Design

Date: 2026-09-11
Status: Approved (design); spec pending user review
Branch: `shell_halves` (off `main`)

## Goal

The `shell` source renders as a full closed mask around the animal and blocks
part of the 3D view. Produce **four duplicate half-shell objects** derived from
the existing shell N5 mask, so the user can toggle any one half on to see the
interior while keeping a shell surface. Two cut families, two halves each:

- **Sagittal** cut along the bilateral-symmetry plane `x = y`.
- **Coronal** cut along the orthogonal vertical plane `x = -y`.

Naming uses `left` / `right` / `front` / `back` halves.

## Context / constraints

- `shell` is modelled in `dataset.json` as an **`image`** source (not a
  table-backed segmentation), rendered with `contrastLimits [0, 1]`.
- Physical N5: `platybrowser/rawdata/sbem-6dpf-1-whole-segmented-shell.n5` on
  `https://s3.embl.de` (read-only reference). Locally only the XML metadata
  exists (`data/rawdata/` holds XMLs, no `.n5`; `.gitignore` ignores `*.n5`).
- Shell volume: **uint8**, size `860 810 714` (x, y, z), voxel size
  `0.32 0.32 0.4` µm, pyramid levels `[1,1,1] [2,2,2] [4,4,4] [8,8,8] [16,16,16]`.
- The affine has no translation, so index `(0,0,0)` maps to physical `(0,0,0)`.
  The bilateral-symmetry plane is taken to pass through the origin (`x = y`);
  no offset for now.
- `x` and `y` share the same voxel size (0.32 µm), so `x = y` and `x = -y` are
  true 45° planes in physical space.
- Do **not** modify or delete any existing S3 object. Only new keys under the
  new prefix `images/bdv-n5-s3/shell_halves/` in bucket `platybrowser-2025`.
- `mc` first alias `EmblArendtS3` (`~/.mc/config.json`) is used for both buckets.

## Geometry / masking definition

Masking is done in index space (`x`, `y`, `z` = array indices). For every kept
voxel the value is unchanged; every removed voxel becomes `0`.

| Source name | Plane | Keep | Zero out | Half |
|---|---|---|---|---|
| `shell_sag_left`  | `x = y`  | `x ≥ y`  | `x < y`  | left  |
| `shell_sag_right` | `x = y`  | `x ≤ y`  | `x > y`  | right |
| `shell_cor_front` | `x = -y` | `x ≥ -y` | `x < -y` | front |
| `shell_cor_back`  | `x = -y` | `x ≤ -y` | `x > -y` | back  |

`z` is never constrained. The diagonal voxels (`x = y`, `x = -y`) are kept on
the `≥` side. The `left/right` and `front/back` assignments are a naming
convention only; they can be swapped by renaming if a view looks mirrored.

## Approach (approved: A — local staging → mask → `mc mirror` up)

1. **Branch.** `shell_halves` off `main`.
2. **Verify write access.** Probe `EmblArendtS3/platybrowser-2025` with a tiny
   temporary object (create then delete) before generating anything.
3. **Stage the source.** `mc mirror` the shell N5 from
   `EmblArendtS3/platybrowser/rawdata/sbem-6dpf-1-whole-segmented-shell.n5`
   into `data/rawdata/shell_halves/` (gitignored staging).
4. **Mask + write N5.** A new script `2025_scripts/generate_shell_halves.py`
   reads the level-0 volume (uint8, 860×810×714), applies the four masks, and writes four BDV N5
   volumes to `data/rawdata/shell_halves/`:
   - uint8, chunk `96³`, gzip compression, fill value `0`;
   - full 5-level pyramid `[1,1,1] … [16,16,16]`;
   - group attributes mirrored from the source:
     - `setup0/attributes.json`: `dataType`, `downsamplingFactors`
     - `setup0/timepoint0/attributes.json`: `multiScale`, `resolution`
       `[0.32, 0.32, 0.4]`.
5. **Upload.** `mc mirror --overwrite data/rawdata/shell_halves/ \
   EmblArendtS3/platybrowser-2025/images/bdv-n5-s3/shell_halves/`.
6. **Metadata.**
   - Local XML per source in `data/platybrowser_6dpf/images/local/<name>.xml`,
     `<ImageLoader format="bdv.n5">` with
     `<n5 type="relative">../../../rawdata/shell_halves/<name>.n5</n5>`.
   - S3 XML per source in
     `data/platybrowser_6dpf/images/bdv-n5-s3/shell_halves/<name>.xml`,
     `<ImageLoader format="bdv.n5.s3">` with
     `<Key>images/bdv-n5-s3/shell_halves/<name>.n5</Key>`,
     `<SigningRegion>us-west-2</SigningRegion>`,
     `<ServiceEndpoint>https://s3.embl.de</ServiceEndpoint>`,
     `<BucketName>platybrowser-2025</BucketName>`.
   - Four new `image` sources in `dataset.json`, each with both `bdv.n5` and
     `bdv.n5.s3` imageData, matching the existing `shell` source shape.
   - Four non-exclusive views in `uiSelectionGroup: "sbem"`, each an
     `imageDisplay` on one source with `contrastLimits: [0.0, 1.0]` and
     `name` equal to the source name.
7. **Reduce + validate + commit.** Run `2025_scripts/compress_dataset_json.py`
   (also a pre-commit hook) and `2025_scripts/validate_dataset_json.py`; commit
   on `shell_halves`.

## Deliverables

- `2025_scripts/generate_shell_halves.py` (uv inline deps: `z5py`, `numpy`;
  reuse the N5 attribute-mirroring approach from
  `2025_scripts/generate_nuclei_proba_images.py`).
- Four N5 volumes in S3 under `platybrowser-2025/images/bdv-n5-s3/shell_halves/`.
- Eight XML files (4 local + 4 S3) in the dataset tree.
- Four sources + four views in `data/platybrowser_6dpf/dataset.json`.
- This spec.

## Verification

- **S3 write probe** succeeded (create + delete a tiny object).
- `mc ls` shows all four `.n5` folders with expected object counts and
  non-trivial sizes.
- Read back each `setup0/attributes.json` and
  `setup0/timepoint0/attributes.json` from S3 and confirm `dataType=uint8`,
  `downsamplingFactors`, `multiScale`, `resolution`.
- Spot-check masking: for each output, sample voxel indices and confirm the
  zero/nonzero pattern matches the keep condition (e.g. via a small z5py read).
- Confirm the full shell volume is unchanged on S3 (same key, not rewritten).
- `compress_dataset_json.py` produces no diff beyond the intended additions;
  `validate_dataset_json.py` passes; pre-commit hook passes.
- MoBIE manual load of the four views (user-facing, final gate).

## Non-goals / out of scope

- No change to the original `shell` source or view.
- No offset parameter for the symmetry plane (plane is through the origin).
- No modification/deletion of any existing S3 object.
- No new dataset/version; work stays on the active `platybrowser_6dpf` dataset.

## Risks / open points

- **Plane through origin** is an assumption. If the true midline is offset, the
  cut is `x = y + c` and the script must be re-run with an offset. The
  generator should expose the offset as a parameter (default 0) so this is a
  cheap follow-up.
- **Local staging disk** ~0.5 GB in, ~2.3 GB uncompressed out (smaller with
  gzip). Staging dir is gitignored and can be removed after upload.
- **Downsampling method** for the pyramid must match the original shell's
  (mean-based, anti-aliased) to keep edges consistent; verify visually.
