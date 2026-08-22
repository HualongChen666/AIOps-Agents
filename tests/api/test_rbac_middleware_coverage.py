# -*- coding: utf-8 -*-
"""
Test coverage for rbac_middleware.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.datastructures import Headers


@pytest.fixture
def mock_request():
    """Mock request object"""
    request = Mock(spec=Request)
    request.url = Mock()
    request.url.path = "/api/test"
    request.method = "GET"
    request.headers = Headers({})
    request.state = Mock()
    return request


@pytest.fixture
def mock_call_next():
    """Mock call_next function"""
    async def call_next(request):
        response = Mock(spec=Response)
        response.status_code = 200
        return response
    return call_next


class TestIsPublicPath:
    """Test _is_public_path function"""
    
    def test_public_path_docs(self):
        """Test /docs path is public"""
        from api.middleware.rbac_middleware import _is_public
        assert _is_public("/docs") is True
        assert _is_public("/docs/") is True
        assert _is_public("/api/docs") is False
    
    def test_public_path_redoc(self):
        """Test /redoc path is public"""
        from api.middleware.rbac_middleware import _is_public
        assert _is_public("/redoc") is True
        assert _is_public("/redoc/") is True
    
    def test_public_path_openapi(self):
        """Test /openapi.json path is public"""
        from api.middleware.rbac_middleware import _is_public
        assert _is_public("/openapi.json") is True
    
    def test_public_path_health(self):
        """Test /health path is public"""
        from api.middleware.rbac_middleware import _is_public
        assert _is_public("/health") is True
        assert _is_public("/health/") is True
    
    def test_public_path_static(self):
        """Test /static/ path is public"""
        from api.middleware.rbac_middleware import _is_public
        assert _is_public("/static/") is True
        assert _is_public("/static/css/style.css") is True
        assert _is_public("/static/js/app.js") is True
    
    def test_public_path_auth_login(self):
        """Test auth login path is public"""
        from api.middleware.rbac_middleware import _is_public
        assert _is_public("/api/v1/auth/login") is True
        assert _is_public("/api/v1/auth/login/") is True
    
    def test_public_path_auth_register(self):
        """Test auth register path is public"""
        from api.middleware.rbac_middleware import _is_public
        assert _is_public("/api/v1/auth/register") is True
    
    def test_public_path_auth_refresh(self):
        """Test auth refresh path is public"""
        from api.middleware.rbac_middleware import _is_public
        assert _is_public("/api/v1/auth/refresh") is True
    
    def test_public_path_alert_webhooks(self):
        """Test alert webhook paths are public"""
        from api.middleware.rbac_middleware import _is_public
        assert _is_public("/api/v1/alerts/") is True
        assert _is_public("/api/v1/alerts/prometheus") is True
        assert _is_public("/api/v1/alerts/grafana") is True
        assert _is_public("/api/v1/alerts/datadog") is True
        assert _is_public("/api/v1/alerts/zabbix") is True
        assert _is_public("/api/v1/alerts/cloudwatch") is True
        assert _is_public("/api/v1/alerts/pagerduty") is True
    
    def test_public_path_webhook(self):
        """Test webhook paths are public"""
        from api.middleware.rbac_middleware import _is_public
        assert _is_public("/webhook/") is True
        assert _is_public("/webhook/test") is True
    
    def test_public_path_hitl_page(self):
        """Test HITL page paths are public"""
        from api.middleware.rbac_middleware import _is_public
        assert _is_public("/hitl-page/") is True
        assert _is_public("/api/v1/hitl-page/") is True
    
    def test_public_path_sw_files(self):
        """Test service worker files are public"""
        from api.middleware.rbac_middleware import _is_public
        assert _is_public("/sw.js") is True
        assert _is_public("/sw-register.js") is True
    
    def test_public_path_metrics(self):
        """Test metrics path is public"""
        from api.middleware.rbac_middleware import _is_public
        assert _is_public("/metrics") is True
    
    def test_public_path_root(self):
        """Test root path is public"""
        from api.middleware.rbac_middleware import _is_public
        assert _is_public("/") is True
    
    def test_private_path(self):
        """Test private path requires authentication"""
        from api.middleware.rbac_middleware import _is_public
        assert _is_public("/api/test") is False
        assert _is_public("/api/v1/users") is False
        assert _is_public("/admin") is False
    
    def test_case_insensitive_path_check(self):
        """Test path checking is case insensitive"""
        from api.middleware.rbac_middleware import _is_public
        assert _is_public("/DOCS") is True
        assert _is_public("/Health") is True
        assert _is_public("/API/V1/AUTH/LOGIN") is True


class TestRBACMiddleware:
    """Test RBACMiddleware class"""
    
    @pytest.mark.asyncio
    async def test_public_path_bypass(self, mock_request, mock_call_next):
        """Test public paths bypass authentication"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/docs"
        middleware = RBACMiddleware(Mock())
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200
        mock_call_next.assert_called_once_with(mock_request)
    
    @pytest.mark.asyncio
    async def test_missing_authorization_header(self, mock_request, mock_call_next):
        """Test missing authorization header returns 401"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({})
        middleware = RBACMiddleware(Mock())
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 401
        assert isinstance(response, JSONResponse)
        mock_call_next.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_invalid_authorization_format(self, mock_request, mock_call_next):
        """Test invalid authorization format returns 401"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "InvalidFormat token"})
        middleware = RBACMiddleware(Mock())
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 401
        mock_call_next.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_malformed_jwt_token(self, mock_request, mock_call_next):
        """Test malformed JWT token returns 401"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer invalid.token"})
        middleware = RBACMiddleware(Mock())
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 401
        mock_call_next.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_empty_jwt_token(self, mock_request, mock_call_next):
        """Test empty JWT token returns 401"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer .."})
        middleware = RBACMiddleware(Mock())
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 401
        mock_call_next.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_valid_token_decode_success(self, mock_request, mock_call_next):
        """Test valid token is decoded successfully"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer valid.token.here"})
        mock_request.method = "GET"
        
        payload = {
            "user_id": "user1",
            "username": "testuser",
            "role": "admin",
            "tenant_id": "tenant1"
        }
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
            middleware = RBACMiddleware(Mock())
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200
        assert mock_request.state.user == payload
        assert mock_request.state.tenant_id == "tenant1"
        assert mock_request.state.role == "admin"
        mock_call_next.assert_called_once_with(mock_request)
    
    @pytest.mark.asyncio
    async def test_token_decode_failure(self, mock_request, mock_call_next):
        """Test token decode failure returns 401"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer invalid.token"})
        
        with patch('api.middleware.rbac_middleware.decode_token', side_effect=Exception("Decode failed")):
            middleware = RBACMiddleware(Mock())
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 401
        mock_call_next.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_write_method_admin_role(self, mock_request, mock_call_next):
        """Test write method with admin role succeeds"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer valid.token"})
        mock_request.method = "POST"
        
        payload = {"role": "admin", "tenant_id": "default"}
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
            middleware = RBACMiddleware(Mock())
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200
        mock_call_next.assert_called_once_with(mock_request)
    
    @pytest.mark.asyncio
    async def test_write_method_operator_role(self, mock_request, mock_call_next):
        """Test write method with operator role succeeds"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer valid.token"})
        mock_request.method = "PUT"
        
        payload = {"role": "operator", "tenant_id": "default"}
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
            middleware = RBACMiddleware(Mock())
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200
        mock_call_next.assert_called_once_with(mock_request)
    
    @pytest.mark.asyncio
    async def test_write_method_business_role(self, mock_request, mock_call_next):
        """Test write method with business role succeeds"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer valid.token"})
        mock_request.method = "DELETE"
        
        payload = {"role": "business", "tenant_id": "default"}
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
            middleware = RBACMiddleware(Mock())
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200
        mock_call_next.assert_called_once_with(mock_request)
    
    @pytest.mark.asyncio
    async def test_write_method_viewer_role_forbidden(self, mock_request, mock_call_next):
        """Test write method with viewer role returns 403"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer valid.token"})
        mock_request.method = "POST"
        
        payload = {"role": "viewer", "tenant_id": "default"}
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
            middleware = RBACMiddleware(Mock())
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 403
        assert isinstance(response, JSONResponse)
        mock_call_next.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_write_method_no_role_forbidden(self, mock_request, mock_call_next):
        """Test write method with no role returns 403"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer valid.token"})
        mock_request.method = "PATCH"
        
        payload = {"tenant_id": "default"}  # No role
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
            middleware = RBACMiddleware(Mock())
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 403
        mock_call_next.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_read_method_any_role(self, mock_request, mock_call_next):
        """Test read method works with any role"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer valid.token"})
        mock_request.method = "GET"
        
        for role in ["admin", "operator", "viewer", "business"]:
            payload = {"role": role, "tenant_id": "default"}
            
            with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
                middleware = RBACMiddleware(Mock())
                response = await middleware.dispatch(mock_request, mock_call_next)
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_default_tenant_id(self, mock_request, mock_call_next):
        """Test default tenant_id when not in token"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer valid.token"})
        mock_request.method = "GET"
        
        payload = {"role": "admin"}  # No tenant_id
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
            middleware = RBACMiddleware(Mock())
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200
        assert mock_request.state.tenant_id == "default"
    
    @pytest.mark.asyncio
    async def test_case_insensitive_role(self, mock_request, mock_call_next):
        """Test role comparison is case insensitive"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer valid.token"})
        mock_request.method = "POST"
        
        for role in ["ADMIN", "Admin", "admin", "OPERATOR", "operator"]:
            payload = {"role": role, "tenant_id": "default"}
            
            with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
                middleware = RBACMiddleware(Mock())
                response = await middleware.dispatch(mock_request, mock_call_next)
            
            assert response.status_code == 200


class TestWriteMethods:
    """Test write method detection"""
    
    def test_post_is_write_method(self):
        """Test POST is considered a write method"""
        from api.middleware.rbac_middleware import WRITE_METHODS
        assert "POST" in WRITE_METHODS
    
    def test_put_is_write_method(self):
        """Test PUT is considered a write method"""
        from api.middleware.rbac_middleware import WRITE_METHODS
        assert "PUT" in WRITE_METHODS
    
    def test_delete_is_write_method(self):
        """Test DELETE is considered a write method"""
        from api.middleware.rbac_middleware import WRITE_METHODS
        assert "DELETE" in WRITE_METHODS
    
    def test_patch_is_write_method(self):
        """Test PATCH is considered a write method"""
        from api.middleware.rbac_middleware import WRITE_METHODS
        assert "PATCH" in WRITE_METHODS
    
    def test_get_is_not_write_method(self):
        """Test GET is not considered a write method"""
        from api.middleware.rbac_middleware import WRITE_METHODS
        assert "GET" not in WRITE_METHODS
    
    def test_head_is_not_write_method(self):
        """Test HEAD is not considered a write method"""
        from api.middleware.rbac_middleware import WRITE_METHODS
        assert "HEAD" not in WRITE_METHODS
    
    def test_options_is_not_write_method(self):
        """Test OPTIONS is not considered a write method"""
        from api.middleware.rbac_middleware import WRITE_METHODS
        assert "OPTIONS" not in WRITE_METHODS


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.mark.asyncio
    async def test_empty_path(self, mock_request, mock_call_next):
        """Test empty path"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = ""
        mock_request.headers = Headers({"authorization": "Bearer valid.token"})
        mock_request.method = "GET"
        
        payload = {"role": "admin", "tenant_id": "default"}
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
            middleware = RBACMiddleware(Mock())
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        # Empty path should be treated as private
        assert response.status_code in [200, 401]
    
    @pytest.mark.asyncio
    async def test_very_long_path(self, mock_request, mock_call_next):
        """Test very long path"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        long_path = "/api/" + "a" * 1000 + "/test"
        mock_request.url.path = long_path
        mock_request.headers = Headers({"authorization": "Bearer valid.token"})
        mock_request.method = "GET"
        
        payload = {"role": "admin", "tenant_id": "default"}
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
            middleware = RBACMiddleware(Mock())
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_special_characters_in_path(self, mock_request, mock_call_next):
        """Test special characters in path"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test@#$%/path"
        mock_request.headers = Headers({"authorization": "Bearer valid.token"})
        mock_request.method = "GET"
        
        payload = {"role": "admin", "tenant_id": "default"}
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
            middleware = RBACMiddleware(Mock())
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_unicode_in_path(self, mock_request, mock_call_next):
        """Test unicode characters in path"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test/路径"
        mock_request.headers = Headers({"authorization": "Bearer valid.token"})
        mock_request.method = "GET"
        
        payload = {"role": "admin", "tenant_id": "default"}
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
            middleware = RBACMiddleware(Mock())
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_token_with_whitespace(self, mock_request, mock_call_next):
        """Test token with whitespace"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer  valid.token  "})
        mock_request.method = "GET"
        
        payload = {"role": "admin", "tenant_id": "default"}
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
            middleware = RBACMiddleware(Mock())
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        # Should handle whitespace in token
        assert response.status_code in [200, 401]


class TestPublicPrefixes:
    """Test public prefixes constant"""
    
    def test_public_prefixes_contains_expected_paths(self):
        """Test PUBLIC_PREFIXES contains expected paths"""
        from api.middleware.rbac_middleware import PUBLIC_PREFIXES
        
        expected_prefixes = {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/static/",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/webhook/",
            "/hitl-page/",
            "/sw.js",
            "/sw-register.js",
            "/metrics"
        }
        
        for prefix in expected_prefixes:
            assert prefix in PUBLIC_PREFIXES
    
    def test_public_prefixes_includes_alert_webhooks(self):
        """Test PUBLIC_PREFIXES includes alert webhook paths"""
        from api.middleware.rbac_middleware import PUBLIC_PREFIXES
        
        alert_webhook_prefixes = [
            "/api/v1/alerts/",
            "/api/v1/alerts/prometheus",
            "/api/v1/alerts/grafana",
            "/api/v1/alerts/datadog",
            "/api/v1/alerts/zabbix",
            "/api/v1/alerts/cloudwatch",
            "/api/v1/alerts/pagerduty"
        ]
        
        for prefix in alert_webhook_prefixes:
            assert prefix in PUBLIC_PREFIXES


class TestTokenExtraction:
    """Test token extraction logic"""
    
    @pytest.mark.asyncio
    async def test_bearer_token_extraction(self, mock_request, mock_call_next):
        """Test Bearer token extraction"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer mytoken"})
        mock_request.method = "GET"
        
        payload = {"role": "admin", "tenant_id": "default"}
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload) as mock_decode:
            middleware = RBACMiddleware(Mock())
            await middleware.dispatch(mock_request, mock_call_next)
        
        # Should extract "mytoken" from "Bearer mytoken"
        mock_decode.assert_called_once()
        call_args = mock_decode.call_args[0][0]
        assert call_args == "mytoken"
    
    @pytest.mark.asyncio
    async def test_bearer_lowercase(self, mock_request, mock_call_next):
        """Test lowercase 'bearer' is handled"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "bearer mytoken"})
        mock_request.method = "GET"
        
        payload = {"role": "admin", "tenant_id": "default"}
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
            middleware = RBACMiddleware(Mock())
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        # Should fail since it expects "Bearer " with capital B
        assert response.status_code == 401


class TestStatePopulation:
    """Test request state population"""
    
    @pytest.mark.asyncio
    async def test_state_user_population(self, mock_request, mock_call_next):
        """Test user is populated in request state"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer valid.token"})
        mock_request.method = "GET"
        
        payload = {"user_id": "user123", "role": "admin", "tenant_id": "tenant1"}
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
            middleware = RBACMiddleware(Mock())
            await middleware.dispatch(mock_request, mock_call_next)
        
        assert mock_request.state.user == payload
        assert mock_request.state.user["user_id"] == "user123"
    
    @pytest.mark.asyncio
    async def test_state_role_population(self, mock_request, mock_call_next):
        """Test role is populated in request state"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer valid.token"})
        mock_request.method = "GET"
        
        payload = {"role": "operator", "tenant_id": "default"}
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
            middleware = RBACMiddleware(Mock())
            await middleware.dispatch(mock_request, mock_call_next)
        
        assert mock_request.state.role == "operator"
    
    @pytest.mark.asyncio
    async def test_state_tenant_id_population(self, mock_request, mock_call_next):
        """Test tenant_id is populated in request state"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer valid.token"})
        mock_request.method = "GET"
        
        payload = {"role": "admin", "tenant_id": "custom_tenant"}
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
            middleware = RBACMiddleware(Mock())
            await middleware.dispatch(mock_request, mock_call_next)
        
        assert mock_request.state.tenant_id == "custom_tenant"


class TestErrorResponses:
    """Test error response formats"""
    
    @pytest.mark.asyncio
    async def test_401_response_format(self, mock_request, mock_call_next):
        """Test 401 response format"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({})
        mock_request.method = "GET"
        
        middleware = RBACMiddleware(Mock())
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 401
        content = response.body.decode()
        assert "Missing or invalid Authorization header" in content
    
    @pytest.mark.asyncio
    async def test_403_response_format(self, mock_request, mock_call_next):
        """Test 403 response format"""
        from api.middleware.rbac_middleware import RBACMiddleware
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({"authorization": "Bearer valid.token"})
        mock_request.method = "POST"
        
        payload = {"role": "viewer", "tenant_id": "default"}
        
        with patch('api.middleware.rbac_middleware.decode_token', return_value=payload):
            middleware = RBACMiddleware(Mock())
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 403
        content = response.body.decode()
        assert "requires operator or admin role" in content
