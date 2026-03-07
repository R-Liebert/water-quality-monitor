from celery import Celery
from celery.schedules import crontab
from app.core.config import settings
from app.services.ingest_ea_data import fetch_uk_ea_sewage_spills
import json
import asyncio
import httpx
from datetime import datetime, timedelta
from app.services.copernicus_service import copernicus_service
from app.services.ingest_weather import fetch_live_precipitation_forecast, calculate_runoff_risk
from app.db.session import get_session_factory
from sqlalchemy.ext.asyncio import create_async_engine
from app.models.waterway import WaterwayObservation
from sqlalchemy import select, func, text

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Setup Periodic Tasks (Hourly cron)
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Fetch Copernicus data hourly
    sender.add_periodic_task(
        crontab(minute=0, hour='*'),
        fetch_copernicus_data.s(),
        name='fetch-copernicus-hourly'
    )
    # Fetch weather and calculate risk
    sender.add_periodic_task(
        crontab(minute=15, hour='*'),
        fetch_weather_and_calculate_risk.s(),
        name='fetch-weather-hourly'
    )
    # Fetch EA Sewage Spills
    sender.add_periodic_task(
        crontab(minute=30, hour='*'),
        fetch_sewage_spills.s(),
        name='fetch-sewage-spills-hourly'
    )

async def fetch_copernicus_stats(geom_geojson, token, client=None):
    if not token:
        return None
    
    # Process API endpoint for statistical analysis
    url = "https://sh.dataspace.copernicus.eu/api/v1/statistics"
    
    # Evalscript to calculate NDWI and a proxy for Turbidity
    # Statistics API REQUIRES dataMask output.
    # We use named outputs to ensure reliability.
    evalscript = """
    //VERSION=3
    function setup() {
      return {
        input: ["B03", "B08", "B11", "dataMask"],
        output: [
          { id: "default", bands: 2 },
          { id: "dataMask", bands: 1 }
        ]
      };
    }
    function evaluatePixel(sample) {
      let ndwi = (sample.B03 + sample.B08) !== 0 ? (sample.B03 - sample.B08) / (sample.B03 + sample.B08) : 0;
      let turbidity = sample.B11; // Simplified proxy for suspended matter
      return {
        default: [ndwi, turbidity],
        dataMask: [sample.dataMask]
      };
    }
    """
    
    payload = {
        "input": {
            "bounds": { 
                "geometry": json.loads(geom_geojson),
                "properties": { "crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84" } 
            },
            "data": [{ 
                "type": "sentinel-2-l2a", 
                "dataFilter": { "mosaickingOrder": "mostRecent", "maxCloudCoverage": 20 } 
            }]
        },
        "aggregation": {
            "timeRange": { 
                "from": (datetime.now() - timedelta(days=30)).isoformat() + "Z", 
                "to": datetime.now().isoformat() + "Z" 
            },
            "aggregationInterval": { "of": "P30D" },
            "evalscript": evalscript
        }
    }

    try:
        if client is None:
            async with httpx.AsyncClient() as new_client:
                response = await new_client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
        else:
            response = await client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})

        if response.status_code != 200:
            if response.status_code == 429:
                print("Copernicus API: Rate limit hit (429).")
            else:
                print(f"Copernicus API Error ({response.status_code}): {response.text}")
            return None

        stats = response.json()

        data_points = stats.get('data', [])
        if not data_points:
            return None
            
        # Extract mean values from 'default' output
        # With multiple outputs, bands are indexed B0, B1 in the specified output ID
        bands = data_points[0].get('outputs', {}).get('default', {}).get('bands', {})
        return {
            "ndwi": bands.get('B0', {}).get('stats', {}).get('mean'),
            "turbidity": bands.get('B1', {}).get('stats', {}).get('mean')
        }
    except Exception as e:
        print(f"Copernicus API Exception: {e}")
    return None

async def run_copernicus_ingestion(session_factory):
    print("Connecting to DB for Copernicus update...")
    
    # Retry token acquisition to handle transient DNS issues
    token = None
    for attempt in range(3):
        token = await copernicus_service.get_token()
        if token:
            break
        print(f"Token acquisition attempt {attempt+1} failed. Retrying in 3s...")
        await asyncio.sleep(3.0)

    if not token:
        print("Failed to acquire Copernicus token after retries. Aborting ingestion.")
        return

    updates = 0
    async with session_factory() as session:
        # Reduced batch size to 5 to avoid 429 errors on free tier
        query = select(
            WaterwayObservation,
            func.ST_AsGeoJSON(
                func.ST_SimplifyPreserveTopology(
                    func.ST_Buffer(WaterwayObservation.geom, 0.0001), 
                    0.0001
                )
            ).label('geom_json')
        ).where(WaterwayObservation.hydration_index == None).limit(5)

        result = await session.execute(query)
        rows = result.all()
        
        if not rows:
            print("No new waterway segments found to update.")
            return

        observations = [row[0] for row in rows]
        geom_jsons = [row.geom_json for row in rows]

        # Fetch Copernicus stats sequentially with delay to respect rate limits
        async with httpx.AsyncClient() as client:
            for obs, gj in zip(observations, geom_jsons):
                stats = await fetch_copernicus_stats(gj, token, client=client)
                if stats:
                    obs.hydration_index = stats['ndwi']
                    obs.turbidity = stats['turbidity']
                    updates += 1
                    print(f"Updated {obs.location_name}: NDWI={obs.hydration_index}")
                await asyncio.sleep(2.0) # More breathing room for rate limits
        
        if updates > 0:
            await session.commit()
            print(f"Successfully updated {updates} waterway segments with Copernicus data.")

async def process_weather_and_update_db(session_factory):
    print("Connecting to DB to update weather risk scores...")
    updates = 0
    try:
        async with session_factory() as session:
            # For demonstration, limit to 50 segments to respect API limits
            # Using ST_Centroid because geom is MULTILINESTRING
            query = select(
                WaterwayObservation, 
                func.ST_Y(func.ST_Centroid(WaterwayObservation.geom)).label('lat'), 
                func.ST_X(func.ST_Centroid(WaterwayObservation.geom)).label('lng')
            ).limit(50)
            
            result = await session.execute(query)
            rows = result.all()
            
            # Use a cache to avoid redundant API calls for nearby segments
            coord_cache = {}
            unique_coords = []

            for row in rows:
                obs, lat, lng = row
                if lat and lng:
                    rounded_lat, rounded_lng = round(lat, 2), round(lng, 2)
                    if (rounded_lat, rounded_lng) not in coord_cache:
                        coord_cache[(rounded_lat, rounded_lng)] = None
                        unique_coords.append((rounded_lat, rounded_lng))

            # Fetch all unique weather data concurrently
            if unique_coords:
                async with httpx.AsyncClient() as client:
                    weather_results = await asyncio.gather(*[
                        fetch_live_precipitation_forecast(lat, lng, client=client)
                        for lat, lng in unique_coords
                    ])
                for i, coords in enumerate(unique_coords):
                    coord_cache[coords] = weather_results[i]

            for row in rows:
                obs, lat, lng = row
                if lat and lng:
                    rounded_lat, rounded_lng = round(lat, 2), round(lng, 2)
                    max_precip = coord_cache.get((rounded_lat, rounded_lng), 0.0)
                    risk_score = calculate_runoff_risk(max_precip)
                    obs.runoff_risk_score = risk_score
                    updates += 1
                    
            if updates > 0:
                await session.commit()
                print(f"Successfully updated {updates} waterway segments with new runoff risk scores.")
            else:
                print("No waterway segments found to update.")
                
    except Exception as e:
        print(f"Failed to update weather risk scores: {e}")
        
    return updates

def run_async_with_db(async_func):
    """Helper to run async code in a synchronous Celery task safely with its own loop and engine."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Create engine and session factory inside the new loop
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = get_session_factory(engine=engine)
    
    try:
        return loop.run_until_complete(async_func(session_factory))
    finally:
        # Clean up engine and loop
        loop.run_until_complete(engine.dispose())
        loop.close()

@celery_app.task
def fetch_copernicus_data():
    """Live task for Copernicus ingestion"""
    print("Ingesting live Copernicus satellite data...")
    run_async_with_db(run_copernicus_ingestion)
    return "Copernicus ingestion complete"

@celery_app.task
def fetch_weather_and_calculate_risk():
    """Live task for weather ingestion and risk model"""
    print("Fetching live Open-Meteo precipitation data for agricultural zones...")
    
    # Run the async fetcher and db updater inside the synchronous celery worker
    updates = run_async_with_db(process_weather_and_update_db)
    
    return {"updated_segments": updates}

async def process_spills_and_update_db(session_factory):
    print("Fetching live EA spills...")
    incidents = fetch_uk_ea_sewage_spills()
    
    if not incidents:
        print("No active sewage spills found.")
        return 0

    updates = 0
    try:
        async with session_factory() as session:
            # First, reset all active spills to 0
            await session.execute(text("UPDATE waterway_observations SET sewage_spill_active = 0"))
            
            # Then, update segments near incidents to 1
            for inc in incidents:
                lat = inc['lat']
                lng = inc['lng']
                # Mark rivers within ~5km (0.05 degrees)
                query = text("""
                    UPDATE waterway_observations
                    SET sewage_spill_active = 1
                    WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 0.05)
                """)
                res = await session.execute(query, {"lng": lng, "lat": lat})
                updates += res.rowcount
                
            await session.commit()
            print(f"Successfully marked {updates} waterway segments as critical due to sewage spills.")
    except Exception as e:
        print(f"Failed to update spill data in DB: {e}")
        
    return updates

@celery_app.task
def fetch_sewage_spills():
    """Task to ingest Environment Agency sewage spill events and update the DB"""
    print("Executing EA sewage spills ingestion task...")
    updates = run_async_with_db(process_spills_and_update_db)
    return f"Marked {updates} waterway segments as critical due to sewage spills."