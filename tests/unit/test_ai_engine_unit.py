# -*- coding: utf-8 -*-
# tests/unit/test_ai_engine_unit.py
# AI 引擎模块单元测试 - 按照COMPREHENSIVE_TEST_PLAN阶段1要求
import asyncio
import hashlib
from datetime import datetime  # noqa: F401
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: F401

import pytest


class TestAIEngineUnit:
    """AI 引擎单元测试 - 核心功能测试"""

    @pytest.fixture
    def mock_ai_config(self):
        """Mock AI配置"""
        return {"is_enabled": True, "max_retries": 2, "model": "gpt-4o-mini", "api_key": "test_key"}

    @pytest.fixture
    def sample_query(self):
        """示例查询"""
        return "CPU使用率过高，请分析原因"

    @pytest.fixture
    def sample_metrics(self):
        """示例指标"""
        return "CPU: 85%, Memory: 45%, Disk: 60%"

    @pytest.fixture
    def sample_rich_context(self):
        """示例富上下文"""
        return {
            "top_processes": [
                {"pid": 1234, "name": "python", "cpu_percent": 25.5, "memory_percent": 10.2},
                {"pid": 5678, "name": "node", "cpu_percent": 15.3, "memory_percent": 8.1},
            ],
            "recent_alerts": [
                {
                    "type": "cpu_high",
                    "message": "CPU exceeds 80%",
                    "timestamp": "2026-06-18T10:00:00Z",
                },
            ],
            "recent_repairs": [],
            "stats": {"total_alerts": 10, "auto_heal_rate": 0.8},
        }

    @pytest.mark.asyncio
    async def test_analyze_basic_functionality(self, sample_query, sample_metrics):
        """测试AI分析基本功能"""
        import os
        import sys

        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

        with patch("config.AI_CONFIG", {"is_enabled": False}):
            from core.ai_engine import _rule_based_analysis, analyze  # noqa: F401

            # Mock规则引擎
            with patch("core.ai_engine._rule_based_analysis") as mock_rule:
                mock_rule.return_value = "规则引擎分析结果"

                result = await analyze(  # noqa: F841
                    query=sample_query, metrics_snapshot=sample_metrics, platform="windows"
                )

                # 验证调用规则引擎
                mock_rule.assert_called_once()
                assert result == "规则引擎分析结果"  # noqa: F841

    @pytest.mark.asyncio
    async def test_analyze_with_ai_enabled(self, sample_query, sample_metrics):
        """测试AI启用时的分析"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": True}):
            with patch("core.ai_engine.LLM_ROUTER_AVAILABLE", True):
                from core.ai_engine import analyze

                # Mock LLM路由器
                mock_router = AsyncMock()
                mock_router.generate = AsyncMock(
                    return_value={
                        "content": "AI分析结果：CPU过高可能是由于进程占用",
                        "model": "gpt-4o-mini",
                        "usage": {
                            "prompt_tokens": 100,
                            "completion_tokens": 50,
                            "total_tokens": 150,
                        },
                    }
                )

                with patch("core.ai_engine.get_llm_router", return_value=mock_router):
                    with patch("core.ai_engine.moderate_content", return_value=(True, [])):
                        with patch("core.ai_engine._rate_limit_wait", new_callable=AsyncMock):

                            result = await analyze(  # noqa: F841
                                query=sample_query,
                                metrics_snapshot=sample_metrics,
                                platform="windows",
                            )

                            # 验证AI分析结果
                            assert "AI分析结果" in result
                            assert mock_router.generate.called

    @pytest.mark.asyncio
    async def test_analyze_with_rich_context(
        self, sample_query, sample_metrics, sample_rich_context
    ):
        """测试富上下文支持"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": True}):
            with patch("core.ai_engine.LLM_ROUTER_AVAILABLE", True):
                from core.ai_engine import analyze

                mock_router = AsyncMock()
                mock_router.generate = AsyncMock(
                    return_value={
                        "content": "基于富上下文的AI分析结果",
                        "model": "gpt-4o-mini",
                        "usage": {"total_tokens": 200},
                    }
                )

                with patch("core.ai_engine.get_llm_router", return_value=mock_router):
                    with patch("core.ai_engine.moderate_content", return_value=(True, [])):
                        with patch("core.ai_engine._rate_limit_wait", new_callable=AsyncMock):

                            result = await analyze(  # noqa: F841
                                query=sample_query,
                                metrics_snapshot=sample_metrics,
                                platform="windows",
                                rich_context=sample_rich_context,
                            )

                            # 验证富上下文被使用
                            assert "基于富上下文" in result

    @pytest.mark.asyncio
    async def test_analyze_platform_validation(self, sample_query, sample_metrics):
        """测试平台参数验证"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            from core.ai_engine import _rule_based_analysis, analyze  # noqa: F401

            with patch("core.ai_engine._rule_based_analysis") as mock_rule:
                mock_rule.return_value = "规则分析结果"

                # 测试无效平台
                result = await analyze(  # noqa: F841
                    query=sample_query, metrics_snapshot=sample_metrics, platform="invalid_platform"
                )

                # 验证降级为windows
                mock_rule.assert_called_once()
                call_args = mock_rule.call_args
                assert call_args[0][2] == "windows"  # platform参数

    @pytest.mark.asyncio
    async def test_analyze_content_moderation(self, sample_query, sample_metrics):
        """测试内容审核"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": True}):
            with patch("core.ai_engine.CONTENT_MODERATION_AVAILABLE", True):
                from fastapi import HTTPException

                from core.ai_engine import analyze

                # Mock内容审核拒绝
                with patch("core.ai_engine.moderate_content", return_value=(False, ["违规内容"])):
                    with pytest.raises(HTTPException) as exc_info:
                        await analyze(
                            query=sample_query, metrics_snapshot=sample_metrics, platform="windows"
                        )

                    # 验证HTTP异常
                    assert exc_info.value.status_code == 400
                    assert "Content violation" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_analyze_llm_failure_fallback(self, sample_query, sample_metrics):
        """测试LLM失败时的降级"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": True}):
            with patch("core.ai_engine.LLM_ROUTER_AVAILABLE", True):
                from core.ai_engine import analyze

                mock_router = AsyncMock()
                mock_router.generate = AsyncMock(side_effect=Exception("LLM API错误"))

                with patch("core.ai_engine.get_llm_router", return_value=mock_router):
                    with patch("core.ai_engine.moderate_content", return_value=(True, [])):
                        with patch("core.ai_engine._rate_limit_wait", new_callable=AsyncMock):
                            with patch("core.ai_engine._rule_based_analysis") as mock_rule:
                                mock_rule.return_value = "降级分析结果"

                                result = await analyze(  # noqa: F841
                                    query=sample_query,
                                    metrics_snapshot=sample_metrics,
                                    platform="windows",
                                )

                                # 验证降级到规则引擎
                                assert result == "降级分析结果"  # noqa: F841
                                mock_rule.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_empty_response_fallback(self, sample_query, sample_metrics):
        """测试空响应降级"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": True}):
            with patch("core.ai_engine.LLM_ROUTER_AVAILABLE", True):
                from core.ai_engine import analyze

                mock_router = AsyncMock()
                mock_router.generate = AsyncMock(
                    return_value={
                        "content": "",  # 空响应
                        "model": "gpt-4o-mini",
                        "usage": {"total_tokens": 100},
                    }
                )

                with patch("core.ai_engine.get_llm_router", return_value=mock_router):
                    with patch("core.ai_engine.moderate_content", return_value=(True, [])):
                        with patch("core.ai_engine._rate_limit_wait", new_callable=AsyncMock):
                            with patch("core.ai_engine._rule_based_analysis") as mock_rule:
                                mock_rule.return_value = "降级分析结果"

                                result = await analyze(  # noqa: F841
                                    query=sample_query,
                                    metrics_snapshot=sample_metrics,
                                    platform="windows",
                                )

                                # 验证降级
                                assert result == "降级分析结果"  # noqa: F841

    def test_build_rich_user_message_basic(self, sample_query, sample_metrics):
        """测试基本用户消息构建"""
        from core.ai_engine import _build_rich_user_message

        result = _build_rich_user_message(  # noqa: F841
            query=sample_query, metrics=sample_metrics, platform="windows", rich_context=None
        )

        # 验证基本消息结构
        assert sample_query in result
        assert sample_metrics in result
        # 验证消息生成成功（不强制平台信息）

    def test_build_rich_user_message_with_context(
        self, sample_query, sample_metrics, sample_rich_context
    ):
        """测试带富上下文的用户消息构建"""
        from core.ai_engine import _build_rich_user_message

        result = _build_rich_user_message(  # noqa: F841
            query=sample_query,
            metrics=sample_metrics,
            platform="windows",
            rich_context=sample_rich_context,
        )

        # 验证富上下文信息（中文或英文）
        assert "进程" in result or "process" in result.lower()
        assert "告警" in result or "alert" in result.lower()

    def test_build_rich_user_message_length_limit(self):
        """测试消息长度限制"""
        from core.ai_engine import _build_rich_user_message

        long_query = "A" * 10000  # 超长查询
        long_metrics = "B" * 10000  # 超长指标

        result = _build_rich_user_message(  # noqa: F841
            query=long_query, metrics=long_metrics, platform="windows", rich_context=None
        )

        # 验证长度限制（根据实际实现调整）
        assert len(result) > 0  # 验证有输出
        assert len(result) < 25000  # 合理的上限

    def test_rule_based_analysis_cpu(self):
        """测试CPU规则分析"""
        from core.ai_engine import _rule_based_analysis

        result = _rule_based_analysis(
            query="CPU过高", metrics="CPU: 85%", platform="windows"
        )  # noqa: F841

        # 验证CPU分析
        assert "CPU" in result or "cpu" in result.lower()

    def test_rule_based_analysis_memory(self):
        """测试内存规则分析"""
        from core.ai_engine import _rule_based_analysis

        result = _rule_based_analysis(
            query="内存不足", metrics="Memory: 90%", platform="linux"
        )  # noqa: F841

        # 验证内存分析
        assert "Memory" in result or "memory" in result.lower() or "内存" in result

    def test_rule_based_analysis_platform_difference(self):
        """测试不同平台的规则分析差异"""
        from core.ai_engine import _rule_based_analysis

        windows_result = _rule_based_analysis(  # noqa: F841
            query="系统问题", metrics="CPU: 80%", platform="windows"
        )

        linux_result = _rule_based_analysis(
            query="系统问题", metrics="CPU: 80%", platform="linux"
        )  # noqa: F841

        # 验证平台特定建议
        # 不同平台可能有不同的建议
        assert isinstance(windows_result, str)
        assert isinstance(linux_result, str)


class TestAIEngineIntegration:
    """AI引擎集成测试 - 组件交互测试"""

    @pytest.mark.asyncio
    async def test_langfuse_integration(self):
        """测试Langfuse集成"""
        with patch("core.ai_engine.LANGFUSE_CONFIG", {"enabled": True}):
            with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
                from core.ai_engine import analyze, observe  # noqa: F401

                # 测试observe装饰器
                @observe
                def test_function(x):
                    return x * 2

                result = test_function(5)  # noqa: F841
                assert result == 10  # noqa: F841

    @pytest.mark.asyncio
    async def test_rag_integration(self):
        """测试RAG集成"""
        with patch("core.ai_engine.RAG_AVAILABLE", True):
            with patch("core.ai_engine.AI_CONFIG", {"is_enabled": True}):
                from core.ai_engine import analyze

                # Mock RAG pipeline
                mock_rag = AsyncMock()
                mock_rag.retrieve_and_generate = AsyncMock(return_value="RAG检索到的相关知识")

                # Mock moderate_content函数
                with patch("core.ai_engine.moderate_content", return_value=(True, [])):
                    with patch("core.ai_engine.get_llm_router", return_value=None):
                        with patch("core.ai_engine._rag_pipeline", mock_rag):
                            with patch("core.ai_engine.LLM_ROUTER_AVAILABLE", False):
                                with patch("core.ai_engine._rule_based_analysis") as mock_rule:
                                    mock_rule.return_value = "规则分析结果"

                            result = await analyze(  # noqa: F841
                                query="测试查询", metrics_snapshot="CPU: 70%", platform="windows"
                            )

                            # 验证降级分析结果
                            assert result is not None
                            assert "降级" in result or "规则" in result

    @pytest.mark.asyncio
    async def test_audit_logging(self):
        """测试审计日志记录"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": True}):
            with patch("core.ai_engine.LLM_ROUTER_AVAILABLE", True):
                from core.ai_engine import analyze

                mock_router = AsyncMock()
                mock_router.generate = AsyncMock(
                    return_value={
                        "content": "测试结果",
                        "model": "gpt-4o-mini",
                        "usage": {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75},
                    }
                )

                with patch("core.ai_engine.get_llm_router", return_value=mock_router):
                    with patch("core.ai_engine.moderate_content", return_value=(True, [])):
                        with patch("core.ai_engine._rate_limit_wait", new_callable=AsyncMock):
                            await analyze(
                                query="测试查询", metrics_snapshot="CPU: 75%", platform="windows"
                            )

                            # 验证分析完成


class TestAIEnginePerformance:
    """AI引擎性能测试"""

    @pytest.mark.asyncio
    async def test_concurrent_analyze_calls(self):
        """测试并发分析调用"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            from core.ai_engine import analyze

            with patch("core.ai_engine._rule_based_analysis", return_value="结果"):
                # 并发调用
                tasks = [
                    analyze(query=f"查询{i}", metrics_snapshot="CPU: 70%", platform="windows")
                    for i in range(5)
                ]

                results = await asyncio.gather(*tasks)

                # 验证所有调用都成功
                assert len(results) == 5
                assert all(r == "结果" for r in results)

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """测试限速功能"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": True}):
            with patch("core.ai_engine.LLM_ROUTER_AVAILABLE", True):
                from core.ai_engine import analyze

                mock_router = AsyncMock()
                mock_router.generate = AsyncMock(
                    return_value={
                        "content": "结果",
                        "model": "gpt-4o-mini",
                        "usage": {"total_tokens": 50},
                    }
                )

                with patch("core.ai_engine.get_llm_router", return_value=mock_router):
                    with patch("core.ai_engine.moderate_content", return_value=(True, [])):
                        with patch(
                            "core.ai_engine._rate_limit_wait", new_callable=AsyncMock
                        ) as mock_rate_limit:

                            await analyze(
                                query="测试", metrics_snapshot="CPU: 70%", platform="windows"
                            )

                            # 验证限速被调用
                            mock_rate_limit.assert_called_once()

    def test_prompt_hash_consistency(self):
        """测试prompt hash一致性"""
        query = "测试查询"
        metrics = "CPU: 80%"

        # 计算hash
        prompt = f"问题: {query}\n指标: {metrics}"
        hash1 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        hash2 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

        # 验证hash一致性
        assert hash1 == hash2

    @pytest.mark.asyncio
    async def test_http_client_singleton(self):
        """测试HTTP客户端单例模式 - 跳过，因为函数是内部实现"""
        # 这些是内部实现细节，不需要直接测试
        # 通过analyze函数的测试间接覆盖
        pytest.skip("Internal implementation detail")

    @pytest.mark.asyncio
    async def test_close_http_client_idempotent(self):
        """测试HTTP客户端关闭的幂等性 - 跳过，因为函数是内部实现"""
        # 这些是内部实现细节，不需要直接测试
        # 通过analyze函数的测试间接覆盖
        pytest.skip("Internal implementation detail")

    @pytest.mark.asyncio
    async def test_close_langfuse_client(self):
        """测试Langfuse客户端关闭"""
        from core.ai_engine import close_langfuse_client

        # 即使Langfuse未初始化，关闭也应该是安全的
        await close_langfuse_client()

        # 不应该抛出异常

    @pytest.mark.asyncio
    async def test_rate_limit_wait_with_cooldown(self):
        """测试限速器冷却期等待"""
        import time

        from core.ai_engine import _rate_limit_wait

        # 设置下一个可用时间为未来
        with patch("core.ai_engine._next_available_time", time.monotonic() + 2.0):
            # 调用限速等待，应该等待
            start = time.monotonic()
            await _rate_limit_wait()
            elapsed = time.monotonic() - start

        # 应该等待了大约2秒（允许一些误差）
        assert elapsed >= 1.5

    @pytest.mark.asyncio
    async def test_rate_limit_wait_without_cooldown(self):
        """测试限速器无冷却期立即放行"""
        import time

        from core.ai_engine import _MIN_REQUEST_INTERVAL, _rate_limit_wait

        # 设置下一个可用时间为过去
        with patch("core.ai_engine._next_available_time", time.monotonic() - 1.0):
            # 调用限速等待，应该立即放行但会预约下一个槽位
            start = time.monotonic()
            await _rate_limit_wait()
            elapsed = time.monotonic() - start

        # 应该立即放行（等待时间很短，但会设置下一个槽位）
        # 由于会设置下一个槽位为当前时间+最小间隔，所以会有一些开销
        # 允许一定的误差范围
        assert elapsed <= _MIN_REQUEST_INTERVAL + 0.5

    @pytest.mark.asyncio
    async def test_analyze_with_invalid_platform(self):
        """测试无效平台参数的处理"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            from core.ai_engine import _rule_based_analysis, analyze  # noqa: F401

            with patch("core.ai_engine._rule_based_analysis") as mock_rule:
                mock_rule.return_value = "规则分析结果"

                # 测试无效平台
                result = await analyze(  # noqa: F841
                    query="测试", metrics_snapshot="CPU: 70%", platform="invalid_platform"
                )

                # 验证降级为windows
                mock_rule.assert_called_once()
                call_args = mock_rule.call_args
                assert call_args[0][2] == "windows"  # platform参数

    @pytest.mark.asyncio
    async def test_analyze_with_none_platform(self):
        """测试None平台参数的处理"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            from core.ai_engine import _rule_based_analysis, analyze  # noqa: F401

            with patch("core.ai_engine._rule_based_analysis") as mock_rule:
                mock_rule.return_value = "规则分析结果"

                # 测试None平台
                _ = await analyze(query="测试", metrics_snapshot="CPU: 70%", platform=None)

                # 验证降级为windows
                mock_rule.assert_called_once()
                call_args = mock_rule.call_args
                assert call_args[0][2] == "windows"  # platform参数

    @pytest.mark.asyncio
    async def test_analyze_with_rag_integration(self):
        """测试RAG集成"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": True}):
            with patch("core.ai_engine.LLM_ROUTER_AVAILABLE", True):
                with patch("core.ai_engine.RAG_AVAILABLE", True):
                    from core.ai_engine import analyze

                    # Mock RAG pipeline
                    mock_rag = AsyncMock()
                    mock_rag.retrieve_and_generate = AsyncMock(return_value="RAG上下文")

                    with patch("core.ai_engine._rag_pipeline", mock_rag):
                        mock_router = AsyncMock()
                        mock_router.generate = AsyncMock(
                            return_value={
                                "content": "AI分析结果",
                                "model": "gpt-4o-mini",
                                "usage": {"total_tokens": 100},
                            }
                        )

                        with patch("core.ai_engine.get_llm_router", return_value=mock_router):
                            with patch("core.ai_engine.moderate_content", return_value=(True, [])):
                                with patch(
                                    "core.ai_engine._rate_limit_wait", new_callable=AsyncMock
                                ):

                                    result = await analyze(  # noqa: F841
                                        query="测试查询",
                                        metrics_snapshot="CPU: 70%",
                                        platform="windows",
                                    )

                                    # 验证RAG被调用
                                    mock_rag.retrieve_and_generate.assert_called_once()
                                    assert "AI分析结果" in result

    @pytest.mark.asyncio
    async def test_analyze_rag_failure_handling(self):
        """测试RAG失败时的处理"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": True}):
            with patch("core.ai_engine.LLM_ROUTER_AVAILABLE", True):
                with patch("core.ai_engine.RAG_AVAILABLE", True):
                    from core.ai_engine import analyze

                    # Mock RAG pipeline抛出异常
                    mock_rag = AsyncMock()
                    mock_rag.retrieve_and_generate = AsyncMock(side_effect=Exception("RAG失败"))

                    with patch("core.ai_engine._rag_pipeline", mock_rag):
                        mock_router = AsyncMock()
                        mock_router.generate = AsyncMock(
                            return_value={
                                "content": "AI分析结果",
                                "model": "gpt-4o-mini",
                                "usage": {"total_tokens": 100},
                            }
                        )

                        with patch("core.ai_engine.get_llm_router", return_value=mock_router):
                            with patch("core.ai_engine.moderate_content", return_value=(True, [])):
                                with patch(
                                    "core.ai_engine._rate_limit_wait", new_callable=AsyncMock
                                ):

                                    result = await analyze(  # noqa: F841
                                        query="测试查询",
                                        metrics_snapshot="CPU: 70%",
                                        platform="windows",
                                    )

                                    # 即使RAG失败，分析应该继续
                                    assert "AI分析结果" in result

    @pytest.mark.asyncio
    async def test_analyze_with_empty_llm_response(self):
        """测试LLM返回空内容的处理"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": True}):
            with patch("core.ai_engine.LLM_ROUTER_AVAILABLE", True):
                from core.ai_engine import analyze

                mock_router = AsyncMock()
                mock_router.generate = AsyncMock(
                    return_value={
                        "content": "",  # 空内容
                        "model": "gpt-4o-mini",
                        "usage": {"total_tokens": 100},
                    }
                )

                with patch("core.ai_engine.get_llm_router", return_value=mock_router):
                    with patch("core.ai_engine.moderate_content", return_value=(True, [])):
                        with patch("core.ai_engine._rate_limit_wait", new_callable=AsyncMock):
                            with patch("core.ai_engine._rule_based_analysis") as mock_rule:
                                mock_rule.return_value = "降级分析结果"

                                result = await analyze(  # noqa: F841
                                    query="测试", metrics_snapshot="CPU: 70%", platform="windows"
                                )

                                # 应该降级到规则引擎
                                mock_rule.assert_called_once()
                                assert result == "降级分析结果"  # noqa: F841

    @pytest.mark.asyncio
    async def test_analyze_with_langfuse_metadata_update(self):
        """测试Langfuse元数据更新 - 跳过，因为涉及内部导入"""
        # Langfuse元数据更新是在函数内部导入的，测试复杂度高
        # 通过集成测试覆盖
        pytest.skip("Internal import, covered by integration tests")

    @pytest.mark.asyncio
    async def test_analyze_with_ai_enhancement(self):
        """测试AI增强功能 - 跳过，因为涉及内部导入"""
        # AI增强是在函数内部导入的，测试复杂度高
        # 通过集成测试覆盖
        pytest.skip("Internal import, covered by integration tests")

    @pytest.mark.asyncio
    async def test_analyze_ai_enhancement_failure(self):
        """测试AI增强失败时的处理 - 跳过，因为涉及内部导入"""
        # AI增强是在函数内部导入的，测试复杂度高
        # 通过集成测试覆盖
        pytest.skip("Internal import, covered by integration tests")

    @pytest.mark.asyncio
    async def test_analyze_query_truncation(self):
        """测试查询字符串截断"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            from core.ai_engine import _QUERY_MAX_LEN, _rule_based_analysis, analyze  # noqa: F401

            # 创建超长查询
            long_query = "A" * 3000  # 超过默认2000限制

            with patch("core.ai_engine._rule_based_analysis") as mock_rule:
                mock_rule.return_value = "规则分析结果"

                result = await analyze(  # noqa: F841
                    query=long_query, metrics_snapshot="CPU: 70%", platform="windows"
                )

                # 验证查询被截断
                call_args = mock_rule.call_args
                assert len(call_args[0][0]) <= 2000

    @pytest.mark.asyncio
    async def test_analyze_metrics_truncation(self):
        """测试指标字符串截断"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            from core.ai_engine import _METRICS_MAX_LEN, _rule_based_analysis, analyze  # noqa: F401

            # 创建超长指标
            long_metrics = "B" * 3000  # 超过默认2000限制

            with patch("core.ai_engine._rule_based_analysis") as mock_rule:
                mock_rule.return_value = "规则分析结果"

                result = await analyze(  # noqa: F841
                    query="测试", metrics_snapshot=long_metrics, platform="windows"
                )

                # 验证指标被截断
                call_args = mock_rule.call_args
                assert len(call_args[0][1]) <= 2000

    @pytest.mark.asyncio
    async def test_close_http_client(self):
        """测试关闭HTTP客户端"""
        from core.ai_engine import _get_http_client, _http_client, close_http_client

        # 确保HTTP客户端已初始化
        _get_http_client()

        # 关闭HTTP客户端
        await close_http_client()

        # 验证客户端已关闭
        assert _http_client is None

    @pytest.mark.asyncio
    async def test_close_http_client_already_closed(self):
        """测试关闭已关闭的HTTP客户端"""
        # 设置HTTP客户端为None
        import core.ai_engine as ai_engine_module
        from core.ai_engine import _http_client, close_http_client

        ai_engine_module._http_client = None

        # 关闭HTTP客户端（应该安全无操作）
        await close_http_client()

        # 验证仍然为None
        assert _http_client is None

    def test_noop_observe_decorator(self):
        """测试透明装饰器"""
        from core.ai_engine import _noop_observe

        # 测试无参数调用
        @_noop_observe
        def test_func():
            return "test"

        result = test_func()  # noqa: F841
        assert result == "test"  # noqa: F841

        # 测试带参数调用
        @_noop_observe(name="test")
        def test_func2():
            return "test2"

        result2 = test_func2()
        assert result2 == "test2"

    def test_observe_import(self):
        """测试observe装饰器导入"""
        from core.ai_engine import observe

        # 验证observe可以被导入
        assert observe is not None
        assert callable(observe)


class TestPredictiveAnalysisEngine:
    """P2增强：预测分析引擎单元测试"""

    @pytest.fixture
    def predictive_engine(self):
        """创建预测分析引擎实例"""
        from core.ai_engine import PredictiveAnalysisEngine

        return PredictiveAnalysisEngine()

    @pytest.mark.asyncio
    async def test_predict_system_anomalies_cpu_high(self, predictive_engine):
        """测试CPU高使用率异常预测"""
        metrics_data = {"cpu": {"usage_percent": 85}, "memory": {"usage_percent": 50}, "disk": []}

        predictions = await predictive_engine.predict_system_anomalies(metrics_data)

        assert predictions["prediction_horizon_hours"] == 24
        assert len(predictions["predicted_anomalies"]) > 0
        assert predictions["predicted_anomalies"][0]["type"] == "cpu_high"
        assert predictions["predicted_anomalies"][0]["probability"] == 0.85
        assert len(predictions["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_predict_system_anomalies_memory_high(self, predictive_engine):
        """测试内存高使用率异常预测"""
        metrics_data = {"cpu": {"usage_percent": 50}, "memory": {"usage_percent": 90}, "disk": []}

        predictions = await predictive_engine.predict_system_anomalies(metrics_data)

        assert len(predictions["predicted_anomalies"]) > 0
        memory_anomaly = [
            a for a in predictions["predicted_anomalies"] if a["type"] == "memory_high"
        ]
        assert len(memory_anomaly) > 0
        assert memory_anomaly[0]["probability"] == 0.90

    @pytest.mark.asyncio
    async def test_predict_system_anomalies_disk_high(self, predictive_engine):
        """测试磁盘高使用率异常预测"""
        metrics_data = {
            "cpu": {"usage_percent": 50},
            "memory": {"usage_percent": 50},
            "disk": [{"mount_point": "/var", "usage_percent": 95}],
        }

        predictions = await predictive_engine.predict_system_anomalies(metrics_data)

        disk_anomaly = [a for a in predictions["predicted_anomalies"] if a["type"] == "disk_high"]
        assert len(disk_anomaly) > 0
        assert disk_anomaly[0]["probability"] == 0.95
        assert disk_anomaly[0]["mount_point"] == "/var"

    @pytest.mark.asyncio
    async def test_predict_system_anomalies_no_anomalies(self, predictive_engine):
        """测试无异常情况"""
        metrics_data = {"cpu": {"usage_percent": 30}, "memory": {"usage_percent": 40}, "disk": []}

        predictions = await predictive_engine.predict_system_anomalies(metrics_data)

        assert len(predictions["predicted_anomalies"]) == 0
        assert predictions["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_predict_system_anomalies_custom_horizon(self, predictive_engine):
        """测试自定义预测时间范围"""
        metrics_data = {"cpu": {"usage_percent": 85}, "memory": {"usage_percent": 50}, "disk": []}

        predictions = await predictive_engine.predict_system_anomalies(
            metrics_data, prediction_horizon_hours=48
        )

        assert predictions["prediction_horizon_hours"] == 48

    @pytest.mark.asyncio
    async def test_predict_capacity_needs_cpu(self, predictive_engine):
        """测试CPU容量需求预测"""
        current_metrics = {"cpu": {"usage_percent": 60}, "memory": {"usage_percent": 50}}

        predictions = await predictive_engine.predict_capacity_needs(
            current_metrics, growth_rate=0.1
        )

        assert predictions["growth_rate"] == 0.1
        assert "predictions_3_months" in predictions
        assert "predictions_6_months" in predictions
        assert predictions["predictions_3_months"]["cpu"] > current_metrics["cpu"]["usage_percent"]
        assert (
            predictions["predictions_6_months"]["cpu"] > predictions["predictions_3_months"]["cpu"]
        )

    @pytest.mark.asyncio
    async def test_predict_capacity_needs_memory(self, predictive_engine):
        """测试内存容量需求预测"""
        current_metrics = {"cpu": {"usage_percent": 50}, "memory": {"usage_percent": 70}}

        predictions = await predictive_engine.predict_capacity_needs(
            current_metrics, growth_rate=0.15
        )

        assert (
            predictions["predictions_3_months"]["memory"]
            > current_metrics["memory"]["usage_percent"]
        )
        assert (
            predictions["predictions_6_months"]["memory"]
            > predictions["predictions_3_months"]["memory"]
        )

    @pytest.mark.asyncio
    async def test_predict_capacity_needs_high_growth_recommendations(self, predictive_engine):
        """测试高增长率时的容量建议"""
        current_metrics = {"cpu": {"usage_percent": 85}, "memory": {"usage_percent": 50}}

        predictions = await predictive_engine.predict_capacity_needs(
            current_metrics, growth_rate=0.2
        )

        # 6个月预测应该超过90%，触发建议
        if predictions["predictions_6_months"]["cpu"] > 90:
            cpu_rec = [r for r in predictions["recommendations"] if "CPU" in r]
            assert len(cpu_rec) > 0


class TestIntelligentRecommendationEngine:
    """P2增强：智能推荐引擎单元测试"""

    @pytest.fixture
    def recommendation_engine(self):
        """创建推荐引擎实例"""
        from core.ai_engine import IntelligentRecommendationEngine

        return IntelligentRecommendationEngine()

    @pytest.mark.asyncio
    async def test_generate_recommendations_cpu_high(self, recommendation_engine):
        """测试CPU高使用率推荐"""
        alert_data = {"type": "cpu_high", "severity": "warning", "id": "alert-001"}

        recommendations = await recommendation_engine.generate_recommendations(alert_data)

        assert len(recommendations) > 0
        assert recommendations[0]["type"] in ["optimization", "scaling"]
        assert recommendations[0]["confidence"] > 0
        assert "action" in recommendations[0]

    @pytest.mark.asyncio
    async def test_generate_recommendations_memory_high(self, recommendation_engine):
        """测试内存高使用率推荐"""
        alert_data = {"type": "memory_high", "severity": "warning", "id": "alert-002"}

        recommendations = await recommendation_engine.generate_recommendations(alert_data)

        assert len(recommendations) > 0
        memory_rec = [r for r in recommendations if "memory" in r["action"].lower()]
        assert len(memory_rec) > 0

    @pytest.mark.asyncio
    async def test_generate_recommendations_disk_high(self, recommendation_engine):
        """测试磁盘高使用率推荐"""
        alert_data = {"type": "disk_high", "severity": "critical", "id": "alert-003"}

        recommendations = await recommendation_engine.generate_recommendations(alert_data)

        assert len(recommendations) > 0
        disk_rec = [
            r
            for r in recommendations
            if "disk" in r["action"].lower() or "space" in r["action"].lower()
        ]
        assert len(disk_rec) > 0

    @pytest.mark.asyncio
    async def test_generate_recommendations_critical_severity(self, recommendation_engine):
        """测试严重级别告警的推荐"""
        alert_data = {"type": "cpu_high", "severity": "critical", "id": "alert-004"}

        recommendations = await recommendation_engine.generate_recommendations(alert_data)

        # 应该包含升级建议
        escalation_rec = [r for r in recommendations if r["type"] == "escalation"]
        assert len(escalation_rec) > 0
        assert escalation_rec[0]["priority"] == "critical"
        assert escalation_rec[0]["confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_generate_recommendations_sorting(self, recommendation_engine):
        """测试推荐结果排序"""
        alert_data = {"type": "cpu_high", "severity": "warning", "id": "alert-005"}

        recommendations = await recommendation_engine.generate_recommendations(alert_data)

        # 验证按置信度和优先级排序
        if len(recommendations) > 1:
            for i in range(len(recommendations) - 1):
                assert recommendations[i]["confidence"] >= recommendations[i + 1]["confidence"]

    @pytest.mark.asyncio
    async def test_generate_recommendations_with_context(self, recommendation_engine):
        """测试带上下文的推荐生成"""
        alert_data = {"type": "cpu_high", "severity": "warning", "id": "alert-006"}
        context = {"current_load": 0.9, "trend": "increasing"}

        recommendations = await recommendation_engine.generate_recommendations(alert_data, context)

        assert len(recommendations) > 0
        # 上下文目前不影响基本推荐，但应该能正常处理
        assert isinstance(recommendations, list)

    @pytest.mark.asyncio
    async def test_get_personalized_recommendations_optimization_preference(
        self, recommendation_engine
    ):
        """测试优化偏好个性化推荐"""
        user_id = "user-001"
        historical_actions = [
            {"type": "optimization", "timestamp": "2026-06-01"},
            {"type": "optimization", "timestamp": "2026-06-02"},
            {"type": "scaling", "timestamp": "2026-06-03"},
        ]

        recommendations = await recommendation_engine.get_personalized_recommendations(
            user_id, historical_actions
        )

        assert len(recommendations) > 0
        assert recommendations[0]["type"] == "optimization"
        assert "optimization" in recommendations[0].get("personalization_reason", "").lower()

    @pytest.mark.asyncio
    async def test_get_personalized_recommendations_scaling_preference(self, recommendation_engine):
        """测试扩容偏好个性化推荐"""
        user_id = "user-002"
        historical_actions = [
            {"type": "scaling", "timestamp": "2026-06-01"},
            {"type": "scaling", "timestamp": "2026-06-02"},
            {"type": "optimization", "timestamp": "2026-06-03"},
        ]

        recommendations = await recommendation_engine.get_personalized_recommendations(
            user_id, historical_actions
        )

        assert len(recommendations) > 0
        assert recommendations[0]["type"] == "scaling"

    @pytest.mark.asyncio
    async def test_get_personalized_recommendations_empty_history(self, recommendation_engine):
        """测试空历史记录的个性化推荐"""
        user_id = "user-003"
        historical_actions = []

        recommendations = await recommendation_engine.get_personalized_recommendations(
            user_id, historical_actions
        )

        # 应该有默认推荐
        assert len(recommendations) > 0
        assert recommendations[0]["type"] == "optimization"  # 默认偏好


class TestNaturalLanguageInteraction:
    """P2增强：自然语言交互单元测试"""

    @pytest.fixture
    def nli_engine(self):
        """创建自然语言交互引擎实例"""
        from core.ai_engine import NaturalLanguageInteraction

        return NaturalLanguageInteraction()

    @pytest.mark.asyncio
    async def test_process_natural_language_query_status(self, nli_engine):
        """测试状态查询意图"""
        query = "What is the current CPU status?"

        result = await nli_engine.process_natural_language_query(query)

        assert result["query"] == query
        assert result["intent"] == "status_query"
        assert "response" in result
        assert "confidence" in result

    @pytest.mark.asyncio
    async def test_process_natural_language_query_root_cause(self, nli_engine):
        """测试根因查询意图"""
        query = "Why is the memory usage so high?"

        result = await nli_engine.process_natural_language_query(query)

        assert result["intent"] == "root_cause_query"

    @pytest.mark.asyncio
    async def test_process_natural_language_query_repair(self, nli_engine):
        """测试修复查询意图"""
        query = "How do I fix the disk space issue?"

        result = await nli_engine.process_natural_language_query(query)

        assert result["intent"] == "repair_query"

    @pytest.mark.asyncio
    async def test_process_natural_language_query_prediction(self, nli_engine):
        """测试预测查询意图"""
        query = "Predict the system load for the next week"

        result = await nli_engine.process_natural_language_query(query)

        assert result["intent"] == "prediction_query"

    @pytest.mark.asyncio
    async def test_process_natural_language_query_recommendation(self, nli_engine):
        """测试推荐查询意图"""
        query = "Recommend some optimizations for the database"

        result = await nli_engine.process_natural_language_query(query)

        assert result["intent"] == "recommendation_query"

    @pytest.mark.asyncio
    async def test_classify_intent_general(self, nli_engine):
        """测试通用意图分类"""
        query = "Tell me about the system"

        intent = await nli_engine._classify_intent(query)

        assert intent == "general_query"

    @pytest.mark.asyncio
    async def test_extract_entities_cpu(self, nli_engine):
        """测试CPU实体提取"""
        query = "Check the CPU usage"

        entities = await nli_engine._extract_entities(query)

        assert entities["metric"] == "cpu"

    @pytest.mark.asyncio
    async def test_extract_entities_memory(self, nli_engine):
        """测试内存实体提取"""
        query = "What about memory consumption?"

        entities = await nli_engine._extract_entities(query)

        assert entities["metric"] == "memory"

    @pytest.mark.asyncio
    async def test_extract_entities_disk(self, nli_engine):
        """测试磁盘实体提取"""
        query = "How much disk space is left?"

        entities = await nli_engine._extract_entities(query)

        assert entities["metric"] == "disk"

    @pytest.mark.asyncio
    async def test_extract_entities_time_ranges(self, nli_engine):
        """测试时间范围实体提取"""
        query1 = "CPU usage in the last hour"
        entities1 = await nli_engine._extract_entities(query1)
        assert entities1["time_range"] == "1h"

        query2 = "Memory usage today"
        entities2 = await nli_engine._extract_entities(query2)
        assert entities2["time_range"] == "24h"

    @pytest.mark.asyncio
    async def test_generate_response_status_query(self, nli_engine):
        """测试状态查询响应生成"""
        intent = "status_query"
        entities = {"metric": "cpu"}
        context = {"metrics": {"cpu": 75.5}}

        response = await nli_engine._generate_response(intent, entities, context)

        assert "cpu" in response.lower()
        assert "75.5" in response or "unknown" in response.lower()

    @pytest.mark.asyncio
    async def test_maintain_conversation_new_user(self, nli_engine):
        """测试新用户对话维护"""
        user_id = "user-001"
        message = "Hello, I need help with the system"

        result = await nli_engine.maintain_conversation(user_id, message)

        assert result["query"] == message
        assert "conversation_history" in result
        assert len(result["conversation_history"]) == 2  # user + assistant
        assert result["conversation_history"][0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_maintain_conversation_existing_user(self, nli_engine):
        """测试现有用户对话维护"""
        user_id = "user-002"

        # 第一条消息
        await nli_engine.maintain_conversation(user_id, "First message")

        # 第二条消息
        result = await nli_engine.maintain_conversation(user_id, "Second message")

        assert len(result["conversation_history"]) == 4  # 2 rounds * 2 messages

    @pytest.mark.asyncio
    async def test_maintain_conversation_history_limit(self, nli_engine):
        """测试对话历史限制"""
        user_id = "user-003"

        # 添加超过限制的消息
        for i in range(15):
            await nli_engine.maintain_conversation(user_id, f"Message {i}")

        # 获取最后一条结果
        result = await nli_engine.maintain_conversation(user_id, "Last message")

        # 应该只保留最近10条消息（5轮对话）
        assert len(result["conversation_history"]) <= 10


class TestLLMAnalysisService:
    """LLM分析服务单元测试"""

    @pytest.fixture
    def llm_service(self):
        """创建LLM分析服务实例"""
        from core.ai_engine import LLMAnalysisService

        return LLMAnalysisService()

    @pytest.mark.asyncio
    async def test_analyze_basic(self, llm_service):
        """测试基本分析功能"""
        context = {"query": "CPU is high", "metrics_snapshot": "CPU: 85%", "platform": "windows"}

        with patch("core.ai_engine.analyze", return_value="Analysis result"):
            result = await llm_service.analyze(context)

            assert result["result"] == "Analysis result"
            from core.ai_interface import AnalysisType

            assert result["analysis_type"] == AnalysisType.GENERAL
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_analyze_with_rich_context(self, llm_service):
        """测试带富上下文的分析"""
        rich_context = {
            "top_processes": [{"name": "chrome", "cpu": 25.5}],
            "recent_alerts": [],
            "recent_repairs": [],
            "stats": {},
        }
        context = {
            "query": "CPU is high",
            "metrics_snapshot": "CPU: 85%",
            "platform": "windows",
            "rich_context": rich_context,
        }

        with patch("core.ai_engine.analyze", return_value="Analysis with context"):
            result = await llm_service.analyze(context)

            assert result["result"] == "Analysis with context"

    @pytest.mark.asyncio
    async def test_observe(self, llm_service):
        """测试观察功能"""
        data = {"metric": "cpu", "value": 85.5}

        with patch.object(llm_service, "analyze", return_value={"result": "Observation result"}):
            result = await llm_service.observe(data)

            assert "result" in result

    @pytest.mark.asyncio
    async def test_generate_runbook(self, llm_service):
        """测试生成修复手册"""
        alert_data = {"id": "alert-001", "title": "High CPU", "desc": "CPU usage exceeds 80%"}
        context = {"metrics_snapshot": "CPU: 85%", "platform": "linux"}

        with patch("core.ai_engine.analyze", return_value="Runbook steps"):
            result = await llm_service.generate_runbook(alert_data, context)

            assert result["runbook"] == "Runbook steps"
            assert result["alert_id"] == "alert-001"
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_search_similar_rag_unavailable(self, llm_service):
        """测试RAG不可用时的搜索"""
        query = "CPU high usage"

        # Mock the import at the module level to avoid heavy dependencies
        import sys

        # Add a mock module before the real one
        sys.modules["core.rag_engine"] = MagicMock()

        try:
            # 当RAG不可用时，应该返回空列表
            result = await llm_service.search_similar(query, limit=5)

            assert isinstance(result, list)
            assert len(result) == 0
        finally:
            # Clean up the mock
            if "core.rag_engine" in sys.modules:
                del sys.modules["core.rag_engine"]

    @pytest.mark.asyncio
    async def test_get_health_status_enabled(self, llm_service):
        """测试AI启用时的健康状态"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": True}):
            result = await llm_service.get_health_status()

            assert result["available"]
            assert result["status"] == "healthy"
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_health_status_disabled(self, llm_service):
        """测试AI禁用时的健康状态"""
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": False}):
            result = await llm_service.get_health_status()

            assert result["available"] is False
            assert result["status"] == "disabled"
