# -*- coding: utf-8 -*-
"""
Alert Intelligence Module
=========================

Advanced AI-powered alert analysis and processing capabilities.
Implements intelligent alert aggregation, trend prediction, and topology-aware correlation.

Key Features:
- ML-based alert clustering and aggregation
- Time series trend prediction (Prophet/LSTM)
- Automated alert routing based on topology
- Advanced noise reduction using historical patterns
- Topology-aware alert correlation
- Fine-grained alert suppression management
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger

# Try to import ML libraries, provide fallbacks if not available
try:
    from sklearn.cluster import DBSCAN
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import StandardScaler

    ML_AVAILABLE = True
except ImportError:
    logger.info("ML libraries not available, using rule-based fallback")
    ML_AVAILABLE = False

try:
    from prophet import Prophet

    PROPHET_AVAILABLE = True
except ImportError:
    logger.info("Prophet not available, trend prediction disabled")
    PROPHET_AVAILABLE = False


class AlertSeverity(Enum):
    """Alert severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    WARNING = "warning"
    INFO = "info"
    LOW = "low"


@dataclass
class AlertPattern:
    """Historical alert pattern for noise reduction"""

    pattern_id: str
    signature: str
    frequency: int
    last_seen: datetime
    is_noise: bool = False
    noise_reason: str = ""
    suppression_window: int = 300  # 5 minutes default


@dataclass
class AlertCluster:
    """Cluster of similar alerts"""

    cluster_id: str
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    centroid: Dict[str, Any] = field(default_factory=dict)
    severity: AlertSeverity = AlertSeverity.WARNING
    created_at: datetime = field(default_factory=datetime.now)
    topology_context: Optional[Dict[str, Any]] = None


@dataclass
class TrendPrediction:
    """Alert trend prediction result"""

    metric_name: str
    predicted_values: List[float]
    predicted_anomalies: List[Tuple[datetime, float]]
    confidence: float
    prediction_horizon: int  # hours
    model_used: str = "rule_based"


class AlertIntelligenceEngine:
    """
    Main intelligence engine for advanced alert processing
    """

    def __init__(self):
        self.patterns: Dict[str, AlertPattern] = {}
        self.clusters: Dict[str, AlertCluster] = {}
        self.topology_graph: Dict[str, List[str]] = defaultdict(list)
        self.routing_rules: List[Dict[str, Any]] = []
        self.suppression_rules: List[Dict[str, Any]] = []

        # Initialize ML components if available
        self.vectorizer = TfidfVectorizer(max_features=100) if ML_AVAILABLE else None
        self.scaler = StandardScaler() if ML_AVAILABLE else None

        logger.info("Alert Intelligence Engine initialized")

    async def analyze_and_aggregate_alerts(
        self, alerts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Perform intelligent alert aggregation using ML clustering

        Args:
            alerts: List of raw alerts to process

        Returns:
            List of aggregated/clustered alerts
        """
        if not alerts:
            return []

        logger.info(f"Processing {len(alerts)} alerts for intelligent aggregation")

        # Extract features for clustering
        features = self._extract_alert_features(alerts)

        # Perform clustering
        if ML_AVAILABLE and len(alerts) > 2:
            clustered_alerts = await self._ml_based_clustering(alerts, features)
        else:
            clustered_alerts = await self._rule_based_clustering(alerts)

        # Apply noise reduction
        filtered_alerts = await self._apply_noise_reduction(clustered_alerts)

        # Update historical patterns
        self._update_patterns(alerts)

        logger.info(
            f"Aggregated {len(alerts)} alerts into {len(filtered_alerts)} intelligent groups"
        )
        return filtered_alerts

    def _extract_alert_features(self, alerts: List[Dict[str, Any]]) -> np.ndarray:
        """Extract numerical features from alerts for ML processing"""
        features: List[List[int]] = []

        for alert in alerts:
            feature_vector = [
                self._encode_severity(alert.get("level", "info")),
                self._encode_category(alert.get("category", "system")),
                len(alert.get("title", "")),
                len(alert.get("desc", "")),
                hash(alert.get("host", "")) % 100,  # Host hash as feature
                hash(alert.get("metric", "")) % 100,  # Metric hash as feature
            ]
            features.append(feature_vector)

        return np.array(features)  # type: ignore[no-any-return]

    def _encode_severity(self, severity: str) -> int:
        """Encode severity to numerical value"""
        severity_map = {"critical": 4, "high": 3, "warning": 2, "info": 1, "low": 0}
        return severity_map.get(severity.lower(), 1)

    def _encode_category(self, category: str) -> int:
        """Encode category to numerical value"""
        category_map = {"security": 4, "performance": 3, "availability": 2, "system": 1, "other": 0}
        return category_map.get(category.lower(), 1)

    async def _ml_based_clustering(
        self, alerts: List[Dict[str, Any]], features: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Use ML clustering to group similar alerts"""
        try:
            # Scale features
            if self.scaler is None:
                logger.warning("Scaler not available, using rule-based clustering")
                return await self._rule_based_clustering(alerts)
            scaled_features = self.scaler.fit_transform(features)

            # Apply DBSCAN clustering
            clustering = DBSCAN(eps=0.5, min_samples=2).fit(scaled_features)
            labels = clustering.labels_

            # Group alerts by cluster
            clusters = defaultdict(list)
            for idx, label in enumerate(labels):
                if label != -1:  # -1 is noise
                    clusters[label].append(alerts[idx])
                else:
                    clusters[f"noise_{idx}"].append(alerts[idx])

            # Create aggregated alerts from clusters
            aggregated = []
            for cluster_id, cluster_alerts in clusters.items():
                if len(cluster_alerts) == 1:
                    aggregated.append(cluster_alerts[0])
                else:
                    aggregated.append(
                        self._create_aggregated_alert(cluster_alerts, str(cluster_id))
                    )

            return aggregated

        except Exception as e:
            logger.error(f"ML clustering failed: {e}, falling back to rule-based")
            return await self._rule_based_clustering(alerts)

    async def _rule_based_clustering(self, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rule-based alert clustering as fallback"""
        clusters = defaultdict(list)

        for alert in alerts:
            # Create signature based on key attributes
            signature = self._create_alert_signature(alert)
            clusters[signature].append(alert)

        # Aggregate alerts in same cluster
        aggregated = []
        for signature, cluster_alerts in clusters.items():
            if len(cluster_alerts) == 1:
                aggregated.append(cluster_alerts[0])
            else:
                aggregated.append(self._create_aggregated_alert(cluster_alerts, signature))

        return aggregated

    def _create_alert_signature(self, alert: Dict[str, Any]) -> str:
        """Create unique signature for alert clustering"""
        key_fields = [
            alert.get("level", ""),
            alert.get("category", ""),
            alert.get("alert_type", ""),
            alert.get("host", ""),
            alert.get("metric", ""),
        ]
        return "|".join(str(field) for field in key_fields)

    def _create_aggregated_alert(
        self, alerts: List[Dict[str, Any]], cluster_id: str
    ) -> Dict[str, Any]:
        """Create aggregated alert from cluster of similar alerts"""
        # Use the most severe alert as base
        base_alert = max(alerts, key=lambda x: self._encode_severity(x.get("level", "info")))

        aggregated = {
            **base_alert,
            "id": f"AGG-{cluster_id}-{datetime.now().strftime('%H%M%S')}",
            "title": f"[聚合] {base_alert.get('title', '')}",
            "desc": f"聚合了 {len(alerts)} 个相似告警",
            "aggregated_count": len(alerts),
            "cluster_id": cluster_id,
            "aggregated_alerts": alerts,
            "aggregated_at": datetime.now().isoformat(),
        }

        return aggregated

    async def _apply_noise_reduction(self, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply historical pattern-based noise reduction"""
        filtered = []

        for alert in alerts:
            signature = self._create_alert_signature(alert)
            pattern = self.patterns.get(signature)

            # Check if this matches a known noise pattern
            if pattern and pattern.is_noise:
                # Check if within suppression window
                if (
                    datetime.now() - pattern.last_seen
                ).total_seconds() < pattern.suppression_window:
                    logger.debug(f"Suppressed noise alert: {signature}")
                    continue

            filtered.append(alert)

        return filtered

    def _update_patterns(self, alerts: List[Dict[str, Any]]) -> None:
        """Update historical patterns based on new alerts"""
        for alert in alerts:
            signature = self._create_alert_signature(alert)

            if signature in self.patterns:
                pattern = self.patterns[signature]
                pattern.frequency += 1
                pattern.last_seen = datetime.now()

                # Auto-detect noise patterns (high frequency, low severity)
                if (
                    pattern.frequency > 10
                    and self._encode_severity(alert.get("level", "info")) <= 1
                ):
                    pattern.is_noise = True
                    pattern.noise_reason = "高频低级别告警"
            else:
                self.patterns[signature] = AlertPattern(
                    pattern_id=signature, signature=signature, frequency=1, last_seen=datetime.now()
                )

    async def predict_alert_trends(
        self,
        metric_name: str,
        historical_data: List[Tuple[datetime, float]],
        horizon_hours: int = 24,
    ) -> TrendPrediction:
        """
        Predict alert trends using time series forecasting

        Args:
            metric_name: Name of the metric to predict
            historical_data: List of (timestamp, value) tuples
            horizon_hours: Prediction horizon in hours

        Returns:
            TrendPrediction with forecasted values and anomalies
        """
        if len(historical_data) < 10:
            logger.warning(f"Insufficient data for trend prediction: {len(historical_data)} points")
            return TrendPrediction(
                metric_name=metric_name,
                predicted_values=[],
                predicted_anomalies=[],
                confidence=0.0,
                prediction_horizon=horizon_hours,
                model_used="insufficient_data",
            )

        try:
            if PROPHET_AVAILABLE:
                return await self._prophet_prediction(metric_name, historical_data, horizon_hours)
            else:
                return await self._rule_based_prediction(
                    metric_name, historical_data, horizon_hours
                )

        except Exception as e:
            logger.error(f"Trend prediction failed: {e}")
            return await self._rule_based_prediction(metric_name, historical_data, horizon_hours)

    async def _prophet_prediction(
        self, metric_name: str, historical_data: List[Tuple[datetime, float]], horizon_hours: int
    ) -> TrendPrediction:
        """Use Prophet for time series prediction"""
        # Prepare data for Prophet
        df = pd.DataFrame(historical_data, columns=["ds", "y"])

        # Fit model
        model = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=False)
        model.fit(df)

        # Make prediction
        future = model.make_future_dataframe(periods=horizon_hours, freq="H")
        forecast = model.predict(future)

        # Extract predictions
        predicted_values = forecast["yhat"].tail(horizon_hours).tolist()

        # Detect anomalies (values outside confidence interval)
        anomalies = []
        for idx, row in forecast.tail(horizon_hours).iterrows():
            if row["yhat_lower"] > row["yhat"] or row["yhat_upper"] < row["yhat"]:
                anomalies.append((row["ds"], row["yhat"]))

        return TrendPrediction(
            metric_name=metric_name,
            predicted_values=predicted_values,
            predicted_anomalies=anomalies,
            confidence=0.8,  # Prophet doesn't provide direct confidence
            prediction_horizon=horizon_hours,
            model_used="prophet",
        )

    async def _rule_based_prediction(
        self, metric_name: str, historical_data: List[Tuple[datetime, float]], horizon_hours: int
    ) -> TrendPrediction:
        """Simple rule-based trend prediction as fallback"""
        # Calculate trend
        values = [v for _, v in historical_data]
        if len(values) >= 2:
            trend = (values[-1] - values[0]) / len(values)
            predicted = [values[-1] + trend * (i + 1) for i in range(horizon_hours)]
        else:
            predicted = [values[-1]] * horizon_hours if values else []

        # Simple anomaly detection
        anomalies = []
        if predicted:
            mean_val = np.mean(predicted)
            std_val = np.std(predicted)
            for i, val in enumerate(predicted):
                if abs(val - mean_val) > 2 * std_val:
                    anomalies.append((datetime.now() + timedelta(hours=i), val))

        return TrendPrediction(
            metric_name=metric_name,
            predicted_values=predicted,
            predicted_anomalies=anomalies,
            confidence=0.5,
            prediction_horizon=horizon_hours,
            model_used="rule_based",
        )

    def build_topology_context(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build topology-aware context for alerts

        Args:
            alerts: List of alerts to analyze

        Returns:
            Topology context dictionary with relationships and dependencies
        """
        topology: Dict[str, Any] = {
            "nodes": set(),
            "edges": defaultdict(list),
            "components": defaultdict(list),
        }

        for alert in alerts:
            host = alert.get("host", "unknown")
            category = alert.get("category", "system")

            topology["nodes"].add(host)
            topology["components"][category].append(host)

            # Simple dependency inference
            if category == "database":
                for other_host in topology["nodes"]:
                    if other_host != host:
                        topology["edges"][other_host].append(host)

        return {
            "nodes": list(topology["nodes"]),
            "edges": dict(topology["edges"]),
            "components": dict(topology["components"]),
            "alert_count_by_component": {
                comp: len(hosts) for comp, hosts in topology["components"].items()
            },
        }

    async def route_alerts_intelligently(
        self, alerts: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Route alerts to appropriate handlers based on topology and rules

        Args:
            alerts: List of alerts to route

        Returns:
            Dictionary mapping route destinations to alerts
        """
        topology_context = self.build_topology_context(alerts)

        routed_alerts = defaultdict(list)

        for alert in alerts:
            # Apply routing rules
            route = self._determine_alert_route(alert, topology_context)
            routed_alerts[route].append(alert)

        return dict(routed_alerts)

    def _determine_alert_route(
        self, alert: Dict[str, Any], topology_context: Dict[str, Any]
    ) -> str:
        """Determine the appropriate route for an alert"""
        # Check custom routing rules first
        for rule in self.routing_rules:
            if self._matches_routing_rule(alert, rule):
                destination = rule.get("destination", "default")
                return str(destination)

        # Default routing based on topology and severity
        severity = alert.get("level", "info")
        category = alert.get("category", "system")

        if severity == "critical":
            return "immediate"
        elif category == "security":
            return "security_team"
        elif category in ["database", "network"]:
            return "infrastructure_team"
        else:
            return "default"

    def _matches_routing_rule(self, alert: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """Check if alert matches a routing rule"""
        conditions = rule.get("conditions", {})

        for key, expected_value in conditions.items():
            if alert.get(key) != expected_value:
                return False

        return True

    def add_routing_rule(self, rule: Dict[str, Any]) -> None:
        """Add a custom routing rule"""
        self.routing_rules.append(rule)
        logger.info(f"Added routing rule: {rule}")

    def add_suppression_rule(self, rule: Dict[str, Any]) -> None:
        """Add a custom suppression rule"""
        self.suppression_rules.append(rule)
        logger.info(f"Added suppression rule: {rule}")

    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get statistics about alert patterns and clusters"""
        return {
            "total_patterns": len(self.patterns),
            "noise_patterns": sum(1 for p in self.patterns.values() if p.is_noise),
            "active_clusters": len(self.clusters),
            "topology_nodes": len(self.topology_graph),
            "routing_rules": len(self.routing_rules),
            "suppression_rules": len(self.suppression_rules),
        }


# Global instance
alert_intelligence_engine = AlertIntelligenceEngine()
