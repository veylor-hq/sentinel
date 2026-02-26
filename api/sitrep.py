import os
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.jwt import FastJWT, DecodedToken
from models.models import User, SITREP, GeoJSONPoint
from beanie import PydanticObjectId

sitrep_router = APIRouter(prefix="/sitrep", tags=["sitrep"])

class SITREPCreate(BaseModel):
    description: str
    lat: float
    lon: float
    mission_id: Optional[PydanticObjectId] = None
    status: str = "PENDING"
    severity: str = "ROUTINE"
    # Military fields
    unit: Optional[str] = None
    grid_ref: Optional[str] = None
    sitrep_type: Optional[str] = None   # CONTACT / CASUALTY / LOGSTAT / MEDEVAC / OTHER
    contact_type: Optional[str] = None  # TROOPS / VEH / UAS / IED / etc
    assets_involved: Optional[str] = None
    action_taken: Optional[str] = None

class SITREPUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    action_taken: Optional[str] = None
    description: Optional[str] = None

FERNET_KEY = os.environ.get("FERNET_KEY", b"vFz8oJw6P9D3yV4H7lq2x5sC1gM0nZ8tU4rV7wQ1x9A=")
if isinstance(FERNET_KEY, str):
    FERNET_KEY = FERNET_KEY.encode()
fernet = Fernet(FERNET_KEY)

@sitrep_router.post("/", response_model=SITREP)
async def create_sitrep(payload: SITREPCreate, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")

    encrypted_desc = fernet.encrypt(payload.description.encode()).decode()

    sitrep = SITREP(
        operator_id=user.id,
        mission_id=payload.mission_id,
        location=GeoJSONPoint(coordinates=[payload.lon, payload.lat]),
        description=encrypted_desc,
        status=payload.status,
        severity=payload.severity,
        unit=payload.unit,
        grid_ref=payload.grid_ref,
        sitrep_type=payload.sitrep_type,
        contact_type=payload.contact_type,
        assets_involved=payload.assets_involved,
        action_taken=payload.action_taken,
        timestamp=datetime.utcnow()
    )

    await sitrep.insert()

    from app.core.websocket import manager
    await manager.broadcast({
        "type": "sitrep_alert",
        "data": {
            "sitrep_id": str(sitrep.id),
            "operator": user.username,
            "unit": payload.unit,
            "sitrep_type": payload.sitrep_type,
            "severity": payload.severity,
            "lat": payload.lat,
            "lon": payload.lon
        }
    })

    sitrep.description = payload.description
    return sitrep


@sitrep_router.get("/", response_model=List[SITREP])
async def list_sitreps(request: Request, mission_id: Optional[PydanticObjectId] = None):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if mission_id:
        sitreps = await SITREP.find(SITREP.mission_id == mission_id).sort(-SITREP.timestamp).to_list()
    else:
        sitreps = await SITREP.find_all().sort(-SITREP.timestamp).limit(100).to_list()

    for s in sitreps:
        try:
            s.description = fernet.decrypt(s.description.encode()).decode()
        except Exception:
            pass
    return sitreps


@sitrep_router.patch("/{sitrep_id}")
async def update_sitrep(sitrep_id: PydanticObjectId, payload: SITREPUpdate, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    sitrep = await SITREP.get(sitrep_id)
    if not sitrep:
        raise HTTPException(404, "SITREP not found")

    if payload.status is not None:
        sitrep.status = payload.status
    if payload.severity is not None:
        sitrep.severity = payload.severity
    if payload.action_taken is not None:
        sitrep.action_taken = payload.action_taken
    if payload.description is not None:
        sitrep.description = fernet.encrypt(payload.description.encode()).decode()

    await sitrep.save()
    # Decrypt for response
    try:
        sitrep.description = fernet.decrypt(sitrep.description.encode()).decode()
    except Exception:
        pass
    return sitrep
