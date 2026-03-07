from celery import Celery
from celery.schedules import crontab
from app.core.config import settings
from app.services.ingest_ea_data import fetch_uk_ea_sewage_spills

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

@celery_app.task
def fetch_copernicus_data():
    """Mock task for Copernicus ingestion"""
    print("Ingesting Copernicus satellite data for UK boundaries...")
    return "Copernicus data processed"

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
            
            # Use a cache to avoid redundant API calls for nearby segments
            # Weather APIs typically use a grid, so rounding to 2 decimal places (approx 1.1km)
            # is a safe way to group segments without losing meaningful weather variance.
            coord_cache = {}
            unique_coords = []

            for _, lat, lng in rows:
                if lat and lng:
                    rounded_lat, rounded_lng = round(lat, 2), round(lng, 2)
                    if (rounded_lat, rounded_lng) not in coord_cache:
                        coord_cache[(rounded_lat, rounded_lng)] = None
                        unique_coords.append((rounded_lat, rounded_lng))

            # Fetch all unique weather data concurrently
            if unique_coords:
                weather_results = await asyncio.gather(*[
                    fetch_live_precipitation_forecast(lat, lng)
                    for lat, lng in unique_coords
                ])
                for i, coords in enumerate(unique_coords):
                    coord_cache[coords] = weather_results[i]

            for obs, lat, lng in rows:
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