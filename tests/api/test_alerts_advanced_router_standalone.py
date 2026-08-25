# -*- coding: utf-8 -*-
"""
Standalone test runner for alerts_advanced_router tests
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Run the tests
if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__.replace("_standalone", ""), "-v", "--tb=short"]))
