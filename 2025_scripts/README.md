# 2025 preprint of the 6dpf cell type atlas

We are adding a few scripts to help process our outputs.

## Getting cell types from views into a table

**Use case:** Detlev manually saves a view after turning up markers of interest and manually selecting cells.
We end up with a bunch of JSON files, one view each, with the name of cell type. See [this example file](./detlev_handcrafted_views/fg_GABA_SN_Dbx_Ptf1a.json).
We want a merged JSON to be possibly further edited, and a CSV table label to cell type for later.

Use `extract_cell_types.sh` (`chmod +x` may be needed) as in 

    ./extract_cell_types.sh -j fused_views.json -c cell_types.csv detlev_handcrafted_views/*.json

## Reformatting tables

The tables have a bunch of `1.0` / `2.0` / `3.0` columns due to bad CSV handling.
We replace all the affected columns.

    ./clean_up_integer.py