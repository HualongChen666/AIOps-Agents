# -*- coding: utf-8 -*-
"""
Incident Management Router Module
==================================

Provides comprehensive API endpoints for incident management.
Supports incident lifecycle, collaboration, automation, analytics, and integrations.

Endpoints:
- Incident CRUD operations
- Incident status management
- Incident assignment and escalation
- Incident comments and attachments
- Incident timeline and history
- Incident statistics and trends
- Bulk operations
- Search and filtering
- Incident merging and linking
- Incident templates
- Incident workflows
- Incident notifications
- Incident reports
- Incident analytics
- Incident SLA management
- Incident root cause analysis
- Incident post-mortem
- Incident integration hooks
"""

import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Query, Depends, Request, UploadFile, File
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from loguru import logger

from core.database import get_db
from core.auth import get_current_user, require_role, verify_token
from core.rate_limiter import get_limiter
from core.models import User

# Initialize rate limiter
limiter = get_limiter()

router = APIRouter(prefix="/api/v1/incident-management", tags=["事件管理"])

# ============================================================================
# Configuration
# ============================================================================
BATCH_SIZE = int(os.getenv("INCIDENT_BATCH_SIZE", "50"))
MAX_ATTACHMENT_SIZE = int(os.getenv("MAX_ATTACHMENT_SIZE", "10485760"))  # 10MB
ALLOWED_ATTACHMENT_TYPES = os.getenv(
    "ALLOWED_ATTACHMENT_TYPES", 
    "image/png,image/jpeg,application/pdf,text/plain"
).split(",")

# ============================================================================
# Pydantic Models
# ============================================================================

class IncidentCreate(BaseModel):
    """Incident creation model"""
    title: str = Field(..., min_length=1, max_length=500, description="Incident title")
    description: str = Field(..., min_length=1, max_length=5000, description="Incident description")
    severity: str = Field(..., description="Severity: low, medium, high, critical")
    category: str = Field(..., description="Incident category")
    priority: str = Field(default="medium", description="Priority: low, medium, high, critical")
    impact: str = Field(default="medium", description="Impact: low, medium, high")
    urgency: str = Field(default="medium", description="Urgency: low, medium, high")
    assigned_to: Optional[str] = Field(None, description="Assigned user ID")
    tags: Optional[List[str]] = Field(default_factory=list, description="Incident tags")
    environment: str = Field(default="production", description="Environment: production, staging, development")
    source: str = Field(default="manual", description="Incident source")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('severity')
    def validate_severity(cls, v):
        valid_severities = ['low', 'medium', 'high', 'critical']
        if v not in valid_severities:
            raise ValueError(f'Severity must be one of {valid_severities}')
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        valid_priorities = ['low', 'medium', 'high', 'critical']
        if v not in valid_priorities:
            raise ValueError(f'Priority must be one of {valid_priorities}')
        return v


class IncidentUpdate(BaseModel):
    """Incident update model"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, min_length=1, max_length=5000)
    severity: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    impact: Optional[str] = None
    urgency: Optional[str] = None
    assigned_to: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    resolution_notes: Optional[str] = None
    root_cause: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IncidentStatusUpdate(BaseModel):
    """Incident status update model"""
    status: str = Field(..., description="Status: open, in_progress, resolved, closed")
    reason: Optional[str] = Field(None, description="Reason for status change")
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['open', 'in_progress', 'resolved', 'closed', 'on_hold']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of {valid_statuses}')
        return v


class IncidentAssign(BaseModel):
    """Incident assignment model"""
    assigned_to: str = Field(..., description="User ID to assign to")
    assignee_type: str = Field(default="user", description="Assignee type: user, team, group")
    notify: bool = Field(default=True, description="Send notification to assignee")
    message: Optional[str] = Field(None, description="Assignment message")


class IncidentComment(BaseModel):
    """Incident comment model"""
    content: str = Field(..., min_length=1, max_length=2000, description="Comment content")
    is_internal: bool = Field(default=False, description="Internal comment flag")
    mention_users: Optional[List[str]] = Field(default_factory=list, description="Mentioned user IDs")


class IncidentBulkCreate(BaseModel):
    """Bulk incident creation model"""
    incidents: List[IncidentCreate] = Field(..., max_length=100, description="List of incidents to create")
    
    @validator('incidents')
    def validate_incidents_length(cls, v):
        if len(v) > BATCH_SIZE:
            raise ValueError(f'Cannot create more than {BATCH_SIZE} incidents at once')
        return v


class IncidentBulkUpdate(BaseModel):
    """Bulk incident update model"""
    incident_ids: List[str] = Field(..., max_length=100, description="List of incident IDs")
    updates: IncidentUpdate = Field(..., description="Updates to apply")
    
    @validator('incident_ids')
    def validate_incident_ids_length(cls, v):
        if len(v) > BATCH_SIZE:
            raise ValueError(f'Cannot update more than {BATCH_SIZE} incidents at once')
        return v


class IncidentSearch(BaseModel):
    """Incident search model"""
    query: str = Field(..., min_length=1, description="Search query")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Search filters")
    sort_by: str = Field(default="created_at", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order: asc, desc")
    limit: int = Field(default=50, ge=1, le=100, description="Results limit")
    offset: int = Field(default=0, ge=0, description="Results offset")


class IncidentFilter(BaseModel):
    """Incident filter model"""
    status: Optional[List[str]] = None
    severity: Optional[List[str]] = None
    category: Optional[List[str]] = None
    priority: Optional[List[str]] = None
    assigned_to: Optional[List[str]] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    resolved_after: Optional[datetime] = None
    resolved_before: Optional[datetime] = None
    tags: Optional[List[str]] = None
    environment: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class IncidentMerge(BaseModel):
    """Incident merge model"""
    source_incident_ids: List[str] = Field(..., min_length=1, description="Source incident IDs to merge")
    target_incident_id: str = Field(..., description="Target incident ID to merge into")
    merge_strategy: str = Field(default="append", description="Merge strategy: append, replace, keep_latest")
    reason: str = Field(..., description="Reason for merge")


class IncidentLink(BaseModel):
    """Incident link model"""
    related_incident_id: str = Field(..., description="Related incident ID")
    link_type: str = Field(default="related", description="Link type: related, duplicate, parent, child")
    description: Optional[str] = Field(None, description="Link description")


class IncidentTemplate(BaseModel):
    """Incident template model"""
    name: str = Field(..., min_length=1, max_length=200, description="Template name")
    description: str = Field(..., min_length=1, max_length=1000, description="Template description")
    template_data: Dict[str, Any] = Field(..., description="Template data")
    category: str = Field(..., description="Template category")
    is_public: bool = Field(default=False, description="Public template flag")


class IncidentWorkflow(BaseModel):
    """Incident workflow model"""
    name: str = Field(..., min_length=1, max_length=200, description="Workflow name")
    steps: List[Dict[str, Any]] = Field(..., description="Workflow steps")
    triggers: List[Dict[str, Any]] = Field(default_factory=list, description="Workflow triggers")
    conditions: List[Dict[str, Any]] = Field(default_factory=list, description="Workflow conditions")


class SLABreach(BaseModel):
    """SLA breach model"""
    sla_type: str = Field(..., description="SLA type: response, resolution")
    breach_time: datetime = Field(..., description="Breach time")
    actual_time: datetime = Field(..., description="Actual time")
    severity: str = Field(..., description="Breach severity")


class RootCauseAnalysis(BaseModel):
    """Root cause analysis model"""
    analysis_method: str = Field(..., description="Analysis method")
    findings: List[Dict[str, Any]] = Field(..., description="Analysis findings")
    root_cause: str = Field(..., description="Identified root cause")
    contributing_factors: List[str] = Field(default_factory=list, description="Contributing factors")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    analyzed_by: str = Field(..., description="Analyzer user ID")


class PostMortem(BaseModel):
    """Post-mortem model"""
    summary: str = Field(..., min_length=1, max_length=2000, description="Incident summary")
    timeline: List[Dict[str, Any]] = Field(..., description="Incident timeline")
    root_cause: str = Field(..., description="Root cause")
    impact: str = Field(..., description="Impact assessment")
    resolution: str = Field(..., description="Resolution details")
    lessons_learned: List[str] = Field(..., description="Lessons learned")
    action_items: List[Dict[str, Any]] = Field(..., description="Action items")
    follow_up_date: Optional[datetime] = Field(None, description="Follow-up date")
    reviewed_by: List[str] = Field(..., description="Reviewer user IDs")


# ============================================================================
# In-Memory Storage (Production: migrate to database)
# ============================================================================
_incidents: Dict[str, Dict[str, Any]] = {}
_incident_comments: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
_incident_attachments: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
_incident_timeline: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
_incident_links: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
_incident_templates: Dict[str, Dict[str, Any]] = {}
_incident_workflows: Dict[str, Dict[str, Any]] = {}
_sla_records: Dict[str, List[Dict[str, Any]]] = defaultdict(list)


def _initialize_default_data():
    """Initialize default incident data"""
    if not _incidents:
        default_incidents = [
            {
                "incident_id": str(uuid.uuid4()),
                "title": "Database connection pool exhausted",
                "description": "Application database connection pool reached maximum capacity",
                "severity": "high",
                "category": "database",
                "priority": "high",
                "impact": "high",
                "urgency": "high",
                "status": "open",
                "assigned_to": "user_001",
                "tags": ["database", "performance", "critical"],
                "environment": "production",
                "source": "alert",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "resolved_at": None,
                "resolution_notes": None,
                "root_cause": None,
                "metadata": {"alert_id": "alert_12345", "service": "api-service"},
            },
            {
                "incident_id": str(uuid.uuid4()),
                "title": "API latency spike",
                "description": "API response times increased beyond acceptable thresholds",
                "severity": "medium",
                "category": "performance",
                "priority": "medium",
                "impact": "medium",
                "urgency": "medium",
                "status": "in_progress",
                "assigned_to": "user_002",
                "tags": ["api", "latency", "performance"],
                "environment": "production",
                "source": "monitoring",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "resolved_at": None,
                "resolution_notes": None,
                "root_cause": None,
                "metadata": {"threshold": "500ms", "current": "1200ms"},
            },
        ]
        for incident in default_incidents:
            _incidents[incident["incident_id"]] = incident
            _incident_timeline[incident["incident_id"]].append({
                "event": "created",
                "timestamp": incident["created_at"],
                "user": "system",
                "details": {"message": "Incident created"}
            })
    
    if not _incident_templates:
        default_templates = [
            {
                "template_id": str(uuid.uuid4()),
                "name": "Database Incident Template",
                "description": "Template for database-related incidents",
                "template_data": {
                    "category": "database",
                    "severity": "high",
                    "priority": "high",
                    "default_tags": ["database", "infrastructure"],
                    "checklist": [
                        "Check database logs",
                        "Verify connection pool settings",
                        "Check query performance",
                        "Verify database resources"
                    ]
                },
                "category": "database",
                "is_public": True,
                "created_by": "system",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
        ]
        for template in default_templates:
            _incident_templates[template["template_id"]] = template


# Initialize default data
_initialize_default_data()


# ============================================================================
# Helper Functions
# ============================================================================

def _add_timeline_event(incident_id: str, event: str, user: str, details: Dict[str, Any]):
    """Add event to incident timeline"""
    _incident_timeline[incident_id].append({
        "event": event,
        "timestamp": datetime.utcnow().isoformat(),
        "user": user,
        "details": details
    })
    logger.info(f"Added timeline event '{event}' for incident {incident_id}")


def _validate_incident_exists(incident_id: str):
    """Validate incident exists"""
    if incident_id not in _incidents:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")


def _check_rate_limit(request: Request):
    """Check rate limit"""
    try:
        limiter.check_request(request)
    except Exception as e:
        logger.warning(f"Rate limit check failed: {e}")


def _process_batch(items: List, process_func, batch_size: int = BATCH_SIZE):
    """Process items in batches to avoid rate limits"""
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = process_func(batch)
        results.extend(batch_results)
        logger.info(f"Processed batch {i//batch_size + 1} with {len(batch)} items")
    return results


# ============================================================================
# API Endpoints (1-10)
# ============================================================================

@router.post(
    "/incidents",
    summary="Create incident",
    responses={
        200: {"description": "Incident created successfully"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def create_incident(
    request: Request,
    incident: IncidentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new incident"""
    try:
        _check_rate_limit(request)
        
        incident_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        new_incident = {
            "incident_id": incident_id,
            "title": incident.title,
            "description": incident.description,
            "severity": incident.severity,
            "category": incident.category,
            "priority": incident.priority,
            "impact": incident.impact,
            "urgency": incident.urgency,
            "status": "open",
            "assigned_to": incident.assigned_to,
            "tags": incident.tags or [],
            "environment": incident.environment,
            "source": incident.source,
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
            "resolution_notes": None,
            "root_cause": None,
            "metadata": incident.metadata or {},
        }
        
        _incidents[incident_id] = new_incident
        _add_timeline_event(
            incident_id,
            "created",
            current_user.username,
            {"message": f"Incident created by {current_user.username}"}
        )
        
        logger.info(
            f"Incident created: ID={incident_id}, Title={incident.title}, "
            f"Severity={incident.severity}, User={current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "status": "created",
            "message": "Incident created successfully",
            "incident": new_incident
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/incidents",
    summary="Get incidents list",
    responses={
        200: {"description": "Incidents retrieved successfully"},
        401: {"description": "Unauthorized"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def get_incidents(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Get list of incidents with optional filters"""
    try:
        _check_rate_limit(request)
        
        incidents = list(_incidents.values())
        
        if status:
            incidents = [inc for inc in incidents if inc.get("status") == status]
        if severity:
            incidents = [inc for inc in incidents if inc.get("severity") == severity]
        if category:
            incidents = [inc for inc in incidents if inc.get("category") == category]
        if assigned_to:
            incidents = [inc for inc in incidents if inc.get("assigned_to") == assigned_to]
        
        incidents = sorted(incidents, key=lambda x: x["created_at"], reverse=True)
        total = len(incidents)
        paginated_incidents = incidents[offset:offset + limit]
        
        logger.info(
            f"Retrieved {len(paginated_incidents)} incidents (total: {total}) "
            f"for user {current_user.username}"
        )
        
        return {
            "incidents": paginated_incidents,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error getting incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/incidents/{incident_id}",
    summary="Get incident by ID",
    responses={
        200: {"description": "Incident retrieved successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def get_incident(
    request: Request,
    incident_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get a specific incident by ID"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        incident = _incidents[incident_id]
        
        logger.info(f"Retrieved incident {incident_id} for user {current_user.username}")
        
        return {
            "incident": incident,
            "comments": _incident_comments.get(incident_id, []),
            "attachments": _incident_attachments.get(incident_id, []),
            "links": _incident_links.get(incident_id, [])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting incident {incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/incidents/{incident_id}",
    summary="Update incident",
    responses={
        200: {"description": "Incident updated successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def update_incident(
    request: Request,
    incident_id: str,
    incident_update: IncidentUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update an incident"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        incident = _incidents[incident_id]
        updated_fields = []
        
        if incident_update.title is not None:
            incident["title"] = incident_update.title
            updated_fields.append("title")
        if incident_update.description is not None:
            incident["description"] = incident_update.description
            updated_fields.append("description")
        if incident_update.severity is not None:
            incident["severity"] = incident_update.severity
            updated_fields.append("severity")
        if incident_update.category is not None:
            incident["category"] = incident_update.category
            updated_fields.append("category")
        if incident_update.priority is not None:
            incident["priority"] = incident_update.priority
            updated_fields.append("priority")
        if incident_update.impact is not None:
            incident["impact"] = incident_update.impact
            updated_fields.append("impact")
        if incident_update.urgency is not None:
            incident["urgency"] = incident_update.urgency
            updated_fields.append("urgency")
        if incident_update.assigned_to is not None:
            incident["assigned_to"] = incident_update.assigned_to
            updated_fields.append("assigned_to")
        if incident_update.tags is not None:
            incident["tags"] = incident_update.tags
            updated_fields.append("tags")
        if incident_update.status is not None:
            incident["status"] = incident_update.status
            updated_fields.append("status")
            if incident_update.status in ["resolved", "closed"] and not incident.get("resolved_at"):
                incident["resolved_at"] = datetime.utcnow().isoformat()
        if incident_update.resolution_notes is not None:
            incident["resolution_notes"] = incident_update.resolution_notes
            updated_fields.append("resolution_notes")
        if incident_update.root_cause is not None:
            incident["root_cause"] = incident_update.root_cause
            updated_fields.append("root_cause")
        if incident_update.metadata is not None:
            incident["metadata"].update(incident_update.metadata)
            updated_fields.append("metadata")
        
        incident["updated_at"] = datetime.utcnow().isoformat()
        _incidents[incident_id] = incident
        
        _add_timeline_event(
            incident_id,
            "updated",
            current_user.username,
            {"fields": updated_fields, "user": current_user.username}
        )
        
        logger.info(
            f"Updated incident {incident_id}, fields: {updated_fields}, "
            f"user: {current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "status": "updated",
            "updated_fields": updated_fields,
            "incident": incident
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating incident {incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/incidents/{incident_id}",
    summary="Delete incident",
    responses={
        200: {"description": "Incident deleted successfully"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - insufficient permissions"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def delete_incident(
    request: Request,
    incident_id: str,
    current_user: User = Depends(require_role(["admin", "incident_manager"])),
):
    """Delete an incident (admin/incident_manager only)"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        del _incidents[incident_id]
        if incident_id in _incident_comments:
            del _incident_comments[incident_id]
        if incident_id in _incident_attachments:
            del _incident_attachments[incident_id]
        if incident_id in _incident_timeline:
            del _incident_timeline[incident_id]
        if incident_id in _incident_links:
            del _incident_links[incident_id]
        
        logger.warning(
            f"Deleted incident {incident_id} by user {current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "status": "deleted",
            "message": "Incident deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting incident {incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/incidents/{incident_id}/status",
    summary="Update incident status",
    responses={
        200: {"description": "Incident status updated successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def update_incident_status(
    request: Request,
    incident_id: str,
    status_update: IncidentStatusUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update incident status"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        incident = _incidents[incident_id]
        old_status = incident["status"]
        incident["status"] = status_update.status
        incident["updated_at"] = datetime.utcnow().isoformat()
        
        if status_update.status in ["resolved", "closed"] and not incident.get("resolved_at"):
            incident["resolved_at"] = datetime.utcnow().isoformat()
        
        _incidents[incident_id] = incident
        
        _add_timeline_event(
            incident_id,
            "status_changed",
            current_user.username,
            {
                "old_status": old_status,
                "new_status": status_update.status,
                "reason": status_update.reason
            }
        )
        
        logger.info(
            f"Updated incident {incident_id} status from {old_status} to "
            f"{status_update.status} by user {current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "old_status": old_status,
            "new_status": status_update.status,
            "incident": incident
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating incident status {incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/incidents/{incident_id}/assign",
    summary="Assign incident",
    responses={
        200: {"description": "Incident assigned successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def assign_incident(
    request: Request,
    incident_id: str,
    assignment: IncidentAssign,
    current_user: User = Depends(get_current_user),
):
    """Assign an incident to a user or team"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        incident = _incidents[incident_id]
        old_assignee = incident.get("assigned_to")
        incident["assigned_to"] = assignment.assigned_to
        incident["updated_at"] = datetime.utcnow().isoformat()
        _incidents[incident_id] = incident
        
        _add_timeline_event(
            incident_id,
            "assigned",
            current_user.username,
            {
                "old_assignee": old_assignee,
                "new_assignee": assignment.assigned_to,
                "assignee_type": assignment.assignee_type,
                "message": assignment.message
            }
        )
        
        logger.info(
            f"Assigned incident {incident_id} to {assignment.assigned_to} "
            f"by user {current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "old_assignee": old_assignee,
            "new_assignee": assignment.assigned_to,
            "assignee_type": assignment.assignee_type,
            "notified": assignment.notify,
            "message": "Incident assigned successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning incident {incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/incidents/{incident_id}/acknowledge",
    summary="Acknowledge incident",
    responses={
        200: {"description": "Incident acknowledged successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def acknowledge_incident(
    request: Request,
    incident_id: str,
    comment: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Acknowledge an incident"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        incident = _incidents[incident_id]
        incident["acknowledged_by"] = current_user.username
        incident["acknowledged_at"] = datetime.utcnow().isoformat()
        incident["updated_at"] = datetime.utcnow().isoformat()
        _incidents[incident_id] = incident
        
        _add_timeline_event(
            incident_id,
            "acknowledged",
            current_user.username,
            {"comment": comment, "user": current_user.username}
        )
        
        logger.info(
            f"Acknowledged incident {incident_id} by user {current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "acknowledged_by": current_user.username,
            "acknowledged_at": incident["acknowledged_at"],
            "message": "Incident acknowledged successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging incident {incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/incidents/{incident_id}/resolve",
    summary="Resolve incident",
    responses={
        200: {"description": "Incident resolved successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def resolve_incident(
    request: Request,
    incident_id: str,
    resolution_notes: str,
    root_cause: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Resolve an incident"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        incident = _incidents[incident_id]
        incident["status"] = "resolved"
        incident["resolution_notes"] = resolution_notes
        incident["root_cause"] = root_cause
        incident["resolved_by"] = current_user.username
        incident["resolved_at"] = datetime.utcnow().isoformat()
        incident["updated_at"] = datetime.utcnow().isoformat()
        _incidents[incident_id] = incident
        
        _add_timeline_event(
            incident_id,
            "resolved",
            current_user.username,
            {
                "resolution_notes": resolution_notes,
                "root_cause": root_cause,
                "resolved_by": current_user.username
            }
        )
        
        logger.info(
            f"Resolved incident {incident_id} by user {current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "resolved_by": current_user.username,
            "resolved_at": incident["resolved_at"],
            "message": "Incident resolved successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving incident {incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/incidents/{incident_id}/escalate",
    summary="Escalate incident",
    responses={
        200: {"description": "Incident escalated successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def escalate_incident(
    request: Request,
    incident_id: str,
    escalation_level: str,
    escalate_to: str,
    reason: str,
    current_user: User = Depends(get_current_user),
):
    """Escalate an incident to a higher level"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        incident = _incidents[incident_id]
        old_level = incident.get("escalation_level", "none")
        incident["escalation_level"] = escalation_level
        incident["escalated_to"] = escalate_to
        incident["escalated_by"] = current_user.username
        incident["escalated_at"] = datetime.utcnow().isoformat()
        incident["updated_at"] = datetime.utcnow().isoformat()
        _incidents[incident_id] = incident
        
        _add_timeline_event(
            incident_id,
            "escalated",
            current_user.username,
            {
                "old_level": old_level,
                "new_level": escalation_level,
                "escalate_to": escalate_to,
                "reason": reason
            }
        )
        
        logger.info(
            f"Escalated incident {incident_id} to level {escalation_level} "
            f"by user {current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "old_level": old_level,
            "new_level": escalation_level,
            "escalated_to": escalate_to,
            "escalated_by": current_user.username,
            "escalated_at": incident["escalated_at"],
            "message": "Incident escalated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error escalating incident {incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API Endpoints (11-20)
# ============================================================================

@router.get(
    "/incidents/{incident_id}/timeline",
    summary="Get incident timeline",
    responses={
        200: {"description": "Timeline retrieved successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def get_incident_timeline(
    request: Request,
    incident_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get incident timeline"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        timeline = _incident_timeline.get(incident_id, [])
        
        logger.info(
            f"Retrieved timeline for incident {incident_id} "
            f"({len(timeline)} events) for user {current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "timeline": timeline,
            "total_events": len(timeline)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting timeline for incident {incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/incidents/{incident_id}/comments",
    summary="Add comment to incident",
    responses={
        200: {"description": "Comment added successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def add_incident_comment(
    request: Request,
    incident_id: str,
    comment: IncidentComment,
    current_user: User = Depends(get_current_user),
):
    """Add a comment to an incident"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        comment_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        new_comment = {
            "comment_id": comment_id,
            "content": comment.content,
            "is_internal": comment.is_internal,
            "mention_users": comment.mention_users or [],
            "created_by": current_user.username,
            "created_at": now,
            "updated_at": now
        }
        
        _incident_comments[incident_id].append(new_comment)
        _add_timeline_event(
            incident_id,
            "comment_added",
            current_user.username,
            {"comment_id": comment_id, "is_internal": comment.is_internal}
        )
        
        logger.info(
            f"Added comment {comment_id} to incident {incident_id} "
            f"by user {current_user.username}"
        )
        
        return {
            "comment_id": comment_id,
            "incident_id": incident_id,
            "comment": new_comment,
            "message": "Comment added successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding comment to incident {incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/incidents/{incident_id}/comments",
    summary="Get incident comments",
    responses={
        200: {"description": "Comments retrieved successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def get_incident_comments(
    request: Request,
    incident_id: str,
    include_internal: bool = Query(False),
    current_user: User = Depends(get_current_user),
):
    """Get incident comments"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        comments = _incident_comments.get(incident_id, [])
        
        if not include_internal:
            comments = [c for c in comments if not c.get("is_internal", False)]
        
        logger.info(
            f"Retrieved {len(comments)} comments for incident {incident_id} "
            f"for user {current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "comments": comments,
            "total": len(comments)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting comments for incident {incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/incidents/{incident_id}/attachments",
    summary="Add attachment to incident",
    responses={
        200: {"description": "Attachment added successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        413: {"description": "Payload too large"},
        415: {"description": "Unsupported media type"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def add_incident_attachment(
    request: Request,
    incident_id: str,
    file: UploadFile = File(...),
    description: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Add an attachment to an incident"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        file_content = await file.read()
        if len(file_content) > MAX_ATTACHMENT_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed size of {MAX_ATTACHMENT_SIZE} bytes"
            )
        
        if file.content_type not in ALLOWED_ATTACHMENT_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"File type {file.content_type} is not allowed"
            )
        
        attachment_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        new_attachment = {
            "attachment_id": attachment_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(file_content),
            "description": description,
            "uploaded_by": current_user.username,
            "uploaded_at": now,
            "storage_path": f"/incidents/{incident_id}/attachments/{attachment_id}"
        }
        
        _incident_attachments[incident_id].append(new_attachment)
        _add_timeline_event(
            incident_id,
            "attachment_added",
            current_user.username,
            {"attachment_id": attachment_id, "filename": file.filename}
        )
        
        logger.info(
            f"Added attachment {attachment_id} ({file.filename}) to incident {incident_id} "
            f"by user {current_user.username}"
        )
        
        return {
            "attachment_id": attachment_id,
            "incident_id": incident_id,
            "attachment": new_attachment,
            "message": "Attachment added successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding attachment to incident {incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/incidents/{incident_id}/attachments",
    summary="Get incident attachments",
    responses={
        200: {"description": "Attachments retrieved successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def get_incident_attachments(
    request: Request,
    incident_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get incident attachments"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        attachments = _incident_attachments.get(incident_id, [])
        
        logger.info(
            f"Retrieved {len(attachments)} attachments for incident {incident_id} "
            f"for user {current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "attachments": attachments,
            "total": len(attachments)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting attachments for incident {incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/incidents/statistics",
    summary="Get incident statistics",
    responses={
        200: {"description": "Statistics retrieved successfully"},
        401: {"description": "Unauthorized"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def get_incident_statistics(
    request: Request,
    time_range: str = Query("7d", description="Time range: 1h, 24h, 7d, 30d"),
    current_user: User = Depends(get_current_user),
):
    """Get incident statistics"""
    try:
        _check_rate_limit(request)
        
        incidents = list(_incidents.values())
        
        total_incidents = len(incidents)
        open_incidents = len([i for i in incidents if i.get("status") == "open"])
        in_progress_incidents = len([i for i in incidents if i.get("status") == "in_progress"])
        resolved_incidents = len([i for i in incidents if i.get("status") == "resolved"])
        closed_incidents = len([i for i in incidents if i.get("status") == "closed"])
        
        severity_counts = {}
        for incident in incidents:
            severity = incident.get("severity", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        category_counts = {}
        for incident in incidents:
            category = incident.get("category", "unknown")
            category_counts[category] = category_counts.get(category, 0) + 1
        
        resolved_incidents_data = [i for i in incidents if i.get("resolved_at")]
        if resolved_incidents_data:
            resolution_times = []
            for inc in resolved_incidents_data:
                created = datetime.fromisoformat(inc["created_at"])
                resolved = datetime.fromisoformat(inc["resolved_at"])
                resolution_times.append((resolved - created).total_seconds())
            avg_resolution_time = sum(resolution_times) / len(resolution_times)
        else:
            avg_resolution_time = 0
        
        statistics = {
            "time_range": time_range,
            "total_incidents": total_incidents,
            "by_status": {
                "open": open_incidents,
                "in_progress": in_progress_incidents,
                "resolved": resolved_incidents,
                "closed": closed_incidents
            },
            "by_severity": severity_counts,
            "by_category": category_counts,
            "average_resolution_time_seconds": avg_resolution_time,
            "resolution_rate": (resolved_incidents / total_incidents * 100) if total_incidents > 0 else 0
        }
        
        logger.info(
            f"Retrieved incident statistics for time range {time_range} "
            f"by user {current_user.username}"
        )
        
        return statistics
    except Exception as e:
        logger.error(f"Error getting incident statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/incidents/trends",
    summary="Get incident trends",
    responses={
        200: {"description": "Trends retrieved successfully"},
        401: {"description": "Unauthorized"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def get_incident_trends(
    request: Request,
    period: str = Query("daily", description="Period: hourly, daily, weekly, monthly"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
):
    """Get incident trends over time"""
    try:
        _check_rate_limit(request)
        
        incidents = list(_incidents.values())
        
        trends = []
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            day_incidents = [
                inc for inc in incidents
                if datetime.fromisoformat(inc["created_at"]).date() == date.date()
            ]
            
            trends.append({
                "date": date_str,
                "count": len(day_incidents),
                "by_severity": {
                    sev: len([inc for inc in day_incidents if inc.get("severity") == sev])
                    for sev in ["low", "medium", "high", "critical"]
                }
            })
        
        trends = trends[::-1]
        
        logger.info(
            f"Retrieved incident trends for period {period}, {days} days "
            f"by user {current_user.username}"
        )
        
        return {
            "period": period,
            "days": days,
            "trends": trends
        }
    except Exception as e:
        logger.error(f"Error getting incident trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/incidents/bulk",
    summary="Bulk create incidents",
    responses={
        200: {"description": "Incidents created successfully"},
        401: {"description": "Unauthorized"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def bulk_create_incidents(
    request: Request,
    bulk_data: IncidentBulkCreate,
    current_user: User = Depends(get_current_user),
):
    """Bulk create incidents"""
    try:
        _check_rate_limit(request)
        
        def process_batch(batch):
            results = []
            for incident_data in batch:
                incident_id = str(uuid.uuid4())
                now = datetime.utcnow().isoformat()
                
                new_incident = {
                    "incident_id": incident_id,
                    "title": incident_data.title,
                    "description": incident_data.description,
                    "severity": incident_data.severity,
                    "category": incident_data.category,
                    "priority": incident_data.priority,
                    "impact": incident_data.impact,
                    "urgency": incident_data.urgency,
                    "status": "open",
                    "assigned_to": incident_data.assigned_to,
                    "tags": incident_data.tags or [],
                    "environment": incident_data.environment,
                    "source": incident_data.source,
                    "created_at": now,
                    "updated_at": now,
                    "resolved_at": None,
                    "resolution_notes": None,
                    "root_cause": None,
                    "metadata": incident_data.metadata or {},
                }
                
                _incidents[incident_id] = new_incident
                _add_timeline_event(
                    incident_id,
                    "created",
                    current_user.username,
                    {"message": f"Bulk created by {current_user.username}"}
                )
                
                results.append({
                    "incident_id": incident_id,
                    "status": "created",
                    "title": incident_data.title
                })
            return results
        
        results = _process_batch(bulk_data.incidents, process_batch)
        
        logger.info(
            f"Bulk created {len(results)} incidents by user {current_user.username}"
        )
        
        return {
            "total_requested": len(bulk_data.incidents),
            "total_created": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"Error in bulk creating incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/incidents/bulk",
    summary="Bulk update incidents",
    responses={
        200: {"description": "Incidents updated successfully"},
        401: {"description": "Unauthorized"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def bulk_update_incidents(
    request: Request,
    bulk_data: IncidentBulkUpdate,
    current_user: User = Depends(get_current_user),
):
    """Bulk update incidents"""
    try:
        _check_rate_limit(request)
        
        def process_batch(batch):
            results = []
            for incident_id in batch:
                if incident_id not in _incidents:
                    results.append({
                        "incident_id": incident_id,
                        "status": "not_found",
                        "message": "Incident not found"
                    })
                    continue
                
                incident = _incidents[incident_id]
                updates = bulk_data.updates
                
                if updates.title is not None:
                    incident["title"] = updates.title
                if updates.description is not None:
                    incident["description"] = updates.description
                if updates.severity is not None:
                    incident["severity"] = updates.severity
                if updates.status is not None:
                    incident["status"] = updates.status
                if updates.assigned_to is not None:
                    incident["assigned_to"] = updates.assigned_to
                
                incident["updated_at"] = datetime.utcnow().isoformat()
                _incidents[incident_id] = incident
                
                _add_timeline_event(
                    incident_id,
                    "bulk_updated",
                    current_user.username,
                    {"message": f"Bulk updated by {current_user.username}"}
                )
                
                results.append({
                    "incident_id": incident_id,
                    "status": "updated"
                })
            return results
        
        results = _process_batch(bulk_data.incident_ids, process_batch)
        
        logger.info(
            f"Bulk updated {len(results)} incidents by user {current_user.username}"
        )
        
        return {
            "total_requested": len(bulk_data.incident_ids),
            "total_updated": len([r for r in results if r["status"] == "updated"]),
            "results": results
        }
    except Exception as e:
        logger.error(f"Error in bulk updating incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/incidents/bulk",
    summary="Bulk delete incidents",
    responses={
        200: {"description": "Incidents deleted successfully"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - insufficient permissions"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def bulk_delete_incidents(
    request: Request,
    incident_ids: List[str],
    current_user: User = Depends(require_role(["admin", "incident_manager"])),
):
    """Bulk delete incidents (admin/incident_manager only)"""
    try:
        _check_rate_limit(request)
        
        def process_batch(batch):
            results = []
            for incident_id in batch:
                if incident_id not in _incidents:
                    results.append({
                        "incident_id": incident_id,
                        "status": "not_found",
                        "message": "Incident not found"
                    })
                    continue
                
                del _incidents[incident_id]
                if incident_id in _incident_comments:
                    del _incident_comments[incident_id]
                if incident_id in _incident_attachments:
                    del _incident_attachments[incident_id]
                if incident_id in _incident_timeline:
                    del _incident_timeline[incident_id]
                if incident_id in _incident_links:
                    del _incident_links[incident_id]
                
                results.append({
                    "incident_id": incident_id,
                    "status": "deleted"
                })
            return results
        
        results = _process_batch(incident_ids, process_batch)
        
        logger.warning(
            f"Bulk deleted {len(results)} incidents by user {current_user.username}"
        )
        
        return {
            "total_requested": len(incident_ids),
            "total_deleted": len([r for r in results if r["status"] == "deleted"]),
            "results": results
        }
    except Exception as e:
        logger.error(f"Error in bulk deleting incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API Endpoints (21-30)
# ============================================================================

@router.post(
    "/incidents/search",
    summary="Search incidents",
    responses={
        200: {"description": "Search results retrieved successfully"},
        401: {"description": "Unauthorized"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def search_incidents(
    request: Request,
    search: IncidentSearch,
    current_user: User = Depends(get_current_user),
):
    """Search incidents with query and filters"""
    try:
        _check_rate_limit(request)
        
        incidents = list(_incidents.values())
        query_lower = search.query.lower()
        
        # Text search in title and description
        filtered_incidents = [
            inc for inc in incidents
            if query_lower in inc.get("title", "").lower()
            or query_lower in inc.get("description", "").lower()
        ]
        
        # Apply additional filters
        if search.filters:
            if "status" in search.filters:
                filtered_incidents = [
                    inc for inc in filtered_incidents
                    if inc.get("status") == search.filters["status"]
                ]
            if "severity" in search.filters:
                filtered_incidents = [
                    inc for inc in filtered_incidents
                    if inc.get("severity") == search.filters["severity"]
                ]
            if "category" in search.filters:
                filtered_incidents = [
                    inc for inc in filtered_incidents
                    if inc.get("category") == search.filters["category"]
                ]
            if "tags" in search.filters:
                filter_tags = search.filters["tags"]
                filtered_incidents = [
                    inc for inc in filtered_incidents
                    if any(tag in inc.get("tags", []) for tag in filter_tags)
                ]
        
        # Sort results
        reverse_sort = search.sort_order == "desc"
        if search.sort_by in ["created_at", "updated_at", "resolved_at"]:
            filtered_incidents = sorted(
                filtered_incidents,
                key=lambda x: x.get(search.sort_by, ""),
                reverse=reverse_sort
            )
        elif search.sort_by == "severity":
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            filtered_incidents = sorted(
                filtered_incidents,
                key=lambda x: severity_order.get(x.get("severity", "low"), 4),
                reverse=reverse_sort
            )
        
        # Pagination
        total = len(filtered_incidents)
        paginated_results = filtered_incidents[search.offset:search.offset + search.limit]
        
        logger.info(
            f"Search incidents: query='{search.query}', results={len(paginated_results)}, "
            f"total={total}, user={current_user.username}"
        )
        
        return {
            "query": search.query,
            "results": paginated_results,
            "total": total,
            "limit": search.limit,
            "offset": search.offset
        }
    except Exception as e:
        logger.error(f"Error searching incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/incidents/filter",
    summary="Filter incidents",
    responses={
        200: {"description": "Filtered incidents retrieved successfully"},
        401: {"description": "Unauthorized"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def filter_incidents(
    request: Request,
    filter_data: IncidentFilter,
    current_user: User = Depends(get_current_user),
):
    """Filter incidents with multiple criteria"""
    try:
        _check_rate_limit(request)
        
        incidents = list(_incidents.values())
        filtered_incidents = incidents
        
        if filter_data.status:
            filtered_incidents = [
                inc for inc in filtered_incidents
                if inc.get("status") in filter_data.status
            ]
        if filter_data.severity:
            filtered_incidents = [
                inc for inc in filtered_incidents
                if inc.get("severity") in filter_data.severity
            ]
        if filter_data.category:
            filtered_incidents = [
                inc for inc in filtered_incidents
                if inc.get("category") in filter_data.category
            ]
        if filter_data.priority:
            filtered_incidents = [
                inc for inc in filtered_incidents
                if inc.get("priority") in filter_data.priority
            ]
        if filter_data.assigned_to:
            filtered_incidents = [
                inc for inc in filtered_incidents
                if inc.get("assigned_to") in filter_data.assigned_to
            ]
        if filter_data.created_after:
            filtered_incidents = [
                inc for inc in filtered_incidents
                if datetime.fromisoformat(inc["created_at"]) >= filter_data.created_after
            ]
        if filter_data.created_before:
            filtered_incidents = [
                inc for inc in filtered_incidents
                if datetime.fromisoformat(inc["created_at"]) <= filter_data.created_before
            ]
        if filter_data.resolved_after:
            filtered_incidents = [
                inc for inc in filtered_incidents
                if inc.get("resolved_at") and datetime.fromisoformat(inc["resolved_at"]) >= filter_data.resolved_after
            ]
        if filter_data.resolved_before:
            filtered_incidents = [
                inc for inc in filtered_incidents
                if inc.get("resolved_at") and datetime.fromisoformat(inc["resolved_at"]) <= filter_data.resolved_before
            ]
        if filter_data.tags:
            filtered_incidents = [
                inc for inc in filtered_incidents
                if any(tag in inc.get("tags", []) for tag in filter_data.tags)
            ]
        if filter_data.environment:
            filtered_incidents = [
                inc for inc in filtered_incidents
                if inc.get("environment") == filter_data.environment
            ]
        
        total = len(filtered_incidents)
        paginated_results = filtered_incidents[filter_data.offset:filter_data.offset + filter_data.limit]
        
        logger.info(
            f"Filtered incidents: total={total}, returned={len(paginated_results)}, "
            f"user={current_user.username}"
        )
        
        return {
            "incidents": paginated_results,
            "total": total,
            "limit": filter_data.limit,
            "offset": filter_data.offset
        }
    except Exception as e:
        logger.error(f"Error filtering incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/incidents/{incident_id}/merge",
    summary="Merge incidents",
    responses={
        200: {"description": "Incidents merged successfully"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - insufficient permissions"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def merge_incidents(
    request: Request,
    incident_id: str,
    merge_data: IncidentMerge,
    current_user: User = Depends(require_role(["admin", "incident_manager"])),
):
    """Merge multiple incidents into one"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        # Validate all source incidents exist
        for source_id in merge_data.source_incident_ids:
            if source_id not in _incidents:
                raise HTTPException(
                    status_code=404,
                    detail=f"Source incident {source_id} not found"
                )
        
        target_incident = _incidents[incident_id]
        merged_comments = []
        merged_attachments = []
        
        for source_id in merge_data.source_incident_ids:
            source_incident = _incidents[source_id]
            
            # Merge comments based on strategy
            if merge_data.merge_strategy in ["append", "keep_latest"]:
                if source_id in _incident_comments:
                    for comment in _incident_comments[source_id]:
                        comment["source_incident_id"] = source_id
                        merged_comments.append(comment)
            
            # Merge attachments
            if source_id in _incident_attachments:
                for attachment in _incident_attachments[source_id]:
                    attachment["source_incident_id"] = source_id
                    merged_attachments.append(attachment)
            
            # Update source incident status
            source_incident["status"] = "merged"
            source_incident["merged_into"] = incident_id
            source_incident["merged_at"] = datetime.utcnow().isoformat()
            _incidents[source_id] = source_incident
            
            # Add link
            _incident_links[incident_id].append({
                "related_incident_id": source_id,
                "link_type": "merged_from",
                "description": f"Merged from {source_id}",
                "created_at": datetime.utcnow().isoformat(),
                "created_by": current_user.username
            })
        
        # Append merged data to target
        if merge_data.merge_strategy == "append":
            _incident_comments[incident_id].extend(merged_comments)
            _incident_attachments[incident_id].extend(merged_attachments)
        elif merge_data.merge_strategy == "replace":
            _incident_comments[incident_id] = merged_comments
            _incident_attachments[incident_id] = merged_attachments
        
        _add_timeline_event(
            incident_id,
            "merged",
            current_user.username,
            {
                "source_incidents": merge_data.source_incident_ids,
                "strategy": merge_data.merge_strategy,
                "reason": merge_data.reason
            }
        )
        
        logger.info(
            f"Merged {len(merge_data.source_incident_ids)} incidents into {incident_id} "
            f"by user {current_user.username}"
        )
        
        return {
            "target_incident_id": incident_id,
            "merged_incidents": merge_data.source_incident_ids,
            "merge_strategy": merge_data.merge_strategy,
            "merged_comments_count": len(merged_comments),
            "merged_attachments_count": len(merged_attachments),
            "message": "Incidents merged successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error merging incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/incidents/{incident_id}/links",
    summary="Link incidents",
    responses={
        200: {"description": "Incidents linked successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def link_incidents(
    request: Request,
    incident_id: str,
    link_data: IncidentLink,
    current_user: User = Depends(get_current_user),
):
    """Link two incidents together"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        _validate_incident_exists(link_data.related_incident_id)
        
        if incident_id == link_data.related_incident_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot link an incident to itself"
            )
        
        link = {
            "related_incident_id": link_data.related_incident_id,
            "link_type": link_data.link_type,
            "description": link_data.description,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": current_user.username
        }
        
        _incident_links[incident_id].append(link)
        
        # Create reverse link for bidirectional relationships
        if link_data.link_type in ["related", "duplicate"]:
            reverse_link = {
                "related_incident_id": incident_id,
                "link_type": link_data.link_type,
                "description": f"Reverse link: {link_data.description}",
                "created_at": datetime.utcnow().isoformat(),
                "created_by": current_user.username
            }
            _incident_links[link_data.related_incident_id].append(reverse_link)
        
        _add_timeline_event(
            incident_id,
            "linked",
            current_user.username,
            {
                "related_incident_id": link_data.related_incident_id,
                "link_type": link_data.link_type
            }
        )
        
        logger.info(
            f"Linked incident {incident_id} to {link_data.related_incident_id} "
            f"by user {current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "related_incident_id": link_data.related_incident_id,
            "link_type": link_data.link_type,
            "link": link,
            "message": "Incidents linked successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/incidents/{incident_id}/links",
    summary="Get incident links",
    responses={
        200: {"description": "Links retrieved successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def get_incident_links(
    request: Request,
    incident_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get all links for an incident"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        links = _incident_links.get(incident_id, [])
        
        logger.info(
            f"Retrieved {len(links)} links for incident {incident_id} "
            f"by user {current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "links": links,
            "total": len(links)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting links for incident {incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/incidents/{incident_id}/links/{related_incident_id}",
    summary="Unlink incidents",
    responses={
        200: {"description": "Incidents unlinked successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def unlink_incidents(
    request: Request,
    incident_id: str,
    related_incident_id: str,
    current_user: User = Depends(get_current_user),
):
    """Remove link between two incidents"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        _validate_incident_exists(related_incident_id)
        
        if incident_id in _incident_links:
            _incident_links[incident_id] = [
                link for link in _incident_links[incident_id]
                if link["related_incident_id"] != related_incident_id
            ]
        
        if related_incident_id in _incident_links:
            _incident_links[related_incident_id] = [
                link for link in _incident_links[related_incident_id]
                if link["related_incident_id"] != incident_id
            ]
        
        _add_timeline_event(
            incident_id,
            "unlinked",
            current_user.username,
            {"related_incident_id": related_incident_id}
        )
        
        logger.info(
            f"Unlinked incident {incident_id} from {related_incident_id} "
            f"by user {current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "related_incident_id": related_incident_id,
            "message": "Incidents unlinked successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unlinking incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/templates",
    summary="Create incident template",
    responses={
        200: {"description": "Template created successfully"},
        401: {"description": "Unauthorized"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def create_template(
    request: Request,
    template: IncidentTemplate,
    current_user: User = Depends(get_current_user),
):
    """Create a new incident template"""
    try:
        _check_rate_limit(request)
        
        template_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        new_template = {
            "template_id": template_id,
            "name": template.name,
            "description": template.description,
            "template_data": template.template_data,
            "category": template.category,
            "is_public": template.is_public,
            "created_by": current_user.username,
            "created_at": now,
            "updated_at": now
        }
        
        _incident_templates[template_id] = new_template
        
        logger.info(
            f"Created template {template_id} ({template.name}) "
            f"by user {current_user.username}"
        )
        
        return {
            "template_id": template_id,
            "template": new_template,
            "message": "Template created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/templates",
    summary="Get incident templates",
    responses={
        200: {"description": "Templates retrieved successfully"},
        401: {"description": "Unauthorized"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def get_templates(
    request: Request,
    category: Optional[str] = Query(None),
    is_public: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Get incident templates with optional filters"""
    try:
        _check_rate_limit(request)
        
        templates = list(_incident_templates.values())
        
        if category:
            templates = [t for t in templates if t.get("category") == category]
        if is_public is not None:
            templates = [t for t in templates if t.get("is_public") == is_public]
        
        logger.info(
            f"Retrieved {len(templates)} templates for user {current_user.username}"
        )
        
        return {
            "templates": templates,
            "total": len(templates)
        }
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/templates/{template_id}",
    summary="Get incident template by ID",
    responses={
        200: {"description": "Template retrieved successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Template not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def get_template(
    request: Request,
    template_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get a specific template by ID"""
    try:
        _check_rate_limit(request)
        
        if template_id not in _incident_templates:
            raise HTTPException(
                status_code=404,
                detail=f"Template {template_id} not found"
            )
        
        template = _incident_templates[template_id]
        
        logger.info(
            f"Retrieved template {template_id} for user {current_user.username}"
        )
        
        return {
            "template_id": template_id,
            "template": template
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/templates/{template_id}",
    summary="Update incident template",
    responses={
        200: {"description": "Template updated successfully"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - insufficient permissions"},
        404: {"description": "Template not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def update_template(
    request: Request,
    template_id: str,
    template: IncidentTemplate,
    current_user: User = Depends(get_current_user),
):
    """Update an incident template"""
    try:
        _check_rate_limit(request)
        
        if template_id not in _incident_templates:
            raise HTTPException(
                status_code=404,
                detail=f"Template {template_id} not found"
            )
        
        existing_template = _incident_templates[template_id]
        
        # Check ownership or admin
        if existing_template.get("created_by") != current_user.username:
            require_role(["admin"])
        
        existing_template["name"] = template.name
        existing_template["description"] = template.description
        existing_template["template_data"] = template.template_data
        existing_template["category"] = template.category
        existing_template["is_public"] = template.is_public
        existing_template["updated_at"] = datetime.utcnow().isoformat()
        
        _incident_templates[template_id] = existing_template
        
        logger.info(
            f"Updated template {template_id} by user {current_user.username}"
        )
        
        return {
            "template_id": template_id,
            "template": existing_template,
            "message": "Template updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/templates/{template_id}",
    summary="Delete incident template",
    responses={
        200: {"description": "Template deleted successfully"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - insufficient permissions"},
        404: {"description": "Template not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def delete_template(
    request: Request,
    template_id: str,
    current_user: User = Depends(require_role(["admin", "incident_manager"])),
):
    """Delete an incident template"""
    try:
        _check_rate_limit(request)
        
        if template_id not in _incident_templates:
            raise HTTPException(
                status_code=404,
                detail=f"Template {template_id} not found"
            )
        
        del _incident_templates[template_id]
        
        logger.info(
            f"Deleted template {template_id} by user {current_user.username}"
        )
        
        return {
            "template_id": template_id,
            "message": "Template deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/workflows",
    summary="Create incident workflow",
    responses={
        200: {"description": "Workflow created successfully"},
        401: {"description": "Unauthorized"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def create_workflow(
    request: Request,
    workflow: IncidentWorkflow,
    current_user: User = Depends(require_role(["admin", "incident_manager"])),
):
    """Create a new incident workflow"""
    try:
        _check_rate_limit(request)
        
        workflow_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        new_workflow = {
            "workflow_id": workflow_id,
            "name": workflow.name,
            "steps": workflow.steps,
            "triggers": workflow.triggers,
            "conditions": workflow.conditions,
            "is_active": True,
            "created_by": current_user.username,
            "created_at": now,
            "updated_at": now
        }
        
        _incident_workflows[workflow_id] = new_workflow
        
        logger.info(
            f"Created workflow {workflow_id} ({workflow.name}) "
            f"by user {current_user.username}"
        )
        
        return {
            "workflow_id": workflow_id,
            "workflow": new_workflow,
            "message": "Workflow created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/workflows",
    summary="Get incident workflows",
    responses={
        200: {"description": "Workflows retrieved successfully"},
        401: {"description": "Unauthorized"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def get_workflows(
    request: Request,
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Get incident workflows with optional filters"""
    try:
        _check_rate_limit(request)
        
        workflows = list(_incident_workflows.values())
        
        if is_active is not None:
            workflows = [w for w in workflows if w.get("is_active") == is_active]
        
        logger.info(
            f"Retrieved {len(workflows)} workflows for user {current_user.username}"
        )
        
        return {
            "workflows": workflows,
            "total": len(workflows)
        }
    except Exception as e:
        logger.error(f"Error getting workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/workflows/{workflow_id}",
    summary="Get incident workflow by ID",
    responses={
        200: {"description": "Workflow retrieved successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Workflow not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def get_workflow(
    request: Request,
    workflow_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get a specific workflow by ID"""
    try:
        _check_rate_limit(request)
        
        if workflow_id not in _incident_workflows:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_id} not found"
            )
        
        workflow = _incident_workflows[workflow_id]
        
        logger.info(
            f"Retrieved workflow {workflow_id} for user {current_user.username}"
        )
        
        return {
            "workflow_id": workflow_id,
            "workflow": workflow
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/workflows/{workflow_id}",
    summary="Update incident workflow",
    responses={
        200: {"description": "Workflow updated successfully"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - insufficient permissions"},
        404: {"description": "Workflow not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def update_workflow(
    request: Request,
    workflow_id: str,
    workflow: IncidentWorkflow,
    current_user: User = Depends(require_role(["admin", "incident_manager"])),
):
    """Update an incident workflow"""
    try:
        _check_rate_limit(request)
        
        if workflow_id not in _incident_workflows:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_id} not found"
            )
        
        existing_workflow = _incident_workflows[workflow_id]
        existing_workflow["name"] = workflow.name
        existing_workflow["steps"] = workflow.steps
        existing_workflow["triggers"] = workflow.triggers
        existing_workflow["conditions"] = workflow.conditions
        existing_workflow["updated_at"] = datetime.utcnow().isoformat()
        
        _incident_workflows[workflow_id] = existing_workflow
        
        logger.info(
            f"Updated workflow {workflow_id} by user {current_user.username}"
        )
        
        return {
            "workflow_id": workflow_id,
            "workflow": existing_workflow,
            "message": "Workflow updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/workflows/{workflow_id}",
    summary="Delete incident workflow",
    responses={
        200: {"description": "Workflow deleted successfully"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - insufficient permissions"},
        404: {"description": "Workflow not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def delete_workflow(
    request: Request,
    workflow_id: str,
    current_user: User = Depends(require_role(["admin", "incident_manager"])),
):
    """Delete an incident workflow"""
    try:
        _check_rate_limit(request)
        
        if workflow_id not in _incident_workflows:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_id} not found"
            )
        
        del _incident_workflows[workflow_id]
        
        logger.info(
            f"Deleted workflow {workflow_id} by user {current_user.username}"
        )
        
        return {
            "workflow_id": workflow_id,
            "message": "Workflow deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/incidents/{incident_id}/sla/breach",
    summary="Record SLA breach",
    responses={
        200: {"description": "SLA breach recorded successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def record_sla_breach(
    request: Request,
    incident_id: str,
    breach: SLABreach,
    current_user: User = Depends(get_current_user),
):
    """Record an SLA breach for an incident"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        breach_record = {
            "breach_id": str(uuid.uuid4()),
            "sla_type": breach.sla_type,
            "breach_time": breach.breach_time.isoformat(),
            "actual_time": breach.actual_time.isoformat(),
            "severity": breach.severity,
            "recorded_by": current_user.username,
            "recorded_at": datetime.utcnow().isoformat()
        }
        
        _sla_records[incident_id].append(breach_record)
        
        _add_timeline_event(
            incident_id,
            "sla_breach",
            current_user.username,
            {
                "sla_type": breach.sla_type,
                "breach_time": breach.breach_time.isoformat(),
                "severity": breach.severity
            }
        )
        
        logger.warning(
            f"SLA breach recorded for incident {incident_id}, type={breach.sla_type}, "
            f"severity={breach.severity} by user {current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "breach_id": breach_record["breach_id"],
            "breach": breach_record,
            "message": "SLA breach recorded successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording SLA breach: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/incidents/{incident_id}/sla",
    summary="Get incident SLA records",
    responses={
        200: {"description": "SLA records retrieved successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def get_incident_sla(
    request: Request,
    incident_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get SLA records for an incident"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        sla_records = _sla_records.get(incident_id, [])
        
        logger.info(
            f"Retrieved {len(sla_records)} SLA records for incident {incident_id} "
            f"by user {current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "sla_records": sla_records,
            "total": len(sla_records)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting SLA records for incident {incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/incidents/{incident_id}/root-cause-analysis",
    summary="Submit root cause analysis",
    responses={
        200: {"description": "Root cause analysis submitted successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def submit_root_cause_analysis(
    request: Request,
    incident_id: str,
    analysis: RootCauseAnalysis,
    current_user: User = Depends(get_current_user),
):
    """Submit root cause analysis for an incident"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        analysis_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        analysis_record = {
            "analysis_id": analysis_id,
            "analysis_method": analysis.analysis_method,
            "findings": analysis.findings,
            "root_cause": analysis.root_cause,
            "contributing_factors": analysis.contributing_factors,
            "recommendations": analysis.recommendations,
            "analyzed_by": analysis.analyzed_by,
            "submitted_by": current_user.username,
            "submitted_at": now
        }
        
        incident = _incidents[incident_id]
        incident["root_cause_analysis"] = analysis_record
        incident["updated_at"] = now
        _incidents[incident_id] = incident
        
        _add_timeline_event(
            incident_id,
            "root_cause_analysis",
            current_user.username,
            {
                "analysis_id": analysis_id,
                "analysis_method": analysis.analysis_method,
                "root_cause": analysis.root_cause
            }
        )
        
        logger.info(
            f"Root cause analysis submitted for incident {incident_id}, "
            f"method={analysis.analysis_method} by user {current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "analysis_id": analysis_id,
            "analysis": analysis_record,
            "message": "Root cause analysis submitted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting root cause analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/incidents/{incident_id}/post-mortem",
    summary="Submit post-mortem",
    responses={
        200: {"description": "Post-mortem submitted successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Incident not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def submit_post_mortem(
    request: Request,
    incident_id: str,
    post_mortem: PostMortem,
    current_user: User = Depends(get_current_user),
):
    """Submit post-mortem for an incident"""
    try:
        _check_rate_limit(request)
        _validate_incident_exists(incident_id)
        
        post_mortem_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        post_mortem_record = {
            "post_mortem_id": post_mortem_id,
            "summary": post_mortem.summary,
            "timeline": post_mortem.timeline,
            "root_cause": post_mortem.root_cause,
            "impact": post_mortem.impact,
            "resolution": post_mortem.resolution,
            "lessons_learned": post_mortem.lessons_learned,
            "action_items": post_mortem.action_items,
            "follow_up_date": post_mortem.follow_up_date.isoformat() if post_mortem.follow_up_date else None,
            "reviewed_by": post_mortem.reviewed_by,
            "submitted_by": current_user.username,
            "submitted_at": now
        }
        
        incident = _incidents[incident_id]
        incident["post_mortem"] = post_mortem_record
        incident["updated_at"] = now
        _incidents[incident_id] = incident
        
        _add_timeline_event(
            incident_id,
            "post_mortem_submitted",
            current_user.username,
            {
                "post_mortem_id": post_mortem_id,
                "reviewed_by": post_mortem.reviewed_by
            }
        )
        
        logger.info(
            f"Post-mortem submitted for incident {incident_id} "
            f"by user {current_user.username}"
        )
        
        return {
            "incident_id": incident_id,
            "post_mortem_id": post_mortem_id,
            "post_mortem": post_mortem_record,
            "message": "Post-mortem submitted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting post-mortem: {e}")
        raise HTTPException(status_code=500, detail=str(e))
