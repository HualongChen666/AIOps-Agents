# -*- coding: utf-8 -*-
"""Release Builder for Release Management Service."""

import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
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
class BuildInfo:
    """Information about a build."""
    build_id: str = field(default_factory=lambda: str(uuid4()))
    build_type: str = "docker"
    status: str = "pending"  # pending, success, failed
    artifact_path: str = ""
    build_url: str = ""
    started_at: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    completed_at: int = 0
    duration_ms: int = 0
    build_args: Dict[str, str] = field(default_factory=dict)
    error_message: str = ""
    checksum: str = ""
    size_bytes: int = 0

    def to_dict(self) -> Dict:
        """Convert build info to dictionary."""
        return {
            "build_id": self.build_id,
            "build_type": self.build_type,
            "status": self.status,
            "artifact_path": self.artifact_path,
            "build_url": self.build_url,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "build_args": self.build_args,
            "error_message": self.error_message,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
        }


class ReleaseBuilder:
    """Builds release packages for deployment."""

    def __init__(self):
        """Initialize the release builder."""
        self._builds: Dict[str, BuildInfo] = {}
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        os.makedirs(Config.BUILD_DIR, exist_ok=True)
        os.makedirs(Config.ARTIFACTS_DIR, exist_ok=True)
        os.makedirs(Config.RELEASES_DIR, exist_ok=True)

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file.

        Args:
            file_path: Path to the file

        Returns:
            SHA256 checksum as hex string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _get_file_size(self, file_path: str) -> int:
        """Get file size in bytes.

        Args:
            file_path: Path to the file

        Returns:
            File size in bytes
        """
        return os.path.getsize(file_path)

    def build_docker_image(
        self,
        project_name: str,
        version: str,
        dockerfile_path: str,
        build_args: Dict[str, str],
        context_path: str = ".",
    ) -> BuildInfo:
        """Build a Docker image.

        Args:
            project_name: Name of the project
            version: Version to build
            dockerfile_path: Path to Dockerfile
            build_args: Build arguments for Docker
            context_path: Build context path

        Returns:
            BuildInfo object with build results
        """
        build_info = BuildInfo(
            build_type="docker",
            build_args=build_args,
        )

        if not os.path.exists(dockerfile_path):
            build_info.status = "failed"
            build_info.error_message = f"Dockerfile not found: {dockerfile_path}"
            build_info.completed_at = int(datetime.now().timestamp() * 1000)
            build_info.duration_ms = build_info.completed_at - build_info.started_at
            return build_info

        image_name = f"{project_name}:{version}"
        image_name_latest = f"{project_name}:latest"

        try:
            # Prepare build command
            cmd = ["docker", "build", "-t", image_name, "-t", image_name_latest]

            # Add build arguments
            for key, value in build_args.items():
                cmd.extend(["--build-arg", f"{key}={value}"])

            cmd.extend(["-f", dockerfile_path, context_path])

            logger.info(f"Building Docker image: {' '.join(cmd)}")

            # Run build command
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=Config.BUILD_TIMEOUT,
            )
            end_time = time.time()

            if result.returncode == 0:
                build_info.status = "success"
                build_info.artifact_path = image_name
                build_info.build_url = f"docker://{image_name}"
                build_info.checksum = image_name  # Use image name as checksum for Docker
                build_info.size_bytes = 0  # Docker image size would need additional command
            else:
                build_info.status = "failed"
                build_info.error_message = result.stderr

            build_info.completed_at = int(datetime.now().timestamp() * 1000)
            build_info.duration_ms = int((end_time - start_time) * 1000)

        except subprocess.TimeoutExpired:
            build_info.status = "failed"
            build_info.error_message = f"Build timeout after {Config.BUILD_TIMEOUT} seconds"
            build_info.completed_at = int(datetime.now().timestamp() * 1000)
            build_info.duration_ms = Config.BUILD_TIMEOUT * 1000
        except Exception as e:
            build_info.status = "failed"
            build_info.error_message = str(e)
            build_info.completed_at = int(datetime.now().timestamp() * 1000)
            build_info.duration_ms = build_info.completed_at - build_info.started_at

        self._builds[build_info.build_id] = build_info
        return build_info

    def build_package(
        self,
        project_name: str,
        version: str,
        source_path: str,
        build_args: Dict[str, str],
        package_type: str = "tar.gz",
    ) -> BuildInfo:
        """Build a package archive.

        Args:
            project_name: Name of the project
            version: Version to build
            source_path: Path to source files
            build_args: Build arguments
            package_type: Type of package (tar.gz, zip)

        Returns:
            BuildInfo object with build results
        """
        build_info = BuildInfo(
            build_type="package",
            build_args=build_args,
        )

        if not os.path.exists(source_path):
            build_info.status = "failed"
            build_info.error_message = f"Source path not found: {source_path}"
            build_info.completed_at = int(datetime.now().timestamp() * 1000)
            build_info.duration_ms = build_info.completed_at - build_info.started_at
            return build_info

        try:
            start_time = time.time()

            # Create temporary directory for build
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create package filename
                package_name = f"{project_name}-{version}.{package_type}"
                package_path = os.path.join(Config.ARTIFACTS_DIR, package_name)

                # Copy source files to temp directory
                temp_source = os.path.join(temp_dir, project_name)
                if os.path.exists(source_path):
                    if os.path.isfile(source_path):
                        os.makedirs(temp_source, exist_ok=True)
                        shutil.copy2(source_path, temp_source)
                    else:
                        shutil.copytree(source_path, temp_source)

                # Create metadata file
                metadata = {
                    "project_name": project_name,
                    "version": version,
                    "build_time": datetime.now().isoformat(),
                    "build_args": build_args,
                }
                metadata_path = os.path.join(temp_source, "build_metadata.json")
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)

                # Create archive
                if package_type == "tar.gz":
                    shutil.make_archive(
                        os.path.join(Config.ARTIFACTS_DIR, f"{project_name}-{version}"),
                        "gztar",
                        temp_dir,
                        project_name,
                    )
                elif package_type == "zip":
                    shutil.make_archive(
                        os.path.join(Config.ARTIFACTS_DIR, f"{project_name}-{version}"),
                        "zip",
                        temp_dir,
                        project_name,
                    )
                else:
                    raise ValueError(f"Unsupported package type: {package_type}")

            # Calculate checksum and size
            if os.path.exists(package_path):
                build_info.checksum = self._calculate_checksum(package_path)
                build_info.size_bytes = self._get_file_size(package_path)
                build_info.artifact_path = package_path
                build_info.build_url = f"file://{package_path}"
                build_info.status = "success"
            else:
                build_info.status = "failed"
                build_info.error_message = "Package file not created"

            end_time = time.time()
            build_info.completed_at = int(datetime.now().timestamp() * 1000)
            build_info.duration_ms = int((end_time - start_time) * 1000)

        except Exception as e:
            build_info.status = "failed"
            build_info.error_message = str(e)
            build_info.completed_at = int(datetime.now().timestamp() * 1000)
            build_info.duration_ms = build_info.completed_at - build_info.started_at
            logger.error(f"Package build failed: {e}", exc_info=True)

        self._builds[build_info.build_id] = build_info
        return build_info

    def build_binary(
        self,
        project_name: str,
        version: str,
        source_path: str,
        build_args: Dict[str, str],
        build_command: List[str],
    ) -> BuildInfo:
        """Build a binary from source.

        Args:
            project_name: Name of the project
            version: Version to build
            source_path: Path to source files
            build_args: Build arguments
            build_command: Command to build the binary

        Returns:
            BuildInfo object with build results
        """
        build_info = BuildInfo(
            build_type="binary",
            build_args=build_args,
        )

        if not os.path.exists(source_path):
            build_info.status = "failed"
            build_info.error_message = f"Source path not found: {source_path}"
            build_info.completed_at = int(datetime.now().timestamp() * 1000)
            build_info.duration_ms = build_info.completed_at - build_info.started_at
            return build_info

        try:
            start_time = time.time()

            # Run build command
            env = os.environ.copy()
            env.update(build_args)

            result = subprocess.run(
                build_command,
                cwd=source_path,
                capture_output=True,
                text=True,
                timeout=Config.BUILD_TIMEOUT,
                env=env,
            )

            if result.returncode == 0:
                # Assume the binary is in the current directory or specified in build_args
                binary_name = build_args.get("binary_name", project_name)
                binary_path = os.path.join(source_path, binary_name)

                if os.path.exists(binary_path):
                    # Copy to artifacts directory
                    artifact_name = f"{project_name}-{version}-{binary_name}"
                    artifact_path = os.path.join(Config.ARTIFACTS_DIR, artifact_name)
                    shutil.copy2(binary_path, artifact_path)

                    build_info.artifact_path = artifact_path
                    build_info.build_url = f"file://{artifact_path}"
                    build_info.checksum = self._calculate_checksum(artifact_path)
                    build_info.size_bytes = self._get_file_size(artifact_path)
                    build_info.status = "success"
                else:
                    build_info.status = "failed"
                    build_info.error_message = f"Binary not found at {binary_path}"
            else:
                build_info.status = "failed"
                build_info.error_message = result.stderr

            end_time = time.time()
            build_info.completed_at = int(datetime.now().timestamp() * 1000)
            build_info.duration_ms = int((end_time - start_time) * 1000)

        except subprocess.TimeoutExpired:
            build_info.status = "failed"
            build_info.error_message = f"Build timeout after {Config.BUILD_TIMEOUT} seconds"
            build_info.completed_at = int(datetime.now().timestamp() * 1000)
            build_info.duration_ms = Config.BUILD_TIMEOUT * 1000
        except Exception as e:
            build_info.status = "failed"
            build_info.error_message = str(e)
            build_info.completed_at = int(datetime.now().timestamp() * 1000)
            build_info.duration_ms = build_info.completed_at - build_info.started_at
            logger.error(f"Binary build failed: {e}", exc_info=True)

        self._builds[build_info.build_id] = build_info
        return build_info

    def get_build(self, build_id: str) -> Optional[BuildInfo]:
        """Get build information by ID.

        Args:
            build_id: Build ID

        Returns:
            BuildInfo object if found, None otherwise
        """
        return self._builds.get(build_id)

    def list_builds(self, project_name: Optional[str] = None) -> List[BuildInfo]:
        """List all builds or builds for a specific project.

        Args:
            project_name: Optional project name to filter by

        Returns:
            List of BuildInfo objects
        """
        builds = list(self._builds.values())
        if project_name:
            # Filter by project name (would need to store project_name in BuildInfo)
            # For now, return all builds
            pass
        return builds

    def delete_build(self, build_id: str) -> bool:
        """Delete a build record and its artifact.

        Args:
            build_id: Build ID to delete

        Returns:
            True if deleted, False if not found
        """
        if build_id not in self._builds:
            return False

        build_info = self._builds[build_id]

        # Delete artifact file if it exists
        if build_info.artifact_path and os.path.exists(build_info.artifact_path):
            try:
                os.remove(build_info.artifact_path)
                logger.info(f"Deleted artifact: {build_info.artifact_path}")
            except Exception as e:
                logger.error(f"Failed to delete artifact: {e}")

        del self._builds[build_id]
        logger.info(f"Deleted build record: {build_id}")
        return True
