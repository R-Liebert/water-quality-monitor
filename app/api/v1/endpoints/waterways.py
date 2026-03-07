from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.db.session import get_db
from app.models.waterway import WaterwayObservation

router = APIRouter()

@router.get("/viewport")
async def get_high_res_viewport(
    min_lat: float, max_lat: float, min_lng: float, max_lng: float,
    zoom: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Dynamically generates river segments for the current viewport.
    Resolution increases as the user zooms in.
    """
    # Determine segment length based on zoom (IN METERS for SRID 4326)
    if zoom >= 15:
        seg_len = 25      # 25m segments
    elif zoom >= 13:
        seg_len = 100     # 100m segments
    else:
        seg_len = 500     # 500m segments

    # Raw SQL for heavy spatial lifting in PostGIS
    # ST_Segmentize uses meters for geographic coordinates (4326)
    sql = text("""
        WITH clipped_rivers AS (
            SELECT location_name as name, ST_Intersection(geom, ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326)) as geom
            FROM waterway_observations
            WHERE geom && ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326)
        ),
        segmented AS (
            SELECT name, (ST_DumpSegments(ST_Segmentize(geom::geography, :seg_len)::geometry)).geom as segment_geom
            FROM clipped_rivers
            WHERE geom IS NOT NULL
        )
        SELECT jsonb_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(jsonb_agg(
                jsonb_build_object(
                    'type', 'Feature',
                    'geometry', ST_AsGeoJSON(segment_geom)::jsonb,
                    'properties', jsonb_build_object(
                        'name', name,
                        'status', 'normal',
                        'risk_score', 0.1,
                        'explanation', 'High-resolution telemetry active.'
                    )
                )
            ), '[]'::jsonb)
        )
        FROM segmented
    """)
    
    result = await db.execute(sql, {
        "min_lat": min_lat, "max_lat": max_lat, 
        "min_lng": min_lng, "max_lng": max_lng,
        "seg_len": seg_len
    })
    
    return result.scalar() or {"type": "FeatureCollection", "features": []}

@router.get("/status", response_model=list)
async def read_waterway_status(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    Retrieve current waterway observations.
    Currently returns raw database records. A proper GeoJSON serializer is recommended.
    """
    result = await db.execute(select(WaterwayObservation).offset(skip).limit(limit))
    observations = result.scalars().all()
    
    # Simple conversion for demo (in production use Pydantic schemas)
    return [
        {
            "id": obs.id,
            "location_name": obs.location_name,
            "hydration_index": obs.hydration_index,
            "turbidity": obs.turbidity,
            "runoff_risk_score": obs.runoff_risk_score,
            "sewage_spill_active": obs.sewage_spill_active,
            "timestamp": obs.timestamp.isoformat() if obs.timestamp else None
        }
        for obs in observations
    ]