# /// script
# dependencies = [
#   "pandas",
# ]
# ///

import pandas as pd

# --- Input Paths ---
# David Puga's specific MN traces
PATH_MN_DAVID = '/home/cyril/platybrowser-project-2025/data/platybrowser_6dpf/tables/sbem-6dpf-1-whole-traces-MNs-David-Puga/default.tsv'
# The CSV containing nucl_table_id
PATH_DAVID_CSV = '/home/cyril/platybrowser-project-2025/david_cells.csv'
# The mapping table between cells and nuclei
PATH_CELLS_TO_NUCL = '/home/cyril/platybrowser-project-2025/data/platybrowser_6dpf/tables/sbem-6dpf-1-whole-segmented-cells/cells_to_nuclei.tsv'
# The base traces table to merge into
PATH_BASE_TRACES = '/home/cyril/platybrowser-project-2025/data/platybrowser_6dpf/tables/sbem-6dpf-1-whole-traces/default.tsv'

# --- Output Paths ---
OUTPUT_NEW = PATH_MN_DAVID + '.new'
OUTPUT_MERGED = '/home/cyril/platybrowser-project-2025/data/platybrowser_6dpf/tables/sbem-6dpf-1-whole-traces/default.tsv.merged'
OUTPUT_LOG = '/home/cyril/platybrowser-project-2025/label_reassignment_log.csv'

def main():
    # 1. LOAD DATA
    df_david = pd.read_csv(PATH_MN_DAVID, sep='\t')
    df_csv = pd.read_csv(PATH_DAVID_CSV)
    df_map = pd.read_csv(PATH_CELLS_TO_NUCL, sep='\t')
    df_base = pd.read_csv(PATH_BASE_TRACES, sep='\t')

    # ---------------------------------------------------------
    # STEP A: UPDATE NUCLEUS_ID (Using david_cells.csv)
    # ---------------------------------------------------------
    # Convert '1.2' strings/floats to integer '1'
    df_csv['join_id'] = pd.to_numeric(df_csv['cell_id'], errors='coerce').fillna(0).astype(int)
    nucl_lookup = df_csv.dropna(subset=['join_id']).set_index('join_id')['nucl_table_id']
    
    df_david.set_index('label_id', inplace=True)
    # Update only existing indices to avoid future warnings
    df_david.loc[df_david.index.intersection(nucl_lookup.index), 'nucleus_id'] = nucl_lookup
    df_david.reset_index(inplace=True)
    df_david['nucleus_id'] = df_david['nucleus_id'].astype(int)

    # ---------------------------------------------------------
    # STEP B: UPDATE CELL_ID (Using cells_to_nuclei.tsv)
    # ---------------------------------------------------------
    # Create lookup: nucleus_id -> label_id (the cell)
    # If nucleus_id is 0 or missing, cell_id becomes 0
    cell_lookup = df_map[df_map['nucleus_id'] > 0].set_index('nucleus_id')['label_id']
    df_david['cell_id'] = df_david['nucleus_id'].map(cell_lookup).fillna(0).astype(int)

    # Save David's updated table as .new
    df_david.to_csv(OUTPUT_NEW, sep='\t', index=False)
    print(f"Intermediate file saved: {OUTPUT_NEW}")

    # ---------------------------------------------------------
    # STEP C: REASSIGN LABEL_IDS AND MERGE
    # ---------------------------------------------------------
    # Calculate offset
    max_base_id = df_base['label_id'].max()
    
    # Store old IDs for log
    df_david_final = df_david.copy()
    old_labels = df_david_final['label_id'].values
    
    # Reassign: start after the base table's last ID
    df_david_final['label_id'] = df_david_final['label_id'] + max_base_id
    new_labels = df_david_final['label_id'].values

    # Generate reassignment log
    log_df = pd.DataFrame({
        'source_data': 'sbem-6dpf-1-whole-traces-MNs-David-Puga',
        'old_label_id': old_labels,
        'new_label_id': new_labels
    })
    log_df.to_csv(OUTPUT_LOG, index=False)

    # Concatenate with base table
    df_merged = pd.concat([df_base, df_david_final], ignore_index=True)
    df_merged.to_csv(OUTPUT_MERGED, sep='\t', index=False)

    # ---------------------------------------------------------
    # STEP D: DUPLICATE ANALYSIS
    # ---------------------------------------------------------
    def get_dups(df, col):
        # We only care about duplicates of valid IDs (not 0)
        subset = df[df[col] > 0]
        counts = subset[col].value_counts()
        return counts[counts > 1].index.tolist()

    dup_cells = get_dups(df_merged, 'cell_id')
    dup_nuclei = get_dups(df_merged, 'nucleus_id')

    # FINAL REPORT
    print(f"Merge Complete: {OUTPUT_MERGED}")
    print(f"Log Saved: {OUTPUT_LOG}")
    
    if dup_cells:
        print(f"Duplicate Cell IDs found: {dup_cells}")
    else:
        print("No duplicate Cell IDs.")

    if dup_nuclei:
        print(f"Duplicate Nucleus IDs found: {dup_nuclei}")
    else:
        print("No duplicate Nucleus IDs.")

    print(f">\tKevin's data had apparently a cell #266 with nuclei ID 503 / 506.")
    print(f">\tKevin's data had two entries with label_id 722 and 724 for nuclei ID 4034 / cell ID 7711")

if __name__ == "__main__":
    main()