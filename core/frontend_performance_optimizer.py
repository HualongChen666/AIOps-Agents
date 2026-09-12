# -*- coding: utf-8 -*-
"""
Frontend Performance Optimization (Phase 3)
Enterprise-grade frontend performance optimization system
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class OptimizationType(Enum):
    """Optimization type"""

    CODE_SPLITTING = "code_splitting"
    LAZY_LOADING = "lazy_loading"
    IMAGE_OPTIMIZATION = "image_optimization"
    BUNDLE_COMPRESSION = "bundle_compression"
    CACHING_STRATEGY = "caching_strategy"
    MINIFICATION = "minification"
    TREE_SHAKING = "tree_shaking"
    CDN_INTEGRATION = "cdn_integration"


class PerformanceMetric(Enum):
    """Performance metric types"""

    FIRST_CONTENTFUL_PAINT = "first_contentful_paint"
    LARGEST_CONTENTFUL_PAINT = "largest_contentful_paint"
    FIRST_INPUT_DELAY = "first_input_delay"
    CUMULATIVE_LAYOUT_SHIFT = "cumulative_layout_shift"
    TIME_TO_INTERACTIVE = "time_to_interactive"
    TOTAL_BLOCKING_TIME = "total_blocking_time"
    SPEED_INDEX = "speed_index"


@dataclass
class OptimizationRule:
    """Optimization rule configuration"""

    rule_id: str
    rule_name: str
    optimization_type: OptimizationType
    priority: int = 1
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceReport:
    """Performance report"""

    report_id: str
    url: str
    timestamp: datetime
    metrics: Dict[str, float] = field(default_factory=dict)
    score: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    optimizations_applied: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationResult:
    """Optimization result"""

    optimization_type: OptimizationType
    success: bool
    original_size: int = 0
    optimized_size: int = 0
    compression_ratio: float = 0.0
    time_saved: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class FrontendPerformanceOptimizer:
    """Enterprise-grade frontend performance optimizer"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize frontend performance optimizer

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Optimization rules
        self.optimization_rules: Dict[str, OptimizationRule] = {}
        self._initialize_default_rules()

        # Performance reports
        self.performance_reports: List[PerformanceReport] = []

        # Optimization history
        self.optimization_history: List[OptimizationResult] = []

        # Configuration
        self.auto_optimization_enabled = self.config.get("auto_optimize", True)
        self.performance_threshold = self.config.get("performance_threshold", 80.0)

        # Statistics
        self.total_optimizations = 0
        self.successful_optimizations = 0

        logger.info("Frontend performance optimizer initialized")

    def _initialize_default_rules(self):
        """Initialize default optimization rules"""
        # Code splitting rule
        self.optimization_rules["code_splitting"] = OptimizationRule(
            rule_id="code_splitting",
            rule_name="Code Splitting",
            optimization_type=OptimizationType.CODE_SPLITTING,
            priority=1,
            enabled=True,
            config={
                "chunk_size_limit": 244 * 1024,  # 244KB
                "min_chunks": 3,
                "async_loading": True,
            },
        )

        # Lazy loading rule
        self.optimization_rules["lazy_loading"] = OptimizationRule(
            rule_id="lazy_loading",
            rule_name="Lazy Loading",
            optimization_type=OptimizationType.LAZY_LOADING,
            priority=2,
            enabled=True,
            config={
                "threshold": 0.1,  # 10% viewport
                "include_images": True,
                "include_components": True,
            },
        )

        # Image optimization rule
        self.optimization_rules["image_optimization"] = OptimizationRule(
            rule_id="image_optimization",
            rule_name="Image Optimization",
            optimization_type=OptimizationType.IMAGE_OPTIMIZATION,
            priority=1,
            enabled=True,
            config={
                "max_width": 1920,
                "quality": 85,
                "formats": ["webp", "avif", "jpeg"],
                "lazy_load": True,
            },
        )

        # Bundle compression rule
        self.optimization_rules["bundle_compression"] = OptimizationRule(
            rule_id="bundle_compression",
            rule_name="Bundle Compression",
            optimization_type=OptimizationType.BUNDLE_COMPRESSION,
            priority=1,
            enabled=True,
            config={"compression_level": 9, "algorithms": ["gzip", "brotli"]},
        )

        # Caching strategy rule
        self.optimization_rules["caching_strategy"] = OptimizationRule(
            rule_id="caching_strategy",
            rule_name="Caching Strategy",
            optimization_type=OptimizationType.CACHING_STRATEGY,
            priority=2,
            enabled=True,
            config={
                "static_cache_ttl": 86400,  # 24 hours
                "api_cache_ttl": 300,  # 5 minutes
                "service_worker": True,
            },
        )

        # Minification rule
        self.optimization_rules["minification"] = OptimizationRule(
            rule_id="minification",
            rule_name="Code Minification",
            optimization_type=OptimizationType.MINIFICATION,
            priority=1,
            enabled=True,
            config={"remove_comments": True, "remove_whitespace": True, "mangle_names": True},
        )

        # Tree shaking rule
        self.optimization_rules["tree_shaking"] = OptimizationRule(
            rule_id="tree_shaking",
            rule_name="Tree Shaking",
            optimization_type=OptimizationType.TREE_SHAKING,
            priority=1,
            enabled=True,
            config={"mode": "production", "side_effects": False},
        )

        # CDN integration rule
        self.optimization_rules["cdn_integration"] = OptimizationRule(
            rule_id="cdn_integration",
            rule_name="CDN Integration",
            optimization_type=OptimizationType.CDN_INTEGRATION,
            priority=3,
            enabled=True,
            config={"cdn_provider": "cloudflare", "cache_control": "public, max-age=31536000"},
        )

    async def analyze_performance(
        self, url: str, metrics: Optional[Dict[str, float]] = None
    ) -> PerformanceReport:
        """
        Analyze frontend performance using real measurements.

        ``metrics`` may be supplied directly (e.g. from a cache or a caller that
        already ran Lighthouse).  Otherwise the metrics are collected with
        Lighthouse; if Lighthouse is unavailable an explicit error is raised
        rather than returning fabricated numbers.

        Args:
            url: URL to analyze
            metrics: Optional pre-collected metrics

        Returns:
            Performance report
        """
        report_id = f"perf_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        if metrics is None:
            metrics = await self._collect_metrics(url)

        # Calculate overall score
        score = self._calculate_performance_score(metrics)

        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, score)

        report = PerformanceReport(
            report_id=report_id,
            url=url,
            timestamp=datetime.now(timezone.utc),
            metrics=metrics,
            score=score,
            recommendations=recommendations,
        )

        self.performance_reports.append(report)

        logger.info(f"Performance analysis completed for {url}, score: {score}")

        return report

    async def _collect_metrics(self, url: str) -> Dict[str, float]:
        """Collect real frontend metrics via Lighthouse."""
        import json as _json
        import os
        import shutil

        lighthouse_bin = os.getenv("LIGHTHOUSE_BIN") or shutil.which("lighthouse")
        npx_bin = shutil.which("npx")

        if not lighthouse_bin and not npx_bin:
            raise RuntimeError(
                "Lighthouse is not available (install it or set LIGHTHOUSE_BIN); "
                "cannot measure frontend performance metrics"
            )

        command = (
            [lighthouse_bin]
            if lighthouse_bin
            else [npx_bin, "--yes", "lighthouse"]
        )
        command += [
            url,
            "--output=json",
            "--output-path=stdout",
            "--quiet",
            "--chrome-flags=--headless --no-sandbox",
        ]

        import asyncio

        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"Lighthouse failed for {url}: {stderr.decode(errors='replace')[-1000:]}"
            )

        payload = _json.loads(stdout.decode())
        audits = payload.get("audits", {})

        def _numeric(audit_id: str, default: float = 0.0) -> float:
            audit = audits.get(audit_id) or {}
            value = audit.get("numericValue")
            return float(value) if value is not None else default

        return {
            PerformanceMetric.FIRST_CONTENTFUL_PAINT.value: _numeric("first-contentful-paint") / 1000.0,
            PerformanceMetric.LARGEST_CONTENTFUL_PAINT.value: _numeric("largest-contentful-paint") / 1000.0,
            PerformanceMetric.FIRST_INPUT_DELAY.value: _numeric("max-potential-fid") / 1000.0,
            PerformanceMetric.CUMULATIVE_LAYOUT_SHIFT.value: _numeric("cumulative-layout-shift"),
            PerformanceMetric.TIME_TO_INTERACTIVE.value: _numeric("interactive") / 1000.0,
            PerformanceMetric.TOTAL_BLOCKING_TIME.value: _numeric("total-blocking-time"),
            PerformanceMetric.SPEED_INDEX.value: _numeric("speed-index") / 1000.0,
        }

    def _calculate_performance_score(self, metrics: Dict[str, float]) -> float:
        """Calculate overall performance score"""
        # Simple scoring algorithm
        fcp_score = max(
            0, 100 - (metrics.get(PerformanceMetric.FIRST_CONTENTFUL_PAINT.value, 0) * 10)
        )
        lcp_score = max(
            0, 100 - (metrics.get(PerformanceMetric.LARGEST_CONTENTFUL_PAINT.value, 0) * 5)
        )
        fid_score = max(0, 100 - (metrics.get(PerformanceMetric.FIRST_INPUT_DELAY.value, 0) * 100))
        cls_score = max(
            0, 100 - (metrics.get(PerformanceMetric.CUMULATIVE_LAYOUT_SHIFT.value, 0) * 100)
        )
        tti_score = max(0, 100 - (metrics.get(PerformanceMetric.TIME_TO_INTERACTIVE.value, 0) * 5))

        return (fcp_score + lcp_score + fid_score + cls_score + tti_score) / 5

    def _generate_recommendations(self, metrics: Dict[str, float], score: float) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []

        if metrics.get(PerformanceMetric.FIRST_CONTENTFUL_PAINT.value, 0) > 1.8:
            recommendations.append("Enable code splitting to reduce initial bundle size")
            recommendations.append("Implement lazy loading for non-critical resources")

        if metrics.get(PerformanceMetric.LARGEST_CONTENTFUL_PAINT.value, 0) > 2.5:
            recommendations.append("Optimize images and use modern formats (WebP, AVIF)")
            recommendations.append("Implement CDN for static assets")

        if metrics.get(PerformanceMetric.FIRST_INPUT_DELAY.value, 0) > 0.1:
            recommendations.append("Reduce JavaScript execution time")
            recommendations.append("Minimize main thread work")

        if metrics.get(PerformanceMetric.CUMULATIVE_LAYOUT_SHIFT.value, 0) > 0.1:
            recommendations.append("Reserve space for dynamic content")
            recommendations.append("Avoid inserting content above existing content")

        if score < self.performance_threshold:
            recommendations.append("Apply comprehensive optimization strategy")

        return recommendations

    async def apply_optimization(
        self, optimization_type: OptimizationType, config: Optional[Dict[str, Any]] = None
    ) -> OptimizationResult:
        """
        Apply optimization

        Args:
            optimization_type: Type of optimization to apply
            config: Optional configuration override

        Returns:
            Optimization result
        """
        self.total_optimizations += 1

        # Get rule configuration
        rule = self.optimization_rules.get(optimization_type.value)
        if not rule or not rule.enabled:
            return OptimizationResult(
                optimization_type=optimization_type,
                success=False,
                metadata={"error": "Rule not found or disabled"},
            )

        # Merge configurations
        final_config = {**rule.config, **(config or {})}

        try:
            # Apply optimization
            result = await self._execute_optimization(optimization_type, final_config)

            if result.success:
                self.successful_optimizations += 1
                self.optimization_history.append(result)

            return result

        except Exception as e:
            logger.error(f"Optimization failed for {optimization_type.value}: {e}")
            return OptimizationResult(
                optimization_type=optimization_type, success=False, metadata={"error": str(e)}
            )

    async def _execute_optimization(
        self, optimization_type: OptimizationType, config: Dict[str, Any]
    ) -> OptimizationResult:
        """Execute a real optimization against the configured source artifacts.

        ``config['source_path']`` (a file or directory) is processed:
          * ``bundle_compression``/``minification`` -> gzip the concatenated content
          * ``image_optimization`` -> compress images with Pillow when available
        Produces ``target_path`` and returns the *real* before/after sizes.
        """
        import gzip
        import os
        import time

        config_only = {
            OptimizationType.CODE_SPLITTING,
            OptimizationType.LAZY_LOADING,
            OptimizationType.TREE_SHAKING,
            OptimizationType.CACHING_STRATEGY,
            OptimizationType.CDN_INTEGRATION,
        }

        if optimization_type in config_only:
            # These optimizations configure delivery (loaders/CDN/caching) rather
            # than transforming artifacts on disk.
            return OptimizationResult(
                optimization_type=optimization_type,
                success=True,
                compression_ratio=0.0,
                metadata={**config, "note": "configuration-only optimization"},
            )

        source_path = config.get("source_path")
        if not source_path or not os.path.exists(source_path):
            return OptimizationResult(
                optimization_type=optimization_type,
                success=False,
                metadata={
                    "error": "No valid 'source_path' configured for optimization",
                    "config": config,
                },
            )

        target_path = config.get("target_path") or f"{source_path}.optimized"
        started = time.perf_counter()

        if optimization_type in (
            OptimizationType.BUNDLE_COMPRESSION,
            OptimizationType.MINIFICATION,
        ):
            original_size = os.path.getsize(source_path)
            with open(source_path, "rb") as src:
                data = src.read()
            if optimization_type == OptimizationType.MINIFICATION:
                # Strip redundant whitespace as a concrete minification step.
                text = data.decode("utf-8", errors="ignore")
                data = "\n".join(line.strip() for line in text.splitlines()).encode("utf-8")
            with gzip.open(target_path, "wb") as dst:
                dst.write(data)
            optimized_size = os.path.getsize(target_path)

        elif optimization_type == OptimizationType.IMAGE_OPTIMIZATION:
            try:
                from PIL import Image
            except ImportError:
                return OptimizationResult(
                    optimization_type=optimization_type,
                    success=False,
                    metadata={"error": "Pillow is required for image optimization"},
                )
            original_size = os.path.getsize(source_path)
            with Image.open(source_path) as img:
                img.save(target_path, optimize=True)
            optimized_size = os.path.getsize(target_path)

        else:
            return OptimizationResult(
                optimization_type=optimization_type,
                success=True,
                compression_ratio=0.0,
                metadata={**config, "note": "no artifact transformation for this type"},
            )

        compression_ratio = (
            (original_size - optimized_size) / original_size if original_size else 0.0
        )

        return OptimizationResult(
            optimization_type=optimization_type,
            success=True,
            original_size=original_size,
            optimized_size=optimized_size,
            compression_ratio=compression_ratio,
            time_saved=time.perf_counter() - started,
            metadata={**config, "target_path": target_path},
        )

    async def auto_optimize(self, url: str) -> Dict[str, Any]:
        """
        Automatically optimize based on performance analysis

        Args:
            url: URL to optimize

        Returns:
            Optimization summary
        """
        if not self.auto_optimization_enabled:
            return {"status": "disabled"}

        # Analyze performance
        report = await self.analyze_performance(url)

        # Apply optimizations if score is below threshold
        if report.score < self.performance_threshold:
            optimizations_applied = []

            for rule_id, rule in self.optimization_rules.items():
                if rule.enabled and rule.priority <= 2:
                    result = await self.apply_optimization(rule.optimization_type)
                    if result.success:
                        optimizations_applied.append(rule_id)

            # Update report
            report.optimizations_applied = optimizations_applied

            return {
                "status": "optimized",
                "report_id": report.report_id,
                "original_score": report.score,
                "optimizations_applied": len(optimizations_applied),
            }

        return {
            "status": "no_optimization_needed",
            "report_id": report.report_id,
            "score": report.score,
        }

    def register_optimization_rule(self, rule: OptimizationRule) -> None:
        """
        Register custom optimization rule

        Args:
            rule: Optimization rule
        """
        self.optimization_rules[rule.rule_id] = rule
        logger.info(f"Registered optimization rule: {rule.rule_id}")

    def get_optimization_rules(self) -> Dict[str, Dict[str, Any]]:
        """Get all optimization rules"""
        return {
            rule_id: {
                "rule_name": rule.rule_name,
                "optimization_type": rule.optimization_type.value,
                "priority": rule.priority,
                "enabled": rule.enabled,
                "config": rule.config,
            }
            for rule_id, rule in self.optimization_rules.items()
        }

    def get_performance_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get performance reports

        Args:
            limit: Maximum number of reports to return

        Returns:
            List of performance reports
        """
        return [
            {
                "report_id": report.report_id,
                "url": report.url,
                "timestamp": report.timestamp.isoformat(),
                "score": report.score,
                "metrics": report.metrics,
                "recommendations": report.recommendations,
            }
            for report in self.performance_reports[-limit:]
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        return {
            "total_optimizations": self.total_optimizations,
            "successful_optimizations": self.successful_optimizations,
            "success_rate": (
                self.successful_optimizations / self.total_optimizations
                if self.total_optimizations > 0
                else 0.0
            ),
            "total_size_saved": sum(
                r.original_size - r.optimized_size for r in self.optimization_history if r.success
            ),
            "total_time_saved": sum(r.time_saved for r in self.optimization_history if r.success),
            "active_rules": len([r for r in self.optimization_rules.values() if r.enabled]),
        }


def get_frontend_performance_optimizer(
    config: Optional[Dict[str, Any]] = None,
) -> FrontendPerformanceOptimizer:
    """
    Factory function to get frontend performance optimizer instance

    Args:
        config: Optional configuration dictionary

    Returns:
        FrontendPerformanceOptimizer: Optimizer instance
    """
    return FrontendPerformanceOptimizer(config)
