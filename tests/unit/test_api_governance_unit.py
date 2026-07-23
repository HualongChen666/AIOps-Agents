# -*- coding: utf-8 -*-
# tests/unit/test_api_governance_unit.py
# API Governance模块单元测试
from datetime import datetime, timezone

import pytest  # noqa: F401


class TestAPIStatus:
    """测试API状态枚举"""

    def test_api_status_values(self):
        """测试API状态枚举值"""
        from core.api_governance import APIStatus

        assert APIStatus.ACTIVE.value == "active"
        assert APIStatus.DEPRECATED.value == "deprecated"
        assert APIStatus.SUNSET.value == "sunset"
        assert APIStatus.RETIRED.value == "retired"


class TestAPIEndpoint:
    """测试API端点"""

    def test_api_endpoint_creation(self):
        """测试API端点创建"""
        from core.api_governance import APIEndpoint, APIStatus

        endpoint = APIEndpoint(path="/api/v1/users", method="GET", version="v1")

        assert endpoint.path == "/api/v1/users"
        assert endpoint.method == "GET"
        assert endpoint.version == "v1"
        assert endpoint.status == APIStatus.ACTIVE
        assert endpoint.deprecation_date is None
        assert endpoint.sunset_date is None
        assert endpoint.retirement_date is None
        assert endpoint.replacement_path is None
        assert endpoint.description == ""
        assert endpoint.usage_count == 0
        assert endpoint.last_used is None

    def test_api_endpoint_with_dates(self):
        """测试带日期的API端点"""
        from core.api_governance import APIEndpoint, APIStatus

        endpoint = APIEndpoint(
            path="/api/v1/users",
            method="GET",
            version="v1",
            status=APIStatus.DEPRECATED,
            deprecation_date=datetime.now(timezone.utc),
            sunset_date=datetime.now(timezone.utc),
            retirement_date=datetime.now(timezone.utc),
            replacement_path="/api/v2/users",
            description="User API",
            usage_count=100,
        )

        assert endpoint.status == APIStatus.DEPRECATED
        assert endpoint.deprecation_date is not None
        assert endpoint.sunset_date is not None
        assert endpoint.retirement_date is not None
        assert endpoint.replacement_path == "/api/v2/users"
        assert endpoint.description == "User API"
        assert endpoint.usage_count == 100


class TestAPIVersion:
    """测试API版本"""

    def test_api_version_creation(self):
        """测试API版本创建"""
        from core.api_governance import APIStatus, APIVersion

        version = APIVersion(
            version="v1", status=APIStatus.ACTIVE, release_date=datetime.now(timezone.utc)
        )

        assert version.version == "v1"
        assert version.status == APIStatus.ACTIVE
        assert version.release_date is not None
        assert version.deprecation_date is None
        assert version.sunset_date is None
        assert version.retirement_date is None


class TestAPIGovernance:
    """测试API治理"""

    def test_api_governance_initialization(self):
        """测试API治理初始化"""
        from core.api_governance import APIGovernance

        governance = APIGovernance()

        assert governance is not None

    def test_register_endpoint(self):
        """测试注册API端点"""
        from core.api_governance import APIEndpoint, APIGovernance, APIStatus  # noqa: F401

        governance = APIGovernance()
        endpoint = APIEndpoint(path="/api/v1/users", method="GET", version="v1")

        governance.register_endpoint(endpoint)

        assert "GET:/api/v1/users" in governance._endpoints

    def test_deprecate_endpoint(self):
        """测试弃用API端点"""
        from datetime import datetime, timedelta, timezone

        from core.api_governance import APIEndpoint, APIGovernance, APIStatus

        governance = APIGovernance()
        endpoint = APIEndpoint(path="/api/v1/users", method="GET", version="v1")

        governance.register_endpoint(endpoint)

        sunset_date = datetime.now(timezone.utc) + timedelta(days=30)
        result = governance.deprecate_endpoint(
            path="/api/v1/users",
            method="GET",
            sunset_date=sunset_date,
            replacement_path="/api/v2/users",
        )

        assert result["status"] == "success"
        assert endpoint.status == APIStatus.DEPRECATED

    def test_deprecate_endpoint_not_found(self):
        """测试弃用不存在的API端点"""
        from datetime import datetime, timedelta, timezone

        from core.api_governance import APIGovernance

        governance = APIGovernance()

        sunset_date = datetime.now(timezone.utc) + timedelta(days=30)
        result = governance.deprecate_endpoint(
            path="/api/v1/users", method="GET", sunset_date=sunset_date
        )

        assert result["status"] == "error"
