# app/models.py
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import uuid4

from beanie import Document, Indexed, Link
from pydantic import BaseModel, Field, validator


# ---------- Enums ----------

class MissionStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


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


class AssetStatus(str, Enum):
    AVAILABLE = "available"
    DEPLOYED = "deployed"
    LOST = "lost"
    MAINTENANCE = "maintenance"


# ---------- Mixins / Common ----------

class TimestampMixin(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def touch(self):
        self.updated_at = datetime.utcnow()


class GeoPoint(BaseModel):
    lat: float
    lon: float


class ChecklistItem(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    text: str
    required: bool = True
    done: bool = False


# ---------- Steps & Alterations (Embedded) ----------

class Alteration(BaseModel):
    """
    A contingency/branch for a step. If condition holds,
    the client can switch to this plan (often a single replacement step).
    """
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    condition: str  # e.g., "If train cancelled" / "If >20m delay"
    # Replacement plan can be one or multiple steps
    replace_with: List["Step"] = Field(default_factory=list)


class Step(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    order: int = 0
    name: str
    type: StepType = StepType.CUSTOM
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    status: StepStatus = StepStatus.PLANNED
    checklist: List[ChecklistItem] = Field(default_factory=list)
    linked_asset_ids: List[str] = Field(default_factory=list)  # keep simple string IDs for speed
    location: Optional[GeoPoint] = None
    # Traccar/GPS association (optional) – e.g., deviceId or track segment id
    track_ref: Optional[str] = None
    alterations: List[Alteration] = Field(default_factory=list)

    @validator("actual_end")
    def actual_end_after_start(cls, v, values):
        if v and values.get("actual_start") and v < values["actual_start"]:
            raise ValueError("actual_end must be >= actual_start")
        return v

    @validator("planned_end")
    def planned_end_after_start(cls, v, values):
        if v and values.get("planned_start") and v < values["planned_start"]:
            raise ValueError("planned_end must be >= planned_start")
        return v


Alteration.update_forward_refs()
Step.update_forward_refs()


# ---------- Core Documents ----------

class Asset(Document, TimestampMixin):
    name: Indexed(str)  # fast search
    status: AssetStatus = AssetStatus.AVAILABLE
    notes: Optional[str] = None
    # Optional tags (e.g., "comm", "compute", "id-doc")
    tags: List[str] = Field(default_factory=list)
    # Optional serials/ids to help identify
    identifiers: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "assets"
        indexes = ["name", "status", [("tags", 1)]]

    class Config:
        orm_mode = True


class Note(Document, TimestampMixin):
    """
    Free-form field notes / AAR snippets. Linked to a mission, optionally a step.
    """
    mission_id: Indexed(str)
    step_id: Optional[str] = None
    content: str

    class Settings:
        name = "notes"
        indexes = ["mission_id", "step_id", [("created_at", -1)]]

    class Config:
        orm_mode = True


class TemplateStep(BaseModel):
    """
    Lightweight template step (no actual times).
    """
    id: str = Field(default_factory=lambda: uuid4().hex)
    order: int = 0
    name: str
    type: StepType = StepType.CUSTOM
    checklist: List[ChecklistItem] = Field(default_factory=list)
    linked_asset_names: List[str] = Field(default_factory=list)
    location: Optional[GeoPoint] = None
    alterations: List[Alteration] = Field(default_factory=list)


class Template(Document, TimestampMixin):
    """
    Mission template with default steps & assets.
    """
    name: Indexed(str)
    description: Optional[str] = None
    default_asset_names: List[str] = Field(default_factory=list)
    default_steps: List[TemplateStep] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    class Settings:
        name = "templates"
        indexes = ["name", [("tags", 1)]]

    class Config:
        orm_mode = True


class Mission(Document, TimestampMixin):
    """
    The main unit: a mission with embedded steps and linked assets.
    """
    name: Indexed(str)
    status: MissionStatus = MissionStatus.PLANNED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # If created from a template, keep reference-for-traceability
    template_id: Optional[str] = None

    # Embedded steps for atomic timeline updates
    steps: List[Step] = Field(default_factory=list)

    # Link physical assets (resolved lazily)
    # Keep both: quick lookup by id string AND optional Link for joins if you want
    asset_ids: List[str] = Field(default_factory=list)
    assets: Optional[List[Link[Asset]]] = None

    # High-level notes or mission metadata
    summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # Optional geospatial anchor (e.g., primary AO)
    ao_center: Optional[GeoPoint] = None

    class Settings:
        name = "missions"
        indexes = [
            "name",
            "status",
            [("start_time", 1)],
            [("tags", 1)],
        ]

    class Config:
        orm_mode = True

    # ---------- Convenience helpers (optional) ----------
    def start(self):
        self.status = MissionStatus.ACTIVE
        self.touch()

    def complete(self):
        self.status = MissionStatus.COMPLETED
        self.touch()

    def cancel(self):
        self.status = MissionStatus.CANCELLED
        self.touch()

    def add_step(self, step: Step):
        self.steps.append(step)
        # maintain sequential order if not set
        if step.order == 0:
            step.order = len(self.steps)
        self.touch()

    def mark_step_status(self, step_id: str, status: StepStatus):
        for s in self.steps:
            if s.id == step_id:
                s.status = status
                break
        self.touch()

    def attach_asset_ids(self, *asset_ids: str):
        for aid in asset_ids:
            if aid not in self.asset_ids:
                self.asset_ids.append(aid)
        self.touch()
