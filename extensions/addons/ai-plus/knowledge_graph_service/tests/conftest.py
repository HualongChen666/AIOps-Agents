# -*- coding: utf-8 -*-
"""Pytest configuration for knowledge_graph_service tests."""

import sys
import os
from pathlib import Path

# Add the project root to the Python path for imports
project_root = str(Path(__file__).parent.parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
