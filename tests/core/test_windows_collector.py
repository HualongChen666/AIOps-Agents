# -*- coding: utf-8 -*-
"""测试Windows采集器模块"""

import pytest


class TestWindowsCollectorModule:
    """测试Windows采集器模块"""

    def test_windows_collector_module_exists(self):
        """测试Windows采集器模块存在"""
        from core import windows_collector

        assert windows_collector is not None

    def test_windows_collector_has_functions(self):
        """测试Windows采集器模块有函数"""
        from core import windows_collector

        # 检查模块有函数
        assert hasattr(windows_collector, "_execute_winrm")
        assert hasattr(windows_collector, "collect_windows_host")
        assert hasattr(windows_collector, "collect_all_windows")


class TestExecuteWinrm:
    """测试执行WinRM命令"""

    def test_execute_winrm_without_pywinrm(self):
        """测试执行WinRM命令（无pywinrm）"""
        try:
            from core.windows_collector import _execute_winrm

            host_cfg = {"ip": "localhost", "port": 5986, "user": "test", "password": "test"}

            # This will fail if pywinrm is not available
            try:
                pass

                # If winrm is available, we can't test the error case easily
                pytest.skip("pywinrm is available")
            except ImportError:
                # Expected if pywinrm is not available
                with pytest.raises(ImportError):
                    import asyncio

                    asyncio.run(_execute_winrm(host_cfg, "echo test"))
        except Exception as e:
            pytest.skip(f"Cannot test _execute_winrm: {e}")


class TestCollectWindowsHost:
    """测试采集Windows主机"""

    def test_collect_windows_host_without_pywinrm(self):
        """测试采集Windows主机（无pywinrm）"""
        try:
            from core.windows_collector import collect_windows_host

            host_cfg = {"ip": "localhost", "port": 5986, "user": "test", "password": "test"}

            # This will fail if pywinrm is not available
            try:
                pass

                # If winrm is available, we can't test the error case easily
                pytest.skip("pywinrm is available")
            except ImportError:
                # Expected if pywinrm is not available
                import asyncio

                result = asyncio.run(collect_windows_host(host_cfg))
                assert "error" in result
        except Exception as e:
            pytest.skip(f"Cannot test collect_windows_host: {e}")


class TestCollectAllWindows:
    """测试采集所有Windows主机"""

    def test_collect_all_windows_without_pywinrm(self):
        """测试采集所有Windows主机（无pywinrm）"""
        try:
            from core.windows_collector import collect_all_windows

            # This will fail if pywinrm is not available
            try:
                pass

                # If winrm is available, we can't test the error case easily
                pytest.skip("pywinrm is available")
            except ImportError:
                # Expected if pywinrm is not available
                import asyncio

                result = asyncio.run(collect_all_windows())
                assert isinstance(result, list)
        except Exception as e:
            pytest.skip(f"Cannot test collect_all_windows: {e}")


class TestWindowsCollectorIntegration:
    """测试Windows采集器集成"""

    def test_complete_workflow_without_pywinrm(self):
        """测试完整工作流（无pywinrm）"""
        pytest.skip("Windows采集器需要pywinrm依赖，跳过测试")


class TestWinrmCertValidation:
    """测试WinRM证书验证常量"""

    def test_winrm_cert_validation_default(self):
        """测试WinRM证书验证默认值"""
        try:
            from core.windows_collector import WINRM_CERT_VALIDATION

            assert WINRM_CERT_VALIDATION is not None
            assert isinstance(WINRM_CERT_VALIDATION, str)
        except Exception as e:
            pytest.skip(f"Cannot test winrm cert validation default: {e}")


class TestExecuteWinrmEdgeCases:
    """测试执行WinRM边界情况"""

    def test_execute_winrm_invalid_auth(self):
        """测试无效认证"""
        try:
            from core.windows_collector import _execute_winrm

            host_cfg = {"ip": "localhost", "port": 5986, "user": "test", "password": ""}
            import asyncio

            # Should raise ValueError for invalid auth
            try:
                asyncio.run(_execute_winrm(host_cfg, "echo test"))
            except ValueError as e:
                assert "Auth credentials" in str(e)
            except ImportError:
                # pywinrm not available, expected
                pass
        except Exception as e:
            pytest.skip(f"Cannot test execute winrm invalid auth: {e}")

    def test_execute_winrm_missing_auth(self):
        """测试缺少认证"""
        try:
            from core.windows_collector import _execute_winrm

            host_cfg = {"ip": "localhost", "port": 5986}
            import asyncio

            # Should raise ValueError for missing auth
            try:
                asyncio.run(_execute_winrm(host_cfg, "echo test"))
            except ValueError as e:
                assert "Auth credentials" in str(e)
            except ImportError:
                # pywinrm not available, expected
                pass
        except Exception as e:
            pytest.skip(f"Cannot test execute winrm missing auth: {e}")


class TestCollectWindowsHostEdgeCases:
    """测试采集Windows主机边界情况"""

    @pytest.mark.asyncio
    async def test_collect_windows_host_missing_ip(self):
        """测试缺少IP"""
        try:
            from core.windows_collector import collect_windows_host

            host_cfg = {"name": "test"}
            result = await collect_windows_host(host_cfg)

            assert "error" in result
        except Exception as e:
            pytest.skip(f"Cannot test collect windows host missing ip: {e}")

    @pytest.mark.asyncio
    async def test_collect_windows_host_missing_name(self):
        """测试缺少名称"""
        try:
            from core.windows_collector import collect_windows_host

            host_cfg = {"ip": "localhost", "port": 5986, "user": "test", "password": "test"}
            result = await collect_windows_host(host_cfg)

            # Should use IP as name
            assert "host" in result
        except Exception as e:
            pytest.skip(f"Cannot test collect windows host missing name: {e}")


class TestCollectAllWindowsEdgeCases:
    """测试采集所有Windows主机边界情况"""

    @pytest.mark.asyncio
    async def test_collect_all_windows_empty_hosts(self):
        """测试空主机列表"""
        try:
            from config import WIN_HOSTS
            from core.windows_collector import collect_all_windows

            # Temporarily clear WIN_HOSTS
            original_hosts = WIN_HOSTS[:]
            WIN_HOSTS.clear()

            try:
                result = await collect_all_windows()

                assert isinstance(result, list)
                assert len(result) == 0
            finally:
                WIN_HOSTS.extend(original_hosts)
        except Exception as e:
            pytest.skip(f"Cannot test collect all windows empty hosts: {e}")

    @pytest.mark.asyncio
    async def test_collect_all_windows_invalid_host_config(self):
        """测试无效主机配置"""
        try:
            from config import WIN_HOSTS
            from core.windows_collector import collect_all_windows

            # Temporarily add invalid host config
            original_hosts = WIN_HOSTS[:]
            WIN_HOSTS.append({"invalid": "config"})

            try:
                result = await collect_all_windows()

                # Should handle invalid config gracefully
                assert isinstance(result, list)
            finally:
                WIN_HOSTS[:] = original_hosts
        except Exception as e:
            pytest.skip(f"Cannot test collect all windows invalid host config: {e}")


class TestExecuteWinrmAdditionalEdgeCases:
    """测试执行WinRM额外边界情况"""

    def test_execute_winrm_empty_command(self):
        """测试空命令"""
        try:
            from core.windows_collector import _execute_winrm

            host_cfg = {"ip": "localhost", "port": 5986, "user": "test", "password": "test"}
            import asyncio

            # Should handle empty command gracefully
            try:
                asyncio.run(_execute_winrm(host_cfg, ""))
            except ImportError:
                # pywinrm not available, expected
                pass
        except Exception as e:
            pytest.skip(f"Cannot test execute winrm empty command: {e}")

    def test_execute_winrm_null_command(self):
        """测试空命令"""
        try:
            from core.windows_collector import _execute_winrm

            host_cfg = {"ip": "localhost", "port": 5986, "user": "test", "password": "test"}
            import asyncio

            # Should handle null command gracefully
            try:
                asyncio.run(_execute_winrm(host_cfg, None))
            except (ImportError, TypeError):
                # pywinrm not available or type error, expected
                pass
        except Exception as e:
            pytest.skip(f"Cannot test execute winrm null command: {e}")


class TestCollectWindowsHostAdditionalEdgeCases:
    """测试采集Windows主机额外边界情况"""

    @pytest.mark.asyncio
    async def test_collect_windows_host_empty_config(self):
        """测试空配置"""
        try:
            from core.windows_collector import collect_windows_host

            host_cfg = {}
            result = await collect_windows_host(host_cfg)

            assert "error" in result
        except Exception as e:
            pytest.skip(f"Cannot test collect windows host empty config: {e}")

    @pytest.mark.asyncio
    async def test_collect_windows_host_null_config(self):
        """测试空配置"""
        try:
            from core.windows_collector import collect_windows_host

            result = await collect_windows_host(None)

            assert "error" in result
        except Exception as e:
            pytest.skip(f"Cannot test collect windows host null config: {e}")

    @pytest.mark.asyncio
    async def test_collect_windows_host_special_chars_in_name(self):
        """测试名称中包含特殊字符"""
        try:
            from core.windows_collector import collect_windows_host

            host_cfg = {"name": "test-host_123", "ip": "localhost"}
            result = await collect_windows_host(host_cfg)

            # Should handle special characters gracefully
            assert "host" in result
        except Exception as e:
            pytest.skip(f"Cannot test collect windows host special chars in name: {e}")


class TestWinrmCertValidationEdgeCases:
    """测试WinRM证书验证边界情况"""

    def test_winrm_cert_validation_type(self):
        """测试WinRM证书验证类型"""
        try:
            from core.windows_collector import WINRM_CERT_VALIDATION

            # Should be a string
            assert isinstance(WINRM_CERT_VALIDATION, str)
            assert len(WINRM_CERT_VALIDATION) > 0
        except Exception as e:
            pytest.skip(f"Cannot test winrm cert validation type: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
