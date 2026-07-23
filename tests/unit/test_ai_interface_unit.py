# -*- coding: utf-8 -*-
# tests/unit/test_ai_interface_unit.py
# AI接口模块单元测试
import pytest


class TestAnalysisType:
    """分析类型枚举测试"""

    def test_analysis_type_enum_values(self):
        """测试分析类型枚举值"""
        from core.ai_interface import AnalysisType

        assert AnalysisType.ANOMALY == "anomaly"
        assert AnalysisType.ROOT_CAUSE == "root_cause"
        assert AnalysisType.RUNBOOK == "runbook"
        assert AnalysisType.GENERAL == "general"

    def test_analysis_type_enum_members(self):
        """测试分析类型枚举成员"""
        from core.ai_interface import AnalysisType

        assert hasattr(AnalysisType, "ANOMALY")
        assert hasattr(AnalysisType, "ROOT_CAUSE")
        assert hasattr(AnalysisType, "RUNBOOK")
        assert hasattr(AnalysisType, "GENERAL")

    def test_analysis_type_string_conversion(self):
        """测试分析类型字符串转换"""
        from core.ai_interface import AnalysisType

        assert AnalysisType.ANOMALY.value == "anomaly"
        assert AnalysisType.ROOT_CAUSE.value == "root_cause"


class TestAIAnalysisService:
    """AI分析服务接口测试"""

    def test_interface_is_abstract(self):
        """测试接口是抽象的"""
        from abc import ABC

        from core.ai_interface import AIAnalysisService

        # 验证是抽象基类
        assert issubclass(AIAnalysisService, ABC)

        # 验证不能直接实例化
        with pytest.raises(TypeError):
            AIAnalysisService()

    def test_interface_has_analyze_method(self):
        """测试接口有analyze方法"""
        from core.ai_interface import AIAnalysisService

        assert hasattr(AIAnalysisService, "analyze")
        assert callable(AIAnalysisService.analyze)

    def test_interface_has_observe_method(self):
        """测试接口有observe方法"""
        from core.ai_interface import AIAnalysisService

        assert hasattr(AIAnalysisService, "observe")
        assert callable(AIAnalysisService.observe)

    def test_interface_has_generate_runbook_method(self):
        """测试接口有generate_runbook方法"""
        from core.ai_interface import AIAnalysisService

        assert hasattr(AIAnalysisService, "generate_runbook")
        assert callable(AIAnalysisService.generate_runbook)

    def test_interface_has_search_similar_method(self):
        """测试接口有search_similar方法"""
        from core.ai_interface import AIAnalysisService

        assert hasattr(AIAnalysisService, "search_similar")
        assert callable(AIAnalysisService.search_similar)

    def test_interface_has_get_health_status_method(self):
        """测试接口有get_health_status方法"""
        from core.ai_interface import AIAnalysisService

        assert hasattr(AIAnalysisService, "get_health_status")
        assert callable(AIAnalysisService.get_health_status)

    def test_interface_implementation(self):
        """测试接口实现"""
        from core.ai_interface import AIAnalysisService, AnalysisType

        # 创建一个实现
        class MockAIAnalysisService(AIAnalysisService):
            async def analyze(self, context, analysis_type=AnalysisType.GENERAL):
                return {"result": "mock"}

            async def observe(self, data):
                return {"observation": "mock"}

            async def generate_runbook(self, alert_data, context=None):
                return {"runbook": "mock"}

            async def search_similar(self, query, limit=10):
                return [{"case": "mock"}]

            async def get_health_status(self):
                return {"status": "healthy"}

        # 验证可以实例化实现
        service = MockAIAnalysisService()
        assert service is not None

        # 验证方法存在
        assert callable(service.analyze)
        assert callable(service.observe)
        assert callable(service.generate_runbook)
        assert callable(service.search_similar)
        assert callable(service.get_health_status)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
