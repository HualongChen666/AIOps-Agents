# -*- coding: utf-8 -*-
"""
Plugin Marketplace Manager
Enterprise-grade plugin marketplace and quality assurance
"""

import ast
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict

from loguru import logger


class PluginQuality(Enum):
    """Plugin quality level"""

    CERTIFIED = "certified"
    VERIFIED = "verified"
    COMMUNITY = "community"
    EXPERIMENTAL = "experimental"


class PluginReviewStatus(Enum):
    """Plugin review status"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    UNDER_REVIEW = "under_review"


class QualityCheckResult(TypedDict):
    """Quality check result structure"""

    syntax_check: bool
    security_check: bool
    performance_check: bool
    documentation_check: bool
    overall_score: float
    issues: List[str]


@dataclass
class PluginListing:
    """Plugin marketplace listing"""

    plugin_id: str
    plugin_name: str
    version: str
    description: str
    author: str
    quality: PluginQuality
    review_status: PluginReviewStatus
    download_count: int = 0
    rating: float = 0.0
    review_count: int = 0
    price: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginReview:
    """Plugin review"""

    review_id: str
    plugin_id: str
    reviewer: str
    rating: int
    comment: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class PluginMarketplaceManager:
    """
    Enterprise-grade plugin marketplace manager
    Provides plugin publishing, downloading, and review management
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin marketplace manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Plugin listings
        self.listings: Dict[str, PluginListing] = {}

        # Plugin reviews
        self.reviews: Dict[str, List[PluginReview]] = {}

        # Quality assurance
        self.quality_checks: Dict[str, QualityCheckResult] = {}

        # Statistics
        self.total_listings = 0
        self.total_downloads = 0
        self.total_reviews = 0

        logger.info("Plugin marketplace manager initialized")

    def publish_plugin(
        self,
        plugin_id: str,
        plugin_name: str,
        version: str,
        description: str,
        author: str,
        plugin_code: str,
        plugin_config: Dict[str, Any],
        quality: PluginQuality = PluginQuality.COMMUNITY,
    ) -> bool:
        """
        Publish plugin to marketplace

        Args:
            plugin_id: Plugin ID
            plugin_name: Plugin name
            version: Plugin version
            description: Plugin description
            author: Plugin author
            plugin_code: Plugin code
            plugin_config: Plugin configuration
            quality: Plugin quality level

        Returns:
            True if published, False otherwise
        """
        # Perform quality checks
        quality_check = self._perform_quality_check(plugin_code, plugin_config)

        # Create listing
        listing = PluginListing(
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            version=version,
            description=description,
            author=author,
            quality=quality,
            review_status=PluginReviewStatus.PENDING,
            metadata={
                "published_at": datetime.now(timezone.utc).isoformat(),
                "quality_check": quality_check,
            },
        )

        self.listings[plugin_id] = listing
        self.quality_checks[plugin_id] = quality_check
        self.total_listings += 1

        logger.info(f"Published plugin: {plugin_id}")

        return True

    def _perform_quality_check(
        self, plugin_code: str, plugin_config: Dict[str, Any]
    ) -> QualityCheckResult:
        """
        Perform quality check on plugin

        Args:
            plugin_code: Plugin code
            plugin_config: Plugin configuration

        Returns:
            Quality check results
        """
        results: QualityCheckResult = {
            "syntax_check": True,
            "security_check": True,
            "performance_check": True,
            "documentation_check": True,
            "overall_score": 0.0,
            "issues": [],
        }

        try:
            # Syntax check
            compile(plugin_code, "<string>", "exec")
        except SyntaxError as e:
            results["syntax_check"] = False
            results["issues"].append(f"Syntax error: {e}")

        # Security check (basic)
        if "eval" in plugin_code or "exec" in plugin_code:
            results["security_check"] = False
            results["issues"].append("Potentially unsafe code detected")

        # Performance check (real AST-based static analysis)
        performance_ok, performance_issues = self._check_performance(plugin_code)
        results["performance_check"] = performance_ok
        results["issues"].extend(performance_issues)

        # Documentation check
        if '"""' not in plugin_code and "'''" not in plugin_code:
            results["documentation_check"] = False
            results["issues"].append("Missing docstring")

        # Calculate overall score
        passed_checks = sum(
            [
                results["syntax_check"],
                results["security_check"],
                results["performance_check"],
                results["documentation_check"],
            ]
        )
        results["overall_score"] = passed_checks / 4.0

        return results

    @classmethod
    def _loop_depth(cls, node: ast.AST, depth: int = 0) -> int:
        """Return the maximum nesting depth of loops reachable from ``node``."""
        max_depth = depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.AsyncFor, ast.While)):
                max_depth = max(max_depth, cls._loop_depth(child, depth + 1))
            else:
                max_depth = max(max_depth, cls._loop_depth(child, depth))
        return max_depth

    @classmethod
    def _check_performance(cls, plugin_code: str) -> tuple[bool, List[str]]:
        """Static performance analysis based on the real code structure.

        Uses the AST (not substring matching) to flag the two hazards that most
        commonly make a plugin slow at runtime:

        * nested loops (``O(n^2)`` behaviour), and
        * oversized functions (large call/compile footprint).

        Returns ``(ok, issues)`` where ``ok`` is ``False`` when any hazard is
        found. Unparsable code is handled by the syntax check, so here it is
        treated as "no additional performance issue".
        """
        issues: List[str] = []
        try:
            tree = ast.parse(plugin_code)
        except SyntaxError:
            return True, issues

        if cls._loop_depth(tree) >= 2:
            issues.append("Nested loops detected (potential quadratic runtime)")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end_lineno = getattr(node, "end_lineno", node.lineno) or node.lineno
                body_lines = end_lineno - node.lineno
                if body_lines > 200:
                    issues.append(f"Function '{node.name}' is very large ({body_lines} lines)")

        # De-duplicate while preserving order.
        unique_issues = list(dict.fromkeys(issues))
        return (len(unique_issues) == 0), unique_issues

    def approve_plugin(self, plugin_id: str, reviewer: str) -> bool:
        """
        Approve plugin for marketplace

        Args:
            plugin_id: Plugin ID
            reviewer: Reviewer name

        Returns:
            True if approved, False otherwise
        """
        if plugin_id not in self.listings:
            logger.error(f"Plugin {plugin_id} not found")
            return False

        listing = self.listings[plugin_id]
        listing.review_status = PluginReviewStatus.APPROVED
        listing.metadata["approved_by"] = reviewer
        listing.metadata["approved_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"Approved plugin: {plugin_id}")

        return True

    def reject_plugin(self, plugin_id: str, reason: str) -> bool:
        """
        Reject plugin from marketplace

        Args:
            plugin_id: Plugin ID
            reason: Rejection reason

        Returns:
            True if rejected, False otherwise
        """
        if plugin_id not in self.listings:
            logger.error(f"Plugin {plugin_id} not found")
            return False

        listing = self.listings[plugin_id]
        listing.review_status = PluginReviewStatus.REJECTED
        listing.metadata["rejection_reason"] = reason
        listing.metadata["rejected_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"Rejected plugin: {plugin_id}")

        return True

    def download_plugin(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """
        Download plugin from marketplace

        Args:
            plugin_id: Plugin ID

        Returns:
            Plugin package or None
        """
        if plugin_id not in self.listings:
            logger.error(f"Plugin {plugin_id} not found")
            return None

        listing = self.listings[plugin_id]

        if listing.review_status != PluginReviewStatus.APPROVED:
            logger.error(f"Plugin {plugin_id} is not approved")
            return None

        # Increment download count
        listing.download_count += 1
        self.total_downloads += 1

        logger.info(f"Downloaded plugin: {plugin_id}")

        return {
            "plugin_id": listing.plugin_id,
            "plugin_name": listing.plugin_name,
            "version": listing.version,
            "download_count": listing.download_count,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        }

    def add_review(self, plugin_id: str, reviewer: str, rating: int, comment: str) -> bool:
        """
        Add review for plugin

        Args:
            plugin_id: Plugin ID
            reviewer: Reviewer name
            rating: Rating (1-5)
            comment: Review comment

        Returns:
            True if added, False otherwise
        """
        if plugin_id not in self.listings:
            logger.error(f"Plugin {plugin_id} not found")
            return False

        if rating < 1 or rating > 5:
            logger.error("Rating must be between 1 and 5")
            return False

        review = PluginReview(
            review_id=f"review_{datetime.now(timezone.utc).timestamp()}",
            plugin_id=plugin_id,
            reviewer=reviewer,
            rating=rating,
            comment=comment,
            timestamp=datetime.now(timezone.utc),
        )

        if plugin_id not in self.reviews:
            self.reviews[plugin_id] = []

        self.reviews[plugin_id].append(review)

        # Update listing rating
        listing = self.listings[plugin_id]
        listing.review_count += 1
        total_rating = sum(r.rating for r in self.reviews[plugin_id])
        listing.rating = total_rating / listing.review_count

        self.total_reviews += 1

        logger.info(f"Added review for plugin: {plugin_id}")

        return True

    def get_plugin_listings(
        self,
        quality: Optional[PluginQuality] = None,
        review_status: Optional[PluginReviewStatus] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get plugin listings

        Args:
            quality: Filter by quality
            review_status: Filter by review status

        Returns:
            List of plugin listings
        """
        listings = []

        for plugin_id, listing in self.listings.items():
            # Apply filters
            if quality and listing.quality != quality:
                continue
            if review_status and listing.review_status != review_status:
                continue

            listings.append(
                {
                    "plugin_id": listing.plugin_id,
                    "plugin_name": listing.plugin_name,
                    "version": listing.version,
                    "description": listing.description,
                    "author": listing.author,
                    "quality": listing.quality.value,
                    "review_status": listing.review_status.value,
                    "download_count": listing.download_count,
                    "rating": listing.rating,
                    "review_count": listing.review_count,
                }
            )

        return listings

    def get_marketplace_summary(self) -> Dict[str, Any]:
        """
        Get marketplace summary

        Returns:
            Marketplace summary
        """
        return {
            "total_listings": self.total_listings,
            "total_downloads": self.total_downloads,
            "total_reviews": self.total_reviews,
            "approved_plugins": len(
                [
                    listing
                    for listing in self.listings.values()
                    if listing.review_status == PluginReviewStatus.APPROVED
                ]
            ),
            "pending_reviews": len(
                [
                    listing
                    for listing in self.listings.values()
                    if listing.review_status == PluginReviewStatus.PENDING
                ]
            ),
            "plugins_by_quality": {
                quality.value: len(
                    [listing for listing in self.listings.values() if listing.quality == quality]
                )
                for quality in PluginQuality
            },
        }


# Global instance
_marketplace_manager: Optional[PluginMarketplaceManager] = None


def get_marketplace_manager() -> PluginMarketplaceManager:
    """
    Get the global plugin marketplace manager instance

    Returns:
        PluginMarketplaceManager instance
    """
    global _marketplace_manager
    if _marketplace_manager is None:
        _marketplace_manager = PluginMarketplaceManager()
    return _marketplace_manager
