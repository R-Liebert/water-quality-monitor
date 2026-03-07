import json

# Roughly drawing major UK river backbones
major_rivers = {
    "River Thames": [[-2.0, 51.7], [-1.2, 51.6], [-0.9, 51.55], [-0.6, 51.5], [-0.1, 51.5], [0.3, 51.45], [0.7, 51.5], [1.0, 51.5]],
    "River Severn": [[-3.7, 52.5], [-3.0, 52.7], [-2.5, 52.4], [-2.2, 51.8], [-2.6, 51.5], [-3.0, 51.4]],
    "River Trent": [[-2.1, 53.1], [-1.5, 52.8], [-0.8, 53.0], [-0.7, 53.6], [-0.2, 53.7]],
    "River Wye": [[-3.7, 52.4], [-3.1, 52.1], [-2.7, 51.6]],
    "River Tyne": [[-2.5, 54.9], [-1.8, 54.95], [-1.4, 55.0]],
    "River Clyde": [[-3.6, 55.6], [-4.0, 55.8], [-4.7, 55.9]],
    "River Mersey": [[-2.0, 53.4], [-2.3, 53.4], [-3.0, 53.45]]
}

features = []
for name, coords in major_rivers.items():
    features.append({
        "type": "Feature",
        "properties": {"name": name},
        "geometry": {"type": "LineString", "coordinates": coords}
    })

geojson = {"type": "FeatureCollection", "features": features}

with open('/app/data/raw_uk_rivers.geojson', 'w') as f:
    json.dump(geojson, f)

print("Generated raw UK river backbones.")
