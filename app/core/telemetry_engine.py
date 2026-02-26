import asyncio
from typing import Dict, Any
from datetime import datetime
from models.models import TelemetryState, Mission, MissionStatus, Asset, GeoJSONPoint, RegionOfInterest
from beanie import PydanticObjectId
from app.core.websocket import manager

async def process_telemetry(payload: Dict[str, Any]):
    """
    Process incoming telemetry payload from the message bus
    Payload expected:
    {
        "asset_id": "...",
        "lat": 12.34,
        "lon": 56.78,
        "speed": 10.5,
        "heading": 90.0,
        "battery": 14.0
    }
    """
    asset_id_str = payload.get("asset_id")
    if not asset_id_str:
        return

    try:
        asset_id = PydanticObjectId(asset_id_str)
    except Exception:
        return

    asset = await Asset.get(asset_id)
    if not asset:
        return

    lat = payload.get("lat")
    lon = payload.get("lon")
    if lat is None or lon is None:
        return

    speed = payload.get("speed")
    heading = payload.get("heading")
    battery = payload.get("battery")
    
    
    current_point = GeoJSONPoint(coordinates=[lon, lat])
    
    # Robust Time-Stamping (multi-device jitter buffer prep)
    # Check for provided timestamp, parse if exists, else fallback
    raw_time = payload.get("timestamp") or payload.get("time")
    record_time = datetime.utcnow()
    if raw_time:
        try:
            if isinstance(raw_time, (int, float)):
                # Assume unix epoch (seconds)
                record_time = datetime.utcfromtimestamp(raw_time)
            elif isinstance(raw_time, str):
                # Attempt basic ISO parsing
                record_time = datetime.fromisoformat(raw_time.replace('Z', '+00:00'))
        except Exception:
            pass # Keep utcnow fallback

    # 1. Update Telemetry State
    state = await TelemetryState.find_one({"asset_id": asset_id})
    if not state:
        state = TelemetryState(
            asset_id=asset_id,
            last_location=current_point,
            speed=speed,
            heading=heading,
            battery=battery,
            timestamp=record_time
        )
        await state.insert()
    else:
        # Ignore out-of-order delayed packets if they are older than our current state
        if state.timestamp and record_time < state.timestamp:
             return
             
        state.last_location = current_point
        state.speed = speed
        state.heading = heading
        state.battery = battery
        state.timestamp = record_time
        await state.save()

    # Broadcast updated state to websockets locally
    await manager.broadcast({
        "type": "telemetry_update",
        "data": state.model_dump(mode='json')
    })
    
    # 2. Geofencing (ROI Intersection)
    intersecting_rois = await RegionOfInterest.find({
        "geometry": {
            "$geoIntersects": {
                "$geometry": current_point.model_dump()
            }
        }
    }).to_list()
    
    for roi in intersecting_rois:
        await manager.broadcast({
            "type": "security_alert",
            "data": {
                "asset_id": str(asset.id),
                "roi_id": str(roi.id),
                "message": f"GEO-FENCE BREACH: {asset.name} entered {roi.name}."
            }
        })

    # 3. Rules Engine & Mission Trigger Evaluator
    # Find active or warm_up missions attached to this asset
    missions = await Mission.find(
        {"attached_assets": asset_id, "status": {"$in": [MissionStatus.WARM_UP, MissionStatus.ACTIVE]}}
    ).to_list()

    for mission in missions:
        # Trigger: If Warm Up and speed > 5 km/h, shift to ACTIVE
        if mission.status == MissionStatus.WARM_UP and speed and speed > 5.0:
            # Check checklists
            all_completed = all(item.is_completed for item in mission.checklists)
            if all_completed or not mission.checklists:
                mission.status = MissionStatus.ACTIVE
                await mission.save()
                await manager.broadcast({
                    "type": "mission_alert",
                    "data": {
                        "mission_id": str(mission.id),
                        "message": f"Mission {mission.name} transitioned to ACTIVE due to asset movement."
                    }
                })

        # Rules Engine: Battery low
        if battery is not None and battery < 15.0:
            await manager.broadcast({
                "type": "security_alert",
                "data": {
                    "mission_id": str(mission.id),
                    "asset_id": str(asset.id),
                    "message": f"Asset {asset.name} has low battery: {battery}%"
                }
            })
