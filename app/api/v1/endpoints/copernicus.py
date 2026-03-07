from fastapi import APIRouter, Response, Request
from app.core.config import settings
from app.services.copernicus_service import copernicus_service
import httpx
from datetime import datetime, timedelta

router = APIRouter()

# High-quality NDWI Evalscript with Alpha Transparency
NDWI_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: ["B03", "B08"],
    output: { bands: 4 }
  };
}
function evaluatePixel(sample) {
  let ndwi = (sample.B03 - sample.B08) / (sample.B03 + sample.B08);
  
  // Clear/Deep Water (NDWI > 0.5)
  if (ndwi > 0.5) return [0, 0, 0.5, 0.9];
  // Shallow/Turbid Water (NDWI 0.2 - 0.5)
  if (ndwi > 0.2) return [0, 0.4, 0.8, 0.8];
  // Flooding / Moist Land (NDWI 0.0 - 0.2)
  if (ndwi > 0.0) return [0.2, 0.8, 1.0, 0.6];
  
  // Non-water features (NDWI <= 0)
  return [0, 0, 0, 0];
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
    bbox = [float(x) for x in params.get("BBOX", "").split(",")]
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
