from datetime import datetime, timedelta
from typing import List, Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.jwt import FastJWT, DecodedToken
from models.models import Asset, AssetCategory, MaintenanceSchedule, User


maintenance_router = APIRouter(prefix="/maintenance", tags=["maintenance"])


class MaintenanceCreate(BaseModel):
    asset_id: PydanticObjectId
    title: str = "Maintenance"
    notes: str = ""
    next_due_at: datetime
    recurrence_interval_days: Optional[int] = Field(
        default=None,
        description="If set, next due date advances by this many days after each completion.",
    )


class MaintenanceUpdate(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    next_due_at: Optional[datetime] = None
    recurrence_interval_days: Optional[int] = None
    is_active: Optional[bool] = None


async def _load_maintainable_asset(asset_id: PydanticObjectId, owner_id: PydanticObjectId) -> Asset:
    asset = await Asset.get(asset_id)
    if not asset or asset.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.category == AssetCategory.PERSON:
        raise HTTPException(
            status_code=400,
            detail="Maintenance schedules cannot be attached to People records",
        )
    return asset


@maintenance_router.get("/", response_model=List[MaintenanceSchedule])
async def list_maintenance(request: Request, active_only: bool = True):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if active_only:
        q = MaintenanceSchedule.find(
            MaintenanceSchedule.owner_id == user.id,
            MaintenanceSchedule.is_active == True,
        )
    else:
        q = MaintenanceSchedule.find(MaintenanceSchedule.owner_id == user.id)
    return await q.sort(MaintenanceSchedule.next_due_at).to_list()


@maintenance_router.post("/", response_model=MaintenanceSchedule)
async def create_maintenance(payload: MaintenanceCreate, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    await _load_maintainable_asset(payload.asset_id, user.id)
    row = MaintenanceSchedule(
        owner_id=user.id,
        asset_id=payload.asset_id,
        title=payload.title,
        notes=payload.notes,
        next_due_at=payload.next_due_at,
        recurrence_interval_days=payload.recurrence_interval_days,
    )
    await row.insert()
    return row


@maintenance_router.patch("/{schedule_id}", response_model=MaintenanceSchedule)
async def update_maintenance(
    schedule_id: PydanticObjectId,
    payload: MaintenanceUpdate,
    request: Request,
):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    row = await MaintenanceSchedule.get(schedule_id)
    if not row or row.owner_id != user.id:
        raise HTTPException(404, "Schedule not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    await row.save()
    return row


@maintenance_router.post("/{schedule_id}/complete", response_model=MaintenanceSchedule)
async def complete_maintenance(schedule_id: PydanticObjectId, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    row = await MaintenanceSchedule.get(schedule_id)
    if not row or row.owner_id != user.id:
        raise HTTPException(404, "Schedule not found")
    now = datetime.utcnow()
    row.last_completed_at = now
    if row.recurrence_interval_days:
        row.next_due_at = now + timedelta(days=row.recurrence_interval_days)
        row.is_active = True
    else:
        row.is_active = False
    await row.save()
    return row


@maintenance_router.delete("/{schedule_id}", status_code=204)
async def delete_maintenance(schedule_id: PydanticObjectId, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    row = await MaintenanceSchedule.get(schedule_id)
    if not row or row.owner_id != user.id:
        raise HTTPException(404, "Schedule not found")
    await row.delete()
    return None
