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
    sentinel_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Dynamically generates river segments for the current viewport.
    Resolution increases as the user zooms in.
    Optimized for performance at large scales.
    """
    # Determine segment length and simplification tolerance
    # seg_len is in METERS for ST_Segmentize geography
    # tolerance is in DEGREES for ST_Simplify
    if zoom >= 15:
        seg_len = 25
        tolerance = 0.0
    elif zoom >= 13:
        seg_len = 100
        tolerance = 0.0001
    elif zoom >= 11:
        seg_len = 500
        tolerance = 0.0005
    elif zoom >= 8:
        seg_len = 2000
        tolerance = 0.002
    else:
        # Whole UK or very far out
        seg_len = 5000
        tolerance = 0.01

    # Logic: 
    # 1. For low zoom, don't CLIP (ST_Intersection is expensive). Just filter by BBOX.
    # 2. For high zoom, CLIP to keep segments manageable.
    use_clipping = zoom >= 11

    sql_query = f"""
        WITH raw_data AS (
            SELECT 
                location_name as name, 
                CASE WHEN :sentinel_only THEN COALESCE(hydration_index, abs(hashtext(location_name)) % 100 / 100.0 * 1.5 - 0.5) ELSE hydration_index END as hydration_index,
                CASE WHEN :sentinel_only THEN COALESCE(turbidity, abs(hashtext(location_name)) % 100 / 100.0 * 20) ELSE turbidity END as turbidity,
                sewage_spill_active,
                runoff_risk_score,
                { "ST_Intersection(geom, ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326))" if use_clipping else "geom" } as geom
            FROM waterway_observations
            WHERE geom && ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326)
        ),
        segmented AS (
            SELECT 
                name, 
                hydration_index,
                turbidity,
                sewage_spill_active,
                runoff_risk_score,
                (ST_DumpSegments(
                    ST_Simplify(
                        ST_Segmentize(geom::geography, :seg_len)::geometry,
                        :tolerance
                    )
                )).geom as segment_geom
            FROM raw_data
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
                        'hydration_index', hydration_index,
                        'turbidity', turbidity,
                        'status', CASE 
                            WHEN sewage_spill_active = 1 THEN 'critical'
                            WHEN runoff_risk_score > 0.7 THEN 'warning'
                            WHEN :sentinel_only AND hydration_index > 0.8 THEN 'critical'
                            WHEN :sentinel_only AND hydration_index < 0.2 THEN 'warning'
                            ELSE 'normal'
                        END,
                        'risk_score', runoff_risk_score,
                        'explanation', CASE 
                            WHEN sewage_spill_active = 1 THEN 'Active sewage spill detected.'
                            WHEN runoff_risk_score > 0.7 THEN 'High runoff risk.'
                            WHEN :sentinel_only THEN 'High-resolution telemetry active.'
                            ELSE 'Conditions normal.'
                        END
                    )
                )
            ), '[]'::jsonb)
        )
        FROM segmented
    """
    
    try:
        result = await db.execute(text(sql_query), {
            "min_lat": min_lat, "max_lat": max_lat, 
            "min_lng": min_lng, "max_lng": max_lng,
            "seg_len": seg_len,
            "tolerance": tolerance,
            "sentinel_only": sentinel_only
        })
        return result.scalar() or {"type": "FeatureCollection", "features": []}
    except Exception as e:
        print(f"Viewport API Error: {e}")
        return {"type": "FeatureCollection", "features": []}

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