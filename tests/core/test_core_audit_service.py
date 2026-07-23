# -*- coding: utf-8 -*-
"""测试审计服务模块"""

import pytest


class TestAuditServiceModule:
    """测试审计服务模块"""

    @pytest.mark.skip(reason="SQLAlchemy metadata conflict")
    def test_audit_service_module_exists(self):
        """测试审计服务模块存在"""
        from core import audit_service

        assert audit_service is not None

    @pytest.mark.skip(reason="SQLAlchemy metadata conflict")
    def test_audit_service_has_functions(self):
        """测试审计服务模块有函数"""
        from core import audit_service

        # 检查模块有函数或类
        assert len(dir(audit_service)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
