# -*- coding: utf-8 -*-
"""
Plugin Development Advanced API Router
Provides comprehensive API endpoints for plugin development workflow
"""

import os
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field, field_validator
from loguru import logger

router = APIRouter(prefix="/api/v1/plugin/development", tags=["Plugin Development Advanced"])


# Pydantic Models
class ScaffoldRequest(BaseModel):
    """Plugin scaffold request model"""
    plugin_name: str = Field(..., description="Plugin name")
    plugin_type: str = Field(..., description="Plugin type (collector, analyzer, notifier, action)")
    author: str = Field(default="Unknown", description="Plugin author")
    version: str = Field(default="1.0.0", description="Plugin version")
    description: str = Field(default="", description="Plugin description")
    template: str = Field(default="default", description="Template to use")

    @field_validator("plugin_type")
    @classmethod
    def validate_plugin_type(cls, v: str) -> str:
        valid_types = ["collector", "analyzer", "notifier", "action"]
        if v not in valid_types:
            raise ValueError(f"Invalid plugin type. Must be one of: {', '.join(valid_types)}")
        return v


class ValidateRequest(BaseModel):
    """Plugin validation request model"""
    plugin_code: str = Field(..., description="Plugin code to validate")
    plugin_config: Dict[str, Any] = Field(default_factory=dict, description="Plugin configuration")


class TestRequest(BaseModel):
    """Plugin test request model"""
    plugin_code: str = Field(..., description="Plugin code to test")
    test_config: Dict[str, Any] = Field(default_factory=dict, description="Test configuration")
    test_data: Dict[str, Any] = Field(default_factory=dict, description="Test data")


class BuildRequest(BaseModel):
    """Plugin build request model"""
    plugin_path: str = Field(..., description="Plugin directory path")
    build_config: Dict[str, Any] = Field(default_factory=dict, description="Build configuration")


class PackageRequest(BaseModel):
    """Plugin package request model"""
    plugin_path: str = Field(..., description="Plugin directory path")
    package_name: Optional[str] = Field(None, description="Package name (auto-generated if not provided)")
    version: Optional[str] = Field(None, description="Package version")
    include_dependencies: bool = Field(default=True, description="Include dependencies")


class ScaffoldResponse(BaseModel):
    """Scaffold response model"""
    success: bool
    plugin_id: str
    plugin_path: str
    message: str
    created_files: List[str]


class ValidateResponse(BaseModel):
    """Validation response model"""
    success: bool
    valid: bool
    errors: List[str]
    warnings: List[str]
    message: str


class TestResponse(BaseModel):
    """Test response model"""
    success: bool
    passed: bool
    test_results: List[Dict[str, Any]]
    coverage: Optional[float]
    message: str


class BuildResponse(BaseModel):
    """Build response model"""
    success: bool
    build_path: str
    build_log: str
    message: str


class PackageResponse(BaseModel):
    """Package response model"""
    success: bool
    package_path: str
    package_name: str
    package_size: int
    message: str


# Plugin templates
PLUGIN_TEMPLATES = {
    "collector": '''# -*- coding: utf-8 -*-
"""
{plugin_name} Collector Plugin
Enterprise-grade data collector plugin
"""

from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime, timezone


class {class_name}:
    """
    {plugin_name} collector plugin
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize plugin

        Args:
            config: Plugin configuration
        """
        self.config = config
        self.plugin_name = "{plugin_name}"
        self.version = "{version}"
        self.author = "{author}"

        logger.info(f"Initialized {self.plugin_name} collector plugin")

    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize plugin with configuration

        Args:
            config: Plugin configuration

        Returns:
            True if successful, False otherwise
        """
        try:
            self.config.update(config)
            logger.info(f"{self.plugin_name} initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize {self.plugin_name}: {e}")
            return False

    def collect(self) -> Dict[str, Any]:
        """
        Collect data

        Returns:
            Collected data
        """
        try:
            # Implement your data collection logic here
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": self.plugin_name,
                "metrics": {},
            }
            logger.info(f"Data collected by {self.plugin_name}")
            return data
        except Exception as e:
            logger.error(f"Failed to collect data: {e}")
            raise

    def cleanup(self) -> bool:
        """
        Cleanup resources

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"{self.plugin_name} cleanup completed")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup {self.plugin_name}: {e}")
            return False
''',
    "analyzer": '''# -*- coding: utf-8 -*-
"""
{plugin_name} Analyzer Plugin
Enterprise-grade data analyzer plugin
"""

from typing import Dict, Any, Optional, List
from loguru import logger
from datetime import datetime, timezone


class {class_name}:
    """
    {plugin_name} analyzer plugin
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize plugin

        Args:
            config: Plugin configuration
        """
        self.config = config
        self.plugin_name = "{plugin_name}"
        self.version = "{version}"
        self.author = "{author}"

        logger.info(f"Initialized {self.plugin_name} analyzer plugin")

    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize plugin with configuration

        Args:
            config: Plugin configuration

        Returns:
            True if successful, False otherwise
        """
        try:
            self.config.update(config)
            logger.info(f"{self.plugin_name} initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize {self.plugin_name}: {e}")
            return False

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze data

        Args:
            data: Input data to analyze

        Returns:
            Analysis results
        """
        try:
            # Implement your analysis logic here
            results = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "analyzer": self.plugin_name,
                "findings": [],
                "metrics": {},
            }
            logger.info(f"Data analyzed by {self.plugin_name}")
            return results
        except Exception as e:
            logger.error(f"Failed to analyze data: {e}")
            raise

    def cleanup(self) -> bool:
        """
        Cleanup resources

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"{self.plugin_name} cleanup completed")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup {self.plugin_name}: {e}")
            return False
''',
    "notifier": '''# -*- coding: utf-8 -*-
"""
{plugin_name} Notifier Plugin
Enterprise-grade notification plugin
"""

from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime, timezone


class {class_name}:
    """
    {plugin_name} notifier plugin
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize plugin

        Args:
            config: Plugin configuration
        """
        self.config = config
        self.plugin_name = "{plugin_name}"
        self.version = "{version}"
        self.author = "{author}"

        logger.info(f"Initialized {self.plugin_name} notifier plugin")

    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize plugin with configuration

        Args:
            config: Plugin configuration

        Returns:
            True if successful, False otherwise
        """
        try:
            self.config.update(config)
            logger.info(f"{self.plugin_name} initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize {self.plugin_name}: {e}")
            return False

    def notify(self, alert: Dict[str, Any]) -> bool:
        """
        Send notification

        Args:
            alert: Alert data

        Returns:
            True if successful, False otherwise
        """
        try:
            # Implement your notification logic here
            logger.info(f"Notification sent by {self.plugin_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    def cleanup(self) -> bool:
        """
        Cleanup resources

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"{self.plugin_name} cleanup completed")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup {self.plugin_name}: {e}")
            return False
''',
    "action": '''# -*- coding: utf-8 -*-
"""
{plugin_name} Action Plugin
Enterprise-grade action plugin
"""

from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime, timezone


class {class_name}:
    """
    {plugin_name} action plugin
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize plugin

        Args:
            config: Plugin configuration
        """
        self.config = config
        self.plugin_name = "{plugin_name}"
        self.version = "{version}"
        self.author = "{author}"

        logger.info(f"Initialized {self.plugin_name} action plugin")

    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize plugin with configuration

        Args:
            config: Plugin configuration

        Returns:
            True if successful, False otherwise
        """
        try:
            self.config.update(config)
            logger.info(f"{self.plugin_name} initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize {self.plugin_name}: {e}")
            return False

    def execute(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute action

        Args:
            action_data: Action data

        Returns:
            Execution results
        """
        try:
            # Implement your action logic here
            results = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": self.plugin_name,
                "status": "success",
                "output": {},
            }
            logger.info(f"Action executed by {self.plugin_name}")
            return results
        except Exception as e:
            logger.error(f"Failed to execute action: {e}")
            raise

    def cleanup(self) -> bool:
        """
        Cleanup resources

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"{self.plugin_name} cleanup completed")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup {self.plugin_name}: {e}")
            return False
''',
}


def _sanitize_class_name(name: str) -> str:
    """Convert plugin name to valid class name"""
    # Remove spaces and special characters, capitalize words
    sanitized = "".join(word.capitalize() for word in name.replace("-", " ").replace("_", " ").split())
    return sanitized + "Plugin"


# Scaffold Endpoint
@router.post("/scaffolds", response_model=ScaffoldResponse, summary="Create plugin scaffold")
async def create_scaffold(request: ScaffoldRequest):
    """
    Create a new plugin scaffold from template
    
    Args:
        request: Scaffold request data
        
    Returns:
        Scaffold creation result
    """
    try:
        # Generate plugin ID
        plugin_id = str(uuid4())
        
        # Create plugin directory
        base_dir = Path("plugins")
        base_dir.mkdir(exist_ok=True)
        
        plugin_dir = base_dir / request.plugin_name
        if plugin_dir.exists():
            raise HTTPException(status_code=400, detail=f"Plugin directory '{request.plugin_name}' already exists")
        
        plugin_dir.mkdir(exist_ok=True)
        
        # Generate class name
        class_name = _sanitize_class_name(request.plugin_name)
        
        # Get template
        template = PLUGIN_TEMPLATES.get(request.plugin_type, PLUGIN_TEMPLATES["collector"])
        plugin_code = template.format(
            plugin_name=request.plugin_name,
            class_name=class_name,
            version=request.version,
            author=request.author,
        )
        
        # Write plugin file
        plugin_file = plugin_dir / f"{request.plugin_name}.py"
        plugin_file.write_text(plugin_code, encoding="utf-8")
        
        # Create config file
        config = {
            "plugin_id": plugin_id,
            "plugin_name": request.plugin_name,
            "plugin_type": request.plugin_type,
            "version": request.version,
            "author": request.author,
            "description": request.description,
            "class_name": class_name,
            "enabled": True,
        }
        
        config_file = plugin_dir / "config.json"
        import json
        config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
        
        # Create README
        readme_content = f"""# {request.plugin_name}

## Description
{request.description}

## Installation
Copy this plugin to the plugins directory.

## Configuration
Edit config.json to configure the plugin.

## Usage
The plugin will be automatically loaded by the plugin system.

## Author
{request.author}

## Version
{request.version}
"""
        readme_file = plugin_dir / "README.md"
        readme_file.write_text(readme_content, encoding="utf-8")
        
        # Create __init__.py
        init_content = f'''# -*- coding: utf-8 -*-
"""
{request.plugin_name} Plugin Package
"""

from .{request.plugin_name} import {class_name}

__all__ = ["{class_name}"]
'''
        init_file = plugin_dir / "__init__.py"
        init_file.write_text(init_content, encoding="utf-8")
        
        created_files = [
            str(plugin_file),
            str(config_file),
            str(readme_file),
            str(init_file),
        ]
        
        logger.info(f"Created plugin scaffold: {request.plugin_name}")
        
        return ScaffoldResponse(
            success=True,
            plugin_id=plugin_id,
            plugin_path=str(plugin_dir),
            message=f"Plugin scaffold created successfully at {plugin_dir}",
            created_files=created_files,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating scaffold: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Validate Endpoint
@router.post("/validate", response_model=ValidateResponse, summary="Validate plugin code")
async def validate_plugin(request: ValidateRequest):
    """
    Validate plugin code for syntax and structure
    
    Args:
        request: Validation request data
        
    Returns:
        Validation result
    """
    try:
        errors = []
        warnings = []
        
        # Syntax check
        try:
            compile(request.plugin_code, '<string>', 'exec')
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
        
        # Check for required methods
        required_methods = ["__init__", "initialize"]
        for method in required_methods:
            if f"def {method}" not in request.plugin_code:
                errors.append(f"Missing required method: {method}")
        
        # Check for cleanup method (warning)
        if "def cleanup" not in request.plugin_code:
            warnings.append("Missing cleanup method (recommended)")
        
        # Check for docstring
        if '"""' not in request.plugin_code:
            warnings.append("Missing docstring (recommended)")
        
        # Validate config structure
        if request.plugin_config:
            if "plugin_name" not in request.plugin_config:
                errors.append("Config missing required field: plugin_name")
            if "plugin_type" not in request.plugin_config:
                errors.append("Config missing required field: plugin_type")
        
        is_valid = len(errors) == 0
        
        logger.info(f"Plugin validation completed: valid={is_valid}, errors={len(errors)}, warnings={len(warnings)}")
        
        return ValidateResponse(
            success=True,
            valid=is_valid,
            errors=errors,
            warnings=warnings,
            message=f"Validation completed: {len(errors)} errors, {len(warnings)} warnings",
        )
    except Exception as e:
        logger.error(f"Error validating plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Test Endpoint
@router.post("/test", response_model=TestResponse, summary="Test plugin code")
async def test_plugin(request: TestRequest):
    """
    Test plugin code with test data
    
    Args:
        request: Test request data
        
    Returns:
        Test result
    """
    try:
        test_results = []
        
        # Create a temporary file for the plugin
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(request.plugin_code)
            temp_file = f.name
        
        try:
            # Try to import and instantiate the plugin
            import sys
            import importlib.util
            
            spec = importlib.util.spec_from_file_location("test_plugin", temp_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules["test_plugin"] = module
                spec.loader.exec_module(module)
                
                # Find the plugin class
                plugin_class = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and attr_name.endswith("Plugin"):
                        plugin_class = attr
                        break
                
                if plugin_class:
                    # Test initialization
                    test_results.append({
                        "test": "initialization",
                        "status": "passed",
                        "message": "Plugin class found and can be instantiated",
                    })
                    
                    # Test instantiation
                    try:
                        instance = plugin_class(request.test_config)
                        test_results.append({
                            "test": "instantiation",
                            "status": "passed",
                            "message": "Plugin instantiated successfully",
                        })
                    except Exception as e:
                        test_results.append({
                            "test": "instantiation",
                            "status": "failed",
                            "message": f"Failed to instantiate: {str(e)}",
                        })
                else:
                    test_results.append({
                        "test": "class_detection",
                        "status": "failed",
                        "message": "No plugin class found (class name should end with 'Plugin')",
                    })
            else:
                test_results.append({
                    "test": "module_load",
                    "status": "failed",
                    "message": "Failed to load plugin module",
                })
        finally:
            # Clean up
            os.unlink(temp_file)
            if "test_plugin" in sys.modules:
                del sys.modules["test_plugin"]
        
        passed = all(result["status"] == "passed" for result in test_results)
        
        logger.info(f"Plugin test completed: passed={passed}, tests={len(test_results)}")
        
        return TestResponse(
            success=True,
            passed=passed,
            test_results=test_results,
            coverage=None,
            message=f"Test completed: {len(test_results)} tests, {sum(1 for r in test_results if r['status'] == 'passed')} passed",
        )
    except Exception as e:
        logger.error(f"Error testing plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Build Endpoint
@router.post("/build", response_model=BuildResponse, summary="Build plugin")
async def build_plugin(request: BuildRequest):
    """
    Build plugin from source
    
    Args:
        request: Build request data
        
    Returns:
        Build result
    """
    try:
        plugin_path = Path(request.plugin_path)
        
        if not plugin_path.exists():
            raise HTTPException(status_code=404, detail=f"Plugin path not found: {request.plugin_path}")
        
        # Create build directory
        build_dir = plugin_path / "build"
        build_dir.mkdir(exist_ok=True)
        
        # Copy source files to build directory
        src_files = list(plugin_path.glob("*.py"))
        for src_file in src_files:
            if src_file.name != "__pycache__":
                shutil.copy2(src_file, build_dir / src_file.name)
        
        # Copy config file
        config_file = plugin_path / "config.json"
        if config_file.exists():
            shutil.copy2(config_file, build_dir / config_file.name)
        
        # Try to compile Python files
        build_log = []
        for py_file in build_dir.glob("*.py"):
            try:
                compile(py_file.read_text(encoding='utf-8'), str(py_file), 'exec')
                build_log.append(f"Compiled: {py_file.name}")
            except SyntaxError as e:
                build_log.append(f"Compilation error in {py_file.name}: {e}")
        
        logger.info(f"Plugin build completed: {plugin_path}")
        
        return BuildResponse(
            success=True,
            build_path=str(build_dir),
            build_log="\n".join(build_log),
            message=f"Plugin built successfully at {build_dir}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Package Endpoint
@router.post("/package", response_model=PackageResponse, summary="Package plugin")
async def package_plugin(request: PackageRequest):
    """
    Package plugin for distribution
    
    Args:
        request: Package request data
        
    Returns:
        Package result
    """
    try:
        plugin_path = Path(request.plugin_path)
        
        if not plugin_path.exists():
            raise HTTPException(status_code=404, detail=f"Plugin path not found: {request.plugin_path}")
        
        # Load config to get plugin name and version
        config_file = plugin_path / "config.json"
        if config_file.exists():
            import json
            config = json.loads(config_file.read_text(encoding='utf-8'))
            plugin_name = config.get("plugin_name", plugin_path.name)
            version = request.version or config.get("version", "1.0.0")
        else:
            plugin_name = plugin_path.name
            version = request.version or "1.0.0"
        
        # Generate package name
        package_name = request.package_name or f"{plugin_name}-{version}"
        package_file = plugin_path / f"{package_name}.zip"
        
        # Create zip package
        with zipfile.ZipFile(package_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in plugin_path.rglob("*"):
                if file_path.is_file() and not file_path.name.endswith(".zip"):
                    arcname = file_path.relative_to(plugin_path)
                    zipf.write(file_path, arcname)
        
        package_size = package_file.stat().st_size
        
        logger.info(f"Plugin packaged: {package_file} ({package_size} bytes)")
        
        return PackageResponse(
            success=True,
            package_path=str(package_file),
            package_name=package_name,
            package_size=package_size,
            message=f"Plugin packaged successfully at {package_file}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error packaging plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))
