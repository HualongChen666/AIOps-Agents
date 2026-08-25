# -*- coding: utf-8 -*-
"""Main entry point for Dependency Management Service."""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from .config import Config
from .dependency_scanner import Dependency, DependencyScanner, ScanMetadata
from .grpc.server import DependencyManagementRPCServer
from .update_manager import Conflict, UpdateManager, UpdateResult
from .version_checker import OutdatedPackage, VersionChecker, Vulnerability

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
dependency_scanner = DependencyScanner()
version_checker = VersionChecker()
update_manager = UpdateManager()
rpc_server = DependencyManagementRPCServer()

# In-memory storage
scan_results: Dict[str, Dict[str, Any]] = {}
check_results: Dict[str, Dict[str, Any]] = {}


# Pydantic models
class ScanRequestModel(BaseModel):
    project_path: str
    scan_types: Optional[List[str]] = None


class CheckOutdatedRequestModel(BaseModel):
    project_path: str
    package_names: Optional[List[str]] = None


class CheckVulnerabilitiesRequestModel(BaseModel):
    project_path: str
    package_names: Optional[List[str]] = None
    severity_level: str = "medium"


class UpdateRequestModel(BaseModel):
    project_path: str
    package_names: Optional[List[str]] = None
    update_type: str = "all"
    dry_run: bool = False


class DetectConflictsRequestModel(BaseModel):
    project_path: str
    package_names: Optional[List[str]] = None


class GenerateLockRequestModel(BaseModel):
    project_path: str
    lock_file_type: str = "requirements.lock"


class GetTreeRequestModel(BaseModel):
    project_path: str
    package_name: str
    depth: int = 3


class ResolveRequestModel(BaseModel):
    project_path: str
    requirements: List[str]


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = Config.SERVICE_NAME
    scan_count: int
    check_count: int


class InfoResponse(BaseModel):
    service: str
    version: str = "1.0.0"
    status: str = "running"


class InvokeRequest(BaseModel):
    action: str = Field(
        ...,
        pattern="^(scan_dependencies|check_outdated|check_vulnerabilities|"
        "update_dependencies|detect_conflicts|generate_lock_file|"
        "get_dependency_tree|resolve_dependencies)$"
    )
    payload: Dict[str, Any] = Field(default_factory=dict)


class InvokeResponse(BaseModel):
    success: bool
    service: str
    action: str
    result: Any


# Helper functions
def _dependency_to_dict(dep: Dependency) -> Dict[str, Any]:
    """Convert Dependency to dict."""
    return {
        "name": dep.name,
        "version": dep.version,
        "source": dep.source,
        "extras": dep.extras,
        "is_dev": dep.is_dev,
    }


def _metadata_to_dict(metadata: ScanMetadata) -> Dict[str, Any]:
    """Convert ScanMetadata to dict."""
    return {
        "scan_time": metadata.scan_time,
        "total_dependencies": metadata.total_dependencies,
        "files_scanned": metadata.files_scanned,
        "duration_seconds": metadata.duration_seconds,
    }


def _outdated_to_dict(outdated: OutdatedPackage) -> Dict[str, Any]:
    """Convert OutdatedPackage to dict."""
    return {
        "name": outdated.name,
        "current_version": outdated.current_version,
        "latest_version": outdated.latest_version,
        "latest_release_date": outdated.latest_release_date,
        "available_versions": outdated.available_versions,
        "is_major_update": outdated.is_major_update,
        "is_security_update": outdated.is_security_update,
    }


def _vulnerability_to_dict(vuln: Vulnerability) -> Dict[str, Any]:
    """Convert Vulnerability to dict."""
    return {
        "package_name": vuln.package_name,
        "affected_versions": vuln.affected_versions,
        "severity": vuln.severity,
        "cve_id": vuln.cve_id,
        "description": vuln.description,
        "published_date": vuln.published_date,
        "fixed_in_version": vuln.fixed_in_version,
        "references": vuln.references,
    }


def _update_result_to_dict(result: UpdateResult) -> Dict[str, Any]:
    """Convert UpdateResult to dict."""
    return {
        "package_name": result.package_name,
        "old_version": result.old_version,
        "new_version": result.new_version,
        "success": result.success,
        "message": result.message,
    }


def _conflict_to_dict(conflict: Conflict) -> Dict[str, Any]:
    """Convert Conflict to dict."""
    return {
        "package_name": conflict.package_name,
        "conflict_type": conflict.conflict_type,
        "conflicting_packages": conflict.conflicting_packages,
        "description": conflict.description,
        "resolution_suggestion": conflict.resolution_suggestion,
    }


# Handler functions
def _scan_dependencies(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Scan dependencies from a project."""
    project_path = payload.get("project_path")
    scan_types = payload.get("scan_types")

    if not project_path:
        raise HTTPException(status_code=400, detail="project_path is required")

    try:
        dependencies, metadata = dependency_scanner.scan_project(project_path, scan_types)

        scan_id = str(uuid4())
        scan_results[scan_id] = {
            "id": scan_id,
            "project_path": project_path,
            "dependencies": [_dependency_to_dict(d) for d in dependencies],
            "metadata": _metadata_to_dict(metadata),
            "scanned_at": datetime.now().isoformat(),
        }

        logger.info(f"Scanned {len(dependencies)} dependencies from {project_path}")

        return {
            "scan_id": scan_id,
            "dependencies": [_dependency_to_dict(d) for d in dependencies],
            "metadata": _metadata_to_dict(metadata),
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error scanning dependencies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _check_outdated(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Check for outdated dependencies."""
    project_path = payload.get("project_path")
    package_names = payload.get("package_names")

    if not project_path:
        raise HTTPException(status_code=400, detail="project_path is required")

    try:
        # First scan the project to get dependencies
        dependencies, _ = dependency_scanner.scan_project(project_path)

        # Check for outdated packages
        outdated = version_checker.check_outdated(dependencies, package_names)

        check_id = str(uuid4())
        check_results[check_id] = {
            "id": check_id,
            "project_path": project_path,
            "outdated": [_outdated_to_dict(o) for o in outdated],
            "checked_at": datetime.now().isoformat(),
        }

        logger.info(f"Found {len(outdated)} outdated packages in {project_path}")

        return {
            "check_id": check_id,
            "outdated": [_outdated_to_dict(o) for o in outdated],
            "total_outdated": len(outdated),
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error checking outdated packages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _check_vulnerabilities(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Check for security vulnerabilities."""
    project_path = payload.get("project_path")
    package_names = payload.get("package_names")
    severity_level = payload.get("severity_level", "medium")

    if not project_path:
        raise HTTPException(status_code=400, detail="project_path is required")

    try:
        # First scan the project to get dependencies
        dependencies, _ = dependency_scanner.scan_project(project_path)

        # Check for vulnerabilities
        vulnerabilities = version_checker.check_vulnerabilities(
            dependencies, package_names, severity_level
        )

        check_id = str(uuid4())
        check_results[check_id] = {
            "id": check_id,
            "project_path": project_path,
            "vulnerabilities": [_vulnerability_to_dict(v) for v in vulnerabilities],
            "checked_at": datetime.now().isoformat(),
        }

        logger.warning(f"Found {len(vulnerabilities)} vulnerabilities in {project_path}")

        return {
            "check_id": check_id,
            "vulnerabilities": [_vulnerability_to_dict(v) for v in vulnerabilities],
            "total_vulnerabilities": len(vulnerabilities),
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error checking vulnerabilities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _update_dependencies(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update dependencies."""
    project_path = payload.get("project_path")
    package_names = payload.get("package_names")
    update_type = payload.get("update_type", "all")
    dry_run = payload.get("dry_run", False)

    if not project_path:
        raise HTTPException(status_code=400, detail="project_path is required")

    try:
        results, warnings = update_manager.update_dependencies(
            project_path, package_names, update_type, dry_run
        )

        logger.info(f"Updated {len(results)} packages in {project_path}")

        return {
            "results": [_update_result_to_dict(r) for r in results],
            "warnings": warnings,
            "total_updated": len([r for r in results if r.success]),
            "total_failed": len([r for r in results if not r.success]),
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating dependencies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _detect_conflicts(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Detect dependency conflicts."""
    project_path = payload.get("project_path")
    package_names = payload.get("package_names")

    if not project_path:
        raise HTTPException(status_code=400, detail="project_path is required")

    try:
        conflicts = update_manager.detect_conflicts(project_path, package_names)

        logger.info(f"Found {len(conflicts)} conflicts in {project_path}")

        return {
            "conflicts": [_conflict_to_dict(c) for c in conflicts],
            "total_conflicts": len(conflicts),
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error detecting conflicts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _generate_lock_file(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a lock file."""
    project_path = payload.get("project_path")
    lock_file_type = payload.get("lock_file_type", "requirements.lock")

    if not project_path:
        raise HTTPException(status_code=400, detail="project_path is required")

    try:
        lock_file_path, dependency_count = update_manager.generate_lock_file(
            project_path, lock_file_type
        )

        logger.info(f"Generated lock file: {lock_file_path} with {dependency_count} dependencies")

        return {
            "lock_file_path": lock_file_path,
            "dependency_count": dependency_count,
            "lock_file_type": lock_file_type,
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating lock file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _get_dependency_tree(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Get dependency tree for a package."""
    project_path = payload.get("project_path")
    package_name = payload.get("package_name")
    depth = payload.get("depth", 3)

    if not project_path or not package_name:
        raise HTTPException(status_code=400, detail="project_path and package_name are required")

    try:
        tree = dependency_scanner.get_dependency_tree(project_path, package_name, depth)

        logger.info(f"Retrieved dependency tree for {package_name}")

        return {
            "package_name": package_name,
            "tree": tree,
            "depth": depth,
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting dependency tree: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _resolve_dependencies(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve dependencies."""
    project_path = payload.get("project_path")
    requirements = payload.get("requirements")

    if not project_path or not requirements:
        raise HTTPException(status_code=400, detail="project_path and requirements are required")

    try:
        # This is a simplified implementation
        # In a real implementation, you would use pip's resolver
        resolved = []
        conflicts = []

        for req in requirements:
            try:
                # Parse the requirement
                if ">=" in req:
                    name = req.split(">=")[0].strip()
                    version = req.split(">=")[1].strip()
                elif "==" in req:
                    name = req.split("==")[0].strip()
                    version = req.split("==")[1].strip()
                else:
                    name = req.strip()
                    version = "*"

                resolved.append({
                    "name": name,
                    "version": version,
                    "dependencies": [],
                    "source": "user",
                })
            except Exception as e:
                conflicts.append(f"Failed to resolve {req}: {e}")

        logger.info(f"Resolved {len(resolved)} dependencies")

        return {
            "resolved": resolved,
            "conflicts": conflicts,
            "total_resolved": len(resolved),
            "total_conflicts": len(conflicts),
        }

    except Exception as e:
        logger.error(f"Error resolving dependencies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Register handlers
HANDLERS = {
    "scan_dependencies": _scan_dependencies,
    "check_outdated": _check_outdated,
    "check_vulnerabilities": _check_vulnerabilities,
    "update_dependencies": _update_dependencies,
    "detect_conflicts": _detect_conflicts,
    "generate_lock_file": _generate_lock_file,
    "get_dependency_tree": _get_dependency_tree,
    "resolve_dependencies": _resolve_dependencies,
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
        scan_count=len(scan_results),
        check_count=len(check_results),
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
