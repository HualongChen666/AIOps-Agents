#!/usr/bin/env python3
"""
Test script to verify dependency upgrades and data processing functionality.
This script tests the upgraded dependencies to ensure they work correctly.
"""

import sys
import traceback


def test_pandas_numpy():
    """Test pandas and numpy data processing functionality."""
    print("Testing pandas and numpy...")
    try:
        import pandas as pd
        import numpy as np
        
        # Test basic numpy operations
        arr = np.array([1, 2, 3, 4, 5])
        assert arr.sum() == 15, "Numpy sum operation failed"
        
        # Test pandas DataFrame operations
        df = pd.DataFrame({
            'A': [1, 2, 3],
            'B': [4, 5, 6]
        })
        assert len(df) == 3, "DataFrame creation failed"
        assert df['A'].sum() == 6, "DataFrame column sum failed"
        
        # Test pandas read/write operations
        df_csv = pd.DataFrame({'x': [1, 2, 3], 'y': [4, 5, 6]})
        
        print(f"[OK] pandas version: {pd.__version__}")
        print(f"[OK] numpy version: {np.__version__}")
        print("[OK] pandas and numpy tests passed")
        return True
    except Exception as e:
        print(f"[FAIL] pandas/numpy test failed: {e}")
        traceback.print_exc()
        return False


def test_pillow():
    """Test Pillow image processing functionality."""
    print("\nTesting Pillow...")
    try:
        from PIL import Image
        import io
        
        # Create a simple image
        img = Image.new('RGB', (100, 100), color='red')
        assert img.size == (100, 100), "Image creation failed"
        
        # Test image operations
        img_resized = img.resize((50, 50))
        assert img_resized.size == (50, 50), "Image resize failed"
        
        # Test image save/load
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_loaded = Image.open(buffer)
        assert img_loaded.size == (100, 100), "Image save/load failed"
        
        print(f"[OK] Pillow version: {Image.__version__}")
        print("[OK] Pillow tests passed")
        return True
    except Exception as e:
        print(f"[FAIL] Pillow test failed: {e}")
        traceback.print_exc()
        return False


def test_http_libraries():
    """Test HTTP client libraries."""
    print("\nTesting HTTP libraries...")
    try:
        import httpx
        import aiohttp
        import requests
        import urllib3
        
        print(f"[OK] httpx version: {httpx.__version__}")
        print(f"[OK] aiohttp version: {aiohttp.__version__}")
        print(f"[OK] requests version: {requests.__version__}")
        print(f"[OK] urllib3 version: {urllib3.__version__}")
        print("[OK] HTTP libraries tests passed")
        return True
    except Exception as e:
        print(f"[FAIL] HTTP libraries test failed: {e}")
        traceback.print_exc()
        return False


def test_database_libraries():
    """Test database libraries."""
    print("\nTesting database libraries...")
    try:
        import sqlalchemy
        import asyncpg
        
        print(f"[OK] sqlalchemy version: {sqlalchemy.__version__}")
        print(f"[OK] asyncpg version: {asyncpg.__version__}")
        print("[OK] Database libraries tests passed")
        return True
    except Exception as e:
        print(f"[FAIL] Database libraries test failed: {e}")
        traceback.print_exc()
        return False


def test_ai_libraries():
    """Test AI/ML libraries."""
    print("\nTesting AI/ML libraries...")
    try:
        import langchain
        import openai
        import anthropic
        
        print(f"[OK] langchain version: {langchain.__version__}")
        print(f"[OK] openai version: {openai.__version__}")
        print(f"[OK] anthropic version: {anthropic.__version__}")
        print("[OK] AI/ML libraries tests passed")
        return True
    except Exception as e:
        print(f"[FAIL] AI/ML libraries test failed: {e}")
        traceback.print_exc()
        return False


def test_core_libraries():
    """Test core framework libraries."""
    print("\nTesting core libraries...")
    try:
        import fastapi
        import pydantic
        import redis
        
        print(f"[OK] fastapi version: {fastapi.__version__}")
        print(f"[OK] pydantic version: {pydantic.__version__}")
        print(f"[OK] redis version: {redis.__version__}")
        print("[OK] Core libraries tests passed")
        return True
    except Exception as e:
        print(f"[FAIL] Core libraries test failed: {e}")
        traceback.print_exc()
        return False


def test_security_libraries():
    """Test security libraries."""
    print("\nTesting security libraries...")
    try:
        import cryptography
        
        print(f"[OK] cryptography version: {cryptography.__version__}")
        print("[OK] Security libraries tests passed")
        return True
    except Exception as e:
        print(f"[FAIL] Security libraries test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all dependency tests."""
    print("=" * 60)
    print("Dependency Upgrade Verification Tests")
    print("=" * 60)
    
    results = {
        'pandas_numpy': test_pandas_numpy(),
        'pillow': test_pillow(),
        'http_libraries': test_http_libraries(),
        'database_libraries': test_database_libraries(),
        'ai_libraries': test_ai_libraries(),
        'core_libraries': test_core_libraries(),
        'security_libraries': test_security_libraries(),
    }
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name:20s}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[OK] All dependency upgrade tests passed!")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
