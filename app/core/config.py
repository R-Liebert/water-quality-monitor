from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Water Quality Monitoring API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Postgres
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/water_quality"
    
    # Celery/Redis
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # API Keys (Loaded automatically from .env)
    COPERNICUS_CLIENT_ID: Optional[str] = None
    COPERNICUS_CLIENT_SECRET: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    EA_API_KEY: Optional[str] = None
    
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    
    OPEN_METEO_URL: str = "https://api.open-meteo.com/v1/forecast"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()