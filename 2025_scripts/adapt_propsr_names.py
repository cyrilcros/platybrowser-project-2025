#!/usr/bin/env python

import json
import pandas as pd

lut = "./prospr.csv"
json_dataset = "../data/platybrowser_6dpf/dataset.json"

# Load the CSV file and create a mapping
try:
    mapping_df = pd.read_csv(lut)
    mapping = pd.Series(mapping_df.platybrowser_new_name.values, index=mapping_df.view_name).to_dict()
    # Load the JSON file
    with open(json_dataset, 'r') as f:
        data = json.load(f)

    # Create a reverse mapping to find the old key from the new key
    reverse_mapping = {v: k for k, v in mapping.items()}

    # Rename keys in "sources"
    if 'sources' in data:
        new_sources = {}
        for old_key, value in data['sources'].items():
            new_key = mapping.get(old_key, old_key)
            new_sources[new_key] = value
        data['sources'] = new_sources

    # Rename keys in "views" and update internal references
    if 'views' in data:
        new_views = {}
        for old_key, view_data in data['views'].items():
            new_key = mapping.get(old_key, old_key)

            # Update the name in imageDisplay
            if 'sourceDisplays' in view_data and len(view_data['sourceDisplays']) > 0:
                if 'imageDisplay' in view_data['sourceDisplays'][0]:
                    # Update the main name
                    view_data['sourceDisplays'][0]['imageDisplay']['name'] = new_key

                    # Update the sources array within imageDisplay
                    if 'sources' in view_data['sourceDisplays'][0]['imageDisplay']:
                        updated_sources_list = []
                        for source_item in view_data['sourceDisplays'][0]['imageDisplay']['sources']:
                            updated_sources_list.append(mapping.get(source_item, source_item))
                        view_data['sourceDisplays'][0]['imageDisplay']['sources'] = updated_sources_list

            new_views[new_key] = view_data
        data['views'] = new_views

    # Write the updated JSON back to the original file
    with open(json_dataset, 'w') as f:
        json.dump(data, f, indent=2)

    print("Successfully updated the JSON file: 'dataset.json'")
    print("\nHere is a sample of the mapping used:")
    for i, (key, value) in enumerate(mapping.items()):
        if i >= 5:
            break
        print(f"'{key}': '{value}'")

except FileNotFoundError:
    print("Make sure both 'prospr.csv' and 'dataset.json' are in the same directory.")
except Exception as e:
    print(f"An error occurred: {e}")