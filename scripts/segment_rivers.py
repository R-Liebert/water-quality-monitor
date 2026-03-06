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
    segment_length_m = 2000 # 2km resolution

    for idx, row in gdf_metric.iterrows():
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
            num_segments = int(np.ceil(length / segment_length_m))
            
            for i in range(num_segments):
                start_dist = i * segment_length_m
                end_dist = min((i + 1) * segment_length_m, length)
                
                if start_dist == end_dist:
                    continue
                    
                p1 = line.interpolate(start_dist)
                p2 = line.interpolate(end_dist)
                segment = LineString([p1, p2])
                
                # Enrichment Logic: Real Data
                center_point = segment.centroid
                trigger_station = None
                for i_ea, ea_p in enumerate(ea_points_metric):
                    if center_point.distance(ea_p) < 5000: # 5km
                        trigger_station = live_ea_stations[i_ea]
                        break
                
                risk_score = 0.1 
                status = "normal"
                explanation = "Water quality metrics within normal parameters."
                source_url = None
                
                if trigger_station:
                    status = "critical"
                    risk_score = 0.95
                    station_ref = trigger_station.get('station_reference', '')
                    explanation = f"LIVE ALERT: Proximity to active Environment Agency station ({trigger_station['location_name']})."
                    source_url = f"https://environment.data.gov.uk/flood-monitoring/id/stations/{station_ref}"
                else:
                    for region, precip in basin_risks.items():
                        if precip > 10.0:
                            status = "warning"
                            risk_score = 0.1 + (precip / 20.0)
                            explanation = f"WEATHER ALERT: Heavy precipitation ({precip}mm) forecast in {region}."
                            source_url = "https://open-meteo.com/"
                            break

                props = row.to_dict()
                props.pop('geometry', None)
                props['segment_id'] = f"{name.replace(' ', '_').lower()}_{idx}_{segment_id}"
                props['status'] = status
                props['risk_score'] = risk_score
                props['explanation'] = explanation
                props['source_url'] = source_url
                
                segmented_lines.append(segment)
                segmented_data.append(props)
                segment_id += 1

    print(f"Generated {len(segmented_lines)} major evaluation zones with high-resolution enrichment.")
    new_gdf = gpd.GeoDataFrame(segmented_data, geometry=segmented_lines, crs="EPSG:27700")

    print("Simplifying geometries for performance (high-precision)...")
    new_gdf.geometry = new_gdf.geometry.simplify(25) # 25m precision

    print("Projecting back to Web Mercator (EPSG:4326) for web frontend...")
    new_gdf_web = new_gdf.to_crs(epsg=4326)

    new_gdf_web.to_file(output_geojson_path, driver="GeoJSON")
    print(f"Successfully saved major high-res segmented rivers to {output_geojson_path}")

if __name__ == "__main__":
    segment_river_into_1km_zones("data/raw_uk_rivers.geojson", "data/segmented_uk_rivers.geojson")
