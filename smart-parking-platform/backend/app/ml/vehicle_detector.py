"""Vehicle detection using YOLOv8 with OpenCV preprocessing."""

import time
from typing import List, Dict, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

import cv2
import numpy as np
from loguru import logger

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("ultralytics not installed — using mock detector")

from app.core.config import get_settings

settings = get_settings()

# COCO classes for vehicles
VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


@dataclass
class DetectedVehicle:
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    vehicle_class: str
    confidence: float
    center: Tuple[int, int]


class VehicleDetector:
    """YOLOv8-based vehicle detection with preprocessing pipeline.

    Data Science Theory:
    - Uses YOLOv8 (single-shot detector) for real-time object detection
    - Preprocessing: Gaussian blur for noise reduction, histogram equalization
    - Non-Maximum Suppression (NMS) to eliminate overlapping detections
    - Confidence thresholding to filter weak predictions
    """

    def __init__(self, model_path: str = None, confidence_threshold: float = None):
        self.confidence_threshold = confidence_threshold or settings.CONFIDENCE_THRESHOLD
        self.model = None

        if YOLO_AVAILABLE:
            try:
                model_file = model_path or settings.YOLO_MODEL
                self.model = YOLO(model_file)
                logger.info(f"YOLOv8 model loaded: {model_file}")
            except Exception as e:
                logger.warning(f"Failed to load YOLO model: {e}. Using mock detector.")

    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """Apply preprocessing pipeline to improve detection quality.

        Steps:
        1. Gaussian Blur — reduces noise (kernel-based convolution)
        2. CLAHE — adaptive histogram equalization for contrast normalization
        3. Resize — normalize input dimensions for consistent inference
        """
        # Gaussian blur for noise reduction: G(x,y) = (1/2πσ²)·exp(-(x²+y²)/2σ²)
        denoised = cv2.GaussianBlur(frame, (3, 3), 0)

        # Convert to LAB color space for CLAHE (Contrast Limited Adaptive Hist. Eq.)
        lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l_channel)

        merged = cv2.merge([cl, a, b])
        enhanced = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

        return enhanced

    def detect(self, frame: np.ndarray) -> List[DetectedVehicle]:
        """Run vehicle detection on a single frame.

        Returns list of detected vehicles with bounding boxes and confidence scores.
        Uses Non-Maximum Suppression (NMS) internally via YOLO to handle overlaps.
        """
        start_time = time.time()
        processed = self.preprocess_frame(frame)
        vehicles = []

        if self.model is not None:
            # YOLOv8 inference
            results = self.model(processed, verbose=False)

            for result in results:
                boxes = result.boxes
                for box in boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])

                    if cls_id in VEHICLE_CLASSES and conf >= self.confidence_threshold:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2

                        vehicles.append(DetectedVehicle(
                            bbox=(x1, y1, x2, y2),
                            vehicle_class=VEHICLE_CLASSES[cls_id],
                            confidence=round(conf, 4),
                            center=(center_x, center_y),
                        ))
        else:
            # Mock detection for development/testing
            vehicles = self._mock_detect(frame)

        elapsed = (time.time() - start_time) * 1000
        logger.debug(f"Detection: {len(vehicles)} vehicles in {elapsed:.1f}ms")
        return vehicles

    def count_by_type(self, vehicles: List[DetectedVehicle]) -> Dict[str, int]:
        """Aggregate vehicle counts by type."""
        counts = {"car": 0, "truck": 0, "motorcycle": 0, "bus": 0}
        for v in vehicles:
            if v.vehicle_class in counts:
                counts[v.vehicle_class] += 1
        return counts

    def annotate_frame(self, frame: np.ndarray, vehicles: List[DetectedVehicle]) -> np.ndarray:
        """Draw bounding boxes and labels on frame for visualization."""
        annotated = frame.copy()
        colors = {
            "car": (0, 255, 0),
            "truck": (255, 165, 0),
            "motorcycle": (255, 255, 0),
            "bus": (0, 0, 255),
        }

        for v in vehicles:
            x1, y1, x2, y2 = v.bbox
            color = colors.get(v.vehicle_class, (255, 255, 255))
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label = f"{v.vehicle_class} {v.confidence:.2f}"
            cv2.putText(
                annotated, label, (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2,
            )

        # Add count overlay
        total = len(vehicles)
        cv2.putText(
            annotated, f"Vehicles: {total}",
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2,
        )
        return annotated

    def _mock_detect(self, frame: np.ndarray) -> List[DetectedVehicle]:
        """Generate mock detections for testing without a real model."""
        h, w = frame.shape[:2]
        np.random.seed(int(time.time()) % 1000)
        count = np.random.randint(2, 8)
        vehicles = []
        for _ in range(count):
            x1 = np.random.randint(0, w - 100)
            y1 = np.random.randint(0, h - 80)
            x2 = x1 + np.random.randint(60, 150)
            y2 = y1 + np.random.randint(40, 100)
            cls = np.random.choice(list(VEHICLE_CLASSES.values()))
            conf = round(np.random.uniform(0.6, 0.98), 4)
            vehicles.append(DetectedVehicle(
                bbox=(x1, y1, min(x2, w), min(y2, h)),
                vehicle_class=cls,
                confidence=conf,
                center=((x1 + x2) // 2, (y1 + y2) // 2),
            ))
        return vehicles
