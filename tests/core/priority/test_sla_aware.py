# -*- coding: utf-8 -*-
"""测试SLA感知调度器模块"""

from datetime import datetime, timedelta

import pytest


class TestSLAAwareSchedulerModule:
    """测试SLA感知调度器模块"""

    def test_sla_aware_module_exists(self):
        """测试SLA感知模块存在"""
        from core.priority import sla_aware

        assert sla_aware is not None

    def test_sla_aware_has_dataclasses(self):
        """测试SLA感知模块有数据类"""
        from core.priority import sla_aware

        # 检查模块有数据类
        assert hasattr(sla_aware, "SLARequirement")
        assert hasattr(sla_aware, "SLAViolation")

    def test_sla_aware_has_classes(self):
        """测试SLA感知模块有类"""
        from core.priority import sla_aware

        # 检查模块有类
        assert hasattr(sla_aware, "SLAAwareScheduler")


class TestSLARequirement:
    """测试SLA要求数据类"""

    def test_sla_requirement_creation(self):
        """测试SLA要求创建"""
        from core.priority.sla_aware import SLARequirement

        requirement = SLARequirement(
            service="payment",
            response_time_target=0.5,
            availability_target=99.9,
            deadline=datetime.now() + timedelta(hours=24),
            priority=1,
        )

        assert requirement.service == "payment"
        assert requirement.response_time_target == 0.5
        assert requirement.availability_target == 99.9


class TestSLAViolation:
    """测试SLA违规数据类"""

    def test_sla_violation_creation(self):
        """测试SLA违规创建"""
        from core.priority.sla_aware import SLAViolation

        violation = SLAViolation(
            service="payment",
            violation_type="response_time",
            severity="high",
            timestamp=datetime.now(),
            impact=0.8,
        )

        assert violation.service == "payment"
        assert violation.violation_type == "response_time"
        assert violation.severity == "high"


class TestSLAAwareScheduler:
    """测试SLA感知调度器类"""

    def test_scheduler_initialization(self):
        """测试调度器初始化"""
        from core.priority.sla_aware import SLAAwareScheduler

        scheduler = SLAAwareScheduler()

        assert scheduler.sla_requirements == {}
        assert scheduler.violations == []

    def test_register_sla(self):
        """测试注册SLA"""
        from core.priority.sla_aware import SLAAwareScheduler, SLARequirement

        scheduler = SLAAwareScheduler()

        requirement = SLARequirement(
            service="payment",
            response_time_target=0.5,
            availability_target=99.9,
            deadline=datetime.now() + timedelta(hours=24),
        )

        scheduler.register_sla(requirement)

        assert "payment" in scheduler.sla_requirements
        assert scheduler.sla_requirements["payment"].response_time_target == 0.5

    def test_check_sla_compliant(self):
        """测试检查SLA合规（合规）"""
        from core.priority.sla_aware import SLAAwareScheduler, SLARequirement

        scheduler = SLAAwareScheduler()

        requirement = SLARequirement(
            service="payment",
            response_time_target=0.5,
            availability_target=99.9,
            deadline=datetime.now() + timedelta(hours=24),
        )

        scheduler.register_sla(requirement)

        metrics = {"response_time": 0.3, "availability": 99.95}

        is_compliant = scheduler.check_sla_compliance("payment", metrics)

        assert is_compliant is True

    def test_check_sla_response_time_violation(self):
        """测试检查SLA合规（响应时间违规）"""
        from core.priority.sla_aware import SLAAwareScheduler, SLARequirement

        scheduler = SLAAwareScheduler()

        requirement = SLARequirement(
            service="payment",
            response_time_target=0.5,
            availability_target=99.9,
            deadline=datetime.now() + timedelta(hours=24),
        )

        scheduler.register_sla(requirement)

        metrics = {"response_time": 1.0, "availability": 99.95}

        is_compliant = scheduler.check_sla_compliance("payment", metrics)

        assert is_compliant is False
        assert len(scheduler.violations) == 1

    def test_check_sla_availability_violation(self):
        """测试检查SLA合规（可用性违规）"""
        from core.priority.sla_aware import SLAAwareScheduler, SLARequirement

        scheduler = SLAAwareScheduler()

        requirement = SLARequirement(
            service="payment",
            response_time_target=0.5,
            availability_target=99.9,
            deadline=datetime.now() + timedelta(hours=24),
        )

        scheduler.register_sla(requirement)

        metrics = {"response_time": 0.3, "availability": 99.5}

        is_compliant = scheduler.check_sla_compliance("payment", metrics)

        assert is_compliant is False
        assert len(scheduler.violations) == 1

    def test_check_sla_no_sla_defined(self):
        """测试检查SLA合规（无SLA定义）"""
        from core.priority.sla_aware import SLAAwareScheduler

        scheduler = SLAAwareScheduler()

        metrics = {"response_time": 1.0, "availability": 99.5}

        is_compliant = scheduler.check_sla_compliance("unknown_service", metrics)

        assert is_compliant is True

    def test_schedule_tasks_with_sla(self):
        """测试调度任务（带SLA）"""
        from core.priority.sla_aware import SLAAwareScheduler, SLARequirement

        scheduler = SLAAwareScheduler()

        requirement = SLARequirement(
            service="payment",
            response_time_target=0.5,
            availability_target=99.9,
            deadline=datetime.now() + timedelta(hours=1),
            priority=2,
        )

        scheduler.register_sla(requirement)

        tasks = [
            {"id": "task_1", "service": "payment"},
            {"id": "task_2", "service": "api"},
        ]

        scheduled = scheduler.schedule_tasks(tasks)

        assert len(scheduled) == 2
        assert "sla_score" in scheduled[0]
        assert "time_to_deadline" in scheduled[0]

    def test_schedule_tasks_without_sla(self):
        """测试调度任务（无SLA）"""
        from core.priority.sla_aware import SLAAwareScheduler

        scheduler = SLAAwareScheduler()

        tasks = [
            {"id": "task_1", "service": "unknown"},
        ]

        scheduled = scheduler.schedule_tasks(tasks)

        assert len(scheduled) == 1
        assert scheduled[0]["sla_score"] == 0.0
        assert scheduled[0]["time_to_deadline"] is None

    def test_schedule_tasks_priority_order(self):
        """测试调度任务（优先级顺序）"""
        from core.priority.sla_aware import SLAAwareScheduler, SLARequirement

        scheduler = SLAAwareScheduler()

        # High priority, far deadline
        requirement1 = SLARequirement(
            service="payment",
            response_time_target=0.5,
            availability_target=99.9,
            deadline=datetime.now() + timedelta(hours=24),
            priority=2,
        )

        # Low priority, near deadline
        requirement2 = SLARequirement(
            service="api",
            response_time_target=0.5,
            availability_target=99.9,
            deadline=datetime.now() + timedelta(hours=1),
            priority=1,
        )

        scheduler.register_sla(requirement1)
        scheduler.register_sla(requirement2)

        tasks = [
            {"id": "task_1", "service": "payment"},
            {"id": "task_2", "service": "api"},
        ]

        scheduled = scheduler.schedule_tasks(tasks)

        # The task with higher SLA score should be first
        assert scheduled[0]["sla_score"] >= scheduled[1]["sla_score"]

    def test_get_violations(self):
        """测试获取违规"""
        from core.priority.sla_aware import SLAAwareScheduler, SLARequirement

        scheduler = SLAAwareScheduler()

        requirement = SLARequirement(
            service="payment",
            response_time_target=0.5,
            availability_target=99.9,
            deadline=datetime.now() + timedelta(hours=24),
        )

        scheduler.register_sla(requirement)

        metrics = {"response_time": 1.0}
        scheduler.check_sla_compliance("payment", metrics)

        violations = scheduler.get_violations()

        assert len(violations) == 1

    def test_get_violations_by_service(self):
        """测试获取违规（按服务）"""
        from core.priority.sla_aware import SLAAwareScheduler, SLARequirement

        scheduler = SLAAwareScheduler()

        requirement = SLARequirement(
            service="payment",
            response_time_target=0.5,
            availability_target=99.9,
            deadline=datetime.now() + timedelta(hours=24),
        )

        scheduler.register_sla(requirement)

        metrics = {"response_time": 1.0}
        scheduler.check_sla_compliance("payment", metrics)

        violations = scheduler.get_violations(service="payment")

        assert len(violations) == 1
        assert violations[0].service == "payment"

    def test_get_violations_by_timestamp(self):
        """测试获取违规（按时间戳）"""
        from core.priority.sla_aware import SLAAwareScheduler, SLARequirement

        scheduler = SLAAwareScheduler()

        requirement = SLARequirement(
            service="payment",
            response_time_target=0.5,
            availability_target=99.9,
            deadline=datetime.now() + timedelta(hours=24),
        )

        scheduler.register_sla(requirement)

        metrics = {"response_time": 1.0}
        scheduler.check_sla_compliance("payment", metrics)

        since = datetime.now() - timedelta(minutes=5)
        violations = scheduler.get_violations(since=since)

        assert len(violations) == 1

    def test_get_sla_status(self):
        """测试获取SLA状态"""
        from core.priority.sla_aware import SLAAwareScheduler, SLARequirement

        scheduler = SLAAwareScheduler()

        requirement = SLARequirement(
            service="payment",
            response_time_target=0.5,
            availability_target=99.9,
            deadline=datetime.now() + timedelta(hours=24),
        )

        scheduler.register_sla(requirement)

        status = scheduler.get_sla_status("payment")

        assert status["service"] == "payment"
        assert status["sla_defined"] is True
        assert status["response_time_target"] == 0.5

    def test_get_sla_status_no_sla(self):
        """测试获取SLA状态（无SLA）"""
        from core.priority.sla_aware import SLAAwareScheduler

        scheduler = SLAAwareScheduler()

        status = scheduler.get_sla_status("unknown_service")

        assert status["status"] == "no_sla_defined"

    def test_get_sla_status_with_violations(self):
        """测试获取SLA状态（有违规）"""
        from core.priority.sla_aware import SLAAwareScheduler, SLARequirement

        scheduler = SLAAwareScheduler()

        requirement = SLARequirement(
            service="payment",
            response_time_target=0.5,
            availability_target=99.9,
            deadline=datetime.now() + timedelta(hours=24),
        )

        scheduler.register_sla(requirement)

        metrics = {"response_time": 1.0}
        scheduler.check_sla_compliance("payment", metrics)

        status = scheduler.get_sla_status("payment")

        assert status["recent_violations"] == 1
        assert status["compliance_status"] == "violated"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
