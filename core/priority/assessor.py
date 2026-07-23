# -*- coding: utf-8 -*-
"""
Business Impact Assessor
Evaluates business impact of alerts and incidents
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class BusinessCriticality(Enum):
    """Business criticality levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BusinessImpact:
    """
    Business impact assessment result

    Attributes:
        service: Service name
        impact_score: Overall impact score (0-1)
        criticality: Business criticality level
        affected_users: Estimated number of affected users
        revenue_impact: Estimated revenue impact
        sla_impact: SLA impact
        factors: Individual impact factors
    """

    service: str
    impact_score: float
    criticality: BusinessCriticality
    affected_users: int
    revenue_impact: float
    sla_impact: bool
    factors: Dict[str, float]


class BusinessImpactAssessor:
    """
    Business impact assessor

    Evaluates the business impact of alerts and incidents
    based on service criticality, user impact, revenue impact, and SLA compliance.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize assessor

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Service criticality mapping
        self.service_criticality: Dict[str, BusinessCriticality] = {
            "payment": BusinessCriticality.CRITICAL,
            "auth": BusinessCriticality.CRITICAL,
            "api": BusinessCriticality.HIGH,
            "database": BusinessCriticality.HIGH,
            "cache": BusinessCriticality.MEDIUM,
            "logging": BusinessCriticality.LOW,
        }

        # Impact weights
        self.weights = {
            "criticality": 0.75,
            "user_impact": 0.1,
            "revenue_impact": 0.05,
            "sla_impact": 0.1,
        }

    def assess(
        self,
        service: str,
        affected_users: int = 0,
        revenue_per_minute: float = 0.0,
        sla_violation: bool = False,
        context: Optional[Dict] = None,
    ) -> BusinessImpact:
        """
        Assess business impact

        Args:
            service: Service name
            affected_users: Number of affected users
            revenue_per_minute: Revenue loss per minute
            sla_violation: Whether SLA is violated
            context: Additional context

        Returns:
            Business impact assessment
        """
        # Get service criticality
        criticality = self.service_criticality.get(service, BusinessCriticality.LOW)

        # Calculate individual factors
        criticality_score = self._calculate_criticality_score(criticality)
        user_impact_score = self._calculate_user_impact_score(affected_users)
        revenue_impact_score = self._calculate_revenue_impact_score(revenue_per_minute)
        sla_impact_score = 1.0 if sla_violation else 0.0

        # Calculate overall impact score
        impact_score = (
            self.weights["criticality"] * criticality_score
            + self.weights["user_impact"] * user_impact_score
            + self.weights["revenue_impact"] * revenue_impact_score
            + self.weights["sla_impact"] * sla_impact_score
        )

        # Determine criticality level
        final_criticality = self._map_score_to_criticality(impact_score)

        # Calculate revenue impact
        revenue_impact = revenue_per_minute * 60  # Per hour estimate

        return BusinessImpact(
            service=service,
            impact_score=impact_score,
            criticality=final_criticality,
            affected_users=affected_users,
            revenue_impact=revenue_impact,
            sla_impact=sla_violation,
            factors={
                "criticality": criticality_score,
                "user_impact": user_impact_score,
                "revenue_impact": revenue_impact_score,
                "sla_impact": sla_impact_score,
            },
        )

    def _calculate_criticality_score(self, criticality: BusinessCriticality) -> float:
        """Calculate criticality score"""
        return {
            BusinessCriticality.LOW: 0.25,
            BusinessCriticality.MEDIUM: 0.5,
            BusinessCriticality.HIGH: 0.75,
            BusinessCriticality.CRITICAL: 1.0,
        }.get(criticality, 0.5)

    def _calculate_user_impact_score(self, affected_users: int) -> float:
        """Calculate user impact score"""
        # Sigmoid function for user impact
        max_users = 10000  # Assumed max users
        normalized = min(affected_users / max_users, 1.0)
        return normalized

    def _calculate_revenue_impact_score(self, revenue_per_minute: float) -> float:
        """Calculate revenue impact score"""
        # Sigmoid function for revenue impact
        max_revenue = 10000  # Assumed max revenue per minute
        normalized = min(revenue_per_minute / max_revenue, 1.0)
        return normalized

    def _map_score_to_criticality(self, score: float) -> BusinessCriticality:
        """Map impact score to criticality level"""
        if score >= 0.75:
            return BusinessCriticality.CRITICAL
        elif score >= 0.5:
            return BusinessCriticality.HIGH
        elif score >= 0.25:
            return BusinessCriticality.MEDIUM
        else:
            return BusinessCriticality.LOW

    @staticmethod
    def _higher_criticality(a: BusinessCriticality, b: BusinessCriticality) -> BusinessCriticality:
        """Return the more severe of two criticality levels."""
        rank = {
            BusinessCriticality.LOW: 0,
            BusinessCriticality.MEDIUM: 1,
            BusinessCriticality.HIGH: 2,
            BusinessCriticality.CRITICAL: 3,
        }
        return a if rank.get(a, 0) >= rank.get(b, 0) else b

    def batch_assess(self, alerts: List[Dict]) -> List[BusinessImpact]:
        """
        Assess multiple alerts in batch

        Args:
            alerts: List of alert dictionaries

        Returns:
            List of business impact assessments
        """
        assessments = []

        for alert in alerts:
            assessment = self.assess(
                service=alert.get("service", "unknown"),
                affected_users=alert.get("affected_users", 0),
                revenue_per_minute=alert.get("revenue_per_minute", 0.0),
                sla_violation=alert.get("sla_violation", False),
                context=alert.get("context"),
            )
            assessments.append(assessment)

        return assessments
