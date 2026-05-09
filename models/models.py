# app/models.py
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from uuid import uuid4

from pymongo import GEOSPHERE
from beanie import Document, Indexed, Link, PydanticObjectId
from pydantic import BaseModel, Field, model_validator


class User(Document):
    username: str
    password: str
    email: Optional[str] = None
    email_verified: bool = False


class MissionStatus(str, Enum):
    PLANNED = "planned"
    WARM_UP = "warm_up"
    ACTIVE = "active"
    DELAYED = "delayed"
    CANCELLED = "cancelled"
    DEBRIEF = "debrief"
    COMPLETED = "completed"


class StepType(str, Enum):
    MOVEMENT = "movement"
    ACTIVITY = "activity"
    WAITING = "waiting"
    SOCIAL = "social"
    CUSTOM = "custom"


class StepStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    DONE = "done"
    SKIPPED = "skipped"
    ALTERED = "altered"


class LocationType(str, Enum):
    GENERIC = "generic"


class GeoJSONPoint(BaseModel):
    type: str = "Point"
    coordinates: List[float]  # [longitude, latitude]


class GeoJSONPolygon(BaseModel):
    type: str = "Polygon"
    coordinates: List[List[List[float]]]


class GeoJSONLineString(BaseModel):
    type: str = "LineString"
    coordinates: List[List[float]]


class Location(Document):
    name: str
    location_type: LocationType = LocationType.GENERIC
    # Legacy DB rows may exist without geometry; geo queries skip them until repaired.
    geometry: Optional[Union[GeoJSONPoint, GeoJSONPolygon, GeoJSONLineString]] = None

    class Settings:
        indexes = [
            [("geometry", GEOSPHERE)]
        ]


class RegionOfInterest(Document):
    name: str
    mission_id: Optional[PydanticObjectId] = None
    geometry: GeoJSONPolygon
    
    class Settings:
        indexes = [
            [("geometry", GEOSPHERE)]
        ]


class SITREP(Document):
    operator_id: PydanticObjectId
    mission_id: Optional[PydanticObjectId] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    location: GeoJSONPoint
    description: str
    status: str = "PENDING"        # PENDING / ACKNOWLEDGED / RESOLVED
    severity: str = "ROUTINE"      # ROUTINE / SIGNIFICANT / URGENT / FLASH

    # Military fields
    unit: Optional[str] = None           # Callsign / unit reporting
    grid_ref: Optional[str] = None       # MGRS or grid ref string
    sitrep_type: Optional[str] = None    # CONTACT / CASUALTY / LOGSTAT / MEDEVAC / OTHER
    contact_type: Optional[str] = None   # TROOPS / VEH / UAS / IED / etc
    assets_involved: Optional[str] = None
    action_taken: Optional[str] = None

    class Settings:
        indexes = [
            [("location", GEOSPHERE)]
        ]


class ChecklistItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    completed_by: Optional[PydanticObjectId] = None


class Note(Document):
    """
    Free-form field notes / AAR snippets. Linked to a mission, optionally a step.
    """
    mission_id: PydanticObjectId
    step_id: Optional[PydanticObjectId] = None
    content: str


class Step(Document):
    order: int = 0
    name: str

    mission_id: PydanticObjectId

    step_type: StepType = StepType.CUSTOM

    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None

    status: StepStatus = StepStatus.PLANNED

    location: Optional[PydanticObjectId] = None
    checklists: List[ChecklistItem] = Field(default_factory=list)

    # Movement / asset link
    asset_id: Optional[PydanticObjectId] = None
    asset_label: Optional[str] = None  # free-text fallback


class MissionTemplate(Document):
    name: str

class Mission(Document):
    name: str
    operator: PydanticObjectId

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    status: MissionStatus = MissionStatus.PLANNED

    summary: Optional[str] = None
    tags: Optional[list] = []

    checklists: List[ChecklistItem] = Field(default_factory=list)
    attached_assets: List[PydanticObjectId] = Field(default_factory=list)
    todo_items: List[ChecklistItem] = Field(default_factory=list)


class Waypoint(BaseModel):
    index: int
    location: GeoJSONPoint
    action_point_step_id: Optional[PydanticObjectId] = None

class Route(Document):
    mission_id: PydanticObjectId
    waypoints: List[Waypoint]
    name: str


class AssetCategory(str, Enum):
    PERSON = "person"
    LOCATION = "location"
    TRANSPORT = "transport"
    ITEM = "item"
    GEAR = "gear"


class AssetLink(BaseModel):
    """Cross-link between registry records (any category)."""

    relation: str
    target_id: PydanticObjectId
    target_category: AssetCategory
    label: Optional[str] = None


class Asset(Document):
    """
    Unified operational registry: people, sites, transport, items, and gear.
    Prefer `category`; legacy MongoDB docs may only have `asset_type` (excluded from API output).
    """

    name: str
    category: AssetCategory = AssetCategory.TRANSPORT
    owner_id: PydanticObjectId
    details: Dict[str, Any] = Field(default_factory=dict)
    links: List[AssetLink] = Field(default_factory=list)
    """Mission `Location` document (steps / geometry library) — optional."""
    map_location_id: Optional[PydanticObjectId] = None
    """Map marker (POI / mark on COP) — optional; preferred user-facing map link."""
    poi_id: Optional[PydanticObjectId] = None
    asset_type: Optional[str] = Field(default=None, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def _category_from_legacy_asset_type(cls, data: Any):
        if not isinstance(data, dict):
            return data
        cat = data.get("category")
        if cat is None or cat == "":
            legacy = data.get("asset_type")
            if legacy is not None:
                m = {"vehicle": "transport", "person": "person", "equipment": "item"}
                data["category"] = m.get(str(legacy), "transport")
        return data


class MaintenanceSchedule(Document):
    """
    Service / inspection plan for a registry asset (not used for People).
    """

    owner_id: PydanticObjectId
    asset_id: PydanticObjectId
    title: str = "Maintenance"
    notes: str = ""
    next_due_at: datetime
    recurrence_interval_days: Optional[int] = None
    last_completed_at: Optional[datetime] = None
    is_active: bool = True


class TelemetryState(Document):
    asset_id: PydanticObjectId
    last_location: GeoJSONPoint
    heading: Optional[float] = None
    speed: Optional[float] = None
    battery: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        indexes = [
            [("last_location", GEOSPHERE)]
        ]


class MissionTemplate(Document):
    name: str
    tags: Optional[list] = []
    todo_items: List[ChecklistItem] = Field(default_factory=list)


class StepTemplate(Document):
    name: str
    order: int = 0
    mission_template: PydanticObjectId

    start_time_offset: Optional[float] = None
    end_time_offset: Optional[float] = None

    step_type: StepType = StepType.CUSTOM
    location: Optional[PydanticObjectId] = None

    # asset link (for movement steps)
    asset_id: Optional[PydanticObjectId] = None
    asset_label: Optional[str] = None

    # Movement phase fields
    origin: Optional[GeoJSONPoint] = None          # Point A
    destination: Optional[GeoJSONPoint] = None     # Point B
    route_waypoints: List[GeoJSONPoint] = Field(default_factory=list)  # custom route points
