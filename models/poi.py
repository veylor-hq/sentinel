from datetime import datetime
from typing import Optional, List
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from models.models import GeoJSONPoint
from pymongo import GEOSPHERE
from enum import Enum

class ThreatLevel(str, Enum):
    UNKNOWN = "unknown"
    LOW = "low"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"

class PointOfInterest(Document):
    name: str
    poi_type: str = "location"
    description: Optional[str] = None
    location: GeoJSONPoint
    threat_level: ThreatLevel = ThreatLevel.UNKNOWN
    reported_by: PydanticObjectId
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list)
    mission_id: Optional[PydanticObjectId] = None
    registry_asset_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Optional link back to Intelligence Registry row.",
    )
    
    class Settings:
        name = "pois"
        indexes = [
            [("location", GEOSPHERE)]
        ]
