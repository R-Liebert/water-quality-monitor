from fastapi import APIRouter, Response, Request
from app.core.config import settings
from app.services.copernicus_service import copernicus_service
import httpx
from datetime import datetime, timedelta

router = APIRouter()

# High-quality NDMI (Moisture) Evalscript with Alpha Transparency
NDWI_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: ["B08", "B11"],
    output: { bands: 4 }
  };
}
function evaluatePixel(sample) {
  let ndmi = (sample.B08 - sample.B11) / (sample.B08 + sample.B11);
  
  // Continuous color gradient for NDMI (Ground/Vegetation Moisture)
  if (ndmi > 0.4) return [0.0, 0.0, 0.8, 0.7]; // Very High Moisture / Water
  if (ndmi > 0.2) return [0.0, 0.6, 0.6, 0.7]; // High Moisture
  if (ndmi > 0.0) return [0.4, 0.8, 0.4, 0.7]; // Moderate Moisture
  if (ndmi > -0.2) return [0.9, 0.8, 0.2, 0.7]; // Low Moisture
  if (ndmi > -0.8) return [0.8, 0.4, 0.1, 0.7]; // Dry / Bare soil
  return [0.6, 0.0, 0.0, 0.7]; // Extreme dry
}
"""

# True Color Evalscript for debugging
TRUE_COLOR_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: ["B04", "B03", "B02"],
    output: { bands: 3 }
  };
}
function evaluatePixel(sample) {
  return [sample.B04 * 2.5, sample.B03 * 2.5, sample.B02 * 2.5];
}
"""

@router.get("/wms")
async def proxy_wms(request: Request):
    params = dict(request.query_params)
    token = await copernicus_service.get_token()
    
    if not token:
        return Response(content="Authentication Failed", status_code=401)

    # Parse WMS parameters to build Process API request
    bbox_str = params.get("BBOX", "")
    if not bbox_str:
        return Response(content="Missing BBOX parameter", status_code=400)
    
    try:
        bbox = [float(x) for x in bbox_str.split(",")]
        # If coordinates are very large, they are likely EPSG:3857 (Mercator meters)
        # We need to unproject them to EPSG:4326 (Degrees) for Copernicus process/stats API
        if crs == "EPSG:3857" or any(abs(c) > 180 for c in bbox):
            import math
            def unproject(x, y):
                lon = (x / 20037508.34) * 180
                lat = (y / 20037508.34) * 180
                lat = 180 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180)) - math.pi / 2)
                return lon, lat
            
            lon_min, lat_min = unproject(bbox[0], bbox[1])
            lon_max, lat_max = unproject(bbox[2], bbox[3])
            bbox = [lon_min, lat_min, lon_max, lat_max]
            crs_code = "4326"
    except ValueError:
        return Response(content="Invalid BBOX format", status_code=400)
    width = int(params.get("WIDTH", 256))
    height = int(params.get("HEIGHT", 256))
    crs = params.get("SRS") or params.get("CRS", "EPSG:3857")
    # Convert EPSG:3857 to 3857
    crs_code = crs.split(":")[-1]
    
    layer_name = params.get("LAYERS", "NDWI")
    evalscript = NDWI_EVALSCRIPT if layer_name == "NDWI" else TRUE_COLOR_EVALSCRIPT

    time_param = params.get("time")
    if time_param and "/" in time_param:
        time_from, time_to = time_param.split("/")
        # add "T00:00:00Z" to make it ISO 8601 if it's only YYYY-MM-DD
        if len(time_from) == 10:
            time_from += "T00:00:00Z"
        if len(time_to) == 10:
            time_to += "T23:59:59Z"
    else:
        time_from = (datetime.now() - timedelta(days=180)).isoformat() + "Z"
        time_to = datetime.now().isoformat() + "Z"

    # Build the Process API JSON payload
    payload = {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": { "crs": f"http://www.opengis.net/def/crs/EPSG/0/{crs_code}" }
            },
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {
                    "timeRange": {
                        "from": time_from,
                        "to": time_to
                    },
                    "mosaickingOrder": "mostRecent",
                    "maxCloudCoverage": 20
                }
            }]
        },
        "output": {
            "width": width,
            "height": height,
            "responses": [{ "identifier": "default", "format": { "type": "image/png" } }]
        },
        "evalscript": evalscript
    }

    async with httpx.AsyncClient() as client:
        try:
            url = "https://sh.dataspace.copernicus.eu/api/v1/process"
            response = await client.post(
                url, 
                json=payload, 
                headers={"Authorization": f"Bearer {token}", "Accept": "image/png"},
                timeout=30.0
            )
            
            if response.status_code != 200:
                print(f"Copernicus Error ({response.status_code}): {response.text}")
                return Response(content=response.content, status_code=response.status_code)
                
            return Response(content=response.content, media_type="image/png")
        except Exception as e:
            return Response(content=str(e), status_code=500)

@router.get("/config")
async def get_copernicus_config():
    return {
        "enabled": settings.COPERNICUS_CLIENT_ID is not None,
        "proxy_url": "/api/v1/copernicus/wms"
    }
