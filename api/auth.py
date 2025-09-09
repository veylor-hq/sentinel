from h11 import Request
from app.core.jwt import DecodedToken, FastJWT
from models.models import User
from app.core.password_utils import get_password_hash, verify_password
from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

dashboard_router = APIRouter(prefix="/dashboard")

@dashboard_router.get("/")
async def dashboard_event(request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        print(token, user)
        raise HTTPException(401, "Unauthorized")


    return {
        "message": "Dashboard endpoint",
        "user": {
            "name": user.username,
            "id": str(user.id)
        }
    }