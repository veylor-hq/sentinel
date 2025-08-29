from datetime import datetime
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from api.auth import auth_router

router = APIRouter(prefix="/api")


@router.get("/")
def api_router():
    return {
        "status": "healthy",
        "message": "Refer to documentation for usage help."
    }


router.include_router(auth_router)