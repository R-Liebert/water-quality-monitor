import json
import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def ingest_geojson(file_path):
    print(f"Reading {file_path}...")
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    features = data.get('features', [])
    print(f"Found {len(features)} features. Starting ingestion...")

    async with AsyncSessionLocal() as session:
        # Optional: Clear existing data
        # await session.execute(delete(WaterwayObservation))
        
        batch_size = 1000
        for i in range(0, len(features), batch_size):
            batch = features[i:i+batch_size]
            
            for feature in batch:
                props = feature.get('properties', {})
                geom = feature.get('geometry', {})
                
                # Convert LineString to WKT or use ST_GeomFromGeoJSON
                geom_json = json.dumps(geom)
                
                # We use raw SQL for efficient spatial insertion with ST_GeomFromGeoJSON
                # Note: SRID 4326
                sql = text("""
                    INSERT INTO waterway_observations 
                    (location_name, geom, runoff_risk_score, hydration_index, turbidity, sewage_spill_active, timestamp)
                    VALUES (:name, ST_GeomFromGeoJSON(:geom), :risk, :hydration, :turbidity, :spill, NOW())
                """)
                
                await session.execute(sql, {
                    "name": props.get('name', 'Unknown'),
                    "geom": geom_json,
                    "risk": props.get('risk_score'),
                    "hydration": props.get('hydration_index'),
                    "turbidity": props.get('turbidity'),
                    "spill": 1 if props.get('status') == 'critical' else 0
                })
            
            await session.commit()
            print(f"Inserted {min(i + batch_size, len(features))}/{len(features)}...")

    print("Ingestion complete.")

if __name__ == "__main__":
    # If running locally, you might need to set DATABASE_URL to localhost
    # os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/water_quality"
    asyncio.run(ingest_geojson("data/segmented_uk_rivers.geojson"))
