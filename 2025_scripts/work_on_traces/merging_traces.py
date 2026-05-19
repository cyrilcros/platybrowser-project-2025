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
import time
from datetime import datetime
from functools import cache

warnings.filterwarnings("ignore")

# --- Configuration ---
SCRATCH_DIR = os.environ.get("SCRATCH_DIR", "/scratch/cros/trace_merging")
PATH_TSV = os.path.join(SCRATCH_DIR, 'default.tsv')

OUTPUT_N5 = os.path.join(SCRATCH_DIR, 'sbem-6dpf-1-whole-combined-segmentation.n5')

VALIDATE_MISSING_PIXELS = False 

n5_paths = {
    "kevin_traces": os.path.join(SCRATCH_DIR, "sbem-6dpf-1-whole-traces.n5"),
    "david_traces": os.path.join(SCRATCH_DIR, "sbem-6dpf-1-whole-traces-david.n5"),
    "nuclei": os.path.join(SCRATCH_DIR, "sbem-6dpf-1-whole-segmented-nuclei.n5")
}

# --- Custom SLURM Progress Bar with Time ---
class SlurmProgress(Callback):
    def __init__(self, step_name):
        self.step_name = step_name
        self.last_percent = -1
        self.start_time = time.time()

    def _posttask(self, key, result, dsk, state, worker_id):
        finished = len(state.get('finished', []))
        total = sum(len(v) for v in state.values())
        if total > 0:
            percent = int(100 * finished / total)
            if percent % 2 == 0 and percent > self.last_percent:
                elapsed = int(time.time() - self.start_time)
                h, rem = divmod(elapsed, 3600)
                m, s = divmod(rem, 60)
                clock = datetime.now().strftime('%H:%M:%S')
                print(f"[{clock}] [{self.step_name}] Progress: {percent}% ({finished}/{total} chunks) | Elapsed: {h:02d}:{m:02d}:{s:02d}", flush=True)
                self.last_percent = percent

@cache
def get_s0_array(path):
    store = zarr.N5FSStore(path)
    return da.from_zarr(store, component='setup0/timepoint0/s0')

def create_lut(mapping_series, max_input_id):
    lut = np.zeros(int(max_input_id) + 1, dtype=np.int32)
    for old_id, new_id in mapping_series.items():
        if old_id > 0 and new_id > 0:
            lut[int(old_id)] = int(new_id)
    return lut

def apply_lut_to_chunk(chunk, lut):
    chunk_int = chunk.astype(int)
    valid_mask = (chunk_int > 0) & (chunk_int < len(lut))
    result = np.zeros(chunk.shape, dtype=np.int16)
    result[valid_mask] = lut[chunk_int[valid_mask]]
    return result

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loading mapping table from {PATH_TSV}...\n")
    df = pd.read_csv(PATH_TSV, sep='\t')
    kevin_df = df[df['kevin_head_traces_id'] > 0]
    # david_df = df[df['david_motorneuron_2nd_segment_traces_id'] > 0] # Skipped David's

    # 1. LOAD RAW ARRAYS
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Connecting to local N5 arrays...")
    nuclei_raw = get_s0_array(n5_paths['nuclei'])
    kevin_raw = get_s0_array(n5_paths['kevin_traces'])
    # david_raw = get_s0_array(n5_paths['david_traces']) # Skipped David's

    # 3. BUILD FAST LOOKUP TABLES
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Building Look-Up Tables...")
    max_nuclei_id = df['label_id'].max()
    lut_nuclei = create_lut(pd.Series(df['label_id'].values, index=df['label_id'].values), max_nuclei_id)
    
    max_kevin_id = kevin_df['kevin_head_traces_id'].max() if not kevin_df.empty else 0
    lut_kevin = create_lut(kevin_df.set_index('kevin_head_traces_id')['label_id'], max_kevin_id)

    # 4. PREPARE OUTPUT STORE & COPY METADATA
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Preparing output N5 structure at {OUTPUT_N5}...")
    out_store = zarr.N5FSStore(OUTPUT_N5)
    out_root = zarr.group(store=out_store, overwrite=True)

    temp_store = zarr.N5FSStore(n5_paths['nuclei'])
    temp_root = zarr.open(temp_store, mode='r')

    # Copy BDV/MoBIE Metadata for the hierarchy
    for path in ['', 'setup0', 'setup0/timepoint0']:
        src_group = zarr.open(temp_store, path=path, mode='r')
        dst_group = out_root.require_group(path)
        dst_group.attrs.update(src_group.attrs.asdict())

    # 5. MAP AND MERGE LAYERS (s0)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Mapping IDs across blocks lazily...")
    nuclei_mapped = nuclei_raw.map_blocks(apply_lut_to_chunk, lut=lut_nuclei, dtype=np.int16)
    kevin_mapped = kevin_raw.map_blocks(apply_lut_to_chunk, lut=lut_kevin, dtype=np.int16)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Stacking layers...")
    combined_traces = kevin_mapped # David's removed
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
        dtype=np.int16,
        compressor=zarr.GZip(level=5),
        fill_value=0,
        overwrite=True
    )

    print(f"\n--- [{datetime.now().strftime('%H:%M:%S')}] Computing Base Resolution (s0) ---")
    with SlurmProgress("s0 Merging"):
        da.store(final_volume, out_s0)
    
    # Copy array-level attributes (resolution, etc.)
    out_s0.attrs.update(temp_s0.attrs.asdict())
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully wrote s0.\n")

    # 6. GENERATE PYRAMID (s1 ... sn)
    computed_s0 = da.from_zarr(out_store, component='setup0/timepoint0/s0')

    scales = sorted([k for k in temp_root['setup0/timepoint0'].keys() if k.startswith('s') and k != 's0'])
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Found scales to generate: {scales}")
    
    for scale in scales:
        print(f"--- [{datetime.now().strftime('%H:%M:%S')}] Computing Pyramid Scale ({scale}) ---")
        temp_sk = temp_root[f'setup0/timepoint0/{scale}']
        t_shape = temp_sk.shape
        t_chunks = temp_sk.chunks

        step_z = max(1, round(temp_s0.shape[0] / t_shape[0]))
        step_y = max(1, round(temp_s0.shape[1] / t_shape[1]))
        step_x = max(1, round(temp_s0.shape[2] / t_shape[2]))

        sampled = computed_s0[::step_z, ::step_y, ::step_x]
        sampled = sampled[:t_shape[0], :t_shape[1], :t_shape[2]]
        sampled = sampled.rechunk(t_chunks)

        out_sk = zarr.create(
            store=out_store,
            path=f'setup0/timepoint0/{scale}',
            shape=t_shape,
            chunks=t_chunks,
            dtype=np.int16,
            compressor=zarr.GZip(level=5),
            fill_value=0,
            overwrite=True
        )

        with SlurmProgress(f"{scale} Downsampling"):
            da.store(sampled, out_sk)

        out_sk.attrs.update(temp_sk.attrs.asdict())
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully wrote {scale}.\n")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Pipeline complete! Full N5 pyramid generated.")

if __name__ == "__main__":
    main()