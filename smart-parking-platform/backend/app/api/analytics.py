"""Analytics and reporting API endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.parking import OccupancySnapshot, ParkingEvent
from app.schemas import DashboardSummary, ZoneAnalytics, OccupancyTrend
from app.services import ParkingService
from app.ml.occupancy_analyzer import OccupancyAnalyzer

router = APIRouter(prefix="/analytics", tags=["Analytics"])

analyzer = OccupancyAnalyzer()


@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard summary with real-time parking overview."""
    service = ParkingService(db)
    return await service.get_dashboard_summary()


@router.get("/zones/{zone_id}", response_model=ZoneAnalytics)
async def get_zone_analytics(
    zone_id: int,
    days: int = Query(7, ge=1, le=90, description="Lookback period in days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed analytics for a specific zone."""
    service = ParkingService(db)
    analytics = await service.get_zone_analytics(zone_id, days=days)
    if not analytics:
        raise HTTPException(status_code=404, detail="Zone not found")
    return analytics


@router.get("/occupancy-trend")
async def get_occupancy_trend(
    zone_id: int = Query(..., description="Zone ID"),
    hours: int = Query(24, ge=1, le=168, description="Hours of history"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get occupancy trend data for charting.

    Returns raw + EMA-smoothed time series for the specified zone.
    Uses Exponential Moving Average (EMA) for trend smoothing.
    """
    start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    result = await db.execute(
        select(OccupancySnapshot)
        .where(
            OccupancySnapshot.zone_id == zone_id,
            OccupancySnapshot.timestamp >= start_time,
        )
        .order_by(OccupancySnapshot.timestamp)
    )
    snapshots = list(result.scalars().all())

    if not snapshots:
        return {"raw": [], "smoothed": [], "anomalies": []}

    raw_rates = [s.occupancy_rate for s in snapshots]
    timestamps = [s.timestamp.isoformat() for s in snapshots]

    # EMA smoothing
    smoothed = analyzer.compute_ema(raw_rates, alpha=0.3)

    # Anomaly detection
    anomalies = analyzer.detect_anomalies(raw_rates, window_size=12)
    anomaly_points = [
        {
            "timestamp": timestamps[i],
            "value": raw_rates[i],
            "z_score": a.z_score,
            "severity": a.severity,
        }
        for i, a in enumerate(anomalies)
        if a.is_anomaly
    ]

    return {
        "raw": [
            {"timestamp": t, "occupancy_rate": r}
            for t, r in zip(timestamps, raw_rates)
        ],
        "smoothed": [
            {"timestamp": t, "occupancy_rate": round(s, 2)}
            for t, s in zip(timestamps, smoothed)
        ],
        "anomalies": anomaly_points,
    }


@router.get("/forecast")
async def get_occupancy_forecast(
    zone_id: int = Query(..., description="Zone ID"),
    horizon: int = Query(24, ge=1, le=72, description="Forecast horizon in hours"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Forecast future occupancy using seasonal decomposition.

    Theory: Combines hourly seasonal averages with recent trend
    to produce point forecasts with 95% confidence intervals.
    """
    # Get historical data (last 7 days)
    start_time = datetime.now(timezone.utc) - timedelta(days=7)

    result = await db.execute(
        select(OccupancySnapshot)
        .where(
            OccupancySnapshot.zone_id == zone_id,
            OccupancySnapshot.timestamp >= start_time,
        )
        .order_by(OccupancySnapshot.timestamp)
    )
    snapshots = list(result.scalars().all())

    rates = [s.occupancy_rate for s in snapshots]
    timestamps = [s.timestamp for s in snapshots]

    forecast = analyzer.forecast_occupancy(rates, timestamps, horizon_hours=horizon)

    return {
        "zone_id": zone_id,
        "forecast": [
            {
                "timestamp": t.isoformat(),
                "predicted": p,
                "lower_bound": l,
                "upper_bound": u,
            }
            for t, p, l, u in zip(
                forecast.timestamps,
                forecast.predicted_occupancy,
                forecast.confidence_lower,
                forecast.confidence_upper,
            )
        ],
    }


@router.get("/peak-hours")
async def get_peak_hours(
    zone_id: int = Query(...),
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Identify peak utilization hours for a zone."""
    start_time = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(OccupancySnapshot)
        .where(
            OccupancySnapshot.zone_id == zone_id,
            OccupancySnapshot.timestamp >= start_time,
        )
        .order_by(OccupancySnapshot.timestamp)
    )
    snapshots = list(result.scalars().all())

    if not snapshots:
        return {"peak_hours": [], "message": "No data available"}

    rates = [s.occupancy_rate for s in snapshots]
    timestamps = [s.timestamp for s in snapshots]

    peaks = analyzer.find_peak_hours(rates, timestamps, top_n=5)
    return {"zone_id": zone_id, "period_days": days, "peak_hours": peaks}


@router.get("/arrival-rate")
async def get_arrival_rate(
    zone_id: int = Query(...),
    hours: int = Query(4, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Estimate vehicle arrival rate using Poisson process model."""
    start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    result = await db.execute(
        select(ParkingEvent)
        .where(
            ParkingEvent.zone_id == zone_id,
            ParkingEvent.event_type == "entry",
            ParkingEvent.timestamp >= start_time,
        )
        .order_by(ParkingEvent.timestamp)
    )
    events = list(result.scalars().all())
    timestamps = [e.timestamp for e in events]

    rate_info = analyzer.estimate_arrival_rate(timestamps)

    return {
        "zone_id": zone_id,
        "period_hours": hours,
        "total_arrivals": len(events),
        **rate_info,
    }
