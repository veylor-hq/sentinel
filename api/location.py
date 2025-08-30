from typing import Annotated, Optional
from app.core.jwt import DecodedToken, FastJWT
from models.models import GeoPoint, Location, LocationType
from datetime import datetime
from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel


class CreateLocationSchema(BaseModel):
    name: str
    location_type: Optional[LocationType] = LocationType.GENERIC
    coordinates: GeoPoint

location_router = APIRouter(prefix="/location")


@location_router.get("/")
async def list_locations():
    locations =  await Location.find_all().to_list()
    return locations


@location_router.post("/")
async def create_location(payload: CreateLocationSchema):
    if await Location.find_one({
        "name": payload.name
    }):
       raise HTTPException(status_code=400, detail="Location already exists")
    
    location = Location(**payload.model_dump())
    await location.insert()
    return location


@location_router.get("/{location_id}")
async def get_location(location_id: PydanticObjectId):
    location = await Location.get(location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location

