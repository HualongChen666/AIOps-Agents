# -*- coding: utf-8 -*-
"""Dependency scanner for Python projects."""

import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin
from urllib.request import urlopen

import toml

try:
    from .config import Config
except ImportError:
    from config import Config

logger = logging.getLogger(Config.SERVICE_NAME)


@dataclass
class Dependency:
    """Represents a Python dependency."""

    name: str
    version: str
    source: str  # requirements.txt, pyproject.toml, etc.
    extras: List[str] = field(default_factory=list)
    is_dev: bool = False
    url: Optional[str] = None
    hash: Optional[str] = None


@dataclass
class ScanMetadata:
    """Metadata about a dependency scan."""

    scan_time: str
    total_dependencies: int
    files_scanned: List[str]
    duration_seconds: float


class DependencyScanner:
    """Scanner for Python project dependencies."""

    def __init__(self) -> None:
        """Initialize the dependency scanner."""
        self._cache: Dict[str, tuple] = {}
        self._cache_duration = Config.CACHE_DURATION

    def scan_project(
        self, project_path: str, scan_types: Optional[List[str]] = None
    ) -> tuple[List[Dependency], ScanMetadata]:
        """Scan a project for dependencies.

        Args:
            project_path: Path to the project directory
            scan_types: List of file types to scan (e.g., ["requirements.txt", "pyproject.toml"])

        Returns:
            Tuple of (dependencies list, scan metadata)

        Raises:
            FileNotFoundError: If project path doesn't exist
            ValueError: If no dependency files found
        """
        start_time = time.time()
        project_path = Path(project_path).resolve()

        if not project_path.exists():
            raise FileNotFoundError(f"Project path not found: {project_path}")

        if not project_path.is_dir():
            raise ValueError(f"Project path is not a directory: {project_path}")

        # Determine which files to scan
        if scan_types is None:
            scan_types = Config.SUPPORTED_FILE_TYPES

        dependencies: List[Dependency] = []
        files_scanned: List[str] = []

        for file_type in scan_types:
            try:
                if file_type == "requirements.txt":
                    deps = self._scan_requirements_txt(project_path)
                elif file_type == "pyproject.toml":
                    deps = self._scan_pyproject_toml(project_path)
                elif file_type == "setup.py":
                    deps = self._scan_setup_py(project_path)
                elif file_type == "Pipfile":
                    deps = self._scan_pipfile(project_path)
                else:
                    logger.warning(f"Unsupported file type: {file_type}")
                    continue

                if deps:
                    dependencies.extend(deps)
                    files_scanned.append(file_type)
                    logger.info(f"Scanned {file_type}: found {len(deps)} dependencies")

            except Exception as e:
                logger.error(f"Error scanning {file_type}: {e}", exc_info=True)
                continue

        if not dependencies:
            raise ValueError(f"No dependencies found in project: {project_path}")

        # Remove duplicates (keep first occurrence)
        seen: Set[str] = set()
        unique_dependencies: List[Dependency] = []
        for dep in dependencies:
            key = f"{dep.name}:{dep.version}"
            if key not in seen:
                seen.add(key)
                unique_dependencies.append(dep)

        duration = time.time() - start_time
        metadata = ScanMetadata(
            scan_time=datetime.now().isoformat(),
            total_dependencies=len(unique_dependencies),
            files_scanned=files_scanned,
            duration_seconds=duration,
        )

        logger.info(f"Scan completed: {len(unique_dependencies)} dependencies in {duration:.2f}s")

        return unique_dependencies, metadata

    def _scan_requirements_txt(self, project_path: Path) -> List[Dependency]:
        """Scan requirements.txt file.

        Args:
            project_path: Path to the project directory

        Returns:
            List of dependencies
        """
        dependencies: List[Dependency] = []
        req_files = [
            project_path / "requirements.txt",
            project_path / "requirements-dev.txt",
            project_path / "dev-requirements.txt",
        ]

        for req_file in req_files:
            if not req_file.exists():
                continue

            is_dev = "dev" in req_file.name.lower()

            try:
                with open(req_file, "r", encoding="utf-8") as f:
                    content = f.read()

                deps = self._parse_requirements_content(content, is_dev, str(req_file.name))
                dependencies.extend(deps)

            except Exception as e:
                logger.error(f"Error reading {req_file}: {e}")

        return dependencies

    def _parse_requirements_content(
        self, content: str, is_dev: bool, source: str
    ) -> List[Dependency]:
        """Parse requirements file content.

        Args:
            content: File content
            is_dev: Whether this is a dev dependency
            source: Source file name

        Returns:
            List of dependencies
        """
        dependencies: List[Dependency] = []

        # Remove comments and empty lines
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            # Handle -r includes (skip for now)
            if line.startswith("-r"):
                continue

            # Handle -e editable installs
            if line.startswith("-e"):
                continue

            # Parse the requirement
            try:
                dep = self._parse_requirement_line(line, is_dev, source)
                if dep:
                    dependencies.append(dep)
            except Exception as e:
                logger.warning(f"Failed to parse requirement line: {line} - {e}")

        return dependencies

    def _parse_requirement_line(self, line: str, is_dev: bool, source: str) -> Optional[Dependency]:
        """Parse a single requirement line.

        Args:
            line: Requirement line
            is_dev: Whether this is a dev dependency
            source: Source file name

        Returns:
            Dependency object or None
        """
        # Remove environment markers
        line = re.sub(r";.*$", "", line).strip()

        # Parse package name and version specifier
        # Examples: "package>=1.0.0", "package==1.0.0", "package"
        match = re.match(r"^([a-zA-Z0-9_-]+)([><=!~]+.*)?$", line)
        if not match:
            return None

        name = match.group(1)
        version_spec = match.group(2) or ""

        # Extract extras
        extras = []
        extras_match = re.search(r"\[([^\]]+)\]", line)
        if extras_match:
            extras = [e.strip() for e in extras_match.group(1).split(",")]

        # Clean version specifier
        version = version_spec.strip("=<>~!") if version_spec else "*"

        return Dependency(
            name=name.lower(),
            version=version,
            source=source,
            extras=extras,
            is_dev=is_dev,
        )

    def _scan_pyproject_toml(self, project_path: Path) -> List[Dependency]:
        """Scan pyproject.toml file.

        Args:
            project_path: Path to the project directory

        Returns:
            List of dependencies
        """
        pyproject_file = project_path / "pyproject.toml"
        if not pyproject_file.exists():
            return []

        try:
            with open(pyproject_file, "r", encoding="utf-8") as f:
                data = toml.load(f)

            dependencies: List[Dependency] = []

            # Parse dependencies from [tool.poetry.dependencies]
            if "tool" in data and "poetry" in data["tool"]:
                poetry = data["tool"]["poetry"]
                if "dependencies" in poetry:
                    for name, spec in poetry["dependencies"].items():
                        if name.lower() == "python":
                            continue  # Skip python version requirement

                        version = "*"
                        extras = []

                        if isinstance(spec, str):
                            version = spec
                        elif isinstance(spec, dict):
                            version = spec.get("version", "*")
                            extras = spec.get("extras", [])

                        dependencies.append(
                            Dependency(
                                name=name.lower(),
                                version=version,
                                source="pyproject.toml",
                                extras=extras,
                                is_dev=False,
                            )
                        )

                # Parse dev dependencies from [tool.poetry.dev-dependencies]
                if "dev-dependencies" in poetry:
                    for name, spec in poetry["dev-dependencies"].items():
                        version = spec if isinstance(spec, str) else "*"
                        dependencies.append(
                            Dependency(
                                name=name.lower(),
                                version=version,
                                source="pyproject.toml",
                                is_dev=True,
                            )
                        )

            # Parse dependencies from [project.dependencies] (PEP 621)
            if "project" in data:
                if "dependencies" in data["project"]:
                    for dep_str in data["project"]["dependencies"]:
                        dep = self._parse_requirement_line(dep_str, False, "pyproject.toml")
                        if dep:
                            dependencies.append(dep)

                if "optional-dependencies" in data["project"]:
                    for group, deps in data["project"]["optional-dependencies"].items():
                        for dep_str in deps:
                            dep = self._parse_requirement_line(dep_str, True, "pyproject.toml")
                            if dep:
                                dependencies.append(dep)

            return dependencies

        except Exception as e:
            logger.error(f"Error parsing pyproject.toml: {e}", exc_info=True)
            return []

    def _scan_setup_py(self, project_path: Path) -> List[Dependency]:
        """Scan setup.py file.

        Args:
            project_path: Path to the project directory

        Returns:
            List of dependencies
        """
        setup_file = project_path / "setup.py"
        if not setup_file.exists():
            return []

        try:
            with open(setup_file, "r", encoding="utf-8") as f:
                content = f.read()

            dependencies: List[Dependency] = []

            # Try to extract install_requires
            install_requires_match = re.search(
                r"install_requires\s*=\s*\[(.*?)\]", content, re.DOTALL
            )
            if install_requires_match:
                reqs_str = install_requires_match.group(1)
                # Extract strings from the list
                reqs = re.findall(r'["\']([^"\']+)["\']', reqs_str)
                for req in reqs:
                    dep = self._parse_requirement_line(req, False, "setup.py")
                    if dep:
                        dependencies.append(dep)

            # Try to extract extras_require
            extras_require_match = re.search(
                r"extras_require\s*=\s*\{(.*?)\}", content, re.DOTALL
            )
            if extras_require_match:
                extras_str = extras_require_match.group(1)
                # Extract all requirement strings
                reqs = re.findall(r'["\']([^"\']+)["\']', extras_str)
                for req in reqs:
                    dep = self._parse_requirement_line(req, True, "setup.py")
                    if dep:
                        dependencies.append(dep)

            return dependencies

        except Exception as e:
            logger.error(f"Error parsing setup.py: {e}", exc_info=True)
            return []

    def _scan_pipfile(self, project_path: Path) -> List[Dependency]:
        """Scan Pipfile (Pipenv).

        Args:
            project_path: Path to the project directory

        Returns:
            List of dependencies
        """
        pipfile = project_path / "Pipfile"
        if not pipfile.exists():
            return []

        try:
            with open(pipfile, "r", encoding="utf-8") as f:
                data = toml.load(f)

            dependencies: List[Dependency] = []

            # Parse [packages]
            if "packages" in data:
                for name, spec in data["packages"].items():
                    version = "*"
                    if isinstance(spec, str):
                        version = spec
                    elif isinstance(spec, dict):
                        version = spec.get("version", "*")

                    dependencies.append(
                        Dependency(
                            name=name.lower(),
                            version=version,
                            source="Pipfile",
                            is_dev=False,
                        )
                    )

            # Parse [dev-packages]
            if "dev-packages" in data:
                for name, spec in data["dev-packages"].items():
                    version = spec if isinstance(spec, str) else "*"
                    dependencies.append(
                        Dependency(
                            name=name.lower(),
                            version=version,
                            source="Pipfile",
                            is_dev=True,
                        )
                    )

            return dependencies

        except Exception as e:
            logger.error(f"Error parsing Pipfile: {e}", exc_info=True)
            return []

    def get_dependency_tree(self, project_path: str, package_name: str, depth: int = 3) -> Dict:
        """Get the dependency tree for a package.

        Args:
            project_path: Path to the project directory
            package_name: Name of the package to get tree for
            depth: Maximum depth to traverse

        Returns:
            Dependency tree as a nested dictionary
        """
        # This is a simplified implementation
        # In a real implementation, you would use pipdeptree or similar tool
        try:
            import subprocess

            result = subprocess.run(
                ["pipdeptree", "-p", package_name],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return self._parse_pipdeptree_output(result.stdout, depth)
            else:
                logger.warning(f"pipdeptree failed: {result.stderr}")
                return {"name": package_name, "version": "unknown", "children": []}

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Could not run pipdeptree: {e}")
            return {"name": package_name, "version": "unknown", "children": []}

    def _parse_pipdeptree_output(self, output: str, depth: int) -> Dict:
        """Parse pipdeptree output.

        Args:
            output: pipdeptree stdout
            depth: Maximum depth

        Returns:
            Parsed tree structure
        """
        # Simplified parsing
        lines = output.strip().split("\n")
        if not lines:
            return {"name": "unknown", "version": "unknown", "children": []}

        first_line = lines[0]
        match = re.match(r"(\w+)==([\d.]+)", first_line)
        if match:
            name, version = match.groups()
        else:
            name, version = "unknown", "unknown"

        return {
            "name": name,
            "version": version,
            "children": [],  # Would parse nested dependencies here
        }
