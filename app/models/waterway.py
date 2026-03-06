from sqlalchemy import Column, Integer, String, Float, DateTime, func
from geoalchemy2 import Geometry
from app.db.base import Base

class WaterwayObservation(Base):
    __tablename__ = "waterway_observations"

    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String, index=True)
    # Using SRID 4326 (WGS 84 - standard for GPS/web)
    # Changed from POINT to MULTILINESTRING to support 1km segments
    geom = Column(Geometry('MULTILINESTRING', srid=4326))
    
    # Copernicus data (e.g. Normalized Difference Water Index - NDWI)
    hydration_index = Column(Float, nullable=True)
    turbidity = Column(Float, nullable=True)
    
    # Weather/Risk data
    runoff_risk_score = Column(Float, nullable=True) # 0.0 to 1.0
    sewage_spill_active = Column(Integer, default=0) # 0 or 1
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
