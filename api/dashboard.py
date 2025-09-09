from app.core.jwt import DecodedToken, FastJWT
from models.models import Mission, Step, User
from app.core.password_utils import get_password_hash, verify_password
from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field


dashboard_router = APIRouter(prefix="/dashboard")


@dashboard_router.get("/")
async def dashboard_event(request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    
    missions = []
    active_missions = await Mission.find(Mission.operator == user.id, Mission.status == "active").to_list()
    for mission in active_missions:
        _mission = {
            "id": str(mission.id),
            "name": mission.name,
            "status": mission.status,
            "steps": []
        }
        step = await Step.find_one(Step.mission_id == mission.id, Step.status == "active")
        if step:
            _mission["steps"].append({
                "name": step.name,
                "order": step.order,
            })
        missions.append(_mission)

    return {
        "message": "Dashboard endpoint",
        "user": {
            "name": user.username,
            "id": str(user.id)
        },
        "active_missions": missions
    }