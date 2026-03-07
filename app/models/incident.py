from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, func
from geoalchemy2 import Geometry
from app.db.base import Base

class EnvironmentalIncident(Base):
    """
    Represents an environmental event such as a Sewage Spill (CSO discharge), 
    Industrial Leak, or Agricultural Runoff event.
    """
    __tablename__ = "environmental_incidents"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String, index=True) # e.g., 'sewage_spill', 'industrial_discharge'
    severity = Column(String) # e.g., 'high', 'medium', 'low'
    
    # Spatial location of the incident
    geom = Column(Geometry('POINT', srid=4326))
    
    # Metadata
    company_name = Column(String, nullable=True) # e.g., Thames Water
    duration_hours = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    
    reported_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Optionally, we could link this to the closest 1km river segment
    # closest_segment_id = Column(String, index=True) 
