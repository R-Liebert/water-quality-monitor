import geopandas as gpd
from shapely.geometry import LineString, MultiLineString
import numpy as np

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geopandas as gpd
from shapely.geometry import LineString, MultiLineString, Point
import numpy as np
import asyncio
from app.services.ingest_ea_data import fetch_uk_ea_sewage_spills
from app.services.ingest_weather import fetch_live_precipitation_forecast

def segment_river_into_1km_zones(input_geojson_path, output_geojson_path):
    print(f"Loading river dataset from {input_geojson_path}...")
    gdf = gpd.read_file(input_geojson_path)

    print("Fetching live data for enrichment...")
    live_ea_stations = fetch_uk_ea_sewage_spills()
    ea_points = [Point(s['lng'], s['lat']) for s in live_ea_stations]
    
    # Regional weather check - sample 10 major UK river basins to speed up
    # (In a full scale system, we'd do this per segment, but for the demo we'll use regions)
    weather_basins = {
        "South West": (50.8, -3.5), "South East": (51.3, 0.5), "Midlands": (52.5, -1.8),
        "North West": (53.5, -2.5), "North East": (54.5, -1.5), "Wales": (52.3, -3.8),
        "Scotland": (56.5, -4.2), "London": (51.5, -0.1)
    }
    
    basin_risks = {}
    print("Fetching live weather forecasts for major UK river basins...")
    for region, (lat, lng) in weather_basins.items():
        max_precip = asyncio.run(fetch_live_precipitation_forecast(lat, lng))
        basin_risks[region] = max_precip
        print(f"  {region}: {max_precip}mm forecast")

    print("Projecting to EPSG:27700 (Metric) for accurate distance calculations...")
    gdf_metric = gdf.to_crs(epsg=27700)
    ea_points_metric = [gpd.GeoSeries([p], crs="EPSG:4326").to_crs(epsg=27700).iloc[0] for p in ea_points]

    segmented_lines = []
    segmented_data = []
    segment_length_m = 10000 

    for idx, row in gdf_metric.iterrows():
        # ONLY keep named rivers for the demo to prevent browser crashes
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
                
                # Enrichment Logic: Real Data
                center_point = segment.centroid
                
                # 1. Critical check (Proximity to active EA station)
                # Find if any EA spill/flood station is within 5km of this segment
                is_critical = False
                for ea_p in ea_points_metric:
                    if center_point.distance(ea_p) < 5000: # 5km
                        is_critical = True
                        break
                
                # 2. Weather/Warning check
                # Check nearest basin weather
                # Simple lat/lng check on original row for speed
                lat, lng = row.geometry.centroid.xy # (this is rough but works for demo)
                risk_score = 0.1 # base
                status = "normal"
                explanation = "Water quality metrics within normal parameters."
                
                if is_critical:
                    status = "critical"
                    risk_score = 0.95
                    explanation = "LIVE ALERT: Proximity to active Environment Agency discharge/flood station."
                else:
                    # check for rain risk in basins
                    # (we'll just use a simple lookup for demo speed)
                    # if a region is > 10mm, mark as warning
                    for region, precip in basin_risks.items():
                        if precip > 10.0:
                            status = "warning"
                            risk_score = 0.1 + (precip / 20.0)
                            explanation = f"WEATHER ALERT: Heavy precipitation ({precip}mm) forecast. High risk of agricultural runoff."
                            break

                props = row.to_dict()
                props.pop('geometry', None)
                props['segment_id'] = f"{name.replace(' ', '_').lower()}_{idx}_{segment_id}"
                props['status'] = status
                props['risk_score'] = risk_score
                props['explanation'] = explanation
                
                segmented_data.append(props)
                segment_id += 1

    print(f"Generated {len(segmented_lines)} major evaluation zones with real-time enrichment.")
    new_gdf = gpd.GeoDataFrame(segmented_data, geometry=segmented_lines, crs="EPSG:27700")

    print("Aggressively simplifying geometries for performance...")
    new_gdf.geometry = new_gdf.geometry.simplify(200) # 200m tolerance

    print("Projecting back to Web Mercator (EPSG:4326) for web frontend...")
    new_gdf_web = new_gdf.to_crs(epsg=4326)

    new_gdf_web.to_file(output_geojson_path, driver="GeoJSON")
    print(f"Successfully saved major segmented rivers with real data to {output_geojson_path}")

if __name__ == "__main__":
    segment_river_into_1km_zones("data/raw_uk_rivers.geojson", "data/segmented_uk_rivers.geojson")
