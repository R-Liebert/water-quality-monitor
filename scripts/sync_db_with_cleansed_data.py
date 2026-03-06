import json
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from geoalchemy2.shape import from_shape
from shapely.geometry import shape, MultiLineString

from app.db.session import AsyncSessionLocal, engine
from app.db.base import Base
from app.models.waterway import WaterwayObservation
from app.models.incident import EnvironmentalIncident # ensure all models are imported for metadata

async def populate_database_with_cleansed_data():
    """
    Imports the cleansed GeoJSON segments into the PostGIS database.
    This ensures the FastAPI /waterways/status endpoint is in sync with the frontend.
    """
    async with engine.begin() as conn:
        print("Creating tables if they don't exist...")
        # Since we changed a column type, we'll drop and recreate for the sync script
        # In production, use alembic migrations
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    input_path = "/app/data/clean_segmented_uk_rivers.geojson"
    print(f"Loading cleansed segments from {input_path}...")
    
    with open(input_path, 'r') as f:
        data = json.load(f)

    async with AsyncSessionLocal() as session:
        # We don't need to delete as we just dropped/created tables above
        
        print(f"Importing {len(data['features'])} segments into PostGIS...")
        
        batch_size = 500
        for i in range(0, len(data['features']), batch_size):
            batch = data['features'][i:i + batch_size]
            for feature in batch:
                props = feature['properties']
                geom_shape = shape(feature['geometry'])
                
                # Force to MultiLineString for DB consistency
                if geom_shape.geom_type == 'LineString':
                    geom_shape = MultiLineString([geom_shape])
                
                obs = WaterwayObservation(
                    location_name=props.get('name', 'Unknown River'),
                    geom=from_shape(geom_shape, srid=4326),
                    hydration_index=props.get('hydration_index'),
                    turbidity=props.get('turbidity'),
                    runoff_risk_score=props.get('risk_score'),
                    sewage_spill_active=1 if props.get('status') == 'critical' else 0
                )
                session.add(obs)
            
            await session.commit()
            print(f"Batch {i//batch_size + 1} imported...")

    print("Database sync complete.")

if __name__ == "__main__":
    asyncio.run(populate_database_with_cleansed_data())
