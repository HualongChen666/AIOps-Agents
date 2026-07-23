# -*- coding: utf-8 -*-
"""
Dynamic Priority Adjustment
Implements dynamic priority adjustment based on real-time conditions
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from .assessor import BusinessImpactAssessor
from .ranker import PriorityRank


@dataclass
class PriorityAdjustment:
    """
    Priority adjustment result

    Attributes:
        alert_id: Alert identifier
        old_priority: Old priority level
        new_priority: New priority level
        old_score: Old priority score
        new_score: New priority score
        reason: Reason for adjustment
        timestamp: Adjustment timestamp
    """

    alert_id: str
    old_priority: str
    new_priority: str
    old_score: float
    new_score: float
    reason: str
    timestamp: datetime


class DynamicPriorityAdjuster:
    """
    Dynamic priority adjuster

    Adjusts priorities based on changing conditions such as:
    - Time elapsed since alert creation
    - New related alerts
    - System state changes
    - External events
    """

    def __init__(self, assessor: Optional[BusinessImpactAssessor] = None):
        """
        Initialize dynamic priority adjuster

        Args:
            assessor: Business impact assessor
        """
        self.assessor = assessor or BusinessImpactAssessor()
        self.adjustments: List[PriorityAdjustment] = []

    def adjust_priorities(
        self, current_ranks: List[PriorityRank], system_state: Optional[Dict] = None
    ) -> List[PriorityAdjustment]:
        """
        Adjust priorities based on current conditions

        Args:
            current_ranks: Current priority ranks
            system_state: Current system state

        Returns:
            List of priority adjustments
        """
        adjustments = []

        for rank in current_ranks:
            old_priority = rank.priority_level
            old_score = rank.priority_score

            # Calculate new priority score
            new_score = self._calculate_adjusted_score(rank, system_state)

            # Map to new priority level
            new_priority = self._map_score_to_level(new_score)

            # Check if priority changed
            if new_priority != old_priority:
                reason = self._determine_adjustment_reason(rank, new_score, system_state)

                adjustment = PriorityAdjustment(
                    alert_id=rank.alert_id,
                    old_priority=old_priority,
                    new_priority=new_priority,
                    old_score=old_score,
                    new_score=new_score,
                    reason=reason,
                    timestamp=datetime.now(),
                )

                adjustments.append(adjustment)

                # Update the rank
                rank.priority_level = new_priority
                rank.priority_score = new_score

                logger.info(
                    f"Adjusted priority for {rank.alert_id}: "
                    f"{old_priority} -> {new_priority} ({reason})"
                )

        self.adjustments.extend(adjustments)

        return adjustments

    def _calculate_adjusted_score(self, rank: PriorityRank, system_state: Optional[Dict]) -> float:
        """
        Calculate adjusted priority score

        Args:
            rank: Current priority rank
            system_state: System state

        Returns:
            Adjusted priority score
        """
        base_score = rank.priority_score
        multiplier = 1.0

        # Adjust based on system load
        if system_state and "system_load" in system_state:
            load = system_state["system_load"]
            if load > 0.8:
                # High system load - deprioritize non-critical alerts
                if rank.priority_level not in ["P0", "P1"]:
                    multiplier *= 0.8
            elif load < 0.3:
                # Low system load - can handle more alerts
                multiplier *= 1.1

        # Adjust based on alert age
        if "created_at" in rank.business_impact.factors:
            created_at = rank.business_impact.factors["created_at"]
            if isinstance(created_at, (int, float)):
                # Convert timestamp to datetime
                created_at_dt = datetime.fromtimestamp(created_at)
            else:
                created_at_dt = created_at
            age_hours = (datetime.now() - created_at_dt).total_seconds() / 3600
            if age_hours > 24:
                # Old alert - deprioritize
                multiplier *= 0.9
            elif age_hours < 1:
                # New alert - prioritize
                multiplier *= 1.1

        # Adjust based on related alerts
        if system_state and "related_alert_count" in system_state:
            related_count = system_state["related_alert_count"]
            if related_count > 5:
                # Many related alerts - escalate priority
                multiplier *= 1.2

        return min(1.0, base_score * multiplier)

    def _map_score_to_level(self, score: float) -> str:
        """Map score to priority level"""
        if score >= 0.9:
            return "P0"
        elif score >= 0.75:
            return "P1"
        elif score >= 0.5:
            return "P2"
        elif score >= 0.25:
            return "P3"
        else:
            return "P4"

    def _determine_adjustment_reason(
        self, rank: PriorityRank, new_score: float, system_state: Optional[Dict]
    ) -> str:
        """Determine reason for priority adjustment"""
        reasons = []

        if system_state:
            if system_state.get("system_load", 0) > 0.8:
                reasons.append("high_system_load")
            if system_state.get("related_alert_count", 0) > 5:
                reasons.append("related_alert_surge")

        if not reasons:
            reasons.append("time_based_adjustment")

        return ", ".join(reasons)

    def get_adjustment_history(
        self, alert_id: Optional[str] = None, since: Optional[datetime] = None
    ) -> List[PriorityAdjustment]:
        """
        Get adjustment history

        Args:
            alert_id: Filter by alert ID
            since: Filter by timestamp

        Returns:
            List of adjustments
        """
        adjustments = self.adjustments

        if alert_id:
            adjustments = [a for a in adjustments if a.alert_id == alert_id]

        if since:
            adjustments = [a for a in adjustments if a.timestamp >= since]

        return adjustments
