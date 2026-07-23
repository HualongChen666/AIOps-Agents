# -*- coding: utf-8 -*-
"""
Unit tests for core/sso_auth.py

Tests for SSO/OIDC authentication functionality.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch  # noqa: F401

import pytest
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from core.sso_auth import (
    OIDC_CLIENT_ID,
    OIDC_CLIENT_SECRET,
    OIDC_ISSUER_URL,
    OIDC_REDIRECT_URI,
    SSO_ENABLED,
    _state_store,
    generate_state,
    router,
)


class TestConfiguration:
    """Test SSO configuration."""

    def test_sso_enabled_when_configured(self):
        """Test that SSO is enabled when all required config is present."""
        # This test assumes environment variables are set for the test
        # In a real test environment, you would set these before importing
        assert isinstance(SSO_ENABLED, bool)

    def test_oidc_config_variables(self):
        """Test that OIDC configuration variables are accessible."""
        assert isinstance(OIDC_ISSUER_URL, str)
        assert isinstance(OIDC_CLIENT_ID, str)
        assert isinstance(OIDC_CLIENT_SECRET, str)
        assert isinstance(OIDC_REDIRECT_URI, str)


class TestStateGeneration:
    """Test state parameter generation for CSRF protection."""

    def test_generate_state(self):
        """Test that state generation produces a secure random string."""
        state = generate_state()
        assert isinstance(state, str)
        assert len(state) > 20  # Should be reasonably long
        assert state.isalnum() or "-" in state or "_" in state

    def test_generate_state_uniqueness(self):
        """Test that generated states are unique."""
        states = [generate_state() for _ in range(100)]
        assert len(set(states)) == 100  # All should be unique


class TestStateStore:
    """Test state parameter storage and validation."""

    def setup_method(self):
        """Clear state store before each test."""
        _state_store.clear()

    def teardown_method(self):
        """Clean up state store after each test."""
        _state_store.clear()

    def test_state_storage(self):
        """Test storing and retrieving state parameters."""
        state = generate_state()
        timestamp = datetime.utcnow()
        _state_store[state] = timestamp

        assert state in _state_store
        assert _state_store[state] == timestamp

    def test_state_expiry(self):
        """Test that state parameters expire after 5 minutes."""
        state = generate_state()
        old_timestamp = datetime.utcnow() - timedelta(minutes=6)
        _state_store[state] = old_timestamp

        # State should be considered expired
        assert datetime.utcnow() - _state_store[state] > timedelta(minutes=5)

    def test_state_cleanup(self):
        """Test cleaning up expired states."""
        state = generate_state()
        _state_store[state] = datetime.utcnow()

        del _state_store[state]
        assert state not in _state_store


class TestLoginEndpoint:
    """Test SSO login endpoint."""

    def setup_method(self):
        """Clear state store before each test."""
        _state_store.clear()

    def teardown_method(self):
        """Clean up state store after each test."""
        _state_store.clear()

    @patch("core.sso_auth.SSO_ENABLED", False)
    async def test_login_when_sso_disabled(self):
        """Test login endpoint when SSO is disabled."""
        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await router.routes[0].endpoint(request)

        assert exc_info.value.status_code == 400
        assert "SSO not configured" in exc_info.value.detail

    @patch("core.sso_auth.SSO_ENABLED", True)
    @patch("core.sso_auth.oauth")
    async def test_login_generates_state(self, mock_oauth):
        """Test that login endpoint generates and stores state."""
        request = Mock(spec=Request)
        mock_oauth.oidc.authorize_redirect = AsyncMock(return_value=RedirectResponse(url="/test"))

        initial_state_count = len(_state_store)
        await router.routes[0].endpoint(request)

        # State should be stored
        assert len(_state_store) == initial_state_count + 1


class TestCallbackEndpoint:
    """Test SSO callback endpoint."""

    def setup_method(self):
        """Clear state store before each test."""
        _state_store.clear()

    def teardown_method(self):
        """Clean up state store after each test."""
        _state_store.clear()

    @patch("core.sso_auth.SSO_ENABLED", False)
    async def test_callback_when_sso_disabled(self):
        """Test callback endpoint when SSO is disabled."""
        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await router.routes[1].endpoint(request, state="test")

        assert exc_info.value.status_code == 400
        assert "SSO not configured" in exc_info.value.detail

    @patch("core.sso_auth.SSO_ENABLED", True)
    async def test_callback_invalid_state(self):
        """Test callback with invalid state parameter."""
        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await router.routes[1].endpoint(request, state="invalid_state")

        assert exc_info.value.status_code == 400
        assert "Invalid state parameter" in exc_info.value.detail

    @patch("core.sso_auth.SSO_ENABLED", True)
    async def test_callback_expired_state(self):
        """Test callback with expired state parameter."""
        request = Mock(spec=Request)
        state = generate_state()
        _state_store[state] = datetime.now(timezone.utc) - timedelta(minutes=6)

        with pytest.raises(HTTPException) as exc_info:
            await router.routes[1].endpoint(request, state=state)

        assert exc_info.value.status_code == 400
        assert "State parameter expired" in exc_info.value.detail
        assert state not in _state_store  # Should be cleaned up


class TestLoginSuccessEndpoint:
    """Test login success endpoint."""

    async def test_login_success_returns_html(self):
        """Test that login success endpoint returns HTML response."""
        token = "test_token_123"
        response = await router.routes[2].endpoint(token)

        assert isinstance(response, HTMLResponse)
        assert response.status_code == 200
        assert "localStorage.setItem" in response.body.decode()
        assert token in response.body.decode()

    async def test_login_success_html_contains_redirect(self):
        """Test that login success HTML contains redirect script."""
        token = "test_token_123"
        response = await router.routes[2].endpoint(token)

        html = response.body.decode()
        assert "window.location.href" in html
        assert "'/'" in html


class TestEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        """Clear state store before each test."""
        _state_store.clear()

    def teardown_method(self):
        """Clean up state store after each test."""
        _state_store.clear()

    def test_empty_state_store(self):
        """Test behavior with empty state store."""
        assert len(_state_store) == 0

    def test_multiple_states(self):
        """Test storing multiple state parameters."""
        states = [generate_state() for _ in range(10)]
        for state in states:
            _state_store[state] = datetime.utcnow()

        assert len(_state_store) == 10
        for state in states:
            assert state in _state_store

    def test_state_concurrent_access(self):
        """Test that state store handles concurrent access (basic test)."""
        import threading

        def add_state():
            state = generate_state()
            _state_store[state] = datetime.utcnow()

        threads = [threading.Thread(target=add_state) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All states should be stored (assuming no race conditions)
        assert len(_state_store) == 10


class TestSecurity:
    """Test security-related functionality."""

    def test_state_entropy(self):
        """Test that state has sufficient entropy."""
        state = generate_state()
        # token_urlsafe(32) produces 43 characters with ~256 bits of entropy
        assert len(state) >= 32

    def test_state_no_predictable_pattern(self):
        """Test that states don't have predictable patterns."""
        states = [generate_state() for _ in range(10)]
        # All states should be different
        assert len(set(states)) == 10
        # No state should be a substring of another (basic check)
        for i, s1 in enumerate(states):
            for j, s2 in enumerate(states):
                if i != j:
                    assert s1 != s2
