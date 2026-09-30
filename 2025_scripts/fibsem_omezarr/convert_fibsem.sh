#!/bin/bash
# Convert platybrowser/bkp/fibsem BDV HDF5 volumes to OME-Zarr v3 (NGFF 0.5).
#
# Usage:
#   convert_fibsem.sh <manifest.tsv> <src-dir> <out-dir> [volume-name ...]
#
# For each row: download the .h5 from the NetApp bucket (anonymous, resumable)
# if missing, then run tensorswitch-v2 with --auto_multiscale.
#
# Env overrides:
#   BASE_URL          source prefix (default the bkp/fibsem prefix)
#   TENSORSWITCH_ENV  conda env with tensorswitch (default on the cluster)
#   CHUNK / SHARD     zarr inner chunk / shard shapes (default 32,256,256 / 64,512,512)
set -euo pipefail

MANIFEST=${1:?usage: convert_fibsem.sh <manifest.tsv> <src-dir> <out-dir> [name ...]}
SRC=${2:?src dir}
OUT=${3:?out dir}
shift 3 || true
ONLY="$*"

BASE_URL=${BASE_URL:-https://buckets.embl.de/platybrowser-n5-generic/platybrowser/bkp/fibsem}
TS_BIN=${TENSORSWITCH_BIN:-/g/arendt/Cyril/envs/conda_env/tensorswitch/bin/tensorswitch-v2}
CHUNK=${CHUNK:-32,256,256}
SHARD=${SHARD:-64,512,512}

[ -x "$TS_BIN" ] || { echo "tensorswitch binary not found: $TS_BIN" >&2; exit 1; }

mkdir -p "$SRC" "$OUT"

run_one() {
  local name=$1 h5=$2 dsp=$3 vz=$4 vy=$5 vx=$6 unit=$7 kind=$8
  local h5p="$SRC/$h5" out="$OUT/$name.ome.zarr"

  if [ ! -s "$h5p" ]; then
    echo "[$(date +%T)] download $h5"
    curl -fL -C - --retry 5 --retry-delay 5 -o "$h5p" "$BASE_URL/$h5"
  fi

  if [ -s "$out/zarr.json" ]; then
    echo "[$(date +%T)] skip $name (already converted)"
    return 0
  fi

  local dtype dmethod
  if [ "$kind" = labels ]; then dtype=labels; dmethod=mode; else dtype=image; dmethod=mean; fi

  echo "[$(date +%T)] convert $name -> $out ($kind, voxel $vz,$vy,$vx $unit)"
  "$TS_BIN" \
    -i "$h5p" -o "$out" \
    --dataset_path "$dsp" --output_format zarr3 \
    --data-type "$dtype" --downsample_method "$dmethod" \
    --auto_multiscale --compression zstd --compression_level 5 \
    --chunk_shape "$CHUNK" --shard_shape "$SHARD" \
    --voxel_size "$vz,$vy,$vx" --voxel_unit "$unit" --no_tmp
}

tail -n +2 "$MANIFEST" | while IFS=$'\t' read -r name h5 dsp vz vy vx unit kind; do
  [ -n "${name:-}" ] || continue
  if [ -n "$ONLY" ]; then
    case " $ONLY " in *" $name "*) ;; *) continue ;; esac
  fi
  run_one "$name" "$h5" "$dsp" "$vz" "$vy" "$vx" "$unit" "$kind"
done

echo "[$(date +%T)] done"
