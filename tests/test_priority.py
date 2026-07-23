# -*- coding: utf-8 -*-
"""
Priority Module Tests
"""

from datetime import datetime, timedelta

import pytest  # noqa: F401

from core.priority import (  # noqa: F401
    BusinessCriticality,
    BusinessImpact,
    BusinessImpactAssessor,
    PriorityRank,
    PriorityRanker,
    Resource,
    ResourceAllocator,
    SLAAwareScheduler,
    SLARequirement,
)


class TestBusinessImpactAssessor:
    """Test business impact assessor"""

    def test_assess_critical_service(self):
        """Test assessment of critical service"""
        assessor = BusinessImpactAssessor()

        impact = assessor.assess(
            service="payment", affected_users=1000, revenue_per_minute=100.0, sla_violation=True
        )

        assert impact.service == "payment"
        assert impact.criticality == BusinessCriticality.CRITICAL
        assert impact.impact_score > 0.8

    def test_assess_low_priority_service(self):
        """Test assessment of low priority service"""
        assessor = BusinessImpactAssessor()

        impact = assessor.assess(
            service="logging", affected_users=10, revenue_per_minute=0.0, sla_violation=False
        )

        assert impact.criticality == BusinessCriticality.LOW
        assert impact.impact_score < 0.5


class TestPriorityRanker:
    """Test priority ranker"""

    def test_rank_alerts(self):
        """Test alert ranking"""
        assessor = BusinessImpactAssessor()
        ranker = PriorityRanker(assessor)

        alerts = [
            {"id": "1", "service": "payment", "affected_users": 1000},
            {"id": "2", "service": "logging", "affected_users": 10},
        ]

        ranks = ranker.rank_alerts(alerts)

        assert len(ranks) == 2
        assert ranks[0].priority_score > ranks[1].priority_score

    def test_get_top_n(self):
        """Test getting top N alerts"""
        assessor = BusinessImpactAssessor()
        ranker = PriorityRanker(assessor)

        alerts = [{"id": str(i), "service": "api", "affected_users": i * 100} for i in range(10)]

        top_5 = ranker.get_top_n(alerts, 5)

        assert len(top_5) == 5


class TestSLAAwareScheduler:
    """Test SLA-aware scheduler"""

    def test_register_sla(self):
        """Test SLA registration"""
        scheduler = SLAAwareScheduler()

        sla = SLARequirement(
            service="payment",
            response_time_target=0.5,
            availability_target=0.999,
            deadline=datetime.now() + timedelta(hours=24),
        )

        scheduler.register_sla(sla)

        assert "payment" in scheduler.sla_requirements

    def test_schedule_tasks(self):
        """Test task scheduling with SLA awareness"""
        scheduler = SLAAwareScheduler()

        sla = SLARequirement(
            service="payment",
            response_time_target=0.5,
            availability_target=0.999,
            deadline=datetime.now() + timedelta(hours=1),
            priority=2,
        )
        scheduler.register_sla(sla)

        tasks = [
            {"id": "1", "service": "payment", "priority": 0.5},
            {"id": "2", "service": "logging", "priority": 0.3},
        ]

        scheduled = scheduler.schedule_tasks(tasks)

        assert len(scheduled) == 2
        assert scheduled[0]["sla_score"] >= scheduled[1]["sla_score"]


class TestResourceAllocator:
    """Test resource allocator"""

    def test_add_resource(self):
        """Test adding resource"""
        allocator = ResourceAllocator()

        resource = Resource(id="cpu_pool", type="cpu", capacity=100.0, available=100.0)

        allocator.add_resource(resource)

        assert "cpu_pool" in allocator.resources

    def test_allocate_resources(self):
        """Test resource allocation"""
        allocator = ResourceAllocator()

        allocator.add_resource(Resource("cpu_1", "cpu", 50.0, 50.0))

        tasks = [
            {"id": "task1", "priority": 0.8, "resource_requirement": {"cpu": 20.0}},
            {"id": "task2", "priority": 0.5, "resource_requirement": {"cpu": 10.0}},
        ]

        allocations = allocator.allocate(tasks, "cpu")

        assert len(allocations) == 2
