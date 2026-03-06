import geopandas as gpd
from shapely.geometry import LineString, MultiLineString
import numpy as np

def segment_river_into_1km_zones(input_geojson_path, output_geojson_path):
    print(f"Loading river dataset from {input_geojson_path}...")
    gdf = gpd.read_file(input_geojson_path)

    print("Projecting to EPSG:27700 (Metric) for accurate distance calculations...")
    gdf_metric = gdf.to_crs(epsg=27700)

    segmented_lines = []
    segmented_data = []
    segment_length_m = 10000 

    for idx, row in gdf_metric.iterrows():
        # EXTREMELY AGGRESSIVE FILTERING for browser stability
        # Only keep named rivers (skips minor unnamed segments)
        if row.get('waterway') != 'river' or row.get('name') == 'Unknown River':
            continue
            
        geom = row.geometry
        name = row.get('name')

        if geom.is_empty:
            continue

        if isinstance(geom, LineString):
            lines = [geom]
        elif isinstance(geom, MultiLineString):
            lines = list(geom.geoms)
        else:
            continue

        segment_id = 0
        for line in lines:
            length = line.length
            # For named rivers, we can use slightly smaller segments for better detail
            # but still capped for performance
            effective_segment_length = max(segment_length_m, length / 10) 
            num_segments = int(np.ceil(length / effective_segment_length))
            
            for i in range(num_segments):
                start_dist = i * effective_segment_length
                end_dist = min((i + 1) * effective_segment_length, length)
                
                if start_dist == end_dist:
                    continue
                    
                p1 = line.interpolate(start_dist)
                p2 = line.interpolate(end_dist)
                segment = LineString([p1, p2])
                segmented_lines.append(segment)
                
                props = row.to_dict()
                props.pop('geometry', None)
                props['segment_id'] = f"{name.replace(' ', '_').lower()}_{idx}_{segment_id}"
                props['length_m'] = segment.length
                
                # Assign mock statuses
                rand_val = np.random.random()
                if rand_val < 0.15:
                    props['status'] = "critical"
                    props['risk_score'] = 0.85 + (np.random.random() * 0.15)
                    props['explanation'] = "Critical runoff warning. Sustained heavy precipitation detected."
                elif rand_val < 0.35:
                    props['status'] = "warning"
                    props['risk_score'] = 0.5 + (np.random.random() * 0.3)
                    props['explanation'] = "Elevated strain on local sewage infrastructure detected."
                else:
                    props['status'] = "normal"
                    props['risk_score'] = 0.1 + (np.random.random() * 0.2)
                    props['explanation'] = "Water quality metrics within normal parameters."
                
                segmented_data.append(props)
                segment_id += 1

    print(f"Generated {len(segmented_lines)} major evaluation zones.")
    new_gdf = gpd.GeoDataFrame(segmented_data, geometry=segmented_lines, crs="EPSG:27700")

    print("Aggressively simplifying geometries for performance...")
    new_gdf.geometry = new_gdf.geometry.simplify(200) # 200m tolerance

    print("Projecting back to Web Mercator (EPSG:4326) for web frontend...")
    new_gdf_web = new_gdf.to_crs(epsg=4326)

    new_gdf_web.to_file(output_geojson_path, driver="GeoJSON")
    print(f"Successfully saved major segmented rivers to {output_geojson_path}")

if __name__ == "__main__":
    segment_river_into_1km_zones("data/raw_uk_rivers.geojson", "data/segmented_uk_rivers.geojson")
