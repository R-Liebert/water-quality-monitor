from fastapi import APIRouter, Depends
from app.core.config import settings

router = APIRouter()

@router.get("/copernicus-wms")
async def get_copernicus_wms_config():
    """
    Provides the frontend with the configuration necessary to load 
    Copernicus Web Map Service (WMS) tiles for soil moisture and surface water.
    
    In a fully productionized environment, this endpoint would first exchange the 
    settings.COPERNICUS_CLIENT_ID for an active OAuth token and append it to the WMS URL,
    or act as a proxy to hide the token from the browser.
    """
    
    # We define the specific satellite layers we want to overlay.
    # NDWI (Normalized Difference Water Index) is perfect for showing hydration.
    # It highlights water bodies and saturated soil in bright blues against a dark background.
    
    return {
        "enabled": settings.COPERNICUS_CLIENT_ID is not None,
        "wms_url": "https://sh.dataspace.copernicus.eu/ogc/wms/YOUR_INSTANCE_ID", # User must configure instance in dashboard
        "layers": {
            "surface_water": "NDWI",
            "true_color": "TRUE-COLOR",
            "moisture_index": "MOISTURE-INDEX" # Example custom evalscript layer
        }
    }