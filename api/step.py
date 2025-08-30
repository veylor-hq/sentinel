from typing import Annotated, Optional
from app.core.jwt import DecodedToken, FastJWT
from models.models import Location, StepType, User, Mission, MissionStatus, Step, StepStatus
from datetime import datetime
from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel


class CreateStepSchema(BaseModel):
    order: int
    name: str

    mission_id: PydanticObjectId

    step_type: Optional[StepType] = StepType.CUSTOM
    status: Optional[StepStatus] = StepStatus.PLANNED

    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None

    location: Optional[PydanticObjectId] = None


step_router = APIRouter(prefix="/step")


@step_router.get("/")
async def list_steps():
    steps = await Step.find_all().to_list()
    return steps


@step_router.post("/")
async def create_step(request: Request, payload: CreateStepSchema):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    
    mission = await Mission.get(payload.mission_id)
    if not mission:
        raise HTTPException(status_code=400, detail="Mission does not exist")
    
    if mission.status in [MissionStatus.COMPLETED, MissionStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Mission is not active")

    if mission.operator != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create step for this mission")

    if payload.location:
        if not await Location.get(payload.location):
            raise HTTPException(status_code=400, detail="Location does not exist")
        
    existing_step = await Step.find_one(
        Step.mission_id == mission.id,
        Step.order == payload.order,
    )
    if existing_step:
        raise HTTPException(status_code=400, detail="Step already exists")

    step = Step(
        **payload.model_dump(),
    )
    await step.insert()
    return step


@step_router.get("/{step_id}")
async def get_step(step_id: PydanticObjectId):
    step = await Step.get(step_id)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    return step

