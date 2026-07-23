# -*- coding: utf-8 -*-
"""测试安全系统集成模块"""

import pytest


class TestSecuritySystemIntegratorModule:
    """测试安全系统集成模块"""

    def test_security_system_integrator_module_exists(self):
        """测试安全系统集成模块存在"""
        from core import security_system_integrator

        assert security_system_integrator is not None

    def test_security_system_integrator_has_enums(self):
        """测试安全系统集成模块有枚举"""
        from core import security_system_integrator

        # 检查模块有枚举
        assert hasattr(security_system_integrator, "SecurityComponent")
        assert hasattr(security_system_integrator, "IntegrationStatus")

    def test_security_system_integrator_has_dataclasses(self):
        """测试安全系统集成模块有数据类"""
        from core import security_system_integrator

        # 检查模块有数据类
        assert hasattr(security_system_integrator, "SecurityIntegration")
        assert hasattr(security_system_integrator, "SecurityIncident")

    def test_security_system_integrator_has_classes(self):
        """测试安全系统集成模块有类"""
        from core import security_system_integrator

        # 检查模块有类
        assert hasattr(security_system_integrator, "SecuritySystemIntegrator")

    def test_security_system_integrator_has_functions(self):
        """测试安全系统集成模块有函数"""
        from core import security_system_integrator

        # 检查模块有函数
        assert hasattr(security_system_integrator, "get_security_system_integrator")


class TestSecurityComponent:
    """测试安全组件枚举"""

    def test_security_component_values(self):
        """测试安全组件值"""
        from core.security_system_integrator import SecurityComponent

        assert SecurityComponent.COMPLIANCE_MANAGER.value == "compliance_manager"
        assert SecurityComponent.SECURITY_TESTING.value == "security_testing"
        assert SecurityComponent.VULNERABILITY_MANAGER.value == "vulnerability_manager"
        assert SecurityComponent.SECURITY_AUDIT.value == "security_audit"
        assert SecurityComponent.AUTHENTICATION.value == "authentication"
        assert SecurityComponent.AUTHORIZATION.value == "authorization"
        assert SecurityComponent.ENCRYPTION.value == "encryption"
        assert SecurityComponent.NETWORK_SECURITY.value == "network_security"


class TestIntegrationStatus:
    """测试集成状态枚举"""

    def test_integration_status_values(self):
        """测试集成状态值"""
        from core.security_system_integrator import IntegrationStatus

        assert IntegrationStatus.CONNECTED.value == "connected"
        assert IntegrationStatus.DISCONNECTED.value == "disconnected"
        assert IntegrationStatus.ERROR.value == "error"
        assert IntegrationStatus.DEGRADED.value == "degraded"


class TestSecurityIntegration:
    """测试安全集成数据类"""

    def test_security_integration_creation(self):
        """测试安全集成创建"""
        from core.security_system_integrator import (
            IntegrationStatus,
            SecurityComponent,
            SecurityIntegration,
        )

        integration = SecurityIntegration(
            integration_id="test_integration",
            component=SecurityComponent.SECURITY_AUDIT,
        )

        assert integration.integration_id == "test_integration"
        assert integration.component == SecurityComponent.SECURITY_AUDIT
        assert integration.status == IntegrationStatus.DISCONNECTED


class TestSecurityIncident:
    """测试安全事件数据类"""

    def test_security_incident_creation(self):
        """测试安全事件创建"""
        from core.security_system_integrator import (
            SecurityComponent,
            SecurityIncident,
        )

        incident = SecurityIncident(
            incident_id="test_incident",
            title="Test Incident",
            severity="high",
            component=SecurityComponent.SECURITY_AUDIT,
        )

        assert incident.incident_id == "test_incident"
        assert incident.title == "Test Incident"
        assert incident.severity == "high"
        assert incident.component == SecurityComponent.SECURITY_AUDIT


class TestSecuritySystemIntegrator:
    """测试安全系统集成类"""

    def test_security_system_integrator_initialization(self):
        """测试安全系统集成初始化"""
        from core.security_system_integrator import SecuritySystemIntegrator

        integrator = SecuritySystemIntegrator()

        assert integrator.config == {}
        assert len(integrator.security_integrations) == 0
        assert len(integrator.security_incidents) == 0

    def test_security_system_integrator_initialization_with_config(self):
        """测试安全系统集成初始化（带配置）"""
        from core.security_system_integrator import SecuritySystemIntegrator

        config = {"auto_reconnect": False, "health_check_interval": 600}
        integrator = SecuritySystemIntegrator(config)

        assert integrator.config == config
        assert integrator.auto_reconnect is False
        assert integrator.health_check_interval == 600

    @pytest.mark.asyncio
    async def test_register_component(self):
        """测试注册组件"""
        from core.security_system_integrator import (
            IntegrationStatus,
            SecurityComponent,
            SecurityIntegration,
            SecuritySystemIntegrator,
        )

        integrator = SecuritySystemIntegrator()
        integration = SecurityIntegration(
            integration_id="test_integration",
            component=SecurityComponent.SECURITY_AUDIT,
        )

        await integrator.register_component(integration)

        assert "test_integration" in integrator.security_integrations
        assert (
            integrator.security_integrations["test_integration"].status
            == IntegrationStatus.CONNECTED
        )

    @pytest.mark.asyncio
    async def test_disconnect_component(self):
        """测试断开组件"""
        from core.security_system_integrator import (
            IntegrationStatus,
            SecurityComponent,
            SecurityIntegration,
            SecuritySystemIntegrator,
        )

        integrator = SecuritySystemIntegrator()
        integration = SecurityIntegration(
            integration_id="test_integration",
            component=SecurityComponent.SECURITY_AUDIT,
        )

        await integrator.register_component(integration)
        result = await integrator.disconnect_component("test_integration")

        assert result is True
        assert (
            integrator.security_integrations["test_integration"].status
            == IntegrationStatus.DISCONNECTED
        )

    @pytest.mark.asyncio
    async def test_disconnect_component_invalid(self):
        """测试断开组件（无效）"""
        from core.security_system_integrator import SecuritySystemIntegrator

        integrator = SecuritySystemIntegrator()

        result = await integrator.disconnect_component("invalid_integration")

        assert result is False

    @pytest.mark.asyncio
    async def test_report_incident(self):
        """测试报告事件"""
        from core.security_system_integrator import (
            SecurityComponent,
            SecurityIncident,
            SecuritySystemIntegrator,
        )

        integrator = SecuritySystemIntegrator()
        incident = SecurityIncident(
            incident_id="test_incident",
            title="Test Incident",
            severity="high",
            component=SecurityComponent.SECURITY_AUDIT,
        )

        incident_id = await integrator.report_incident(incident)

        assert incident_id == "test_incident"
        assert len(integrator.security_incidents) == 1
        assert integrator.total_incidents == 1
        assert integrator.active_incidents == 1

    @pytest.mark.asyncio
    async def test_resolve_incident(self):
        """测试解决事件"""
        from core.security_system_integrator import (
            SecurityComponent,
            SecurityIncident,
            SecuritySystemIntegrator,
        )

        integrator = SecuritySystemIntegrator()
        incident = SecurityIncident(
            incident_id="test_incident",
            title="Test Incident",
            severity="high",
            component=SecurityComponent.SECURITY_AUDIT,
        )

        await integrator.report_incident(incident)
        result = await integrator.resolve_incident("test_incident", "Resolved")

        assert result is True
        assert integrator.security_incidents[0].status == "resolved"
        assert integrator.active_incidents == 0

    @pytest.mark.asyncio
    async def test_resolve_incident_invalid(self):
        """测试解决事件（无效）"""
        from core.security_system_integrator import SecuritySystemIntegrator

        integrator = SecuritySystemIntegrator()

        result = await integrator.resolve_incident("invalid_incident")

        assert result is False

    @pytest.mark.asyncio
    async def test_run_security_scan(self):
        """测试运行安全扫描"""
        from core.security_system_integrator import (
            SecurityComponent,
            SecurityIntegration,
            SecuritySystemIntegrator,
        )

        integrator = SecuritySystemIntegrator()
        integration = SecurityIntegration(
            integration_id="test_integration",
            component=SecurityComponent.SECURITY_AUDIT,
        )

        await integrator.register_component(integration)
        scan_results = await integrator.run_security_scan()

        assert "scan_id" in scan_results
        assert "components" in scan_results
        assert "started_at" in scan_results
        assert "completed_at" in scan_results

    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        from core.security_system_integrator import (
            SecurityComponent,
            SecurityIntegration,
            SecuritySystemIntegrator,
        )

        integrator = SecuritySystemIntegrator()
        integration = SecurityIntegration(
            integration_id="test_integration",
            component=SecurityComponent.SECURITY_AUDIT,
        )

        await integrator.register_component(integration)
        health_results = await integrator.health_check()

        assert "overall_status" in health_results
        assert "components" in health_results
        assert "checked_at" in health_results

    def test_get_incident(self):
        """测试获取事件"""
        import asyncio

        from core.security_system_integrator import (
            SecurityComponent,
            SecurityIncident,
            SecuritySystemIntegrator,
        )

        integrator = SecuritySystemIntegrator()
        incident = SecurityIncident(
            incident_id="test_incident",
            title="Test Incident",
            severity="high",
            component=SecurityComponent.SECURITY_AUDIT,
        )

        asyncio.run(integrator.report_incident(incident))

        incident_details = integrator.get_incident("test_incident")

        assert incident_details is not None
        assert incident_details["incident_id"] == "test_incident"

    def test_get_incident_invalid(self):
        """测试获取事件（无效）"""
        from core.security_system_integrator import SecuritySystemIntegrator

        integrator = SecuritySystemIntegrator()

        incident_details = integrator.get_incident("invalid_incident")

        assert incident_details is None

    def test_list_incidents(self):
        """测试列出事件"""
        import asyncio

        from core.security_system_integrator import (
            SecurityComponent,
            SecurityIncident,
            SecuritySystemIntegrator,
        )

        integrator = SecuritySystemIntegrator()
        incident = SecurityIncident(
            incident_id="test_incident",
            title="Test Incident",
            severity="high",
            component=SecurityComponent.SECURITY_AUDIT,
        )

        asyncio.run(integrator.report_incident(incident))

        incidents = integrator.list_incidents()

        assert len(incidents) == 1

    def test_list_incidents_with_filter(self):
        """测试列出事件（带过滤器）"""
        import asyncio

        from core.security_system_integrator import (
            SecurityComponent,
            SecurityIncident,
            SecuritySystemIntegrator,
        )

        integrator = SecuritySystemIntegrator()
        incident = SecurityIncident(
            incident_id="test_incident",
            title="Test Incident",
            severity="high",
            component=SecurityComponent.SECURITY_AUDIT,
            status="open",
        )

        asyncio.run(integrator.report_incident(incident))

        incidents = integrator.list_incidents(status="open")

        assert len(incidents) == 1

    def test_register_alert_handler(self):
        """测试注册警报处理器"""
        from core.security_system_integrator import SecuritySystemIntegrator

        integrator = SecuritySystemIntegrator()

        def handler(alert_data):
            pass

        integrator.register_alert_handler(handler)

        assert len(integrator.alert_handlers) == 1

    def test_get_statistics(self):
        """测试获取统计信息"""
        from core.security_system_integrator import SecuritySystemIntegrator

        integrator = SecuritySystemIntegrator()

        stats = integrator.get_statistics()

        assert "total_integrations" in stats
        assert "active_integrations" in stats
        assert "total_incidents" in stats
        assert "active_incidents" in stats


class TestGetSecuritySystemIntegrator:
    """测试获取安全系统集成"""

    def test_get_security_system_integrator(self):
        """测试获取安全系统集成"""
        from core.security_system_integrator import get_security_system_integrator

        integrator = get_security_system_integrator()

        assert integrator is not None
        assert hasattr(integrator, "security_integrations")

    def test_get_security_system_integrator_with_config(self):
        """测试获取安全系统集成（带配置）"""
        from core.security_system_integrator import get_security_system_integrator

        config = {"auto_reconnect": False}
        integrator = get_security_system_integrator(config)

        assert integrator.config == config


class TestSecuritySystemIntegratorIntegration:
    """测试安全系统集成集成"""

    @pytest.mark.asyncio
    async def test_complete_security_workflow(self):
        """测试完整安全工作流"""
        from core.security_system_integrator import (
            SecurityComponent,
            SecurityIncident,
            SecurityIntegration,
            SecuritySystemIntegrator,
        )

        integrator = SecuritySystemIntegrator()

        # Register component
        integration = SecurityIntegration(
            integration_id="test_integration",
            component=SecurityComponent.SECURITY_AUDIT,
        )
        await integrator.register_component(integration)
        assert "test_integration" in integrator.security_integrations

        # Report incident
        incident = SecurityIncident(
            incident_id="test_incident",
            title="Test Incident",
            severity="high",
            component=SecurityComponent.SECURITY_AUDIT,
        )
        await integrator.report_incident(incident)
        assert len(integrator.security_incidents) == 1

        # Resolve incident
        await integrator.resolve_incident("test_incident", "Resolved")
        assert integrator.security_incidents[0].status == "resolved"

        # Get statistics
        stats = integrator.get_statistics()
        assert stats["total_incidents"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
