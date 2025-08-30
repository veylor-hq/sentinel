from typing import Annotated, Optional
from app.core.jwt import DecodedToken, FastJWT
from models.models import Location, MissionTemplate, Step, StepTemplate, User, Mission, MissionStatus
from datetime import datetime
from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel


class CreateMissionSchema(BaseModel):
    name: str

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


mission_router = APIRouter(prefix="/mission")


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
async def get_mission(
    mission_id: PydanticObjectId,
    request: Request,
    include_steps: Annotated[Optional[bool], Query(alias="include_steps")] = False,
    include_locations: Annotated[Optional[bool], Query(alias="include_locations")] = False,
):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")

    mission = await Mission.get(mission_id)
    if not mission:
        raise HTTPException(404, "Mission not found")

    if mission.operator != token.id:
        raise HTTPException(403, "Forbidden")

    steps_data = []
    if include_steps:
        steps = await Step.find(Step.mission_id == mission.id).to_list()
        if include_locations:
            steps_data = [
                {
                    "_id": str(step.id),
                    **step.model_dump(exclude={"mission_id", "id"}),
                    "location": await Location.get(step.location) if step.location else None,
                }
                for step in steps
            ]
        else:
            steps_data = steps

    return {
        "mission": mission,
        "steps": steps_data
    }


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


@mission_router.patch("/{mission_id}")
async def change_mission_state(
    mission_id: PydanticObjectId,
    request: Request,
    new_state: Annotated[MissionStatus, Query(alias="new_state")]
):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")

    mission = await Mission.get(mission_id)
    if not mission:
        raise HTTPException(404, "Mission not found")

    if mission.operator != token.id:
        raise HTTPException(403, "Forbidden")

    mission.status = new_state
    await mission.save()

    return mission


# make mission template from mission id, copy all steps into step templates
@mission_router.post("/{mission_id}/template")
async def create_mission_template(mission_id: PydanticObjectId, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")

    mission = await Mission.get(mission_id)
    if not mission:
        raise HTTPException(404, "Mission not found")

    if mission.operator != token.id:
        raise HTTPException(403, "Forbidden")

    mission_template = await MissionTemplate(
        name=mission.name,
        tags=mission.tags
    ).insert()

    steps = await Step.find(Step.mission_id == mission.id).to_list()
    step_templates = []
    for step in steps:
        step_template = await StepTemplate(
            **step.model_dump(exclude={"id", "mission_id", "actual_start", "actual_end", "status"}),
            mission_template=mission_template.id,
            start_time_offset=step.planned_start.timestamp() - mission.start_time.timestamp() if step.planned_start and mission.start_time else None,
            end_time_offset=step.planned_end.timestamp() - mission.start_time.timestamp() if step.planned_end and mission.start_time else None
        ).insert()
        step_templates.append(step_template)

    return {
        "mission_template": mission_template,
        "step_templates": step_templates
    }


# template to mission
import re

@mission_router.post("/{mission_template_id}/from_template")
async def create_mission_from_template(mission_template_id: PydanticObjectId, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")

    mission_template = await MissionTemplate.get(mission_template_id)
    if not mission_template:
        raise HTTPException(404, "Mission template not found")

    # Get all missions starting with template name
    existing_missions = await Mission.find(
        {"name": {"$regex": f"^{re.escape(mission_template.name)}"}}
    ).to_list()

    # Collect numeric suffixes
    numbers = []
    for m in existing_missions:
        match = re.match(rf"^{re.escape(mission_template.name)}-(\d+)$", m.name)
        if match:
            numbers.append(int(match.group(1)))
        elif m.name == mission_template.name:
            numbers.append(0)  # exact match counts as first duplicate

    next_number = max(numbers, default=-1) + 1

    # Assign new name
    mission_name = mission_template.name if next_number == 0 else f"{mission_template.name}-{next_number}"

    # Create the mission
    mission = await Mission(
        **mission_template.model_dump(exclude={"id", "name"}),
        name=mission_name,
        operator=user.id
    ).insert()

    # Copy steps preserving order
    step_templates = await StepTemplate.find(StepTemplate.mission_template == mission_template.id).sort(StepTemplate.order).to_list()
    for step_template in step_templates:
        await Step(
            **step_template.model_dump(exclude={"id", "mission_template"}),
            mission_id=mission.id
        ).insert()

    return mission
