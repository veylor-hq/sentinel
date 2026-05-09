import re
from typing import Annotated, Optional
from app.core.jwt import DecodedToken, FastJWT
from models.models import Location, MissionTemplate, Step, StepStatus, StepTemplate, User, Mission, MissionStatus
from datetime import datetime, timedelta
from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

class CreateMissionSchema(BaseModel):
    name: str

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


mission_router = APIRouter(prefix="/mission")

class CreateTemplateSchema(BaseModel):
    name: str
    description: Optional[str] = None


async def get_user_by_id(user_id: PydanticObjectId) -> Optional[User]:
    """Finds a user document by its PydanticObjectId."""
    user: Optional[User] = await User.get(user_id)
    return user

# ── Templates (must be before /{mission_id} to avoid routing conflict) ──────

@mission_router.get("/templates/")
async def list_mission_templates(
    include_steps: Annotated[Optional[bool], Query(alias="include_steps")] = False,
    include_locations: Annotated[Optional[bool], Query(alias="include_locations")] = False
):
    templates = await MissionTemplate.find_all().to_list()
    result = []
    for template in templates:
        template_data = {
            "mission_template": template,
            "step_templates": []
        }
        if include_steps:
            step_templates = await StepTemplate.find(StepTemplate.mission_template == template.id).sort(StepTemplate.order).to_list()
            if include_locations:
                template_data["step_templates"] = [
                    {
                        "_id": str(step_template.id),
                        **step_template.model_dump(exclude={"mission_template", "id"}),
                        "location": await Location.get(step_template.location) if step_template.location else None,
                    }
                    for step_template in step_templates
                ]
            else:
                template_data["step_templates"] = step_templates
        result.append(template_data)
    return result

@mission_router.post("/templates/")
async def create_blank_template(request: Request, payload: CreateTemplateSchema):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    mission_template = await MissionTemplate(
        name=payload.name,
        tags=[]
    ).insert()
    return {"mission_template": mission_template, "step_templates": []}


class UpdateTemplateSchema(BaseModel):
    name: str

class CreateStepTemplateSchema(BaseModel):
    name: str
    step_type: str = "custom"
    order: Optional[int] = None
    duration_seconds: Optional[float] = None
    # Movement fields (lat/lon pairs for simplicity; stored as GeoJSONPoint on the backend)
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lon: Optional[float] = None
    route_waypoints: Optional[list] = None  # list of {lat, lon}

class UpdateStepTemplateSchema(BaseModel):
    name: Optional[str] = None
    step_type: Optional[str] = None
    order: Optional[int] = None
    duration_seconds: Optional[float] = None
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lon: Optional[float] = None
    route_waypoints: Optional[list] = None  # list of {lat, lon}


@mission_router.patch("/templates/{template_id}")
async def update_template(template_id: PydanticObjectId, request: Request, payload: UpdateTemplateSchema):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    tmpl = await MissionTemplate.get(template_id)
    if not tmpl:
        raise HTTPException(404, "Template not found")
    tmpl.name = payload.name
    await tmpl.save()
    return tmpl


@mission_router.delete("/templates/{template_id}")
async def delete_template(template_id: PydanticObjectId, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    tmpl = await MissionTemplate.get(template_id)
    if not tmpl:
        raise HTTPException(404, "Template not found")
    await StepTemplate.find(StepTemplate.mission_template == template_id).delete()
    await tmpl.delete()
    return {"ok": True}


@mission_router.get("/templates/{template_id}/steps/")
async def list_step_templates(template_id: PydanticObjectId, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    steps = await StepTemplate.find(StepTemplate.mission_template == template_id).sort(StepTemplate.order).to_list()
    return steps


@mission_router.post("/templates/{template_id}/steps/")
async def add_step_template(template_id: PydanticObjectId, request: Request, payload: CreateStepTemplateSchema):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    tmpl = await MissionTemplate.get(template_id)
    if not tmpl:
        raise HTTPException(404, "Template not found")
    existing = await StepTemplate.find(StepTemplate.mission_template == template_id).to_list()
    order = payload.order if payload.order is not None else len(existing) + 1

    from models.models import GeoJSONPoint as GeoPoint
    origin = GeoPoint(coordinates=[payload.origin_lon, payload.origin_lat]) if payload.origin_lat is not None and payload.origin_lon is not None else None
    destination = GeoPoint(coordinates=[payload.destination_lon, payload.destination_lat]) if payload.destination_lat is not None and payload.destination_lon is not None else None
    waypoints = [GeoPoint(coordinates=[w["lon"], w["lat"]]) for w in (payload.route_waypoints or [])]

    step = await StepTemplate(
        name=payload.name,
        step_type=payload.step_type,
        order=order,
        mission_template=template_id,
        end_time_offset=payload.duration_seconds,
        origin=origin,
        destination=destination,
        route_waypoints=waypoints
    ).insert()
    return step


@mission_router.patch("/templates/{template_id}/steps/{step_id}")
async def update_step_template(template_id: PydanticObjectId, step_id: PydanticObjectId, request: Request, payload: UpdateStepTemplateSchema):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    step = await StepTemplate.get(step_id)
    if not step or step.mission_template != template_id:
        raise HTTPException(404, "Step not found")
    if payload.name is not None:
        step.name = payload.name
    if payload.step_type is not None:
        step.step_type = payload.step_type
    if payload.order is not None:
        step.order = payload.order
    if payload.duration_seconds is not None:
        step.end_time_offset = payload.duration_seconds
    from models.models import GeoJSONPoint as GeoPoint
    if payload.origin_lat is not None and payload.origin_lon is not None:
        step.origin = GeoPoint(coordinates=[payload.origin_lon, payload.origin_lat])
    elif payload.origin_lat is None and payload.origin_lon is None and step.origin is not None:
        step.origin = None
    if payload.destination_lat is not None and payload.destination_lon is not None:
        step.destination = GeoPoint(coordinates=[payload.destination_lon, payload.destination_lat])
    elif payload.destination_lat is None and payload.destination_lon is None and step.destination is not None:
        step.destination = None
    if payload.route_waypoints is not None:
        step.route_waypoints = [GeoPoint(coordinates=[w["lon"], w["lat"]]) for w in payload.route_waypoints]
    await step.save()
    return step


@mission_router.delete("/templates/{template_id}/steps/{step_id}")
async def delete_step_template(template_id: PydanticObjectId, step_id: PydanticObjectId, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    step = await StepTemplate.get(step_id)
    if not step or step.mission_template != template_id:
        raise HTTPException(404, "Step not found")
    await step.delete()
    return {"ok": True}


# ── Missions ─────────────────────────────────────────────────────────────────

@mission_router.get("/")
async def get_missions(
    request: Request,
    status_filter: Annotated[Optional[MissionStatus], Query(alias="mission_status")] = None,
):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        print(token, user)
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


@mission_router.get("/{mission_id}/brief")
async def get_mission_brief(mission_id: PydanticObjectId, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")

    mission = await Mission.get(mission_id)
    if not mission:
        raise HTTPException(404, "Mission not found")

    if mission.operator != token.id:
        raise HTTPException(403, "Forbidden")

    steps = await Step.find(Step.mission_id == mission.id).sort(Step.order).to_list()
    from models.models import Route, RegionOfInterest, Asset, Note
    notes = await Note.find(Note.mission_id == mission.id).to_list()
    routes = await Route.find(Route.mission_id == mission.id).to_list()
    rois = await RegionOfInterest.find(RegionOfInterest.mission_id == mission.id).to_list()
    assets = await Asset.find({"_id": {"$in": mission.attached_assets}}).to_list()
    # For the asset picker: all assets the operator owns
    all_assets = await Asset.find(Asset.owner_id == token.id).to_list()
    # Resolve operator username
    operator_user = await User.get(mission.operator)
    operator_name = operator_user.username if operator_user else str(mission.operator)

    return {
        "mission": mission,
        "steps": steps,
        "notes": notes,
        "routes": routes,
        "rois": rois,
        "assets": assets,
        "all_assets": all_assets,
        "operator_name": operator_name,
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


class CreateStepSchema(BaseModel):
    name: str
    step_type: str = "custom"
    order: Optional[int] = None

class UpdateSummarySchema(BaseModel):
    summary: Optional[str] = None

@mission_router.post("/{mission_id}/steps/")
async def add_mission_step(mission_id: PydanticObjectId, request: Request, payload: CreateStepSchema):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    mission = await Mission.get(mission_id)
    if not mission or mission.operator != token.id:
        raise HTTPException(403, "Forbidden")
    existing = await Step.find(Step.mission_id == mission_id).to_list()
    order = payload.order if payload.order is not None else len(existing) + 1
    step = await Step(
        name=payload.name,
        step_type=payload.step_type,
        order=order,
        mission_id=mission_id
    ).insert()
    return step

@mission_router.put("/{mission_id}/summary")
async def update_mission_summary(mission_id: PydanticObjectId, request: Request, payload: UpdateSummarySchema):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    mission = await Mission.get(mission_id)
    if not mission or mission.operator != token.id:
        raise HTTPException(403, "Forbidden")
    mission.summary = payload.summary
    await mission.save()
    return mission


# ── Step progression ──────────────────────────────────────────────────────────

class UpdateStepSchema(BaseModel):
    status: Optional[str] = None
    asset_id: Optional[str] = None
    asset_label: Optional[str] = None
    clear_asset: bool = False

@mission_router.patch("/{mission_id}/steps/{step_id}")
async def update_mission_step(mission_id: PydanticObjectId, step_id: PydanticObjectId, request: Request, payload: UpdateStepSchema):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    mission = await Mission.get(mission_id)
    if not mission or mission.operator != token.id:
        raise HTTPException(403, "Forbidden")
    step = await Step.get(step_id)
    if not step or step.mission_id != mission_id:
        raise HTTPException(404, "Step not found")

    if payload.status is not None:
        from models.models import StepStatus as SS
        try:
            step.status = SS(payload.status)
            if payload.status == "active":
                step.actual_start = datetime.utcnow()
            elif payload.status in ("done", "skipped"):
                step.actual_end = datetime.utcnow()
        except ValueError:
            raise HTTPException(400, f"Invalid step status: {payload.status}")

    if payload.clear_asset:
        step.asset_id = None
        step.asset_label = None
    else:
        if payload.asset_id is not None:
            try:
                step.asset_id = PydanticObjectId(payload.asset_id)
            except Exception:
                raise HTTPException(400, "Invalid asset_id")
        if payload.asset_label is not None:
            step.asset_label = payload.asset_label

    await step.save()
    return step


# ── Mission asset attach/detach ───────────────────────────────────────────────

@mission_router.post("/{mission_id}/assets/{asset_id}")
async def attach_asset(mission_id: PydanticObjectId, asset_id: PydanticObjectId, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    mission = await Mission.get(mission_id)
    if not mission or mission.operator != token.id:
        raise HTTPException(403, "Forbidden")
    from models.models import Asset
    asset = await Asset.get(asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    if asset_id not in mission.attached_assets:
        mission.attached_assets.append(asset_id)
        await mission.save()
    return {"ok": True}

@mission_router.delete("/{mission_id}/assets/{asset_id}")
async def detach_asset(mission_id: PydanticObjectId, asset_id: PydanticObjectId, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    mission = await Mission.get(mission_id)
    if not mission or mission.operator != token.id:
        raise HTTPException(403, "Forbidden")
    mission.attached_assets = [a for a in mission.attached_assets if a != asset_id]
    await mission.save()
    return {"ok": True}


# ── Mission TODO items ────────────────────────────────────────────────────────

class AddTodoSchema(BaseModel):
    description: str

@mission_router.post("/{mission_id}/todos/")
async def add_todo(mission_id: PydanticObjectId, request: Request, payload: AddTodoSchema):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    mission = await Mission.get(mission_id)
    if not mission or mission.operator != token.id:
        raise HTTPException(403, "Forbidden")
    from models.models import ChecklistItem
    item = ChecklistItem(description=payload.description)
    mission.todo_items.append(item)
    await mission.save()
    return item

@mission_router.patch("/{mission_id}/todos/{todo_id}")
async def toggle_todo(mission_id: PydanticObjectId, todo_id: str, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    mission = await Mission.get(mission_id)
    if not mission or mission.operator != token.id:
        raise HTTPException(403, "Forbidden")
    for item in mission.todo_items:
        if item.id == todo_id:
            item.is_completed = not item.is_completed
            if item.is_completed:
                item.completed_at = datetime.utcnow()
            break
    await mission.save()
    return {"ok": True}

@mission_router.delete("/{mission_id}/todos/{todo_id}")
async def delete_todo(mission_id: PydanticObjectId, todo_id: str, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    mission = await Mission.get(mission_id)
    if not mission or mission.operator != token.id:
        raise HTTPException(403, "Forbidden")
    mission.todo_items = [i for i in mission.todo_items if i.id != todo_id]
    await mission.save()
    return {"ok": True}


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
        
    # Gating Logic: Cannot transition to WARM_UP or ACTIVE if checklists exist but are incomplete
    if new_state in [MissionStatus.WARM_UP, MissionStatus.ACTIVE]:
        if mission.checklists:
            incomplete = [item for item in mission.checklists if not item.is_completed]
            if incomplete:
                raise HTTPException(400, "Cannot transition: Mandatory pre-flight checklists are incomplete.")

    mission.status = new_state
    await mission.save()

    return mission

@mission_router.put("/{mission_id}/checklist/{item_id}")
async def toggle_checklist_item(
    mission_id: PydanticObjectId,
    item_id: str,
    request: Request,
    completed: Annotated[bool, Query(alias="completed")]
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
        
    found = False
    for item in mission.checklists:
        if item.id == item_id:
            item.is_completed = completed
            item.completed_at = datetime.utcnow() if completed else None
            item.completed_by = user.id if completed else None
            found = True
            break
            
    if not found:
        raise HTTPException(404, "Checklist item not found")
        
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


@mission_router.post("/{mission_template_id}/from_template")
async def create_mission_from_template(
    mission_template_id: PydanticObjectId,
    request: Request,
    fast_start: Annotated[bool, Query(alias="fast_start")] = False
):
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
        operator=user.id,
        start_time=datetime.utcnow() if fast_start else None,
        status=MissionStatus.ACTIVE if fast_start else MissionStatus.PLANNED
    ).insert()

    # Copy steps preserving order
    step_templates = await StepTemplate.find(StepTemplate.mission_template == mission_template.id).sort(StepTemplate.order).to_list()
    for step_template in step_templates:
        await Step(
            **step_template.model_dump(exclude={"id", "mission_template"}),
            mission_id=mission.id,
            planned_start=mission.start_time + timedelta(seconds=step_template.start_time_offset) if mission.start_time and step_template.start_time_offset is not None else None,
            status=StepStatus.ACTIVE if fast_start and step_template.order == 1 else StepStatus.PLANNED
        ).insert()

    return mission


# (list_mission_templates moved to top of file to avoid /{mission_id} conflict)