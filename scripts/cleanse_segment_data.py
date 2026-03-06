import geopandas as gpd
import json
import os

def cleanse_segment_data(input_geojson, output_geojson):
    print(f"Loading segmented data from {input_geojson}...")
    
    if not os.path.exists(input_geojson):
         print(f"Error: Could not find {input_geojson}")
         return

    with open(input_geojson, 'r') as f:
        data = json.load(f)

    cleansed_features = []
    removed_count = 0
    
    # Data Validation Rules:
    # 1. 'status' must exist. If not, default to 'nodata'.
    # 2. If 'status' is 'nodata', then 'risk_score' must be exactly None (not 0.0 or a string).
    # 3. Strip out mock string explanations. Replace with a standard "Awaiting Telemetry" if nodata.

    for feature in data.get('features', []):
        props = feature.get('properties', {})
        
        # Rule 1: Reset all simulated data to a clean, baseline 'nodata' state 
        # so the system is ready for live ingestion.
        
        # We are actively stripping out the mock warnings, criticals, and random risk scores
        # generated during the initial `segment_rivers.py` run.
        if props.get('status') != 'nodata':
             removed_count += 1
             
        props['status'] = 'nodata'
        
        # Rule 2: Enforce null values for quantitative fields awaiting real data
        props['risk_score'] = None
        props['turbidity'] = None
        
        # Rule 3: Standardize the explanation field
        props['explanation'] = "Awaiting real-time telemetry from satellite or terrestrial sensors."

        # Keep the valid identifying metadata (name, segment_id, length_m)
        feature['properties'] = props
        cleansed_features.append(feature)

    # Rebuild the valid FeatureCollection
    cleansed_data = {
        "type": "FeatureCollection",
        "features": cleansed_features
    }

    # Save the cleansed data
    with open(output_geojson, 'w') as f:
        json.dump(cleansed_data, f)
        
    print(f"Data Cleansing Complete.")
    print(f"Removed {removed_count} simulated metric sets.")
    print(f"Verified {len(cleansed_features)} segments now conform to the 'nodata' baseline schema.")
    print(f"Saved clean dataset to {output_geojson}")

if __name__ == "__main__":
    input_path = "/app/data/segmented_uk_rivers.geojson"
    output_path = "/app/data/clean_segmented_uk_rivers.geojson"
    cleanse_segment_data(input_path, output_path)
