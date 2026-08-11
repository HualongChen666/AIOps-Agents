# -*- coding: utf-8 -*-
"""Productization extensions for the AIOps agent (hardware remediation, etc.)."""

from .plugin_loader import get_addon, list_addons, load_all_addons

__all__ = ["get_addon", "list_addons", "load_all_addons"]
