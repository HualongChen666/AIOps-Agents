# -*- coding: utf-8 -*-
"""Test security configuration for task 1.6."""

import pytest


class TestSecurityConfiguration:
    """Test security configuration for task 1.6."""

    def test_rbac_middleware_exists(self):
        """Test that RBAC middleware exists and is properly configured."""
        # Check that RBACMiddleware exists
        from api.middleware.rbac_middleware import RBACMiddleware, WRITE_METHODS, PUBLIC_PREFIXES
        
        # Verify middleware class exists
        assert RBACMiddleware is not None, "RBACMiddleware should exist"
        
        # Verify write methods are defined
        expected_write_methods = {"POST", "PUT", "DELETE", "PATCH"}
        assert WRITE_METHODS == expected_write_methods, "Write methods should be correctly defined"
        
        # Verify public prefixes are defined
        assert "/docs" in PUBLIC_PREFIXES, "Documentation should be public"
        assert "/health" in PUBLIC_PREFIXES, "Health endpoint should be public"
        assert "/api/v1/auth/login" in PUBLIC_PREFIXES, "Login endpoint should be public"
        
        print("✓ RBAC middleware exists and is properly configured")

    def test_security_headers_class_exists(self):
        """Test that SecurityHeaders class exists with all required headers."""
        from core.security_middleware import SecurityHeaders
        from fastapi import Response
        
        # Create a test response
        response = Response(content="test")
        
        # Apply security headers
        secured_response = SecurityHeaders.add_security_headers(response)
        
        # Verify all required security headers are present
        required_headers = [
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "X-Frame-Options",
            "X-Content-Type-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Permissions-Policy",
        ]
        
        for header in required_headers:
            assert header in secured_response.headers, f"Security header {header} should be present"
        
        # Verify specific header values
        assert secured_response.headers["X-Frame-Options"] == "DENY", "X-Frame-Options should be DENY"
        assert "max-age=31536000" in secured_response.headers["Strict-Transport-Security"], "HSTS should have max-age"
        
        print("✓ All required security headers are configured")

    def test_key_management_service_exists(self):
        """Test that key management service exists and is initialized."""
        from core.key_management_service import get_key_service
        
        # Get key service instance
        key_service = get_key_service()
        
        assert key_service is not None, "Key management service should exist"
        
        # Verify it has required methods (based on actual implementation)
        assert hasattr(key_service, "get_key"), "Should have get_key method"
        assert hasattr(key_service, "set_key"), "Should have set_key method"
        assert hasattr(key_service, "delete_key"), "Should have delete_key method"
        assert hasattr(key_service, "key_exists"), "Should have key_exists method"
        
        print("✓ Key management service is available")

    def test_authentication_module_exists(self):
        """Test that authentication module exists with required functions."""
        from core.authentication import get_current_user, get_current_active_user
        
        # Verify authentication functions exist
        assert get_current_user is not None, "get_current_user should exist"
        assert get_current_active_user is not None, "get_current_active_user should exist"
        
        print("✓ Authentication module is available")

    def test_fine_grained_rbac_exists(self):
        """Test that fine-grained RBAC system exists."""
        from core.fine_rbac import require_permission, check_permission, grant_permission
        
        # Verify RBAC functions exist
        assert require_permission is not None, "require_permission should exist"
        assert check_permission is not None, "check_permission should exist"
        assert grant_permission is not None, "grant_permission should exist"
        
        # Test that require_permission returns a dependency (without calling it)
        # Just verify the function is callable
        assert callable(require_permission), "require_permission should be callable"
        
        # Test permission check
        grant_permission("default", "test", "read", "admin")
        assert check_permission("default", "test", "read", "admin") is True, "Admin should have permission"
        assert check_permission("default", "test", "read", "user") is False, "User should not have permission by default"
        
        print("✓ Fine-grained RBAC system is available")

    def test_csp_policy_is_configured(self):
        """Test that CSP policy is properly configured."""
        from core.security_middleware import SecurityHeaders
        from fastapi import Response
        
        response = Response(content="test")
        secured_response = SecurityHeaders.add_security_headers(response)
        
        csp = secured_response.headers["Content-Security-Policy"]
        
        # Verify CSP includes essential directives
        assert "default-src" in csp, "CSP should have default-src"
        assert "script-src" in csp, "CSP should have script-src"
        assert "style-src" in csp, "CSP should have style-src"
        
        print("✓ CSP policy is properly configured")

    def test_password_policy_exists(self):
        """Test that password policy enforcement exists."""
        from core.security_middleware import PasswordPolicy
        
        # Test password validation
        weak_password = "password"
        is_valid, message = PasswordPolicy.validate_password(weak_password)
        assert not is_valid, "Weak password should be rejected"
        
        # Test strong password
        strong_password = "StrongP@ssw0rd123"
        is_valid, message = PasswordPolicy.validate_password(strong_password)
        assert is_valid, "Strong password should be accepted"
        
        # Test password hashing
        hashed = PasswordPolicy.hash_password(strong_password)
        assert hashed is not None, "Password should be hashable"
        assert len(hashed) > 0, "Hashed password should not be empty"
        
        # Test password verification
        is_correct = PasswordPolicy.verify_password(strong_password, hashed)
        assert is_correct, "Password verification should work"
        
        print("✓ Password policy enforcement is available")

    def test_mfa_manager_exists(self):
        """Test that MFA manager exists."""
        from core.security_middleware import MFAManager
        
        # Verify MFA manager exists
        mfa_manager = MFAManager()
        assert mfa_manager is not None, "MFA manager should exist"
        
        # Verify it has required methods (based on actual implementation)
        assert hasattr(mfa_manager, "generate_totp_secret"), "Should have generate_totp_secret method"
        assert hasattr(mfa_manager, "verify_totp"), "Should have verify_totp method"
        assert hasattr(mfa_manager, "enable_mfa"), "Should have enable_mfa method"
        assert hasattr(mfa_manager, "disable_mfa"), "Should have disable_mfa method"
        
        print("✓ MFA manager is available")

    def test_rate_limiter_exists(self):
        """Test that rate limiter exists."""
        from core.security_middleware import RateLimiter
        
        # Verify rate limiter exists
        rate_limiter = RateLimiter()
        assert rate_limiter is not None, "Rate limiter should exist"
        
        # Verify it has required methods
        assert hasattr(rate_limiter, "check_rate_limit"), "Should have check_rate_limit method"
        
        print("✓ Rate limiter is available")

    def test_tls_enforcer_exists(self):
        """Test that TLS enforcer exists."""
        from core.security_middleware import TLSEnforcer
        
        # Verify TLS enforcer exists
        tls_enforcer = TLSEnforcer()
        assert tls_enforcer is not None, "TLS enforcer should exist"
        
        # Verify it has required methods
        assert hasattr(tls_enforcer, "check_tls"), "Should have check_tls method"
        
        print("✓ TLS enforcer is available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
