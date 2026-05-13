#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "pandas",
#   "numpy",
# ]
# ///

import pandas as pd
import numpy as np
import warnings

# Suppress noisy warnings
warnings.filterwarnings("ignore")

# --- Input Paths (Relative to project root) ---
PATH_MN_DAVID = 'data/platybrowser_6dpf/tables/sbem-6dpf-1-whole-traces-MNs-David-Puga/default.tsv'
PATH_DAVID_CSV = 'david_cells.csv'
PATH_CELLS_TO_NUCL = 'data/platybrowser_6dpf/tables/sbem-6dpf-1-whole-segmented-cells/cells_to_nuclei.tsv'
PATH_BASE_TRACES = 'data/platybrowser_6dpf/tables/sbem-6dpf-1-whole-traces/default.tsv'
PATH_NUCLEI_TABLE = 'data/platybrowser_6dpf/tables/sbem-6dpf-1-whole-segmented-nuclei/default.tsv'

# --- Output Paths (Relative to project root) ---
OUTPUT_MERGED = 'data/platybrowser_6dpf/tables/sbem-6dpf-1-whole-combined-traces/default.tsv'

def main():
    # 1. LOAD DATA
    df_david_raw = pd.read_csv(PATH_MN_DAVID, sep='\t')
    df_david_map = pd.read_csv(PATH_DAVID_CSV)
    df_kevin_raw = pd.read_csv(PATH_BASE_TRACES, sep='\t')
    df_cell_to_nucl = pd.read_csv(PATH_CELLS_TO_NUCL, sep='\t')
    df_nuclei = pd.read_csv(PATH_NUCLEI_TABLE, sep='\t')

    # ---------------------------------------------------------
    # STEP 1: RESOLVE NUCLEUS IDs FOR BOTH DATASETS
    # ---------------------------------------------------------
    
    # Resolve David's Nucleus IDs
    df_david_map['join_id'] = pd.to_numeric(df_david_map['cell_id'], errors='coerce').fillna(0).astype(int)
    d_nucl_lookup = df_david_map.dropna(subset=['join_id']).set_index('join_id')['nucl_table_id']
    
    df_david = df_david_raw.copy()
    df_david['nucleus_id'] = df_david['label_id'].map(d_nucl_lookup).fillna(0).astype(int)
    
    # Track and filter David's missing nuclei
    df_david_dropped = df_david[df_david['nucleus_id'] == 0]
    df_david = df_david[df_david['nucleus_id'] > 0] 
    print(f"INFO: Dropped {len(df_david_dropped)} traces from David's dataset (no valid nucleus_id).")
    if not df_david_dropped.empty:
        sample_ids = df_david_dropped['label_id'].head(5).tolist()
        print(f"      Example dropped label_ids from David: {sample_ids}")

    # Track and filter Kevin's missing nuclei
    df_kevin_dropped = df_kevin_raw[df_kevin_raw['nucleus_id'].isna() | (df_kevin_raw['nucleus_id'] == 0)]
    df_kevin = df_kevin_raw[df_kevin_raw['nucleus_id'] > 0].copy()
    print(f"INFO: Dropped {len(df_kevin_dropped)} traces from Kevin's dataset (no valid nucleus_id).")
    if not df_kevin_dropped.empty:
        sample_ids = df_kevin_dropped['label_id'].head(5).tolist()
        print(f"      Example dropped label_ids from Kevin: {sample_ids}")

    # ---------------------------------------------------------
    # STEP 2: APPLY CONFLICT RULES
    # ---------------------------------------------------------
    
    def clean_trace_group(df, name):
        """
        Rule: If 2 nuclei for 1 trace, keep one + warning.
        Rule: If 2 traces for 1 nucleus, skip.
        """
        # A: Check for 1 trace pointing to multiple nuclei
        trace_to_nucl_counts = df.groupby('label_id')['nucleus_id'].nunique()
        multi_nucl_traces = trace_to_nucl_counts[trace_to_nucl_counts > 1].index
        if not multi_nucl_traces.empty:
            print(f"WARNING: Trace IDs {multi_nucl_traces.tolist()} in {name} match multiple nuclei. Keeping first.")
            df = df.drop_duplicates(subset=['label_id'], keep='first')

        # B: Check for 1 nucleus having multiple traces
        nucl_to_trace_counts = df.groupby('nucleus_id')['label_id'].nunique()
        multi_trace_nucl = nucl_to_trace_counts[nucl_to_trace_counts > 1].index
        if not multi_trace_nucl.empty:
            print(f"SKIP: Nuclei {multi_trace_nucl.tolist()} in {name} have multiple traces. Removing.")
            df = df[~df['nucleus_id'].isin(multi_trace_nucl)]
            
        return df[['nucleus_id', 'label_id', 'bb_min_x', 'bb_min_y', 'bb_min_z', 'bb_max_x', 'bb_max_y', 'bb_max_z']]

    df_kevin_clean = clean_trace_group(df_kevin, "Kevin")
    df_david_clean = clean_trace_group(df_david, "David")

    # ---------------------------------------------------------
    # STEP 3: MERGE INTO NUCLEI TABLE
    # ---------------------------------------------------------
    
    df_kevin_clean = df_kevin_clean.rename(columns={'label_id': 'kevin_head_traces_id'})
    df_david_clean = df_david_clean.rename(columns={'label_id': 'david_motorneuron_2nd_segment_traces_id'})

    # Start with nuclei as base
    df_final = df_nuclei.copy().rename(columns={'label_id': 'nucleus_id'})

    # Merge Kevin and David IDs
    df_final = df_final.merge(df_kevin_clean, on='nucleus_id', how='left', suffixes=('', '_kevin'))
    df_final = df_final.merge(df_david_clean, on='nucleus_id', how='left', suffixes=('', '_david'))

    # Filter out nucleus_id == 0 before checking for duplicates
    df_valid_mappings = df_cell_to_nucl[df_cell_to_nucl['nucleus_id'] > 0].copy()
    
    # Ensure nucleus_id is unique to avoid reindexing errors
    df_cell_to_nucl_unique = df_valid_mappings.drop_duplicates(subset=['nucleus_id'], keep='first')
    
    duplicates_removed = len(df_valid_mappings) - len(df_cell_to_nucl_unique)
    if duplicates_removed > 0:
        print(f"WARNING: Ignored {duplicates_removed} true duplicate valid nucleus->cell mappings in cells_to_nuclei.tsv.")

    cell_map = df_cell_to_nucl_unique.set_index('nucleus_id')['label_id']
    df_final['cell_id'] = df_final['nucleus_id'].map(cell_map).fillna(0).astype(int)

    # ---------------------------------------------------------
    # STEP 4: EXPAND BOUNDING BOXES
    # ---------------------------------------------------------
    for axis in ['x', 'y', 'z']:
        # Minima
        df_final[f'bb_min_{axis}'] = df_final[[f'bb_min_{axis}', f'bb_min_{axis}_kevin', f'bb_min_{axis}_david']].min(axis=1)
        # Maxima
        df_final[f'bb_max_{axis}'] = df_final[[f'bb_max_{axis}', f'bb_max_{axis}_kevin', f'bb_max_{axis}_david']].max(axis=1)

    # ---------------------------------------------------------
    # STEP 5: CLEANUP AND SAVE
    # ---------------------------------------------------------
    # Filter: Keep only nuclei that appeared in either Kevin's or David's traces
    df_final = df_final[df_final['kevin_head_traces_id'].notna() | df_final['david_motorneuron_2nd_segment_traces_id'].notna()].copy()
    
    # Rename nucleus_id back to label_id per request
    df_final = df_final.rename(columns={'nucleus_id': 'label_id'})
    
    # Ensure IDs are integers (NaNs make them floats)
    for col in ['kevin_head_traces_id', 'david_motorneuron_2nd_segment_traces_id']:
        df_final[col] = df_final[col].fillna(0).astype(int)

    # Final column selection strictly in the requested order
    cols_to_keep = [
        'label_id',
        'anchor_x', 'anchor_y', 'anchor_z',
        'bb_min_x', 'bb_min_y', 'bb_min_z',
        'bb_max_x', 'bb_max_y', 'bb_max_z',
        'cell_id',
        'kevin_head_traces_id', 'david_motorneuron_2nd_segment_traces_id'
    ]
    
    df_final = df_final[cols_to_keep]
    
    df_final.to_csv(OUTPUT_MERGED, sep='\t', index=False)
    print(f"Successfully merged {len(df_final)} nuclei-linked traces to {OUTPUT_MERGED}")

if __name__ == "__main__":
    main()