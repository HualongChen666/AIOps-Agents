# -*- coding: utf-8 -*-
"""
Standalone test runner for advanced router tests
This script runs the advanced router tests independently without depending on the main conftest.py
"""

import os
import subprocess
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

# Change to the tests/api directory
os.chdir(os.path.join(project_root, "tests", "api"))

# Test files to run
test_files = [
    "test_alerts_advanced_router.py",
    "test_ai_advanced_router.py",
    "test_integration_providers_router.py",
]

# Run pytest with minimal configuration
print("Running advanced router tests...")
print("=" * 80)

for test_file in test_files:
    print(f"\nRunning {test_file}...")
    print("-" * 80)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short", "-p", "no:warnings"],
        capture_output=False,
        text=True,
        shell=False,
    )
    if result.returncode != 0:
        print(f"[FAIL] {test_file} failed with return code {result.returncode}")
    else:
        print(f"[PASS] {test_file} passed")

print("\n" + "=" * 80)
print("Test run completed!")
