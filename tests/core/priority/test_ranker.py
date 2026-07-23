# -*- coding: utf-8 -*-
"""测试优先级排序器模块"""

import pytest


class TestPriorityRankerModule:
    """测试优先级排序器模块"""

    def test_ranker_module_exists(self):
        """测试排序器模块存在"""
        from core.priority import ranker

        assert ranker is not None

    def test_ranker_has_dataclasses(self):
        """测试排序器模块有数据类"""
        from core.priority import ranker

        # 检查模块有数据类
        assert hasattr(ranker, "PriorityRank")

    def test_ranker_has_classes(self):
        """测试排序器模块有类"""
        from core.priority import ranker

        # 检查模块有类
        assert hasattr(ranker, "PriorityRanker")


class TestPriorityRank:
    """测试优先级排序数据类"""

    def test_priority_rank_creation(self):
        """测试优先级排序创建"""
        from core.priority.assessor import BusinessCriticality, BusinessImpact
        from core.priority.ranker import PriorityRank

        rank = PriorityRank(
            alert_id="alert_1",
            priority_score=0.8,
            priority_level="P1",
            business_impact=BusinessImpact(
                service="api",
                impact_score=0.8,
                criticality=BusinessCriticality.HIGH,
                affected_users=100,
                revenue_impact=1000.0,
                sla_impact=False,
                factors={},
            ),
            rank=1,
        )

        assert rank.alert_id == "alert_1"
        assert rank.priority_score == 0.8
        assert rank.priority_level == "P1"
        assert rank.rank == 1


class TestPriorityRanker:
    """测试优先级排序器类"""

    def test_ranker_initialization(self):
        """测试排序器初始化"""
        from core.priority.ranker import PriorityRanker

        ranker = PriorityRanker()

        assert ranker.assessor is not None
        assert "P0" in ranker.thresholds
        assert ranker.thresholds["P0"] == 0.9

    def test_ranker_initialization_with_assessor(self):
        """测试排序器初始化（带评估器）"""
        from core.priority.assessor import BusinessImpactAssessor
        from core.priority.ranker import PriorityRanker

        assessor = BusinessImpactAssessor()
        ranker = PriorityRanker(assessor)

        assert ranker.assessor is assessor

    def test_rank_alerts(self):
        """测试排序告警"""
        from core.priority.ranker import PriorityRanker

        ranker = PriorityRanker()

        alerts = [
            {"id": "alert_1", "service": "payment", "affected_users": 1000},
            {"id": "alert_2", "service": "api", "affected_users": 100},
        ]

        ranks = ranker.rank_alerts(alerts)

        assert len(ranks) == 2
        assert ranks[0].rank == 1
        assert ranks[1].rank == 2

    def test_rank_alerts_with_urgency(self):
        """测试排序告警（带紧急程度）"""
        from core.priority.ranker import PriorityRanker

        ranker = PriorityRanker()

        alerts = [
            {"id": "alert_1", "service": "api", "affected_users": 100, "urgency": "critical"},
            {"id": "alert_2", "service": "api", "affected_users": 100, "urgency": "low"},
        ]

        ranks = ranker.rank_alerts(alerts)

        assert len(ranks) == 2
        # Critical urgency should have higher score
        assert ranks[0].priority_score >= ranks[1].priority_score

    def test_calculate_priority_score(self):
        """测试计算优先级分数"""
        from core.priority.assessor import BusinessCriticality, BusinessImpact
        from core.priority.ranker import PriorityRanker

        ranker = PriorityRanker()

        alert = {"id": "alert_1", "service": "api"}
        impact = BusinessImpact(
            service="api",
            impact_score=0.5,
            criticality=BusinessCriticality.MEDIUM,
            affected_users=0,
            revenue_impact=0.0,
            sla_impact=False,
            factors={},
        )

        score = ranker._calculate_priority_score(alert, impact)

        assert 0 <= score <= 1.0

    def test_calculate_priority_score_with_urgency(self):
        """测试计算优先级分数（带紧急程度）"""
        from core.priority.assessor import BusinessCriticality, BusinessImpact
        from core.priority.ranker import PriorityRanker

        ranker = PriorityRanker()

        alert = {"id": "alert_1", "service": "api", "urgency": "critical"}
        impact = BusinessImpact(
            service="api",
            impact_score=0.5,
            criticality=BusinessCriticality.MEDIUM,
            affected_users=0,
            revenue_impact=0.0,
            sla_impact=False,
            factors={},
        )

        score = ranker._calculate_priority_score(alert, impact)

        assert 0 <= score <= 1.0

    def test_map_score_to_level(self):
        """测试映射分数到级别"""
        from core.priority.ranker import PriorityRanker

        ranker = PriorityRanker()

        assert ranker._map_score_to_level(0.95) == "P0"
        assert ranker._map_score_to_level(0.8) == "P1"
        assert ranker._map_score_to_level(0.6) == "P2"
        assert ranker._map_score_to_level(0.3) == "P3"
        assert ranker._map_score_to_level(0.1) == "P4"

    def test_get_top_n(self):
        """测试获取前N个"""
        from core.priority.ranker import PriorityRanker

        ranker = PriorityRanker()

        alerts = [
            {"id": "alert_1", "service": "payment", "affected_users": 1000},
            {"id": "alert_2", "service": "api", "affected_users": 100},
            {"id": "alert_3", "service": "cache", "affected_users": 50},
        ]

        top_2 = ranker.get_top_n(alerts, n=2)

        assert len(top_2) == 2

    def test_filter_by_priority(self):
        """测试按优先级过滤"""
        from core.priority.ranker import PriorityRanker

        ranker = PriorityRanker()

        alerts = [
            {"id": "alert_1", "service": "payment", "affected_users": 1000},
            {"id": "alert_2", "service": "api", "affected_users": 100},
        ]

        filtered = ranker.filter_by_priority(alerts, min_level="P1")

        assert isinstance(filtered, list)

    def test_filter_by_priority_p0(self):
        """测试按优先级过滤（P0）"""
        from core.priority.ranker import PriorityRanker

        ranker = PriorityRanker()

        alerts = [
            {"id": "alert_1", "service": "payment", "affected_users": 10000},
            {"id": "alert_2", "service": "api", "affected_users": 100},
        ]

        filtered = ranker.filter_by_priority(alerts, min_level="P0")

        assert isinstance(filtered, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
