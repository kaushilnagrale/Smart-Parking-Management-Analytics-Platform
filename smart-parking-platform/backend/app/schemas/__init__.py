"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole
from app.models.parking import ZoneType, VehicleType


# ─── Auth Schemas ──────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.VIEWER


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Parking Zone Schemas ─────────────────────────────────────────────

class ZoneCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    zone_code: str = Field(..., min_length=1, max_length=20)
    zone_type: ZoneType = ZoneType.STANDARD
    total_spots: int = Field(..., gt=0)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    floor_level: int = 0
    hourly_rate: float = Field(default=2.0, ge=0)


class ZoneUpdate(BaseModel):
    name: Optional[str] = None
    zone_type: Optional[ZoneType] = None
    total_spots: Optional[int] = None
    hourly_rate: Optional[float] = None
    is_active: Optional[bool] = None


class ZoneResponse(BaseModel):
    id: int
    name: str
    zone_code: str
    zone_type: ZoneType
    total_spots: int
    occupied_spots: int
    available_spots: int
    occupancy_rate: float
    latitude: Optional[float]
    longitude: Optional[float]
    floor_level: int
    hourly_rate: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ZoneAvailability(BaseModel):
    zone_code: str
    zone_name: str
    total_spots: int
    available_spots: int
    occupancy_rate: float
    zone_type: ZoneType


# ─── Camera Schemas ────────────────────────────────────────────────────

class CameraCreate(BaseModel):
    camera_id: str
    name: str
    stream_url: str
    zone_id: int
    resolution_width: int = 1920
    resolution_height: int = 1080
    fps: int = 30


class CameraResponse(BaseModel):
    id: int
    camera_id: str
    name: str
    stream_url: str
    zone_id: int
    is_active: bool
    last_heartbeat: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Parking Event Schemas ─────────────────────────────────────────────

class ParkingEventCreate(BaseModel):
    zone_id: int
    camera_id: Optional[str] = None
    event_type: str = Field(..., pattern="^(entry|exit)$")
    vehicle_type: VehicleType = VehicleType.CAR
    license_plate: Optional[str] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)


class ParkingEventResponse(BaseModel):
    id: int
    zone_id: int
    camera_id: Optional[str]
    event_type: str
    vehicle_type: VehicleType
    license_plate: Optional[str]
    confidence_score: float
    timestamp: datetime

    class Config:
        from_attributes = True


# ─── Analytics Schemas ─────────────────────────────────────────────────

class OccupancyTrend(BaseModel):
    timestamp: datetime
    occupancy_rate: float
    vehicle_count: int


class ZoneAnalytics(BaseModel):
    zone_code: str
    zone_name: str
    avg_occupancy_rate: float
    peak_hour: int
    total_entries: int
    total_exits: int
    avg_duration_minutes: float
    revenue_estimate: float


class DashboardSummary(BaseModel):
    total_zones: int
    total_spots: int
    total_occupied: int
    total_available: int
    overall_occupancy_rate: float
    active_cameras: int
    events_today: int
    zones: List[ZoneAvailability]


# ─── Detection Schemas ─────────────────────────────────────────────────

class DetectionResult(BaseModel):
    vehicle_count: int
    vehicles: List[dict]  # bbox, class, confidence
    license_plates: List[str]
    frame_timestamp: datetime
    processing_time_ms: float
