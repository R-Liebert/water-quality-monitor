from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.api.v1.endpoints import waterways, config, copernicus

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="Professional Water Quality Monitoring System (UK Demo)"
)

# Include routers
app.include_router(
    waterways.router,
    prefix=f"{settings.API_V1_STR}/waterways",
    tags=["waterways"]
)

app.include_router(
    config.router,
    prefix=f"{settings.API_V1_STR}/config",
    tags=["config"]
)

app.include_router(
    copernicus.router,
    prefix=f"{settings.API_V1_STR}/copernicus",
    tags=["copernicus"]
)

# Serve the static frontend files
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/")
def read_root():
    return RedirectResponse(url="/frontend/index.html")