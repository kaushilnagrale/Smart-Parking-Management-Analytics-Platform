"""Parking events and ML detection API endpoints."""

import time
import io
import base64
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import cv2
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_operator
from app.models.user import User
from app.schemas import ParkingEventCreate, ParkingEventResponse, DetectionResult
from app.services import ParkingService
from app.ml.vehicle_detector import VehicleDetector
from app.ml.plate_recognizer import LicensePlateRecognizer

router = APIRouter(prefix="/events", tags=["Parking Events"])

# Initialize ML models (singleton pattern)
vehicle_detector = VehicleDetector()
plate_recognizer = LicensePlateRecognizer()


@router.post("/", response_model=ParkingEventResponse, status_code=201)
async def create_event(
    event_data: ParkingEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_operator),
):
    """Record a parking event (entry/exit)."""
    service = ParkingService(db)
    try:
        event = await service.record_event(event_data)
        return event
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=list[ParkingEventResponse])
async def list_events(
    zone_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List recent parking events with optional zone filter."""
    service = ParkingService(db)
    events = await service.get_events(zone_id=zone_id, limit=limit)
    return events


@router.post("/detect", response_model=DetectionResult)
async def detect_vehicles(
    file: UploadFile = File(..., description="Camera frame image (JPEG/PNG)"),
    zone_id: Optional[int] = Query(None, description="Zone ID for context"),
    current_user: User = Depends(get_current_operator),
):
    """Run vehicle detection + license plate recognition on uploaded frame.

    ML Pipeline:
    1. YOLOv8 object detection → vehicle bounding boxes
    2. For each vehicle → license plate detection & OCR
    3. Returns structured detection results
    """
    start_time = time.time()

    # Read and decode image
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image file")

    # Step 1: Vehicle detection
    vehicles = vehicle_detector.detect(frame)

    # Step 2: License plate recognition for each vehicle
    license_plates = []
    vehicle_data = []

    for v in vehicles:
        plate_result = plate_recognizer.recognize_from_vehicle(frame, v.bbox)
        plate_text = plate_result.text if plate_result else None

        if plate_text:
            license_plates.append(plate_text)

        vehicle_data.append({
            "bbox": list(v.bbox),
            "class": v.vehicle_class,
            "confidence": v.confidence,
            "center": list(v.center),
            "license_plate": plate_text,
        })

    elapsed_ms = (time.time() - start_time) * 1000

    return DetectionResult(
        vehicle_count=len(vehicles),
        vehicles=vehicle_data,
        license_plates=license_plates,
        frame_timestamp=datetime.now(timezone.utc),
        processing_time_ms=round(elapsed_ms, 2),
    )


@router.post("/detect/annotated")
async def detect_and_annotate(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_operator),
):
    """Detect vehicles and return annotated image as base64."""
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image file")

    vehicles = vehicle_detector.detect(frame)
    annotated = vehicle_detector.annotate_frame(frame, vehicles)

    # Encode to base64 JPEG
    _, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
    img_base64 = base64.b64encode(buffer).decode("utf-8")

    return {
        "image": f"data:image/jpeg;base64,{img_base64}",
        "vehicle_count": len(vehicles),
        "detections": [
            {"class": v.vehicle_class, "confidence": v.confidence}
            for v in vehicles
        ],
    }
