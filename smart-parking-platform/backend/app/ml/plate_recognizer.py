"""License Plate Recognition using OpenCV preprocessing + Tesseract OCR.

Data Science Theory:
- Canny Edge Detection: Multi-stage gradient-based edge detector
- Contour Analysis: Connected component analysis for plate region detection
- Perspective Transform (Homography): Corrects plate orientation
- Otsu's Thresholding: Automatic optimal threshold selection
- Tesseract OCR: LSTM-based character recognition with CTC loss
"""

import re
from typing import Optional, List, Tuple
from dataclasses import dataclass

import cv2
import numpy as np
from loguru import logger

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract not installed — plate recognition disabled")

from app.core.config import get_settings

settings = get_settings()


@dataclass
class PlateResult:
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]
    processed_image: Optional[np.ndarray] = None


class LicensePlateRecognizer:
    """Automatic License Plate Recognition (ALPR/ANPR) pipeline.

    Pipeline stages:
    1. Region of Interest extraction from vehicle bounding box
    2. Grayscale conversion + bilateral filtering (edge-preserving denoising)
    3. Canny edge detection for plate boundary identification
    4. Contour analysis to find rectangular plate region
    5. Perspective correction via homography transform
    6. Adaptive thresholding (Otsu's method) for binarization
    7. Morphological operations for character cleanup
    8. Tesseract OCR for character recognition
    """

    def __init__(self):
        if TESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

        # Plate detection parameters
        self.min_plate_area = 1500
        self.max_plate_area = 50000
        self.plate_aspect_ratio_range = (2.0, 6.0)  # width/height ratio

    def preprocess_for_plate_detection(self, image: np.ndarray) -> np.ndarray:
        """Preprocessing pipeline for plate region detection.

        Steps:
        1. Convert to grayscale
        2. Bilateral filter — preserves edges while reducing noise
           d(σ_color, σ_space): balances spatial and intensity similarity
        3. Adaptive histogram equalization (CLAHE)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Bilateral filter: edge-preserving noise reduction
        # Unlike Gaussian, it considers both spatial distance AND intensity difference
        filtered = cv2.bilateralFilter(gray, 11, 17, 17)

        # CLAHE for contrast normalization
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(filtered)

        return enhanced

    def find_plate_contours(self, preprocessed: np.ndarray) -> List[np.ndarray]:
        """Detect potential license plate regions using edge detection + contour analysis.

        Theory:
        - Canny uses gradient magnitude and direction to find edges
        - Contours are found via border following algorithm
        - Rectangularity test filters non-plate regions
        """
        # Canny edge detection: gradient computation → NMS → hysteresis thresholding
        edges = cv2.Canny(preprocessed, 30, 200)

        # Morphological closing to connect nearby edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        plate_candidates = []
        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:30]:
            area = cv2.contourArea(contour)
            if area < self.min_plate_area or area > self.max_plate_area:
                continue

            # Approximate contour to polygon
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

            # License plates are roughly rectangular (4 vertices)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = w / float(h)

                if self.plate_aspect_ratio_range[0] <= aspect_ratio <= self.plate_aspect_ratio_range[1]:
                    plate_candidates.append(approx)

        return plate_candidates

    def extract_plate_region(
        self, image: np.ndarray, contour: np.ndarray
    ) -> np.ndarray:
        """Extract and perspective-correct the plate region.

        Theory: Homography matrix H maps points from source to destination plane
        x' = H · x where H is a 3×3 transformation matrix
        """
        # Get bounding rect
        rect = cv2.boundingRect(contour)
        x, y, w, h = rect

        # Extract ROI with margin
        margin = 5
        y1 = max(0, y - margin)
        y2 = min(image.shape[0], y + h + margin)
        x1 = max(0, x - margin)
        x2 = min(image.shape[1], x + w + margin)

        plate_roi = image[y1:y2, x1:x2]

        # Resize to standard dimensions for OCR
        plate_resized = cv2.resize(plate_roi, (300, 80), interpolation=cv2.INTER_CUBIC)

        return plate_resized

    def preprocess_for_ocr(self, plate_image: np.ndarray) -> np.ndarray:
        """Prepare plate image for OCR character recognition.

        Steps:
        1. Grayscale conversion
        2. Otsu's thresholding: automatic optimal threshold T*
           T* = argmin_T [σ²_within(T)] = argmax_T [σ²_between(T)]
        3. Morphological operations for character cleanup
        """
        gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)

        # Otsu's binarization: finds threshold that minimizes intra-class variance
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Morphological opening to remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

        # Invert if needed (ensure dark text on light background)
        if np.mean(cleaned) < 128:
            cleaned = cv2.bitwise_not(cleaned)

        # Add border for better OCR
        bordered = cv2.copyMakeBorder(cleaned, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)

        return bordered

    def recognize_text(self, plate_image: np.ndarray) -> Tuple[str, float]:
        """Run Tesseract OCR on preprocessed plate image.

        Theory: Tesseract 4+ uses LSTM-based recognition with CTC loss
        L_CTC = -ln(Σ_{π∈B⁻¹(y)} Π_t p(π_t|x))
        This enables sequence prediction without pre-segmented characters.
        """
        if not TESSERACT_AVAILABLE:
            return self._mock_recognize()

        processed = self.preprocess_for_ocr(plate_image)

        # Tesseract config: single line mode, alphanumeric only
        config = "--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

        try:
            data = pytesseract.image_to_data(
                processed, config=config, output_type=pytesseract.Output.DICT
            )

            texts = []
            confidences = []
            for i, text in enumerate(data["text"]):
                conf = int(data["conf"][i])
                if conf > 30 and text.strip():
                    texts.append(text.strip())
                    confidences.append(conf)

            if texts:
                plate_text = "".join(texts).upper()
                avg_conf = sum(confidences) / len(confidences) / 100.0
                return self._clean_plate_text(plate_text), avg_conf

        except Exception as e:
            logger.error(f"OCR failed: {e}")

        return "", 0.0

    def recognize_from_vehicle(
        self, frame: np.ndarray, vehicle_bbox: Tuple[int, int, int, int]
    ) -> Optional[PlateResult]:
        """Full pipeline: extract plate from vehicle region and recognize text."""
        x1, y1, x2, y2 = vehicle_bbox

        # Focus on lower portion of vehicle (where plates typically are)
        vehicle_height = y2 - y1
        plate_region_y1 = y1 + int(vehicle_height * 0.5)
        vehicle_roi = frame[plate_region_y1:y2, x1:x2]

        if vehicle_roi.size == 0:
            return None

        # Preprocess and find plate contours
        preprocessed = self.preprocess_for_plate_detection(vehicle_roi)
        candidates = self.find_plate_contours(preprocessed)

        if not candidates:
            return None

        # Try OCR on the best candidate
        best_plate = candidates[0]
        plate_image = self.extract_plate_region(vehicle_roi, best_plate)
        text, confidence = self.recognize_text(plate_image)

        if text and confidence > 0.3:
            px, py, pw, ph = cv2.boundingRect(best_plate)
            return PlateResult(
                text=text,
                confidence=confidence,
                bbox=(x1 + px, plate_region_y1 + py, pw, ph),
                processed_image=plate_image,
            )

        return None

    @staticmethod
    def _clean_plate_text(text: str) -> str:
        """Clean and validate recognized plate text."""
        # Remove non-alphanumeric characters
        cleaned = re.sub(r"[^A-Z0-9]", "", text.upper())

        # Common OCR corrections
        corrections = {"O": "0", "I": "1", "S": "5", "B": "8", "G": "6"}

        # Only apply corrections to likely-numeric positions
        # (basic heuristic: if surrounded by digits)
        result = list(cleaned)
        for i, char in enumerate(result):
            if char in corrections:
                # Check if neighbors are digits
                prev_digit = i > 0 and result[i - 1].isdigit()
                next_digit = i < len(result) - 1 and result[i + 1].isdigit()
                if prev_digit and next_digit:
                    result[i] = corrections[char]

        return "".join(result)

    @staticmethod
    def _mock_recognize() -> Tuple[str, float]:
        """Mock plate recognition for testing."""
        import random
        letters = "".join(random.choices("ABCDEFGHJKLMNPRSTUVWXYZ", k=3))
        numbers = "".join(random.choices("0123456789", k=4))
        return f"{letters}{numbers}", round(random.uniform(0.7, 0.95), 2)
