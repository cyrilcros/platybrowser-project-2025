#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "zarr",
#   "fsspec",
#   "pandas",
#   "s3fs" 
# ]
# ///

import zarr
import warnings
import pandas as pd
import io
from functools import cache

# Suppress noisy warnings from fsspec about HTTP headers
warnings.filterwarnings("ignore")

# Note the URL change: s3://bucket-name/path
n5_paths = {
    "kevin_traces": "s3://platybrowser/rawdata/sbem-6dpf-1-whole-traces.n5",
    "david_traces": "s3://platybrowser-2025/demo-v0/sbem-6dpf-1-whole-traces-david.n5",
    "nuclei": "s3://platybrowser/0.0.0/images/local/sbem-6dpf-1-whole-segmented-nuclei.n5"
}

# Explicitly configure anonymous access and the custom MinIO endpoint
s3_storage_options = {
    'anon': True,
    'client_kwargs': {
        'endpoint_url': 'https://s3.embl.de'
    }
}

def analyze_n5_datasets(paths):
    for name, url in paths.items():
        print(f"{'='*50}")
        print(f"Inspecting: {name}")
        print(f"{'='*50}")
        
        try:
            # Pass the storage options into N5FSStore
            store = zarr.N5FSStore(url, **s3_storage_options)
            group = zarr.open_group(store=store, mode='r')
            
            print("Root Attributes:")
            attributes = dict(group.attrs)
            if not attributes:
                print("   (No root attributes found)")
            for key, val in attributes.items():
                print(f"   - {key}: {val}")
            
            print("\nDataset Structure (Arrays and Dimensions):")
            print(group.tree())
            
        except Exception as e:
            print(f"Error processing {name}: {e}")
            
        print("\n")

if __name__ == "__main__":
    analyze_n5_datasets(n5_paths)