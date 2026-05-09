from datetime import datetime
from typing import Optional
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from api.auth import auth_router
from api.mission import mission_router
from api.location import location_router
from api.step import step_router
from api.dashboard import dashboard_router
from api.profile import profile_router
from app.core.jwt import FastJWT


router = APIRouter(prefix="/api")
public_router = APIRouter(prefix="/public")
private_router = APIRouter(prefix="/private")


from api.ws import ws_router
from api.aar import aar_router
from api.ingress import ingress_router
from api.federation import federation_router
from api.yjs import yjs_router
from api.poi import poi_router
from api.sitrep import sitrep_router
from api.asset import asset_router
from api.maintenance import maintenance_router

public_router.include_router(auth_router)
public_router.include_router(ingress_router)
public_router.include_router(federation_router)

private_router.include_router(mission_router, dependencies=[Depends(FastJWT().login_required)])
private_router.include_router(location_router, dependencies=[Depends(FastJWT().login_required)])
private_router.include_router(step_router, dependencies=[Depends(FastJWT().login_required)])
private_router.include_router(dashboard_router, dependencies=[Depends(FastJWT().login_required)])
private_router.include_router(profile_router, dependencies=[Depends(FastJWT().login_required)])
private_router.include_router(aar_router, dependencies=[Depends(FastJWT().login_required)])
private_router.include_router(poi_router, dependencies=[Depends(FastJWT().login_required)])
private_router.include_router(sitrep_router, dependencies=[Depends(FastJWT().login_required)])
private_router.include_router(asset_router, dependencies=[Depends(FastJWT().login_required)])
private_router.include_router(maintenance_router, dependencies=[Depends(FastJWT().login_required)])

router.include_router(public_router)
router.include_router(private_router)
router.include_router(ws_router)
router.include_router(yjs_router)


@router.get("/")
def api_router():
    return {
        "status": "healthy",
        "message": "Refer to documentation for usage help."
    }