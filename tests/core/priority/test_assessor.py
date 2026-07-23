# -*- coding: utf-8 -*-
"""测试业务影响评估器模块"""

import pytest


class TestBusinessImpactAssessorModule:
    """测试业务影响评估器模块"""

    def test_assessor_module_exists(self):
        """测试评估器模块存在"""
        from core.priority import assessor

        assert assessor is not None

    def test_assessor_has_enums(self):
        """测试评估器模块有枚举"""
        from core.priority import assessor

        # 检查模块有枚举
        assert hasattr(assessor, "BusinessCriticality")

    def test_assessor_has_dataclasses(self):
        """测试评估器模块有数据类"""
        from core.priority import assessor

        # 检查模块有数据类
        assert hasattr(assessor, "BusinessImpact")

    def test_assessor_has_classes(self):
        """测试评估器模块有类"""
        from core.priority import assessor

        # 检查模块有类
        assert hasattr(assessor, "BusinessImpactAssessor")


class TestBusinessCriticality:
    """测试业务关键性枚举"""

    def test_business_criticality_values(self):
        """测试业务关键性值"""
        from core.priority.assessor import BusinessCriticality

        assert BusinessCriticality.LOW.value == "low"
        assert BusinessCriticality.MEDIUM.value == "medium"
        assert BusinessCriticality.HIGH.value == "high"
        assert BusinessCriticality.CRITICAL.value == "critical"


class TestBusinessImpact:
    """测试业务影响数据类"""

    def test_business_impact_creation(self):
        """测试业务影响创建"""
        from core.priority.assessor import (
            BusinessCriticality,
            BusinessImpact,
        )

        impact = BusinessImpact(
            service="payment",
            impact_score=0.9,
            criticality=BusinessCriticality.CRITICAL,
            affected_users=1000,
            revenue_impact=5000.0,
            sla_impact=True,
            factors={"criticality": 1.0, "user_impact": 0.1},
        )

        assert impact.service == "payment"
        assert impact.impact_score == 0.9
        assert impact.criticality == BusinessCriticality.CRITICAL


class TestBusinessImpactAssessor:
    """测试业务影响评估器类"""

    def test_assessor_initialization(self):
        """测试评估器初始化"""
        from core.priority.assessor import BusinessImpactAssessor

        assessor = BusinessImpactAssessor()

        assert assessor.config == {}
        assert "payment" in assessor.service_criticality
        assert "criticality" in assessor.weights

    def test_assessor_initialization_with_config(self):
        """测试评估器初始化（带配置）"""
        from core.priority.assessor import BusinessImpactAssessor

        config = {"custom_key": "custom_value"}
        assessor = BusinessImpactAssessor(config)

        assert assessor.config == config

    def test_assess_critical_service(self):
        """测试评估关键服务"""
        from core.priority.assessor import (
            BusinessCriticality,
            BusinessImpactAssessor,
        )

        assessor = BusinessImpactAssessor()

        impact = assessor.assess(
            service="payment",
            affected_users=1000,
            revenue_per_minute=100.0,
            sla_violation=True,
        )

        assert impact.service == "payment"
        assert impact.impact_score > 0.5
        assert impact.criticality in [BusinessCriticality.HIGH, BusinessCriticality.CRITICAL]

    def test_assess_unknown_service(self):
        """测试评估未知服务"""
        from core.priority.assessor import (
            BusinessCriticality,
            BusinessImpactAssessor,
        )

        assessor = BusinessImpactAssessor()

        impact = assessor.assess(
            service="unknown_service",
            affected_users=0,
            revenue_per_minute=0.0,
            sla_violation=False,
        )

        assert impact.service == "unknown_service"
        # Unknown service gets MEDIUM criticality from mapping, but impact score is low
        # so final criticality is mapped from score
        assert impact.criticality == BusinessCriticality.LOW  # Score 0.2 maps to LOW

    def test_assess_with_high_user_impact(self):
        """测试评估（高用户影响）"""
        from core.priority.assessor import BusinessImpactAssessor

        assessor = BusinessImpactAssessor()

        impact = assessor.assess(
            service="api",
            affected_users=10000,  # High user impact
            revenue_per_minute=0.0,
            sla_violation=False,
        )

        assert impact.affected_users == 10000
        assert impact.factors["user_impact"] == 1.0

    def test_assess_with_revenue_impact(self):
        """测试评估（收入影响）"""
        from core.priority.assessor import BusinessImpactAssessor

        assessor = BusinessImpactAssessor()

        impact = assessor.assess(
            service="api",
            affected_users=0,
            revenue_per_minute=10000.0,  # High revenue impact
            sla_violation=False,
        )

        assert impact.revenue_impact == 600000.0  # Per hour
        assert impact.factors["revenue_impact"] == 1.0

    def test_assess_with_sla_violation(self):
        """测试评估（SLA违规）"""
        from core.priority.assessor import BusinessImpactAssessor

        assessor = BusinessImpactAssessor()

        impact = assessor.assess(
            service="api",
            affected_users=0,
            revenue_per_minute=0.0,
            sla_violation=True,
        )

        assert impact.sla_impact is True
        assert impact.factors["sla_impact"] == 1.0

    def test_calculate_criticality_score(self):
        """测试计算关键性分数"""
        from core.priority.assessor import (
            BusinessCriticality,
            BusinessImpactAssessor,
        )

        assessor = BusinessImpactAssessor()

        score = assessor._calculate_criticality_score(BusinessCriticality.CRITICAL)

        assert score == 1.0

    def test_calculate_user_impact_score(self):
        """测试计算用户影响分数"""
        from core.priority.assessor import BusinessImpactAssessor

        assessor = BusinessImpactAssessor()

        score = assessor._calculate_user_impact_score(5000)

        assert score == 0.5

    def test_calculate_revenue_impact_score(self):
        """测试计算收入影响分数"""
        from core.priority.assessor import BusinessImpactAssessor

        assessor = BusinessImpactAssessor()

        score = assessor._calculate_revenue_impact_score(5000.0)

        assert score == 0.5

    def test_map_score_to_criticality(self):
        """测试映射分数到关键性"""
        from core.priority.assessor import (
            BusinessCriticality,
            BusinessImpactAssessor,
        )

        assessor = BusinessImpactAssessor()

        criticality = assessor._map_score_to_criticality(0.8)

        assert criticality == BusinessCriticality.CRITICAL

    def test_batch_assess(self):
        """测试批量评估"""
        from core.priority.assessor import BusinessImpactAssessor

        assessor = BusinessImpactAssessor()

        alerts = [
            {"service": "payment", "affected_users": 100, "revenue_per_minute": 10.0},
            {"service": "api", "affected_users": 50, "revenue_per_minute": 5.0},
        ]

        assessments = assessor.batch_assess(alerts)

        assert len(assessments) == 2
        assert assessments[0].service == "payment"
        assert assessments[1].service == "api"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
