#!/bin/bash

#SBATCH -t 24:00:00
#SBATCH --job-name snakemake_platy
#SBATCH --mem=32G
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --cpus-per-task=8
#SBATCH --output /g/arendt/Cyril/bioinformatics/cluster/snakemake_platy_out.txt
#SBATCH --error /g/arendt/Cyril/bioinformatics/cluster/snakemake_platy_out.txt

module unload
module load Miniforge3/24.1.2-0 snakemake
source <(conda shell.bash hook)
conda activate snakemake_genes

cd /home/cros/bioinformatics/platybrowser-project-2025/analysis/gene_clustering
snakemake -k -j 12 --rerun-incomplete

