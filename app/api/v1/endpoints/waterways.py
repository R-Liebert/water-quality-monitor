from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.db.session import get_db
from app.models.waterway import WaterwayObservation

router = APIRouter()

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