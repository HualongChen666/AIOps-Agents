# -*- coding: utf-8 -*-
"""Tests for core.agent.coding_tools module - based on actual implementation"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from core.agent.coding_tools import (
    _get_workspace_root,
    _resolve_allowed_path,
    _validate_command_args,
    _MAX_FILE_READ_BYTES,
    _MAX_FILE_WRITE_BYTES,
)


class TestWorkspaceFunctions:
    """Test cases for workspace-related functions"""

    def test_get_workspace_root(self):
        """Test getting workspace root"""
        with patch.dict('os.environ', {'AIOPS_AGENT_WORKSPACE': '/test/workspace'}):
            root = _get_workspace_root()
            assert root is not None
            assert 'workspace' in str(root)

    def test_get_workspace_root_default(self):
        """Test getting workspace root with default"""
        with patch.dict('os.environ', {}, clear=True):
            with patch('os.getcwd', return_value='/current/dir'):
                root = _get_workspace_root()
                assert root is not None


class TestPathResolution:
    """Test cases for path resolution functions"""

    def test_resolve_allowed_path_relative(self):
        """Test resolving relative path"""
        import platform
        if platform.system() == 'Windows':
            workspace = Path('C:/workspace')
        else:
            workspace = Path('/workspace')
        with patch('core.agent.coding_tools._get_workspace_root', return_value=workspace):
            with patch('os.getcwd', return_value=str(workspace)):
                result = _resolve_allowed_path('test.py')
                assert result is not None
                assert 'test.py' in str(result)

    def test_resolve_allowed_path_absolute_within_workspace(self):
        """Test resolving absolute path within workspace"""
        import platform
        if platform.system() == 'Windows':
            workspace = Path('C:/workspace')
            test_path = 'C:/workspace/test.py'
        else:
            workspace = Path('/workspace')
            test_path = '/workspace/test.py'
        with patch('core.agent.coding_tools._get_workspace_root', return_value=workspace):
            result = _resolve_allowed_path(test_path)
            assert result is not None
            assert result.name == 'test.py'

    def test_resolve_allowed_path_absolute_outside_workspace(self):
        """Test resolving absolute path outside workspace raises error"""
        import platform
        if platform.system() == 'Windows':
            workspace = Path('C:/workspace')
            test_path = 'C:/etc/passwd'
        else:
            workspace = Path('/workspace')
            test_path = '/etc/passwd'
        with patch('core.agent.coding_tools._get_workspace_root', return_value=workspace):
            with pytest.raises(ValueError, match="outside workspace"):
                _resolve_allowed_path(test_path)

    def test_resolve_allowed_path_with_cwd(self):
        """Test resolving path with custom cwd"""
        import platform
        if platform.system() == 'Windows':
            workspace = Path('C:/workspace')
            cwd = 'C:/workspace/subdir'
        else:
            workspace = Path('/workspace')
            cwd = '/workspace/subdir'
        with patch('core.agent.coding_tools._get_workspace_root', return_value=workspace):
            result = _resolve_allowed_path('test.py', cwd=cwd)
            assert result is not None


class TestCommandValidation:
    """Test cases for command validation"""

    def test_validate_command_args_empty(self):
        """Test validation with empty args"""
        with pytest.raises(ValueError, match="empty command"):
            _validate_command_args([])

    def test_validate_command_args_disallowed_base(self):
        """Test validation with disallowed base command"""
        with pytest.raises(ValueError, match="not allowed"):
            _validate_command_args(['curl', 'http://example.com'])

    def test_validate_command_args_disallowed_recursive(self):
        """Test validation with recursive flags"""
        with pytest.raises(ValueError, match="not allowed"):
            _validate_command_args(['rm', '-R', '/test'])

    def test_validate_command_args_interpreter_forbidden(self):
        """Test validation with forbidden interpreter patterns"""
        with pytest.raises(ValueError, match="not allowed"):
            _validate_command_args(['python', '-c', 'print("test")'])

    def test_validate_command_args_valid(self):
        """Test validation with valid command"""
        # Should not raise
        _validate_command_args(['ls', '-la'])


class TestFileLimits:
    """Test cases for file size limits"""

    def test_max_file_read_bytes(self):
        """Test max file read bytes constant"""
        assert _MAX_FILE_READ_BYTES == 1_000_000  # 1 MB

    def test_max_file_write_bytes(self):
        """Test max file write bytes constant"""
        assert _MAX_FILE_WRITE_BYTES == 10_000_000  # 10 MB


class TestPathSecurity:
    """Test cases for path security"""

    def test_path_traversal_prevention(self):
        """Test that path traversal is prevented"""
        with patch('core.agent.coding_tools._get_workspace_root', return_value=Path('/workspace')):
            with pytest.raises(ValueError, match="outside workspace"):
                _resolve_allowed_path('../../../etc/passwd')

    def test_symlink_protection(self):
        """Test that symlinks outside workspace are rejected"""
        with patch('core.agent.coding_tools._get_workspace_root', return_value=Path('/workspace')):
            with pytest.raises(ValueError, match="outside workspace"):
                _resolve_allowed_path('/workspace/link/../etc/passwd')
