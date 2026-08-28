# -*- coding: utf-8 -*-
"""
Multi-Tenant Resource Quota Management

This module provides resource quota management for multi-tenant deployments,
ensuring fair resource allocation and preventing resource exhaustion.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from loguru import logger


class ResourceType(Enum):
    """Resource type enumeration"""
    
    API_CALLS = "api_calls"
    STORAGE_GB = "storage_gb"
    CONCURRENT_USERS = "concurrent_users"
    ALERTS_PER_DAY = "alerts_per_day"
    WORKFLOWS_PER_DAY = "workflows_per_day"
    METRICS_PER_DAY = "metrics_per_day"


@dataclass
class ResourceQuota:
    """Resource quota definition"""
    
    resource_type: ResourceType
    limit: int
    used: int = 0
    period: timedelta = timedelta(days=1)
    soft_limit: Optional[int] = None  # Soft limit for warning
    hard_limit: Optional[int] = None  # Hard limit for blocking
    
    def get_utilization_percent(self) -> float:
        """Get current utilization percentage"""
        if self.limit == 0:
            return 0.0
        return (self.used / self.limit) * 100
    
    def is_exceeded(self) -> bool:
        """Check if quota is exceeded"""
        return self.used >= self.limit
    
    def is_near_limit(self, threshold: float = 0.9) -> bool:
        """Check if quota is near limit"""
        return self.get_utilization_percent() >= (threshold * 100)
    
    def reset_usage(self):
        """Reset usage counter"""
        self.used = 0


@dataclass
class TenantQuotaProfile:
    """Tenant quota profile"""
    
    tenant_id: str
    plan: str  # basic, standard, premium, enterprise
    quotas: Dict[ResourceType, ResourceQuota] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def get_quota(self, resource_type: ResourceType) -> Optional[ResourceQuota]:
        """Get quota for a specific resource type"""
        return self.quotas.get(resource_type)
    
    def set_quota(self, resource_type: ResourceType, quota: ResourceQuota):
        """Set quota for a specific resource type"""
        self.quotas[resource_type] = quota
        self.updated_at = datetime.now()
    
    def check_quota(self, resource_type: ResourceType, amount: int = 1) -> bool:
        """Check if quota allows the requested amount"""
        quota = self.get_quota(resource_type)
        if not quota:
            return True  # No quota defined, allow by default
        
        if quota.used + amount > quota.limit:
            logger.warning(
                f"Tenant {self.tenant_id} quota exceeded for {resource_type.value}: "
                f"{quota.used + amount}/{quota.limit}"
            )
            return False
        
        return True
    
    def consume_quota(self, resource_type: ResourceType, amount: int = 1) -> bool:
        """Consume quota for a resource"""
        quota = self.get_quota(resource_type)
        if not quota:
            return True  # No quota defined, allow by default
        
        if not self.check_quota(resource_type, amount):
            return False
        
        quota.used += amount
        return True
    
    def release_quota(self, resource_type: ResourceType, amount: int = 1):
        """Release quota for a resource"""
        quota = self.get_quota(resource_type)
        if not quota:
            return  # No quota defined, nothing to release
        
        quota.used = max(0, quota.used - amount)


class MultiTenantQuotaManager:
    """Multi-tenant quota manager"""
    
    def __init__(self):
        """Initialize quota manager"""
        self.tenant_profiles: Dict[str, TenantQuotaProfile] = {}
        self.plan_templates: Dict[str, Dict[ResourceType, int]] = {}
        
        # Initialize plan templates
        self._initialize_plan_templates()
    
    def _initialize_plan_templates(self):
        """Initialize quota templates for different plans"""
        self.plan_templates = {
            "basic": {
                ResourceType.API_CALLS: 10000,
                ResourceType.STORAGE_GB: 10,
                ResourceType.CONCURRENT_USERS: 5,
                ResourceType.ALERTS_PER_DAY: 1000,
                ResourceType.WORKFLOWS_PER_DAY: 100,
                ResourceType.METRICS_PER_DAY: 10000,
            },
            "standard": {
                ResourceType.API_CALLS: 50000,
                ResourceType.STORAGE_GB: 50,
                ResourceType.CONCURRENT_USERS: 20,
                ResourceType.ALERTS_PER_DAY: 5000,
                ResourceType.WORKFLOWS_PER_DAY: 500,
                ResourceType.METRICS_PER_DAY: 50000,
            },
            "premium": {
                ResourceType.API_CALLS: 200000,
                ResourceType.STORAGE_GB: 200,
                ResourceType.CONCURRENT_USERS: 100,
                ResourceType.ALERTS_PER_DAY: 20000,
                ResourceType.WORKFLOWS_PER_DAY: 2000,
                ResourceType.METRICS_PER_DAY: 200000,
            },
            "enterprise": {
                ResourceType.API_CALLS: 1000000,
                ResourceType.STORAGE_GB: 1000,
                ResourceType.CONCURRENT_USERS: 500,
                ResourceType.ALERTS_PER_DAY: 100000,
                ResourceType.WORKFLOWS_PER_DAY: 10000,
                ResourceType.METRICS_PER_DAY: 1000000,
            },
        }
    
    def create_tenant_profile(
        self,
        tenant_id: str,
        plan: str = "standard",
        custom_quotas: Optional[Dict[ResourceType, int]] = None
    ) -> TenantQuotaProfile:
        """Create tenant quota profile"""
        if plan not in self.plan_templates:
            raise ValueError(f"Invalid plan: {plan}")
        
        template = self.plan_templates[plan]
        quotas = {}
        
        for resource_type, limit in template.items():
            quotas[resource_type] = ResourceQuota(
                resource_type=resource_type,
                limit=limit,
                soft_limit=int(limit * 0.8),
                hard_limit=int(limit * 1.1)
            )
        
        # Apply custom quotas if provided
        if custom_quotas:
            for resource_type, limit in custom_quotas.items():
                if resource_type in quotas:
                    quotas[resource_type].limit = limit
                    quotas[resource_type].soft_limit = int(limit * 0.8)
                    quotas[resource_type].hard_limit = int(limit * 1.1)
        
        profile = TenantQuotaProfile(
            tenant_id=tenant_id,
            plan=plan,
            quotas=quotas
        )
        
        self.tenant_profiles[tenant_id] = profile
        logger.info(f"Created quota profile for tenant {tenant_id} with plan {plan}")
        
        return profile
    
    def get_tenant_profile(self, tenant_id: str) -> Optional[TenantQuotaProfile]:
        """Get tenant quota profile"""
        return self.tenant_profiles.get(tenant_id)
    
    def check_tenant_quota(
        self,
        tenant_id: str,
        resource_type: ResourceType,
        amount: int = 1
    ) -> bool:
        """Check if tenant has sufficient quota"""
        profile = self.get_tenant_profile(tenant_id)
        if not profile:
            return True  # No profile, allow by default
        
        return profile.check_quota(resource_type, amount)
    
    def consume_tenant_quota(
        self,
        tenant_id: str,
        resource_type: ResourceType,
        amount: int = 1
    ) -> bool:
        """Consume tenant quota"""
        profile = self.get_tenant_profile(tenant_id)
        if not profile:
            return True  # No profile, allow by default
        
        return profile.consume_quota(resource_type, amount)
    
    def release_tenant_quota(
        self,
        tenant_id: str,
        resource_type: ResourceType,
        amount: int = 1
    ):
        """Release tenant quota"""
        profile = self.get_tenant_profile(tenant_id)
        if not profile:
            return  # No profile, nothing to release
        
        profile.release_quota(resource_type, amount)
    
    def get_tenant_quota_utilization(self, tenant_id: str) -> Dict[str, float]:
        """Get tenant quota utilization percentages"""
        profile = self.get_tenant_profile(tenant_id)
        if not profile:
            return {}
        
        utilization = {}
        for resource_type, quota in profile.quotas.items():
            utilization[resource_type.value] = quota.get_utilization_percent()
        
        return utilization
    
    def reset_tenant_quota(self, tenant_id: str, resource_type: Optional[ResourceType] = None):
        """Reset tenant quota usage"""
        profile = self.get_tenant_profile(tenant_id)
        if not profile:
            return
        
        if resource_type:
            quota = profile.get_quota(resource_type)
            if quota:
                quota.reset_usage()
        else:
            for quota in profile.quotas.values():
                quota.reset_usage()
        
        logger.info(f"Reset quota for tenant {tenant_id}")
    
    def upgrade_tenant_plan(self, tenant_id: str, new_plan: str) -> bool:
        """Upgrade tenant to a higher plan"""
        if new_plan not in self.plan_templates:
            logger.error(f"Invalid plan: {new_plan}")
            return False
        
        profile = self.get_tenant_profile(tenant_id)
        if not profile:
            logger.error(f"Tenant profile not found: {tenant_id}")
            return False
        
        # Create new profile with new plan
        new_profile = self.create_tenant_profile(tenant_id, new_plan)
        
        logger.info(f"Upgraded tenant {tenant_id} from {profile.plan} to {new_plan}")
        return True
    
    def get_quota_alerts(self, threshold: float = 0.9) -> List[Dict[str, Any]]:
        """Get tenants approaching quota limits"""
        alerts = []
        
        for tenant_id, profile in self.tenant_profiles.items():
            for resource_type, quota in profile.quotas.items():
                if quota.is_near_limit(threshold):
                    alerts.append({
                        "tenant_id": tenant_id,
                        "resource_type": resource_type.value,
                        "utilization": quota.get_utilization_percent(),
                        "used": quota.used,
                        "limit": quota.limit,
                        "plan": profile.plan
                    })
        
        return alerts


# Global quota manager instance
quota_manager = MultiTenantQuotaManager()