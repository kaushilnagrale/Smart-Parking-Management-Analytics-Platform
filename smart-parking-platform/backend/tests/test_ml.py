"""Test suite for Smart Parking Platform API."""

import pytest
import numpy as np
from datetime import datetime, timedelta, timezone

from app.ml.vehicle_detector import VehicleDetector
from app.ml.plate_recognizer import LicensePlateRecognizer
from app.ml.occupancy_analyzer import OccupancyAnalyzer


# ─── Vehicle Detection Tests ──────────────────────────────────────────

class TestVehicleDetector:
    def setup_method(self):
        self.detector = VehicleDetector()

    def test_preprocess_frame(self):
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        processed = self.detector.preprocess_frame(frame)
        assert processed.shape == frame.shape
        assert processed.dtype == np.uint8

    def test_mock_detect(self):
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        vehicles = self.detector.detect(frame)
        assert isinstance(vehicles, list)
        assert len(vehicles) > 0

        for v in vehicles:
            assert v.vehicle_class in ("car", "truck", "motorcycle", "bus")
            assert 0 < v.confidence <= 1.0
            assert len(v.bbox) == 4
            assert len(v.center) == 2

    def test_count_by_type(self):
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        vehicles = self.detector.detect(frame)
        counts = self.detector.count_by_type(vehicles)
        assert "car" in counts
        assert sum(counts.values()) == len(vehicles)

    def test_annotate_frame(self):
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        vehicles = self.detector.detect(frame)
        annotated = self.detector.annotate_frame(frame, vehicles)
        assert annotated.shape == frame.shape


# ─── License Plate Recognition Tests ──────────────────────────────────

class TestPlateRecognizer:
    def setup_method(self):
        self.recognizer = LicensePlateRecognizer()

    def test_preprocess_for_plate_detection(self):
        image = np.random.randint(0, 255, (200, 400, 3), dtype=np.uint8)
        processed = self.recognizer.preprocess_for_plate_detection(image)
        assert len(processed.shape) == 2  # Grayscale
        assert processed.shape[0] == 200
        assert processed.shape[1] == 400

    def test_clean_plate_text(self):
        assert self.recognizer._clean_plate_text("ABC1234") == "ABC1234"
        assert self.recognizer._clean_plate_text("AB-C 12.34") == "ABC1234"
        assert self.recognizer._clean_plate_text("abc1234") == "ABC1234"

    def test_mock_recognize(self):
        text, conf = self.recognizer._mock_recognize()
        assert len(text) == 7
        assert 0 < conf <= 1.0


# ─── Occupancy Analyzer Tests ─────────────────────────────────────────

class TestOccupancyAnalyzer:
    def setup_method(self):
        self.analyzer = OccupancyAnalyzer()

    def test_compute_ema(self):
        data = [10, 20, 30, 40, 50]
        ema = self.analyzer.compute_ema(data, alpha=0.5)
        assert len(ema) == len(data)
        assert ema[0] == 10  # First value unchanged
        # EMA should be smoothed
        assert all(isinstance(v, float) or isinstance(v, int) for v in ema)

    def test_compute_ema_empty(self):
        assert self.analyzer.compute_ema([]) == []

    def test_detect_anomalies(self):
        # Normal values with one outlier
        values = [50.0] * 20 + [95.0] + [50.0] * 5
        anomalies = self.analyzer.detect_anomalies(values, window_size=10)
        assert len(anomalies) == len(values)
        # The spike at index 20 should be flagged
        assert anomalies[20].is_anomaly == True
        assert anomalies[20].z_score > 2.0

    def test_detect_anomalies_no_anomalies(self):
        values = [50.0 + np.random.normal(0, 1) for _ in range(50)]
        anomalies = self.analyzer.detect_anomalies(values)
        anomaly_count = sum(1 for a in anomalies if a.is_anomaly)
        # Very few should be flagged (statistical noise)
        assert anomaly_count < 5

    def test_estimate_arrival_rate(self):
        now = datetime.now(timezone.utc)
        timestamps = [now + timedelta(minutes=i * 5) for i in range(20)]
        rate = self.analyzer.estimate_arrival_rate(timestamps)
        assert "lambda" in rate
        assert rate["lambda"] > 0
        assert rate["expected_per_hour"] > 0

    def test_estimate_arrival_rate_empty(self):
        rate = self.analyzer.estimate_arrival_rate([])
        assert rate["lambda"] == 0.0

    def test_forecast_occupancy_insufficient_data(self):
        forecast = self.analyzer.forecast_occupancy(
            [50.0, 60.0], [datetime.now(timezone.utc)] * 2, horizon_hours=6
        )
        assert len(forecast.timestamps) == 6
        assert all(0 <= p <= 100 for p in forecast.predicted_occupancy)

    def test_forecast_occupancy_full(self):
        now = datetime.now(timezone.utc)
        rates = [40 + 20 * np.sin(i / 4) + np.random.normal(0, 3) for i in range(168)]
        timestamps = [now - timedelta(hours=168 - i) for i in range(168)]

        forecast = self.analyzer.forecast_occupancy(rates, timestamps, horizon_hours=24)
        assert len(forecast.timestamps) == 24
        assert len(forecast.predicted_occupancy) == 24
        assert len(forecast.confidence_lower) == 24
        assert len(forecast.confidence_upper) == 24

        # Confidence intervals should contain the prediction
        for pred, lower, upper in zip(
            forecast.predicted_occupancy,
            forecast.confidence_lower,
            forecast.confidence_upper,
        ):
            assert lower <= pred <= upper

    def test_find_peak_hours(self):
        now = datetime.now(timezone.utc)
        rates = []
        timestamps = []
        for i in range(168):
            ts = now - timedelta(hours=168 - i)
            hour = ts.hour
            if 9 <= hour <= 11:
                rate = 85.0
            elif 17 <= hour <= 19:
                rate = 80.0
            else:
                rate = 40.0
            rates.append(rate)
            timestamps.append(ts)

        peaks = self.analyzer.find_peak_hours(rates, timestamps, top_n=3)
        assert len(peaks) == 3
        assert peaks[0]["avg_occupancy_rate"] > peaks[-1]["avg_occupancy_rate"]
        # Peak hours should be in the 9-11 or 17-19 range
        peak_hours = [p["hour"] for p in peaks]
        assert any(9 <= h <= 11 for h in peak_hours)


# ─── Heatmap Tests ─────────────────────────────────────────────────────

class TestHeatmap:
    def setup_method(self):
        self.analyzer = OccupancyAnalyzer()

    def test_generate_heatmap(self):
        positions = [(33.42, -111.94), (33.43, -111.93), (33.42, -111.95)]
        rates = [80.0, 50.0, 30.0]
        heatmap = self.analyzer.generate_heatmap(positions, rates, grid_size=20)
        assert heatmap.shape == (20, 20)

    def test_generate_heatmap_insufficient_data(self):
        heatmap = self.analyzer.generate_heatmap([(0, 0)], [50.0], grid_size=10)
        assert heatmap.shape == (10, 10)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
