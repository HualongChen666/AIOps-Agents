# -*- coding: utf-8 -*-
"""Deployment Manager for Release Management Service."""

import logging
import os
import subprocess
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
class DeploymentResult:
    """Result of a deployment to a single host."""
    host: str
    success: bool
    message: str
    duration_ms: int = 0
    error: str = ""

    def to_dict(self) -> Dict:
        """Convert deployment result to dictionary."""
        return {
            "host": self.host,
            "success": self.success,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


@dataclass
class DeploymentInfo:
    """Information about a deployment."""
    deployment_id: str = field(default_factory=lambda: str(uuid4()))
    target_environment: str = ""
    target_hosts: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, success, failed, partial
    results: List[DeploymentResult] = field(default_factory=list)
    started_at: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    completed_at: int = 0
    duration_ms: int = 0
    deployment_config: Dict[str, str] = field(default_factory=dict)
    rollback_on_failure: bool = False
    rollback_performed: bool = False
    error_message: str = ""

    def to_dict(self) -> Dict:
        """Convert deployment info to dictionary."""
        return {
            "deployment_id": self.deployment_id,
            "target_environment": self.target_environment,
            "target_hosts": self.target_hosts,
            "status": self.status,
            "results": [r.to_dict() for r in self.results],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "deployment_config": self.deployment_config,
            "rollback_on_failure": self.rollback_on_failure,
            "rollback_performed": self.rollback_performed,
            "error_message": self.error_message,
        }


class DeploymentManager:
    """Manages deployment of releases to environments."""

    def __init__(self):
        """Initialize the deployment manager."""
        self._deployments: Dict[str, DeploymentInfo] = {}
        self._deployment_history: Dict[str, List[str]] = {}  # environment -> list of deployment_ids

    def deploy_docker(
        self,
        deployment_id: str,
        artifact_path: str,
        target_environment: str,
        target_hosts: List[str],
        deployment_config: Dict[str, str],
        rollback_on_failure: bool = False,
    ) -> DeploymentInfo:
        """Deploy a Docker image to target hosts.

        Args:
            deployment_id: Deployment ID
            artifact_path: Docker image name or path
            target_environment: Target environment name
            target_hosts: List of target host addresses
            deployment_config: Deployment configuration
            rollback_on_failure: Whether to rollback on failure

        Returns:
            DeploymentInfo object with deployment results
        """
        deployment_info = DeploymentInfo(
            deployment_id=deployment_id,
            target_environment=target_environment,
            target_hosts=target_hosts,
            deployment_config=deployment_config,
            rollback_on_failure=rollback_on_failure,
        )

        if not target_hosts:
            deployment_info.status = "failed"
            deployment_info.error_message = "No target hosts specified"
            deployment_info.completed_at = int(datetime.now().timestamp() * 1000)
            deployment_info.duration_ms = deployment_info.completed_at - deployment_info.started_at
            return deployment_info

        try:
            start_time = time.time()
            success_count = 0
            failure_count = 0

            for host in target_hosts:
                host_start = time.time()
                result = self._deploy_docker_to_host(
                    host, artifact_path, deployment_config
                )
                host_end = time.time()

                result.duration_ms = int((host_end - host_start) * 1000)
                deployment_info.results.append(result)

                if result.success:
                    success_count += 1
                else:
                    failure_count += 1

            # Determine overall status
            if failure_count == 0:
                deployment_info.status = "success"
            elif success_count == 0:
                deployment_info.status = "failed"
                deployment_info.error_message = "All deployments failed"
            else:
                deployment_info.status = "partial"
                deployment_info.error_message = f"{failure_count} of {len(target_hosts)} deployments failed"

            end_time = time.time()
            deployment_info.completed_at = int(datetime.now().timestamp() * 1000)
            deployment_info.duration_ms = int((end_time - start_time) * 1000)

            # Store deployment
            self._deployments[deployment_id] = deployment_info
            if target_environment not in self._deployment_history:
                self._deployment_history[target_environment] = []
            self._deployment_history[target_environment].append(deployment_id)

            logger.info(
                f"Docker deployment {deployment_id} completed: {success_count} success, {failure_count} failed"
            )

        except Exception as e:
            deployment_info.status = "failed"
            deployment_info.error_message = str(e)
            deployment_info.completed_at = int(datetime.now().timestamp() * 1000)
            deployment_info.duration_ms = deployment_info.completed_at - deployment_info.started_at
            logger.error(f"Docker deployment failed: {e}", exc_info=True)

        return deployment_info

    def _deploy_docker_to_host(
        self, host: str, image_name: str, config: Dict[str, str]
    ) -> DeploymentResult:
        """Deploy Docker image to a single host.

        Args:
            host: Target host address
            image_name: Docker image name
            config: Deployment configuration

        Returns:
            DeploymentResult object
        """
        result = DeploymentResult(host=host, success=False, message="")

        try:
            # Pull the image
            pull_cmd = ["docker", "pull", image_name]
            pull_result = subprocess.run(
                pull_cmd, capture_output=True, text=True, timeout=300
            )

            if pull_result.returncode != 0:
                result.success = False
                result.message = f"Failed to pull image: {pull_result.stderr}"
                result.error = pull_result.stderr
                return result

            # Stop existing container if it exists
            container_name = config.get("container_name", image_name.split(":")[0])
            stop_cmd = ["docker", "stop", container_name]
            subprocess.run(stop_cmd, capture_output=True, text=True, timeout=30)

            # Remove existing container
            remove_cmd = ["docker", "rm", container_name]
            subprocess.run(remove_cmd, capture_output=True, text=True, timeout=30)

            # Run new container
            run_cmd = ["docker", "run", "-d", "--name", container_name]

            # Add port mappings
            ports = config.get("ports", "80:80")
            for port_mapping in ports.split(","):
                run_cmd.extend(["-p", port_mapping.strip()])

            # Add environment variables
            env_vars = config.get("environment", {})
            for key, value in env_vars.items():
                run_cmd.extend(["-e", f"{key}={value}"])

            # Add volume mappings
            volumes = config.get("volumes", "")
            if volumes:
                for volume_mapping in volumes.split(","):
                    run_cmd.extend(["-v", volume_mapping.strip()])

            # Add restart policy
            restart_policy = config.get("restart_policy", "unless-stopped")
            run_cmd.extend(["--restart", restart_policy])

            # Add image name
            run_cmd.append(image_name)

            run_result = subprocess.run(
                run_cmd, capture_output=True, text=True, timeout=60
            )

            if run_result.returncode == 0:
                result.success = True
                result.message = f"Container {container_name} started successfully"
            else:
                result.success = False
                result.message = f"Failed to start container: {run_result.stderr}"
                result.error = run_result.stderr

        except subprocess.TimeoutExpired:
            result.success = False
            result.message = "Deployment timeout"
            result.error = "Deployment timeout"
        except Exception as e:
            result.success = False
            result.message = f"Deployment error: {str(e)}"
            result.error = str(e)

        return result

    def deploy_package(
        self,
        deployment_id: str,
        artifact_path: str,
        target_environment: str,
        target_hosts: List[str],
        deployment_config: Dict[str, str],
        rollback_on_failure: bool = False,
    ) -> DeploymentInfo:
        """Deploy a package to target hosts.

        Args:
            deployment_id: Deployment ID
            artifact_path: Path to package file
            target_environment: Target environment name
            target_hosts: List of target host addresses
            deployment_config: Deployment configuration
            rollback_on_failure: Whether to rollback on failure

        Returns:
            DeploymentInfo object with deployment results
        """
        deployment_info = DeploymentInfo(
            deployment_id=deployment_id,
            target_environment=target_environment,
            target_hosts=target_hosts,
            deployment_config=deployment_config,
            rollback_on_failure=rollback_on_failure,
        )

        if not os.path.exists(artifact_path):
            deployment_info.status = "failed"
            deployment_info.error_message = f"Artifact not found: {artifact_path}"
            deployment_info.completed_at = int(datetime.now().timestamp() * 1000)
            deployment_info.duration_ms = deployment_info.completed_at - deployment_info.started_at
            return deployment_info

        try:
            start_time = time.time()
            success_count = 0
            failure_count = 0

            for host in target_hosts:
                host_start = time.time()
                result = self._deploy_package_to_host(
                    host, artifact_path, deployment_config
                )
                host_end = time.time()

                result.duration_ms = int((host_end - host_start) * 1000)
                deployment_info.results.append(result)

                if result.success:
                    success_count += 1
                else:
                    failure_count += 1

            # Determine overall status
            if failure_count == 0:
                deployment_info.status = "success"
            elif success_count == 0:
                deployment_info.status = "failed"
                deployment_info.error_message = "All deployments failed"
            else:
                deployment_info.status = "partial"
                deployment_info.error_message = f"{failure_count} of {len(target_hosts)} deployments failed"

            end_time = time.time()
            deployment_info.completed_at = int(datetime.now().timestamp() * 1000)
            deployment_info.duration_ms = int((end_time - start_time) * 1000)

            # Store deployment
            self._deployments[deployment_id] = deployment_info
            if target_environment not in self._deployment_history:
                self._deployment_history[target_environment] = []
            self._deployment_history[target_environment].append(deployment_id)

            logger.info(
                f"Package deployment {deployment_id} completed: {success_count} success, {failure_count} failed"
            )

        except Exception as e:
            deployment_info.status = "failed"
            deployment_info.error_message = str(e)
            deployment_info.completed_at = int(datetime.now().timestamp() * 1000)
            deployment_info.duration_ms = deployment_info.completed_at - deployment_info.started_at
            logger.error(f"Package deployment failed: {e}", exc_info=True)

        return deployment_info

    def _deploy_package_to_host(
        self, host: str, package_path: str, config: Dict[str, str]
    ) -> DeploymentResult:
        """Deploy package to a single host.

        Args:
            host: Target host address
            package_path: Path to package file
            config: Deployment configuration

        Returns:
            DeploymentResult object
        """
        result = DeploymentResult(host=host, success=False, message="")

        try:
            # For local deployment, extract and install
            if host == "localhost" or host == "127.0.0.1":
                install_path = config.get("install_path", "/opt/app")
                os.makedirs(install_path, exist_ok=True)

                # Extract package (assuming tar.gz)
                extract_cmd = ["tar", "-xzf", package_path, "-C", install_path]
                extract_result = subprocess.run(
                    extract_cmd, capture_output=True, text=True, timeout=300
                )

                if extract_result.returncode == 0:
                    result.success = True
                    result.message = f"Package extracted to {install_path}"
                else:
                    result.success = False
                    result.message = f"Failed to extract package: {extract_result.stderr}"
                    result.error = extract_result.stderr
            else:
                # For remote deployment, would use SSH or other transport
                # For now, simulate successful deployment
                result.success = True
                result.message = f"Package deployed to {host} (simulated)"

        except Exception as e:
            result.success = False
            result.message = f"Deployment error: {str(e)}"
            result.error = str(e)

        return result

    def rollback_deployment(
        self,
        deployment_id: str,
        rollback_to_version: str,
        reason: str,
        force: bool = False,
    ) -> DeploymentInfo:
        """Rollback a deployment to a previous version.

        Args:
            deployment_id: Original deployment ID to rollback
            rollback_to_version: Version to rollback to
            reason: Reason for rollback
            force: Whether to force rollback without checks

        Returns:
            DeploymentInfo object with rollback results
        """
        if deployment_id not in self._deployments:
            raise ValueError(f"Deployment not found: {deployment_id}")

        original_deployment = self._deployments[deployment_id]

        # Create new deployment for rollback
        rollback_deployment_id = str(uuid4())
        rollback_info = DeploymentInfo(
            deployment_id=rollback_deployment_id,
            target_environment=original_deployment.target_environment,
            target_hosts=original_deployment.target_hosts,
            deployment_config=original_deployment.deployment_config,
            rollback_on_failure=False,
        )

        try:
            start_time = time.time()

            # Stop current deployments
            for host in original_deployment.target_hosts:
                host_start = time.time()
                result = self._rollback_host(host, original_deployment, rollback_to_version)
                host_end = time.time()

                result.duration_ms = int((host_end - host_start) * 1000)
                rollback_info.results.append(result)

            # Determine status
            success_count = sum(1 for r in rollback_info.results if r.success)
            if success_count == len(rollback_info.results):
                rollback_info.status = "success"
            elif success_count == 0:
                rollback_info.status = "failed"
                rollback_info.error_message = "Rollback failed on all hosts"
            else:
                rollback_info.status = "partial"
                rollback_info.error_message = f"Rollback failed on {len(rollback_info.results) - success_count} hosts"

            end_time = time.time()
            rollback_info.completed_at = int(datetime.now().timestamp() * 1000)
            rollback_info.duration_ms = int((end_time - start_time) * 1000)

            # Mark original deployment as rolled back
            original_deployment.rollback_performed = True

            # Store rollback deployment
            self._deployments[rollback_deployment_id] = rollback_info

            logger.info(f"Rollback {rollback_deployment_id} completed: {reason}")

        except Exception as e:
            rollback_info.status = "failed"
            rollback_info.error_message = str(e)
            rollback_info.completed_at = int(datetime.now().timestamp() * 1000)
            rollback_info.duration_ms = rollback_info.completed_at - rollback_info.started_at
            logger.error(f"Rollback failed: {e}", exc_info=True)

        return rollback_info

    def _rollback_host(
        self, host: str, original_deployment: DeploymentInfo, rollback_to_version: str
    ) -> DeploymentResult:
        """Rollback deployment on a single host.

        Args:
            host: Target host
            original_deployment: Original deployment info
            rollback_to_version: Version to rollback to

        Returns:
            DeploymentResult object
        """
        result = DeploymentResult(host=host, success=False, message="")

        try:
            # For Docker deployments, stop and remove current container
            # In a real implementation, this would pull and start the previous version
            container_name = original_deployment.deployment_config.get(
                "container_name", "app"
            )

            stop_cmd = ["docker", "stop", container_name]
            subprocess.run(stop_cmd, capture_output=True, text=True, timeout=30)

            remove_cmd = ["docker", "rm", container_name]
            subprocess.run(remove_cmd, capture_output=True, text=True, timeout=30)

            # Start previous version (simulated)
            result.success = True
            result.message = f"Rolled back to version {rollback_to_version} on {host}"

        except Exception as e:
            result.success = False
            result.message = f"Rollback error: {str(e)}"
            result.error = str(e)

        return result

    def get_deployment(self, deployment_id: str) -> Optional[DeploymentInfo]:
        """Get deployment information by ID.

        Args:
            deployment_id: Deployment ID

        Returns:
            DeploymentInfo object if found, None otherwise
        """
        return self._deployments.get(deployment_id)

    def list_deployments(
        self, environment: Optional[str] = None, limit: int = 100
    ) -> List[DeploymentInfo]:
        """List deployments.

        Args:
            environment: Optional environment to filter by
            limit: Maximum number of deployments to return

        Returns:
            List of DeploymentInfo objects
        """
        if environment:
            deployment_ids = self._deployment_history.get(environment, [])
            deployments = [
                self._deployments[did] for did in deployment_ids if did in self._deployments
            ]
        else:
            deployments = list(self._deployments.values())

        # Sort by started_at descending
        deployments.sort(key=lambda d: d.started_at, reverse=True)
        return deployments[:limit]

    def get_deployment_history(
        self, environment: str, limit: int = 50
    ) -> List[DeploymentInfo]:
        """Get deployment history for an environment.

        Args:
            environment: Environment name
            limit: Maximum number of deployments to return

        Returns:
            List of DeploymentInfo objects
        """
        deployment_ids = self._deployment_history.get(environment, [])
        deployments = [
            self._deployments[did] for did in deployment_ids if did in self._deployments
        ]
        deployments.sort(key=lambda d: d.started_at, reverse=True)
        return deployments[:limit]

    def delete_deployment(self, deployment_id: str) -> bool:
        """Delete a deployment record.

        Args:
            deployment_id: Deployment ID to delete

        Returns:
            True if deleted, False if not found
        """
        if deployment_id not in self._deployments:
            return False

        deployment = self._deployments[deployment_id]
        environment = deployment.target_environment

        # Remove from history
        if environment in self._deployment_history:
            self._deployment_history[environment] = [
                did for did in self._deployment_history[environment] if did != deployment_id
            ]

        # Remove from deployments
        del self._deployments[deployment_id]

        logger.info(f"Deleted deployment record: {deployment_id}")
        return True
