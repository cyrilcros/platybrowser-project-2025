# 2025 preprint of the 6dpf cell type atlas

We are adding a few scripts to help process our outputs. I also am reformatting Platybrowser legacy code. I am using BASH Shell or Python.
You should only need `uv` (`module load uv`  works at EMBL), and dependencies will be installed via [inline-script metadata](Inline script metadata).

## Reformatting tables

First I need to remove symlinked tables, so I don't affect other datasets. It is also better practice...

    cd ./data/platybrowser_6dpf/tables/
    find . -type l -exec sh -c 'cp --remove-destination -aL "$1" "$1.tmp" && mv "$1.tmp" "$1"' _ {} \;

The tables have a bunch of `1.0` / `2.0` / `3.0` columns due to bad CSV handling.
We replace all the affected columns.

    ./clean_up_integer.py

## Adding up what Alyona has registered so far

We assume we have valid views in a local folder like `data-tmp`.
For now I am symlinking (randomly...) representative images from Alyona's repo to this `data-tmp` and running this on it. The actual path for what Alyona registered is `/g/cba/exchange/buglakova/platybrowser-smfish-project/data/1.0.1/images/bdv-n5`.

We want to:

1. convert from `bdv-n5` to `bdv-n5-s3`
2. upload to a S3 bucket
3. add `bdv-n5-s3` as sources using a naming scheme from [`2025_staining_naming.csv`](./2025_staining_naming.csv)
4. use the naming scheme to create corresponding views

### From local bdv.n5 XML to bdv.n5.s3 XML and a populated S3 bucket

Let's say we we have a bunch of n5 files and XML folders with identical names as part of `data/platybrowser_6dpf/images/bdv-n5`. I want to populate 
`data/platybrowser_6dpf/images/bdv-n5-s3` by uploading to S3 and converting my XML stanza to `<ImageLoader format="bdv.n5.s3">`
with the right bucket. At this point I am not yet touching `data/platybrowser_6dpf/dataset.json`. I am also assuming the resolution, scale factor, trnasofrmation, unit, etc... are correct, I am just adjusting from a working local version to a remote one.

You need to use the `.env` file (cf copy from and fill `.env.example`) for S3 access.

    ./upload_Alyona_local_n5_to_s3.py -i ../data-tmp/ -o ../data/platybrowser_6dpf/images/bdv-n5-s3/paper_2025 \
    -e "https://s3.embl.de" -r "us-west-2"  -b "platybrowser-2025" -p "demo-v0" --dry-run

Remove the `--dry-run`  to upload. Files are sequentially uploaded which is slow but acceptable.

### From bdv.n5.s3 XML files to new sources and view in dataset.json

We are altering the `dataset.json`

    ./add_sources_and_views_to_n5_s3_data.py ../data/platybrowser_6dpf/dataset.json \ ../data/platybrowser_6dpf/images/bdv-n5-s3/paper_2025 2025_staining_naming.csv stainings-2025-paper

## Getting cell types from views into a table

**Use case:** Detlev manually saves a view after turning up markers of interest and manually selecting cells.
We end up with a bunch of JSON files, one view each, with the name of cell type. See [this example file](./detlev_handcrafted_views/fg_GABA_SN_Dbx_Ptf1a.json).
We want a merged JSON to be possibly further edited, and a CSV table label to cell type for later.

Use `extract_cell_types.sh` (`chmod +x` may be needed) as in 

    ./extract_cell_types.sh -j fused_views.json -t ../data/platybrowser_6dpf/tables/sbem-6dpf-1-whole-segmented-cells/cell-types-manual-curation.tsv detlev_handcrafted_views/*.json
