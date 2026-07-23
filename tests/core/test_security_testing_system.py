# -*- coding: utf-8 -*-
"""测试安全测试系统模块"""

import pytest


class TestSecurityTestingSystemModule:
    """测试安全测试系统模块"""

    def test_security_testing_system_module_exists(self):
        """测试安全测试系统模块存在"""
        from core import security_testing_system

        assert security_testing_system is not None

    def test_security_testing_system_has_enums(self):
        """测试安全测试系统模块有枚举"""
        from core import security_testing_system

        # 检查模块有枚举
        assert hasattr(security_testing_system, "TestType")
        assert hasattr(security_testing_system, "SeverityLevel")
        assert hasattr(security_testing_system, "TestStatus")

    def test_security_testing_system_has_dataclasses(self):
        """测试安全测试系统模块有数据类"""
        from core import security_testing_system

        # 检查模块有数据类
        assert hasattr(security_testing_system, "SecurityTest")
        assert hasattr(security_testing_system, "Vulnerability")
        assert hasattr(security_testing_system, "TestResult")

    def test_security_testing_system_has_classes(self):
        """测试安全测试系统模块有类"""
        from core import security_testing_system

        # 检查模块有类
        assert hasattr(security_testing_system, "SecurityTestingSystem")

    def test_security_testing_system_has_functions(self):
        """测试安全测试系统模块有函数"""
        from core import security_testing_system

        # 检查模块有函数
        assert hasattr(security_testing_system, "get_security_testing_system")


class TestTestType:
    """测试测试类型枚举"""

    def test_test_type_values(self):
        """测试测试类型值"""
        from core.security_testing_system import TestType

        assert TestType.SAST.value == "sast"
        assert TestType.DAST.value == "dast"
        assert TestType.SCA.value == "sca"
        assert TestType.DEPENDENCY_SCAN.value == "dependency_scan"
        assert TestType.CONTAINER_SCAN.value == "container_scan"
        assert TestType.INFRASTRUCTURE_SCAN.value == "infrastructure_scan"
        assert TestType.PENETRATION_TEST.value == "penetration_test"
        assert TestType.CODE_REVIEW.value == "code_review"


class TestSeverityLevel:
    """测试严重性级别枚举"""

    def test_severity_level_values(self):
        """测试严重性级别值"""
        from core.security_testing_system import SeverityLevel

        assert SeverityLevel.CRITICAL.value == "critical"
        assert SeverityLevel.HIGH.value == "high"
        assert SeverityLevel.MEDIUM.value == "medium"
        assert SeverityLevel.LOW.value == "low"
        assert SeverityLevel.INFO.value == "info"


class TestTestStatus:
    """测试测试状态枚举"""

    def test_test_status_values(self):
        """测试测试状态值"""
        from core.security_testing_system import TestStatus

        assert TestStatus.PENDING.value == "pending"
        assert TestStatus.RUNNING.value == "running"
        assert TestStatus.COMPLETED.value == "completed"
        assert TestStatus.FAILED.value == "failed"
        assert TestStatus.SKIPPED.value == "skipped"


class TestSecurityTest:
    """测试安全测试数据类"""

    def test_security_test_creation(self):
        """测试安全测试创建"""
        from core.security_testing_system import SecurityTest, TestType

        test = SecurityTest(
            test_id="test_scan",
            test_name="Test Scan",
            test_type=TestType.SAST,
            target="source_code",
        )

        assert test.test_id == "test_scan"
        assert test.test_name == "Test Scan"
        assert test.test_type == TestType.SAST
        assert test.target == "source_code"


class TestVulnerability:
    """测试漏洞数据类"""

    def test_vulnerability_creation(self):
        """测试漏洞创建"""
        from core.security_testing_system import SeverityLevel, Vulnerability

        vuln = Vulnerability(
            vulnerability_id="VULN_1",
            title="Test Vulnerability",
            severity=SeverityLevel.HIGH,
        )

        assert vuln.vulnerability_id == "VULN_1"
        assert vuln.title == "Test Vulnerability"
        assert vuln.severity == SeverityLevel.HIGH


class TestTestResult:
    """测试测试结果数据类"""

    def test_test_result_creation(self):
        """测试测试结果创建"""
        from core.security_testing_system import TestResult, TestStatus

        result = TestResult(
            test_id="test_scan",
            status=TestStatus.COMPLETED,
        )

        assert result.test_id == "test_scan"
        assert result.status == TestStatus.COMPLETED


class TestSecurityTestingSystem:
    """测试安全测试系统类"""

    def test_security_testing_system_initialization(self):
        """测试安全测试系统初始化"""
        from core.security_testing_system import SecurityTestingSystem

        system = SecurityTestingSystem()

        assert system.config == {}
        assert len(system.security_tests) > 0
        assert len(system.test_results) == 0
        assert len(system.vulnerabilities) == 0

    def test_security_testing_system_initialization_with_config(self):
        """测试安全测试系统初始化（带配置）"""
        from core.security_testing_system import SecurityTestingSystem

        config = {"reports_dir": "./test_reports", "auto_scan_enabled": False}
        system = SecurityTestingSystem(config)

        assert system.config == config

    def test_security_testing_system_default_tests(self):
        """测试安全测试系统默认测试"""
        from core.security_testing_system import SecurityTestingSystem

        system = SecurityTestingSystem()

        assert "sast_scan" in system.security_tests
        assert "dast_scan" in system.security_tests
        assert "sca_scan" in system.security_tests
        assert "dependency_scan" in system.security_tests
        assert "container_scan" in system.security_tests
        assert "infrastructure_scan" in system.security_tests

    def test_register_test(self):
        """测试注册测试"""
        from core.security_testing_system import (
            SecurityTest,
            SecurityTestingSystem,
            TestType,
        )

        system = SecurityTestingSystem()
        test = SecurityTest(
            test_id="new_test",
            test_name="New Test",
            test_type=TestType.SAST,
            target="source_code",
        )

        system.register_test(test)

        assert "new_test" in system.security_tests

    @pytest.mark.asyncio
    async def test_run_security_test(self):
        """测试运行安全测试"""
        from core.security_testing_system import SecurityTestingSystem

        system = SecurityTestingSystem()

        # Run test
        result_id = await system.run_security_test("sast_scan")

        assert result_id == "sast_scan"
        assert system.total_tests == 1

    @pytest.mark.asyncio
    async def test_run_security_test_invalid(self):
        """测试运行安全测试（无效）"""
        from core.security_testing_system import SecurityTestingSystem

        system = SecurityTestingSystem()

        with pytest.raises(ValueError):
            await system.run_security_test("invalid_test")

    @pytest.mark.asyncio
    async def test_run_all_tests(self):
        """测试运行所有测试"""
        from core.security_testing_system import SecurityTestingSystem

        system = SecurityTestingSystem()

        test_ids = await system.run_all_tests()

        assert len(test_ids) > 0
        assert system.total_tests > 0

    @pytest.mark.asyncio
    async def test_run_all_tests_with_filter(self):
        """测试运行所有测试（带过滤器）"""
        from core.security_testing_system import (
            SecurityTestingSystem,
            TestType,
        )

        system = SecurityTestingSystem()

        test_ids = await system.run_all_tests(test_type=TestType.SAST)

        assert len(test_ids) >= 1

    def test_get_test_result(self):
        """测试获取测试结果"""
        import asyncio

        from core.security_testing_system import SecurityTestingSystem

        system = SecurityTestingSystem()

        # Run test
        asyncio.run(system.run_security_test("sast_scan"))

        # Wait for test to complete
        import time

        time.sleep(4)

        result = system.get_test_result("sast_scan")

        assert result is not None
        assert result["test_id"] == "sast_scan"

    def test_get_test_result_invalid(self):
        """测试获取测试结果（无效）"""
        from core.security_testing_system import SecurityTestingSystem

        system = SecurityTestingSystem()

        result = system.get_test_result("invalid_test")

        assert result is None

    def test_get_vulnerabilities(self):
        """测试获取漏洞"""
        import asyncio
        import time

        from core.security_testing_system import SecurityTestingSystem

        system = SecurityTestingSystem()

        # Run test
        asyncio.run(system.run_security_test("sast_scan"))

        # Wait for test to complete
        time.sleep(4)

        vulns = system.get_vulnerabilities()

        assert isinstance(vulns, list)

    def test_get_vulnerabilities_with_filter(self):
        """测试获取漏洞（带过滤器）"""
        import asyncio
        import time

        from core.security_testing_system import (
            SecurityTestingSystem,
            SeverityLevel,
        )

        system = SecurityTestingSystem()

        # Run test
        asyncio.run(system.run_security_test("sast_scan"))

        # Wait for test to complete
        time.sleep(4)

        vulns = system.get_vulnerabilities(severity=SeverityLevel.CRITICAL)

        assert isinstance(vulns, list)

    @pytest.mark.asyncio
    async def test_generate_security_report(self):
        """测试生成安全报告"""
        from core.security_testing_system import SecurityTestingSystem

        system = SecurityTestingSystem()

        report = await system.generate_security_report()

        assert "generated_at" in report
        assert "total_tests" in report
        assert "total_vulnerabilities" in report
        assert "critical_vulnerabilities" in report
        assert "vulnerabilities_by_severity" in report

    def test_get_statistics(self):
        """测试获取统计信息"""
        from core.security_testing_system import SecurityTestingSystem

        system = SecurityTestingSystem()

        stats = system.get_statistics()

        assert "total_tests" in stats
        assert "total_vulnerabilities" in stats
        assert "critical_vulnerabilities" in stats
        assert "enabled_tests" in stats
        assert "registered_tests" in stats


class TestGetSecurityTestingSystem:
    """测试获取安全测试系统"""

    def test_get_security_testing_system(self):
        """测试获取安全测试系统"""
        from core.security_testing_system import get_security_testing_system

        system = get_security_testing_system()

        assert system is not None
        assert hasattr(system, "security_tests")

    def test_get_security_testing_system_with_config(self):
        """测试获取安全测试系统（带配置）"""
        from core.security_testing_system import get_security_testing_system

        config = {"reports_dir": "./test_reports"}
        system = get_security_testing_system(config)

        assert system.config == config


class TestSecurityTestingSystemIntegration:
    """测试安全测试系统集成"""

    @pytest.mark.asyncio
    async def test_complete_security_testing_workflow(self):
        """测试完整安全测试工作流"""
        from core.security_testing_system import SecurityTestingSystem

        system = SecurityTestingSystem()

        # Run test
        result_id = await system.run_security_test("sast_scan")
        assert result_id == "sast_scan"

        # Wait for test to complete
        import time

        time.sleep(4)

        # Get result
        result = system.get_test_result("sast_scan")
        assert result is not None

        # Get vulnerabilities
        vulns = system.get_vulnerabilities()
        assert isinstance(vulns, list)

        # Get statistics
        stats = system.get_statistics()
        assert stats["total_tests"] == 1

        # Generate report
        report = await system.generate_security_report()
        assert report["total_tests"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
