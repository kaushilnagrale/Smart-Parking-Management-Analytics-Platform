"""Occupancy analytics, anomaly detection, and time-series forecasting.

Data Science Theory applied:
- Exponential Moving Average (EMA) for real-time trend smoothing
- Z-Score anomaly detection for unusual occupancy patterns
- Kernel Density Estimation (KDE) for utilization heatmaps
- Poisson process modeling for vehicle arrival rates
- Simple SARIMA-style forecasting for occupancy prediction
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

import numpy as np
from loguru import logger

try:
    from scipy import stats
    from scipy.ndimage import gaussian_filter
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


@dataclass
class AnomalyResult:
    is_anomaly: bool
    z_score: float
    expected_value: float
    actual_value: float
    severity: str  # "low", "medium", "high"


@dataclass
class ForecastResult:
    timestamps: List[datetime]
    predicted_occupancy: List[float]
    confidence_lower: List[float]
    confidence_upper: List[float]


class OccupancyAnalyzer:
    """Real-time and historical occupancy analysis engine."""

    def __init__(self):
        self.ema_alpha = 0.3  # EMA smoothing factor
        self.anomaly_threshold = 2.5  # Z-score threshold

    # ─── Exponential Moving Average ────────────────────────────────────

    def compute_ema(self, data: List[float], alpha: float = None) -> List[float]:
        """Compute Exponential Moving Average.

        EMA_t = α · x_t + (1 - α) · EMA_{t-1}

        Higher α = more weight on recent observations (faster response).
        Lower α = more smoothing (slower response to changes).
        """
        a = alpha or self.ema_alpha
        if not data:
            return []

        ema = [data[0]]
        for i in range(1, len(data)):
            ema.append(a * data[i] + (1 - a) * ema[-1])
        return ema

    # ─── Z-Score Anomaly Detection ─────────────────────────────────────

    def detect_anomalies(
        self, values: List[float], window_size: int = 24
    ) -> List[AnomalyResult]:
        """Detect anomalies using rolling Z-score method.

        Z = (x - μ) / σ

        An observation is flagged anomalous if |Z| > threshold.
        Uses a rolling window to adapt to time-varying baselines.
        """
        results = []
        arr = np.array(values)

        for i in range(len(arr)):
            start = max(0, i - window_size)
            window = arr[start:i + 1]

            if len(window) < 3:
                results.append(AnomalyResult(
                    is_anomaly=False, z_score=0.0,
                    expected_value=float(arr[i]), actual_value=float(arr[i]),
                    severity="low"
                ))
                continue

            mean = np.mean(window[:-1]) if len(window) > 1 else window[0]
            std = np.std(window[:-1]) if len(window) > 1 else 1.0
            std = max(std, 1e-6)  # Avoid division by zero

            z_score = (arr[i] - mean) / std

            is_anomaly = abs(z_score) > self.anomaly_threshold
            severity = "low"
            if abs(z_score) > 4.0:
                severity = "high"
            elif abs(z_score) > 3.0:
                severity = "medium"

            results.append(AnomalyResult(
                is_anomaly=is_anomaly,
                z_score=round(float(z_score), 4),
                expected_value=round(float(mean), 2),
                actual_value=float(arr[i]),
                severity=severity if is_anomaly else "low",
            ))

        return results

    # ─── Kernel Density Estimation (Heatmap) ───────────────────────────

    def generate_heatmap(
        self,
        zone_positions: List[Tuple[float, float]],
        occupancy_rates: List[float],
        grid_size: int = 50,
    ) -> np.ndarray:
        """Generate occupancy density heatmap using KDE.

        KDE: f̂(x) = (1/nh) · Σ K((x - xᵢ)/h)

        where K is Gaussian kernel and h is bandwidth.
        Uses scipy's gaussian_kde for 2D density estimation.
        """
        if not SCIPY_AVAILABLE or len(zone_positions) < 2:
            return np.zeros((grid_size, grid_size))

        positions = np.array(zone_positions)
        weights = np.array(occupancy_rates)

        # Create grid
        x_min, x_max = positions[:, 0].min() - 0.01, positions[:, 0].max() + 0.01
        y_min, y_max = positions[:, 1].min() - 0.01, positions[:, 1].max() + 0.01

        x_grid = np.linspace(x_min, x_max, grid_size)
        y_grid = np.linspace(y_min, y_max, grid_size)
        xx, yy = np.meshgrid(x_grid, y_grid)

        # KDE with weighted samples
        try:
            kernel = stats.gaussian_kde(
                positions.T, weights=weights, bw_method="scott"
            )
            grid_points = np.vstack([xx.ravel(), yy.ravel()])
            density = kernel(grid_points).reshape(grid_size, grid_size)

            # Normalize to 0-100 scale
            if density.max() > 0:
                density = (density / density.max()) * 100

            return density
        except Exception as e:
            logger.error(f"KDE computation failed: {e}")
            return np.zeros((grid_size, grid_size))

    # ─── Poisson Arrival Rate Estimation ───────────────────────────────

    def estimate_arrival_rate(
        self, event_timestamps: List[datetime], interval_minutes: int = 60
    ) -> Dict[str, float]:
        """Estimate vehicle arrival rate using Poisson process model.

        P(N(t) = k) = (λt)^k · e^(-λt) / k!

        Returns λ (rate parameter) and derived statistics.
        """
        if len(event_timestamps) < 2:
            return {"lambda": 0.0, "expected_per_hour": 0.0, "std_dev": 0.0}

        # Calculate inter-arrival times
        sorted_times = sorted(event_timestamps)
        inter_arrivals = [
            (sorted_times[i + 1] - sorted_times[i]).total_seconds() / 60.0
            for i in range(len(sorted_times) - 1)
        ]

        if not inter_arrivals or np.mean(inter_arrivals) == 0:
            return {"lambda": 0.0, "expected_per_hour": 0.0, "std_dev": 0.0}

        # MLE for Poisson: λ̂ = n / T (count / total time)
        total_time_hours = (sorted_times[-1] - sorted_times[0]).total_seconds() / 3600.0
        total_time_hours = max(total_time_hours, 1 / 60)  # Minimum 1 minute

        lambda_rate = len(event_timestamps) / total_time_hours

        return {
            "lambda": round(lambda_rate, 4),
            "expected_per_hour": round(lambda_rate, 2),
            "std_dev": round(np.sqrt(lambda_rate), 4),
            "mean_inter_arrival_min": round(float(np.mean(inter_arrivals)), 2),
        }

    # ─── Simple Occupancy Forecasting ──────────────────────────────────

    def forecast_occupancy(
        self,
        historical_rates: List[float],
        timestamps: List[datetime],
        horizon_hours: int = 24,
    ) -> ForecastResult:
        """Simple occupancy forecasting using seasonal decomposition.

        Approach:
        1. Compute hourly averages (seasonal component)
        2. Compute recent trend using linear regression
        3. Combine: forecast = seasonal_avg + trend_adjustment
        4. Confidence intervals using historical variance

        For production, replace with SARIMA or Prophet.
        """
        if len(historical_rates) < 24:
            # Not enough data — return flat forecast
            now = datetime.now(timezone.utc)
            future_times = [now + timedelta(hours=i) for i in range(horizon_hours)]
            current_rate = historical_rates[-1] if historical_rates else 50.0
            return ForecastResult(
                timestamps=future_times,
                predicted_occupancy=[current_rate] * horizon_hours,
                confidence_lower=[max(0, current_rate - 15)] * horizon_hours,
                confidence_upper=[min(100, current_rate + 15)] * horizon_hours,
            )

        rates = np.array(historical_rates)
        times = np.array(timestamps)

        # Step 1: Hourly seasonal averages
        hourly_avg = {}
        hourly_std = {}
        for rate, ts in zip(rates, times):
            hour = ts.hour
            if hour not in hourly_avg:
                hourly_avg[hour] = []
            hourly_avg[hour].append(rate)

        for hour in hourly_avg:
            values = hourly_avg[hour]
            hourly_std[hour] = float(np.std(values)) if len(values) > 1 else 10.0
            hourly_avg[hour] = float(np.mean(values))

        # Step 2: Recent trend (last 6 hours linear regression)
        recent = rates[-6:] if len(rates) >= 6 else rates
        x = np.arange(len(recent))
        if len(recent) >= 2:
            slope = np.polyfit(x, recent, 1)[0]
        else:
            slope = 0.0

        # Step 3: Generate forecast
        now = datetime.now(timezone.utc)
        forecast_times = []
        forecast_values = []
        conf_lower = []
        conf_upper = []

        for i in range(horizon_hours):
            future_time = now + timedelta(hours=i + 1)
            hour = future_time.hour

            # Seasonal baseline + decaying trend
            baseline = hourly_avg.get(hour, 50.0)
            trend_adj = slope * (i + 1) * 0.5  # Decay the trend
            predicted = np.clip(baseline + trend_adj, 0, 100)

            std = hourly_std.get(hour, 10.0)
            ci_width = std * 1.96  # 95% confidence interval

            forecast_times.append(future_time)
            forecast_values.append(round(float(predicted), 2))
            conf_lower.append(round(max(0, float(predicted - ci_width)), 2))
            conf_upper.append(round(min(100, float(predicted + ci_width)), 2))

        return ForecastResult(
            timestamps=forecast_times,
            predicted_occupancy=forecast_values,
            confidence_lower=conf_lower,
            confidence_upper=conf_upper,
        )

    # ─── Peak Hour Analysis ────────────────────────────────────────────

    def find_peak_hours(
        self, rates: List[float], timestamps: List[datetime], top_n: int = 3
    ) -> List[Dict]:
        """Identify peak utilization hours from historical data."""
        hourly_data = {}
        for rate, ts in zip(rates, timestamps):
            hour = ts.hour
            if hour not in hourly_data:
                hourly_data[hour] = []
            hourly_data[hour].append(rate)

        hourly_averages = {
            hour: np.mean(values)
            for hour, values in hourly_data.items()
        }

        sorted_hours = sorted(hourly_averages.items(), key=lambda x: x[1], reverse=True)

        return [
            {
                "hour": hour,
                "avg_occupancy_rate": round(float(avg), 2),
                "label": f"{hour:02d}:00 - {(hour + 1) % 24:02d}:00",
            }
            for hour, avg in sorted_hours[:top_n]
        ]
