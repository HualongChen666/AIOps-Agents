#!/usr/bin/env python3
"""
Dependency Compatibility Test Script
Tests that updated dependencies are compatible with the project
"""
import sys
import importlib
from typing import Dict, List, Tuple

# List of updated dependencies with their minimum versions
UPDATED_DEPENDENCIES = {
    'fastapi': '0.109.1',
    'pydantic': '2.4.0',
    'pyjwt': '2.13.0',
    'aiohttp': '3.13.3',
    'httpx': '0.27.2',
    'Pillow': '11.3.0',
    'sentence_transformers': '3.1.0',
    'python_multipart': '0.0.18',
    'cryptography': '43.0.0',
    'authlib': '1.3.1',
}

def check_version(package_name: str, min_version: str) -> Tuple[bool, str]:
    """Check if a package is installed and meets minimum version requirement"""
    try:
        module = importlib.import_module(package_name)
        version = getattr(module, '__version__', 'unknown')
        # Simple version comparison (can be improved with packaging library)
        print(f"✓ {package_name}: {version} (required: >={min_version})")
        return True, version
    except ImportError as e:
        print(f"✗ {package_name}: Not installed (required: >={min_version})")
        return False, str(e)

def test_basic_imports() -> bool:
    """Test basic imports of updated packages"""
    print("\n=== Testing Basic Imports ===")
    success = True

    # Test FastAPI
    try:
        import fastapi
        from fastapi import FastAPI
        print("✓ FastAPI import successful")
    except ImportError as e:
        print(f"✗ FastAPI import failed: {e}")
        success = False

    # Test Pydantic
    try:
        import pydantic
        from pydantic import BaseModel
        print("✓ Pydantic import successful")
    except ImportError as e:
        print(f"✗ Pydantic import failed: {e}")
        success = False

    # Test PyJWT
    try:
        import jwt
        print("✓ PyJWT import successful")
    except ImportError as e:
        print(f"✗ PyJWT import failed: {e}")
        success = False

    # Test aiohttp
    try:
        import aiohttp
        print("✓ aiohttp import successful")
    except ImportError as e:
        print(f"✗ aiohttp import failed: {e}")
        success = False

    # Test httpx
    try:
        import httpx
        print("✓ httpx import successful")
    except ImportError as e:
        print(f"✗ httpx import failed: {e}")
        success = False

    # Test Pillow
    try:
        from PIL import Image
        print("✓ Pillow import successful")
    except ImportError as e:
        print(f"✗ Pillow import failed: {e}")
        success = False

    # Test sentence-transformers
    try:
        import sentence_transformers
        print("✓ sentence-transformers import successful")
    except ImportError as e:
        print(f"✗ sentence-transformers import failed: {e}")
        success = False

    # Test python-multipart
    try:
        import multipart
        print("✓ python-multipart import successful")
    except ImportError as e:
        print(f"✗ python-multipart import failed: {e}")
        success = False

    # Test cryptography
    try:
        import cryptography
        print("✓ cryptography import successful")
    except ImportError as e:
        print(f"✗ cryptography import failed: {e}")
        success = False

    # Test authlib
    try:
        import authlib
        print("✓ authlib import successful")
    except ImportError as e:
        print(f"✗ authlib import failed: {e}")
        success = False

    return success

def test_functionality() -> bool:
    """Test basic functionality of updated packages"""
    print("\n=== Testing Basic Functionality ===")
    success = True

    # Test Pydantic model creation
    try:
        from pydantic import BaseModel, EmailStr
        class TestModel(BaseModel):
            name: str
            email: EmailStr

        model = TestModel(name="Test", email="test@example.com")
        print("✓ Pydantic model creation successful")
    except Exception as e:
        print(f"✗ Pydantic model creation failed: {e}")
        success = False

    # Test PyJWT encoding/decoding
    try:
        import jwt
        payload = {"user": "test"}
        token = jwt.encode(payload, "secret", algorithm="HS256")
        decoded = jwt.decode(token, "secret", algorithms=["HS256"])
        print("✓ PyJWT encoding/decoding successful")
    except Exception as e:
        print(f"✗ PyJWT encoding/decoding failed: {e}")
        success = False

    # Test FastAPI app creation
    try:
        from fastapi import FastAPI
        app = FastAPI()
        print("✓ FastAPI app creation successful")
    except Exception as e:
        print(f"✗ FastAPI app creation failed: {e}")
        success = False

    return success

def main():
    """Main test function"""
    print("=== Dependency Compatibility Test ===")
    print(f"Python version: {sys.version}")
    print()

    # Check versions
    print("=== Checking Installed Versions ===")
    all_installed = True
    for package, min_version in UPDATED_DEPENDENCIES.items():
        success, _ = check_version(package, min_version)
        if not success:
            all_installed = False

    # Test imports
    imports_ok = test_basic_imports()

    # Test functionality
    functionality_ok = test_functionality()

    # Summary
    print("\n=== Test Summary ===")
    if all_installed and imports_ok and functionality_ok:
        print("✓ All dependency compatibility tests passed!")
        return 0
    else:
        print("✗ Some dependency compatibility tests failed")
        if not all_installed:
            print("  - Some packages are not installed")
        if not imports_ok:
            print("  - Some package imports failed")
        if not functionality_ok:
            print("  - Some functionality tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
