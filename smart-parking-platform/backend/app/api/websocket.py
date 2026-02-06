"""WebSocket endpoint for real-time parking updates."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manages active WebSocket connections for real-time broadcasting."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        dead = set()
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                dead.add(conn)

        self.active_connections -= dead

    async def send_personal(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_json(message)
        except Exception:
            self.active_connections.discard(websocket)


manager = ConnectionManager()


@router.websocket("/ws/parking")
async def parking_websocket(websocket: WebSocket):
    """Real-time parking updates via WebSocket.

    Clients receive:
    - zone_update: Occupancy changes per zone
    - event: New parking entry/exit events
    - alert: Anomaly or capacity warnings
    - heartbeat: Periodic keepalive

    Message format:
    {
        "type": "zone_update" | "event" | "alert" | "heartbeat",
        "data": { ... },
        "timestamp": "2024-01-01T00:00:00Z"
    }
    """
    await manager.connect(websocket)

    try:
        # Send initial connection confirmation
        await manager.send_personal(websocket, {
            "type": "connected",
            "data": {"message": "Connected to parking feed"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        while True:
            # Listen for client messages (subscription preferences, etc.)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)

                # Handle subscription messages
                if message.get("type") == "subscribe":
                    zone_ids = message.get("zones", [])
                    await manager.send_personal(websocket, {
                        "type": "subscribed",
                        "data": {"zones": zone_ids},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

            except asyncio.TimeoutError:
                # Send heartbeat
                await manager.send_personal(websocket, {
                    "type": "heartbeat",
                    "data": {},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Helper function for other modules to broadcast updates
async def broadcast_zone_update(zone_code: str, occupied: int, total: int):
    """Broadcast zone occupancy update to all WebSocket clients."""
    await manager.broadcast({
        "type": "zone_update",
        "data": {
            "zone_code": zone_code,
            "occupied_spots": occupied,
            "total_spots": total,
            "occupancy_rate": round(occupied / total * 100, 2) if total > 0 else 0,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def broadcast_parking_event(event_type: str, zone_code: str, plate: str = None):
    """Broadcast parking event to all WebSocket clients."""
    await manager.broadcast({
        "type": "event",
        "data": {
            "event_type": event_type,
            "zone_code": zone_code,
            "license_plate": plate,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
