# app/models.py
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import uuid4

from beanie import Document, Indexed, Link, PydanticObjectId
from pydantic import BaseModel, Field, validator


class User(Document):
    username: str
    password: str


class MissionStatus(str, Enum):
    PLANNED = "planned"
    DELAYED = "delayed"
    CANCELLED = "cancelled"
    ACTIVE = "active"
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


class GeoPoint(BaseModel):
    lat: float
    lon: float


class Location(Document):
    name: str
    location_type: LocationType = LocationType.GENERIC
    coordinates: GeoPoint


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

class MissionTemplate(Document):
    name: str

class Mission(Document):
    name: str
    operator: PydanticObjectId

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    status: MissionStatus = MissionStatus.PLANNED

    # High-level notes or mission metadata
    summary: Optional[str] = None
    tags: Optional[list] = []


class MissionTemplate(Document):
    name: str

    tags: Optional[list] = []

class StepTemplate(Document):
    name: str
    order: int = 0
    mission_template: PydanticObjectId

    start_time_offset: Optional[float] = None
    end_time_offset: Optional[float] = None

    step_type: StepType = StepType.CUSTOM
    location: Optional[PydanticObjectId] = None 