#!/bin/bash
#SBATCH -t 24:00:00
#SBATCH --job-name fibsem_omezarr
#SBATCH --mem=64G
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --cpus-per-task=16
#SBATCH --output /scratch/cros/fibsem_omezarr/logs/convert_%j.out
#SBATCH --error  /scratch/cros/fibsem_omezarr/logs/convert_%j.err
# PRE-REQ: mkdir -p /scratch/cros/fibsem_omezarr/logs before sbatch
#
# Usage (from the directory holding this file):
#   sbatch convert_fibsem.sbatch                       # all volumes
#   sbatch convert_fibsem.sbatch em-raw-parapod-fib    # one volume
set -euo pipefail

# Under Slurm the script runs from /var/spool, so use the submit dir.
HERE=${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}
SRC=${SRC:-/scratch/cros/fibsem_omezarr/src}
OUT=${OUT:-/scratch/cros/fibsem_omezarr/out}

"$HERE/convert_fibsem.sh" "$HERE/manifest.tsv" "$SRC" "$OUT" "$@"
