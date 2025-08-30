from typing import Annotated, Optional
from app.core.jwt import DecodedToken, FastJWT
from models.models import User, Mission, MissionStatus
from app.core.password_utils import get_password_hash, verify_password
from datetime import datetime
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field


class CreateMissionSchema(BaseModel):
    name: str

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


mission_router = APIRouter(prefix="/mission")

from typing import Optional
from beanie import PydanticObjectId


async def get_user_by_id(user_id: PydanticObjectId) -> Optional[User]:
    """Finds a user document by its PydanticObjectId."""
    user: Optional[User] = await User.get(user_id)
    return user

@mission_router.get("/")
async def get_missions(
    request: Request,
    status_filter: Annotated[Optional[MissionStatus], Query(alias="mission_status")] = None,
):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")

    filters = [Mission.operator == token.id]
    if status_filter is not None:
        filters.append(Mission.status == status_filter)

    return await Mission.find(*filters).to_list()


@mission_router.get("/{mission_id}")
async def get_mission(mission_id: PydanticObjectId, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")

    mission = await Mission.get(mission_id)
    if not mission:
        raise HTTPException(404, "Mission not found")

    if mission.operator != token.id:
        raise HTTPException(403, "Forbidden")

    return mission


@mission_router.post("/")
async def new_mission(request: Request, payload: CreateMissionSchema):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user: Optional[User] = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    
    if await Mission.find_one({
        "name": payload.name,
        "operator": token.id
    }):
        raise HTTPException(400, "Mission Alredy Exists")

    mission = await Mission(
        **payload.model_dump(),
        operator=token.id
    ).insert()


    return mission