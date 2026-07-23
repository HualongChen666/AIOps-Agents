# -*- coding: utf-8 -*-
"""测试告警服务模块"""

import pytest


class TestAlertServiceModule:
    """测试告警服务模块"""

    @pytest.mark.skip(reason="SQLAlchemy metadata conflict")
    def test_alert_service_module_exists(self):
        """测试告警服务模块存在"""
        from core import alert_service

        assert alert_service is not None

    @pytest.mark.skip(reason="SQLAlchemy metadata conflict")
    def test_alert_service_has_functions(self):
        """测试告警服务模块有函数"""
        from core import alert_service

        # 检查模块有函数或类
        assert len(dir(alert_service)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
