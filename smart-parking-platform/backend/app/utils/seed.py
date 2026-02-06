"""Database seeder for initial data."""

import asyncio
from datetime import datetime, timedelta, timezone
import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.core.database import AsyncSessionLocal, init_db
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.parking import (
    ParkingZone, ZoneType, Camera, ParkingEvent,
    VehicleType, OccupancySnapshot,
)

SEED_USERS = [
    {"email": "admin@smartparking.com", "full_name": "System Admin", "password": "admin123", "role": UserRole.ADMIN},
    {"email": "operator@smartparking.com", "full_name": "Parking Operator", "password": "operator123", "role": UserRole.OPERATOR},
    {"email": "viewer@smartparking.com", "full_name": "Dashboard Viewer", "password": "viewer123", "role": UserRole.VIEWER},
]

SEED_ZONES = [
    {"name": "Main Entrance - Level 1", "zone_code": "A1", "zone_type": ZoneType.STANDARD, "total_spots": 50, "latitude": 33.4255, "longitude": -111.9400, "floor_level": 1, "hourly_rate": 3.00},
    {"name": "Main Entrance - Level 2", "zone_code": "A2", "zone_type": ZoneType.STANDARD, "total_spots": 50, "latitude": 33.4256, "longitude": -111.9401, "floor_level": 2, "hourly_rate": 2.50},
    {"name": "East Wing - Compact", "zone_code": "B1", "zone_type": ZoneType.COMPACT, "total_spots": 30, "latitude": 33.4260, "longitude": -111.9395, "floor_level": 1, "hourly_rate": 2.00},
    {"name": "West Wing - Standard", "zone_code": "C1", "zone_type": ZoneType.STANDARD, "total_spots": 40, "latitude": 33.4250, "longitude": -111.9405, "floor_level": 1, "hourly_rate": 2.50},
    {"name": "Basement - Handicap", "zone_code": "D1", "zone_type": ZoneType.HANDICAP, "total_spots": 15, "latitude": 33.4253, "longitude": -111.9398, "floor_level": -1, "hourly_rate": 1.50},
    {"name": "Rooftop - EV Charging", "zone_code": "E1", "zone_type": ZoneType.EV_CHARGING, "total_spots": 20, "latitude": 33.4258, "longitude": -111.9402, "floor_level": 3, "hourly_rate": 4.00},
    {"name": "VIP Section", "zone_code": "F1", "zone_type": ZoneType.VIP, "total_spots": 10, "latitude": 33.4254, "longitude": -111.9399, "floor_level": 1, "hourly_rate": 8.00},
    {"name": "Overflow - North Lot", "zone_code": "G1", "zone_type": ZoneType.OVERSIZED, "total_spots": 25, "latitude": 33.4265, "longitude": -111.9390, "floor_level": 0, "hourly_rate": 2.00},
]


async def seed_database():
    await init_db()

    async with AsyncSessionLocal() as db:
        # Seed users
        for user_data in SEED_USERS:
            existing = await db.execute(select(User).where(User.email == user_data["email"]))
            if existing.scalar_one_or_none() is None:
                user = User(
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    hashed_password=get_password_hash(user_data["password"]),
                    role=user_data["role"],
                )
                db.add(user)
                logger.info(f"Created user: {user_data['email']}")

        # Seed zones
        zone_objects = []
        for zone_data in SEED_ZONES:
            existing = await db.execute(select(ParkingZone).where(ParkingZone.zone_code == zone_data["zone_code"]))
            if existing.scalar_one_or_none() is None:
                zone = ParkingZone(**zone_data)
                zone.occupied_spots = random.randint(0, zone.total_spots)
                db.add(zone)
                zone_objects.append(zone)
                logger.info(f"Created zone: {zone_data['zone_code']}")

        await db.commit()

        # Seed cameras
        zones = (await db.execute(select(ParkingZone))).scalars().all()
        for zone in zones:
            existing = await db.execute(select(Camera).where(Camera.camera_id == f"CAM-{zone.zone_code}-01"))
            if existing.scalar_one_or_none() is None:
                camera = Camera(
                    camera_id=f"CAM-{zone.zone_code}-01",
                    name=f"Camera {zone.zone_code} Main",
                    stream_url=f"rtsp://localhost:8554/{zone.zone_code.lower()}",
                    zone_id=zone.id,
                )
                db.add(camera)

        await db.commit()

        # Seed historical occupancy snapshots (7 days)
        snap_count = await db.execute(select(OccupancySnapshot.id).limit(1))
        if snap_count.scalar_one_or_none() is None:
            logger.info("Seeding occupancy snapshots (7 days)...")
            now = datetime.now(timezone.utc)
            for zone in zones:
                base_rate = random.uniform(30, 70)
                for hours_ago in range(168, 0, -1):  # 7 days
                    ts = now - timedelta(hours=hours_ago)
                    hour = ts.hour

                    # Simulate daily pattern: peak 9-11 and 17-19
                    if 9 <= hour <= 11 or 17 <= hour <= 19:
                        rate = min(95, base_rate + random.uniform(15, 30))
                    elif 6 <= hour <= 20:
                        rate = base_rate + random.uniform(-10, 15)
                    else:
                        rate = max(5, base_rate - random.uniform(15, 30))

                    occupied = int(zone.total_spots * rate / 100)
                    snapshot = OccupancySnapshot(
                        zone_id=zone.id,
                        occupied_spots=occupied,
                        total_spots=zone.total_spots,
                        occupancy_rate=round(rate, 2),
                        timestamp=ts,
                    )
                    db.add(snapshot)

            await db.commit()
            logger.info("Seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_database())
