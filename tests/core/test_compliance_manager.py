# -*- coding: utf-8 -*-
"""测试合规管理器"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from core.compliance_manager import (
    ComplianceFramework,
    ComplianceManager,
    ComplianceRule,
    ComplianceStatus,
    RiskLevel,
    get_compliance_manager,
)


@pytest.fixture
def manager(tmp_path):
    return ComplianceManager({"audit_trail_dir": str(tmp_path), "auto_check_enabled": False})


class TestEnumsAndDataclasses:
    def test_framework_values(self):
        assert ComplianceFramework.GDPR.value == "gdpr"
        assert ComplianceStatus.COMPLIANT.value == "compliant"

    def test_dataclasses(self):
        rule = ComplianceRule(
            rule_id="r1",
            rule_name="R",
            framework=ComplianceFramework.SOC2,
            description="d",
            severity=RiskLevel.HIGH,
        )
        assert rule.enabled is True


class TestInitialization:
    def test_default_rules(self, manager):
        assert "gdpr_data_minimization" in manager.compliance_rules
        assert manager.total_checks == 0

    def test_get_manager(self, tmp_path):
        m = get_compliance_manager({"audit_trail_dir": str(tmp_path)})
        assert isinstance(m, ComplianceManager)


class TestRules:
    def test_register_rule(self, manager):
        rule = ComplianceRule(
            rule_id="custom",
            rule_name="Custom",
            framework=ComplianceFramework.NIST,
            description="d",
            severity=RiskLevel.LOW,
        )
        manager.register_rule(rule)
        assert manager.compliance_rules["custom"] is rule

    def test_get_compliance_rules(self, manager):
        rules = manager.get_compliance_rules(framework=ComplianceFramework.GDPR)
        assert all(r["framework"] == "gdpr" for r in rules.values())

        all_rules = manager.get_compliance_rules()
        assert len(all_rules) == len(manager.compliance_rules)


class TestComplianceChecks:
    def test_run_check_by_rule_id(self, manager):
        with patch("random.random", return_value=0.8):
            checks = asyncio.run(manager.run_compliance_check(rule_id="gdpr_data_minimization"))
        assert len(checks) == 1
        assert checks[0].rule_id == "gdpr_data_minimization"

    def test_run_check_by_framework(self, manager):
        with patch("random.random", return_value=0.8):
            checks = asyncio.run(manager.run_compliance_check(framework=ComplianceFramework.GDPR))
        assert len(checks) == 3
        assert all(c.rule_id.startswith("gdpr") for c in checks)

    def test_run_all_checks(self, manager):
        with patch("random.random", return_value=0.8):
            checks = asyncio.run(manager.run_compliance_check())
        assert len(checks) == len(manager.compliance_rules)

    def test_run_check_nonexistent(self, manager):
        checks = asyncio.run(manager.run_compliance_check(rule_id="missing"))
        assert checks == []


class TestReportAndHistory:
    def test_generate_report(self, manager, tmp_path):
        start = datetime.now(timezone.utc)
        end = datetime.now(timezone.utc)
        with patch("random.random", return_value=0.8):
            report = asyncio.run(
                manager.generate_compliance_report(ComplianceFramework.GDPR, start, end)
            )
        assert report.overall_status == ComplianceStatus.COMPLIANT
        report_file = f"report_gdpr_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.json"
        assert (tmp_path / report_file).exists()

    def test_get_check_history(self, manager):
        with patch("random.random", return_value=0.8):
            asyncio.run(manager.run_compliance_check(rule_id="gdpr_data_minimization"))
        history = manager.get_check_history(rule_id="gdpr_data_minimization")
        assert len(history) == 1

    def test_violation_notification(self, manager):
        calls = []
        manager.register_notification_handler(lambda v: calls.append(len(v)))
        with patch("random.random", return_value=0.2):
            asyncio.run(manager.run_compliance_check(rule_id="gdpr_data_minimization"))
        assert calls == [1]

    async def _async_handler(self, v):
        self._async_calls = len(v)

    def test_async_violation_notification(self, manager):
        calls = []

        async def handler(v):
            calls.append(len(v))

        manager.register_notification_handler(handler)
        with patch("random.random", return_value=0.2):
            asyncio.run(manager.run_compliance_check(rule_id="gdpr_data_minimization"))
        assert calls == [1]


class TestStatistics:
    def test_get_statistics(self, manager):
        with patch("random.random", return_value=0.2):
            asyncio.run(manager.run_compliance_check(rule_id="gdpr_data_minimization"))
        stats = manager.get_statistics()
        assert stats["total_checks"] == 1
        assert stats["total_violations"] == 1
        assert stats["violation_rate"] == 1.0

    def test_start_auto_check_disabled(self, manager):
        manager.config["auto_check_enabled"] = False
        result = asyncio.run(manager.start_auto_check_loop())
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
