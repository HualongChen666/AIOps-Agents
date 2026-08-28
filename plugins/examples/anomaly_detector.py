# -*- coding: utf-8 -*-
"""
Example Plugin 2: Anomaly Detector

This plugin demonstrates how to analyze metrics and detect anomalies
using statistical methods.
"""

import logging
import numpy as np
from typing import Dict, Any, List
from core.plugin_system import BasePlugin, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class AnomalyDetectorPlugin(BasePlugin):
    """
    Anomaly Detector Plugin
    
    Detects anomalies in time-series data using statistical methods
    including z-score analysis and moving average deviations.
    """
    
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        return PluginMetadata(
            name="anomaly_detector",
            version="1.0.0",
            description="Detects anomalies in time-series data using statistical methods",
            author="AIOps Team",
            plugin_type=PluginType.ANALYZER,
            dependencies=["numpy"],
            config_schema={
                "type": "object",
                "properties": {
                    "threshold": {
                        "type": "number",
                        "minimum": 1.0,
                        "maximum": 10.0,
                        "default": 3.0,
                        "description": "Z-score threshold for anomaly detection"
                    },
                    "window_size": {
                        "type": "integer",
                        "minimum": 10,
                        "maximum": 1000,
                        "default": 100,
                        "description": "Window size for moving average calculation"
                    },
                    "method": {
                        "type": "string",
                        "enum": ["zscore", "iqr", "isolation_forest"],
                        "default": "zscore",
                        "description": "Anomaly detection method"
                    },
                    "min_data_points": {
                        "type": "integer",
                        "minimum": 10,
                        "default": 20,
                        "description": "Minimum number of data points required"
                    }
                }
            }
        )
    
    def initialize(self) -> bool:
        """Initialize the plugin"""
        self._threshold = self.config.get("threshold", 3.0)
        self._window_size = self.config.get("window_size", 100)
        self._method = self.config.get("method", "zscore")
        self._min_data_points = self.config.get("min_data_points", 20)
        
        logger.info(f"AnomalyDetectorPlugin initialized with method: {self._method}")
        self._is_initialized = True
        return True
    
    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute plugin logic to detect anomalies"""
        if not self._is_initialized:
            return {"status": "error", "error": "Plugin not initialized"}
        
        try:
            # Extract time-series data
            values = data.get("values", [])
            timestamps = data.get("timestamps", [])
            
            if not values:
                return {"status": "error", "error": "No values provided"}
            
            if len(values) < self._min_data_points:
                return {
                    "status": "error",
                    "error": f"Need at least {self._min_data_points} data points, got {len(values)}"
                }
            
            # Detect anomalies based on configured method
            if self._method == "zscore":
                anomalies = self._detect_zscore_anomalies(values, timestamps)
            elif self._method == "iqr":
                anomalies = self._detect_iqr_anomalies(values, timestamps)
            elif self._method == "isolation_forest":
                anomalies = self._detect_isolation_forest_anomalies(values, timestamps)
            else:
                return {"status": "error", "error": f"Unknown method: {self._method}"}
            
            # Calculate anomaly statistics
            anomaly_count = len(anomalies)
            anomaly_rate = (anomaly_count / len(values)) * 100 if values else 0
            
            return {
                "status": "success",
                "anomalies": anomalies,
                "anomaly_count": anomaly_count,
                "anomaly_rate": anomaly_rate,
                "method": self._method,
                "threshold": self._threshold
            }
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return {"status": "error", "error": str(e)}
    
    def _detect_zscore_anomalies(self, values: List[float], timestamps: List[Any]) -> List[Dict[str, Any]]:
        """Detect anomalies using z-score method"""
        values_array = np.array(values)
        
        # Calculate mean and standard deviation
        mean = np.mean(values_array)
        std = np.std(values_array)
        
        if std == 0:
            logger.warning("Standard deviation is zero, cannot detect anomalies")
            return []
        
        # Calculate z-scores
        z_scores = (values_array - mean) / std
        
        # Identify anomalies
        anomalies = []
        for i, (value, z_score) in enumerate(zip(values, z_scores)):
            if abs(z_score) > self._threshold:
                anomaly = {
                    "index": i,
                    "value": value,
                    "z_score": float(z_score),
                    "timestamp": timestamps[i] if i < len(timestamps) else None,
                    "method": "zscore",
                    "severity": "high" if abs(z_score) > self._threshold * 1.5 else "medium"
                }
                anomalies.append(anomaly)
        
        logger.info(f"Detected {len(anomalies)} anomalies using z-score method")
        return anomalies
    
    def _detect_iqr_anomalies(self, values: List[float], timestamps: List[Any]) -> List[Dict[str, Any]]:
        """Detect anomalies using Interquartile Range (IQR) method"""
        values_array = np.array(values)
        
        # Calculate quartiles
        q1 = np.percentile(values_array, 25)
        q3 = np.percentile(values_array, 75)
        iqr = q3 - q1
        
        if iqr == 0:
            logger.warning("IQR is zero, cannot detect anomalies")
            return []
        
        # Define bounds
        lower_bound = q1 - (self._threshold * iqr)
        upper_bound = q3 + (self._threshold * iqr)
        
        # Identify anomalies
        anomalies = []
        for i, value in enumerate(values):
            if value < lower_bound or value > upper_bound:
                anomaly = {
                    "index": i,
                    "value": value,
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                    "timestamp": timestamps[i] if i < len(timestamps) else None,
                    "method": "iqr",
                    "severity": "high" if value < lower_bound * 0.5 or value > upper_bound * 1.5 else "medium"
                }
                anomalies.append(anomaly)
        
        logger.info(f"Detected {len(anomalies)} anomalies using IQR method")
        return anomalies
    
    def _detect_isolation_forest_anomalies(self, values: List[float], timestamps: List[Any]) -> List[Dict[str, Any]]:
        """Detect anomalies using Isolation Forest method (simplified)"""
        # Note: This is a simplified implementation
        # In production, use sklearn's IsolationForest
        
        values_array = np.array(values)
        
        # Calculate median absolute deviation (MAD)
        median = np.median(values_array)
        mad = np.median(np.abs(values_array - median))
        
        if mad == 0:
            logger.warning("MAD is zero, cannot detect anomalies")
            return []
        
        # Calculate modified z-scores
        modified_z_scores = 0.6745 * (values_array - median) / mad
        
        # Identify anomalies
        anomalies = []
        for i, (value, mz_score) in enumerate(zip(values, modified_z_scores)):
            if abs(mz_score) > self._threshold:
                anomaly = {
                    "index": i,
                    "value": value,
                    "modified_z_score": float(mz_score),
                    "timestamp": timestamps[i] if i < len(timestamps) else None,
                    "method": "isolation_forest",
                    "severity": "high" if abs(mz_score) > self._threshold * 1.5 else "medium"
                }
                anomalies.append(anomaly)
        
        logger.info(f"Detected {len(anomalies)} anomalies using isolation forest method")
        return anomalies
    
    def close(self) -> None:
        """Close the plugin and release resources"""
        self._is_initialized = False
        logger.info("AnomalyDetectorPlugin closed")