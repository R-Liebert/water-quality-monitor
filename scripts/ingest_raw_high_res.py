import json
import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def ingest_raw_rivers(file_path):
    print(f"Reading raw geometry from {file_path}...")
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    features = data.get('features', [])
    print(f"Found {len(features)} features. Loading into PostGIS...")

    async with AsyncSessionLocal() as session:
        # Clear existing observations to replace with high-res raw data
        await session.execute(text("TRUNCATE TABLE waterway_observations RESTART IDENTITY"))
        
        batch_size = 500
        for i in range(0, len(features), batch_size):
            batch = features[i:i+batch_size]
            for feature in batch:
                props = feature.get('properties', {})
                geom = feature.get('geometry', {})
                
                sql = text("""
                    INSERT INTO waterway_observations 
                    (location_name, geom, runoff_risk_score, hydration_index, turbidity, sewage_spill_active, timestamp)
                    VALUES (:name, ST_Multi(ST_GeomFromGeoJSON(:geom)), 0.1, NULL, NULL, 0, NOW())
                """)
                
                await session.execute(sql, {
                    "name": props.get('name', 'Unknown River'),
                    "geom": json.dumps(geom)
                })
            
            await session.commit()
            print(f"Ingested {min(i + batch_size, len(features))}/{len(features)}...")

    print("Ingestion of high-resolution geometry complete.")

if __name__ == "__main__":
    asyncio.run(ingest_raw_rivers("data/raw_uk_rivers.geojson"))
