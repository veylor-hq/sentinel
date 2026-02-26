from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Union
from app.core.telemetry_engine import process_telemetry
import asyncio

ingress_router = APIRouter(prefix="/ingress")

class TelemetryPayload(BaseModel):
    asset_id: str
    lat: float
    lon: float
    speed: Optional[float] = None
    heading: Optional[float] = None
    battery: Optional[float] = None

@ingress_router.post("/telemetry")
async def post_telemetry(payload: Union[TelemetryPayload, List[TelemetryPayload]]):
    # Depending on auth requirements, this will be unauthenticated or 
    # use lightweight API keys
    
    # Process asynchronously to return quickly
    if isinstance(payload, list):
        for p in payload:
            asyncio.create_task(process_telemetry(p.model_dump()))
    else:
        asyncio.create_task(process_telemetry(payload.model_dump()))
    
    return {"status": "accepted"}
