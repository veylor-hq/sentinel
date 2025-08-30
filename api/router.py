from datetime import datetime
from typing import Optional
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from api.auth import auth_router
from api.mission import mission_router
from app.core.jwt import FastJWT


router = APIRouter(prefix="/api")
public_router = APIRouter(prefix="/public")
private_router = APIRouter(prefix="/private")


public_router.include_router(auth_router)
private_router.include_router(mission_router, dependencies=[Depends(FastJWT().login_required)])

router.include_router(public_router)
router.include_router(private_router)


@router.get("/")
def api_router():
    return {
        "status": "healthy",
        "message": "Refer to documentation for usage help."
    }