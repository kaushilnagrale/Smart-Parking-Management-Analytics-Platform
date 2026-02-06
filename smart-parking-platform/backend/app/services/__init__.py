"""Business logic services for parking operations."""

from typing import List, Optional, Dict
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from loguru import logger

from app.models.parking import ParkingZone, ParkingEvent, OccupancySnapshot, Camera
from app.models.user import User, UserRole
from app.schemas import (
    ZoneCreate, ZoneUpdate, ZoneResponse, ZoneAvailability,
    ParkingEventCreate, DashboardSummary, ZoneAnalytics,
)
from app.core.security import get_password_hash


class ParkingService:
    """Core parking management service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Zone CRUD ─────────────────────────────────────────────────────

    async def create_zone(self, zone_data: ZoneCreate) -> ParkingZone:
        zone = ParkingZone(**zone_data.model_dump())
        self.db.add(zone)
        await self.db.flush()
        await self.db.refresh(zone)
        return zone

    async def get_zone(self, zone_id: int) -> Optional[ParkingZone]:
        result = await self.db.execute(
            select(ParkingZone).where(ParkingZone.id == zone_id)
        )
        return result.scalar_one_or_none()

    async def get_zone_by_code(self, zone_code: str) -> Optional[ParkingZone]:
        result = await self.db.execute(
            select(ParkingZone).where(ParkingZone.zone_code == zone_code)
        )
        return result.scalar_one_or_none()

    async def list_zones(self, active_only: bool = True) -> List[ParkingZone]:
        query = select(ParkingZone)
        if active_only:
            query = query.where(ParkingZone.is_active == True)
        query = query.order_by(ParkingZone.zone_code)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_zone(self, zone_id: int, update_data: ZoneUpdate) -> Optional[ParkingZone]:
        zone = await self.get_zone(zone_id)
        if not zone:
            return None

        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(zone, field, value)

        await self.db.flush()
        await self.db.refresh(zone)
        return zone

    async def delete_zone(self, zone_id: int) -> bool:
        zone = await self.get_zone(zone_id)
        if not zone:
            return False
        await self.db.delete(zone)
        return True

    # ─── Availability ──────────────────────────────────────────────────

    async def get_availability(self) -> List[ZoneAvailability]:
        zones = await self.list_zones(active_only=True)
        return [
            ZoneAvailability(
                zone_code=z.zone_code,
                zone_name=z.name,
                total_spots=z.total_spots,
                available_spots=z.available_spots,
                occupancy_rate=z.occupancy_rate,
                zone_type=z.zone_type,
            )
            for z in zones
        ]

    # ─── Parking Events ───────────────────────────────────────────────

    async def record_event(self, event_data: ParkingEventCreate) -> ParkingEvent:
        zone = await self.get_zone(event_data.zone_id)
        if not zone:
            raise ValueError(f"Zone {event_data.zone_id} not found")

        event = ParkingEvent(**event_data.model_dump())
        self.db.add(event)

        # Update zone occupancy count
        if event_data.event_type == "entry":
            zone.occupied_spots = min(zone.occupied_spots + 1, zone.total_spots)
        elif event_data.event_type == "exit":
            zone.occupied_spots = max(zone.occupied_spots - 1, 0)

        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def get_events(
        self,
        zone_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[ParkingEvent]:
        query = select(ParkingEvent)

        conditions = []
        if zone_id:
            conditions.append(ParkingEvent.zone_id == zone_id)
        if start_time:
            conditions.append(ParkingEvent.timestamp >= start_time)
        if end_time:
            conditions.append(ParkingEvent.timestamp <= end_time)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(ParkingEvent.timestamp.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ─── Dashboard ─────────────────────────────────────────────────────

    async def get_dashboard_summary(self) -> DashboardSummary:
        zones = await self.list_zones(active_only=True)

        total_spots = sum(z.total_spots for z in zones)
        total_occupied = sum(z.occupied_spots for z in zones)

        # Count active cameras
        cam_result = await self.db.execute(
            select(func.count(Camera.id)).where(Camera.is_active == True)
        )
        active_cameras = cam_result.scalar() or 0

        # Count today's events
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        events_result = await self.db.execute(
            select(func.count(ParkingEvent.id)).where(
                ParkingEvent.timestamp >= today_start
            )
        )
        events_today = events_result.scalar() or 0

        availability = await self.get_availability()

        return DashboardSummary(
            total_zones=len(zones),
            total_spots=total_spots,
            total_occupied=total_occupied,
            total_available=total_spots - total_occupied,
            overall_occupancy_rate=(
                round(total_occupied / total_spots * 100, 2) if total_spots > 0 else 0.0
            ),
            active_cameras=active_cameras,
            events_today=events_today,
            zones=availability,
        )

    # ─── Analytics ─────────────────────────────────────────────────────

    async def get_zone_analytics(
        self, zone_id: int, days: int = 7
    ) -> Optional[ZoneAnalytics]:
        zone = await self.get_zone(zone_id)
        if not zone:
            return None

        start_time = datetime.now(timezone.utc) - timedelta(days=days)

        # Get events for the period
        events = await self.get_events(
            zone_id=zone_id, start_time=start_time, limit=10000
        )

        entries = [e for e in events if e.event_type == "entry"]
        exits = [e for e in events if e.event_type == "exit"]

        # Get occupancy snapshots for average rate
        snap_result = await self.db.execute(
            select(func.avg(OccupancySnapshot.occupancy_rate))
            .where(
                and_(
                    OccupancySnapshot.zone_id == zone_id,
                    OccupancySnapshot.timestamp >= start_time,
                )
            )
        )
        avg_rate = snap_result.scalar() or zone.occupancy_rate

        # Find peak hour
        hour_counts: Dict[int, int] = {}
        for e in entries:
            h = e.timestamp.hour
            hour_counts[h] = hour_counts.get(h, 0) + 1
        peak_hour = max(hour_counts, key=hour_counts.get) if hour_counts else 12

        return ZoneAnalytics(
            zone_code=zone.zone_code,
            zone_name=zone.name,
            avg_occupancy_rate=round(float(avg_rate), 2),
            peak_hour=peak_hour,
            total_entries=len(entries),
            total_exits=len(exits),
            avg_duration_minutes=45.0,  # Placeholder — requires entry/exit pairing
            revenue_estimate=round(len(entries) * zone.hourly_rate * 1.5, 2),
        )

    # ─── Snapshots ─────────────────────────────────────────────────────

    async def take_occupancy_snapshot(self):
        """Record current occupancy for all zones (called periodically)."""
        zones = await self.list_zones(active_only=True)
        for zone in zones:
            snapshot = OccupancySnapshot(
                zone_id=zone.id,
                occupied_spots=zone.occupied_spots,
                total_spots=zone.total_spots,
                occupancy_rate=zone.occupancy_rate,
            )
            self.db.add(snapshot)
        await self.db.flush()
        logger.info(f"Occupancy snapshot recorded for {len(zones)} zones")


class UserService:
    """User management service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, email: str, full_name: str, password: str, role: UserRole) -> User:
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list_users(self) -> List[User]:
        result = await self.db.execute(select(User).order_by(User.created_at.desc()))
        return list(result.scalars().all())
