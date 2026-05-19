#!/usr/bin/env -S uv run
# /// script
# requires-python = "==3.11.*"
# dependencies = [
#   "zarr<3",
#   "fsspec",
#   "pandas",
#   "dask",
#   "numpy"
# ]
# ///

import zarr
import dask.array as da
from dask.callbacks import Callback
import numpy as np
import pandas as pd
import warnings
import os
from functools import cache

warnings.filterwarnings("ignore")

# --- Configuration ---
SCRATCH_DIR = os.environ.get("SCRATCH_DIR", "/scratch/cros/trace_merging")
PATH_TSV = os.path.join(SCRATCH_DIR, 'default.tsv')

# We now output directly to a final N5 folder
OUTPUT_N5 = os.path.join(SCRATCH_DIR, 'sbem-6dpf-1-whole-combined-segmentation.n5')

VALIDATE_MISSING_PIXELS = True 

n5_paths = {
    "kevin_traces": os.path.join(SCRATCH_DIR, "sbem-6dpf-1-whole-traces.n5"),
    "david_traces": os.path.join(SCRATCH_DIR, "sbem-6dpf-1-whole-traces-david.n5"),
    "nuclei": os.path.join(SCRATCH_DIR, "sbem-6dpf-1-whole-segmented-nuclei.n5")
}

# --- Custom SLURM Progress Bar ---
class SlurmProgress(Callback):
    """Prints progress cleanly to SLURM logs every 2% to avoid carriage-return spam."""
    def __init__(self, step_name):
        self.step_name = step_name
        self.last_percent = -1

    def _posttask(self, key, result, dsk, state, worker_id):
        finished = len(state.get('finished', []))
        total = sum(len(v) for v in state.values())
        if total > 0:
            percent = int(100 * finished / total)
            if percent % 2 == 0 and percent > self.last_percent:
                print(f"[{self.step_name}] Progress: {percent}% ({finished}/{total} chunks)", flush=True)
                self.last_percent = percent


@cache
def get_s0_array(path):
    store = zarr.N5FSStore(path)
    return da.from_zarr(store, component='setup0/timepoint0/s0')

def create_lut(mapping_series, max_input_id):
    lut = np.zeros(int(max_input_id) + 1, dtype=np.uint32)
    for old_id, new_id in mapping_series.items():
        if old_id > 0 and new_id > 0:
            lut[int(old_id)] = int(new_id)
    return lut

def apply_lut_to_chunk(chunk, lut):
    chunk_int = chunk.astype(int)
    valid_mask = (chunk_int > 0) & (chunk_int < len(lut))
    result = np.zeros(chunk.shape, dtype=np.uint32)
    result[valid_mask] = lut[chunk_int[valid_mask]]
    return result

def check_missing_pixels(expected_ids, dask_array, name):
    print(f"Scanning {name} raw data to validate pixel existence...")
    actual_ids = set(da.unique(dask_array).compute())
    actual_ids.discard(0)
    expected_ids_set = set(expected_ids[expected_ids > 0])
    missing_ids = expected_ids_set - actual_ids
    if missing_ids:
        print(f"  -> WARNING: {len(missing_ids)} Trace IDs listed in the TSV were NOT found in the {name} image data!")
        print(f"  -> Example missing IDs: {list(missing_ids)[:10]}\n")
    else:
        print(f"  -> SUCCESS: All {len(expected_ids_set)} expected {name} Trace IDs exist in the image data.\n")

def main():
    print(f"Loading mapping table from {PATH_TSV}...\n")
    df = pd.read_csv(PATH_TSV, sep='\t')
    kevin_df = df[df['kevin_head_traces_id'] > 0]
    david_df = df[df['david_motorneuron_2nd_segment_traces_id'] > 0]

    # 1. LOAD RAW ARRAYS
    print("Connecting to local N5 arrays...")
    nuclei_raw = get_s0_array(n5_paths['nuclei'])
    kevin_raw = get_s0_array(n5_paths['kevin_traces'])
    david_raw = get_s0_array(n5_paths['david_traces'])

    if VALIDATE_MISSING_PIXELS:
        check_missing_pixels(kevin_df['kevin_head_traces_id'].values, kevin_raw, "Kevin's")
        check_missing_pixels(david_df['david_motorneuron_2nd_segment_traces_id'].values, david_raw, "David's")

    # 2. BUILD FAST LOOKUP TABLES
    print("Building Look-Up Tables...")
    max_nuclei_id = df['label_id'].max()
    lut_nuclei = create_lut(pd.Series(df['label_id'].values, index=df['label_id'].values), max_nuclei_id)
    
    max_kevin_id = kevin_df['kevin_head_traces_id'].max() if not kevin_df.empty else 0
    lut_kevin = create_lut(kevin_df.set_index('kevin_head_traces_id')['label_id'], max_kevin_id)

    max_david_id = david_df['david_motorneuron_2nd_segment_traces_id'].max() if not david_df.empty else 0
    lut_david = create_lut(david_df.set_index('david_motorneuron_2nd_segment_traces_id')['label_id'], max_david_id)

    # 3. PREPARE OUTPUT STORE & COPY METADATA
    print(f"Preparing output N5 structure at {OUTPUT_N5}...")
    out_store = zarr.N5FSStore(OUTPUT_N5)
    out_root = zarr.group(store=out_store, overwrite=True)

    temp_store = zarr.N5FSStore(n5_paths['nuclei'])
    temp_root = zarr.open(temp_store, mode='r')

    # Copy BDV/MoBIE Metadata for the hierarchy
    for path in ['', 'setup0', 'setup0/timepoint0']:
        src_group = zarr.open(temp_store, path=path, mode='r')
        dst_group = out_root.require_group(path)
        dst_group.attrs.update(src_group.attrs.asdict())

    # 4. MAP AND MERGE LAYERS (s0)
    print("Mapping IDs across blocks lazily...")
    nuclei_mapped = nuclei_raw.map_blocks(apply_lut_to_chunk, lut=lut_nuclei, dtype=np.uint32)
    kevin_mapped = kevin_raw.map_blocks(apply_lut_to_chunk, lut=lut_kevin, dtype=np.uint32)
    david_mapped = david_raw.map_blocks(apply_lut_to_chunk, lut=lut_david, dtype=np.uint32)

    print("Stacking layers...")
    combined_traces = da.where(david_mapped > 0, david_mapped, kevin_mapped)
    final_volume = da.where(combined_traces > 0, combined_traces, nuclei_mapped)

    # Rechunk to perfectly match the nuclei template
    temp_s0 = temp_root['setup0/timepoint0/s0']
    final_volume = final_volume.rechunk(temp_s0.chunks)

    # Initialize s0 in the output store
    out_s0 = zarr.create(
        store=out_store,
        path='setup0/timepoint0/s0',
        shape=temp_s0.shape,
        chunks=temp_s0.chunks,
        dtype=np.uint32,
        compressor=zarr.GZip(level=6),
        fill_value=0,
        overwrite=True
    )

    print("\n--- Computing Base Resolution (s0) ---")
    with SlurmProgress("s0 Merging"):
        da.store(final_volume, out_s0)
    
    # Copy array-level attributes (resolution, etc.)
    out_s0.attrs.update(temp_s0.attrs.asdict())
    print("Successfully wrote s0.\n")

    # 5. GENERATE PYRAMID (s1 ... sn)
    # Re-read the computed s0 from disk so we don't recompute the LUT mapping!
    computed_s0 = da.from_zarr(out_store, component='setup0/timepoint0/s0')

    # Find all downsampled scales in the template
    scales = sorted([k for k in temp_root['setup0/timepoint0'].group_keys() if k.startswith('s') and k != 's0'])
    
    for scale in scales:
        print(f"--- Computing Pyramid Scale ({scale}) ---")
        temp_sk = temp_root[f'setup0/timepoint0/{scale}']
        t_shape = temp_sk.shape
        t_chunks = temp_sk.chunks

        # Calculate exact downsampling stride relative to s0
        step_z = max(1, round(temp_s0.shape[0] / t_shape[0]))
        step_y = max(1, round(temp_s0.shape[1] / t_shape[1]))
        step_x = max(1, round(temp_s0.shape[2] / t_shape[2]))

        # Nearest-neighbor downsampling
        sampled = computed_s0[::step_z, ::step_y, ::step_x]
        
        # Crop safely and rechunk to match template
        sampled = sampled[:t_shape[0], :t_shape[1], :t_shape[2]]
        sampled = sampled.rechunk(t_chunks)

        out_sk = zarr.create(
            store=out_store,
            path=f'setup0/timepoint0/{scale}',
            shape=t_shape,
            chunks=t_chunks,
            dtype=np.uint32,
            compressor=zarr.GZip(level=6),
            fill_value=0,
            overwrite=True
        )

        with SlurmProgress(f"{scale} Downsampling"):
            da.store(sampled, out_sk)

        out_sk.attrs.update(temp_sk.attrs.asdict())
        print(f"Successfully wrote {scale}.\n")

    print("Pipeline complete! Full N5 pyramid generated.")

if __name__ == "__main__":
    main()