import zipfile
import io
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Response
from beanie import PydanticObjectId
from app.core.jwt import DecodedToken, FastJWT
from models.models import User, Mission, TelemetryState, SITREP, Note

aar_router = APIRouter(prefix="/aar")

@aar_router.get("/{mission_id}/export")
async def export_aar(mission_id: PydanticObjectId, request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")

    mission = await Mission.get(mission_id)
    if not mission or mission.operator != token.id:
        raise HTTPException(404, "Mission not found or not authorized")

    sitreps = await SITREP.find(SITREP.mission_id == mission.id).to_list()
    notes = await Note.find(Note.mission_id == mission.id).to_list()
    
    # Ideally, Telemetry is queried from a time series DB based on mission start/end.
    # Here, we export the latest states or fetch history if it was stored.
    telemetry = await TelemetryState.find().to_list()
    # TODO: Fetch true history when DB supports it

    bundle_data = {
        "mission": json.loads(mission.model_dump_json()),
        "sitreps": [json.loads(s.model_dump_json()) for s in sitreps],
        "notes": [json.loads(n.model_dump_json()) for n in notes],
        "telemetry_latest": [json.loads(t.model_dump_json()) for t in telemetry]
    }

    # Create zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps({"exported_at": datetime.utcnow().isoformat(), "exporter": str(user.username)}))
        zf.writestr(f"mission_{mission.name.replace(' ', '_')}.json", json.dumps(bundle_data, indent=2))
        
    zip_buffer.seek(0)
    
    # Normally, AES-256 encryption is applied here before returning
    # from cryptography.fernet import Fernet ... 
    
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=mission_{mission_id}_aar.veylor-aar"
        }
    )
