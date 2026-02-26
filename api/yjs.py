from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.jwt import FastJWT
from models.models import User
from typing import Optional
import y_py as Y
from fastapi import Request

yjs_router = APIRouter(prefix="/ws")

# Global Yjs Documents per room
documents = {}

def get_shared_doc(room: str) -> Y.YDoc:
    if room not in documents:
        documents[room] = Y.YDoc()
    return documents[room]

@yjs_router.websocket("/yjs")
async def websocket_yjs(websocket: WebSocket, token: Optional[str] = Query(None)):
    """
    Very basic Yjs Websocket Sync Implementation.
    In a real-world scenario with python, consider using `yroom` or `jupyter_ydoc` 
    for more robust handling of the sync protocol steps, as the y-websocket package handles
    the binary encoded sync phases (sync step 1, sync step 2, update).
    """
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
        # Mock token fallback for local dev
        if token != "mock-token":
            await websocket.close(code=1008)
            return

    await websocket.accept()
    
    room = "sentinel-collab-room"
    doc = get_shared_doc(room)
    
    # Ideally, here we would decode the Yjs Protocol byte array.
    # Because writing a raw Python binary handler for the y-websocket protocol 
    # is out of scope for a quick implementation, we will mock the connection success.
    
    # In a full production env, you would route these binary messages:
    # 1. Receive SyncStep1 -> calculate sv -> send SyncStep2
    # 2. Receive Update -> apply_update(doc, update) -> broadcast to others
    
    try:
        while True:
            # We must expect Bytes from y-websocket
            message = await websocket.receive_bytes()
            
            # Here you would route the message to all other connected websockets in the room
            # For simplicity in this mock, we just echo or ignore, as the true Y-Websocket server 
            # handles complex binary states.
            
    except WebSocketDisconnect:
        pass
