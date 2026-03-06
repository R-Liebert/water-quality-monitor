from fastapi import APIRouter, Depends, Query, Response, Request
from app.core.config import settings
from app.services.copernicus_service import copernicus_service
import httpx
import base64

router = APIRouter()

# Evalscript for NDWI
NDWI_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: ["B03", "B08"],
    output: { bands: 3 }
  };
}
function evaluatePixel(sample) {
  let ndwi = (sample.B03 - sample.B08) / (sample.B03 + sample.B08);
  // Map NDWI to a blue-ish ramp
  if (ndwi > 0.2) return [0, 0, 0.5 + ndwi/2]; // Water
  if (ndwi > 0) return [0.5, 0.8, 1]; // Saturated
  return [1, 1, 1]; // Dry
}
"""

# Evalscript for True Color
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

    # Use the Universal CDSE endpoint (no Instance ID needed if using EVALSCRIPT)
    url = "https://sh.dataspace.copernicus.eu/ogc/wms/default"
    
    # Select evalscript based on requested layer
    layer_name = params.get("LAYERS", "NDWI")
    evalscript = NDWI_EVALSCRIPT if layer_name == "NDWI" else TRUE_COLOR_EVALSCRIPT
    
    # Inject our dynamic configuration
    params["EVALSCRIPT"] = base64.b64encode(evalscript.encode()).decode()
    params["LAYERS"] = "S2L2A" # Standard Sentinel-2 L2A collection
    
    if "TIME" not in params:
        from datetime import datetime, timedelta
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        params["TIME"] = f"{thirty_days_ago.date().isoformat()}/{now.date().isoformat()}"
    
    if "MAXCC" not in params:
        params["MAXCC"] = "20"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
            return Response(content=response.content, media_type=response.headers.get("content-type"))
        except Exception as e:
            return Response(content=str(e), status_code=500)

@router.get("/config")
async def get_copernicus_config():
    return {
        "enabled": settings.COPERNICUS_CLIENT_ID is not None,
        "proxy_url": "/api/v1/copernicus/wms"
    }
