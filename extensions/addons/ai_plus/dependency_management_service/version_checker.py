# -*- coding: utf-8 -*-
"""Version checker for Python packages."""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

try:
    from .config import Config
    from .dependency_scanner import Dependency
except ImportError:
    from config import Config
    from dependency_scanner import Dependency

logger = logging.getLogger(Config.SERVICE_NAME)


@dataclass
class OutdatedPackage:
    """Represents an outdated package."""

    name: str
    current_version: str
    latest_version: str
    latest_release_date: str
    available_versions: List[str] = field(default_factory=list)
    is_major_update: bool = False
    is_security_update: bool = False


@dataclass
class Vulnerability:
    """Represents a security vulnerability."""

    package_name: str
    affected_versions: str
    severity: str
    cve_id: str
    description: str
    published_date: str
    fixed_in_version: Optional[str] = None
    references: List[str] = field(default_factory=list)


class VersionChecker:
    """Checker for package versions and security vulnerabilities."""

    def __init__(self) -> None:
        """Initialize the version checker."""
        self._cache: Dict[str, tuple] = {}
        self._cache_duration = Config.CACHE_DURATION
        self._pypi_api_url = Config.PYPI_API_URL

    def check_outdated(
        self, dependencies: List[Dependency], package_names: Optional[List[str]] = None
    ) -> List[OutdatedPackage]:
        """Check for outdated packages.

        Args:
            dependencies: List of dependencies to check
            package_names: Optional list of specific packages to check

        Returns:
            List of outdated packages
        """
        outdated: List[OutdatedPackage] = []

        # Filter packages if specific names provided
        if package_names:
            package_names_lower = [p.lower() for p in package_names]
            dependencies = [d for d in dependencies if d.name in package_names_lower]

        for dep in dependencies:
            try:
                latest_info = self._get_latest_version(dep.name)
                if not latest_info:
                    continue

                current_version = self._normalize_version(dep.version)
                latest_version = latest_info["version"]

                if self._is_version_outdated(current_version, latest_version):
                    available_versions = latest_info.get("versions", [])
                    is_major = self._is_major_update(current_version, latest_version)
                    is_security = self._is_security_update(dep.name, current_version, latest_version)

                    outdated.append(
                        OutdatedPackage(
                            name=dep.name,
                            current_version=dep.version,
                            latest_version=latest_version,
                            latest_release_date=latest_info.get("upload_time", ""),
                            available_versions=available_versions,
                            is_major_update=is_major,
                            is_security_update=is_security,
                        )
                    )
                    logger.info(f"Outdated package found: {dep.name} ({dep.version} -> {latest_version})")

            except Exception as e:
                logger.error(f"Error checking version for {dep.name}: {e}", exc_info=True)
                continue

        return outdated

    def check_vulnerabilities(
        self,
        dependencies: List[Dependency],
        package_names: Optional[List[str]] = None,
        severity_level: str = "medium",
    ) -> List[Vulnerability]:
        """Check for security vulnerabilities.

        Args:
            dependencies: List of dependencies to check
            package_names: Optional list of specific packages to check
            severity_level: Minimum severity level to report (low, medium, high, critical)

        Returns:
            List of vulnerabilities
        """
        vulnerabilities: List[Vulnerability] = []

        # Filter packages if specific names provided
        if package_names:
            package_names_lower = [p.lower() for p in package_names]
            dependencies = [d for d in dependencies if d.name in package_names_lower]

        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_severity = severity_order.get(severity_level.lower(), 1)

        for dep in dependencies:
            try:
                vulns = self._get_package_vulnerabilities(dep.name)
                for vuln in vulns:
                    vuln_severity = vuln.get("severity", "low").lower()
                    if severity_order.get(vuln_severity, 0) >= min_severity:
                        # Check if current version is affected
                        if self._is_version_affected(dep.version, vuln.get("affected_versions", "")):
                            vulnerabilities.append(
                                Vulnerability(
                                    package_name=dep.name,
                                    affected_versions=vuln.get("affected_versions", ""),
                                    severity=vuln_severity,
                                    cve_id=vuln.get("cve_id", ""),
                                    description=vuln.get("description", ""),
                                    published_date=vuln.get("published_date", ""),
                                    fixed_in_version=vuln.get("fixed_in_version"),
                                    references=vuln.get("references", []),
                                )
                            )
                            logger.warning(
                                f"Vulnerability found in {dep.name}: {vuln.get('cve_id', 'N/A')}"
                            )

            except Exception as e:
                logger.error(f"Error checking vulnerabilities for {dep.name}: {e}", exc_info=True)
                continue

        return vulnerabilities

    def _get_latest_version(self, package_name: str) -> Optional[Dict]:
        """Get the latest version information for a package from PyPI.

        Args:
            package_name: Name of the package

        Returns:
            Dictionary with version info or None
        """
        # Check cache
        cache_key = f"latest:{package_name}"
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if time.time() - cached_time < self._cache_duration:
                return cached_data

        try:
            url = f"{self._pypi_api_url}/{package_name}/json"
            with urlopen(url, timeout=Config.CHECK_TIMEOUT) as response:
                data = json.loads(response.read().decode())

            releases = data.get("releases", {})
            versions = sorted(releases.keys(), key=self._version_key, reverse=True)

            if not versions:
                return None

            latest_version = versions[0]
            latest_release_info = releases.get(latest_version, [])
            upload_time = ""
            if latest_release_info:
                upload_time = latest_release_info[0].get("upload_time", "")

            result = {
                "version": latest_version,
                "versions": versions[:10],  # Top 10 versions
                "upload_time": upload_time,
            }

            # Cache the result
            self._cache[cache_key] = (result, time.time())

            return result

        except (HTTPError, URLError, json.JSONDecodeError) as e:
            logger.error(f"Error fetching latest version for {package_name}: {e}")
            return None

    def _get_package_vulnerabilities(self, package_name: str) -> List[Dict]:
        """Get vulnerability information for a package.

        Args:
            package_name: Name of the package

        Returns:
            List of vulnerability dictionaries
        """
        # Check cache
        cache_key = f"vulns:{package_name}"
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if time.time() - cached_time < self._cache_duration:
                return cached_data

        try:
            # Try to fetch from PyPI (which may include vulnerability info)
            url = f"{self._pypi_api_url}/{package_name}/json"
            with urlopen(url, timeout=Config.CHECK_TIMEOUT) as response:
                data = json.loads(response.read().decode())

            vulnerabilities = []

            # Check for vulnerability info in the response
            # Note: PyPI doesn't directly provide vulnerability info
            # In a real implementation, you would use a dedicated vulnerability database
            # like OSV, GitHub Advisory Database, or Snyk

            # For now, we'll return empty list
            # In production, integrate with:
            # - https://osv.dev/
            # - https://github.com/advisories
            # - https://pypi.org/pypi/<package>/json (may have some links)

            # Cache the result
            self._cache[cache_key] = (vulnerabilities, time.time())

            return vulnerabilities

        except (HTTPError, URLError, json.JSONDecodeError) as e:
            logger.error(f"Error fetching vulnerabilities for {package_name}: {e}")
            return []

    def _normalize_version(self, version: str) -> str:
        """Normalize a version string for comparison.

        Args:
            version: Version string (may include specifiers like >=, ==, etc.)

        Returns:
            Normalized version string
        """
        # Remove version specifiers
        version = re.sub(r"[><=!~\[\]]", "", version)
        version = version.strip()

        # Handle wildcards
        if version == "*" or version == "":
            return "0.0.0"

        return version

    def _version_key(self, version: str) -> tuple:
        """Convert version string to comparable tuple.

        Args:
            version: Version string

        Returns:
            Tuple of version components
        """
        # Remove any pre-release identifiers
        version = re.split(r"[a-zA-Z]", version)[0]
        parts = version.split(".")

        # Convert to integers, pad with zeros
        key = []
        for part in parts[:3]:  # Only consider major.minor.patch
            try:
                key.append(int(part))
            except ValueError:
                key.append(0)

        # Pad to ensure consistent length
        while len(key) < 3:
            key.append(0)

        return tuple(key)

    def _is_version_outdated(self, current: str, latest: str) -> bool:
        """Check if current version is outdated.

        Args:
            current: Current version
            latest: Latest version

        Returns:
            True if outdated, False otherwise
        """
        current_key = self._version_key(current)
        latest_key = self._version_key(latest)

        return current_key < latest_key

    def _is_major_update(self, current: str, latest: str) -> bool:
        """Check if update is a major version update.

        Args:
            current: Current version
            latest: Latest version

        Returns:
            True if major update, False otherwise
        """
        current_key = self._version_key(current)
        latest_key = self._version_key(latest)

        return latest_key[0] > current_key[0]

    def _is_security_update(self, package_name: str, current: str, latest: str) -> bool:
        """Check if update is a security update.

        Args:
            package_name: Package name
            current: Current version
            latest: Latest version

        Returns:
            True if security update, False otherwise
        """
        # This would check if there are security vulnerabilities
        # in the current version that are fixed in the latest
        try:
            vulns = self._get_package_vulnerabilities(package_name)
            for vuln in vulns:
                if self._is_version_affected(current, vuln.get("affected_versions", "")):
                    fixed_version = vuln.get("fixed_in_version")
                    if fixed_version and self._version_key(fixed_version) <= self._version_key(
                        latest
                    ):
                        return True
        except Exception:
            pass

        return False

    def _is_version_affected(self, version: str, affected_versions: str) -> bool:
        """Check if a version is affected by a vulnerability.

        Args:
            version: Version to check
            affected_versions: Affected version range

        Returns:
            True if affected, False otherwise
        """
        if not affected_versions:
            return False

        # Simple check - in production, use proper version range parsing
        # This is a simplified implementation
        version = self._normalize_version(version)

        # Check if version is in the affected range
        # Examples: "< 1.0.0", ">= 2.0.0, < 3.0.0"
        if "<" in affected_versions:
            parts = affected_versions.split("<")
            if len(parts) == 2:
                threshold = self._normalize_version(parts[1].strip())
                return self._version_key(version) < self._version_key(threshold)

        if ">" in affected_versions:
            parts = affected_versions.split(">")
            if len(parts) == 2:
                threshold = self._normalize_version(parts[1].strip())
                return self._version_key(version) > self._version_key(threshold)

        return False

    def resolve_version_conflict(
        self, package_name: str, required_versions: List[str]
    ) -> Optional[str]:
        """Resolve version conflicts for a package.

        Args:
            package_name: Package name
            required_versions: List of required version specifiers

        Returns:
            Resolved version or None if unresolvable
        """
        if not required_versions:
            return None

        # Get all available versions
        latest_info = self._get_latest_version(package_name)
        if not latest_info:
            return None

        available_versions = latest_info.get("versions", [])

        # Find the latest version that satisfies all requirements
        for version in available_versions:
            if all(self._satisfies_requirement(version, req) for req in required_versions):
                return version

        return None

    def _satisfies_requirement(self, version: str, requirement: str) -> bool:
        """Check if a version satisfies a requirement.

        Args:
            version: Version to check
            requirement: Requirement specifier (e.g., ">=1.0.0", "==2.0.0")

        Returns:
            True if satisfies, False otherwise
        """
        version_key = self._version_key(version)

        # Parse requirement
        if ">=" in requirement:
            threshold = self._normalize_version(requirement.replace(">=", "").strip())
            return version_key >= self._version_key(threshold)
        elif "<=" in requirement:
            threshold = self._normalize_version(requirement.replace("<=", "").strip())
            return version_key <= self._version_key(threshold)
        elif ">" in requirement:
            threshold = self._normalize_version(requirement.replace(">", "").strip())
            return version_key > self._version_key(threshold)
        elif "<" in requirement:
            threshold = self._normalize_version(requirement.replace("<", "").strip())
            return version_key < self._version_key(threshold)
        elif "==" in requirement:
            threshold = self._normalize_version(requirement.replace("==", "").strip())
            return version_key == self._version_key(threshold)
        elif "~=" in requirement:
            # Compatible release (e.g., ~=1.2.3 means >=1.2.3, <2.0.0)
            threshold = self._normalize_version(requirement.replace("~=", "").strip())
            threshold_key = self._version_key(threshold)
            return version_key >= threshold_key and version_key[0] == threshold_key[0]
        else:
            # No specifier, any version is fine
            return True
