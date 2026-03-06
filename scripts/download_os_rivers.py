import os
import requests
import json

def download_true_rivers():
    print("Fetching true river geometry using OpenStreetMap Overpass API for a UK region...")
    # Overpass query: fetch major named waterways for the entire United Kingdom
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = """
    [out:json][timeout:300];
    (
      way["waterway"~"river|canal"]["name"](49.9,-8.2,60.8,1.8);
    );
    out geom;
    """
    
    response = requests.post(overpass_url, data={'data': overpass_query})
    response.raise_for_status()
    data = response.json()
    
    features = []
    for element in data.get('elements', []):
        if element['type'] == 'way':
            coords = [[node['lon'], node['lat']] for node in element.get('geometry', [])]
            if len(coords) > 1:
                feature = {
                    "type": "Feature",
                    "properties": {
                        "name": element.get('tags', {}).get('name', 'Unknown River'),
                        "waterway": "river"
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords
                    }
                }
                features.append(feature)
                
    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }
    
    os.makedirs('data', exist_ok=True)
    with open('data/raw_uk_rivers.geojson', 'w') as f:
        json.dump(geojson_data, f)
        
    print(f"Successfully downloaded true river geometry. Saved {len(features)} river ways to data/raw_uk_rivers.geojson")

if __name__ == "__main__":
    download_true_rivers()
