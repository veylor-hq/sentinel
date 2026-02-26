from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List, Optional
from pydantic import BaseModel

from app.core.jwt import FastJWT, DecodedToken
from models.models import User, Asset
from beanie import PydanticObjectId

asset_router = APIRouter(prefix="/asset", tags=["asset"])

class AssetCreate(BaseModel):
    name: str
    asset_type: str = "vehicle"

@asset_router.post("/", response_model=Asset)
async def create_asset(payload: AssetCreate, request: Request):
    """Register a new asset into the system."""
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    asset = Asset(
        name=payload.name,
        asset_type=payload.asset_type,
        owner_id=user.id
    )
    await asset.insert()
    return asset

@asset_router.get("/", response_model=List[Asset])
async def list_assets(request: Request):
    """List all assets available to the user."""
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    # Assuming user can see all assets they own or generally all assets for now
    return await Asset.find_all().to_list()

@asset_router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(asset_id: PydanticObjectId, request: Request):
    """Delete an asset."""
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    
    asset = await Asset.get(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    await asset.delete()
    return None
