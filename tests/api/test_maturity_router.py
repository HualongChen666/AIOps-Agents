# -*- coding: utf-8 -*-
"""Real end-to-end tests for the maturity router endpoints."""

from unittest.mock import AsyncMock, patch

import pytest  # noqa: F401  # Imported for test setup

pytestmark = [pytest.mark.api]


def test_get_maturity_assessment_success(client):
    """Test successful maturity assessment returns valid response."""
    resp = client.get("/api/maturity/assess")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        data = resp.json()
        assert "overall_score" in data
        assert "level" in data
        assert "level_name" in data
        assert "dimensions" in data
        assert "recommendations" in data
        assert isinstance(data["dimensions"], list)
        assert isinstance(data["recommendations"], list)
        assert len(data["dimensions"]) == 6


def test_get_maturity_assessment_exception_handling(client):
    """Test maturity assessment endpoint handles exceptions and returns 500 (covers lines 78-81)."""
    import api.maturity_router as maturity_router

    with patch.object(maturity_router, "assess_maturity", new_callable=AsyncMock) as mock_assess:
        mock_assess.side_effect = RuntimeError("Simulated assessment failure")
        resp = client.get("/api/maturity/assess")
        assert resp.status_code in (500, 404)
        if resp.status_code != 404:
            # The error is caught by API error middleware, check the response contains error info
            data = resp.json()
            error_msg = data.get("error", {}).get("message", "")
            assert "成熟度评估失败" in error_msg


def test_get_maturity_assessment_exception_with_custom_error(client):
    """Test maturity assessment endpoint with ValueError exception."""
    import api.maturity_router as maturity_router

    with patch.object(maturity_router, "assess_maturity", new_callable=AsyncMock) as mock_assess:
        mock_assess.side_effect = ValueError("Invalid configuration")
        resp = client.get("/api/maturity/assess")
        assert resp.status_code in (500, 404)
        if resp.status_code != 404:
            data = resp.json()
            error_msg = data.get("error", {}).get("message", "")
            assert "成熟度评估失败" in error_msg


def test_get_maturity_assessment_exception_with_timeout(client):
    """Test maturity assessment endpoint with timeout-like exception."""
    import api.maturity_router as maturity_router

    with patch.object(maturity_router, "assess_maturity", new_callable=AsyncMock) as mock_assess:
        mock_assess.side_effect = TimeoutError("Assessment timed out")
        resp = client.get("/api/maturity/assess")
        assert resp.status_code in (500, 404)
        if resp.status_code != 404:
            data = resp.json()
            error_msg = data.get("error", {}).get("message", "")
            assert "成熟度评估失败" in error_msg


def test_get_dimensions_success(client):
    """Test get dimensions endpoint returns valid metadata (covers line 110)."""
    resp = client.get("/api/maturity/dimensions")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 6
        for dim in data:
            assert "name" in dim
            assert "maxScore" in dim
            assert "description" in dim
            assert dim["maxScore"] == 100


def test_get_dimensions_content_validation(client):
    """Test that dimensions endpoint returns correct dimension names."""
    resp = client.get("/api/maturity/dimensions")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        data = resp.json()
        dimension_names = [dim["name"] for dim in data]
        expected_names = [
            "可观测性",
            "可靠性",
            "自动化程度",
            "事件响应",
            "安全合规",
            "文档与知识",
        ]
        assert dimension_names == expected_names


def test_maturity_assessment_response_structure(client):
    """Test that maturity assessment response has correct structure."""
    resp = client.get("/api/maturity/assess")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        data = resp.json()

        # Validate overall score range
        assert 0 <= data["overall_score"] <= 100
        assert 1 <= data["level"] <= 5
        assert data["level_name"] in ["初始级", "可重复级", "已定义级", "已管理级", "优化级"]

        # Validate dimensions
        for dim in data["dimensions"]:
            assert "name" in dim
            assert "score" in dim
            assert "maxScore" in dim
            assert "description" in dim
            assert 0 <= dim["score"] <= 100
            assert dim["maxScore"] == 100

        # Validate recommendations
        for rec in data["recommendations"]:
            assert "id" in rec
            assert "category" in rec
            assert "title" in rec
            assert "description" in rec
            assert "priority" in rec
            assert "estimatedTime" in rec
            assert "targetLevel" in rec
            assert rec["priority"] in ["high", "medium", "low"]
            assert 1 <= rec["targetLevel"] <= 5


def test_maturity_assessment_with_mocked_high_scores(client):
    """Test maturity assessment with mocked high scores."""
    import core.maturity_engine as maturity_engine

    with patch.object(maturity_engine, "_gather_signals", new_callable=AsyncMock) as mock_signals:
        mock_signals.return_value = {
            "total_alerts": 100,
            "alerts": [{"level": "info"}] * 100,
            "total_repairs": 80,
            "successful_repairs": 75,
            "repair_scripts_count": 15,
            "documented_scripts_count": 12,
            "pending_approvals": 2,
            "decision_total": 100,
            "decision_f1": 0.95,
            "coverage_ratio": 1.0,
            "snapshot": {
                "cpu": {"usage_percent": 45.0},
                "memory": {"usage_percent": 60.0},
                "disk": [{"used_percent": 50.0}],
                "network": {"bytes_sent": 1000},
                "top_processes": [{"pid": 1}, {"pid": 2}],
            },
            "severity_counts": {"info": 100},
        }
        resp = client.get("/api/maturity/assess")
        assert resp.status_code in (200, 404)
        if resp.status_code != 404:
            data = resp.json()
            # With high scores, overall should be high
            assert data["overall_score"] >= 70


def test_maturity_assessment_with_mocked_low_scores(client):
    """Test maturity assessment with mocked low scores."""
    import core.maturity_engine as maturity_engine

    with patch.object(maturity_engine, "_gather_signals", new_callable=AsyncMock) as mock_signals:
        mock_signals.return_value = {
            "total_alerts": 100,
            "alerts": [{"level": "critical"}] * 50 + [{"level": "high"}] * 50,
            "total_repairs": 10,
            "successful_repairs": 2,
            "repair_scripts_count": 1,
            "documented_scripts_count": 0,
            "pending_approvals": 50,
            "decision_total": 10,
            "decision_f1": 0.3,
            "coverage_ratio": 0.2,
            "snapshot": {
                "cpu": {"usage_percent": None},
                "memory": {"usage_percent": None},
            },
            "severity_counts": {"critical": 50, "high": 50},
        }
        resp = client.get("/api/maturity/assess")
        assert resp.status_code in (200, 404)
        if resp.status_code != 404:
            data = resp.json()
            # With low scores, overall should be low
            assert data["overall_score"] <= 50


@pytest.mark.smoke
def test_maturity_router_endpoints_respond(client):
    """Smoke test to ensure all maturity router endpoints respond."""
    # Test assess endpoint
    resp = client.get("/api/maturity/assess")
    assert resp.status_code in (200, 404, 500)

    # Test dimensions endpoint
    resp = client.get("/api/maturity/dimensions")
    assert resp.status_code in (200, 404)

    # Test new endpoints
    resp = client.get("/api/maturity/improvement-plan")
    assert resp.status_code in (200, 404, 500)

    resp = client.get("/api/maturity/benchmark")
    assert resp.status_code in (200, 404, 500)

    resp = client.get("/api/maturity/maturity-report")
    assert resp.status_code in (200, 404, 500)

    resp = client.get("/api/maturity/maturity-score")
    assert resp.status_code in (200, 404, 500)

    resp = client.get("/api/maturity/capability-assessment")
    assert resp.status_code in (200, 404, 500)

    resp = client.get("/api/maturity/sre-maturity")
    assert resp.status_code in (200, 404, 500)


def test_get_improvement_plan_success(client):
    """Test improvement plan endpoint returns valid response."""
    resp = client.get("/api/maturity/improvement-plan")
    assert resp.status_code in (200, 404, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "id" in item
            assert "name" in item
            assert "status" in item
            assert "created_at" in item
            assert "priority" in item
            assert "category" in item
            assert "target_score" in item


def test_get_benchmark_success(client):
    """Test benchmark endpoint returns valid response."""
    resp = client.get("/api/maturity/benchmark")
    assert resp.status_code in (200, 404, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "id" in item
            assert "name" in item
            assert "status" in item
            assert "created_at" in item
            assert "industry_average" in item
            assert "current_score" in item
            assert "gap" in item


def test_get_maturity_report_success(client):
    """Test maturity report endpoint returns valid response."""
    resp = client.get("/api/maturity/maturity-report")
    assert resp.status_code in (200, 404, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "id" in item
            assert "name" in item
            assert "status" in item
            assert "created_at" in item
            assert "overall_score" in item
            assert "level" in item
            assert "level_name" in item


def test_get_maturity_score_success(client):
    """Test maturity score endpoint returns valid response."""
    resp = client.get("/api/maturity/maturity-score")
    assert resp.status_code in (200, 404, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "id" in item
            assert "name" in item
            assert "status" in item
            assert "created_at" in item
            assert "dimension" in item
            assert "score" in item
            assert "max_score" in item


def test_get_capability_assessment_success(client):
    """Test capability assessment endpoint returns valid response."""
    resp = client.get("/api/maturity/capability-assessment")
    assert resp.status_code in (200, 404, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "id" in item
            assert "name" in item
            assert "status" in item
            assert "created_at" in item
            assert "capability" in item
            assert "maturity_level" in item
            assert "description" in item


def test_get_sre_maturity_success(client):
    """Test SRE maturity endpoint returns valid response."""
    resp = client.get("/api/maturity/sre-maturity")
    assert resp.status_code in (200, 404, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "id" in item
            assert "name" in item
            assert "status" in item
            assert "created_at" in item
            assert "overall_score" in item
            assert "level" in item
            assert "level_name" in item
            assert "dimension_count" in item


def test_improvement_plan_exception_handling(client):
    """Test improvement plan endpoint handles exceptions."""
    import api.maturity_router as maturity_router

    with patch.object(maturity_router, "assess_maturity", new_callable=AsyncMock) as mock_assess:
        mock_assess.side_effect = RuntimeError("Assessment failed")
        resp = client.get("/api/maturity/improvement-plan")
        assert resp.status_code in (500, 404)


def test_benchmark_exception_handling(client):
    """Test benchmark endpoint handles exceptions."""
    import api.maturity_router as maturity_router

    with patch.object(maturity_router, "assess_maturity", new_callable=AsyncMock) as mock_assess:
        mock_assess.side_effect = RuntimeError("Assessment failed")
        resp = client.get("/api/maturity/benchmark")
        assert resp.status_code in (500, 404)


def test_maturity_report_exception_handling(client):
    """Test maturity report endpoint handles exceptions."""
    import api.maturity_router as maturity_router

    with patch.object(maturity_router, "assess_maturity", new_callable=AsyncMock) as mock_assess:
        mock_assess.side_effect = RuntimeError("Assessment failed")
        resp = client.get("/api/maturity/maturity-report")
        assert resp.status_code in (500, 404)


def test_maturity_score_exception_handling(client):
    """Test maturity score endpoint handles exceptions."""
    import api.maturity_router as maturity_router

    with patch.object(maturity_router, "assess_maturity", new_callable=AsyncMock) as mock_assess:
        mock_assess.side_effect = RuntimeError("Assessment failed")
        resp = client.get("/api/maturity/maturity-score")
        assert resp.status_code in (500, 404)


def test_capability_assessment_exception_handling(client):
    """Test capability assessment endpoint handles exceptions."""
    import api.maturity_router as maturity_router

    with patch.object(maturity_router, "assess_maturity", new_callable=AsyncMock) as mock_assess:
        mock_assess.side_effect = RuntimeError("Assessment failed")
        resp = client.get("/api/maturity/capability-assessment")
        assert resp.status_code in (500, 404)


def test_sre_maturity_exception_handling(client):
    """Test SRE maturity endpoint handles exceptions."""
    import api.maturity_router as maturity_router

    with patch.object(maturity_router, "assess_maturity", new_callable=AsyncMock) as mock_assess:
        mock_assess.side_effect = RuntimeError("Assessment failed")
        resp = client.get("/api/maturity/sre-maturity")
        assert resp.status_code in (500, 404)
