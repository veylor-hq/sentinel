from typing import Optional
from app.core.jwt import DecodedToken, FastJWT
from models.models import User, Mission, Step, Location, Note
from app.core.password_utils import get_password_hash, verify_password
from datetime import datetime
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
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


@mission_router.post("/")
async def new_mission(request: Request, payload: CreateMissionSchema):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    print(token)
    user: Optional[User] = await User.get(token.id)
    print(user)
    if not user:
        raise HTTPException(401, "Unauthorized")
    
    if await Mission.find_one({
        "name": payload.name,
        "operator": token.id
    }):
        raise HTTPException(400, "Mission Alredy Exists")

    mission = await Mission(
        **payload,
        operator=token.id
    ).insert()


    return mission