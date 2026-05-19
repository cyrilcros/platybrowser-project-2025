#!/bin/bash

# Define the central scratch directory on the cluster
REMOTE_DIR="/scratch/cros/trace_merging"

echo "1. Creating remote directory..."
ssh cluster "mkdir -p $REMOTE_DIR"

echo "2. Transferring scripts to the cluster scratch space..."
scp merge_traces.py launch_trace_merging.sh cluster:$REMOTE_DIR/

echo "3. Submitting the job to SLURM..."
ssh cluster "cd $REMOTE_DIR && chmod +x merge_traces.py && sbatch launch_trace_merging.sh"

echo "Deployment complete!"