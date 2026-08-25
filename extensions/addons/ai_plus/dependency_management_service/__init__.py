# -*- coding: utf-8 -*-
"""Dependency Management Service."""

from .config import Config
from .dependency_scanner import Dependency, DependencyScanner, ScanMetadata
from .update_manager import Conflict, UpdateManager, UpdateResult
from .version_checker import OutdatedPackage, VersionChecker, Vulnerability

__all__ = [
    "Config",
    "Dependency",
    "DependencyScanner",
    "ScanMetadata",
    "UpdateManager",
    "UpdateResult",
    "Conflict",
    "VersionChecker",
    "OutdatedPackage",
    "Vulnerability",
]
