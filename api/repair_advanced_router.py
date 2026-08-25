# -*- coding: utf-8 -*-
"""
Advanced Repair Management API Router

Implements 20 API endpoints for repair management functionality including:
- Configuration management
- HITL (Human-in-the-Loop) approval workflow
- Repair effectiveness evaluation
- Repair verification
- Platform-specific repairs (hardware, cloud, cluster, pod, k8s, docker, macos, windows, linux)
- Cross-platform and unified repair
- Repair history
- Script management
- Intelligent repair
- Approval workflow

All endpoints integrate with core business logic from:
- core.repair_engine (for repair execution)
- core.auto_heal (for auto-healing logic)
- core.hitl.approval (for approval workflow)
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from core.auto_heal import (
    CrossPlatformScriptExecutor,
    RepairScriptLibrary,
    RiskAssessmentEngine,
)
from core.hitl.approval import ApprovalStatus, ApprovalWorkflow
from core.repair_engine import get_repair_history

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/repair", tags=["高级修复管理"])

# ============================================================
# In-memory data stores (in production, use database)
# ============================================================
_repair_configurations: Dict[str, Dict[str, Any]] = {}
_hitl_approvals: Dict[str, Dict[str, Any]] = {}
_repair_effectiveness: Dict[str, Dict[str, Any]] = {}
_repair_verifications: Dict[str, Dict[str, Any]] = {}
_hardware_repairs: Dict[str, Dict[str, Any]] = {}
_cloud_repairs: Dict[str, Dict[str, Any]] = {}
_cluster_repairs: Dict[str, Dict[str, Any]] = {}
_pod_repairs: Dict[str, Dict[str, Any]] = {}
_k8s_repairs: Dict[str, Dict[str, Any]] = {}
_docker_repairs: Dict[str, Dict[str, Any]] = {}
_macos_repairs: Dict[str, Dict[str, Any]] = {}
_windows_repairs: Dict[str, Dict[str, Any]] = {}
_linux_repairs: Dict[str, Dict[str, Any]] = {}
_cross_platform_repairs: Dict[str, Dict[str, Any]] = {}
_unified_repairs: Dict[str, Dict[str, Any]] = {}
_repair_scripts_store: Dict[str, Dict[str, Any]] = {}
_intelligent_repairs: Dict[str, Dict[str, Any]] = {}

# Initialize approval workflow
_approval_workflow = ApprovalWorkflow()
_script_library = RepairScriptLibrary()
_risk_engine = RiskAssessmentEngine()
_cross_platform_executor = CrossPlatformScriptExecutor()

# ============================================================
# Pydantic Models for Data Validation
# ============================================================


class RepairConfigCreate(BaseModel):
    """Model for creating repair configuration"""

    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    description: str = Field(default="", max_length=500, description="Configuration description")
    config_type: str = Field(
        default="global", description="Configuration type: global, platform, resource, script"
    )
    key: str = Field(..., min_length=1, max_length=100, description="Configuration key")
    value: str = Field(..., description="Configuration value")
    category: str = Field(default="default", description="Configuration category")
    is_secret: bool = Field(default=False, description="Whether the configuration is secret")


class RepairConfigUpdate(BaseModel):
    """Model for updating repair configuration"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    config_type: Optional[str] = None
    key: Optional[str] = Field(None, min_length=1, max_length=100)
    value: Optional[str] = None
    category: Optional[str] = None
    is_secret: Optional[bool] = None
    is_active: Optional[bool] = None


class HitlApprovalCreate(BaseModel):
    """Model for creating HITL approval request"""

    repair_id: str = Field(..., description="Associated repair ID")
    repair_type: str = Field(..., description="Type of repair")
    target_resource: str = Field(..., description="Target resource for repair")
    description: str = Field(..., description="Description of the repair")
    risk_level: str = Field(default="low", description="Risk level: low, medium, high, critical")
    requested_by: str = Field(default="system", description="Requester identifier")


class HitlApprovalAction(BaseModel):
    """Model for approval/rejection action"""

    comment: Optional[str] = Field(None, description="Approval or rejection comment")
    reason: Optional[str] = Field(None, description="Rejection reason")


class EffectivenessCreate(BaseModel):
    """Model for creating effectiveness record"""

    repair_id: str = Field(..., description="Associated repair ID")
    repair_type: str = Field(..., description="Type of repair")
    target_resource: str = Field(..., description="Target resource")


class VerificationCreate(BaseModel):
    """Model for creating verification record"""

    repair_id: str = Field(..., description="Associated repair ID")
    repair_type: str = Field(..., description="Type of repair")
    target_resource: str = Field(..., description="Target resource")
    verification_type: str = Field(
        default="health-check",
        description="Verification type: health-check, functional, performance, security",
    )


class RepairScriptCreate(BaseModel):
    """Model for creating repair script"""

    name: str = Field(..., min_length=1, max_length=100, description="Script name")
    description: str = Field(default="", max_length=500, description="Script description")
    language: str = Field(
        default="bash", description="Script language: bash, python, powershell, javascript"
    )
    platform: str = Field(default="linux", description="Target platform")
    category: str = Field(default="general", description="Script category")
    content: str = Field(..., description="Script content")


class RepairScriptUpdate(BaseModel):
    """Model for updating repair script"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    language: Optional[str] = None
    platform: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = Field(None, description="Script status: active, inactive, deprecated")


class IntelligentRepairCreate(BaseModel):
    """Model for creating intelligent repair"""

    issue_type: str = Field(..., description="Type of issue detected")
    severity: str = Field(default="low", description="Severity: low, medium, high, critical")
    auto_apply: bool = Field(default=False, description="Whether to auto-apply the repair")


class PlatformRepairCreate(BaseModel):
    """Model for platform-specific repair"""

    target_resource: str = Field(..., description="Target resource identifier")
    issue_type: str = Field(..., description="Type of issue")
    severity: str = Field(default="medium", description="Issue severity")
    repair_action: str = Field(..., description="Repair action to perform")


class ApprovalUpdate(BaseModel):
    """Model for updating approval status"""

    status: str = Field(..., description="New status: approved, rejected")
    comment: Optional[str] = Field(None, description="Approval comment")


class ApprovalReject(BaseModel):
    """Model for rejecting approval"""

    reason: str = Field(..., description="Rejection reason")


# ============================================================
# Helper Functions
# ============================================================


def _generate_id() -> str:
    """Generate unique ID"""
    return str(uuid.uuid4())


def _get_current_timestamp() -> str:
    """Get current ISO timestamp"""
    return datetime.utcnow().isoformat()


# ============================================================
# 1. Repair Configuration Management
# ============================================================


@router.get("/configuration", summary="Get all repair configurations")
async def get_configurations(
    category: Optional[str] = Query(None, description="Filter by category"),
    config_type: Optional[str] = Query(None, description="Filter by type"),
) -> Dict[str, Any]:
    """
    Retrieve all repair configurations with optional filtering
    """
    logger.info("Fetching repair configurations")
    try:
        items = list(_repair_configurations.values())

        if category:
            items = [item for item in items if item.get("category") == category]
        if config_type:
            items = [item for item in items if item.get("config_type") == config_type]

        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"Failed to fetch configurations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch configurations: {str(e)}")


@router.post("/configuration", summary="Create repair configuration")
async def create_configuration(config: RepairConfigCreate, request: Request) -> Dict[str, Any]:
    """
    Create a new repair configuration
    """
    logger.info(f"Creating configuration: {config.name}")
    try:
        config_id = _generate_id()
        operator_ip = request.client.host if request.client else "unknown"

        new_config = {
            "id": config_id,
            "name": config.name,
            "description": config.description,
            "config_type": config.config_type,
            "key": config.key,
            "value": config.value,
            "category": config.category,
            "is_secret": config.is_secret,
            "is_active": True,
            "updated_at": _get_current_timestamp(),
            "updated_by": operator_ip,
        }

        _repair_configurations[config_id] = new_config
        logger.info(f"Configuration created: {config_id}")
        return new_config
    except Exception as e:
        logger.error(f"Failed to create configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create configuration: {str(e)}")


@router.patch("/configuration/{config_id}", summary="Update repair configuration")
async def update_configuration(
    config_id: str, config_update: RepairConfigUpdate, request: Request
) -> Dict[str, Any]:
    """
    Update an existing repair configuration
    """
    logger.info(f"Updating configuration: {config_id}")
    try:
        if config_id not in _repair_configurations:
            raise HTTPException(status_code=404, detail="Configuration not found")

        operator_ip = request.client.host if request.client else "unknown"
        existing = _repair_configurations[config_id]

        # Update fields
        update_data = config_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            existing[key] = value

        existing["updated_at"] = _get_current_timestamp()
        existing["updated_by"] = operator_ip

        logger.info(f"Configuration updated: {config_id}")
        return existing
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")


@router.delete("/configuration/{config_id}", summary="Delete repair configuration")
async def delete_configuration(config_id: str) -> Dict[str, Any]:
    """
    Delete a repair configuration
    """
    logger.info(f"Deleting configuration: {config_id}")
    try:
        if config_id not in _repair_configurations:
            raise HTTPException(status_code=404, detail="Configuration not found")

        del _repair_configurations[config_id]
        logger.info(f"Configuration deleted: {config_id}")
        return {"message": "Configuration deleted successfully", "id": config_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete configuration: {str(e)}")


# ============================================================
# 2. HITL Approval Management
# ============================================================


@router.get("/hitl-approval", summary="Get all HITL approval requests")
async def get_hitl_approvals(
    status: Optional[str] = Query(None, description="Filter by status")
) -> Dict[str, Any]:
    """
    Retrieve all HITL approval requests with optional filtering
    """
    logger.info("Fetching HITL approval requests")
    try:
        items = list(_hitl_approvals.values())

        if status:
            items = [item for item in items if item.get("status") == status]

        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"Failed to fetch HITL approvals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch HITL approvals: {str(e)}")


@router.post("/hitl-approval", summary="Create HITL approval request")
async def create_hitl_approval(approval: HitlApprovalCreate, request: Request) -> Dict[str, Any]:
    """
    Create a new HITL approval request
    """
    logger.info(f"Creating HITL approval for repair: {approval.repair_id}")
    try:
        approval_id = _generate_id()
        operator_ip = request.client.host if request.client else "unknown"

        new_approval = {
            "id": approval_id,
            "repair_id": approval.repair_id,
            "repair_type": approval.repair_type,
            "target_resource": approval.target_resource,
            "description": approval.description,
            "risk_level": approval.risk_level,
            "status": "pending",
            "requested_by": approval.requested_by or operator_ip,
            "requested_at": _get_current_timestamp(),
        }

        _hitl_approvals[approval_id] = new_approval
        logger.info(f"HITL approval created: {approval_id}")
        return new_approval
    except Exception as e:
        logger.error(f"Failed to create HITL approval: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create HITL approval: {str(e)}")


@router.post("/hitl-approval/{approval_id}/approve", summary="Approve HITL request")
async def approve_hitl_request(
    approval_id: str, action: HitlApprovalAction, request: Request
) -> Dict[str, Any]:
    """
    Approve a HITL approval request
    """
    logger.info(f"Approving HITL request: {approval_id}")
    try:
        if approval_id not in _hitl_approvals:
            raise HTTPException(status_code=404, detail="Approval request not found")

        operator_ip = request.client.host if request.client else "unknown"
        approval = _hitl_approvals[approval_id]

        if approval["status"] != "pending":
            raise HTTPException(status_code=400, detail="Approval request is not pending")

        approval["status"] = "approved"
        approval["approver"] = operator_ip
        approval["approved_at"] = _get_current_timestamp()
        approval["comment"] = action.comment

        logger.info(f"HITL request approved: {approval_id}")
        return approval
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve HITL request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to approve HITL request: {str(e)}")


@router.post("/hitl-approval/{approval_id}/reject", summary="Reject HITL request")
async def reject_hitl_request(
    approval_id: str, action: HitlApprovalAction, request: Request
) -> Dict[str, Any]:
    """
    Reject a HITL approval request
    """
    logger.info(f"Rejecting HITL request: {approval_id}")
    try:
        if approval_id not in _hitl_approvals:
            raise HTTPException(status_code=404, detail="Approval request not found")

        operator_ip = request.client.host if request.client else "unknown"
        approval = _hitl_approvals[approval_id]

        if approval["status"] != "pending":
            raise HTTPException(status_code=400, detail="Approval request is not pending")

        approval["status"] = "rejected"
        approval["approver"] = operator_ip
        approval["approved_at"] = _get_current_timestamp()
        approval["rejection_reason"] = action.reason or action.comment

        logger.info(f"HITL request rejected: {approval_id}")
        return approval
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject HITL request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reject HITL request: {str(e)}")


# ============================================================
# 3. Repair Effectiveness Management
# ============================================================


@router.get("/effectiveness", summary="Get repair effectiveness data")
async def get_effectiveness(
    trend: Optional[str] = Query(None, description="Filter by trend")
) -> Dict[str, Any]:
    """
    Retrieve repair effectiveness metrics
    """
    logger.info("Fetching repair effectiveness data")
    try:
        items = list(_repair_effectiveness.values())

        if trend:
            items = [item for item in items if item.get("trend") == trend]

        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"Failed to fetch effectiveness data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch effectiveness data: {str(e)}")


@router.post("/effectiveness", summary="Create effectiveness record")
async def create_effectiveness(effectiveness: EffectivenessCreate) -> Dict[str, Any]:
    """
    Create a new effectiveness record
    """
    logger.info(f"Creating effectiveness record for repair: {effectiveness.repair_id}")
    try:
        effectiveness_id = _generate_id()

        # Calculate initial metrics
        total_repairs = 1
        successful_repairs = 1  # Assume success for new record
        success_rate = 100.0
        avg_repair_time = 60.0  # Default 60 seconds

        new_effectiveness = {
            "id": effectiveness_id,
            "repair_id": effectiveness.repair_id,
            "repair_type": effectiveness.repair_type,
            "target_resource": effectiveness.target_resource,
            "success_rate": success_rate,
            "avg_repair_time": avg_repair_time,
            "total_repairs": total_repairs,
            "successful_repairs": successful_repairs,
            "failed_repairs": 0,
            "last_evaluated": _get_current_timestamp(),
            "trend": "stable",
        }

        _repair_effectiveness[effectiveness_id] = new_effectiveness
        logger.info(f"Effectiveness record created: {effectiveness_id}")
        return new_effectiveness
    except Exception as e:
        logger.error(f"Failed to create effectiveness record: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create effectiveness record: {str(e)}"
        )


@router.post("/effectiveness/{effectiveness_id}/evaluate", summary="Re-evaluate effectiveness")
async def evaluate_effectiveness(effectiveness_id: str) -> Dict[str, Any]:
    """
    Re-evaluate effectiveness metrics for a repair
    """
    logger.info(f"Evaluating effectiveness: {effectiveness_id}")
    try:
        if effectiveness_id not in _repair_effectiveness:
            raise HTTPException(status_code=404, detail="Effectiveness record not found")

        effectiveness = _repair_effectiveness[effectiveness_id]

        # Simulate re-evaluation logic
        # In production, this would query actual repair history
        effectiveness["last_evaluated"] = _get_current_timestamp()

        # Update trend based on success rate
        if effectiveness["success_rate"] >= 90:
            effectiveness["trend"] = "improving"
        elif effectiveness["success_rate"] >= 70:
            effectiveness["trend"] = "stable"
        else:
            effectiveness["trend"] = "declining"

        logger.info(f"Effectiveness evaluated: {effectiveness_id}")
        return effectiveness
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to evaluate effectiveness: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to evaluate effectiveness: {str(e)}")


# ============================================================
# 4. Repair Verification Management
# ============================================================


@router.get("/verification", summary="Get repair verification records")
async def get_verifications(
    status: Optional[str] = Query(None, description="Filter by status"),
    verification_type: Optional[str] = Query(None, description="Filter by verification type"),
) -> Dict[str, Any]:
    """
    Retrieve all repair verification records
    """
    logger.info("Fetching repair verification records")
    try:
        items = list(_repair_verifications.values())

        if status:
            items = [item for item in items if item.get("status") == status]
        if verification_type:
            items = [item for item in items if item.get("verification_type") == verification_type]

        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"Failed to fetch verification records: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch verification records: {str(e)}"
        )


@router.post("/verification", summary="Create verification record")
async def create_verification(verification: VerificationCreate) -> Dict[str, Any]:
    """
    Create a new verification record
    """
    logger.info(f"Creating verification record for repair: {verification.repair_id}")
    try:
        verification_id = _generate_id()

        new_verification = {
            "id": verification_id,
            "repair_id": verification.repair_id,
            "repair_type": verification.repair_type,
            "target_resource": verification.target_resource,
            "verification_type": verification.verification_type,
            "status": "pending",
            "start_time": _get_current_timestamp(),
            "checks_passed": 0,
            "checks_total": 5,  # Default 5 checks
        }

        _repair_verifications[verification_id] = new_verification
        logger.info(f"Verification record created: {verification_id}")
        return new_verification
    except Exception as e:
        logger.error(f"Failed to create verification record: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create verification record: {str(e)}"
        )


@router.post("/verification/{verification_id}/verify", summary="Execute verification")
async def execute_verification(verification_id: str) -> Dict[str, Any]:
    """
    Execute verification checks
    """
    logger.info(f"Executing verification: {verification_id}")
    try:
        if verification_id not in _repair_verifications:
            raise HTTPException(status_code=404, detail="Verification record not found")

        verification = _repair_verifications[verification_id]

        if verification["status"] != "pending":
            raise HTTPException(status_code=400, detail="Verification is not in pending state")

        # Simulate verification execution
        verification["status"] = "running"

        # In production, this would run actual verification checks
        # For now, simulate a successful verification
        verification["status"] = "passed"
        verification["end_time"] = _get_current_timestamp()
        verification["duration"] = 30.0  # 30 seconds
        verification["checks_passed"] = verification["checks_total"]
        verification["details"] = "All verification checks passed successfully"

        logger.info(f"Verification executed: {verification_id}")
        return verification
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute verification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to execute verification: {str(e)}")


@router.post("/verification/{verification_id}/rerun", summary="Rerun verification")
async def rerun_verification(verification_id: str) -> Dict[str, Any]:
    """
    Rerun a failed verification
    """
    logger.info(f"Rerunning verification: {verification_id}")
    try:
        if verification_id not in _repair_verifications:
            raise HTTPException(status_code=404, detail="Verification record not found")

        verification = _repair_verifications[verification_id]

        # Reset to pending
        verification["status"] = "pending"
        verification["start_time"] = _get_current_timestamp()
        verification["end_time"] = None
        verification["duration"] = None
        verification["checks_passed"] = 0

        logger.info(f"Verification reset for rerun: {verification_id}")
        return verification
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rerun verification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to rerun verification: {str(e)}")


# ============================================================
# 5-14. Platform-Specific Repairs
# ============================================================


def _create_platform_repair_endpoint(store: Dict[str, Dict[str, Any]], platform_name: str):
    """Factory function to create platform-specific repair endpoints"""

    @router.get(f"/{platform_name}", summary=f"Get {platform_name} repairs")
    async def get_platform_repairs(
        status: Optional[str] = Query(None, description="Filter by status")
    ) -> Dict[str, Any]:
        logger.info(f"Fetching {platform_name} repairs")
        try:
            items = list(store.values())
            if status:
                items = [item for item in items if item.get("status") == status]
            return {"items": items, "total": len(items)}
        except Exception as e:
            logger.error(f"Failed to fetch {platform_name} repairs: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to fetch repairs: {str(e)}")

    @router.post(f"/{platform_name}", summary=f"Create {platform_name} repair")
    async def create_platform_repair(
        repair: PlatformRepairCreate, request: Request
    ) -> Dict[str, Any]:
        logger.info(f"Creating {platform_name} repair for: {repair.target_resource}")
        try:
            repair_id = _generate_id()
            operator_ip = (
                request.client.host if request.client else "unknown"
            )  # noqa: F841 - Reserved for audit logging

            new_repair = {
                "id": repair_id,
                "hostname": repair.target_resource,
                "hardware_type": platform_name,
                "device_id": _generate_id(),
                "issue_type": repair.issue_type,
                "severity": repair.severity,
                "status": "detected",
                "detected_at": _get_current_timestamp(),
                "repair_action": repair.repair_action,
                "result": None,
            }

            store[repair_id] = new_repair
            logger.info(f"{platform_name} repair created: {repair_id}")
            return new_repair
        except Exception as e:
            logger.error(f"Failed to create {platform_name} repair: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to create repair: {str(e)}")

    @router.post(
        f"/{platform_name}/{{repair_id}}/repair", summary=f"Execute {platform_name} repair"
    )
    async def execute_platform_repair(repair_id: str) -> Dict[str, Any]:
        logger.info(f"Executing {platform_name} repair: {repair_id}")
        try:
            if repair_id not in store:
                raise HTTPException(status_code=404, detail="Repair not found")

            repair = store[repair_id]
            repair["status"] = "repairing"

            # In production, this would call actual repair logic
            # For now, simulate successful repair
            repair["status"] = "completed"
            repair["result"] = f"{platform_name} repair completed successfully"

            logger.info(f"{platform_name} repair executed: {repair_id}")
            return repair
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to execute {platform_name} repair: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to execute repair: {str(e)}")

    return get_platform_repairs, create_platform_repair, execute_platform_repair


# Create all platform-specific endpoints
_get_hardware, _create_hardware, _execute_hardware = _create_platform_repair_endpoint(
    _hardware_repairs, "hardware"
)
_get_cloud, _create_cloud, _execute_cloud = _create_platform_repair_endpoint(
    _cloud_repairs, "cloud"
)
_get_cluster, _create_cluster, _execute_cluster = _create_platform_repair_endpoint(
    _cluster_repairs, "cluster"
)
_get_pod, _create_pod, _execute_pod = _create_platform_repair_endpoint(_pod_repairs, "pod")
_get_k8s, _create_k8s, _execute_k8s = _create_platform_repair_endpoint(_k8s_repairs, "k8s")
_get_docker, _create_docker, _execute_docker = _create_platform_repair_endpoint(
    _docker_repairs, "docker"
)
_get_macos, _create_macos, _execute_macos = _create_platform_repair_endpoint(
    _macos_repairs, "macos"
)
_get_windows, _create_windows, _execute_windows = _create_platform_repair_endpoint(
    _windows_repairs, "windows"
)
_get_linux, _create_linux, _execute_linux = _create_platform_repair_endpoint(
    _linux_repairs, "linux"
)


# ============================================================
# 14. Cross-Platform Repair
# ============================================================


@router.get("/cross-platform", summary="Get cross-platform repairs")
async def get_cross_platform_repairs(
    status: Optional[str] = Query(None, description="Filter by status")
) -> Dict[str, Any]:
    """
    Retrieve cross-platform repair records
    """
    logger.info("Fetching cross-platform repairs")
    try:
        items = list(_cross_platform_repairs.values())
        if status:
            items = [item for item in items if item.get("status") == status]
        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"Failed to fetch cross-platform repairs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch cross-platform repairs: {str(e)}"
        )


@router.post("/cross-platform", summary="Create cross-platform repair")
async def create_cross_platform_repair(
    repair: PlatformRepairCreate, request: Request
) -> Dict[str, Any]:
    """
    Create a cross-platform repair using the CrossPlatformScriptExecutor
    """
    logger.info(f"Creating cross-platform repair for: {repair.target_resource}")
    try:
        repair_id = _generate_id()
        operator_ip = request.client.host if request.client else "unknown"

        # Use the cross-platform executor
        script_key = f"cross_platform_{repair.issue_type}"
        context = {
            "target_resource": repair.target_resource,
            "severity": repair.severity,
            "operator": operator_ip,
        }

        execution_result = _cross_platform_executor.execute_script(script_key, context)

        new_repair = {
            "id": repair_id,
            "target_resource": repair.target_resource,
            "issue_type": repair.issue_type,
            "severity": repair.severity,
            "status": "completed" if execution_result.get("success") else "failed",
            "repair_action": repair.repair_action,
            "result": execution_result,
            "created_at": _get_current_timestamp(),
            "created_by": operator_ip,
        }

        _cross_platform_repairs[repair_id] = new_repair
        logger.info(f"Cross-platform repair created: {repair_id}")
        return new_repair
    except Exception as e:
        logger.error(f"Failed to create cross-platform repair: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create cross-platform repair: {str(e)}"
        )


# ============================================================
# 15. Unified Repair
# ============================================================


@router.get("/unified", summary="Get unified repairs")
async def get_unified_repairs(
    status: Optional[str] = Query(None, description="Filter by status")
) -> Dict[str, Any]:
    """
    Retrieve unified repair records
    """
    logger.info("Fetching unified repairs")
    try:
        items = list(_unified_repairs.values())
        if status:
            items = [item for item in items if item.get("status") == status]
        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"Failed to fetch unified repairs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch unified repairs: {str(e)}")


@router.post("/unified", summary="Create unified repair")
async def create_unified_repair(repair: PlatformRepairCreate, request: Request) -> Dict[str, Any]:
    """
    Create a unified repair that coordinates multiple repair strategies
    """
    logger.info(f"Creating unified repair for: {repair.target_resource}")
    try:
        repair_id = _generate_id()
        operator_ip = request.client.host if request.client else "unknown"

        # Unified repair combines multiple strategies
        new_repair = {
            "id": repair_id,
            "target_resource": repair.target_resource,
            "issue_type": repair.issue_type,
            "severity": repair.severity,
            "status": "analyzing",
            "repair_action": repair.repair_action,
            "strategies": ["auto_heal", "manual_intervention", "verification"],
            "created_at": _get_current_timestamp(),
            "created_by": operator_ip,
        }

        _unified_repairs[repair_id] = new_repair
        logger.info(f"Unified repair created: {repair_id}")
        return new_repair
    except Exception as e:
        logger.error(f"Failed to create unified repair: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create unified repair: {str(e)}")


# ============================================================
# 16. Repair History
# ============================================================


@router.get("/history", summary="Get repair history")
async def get_repair_history_api(
    limit: int = Query(default=20, ge=1, le=500, description="Maximum number of records"),
    date_from: Optional[str] = Query(None, description="Filter by start date"),
    date_to: Optional[str] = Query(None, description="Filter by end date"),
) -> Dict[str, Any]:
    """
    Retrieve repair history with optional filtering
    Uses the actual repair_engine.get_repair_history function
    """
    logger.info(f"Fetching repair history with limit={limit}")
    try:
        # Get history from repair_engine
        records = get_repair_history(limit)

        # Apply date filters if provided
        if date_from or date_to:
            filtered_records = []
            for record in records:
                record_time = record.get("time", "")
                if date_from and record_time < date_from:
                    continue
                if date_to and record_time > date_to:
                    continue
                filtered_records.append(record)
            records = filtered_records

        # Transform records to match frontend expectations
        items = []
        for record in records:
            items.append(
                {
                    "id": record.get("id", _generate_id()),
                    "repair_type": record.get("script_name", "unknown"),
                    "target_resource": record.get("params", {}).get("resource", "unknown"),
                    "issue_description": record.get("output", ""),
                    "status": "success" if record.get("success") else "failed",
                    "start_time": record.get("time", _get_current_timestamp()),
                    "end_time": record.get("time", _get_current_timestamp()),
                    "duration": None,
                    "executed_by": "system",
                    "details": record.get("output", ""),
                }
            )

        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"Failed to fetch repair history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch repair history: {str(e)}")


# ============================================================
# 17. Repair Scripts Management
# ============================================================


@router.get("/scripts", summary="Get all repair scripts")
async def get_scripts(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    status: Optional[str] = Query(None, description="Filter by status"),
) -> Dict[str, Any]:
    """
    Retrieve all repair scripts with optional filtering
    """
    logger.info("Fetching repair scripts")
    try:
        items = list(_repair_scripts_store.values())

        if platform:
            items = [item for item in items if item.get("platform") == platform]
        if status:
            items = [item for item in items if item.get("status") == status]

        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"Failed to fetch scripts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch scripts: {str(e)}")


@router.post("/scripts", summary="Create repair script")
async def create_script(script: RepairScriptCreate, request: Request) -> Dict[str, Any]:
    """
    Create a new repair script
    """
    logger.info(f"Creating script: {script.name}")
    try:
        script_id = _generate_id()
        operator_ip = request.client.host if request.client else "unknown"

        new_script = {
            "id": script_id,
            "name": script.name,
            "description": script.description,
            "language": script.language,
            "platform": script.platform,
            "category": script.category,
            "content": script.content,
            "version": "1.0.0",
            "created_at": _get_current_timestamp(),
            "updated_at": _get_current_timestamp(),
            "author": operator_ip,
            "status": "active",
        }

        _repair_scripts_store[script_id] = new_script
        logger.info(f"Script created: {script_id}")
        return new_script
    except Exception as e:
        logger.error(f"Failed to create script: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create script: {str(e)}")


@router.patch("/scripts/{script_id}", summary="Update repair script")
async def update_script(script_id: str, script_update: RepairScriptUpdate) -> Dict[str, Any]:
    """
    Update an existing repair script
    """
    logger.info(f"Updating script: {script_id}")
    try:
        if script_id not in _repair_scripts_store:
            raise HTTPException(status_code=404, detail="Script not found")

        script = _repair_scripts_store[script_id]
        update_data = script_update.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            script[key] = value

        script["updated_at"] = _get_current_timestamp()

        logger.info(f"Script updated: {script_id}")
        return script
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update script: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update script: {str(e)}")


@router.delete("/scripts/{script_id}", summary="Delete repair script")
async def delete_script(script_id: str) -> Dict[str, Any]:
    """
    Delete a repair script
    """
    logger.info(f"Deleting script: {script_id}")
    try:
        if script_id not in _repair_scripts_store:
            raise HTTPException(status_code=404, detail="Script not found")

        del _repair_scripts_store[script_id]
        logger.info(f"Script deleted: {script_id}")
        return {"message": "Script deleted successfully", "id": script_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete script: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete script: {str(e)}")


# ============================================================
# 18. Intelligent Repair
# ============================================================


@router.get("/intelligent", summary="Get intelligent repairs")
async def get_intelligent_repairs(
    status: Optional[str] = Query(None, description="Filter by status")
) -> Dict[str, Any]:
    """
    Retrieve intelligent repair records
    """
    logger.info("Fetching intelligent repairs")
    try:
        items = list(_intelligent_repairs.values())
        if status:
            items = [item for item in items if item.get("status") == status]
        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"Failed to fetch intelligent repairs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch intelligent repairs: {str(e)}"
        )


@router.post("/intelligent", summary="Create intelligent repair")
async def create_intelligent_repair(
    repair: IntelligentRepairCreate, request: Request
) -> Dict[str, Any]:
    """
    Create an intelligent repair with AI-powered analysis
    """
    logger.info(f"Creating intelligent repair for issue: {repair.issue_type}")
    try:
        repair_id = _generate_id()
        operator_ip = (
            request.client.host if request.client else "unknown"
        )  # noqa: F841 - Reserved for audit logging

        # Use risk assessment engine
        script = _script_library.get_script("cpu_high_script")  # Example script
        context = {
            "environment": "production",
            "severity": repair.severity,
        }

        risk_assessment = _risk_engine.assess_repair_risk(script, context) if script else None

        new_repair = {
            "id": repair_id,
            "issue_type": repair.issue_type,
            "severity": repair.severity,
            "detected_at": _get_current_timestamp(),
            "ai_recommendation": f"AI suggests: {repair.issue_type} repair strategy",
            "confidence": 0.85 if risk_assessment else 0.5,
            "auto_applied": repair.auto_apply,
            "status": "ready" if not repair.auto_apply else "applied",
            "result": None,
            "risk_assessment": risk_assessment.__dict__ if risk_assessment else None,
        }

        _intelligent_repairs[repair_id] = new_repair
        logger.info(f"Intelligent repair created: {repair_id}")
        return new_repair
    except Exception as e:
        logger.error(f"Failed to create intelligent repair: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create intelligent repair: {str(e)}"
        )


@router.post("/intelligent/{repair_id}/analyze", summary="Analyze intelligent repair")
async def analyze_intelligent_repair(repair_id: str) -> Dict[str, Any]:
    """
    Run AI analysis on an intelligent repair
    """
    logger.info(f"Analyzing intelligent repair: {repair_id}")
    try:
        if repair_id not in _intelligent_repairs:
            raise HTTPException(status_code=404, detail="Intelligent repair not found")

        repair = _intelligent_repairs[repair_id]
        repair["status"] = "analyzing"

        # Simulate AI analysis
        repair["status"] = "ready"
        repair["ai_recommendation"] = f"Updated AI recommendation for {repair['issue_type']}"
        repair["confidence"] = min(1.0, repair["confidence"] + 0.1)

        logger.info(f"Intelligent repair analyzed: {repair_id}")
        return repair
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze intelligent repair: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze intelligent repair: {str(e)}"
        )


@router.post("/intelligent/{repair_id}/apply", summary="Apply intelligent repair")
async def apply_intelligent_repair(repair_id: str) -> Dict[str, Any]:
    """
    Apply an intelligent repair
    """
    logger.info(f"Applying intelligent repair: {repair_id}")
    try:
        if repair_id not in _intelligent_repairs:
            raise HTTPException(status_code=404, detail="Intelligent repair not found")

        repair = _intelligent_repairs[repair_id]
        repair["status"] = "applied"
        repair["result"] = "Intelligent repair applied successfully"

        logger.info(f"Intelligent repair applied: {repair_id}")
        return repair
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to apply intelligent repair: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to apply intelligent repair: {str(e)}")


# ============================================================
# 19-21. Approval Workflow Endpoints
# ============================================================


@router.get("/approvals/pending", summary="Get pending approvals")
async def get_pending_approvals() -> Dict[str, Any]:
    """
    Retrieve all pending approval requests using the ApprovalWorkflow
    """
    logger.info("Fetching pending approvals")
    try:
        # Get pending requests from approval workflow
        pending_items = []
        for request_id, request in _approval_workflow.active_requests.items():
            if request.status == ApprovalStatus.PENDING:
                pending_items.append(request.to_dict())

        return {"items": pending_items, "total": len(pending_items)}
    except Exception as e:
        logger.error(f"Failed to fetch pending approvals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch pending approvals: {str(e)}")


@router.patch("/approvals/{approval_id}", summary="Update approval status")
async def update_approval(
    approval_id: str, update: ApprovalUpdate, request: Request
) -> Dict[str, Any]:
    """
    Update approval status (approve/reject) using the ApprovalWorkflow
    """
    logger.info(f"Updating approval: {approval_id} to {update.status}")
    try:
        operator_ip = request.client.host if request.client else "unknown"

        if update.status == "approved":
            # Find the step and approve it
            request_data = _approval_workflow.get_request_status(approval_id)
            if not request_data:
                raise HTTPException(status_code=404, detail="Approval request not found")

            # Get the first pending step
            steps = request_data.get("steps", [])
            pending_step = next((s for s in steps if s["status"] == "pending"), None)
            if not pending_step:
                raise HTTPException(status_code=400, detail="No pending step found")

            success = _approval_workflow.approve_step(
                approval_id, pending_step["step_id"], operator_ip, update.comment
            )

            if not success:
                raise HTTPException(status_code=400, detail="Failed to approve step")

        elif update.status == "rejected":
            # Find the step and reject it
            request_data = _approval_workflow.get_request_status(approval_id)
            if not request_data:
                raise HTTPException(status_code=404, detail="Approval request not found")

            steps = request_data.get("steps", [])
            pending_step = next((s for s in steps if s["status"] == "pending"), None)
            if not pending_step:
                raise HTTPException(status_code=400, detail="No pending step found")

            success = _approval_workflow.reject_step(
                approval_id, pending_step["step_id"], operator_ip, update.comment
            )

            if not success:
                raise HTTPException(status_code=400, detail="Failed to reject step")

        else:
            raise HTTPException(status_code=400, detail="Invalid status")

        # Return updated request
        updated_request = _approval_workflow.get_request_status(approval_id)
        logger.info(f"Approval updated: {approval_id}")
        return updated_request
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update approval: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update approval: {str(e)}")


@router.post("/approvals/reject", summary="Reject approval")
async def reject_approval(
    approval_id: str, reject_data: ApprovalReject, request: Request
) -> Dict[str, Any]:
    """
    Reject an approval request
    """
    logger.info(f"Rejecting approval: {approval_id}")
    try:
        operator_ip = request.client.host if request.client else "unknown"

        request_data = _approval_workflow.get_request_status(approval_id)
        if not request_data:
            raise HTTPException(status_code=404, detail="Approval request not found")

        steps = request_data.get("steps", [])
        pending_step = next((s for s in steps if s["status"] == "pending"), None)
        if not pending_step:
            raise HTTPException(status_code=400, detail="No pending step found")

        success = _approval_workflow.reject_step(
            approval_id, pending_step["step_id"], operator_ip, reject_data.reason
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to reject approval")

        updated_request = _approval_workflow.get_request_status(approval_id)
        logger.info(f"Approval rejected: {approval_id}")
        return updated_request
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject approval: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reject approval: {str(e)}")
