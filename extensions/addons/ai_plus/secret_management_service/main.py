# -*- coding: utf-8 -*-
"""Main entry point for Secret Management Service."""

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
    from .access_control import AccessControl
    from .audit_log import AuditLog
    from .config import Config
    from .encryption_service import EncryptionService
    from .grpc.server import SecretManagementRPCServer
    from .secret_manager import SecretManager
except ImportError:
    from access_control import AccessControl
    from audit_log import AuditLog
    from config import Config
    from encryption_service import EncryptionService
    from grpc.server import SecretManagementRPCServer
    from secret_manager import SecretManager

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
secret_manager = SecretManager()
encryption_service = EncryptionService()
access_control = AccessControl()
audit_log = AuditLog()
rpc_server = SecretManagementRPCServer()

# In-memory storage for additional data
rotation_tasks: Dict[str, asyncio.Task] = {}


# Pydantic models
class CreateSecretRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1)
    description: str = ""
    created_by: str = ""
    tags: Dict[str, str] = Field(default_factory=dict)
    principal: str = ""


class UpdateSecretRequest(BaseModel):
    secret_id: str = Field(..., min_length=1)
    value: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    updated_by: str = ""
    principal: str = ""


class RotateSecretRequest(BaseModel):
    secret_id: str = Field(..., min_length=1)
    new_value: str = Field(..., min_length=1)
    rotated_by: str = ""
    old_value_retention_hours: int = 24
    principal: str = ""


class GrantAccessRequest(BaseModel):
    secret_id: str = Field(..., min_length=1)
    principal: str = Field(..., min_length=1)
    principal_type: str = Field(..., pattern="^(user|service|role)$")
    permissions: List[str] = Field(..., min_items=1)
    granted_by: str = ""


class RevokeAccessRequest(BaseModel):
    secret_id: str = Field(..., min_length=1)
    principal: str = Field(..., min_length=1)
    revoked_by: str = ""


class GetSecretRequest(BaseModel):
    secret_id: str = Field(..., min_length=1)
    include_value: bool = False
    version: int = 0
    principal: str = ""


class ListSecretsRequest(BaseModel):
    filter_status: str = "active"
    filter_tag: Optional[str] = None
    limit: int = 100
    offset: int = 0
    principal: str = ""


class GetAuditLogRequest(BaseModel):
    secret_id: Optional[str] = None
    action: Optional[str] = None
    principal: Optional[str] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    limit: int = 100
    offset: int = 0


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = Config.SERVICE_NAME
    secret_count: int
    audit_log_count: int


class InfoResponse(BaseModel):
    service: str
    version: str = "1.0.0"
    status: str = "running"


class InvokeRequest(BaseModel):
    action: str = Field(
        ...,
        pattern="^(create_secret|get_secret|update_secret|delete_secret|list_secrets|"
        "rotate_secret|get_secret_versions|revert_secret_version|grant_access|"
        "revoke_access|list_access|get_audit_log|health_check)$"
    )
    payload: Dict[str, Any] = Field(default_factory=dict)


class InvokeResponse(BaseModel):
    success: bool
    service: str
    action: str
    result: Any


# Helper functions
def _create_secret(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new secret."""
    try:
        secret = secret_manager.create_secret(
            name=payload["name"],
            value=payload["value"],
            description=payload.get("description", ""),
            created_by=payload.get("created_by", ""),
            tags=payload.get("tags", {}),
            principal=payload.get("principal", ""),
        )

        # Log audit event
        audit_log.log(
            secret_id=secret.metadata.secret_id,
            action="create",
            principal=payload.get("principal", "system"),
            result="success",
            details=f"Created secret: {secret.metadata.name}",
        )

        return secret.to_dict(include_value=False)

    except PermissionError as e:
        audit_log.log(
            secret_id=payload.get("name", "unknown"),
            action="create",
            principal=payload.get("principal", "unknown"),
            result="failure",
            details=str(e),
        )
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create secret: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_secret(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Get a secret."""
    try:
        result = secret_manager.get_secret(
            secret_id=payload["secret_id"],
            include_value=payload.get("include_value", False),
            version=payload.get("version", 0),
            principal=payload.get("principal", ""),
        )

        # Log audit event
        audit_log.log(
            secret_id=payload["secret_id"],
            action="read",
            principal=payload.get("principal", "system"),
            result="success",
        )

        return result

    except PermissionError as e:
        audit_log.log(
            secret_id=payload["secret_id"],
            action="read",
            principal=payload.get("principal", "unknown"),
            result="failure",
            details=str(e),
        )
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        audit_log.log(
            secret_id=payload["secret_id"],
            action="read",
            principal=payload.get("principal", "unknown"),
            result="failure",
            details=str(e),
        )
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get secret: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _update_secret(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update a secret."""
    try:
        secret = secret_manager.update_secret(
            secret_id=payload["secret_id"],
            value=payload.get("value"),
            description=payload.get("description"),
            tags=payload.get("tags"),
            updated_by=payload.get("updated_by", ""),
            principal=payload.get("principal", ""),
        )

        # Log audit event
        audit_log.log(
            secret_id=payload["secret_id"],
            action="update",
            principal=payload.get("principal", "system"),
            result="success",
        )

        return secret.to_dict(include_value=False)

    except PermissionError as e:
        audit_log.log(
            secret_id=payload["secret_id"],
            action="update",
            principal=payload.get("principal", "unknown"),
            result="failure",
            details=str(e),
        )
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        audit_log.log(
            secret_id=payload["secret_id"],
            action="update",
            principal=payload.get("principal", "unknown"),
            result="failure",
            details=str(e),
        )
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update secret: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _delete_secret(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a secret."""
    try:
        success = secret_manager.delete_secret(
            secret_id=payload["secret_id"],
            permanent=payload.get("permanent", False),
            principal=payload.get("principal", ""),
        )

        # Log audit event
        audit_log.log(
            secret_id=payload["secret_id"],
            action="delete",
            principal=payload.get("principal", "system"),
            result="success",
            details=f"Permanent: {payload.get('permanent', False)}",
        )

        return {"deleted": payload["secret_id"], "success": success}

    except PermissionError as e:
        audit_log.log(
            secret_id=payload["secret_id"],
            action="delete",
            principal=payload.get("principal", "unknown"),
            result="failure",
            details=str(e),
        )
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        audit_log.log(
            secret_id=payload["secret_id"],
            action="delete",
            principal=payload.get("principal", "unknown"),
            result="failure",
            details=str(e),
        )
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete secret: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _list_secrets(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List secrets."""
    try:
        return secret_manager.list_secrets(
            filter_status=payload.get("filter_status", "active"),
            filter_tag=payload.get("filter_tag"),
            limit=payload.get("limit", 100),
            offset=payload.get("offset", 0),
            principal=payload.get("principal", ""),
        )
    except Exception as e:
        logger.error(f"Failed to list secrets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _rotate_secret(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Rotate a secret."""
    try:
        secret = secret_manager.rotate_secret(
            secret_id=payload["secret_id"],
            new_value=payload["new_value"],
            rotated_by=payload.get("rotated_by", ""),
            old_value_retention_hours=payload.get("old_value_retention_hours", 24),
            principal=payload.get("principal", ""),
        )

        # Log audit event
        audit_log.log(
            secret_id=payload["secret_id"],
            action="rotate",
            principal=payload.get("principal", "system"),
            result="success",
        )

        return secret.to_dict(include_value=False)

    except PermissionError as e:
        audit_log.log(
            secret_id=payload["secret_id"],
            action="rotate",
            principal=payload.get("principal", "unknown"),
            result="failure",
            details=str(e),
        )
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        audit_log.log(
            secret_id=payload["secret_id"],
            action="rotate",
            principal=payload.get("principal", "unknown"),
            result="failure",
            details=str(e),
        )
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to rotate secret: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_secret_versions(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get secret versions."""
    try:
        return secret_manager.get_secret_versions(
            secret_id=payload["secret_id"],
            principal=payload.get("principal", ""),
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get secret versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _revert_secret_version(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Revert to a specific version."""
    try:
        secret = secret_manager.revert_secret_version(
            secret_id=payload["secret_id"],
            target_version=payload["target_version"],
            reverted_by=payload.get("reverted_by", ""),
            principal=payload.get("principal", ""),
        )

        # Log audit event
        audit_log.log(
            secret_id=payload["secret_id"],
            action="revert_version",
            principal=payload.get("principal", "system"),
            result="success",
            details=f"Reverted to version {payload['target_version']}",
        )

        return secret.to_dict(include_value=False)

    except PermissionError as e:
        audit_log.log(
            secret_id=payload["secret_id"],
            action="revert_version",
            principal=payload.get("principal", "unknown"),
            result="failure",
            details=str(e),
        )
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        audit_log.log(
            secret_id=payload["secret_id"],
            action="revert_version",
            principal=payload.get("principal", "unknown"),
            result="failure",
            details=str(e),
        )
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to revert secret version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _grant_access(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Grant access to a secret."""
    try:
        success = access_control.grant_access(
            secret_id=payload["secret_id"],
            principal=payload["principal"],
            principal_type=payload["principal_type"],
            permissions=payload["permissions"],
            granted_by=payload.get("granted_by", ""),
        )

        # Log audit event
        audit_log.log(
            secret_id=payload["secret_id"],
            action="grant_access",
            principal=payload.get("granted_by", "system"),
            result="success",
            details=f"Granted {payload['permissions']} to {payload['principal']}",
        )

        return {"success": success}

    except Exception as e:
        logger.error(f"Failed to grant access: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _revoke_access(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Revoke access to a secret."""
    try:
        success = access_control.revoke_access(
            secret_id=payload["secret_id"],
            principal=payload["principal"],
            revoked_by=payload.get("revoked_by", ""),
        )

        # Log audit event
        audit_log.log(
            secret_id=payload["secret_id"],
            action="revoke_access",
            principal=payload.get("revoked_by", "system"),
            result="success",
            details=f"Revoked access for {payload['principal']}",
        )

        return {"success": success}

    except Exception as e:
        logger.error(f"Failed to revoke access: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _list_access(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List access permissions."""
    try:
        return access_control.get_permissions(payload["secret_id"])
    except Exception as e:
        logger.error(f"Failed to list access: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_audit_log(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Get audit log."""
    try:
        entries = audit_log.query(
            secret_id=payload.get("secret_id"),
            action=payload.get("action"),
            principal=payload.get("principal"),
            start_time=payload.get("start_time"),
            end_time=payload.get("end_time"),
            limit=payload.get("limit", 100),
            offset=payload.get("offset", 0),
        )
        return {"entries": entries, "total_count": len(entries)}
    except Exception as e:
        logger.error(f"Failed to get audit log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _health_check(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Health check."""
    return {
        "healthy": True,
        "status": "ok",
        "version": "1.0.0",
        "timestamp": int(datetime.now().timestamp() * 1000),
    }


# Register handlers
HANDLERS = {
    "create_secret": _create_secret,
    "get_secret": _get_secret,
    "update_secret": _update_secret,
    "delete_secret": _delete_secret,
    "list_secrets": _list_secrets,
    "rotate_secret": _rotate_secret,
    "get_secret_versions": _get_secret_versions,
    "revert_secret_version": _revert_secret_version,
    "grant_access": _grant_access,
    "revoke_access": _revoke_access,
    "list_access": _list_access,
    "get_audit_log": _get_audit_log,
    "health_check": _health_check,
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
        secret_count=len(secret_manager._secrets),
        audit_log_count=len(audit_log._logs),
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
    await rpc_server.start(Config.GRPC_HOST, Config.GRPC_PORT)

    # Start background task for scheduled rotations
    asyncio.create_task(rotation_scheduler())


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info(f"Shutting down {Config.SERVICE_NAME}")
    await rpc_server.stop()

    # Cancel rotation tasks
    for task in rotation_tasks.values():
        task.cancel()


async def rotation_scheduler():
    """Background task for scheduled secret rotations."""
    while True:
        try:
            # Check for due rotations
            schedule = secret_manager.get_rotation_schedule()
            current_time = int(datetime.now().timestamp() * 1000)

            for item in schedule:
                if item["is_due"]:
                    logger.info(f"Rotation due for secret: {item['name']}")
                    # In a real implementation, this would trigger rotation
                    # For now, just log it

            # Check every minute
            await asyncio.sleep(60)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Rotation scheduler error: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=Config.HOST, port=Config.PORT)
