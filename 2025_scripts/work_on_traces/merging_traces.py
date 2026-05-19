#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "zarr",
#   "fsspec",
#   "pandas",
#   "dask",
#   "numpy"
# ]
# ///

import zarr
import dask.array as da
import numpy as np
import pandas as pd
import warnings
import os
from functools import cache

warnings.filterwarnings("ignore")

# --- Configuration ---
SCRATCH_DIR = os.environ.get("SCRATCH_DIR", "/scratch/cros/trace_merging")

# Make sure this points to wherever your TSV actually lives!
# If it is not copied to the scratch dir, use the absolute path:
# PATH_TSV = '/g/arendt/Cyril/bioinformatics/cluster/data/platybrowser_6dpf/tables/sbem-6dpf-1-whole-combined-traces/default.tsv'
PATH_TSV = 'data/platybrowser_6dpf/tables/sbem-6dpf-1-whole-combined-traces/default.tsv'

OUTPUT_ZARR = os.path.join(SCRATCH_DIR, 'sbem-6dpf-1-whole-combined-segmentation.zarr')
VALIDATE_MISSING_PIXELS = True 

n5_paths = {
    "kevin_traces": os.path.join(SCRATCH_DIR, "sbem-6dpf-1-whole-traces.n5"),
    "david_traces": os.path.join(SCRATCH_DIR, "sbem-6dpf-1-whole-traces-david.n5"),
    "nuclei": os.path.join(SCRATCH_DIR, "sbem-6dpf-1-whole-segmented-nuclei.n5")
}

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

    # 2. VALIDATE MISSING PIXELS 
    if VALIDATE_MISSING_PIXELS:
        check_missing_pixels(kevin_df['kevin_head_traces_id'].values, kevin_raw, "Kevin's")
        check_missing_pixels(david_df['david_motorneuron_2nd_segment_traces_id'].values, david_raw, "David's")

    # 3. BUILD FAST LOOKUP TABLES (LUTs)
    print("Building Look-Up Tables...")
    
    max_nuclei_id = df['label_id'].max()
    nuclei_series = pd.Series(df['label_id'].values, index=df['label_id'].values)
    lut_nuclei = create_lut(nuclei_series, max_nuclei_id)
    
    max_kevin_id = kevin_df['kevin_head_traces_id'].max() if not kevin_df.empty else 0
    lut_kevin = create_lut(kevin_df.set_index('kevin_head_traces_id')['label_id'], max_kevin_id)

    max_david_id = david_df['david_motorneuron_2nd_segment_traces_id'].max() if not david_df.empty else 0
    lut_david = create_lut(david_df.set_index('david_motorneuron_2nd_segment_traces_id')['label_id'], max_david_id)

    # 4. MAP AND MERGE LAYERS
    print("Mapping IDs across blocks lazily...")
    nuclei_mapped = nuclei_raw.map_blocks(apply_lut_to_chunk, lut=lut_nuclei, dtype=np.uint32)
    kevin_mapped = kevin_raw.map_blocks(apply_lut_to_chunk, lut=lut_kevin, dtype=np.uint32)
    david_mapped = david_raw.map_blocks(apply_lut_to_chunk, lut=lut_david, dtype=np.uint32)

    print("Stacking layers...")
    combined_traces = da.where(david_mapped > 0, david_mapped, kevin_mapped)
    final_volume = da.where(combined_traces > 0, combined_traces, nuclei_mapped)

    # 5. WRITE OUTPUT TO SCRATCH
    print(f"Executing computation and writing to {OUTPUT_ZARR}...")
    
    final_volume = final_volume.rechunk((128, 128, 128))
    compressor = zarr.Blosc(cname='zstd', clevel=3, shuffle=zarr.Blosc.SHUFFLE)
    
    final_volume.to_zarr(
        OUTPUT_ZARR, 
        component='setup0/timepoint0/s0', 
        overwrite=True, 
        dimension_separator='/',
        compressor=compressor
    )
    
    print("Done! The s0 full-resolution volume is saved to the scratch directory.")

if __name__ == "__main__":
    main()