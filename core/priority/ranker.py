# -*- coding: utf-8 -*-
"""
Priority Ranker
Automatically ranks alerts based on business impact
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from loguru import logger

from .assessor import BusinessImpact, BusinessImpactAssessor


@dataclass
class PriorityRank:
    """
    Priority rank result

    Attributes:
        alert_id: Alert identifier
        priority_score: Priority score (0-1)
        priority_level: Priority level (P0-P4)
        business_impact: Business impact assessment
        rank: Overall rank position
    """

    alert_id: str
    priority_score: float
    priority_level: str
    business_impact: BusinessImpact
    rank: int = 0


class PriorityRanker:
    """
    Priority ranker for automatic alert prioritization

    Ranks alerts based on business impact, urgency, and other factors
    """

    def __init__(self, assessor: Optional[BusinessImpactAssessor] = None):
        """
        Initialize priority ranker

        Args:
            assessor: Business impact assessor
        """
        self.assessor = assessor or BusinessImpactAssessor()

        # Priority thresholds
        self.thresholds = {
            "P0": 0.9,  # Critical
            "P1": 0.75,  # High
            "P2": 0.5,  # Medium
            "P3": 0.25,  # Low
            "P4": 0.0,  # Informational
        }

    def rank_alerts(self, alerts: List[Dict]) -> List[PriorityRank]:
        """
        Rank alerts by priority

        Args:
            alerts: List of alert dictionaries

        Returns:
            List of priority ranks sorted by priority
        """
        # Assess business impact for all alerts
        impacts = self.assessor.batch_assess(alerts)

        # Calculate priority scores
        ranks = []
        for alert, impact in zip(alerts, impacts):
            priority_score = self._calculate_priority_score(alert, impact)
            priority_level = self._map_score_to_level(priority_score)

            rank = PriorityRank(
                alert_id=alert.get("id", "unknown"),
                priority_score=priority_score,
                priority_level=priority_level,
                business_impact=impact,
            )
            ranks.append(rank)

        # Sort by priority score (descending)
        ranks.sort(key=lambda r: r.priority_score, reverse=True)

        # Assign rank positions
        for i, rank in enumerate(ranks):
            rank.rank = i + 1

        logger.info(f"Ranked {len(ranks)} alerts")

        return ranks

    def _calculate_priority_score(self, alert: Dict, impact: BusinessImpact) -> float:
        """
        Calculate priority score

        Args:
            alert: Alert data
            impact: Business impact assessment

        Returns:
            Priority score (0-1)
        """
        # Base score from business impact
        base_score = impact.impact_score

        # Adjust for urgency (if available)
        urgency_multiplier = 1.0
        if "urgency" in alert:
            urgency = alert["urgency"]
            if urgency == "critical":
                urgency_multiplier = 1.2
            elif urgency == "high":
                urgency_multiplier = 1.1
            elif urgency == "low":
                urgency_multiplier = 0.9

        # Adjust for age (older alerts may be less urgent)
        age_multiplier = 1.0
        if "created_at" in alert:
            # Simplified: assume newer is more urgent
            age_multiplier = 1.0

        # Calculate final score
        final_score = min(1.0, base_score * urgency_multiplier * age_multiplier)

        return final_score

    def _map_score_to_level(self, score: float) -> str:
        """
        Map score to priority level

        Args:
            score: Priority score

        Returns:
            Priority level (P0-P4)
        """
        if score >= self.thresholds["P0"]:
            return "P0"
        elif score >= self.thresholds["P1"]:
            return "P1"
        elif score >= self.thresholds["P2"]:
            return "P2"
        elif score >= self.thresholds["P3"]:
            return "P3"
        else:
            return "P4"

    def get_top_n(self, alerts: List[Dict], n: int = 10) -> List[PriorityRank]:
        """
        Get top N alerts by priority

        Args:
            alerts: List of alert dictionaries
            n: Number of top alerts to return

        Returns:
            Top N priority ranks
        """
        ranked = self.rank_alerts(alerts)
        return ranked[:n]

    def filter_by_priority(self, alerts: List[Dict], min_level: str = "P1") -> List[PriorityRank]:
        """
        Filter alerts by minimum priority level

        Args:
            alerts: List of alert dictionaries
            min_level: Minimum priority level

        Returns:
            Filtered priority ranks
        """
        ranked = self.rank_alerts(alerts)

        level_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
        min_rank = level_order.get(min_level, 4)

        filtered = [r for r in ranked if level_order.get(r.priority_level, 4) <= min_rank]

        return filtered
