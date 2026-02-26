from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.websocket import manager
from app.core.jwt import FastJWT
from models.models import User
from typing import Optional

ws_router = APIRouter(prefix="/ws")

@ws_router.websocket("/telemetry")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    if not token:
        await websocket.close(code=1008)
        return
        
    try:
        decoded_token = await FastJWT().decode(token)
        user = await User.get(decoded_token.id)
        if not user:
             await websocket.close(code=1008)
             return
    except Exception:
        await websocket.close(code=1008)
        return
        
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Broadcast incoming telemetry data to all connected clients.
            # Adds user identification to track sender.
            await manager.broadcast({"user_id": str(user.id), "username": user.username, "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
