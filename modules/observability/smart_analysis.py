# -*- coding: utf-8 -*-
"""
smart_analysis.py
-----------------
智能可观测性 - 智能分析模块。

功能：
- 趋势分析
- 异常模式识别
- 根因关联分析
- 预测性分析
- 智能洞察生成
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple  # noqa: F401

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 趋势类型枚举
# ----------------------------------------------------------------------
class TrendType(Enum):
    """趋势类型"""

    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


# ----------------------------------------------------------------------
# 2️⃣ 趋势分析结果
# ----------------------------------------------------------------------
@dataclass
class TrendAnalysisResult:
    """趋势分析结果"""

    metric_name: str
    trend_type: TrendType
    slope: float
    r_squared: float
    confidence: float
    forecast: Optional[List[float]] = None
    insights: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "metric_name": self.metric_name,
            "trend_type": self.trend_type.value,
            "slope": self.slope,
            "r_squared": self.r_squared,
            "confidence": self.confidence,
            "forecast": self.forecast,
            "insights": self.insights,
        }


# ----------------------------------------------------------------------
# 3️⃣ 异常模式
# ----------------------------------------------------------------------
@dataclass
class AnomalyPattern:
    """异常模式"""

    pattern_type: str
    description: str
    severity: str
    affected_metrics: List[str]
    start_time: str
    end_time: Optional[str] = None
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "pattern_type": self.pattern_type,
            "description": self.description,
            "severity": self.severity,
            "affected_metrics": self.affected_metrics,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "confidence": self.confidence,
        }


# ----------------------------------------------------------------------
# 4️⃣ 趋势分析器
# ----------------------------------------------------------------------
class TrendAnalyzer:
    """趋势分析器"""

    def __init__(self):
        self.min_data_points = 10

    def analyze(
        self,
        metric_name: str,
        data: List[float],
        timestamps: Optional[List[str]] = None,
    ) -> TrendAnalysisResult:
        """
        分析趋势

        Parameters
        ----------
        metric_name : str
            指标名称
        data : List[float]
            数据点
        timestamps : List[str], optional
            时间戳

        Returns
        -------
        TrendAnalysisResult
            趋势分析结果
        """
        if len(data) < self.min_data_points:
            return TrendAnalysisResult(
                metric_name=metric_name,
                trend_type=TrendType.STABLE,
                slope=0.0,
                r_squared=0.0,
                confidence=0.0,
                insights=["Insufficient data for trend analysis"],
            )

        # 线性回归
        x = np.arange(len(data))
        y = np.array(data)

        # 计算斜率和截距
        slope, intercept = np.polyfit(x, y, 1)

        # 计算 R²
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # 确定趋势类型
        if abs(slope) < 0.01:
            trend_type = TrendType.STABLE
        elif slope > 0:
            trend_type = TrendType.INCREASING
        else:
            trend_type = TrendType.DECREASING

        # 检查波动性
        volatility = np.std(y) / np.mean(y) if np.mean(y) > 0 else 0
        if volatility > 0.5:
            trend_type = TrendType.VOLATILE

        # 生成洞察
        insights = self._generate_insights(
            metric_name,
            trend_type,
            slope,
            r_squared,
            volatility,
        )

        # 简单预测
        forecast = self._simple_forecast(data, slope, intercept, steps=5)

        return TrendAnalysisResult(
            metric_name=metric_name,
            trend_type=trend_type,
            slope=float(slope),
            r_squared=float(r_squared),
            confidence=float(r_squared),
            forecast=forecast,
            insights=insights,
        )

    def _generate_insights(
        self,
        metric_name: str,
        trend_type: TrendType,
        slope: float,
        r_squared: float,
        volatility: float,
    ) -> List[str]:
        """生成洞察"""
        insights = []

        if trend_type == TrendType.INCREASING:
            insights.append(f"{metric_name} is showing an increasing trend")
            if slope > 1.0:
                insights.append(f"Rapid increase detected (slope: {slope:.2f})")
        elif trend_type == TrendType.DECREASING:
            insights.append(f"{metric_name} is showing a decreasing trend")
            if slope < -1.0:
                insights.append(f"Rapid decrease detected (slope: {slope:.2f})")
        elif trend_type == TrendType.STABLE:
            insights.append(f"{metric_name} is stable")
        elif trend_type == TrendType.VOLATILE:
            insights.append(f"{metric_name} is highly volatile")
            insights.append(f"Volatility: {volatility:.2%}")

        if r_squared > 0.8:
            insights.append(f"Strong trend correlation (R²: {r_squared:.2f})")
        elif r_squared < 0.3:
            insights.append(f"Weak trend correlation (R²: {r_squared:.2f})")

        return insights

    def _simple_forecast(
        self,
        data: List[float],
        slope: float,
        intercept: float,
        steps: int = 5,
    ) -> List[float]:
        """简单预测"""
        last_x = len(data) - 1
        forecast = []

        for i in range(1, steps + 1):
            x = last_x + i
            y = slope * x + intercept
            forecast.append(float(y))

        return forecast


# ----------------------------------------------------------------------
# 5️⃣ 异常模式识别器
# ----------------------------------------------------------------------
class AnomalyPatternRecognizer:
    """异常模式识别器"""

    def __init__(self):
        self.pattern_detectors = {
            "spike": self._detect_spike,
            "dip": self._detect_dip,
            "gradual_increase": self._detect_gradual_increase,
            "gradual_decrease": self._detect_gradual_decrease,
            "oscillation": self._detect_oscillation,
        }

    def recognize(
        self,
        metrics_data: Dict[str, List[float]],
        timestamps: Optional[List[str]] = None,
    ) -> List[AnomalyPattern]:
        """
        识别异常模式

        Parameters
        ----------
        metrics_data : Dict[str, List[float]]
            指标数据
        timestamps : List[str], optional
            时间戳

        Returns
        -------
        List[AnomalyPattern]
            异常模式列表
        """
        patterns = []

        for metric_name, data in metrics_data.items():
            for pattern_type, detector in self.pattern_detectors.items():
                result = detector(data)
                if result:
                    patterns.append(
                        AnomalyPattern(
                            pattern_type=pattern_type,
                            description=result["description"],
                            severity=result["severity"],
                            affected_metrics=[metric_name],
                            start_time=timestamps[0] if timestamps else datetime.now().isoformat(),
                            confidence=result.get("confidence", 0.8),
                        )
                    )

        return patterns

    def _detect_spike(self, data: List[float]) -> Optional[Dict[str, Any]]:
        """检测尖峰"""
        if len(data) < 3:
            return None

        # 使用 z-score 检测
        mean = np.mean(data)
        std = np.std(data)

        for i, value in enumerate(data):
            z_score = abs((value - mean) / std) if std > 0 else 0
            if z_score > 3:
                return {
                    "description": (  # noqa: E501
                        f"Spike detected at index {i} (value: {value:.2f}, z-score: {z_score:.2f})"
                    ),
                    "severity": "high" if z_score > 5 else "medium",
                    "confidence": min(1.0, z_score / 5),
                }

        return None

    def _detect_dip(self, data: List[float]) -> Optional[Dict[str, Any]]:
        """检测低谷"""
        if len(data) < 3:
            return None

        mean = np.mean(data)
        std = np.std(data)

        for i, value in enumerate(data):
            z_score = (mean - value) / std if std > 0 else 0
            if z_score > 3:
                return {
                    "description": (  # noqa: E501
                        f"Dip detected at index {i} (value: {value:.2f}, z-score: {z_score:.2f})"
                    ),
                    "severity": "high" if z_score > 5 else "medium",
                    "confidence": min(1.0, z_score / 5),
                }

        return None

    def _detect_gradual_increase(self, data: List[float]) -> Optional[Dict[str, Any]]:
        """检测逐渐增长"""
        if len(data) < 10:
            return None

        # 计算移动平均
        window = 5
        if len(data) < window:
            return None

        moving_avg = pd.Series(data).rolling(window=window).mean().tolist()

        # 检查是否持续增长
        increases = 0
        for i in range(1, len(moving_avg)):
            if moving_avg[i] > moving_avg[i - 1]:
                increases += 1

        if increases / len(moving_avg) > 0.8:
            return {
                "description": "Gradual increase detected",
                "severity": "medium",
                "confidence": increases / len(moving_avg),
            }

        return None

    def _detect_gradual_decrease(self, data: List[float]) -> Optional[Dict[str, Any]]:
        """检测逐渐下降"""
        if len(data) < 10:
            return None

        window = 5
        if len(data) < window:
            return None

        moving_avg = pd.Series(data).rolling(window=window).mean().tolist()

        decreases = 0
        for i in range(1, len(moving_avg)):
            if moving_avg[i] < moving_avg[i - 1]:
                decreases += 1

        if decreases / len(moving_avg) > 0.8:
            return {
                "description": "Gradual decrease detected",
                "severity": "medium",
                "confidence": decreases / len(moving_avg),
            }

        return None

    def _detect_oscillation(self, data: List[float]) -> Optional[Dict[str, Any]]:
        """检测振荡"""
        if len(data) < 10:
            return None

        # 计算符号变化次数
        sign_changes = 0
        for i in range(1, len(data)):
            if (data[i] - data[i - 1]) * (data[i - 1] - data[i - 2]) < 0:
                sign_changes += 1

        if sign_changes > len(data) / 3:
            return {
                "description": f"Oscillation detected ({sign_changes} sign changes)",
                "severity": "medium",
                "confidence": sign_changes / len(data),
            }

        return None


# ----------------------------------------------------------------------
# 6️⃣ 智能分析引擎
# ----------------------------------------------------------------------
class SmartAnalysisEngine:
    """智能分析引擎"""

    def __init__(self):
        self.trend_analyzer = TrendAnalyzer()
        self.pattern_recognizer = AnomalyPatternRecognizer()
        self.analysis_history: List[Dict[str, Any]] = []

    def analyze_metrics(
        self,
        metrics_data: Dict[str, List[float]],
        timestamps: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        分析指标

        Parameters
        ----------
        metrics_data : Dict[str, List[float]]
            指标数据
        timestamps : List[str], optional
            时间戳

        Returns
        -------
        Dict[str, Any]
            分析结果
        """
        logger.info(f"Analyzing {len(metrics_data)} metrics")

        # 趋势分析
        trend_results = []
        for metric_name, data in metrics_data.items():
            result = self.trend_analyzer.analyze(metric_name, data, timestamps)
            trend_results.append(result.to_dict())

        # 异常模式识别
        anomaly_patterns = self.pattern_recognizer.recognize(metrics_data, timestamps)

        # 生成综合洞察
        insights = self._generate_comprehensive_insights(
            trend_results,
            anomaly_patterns,
        )

        # 记录分析历史
        analysis_record = {
            "timestamp": datetime.now().isoformat(),
            "trend_results": trend_results,
            "anomaly_patterns": [p.to_dict() for p in anomaly_patterns],
            "insights": insights,
        }
        self.analysis_history.append(analysis_record)

        return {
            "trend_analysis": trend_results,
            "anomaly_patterns": [p.to_dict() for p in anomaly_patterns],
            "insights": insights,
            "analysis_timestamp": datetime.now().isoformat(),
        }

    def _generate_comprehensive_insights(
        self,
        trend_results: List[Dict[str, Any]],
        anomaly_patterns: List[AnomalyPattern],
    ) -> List[str]:
        """生成综合洞察"""
        insights = []

        # 趋势洞察
        increasing_metrics = [r for r in trend_results if r["trend_type"] == "increasing"]
        decreasing_metrics = [r for r in trend_results if r["trend_type"] == "decreasing"]
        volatile_metrics = [r for r in trend_results if r["trend_type"] == "volatile"]

        if increasing_metrics:
            insights.append(f"{len(increasing_metrics)} metrics showing increasing trend")

        if decreasing_metrics:
            insights.append(f"{len(decreasing_metrics)} metrics showing decreasing trend")

        if volatile_metrics:
            insights.append(f"{len(volatile_metrics)} metrics showing high volatility")

        # 异常模式洞察
        high_severity_patterns = [p for p in anomaly_patterns if p.severity == "high"]
        if high_severity_patterns:
            insights.append(
                f"{len(high_severity_patterns)} high-severity anomaly patterns detected"
            )

        # 关联洞察
        if len(increasing_metrics) > 0 and len(anomaly_patterns) > 0:
            insights.append("Potential correlation between increasing trends and anomaly patterns")

        return insights

    def get_analysis_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        if not self.analysis_history:
            return {}

        latest = self.analysis_history[-1]

        return {
            "total_analyses": len(self.analysis_history),
            "latest_analysis": latest,
            "trend_summary": self._summarize_trends(latest["trend_results"]),
            "pattern_summary": self._summarize_patterns(latest["anomaly_patterns"]),
        }

    def _summarize_trends(self, trend_results: List[Dict[str, Any]]) -> Dict[str, int]:
        """汇总趋势"""
        summary: Dict[str, int] = {}
        for result in trend_results:
            trend_type = result["trend_type"]
            summary[trend_type] = summary.get(trend_type, 0) + 1
        return summary

    def _summarize_patterns(self, anomaly_patterns: List[Dict[str, Any]]) -> Dict[str, int]:
        """汇总异常模式"""
        summary: Dict[str, int] = {}
        for pattern in anomaly_patterns:
            pattern_type = pattern["pattern_type"]
            summary[pattern_type] = summary.get(pattern_type, 0) + 1
        return summary


# ----------------------------------------------------------------------
# 7️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_smart_analysis_engine() -> SmartAnalysisEngine:
    """创建智能分析引擎"""
    return SmartAnalysisEngine()


# ----------------------------------------------------------------------
# 8️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 测试智能分析引擎
    logger.info("Testing smart analysis engine")

    engine = create_smart_analysis_engine()

    # 生成测试数据
    np.random.seed(42)
    metrics_data = {
        "cpu_usage": np.random.normal(50, 10, 100).tolist(),
        "memory_usage": np.random.normal(60, 5, 100).tolist(),
        "request_rate": np.random.normal(1000, 200, 100).tolist(),
    }

    # 添加一些异常
    metrics_data["cpu_usage"][50] = 95.0  # 尖峰
    metrics_data["memory_usage"][60:70] = [80.0] * 10  # 持续高值

    # 执行分析
    result = engine.analyze_metrics(metrics_data)

    logger.info(f"Trend analysis: {len(result['trend_analysis'])} metrics analyzed")
    logger.info(f"Anomaly patterns: {len(result['anomaly_patterns'])} patterns detected")
    logger.info(f"Insights: {result['insights']}")

    # 获取摘要
    summary = engine.get_analysis_summary()
    logger.info(f"Analysis summary: {summary}")

    logger.info("Test passed!")
