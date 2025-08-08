# 2025 preprint of the 6dpf cell type atlas

We are adding a few scripts to help process our outputs.

## Getting cell types from views into a table

**Use case:** Detlev manually saves a view after turning up markers of interest and manually selecting cells.
We end up with a bunch of JSON files, one view each, with the name of cell type. See [this example file](./detlev_handcrafted_views/fg_GABA_SN_Dbx_Ptf1a.json).
We want a merged JSON to be possibly further edited, and a CSV table label to cell type for later.

Use `extract_cell_types.sh` (`chmod +x` may be needed) as in 

    ./extract_cell_types.sh -j fused_views.json -c cell_types.csv detlev_handcrafted_views/*.json

## Reformatting tables

First I need to remove symlinked tables, so I don't affect other datasets. It is also better practice...

    cd ./data/platybrowser_6dpf/tables/
    find . -type l -exec sh -c 'cp --remove-destination -aL "$1" "$1.tmp" && mv "$1.tmp" "$1"' _ {} \;

The tables have a bunch of `1.0` / `2.0` / `3.0` columns due to bad CSV handling.
We replace all the affected columns.

    ./clean_up_integer.py

## Reformatting Prospr

I am changing the displayed names of some views for Prospr using this [look up table as a csv](./prospr.csv). 
The old prospr name is left unchanged.

    ./adapt_prospr_names.py