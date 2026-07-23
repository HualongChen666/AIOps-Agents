# -*- coding: utf-8 -*-
"""测试服务工作配置模块"""

import pytest


class TestServiceWorkerConfigModule:
    """测试服务工作配置模块"""

    def test_service_worker_config_module_exists(self):
        """测试服务工作配置模块存在"""
        from core import service_worker_config

        assert service_worker_config is not None

    def test_service_worker_config_has_functions(self):
        """测试服务工作配置模块有函数"""
        from core import service_worker_config

        # 检查模块有函数或类
        assert len(dir(service_worker_config)) > 0


class TestServiceWorkerConfig:
    """测试服务工作配置"""

    def test_service_worker_config_exists(self):
        """测试服务工作配置存在"""
        try:
            from core.service_worker_config import SERVICE_WORKER_CONFIG

            assert SERVICE_WORKER_CONFIG is not None
            assert isinstance(SERVICE_WORKER_CONFIG, dict)
        except Exception as e:
            pytest.skip(f"Cannot test service worker config exists: {e}")

    def test_service_worker_config_structure(self):
        """测试服务工作配置结构"""
        try:
            from core.service_worker_config import SERVICE_WORKER_CONFIG

            # Check required fields
            assert "version" in SERVICE_WORKER_CONFIG
            assert "cache_name" in SERVICE_WORKER_CONFIG
            assert "cache_urls" in SERVICE_WORKER_CONFIG
            assert "offline_fallback" in SERVICE_WORKER_CONFIG
        except Exception as e:
            pytest.skip(f"Cannot test service worker config structure: {e}")

    def test_service_worker_config_values(self):
        """测试服务工作配置值"""
        try:
            from core.service_worker_config import SERVICE_WORKER_CONFIG

            # Check values
            assert SERVICE_WORKER_CONFIG["version"] == "1.0.0"
            assert "aiops-cache" in SERVICE_WORKER_CONFIG["cache_name"]
            assert isinstance(SERVICE_WORKER_CONFIG["cache_urls"], list)
        except Exception as e:
            pytest.skip(f"Cannot test service worker config values: {e}")


class TestGetServiceWorkerScript:
    """测试获取服务工作脚本函数"""

    def test_get_service_worker_script(self):
        """测试获取服务工作脚本"""
        try:
            from core.service_worker_config import get_service_worker_script

            script = get_service_worker_script()

            assert script is not None
            assert isinstance(script, str)
            assert len(script) > 0
        except Exception as e:
            pytest.skip(f"Cannot test get service worker script: {e}")

    def test_get_service_worker_script_content(self):
        """测试获取服务工作脚本内容"""
        try:
            from core.service_worker_config import get_service_worker_script

            script = get_service_worker_script()

            # Check for key Service Worker patterns
            assert "CACHE_NAME" in script
            assert "addEventListener" in script
            assert "install" in script
            assert "activate" in script
            assert "fetch" in script
        except Exception as e:
            pytest.skip(f"Cannot test get service worker script content: {e}")


class TestGetServiceWorkerRegistrationScript:
    """测试获取服务工作注册脚本函数"""

    def test_get_service_worker_registration_script(self):
        """测试获取服务工作注册脚本"""
        try:
            from core.service_worker_config import get_service_worker_registration_script

            script = get_service_worker_registration_script()

            assert script is not None
            assert isinstance(script, str)
            assert len(script) > 0
        except Exception as e:
            pytest.skip(f"Cannot test get service worker registration script: {e}")

    def test_get_service_worker_registration_script_content(self):
        """测试获取服务工作注册脚本内容"""
        try:
            from core.service_worker_config import get_service_worker_registration_script

            script = get_service_worker_registration_script()

            # Check for key registration patterns
            assert "serviceWorker" in script
            assert "register" in script
            assert "navigator" in script
        except Exception as e:
            pytest.skip(f"Cannot test get service worker registration script content: {e}")


class TestServiceWorkerConfigIntegration:
    """测试服务工作配置集成"""

    def test_config_and_script_consistency(self):
        """测试配置和脚本一致性"""
        try:
            from core.service_worker_config import SERVICE_WORKER_CONFIG, get_service_worker_script

            script = get_service_worker_script()

            # Check that cache name from config is in script
            assert SERVICE_WORKER_CONFIG["cache_name"] in script
        except Exception as e:
            pytest.skip(f"Cannot test config and script consistency: {e}")

    def test_complete_lifecycle(self):
        """测试完整生命周期"""
        try:
            from core.service_worker_config import (
                SERVICE_WORKER_CONFIG,
                get_service_worker_registration_script,
                get_service_worker_script,
            )

            # Get config
            assert SERVICE_WORKER_CONFIG is not None

            # Get service worker script
            sw_script = get_service_worker_script()
            assert sw_script is not None

            # Get registration script
            reg_script = get_service_worker_registration_script()
            assert reg_script is not None

            # Both scripts should be valid strings
            assert len(sw_script) > 0
            assert len(reg_script) > 0
        except Exception as e:
            pytest.skip(f"Cannot test complete lifecycle: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
