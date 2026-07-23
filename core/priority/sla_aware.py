# -*- coding: utf-8 -*-
"""
SLA-Aware Scheduler
Schedules tasks considering SLA requirements
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from loguru import logger


@dataclass
class SLARequirement:
    """
    SLA requirement

    Attributes:
        service: Service name
        response_time_target: Target response time in seconds
        availability_target: Target availability percentage
        deadline: SLA deadline
        priority: SLA priority
    """

    service: str
    response_time_target: float
    availability_target: float
    deadline: datetime
    priority: int = 1


@dataclass
class SLAViolation:
    """
    SLA violation record

    Attributes:
        service: Service name
        violation_type: Type of violation
        severity: Violation severity
        timestamp: Violation timestamp
        impact: Business impact
    """

    service: str
    violation_type: str
    severity: str
    timestamp: datetime
    impact: float


class SLAAwareScheduler:
    """
    SLA-aware task scheduler

    Schedules tasks considering SLA requirements and deadlines
    """

    def __init__(self):
        """Initialize SLA-aware scheduler"""
        self.sla_requirements: Dict[str, SLARequirement] = {}
        self.violations: List[SLAViolation] = []

    def register_sla(self, requirement: SLARequirement) -> None:
        """
        Register SLA requirement

        Args:
            requirement: SLA requirement
        """
        self.sla_requirements[requirement.service] = requirement
        logger.info(f"Registered SLA for {requirement.service}")

    def check_sla_compliance(self, service: str, current_metrics: Dict) -> bool:
        """
        Check if service is SLA compliant

        Args:
            service: Service name
            current_metrics: Current service metrics

        Returns:
            True if compliant
        """
        if service not in self.sla_requirements:
            return True  # No SLA defined

        sla = self.sla_requirements[service]

        # Check response time
        if "response_time" in current_metrics:
            if current_metrics["response_time"] > sla.response_time_target:
                self._record_violation(
                    service,
                    "response_time",
                    "high",
                    current_metrics["response_time"] / sla.response_time_target,
                )
                return False

        # Check availability
        if "availability" in current_metrics:
            if current_metrics["availability"] < sla.availability_target:
                self._record_violation(
                    service,
                    "availability",
                    "high",
                    sla.availability_target - current_metrics["availability"],
                )
                return False

        return True

    def _record_violation(
        self, service: str, violation_type: str, severity: str, impact: float
    ) -> None:
        """
        Record SLA violation

        Args:
            service: Service name
            violation_type: Type of violation
            severity: Severity level
            impact: Impact score
        """
        violation = SLAViolation(
            service=service,
            violation_type=violation_type,
            severity=severity,
            timestamp=datetime.now(),
            impact=impact,
        )
        self.violations.append(violation)
        logger.warning(f"SLA violation recorded: {service} - {violation_type}")

    def schedule_tasks(
        self, tasks: List[Dict], current_time: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Schedule tasks considering SLA deadlines

        Args:
            tasks: List of tasks to schedule
            current_time: Current time

        Returns:
            Scheduled tasks sorted by SLA priority
        """
        if current_time is None:
            current_time = datetime.now()

        # Calculate SLA urgency for each task
        scheduled_tasks = []

        for task in tasks:
            service = task.get("service", "unknown")

            if service in self.sla_requirements:
                sla = self.sla_requirements[service]

                # Calculate time to deadline
                time_to_deadline = (sla.deadline - current_time).total_seconds()

                # Calculate urgency score (closer to deadline = higher urgency)
                urgency = 1.0 / max(1.0, time_to_deadline / 3600)  # Normalize by hour

                # Combine with SLA priority
                sla_score = urgency * sla.priority

                task["sla_score"] = sla_score
                task["time_to_deadline"] = time_to_deadline
            else:
                task["sla_score"] = 0.0
                task["time_to_deadline"] = None

            scheduled_tasks.append(task)

        # Sort by SLA score (descending)
        scheduled_tasks.sort(key=lambda t: t.get("sla_score", 0), reverse=True)

        logger.info(f"Scheduled {len(scheduled_tasks)} tasks with SLA awareness")

        return scheduled_tasks

    def get_violations(
        self, service: Optional[str] = None, since: Optional[datetime] = None
    ) -> List[SLAViolation]:
        """
        Get SLA violations

        Args:
            service: Filter by service (optional)
            since: Filter by timestamp (optional)

        Returns:
            List of violations
        """
        violations = self.violations

        if service:
            violations = [v for v in violations if v.service == service]

        if since:
            violations = [v for v in violations if v.timestamp >= since]

        return violations

    def get_sla_status(self, service: str) -> Dict:
        """
        Get SLA status for a service

        Args:
            service: Service name

        Returns:
            SLA status dictionary
        """
        if service not in self.sla_requirements:
            return {"status": "no_sla_defined"}

        sla = self.sla_requirements[service]
        recent_violations = [
            v
            for v in self.violations
            if v.service == service and v.timestamp > datetime.now() - timedelta(hours=24)
        ]

        return {
            "service": service,
            "sla_defined": True,
            "response_time_target": sla.response_time_target,
            "availability_target": sla.availability_target,
            "deadline": sla.deadline.isoformat(),
            "recent_violations": len(recent_violations),
            "compliance_status": "compliant" if not recent_violations else "violated",
        }
