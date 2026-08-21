# -*- coding: utf-8 -*-
"""
Performance Regression Detector
================================
Enterprise-level performance regression detection system providing:
- Historical performance data management
- Baseline establishment and maintenance
- Regression detection algorithms (statistical significance tests)
- Trend analysis
- Anomaly detection
- Regression report generation
- Automatic alerting
"""

import json
import os
import statistics
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from collections import defaultdict
import pickle

import numpy as np
from scipy import stats
from scipy.signal import find_peaks
from loguru import logger


class RegressionSeverity(Enum):
    """Severity levels for performance regressions"""
    
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    BLOCKER = "blocker"


class DetectionMethod(Enum):
    """Methods for regression detection"""
    
    T_TEST = "t_test"
    MANN_WHITNEY_U = "mann_whitney_u"
    Z_TEST = "z_test"
    PERCENTILE_COMPARISON = "percentile_comparison"
    REGRESSION_ANALYSIS = "regression_analysis"
    CHANGE_POINT_DETECTION = "change_point_detection"
    SEASONAL_DECOMPOSITION = "seasonal_decomposition"


@dataclass
class BaselineData:
    """Baseline performance data"""
    
    test_name: str
    metric_type: str
    values: List[float]
    timestamps: List[datetime]
    statistics: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate statistics after initialization"""
        if self.values and not self.statistics:
            self.statistics = self._calculate_statistics()
    
    def _calculate_statistics(self) -> Dict[str, float]:
        """Calculate statistical metrics"""
        if not self.values:
            return {}
        
        sorted_values = sorted(self.values)
        n = len(sorted_values)
        
        return {
            "count": n,
            "mean": statistics.mean(self.values),
            "median": statistics.median(self.values),
            "std_dev": statistics.stdev(self.values) if n > 1 else 0.0,
            "variance": statistics.variance(self.values) if n > 1 else 0.0,
            "min": min(self.values),
            "max": max(self.values),
            "p50": sorted_values[int(n * 0.5)],
            "p90": sorted_values[int(n * 0.9)],
            "p95": sorted_values[int(n * 0.95)],
            "p99": sorted_values[int(n * 0.99)],
            "iqr": sorted_values[int(n * 0.75)] - sorted_values[int(n * 0.25)]
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "test_name": self.test_name,
            "metric_type": self.metric_type,
            "values": self.values,
            "timestamps": [ts.isoformat() for ts in self.timestamps],
            "statistics": self.statistics,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaselineData':
        """Create from dictionary"""
        return cls(
            test_name=data["test_name"],
            metric_type=data["metric_type"],
            values=data["values"],
            timestamps=[datetime.fromisoformat(ts) for ts in data["timestamps"]],
            statistics=data.get("statistics", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=data.get("metadata", {})
        )


@dataclass
class RegressionResult:
    """Result of regression detection"""
    
    test_name: str
    metric_type: str
    baseline_data: BaselineData
    current_values: List[float]
    detection_method: DetectionMethod
    detected: bool
    severity: RegressionSeverity
    p_value: Optional[float] = None
    test_statistic: Optional[float] = None
    effect_size: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None
    change_point: Optional[int] = None
    trend: Optional[str] = None
    message: str = ""
    detected_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "test_name": self.test_name,
            "metric_type": self.metric_type,
            "detection_method": self.detection_method.value,
            "detected": self.detected,
            "severity": self.severity.value,
            "p_value": self.p_value,
            "test_statistic": self.test_statistic,
            "effect_size": self.effect_size,
            "confidence_interval": self.confidence_interval,
            "change_point": self.change_point,
            "trend": self.trend,
            "message": self.message,
            "detected_at": self.detected_at.isoformat(),
            "metadata": self.metadata,
            "baseline_statistics": self.baseline_data.statistics,
            "current_statistics": self._calculate_current_statistics()
        }
    
    def _calculate_current_statistics(self) -> Dict[str, float]:
        """Calculate statistics for current values"""
        if not self.current_values:
            return {}
        
        sorted_values = sorted(self.current_values)
        n = len(sorted_values)
        
        return {
            "count": n,
            "mean": statistics.mean(self.current_values),
            "median": statistics.median(self.current_values),
            "std_dev": statistics.stdev(self.current_values) if n > 1 else 0.0,
            "min": min(self.current_values),
            "max": max(self.current_values),
            "p50": sorted_values[int(n * 0.5)],
            "p90": sorted_values[int(n * 0.9)],
            "p95": sorted_values[int(n * 0.95)],
            "p99": sorted_values[int(n * 0.99)]
        }


@dataclass
class AlertConfig:
    """Configuration for regression alerts"""
    
    enabled: bool = True
    severity_threshold: RegressionSeverity = RegressionSeverity.WARNING
    notification_channels: List[str] = field(default_factory=lambda: ["log"])
    webhook_url: Optional[str] = None
    email_recipients: List[str] = field(default_factory=list)
    slack_channel: Optional[str] = None
    cooldown_minutes: int = 30


class StatisticalTests:
    """Statistical test implementations for regression detection"""
    
    @staticmethod
    def t_test(baseline: List[float], current: List[float], alpha: float = 0.05) -> Dict[str, Any]:
        """
        Perform independent two-sample t-test
        
        Args:
            baseline: Baseline values
            current: Current values
            alpha: Significance level
            
        Returns:
            Dictionary with test results
        """
        if len(baseline) < 2 or len(current) < 2:
            return {
                "detected": False,
                "p_value": 1.0,
                "test_statistic": 0.0,
                "message": "Insufficient data for t-test"
            }
        
        try:
            # Perform t-test
            statistic, p_value = stats.ttest_ind(baseline, current)
            
            # Calculate effect size (Cohen's d)
            pooled_std = np.sqrt(
                (statistics.variance(baseline) * (len(baseline) - 1) +
                 statistics.variance(current) * (len(current) - 1)) /
                (len(baseline) + len(current) - 2)
            )
            effect_size = abs(statistics.mean(current) - statistics.mean(baseline)) / pooled_std if pooled_std > 0 else 0
            
            # Calculate confidence interval for difference
            diff = statistics.mean(current) - statistics.mean(baseline)
            se = pooled_std * np.sqrt(1/len(baseline) + 1/len(current))
            ci = (diff - 1.96 * se, diff + 1.96 * se)
            
            detected = p_value < alpha
            
            return {
                "detected": detected,
                "p_value": p_value,
                "test_statistic": statistic,
                "effect_size": effect_size,
                "confidence_interval": ci,
                "message": f"T-test: p={p_value:.4f}, statistic={statistic:.4f}"
            }
        except Exception as e:
            logger.error(f"T-test failed: {e}")
            return {
                "detected": False,
                "p_value": 1.0,
                "test_statistic": 0.0,
                "message": f"T-test error: {str(e)}"
            }
    
    @staticmethod
    def mann_whitney_u_test(baseline: List[float], current: List[float], alpha: float = 0.05) -> Dict[str, Any]:
        """
        Perform Mann-Whitney U test (non-parametric)
        
        Args:
            baseline: Baseline values
            current: Current values
            alpha: Significance level
            
        Returns:
            Dictionary with test results
        """
        if len(baseline) < 3 or len(current) < 3:
            return {
                "detected": False,
                "p_value": 1.0,
                "test_statistic": 0.0,
                "message": "Insufficient data for Mann-Whitney U test"
            }
        
        try:
            # Perform Mann-Whitney U test
            statistic, p_value = stats.mannwhitneyu(baseline, current, alternative='two-sided')
            
            # Calculate effect size (r)
            n1, n2 = len(baseline), len(current)
            z_score = stats.norm.ppf(p_value / 2) if p_value > 0 else 0
            effect_size = abs(z_score) / np.sqrt(n1 + n2)
            
            detected = p_value < alpha
            
            return {
                "detected": detected,
                "p_value": p_value,
                "test_statistic": statistic,
                "effect_size": effect_size,
                "message": f"Mann-Whitney U: p={p_value:.4f}, U={statistic:.4f}"
            }
        except Exception as e:
            logger.error(f"Mann-Whitney U test failed: {e}")
            return {
                "detected": False,
                "p_value": 1.0,
                "test_statistic": 0.0,
                "message": f"Mann-Whitney U test error: {str(e)}"
            }
    
    @staticmethod
    def z_test(baseline: List[float], current: List[float], alpha: float = 0.05) -> Dict[str, Any]:
        """
        Perform z-test for large samples
        
        Args:
            baseline: Baseline values
            current: Current values
            alpha: Significance level
            
        Returns:
            Dictionary with test results
        """
        if len(baseline) < 30 or len(current) < 30:
            return {
                "detected": False,
                "p_value": 1.0,
                "test_statistic": 0.0,
                "message": "Insufficient data for z-test (need n >= 30)"
            }
        
        try:
            mean_baseline = statistics.mean(baseline)
            mean_current = statistics.mean(current)
            std_baseline = statistics.stdev(baseline)
            std_current = statistics.stdev(current)
            
            # Calculate z-statistic
            pooled_std = np.sqrt(std_baseline**2 / len(baseline) + std_current**2 / len(current))
            z_statistic = (mean_current - mean_baseline) / pooled_std if pooled_std > 0 else 0
            
            # Calculate p-value (two-tailed)
            p_value = 2 * (1 - stats.norm.cdf(abs(z_statistic)))
            
            # Calculate effect size
            effect_size = abs(mean_current - mean_baseline) / pooled_std if pooled_std > 0 else 0
            
            # Calculate confidence interval
            diff = mean_current - mean_baseline
            ci = (diff - 1.96 * pooled_std, diff + 1.96 * pooled_std)
            
            detected = p_value < alpha
            
            return {
                "detected": detected,
                "p_value": p_value,
                "test_statistic": z_statistic,
                "effect_size": effect_size,
                "confidence_interval": ci,
                "message": f"Z-test: p={p_value:.4f}, z={z_statistic:.4f}"
            }
        except Exception as e:
            logger.error(f"Z-test failed: {e}")
            return {
                "detected": False,
                "p_value": 1.0,
                "test_statistic": 0.0,
                "message": f"Z-test error: {str(e)}"
            }
    
    @staticmethod
    def percentile_comparison(baseline: List[float], current: List[float], 
                              percentile: int = 95, threshold: float = 0.1) -> Dict[str, Any]:
        """
        Compare percentiles between baseline and current
        
        Args:
            baseline: Baseline values
            current: Current values
            percentile: Percentile to compare (e.g., 95 for p95)
            threshold: Relative change threshold
            
        Returns:
            Dictionary with comparison results
        """
        if not baseline or not current:
            return {
                "detected": False,
                "message": "Insufficient data for percentile comparison"
            }
        
        try:
            baseline_p = np.percentile(baseline, percentile)
            current_p = np.percentile(current, percentile)
            
            if baseline_p > 0:
                relative_change = (current_p - baseline_p) / baseline_p
            else:
                relative_change = 0
            
            detected = abs(relative_change) > threshold
            
            return {
                "detected": detected,
                "baseline_percentile": baseline_p,
                "current_percentile": current_p,
                "relative_change": relative_change,
                "message": f"P{percentile}: baseline={baseline_p:.4f}, current={current_p:.4f}, change={relative_change:.2%}"
            }
        except Exception as e:
            logger.error(f"Percentile comparison failed: {e}")
            return {
                "detected": False,
                "message": f"Percentile comparison error: {str(e)}"
            }


class TrendAnalysis:
    """Trend analysis for performance data"""
    
    @staticmethod
    def linear_regression(values: List[float], timestamps: Optional[List[datetime]] = None) -> Dict[str, Any]:
        """
        Perform linear regression to detect trends
        
        Args:
            values: Time series values
            timestamps: Optional timestamps (uses indices if not provided)
            
        Returns:
            Dictionary with regression results
        """
        if len(values) < 3:
            return {
                "trend": "insufficient_data",
                "slope": 0.0,
                "intercept": 0.0,
                "r_squared": 0.0,
                "message": "Insufficient data for trend analysis"
            }
        
        try:
            x = np.arange(len(values))
            y = np.array(values)
            
            # Perform linear regression
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            r_squared = r_value ** 2
            
            # Determine trend direction
            if abs(slope) < std_err * 2:
                trend = "stable"
            elif slope > 0:
                trend = "increasing"
            else:
                trend = "decreasing"
            
            return {
                "trend": trend,
                "slope": slope,
                "intercept": intercept,
                "r_squared": r_squared,
                "p_value": p_value,
                "std_err": std_err,
                "message": f"Trend: {trend}, slope={slope:.6f}, R²={r_squared:.4f}"
            }
        except Exception as e:
            logger.error(f"Linear regression failed: {e}")
            return {
                "trend": "error",
                "slope": 0.0,
                "intercept": 0.0,
                "r_squared": 0.0,
                "message": f"Regression error: {str(e)}"
            }
    
    @staticmethod
    def moving_average(values: List[float], window_size: int = 5) -> List[float]:
        """
        Calculate moving average
        
        Args:
            values: Time series values
            window_size: Size of moving window
            
        Returns:
            List of moving average values
        """
        if len(values) < window_size:
            return values.copy()
        
        return [statistics.mean(values[i:i+window_size]) 
                for i in range(len(values) - window_size + 1)]
    
    @staticmethod
    def detect_change_point(values: List[float], min_size: int = 5) -> Optional[int]:
        """
        Detect change point in time series using CUSUM-like approach
        
        Args:
            values: Time series values
            min_size: Minimum size for each segment
            
        Returns:
            Index of change point or None
        """
        if len(values) < 2 * min_size:
            return None
        
        try:
            n = len(values)
            best_change_point = None
            max_statistic = 0
            
            for i in range(min_size, n - min_size):
                before = values[:i]
                after = values[i:]
                
                mean_before = statistics.mean(before)
                mean_after = statistics.mean(after)
                
                # Calculate test statistic
                statistic = abs(mean_after - mean_before)
                
                if statistic > max_statistic:
                    max_statistic = statistic
                    best_change_point = i
            
            # Only return if change is significant
            if max_statistic > statistics.stdev(values) * 2:
                return best_change_point
            
            return None
        except Exception as e:
            logger.error(f"Change point detection failed: {e}")
            return None
    
    @staticmethod
    def seasonal_decomposition(values: List[float], period: int = 7) -> Dict[str, Any]:
        """
        Simple seasonal decomposition (trend + seasonal + residual)
        
        Args:
            values: Time series values
            period: Period for seasonal component
            
        Returns:
            Dictionary with decomposition results
        """
        if len(values) < 2 * period:
            return {
                "trend": [],
                "seasonal": [],
                "residual": [],
                "message": "Insufficient data for seasonal decomposition"
            }
        
        try:
            # Calculate trend using moving average
            trend = TrendAnalysis.moving_average(values, window_size=period)
            
            # Calculate seasonal component
            seasonal = []
            for i in range(len(values)):
                if i < len(trend):
                    seasonal.append(values[i] - trend[i])
                else:
                    seasonal.append(0)
            
            # Calculate residual
            residual = []
            for i in range(len(values)):
                if i < len(trend):
                    residual.append(values[i] - trend[i] - seasonal[i])
                else:
                    residual.append(0)
            
            return {
                "trend": trend,
                "seasonal": seasonal,
                "residual": residual,
                "message": "Seasonal decomposition completed"
            }
        except Exception as e:
            logger.error(f"Seasonal decomposition failed: {e}")
            return {
                "trend": [],
                "seasonal": [],
                "residual": [],
                "message": f"Decomposition error: {str(e)}"
            }


class AnomalyDetector:
    """Anomaly detection for performance data"""
    
    @staticmethod
    def detect_outliers_zscore(values: List[float], threshold: float = 3.0) -> List[int]:
        """
        Detect outliers using z-score method
        
        Args:
            values: Data values
            threshold: Z-score threshold
            
        Returns:
            List of outlier indices
        """
        if len(values) < 3:
            return []
        
        try:
            mean = statistics.mean(values)
            std_dev = statistics.stdev(values)
            
            if std_dev == 0:
                return []
            
            outliers = []
            for i, value in enumerate(values):
                z_score = abs((value - mean) / std_dev)
                if z_score > threshold:
                    outliers.append(i)
            
            return outliers
        except Exception as e:
            logger.error(f"Z-score outlier detection failed: {e}")
            return []
    
    @staticmethod
    def detect_outliers_iqr(values: List[float], multiplier: float = 1.5) -> List[int]:
        """
        Detect outliers using IQR method
        
        Args:
            values: Data values
            multiplier: IQR multiplier
            
        Returns:
            List of outlier indices
        """
        if len(values) < 4:
            return []
        
        try:
            sorted_values = sorted(values)
            n = len(sorted_values)
            
            q1 = sorted_values[n // 4]
            q3 = sorted_values[3 * n // 4]
            iqr = q3 - q1
            
            lower_bound = q1 - multiplier * iqr
            upper_bound = q3 + multiplier * iqr
            
            outliers = []
            for i, value in enumerate(values):
                if value < lower_bound or value > upper_bound:
                    outliers.append(i)
            
            return outliers
        except Exception as e:
            logger.error(f"IQR outlier detection failed: {e}")
            return []
    
    @staticmethod
    def detect_anomalies_isolation_forest(values: List[float], contamination: float = 0.1) -> List[int]:
        """
        Detect anomalies using isolation forest (simplified version)
        
        Args:
            values: Data values
            contamination: Expected contamination rate
            
        Returns:
            List of anomaly indices
        """
        # Simplified version using statistical methods
        # In production, use sklearn's IsolationForest
        return AnomalyDetector.detect_outliers_iqr(values, multiplier=2.0)


class HistoricalDataManager:
    """Manages historical performance data storage and retrieval"""
    
    def __init__(self, storage_path: Union[str, Path] = ".benchmarks/history"):
        """
        Initialize historical data manager
        
        Args:
            storage_path: Path to store historical data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, BaselineData] = {}
        self._lock = threading.Lock()
    
    def _get_storage_file(self, test_name: str, metric_type: str) -> Path:
        """Get storage file path for a test and metric"""
        safe_name = test_name.replace("/", "_").replace("\\", "_")
        return self.storage_path / f"{safe_name}_{metric_type}.pkl"
    
    def save_baseline(self, baseline: BaselineData) -> bool:
        """
        Save baseline data to storage
        
        Args:
            baseline: Baseline data to save
            
        Returns:
            Success status
        """
        try:
            with self._lock:
                file_path = self._get_storage_file(baseline.test_name, baseline.metric_type)
                with open(file_path, 'wb') as f:
                    pickle.dump(baseline, f)
                
                self._cache[f"{baseline.test_name}_{baseline.metric_type}"] = baseline
                logger.info(f"Saved baseline for {baseline.test_name}/{baseline.metric_type}")
                return True
        except Exception as e:
            logger.error(f"Failed to save baseline: {e}")
            return False
    
    def load_baseline(self, test_name: str, metric_type: str) -> Optional[BaselineData]:
        """
        Load baseline data from storage
        
        Args:
            test_name: Test name
            metric_type: Metric type
            
        Returns:
            Baseline data or None
        """
        cache_key = f"{test_name}_{metric_type}"
        
        # Check cache first
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            file_path = self._get_storage_file(test_name, metric_type)
            if not file_path.exists():
                return None
            
            with open(file_path, 'rb') as f:
                baseline = pickle.load(f)
            
            self._cache[cache_key] = baseline
            return baseline
        except Exception as e:
            logger.error(f"Failed to load baseline: {e}")
            return None
    
    def update_baseline(self, test_name: str, metric_type: str, 
                       new_values: List[float], timestamps: List[datetime],
                       max_samples: int = 1000) -> bool:
        """
        Update baseline with new data
        
        Args:
            test_name: Test name
            metric_type: Metric type
            new_values: New values to add
            timestamps: Timestamps for new values
            max_samples: Maximum number of samples to keep
            
        Returns:
            Success status
        """
        try:
            baseline = self.load_baseline(test_name, metric_type)
            
            if baseline:
                # Update existing baseline
                baseline.values.extend(new_values)
                baseline.timestamps.extend(timestamps)
                
                # Trim to max_samples
                if len(baseline.values) > max_samples:
                    baseline.values = baseline.values[-max_samples:]
                    baseline.timestamps = baseline.timestamps[-max_samples:]
                
                # Recalculate statistics
                baseline.statistics = baseline._calculate_statistics()
            else:
                # Create new baseline
                baseline = BaselineData(
                    test_name=test_name,
                    metric_type=metric_type,
                    values=new_values,
                    timestamps=timestamps
                )
            
            return self.save_baseline(baseline)
        except Exception as e:
            logger.error(f"Failed to update baseline: {e}")
            return False
    
    def list_baselines(self) -> List[Dict[str, Any]]:
        """
        List all available baselines
        
        Returns:
            List of baseline information
        """
        baselines = []
        
        try:
            for file_path in self.storage_path.glob("*.pkl"):
                try:
                    with open(file_path, 'rb') as f:
                        baseline = pickle.load(f)
                    baselines.append({
                        "test_name": baseline.test_name,
                        "metric_type": baseline.metric_type,
                        "sample_count": len(baseline.values),
                        "created_at": baseline.created_at.isoformat(),
                        "statistics": baseline.statistics
                    })
                except Exception as e:
                    logger.warning(f"Failed to read baseline file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Failed to list baselines: {e}")
        
        return baselines
    
    def delete_baseline(self, test_name: str, metric_type: str) -> bool:
        """
        Delete a baseline
        
        Args:
            test_name: Test name
            metric_type: Metric type
            
        Returns:
            Success status
        """
        try:
            file_path = self._get_storage_file(test_name, metric_type)
            if file_path.exists():
                file_path.unlink()
                
                # Remove from cache
                cache_key = f"{test_name}_{metric_type}"
                if cache_key in self._cache:
                    del self._cache[cache_key]
                
                logger.info(f"Deleted baseline for {test_name}/{metric_type}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete baseline: {e}")
            return False


class PerformanceRegressionDetector:
    """Main performance regression detector"""
    
    def __init__(self, storage_path: Union[str, Path] = ".benchmarks/history",
                 alert_config: Optional[AlertConfig] = None):
        """
        Initialize regression detector
        
        Args:
            storage_path: Path to store historical data
            alert_config: Alert configuration
        """
        self.data_manager = HistoricalDataManager(storage_path)
        self.alert_config = alert_config or AlertConfig()
        self._alert_cooldowns: Dict[str, datetime] = {}
        self._lock = threading.Lock()
    
    def establish_baseline(self, test_name: str, metric_type: str,
                          values: List[float], timestamps: Optional[List[datetime]] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Establish a performance baseline
        
        Args:
            test_name: Test name
            metric_type: Metric type
            values: Baseline values
            timestamps: Optional timestamps
            metadata: Optional metadata
            
        Returns:
            Success status
        """
        if not timestamps:
            timestamps = [datetime.now() for _ in values]
        
        baseline = BaselineData(
            test_name=test_name,
            metric_type=metric_type,
            values=values,
            timestamps=timestamps,
            metadata=metadata or {}
        )
        
        return self.data_manager.save_baseline(baseline)
    
    def detect_regression(self, test_name: str, metric_type: str,
                        current_values: List[float],
                        methods: Optional[List[DetectionMethod]] = None,
                        alpha: float = 0.05) -> RegressionResult:
        """
        Detect performance regression using specified methods
        
        Args:
            test_name: Test name
            metric_type: Metric type
            current_values: Current performance values
            methods: Detection methods to use
            alpha: Significance level
            
        Returns:
            Regression detection result
        """
        if methods is None:
            methods = [
                DetectionMethod.T_TEST,
                DetectionMethod.MANN_WHITNEY_U,
                DetectionMethod.PERCENTILE_COMPARISON
            ]
        
        # Load baseline
        baseline = self.data_manager.load_baseline(test_name, metric_type)
        
        if not baseline:
            return RegressionResult(
                test_name=test_name,
                metric_type=metric_type,
                baseline_data=BaselineData(test_name, metric_type, [], []),
                current_values=current_values,
                detection_method=methods[0],
                detected=False,
                severity=RegressionSeverity.INFO,
                message="No baseline available for comparison"
            )
        
        # Run detection methods
        results = []
        for method in methods:
            result = self._run_detection_method(
                method, baseline.values, current_values, alpha
            )
            results.append((method, result))
        
        # Determine overall result
        detected = any(r["detected"] for _, r in results)
        
        # Calculate severity
        severity = self._calculate_severity(results, baseline.values, current_values)
        
        # Get trend
        trend_result = TrendAnalysis.linear_regression(current_values)
        
        # Get change point
        change_point = TrendAnalysis.detect_change_point(current_values)
        
        # Use the first method's results for the primary result
        primary_method, primary_result = results[0]
        
        regression_result = RegressionResult(
            test_name=test_name,
            metric_type=metric_type,
            baseline_data=baseline,
            current_values=current_values,
            detection_method=primary_method,
            detected=detected,
            severity=severity,
            p_value=primary_result.get("p_value"),
            test_statistic=primary_result.get("test_statistic"),
            effect_size=primary_result.get("effect_size"),
            confidence_interval=primary_result.get("confidence_interval"),
            change_point=change_point,
            trend=trend_result.get("trend"),
            message=primary_result.get("message", ""),
            metadata={"all_methods": [(m.value, r) for m, r in results]}
        )
        
        # Trigger alert if regression detected
        if detected and self.alert_config.enabled:
            self._trigger_alert(regression_result)
        
        return regression_result
    
    def _run_detection_method(self, method: DetectionMethod, baseline: List[float],
                             current: List[float], alpha: float) -> Dict[str, Any]:
        """Run a specific detection method"""
        if method == DetectionMethod.T_TEST:
            return StatisticalTests.t_test(baseline, current, alpha)
        elif method == DetectionMethod.MANN_WHITNEY_U:
            return StatisticalTests.mann_whitney_u_test(baseline, current, alpha)
        elif method == DetectionMethod.Z_TEST:
            return StatisticalTests.z_test(baseline, current, alpha)
        elif method == DetectionMethod.PERCENTILE_COMPARISON:
            return StatisticalTests.percentile_comparison(baseline, current)
        elif method == DetectionMethod.REGRESSION_ANALYSIS:
            return TrendAnalysis.linear_regression(current)
        elif method == DetectionMethod.CHANGE_POINT_DETECTION:
            change_point = TrendAnalysis.detect_change_point(current)
            return {
                "detected": change_point is not None,
                "change_point": change_point,
                "message": f"Change point at index {change_point}" if change_point else "No change point detected"
            }
        elif method == DetectionMethod.SEASONAL_DECOMPOSITION:
            return TrendAnalysis.seasonal_decomposition(current)
        else:
            return {"detected": False, "message": f"Unknown method: {method}"}
    
    def _calculate_severity(self, results: List[Tuple[DetectionMethod, Dict[str, Any]]],
                           baseline: List[float], current: List[float]) -> RegressionSeverity:
        """Calculate regression severity based on detection results"""
        detected_count = sum(1 for _, r in results if r["detected"])
        
        if detected_count == 0:
            return RegressionSeverity.INFO
        
        # Calculate relative change
        baseline_mean = statistics.mean(baseline)
        current_mean = statistics.mean(current)
        
        if baseline_mean > 0:
            relative_change = abs((current_mean - baseline_mean) / baseline_mean)
        else:
            relative_change = 0
        
        # Determine severity based on change and detection count
        if relative_change > 0.5 or detected_count >= len(results):
            return RegressionSeverity.BLOCKER
        elif relative_change > 0.3 or detected_count >= len(results) * 0.75:
            return RegressionSeverity.CRITICAL
        elif relative_change > 0.1 or detected_count >= len(results) * 0.5:
            return RegressionSeverity.WARNING
        else:
            return RegressionSeverity.INFO
    
    def _trigger_alert(self, result: RegressionResult):
        """Trigger alert for regression"""
        # Check cooldown
        alert_key = f"{result.test_name}_{result.metric_type}"
        now = datetime.now()
        
        with self._lock:
            if alert_key in self._alert_cooldowns:
                if now - self._alert_cooldowns[alert_key] < timedelta(minutes=self.alert_config.cooldown_minutes):
                    return
            
            self._alert_cooldowns[alert_key] = now
        
        # Check severity threshold
        severity_order = [RegressionSeverity.INFO, RegressionSeverity.WARNING, 
                        RegressionSeverity.CRITICAL, RegressionSeverity.BLOCKER]
        if severity_order.index(result.severity) < severity_order.index(self.alert_config.severity_threshold):
            return
        
        # Send alerts based on configuration
        for channel in self.alert_config.notification_channels:
            if channel == "log":
                self._log_alert(result)
            elif channel == "webhook" and self.alert_config.webhook_url:
                self._webhook_alert(result)
            elif channel == "email" and self.alert_config.email_recipients:
                self._email_alert(result)
            elif channel == "slack" and self.alert_config.slack_channel:
                self._slack_alert(result)
    
    def _log_alert(self, result: RegressionResult):
        """Log alert"""
        logger.warning(
            f"Performance Regression Detected: {result.test_name}/{result.metric_type} - "
            f"Severity: {result.severity.value} - "
            f"Message: {result.message}"
        )
    
    def _webhook_alert(self, result: RegressionResult):
        """Send webhook alert"""
        # Implementation would use requests or similar
        logger.info(f"Webhook alert would be sent to {self.alert_config.webhook_url}")
    
    def _email_alert(self, result: RegressionResult):
        """Send email alert"""
        # Implementation would use SMTP or email service
        logger.info(f"Email alert would be sent to {self.alert_config.email_recipients}")
    
    def _slack_alert(self, result: RegressionResult):
        """Send Slack alert"""
        # Implementation would use Slack API
        logger.info(f"Slack alert would be sent to {self.alert_config.slack_channel}")
    
    def batch_detect(self, test_data: List[Dict[str, Any]], 
                    methods: Optional[List[DetectionMethod]] = None,
                    alpha: float = 0.05) -> List[RegressionResult]:
        """
        Batch detect regressions for multiple tests
        
        Args:
            test_data: List of test data dictionaries
            methods: Detection methods to use
            alpha: Significance level
            
        Returns:
            List of regression results
        """
        results = []
        
        for data in test_data:
            test_name = data.get("test_name")
            metric_type = data.get("metric_type")
            current_values = data.get("values", [])
            
            if test_name and metric_type and current_values:
                result = self.detect_regression(
                    test_name, metric_type, current_values, methods, alpha
                )
                results.append(result)
        
        return results
    
    def analyze_trend(self, test_name: str, metric_type: str,
                     values: List[float]) -> Dict[str, Any]:
        """
        Analyze trend for a test metric
        
        Args:
            test_name: Test name
            metric_type: Metric type
            values: Performance values
            
        Returns:
            Trend analysis results
        """
        trend_result = TrendAnalysis.linear_regression(values)
        change_point = TrendAnalysis.detect_change_point(values)
        decomposition = TrendAnalysis.seasonal_decomposition(values)
        
        return {
            "test_name": test_name,
            "metric_type": metric_type,
            "trend": trend_result,
            "change_point": change_point,
            "decomposition": decomposition
        }
    
    def detect_anomalies(self, test_name: str, metric_type: str,
                        values: List[float]) -> Dict[str, Any]:
        """
        Detect anomalies in performance data
        
        Args:
            test_name: Test name
            metric_type: Metric type
            values: Performance values
            
        Returns:
            Anomaly detection results
        """
        zscore_outliers = AnomalyDetector.detect_outliers_zscore(values)
        iqr_outliers = AnomalyDetector.detect_outliers_iqr(values)
        
        return {
            "test_name": test_name,
            "metric_type": metric_type,
            "zscore_outliers": zscore_outliers,
            "iqr_outliers": iqr_outliers,
            "total_anomalies": len(set(zscore_outliers + iqr_outliers))
        }


class RegressionReportGenerator:
    """Generate regression detection reports"""
    
    def __init__(self, detector: PerformanceRegressionDetector):
        """
        Initialize report generator
        
        Args:
            detector: Regression detector instance
        """
        self.detector = detector
    
    def generate_summary_report(self, results: List[RegressionResult]) -> str:
        """
        Generate summary report for regression results
        
        Args:
            results: List of regression results
            
        Returns:
            Formatted report string
        """
        lines = [
            "=" * 80,
            "PERFORMANCE REGRESSION DETECTION REPORT",
            "=" * 80,
            f"Generated at: {datetime.now().isoformat()}",
            f"Total tests analyzed: {len(results)}",
            f"Regressions detected: {sum(1 for r in results if r.detected)}",
            "",
            "-" * 80,
            "DETAILED RESULTS",
            "-" * 80,
        ]
        
        for result in results:
            lines.append(f"\nTest: {result.test_name}")
            lines.append(f"Metric: {result.metric_type}")
            lines.append(f"Method: {result.detection_method.value}")
            lines.append(f"Detected: {result.detected}")
            lines.append(f"Severity: {result.severity.value}")
            
            if result.p_value is not None:
                lines.append(f"P-value: {result.p_value:.4f}")
            
            if result.test_statistic is not None:
                lines.append(f"Test statistic: {result.test_statistic:.4f}")
            
            if result.effect_size is not None:
                lines.append(f"Effect size: {result.effect_size:.4f}")
            
            if result.trend:
                lines.append(f"Trend: {result.trend}")
            
            if result.change_point is not None:
                lines.append(f"Change point: {result.change_point}")
            
            lines.append(f"Message: {result.message}")
            lines.append("-" * 40)
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)
    
    def generate_json_report(self, results: List[RegressionResult]) -> str:
        """
        Generate JSON report
        
        Args:
            results: List of regression results
            
        Returns:
            JSON string
        """
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(results),
                "regressions_detected": sum(1 for r in results if r.detected),
                "by_severity": {
                    severity.value: sum(1 for r in results if r.severity == severity)
                    for severity in RegressionSeverity
                }
            },
            "results": [r.to_dict() for r in results]
        }
        
        return json.dumps(report, indent=2, default=str)
    
    def save_report(self, results: List[RegressionResult], 
                   output_path: Union[str, Path], format: str = "json") -> str:
        """
        Save report to file
        
        Args:
            results: List of regression results
            output_path: Path to save report
            format: Report format ('json' or 'text')
            
        Returns:
            Path to saved report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            content = self.generate_json_report(results)
        elif format == "text":
            content = self.generate_summary_report(results)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"Report saved to {output_path}")
        return str(output_path)
