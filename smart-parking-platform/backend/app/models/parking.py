"""Parking zone, camera, and event models."""

import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Enum, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class ZoneType(str, enum.Enum):
    STANDARD = "standard"
    HANDICAP = "handicap"
    EV_CHARGING = "ev_charging"
    COMPACT = "compact"
    OVERSIZED = "oversized"
    VIP = "vip"


class VehicleType(str, enum.Enum):
    CAR = "car"
    TRUCK = "truck"
    MOTORCYCLE = "motorcycle"
    BUS = "bus"
    UNKNOWN = "unknown"


class ParkingZone(Base):
    __tablename__ = "parking_zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    zone_code = Column(String(20), unique=True, nullable=False)  # e.g., "A1", "B3"
    zone_type = Column(Enum(ZoneType), default=ZoneType.STANDARD)
    total_spots = Column(Integer, nullable=False)
    occupied_spots = Column(Integer, default=0)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    floor_level = Column(Integer, default=0)  # 0 = ground, -1 = basement, etc.
    hourly_rate = Column(Float, default=2.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    cameras = relationship("Camera", back_populates="zone")
    events = relationship("ParkingEvent", back_populates="zone")

    @property
    def available_spots(self) -> int:
        return max(0, self.total_spots - self.occupied_spots)

    @property
    def occupancy_rate(self) -> float:
        if self.total_spots == 0:
            return 0.0
        return round(self.occupied_spots / self.total_spots * 100, 2)

    def __repr__(self):
        return f"<ParkingZone {self.zone_code}: {self.occupied_spots}/{self.total_spots}>"


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    stream_url = Column(String(500), nullable=False)
    zone_id = Column(Integer, ForeignKey("parking_zones.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    resolution_width = Column(Integer, default=1920)
    resolution_height = Column(Integer, default=1080)
    fps = Column(Integer, default=30)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    zone = relationship("ParkingZone", back_populates="cameras")

    def __repr__(self):
        return f"<Camera {self.camera_id} zone={self.zone_id}>"


class ParkingEvent(Base):
    __tablename__ = "parking_events"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("parking_zones.id"), nullable=False)
    camera_id = Column(String(50), nullable=True)
    event_type = Column(String(20), nullable=False)  # "entry" or "exit"
    vehicle_type = Column(Enum(VehicleType), default=VehicleType.CAR)
    license_plate = Column(String(20), nullable=True)
    confidence_score = Column(Float, default=0.0)  # ML detection confidence
    image_path = Column(String(500), nullable=True)  # Stored frame snapshot
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relationships
    zone = relationship("ParkingZone", back_populates="events")

    def __repr__(self):
        return f"<ParkingEvent {self.event_type} zone={self.zone_id} plate={self.license_plate}>"


class OccupancySnapshot(Base):
    """Periodic snapshots of zone occupancy for time-series analytics."""
    __tablename__ = "occupancy_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("parking_zones.id"), nullable=False)
    occupied_spots = Column(Integer, nullable=False)
    total_spots = Column(Integer, nullable=False)
    occupancy_rate = Column(Float, nullable=False)
    vehicle_count_car = Column(Integer, default=0)
    vehicle_count_truck = Column(Integer, default=0)
    vehicle_count_motorcycle = Column(Integer, default=0)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    def __repr__(self):
        return f"<OccupancySnapshot zone={self.zone_id} rate={self.occupancy_rate}%>"
