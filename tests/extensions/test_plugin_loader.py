# -*- coding: utf-8 -*-
"""Tests for plugin_loader module."""

import sys
import types
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import the module to ensure coverage tracking
import extensions.plugin_loader as plugin_loader_module
from extensions.plugin_loader import (
    _sanitize,
    _module_name,
    _parent_package,
    _load_one,
    load_all_addons,
    list_addons,
    get_addon,
    ROOT,
    PREFIX,
)

# Simple fixture to avoid database issues
@pytest.fixture(autouse=True)
def isolate_tests():
    """Isolate tests from global conftest."""
    yield


class TestSanitize:
    """Test the _sanitize function."""

    def test_sanitize_hyphens(self):
        """Test that hyphens are replaced with underscores."""
        assert _sanitize("test-module") == "test_module"

    def test_sanitize_dots(self):
        """Test that dots are replaced with underscores."""
        assert _sanitize("test.module") == "test_module"

    def test_sanitize_mixed(self):
        """Test that both hyphens and dots are replaced."""
        assert _sanitize("test-module.name") == "test_module_name"

    def test_sanitize_no_changes(self):
        """Test that valid identifiers are unchanged."""
        assert _sanitize("test_module") == "test_module"

    def test_sanitize_empty(self):
        """Test that empty string returns empty."""
        assert _sanitize("") == ""

    def test_sanitize_multiple_hyphens(self):
        """Test multiple hyphens in a row."""
        assert _sanitize("test--module") == "test__module"

    def test_sanitize_multiple_dots(self):
        """Test multiple dots in a row."""
        assert _sanitize("test..module") == "test__module"


class TestModuleName:
    """Test the _module_name function."""

    def test_module_name_simple(self):
        """Test simple module name generation."""
        py_path = ROOT / "test" / "module.py"
        result = _module_name(py_path)
        assert result == f"{PREFIX}.test.module"

    def test_module_name_with_hyphens(self):
        """Test module name with hyphens in directory."""
        py_path = ROOT / "test-module" / "file.py"
        result = _module_name(py_path)
        assert result == f"{PREFIX}.test_module.file"

    def test_module_name_init_file(self):
        """Test that __init__.py files are handled correctly."""
        py_path = ROOT / "test" / "__init__.py"
        result = _module_name(py_path)
        assert result == f"{PREFIX}.test"

    def test_module_name_nested(self):
        """Test nested module paths."""
        py_path = ROOT / "a" / "b" / "c" / "module.py"
        result = _module_name(py_path)
        assert result == f"{PREFIX}.a.b.c.module"

    def test_module_name_nested_init(self):
        """Test nested __init__.py files."""
        py_path = ROOT / "a" / "b" / "__init__.py"
        result = _module_name(py_path)
        assert result == f"{PREFIX}.a.b"


class TestParentPackage:
    """Test the _parent_package function."""

    def test_parent_package_simple(self):
        """Test simple parent package."""
        assert _parent_package("a.b.c") == "a.b"

    def test_parent_package_single_level(self):
        """Test single level module."""
        assert _parent_package("module") is None

    def test_parent_package_two_levels(self):
        """Test two level module."""
        assert _parent_package("a.b") == "a"

    def test_parent_package_deep(self):
        """Test deeply nested module."""
        assert _parent_package("a.b.c.d.e") == "a.b.c.d"


class TestLoadOne:
    """Test the _load_one function."""

    def test_load_one_success(self, tmp_path):
        """Test successful module loading."""
        # Create a temporary Python file
        test_file = tmp_path / "test_module.py"
        test_file.write_text("x = 42\n")

        module, ok, err = _load_one(test_file, "test_module")
        assert ok is True
        assert err == ""
        assert module.x == 42
        assert "test_module" in sys.modules

    def test_load_one_syntax_error(self, tmp_path):
        """Test loading a file with syntax error."""
        test_file = tmp_path / "bad_module.py"
        test_file.write_text("def broken(\n")  # Syntax error

        module, ok, err = _load_one(test_file, "bad_module")
        assert ok is False
        assert "SyntaxError" in err
        assert "bad_module" in sys.modules

    def test_load_one_import_error(self, tmp_path):
        """Test loading a file with import error."""
        test_file = tmp_path / "import_error_module.py"
        test_file.write_text("import nonexistent_module\n")

        module, ok, err = _load_one(test_file, "import_error_module")
        assert ok is False
        assert "ModuleNotFoundError" in err or "ImportError" in err

    def test_load_one_runtime_error(self, tmp_path):
        """Test loading a file with runtime error."""
        test_file = tmp_path / "runtime_error_module.py"
        test_file.write_text("raise RuntimeError('test error')\n")

        module, ok, err = _load_one(test_file, "runtime_error_module")
        assert ok is False
        assert "RuntimeError" in err

    def test_load_one_addon_file_attribute(self, tmp_path):
        """Test that __addon_file__ attribute is set."""
        test_file = tmp_path / "test_attr.py"
        test_file.write_text("pass\n")

        module, ok, err = _load_one(test_file, "test_attr")
        assert ok is True
        assert hasattr(module, "__addon_file__")
        assert module.__addon_file__ == str(test_file)

    def test_load_one_invalid_spec(self, tmp_path):
        """Test handling of invalid spec."""
        # Use a non-existent path to trigger spec creation failure
        test_file = tmp_path / "nonexistent.py"
        
        with patch('importlib.util.spec_from_file_location', return_value=None):
            module, ok, err = _load_one(test_file, "nonexistent")
            assert ok is False
            assert err == "could not create spec"
            assert isinstance(module, types.ModuleType)


class TestLoadAllAddons:
    """Test the load_all_addons function."""

    def test_load_all_addons_empty_directory(self, tmp_path):
        """Test loading from an empty directory."""
        import extensions.plugin_loader as pl
        original_root = pl.ROOT
        pl.ROOT = tmp_path
        
        try:
            result = load_all_addons()
            assert result["loaded"] == []
            assert result["failed"] == []
            assert result["total"] == 0
        finally:
            pl.ROOT = original_root

    def test_load_all_addons_successful_load(self, tmp_path):
        """Test successful loading of multiple modules."""
        import extensions.plugin_loader as pl
        original_root = pl.ROOT
        pl.ROOT = tmp_path
        
        try:
            # Create test modules
            (tmp_path / "module1.py").write_text("x = 1\n")
            (tmp_path / "module2.py").write_text("y = 2\n")
            
            result = load_all_addons()
            assert result["total"] == 2
            assert len(result["loaded"]) == 2
            assert result["failed"] == []
            assert f"{PREFIX}.module1" in result["loaded"]
            assert f"{PREFIX}.module2" in result["loaded"]
        finally:
            pl.ROOT = original_root

    def test_load_all_addons_with_failure(self, tmp_path):
        """Test loading with some modules failing."""
        import extensions.plugin_loader as pl
        original_root = pl.ROOT
        pl.ROOT = tmp_path
        
        try:
            (tmp_path / "good.py").write_text("x = 1\n")
            (tmp_path / "bad.py").write_text("import nonexistent\n")
            
            result = load_all_addons(max_passes=1)
            assert result["total"] == 2
            assert len(result["loaded"]) == 1
            assert len(result["failed"]) == 1
            assert f"{PREFIX}.good" in result["loaded"]
            assert any(f["name"] == f"{PREFIX}.bad" for f in result["failed"])
        finally:
            pl.ROOT = original_root

    def test_load_all_addons_relative_imports(self, tmp_path):
        """Test that relative imports work with multiple passes."""
        import extensions.plugin_loader as pl
        original_root = pl.ROOT
        pl.ROOT = tmp_path
        
        try:
            # Create a package structure
            pkg_dir = tmp_path / "pkg"
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("")
            (pkg_dir / "a.py").write_text("x = 1\n")
            (pkg_dir / "b.py").write_text("from . import a\ny = a.x + 1\n")
            
            result = load_all_addons(max_passes=3)
            assert result["total"] == 3  # __init__.py, a.py, b.py
            assert len(result["loaded"]) >= 2  # At least a.py and b.py should load
        finally:
            pl.ROOT = original_root

    def test_load_all_addons_max_passes(self, tmp_path):
        """Test that max_passes parameter is respected."""
        import extensions.plugin_loader as pl
        original_root = pl.ROOT
        pl.ROOT = tmp_path
        
        try:
            (tmp_path / "module.py").write_text("pass\n")
            
            result = load_all_addons(max_passes=10)
            assert result["total"] == 1
            assert len(result["loaded"]) == 1
        finally:
            pl.ROOT = original_root

    def test_load_all_addons_no_progress(self, tmp_path):
        """Test that loading stops when no progress is made."""
        import extensions.plugin_loader as pl
        original_root = pl.ROOT
        pl.ROOT = tmp_path
        
        try:
            (tmp_path / "bad.py").write_text("import nonexistent\n")
            
            result = load_all_addons(max_passes=5)
            # Should stop early since no progress can be made
            assert result["total"] == 1
            assert len(result["failed"]) == 1
        finally:
            pl.ROOT = original_root

    def test_load_all_addons_hyphenated_directory(self, tmp_path):
        """Test loading from directories with hyphens."""
        import extensions.plugin_loader as pl
        original_root = pl.ROOT
        pl.ROOT = tmp_path
        
        try:
            hyphen_dir = tmp_path / "test-module"
            hyphen_dir.mkdir()
            (hyphen_dir / "file.py").write_text("z = 3\n")
            
            result = load_all_addons()
            assert result["total"] == 1
            assert f"{PREFIX}.test_module.file" in result["loaded"]
        finally:
            pl.ROOT = original_root

    def test_load_all_addons_nested_structure(self, tmp_path):
        """Test loading from nested directory structure."""
        import extensions.plugin_loader as pl
        original_root = pl.ROOT
        pl.ROOT = tmp_path
        
        try:
            nested = tmp_path / "a" / "b" / "c"
            nested.mkdir(parents=True)
            (nested / "module.py").write_text("value = 42\n")
            
            result = load_all_addons()
            assert result["total"] == 1
            assert f"{PREFIX}.a.b.c.module" in result["loaded"]
        finally:
            pl.ROOT = original_root

    def test_load_all_addons_with_init_files(self, tmp_path):
        """Test that __init__.py files are handled correctly."""
        import extensions.plugin_loader as pl
        original_root = pl.ROOT
        pl.ROOT = tmp_path
        
        try:
            pkg = tmp_path / "package"
            pkg.mkdir()
            (pkg / "__init__.py").write_text("pkg_var = 10\n")
            (pkg / "module.py").write_text("mod_var = 20\n")
            
            result = load_all_addons()
            assert result["total"] == 2
            assert f"{PREFIX}.package" in result["loaded"]
            assert f"{PREFIX}.package.module" in result["loaded"]
        finally:
            pl.ROOT = original_root


class TestListAddons:
    """Test the list_addons function."""

    def test_list_addons_empty(self, tmp_path):
        """Test listing from empty directory."""
        import extensions.plugin_loader as pl
        original_root = pl.ROOT
        pl.ROOT = tmp_path
        
        try:
            result = list_addons()
            assert result == []
        finally:
            pl.ROOT = original_root

    def test_list_addons_files(self, tmp_path):
        """Test listing Python files."""
        import extensions.plugin_loader as pl
        original_root = pl.ROOT
        pl.ROOT = tmp_path
        
        try:
            (tmp_path / "a.py").write_text("")
            (tmp_path / "b.py").write_text("")
            
            result = list_addons()
            assert len(result) == 2
            assert "a.py" in result
            assert "b.py" in result
        finally:
            pl.ROOT = original_root

    def test_list_addons_nested(self, tmp_path):
        """Test listing from nested directories."""
        import extensions.plugin_loader as pl
        original_root = pl.ROOT
        pl.ROOT = tmp_path
        
        try:
            nested = tmp_path / "subdir"
            nested.mkdir()
            (nested / "module.py").write_text("")
            
            result = list_addons()
            assert len(result) == 1
            assert str(Path("subdir") / "module.py") in result
        finally:
            pl.ROOT = original_root

    def test_list_addons_sorted(self, tmp_path):
        """Test that results are sorted."""
        import extensions.plugin_loader as pl
        original_root = pl.ROOT
        pl.ROOT = tmp_path
        
        try:
            (tmp_path / "z.py").write_text("")
            (tmp_path / "a.py").write_text("")
            (tmp_path / "m.py").write_text("")
            
            result = list_addons()
            assert result == ["a.py", "m.py", "z.py"]
        finally:
            pl.ROOT = original_root

    def test_list_addons_non_py_files_ignored(self, tmp_path):
        """Test that non-Python files are ignored."""
        import extensions.plugin_loader as pl
        original_root = pl.ROOT
        pl.ROOT = tmp_path
        
        try:
            (tmp_path / "test.txt").write_text("")
            (tmp_path / "test.md").write_text("")
            (tmp_path / "test.py").write_text("")
            
            result = list_addons()
            assert result == ["test.py"]
        finally:
            pl.ROOT = original_root


class TestGetAddon:
    """Test the get_addon function."""

    def test_get_addon_loaded(self, tmp_path):
        """Test getting a loaded addon."""
        # First load a module
        test_file = tmp_path / "test.py"
        test_file.write_text("value = 123\n")
        _load_one(test_file, "test_addon")
        
        result = get_addon("test_addon")
        assert result is not None
        assert result.value == 123

    def test_get_addon_not_loaded(self):
        """Test getting a non-loaded addon."""
        result = get_addon("nonexistent_addon")
        assert result is None

    def test_get_addon_from_sys_modules(self):
        """Test that it retrieves from sys.modules."""
        # Create a module directly in sys.modules
        test_module = types.ModuleType("manual_addon")
        test_module.custom_attr = "test"
        sys.modules["manual_addon"] = test_module
        
        result = get_addon("manual_addon")
        assert result is not None
        assert result.custom_attr == "test"
        
        # Cleanup
        del sys.modules["manual_addon"]

    def test_get_addon_case_sensitive(self):
        """Test that addon names are case-sensitive."""
        sys.modules["TestAddon"] = types.ModuleType("TestAddon")
        
        result = get_addon("testaddon")
        assert result is None
        
        result = get_addon("TestAddon")
        assert result is not None
        
        del sys.modules["TestAddon"]


class TestIntegration:
    """Integration tests for plugin_loader."""

    def test_full_workflow(self, tmp_path):
        """Test the complete workflow of listing, loading, and getting addons."""
        import extensions.plugin_loader as pl
        original_root = pl.ROOT
        pl.ROOT = tmp_path
        
        try:
            # Create test structure
            pkg = tmp_path / "test_pkg"
            pkg.mkdir()
            (pkg / "__init__.py").write_text("init_var = 1\n")
            (pkg / "module.py").write_text("mod_var = 2\n")
            
            # List addons
            addons = list_addons()
            assert len(addons) == 2
            
            # Load all addons
            result = load_all_addons()
            assert result["total"] == 2
            assert len(result["loaded"]) == 2
            
            # Get specific addon
            addon = get_addon(f"{PREFIX}.test_pkg.module")
            assert addon is not None
            assert addon.mod_var == 2
        finally:
            pl.ROOT = original_root

    def test_error_recovery(self, tmp_path):
        """Test that errors in one module don't prevent loading others."""
        import extensions.plugin_loader as pl
        original_root = pl.ROOT
        pl.ROOT = tmp_path
        
        try:
            (tmp_path / "good1.py").write_text("x = 1\n")
            (tmp_path / "bad.py").write_text("import nonexistent\n")
            (tmp_path / "good2.py").write_text("y = 2\n")
            
            result = load_all_addons()
            assert result["total"] == 3
            assert len(result["loaded"]) == 2
            assert len(result["failed"]) == 1
            assert f"{PREFIX}.good1" in result["loaded"]
            assert f"{PREFIX}.good2" in result["loaded"]
        finally:
            pl.ROOT = original_root
