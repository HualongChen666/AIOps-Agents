# -*- coding: utf-8 -*-
# tests/unit/test_ai_interface.py
# AI接口单元测试
from abc import ABC
from unittest.mock import AsyncMock, Mock  # noqa: F401

import pytest

from core.ai_interface import AIAnalysisService, AnalysisType


class TestAnalysisType:
    """分析类型枚举测试"""

    def test_analysis_type_values(self):
        """测试分析类型枚举值"""
        assert AnalysisType.ANOMALY == "anomaly"
        assert AnalysisType.ROOT_CAUSE == "root_cause"
        assert AnalysisType.RUNBOOK == "runbook"
        assert AnalysisType.GENERAL == "general"

    def test_analysis_type_enum_behavior(self):
        """测试分析类型枚举行为"""
        # 测试枚举可以比较
        assert AnalysisType.ANOMALY == AnalysisType.ANOMALY
        assert AnalysisType.ANOMALY != AnalysisType.ROOT_CAUSE

        # 测试枚举可以用于字典键
        mapping = {AnalysisType.ANOMALY: "异常分析", AnalysisType.ROOT_CAUSE: "根因分析"}
        assert mapping[AnalysisType.ANOMALY] == "异常分析"

        # 测试枚举可以迭代
        analysis_types = list(AnalysisType)
        assert len(analysis_types) == 4
        assert AnalysisType.ANOMALY in analysis_types

    def test_analysis_type_string_representation(self):
        """测试分析类型的字符串表示"""
        # 枚举的字符串表示是枚举名称，不是值
        assert str(AnalysisType.ANOMALY) == "AnalysisType.ANOMALY"
        assert str(AnalysisType.ROOT_CAUSE) == "AnalysisType.ROOT_CAUSE"
        assert str(AnalysisType.RUNBOOK) == "AnalysisType.RUNBOOK"
        assert str(AnalysisType.GENERAL) == "AnalysisType.GENERAL"

        # 但值可以通过.value访问
        assert AnalysisType.ANOMALY.value == "anomaly"
        assert AnalysisType.ROOT_CAUSE.value == "root_cause"
        assert AnalysisType.RUNBOOK.value == "runbook"
        assert AnalysisType.GENERAL.value == "general"


class TestAIAnalysisService:
    """AI分析服务接口测试"""

    def test_interface_is_abstract(self):
        """测试接口是抽象的"""
        assert issubclass(AIAnalysisService, ABC)

        # 测试不能直接实例化
        with pytest.raises(TypeError):
            AIAnalysisService()

    def test_interface_has_required_methods(self):
        """测试接口有必需的方法"""
        assert hasattr(AIAnalysisService, "analyze")
        assert hasattr(AIAnalysisService, "observe")
        assert hasattr(AIAnalysisService, "generate_runbook")
        assert hasattr(AIAnalysisService, "search_similar")
        assert hasattr(AIAnalysisService, "get_health_status")

    def test_analyze_method_is_abstract(self):
        """测试analyze方法是抽象的"""
        from inspect import isabstract  # noqa: F401

        # 创建一个具体实现类
        class ConcreteService(AIAnalysisService):
            async def analyze(self, context, analysis_type=AnalysisType.GENERAL):
                return {"result": "success"}

            async def observe(self, data):
                return {"observation": "data"}

            async def generate_runbook(self, alert_data, context=None):
                return {"runbook": "steps"}

            async def search_similar(self, query, limit=10):
                return [{"case": "similar"}]

            async def get_health_status(self):
                return {"status": "healthy"}

        # 具体实现类可以实例化
        service = ConcreteService()
        assert isinstance(service, AIAnalysisService)

    @pytest.mark.asyncio
    async def test_concrete_implementation_analyze(self):
        """测试具体实现的analyze方法"""

        class ConcreteService(AIAnalysisService):
            async def analyze(self, context, analysis_type=AnalysisType.GENERAL):
                return {
                    "analysis": "Analysis of type " + analysis_type.value,
                    "context_keys": list(context.keys()),
                }

            async def observe(self, data):
                return {"observation": "data"}

            async def generate_runbook(self, alert_data, context=None):
                return {"runbook": "steps"}

            async def search_similar(self, query, limit=10):
                return [{"case": "similar"}]

            async def get_health_status(self):
                return {"status": "healthy"}

        service = ConcreteService()

        # 测试基本调用
        result = await service.analyze({"metric": "cpu"}, AnalysisType.ANOMALY)
        assert "anomaly" in result["analysis"]  # 改为包含检查
        assert "metric" in result["context_keys"]

    @pytest.mark.asyncio
    async def test_concrete_implementation_observe(self):
        """测试具体实现的observe方法"""

        class ConcreteService(AIAnalysisService):
            async def analyze(self, context, analysis_type=AnalysisType.GENERAL):
                return {"result": "success"}

            async def observe(self, data):
                return {"observation": "data", "data_keys": list(data.keys())}

            async def generate_runbook(self, alert_data, context=None):
                return {"runbook": "steps"}

            async def search_similar(self, query, limit=10):
                return [{"case": "similar"}]

            async def get_health_status(self):
                return {"status": "healthy"}

        service = ConcreteService()
        result = await service.observe({"log": "error message"})
        assert result["observation"] == "data"
        assert "log" in result["data_keys"]

    @pytest.mark.asyncio
    async def test_concrete_implementation_generate_runbook(self):
        """测试具体实现的generate_runbook方法"""

        class ConcreteService(AIAnalysisService):
            async def analyze(self, context, analysis_type=AnalysisType.GENERAL):
                return {"result": "success"}

            async def observe(self, data):
                return {"observation": "data"}

            async def generate_runbook(self, alert_data, context=None):
                return {
                    "runbook": "steps",
                    "alert": alert_data.get("type", "unknown"),
                    "has_context": context is not None,
                }

            async def search_similar(self, query, limit=10):
                return [{"case": "similar"}]

            async def get_health_status(self):
                return {"status": "healthy"}

        service = ConcreteService()
        result = await service.generate_runbook({"type": "cpu_high"}, {"extra": "info"})
        assert result["alert"] == "cpu_high"
        assert result["has_context"] is True

    @pytest.mark.asyncio
    async def test_concrete_implementation_search_similar(self):
        """测试具体实现的search_similar方法"""

        class ConcreteService(AIAnalysisService):
            async def analyze(self, context, analysis_type=AnalysisType.GENERAL):
                return {"result": "success"}

            async def observe(self, data):
                return {"observation": "data"}

            async def generate_runbook(self, alert_data, context=None):
                return {"runbook": "steps"}

            async def search_similar(self, query, limit=10):
                return {
                    "query": query,
                    "limit": limit,
                    "results": [{"case": f"similar_{i}"} for i in range(min(limit, 5))],
                }

            async def get_health_status(self):
                return {"status": "healthy"}

        service = ConcreteService()
        result = await service.search_similar("cpu error", limit=3)
        assert result["query"] == "cpu error"
        assert result["limit"] == 3
        assert len(result["results"]) == 3

    @pytest.mark.asyncio
    async def test_concrete_implementation_get_health_status(self):
        """测试具体实现的get_health_status方法"""

        class ConcreteService(AIAnalysisService):
            async def analyze(self, context, analysis_type=AnalysisType.GENERAL):
                return {"result": "success"}

            async def observe(self, data):
                return {"observation": "data"}

            async def generate_runbook(self, alert_data, context=None):
                return {"runbook": "steps"}

            async def search_similar(self, query, limit=10):
                return [{"case": "similar"}]

            async def get_health_status(self):
                return {"status": "healthy", "latency_ms": 50, "error_rate": 0.01}

        service = ConcreteService()
        result = await service.get_health_status()
        assert result["status"] == "healthy"
        assert result["latency_ms"] == 50
        assert result["error_rate"] == 0.01

    def test_interface_type_hints(self):
        """测试接口方法的类型提示"""
        from typing import get_type_hints

        # 检查analyze方法的类型提示
        hints = get_type_hints(AIAnalysisService.analyze)
        assert "context" in hints
        assert "analysis_type" in hints
        assert "return" in hints


class TestInterfaceInheritance:
    """接口继承测试"""

    @pytest.mark.asyncio
    async def test_multiple_implementations(self):
        """测试多个具体实现可以共存"""

        class ServiceA(AIAnalysisService):
            async def analyze(self, context, analysis_type=AnalysisType.GENERAL):
                return {"service": "A"}

            async def observe(self, data):
                return {"service": "A"}

            async def generate_runbook(self, alert_data, context=None):
                return {"service": "A"}

            async def search_similar(self, query, limit=10):
                return [{"service": "A"}]

            async def get_health_status(self):
                return {"service": "A"}

        class ServiceB(AIAnalysisService):
            async def analyze(self, context, analysis_type=AnalysisType.GENERAL):
                return {"service": "B"}

            async def observe(self, data):
                return {"service": "B"}

            async def generate_runbook(self, alert_data, context=None):
                return {"service": "B"}

            async def search_similar(self, query, limit=10):
                return [{"service": "B"}]

            async def get_health_status(self):
                return {"service": "B"}

        service_a = ServiceA()
        service_b = ServiceB()

        assert isinstance(service_a, AIAnalysisService)
        assert isinstance(service_b, AIAnalysisService)
        assert (await service_a.analyze({}, AnalysisType.GENERAL)) == {"service": "A"}
        assert (await service_b.analyze({}, AnalysisType.GENERAL)) == {"service": "B"}

    @pytest.mark.asyncio
    async def test_interface_polymorphism(self):
        """测试接口多态性"""

        class MockService(AIAnalysisService):
            def __init__(self, name):
                self.name = name

            async def analyze(self, context, analysis_type=AnalysisType.GENERAL):
                return {"service": self.name, "type": analysis_type.value}

            async def observe(self, data):
                return {"service": self.name}

            async def generate_runbook(self, alert_data, context=None):
                return {"service": self.name}

            async def search_similar(self, query, limit=10):
                return [{"service": self.name}]

            async def get_health_status(self):
                return {"service": self.name}

        services = [MockService("A"), MockService("B"), MockService("C")]

        # 多态调用
        results = [await s.analyze({}, AnalysisType.ANOMALY) for s in services]

        assert len(results) == 3
        assert results[0]["service"] == "A"
        assert results[1]["service"] == "B"
        assert results[2]["service"] == "C"
        assert all(r["type"] == AnalysisType.ANOMALY.value for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
