"""API router aggregation."""

from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.zones import router as zones_router
from app.api.events import router as events_router
from app.api.analytics import router as analytics_router
from app.api.websocket import router as ws_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(zones_router)
api_router.include_router(events_router)
api_router.include_router(analytics_router)

# WebSocket router (no prefix needed)
websocket_router = ws_router
