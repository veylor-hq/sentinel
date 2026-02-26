from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional
from beanie import PydanticObjectId
from app.core.jwt import FastJWT, DecodedToken
from models.models import User, GeoJSONPoint
from models.poi import PointOfInterest, ThreatLevel

poi_router = APIRouter(prefix="/poi", tags=["poi"])

@poi_router.get("/", response_model=List[PointOfInterest])
async def list_pois(
    request: Request,
    mission_id: Optional[str] = None
):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    query = {}
    if mission_id:
        try:
            query["mission_id"] = PydanticObjectId(mission_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid mission ID format")
            
    # Return all POIs if no mission ID is specified, or filter by mission
    pois = await PointOfInterest.find(query).to_list()
    return pois

from pydantic import BaseModel

class CreatePOIPayload(BaseModel):
    name: str
    poi_type: str = "location"
    description: Optional[str] = None
    lat: float
    lon: float
    threat_level: ThreatLevel = ThreatLevel.UNKNOWN
    tags: List[str] = []
    mission_id: Optional[str] = None

@poi_router.post("/", response_model=PointOfInterest)
async def create_poi(
    payload: CreatePOIPayload,
    request: Request
):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    m_id = None
    if payload.mission_id:
        try:
            m_id = PydanticObjectId(payload.mission_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid mission ID format")
            
    poi = PointOfInterest(
        name=payload.name,
        poi_type=payload.poi_type,
        description=payload.description,
        location=GeoJSONPoint(coordinates=[payload.lon, payload.lat]),
        threat_level=payload.threat_level,
        reported_by=user.id,
        tags=payload.tags,
        mission_id=m_id
    )
    
    await poi.insert()
    return poi

@poi_router.delete("/{poi_id}")
async def delete_poi(
    poi_id: str,
    request: Request
):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    try:
        p_id = PydanticObjectId(poi_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid POI ID")
        
    poi = await PointOfInterest.get(p_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
        
    await poi.delete()
    return {"status": "deleted"}
