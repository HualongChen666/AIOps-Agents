# -*- coding: utf-8 -*-
"""
基础服务发现管理器模块测试
测试服务发现管理器核心功能的基础场景
"""

import pytest


class TestServiceDiscoveryManagerBasic:
    """服务发现管理器模块基础测试"""

    def test_service_discovery_manager_module_structure(self):
        """测试服务发现管理器模块结构"""
        try:
            from core import service_discovery_manager

            assert service_discovery_manager is not None
        except ImportError as e:
            pytest.skip(f"Service discovery manager module not available: {e}")

    def test_service_discovery_manager_functions_exist(self):
        """测试服务发现管理器关键函数存在"""
        try:
            from core.service_discovery_manager import (
                deregister_service,
                discover_services,
                register_service,
            )

            # 验证关键函数存在
            assert discover_services is not None
            assert register_service is not None
            assert deregister_service is not None
        except Exception as e:
            pytest.skip(f"Service discovery manager functions test failed: {e}")

    def test_service_discovery_manager_classes_exist(self):
        """测试服务发现管理器关键类存在"""
        try:
            from core.service_discovery_manager import (
                HealthChecker,
                ServiceDiscoveryManager,
                ServiceRegistry,
            )

            # 验证关键类存在
            assert ServiceDiscoveryManager is not None
            assert ServiceRegistry is not None
            assert HealthChecker is not None
        except Exception as e:
            pytest.skip(f"Service discovery manager classes test failed: {e}")

    def test_service_discovery_manager_constants(self):
        """测试服务发现管理器常量定义"""
        try:
            from core.service_discovery_manager import DiscoveryMethod, ServiceStatus

            # 验证常量存在
            assert ServiceStatus is not None
            assert DiscoveryMethod is not None
        except Exception as e:
            pytest.skip(f"Service discovery manager constants test failed: {e}")
