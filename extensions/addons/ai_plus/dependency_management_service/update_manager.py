# -*- coding: utf-8 -*-
"""Update manager for Python dependencies."""

import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from .config import Config
    from .dependency_scanner import Dependency
except ImportError:
    from config import Config
    from dependency_scanner import Dependency

logger = logging.getLogger(Config.SERVICE_NAME)


@dataclass
class UpdateResult:
    """Result of a package update."""

    package_name: str
    old_version: str
    new_version: str
    success: bool
    message: str


@dataclass
class Conflict:
    """Represents a dependency conflict."""

    package_name: str
    conflict_type: str  # version, dependency, circular
    conflicting_packages: List[str]
    description: str
    resolution_suggestion: str


class UpdateManager:
    """Manager for updating dependencies."""

    def __init__(self) -> None:
        """Initialize the update manager."""
        self._backup_dir = Path(tempfile.gettempdir()) / "dependency_backups"

    def update_dependencies(
        self,
        project_path: str,
        package_names: Optional[List[str]] = None,
        update_type: str = "all",
        dry_run: bool = False,
    ) -> tuple[List[UpdateResult], List[str]]:
        """Update dependencies in a project.

        Args:
            project_path: Path to the project directory
            package_names: Specific packages to update (None for all)
            update_type: Type of update (all, specific, security)
            dry_run: If True, only simulate the update

        Returns:
            Tuple of (update results, warnings)
        """
        project_path = Path(project_path).resolve()

        if not project_path.exists():
            raise FileNotFoundError(f"Project path not found: {project_path}")

        results: List[UpdateResult] = []
        warnings: List[str] = []

        # Create backup if needed
        if Config.BACKUP_BEFORE_UPDATE and not dry_run:
            backup_path = self._create_backup(project_path)
            logger.info(f"Created backup at: {backup_path}")

        try:
            if update_type == "all":
                # Update all packages
                if dry_run:
                    results.append(
                        UpdateResult(
                            package_name="all",
                            old_version="*",
                            new_version="latest",
                            success=True,
                            message="Dry run: would update all packages",
                        )
                    )
                else:
                    result = self._update_all_packages(project_path)
                    results.extend(result)

            elif update_type == "specific":
                # Update specific packages
                if not package_names:
                    raise ValueError("package_names required for specific update")

                for pkg_name in package_names:
                    try:
                        if dry_run:
                            results.append(
                                UpdateResult(
                                    package_name=pkg_name,
                                    old_version="unknown",
                                    new_version="latest",
                                    success=True,
                                    message=f"Dry run: would update {pkg_name}",
                                )
                            )
                        else:
                            result = self._update_package(project_path, pkg_name)
                            results.append(result)
                    except Exception as e:
                        results.append(
                            UpdateResult(
                                package_name=pkg_name,
                                old_version="unknown",
                                new_version="unknown",
                                success=False,
                                message=str(e),
                            )
                        )
                        warnings.append(f"Failed to update {pkg_name}: {e}")

            elif update_type == "security":
                # Update only security-related packages
                if dry_run:
                    results.append(
                        UpdateResult(
                            package_name="security",
                            old_version="*",
                            new_version="latest",
                            success=True,
                            message="Dry run: would update security packages",
                        )
                    )
                else:
                    result = self._update_security_packages(project_path)
                    results.extend(result)

            else:
                raise ValueError(f"Unknown update type: {update_type}")

        except Exception as e:
            logger.error(f"Error during update: {e}", exc_info=True)
            # Restore backup if available
            if Config.BACKUP_BEFORE_UPDATE and not dry_run:
                self._restore_backup(project_path, backup_path)
            raise

        return results, warnings

    def _update_all_packages(self, project_path: Path) -> List[UpdateResult]:
        """Update all packages in the project.

        Args:
            project_path: Path to the project directory

        Returns:
            List of update results
        """
        results: List[UpdateResult] = []

        # Try different package managers
        if (project_path / "pyproject.toml").exists():
            # Use poetry
            results = self._update_with_poetry(project_path, [])
        elif (project_path / "Pipfile").exists():
            # Use pipenv
            results = self._update_with_pipenv(project_path, [])
        elif (project_path / "requirements.txt").exists():
            # Use pip
            results = self._update_with_pip(project_path, [])
        else:
            raise ValueError("No supported package manager found")

        return results

    def _update_package(self, project_path: Path, package_name: str) -> UpdateResult:
        """Update a specific package.

        Args:
            project_path: Path to the project directory
            package_name: Name of the package to update

        Returns:
            Update result
        """
        # Get current version
        current_version = self._get_installed_version(package_name)

        # Try different package managers
        if (project_path / "pyproject.toml").exists():
            results = self._update_with_poetry(project_path, [package_name])
        elif (project_path / "Pipfile").exists():
            results = self._update_with_pipenv(project_path, [package_name])
        else:
            results = self._update_with_pip(project_path, [package_name])

        if results:
            return results[0]

        return UpdateResult(
            package_name=package_name,
            old_version=current_version,
            new_version="unknown",
            success=False,
            message="Update failed",
        )

    def _update_security_packages(self, project_path: Path) -> List[UpdateResult]:
        """Update packages with security vulnerabilities.

        Args:
            project_path: Path to the project directory

        Returns:
            List of update results
        """
        # This would integrate with vulnerability checker
        # For now, just update all packages
        return self._update_all_packages(project_path)

    def _update_with_pip(self, project_path: Path, package_names: List[str]) -> List[UpdateResult]:
        """Update packages using pip.

        Args:
            project_path: Path to the project directory
            package_names: List of package names to update

        Returns:
            List of update results
        """
        results: List[UpdateResult] = []

        try:
            if package_names:
                # Update specific packages
                for pkg_name in package_names:
                    current_version = self._get_installed_version(pkg_name)

                    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", pkg_name]
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=Config.UPDATE_TIMEOUT
                    )

                    if result.returncode == 0:
                        new_version = self._get_installed_version(pkg_name)
                        results.append(
                            UpdateResult(
                                package_name=pkg_name,
                                old_version=current_version,
                                new_version=new_version,
                                success=True,
                                message="Updated successfully",
                            )
                        )
                    else:
                        results.append(
                            UpdateResult(
                                package_name=pkg_name,
                                old_version=current_version,
                                new_version=current_version,
                                success=False,
                                message=result.stderr,
                            )
                        )
            else:
                # Update all packages from requirements.txt
                req_file = project_path / "requirements.txt"
                if req_file.exists():
                    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "-r", str(req_file)]
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=Config.UPDATE_TIMEOUT
                    )

                    if result.returncode == 0:
                        results.append(
                            UpdateResult(
                                package_name="all",
                                old_version="*",
                                new_version="latest",
                                success=True,
                                message="All packages updated",
                            )
                        )
                    else:
                        results.append(
                            UpdateResult(
                                package_name="all",
                                old_version="*",
                                new_version="*",
                                success=False,
                                message=result.stderr,
                            )
                        )

        except subprocess.TimeoutExpired:
            logger.error("Update timed out")
            results.append(
                UpdateResult(
                    package_name=package_names[0] if package_names else "all",
                    old_version="unknown",
                    new_version="unknown",
                    success=False,
                    message="Update timed out",
                )
            )
        except Exception as e:
            logger.error(f"Error updating with pip: {e}", exc_info=True)

        return results

    def _update_with_poetry(self, project_path: Path, package_names: List[str]) -> List[UpdateResult]:
        """Update packages using Poetry.

        Args:
            project_path: Path to the project directory
            package_names: List of package names to update

        Returns:
            List of update results
        """
        results: List[UpdateResult] = []

        try:
            if package_names:
                # Update specific packages
                for pkg_name in package_names:
                    current_version = self._get_poetry_version(project_path, pkg_name)

                    cmd = ["poetry", "update", pkg_name]
                    result = subprocess.run(
                        cmd,
                        cwd=project_path,
                        capture_output=True,
                        text=True,
                        timeout=Config.UPDATE_TIMEOUT,
                    )

                    if result.returncode == 0:
                        new_version = self._get_poetry_version(project_path, pkg_name)
                        results.append(
                            UpdateResult(
                                package_name=pkg_name,
                                old_version=current_version,
                                new_version=new_version,
                                success=True,
                                message="Updated successfully",
                            )
                        )
                    else:
                        results.append(
                            UpdateResult(
                                package_name=pkg_name,
                                old_version=current_version,
                                new_version=current_version,
                                success=False,
                                message=result.stderr,
                            )
                        )
            else:
                # Update all packages
                cmd = ["poetry", "update"]
                result = subprocess.run(
                    cmd,
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=Config.UPDATE_TIMEOUT,
                )

                if result.returncode == 0:
                    results.append(
                        UpdateResult(
                            package_name="all",
                            old_version="*",
                            new_version="latest",
                            success=True,
                            message="All packages updated",
                        )
                    )
                else:
                    results.append(
                        UpdateResult(
                            package_name="all",
                            old_version="*",
                            new_version="*",
                            success=False,
                            message=result.stderr,
                        )
                    )

        except subprocess.TimeoutExpired:
            logger.error("Update timed out")
        except Exception as e:
            logger.error(f"Error updating with poetry: {e}", exc_info=True)

        return results

    def _update_with_pipenv(self, project_path: Path, package_names: List[str]) -> List[UpdateResult]:
        """Update packages using Pipenv.

        Args:
            project_path: Path to the project directory
            package_names: List of package names to update

        Returns:
            List of update results
        """
        results: List[UpdateResult] = []

        try:
            if package_names:
                # Update specific packages
                for pkg_name in package_names:
                    current_version = self._get_pipenv_version(project_path, pkg_name)

                    cmd = ["pipenv", "update", pkg_name]
                    result = subprocess.run(
                        cmd,
                        cwd=project_path,
                        capture_output=True,
                        text=True,
                        timeout=Config.UPDATE_TIMEOUT,
                    )

                    if result.returncode == 0:
                        new_version = self._get_pipenv_version(project_path, pkg_name)
                        results.append(
                            UpdateResult(
                                package_name=pkg_name,
                                old_version=current_version,
                                new_version=new_version,
                                success=True,
                                message="Updated successfully",
                            )
                        )
                    else:
                        results.append(
                            UpdateResult(
                                package_name=pkg_name,
                                old_version=current_version,
                                new_version=current_version,
                                success=False,
                                message=result.stderr,
                            )
                        )
            else:
                # Update all packages
                cmd = ["pipenv", "update"]
                result = subprocess.run(
                    cmd,
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=Config.UPDATE_TIMEOUT,
                )

                if result.returncode == 0:
                    results.append(
                        UpdateResult(
                            package_name="all",
                            old_version="*",
                            new_version="latest",
                            success=True,
                            message="All packages updated",
                        )
                    )
                else:
                    results.append(
                        UpdateResult(
                            package_name="all",
                            old_version="*",
                            new_version="*",
                            success=False,
                            message=result.stderr,
                        )
                    )

        except subprocess.TimeoutExpired:
            logger.error("Update timed out")
        except Exception as e:
            logger.error(f"Error updating with pipenv: {e}", exc_info=True)

        return results

    def detect_conflicts(
        self, project_path: str, package_names: Optional[List[str]] = None
    ) -> List[Conflict]:
        """Detect dependency conflicts.

        Args:
            project_path: Path to the project directory
            package_names: Specific packages to check (None for all)

        Returns:
            List of conflicts
        """
        conflicts: List[Conflict] = []

        try:
            # Use pip check to detect conflicts
            cmd = [sys.executable, "-m", "pip", "check"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                # Parse the output for conflicts
                lines = result.stderr.split("\n")
                for line in lines:
                    if "conflict" in line.lower() or "incompatible" in line.lower():
                        conflicts.append(
                            Conflict(
                                package_name="unknown",
                                conflict_type="version",
                                conflicting_packages=[],
                                description=line,
                                resolution_suggestion="Update conflicting packages to compatible versions",
                            )
                        )

        except Exception as e:
            logger.error(f"Error detecting conflicts: {e}", exc_info=True)

        return conflicts

    def generate_lock_file(
        self, project_path: str, lock_file_type: str = "requirements.lock"
    ) -> tuple[str, int]:
        """Generate a lock file for the project.

        Args:
            project_path: Path to the project directory
            lock_file_type: Type of lock file to generate

        Returns:
            Tuple of (lock file path, dependency count)
        """
        project_path = Path(project_path).resolve()

        if not project_path.exists():
            raise FileNotFoundError(f"Project path not found: {project_path}")

        lock_file_path = project_path / lock_file_type

        try:
            if lock_file_type == "requirements.lock":
                # Generate using pip freeze
                cmd = [sys.executable, "-m", "pip", "freeze"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if result.returncode == 0:
                    with open(lock_file_path, "w", encoding="utf-8") as f:
                        f.write(result.stdout)

                    dependency_count = len([line for line in result.stdout.split("\n") if line.strip()])
                    return str(lock_file_path), dependency_count

            elif lock_file_type == "poetry.lock":
                # Generate using poetry lock
                cmd = ["poetry", "lock"]
                result = subprocess.run(
                    cmd, cwd=project_path, capture_output=True, text=True, timeout=60
                )

                if result.returncode == 0:
                    lock_file_path = project_path / "poetry.lock"
                    # Count dependencies
                    dependency_count = self._count_poetry_dependencies(lock_file_path)
                    return str(lock_file_path), dependency_count

            elif lock_file_type == "Pipfile.lock":
                # Generate using pipenv lock
                cmd = ["pipenv", "lock"]
                result = subprocess.run(
                    cmd, cwd=project_path, capture_output=True, text=True, timeout=60
                )

                if result.returncode == 0:
                    lock_file_path = project_path / "Pipfile.lock"
                    dependency_count = self._count_pipenv_dependencies(lock_file_path)
                    return str(lock_file_path), dependency_count

            else:
                raise ValueError(f"Unsupported lock file type: {lock_file_type}")

        except Exception as e:
            logger.error(f"Error generating lock file: {e}", exc_info=True)
            raise

        return str(lock_file_path), 0

    def _get_installed_version(self, package_name: str) -> str:
        """Get the installed version of a package.

        Args:
            package_name: Name of the package

        Returns:
            Version string or "unknown"
        """
        try:
            cmd = [sys.executable, "-m", "pip", "show", package_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("Version:"):
                        return line.split(":", 1)[1].strip()

        except Exception:
            pass

        return "unknown"

    def _get_poetry_version(self, project_path: Path, package_name: str) -> str:
        """Get the version of a package from poetry.lock.

        Args:
            project_path: Path to the project directory
            package_name: Name of the package

        Returns:
            Version string or "unknown"
        """
        try:
            import toml

            lock_file = project_path / "poetry.lock"
            if lock_file.exists():
                with open(lock_file, "r", encoding="utf-8") as f:
                    data = toml.load(f)

                for package in data.get("package", []):
                    if package.get("name", "").lower() == package_name.lower():
                        return package.get("version", "unknown")

        except Exception:
            pass

        return "unknown"

    def _get_pipenv_version(self, project_path: Path, package_name: str) -> str:
        """Get the version of a package from Pipfile.lock.

        Args:
            project_path: Path to the project directory
            package_name: Name of the package

        Returns:
            Version string or "unknown"
        """
        try:
            import json

            lock_file = project_path / "Pipfile.lock"
            if lock_file.exists():
                with open(lock_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                default_packages = data.get("default", {})
                if package_name in default_packages:
                    return default_packages[package_name].get("version", "unknown")

        except Exception:
            pass

        return "unknown"

    def _count_poetry_dependencies(self, lock_file: Path) -> int:
        """Count dependencies in poetry.lock.

        Args:
            lock_file: Path to poetry.lock

        Returns:
            Number of dependencies
        """
        try:
            import toml

            with open(lock_file, "r", encoding="utf-8") as f:
                data = toml.load(f)

            return len(data.get("package", []))

        except Exception:
            return 0

    def _count_pipenv_dependencies(self, lock_file: Path) -> int:
        """Count dependencies in Pipfile.lock.

        Args:
            lock_file: Path to Pipfile.lock

        Returns:
            Number of dependencies
        """
        try:
            import json

            with open(lock_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            default_count = len(data.get("default", {}))
            develop_count = len(data.get("develop", {}))
            return default_count + develop_count

        except Exception:
            return 0

    def _create_backup(self, project_path: Path) -> Path:
        """Create a backup of the project.

        Args:
            project_path: Path to the project directory

        Returns:
            Path to the backup directory
        """
        self._backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{project_path.name}_{timestamp}"
        backup_path = self._backup_dir / backup_name

        # Copy important files
        important_files = [
            "requirements.txt",
            "requirements-dev.txt",
            "pyproject.toml",
            "setup.py",
            "Pipfile",
            "poetry.lock",
            "Pipfile.lock",
        ]

        backup_path.mkdir(parents=True, exist_ok=True)

        for file_name in important_files:
            src_file = project_path / file_name
            if src_file.exists():
                shutil.copy2(src_file, backup_path / file_name)

        return backup_path

    def _restore_backup(self, project_path: Path, backup_path: Path) -> None:
        """Restore a backup of the project.

        Args:
            project_path: Path to the project directory
            backup_path: Path to the backup directory
        """
        if not backup_path.exists():
            logger.warning(f"Backup not found: {backup_path}")
            return

        # Restore files
        for file_path in backup_path.iterdir():
            if file_path.is_file():
                shutil.copy2(file_path, project_path / file_path.name)

        logger.info(f"Restored backup from: {backup_path}")


# Import sys at module level
import sys
