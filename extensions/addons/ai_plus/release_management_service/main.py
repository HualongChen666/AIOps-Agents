# -*- coding: utf-8 -*-
"""Main entry point for Release Management Service."""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

try:
    from .config import Config
    from .deployment_manager import DeploymentManager, DeploymentInfo
    from .grpc.server import ReleaseManagementRPCServer
    from .release_builder import ReleaseBuilder, BuildInfo
    from .version_manager import VersionManager, Version
except ImportError:
    from config import Config
    from deployment_manager import DeploymentManager, DeploymentInfo
    from grpc.server import ReleaseManagementRPCServer
    from release_builder import ReleaseBuilder, BuildInfo
    from version_manager import VersionManager, Version

# Configure logging
Config.validate()
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format=Config.LOG_FORMAT,
)
logger = logging.getLogger(Config.SERVICE_NAME)

# Initialize FastAPI app
app = FastAPI(title=Config.SERVICE_NAME.replace("_", " ").title())

# Initialize service components
version_manager = VersionManager()
release_builder = ReleaseBuilder()
deployment_manager = DeploymentManager()
rpc_server = ReleaseManagementRPCServer()

# In-memory storage
releases: Dict[str, Dict[str, Any]] = {}
release_history: Dict[str, List[Dict[str, Any]]] = {}  # release_id -> list of events


# Pydantic models
class ReleaseModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    project_name: str
    version: str
    release_type: str = "patch"  # major, minor, patch, hotfix
    description: str = ""
    changes: List[str] = Field(default_factory=list)
    environment: str = "staging"
    status: str = "draft"  # draft, pending, approved, deployed, rolled_back, failed
    requires_approval: bool = True
    approvers: List[str] = Field(default_factory=list)
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    updated_at: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    created_by: str = "system"
    updated_by: str = "system"
    build_info: Optional[Dict[str, Any]] = None
    deployment_info: Optional[Dict[str, Any]] = None
    approvals: List[Dict[str, Any]] = Field(default_factory=list)


class CreateReleaseRequest(BaseModel):
    project_name: str
    version: Optional[str] = None
    release_type: str = "patch"
    description: str = ""
    changes: List[str] = Field(default_factory=list)
    environment: str = "staging"
    requires_approval: bool = True
    approvers: List[str] = Field(default_factory=list)


class BuildReleaseRequest(BaseModel):
    release_id: str
    build_type: str = "docker"
    build_args: Dict[str, str] = Field(default_factory=dict)
    source_path: Optional[str] = None
    dockerfile_path: Optional[str] = None


class DeployReleaseRequest(BaseModel):
    release_id: str
    target_environment: str
    target_hosts: List[str]
    deployment_config: Dict[str, str] = Field(default_factory=dict)
    rollback_on_failure: bool = False


class RollbackReleaseRequest(BaseModel):
    release_id: str
    rollback_to_version: str
    reason: str = ""
    force: bool = False


class ApproveReleaseRequest(BaseModel):
    release_id: str
    approver: str
    comment: str = ""


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = Config.SERVICE_NAME
    release_count: int
    version_count: int
    build_count: int
    deployment_count: int


class InfoResponse(BaseModel):
    service: str
    version: str = "1.0.0"
    status: str = "running"


class InvokeRequest(BaseModel):
    action: str = Field(
        ...,
        pattern="^(create_release|get_release|list_releases|update_release|delete_release|"
        "build_release|deploy_release|rollback_release|approve_release|reject_release|"
        "get_release_history|get_release_status|create_version|get_version|list_versions|"
        "increment_version|compare_versions)$"
    )
    payload: Dict[str, Any] = Field(default_factory=dict)


class InvokeResponse(BaseModel):
    success: bool
    service: str
    action: str
    result: Any


# Helper functions
def _add_release_event(release_id: str, event_type: str, description: str, performed_by: str, metadata: Dict[str, Any] = None):
    """Add an event to release history."""
    if release_id not in release_history:
        release_history[release_id] = []

    event = {
        "event_type": event_type,
        "description": description,
        "performed_by": performed_by,
        "timestamp": int(datetime.now().timestamp() * 1000),
        "metadata": metadata or {},
    }

    release_history[release_id].append(event)

    # Limit history size
    if len(release_history[release_id]) > Config.MAX_RELEASE_HISTORY:
        release_history[release_id] = release_history[release_id][-Config.MAX_RELEASE_HISTORY:]


def _create_release(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new release."""
    project_name = payload.get("project_name")
    version = payload.get("version")
    release_type = payload.get("release_type", "patch")

    # Auto-generate version if not provided
    if not version:
        version_obj = version_manager.create_version(
            project_name=project_name,
            increment_type=release_type,
        )
        version = version_obj.version
    else:
        # Ensure version exists
        existing_version = version_manager.get_version(project_name, version)
        if not existing_version:
            version_obj = version_manager.create_version(
                project_name=project_name,
                base_version=version,
            )
        else:
            version_obj = existing_version

    release = ReleaseModel(
        project_name=project_name,
        version=version,
        release_type=release_type,
        description=payload.get("description", ""),
        changes=payload.get("changes", []),
        environment=payload.get("environment", "staging"),
        requires_approval=payload.get("requires_approval", True),
        approvers=payload.get("approvers", []),
    )

    # Initialize approvals
    if release.requires_approval and release.approvers:
        for approver in release.approvers:
            release.approvals.append({
                "approver": approver,
                "status": "pending",
                "comment": "",
                "approved_at": 0,
            })

    releases[release.id] = release.model_dump()

    _add_release_event(
        release.id,
        "created",
        f"Release {release.version} created",
        "system",
        {"version": version, "release_type": release_type}
    )

    logger.info(f"Created release {release.id}: {project_name} v{version}")
    return release.model_dump()


def _get_release(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Get a release by ID."""
    release_id = payload.get("release_id")
    if not release_id or release_id not in releases:
        raise HTTPException(status_code=404, detail="Release not found")
    return releases[release_id]


def _list_releases(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List all releases."""
    project_name = payload.get("project_name")
    environment = payload.get("environment")
    status = payload.get("status")
    limit = payload.get("limit", 100)

    filtered_releases = list(releases.values())

    if project_name:
        filtered_releases = [r for r in filtered_releases if r.get("project_name") == project_name]
    if environment:
        filtered_releases = [r for r in filtered_releases if r.get("environment") == environment]
    if status:
        filtered_releases = [r for r in filtered_releases if r.get("status") == status]

    # Sort by created_at descending
    filtered_releases.sort(key=lambda r: r.get("created_at", 0), reverse=True)

    return filtered_releases[:limit]


def _update_release(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update a release."""
    release_id = payload.get("release_id")
    if not release_id or release_id not in releases:
        raise HTTPException(status_code=404, detail="Release not found")

    release = releases[release_id].copy()

    # Update allowed fields
    if "description" in payload:
        release["description"] = payload["description"]
    if "changes" in payload:
        release["changes"] = payload["changes"]
    if "environment" in payload:
        release["environment"] = payload["environment"]
    if "approvers" in payload:
        release["approvers"] = payload["approvers"]
        # Reinitialize approvals
        release["approvals"] = []
        for approver in release["approvers"]:
            release["approvals"].append({
                "approver": approver,
                "status": "pending",
                "comment": "",
                "approved_at": 0,
            })

    release["updated_at"] = int(datetime.now().timestamp() * 1000)
    releases[release_id] = release

    _add_release_event(
        release_id,
        "updated",
        "Release updated",
        "system"
    )

    logger.info(f"Updated release {release_id}")
    return release


def _delete_release(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a release."""
    release_id = payload.get("release_id")
    if not release_id or release_id not in releases:
        raise HTTPException(status_code=404, detail="Release not found")

    del releases[release_id]
    if release_id in release_history:
        del release_history[release_id]

    logger.info(f"Deleted release {release_id}")
    return {"deleted": release_id}


def _build_release(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build a release package."""
    release_id = payload.get("release_id")
    if not release_id or release_id not in releases:
        raise HTTPException(status_code=404, detail="Release not found")

    release = releases[release_id]
    build_type = payload.get("build_type", "docker")
    build_args = payload.get("build_args", {})

    # Update release status
    release["status"] = "building"
    release["updated_at"] = int(datetime.now().timestamp() * 1000)

    try:
        if build_type == "docker":
            dockerfile_path = payload.get("dockerfile_path", "Dockerfile")
            if not os.path.exists(dockerfile_path):
                # Use a default path for demonstration
                dockerfile_path = "./Dockerfile"

            build_info = release_builder.build_docker_image(
                project_name=release["project_name"],
                version=release["version"],
                dockerfile_path=dockerfile_path,
                build_args=build_args,
            )
        elif build_type == "package":
            source_path = payload.get("source_path", ".")
            build_info = release_builder.build_package(
                project_name=release["project_name"],
                version=release["version"],
                source_path=source_path,
                build_args=build_args,
            )
        elif build_type == "binary":
            source_path = payload.get("source_path", ".")
            build_command = payload.get("build_command", ["make", "build"])
            build_info = release_builder.build_binary(
                project_name=release["project_name"],
                version=release["version"],
                source_path=source_path,
                build_args=build_args,
                build_command=build_command,
            )
        else:
            raise ValueError(f"Unsupported build type: {build_type}")

        # Update release with build info
        release["build_info"] = build_info.to_dict()

        if build_info.status == "success":
            release["status"] = "built"
            _add_release_event(
                release_id,
                "built",
                f"Build completed successfully: {build_info.build_id}",
                "system",
                {"build_id": build_info.build_id, "artifact_path": build_info.artifact_path}
            )
        else:
            release["status"] = "failed"
            _add_release_event(
                release_id,
                "build_failed",
                f"Build failed: {build_info.error_message}",
                "system",
                {"build_id": build_info.build_id, "error": build_info.error_message}
            )

        release["updated_at"] = int(datetime.now().timestamp() * 1000)
        releases[release_id] = release

        return {
            "release_id": release_id,
            "build_id": build_info.build_id,
            "status": build_info.status,
            "artifact_path": build_info.artifact_path,
            "duration_ms": build_info.duration_ms,
        }

    except Exception as e:
        release["status"] = "failed"
        release["updated_at"] = int(datetime.now().timestamp() * 1000)
        releases[release_id] = release
        logger.error(f"Build failed for release {release_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _deploy_release(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Deploy a release."""
    release_id = payload.get("release_id")
    if not release_id or release_id not in releases:
        raise HTTPException(status_code=404, detail="Release not found")

    release = releases[release_id]

    # Check if release is built
    if not release.get("build_info") or release["build_info"].get("status") != "success":
        raise HTTPException(status_code=400, detail="Release must be built before deployment")

    # Check approval if required
    if release.get("requires_approval"):
        approved_count = sum(1 for a in release.get("approvals", []) if a.get("status") == "approved")
        if approved_count < len(release.get("approvers", [])):
            raise HTTPException(status_code=400, detail="Release requires approval before deployment")

    target_environment = payload.get("target_environment")
    target_hosts = payload.get("target_hosts", [])
    deployment_config = payload.get("deployment_config", {})
    rollback_on_failure = payload.get("rollback_on_failure", False)

    # Update release status
    release["status"] = "deploying"
    release["updated_at"] = int(datetime.now().timestamp() * 1000)

    try:
        deployment_id = str(uuid4())
        artifact_path = release["build_info"]["artifact_path"]

        if release["build_info"]["build_type"] == "docker":
            deployment_info = deployment_manager.deploy_docker(
                deployment_id=deployment_id,
                artifact_path=artifact_path,
                target_environment=target_environment,
                target_hosts=target_hosts,
                deployment_config=deployment_config,
                rollback_on_failure=rollback_on_failure,
            )
        else:
            deployment_info = deployment_manager.deploy_package(
                deployment_id=deployment_id,
                artifact_path=artifact_path,
                target_environment=target_environment,
                target_hosts=target_hosts,
                deployment_config=deployment_config,
                rollback_on_failure=rollback_on_failure,
            )

        # Update release with deployment info
        release["deployment_info"] = deployment_info.to_dict()

        if deployment_info.status == "success":
            release["status"] = "deployed"
            release["environment"] = target_environment
            _add_release_event(
                release_id,
                "deployed",
                f"Deployed to {target_environment}",
                "system",
                {"deployment_id": deployment_id, "environment": target_environment}
            )
        elif deployment_info.status == "partial":
            release["status"] = "partially_deployed"
            _add_release_event(
                release_id,
                "partially_deployed",
                f"Partially deployed to {target_environment}",
                "system",
                {"deployment_id": deployment_id, "environment": target_environment}
            )
        else:
            release["status"] = "failed"
            _add_release_event(
                release_id,
                "deployment_failed",
                f"Deployment failed: {deployment_info.error_message}",
                "system",
                {"deployment_id": deployment_id, "error": deployment_info.error_message}
            )

        release["updated_at"] = int(datetime.now().timestamp() * 1000)
        releases[release_id] = release

        return {
            "release_id": release_id,
            "deployment_id": deployment_id,
            "status": deployment_info.status,
            "duration_ms": deployment_info.duration_ms,
            "results": [r.to_dict() for r in deployment_info.results],
        }

    except Exception as e:
        release["status"] = "failed"
        release["updated_at"] = int(datetime.now().timestamp() * 1000)
        releases[release_id] = release
        logger.error(f"Deployment failed for release {release_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _rollback_release(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Rollback a release."""
    release_id = payload.get("release_id")
    if not release_id or release_id not in releases:
        raise HTTPException(status_code=404, detail="Release not found")

    release = releases[release_id]

    if not release.get("deployment_info"):
        raise HTTPException(status_code=400, detail="No deployment to rollback")

    rollback_to_version = payload.get("rollback_to_version")
    reason = payload.get("reason", "")
    force = payload.get("force", False)

    try:
        deployment_id = release["deployment_info"]["deployment_id"]
        rollback_info = deployment_manager.rollback_deployment(
            deployment_id=deployment_id,
            rollback_to_version=rollback_to_version,
            reason=reason,
            force=force,
        )

        # Update release status
        if rollback_info.status == "success":
            release["status"] = "rolled_back"
            _add_release_event(
                release_id,
                "rolled_back",
                f"Rolled back to {rollback_to_version}",
                "system",
                {"rollback_id": rollback_info.deployment_id, "reason": reason}
            )
        else:
            release["status"] = "rollback_failed"
            _add_release_event(
                release_id,
                "rollback_failed",
                f"Rollback failed: {rollback_info.error_message}",
                "system",
                {"rollback_id": rollback_info.deployment_id, "error": rollback_info.error_message}
            )

        release["updated_at"] = int(datetime.now().timestamp() * 1000)
        releases[release_id] = release

        return {
            "release_id": release_id,
            "rollback_id": rollback_info.deployment_id,
            "status": rollback_info.status,
            "duration_ms": rollback_info.duration_ms,
        }

    except Exception as e:
        release["status"] = "rollback_failed"
        release["updated_at"] = int(datetime.now().timestamp() * 1000)
        releases[release_id] = release
        logger.error(f"Rollback failed for release {release_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _approve_release(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Approve a release."""
    release_id = payload.get("release_id")
    if not release_id or release_id not in releases:
        raise HTTPException(status_code=404, detail="Release not found")

    release = releases[release_id]
    approver = payload.get("approver")
    comment = payload.get("comment", "")

    if not release.get("requires_approval"):
        raise HTTPException(status_code=400, detail="Release does not require approval")

    # Find and update approval
    approval_found = False
    for approval in release.get("approvals", []):
        if approval["approver"] == approver:
            approval["status"] = "approved"
            approval["comment"] = comment
            approval["approved_at"] = int(datetime.now().timestamp() * 1000)
            approval_found = True
            break

    if not approval_found:
        raise HTTPException(status_code=400, detail=f"Approver {approver} not in approvers list")

    # Check if all approvals are received
    approved_count = sum(1 for a in release.get("approvals", []) if a.get("status") == "approved")
    if approved_count == len(release.get("approvers", [])):
        release["status"] = "approved"
    else:
        release["status"] = "pending"

    release["updated_at"] = int(datetime.now().timestamp() * 1000)
    releases[release_id] = release

    _add_release_event(
        release_id,
        "approved",
        f"Approved by {approver}",
        approver,
        {"comment": comment}
    )

    logger.info(f"Release {release_id} approved by {approver}")
    return release


def _reject_release(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Reject a release."""
    release_id = payload.get("release_id")
    if not release_id or release_id not in releases:
        raise HTTPException(status_code=404, detail="Release not found")

    release = releases[release_id]
    rejecter = payload.get("rejecter")
    reason = payload.get("reason", "")

    release["status"] = "rejected"
    release["updated_at"] = int(datetime.now().timestamp() * 1000)
    releases[release_id] = release

    _add_release_event(
        release_id,
        "rejected",
        f"Rejected by {rejecter}: {reason}",
        rejecter,
        {"reason": reason}
    )

    logger.info(f"Release {release_id} rejected by {rejecter}")
    return release


def _get_release_history(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get release history."""
    release_id = payload.get("release_id")
    limit = payload.get("limit", 100)

    if not release_id or release_id not in release_history:
        return []

    events = release_history[release_id][-limit:]
    return events


def _get_release_status(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Get release status."""
    release_id = payload.get("release_id")
    if not release_id or release_id not in releases:
        raise HTTPException(status_code=404, detail="Release not found")

    release = releases[release_id]

    # Calculate approval status
    approval_status = "not_required"
    pending_approvals = []
    completed_approvals = []

    if release.get("requires_approval"):
        approval_status = "pending"
        for approval in release.get("approvals", []):
            if approval["status"] == "pending":
                pending_approvals.append(approval["approver"])
            elif approval["status"] == "approved":
                completed_approvals.append(approval["approver"])

        if not pending_approvals:
            approval_status = "approved"

    # Calculate progress
    progress = 0
    current_steps = []
    completed_steps = []

    status = release.get("status", "draft")
    if status == "draft":
        progress = 10
        current_steps = ["Create release", "Request approval"]
        completed_steps = []
    elif status == "pending":
        progress = 30
        current_steps = ["Awaiting approval"]
        completed_steps = ["Create release"]
    elif status == "approved":
        progress = 50
        current_steps = ["Build release"]
        completed_steps = ["Create release", "Approval received"]
    elif status == "building":
        progress = 60
        current_steps = ["Building"]
        completed_steps = ["Create release", "Approval received"]
    elif status == "built":
        progress = 70
        current_steps = ["Deploy release"]
        completed_steps = ["Create release", "Approval received", "Build completed"]
    elif status == "deploying":
        progress = 80
        current_steps = ["Deploying"]
        completed_steps = ["Create release", "Approval received", "Build completed"]
    elif status == "deployed":
        progress = 100
        current_steps = []
        completed_steps = ["Create release", "Approval received", "Build completed", "Deployment completed"]
    elif status == "rolled_back":
        progress = 100
        current_steps = []
        completed_steps = ["Create release", "Deployment completed", "Rollback completed"]
    elif status in ["failed", "rejected"]:
        progress = 0
        current_steps = []
        completed_steps = []

    return {
        "release_id": release_id,
        "version": release["version"],
        "current_status": status,
        "build_status": release.get("build_info", {}).get("status", "not_started"),
        "deployment_status": release.get("deployment_info", {}).get("status", "not_started"),
        "approval_status": approval_status,
        "pending_approvals": pending_approvals,
        "completed_approvals": completed_approvals,
        "progress_percentage": progress,
        "current_steps": current_steps,
        "completed_steps": completed_steps,
    }


def _create_version(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new version."""
    project_name = payload.get("project_name")
    base_version = payload.get("base_version")
    increment_type = payload.get("increment_type", "patch")
    pre_release = payload.get("pre_release", "")
    pre_release_number = payload.get("pre_release_number", 0)
    build_metadata = payload.get("build_metadata", "")

    version = version_manager.create_version(
        project_name=project_name,
        base_version=base_version,
        increment_type=increment_type,
        pre_release=pre_release,
        pre_release_number=pre_release_number,
        build_metadata=build_metadata,
    )

    return version.to_dict()


def _get_version(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Get a version."""
    project_name = payload.get("project_name")
    version_string = payload.get("version")

    version = version_manager.get_version(project_name, version_string)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return version.to_dict()


def _list_versions(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List versions."""
    project_name = payload.get("project_name")
    limit = payload.get("limit", 100)
    offset = payload.get("offset", 0)

    versions = version_manager.list_versions(project_name, limit, offset)
    return [v.to_dict() for v in versions]


def _increment_version(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Increment a version."""
    project_name = payload.get("project_name")
    current_version = payload.get("current_version")
    increment_type = payload.get("increment_type", "patch")
    pre_release = payload.get("pre_release", "")
    pre_release_number = payload.get("pre_release_number", 0)

    version = version_manager.create_version(
        project_name=project_name,
        base_version=current_version,
        increment_type=increment_type,
        pre_release=pre_release,
        pre_release_number=pre_release_number,
    )

    return version.to_dict()


def _compare_versions(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two versions."""
    version1 = payload.get("version1")
    version2 = payload.get("version2")

    comparison_result = version_manager.compare_versions(version1, version2)
    difference = version_manager.get_version_difference(version1, version2)

    return {
        "version1": version1,
        "version2": version2,
        "comparison_result": comparison_result,
        "difference": difference,
    }


# Register handlers
HANDLERS = {
    "create_release": _create_release,
    "get_release": _get_release,
    "list_releases": _list_releases,
    "update_release": _update_release,
    "delete_release": _delete_release,
    "build_release": _build_release,
    "deploy_release": _deploy_release,
    "rollback_release": _rollback_release,
    "approve_release": _approve_release,
    "reject_release": _reject_release,
    "get_release_history": _get_release_history,
    "get_release_status": _get_release_status,
    "create_version": _create_version,
    "get_version": _get_version,
    "list_versions": _list_versions,
    "increment_version": _increment_version,
    "compare_versions": _compare_versions,
}

# Register RPC handlers
for name, handler in HANDLERS.items():
    rpc_server.register(name, handler)


# FastAPI endpoints
@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        service=Config.SERVICE_NAME,
        release_count=len(releases),
        version_count=len(version_manager.get_all_projects()),
        build_count=len(release_builder.list_builds()),
        deployment_count=len(deployment_manager.list_deployments()),
    )


@app.get("/info", response_model=InfoResponse)
async def info() -> InfoResponse:
    """Service info endpoint."""
    return InfoResponse(service=Config.SERVICE_NAME)


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(req: InvokeRequest) -> InvokeResponse:
    """Generic invoke endpoint for all actions."""
    handler = HANDLERS.get(req.action)
    if not handler:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")

    try:
        result = handler(req.payload)
        return InvokeResponse(
            success=True, service=Config.SERVICE_NAME, action=req.action, result=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Invoke failed for action {req.action}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rpc/{method}")
async def rpc_call(method: str, payload: Dict[str, Any] = None):
    """RPC endpoint for inter-service communication."""
    try:
        result = await rpc_server.call(method, payload or {})
        return {"success": True, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"RPC call {method} failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rpc")
async def list_rpc_methods():
    """List available RPC methods."""
    return {"methods": rpc_server.list_methods()}


# Lifecycle events
@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info(f"Starting {Config.SERVICE_NAME}")
    await rpc_server.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info(f"Shutting down {Config.SERVICE_NAME}")
    await rpc_server.stop()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=Config.HOST, port=Config.PORT)
