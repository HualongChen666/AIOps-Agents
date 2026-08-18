# -*- coding: utf-8 -*-
"""Script to run workflow_service tests with proper configuration."""

import sys
import os
import subprocess

# Add the workflow_service directory to Python path
workflow_service_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../extensions/addons/operations/workflow_service'))
sys.path.insert(0, workflow_service_path)

# Change to the workflow_service directory
os.chdir(workflow_service_path)

# Run pytest with proper configuration
result = subprocess.run([
    sys.executable, '-m', 'pytest',
    os.path.join(os.path.dirname(__file__), 'test_config.py'),
    '-v', '--tb=short', '-x'
], capture_output=True, text=True)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print("\nReturn code:", result.returncode)

sys.exit(result.returncode)
