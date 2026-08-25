# -*- coding: utf-8 -*-
"""Version Manager for Release Management Service."""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

try:
    from .config import Config
except ImportError:
    from config import Config

logger = logging.getLogger(Config.SERVICE_NAME)


@dataclass
class Version:
    """Represents a semantic version."""
    id: str = field(default_factory=lambda: str(uuid4()))
    project_name: str = ""
    version: str = ""
    major: int = 0
    minor: int = 0
    patch: int = 0
    pre_release: str = ""
    pre_release_number: int = 0
    build_metadata: str = ""
    is_latest: bool = False
    created_at: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))

    def to_dict(self) -> Dict:
        """Convert version to dictionary."""
        return {
            "id": self.id,
            "project_name": self.project_name,
            "version": self.version,
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "pre_release": self.pre_release,
            "pre_release_number": self.pre_release_number,
            "build_metadata": self.build_metadata,
            "is_latest": self.is_latest,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Version":
        """Create version from dictionary."""
        return cls(**data)


class VersionManager:
    """Manages semantic versioning for projects."""

    def __init__(self):
        """Initialize the version manager."""
        self._versions: Dict[str, List[Version]] = {}  # project_name -> list of versions
        self._version_index: Dict[str, Version] = {}  # version_id -> version

    def parse_version(self, version_string: str) -> Dict:
        """Parse a semantic version string.

        Args:
            version_string: Version string to parse (e.g., "1.2.3", "2.0.0-alpha.1", "3.1.0+build.123")

        Returns:
            Dictionary with parsed version components

        Raises:
            ValueError: If version string is invalid
        """
        # Semantic versioning pattern: major.minor.patch[-pre-release][+build-metadata]
        pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9]+)(?:\.(\d+))?)?(?:\+([a-zA-Z0-9.-]+))?$'
        match = re.match(pattern, version_string)

        if not match:
            raise ValueError(f"Invalid semantic version: {version_string}")

        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3))
        pre_release = match.group(4) or ""
        pre_release_number = int(match.group(5)) if match.group(5) else 0
        build_metadata = match.group(6) or ""

        return {
            "major": major,
            "minor": minor,
            "patch": patch,
            "pre_release": pre_release,
            "pre_release_number": pre_release_number,
            "build_metadata": build_metadata,
        }

    def format_version(
        self,
        major: int,
        minor: int,
        patch: int,
        pre_release: str = "",
        pre_release_number: int = 0,
        build_metadata: str = "",
    ) -> str:
        """Format version components into a version string.

        Args:
            major: Major version number
            minor: Minor version number
            patch: Patch version number
            pre_release: Pre-release identifier (e.g., "alpha", "beta", "rc")
            pre_release_number: Pre-release number
            build_metadata: Build metadata

        Returns:
            Formatted version string
        """
        version = f"{major}.{minor}.{patch}"
        if pre_release:
            if pre_release_number > 0:
                version += f"-{pre_release}.{pre_release_number}"
            else:
                version += f"-{pre_release}"
        if build_metadata:
            version += f"+{build_metadata}"
        return version

    def create_version(
        self,
        project_name: str,
        base_version: Optional[str] = None,
        increment_type: str = "patch",
        pre_release: str = "",
        pre_release_number: int = 0,
        build_metadata: str = "",
    ) -> Version:
        """Create a new version.

        Args:
            project_name: Name of the project
            base_version: Base version to increment from (if None, uses latest or default)
            increment_type: Type of increment (major, minor, patch)
            pre_release: Pre-release identifier
            pre_release_number: Pre-release number
            build_metadata: Build metadata

        Returns:
            Created Version object

        Raises:
            ValueError: If parameters are invalid
        """
        if project_name not in self._versions:
            self._versions[project_name] = []

        # Determine base version
        if base_version:
            parsed = self.parse_version(base_version)
            major, minor, patch = parsed["major"], parsed["minor"], parsed["patch"]
        elif self._versions[project_name]:
            # Use latest version
            latest = self._versions[project_name][-1]
            major, minor, patch = latest.major, latest.minor, latest.patch
        else:
            # Use default version
            parsed = self.parse_version(Config.DEFAULT_VERSION)
            major, minor, patch = parsed["major"], parsed["minor"], parsed["patch"]

        # Increment version
        if increment_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif increment_type == "minor":
            minor += 1
            patch = 0
        elif increment_type == "patch":
            patch += 1
        else:
            raise ValueError(f"Invalid increment type: {increment_type}")

        # Format version string
        version_string = self.format_version(
            major, minor, patch, pre_release, pre_release_number, build_metadata
        )

        # Create version object
        version = Version(
            project_name=project_name,
            version=version_string,
            major=major,
            minor=minor,
            patch=patch,
            pre_release=pre_release,
            pre_release_number=pre_release_number,
            build_metadata=build_metadata,
        )

        # Mark previous latest as not latest
        if self._versions[project_name]:
            self._versions[project_name][-1].is_latest = False

        # Mark new version as latest
        version.is_latest = True

        # Store version
        self._versions[project_name].append(version)
        self._version_index[version.id] = version

        logger.info(f"Created version {version_string} for project {project_name}")
        return version

    def get_version(self, project_name: str, version_string: str) -> Optional[Version]:
        """Get a specific version.

        Args:
            project_name: Name of the project
            version_string: Version string to find

        Returns:
            Version object if found, None otherwise
        """
        if project_name not in self._versions:
            return None

        for version in self._versions[project_name]:
            if version.version == version_string:
                return version
        return None

    def get_version_by_id(self, version_id: str) -> Optional[Version]:
        """Get version by ID.

        Args:
            version_id: Version ID

        Returns:
            Version object if found, None otherwise
        """
        return self._version_index.get(version_id)

    def list_versions(
        self, project_name: str, limit: int = 100, offset: int = 0
    ) -> List[Version]:
        """List versions for a project.

        Args:
            project_name: Name of the project
            limit: Maximum number of versions to return
            offset: Number of versions to skip

        Returns:
            List of Version objects
        """
        if project_name not in self._versions:
            return []

        versions = self._versions[project_name][offset : offset + limit]
        return versions

    def get_latest_version(self, project_name: str) -> Optional[Version]:
        """Get the latest version for a project.

        Args:
            project_name: Name of the project

        Returns:
            Latest Version object if found, None otherwise
        """
        if project_name not in self._versions or not self._versions[project_name]:
            return None
        return self._versions[project_name][-1]

    def compare_versions(self, version1: str, version2: str) -> str:
        """Compare two version strings.

        Args:
            version1: First version string
            version2: Second version string

        Returns:
            "greater" if version1 > version2, "equal" if equal, "less" if version1 < version2
        """
        v1 = self.parse_version(version1)
        v2 = self.parse_version(version2)

        # Compare major, minor, patch
        if v1["major"] != v2["major"]:
            return "greater" if v1["major"] > v2["major"] else "less"
        if v1["minor"] != v2["minor"]:
            return "greater" if v1["minor"] > v2["minor"] else "less"
        if v1["patch"] != v2["patch"]:
            return "greater" if v1["patch"] > v2["patch"] else "less"

        # Compare pre-release
        if v1["pre_release"] and not v2["pre_release"]:
            return "less"  # Pre-release is less than release
        if not v1["pre_release"] and v2["pre_release"]:
            return "greater"  # Release is greater than pre-release
        if v1["pre_release"] and v2["pre_release"]:
            if v1["pre_release"] != v2["pre_release"]:
                # Simple comparison for common pre-release types
                pre_order = {"alpha": 0, "beta": 1, "rc": 2}
                v1_order = pre_order.get(v1["pre_release"], 99)
                v2_order = pre_order.get(v2["pre_release"], 99)
                if v1_order != v2_order:
                    return "greater" if v1_order > v2_order else "less"
            if v1["pre_release_number"] != v2["pre_release_number"]:
                return "greater" if v1["pre_release_number"] > v2["pre_release_number"] else "less"

        return "equal"

    def get_version_difference(self, version1: str, version2: str) -> int:
        """Get the numeric difference between two versions.

        Args:
            version1: First version string
            version2: Second version string

        Returns:
            Numeric difference (positive if version1 > version2, negative if less)
        """
        v1 = self.parse_version(version1)
        v2 = self.parse_version(version2)

        # Calculate a numeric value for comparison
        val1 = v1["major"] * 1000000 + v1["minor"] * 1000 + v1["patch"]
        val2 = v2["major"] * 1000000 + v2["minor"] * 1000 + v2["patch"]

        return val1 - val2

    def delete_version(self, version_id: str) -> bool:
        """Delete a version.

        Args:
            version_id: Version ID to delete

        Returns:
            True if deleted, False if not found
        """
        if version_id not in self._version_index:
            return False

        version = self._version_index[version_id]
        project_name = version.project_name

        # Remove from project list
        if project_name in self._versions:
            self._versions[project_name] = [
                v for v in self._versions[project_name] if v.id != version_id
            ]

        # Update latest flag
        if self._versions[project_name]:
            self._versions[project_name][-1].is_latest = True

        # Remove from index
        del self._version_index[version_id]

        logger.info(f"Deleted version {version.version} for project {project_name}")
        return True

    def get_all_projects(self) -> List[str]:
        """Get list of all projects.

        Returns:
            List of project names
        """
        return list(self._versions.keys())
