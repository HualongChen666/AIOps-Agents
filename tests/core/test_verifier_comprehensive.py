# -*- coding: utf-8 -*-
"""
Comprehensive test suite for core/verifier.py
Target: 90%+ statement and branch coverage
"""

import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.verifier import (
    _CONFIDENCE_METRIC_THRESHOLD,
    _CONFIDENCE_PROCESS_CHECK,
    _CONFIDENCE_SERVICE_STATUS,
    _SERVICE_NAME_PATTERN,
    _SYSTEMCTL_ACTIVE_STATES,
    _VALID_PLATFORMS,
    VerifyResult,
    _build_error_result,
    _build_skipped_result,
    _select_strategy,
    verify_repair,
)


class TestVerifyRepair:
    """Test suite for verify_repair function"""

    @pytest.mark.asyncio
    async def test_verify_repair_disabled(self):
        """Test verification when disabled in config"""
        with patch("core.verifier.VERIFY_CONFIG", {"enabled": False}):
            alert = {"platform": "linux", "host": "server1"}
            result = await verify_repair(
                alert=alert,
                script_key="restart_service",
                params={},
                pre_snapshot=None,
                repair_output="Success",
                repair_id=1,
            )

            assert result["verified"] is None
            assert result["strategy"] == "skipped"

    @pytest.mark.asyncio
    async def test_verify_repair_invalid_alert(self):
        """Test verification with invalid alert"""
        with patch("core.verifier.VERIFY_CONFIG", {"enabled": True}):
            result = await verify_repair(
                alert=None,
                script_key="restart_service",
                params={},
                pre_snapshot=None,
                repair_output="Success",
                repair_id=1,
            )

            assert result["strategy"] == "error"
            assert "must be dict" in result["error_msg"]

    @pytest.mark.asyncio
    async def test_verify_repair_invalid_script_key(self):
        """Test verification with invalid script key"""
        with patch("core.verifier.VERIFY_CONFIG", {"enabled": True}):
            alert = {"platform": "linux"}
            result = await verify_repair(
                alert=alert,
                script_key="",
                params={},
                pre_snapshot=None,
                repair_output="Success",
                repair_id=1,
            )

            assert result["strategy"] == "error"
            assert "cannot be empty" in result["error_msg"]

    @pytest.mark.asyncio
    async def test_verify_repair_invalid_platform(self):
        """Test verification with invalid platform (should default to windows)"""
        with patch("core.verifier.VERIFY_CONFIG", {"enabled": True}):
            alert = {"platform": "invalid_platform"}
            result = await verify_repair(
                alert=alert,
                script_key="restart_service",
                params={},
                pre_snapshot=None,
                repair_output="Success",
                repair_id=1,
            )

            # Should default to windows
            assert result["strategy"] in ["skipped", "error", "service_status"]

    @pytest.mark.asyncio
    async def test_verify_repair_skipped_strategy(self):
        """Test verification when strategy is skipped"""
        with patch("core.verifier.VERIFY_CONFIG", {"enabled": True}):
            with patch("core.verifier._select_strategy", return_value="none"):
                alert = {"platform": "linux"}
                result = await verify_repair(
                    alert=alert,
                    script_key="unknown_script",
                    params={},
                    pre_snapshot=None,
                    repair_output="Success",
                    repair_id=1,
                )

                assert result["verified"] is None
                assert result["strategy"] == "skipped"

    @pytest.mark.asyncio
    async def test_verify_repair_timeout(self):
        """Test verification timeout"""
        with patch("core.verifier.VERIFY_CONFIG", {"enabled": True, "timeout_sec": 0.1}):
            with patch("core.verifier._select_strategy", return_value="service_status"):
                with patch(
                    "core.verifier._dispatch_verification", side_effect=asyncio.TimeoutError
                ):
                    alert = {"platform": "linux"}
                    result = await verify_repair(
                        alert=alert,
                        script_key="restart_service",
                        params={},
                        pre_snapshot=None,
                        repair_output="Success",
                        repair_id=1,
                    )

                    assert result["strategy"] == "timeout"
                    assert "timeout" in result["error_msg"].lower()

    @pytest.mark.asyncio
    async def test_verify_repair_cancelled(self):
        """Test verification cancellation"""
        with patch("core.verifier.VERIFY_CONFIG", {"enabled": True}):
            with patch("core.verifier._select_strategy", return_value="service_status"):
                with patch(
                    "core.verifier._dispatch_verification", side_effect=asyncio.CancelledError
                ):
                    alert = {"platform": "linux"}

                    with pytest.raises(asyncio.CancelledError):
                        await verify_repair(
                            alert=alert,
                            script_key="restart_service",
                            params={},
                            pre_snapshot=None,
                            repair_output="Success",
                            repair_id=1,
                        )

    @pytest.mark.asyncio
    async def test_verify_repair_exception(self):
        """Test verification with exception"""
        with patch("core.verifier.VERIFY_CONFIG", {"enabled": True}):
            with patch("core.verifier._select_strategy", return_value="service_status"):
                with patch(
                    "core.verifier._dispatch_verification", side_effect=Exception("Test error")
                ):
                    alert = {"platform": "linux"}
                    result = await verify_repair(
                        alert=alert,
                        script_key="restart_service",
                        params={},
                        pre_snapshot=None,
                        repair_output="Success",
                        repair_id=1,
                    )

                    assert result["strategy"] == "error"
                    assert "Test error" in result["error_msg"]

    @pytest.mark.asyncio
    async def test_verify_repair_metric_threshold_conflict(self):
        """Test verification with metric_threshold timeout conflict"""
        with patch(
            "core.verifier.VERIFY_CONFIG", {"enabled": True, "timeout_sec": 3, "metric_wait_sec": 5}
        ):
            with patch("core.verifier._select_strategy", return_value="metric_threshold"):
                alert = {"platform": "linux"}
                result = await verify_repair(
                    alert=alert,
                    script_key="free_cache",
                    params={},
                    pre_snapshot=None,
                    repair_output="Success",
                    repair_id=1,
                )

                assert result["strategy"] == "skipped"
                assert "incompatible" in result["recommendation"].lower()

    @pytest.mark.asyncio
    async def test_verify_repair_success(self):
        """Test successful verification"""
        with patch("core.verifier.VERIFY_CONFIG", {"enabled": True, "timeout_sec": 10}):
            with patch("core.verifier._select_strategy", return_value="service_status"):
                with patch("core.verifier._dispatch_verification") as mock_dispatch:
                    mock_dispatch.return_value = {
                        "verified": True,
                        "strategy": "service_status",
                        "confidence": 0.95,
                        "evidence": {},
                        "duration_sec": 1.0,
                        "error_msg": "",
                        "recommendation": "",
                    }

                    with patch("core.verifier.upsert_verify_record"):
                        alert = {"platform": "linux"}
                        result = await verify_repair(
                            alert=alert,
                            script_key="restart_service",
                            params={},
                            pre_snapshot=None,
                            repair_output="Success",
                            repair_id=1,
                        )

                        assert result["verified"] is True


class TestSelectStrategy:
    """Test suite for _select_strategy function"""

    def test_select_strategy_ai_dynamic_systemctl(self):
        """Test AI_DYNAMIC with systemctl restart"""
        ai_runbook = {"commands": ["systemctl restart nginx"]}
        result = _select_strategy("AI_DYNAMIC", ai_runbook)
        assert result == "service_status"

    def test_select_strategy_ai_dynamic_kill(self):
        """Test AI_DYNAMIC with kill command"""
        ai_runbook = {"commands": ["kill -9 1234"]}
        result = _select_strategy("AI_DYNAMIC", ai_runbook)
        assert result == "process_check"

    def test_select_strategy_ai_dynamic_stop_process(self):
        """Test AI_DYNAMIC with Stop-Process"""
        ai_runbook = {"commands": ["Stop-Process -Id 1234"]}
        result = _select_strategy("AI_DYNAMIC", ai_runbook)
        assert result == "process_check"

    def test_select_strategy_ai_dynamic_drop_caches(self):
        """Test AI_DYNAMIC with drop_caches"""
        ai_runbook = {"commands": ["echo 3 > /proc/sys/vm/drop_caches"]}
        result = _select_strategy("AI_DYNAMIC", ai_runbook)
        assert result == "metric_threshold"

    def test_select_strategy_ai_dynamic_disk_cleanup(self):
        """Test AI_DYNAMIC with disk cleanup"""
        ai_runbook = {"commands": ["rm -rf /tmp/*"]}
        result = _select_strategy("AI_DYNAMIC", ai_runbook)
        assert result == "disk_usage"

    def test_select_strategy_ai_dynamic_network(self):
        """Test AI_DYNAMIC with network command"""
        ai_runbook = {"commands": ["ping google.com"]}
        result = _select_strategy("AI_DYNAMIC", ai_runbook)
        assert result == "network_check"

    def test_select_strategy_ai_dynamic_kubectl(self):
        """Test AI_DYNAMIC with kubectl"""
        ai_runbook = {"commands": ["kubectl get pods"]}
        result = _select_strategy("AI_DYNAMIC", ai_runbook)
        assert result == "k8s_status"

    def test_select_strategy_ai_dynamic_no_match(self):
        """Test AI_DYNAMIC with no matching pattern"""
        ai_runbook = {"commands": ["some random command"]}
        result = _select_strategy("AI_DYNAMIC", ai_runbook)
        assert result == "custom_command"

    def test_select_strategy_ai_dynamic_no_runbook(self):
        """Test AI_DYNAMIC without runbook"""
        result = _select_strategy("AI_DYNAMIC", None)
        assert result == "custom_command"

    def test_select_strategy_restart_service(self):
        """Test restart_service script key"""
        result = _select_strategy("restart_service", None)
        assert result == "service_status"

    def test_select_strategy_kill_high_cpu(self):
        """Test kill_high_cpu script key"""
        result = _select_strategy("kill_high_cpu", None)
        assert result == "process_check"

    def test_select_strategy_free_cache(self):
        """Test free_cache script key"""
        result = _select_strategy("free_cache", None)
        assert result == "metric_threshold"

    def test_select_strategy_disk_high_script(self):
        """Test disk_high_script script key"""
        result = _select_strategy("disk_high_script", None)
        assert result == "disk_usage"

    def test_select_strategy_flush_dns(self):
        """Test flush_dns script key"""
        result = _select_strategy("flush_dns", None)
        assert result == "network_check"

    def test_select_strategy_k8s_pod_crash(self):
        """Test k8s_pod_crash script key"""
        result = _select_strategy("k8s_pod_crash", None)
        assert result == "k8s_status"

    def test_select_strategy_unknown(self):
        """Test unknown script key"""
        result = _select_strategy("unknown_script", None)
        assert result == "none"


class TestBuildSkippedResult:
    """Test suite for _build_skipped_result function"""

    def test_build_skipped_result_basic(self):
        """Test basic skipped result"""
        result = _build_skipped_result(strategy="skipped", recommendation="Test recommendation")

        assert result["verified"] is None
        assert result["strategy"] == "skipped"
        assert result["confidence"] == 0.0
        assert result["recommendation"] == "Test recommendation"
        assert result["error_msg"] == ""


class TestBuildErrorResult:
    """Test suite for _build_error_result function"""

    def test_build_error_result_basic(self):
        """Test basic error result"""
        result = _build_error_result(strategy="error", error_msg="Test error")

        assert result["verified"] is False
        assert result["strategy"] == "error"
        assert result["confidence"] == 0.0
        assert result["error_msg"] == "Test error"
        assert result["recommendation"] == ""

    def test_build_error_result_with_duration(self):
        """Test error result with duration"""
        result = _build_error_result(strategy="error", error_msg="Test error", duration_sec=5.5)

        assert result["duration_sec"] == 5.5


class TestConstants:
    """Test suite for module constants"""

    def test_confidence_constants(self):
        """Test confidence constants"""
        assert 0.0 <= _CONFIDENCE_SERVICE_STATUS <= 1.0
        assert 0.0 <= _CONFIDENCE_PROCESS_CHECK <= 1.0
        assert 0.0 <= _CONFIDENCE_METRIC_THRESHOLD <= 1.0

    def test_valid_platforms(self):
        """Test valid platforms constant"""
        assert "windows" in _VALID_PLATFORMS
        assert "linux" in _VALID_PLATFORMS

    def test_service_name_pattern(self):
        """Test service name pattern"""
        assert _SERVICE_NAME_PATTERN.match("nginx")
        assert _SERVICE_NAME_PATTERN.match("my-service_1")
        assert not _SERVICE_NAME_PATTERN.match("nginx;rm -rf")

    def test_systemctl_active_states(self):
        """Test systemctl active states"""
        assert "active" in _SYSTEMCTL_ACTIVE_STATES
        assert "activating" in _SYSTEMCTL_ACTIVE_STATES
        assert "reloading" in _SYSTEMCTL_ACTIVE_STATES


class TestVerifyResultTypedDict:
    """Test suite for VerifyResult TypedDict"""

    def test_verify_result_structure(self):
        """Test VerifyResult has correct structure"""
        result: VerifyResult = {
            "verified": True,
            "strategy": "service_status",
            "confidence": 0.95,
            "evidence": {},
            "duration_sec": 1.0,
            "error_msg": "",
            "recommendation": "",
        }

        assert result["verified"] is True
        assert result["strategy"] == "service_status"
        assert result["confidence"] == 0.95


class TestEdgeCases:
    """Test suite for edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_verify_repair_deep_copy_pre_snapshot(self):
        """Test that pre_snapshot is deep copied"""
        with patch("core.verifier.VERIFY_CONFIG", {"enabled": True}):
            with patch("core.verifier._select_strategy", return_value="none"):
                original_snapshot = {"data": "test"}
                alert = {"platform": "linux"}

                await verify_repair(
                    alert=alert,
                    script_key="unknown",
                    params={},
                    pre_snapshot=original_snapshot,
                    repair_output="Success",
                    repair_id=1,
                )

                # Original should be unchanged
                assert original_snapshot == {"data": "test"}

    @pytest.mark.asyncio
    async def test_verify_repair_repair_output_truncation(self):
        """Test that repair_output is truncated in evidence"""
        long_output = "x" * 500

        with patch("core.verifier.VERIFY_CONFIG", {"enabled": True}):
            with patch("core.verifier._select_strategy", return_value="none"):
                with patch("core.verifier._dispatch_verification") as mock_dispatch:
                    mock_dispatch.return_value = {
                        "verified": None,
                        "strategy": "skipped",
                        "confidence": 0.0,
                        "evidence": {},
                        "duration_sec": 0.0,
                        "error_msg": "",
                        "recommendation": "",
                    }

                    with patch("core.verifier.upsert_verify_record"):
                        alert = {"platform": "linux"}
                        result = await verify_repair(
                            alert=alert,
                            script_key="unknown",
                            params={},
                            pre_snapshot=None,
                            repair_output=long_output,
                            repair_id=1,
                        )

                        # Check that repair_output was added to evidence
                        assert "repair_output_preview" in result["evidence"]
                        assert len(result["evidence"]["repair_output_preview"]) <= 200

    @pytest.mark.asyncio
    async def test_verify_repair_vector_db_failure(self):
        """Test that vector DB write failure doesn't affect result"""
        with patch("core.verifier.VERIFY_CONFIG", {"enabled": True}):
            with patch("core.verifier._select_strategy", return_value="none"):
                with patch("core.verifier.upsert_verify_record", side_effect=Exception("DB error")):
                    alert = {"platform": "linux"}
                    result = await verify_repair(
                        alert=alert,
                        script_key="unknown",
                        params={},
                        pre_snapshot=None,
                        repair_output="Success",
                        repair_id=1,
                    )

                    # Should still return result despite DB error
                    assert result["strategy"] == "skipped"
