# -*- coding: utf-8 -*-
"""Sphinx configuration for AIOps Agent documentation."""

import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

project = "AIOps Agent"
copyright = "2026, AIOps Agent Contributors"
author = "AIOps Agent Contributors"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
]
templates_path = ["_templates"]
exclude_patterns = []
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
