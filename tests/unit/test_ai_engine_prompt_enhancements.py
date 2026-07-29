# -*- coding: utf-8 -*-
"""针对 AIOps Agent SYSTEM_PROMPT 改进与 JSON schema 校验的回归测试."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestSystemPromptContent:
    """验证系统提示词是否包含关键安全、格式、规则."""

    def test_system_prompt_has_anti_jailbreak_rule(self):
        from core.ai_engine import SYSTEM_PROMPT

        assert "忽略本系统提示" in SYSTEM_PROMPT
        assert "不可信内容" in SYSTEM_PROMPT
        assert "泄露系统信息" in SYSTEM_PROMPT or "绕过安全限制" in SYSTEM_PROMPT

    def test_system_prompt_enforces_json_only(self):
        from core.ai_engine import SYSTEM_PROMPT

        assert "JSON" in SYSTEM_PROMPT
        assert "json.loads" in SYSTEM_PROMPT or "JSON 对象" in SYSTEM_PROMPT
        assert "markdown" in SYSTEM_PROMPT

    def test_system_prompt_handles_empty_data(self):
        from core.ai_engine import SYSTEM_PROMPT

        assert "关键上下文" in SYSTEM_PROMPT
        assert "reliability_score" in SYSTEM_PROMPT
        assert "candidates" in SYSTEM_PROMPT
        assert "escalation_recommended" in SYSTEM_PROMPT

    def test_system_prompt_has_command_safety_rules(self):
        from core.ai_engine import SYSTEM_PROMPT

        assert "PID < 100" in SYSTEM_PROMPT
        assert "python" in SYSTEM_PROMPT
        assert "uvicorn" in SYSTEM_PROMPT
        assert "清空防火墙规则" in SYSTEM_PROMPT
        assert "格式化磁盘" in SYSTEM_PROMPT

    def test_system_prompt_has_multiple_root_cause_guidance(self):
        from core.ai_engine import SYSTEM_PROMPT

        assert "多因素共同触发" in SYSTEM_PROMPT
        assert "multi_root_cause_note" in SYSTEM_PROMPT

    def test_runbook_system_prompt_is_distinct(self):
        from core.ai_engine import RUNBOOK_SYSTEM_PROMPT, SYSTEM_PROMPT

        assert "修复方案" in RUNBOOK_SYSTEM_PROMPT
        assert RUNBOOK_SYSTEM_PROMPT is not SYSTEM_PROMPT


class TestRootCauseResponseSchema:
    """验证 Pydantic 根因分析响应模型."""

    def test_valid_root_cause_response(self):
        from core.ai_engine import RootCauseAnalysisResponse

        payload = {
            "data_assessment": {
                "reliability_score": 0.8,
                "reliability_concerns": ["粒度不足"],
            },
            "candidates": [
                {
                    "rank": 1,
                    "root_cause": "mysql_slow_query",
                    "confidence": 0.85,
                    "expected_observations_if_true": ["cpu高"],
                    "missing_data": ["慢查询日志"],
                    "is_verifiable": True,
                    "evidence": ["qps下降"],
                }
            ],
            "multi_root_cause_note": "",
            "escalation_recommended": False,
            "escalation_reason": "",
            "recommended_action": "检查慢查询日志",
        }
        model = RootCauseAnalysisResponse.model_validate(payload)
        assert model.escalation_recommended is False
        assert len(model.candidates) == 1
        assert model.candidates[0].rank == 1

    def test_invalid_confidence_rejected(self):
        from core.ai_engine import RootCauseAnalysisResponse

        payload = {
            "data_assessment": {"reliability_score": 0.8},
            "candidates": [
                {
                    "rank": 1,
                    "root_cause": "x",
                    "confidence": 1.5,  # 越界
                    "is_verifiable": True,
                }
            ],
            "escalation_recommended": False,
        }
        with pytest.raises(Exception):
            RootCauseAnalysisResponse.model_validate(payload)

    def test_missing_data_assessment_rejected(self):
        from core.ai_engine import RootCauseAnalysisResponse

        payload = {
            "candidates": [],
            "escalation_recommended": True,
        }
        with pytest.raises(Exception):
            RootCauseAnalysisResponse.model_validate(payload)


class TestValidateRootCauseOutput:
    """验证 LLM 输出清洗与 schema 校验."""

    def test_valid_json_parsed(self):
        from core.ai_engine import _validate_root_cause_output

        raw = json.dumps(
            {
                "data_assessment": {"reliability_score": 0.9},
                "candidates": [
                    {
                        "rank": 1,
                        "root_cause": "cpu_high",
                        "confidence": 0.9,
                        "is_verifiable": True,
                    }
                ],
                "escalation_recommended": False,
            }
        )
        validated = _validate_root_cause_output(raw)
        assert validated is not None
        parsed = json.loads(validated)
        assert parsed["candidates"][0]["root_cause"] == "cpu_high"

    def test_markdown_fence_stripped(self):
        from core.ai_engine import _validate_root_cause_output

        inner = json.dumps(
            {
                "data_assessment": {"reliability_score": 0.7},
                "candidates": [],
                "escalation_recommended": True,
                "escalation_reason": "无数据",
            }
        )
        raw = f"```json\n{inner}\n```"
        validated = _validate_root_cause_output(raw)
        assert validated is not None
        assert json.loads(validated)["escalation_recommended"] is True

    def test_invalid_json_returns_none(self):
        from core.ai_engine import _validate_root_cause_output

        assert _validate_root_cause_output("not a json") is None
        assert _validate_root_cause_output("") is None


class TestFallbackJson:
    """兜底 JSON 满足 schema 且明确升级."""

    def test_fallback_has_expected_shape(self):
        from core.ai_engine import _fallback_schema_error_json

        raw = _fallback_schema_error_json("test")
        parsed = json.loads(raw)
        assert parsed["data_assessment"]["reliability_score"] == 0.0
        assert parsed["candidates"] == []
        assert parsed["escalation_recommended"] is True
        assert "人工复核" in parsed["escalation_reason"]


class TestAnalyzePromptOverrides:
    """验证 analyze() 参数传递与 JSON 校验."""

    @pytest.mark.asyncio
    async def test_analyze_passes_custom_system_prompt(self):
        from core.ai_engine import analyze

        valid_payload = {
            "data_assessment": {"reliability_score": 0.8},
            "candidates": [],
            "escalation_recommended": True,
            "escalation_reason": "test",
            "recommended_action": "wait",
        }
        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": True}):
            mock_router = AsyncMock()
            mock_router.generate = AsyncMock(
                return_value={
                    "content": json.dumps(valid_payload),
                    "model": "gpt",
                    "usage": {"total_tokens": 10},
                }
            )
            with patch("core.ai_engine.get_llm_router", return_value=mock_router):
                with patch("core.ai_engine.moderate_content", return_value=(True, [])):
                    with patch("core.ai_engine._rate_limit_wait", new_callable=AsyncMock):
                        with patch("core.ai_engine._langfuse_available", False):
                            with patch("core.ai_engine.get_llm_cost_monitor", return_value=None):
                                result = await analyze(
                                    query="test",
                                    system_prompt="custom system prompt",
                                    validate_json=True,
                                )
        assert isinstance(result, str)
        assert json.loads(result)["escalation_recommended"] is True
        call_kwargs = mock_router.generate.call_args.kwargs
        assert call_kwargs["system"] == "custom system prompt"

    @pytest.mark.asyncio
    async def test_analyze_returns_fallback_for_invalid_json(self):
        from core.ai_engine import analyze

        with patch("core.ai_engine.AI_CONFIG", {"is_enabled": True}):
            mock_router = AsyncMock()
            mock_router.generate = AsyncMock(
                return_value={
                    "content": "invalid json",
                    "model": "gpt",
                    "usage": {"total_tokens": 5},
                }
            )
            with patch("core.ai_engine.get_llm_router", return_value=mock_router):
                with patch("core.ai_engine.moderate_content", return_value=(True, [])):
                    with patch("core.ai_engine._rate_limit_wait", new_callable=AsyncMock):
                        with patch("core.ai_engine._langfuse_available", False):
                            with patch("core.ai_engine.get_llm_cost_monitor", return_value=None):
                                result = await analyze(
                                    query="test",
                                    validate_json=True,
                                )
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["escalation_recommended"] is True
        assert parsed["candidates"] == []


class TestRunbookSystemPrompt:
    """验证 runbook 生成使用独立 system prompt."""

    @pytest.mark.asyncio
    async def test_llm_analysis_service_runbook_uses_runbook_prompt(self):
        from core.ai_engine import RUNBOOK_SYSTEM_PROMPT, LLMAnalysisService

        service = LLMAnalysisService()
        with patch("core.ai_engine.analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = '{"steps": []}'
            await service.generate_runbook(
                {"id": "a1", "title": "CPU", "desc": "high"},
                {"platform": "linux"},
            )
            call_kwargs = mock_analyze.call_args.kwargs
            assert call_kwargs["system_prompt"] is RUNBOOK_SYSTEM_PROMPT
            assert call_kwargs["validate_json"] is False


class TestAIRouterSchemaValidation:
    """验证 api/ai_router.py 对 analyze 返回的 JSON 做兜底."""

    @pytest.fixture
    def ai_router_client(self, monkeypatch):
        import api.ai_router as _ai_router

        monkeypatch.setattr(_ai_router, "_collect_snapshot_with_cache", AsyncMock(return_value={}))
        monkeypatch.setattr(_ai_router, "_collect_rich_context", AsyncMock(return_value=None))
        test_app = FastAPI()
        test_app.include_router(_ai_router.router)
        return TestClient(test_app)

    def test_ai_router_returns_fallback_for_invalid_llm_json(self, ai_router_client):
        import api.ai_router as _ai_router

        with patch.object(_ai_router, "analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = "not json"
            response = ai_router_client.post(
                "/api/ai/analyze",
                json={
                    "query": "test",
                    "include_metrics": False,
                    "platform": "windows",
                    "include_rich_context": False,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["analysis"]["escalation_recommended"] is True
            assert data["analysis"]["candidates"] == []
            assert mock_analyze.call_args.kwargs.get("validate_json") is True
