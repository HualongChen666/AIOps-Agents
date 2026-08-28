# -*- coding: utf-8 -*-
"""
Tests for Enterprise Features - Multi-Tenant Quota and Compliance Management

Tests for multi-tenant resource quota management and compliance management.
"""

import pytest
from datetime import datetime, timedelta
from core.multi_tenant_quota import (
    MultiTenantQuotaManager,
    ResourceType,
    ResourceQuota,
    TenantQuotaProfile,
    quota_manager
)
from core.compliance_manager import (
    ComplianceManager,
    ComplianceStandard,
    ComplianceStatus,
    PolicyType,
    ActionType,
    CompliancePolicy,
    AuditLogEntry,
    ComplianceCheck,
    compliance_manager
)


class TestResourceQuota:
    """Test ResourceQuota class"""
    
    def test_quota_initialization(self):
        """Test quota initialization"""
        quota = ResourceQuota(
            resource_type=ResourceType.API_CALLS,
            limit=1000
        )
        
        assert quota.resource_type == ResourceType.API_CALLS
        assert quota.limit == 1000
        assert quota.used == 0
        assert quota.get_utilization_percent() == 0.0
    
    def test_quota_utilization(self):
        """Test quota utilization calculation"""
        quota = ResourceQuota(
            resource_type=ResourceType.API_CALLS,
            limit=1000
        )
        
        quota.used = 500
        assert quota.get_utilization_percent() == 50.0
        
        quota.used = 1000
        assert quota.get_utilization_percent() == 100.0
    
    def test_quota_exceeded(self):
        """Test quota exceeded check"""
        quota = ResourceQuota(
            resource_type=ResourceType.API_CALLS,
            limit=1000
        )
        
        assert quota.is_exceeded() is False
        
        quota.used = 1000
        assert quota.is_exceeded() is True
    
    def test_quota_near_limit(self):
        """Test quota near limit check"""
        quota = ResourceQuota(
            resource_type=ResourceType.API_CALLS,
            limit=1000
        )
        
        assert quota.is_near_limit() is False
        
        quota.used = 900
        assert quota.is_near_limit() is True
        
        quota.used = 850
        assert quota.is_near_limit(0.8) is True
    
    def test_quota_reset(self):
        """Test quota reset"""
        quota = ResourceQuota(
            resource_type=ResourceType.API_CALLS,
            limit=1000
        )
        
        quota.used = 500
        quota.reset_usage()
        
        assert quota.used == 0


class TestTenantQuotaProfile:
    """Test TenantQuotaProfile class"""
    
    def test_profile_initialization(self):
        """Test profile initialization"""
        profile = TenantQuotaProfile(
            tenant_id="tenant_123",
            plan="standard"
        )
        
        assert profile.tenant_id == "tenant_123"
        assert profile.plan == "standard"
        assert len(profile.quotas) == 0
    
    def test_get_and_set_quota(self):
        """Test getting and setting quotas"""
        profile = TenantQuotaProfile(
            tenant_id="tenant_123",
            plan="standard"
        )
        
        quota = ResourceQuota(
            resource_type=ResourceType.API_CALLS,
            limit=1000
        )
        
        profile.set_quota(ResourceType.API_CALLS, quota)
        retrieved_quota = profile.get_quota(ResourceType.API_CALLS)
        
        assert retrieved_quota is not None
        assert retrieved_quota.limit == 1000
    
    def test_check_quota(self):
        """Test quota checking"""
        profile = TenantQuotaProfile(
            tenant_id="tenant_123",
            plan="standard"
        )
        
        quota = ResourceQuota(
            resource_type=ResourceType.API_CALLS,
            limit=1000
        )
        
        profile.set_quota(ResourceType.API_CALLS, quota)
        
        assert profile.check_quota(ResourceType.API_CALLS, 500) is True
        assert profile.check_quota(ResourceType.API_CALLS, 1000) is True
        assert profile.check_quota(ResourceType.API_CALLS, 1001) is False
    
    def test_consume_quota(self):
        """Test quota consumption"""
        profile = TenantQuotaProfile(
            tenant_id="tenant_123",
            plan="standard"
        )
        
        quota = ResourceQuota(
            resource_type=ResourceType.API_CALLS,
            limit=1000
        )
        
        profile.set_quota(ResourceType.API_CALLS, quota)
        
        assert profile.consume_quota(ResourceType.API_CALLS, 500) is True
        assert profile.quotas[ResourceType.API_CALLS].used == 500
        
        assert profile.consume_quota(ResourceType.API_CALLS, 600) is False
    
    def test_release_quota(self):
        """Test quota release"""
        profile = TenantQuotaProfile(
            tenant_id="tenant_123",
            plan="standard"
        )
        
        quota = ResourceQuota(
            resource_type=ResourceType.API_CALLS,
            limit=1000
        )
        
        profile.set_quota(ResourceType.API_CALLS, quota)
        profile.consume_quota(ResourceType.API_CALLS, 500)
        
        profile.release_quota(ResourceType.API_CALLS, 200)
        assert profile.quotas[ResourceType.API_CALLS].used == 300
        
        profile.release_quota(ResourceType.API_CALLS, 400)
        assert profile.quotas[ResourceType.API_CALLS].used == 0


class TestMultiTenantQuotaManager:
    """Test MultiTenantQuotaManager class"""
    
    def test_manager_initialization(self):
        """Test manager initialization"""
        manager = MultiTenantQuotaManager()
        
        assert len(manager.plan_templates) == 4
        assert "basic" in manager.plan_templates
        assert "standard" in manager.plan_templates
        assert "premium" in manager.plan_templates
        assert "enterprise" in manager.plan_templates
    
    def test_create_tenant_profile(self):
        """Test creating tenant profile"""
        manager = MultiTenantQuotaManager()
        
        profile = manager.create_tenant_profile(
            tenant_id="tenant_123",
            plan="standard"
        )
        
        assert profile.tenant_id == "tenant_123"
        assert profile.plan == "standard"
        assert len(profile.quotas) == 6  # All resource types
    
    def test_create_tenant_profile_invalid_plan(self):
        """Test creating tenant profile with invalid plan"""
        manager = MultiTenantQuotaManager()
        
        with pytest.raises(ValueError):
            manager.create_tenant_profile(
                tenant_id="tenant_123",
                plan="invalid_plan"
            )
    
    def test_create_tenant_profile_custom_quotas(self):
        """Test creating tenant profile with custom quotas"""
        manager = MultiTenantQuotaManager()
        
        custom_quotas = {
            ResourceType.API_CALLS: 50000,
            ResourceType.STORAGE_GB: 100
        }
        
        profile = manager.create_tenant_profile(
            tenant_id="tenant_123",
            plan="standard",
            custom_quotas=custom_quotas
        )
        
        assert profile.quotas[ResourceType.API_CALLS].limit == 50000
        assert profile.quotas[ResourceType.STORAGE_GB].limit == 100
    
    def test_get_tenant_profile(self):
        """Test getting tenant profile"""
        manager = MultiTenantQuotaManager()
        
        manager.create_tenant_profile(
            tenant_id="tenant_123",
            plan="standard"
        )
        
        profile = manager.get_tenant_profile("tenant_123")
        
        assert profile is not None
        assert profile.tenant_id == "tenant_123"
    
    def test_check_tenant_quota(self):
        """Test checking tenant quota"""
        manager = MultiTenantQuotaManager()
        
        manager.create_tenant_profile(
            tenant_id="tenant_123",
            plan="standard"
        )
        
        assert manager.check_tenant_quota("tenant_123", ResourceType.API_CALLS, 1000) is True
        assert manager.check_tenant_quota("tenant_123", ResourceType.API_CALLS, 1000000) is False
    
    def test_consume_tenant_quota(self):
        """Test consuming tenant quota"""
        manager = MultiTenantQuotaManager()
        
        manager.create_tenant_profile(
            tenant_id="tenant_123",
            plan="standard"
        )
        
        assert manager.consume_tenant_quota("tenant_123", ResourceType.API_CALLS, 1000) is True
        assert manager.consume_tenant_quota("tenant_123", ResourceType.API_CALLS, 50000) is False
    
    def test_release_tenant_quota(self):
        """Test releasing tenant quota"""
        manager = MultiTenantQuotaManager()
        
        manager.create_tenant_profile(
            tenant_id="tenant_123",
            plan="standard"
        )
        
        manager.consume_tenant_quota("tenant_123", ResourceType.API_CALLS, 1000)
        manager.release_tenant_quota("tenant_123", ResourceType.API_CALLS, 500)
        
        profile = manager.get_tenant_profile("tenant_123")
        assert profile.quotas[ResourceType.API_CALLS].used == 500
    
    def test_get_tenant_quota_utilization(self):
        """Test getting tenant quota utilization"""
        manager = MultiTenantQuotaManager()
        
        manager.create_tenant_profile(
            tenant_id="tenant_123",
            plan="standard"
        )
        
        manager.consume_tenant_quota("tenant_123", ResourceType.API_CALLS, 25000)
        
        utilization = manager.get_tenant_quota_utilization("tenant_123")
        
        assert "api_calls" in utilization
        assert utilization["api_calls"] == 50.0  # 25000/50000
    
    def test_reset_tenant_quota(self):
        """Test resetting tenant quota"""
        manager = MultiTenantQuotaManager()
        
        manager.create_tenant_profile(
            tenant_id="tenant_123",
            plan="standard"
        )
        
        manager.consume_tenant_quota("tenant_123", ResourceType.API_CALLS, 1000)
        manager.reset_tenant_quota("tenant_123")
        
        profile = manager.get_tenant_profile("tenant_123")
        assert profile.quotas[ResourceType.API_CALLS].used == 0
    
    def test_upgrade_tenant_plan(self):
        """Test upgrading tenant plan"""
        manager = MultiTenantQuotaManager()
        
        manager.create_tenant_profile(
            tenant_id="tenant_123",
            plan="basic"
        )
        
        assert manager.upgrade_tenant_plan("tenant_123", "premium") is True
        
        profile = manager.get_tenant_profile("tenant_123")
        assert profile.plan == "premium"
    
    def test_upgrade_tenant_plan_invalid(self):
        """Test upgrading tenant plan with invalid plan"""
        manager = MultiTenantQuotaManager()
        
        manager.create_tenant_profile(
            tenant_id="tenant_123",
            plan="basic"
        )
        
        assert manager.upgrade_tenant_plan("tenant_123", "invalid") is False
    
    def test_get_quota_alerts(self):
        """Test getting quota alerts"""
        manager = MultiTenantQuotaManager()
        
        manager.create_tenant_profile(
            tenant_id="tenant_123",
            plan="standard"
        )
        
        # Consume quota to near limit
        manager.consume_tenant_quota("tenant_123", ResourceType.API_CALLS, 45000)
        
        alerts = manager.get_quota_alerts(threshold=0.9)
        
        assert len(alerts) > 0
        assert alerts[0]["tenant_id"] == "tenant_123"
        assert alerts[0]["resource_type"] == "api_calls"


class TestComplianceManager:
    """Test ComplianceManager class"""
    
    def test_manager_initialization(self):
        """Test manager initialization"""
        manager = ComplianceManager()
        
        assert len(manager.policies) > 0
        assert "soc2_access_control" in manager.policies
        assert "gdpr_data_protection" in manager.policies
    
    def test_add_policy(self):
        """Test adding a policy"""
        manager = ComplianceManager()
        
        policy = CompliancePolicy(
            id="custom_policy",
            name="Custom Policy",
            standard=ComplianceStandard.GDPR,
            policy_type=PolicyType.ACCESS_CONTROL,
            description="Custom compliance policy",
            requirements=["requirement1", "requirement2"]
        )
        
        assert manager.add_policy(policy) is True
        assert manager.get_policy("custom_policy") is not None
    
    def test_add_duplicate_policy(self):
        """Test adding duplicate policy"""
        manager = ComplianceManager()
        
        policy = CompliancePolicy(
            id="soc2_access_control",  # Duplicate ID
            name="Duplicate Policy",
            standard=ComplianceStandard.SOC2,
            policy_type=PolicyType.ACCESS_CONTROL,
            description="Duplicate policy",
            requirements=[]
        )
        
        assert manager.add_policy(policy) is False
    
    def test_get_policy(self):
        """Test getting a policy"""
        manager = ComplianceManager()
        
        policy = manager.get_policy("soc2_access_control")
        
        assert policy is not None
        assert policy.name == "SOC2 Access Control"
        assert policy.standard == ComplianceStandard.SOC2
    
    def test_get_policies_by_standard(self):
        """Test getting policies by standard"""
        manager = ComplianceManager()
        
        soc2_policies = manager.get_policies_by_standard(ComplianceStandard.SOC2)
        
        assert len(soc2_policies) > 0
        assert all(p.standard == ComplianceStandard.SOC2 for p in soc2_policies)
    
    def test_enable_policy(self):
        """Test enabling a policy"""
        manager = ComplianceManager()
        
        manager.disable_policy("soc2_access_control")
        assert manager.enable_policy("soc2_access_control") is True
        
        policy = manager.get_policy("soc2_access_control")
        assert policy.enabled is True
    
    def test_disable_policy(self):
        """Test disabling a policy"""
        manager = ComplianceManager()
        
        assert manager.disable_policy("soc2_access_control") is True
        
        policy = manager.get_policy("soc2_access_control")
        assert policy.enabled is False
    
    def test_log_audit_event(self):
        """Test logging audit event"""
        manager = ComplianceManager()
        
        entry = manager.log_audit_event(
            tenant_id="tenant_123",
            user_id="user_123",
            action=ActionType.CREATE,
            resource_type="alert",
            resource_id="alert_123",
            outcome="success",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )
        
        assert entry.tenant_id == "tenant_123"
        assert entry.user_id == "user_123"
        assert entry.action == ActionType.CREATE
        assert len(manager.audit_logs) == 1
    
    def test_get_audit_logs(self):
        """Test getting audit logs"""
        manager = ComplianceManager()
        
        manager.log_audit_event(
            tenant_id="tenant_123",
            user_id="user_123",
            action=ActionType.CREATE,
            resource_type="alert",
            resource_id="alert_123",
            outcome="success",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )
        
        logs = manager.get_audit_logs(tenant_id="tenant_123")
        
        assert len(logs) == 1
        assert logs[0].tenant_id == "tenant_123"
    
    def test_get_audit_logs_with_filters(self):
        """Test getting audit logs with filters"""
        manager = ComplianceManager()
        
        manager.log_audit_event(
            tenant_id="tenant_123",
            user_id="user_123",
            action=ActionType.CREATE,
            resource_type="alert",
            resource_id="alert_123",
            outcome="success",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )
        
        manager.log_audit_event(
            tenant_id="tenant_456",
            user_id="user_456",
            action=ActionType.UPDATE,
            resource_type="alert",
            resource_id="alert_456",
            outcome="success",
            ip_address="192.168.1.2",
            user_agent="Mozilla/5.0"
        )
        
        logs = manager.get_audit_logs(tenant_id="tenant_123")
        
        assert len(logs) == 1
        assert logs[0].tenant_id == "tenant_123"
    
    def test_run_compliance_check(self):
        """Test running compliance check"""
        manager = ComplianceManager()
        
        check = manager.run_compliance_check(
            policy_id="soc2_access_control",
            checked_by="system"
        )
        
        assert check.policy_id == "soc2_access_control"
        assert check.checked_by == "system"
        assert check.status in [ComplianceStatus.COMPLIANT, ComplianceStatus.PARTIAL]
    
    def test_run_compliance_check_disabled_policy(self):
        """Test running compliance check on disabled policy"""
        manager = ComplianceManager()
        
        manager.disable_policy("soc2_access_control")
        
        check = manager.run_compliance_check(
            policy_id="soc2_access_control",
            checked_by="system"
        )
        
        assert check.status == ComplianceStatus.EXEMPT
    
    def test_run_compliance_check_invalid_policy(self):
        """Test running compliance check on invalid policy"""
        manager = ComplianceManager()
        
        with pytest.raises(ValueError):
            manager.run_compliance_check(
                policy_id="invalid_policy",
                checked_by="system"
            )
    
    def test_get_compliance_status(self):
        """Test getting compliance status"""
        manager = ComplianceManager()
        
        status = manager.get_compliance_status()
        
        assert "total_policies" in status
        assert "compliant_policies" in status
        assert "compliance_rate" in status
    
    def test_get_compliance_status_by_standard(self):
        """Test getting compliance status by standard"""
        manager = ComplianceManager()
        
        status = manager.get_compliance_status(ComplianceStandard.SOC2)
        
        assert status["standard"] == "soc2"
        assert "total_policies" in status
    
    def test_purge_old_audit_logs(self):
        """Test purging old audit logs"""
        manager = ComplianceManager()
        
        # Add some logs with old timestamps
        from datetime import datetime, timedelta
        old_time = datetime.now() - timedelta(days=10)
        
        for i in range(10):
            entry = manager.log_audit_event(
                tenant_id="tenant_123",
                user_id="user_123",
                action=ActionType.CREATE,
                resource_type="alert",
                resource_id=f"alert_{i}",
                outcome="success",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0"
            )
            # Manually set old timestamp
            entry.timestamp = old_time
        
        original_count = len(manager.audit_logs)
        
        # Purge logs older than 5 days (should remove all)
        manager.purge_old_audit_logs(retention_days=5)
        
        assert len(manager.audit_logs) < original_count


class TestIntegration:
    """Integration tests for enterprise features"""
    
    def test_quota_and_compliance_integration(self):
        """Test integration between quota and compliance management"""
        quota_mgr = MultiTenantQuotaManager()
        compliance_mgr = ComplianceManager()
        
        # Create tenant profile
        quota_mgr.create_tenant_profile(
            tenant_id="tenant_123",
            plan="standard"
        )
        
        # Log audit event for quota consumption
        compliance_mgr.log_audit_event(
            tenant_id="tenant_123",
            user_id="user_123",
            action=ActionType.CREATE,
            resource_type="tenant",
            resource_id="tenant_123",
            outcome="success",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )
        
        # Verify both systems have data
        assert quota_mgr.get_tenant_profile("tenant_123") is not None
        assert len(compliance_mgr.get_audit_logs(tenant_id="tenant_123")) == 1
    
    def test_multi_tenant_isolation(self):
        """Test multi-tenant isolation"""
        quota_mgr = MultiTenantQuotaManager()
        
        # Create two tenants
        quota_mgr.create_tenant_profile(
            tenant_id="tenant_123",
            plan="standard"
        )
        
        quota_mgr.create_tenant_profile(
            tenant_id="tenant_456",
            plan="premium"
        )
        
        # Consume quota for tenant_123
        quota_mgr.consume_tenant_quota("tenant_123", ResourceType.API_CALLS, 1000)
        
        # Verify tenant_456 is not affected
        profile_456 = quota_mgr.get_tenant_profile("tenant_456")
        assert profile_456.quotas[ResourceType.API_CALLS].used == 0