# -*- coding: utf-8 -*-
"""
Performance Analysis Report Generator
Generates comprehensive performance analysis reports with trends and recommendations
"""

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class ReportFormat(Enum):
    """Report output formats"""

    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    PDF = "pdf"


class Severity(Enum):
    """Issue severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PerformanceIssue:
    """Performance issue identified in analysis"""

    issue_type: str
    severity: Severity
    description: str
    metric_name: str
    current_value: float
    threshold_value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert issue to dictionary"""
        return {
            "issue_type": self.issue_type,
            "severity": self.severity.value,
            "description": self.description,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "timestamp": self.timestamp.isoformat(),
            "recommendations": self.recommendations,
        }


@dataclass
class TrendData:
    """Trend analysis data"""

    metric_name: str
    trend: str  # "increasing", "decreasing", "stable", "fluctuating"
    change_percent: float
    current_value: float
    previous_value: float
    time_period: str
    confidence: float  # 0.0 to 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert trend data to dictionary"""
        return {
            "metric_name": self.metric_name,
            "trend": self.trend,
            "change_percent": self.change_percent,
            "current_value": self.current_value,
            "previous_value": self.previous_value,
            "time_period": self.time_period,
            "confidence": self.confidence,
        }


@dataclass
class ComparisonResult:
    """Result of performance comparison"""

    metric_name: str
    baseline_value: float
    current_value: float
    change_percent: float
    change_absolute: float
    status: str  # "improved", "degraded", "stable"

    def to_dict(self) -> Dict[str, Any]:
        """Convert comparison result to dictionary"""
        return {
            "metric_name": self.metric_name,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "change_percent": self.change_percent,
            "change_absolute": self.change_absolute,
            "status": self.status,
        }


@dataclass
class PerformanceReport:
    """Complete performance analysis report"""

    report_id: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    time_range: str = "last_24h"
    summary: Dict[str, Any] = field(default_factory=dict)
    trends: List[TrendData] = field(default_factory=list)
    comparisons: List[ComparisonResult] = field(default_factory=list)
    issues: List[PerformanceIssue] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary"""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "time_range": self.time_range,
            "summary": self.summary,
            "trends": [trend.to_dict() for trend in self.trends],
            "comparisons": [comp.to_dict() for comp in self.comparisons],
            "issues": [issue.to_dict() for issue in self.issues],
            "recommendations": self.recommendations,
            "metadata": self.metadata,
        }

    def to_markdown(self) -> str:
        """Convert report to markdown format"""
        md = "# Performance Analysis Report\n\n"
        md += f"**Report ID**: {self.report_id}\n"
        md += f"**Generated**: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        md += f"**Time Range**: {self.time_range}\n\n"

        # Summary
        md += "## Summary\n\n"
        for key, value in self.summary.items():
            md += f"- **{key}**: {value}\n"
        md += "\n"

        # Trends
        if self.trends:
            md += "## Performance Trends\n\n"
            for trend in self.trends:
                emoji = (
                    "📈"
                    if trend.trend == "increasing"
                    else "📉" if trend.trend == "decreasing" else "➡️"
                )
                md += f"{emoji} **{  # noqa: E501
                    trend.metric_name}**: {
                        trend.trend} ({
                            trend.change_percent:+.1f}%)\n"
            md += "\n"

        # Comparisons
        if self.comparisons:
            md += "## Performance Comparison\n\n"
            for comp in self.comparisons:
                emoji = (
                    "✅"
                    if comp.status == "improved"
                    else "❌" if comp.status == "degraded" else "➡️"
                )
                md += (
                    f"{emoji} **{comp.metric_name}**: {comp.change_percent:+.1f}% ({comp.status})\n"
                )
            md += "\n"

        # Issues
        if self.issues:
            md += "## Performance Issues\n\n"
            for issue in self.issues:
                severity_emoji = {
                    "info": "ℹ️",
                    "warning": "⚠️",
                    "error": "❌",
                    "critical": "🚨",
                }.get(issue.severity.value, "ℹ️")
                md += f"{severity_emoji} **{issue.issue_type}** [{issue.severity.value.upper()}]\n"
                md += f"   {issue.description}\n"
                md += f"   Current: {issue.current_value}, Threshold: {issue.threshold_value}\n"
                if issue.recommendations:
                    md += "   Recommendations:\n"
                    for rec in issue.recommendations:
                        md += f"   - {rec}\n"
                md += "\n"

        # Recommendations
        if self.recommendations:
            md += "## Overall Recommendations\n\n"
            for i, rec in enumerate(self.recommendations, 1):
                md += f"{i}. {rec}\n"
            md += "\n"

        return md


class PerformanceAnalysisReportGenerator:
    """
    Generator for performance analysis reports
    """

    def __init__(self):
        """Initialize the report generator"""
        self.report_history: List[PerformanceReport] = []
        self.thresholds: Dict[str, Dict[str, float]] = {
            "response_time_ms": {"warning": 500, "error": 1000, "critical": 5000},
            "error_rate": {"warning": 0.01, "error": 0.05, "critical": 0.10},
            "cpu_usage_percent": {"warning": 70, "error": 85, "critical": 95},
            "memory_usage_mb": {"warning": 1024, "error": 2048, "critical": 4096},
            "throughput_rps": {
                "warning": 10,
                "error": 5,
                "critical": 1,
            },  # Lower threshold for throughput
        }
        logger.info("Performance analysis report generator initialized")

    def generate_report(
        self,
        metrics_data: Dict[str, Any],
        time_range: str = "last_24h",
        baseline_data: Optional[Dict[str, Any]] = None,
    ) -> PerformanceReport:
        """
        Generate a comprehensive performance analysis report

        Args:
            metrics_data: Current metrics data
            time_range: Time range for the report
            baseline_data: Optional baseline data for comparison

        Returns:
            PerformanceReport with analysis results
        """
        report_id = f"perf_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        report = PerformanceReport(report_id=report_id, time_range=time_range)

        # Generate summary
        report.summary = self._generate_summary(metrics_data)

        # Analyze trends
        report.trends = self._analyze_trends(metrics_data, time_range)

        # Compare with baseline if provided
        if baseline_data:
            report.comparisons = self._compare_performance(metrics_data, baseline_data)

        # Identify performance issues
        report.issues = self._identify_issues(metrics_data)

        # Generate recommendations
        report.recommendations = self._generate_recommendations(report.issues, report.trends)

        # Add metadata
        report.metadata = {
            "data_points": len(metrics_data.get("history", [])),
            "analysis_duration_ms": 0,  # Could track actual analysis time
            "generator_version": "1.0.0",
        }

        # Store report in history
        self.report_history.append(report)

        logger.info(f"Generated performance report: {report_id}")
        return report

    def _generate_summary(self, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance summary"""
        summary = {
            "total_requests": metrics_data.get("request_count", 0),
            "total_errors": metrics_data.get("error_count", 0),
            "avg_response_time_ms": metrics_data.get("avg_response_time_ms", 0),
            "error_rate": metrics_data.get("error_rate", 0),
            "throughput_rps": metrics_data.get("throughput_rps", 0),
            "cpu_usage_percent": metrics_data.get("cpu_usage_percent", 0),
            "memory_usage_mb": metrics_data.get("memory_usage_mb", 0),
        }
        return summary

    def _analyze_trends(self, metrics_data: Dict[str, Any], time_range: str) -> List[TrendData]:
        """Analyze performance trends"""
        trends: List[TrendData] = []
        history = metrics_data.get("history", [])

        if len(history) < 2:
            return trends

        # Analyze response time trend
        response_times = [h.get("response_time_ms", 0) for h in history]
        if response_times:
            trend_data = self._calculate_trend("response_time_ms", response_times, time_range)
            if trend_data:
                trends.append(trend_data)

        # Analyze error rate trend
        error_rates = [h.get("error_rate", 0) for h in history]
        if error_rates:
            trend_data = self._calculate_trend("error_rate", error_rates, time_range)
            if trend_data:
                trends.append(trend_data)

        # Analyze throughput trend
        throughputs = [h.get("throughput_rps", 0) for h in history]
        if throughputs:
            trend_data = self._calculate_trend("throughput_rps", throughputs, time_range)
            if trend_data:
                trends.append(trend_data)

        return trends

    def _calculate_trend(
        self, metric_name: str, values: List[float], time_period: str
    ) -> Optional[TrendData]:
        """Calculate trend for a metric"""
        if len(values) < 2:
            return None

        current_value = values[-1]
        previous_value = values[0]

        if previous_value == 0:
            change_percent = 0.0
        else:
            change_percent = ((current_value - previous_value) / previous_value) * 100

        # Determine trend direction
        if abs(change_percent) < 5:
            trend = "stable"
        elif change_percent > 0:
            trend = "increasing"
        else:
            trend = "decreasing"

        # Calculate confidence based on variance
        if len(values) > 2:
            variance = statistics.variance(values)
            mean = statistics.mean(values)
            confidence = max(0, min(1, 1 - (variance / (mean * mean + 1))))
        else:
            confidence = 0.5

        return TrendData(
            metric_name=metric_name,
            trend=trend,
            change_percent=change_percent,
            current_value=current_value,
            previous_value=previous_value,
            time_period=time_period,
            confidence=confidence,
        )

    def _compare_performance(
        self, current_data: Dict[str, Any], baseline_data: Dict[str, Any]
    ) -> List[ComparisonResult]:
        """Compare current performance with baseline"""
        comparisons = []

        # Compare response times
        current_rt = current_data.get("avg_response_time_ms", 0)
        baseline_rt = baseline_data.get("avg_response_time_ms", 0)
        if baseline_rt > 0:
            comparisons.append(
                self._create_comparison(
                    "response_time_ms", baseline_rt, current_rt, lower_is_better=True
                )
            )

        # Compare error rates
        current_er = current_data.get("error_rate", 0)
        baseline_er = baseline_data.get("error_rate", 0)
        if baseline_er > 0:
            comparisons.append(
                self._create_comparison("error_rate", baseline_er, current_er, lower_is_better=True)
            )

        # Compare throughput
        current_tp = current_data.get("throughput_rps", 0)
        baseline_tp = baseline_data.get("throughput_rps", 0)
        if baseline_tp > 0:
            comparisons.append(
                self._create_comparison(
                    "throughput_rps", baseline_tp, current_tp, lower_is_better=False
                )
            )

        return comparisons

    def _create_comparison(
        self, metric_name: str, baseline_value: float, current_value: float, lower_is_better: bool
    ) -> ComparisonResult:
        """Create a comparison result"""
        if baseline_value == 0:
            change_percent = 0.0
            status = "stable"
        else:
            change_percent = ((current_value - baseline_value) / baseline_value) * 100

            if lower_is_better:
                status = (
                    "improved"
                    if change_percent < -5
                    else "degraded" if change_percent > 5 else "stable"
                )
            else:
                status = (
                    "improved"
                    if change_percent > 5
                    else "degraded" if change_percent < -5 else "stable"
                )

        return ComparisonResult(
            metric_name=metric_name,
            baseline_value=baseline_value,
            current_value=current_value,
            change_percent=change_percent,
            change_absolute=current_value - baseline_value,
            status=status,
        )

    def _identify_issues(self, metrics_data: Dict[str, Any]) -> List[PerformanceIssue]:
        """Identify performance issues based on thresholds"""
        issues = []

        # Check response time
        response_time = metrics_data.get("avg_response_time_ms", 0)
        rt_thresholds: Dict[str, float] = self.thresholds.get("response_time_ms", {})
        if response_time > rt_thresholds.get("critical", float("inf")):
            issues.append(
                PerformanceIssue(
                    issue_type="high_response_time",
                    severity=Severity.CRITICAL,
                    description="Response time exceeds critical threshold",
                    metric_name="response_time_ms",
                    current_value=response_time,
                    threshold_value=rt_thresholds.get("critical", 5000),
                    recommendations=[
                        "Identify slow database queries",
                        "Implement caching",
                        "Review and optimize code paths",
                    ],
                )
            )
        elif response_time > rt_thresholds.get("error", 1000):
            issues.append(
                PerformanceIssue(
                    issue_type="high_response_time",
                    severity=Severity.ERROR,
                    description="Response time exceeds error threshold",
                    metric_name="response_time_ms",
                    current_value=response_time,
                    threshold_value=rt_thresholds.get("error", 1000),
                    recommendations=[
                        "Profile application performance",
                        "Check for blocking operations",
                    ],
                )
            )
        elif response_time > rt_thresholds.get("warning", 500):
            issues.append(
                PerformanceIssue(
                    issue_type="high_response_time",
                    severity=Severity.WARNING,
                    description="Response time exceeds warning threshold",
                    metric_name="response_time_ms",
                    current_value=response_time,
                    threshold_value=rt_thresholds.get("warning", 500),
                    recommendations=["Monitor performance trends", "Consider optimization"],
                )
            )

        # Check error rate
        error_rate = metrics_data.get("error_rate", 0)
        er_thresholds: Dict[str, float] = self.thresholds.get("error_rate", {})
        if error_rate > er_thresholds.get("critical", 0.10):
            issues.append(
                PerformanceIssue(
                    issue_type="high_error_rate",
                    severity=Severity.CRITICAL,
                    description="Error rate exceeds critical threshold",
                    metric_name="error_rate",
                    current_value=error_rate,
                    threshold_value=er_thresholds.get("critical", 0.10),
                    recommendations=[
                        "Investigate error logs",
                        "Check service dependencies",
                        "Review recent changes",
                    ],
                )
            )
        elif error_rate > er_thresholds.get("error", 0.05):
            issues.append(
                PerformanceIssue(
                    issue_type="high_error_rate",
                    severity=Severity.ERROR,
                    description="Error rate exceeds error threshold",
                    metric_name="error_rate",
                    current_value=error_rate,
                    threshold_value=er_thresholds.get("error", 0.05),
                    recommendations=["Review error patterns", "Increase monitoring"],
                )
            )

        # Check CPU usage
        cpu_usage = metrics_data.get("cpu_usage_percent", 0)
        cpu_thresholds: Dict[str, float] = self.thresholds.get("cpu_usage_percent", {})
        if cpu_usage > cpu_thresholds.get("critical", 95):
            issues.append(
                PerformanceIssue(
                    issue_type="high_cpu_usage",
                    severity=Severity.CRITICAL,
                    description="CPU usage exceeds critical threshold",
                    metric_name="cpu_usage_percent",
                    current_value=cpu_usage,
                    threshold_value=cpu_thresholds.get("critical", 95),
                    recommendations=[
                        "Scale horizontally",
                        "Optimize CPU-intensive operations",
                        "Review workload distribution",
                    ],
                )
            )

        # Check memory usage
        memory_usage = metrics_data.get("memory_usage_mb", 0)
        mem_thresholds: Dict[str, float] = self.thresholds.get("memory_usage_mb", {})
        if memory_usage > mem_thresholds.get("critical", 4096):
            issues.append(
                PerformanceIssue(
                    issue_type="high_memory_usage",
                    severity=Severity.CRITICAL,
                    description="Memory usage exceeds critical threshold",
                    metric_name="memory_usage_mb",
                    current_value=memory_usage,
                    threshold_value=mem_thresholds.get("critical", 4096),
                    recommendations=[
                        "Investigate memory leaks",
                        "Optimize data structures",
                        "Increase available memory",
                    ],
                )
            )

        return issues

    def _generate_recommendations(
        self, issues: List[PerformanceIssue], trends: List[TrendData]
    ) -> List[str]:
        """Generate overall recommendations based on issues and trends"""
        recommendations = []

        # Add issue-specific recommendations
        for issue in issues:
            recommendations.extend(issue.recommendations)

        # Add trend-based recommendations
        for trend in trends:
            if trend.trend == "increasing" and "response_time" in trend.metric_name:
                recommendations.append(
                    "Monitor increasing response time trends - consider proactive optimization"
                )
            elif trend.trend == "increasing" and "error_rate" in trend.metric_name:
                recommendations.append("Investigate increasing error rate trends immediately")
            elif trend.trend == "decreasing" and "throughput" in trend.metric_name:
                recommendations.append(
                    "Investigate decreasing throughput trends - may indicate capacity issues"
                )

        # Remove duplicates and prioritize
        unique_recommendations = list(dict.fromkeys(recommendations))

        # Prioritize critical recommendations
        critical_issues = [i for i in issues if i.severity == Severity.CRITICAL]
        if critical_issues:
            unique_recommendations.insert(
                0, "URGENT: Address critical performance issues immediately"
            )

        return unique_recommendations[:10]  # Limit to top 10 recommendations

    def get_report(self, report_id: str) -> Optional[PerformanceReport]:
        """
        Get a specific report by ID

        Args:
            report_id: Report ID

        Returns:
            PerformanceReport if found, None otherwise
        """
        for report in self.report_history:
            if report.report_id == report_id:
                return report
        return None

    def get_recent_reports(self, limit: int = 10) -> List[PerformanceReport]:
        """
        Get most recent reports

        Args:
            limit: Maximum number of reports to return

        Returns:
            List of recent PerformanceReport instances
        """
        return self.report_history[-limit:]


# Global instance
_report_generator: Optional[PerformanceAnalysisReportGenerator] = None


def get_performance_analysis_report_generator() -> PerformanceAnalysisReportGenerator:
    """
    Get the global performance analysis report generator instance

    Returns:
        PerformanceAnalysisReportGenerator instance
    """
    global _report_generator
    if _report_generator is None:
        _report_generator = PerformanceAnalysisReportGenerator()
    return _report_generator
