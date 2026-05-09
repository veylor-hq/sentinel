from fastapi import APIRouter, HTTPException, status, Request, Query
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from beanie import PydanticObjectId

from app.core.jwt import FastJWT, DecodedToken
from models.models import User, Asset, AssetCategory, AssetLink
from models.poi import PointOfInterest


asset_router = APIRouter(prefix="/asset", tags=["asset"])


class AssetLinkIn(BaseModel):
    relation: str
    target_id: PydanticObjectId
    target_category: AssetCategory
    label: Optional[str] = None


class AssetCreate(BaseModel):
    name: str
    category: AssetCategory = AssetCategory.TRANSPORT
    details: Dict[str, Any] = Field(default_factory=dict)
    links: List[AssetLinkIn] = Field(default_factory=list)
    map_location_id: Optional[PydanticObjectId] = None
    poi_id: Optional[PydanticObjectId] = None


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[AssetCategory] = None
    details: Optional[Dict[str, Any]] = None
    links: Optional[List[AssetLinkIn]] = None
    map_location_id: Optional[PydanticObjectId] = None
    poi_id: Optional[PydanticObjectId] = None


def _links_from_payload(payload: List[AssetLinkIn]) -> List[AssetLink]:
    return [
        AssetLink(
            relation=x.relation,
            target_id=x.target_id,
            target_category=x.target_category,
            label=x.label,
        )
        for x in payload
    ]


async def _sync_registry_poi_link(
    asset: Asset,
    previous_poi_id: Optional[PydanticObjectId],
) -> None:
    """Keep POI.registry_asset_id in sync when linking registry rows to map markers."""
    if previous_poi_id is not None and previous_poi_id != asset.poi_id:
        old_poi = await PointOfInterest.get(previous_poi_id)
        if old_poi is not None and old_poi.registry_asset_id == asset.id:
            old_poi.registry_asset_id = None
            await old_poi.save()
    if asset.poi_id is not None:
        poi = await PointOfInterest.get(asset.poi_id)
        if poi is not None:
            poi.registry_asset_id = asset.id
            await poi.save()
    elif previous_poi_id is not None:
        old_poi = await PointOfInterest.get(previous_poi_id)
        if old_poi is not None and old_poi.registry_asset_id == asset.id:
            old_poi.registry_asset_id = None
            await old_poi.save()


@asset_router.post("/", response_model=Asset)
async def create_asset(payload: AssetCreate, request: Request):
    """Register a new registry record (person, location, transport, item, or gear)."""
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    asset = Asset(
        name=payload.name,
        category=payload.category,
        owner_id=user.id,
        details=payload.details,
        links=_links_from_payload(payload.links),
        map_location_id=payload.map_location_id,
        poi_id=payload.poi_id,
    )
    await asset.insert()
    await _sync_registry_poi_link(asset, None)
    return asset


@asset_router.get("/", response_model=List[Asset])
async def list_assets(
    request: Request,
    category: Optional[AssetCategory] = Query(default=None),
):
    """List registry records owned by the current operator, optionally filtered by section."""
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if category is not None:
        return await Asset.find(Asset.owner_id == user.id, Asset.category == category).to_list()
    return await Asset.find(Asset.owner_id == user.id).to_list()


@asset_router.get("/{asset_id}", response_model=Asset)
async def get_asset(asset_id: PydanticObjectId, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    asset = await Asset.get(asset_id)
    if not asset or asset.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@asset_router.patch("/{asset_id}", response_model=Asset)
async def update_asset(
    asset_id: PydanticObjectId,
    payload: AssetUpdate,
    request: Request,
):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    asset = await Asset.get(asset_id)
    if not asset or asset.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Asset not found")

    prev_poi = asset.poi_id
    data = payload.model_dump(exclude_unset=True)
    if "links" in data:
        if payload.links is not None:
            asset.links = _links_from_payload(payload.links)
        del data["links"]
    for key, val in data.items():
        setattr(asset, key, val)
    await asset.save()
    await _sync_registry_poi_link(asset, prev_poi)
    return asset


@asset_router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(asset_id: PydanticObjectId, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")

    asset = await Asset.get(asset_id)
    if not asset or asset.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.poi_id:
        poi = await PointOfInterest.get(asset.poi_id)
        if poi is not None and poi.registry_asset_id == asset.id:
            poi.registry_asset_id = None
            await poi.save()
    await asset.delete()
    return None
