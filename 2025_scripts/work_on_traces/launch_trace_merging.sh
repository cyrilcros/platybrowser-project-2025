#!/bin/bash

#SBATCH -t 10:00:00
#SBATCH --job-name trace_merge
#SBATCH -N 1
#SBATCH -p bigmem
#SBATCH -C turin
#SBATCH -n 8
#SBATCH --mem 64086
#SBATCH --output /scratch/cros/trace_merging/trace_merge_%j_out.txt
#SBATCH --error /scratch/cros/trace_merging/trace_merge_%j_err.txt

unset XDG_RUNTIME_DIR
module purge
source ~/.bash_profile

# Load required modules
module load mc python uv

# Centralize everything in the scratch directory
export SCRATCH_DIR="/scratch/cros/trace_merging"
cd "$SCRATCH_DIR"

echo "Using scratch directory: $SCRATCH_DIR"

# Setup MinIO client (mc) alias for anonymous EMBL S3 access
mc alias set embl_anon https://s3.embl.de "" "" --api S3v4

# Sync S3 images to the local scratch space
echo "Downloading David's traces..."
mc mirror --quiet embl_anon/platybrowser-2025/demo-v0/sbem-6dpf-1-whole-traces-david.n5 "${SCRATCH_DIR}/sbem-6dpf-1-whole-traces-david.n5"

echo "Downloading Kevin's traces..."
mc mirror --quiet embl_anon/platybrowser/rawdata/sbem-6dpf-1-whole-traces.n5 "${SCRATCH_DIR}/sbem-6dpf-1-whole-traces.n5"

echo "Downloading Nuclei..."
mc mirror --quiet embl_anon/platybrowser/0.0.0/images/local/sbem-6dpf-1-whole-segmented-nuclei.n5 "${SCRATCH_DIR}/sbem-6dpf-1-whole-segmented-nuclei.n5"

echo "Downloads complete. Launching merge script..."

# Run the python script from the current directory
./merge_traces.py