# -*- coding: utf-8 -*-
"""
Test Coverage Manager
Enterprise-grade test coverage tracking and management
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class CoverageLevel(Enum):
    """Coverage level"""

    EXCELLENT = "excellent"  # 90%+
    GOOD = "good"  # 80-89%
    ACCEPTABLE = "acceptable"  # 70-79%
    NEEDS_IMPROVEMENT = "needs_improvement"  # <70%


@dataclass
class ModuleCoverage:
    """Module coverage data"""

    module_id: str
    module_name: str
    total_lines: int
    covered_lines: int
    coverage_percentage: float
    coverage_level: CoverageLevel
    last_updated: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoverageThreshold:
    """Coverage threshold configuration"""

    module_type: str
    minimum_coverage: float
    target_coverage: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class TestCoverageManager:
    """
    Enterprise-grade test coverage manager
    Provides coverage tracking, threshold management, and reporting
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize test coverage manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Module coverage data
        self.module_coverage: Dict[str, ModuleCoverage] = {}

        # Coverage thresholds
        self.coverage_thresholds: Dict[str, CoverageThreshold] = {}

        # Configuration
        self.default_threshold = self.config.get("default_threshold", 80.0)
        self.auto_track_coverage = self.config.get("auto_track_coverage", False)

        # Statistics
        self.total_modules = 0
        self.average_coverage = 0.0

        # Initialize default thresholds
        self._initialize_default_thresholds()

        logger.info("Test coverage manager initialized")

    def _initialize_default_thresholds(self) -> None:
        """Initialize default coverage thresholds"""
        self.coverage_thresholds["core"] = CoverageThreshold(
            module_type="core", minimum_coverage=70.0, target_coverage=80.0
        )

        self.coverage_thresholds["integration"] = CoverageThreshold(
            module_type="integration", minimum_coverage=65.0, target_coverage=75.0
        )

        self.coverage_thresholds["ai"] = CoverageThreshold(
            module_type="ai", minimum_coverage=60.0, target_coverage=70.0
        )

        self.coverage_thresholds["api"] = CoverageThreshold(
            module_type="api", minimum_coverage=75.0, target_coverage=85.0
        )

    def add_module_coverage(
        self, module_id: str, module_name: str, total_lines: int, covered_lines: int
    ) -> bool:
        """
        Add module coverage data

        Args:
            module_id: Module ID
            module_name: Module name
            total_lines: Total lines of code
            covered_lines: Covered lines by tests

        Returns:
            True if added, False otherwise
        """
        if total_lines == 0:
            logger.error(f"Total lines cannot be zero for module {module_id}")
            return False

        coverage_percentage = (covered_lines / total_lines) * 100.0
        coverage_level = self._calculate_coverage_level(coverage_percentage)

        module_coverage = ModuleCoverage(
            module_id=module_id,
            module_name=module_name,
            total_lines=total_lines,
            covered_lines=covered_lines,
            coverage_percentage=coverage_percentage,
            coverage_level=coverage_level,
            last_updated=datetime.now(timezone.utc),
        )

        self.module_coverage[module_id] = module_coverage
        self.total_modules += 1
        self._update_average_coverage()

        logger.info(f"Added module coverage: {module_id} ({coverage_percentage:.2f}%)")

        return True

    def _calculate_coverage_level(self, percentage: float) -> CoverageLevel:
        """
        Calculate coverage level from percentage

        Args:
            percentage: Coverage percentage

        Returns:
            Coverage level
        """
        if percentage >= 90.0:
            return CoverageLevel.EXCELLENT
        elif percentage >= 80.0:
            return CoverageLevel.GOOD
        elif percentage >= 70.0:
            return CoverageLevel.ACCEPTABLE
        else:
            return CoverageLevel.NEEDS_IMPROVEMENT

    def _update_average_coverage(self) -> None:
        """Update average coverage"""
        if not self.module_coverage:
            self.average_coverage = 0.0
            return

        total_percentage = sum(mc.coverage_percentage for mc in self.module_coverage.values())
        self.average_coverage = total_percentage / len(self.module_coverage)

    def get_module_coverage(self, module_id: str) -> Optional[ModuleCoverage]:
        """
        Get module coverage data

        Args:
            module_id: Module ID

        Returns:
            Module coverage data or None
        """
        return self.module_coverage.get(module_id)

    def check_coverage_threshold(self, module_id: str, module_type: str) -> Dict[str, Any]:
        """
        Check if module meets coverage threshold

        Args:
            module_id: Module ID
            module_type: Module type

        Returns:
            Threshold check result
        """
        module_coverage = self.get_module_coverage(module_id)

        if not module_coverage:
            return {
                "module_id": module_id,
                "meets_threshold": False,
                "reason": "Module coverage not found",
            }

        threshold = self.coverage_thresholds.get(module_type)

        if not threshold:
            threshold = CoverageThreshold(
                module_type="default",
                minimum_coverage=self.default_threshold,
                target_coverage=self.default_threshold,
            )

        meets_minimum = module_coverage.coverage_percentage >= threshold.minimum_coverage
        meets_target = module_coverage.coverage_percentage >= threshold.target_coverage

        return {
            "module_id": module_id,
            "module_type": module_type,
            "current_coverage": module_coverage.coverage_percentage,
            "minimum_coverage": threshold.minimum_coverage,
            "target_coverage": threshold.target_coverage,
            "meets_minimum": meets_minimum,
            "meets_target": meets_target,
            "coverage_level": module_coverage.coverage_level.value,
        }

    def get_coverage_summary(self) -> Dict[str, Any]:
        """
        Get coverage summary

        Returns:
            Coverage summary
        """
        modules_by_level = {
            level.value: len(
                [mc for mc in self.module_coverage.values() if mc.coverage_level == level]
            )
            for level in CoverageLevel
        }

        return {
            "total_modules": self.total_modules,
            "average_coverage": self.average_coverage,
            "modules_by_level": modules_by_level,
            "total_lines": sum(mc.total_lines for mc in self.module_coverage.values()),
            "total_covered_lines": sum(mc.covered_lines for mc in self.module_coverage.values()),
            "thresholds": {
                module_type: {
                    "minimum": threshold.minimum_coverage,
                    "target": threshold.target_coverage,
                }
                for module_type, threshold in self.coverage_thresholds.items()
            },
        }

    def get_coverage_report(self) -> Dict[str, Any]:
        """
        Generate detailed coverage report

        Returns:
            Coverage report
        """
        modules_below_threshold = []

        for module_id, module_coverage in self.module_coverage.items():
            # Check against default threshold
            if module_coverage.coverage_percentage < self.default_threshold:
                modules_below_threshold.append(
                    {
                        "module_id": module_id,
                        "module_name": module_coverage.module_name,
                        "coverage": module_coverage.coverage_percentage,
                        "level": module_coverage.coverage_level.value,
                    }
                )

        return {
            "summary": self.get_coverage_summary(),
            "modules_below_threshold": modules_below_threshold,
            "recommendations": self._generate_recommendations(),
        }

    def _generate_recommendations(self) -> List[str]:
        """
        Generate coverage improvement recommendations

        Returns:
            List of recommendations
        """
        recommendations = []

        if self.average_coverage < 70.0:
            recommendations.append(
                "Overall coverage is below 70%. Focus on increasing test coverage for critical modules."  # noqa: E501
            )
        elif self.average_coverage < 80.0:
            recommendations.append(
                "Overall coverage is below 80%. Continue adding tests to reach the target."
            )

        modules_below_target = [
            mc for mc in self.module_coverage.values() if mc.coverage_percentage < 80.0
        ]

        if modules_below_target:
            recommendations.append(
                f"{len(modules_below_target)} modules are below 80% coverage. "
                "Prioritize testing these modules."
            )

        return recommendations


# Global instance
_coverage_manager: Optional[TestCoverageManager] = None


def get_coverage_manager() -> TestCoverageManager:
    """
    Get the global test coverage manager instance

    Returns:
        TestCoverageManager instance
    """
    global _coverage_manager
    if _coverage_manager is None:
        _coverage_manager = TestCoverageManager()
    return _coverage_manager
