from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/frontend-config")
async def get_frontend_config():
    """
    Exposes safe, non-secret configuration variables to the frontend.
    This prevents users from having to hardcode API keys into HTML/JS files.
    """
    return {
        "google_maps_api_key": settings.GOOGLE_API_KEY if settings.GOOGLE_API_KEY else None
    }