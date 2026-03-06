import httpx
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

async def fetch_live_precipitation_forecast(lat: float, lng: float) -> float:
    """
    Fetches the actual 7-day precipitation forecast for a given coordinate 
    using the free Open-Meteo API. Returns the maximum expected precipitation in mm.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lng,
        "hourly": "precipitation",
        "timezone": "Europe/London"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract hourly precipitation data
            precipitation_data = data.get("hourly", {}).get("precipitation", [])
            
            if not precipitation_data:
                return 0.0
                
            # For risk calculation, we look at the maximum forecasted precipitation spike
            max_precip = max(precipitation_data)
            return max_precip
            
    except Exception as e:
        logger.error(f"Failed to fetch weather data for {lat},{lng}: {e}")
        return 0.0

def calculate_runoff_risk(max_precipitation_mm: float) -> float:
    """
    Calculates a simple runoff risk score (0.0 to 1.0) based on precipitation.
    Heavy rain (> 10mm/hr) causes significant fertilizer runoff.
    """
    if max_precipitation_mm <= 0:
        return 0.1 # Base risk
    elif max_precipitation_mm > 15:
        return 0.95 # Critical risk
    else:
        # Linear scale between 0 and 15mm
        return min(0.1 + (max_precipitation_mm / 15.0) * 0.8, 0.95)
