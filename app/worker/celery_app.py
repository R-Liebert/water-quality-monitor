from celery import Celery
from celery.schedules import crontab
from app.core.config import settings
from app.services.ingest_ea_data import fetch_uk_ea_sewage_spills
import json
from datetime import datetime, timedelta

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

from app.services.copernicus_service import copernicus_service
import httpx

async def fetch_copernicus_stats(geom_geojson):
    token = await copernicus_service.get_token()
    if not token: return None
    
    # Process API endpoint for statistical analysis
    url = "https://sh.dataspace.copernicus.eu/api/v1/statistics"
    
    # Evalscript to calculate NDWI and a proxy for Turbidity
    evalscript = """
    //VERSION=3
    function setup() {
      return {
        input: ["B03", "B08", "B11"],
        output: { id: "default", bands: 2 }
      };
    }
    function evaluatePixel(sample) {
      let ndwi = (sample.B03 - sample.B08) / (sample.B03 + sample.B08);
      let turbidity = sample.B11; // Simplified proxy for suspended matter
      return [ndwi, turbidity];
    }
    """
    
    payload = {
        "input": {
            "bounds": { "geometry": json.loads(geom_geojson), "properties": { "crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84" } },
            "data": [{ "type": "sentinel-2-l2a", "dataFilter": { "mosaickingOrder": "mostRecent", "maxCloudCoverage": 20 } }]
        },
        "aggregation": {
            "timeRange": { "from": (datetime.now() - timedelta(days=30)).isoformat() + "Z", "to": datetime.now().isoformat() + "Z" },
            "aggregationInterval": { "of": "P30D" },
            "evalscript": evalscript
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
            if response.status_code == 200:
                stats = response.json()
                # Extract mean values
                data = stats.get('data', [{}])[0].get('outputs', {}).get('default', {}).get('bands', {})
                return {
                    "ndwi": data.get('B0', {}).get('stats', {}).get('mean'),
                    "turbidity": data.get('B1', {}).get('stats', {}).get('mean')
                }
        except Exception as e:
            print(f"Copernicus API Error: {e}")
    return None

async def run_copernicus_ingestion():
    print("Connecting to DB for Copernicus update...")
    async with AsyncSessionLocal() as session:
        # Sample 20 segments to update per run to stay within API rate limits
        query = select(WaterwayObservation).limit(20)
        result = await session.execute(query)
        observations = result.scalars().all()
        
        for obs in observations:
            # We need the GeoJSON of the segment
            geom_json = await session.execute(func.ST_AsGeoJSON(obs.geom))
            stats = await fetch_copernicus_stats(geom_json.scalar())
            if stats:
                obs.hydration_index = stats['ndwi']
                obs.turbidity = stats['turbidity']
                print(f"Updated {obs.location_name}: NDWI={obs.hydration_index}")
        
        await session.commit()

@celery_app.task
def fetch_copernicus_data():
    """Live task for Copernicus ingestion"""
    print("Ingesting live Copernicus satellite data...")
    asyncio.run(run_copernicus_ingestion())
    return "Copernicus ingestion complete"

import asyncio
from app.services.ingest_weather import fetch_live_precipitation_forecast, calculate_runoff_risk
from app.db.session import AsyncSessionLocal
from app.models.waterway import WaterwayObservation
from sqlalchemy import select, func

async def process_weather_and_update_db():
    print("Connecting to DB to update weather risk scores...")
    updates = 0
    try:
        async with AsyncSessionLocal() as session:
            # For demonstration, limit to 50 segments to respect API limits
            query = select(
                WaterwayObservation, 
                func.ST_Y(WaterwayObservation.geom).label('lat'), 
                func.ST_X(WaterwayObservation.geom).label('lng')
            ).limit(50)
            
            result = await session.execute(query)
            rows = result.all()
            
            for obs, lat, lng in rows:
                if lat and lng:
                    max_precip = await fetch_live_precipitation_forecast(lat, lng)
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

@celery_app.task
def fetch_weather_and_calculate_risk():
    """Live task for weather ingestion and risk model"""
    print("Fetching live Open-Meteo precipitation data for agricultural zones...")
    
    # Run the async fetcher and db updater inside the synchronous celery worker
    updates = asyncio.run(process_weather_and_update_db())
    
    return {"updated_segments": updates}

@celery_app.task
def fetch_sewage_spills():
    """Task to ingest Environment Agency sewage spill events"""
    print("Executing EA sewage spills ingestion task...")
    result = fetch_uk_ea_sewage_spills()
    return f"Processed {len(result)} sewage incidents."