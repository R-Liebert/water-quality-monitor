import httpx
import logging
from datetime import datetime, timedelta
from app.core.config import settings

logger = logging.getLogger(__name__)

class CopernicusService:
    _token = None
    _token_expiry = datetime.min

    async def get_token(self):
        if datetime.now() < self._token_expiry and self._token:
            return self._token

        url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": settings.COPERNICUS_CLIENT_ID,
            "client_secret": settings.COPERNICUS_CLIENT_SECRET
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, data=data)
                response.raise_for_status()
                result = response.json()
                self._token = result["access_token"]
                # Set expiry slightly early to be safe
                self._token_expiry = datetime.now() + timedelta(seconds=result["expires_in"] - 60)
                return self._token
            except Exception as e:
                logger.error(f"Failed to fetch Copernicus token: {e}")
                return None

copernicus_service = CopernicusService()
