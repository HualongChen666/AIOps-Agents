# -*- coding: utf-8 -*-
"""
Advanced Change Management API Router
======================================

Provides comprehensive change management endpoints including requests,
approvals, schedules, impact analysis, and rollback plans.

Endpoints:
- GET/POST   /api/v1/change/requests
- GET/PATCH/DELETE /api/v1/change/requests/{id}
- GET/POST   /api/v1/change/approvals
- GET/POST   /api/v1/change/schedules
- POST       /api/v1/change/impact-analysis
- GET/POST   /api/v1/change/rollback-plans
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from core.auth_db import User
from core.auth_service import require_roles
from core.change_management_engine import (
    ChangeManagementError,
    ChangeRequest,
    RiskLevel,
    approve_request,
    create_request,
    get_request,
    implement_request,
    list_requests,
    reject_request,
    rollback_request,
    submit_request,
)
from core.command_guard import record_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/change", tags=["change-advanced"])


# ============================================================================
# Enums and Models
# ============================================================================

class ChangeStatus(str, Enum):
    """Change request status."""
    DRAFT = "draft"
    PENDING = "pending"
    REVIEW = "review"
    APPROVED = "approved"
    IMPLEMENTED = "implemented"
    ROLLED_BACK = "rolled_back"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApprovalStatus(str, Enum):
    """Approval status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONDITIONAL = "conditional"


class ScheduleStatus(str, Enum):
    """Schedule status."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"


class ImpactLevel(str, Enum):
    """Impact level."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# Pydantic Models
# ============================================================================

class ChangeRequestCreate(BaseModel):
    """Model for creating a change request."""
    title: str = Field(..., min_length=1, max_length=255, description="Change title")
    description: str = Field(default="", description="Detailed description")
    requester: str = Field(..., description="Requester name")
    approver: str = Field(default="", description="Approver name")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Risk level")
    schedule: str = Field(default="", description="Scheduled execution time")
    affected_services: List[str] = Field(default_factory=list, description="Affected services")
    implementation_plan: str = Field(default="", description="Implementation plan")
    rollback_plan: str = Field(default="", description="Rollback plan")
    priority: str = Field(default="medium", description="Priority (low/medium/high/critical)")
    estimated_duration: int = Field(default=60, description="Estimated duration in minutes")
    change_type: str = Field(default="standard", description="Change type (standard/emergency/routine)")
    test_plan: str = Field(default="", description="Test plan")
    validation_criteria: List[str] = Field(default_factory=list, description="Validation criteria")
    notification_recipients: List[str] = Field(default_factory=list, description="Notification recipients")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ChangeRequestUpdate(BaseModel):
    """Model for updating a change request."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    approver: Optional[str] = None
    risk_level: Optional[RiskLevel] = None
    schedule: Optional[str] = None
    affected_services: Optional[List[str]] = None
    implementation_plan: Optional[str] = None
    rollback_plan: Optional[str] = None
    priority: Optional[str] = None
    estimated_duration: Optional[int] = None
    change_type: Optional[str] = None
    test_plan: Optional[str] = None
    validation_criteria: Optional[List[str]] = None
    notification_recipients: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class ApprovalRequest(BaseModel):
    """Model for approval request."""
    change_request_id: str = Field(..., description="Change request ID")
    approver: str = Field(..., description="Approver name")
    decision: ApprovalStatus = Field(..., description="Approval decision")
    comments: str = Field(default="", description="Approval comments")
    conditions: Optional[List[str]] = Field(default_factory=list, description="Conditions for conditional approval")


class ApprovalResponse(BaseModel):
    """Model for approval response."""
    id: str = Field(..., description="Approval ID")
    change_request_id: str = Field(..., description="Change request ID")
    approver: str = Field(..., description="Approver name")
    decision: ApprovalStatus = Field(..., description="Approval decision")
    comments: str = Field(default="", description="Approval comments")
    conditions: List[str] = Field(default_factory=list, description="Conditions")
    approved_at: datetime = Field(default_factory=datetime.utcnow)
    valid_until: Optional[datetime] = Field(None, description="Approval validity period")


class ScheduleRequest(BaseModel):
    """Model for schedule request."""
    change_request_id: str = Field(..., description="Change request ID")
    scheduled_start: datetime = Field(..., description="Scheduled start time")
    scheduled_end: datetime = Field(..., description="Scheduled end time")
    maintenance_window: str = Field(default="", description="Maintenance window identifier")
    timezone: str = Field(default="UTC", description="Timezone")
    assigned_team: List[str] = Field(default_factory=list, description="Assigned team members")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisites")
    dependencies: List[str] = Field(default_factory=list, description="Dependent change IDs")


class ScheduleResponse(BaseModel):
    """Model for schedule response."""
    id: str = Field(..., description="Schedule ID")
    change_request_id: str = Field(..., description="Change request ID")
    scheduled_start: datetime = Field(..., description="Scheduled start time")
    scheduled_end: datetime = Field(..., description="Scheduled end time")
    maintenance_window: str = Field(default="", description="Maintenance window")
    timezone: str = Field(default="UTC", description="Timezone")
    status: ScheduleStatus = Field(default=ScheduleStatus.SCHEDULED, description="Schedule status")
    assigned_team: List[str] = Field(default_factory=list, description="Assigned team")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisites")
    dependencies: List[str] = Field(default_factory=list, description="Dependencies")
    actual_start: Optional[datetime] = Field(None, description="Actual start time")
    actual_end: Optional[datetime] = Field(None, description="Actual end time")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ImpactAnalysisRequest(BaseModel):
    """Model for impact analysis request."""
    change_request_id: str = Field(..., description="Change request ID")
    affected_services: List[str] = Field(..., description="Services to analyze")
    change_description: str = Field(..., description="Description of the change")
    risk_level: RiskLevel = Field(..., description="Risk level")
    analysis_depth: str = Field(default="standard", description="Analysis depth (quick/standard/deep)")


class ImpactAnalysisResponse(BaseModel):
    """Model for impact analysis response."""
    change_request_id: str = Field(..., description="Change request ID")
    overall_impact: ImpactLevel = Field(..., description="Overall impact level")
    service_impacts: List[Dict[str, Any]] = Field(default_factory=list, description="Per-service impact")
    downtime_estimate: Dict[str, Any] = Field(..., description="Downtime estimates")
    risk_factors: List[Dict[str, Any]] = Field(default_factory=list, description="Identified risk factors")
    mitigation_strategies: List[str] = Field(default_factory=list, description="Mitigation strategies")
    dependencies_affected: List[str] = Field(default_factory=list, description="Affected dependencies")
    rollback_feasibility: str = Field(..., description="Rollback feasibility assessment")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class RollbackPlanRequest(BaseModel):
    """Model for rollback plan request."""
    change_request_id: str = Field(..., description="Change request ID")
    rollback_steps: List[str] = Field(..., description="Rollback steps")
    estimated_rollback_time: int = Field(..., description="Estimated rollback time in minutes")
    data_consistency_checks: List[str] = Field(default_factory=list, description="Data consistency checks")
    rollback_triggers: List[str] = Field(default_factory=list, description="Triggers for rollback")
    validation_after_rollback: List[str] = Field(default_factory=list, description="Validation steps after rollback")


class RollbackPlanResponse(BaseModel):
    """Model for rollback plan response."""
    id: str = Field(..., description="Rollback plan ID")
    change_request_id: str = Field(..., description="Change request ID")
    rollback_steps: List[str] = Field(..., description="Rollback steps")
    estimated_rollback_time: int = Field(..., description="Estimated rollback time (minutes)")
    data_consistency_checks: List[str] = Field(default_factory=list, description="Data consistency checks")
    rollback_triggers: List[str] = Field(default_factory=list, description="Rollback triggers")
    validation_after_rollback: List[str] = Field(default_factory=list, description="Validation steps")
    complexity: str = Field(..., description="Rollback complexity (low/medium/high)")
    success_probability: float = Field(..., ge=0, le=1, description="Success probability")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", description="Creator")


# ============================================================================
# In-Memory Data Storage
# ============================================================================

_approvals: Dict[str, ApprovalResponse] = {}
_schedules: Dict[str, ScheduleResponse] = {}
_rollback_plans: Dict[str, RollbackPlanResponse] = {}


def _generate_approval_id() -> str:
    """Generate a unique approval ID."""
    import uuid
    return f"APR-{uuid.uuid4().hex[:8].upper()}"


def _generate_schedule_id() -> str:
    """Generate a unique schedule ID."""
    import uuid
    return f"SCH-{uuid.uuid4().hex[:8].upper()}"


def _generate_rollback_plan_id() -> str:
    """Generate a unique rollback plan ID."""
    import uuid
    return f"RBP-{uuid.uuid4().hex[:8].upper()}"


# ============================================================================
# API Endpoints - Change Requests
# ============================================================================

@router.get("/requests", response_model=List[ChangeRequest])
async def list_change_requests(
    status: Optional[str] = Query(None, description="Filter by status"),
    risk_level: Optional[RiskLevel] = Query(None, description="Filter by risk level"),
    requester: Optional[str] = Query(None, description="Filter by requester"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    List all change requests with optional filtering.
    
    Returns change requests with filtering by status, risk level,
    requester, and priority.
    """
    try:
        tenant_id = str(current_user.tenant_id) if hasattr(current_user, 'tenant_id') else "default"
        requests = await list_requests(tenant_id=tenant_id)
        
        if status:
            requests = [r for r in requests if r.status.value == status]
        if risk_level:
            requests = [r for r in requests if r.risk_level == risk_level]
        if requester:
            requests = [r for r in requests if r.requester == requester]
        
        # Filter by priority from metadata
        if priority:
            requests = [r for r in requests if r.audit_log and any(
                "priority" in str(entry.message).lower() and priority in str(entry.message).lower()
                for entry in r.audit_log
            )]
        
        return sorted(requests, key=lambda r: r.id, reverse=True)
    except Exception as e:
        logger.error(f"Error listing change requests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list change requests: {str(e)}")


@router.post("/requests", response_model=ChangeRequest, status_code=status.HTTP_201_CREATED)
async def create_change_request(
    request: ChangeRequestCreate,
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Create a new change request.
    
    Creates a comprehensive change request with all required metadata
    including implementation plan, rollback plan, and validation criteria.
    """
    try:
        tenant_id = str(current_user.tenant_id) if hasattr(current_user, 'tenant_id') else "default"
        
        # Build request data
        data = {
            "title": request.title,
            "description": request.description,
            "requester": request.requester,
            "approver": request.approver,
            "risk_level": request.risk_level,
            "schedule": request.schedule,
            "affected_services": request.affected_services,
            "implementation_plan": request.implementation_plan,
            "rollback_plan": request.rollback_plan,
        }
        
        # Add metadata for extended fields
        metadata = {
            "priority": request.priority,
            "estimated_duration": request.estimated_duration,
            "change_type": request.change_type,
            "test_plan": request.test_plan,
            "validation_criteria": request.validation_criteria,
            "notification_recipients": request.notification_recipients,
        }
        if request.metadata:
            metadata.update(request.metadata)
        
        # Create the request
        change_request = await create_request(data, tenant_id=tenant_id)
        
        # Add metadata to audit log
        from core.change_management_engine import AuditEntry
        change_request.audit_log.append(
            AuditEntry(
                actor=request.requester,
                action="metadata_added",
                message=f"Extended metadata: {metadata}",
            )
        )
        
        logger.info(f"Created change request: {change_request.id}")
        
        return change_request
    except ChangeManagementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating change request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create change request: {str(e)}")


@router.get("/requests/{request_id}", response_model=ChangeRequest)
async def get_change_request(
    request_id: str,
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """Get a specific change request by ID."""
    try:
        tenant_id = str(current_user.tenant_id) if hasattr(current_user, 'tenant_id') else "default"
        return await get_request(request_id, tenant_id=tenant_id)
    except (ChangeManagementError, PermissionError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting change request {request_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get change request: {str(e)}")


@router.patch("/requests/{request_id}", response_model=ChangeRequest)
async def update_change_request(
    request_id: str,
    update: ChangeRequestUpdate,
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Update a change request.
    
    Updates specific fields of a change request while maintaining
    audit trail of changes.
    """
    try:
        tenant_id = str(current_user.tenant_id) if hasattr(current_user, 'tenant_id') else "default"
        change_request = await get_request(request_id, tenant_id=tenant_id)
        
        # Update basic fields
        if update.title is not None:
            change_request.title = update.title
        if update.description is not None:
            change_request.description = update.description
        if update.approver is not None:
            change_request.approver = update.approver
        if update.risk_level is not None:
            change_request.risk_level = update.risk_level
        if update.schedule is not None:
            change_request.schedule = update.schedule
        if update.affected_services is not None:
            change_request.affected_services = update.affected_services
        if update.implementation_plan is not None:
            change_request.implementation_plan = update.implementation_plan
        if update.rollback_plan is not None:
            change_request.rollback_plan = update.rollback_plan
        
        # Add metadata update to audit log
        from core.change_management_engine import AuditEntry
        metadata_updates = {}
        if update.priority is not None:
            metadata_updates["priority"] = update.priority
        if update.estimated_duration is not None:
            metadata_updates["estimated_duration"] = update.estimated_duration
        if update.change_type is not None:
            metadata_updates["change_type"] = update.change_type
        if update.test_plan is not None:
            metadata_updates["test_plan"] = update.test_plan
        if update.validation_criteria is not None:
            metadata_updates["validation_criteria"] = update.validation_criteria
        if update.notification_recipients is not None:
            metadata_updates["notification_recipients"] = update.notification_recipients
        
        if metadata_updates:
            change_request.audit_log.append(
                AuditEntry(
                    actor=current_user.username if hasattr(current_user, 'username') else "system",
                    action="updated",
                    message=f"Updated metadata: {metadata_updates}",
                )
            )
        
        # Persist changes
        from core.change_management_engine import _persist
        await _persist()
        
        logger.info(f"Updated change request: {request_id}")
        
        return change_request
    except (ChangeManagementError, PermissionError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating change request {request_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update change request: {str(e)}")


@router.delete("/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_change_request(
    request_id: str,
    current_user=Depends(require_roles("admin")),
):
    """
    Delete a change request.
    
    Deletes a change request (only allowed for draft or rejected requests).
    """
    try:
        tenant_id = str(current_user.tenant_id) if hasattr(current_user, 'tenant_id') else "default"
        change_request = await get_request(request_id, tenant_id=tenant_id)
        
        # Only allow deletion of draft or rejected requests
        from core.change_management_engine import ChangeStatus
        if change_request.status not in [ChangeStatus.DRAFT, ChangeStatus.REJECTED]:
            raise HTTPException(
                status_code=400,
                detail="Can only delete draft or rejected change requests"
            )
        
        # Delete from storage
        from core.change_management_engine import _REQUESTS, _persist
        if request_id in _REQUESTS:
            del _REQUESTS[request_id]
            await _persist()
        
        logger.info(f"Deleted change request: {request_id}")
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting change request {request_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete change request: {str(e)}")


# ============================================================================
# API Endpoints - Approvals
# ============================================================================

@router.get("/approvals", response_model=List[ApprovalResponse])
async def list_approvals(
    change_request_id: Optional[str] = Query(None, description="Filter by change request ID"),
    decision: Optional[ApprovalStatus] = Query(None, description="Filter by decision"),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    List all approvals with optional filtering.
    
    Returns approval records showing who approved what and when.
    """
    try:
        approvals = list(_approvals.values())
        
        if change_request_id:
            approvals = [a for a in approvals if a.change_request_id == change_request_id]
        if decision:
            approvals = [a for a in approvals if a.decision == decision]
        
        return sorted(approvals, key=lambda a: a.approved_at, reverse=True)
    except Exception as e:
        logger.error(f"Error listing approvals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list approvals: {str(e)}")


@router.post("/approvals", response_model=ApprovalResponse, status_code=status.HTTP_201_CREATED)
async def create_approval(
    request: ApprovalRequest,
    current_user: User = Depends(require_roles("admin")),
):
    """
    Create an approval decision.
    
    Records an approval decision for a change request with optional
    conditions for conditional approvals.
    """
    try:
        tenant_id = str(current_user.tenant_id) if hasattr(current_user, 'tenant_id') else "default"
        
        # Verify change request exists
        change_request = await get_request(request.change_request_id, tenant_id=tenant_id)
        
        # Create approval record
        approval_id = _generate_approval_id()
        
        # Set validity period (30 days for standard approvals)
        valid_until = datetime.utcnow() + timedelta(days=30)
        
        approval = ApprovalResponse(
            id=approval_id,
            change_request_id=request.change_request_id,
            approver=request.approver,
            decision=request.decision,
            comments=request.comments,
            conditions=request.conditions,
            approved_at=datetime.utcnow(),
            valid_until=valid_until,
        )
        
        _approvals[approval_id] = approval
        
        # Update change request based on decision
        if request.decision == ApprovalStatus.APPROVED:
            await approve_request(request.change_request_id, tenant_id=tenant_id)
        elif request.decision == ApprovalStatus.REJECTED:
            await reject_request(request.change_request_id, tenant_id=tenant_id)
        
        # Record audit
        record_audit(
            host=request.change_request_id,
            command="CHANGE_APPROVAL",
            risk_level="high",
            executor=current_user.username,
            result=request.decision.value,
            user_id=str(current_user.id) if current_user.id else None,
            tenant_id=tenant_id,
        )
        
        logger.info(f"Created approval: {approval_id} for request {request.change_request_id}")
        
        return approval
    except (ChangeManagementError, PermissionError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating approval: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create approval: {str(e)}")


# ============================================================================
# API Endpoints - Schedules
# ============================================================================

@router.get("/schedules", response_model=List[ScheduleResponse])
async def list_schedules(
    change_request_id: Optional[str] = Query(None, description="Filter by change request ID"),
    status: Optional[ScheduleStatus] = Query(None, description="Filter by status"),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    List all change schedules with optional filtering.
    
    Returns schedule information for change requests including
    maintenance windows and assigned teams.
    """
    try:
        schedules = list(_schedules.values())
        
        if change_request_id:
            schedules = [s for s in schedules if s.change_request_id == change_request_id]
        if status:
            schedules = [s for s in schedules if s.status == status]
        
        return sorted(schedules, key=lambda s: s.scheduled_start, reverse=True)
    except Exception as e:
        logger.error(f"Error listing schedules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list schedules: {str(e)}")


@router.post("/schedules", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    request: ScheduleRequest,
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Create a change schedule.
    
    Schedules a change request for execution within a specific
    maintenance window with assigned team and dependencies.
    """
    try:
        tenant_id = str(current_user.tenant_id) if hasattr(current_user, 'tenant_id') else "default"
        
        # Verify change request exists
        change_request = await get_request(request.change_request_id, tenant_id=tenant_id)
        
        # Validate schedule times
        if request.scheduled_end <= request.scheduled_start:
            raise HTTPException(status_code=400, detail="End time must be after start time")
        
        # Create schedule record
        schedule_id = _generate_schedule_id()
        
        schedule = ScheduleResponse(
            id=schedule_id,
            change_request_id=request.change_request_id,
            scheduled_start=request.scheduled_start,
            scheduled_end=request.scheduled_end,
            maintenance_window=request.maintenance_window,
            timezone=request.timezone,
            status=ScheduleStatus.SCHEDULED,
            assigned_team=request.assigned_team,
            prerequisites=request.prerequisites,
            dependencies=request.dependencies,
        )
        
        _schedules[schedule_id] = schedule
        
        # Update change request schedule
        change_request.schedule = request.scheduled_start.isoformat()
        
        # Persist changes
        from core.change_management_engine import _persist
        await _persist()
        
        logger.info(f"Created schedule: {schedule_id} for request {request.change_request_id}")
        
        return schedule
    except (ChangeManagementError, PermissionError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")


@router.patch("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    status: Optional[ScheduleStatus] = None,
    actual_start: Optional[datetime] = None,
    actual_end: Optional[datetime] = None,
    current_user=Depends(require_roles("admin", "operator")),
):
    """Update a schedule (typically to mark as in progress or completed)."""
    try:
        if schedule_id not in _schedules:
            raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
        
        schedule = _schedules[schedule_id]
        
        if status is not None:
            schedule.status = status
        if actual_start is not None:
            schedule.actual_start = actual_start
        if actual_end is not None:
            schedule.actual_end = actual_end
        
        logger.info(f"Updated schedule: {schedule_id}")
        
        return schedule
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating schedule {schedule_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")


# ============================================================================
# API Endpoints - Impact Analysis
# ============================================================================

@router.post("/impact-analysis", response_model=ImpactAnalysisResponse)
async def perform_impact_analysis(
    request: ImpactAnalysisRequest,
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Perform impact analysis for a change.
    
    Analyzes the potential impact of a change on affected services,
    including downtime estimates, risk factors, and mitigation strategies.
    """
    try:
        tenant_id = str(current_user.tenant_id) if hasattr(current_user, 'tenant_id') else "default"
        
        # Verify change request exists
        change_request = await get_request(request.change_request_id, tenant_id=tenant_id)
        
        # Calculate overall impact based on risk level and affected services
        if request.risk_level == RiskLevel.HIGH:
            overall_impact = ImpactLevel.HIGH
        elif request.risk_level == RiskLevel.MEDIUM:
            overall_impact = ImpactLevel.MEDIUM
        else:
            overall_impact = ImpactLevel.LOW
        
        # Generate per-service impacts
        service_impacts = []
        for service in request.affected_services:
            service_impact = {
                "service": service,
                "impact_level": overall_impact.value,
                "estimated_downtime": 15 if overall_impact == ImpactLevel.LOW else 30 if overall_impact == ImpactLevel.MEDIUM else 60,
                "affected_users": "low" if overall_impact == ImpactLevel.LOW else "medium" if overall_impact == ImpactLevel.MEDIUM else "high",
                "business_criticality": "high" if "database" in service.lower() or "api" in service.lower() else "medium",
            }
            service_impacts.append(service_impact)
        
        # Calculate downtime estimates
        total_downtime = sum(s["estimated_downtime"] for s in service_impacts)
        downtime_estimate = {
            "total_estimated_minutes": total_downtime,
            "per_service_downtime": {s["service"]: s["estimated_downtime"] for s in service_impacts},
            "peak_impact_window": f"{total_downtime // 2} minutes around scheduled time",
        }
        
        # Identify risk factors
        risk_factors = [
            {
                "factor": "Service dependency",
                "severity": "medium" if len(request.affected_services) > 1 else "low",
                "description": f"Change affects {len(request.affected_services)} services",
            },
            {
                "factor": "Risk level",
                "severity": request.risk_level.value,
                "description": f"Change classified as {request.risk_level.value} risk",
            },
        ]
        
        # Generate mitigation strategies
        mitigation_strategies = [
            "Implement during low-traffic periods",
            "Prepare rollback plan before execution",
            "Monitor system metrics during and after change",
            "Have on-call team available during change window",
            "Test in staging environment first",
        ]
        
        # Identify affected dependencies
        dependencies_affected = []
        for service in request.affected_services:
            # Simulate dependency detection
            if "database" in service.lower():
                dependencies_affected.extend(["cache-service", "api-gateway"])
            elif "api" in service.lower():
                dependencies_affected.extend(["frontend", "mobile-app"])
        
        # Assess rollback feasibility
        if request.risk_level == RiskLevel.HIGH:
            rollback_feasibility = "Complex - requires careful coordination"
        elif request.risk_level == RiskLevel.MEDIUM:
            rollback_feasibility = "Moderate - standard rollback procedures apply"
        else:
            rollback_feasibility = "Simple - automated rollback available"
        
        # Generate recommendations
        recommendations = [
            "Schedule change during maintenance window",
            "Notify all stakeholders 24 hours in advance",
            "Ensure all team members are available",
            "Verify rollback plan is tested and documented",
            "Monitor key metrics during execution",
        ]
        
        analysis = ImpactAnalysisResponse(
            change_request_id=request.change_request_id,
            overall_impact=overall_impact,
            service_impacts=service_impacts,
            downtime_estimate=downtime_estimate,
            risk_factors=risk_factors,
            mitigation_strategies=mitigation_strategies,
            dependencies_affected=list(set(dependencies_affected)),
            rollback_feasibility=rollback_feasibility,
            recommendations=recommendations,
        )
        
        logger.info(f"Performed impact analysis for request {request.change_request_id}")
        
        return analysis
    except (ChangeManagementError, PermissionError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error performing impact analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to perform impact analysis: {str(e)}")


# ============================================================================
# API Endpoints - Rollback Plans
# ============================================================================

@router.get("/rollback-plans", response_model=List[RollbackPlanResponse])
async def list_rollback_plans(
    change_request_id: Optional[str] = Query(None, description="Filter by change request ID"),
    current_user=Depends(require_roles("admin", "operator", "business")),
):
    """
    List all rollback plans with optional filtering.
    
    Returns rollback plans for change requests including steps,
    triggers, and validation procedures.
    """
    try:
        plans = list(_rollback_plans.values())
        
        if change_request_id:
            plans = [p for p in plans if p.change_request_id == change_request_id]
        
        return sorted(plans, key=lambda p: p.created_at, reverse=True)
    except Exception as e:
        logger.error(f"Error listing rollback plans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list rollback plans: {str(e)}")


@router.post("/rollback-plans", response_model=RollbackPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_rollback_plan(
    request: RollbackPlanRequest,
    current_user=Depends(require_roles("admin", "operator")),
):
    """
    Create a rollback plan.
    
    Creates a detailed rollback plan with steps, triggers,
    and validation procedures for a change request.
    """
    try:
        tenant_id = str(current_user.tenant_id) if hasattr(current_user, 'tenant_id') else "default"
        
        # Verify change request exists
        change_request = await get_request(request.change_request_id, tenant_id=tenant_id)
        
        # Determine complexity based on number of steps
        num_steps = len(request.rollback_steps)
        if num_steps <= 3:
            complexity = "low"
            success_probability = 0.95
        elif num_steps <= 7:
            complexity = "medium"
            success_probability = 0.85
        else:
            complexity = "high"
            success_probability = 0.75
        
        # Create rollback plan record
        plan_id = _generate_rollback_plan_id()
        
        plan = RollbackPlanResponse(
            id=plan_id,
            change_request_id=request.change_request_id,
            rollback_steps=request.rollback_steps,
            estimated_rollback_time=request.estimated_rollback_time,
            data_consistency_checks=request.data_consistency_checks,
            rollback_triggers=request.rollback_triggers,
            validation_after_rollback=request.validation_after_rollback,
            complexity=complexity,
            success_probability=success_probability,
            created_by=current_user.username if hasattr(current_user, 'username') else "system",
        )
        
        _rollback_plans[plan_id] = plan
        
        # Update change request with rollback plan
        change_request.rollback_plan = "\n".join(request.rollback_steps)
        
        # Persist changes
        from core.change_management_engine import _persist
        await _persist()
        
        logger.info(f"Created rollback plan: {plan_id} for request {request.change_request_id}")
        
        return plan
    except (ChangeManagementError, PermissionError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating rollback plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create rollback plan: {str(e)}")
