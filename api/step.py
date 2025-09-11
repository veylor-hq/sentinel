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

    if mission.operator != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create step for this mission")

    if mission.status in [MissionStatus.COMPLETED, MissionStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Mission is not active")

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


@step_router.patch("/{step_id}")
async def change_step_status(step_id: PydanticObjectId, status: StepStatus):
    step = await Step.get(step_id)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    step.status = status
    await step.save()
    return step


@step_router.post("/proceed/{mission_id}")
async def proceed_mission_step(mission_id: PydanticObjectId):
    mission = await Mission.get(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    if mission.status in [MissionStatus.COMPLETED, MissionStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Mission is not active")

    if mission.status == MissionStatus.PLANNED:
        mission.status = MissionStatus.ACTIVE
        mission.start_time = datetime.utcnow()
        await mission.save()

    steps = await Step.find(Step.mission_id == mission.id).sort(Step.order).to_list()
    if not steps:
        raise HTTPException(status_code=400, detail="No steps in the mission")

    active_step = next((s for s in steps if s.status == StepStatus.ACTIVE), None)
    if active_step:
        active_step.status = StepStatus.DONE
        active_step.actual_end = datetime.utcnow()
        await active_step.save()
        next_step_index = steps.index(active_step) + 1
    else:
        next_step_index = 0

    if next_step_index < len(steps):
        next_step = steps[next_step_index]
        next_step.status = StepStatus.ACTIVE
        next_step.actual_start = datetime.utcnow()
        await next_step.save()
    else:
        mission.status = MissionStatus.COMPLETED
        mission.end_time = datetime.utcnow()
        await mission.save()

    return {
        "mission": mission,
        "active_step": next_step if next_step_index < len(steps) else None
    }