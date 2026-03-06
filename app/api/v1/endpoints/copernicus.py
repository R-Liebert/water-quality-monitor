from fastapi import APIRouter, Depends, Query, Response, Request
from app.core.config import settings
from app.services.copernicus_service import copernicus_service
import httpx

router = APIRouter()

@router.get("/wms")
async def proxy_wms(request: Request):
    params = dict(request.query_params)
    token = await copernicus_service.get_token()
    
    if not token:
        return Response(content="Authentication Failed", status_code=401)

    # Use the dynamic CDSE OGC endpoint
    url = "https://sh.dataspace.copernicus.eu/ogc/wms/e0106634-0672-42c1-811a-91a3c148fa30"
    
    # Add mosaicking and cloud filters to the request if they aren't there
    if 'TIME' not in params:
        from datetime import datetime, timedelta
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        params['TIME'] = f"{thirty_days_ago.date().isoformat()}/{now.date().isoformat()}"
    
    if 'MAXCC' not in params:
        params['MAXCC'] = '20'

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
        return Response(content=response.content, media_type=response.headers.get("content-type"))

@router.get("/config")
async def get_copernicus_config():
    return {
        "enabled": settings.COPERNICUS_CLIENT_ID is not None,
        "proxy_url": "/api/v1/copernicus/wms"
    }