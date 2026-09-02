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

        # Repository (set via set_repository method)
        self._repository = None

        # Configuration
        self.default_threshold = self.config.get("default_threshold", 80.0)
        self.auto_track_coverage = self.config.get("auto_track_coverage", False)

        logger.info("Test coverage manager initialized")

    def set_repository(self, repository):
        """
        Set the repository for database operations

        Args:
            repository: TestRepository instance
        """
        self._repository = repository
        logger.info("Repository set for test coverage manager")

    def add_module_coverage(
        self, module_id: str, module_name: str, total_lines: int, covered_lines: int, module_type: str = "core"
    ) -> bool:
        """
        Add module coverage data

        Args:
            module_id: Module ID
            module_name: Module name
            total_lines: Total lines of code
            covered_lines: Covered lines by tests
            module_type: Module type

        Returns:
            True if added, False otherwise
        """
        if not self._repository:
            logger.error("Repository not set")
            return False

        if total_lines == 0:
            logger.error(f"Total lines cannot be zero for module {module_id}")
            return False

        try:
            self._repository.create_or_update_coverage(
                module_id=module_id,
                module_name=module_name,
                module_type=module_type,
                total_lines=total_lines,
                covered_lines=covered_lines,
            )
            logger.info(f"Added module coverage: {module_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding module coverage {module_id}: {e}")
            return False

    def get_module_coverage(self, module_id: str) -> Optional[ModuleCoverage]:
        """
        Get module coverage data

        Args:
            module_id: Module ID

        Returns:
            Module coverage data or None
        """
        if not self._repository:
            logger.error("Repository not set")
            return None

        try:
            coverage_db = self._repository.get_coverage(module_id)
            if not coverage_db:
                return None

            return ModuleCoverage(
                module_id=coverage_db.module_id,
                module_name=coverage_db.module_name,
                total_lines=coverage_db.total_lines,
                covered_lines=coverage_db.covered_lines,
                coverage_percentage=coverage_db.coverage_percentage,
                coverage_level=CoverageLevel(coverage_db.coverage_level),
                last_updated=coverage_db.last_updated,
            )
        except Exception as e:
            logger.error(f"Error getting module coverage {module_id}: {e}")
            return None

    def check_coverage_threshold(self, module_id: str, module_type: str) -> Dict[str, Any]:
        """
        Check if module meets coverage threshold

        Args:
            module_id: Module ID
            module_type: Module type

        Returns:
            Threshold check result
        """
        if not self._repository:
            logger.error("Repository not set")
            return {
                "module_id": module_id,
                "meets_threshold": False,
                "reason": "Repository not set",
            }

        try:
            module_coverage = self.get_module_coverage(module_id)

            if not module_coverage:
                return {
                    "module_id": module_id,
                    "meets_threshold": False,
                    "reason": "Module coverage not found",
                }

            threshold_db = self._repository.get_coverage_threshold(module_type)

            if not threshold_db:
                # Use default threshold
                minimum_coverage = self.default_threshold
                target_coverage = self.default_threshold
            else:
                minimum_coverage = threshold_db.minimum_coverage
                target_coverage = threshold_db.target_coverage

            meets_minimum = module_coverage.coverage_percentage >= minimum_coverage
            meets_target = module_coverage.coverage_percentage >= target_coverage

            return {
                "module_id": module_id,
                "module_type": module_type,
                "current_coverage": module_coverage.coverage_percentage,
                "minimum_coverage": minimum_coverage,
                "target_coverage": target_coverage,
                "meets_minimum": meets_minimum,
                "meets_target": meets_target,
                "coverage_level": module_coverage.coverage_level.value,
            }
        except Exception as e:
            logger.error(f"Error checking coverage threshold for {module_id}: {e}")
            return {
                "module_id": module_id,
                "meets_threshold": False,
                "reason": str(e),
            }

    def get_coverage_summary(self) -> Dict[str, Any]:
        """
        Get coverage summary

        Returns:
            Coverage summary
        """
        if self._repository:
            try:
                return self._repository.get_coverage_statistics()
            except Exception as e:
                logger.error(f"Error getting coverage statistics from repository: {e}")

        # Fallback to default values
        return {
            "total_modules": 0,
            "average_coverage": 0.0,
            "modules_by_level": {
                "excellent": 0,
                "good": 0,
                "acceptable": 0,
                "needs_improvement": 0,
            },
            "total_lines": 0,
            "total_covered_lines": 0,
            "thresholds": {},
        }

    def get_coverage_report(self) -> Dict[str, Any]:
        """
        Generate detailed coverage report

        Returns:
            Coverage report
        """
        if not self._repository:
            logger.error("Repository not set")
            return {
                "summary": self.get_coverage_summary(),
                "modules_below_threshold": [],
                "recommendations": [],
            }

        try:
            coverages = self._repository.get_all_coverages()
            modules_below_threshold = []

            for coverage in coverages:
                # Check against default threshold
                if coverage.coverage_percentage < self.default_threshold:
                    modules_below_threshold.append(
                        {
                            "module_id": coverage.module_id,
                            "module_name": coverage.module_name,
                            "coverage": coverage.coverage_percentage,
                            "level": coverage.coverage_level,
                        }
                    )

            return {
                "summary": self.get_coverage_summary(),
                "modules_below_threshold": modules_below_threshold,
                "recommendations": self._generate_recommendations(coverages),
            }
        except Exception as e:
            logger.error(f"Error generating coverage report: {e}")
            return {
                "summary": self.get_coverage_summary(),
                "modules_below_threshold": [],
                "recommendations": [],
            }

    def _generate_recommendations(self, coverages: List) -> List[str]:
        """
        Generate coverage improvement recommendations

        Args:
            coverages: List of coverage objects

        Returns:
            List of recommendations
        """
        recommendations = []

        if not coverages:
            return recommendations

        avg_coverage = sum(c.coverage_percentage for c in coverages) / len(coverages)

        if avg_coverage < 70.0:
            recommendations.append(
                "Overall coverage is below 70%. Focus on increasing test coverage for critical modules."
            )
        elif avg_coverage < 80.0:
            recommendations.append(
                "Overall coverage is below 80%. Continue adding tests to reach the target."
            )

        modules_below_target = [c for c in coverages if c.coverage_percentage < 80.0]

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
