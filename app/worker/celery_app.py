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

@celery_app.task
def fetch_weather_and_calculate_risk():
    """Live task for weather ingestion and risk model"""
    print("Fetching live Open-Meteo precipitation data for agricultural zones...")
    
    # Coordinates for a major UK agricultural zone near the River Severn for demonstration
    test_lat, test_lng = 52.1, -2.2 
    
    # Run the async fetcher inside the synchronous celery worker
    max_precip = asyncio.run(fetch_live_precipitation_forecast(test_lat, test_lng))
    risk_score = calculate_runoff_risk(max_precip)
    
    print(f"Forecasted Max Precipitation: {max_precip}mm -> Runoff Risk Score: {risk_score:.2f}")
    
    # In a full deployment, this score would be written back to the PostGIS database 
    # to update the corresponding 1km river segment.
    return {"max_precip_mm": max_precip, "calculated_risk": risk_score}

@celery_app.task
def fetch_sewage_spills():
    """Task to ingest Environment Agency sewage spill events"""
    print("Executing EA sewage spills ingestion task...")
    result = fetch_uk_ea_sewage_spills()
    return f"Processed {len(result)} sewage incidents."