# -*- coding: utf-8 -*-
"""
Minimal conftest for advanced router tests
"""

import pytest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Basic pytest configuration
def pytest_configure(config):
    """Configure pytest for advanced router tests"""
    # Set any necessary environment variables
    os.environ.setdefault('TESTING', 'true')
