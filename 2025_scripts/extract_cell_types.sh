#!/bin/bash

# This script take a bunch of manually saved Platybrowser JSON views
# It merges them and returns a JSON, and extracts labelled cells into a CSV table.

set -e

################ Parsing

JSON_OUT=""
CSV_OUT=""
INPUT_FILES=()

usage() {
    echo "Usage: $0 -j <json_file> -c <csv_file> [input_file1.json ...]"
    echo "       $0 --json_out <json_file> --csv_out <csv_file> [input_file1.json ...]"
    echo ""
    echo "Merges 'views' from multiple JSON files and extracts cell segmentation data to a CSV."
    echo ""
    echo "Options:"
    echo "  -j, --json_out <file>    Required. Path for the merged JSON output file."
    echo "  -c, --csv_out <file>     Required. Path for the CSV output file."
    echo "  -h, --help               Display this help message and exit."
    exit 1
}

PARSED_ARGS=$(getopt -o j:c:h --long json_out:,csv_out:,help --name "$0" -- "$@")
if [[ $? -ne 0 ]]; then
    exit 2
fi

eval set -- "$PARSED_ARGS"

while true; do
    case "$1" in
        -j|--json_out)
            JSON_OUT="$2"
            shift 2
            ;;
        -c|--csv_out)
            CSV_OUT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        --)
            shift 
            break
            ;;
        *)
            echo "Internal error!" >&2
            exit 3
            ;;
    esac
done

for arg in "$@"; do
    INPUT_FILES+=("$arg")
done


if [[ -z "$JSON_OUT" ]] || [[ -z "$CSV_OUT" ]]; then
    echo "Error: --json_out and --csv_out arguments are required." >&2
    usage
fi

if [ ${#INPUT_FILES[@]} -eq 0 ]; then
    echo "Error: At least one input JSON file is required." >&2
    usage
fi

################ Merging

echo "Merging ${#INPUT_FILES[@]} input files into $JSON_OUT..."
jq -s 'reduce .[] as $item ({views: {}}; .views += $item.views)' "${INPUT_FILES[@]}" > "$JSON_OUT"
echo "Merge complete."

################ Extracting into CSV of "cell ID" to "cell type"

echo "Extracting cell data from $JSON_OUT into $CSV_OUT..."
jq -r '
    ["cell ID", "cell type"],
    (
        .views | to_entries[] |
        . as $view_entry |
        $view_entry.value.sourceDisplays[]? |
        select(.segmentationDisplay.selectedSegmentIds) |
        .segmentationDisplay.selectedSegmentIds[] |
        [ (split(";")[-1]), $view_entry.key ]
    )
| @csv
' "$JSON_OUT" > "$CSV_OUT"

echo "Extraction complete. CSV saved to $CSV_OUT."
echo "Done."