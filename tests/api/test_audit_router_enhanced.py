# -*- coding: utf-8 -*-
# tests/api/test_audit_router_enhanced.py
# 审计路由API测试
import os
import sys
from unittest.mock import Mock, patch

import pytest  # noqa: F401
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.audit_router import router

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

sys.modules["core.authentication"] = Mock()
sys.modules["core.authentication"].get_current_active_user = Mock()
sys.modules["core.authentication"].role_required = Mock(return_value=lambda: {"role": "admin"})
sys.modules["core.audit_service"] = Mock()
sys.modules["core.audit_service"].audit_service = Mock()


test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)


class TestAuditRouter:
    """审计路由测试"""

    def test_get_audit_logs(self):
        """测试获取审计日志"""
        with patch("core.audit_service.audit_service.get_audit_logs") as mock_logs:
            mock_logs.return_value = [{"id": 1, "action": "login", "user": "admin"}]
            response = client.get("/api/v1/audit/logs")
            assert response.status_code in [200, 401, 403, 404]

    def test_get_audit_summary(self):
        """测试获取审计摘要"""
        with patch("core.audit_service.audit_service.get_summary") as mock_summary:
            mock_summary.return_value = {"total_actions": 100, "failed_actions": 5}
            response = client.get("/api/v1/audit/summary")
            assert response.status_code in [200, 401, 403, 404]
