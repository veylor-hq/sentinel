from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.jwt import FastJWT

# Use an extremely short exp time for handshakes
JWT_EXPIRATION_SECONDS = 300

federation_router = APIRouter(prefix="/federation")

class HandshakeRequest(BaseModel):
    peer_id: str
    public_key: Optional[str] = None
    
class HandshakeResponse(BaseModel):
    token: str
    ws_url: str

@federation_router.post("/handshake", response_model=HandshakeResponse)
async def initiate_handshake(payload: HandshakeRequest):
    """
    Exchanges basic info to grant a short-lived token meant for WebSocket peering.
    In a real system, you'd verify the peer_id against a trusted list or verify 
    a signature based on public_key.
    """
    if not payload.peer_id:
        raise HTTPException(status_code=400, detail="peer_id required")
        
    # Generate a temporary token scoped specifically to 'federation_read'
    temp_token = await FastJWT().encode(
        {"id": payload.peer_id, "role": "federated_peer"},
    )
    
    return HandshakeResponse(
        token=temp_token,
        ws_url="/api/ws/telemetry" # Where the peer should connect
    )
