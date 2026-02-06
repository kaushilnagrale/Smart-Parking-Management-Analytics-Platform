"""Parking zones and availability API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_operator, get_current_admin
from app.models.user import User
from app.schemas import (
    ZoneCreate, ZoneUpdate, ZoneResponse, ZoneAvailability,
    CameraCreate, CameraResponse,
)
from app.services import ParkingService

router = APIRouter(prefix="/zones", tags=["Parking Zones"])


@router.get("/", response_model=list[ZoneResponse])
async def list_zones(
    active_only: bool = Query(True, description="Filter active zones only"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all parking zones."""
    service = ParkingService(db)
    zones = await service.list_zones(active_only=active_only)
    return [
        ZoneResponse(
            id=z.id, name=z.name, zone_code=z.zone_code,
            zone_type=z.zone_type, total_spots=z.total_spots,
            occupied_spots=z.occupied_spots,
            available_spots=z.available_spots,
            occupancy_rate=z.occupancy_rate,
            latitude=z.latitude, longitude=z.longitude,
            floor_level=z.floor_level, hourly_rate=z.hourly_rate,
            is_active=z.is_active, created_at=z.created_at,
        )
        for z in zones
    ]


@router.get("/availability", response_model=list[ZoneAvailability])
async def get_availability(db: AsyncSession = Depends(get_db)):
    """Get real-time parking availability (public endpoint)."""
    service = ParkingService(db)
    return await service.get_availability()


@router.get("/{zone_id}", response_model=ZoneResponse)
async def get_zone(
    zone_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get zone details by ID."""
    service = ParkingService(db)
    zone = await service.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    return ZoneResponse(
        id=zone.id, name=zone.name, zone_code=zone.zone_code,
        zone_type=zone.zone_type, total_spots=zone.total_spots,
        occupied_spots=zone.occupied_spots,
        available_spots=zone.available_spots,
        occupancy_rate=zone.occupancy_rate,
        latitude=zone.latitude, longitude=zone.longitude,
        floor_level=zone.floor_level, hourly_rate=zone.hourly_rate,
        is_active=zone.is_active, created_at=zone.created_at,
    )


@router.post("/", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_zone(
    zone_data: ZoneCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Create a new parking zone (admin only)."""
    service = ParkingService(db)
    zone = await service.create_zone(zone_data)
    return ZoneResponse(
        id=zone.id, name=zone.name, zone_code=zone.zone_code,
        zone_type=zone.zone_type, total_spots=zone.total_spots,
        occupied_spots=zone.occupied_spots,
        available_spots=zone.available_spots,
        occupancy_rate=zone.occupancy_rate,
        latitude=zone.latitude, longitude=zone.longitude,
        floor_level=zone.floor_level, hourly_rate=zone.hourly_rate,
        is_active=zone.is_active, created_at=zone.created_at,
    )


@router.put("/{zone_id}", response_model=ZoneResponse)
async def update_zone(
    zone_id: int,
    update_data: ZoneUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator),
):
    """Update a parking zone (operator+ access)."""
    service = ParkingService(db)
    zone = await service.update_zone(zone_id, update_data)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    return ZoneResponse(
        id=zone.id, name=zone.name, zone_code=zone.zone_code,
        zone_type=zone.zone_type, total_spots=zone.total_spots,
        occupied_spots=zone.occupied_spots,
        available_spots=zone.available_spots,
        occupancy_rate=zone.occupancy_rate,
        latitude=zone.latitude, longitude=zone.longitude,
        floor_level=zone.floor_level, hourly_rate=zone.hourly_rate,
        is_active=zone.is_active, created_at=zone.created_at,
    )


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(
    zone_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Delete a parking zone (admin only)."""
    service = ParkingService(db)
    success = await service.delete_zone(zone_id)
    if not success:
        raise HTTPException(status_code=404, detail="Zone not found")
