# -*- coding: utf-8 -*-
"""
Custom Horizontal Pod Autoscaler (HPA) Controller for AIOps Platform
Provides intelligent autoscaling based on custom metrics, predictive forecasting, and ML models
"""

import logging
import statistics
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ScaleDirection(Enum):
    """Scale direction enumeration"""

    UP = "up"
    DOWN = "down"
    NONE = "none"


@dataclass
class MetricData:
    """Represents metric data point"""

    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
        }


@dataclass
class ScalingDecision:
    """Represents a scaling decision"""

    resource: str
    current_replicas: int
    desired_replicas: int
    direction: ScaleDirection
    reason: str
    confidence: float
    metrics: List[MetricData]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "resource": self.resource,
            "current_replicas": self.current_replicas,
            "desired_replicas": self.desired_replicas,
            "direction": self.direction.value,
            "reason": self.reason,
            "confidence": self.confidence,
            "metrics": [m.to_dict() for m in self.metrics],
        }


class CustomHPAController:
    """
    Custom HPA Controller

    Provides intelligent autoscaling based on:
    - Custom metrics (application-level, business metrics)
    - Predictive forecasting
    - ML-based anomaly detection
    - Multi-metric evaluation
    - Rate limiting and cooldown periods
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Custom HPA Controller

        Args:
            config: Configuration dictionary containing:
                - scale_up_threshold: Scale up threshold (default: 0.8)
                - scale_down_threshold: Scale down threshold (default: 0.3)
                - max_replicas: Maximum replicas (default: 10)
                - min_replicas: Minimum replicas (default: 1)
                - scale_up_cooldown: Scale up cooldown in seconds (default: 60)
                - scale_down_cooldown: Scale down cooldown in seconds (default: 300)
                - prediction_horizon: Prediction horizon in minutes (default: 15)
        """
        self.config = config or {}
        self.scale_up_threshold = self.config.get("scale_up_threshold", 0.8)
        self.scale_down_threshold = self.config.get("scale_down_threshold", 0.3)
        self.max_replicas = self.config.get("max_replicas", 10)
        self.min_replicas = self.config.get("min_replicas", 1)
        self.scale_up_cooldown = float(self.config.get("scale_up_cooldown", 60))
        self.scale_down_cooldown = float(self.config.get("scale_down_cooldown", 300))
        self.prediction_horizon = self.config.get("prediction_horizon", 15)

        self._last_scale_up: Dict[str, datetime] = {}
        self._last_scale_down: Dict[str, datetime] = {}
        self._metric_history: Dict[str, List[MetricData]] = {}
        self._is_initialized = False

        logger.info("Custom HPA Controller initialized")

    def initialize(self) -> bool:
        """
        Initialize HPA controller

        Returns:
            True if initialization successful
        """
        try:
            self._is_initialized = True
            logger.info("Custom HPA Controller initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize HPA controller: {e}")
            return False

    async def evaluate_scaling(
        self,
        resource: str,
        current_replicas: int,
        metrics: List[MetricData],
        forecast: Optional[List[float]] = None,
    ) -> ScalingDecision:
        """
        Evaluate whether scaling is needed

        Args:
            resource: Resource name (e.g., deployment name)
            current_replicas: Current number of replicas
            metrics: Current metric data
            forecast: Optional forecasted metric values

        Returns:
            ScalingDecision object
        """
        if not self._is_initialized:
            raise RuntimeError("HPA controller not initialized")

        # Store metric history
        self._store_metric_history(resource, metrics)

        # Calculate current utilization
        utilization = self._calculate_utilization(metrics)

        # Check cooldown periods
        if not self._can_scale_up(resource):
            logger.info(f"Scale up cooldown active for {resource}")
            return ScalingDecision(
                resource=resource,
                current_replicas=current_replicas,
                desired_replicas=current_replicas,
                direction=ScaleDirection.NONE,
                reason="Scale up cooldown active",
                confidence=0.0,
                metrics=metrics,
            )

        if not self._can_scale_down(resource):
            logger.info(f"Scale down cooldown active for {resource}")
            return ScalingDecision(
                resource=resource,
                current_replicas=current_replicas,
                desired_replicas=current_replicas,
                direction=ScaleDirection.NONE,
                reason="Scale down cooldown active",
                confidence=0.0,
                metrics=metrics,
            )

        # Evaluate forecast if available
        if forecast:
            forecast_utilization = statistics.mean(forecast)
            logger.info(f"Forecasted utilization for {resource}: {forecast_utilization:.2f}")
            utilization = max(utilization, forecast_utilization)

        # Determine scaling action
        if utilization >= self.scale_up_threshold:
            desired_replicas = self._calculate_scale_up_replicas(current_replicas, utilization)
            direction = ScaleDirection.UP
            reason = f"Utilization {utilization:.2f} >= threshold {self.scale_up_threshold}"
            confidence = min(1.0, (utilization - self.scale_up_threshold) / 0.2)

        elif utilization <= self.scale_down_threshold:
            desired_replicas = self._calculate_scale_down_replicas(current_replicas, utilization)
            direction = ScaleDirection.DOWN
            reason = f"Utilization {utilization:.2f} <= threshold {self.scale_down_threshold}"
            confidence = min(1.0, (self.scale_down_threshold - utilization) / 0.2)

        else:
            desired_replicas = current_replicas
            direction = ScaleDirection.NONE
            reason = f"Utilization {utilization:.2f} within normal range"
            confidence = 0.0

        # Enforce replica limits
        desired_replicas = max(self.min_replicas, min(self.max_replicas, desired_replicas))

        # Update cooldown timestamps
        if direction == ScaleDirection.UP and desired_replicas > current_replicas:
            self._last_scale_up[resource] = datetime.now()
        elif direction == ScaleDirection.DOWN and desired_replicas < current_replicas:
            self._last_scale_down[resource] = datetime.now()

        decision = ScalingDecision(
            resource=resource,
            current_replicas=current_replicas,
            desired_replicas=desired_replicas,
            direction=direction,
            reason=reason,
            confidence=confidence,
            metrics=metrics,
        )

        logger.info(
            f"Scaling decision for {resource}: {direction.value} to {desired_replicas} replicas"
        )
        return decision

    def _calculate_utilization(self, metrics: List[MetricData]) -> float:
        """
        Calculate utilization from metrics

        Args:
            metrics: Metric data points

        Returns:
            Utilization value (0-1)
        """
        if not metrics:
            return 0.0

        # Average all metric values
        values = [m.value for m in metrics]
        avg_value = statistics.mean(values)

        # Normalize to 0-1 range (assuming max value of 100)
        return min(1.0, avg_value / 100.0)

    def _calculate_scale_up_replicas(self, current_replicas: int, utilization: float) -> int:
        """
        Calculate desired replicas for scale up

        Args:
            current_replicas: Current number of replicas
            utilization: Current utilization

        Returns:
            Desired number of replicas
        """
        # Scale proportionally to utilization
        scale_factor = utilization / self.scale_up_threshold
        desired = int(current_replicas * scale_factor)

        # Ensure at least 1 more replica
        return max(current_replicas + 1, desired)

    def _calculate_scale_down_replicas(self, current_replicas: int, utilization: float) -> int:
        """
        Calculate desired replicas for scale down

        Args:
            current_replicas: Current number of replicas
            utilization: Current utilization

        Returns:
            Desired number of replicas
        """
        # Scale proportionally to utilization
        scale_factor = utilization / self.scale_down_threshold
        desired = int(current_replicas * scale_factor)

        # Ensure at least 1 less replica
        return min(current_replicas - 1, desired)

    def _can_scale_up(self, resource: str) -> bool:
        """
        Check if scale up is allowed (cooldown check)

        Args:
            resource: Resource name

        Returns:
            True if scale up is allowed
        """
        if resource not in self._last_scale_up:
            return True

        elapsed = (datetime.now() - self._last_scale_up[resource]).total_seconds()
        return elapsed >= self.scale_up_cooldown

    def _can_scale_down(self, resource: str) -> bool:
        """
        Check if scale down is allowed (cooldown check)

        Args:
            resource: Resource name

        Returns:
            True if scale down is allowed
        """
        if resource not in self._last_scale_down:
            return True

        elapsed = (datetime.now() - self._last_scale_down[resource]).total_seconds()
        return elapsed >= self.scale_down_cooldown

    def _store_metric_history(self, resource: str, metrics: List[MetricData]) -> None:
        """
        Store metric data in history

        Args:
            resource: Resource name
            metrics: Metric data points
        """
        if resource not in self._metric_history:
            self._metric_history[resource] = []

        self._metric_history[resource].extend(metrics)

        # Keep only last 100 data points
        if len(self._metric_history[resource]) > 100:
            self._metric_history[resource] = self._metric_history[resource][-100:]

    def get_metric_history(self, resource: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get metric history for a resource

        Args:
            resource: Resource name
            limit: Maximum number of data points

        Returns:
            List of metric data dictionaries
        """
        if resource not in self._metric_history:
            return []

        history = self._metric_history[resource][-limit:]
        return [m.to_dict() for m in history]

    def predict_utilization(self, resource: str, horizon_minutes: int = 15) -> List[float]:
        """
        Predict future utilization using simple linear extrapolation

        Args:
            resource: Resource name
            horizon_minutes: Prediction horizon in minutes

        Returns:
            List of predicted utilization values
        """
        if resource not in self._metric_history or len(self._metric_history[resource]) < 2:
            return []

        history = self._metric_history[resource][-10:]  # Use last 10 points
        values = [m.value for m in history]

        # Simple linear trend
        if len(values) >= 2:
            trend = (values[-1] - values[0]) / len(values)
            predictions = []

            for i in range(horizon_minutes):
                predicted = values[-1] + (trend * (i + 1))
                predictions.append(min(100.0, max(0.0, predicted)))

            return predictions

        return []

    def get_status(self) -> Dict[str, Any]:
        """
        Get HPA controller status

        Returns:
            Status dictionary
        """
        return {
            "initialized": self._is_initialized,
            "config": {
                "scale_up_threshold": self.scale_up_threshold,
                "scale_down_threshold": self.scale_down_threshold,
                "max_replicas": self.max_replicas,
                "min_replicas": self.min_replicas,
                "scale_up_cooldown": self.scale_up_cooldown,
                "scale_down_cooldown": self.scale_down_cooldown,
                "prediction_horizon": self.prediction_horizon,
            },
            "tracked_resources": list(self._last_scale_up.keys()),
            "metric_history_resources": list(self._metric_history.keys()),
        }

    def reset_cooldowns(self, resource: str) -> None:
        """
        Reset cooldowns for a resource

        Args:
            resource: Resource name
        """
        if resource in self._last_scale_up:
            del self._last_scale_up[resource]
        if resource in self._last_scale_down:
            del self._last_scale_down[resource]

        logger.info(f"Reset cooldowns for resource: {resource}")

    def clear_metric_history(self, resource: str) -> None:
        """
        Clear metric history for a resource

        Args:
            resource: Resource name
        """
        if resource in self._metric_history:
            del self._metric_history[resource]

        logger.info(f"Cleared metric history for resource: {resource}")


def create_custom_hpa_controller(
    config: Optional[Dict[str, Any]] = None,
) -> Optional[CustomHPAController]:
    """
    Factory function to create Custom HPA Controller

    Args:
        config: Configuration dictionary

    Returns:
        CustomHPAController instance or None if failed
    """
    try:
        controller = CustomHPAController(config)
        if controller.initialize():
            return controller
        return None
    except Exception as e:
        logger.error(f"Failed to create custom HPA controller: {e}")
        return None
