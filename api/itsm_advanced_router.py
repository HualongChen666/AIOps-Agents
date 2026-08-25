# -*- coding: utf-8 -*-
"""
ITSM Advanced API Router
Provides comprehensive API endpoints for ITSM incidents, problems, changes, service catalog, SLA, and knowledge base
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from loguru import logger

router = APIRouter(prefix="/api/v1/itsm", tags=["ITSM Advanced"])


# Pydantic Models
class ITSMIncident(BaseModel):
    """ITSM incident model"""
    incident_id: str
    title: str
    description: str
    priority: str
    status: str
    assigned_to: Optional[str] = None
    category: str
    impact: str
    urgency: str
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None
    resolution_notes: Optional[str] = None


class ITSMIncidentCreate(BaseModel):
    """ITSM incident creation model"""
    title: str
    description: str
    priority: str = Field(default="medium", description="Priority: low, medium, high, critical")
    category: str
    impact: str = Field(default="medium", description="Impact: low, medium, high")
    urgency: str = Field(default="medium", description="Urgency: low, medium, high")
    assigned_to: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Database connection timeout",
                "description": "Application is experiencing database connection timeouts",
                "priority": "high",
                "category": "database",
                "impact": "high",
                "urgency": "high",
                "assigned_to": "john.doe"
            }
        }
    }


class ITSMIncidentUpdate(BaseModel):
    """ITSM incident update model"""
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    category: Optional[str] = None
    impact: Optional[str] = None
    urgency: Optional[str] = None
    resolution_notes: Optional[str] = None


class ITSMProblem(BaseModel):
    """ITSM problem model"""
    problem_id: str
    title: str
    description: str
    status: str
    priority: str
    root_cause: Optional[str] = None
    related_incidents: List[str] = []
    workarounds: List[str] = []
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None


class ITSMProblemCreate(BaseModel):
    """ITSM problem creation model"""
    title: str
    description: str
    priority: str = Field(default="medium", description="Priority: low, medium, high, critical")
    related_incidents: Optional[List[str]] = None


class ITSMChange(BaseModel):
    """ITSM change model"""
    change_id: str
    title: str
    description: str
    change_type: str
    status: str
    priority: str
    risk_level: str
    planned_start: str
    planned_end: str
    requested_by: str
    approved_by: Optional[str] = None
    created_at: str
    updated_at: str
    implemented_at: Optional[str] = None


class ITSMChangeCreate(BaseModel):
    """ITSM change creation model"""
    title: str
    description: str
    change_type: str = Field(default="normal", description="Type: standard, normal, emergency")
    priority: str = Field(default="medium", description="Priority: low, medium, high, critical")
    risk_level: str = Field(default="medium", description="Risk: low, medium, high")
    planned_start: str
    planned_end: str
    requested_by: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Upgrade database to version 15",
                "description": "Upgrade PostgreSQL from version 14 to 15",
                "change_type": "normal",
                "priority": "high",
                "risk_level": "high",
                "planned_start": "2026-07-10T02:00:00Z",
                "planned_end": "2026-07-10T04:00:00Z",
                "requested_by": "admin"
            }
        }
    }


class ServiceCatalogItem(BaseModel):
    """Service catalog item model"""
    service_id: str
    name: str
    description: str
    category: str
    availability: str
    sla_target: str
    owner: str
    status: str
    created_at: str
    updated_at: str


class SLA(BaseModel):
    """SLA model"""
    sla_id: str
    name: str
    description: str
    service_id: str
    response_time_target: str
    resolution_time_target: str
    availability_target: float
    current_performance: float
    status: str
    created_at: str
    updated_at: str


class KnowledgeBaseArticle(BaseModel):
    """Knowledge base article model"""
    article_id: str
    title: str
    content: str
    category: str
    tags: List[str]
    author: str
    status: str
    created_at: str
    updated_at: str
    views: int = 0
    helpful_count: int = 0


class KnowledgeBaseArticleCreate(BaseModel):
    """Knowledge base article creation model"""
    title: str
    content: str
    category: str
    tags: Optional[List[str]] = None
    author: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "How to reset database connection pool",
                "content": "Step-by-step guide to reset database connection pool...",
                "category": "database",
                "tags": ["database", "troubleshooting", "connection"],
                "author": "support.team"
            }
        }
    }


# In-memory storage (in production, use a real database)
_incidents: Dict[str, Dict[str, Any]] = {}
_problems: Dict[str, Dict[str, Any]] = {}
_changes: Dict[str, Dict[str, Any]] = {}
_service_catalog: Dict[str, Dict[str, Any]] = {}
_slas: Dict[str, Dict[str, Any]] = {}
_knowledge_base: Dict[str, Dict[str, Any]] = {}


def _initialize_default_data():
    """Initialize default ITSM data"""
    if not _incidents:
        default_incidents = [
            {
                "incident_id": str(uuid4()),
                "title": "Web server high CPU usage",
                "description": "Web server CPU usage is above 90%",
                "priority": "high",
                "status": "open",
                "assigned_to": "john.doe",
                "category": "infrastructure",
                "impact": "high",
                "urgency": "high",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "resolved_at": None,
                "resolution_notes": None
            },
            {
                "incident_id": str(uuid4()),
                "title": "Database slow query performance",
                "description": "Database queries are taking longer than expected",
                "priority": "medium",
                "status": "in_progress",
                "assigned_to": "jane.smith",
                "category": "database",
                "impact": "medium",
                "urgency": "medium",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "resolved_at": None,
                "resolution_notes": None
            }
        ]
        for incident in default_incidents:
            _incidents[incident["incident_id"]] = incident
    
    if not _service_catalog:
        default_services = [
            {
                "service_id": str(uuid4()),
                "name": "Web Application",
                "description": "Main web application service",
                "category": "application",
                "availability": "99.9%",
                "sla_target": "99.9%",
                "owner": "platform.team",
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            },
            {
                "service_id": str(uuid4()),
                "name": "Database Service",
                "description": "Managed database service",
                "category": "database",
                "availability": "99.95%",
                "sla_target": "99.95%",
                "owner": "database.team",
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        ]
        for service in default_services:
            _service_catalog[service["service_id"]] = service
    
    if not _slas:
        default_slas = [
            {
                "sla_id": str(uuid4()),
                "name": "Critical Incident SLA",
                "description": "SLA for critical incidents",
                "service_id": list(_service_catalog.keys())[0] if _service_catalog else str(uuid4()),
                "response_time_target": "15 minutes",
                "resolution_time_target": "4 hours",
                "availability_target": 99.9,
                "current_performance": 99.8,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        ]
        for sla in default_slas:
            _slas[sla["sla_id"]] = sla
    
    if not _knowledge_base:
        default_articles = [
            {
                "article_id": str(uuid4()),
                "title": "Troubleshooting high CPU usage",
                "content": "Steps to troubleshoot high CPU usage on servers...",
                "category": "infrastructure",
                "tags": ["cpu", "troubleshooting", "performance"],
                "author": "support.team",
                "status": "published",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "views": 150,
                "helpful_count": 45
            }
        ]
        for article in default_articles:
            _knowledge_base[article["article_id"]] = article


# Initialize default data
_initialize_default_data()


@router.get(
    "/incidents",
    response_model=List[ITSMIncident],
    summary="Get ITSM incidents",
    responses={
        200: {"description": "List of incidents"},
        500: {"description": "Internal server error"}
    }
)
async def get_incidents(
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    priority_filter: Optional[str] = Query(None, description="Filter by priority"),
    category_filter: Optional[str] = Query(None, description="Filter by category")
):
    """
    Get list of ITSM incidents
    
    Args:
        limit: Maximum number of incidents to return
        status_filter: Optional status filter (open, in_progress, resolved, closed)
        priority_filter: Optional priority filter (low, medium, high, critical)
        category_filter: Optional category filter
    
    Returns:
        List of ITSM incidents
    """
    try:
        incidents = list(_incidents.values())
        
        if status_filter:
            incidents = [inc for inc in incidents if inc.get("status") == status_filter]
        if priority_filter:
            incidents = [inc for inc in incidents if inc.get("priority") == priority_filter]
        if category_filter:
            incidents = [inc for inc in incidents if inc.get("category") == category_filter]
        
        return [
            ITSMIncident(**inc)
            for inc in sorted(incidents, key=lambda x: x["created_at"], reverse=True)[:limit]
        ]
    except Exception as e:
        logger.error(f"Error getting incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/incidents",
    response_model=ITSMIncident,
    summary="Create ITSM incident",
    responses={
        200: {"description": "Incident created successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"}
    }
)
async def create_incident(request: ITSMIncidentCreate):
    """
    Create a new ITSM incident
    
    Args:
        request: Incident creation request
    
    Returns:
        Created incident details
    """
    try:
        incident_id = str(uuid4())
        now = datetime.utcnow().isoformat()
        
        incident = {
            "incident_id": incident_id,
            "title": request.title,
            "description": request.description,
            "priority": request.priority,
            "status": "open",
            "assigned_to": request.assigned_to,
            "category": request.category,
            "impact": request.impact,
            "urgency": request.urgency,
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
            "resolution_notes": None
        }
        
        _incidents[incident_id] = incident
        logger.info(f"Created incident {request.title} with ID {incident_id}")
        
        return ITSMIncident(**incident)
    except Exception as e:
        logger.error(f"Error creating incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/incidents/{incident_id}",
    response_model=ITSMIncident,
    summary="Get ITSM incident by ID",
    responses={
        200: {"description": "Incident details"},
        404: {"description": "Incident not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_incident(incident_id: str):
    """
    Get a specific ITSM incident by ID
    
    Args:
        incident_id: Incident ID
    
    Returns:
        Incident details
    """
    try:
        incident = _incidents.get(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
        
        return ITSMIncident(**incident)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/incidents/{incident_id}",
    response_model=ITSMIncident,
    summary="Update ITSM incident",
    responses={
        200: {"description": "Incident updated successfully"},
        404: {"description": "Incident not found"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"}
    }
)
async def update_incident(incident_id: str, request: ITSMIncidentUpdate):
    """
    Update an ITSM incident
    
    Args:
        incident_id: Incident ID
        request: Update request
    
    Returns:
        Updated incident details
    """
    try:
        incident = _incidents.get(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
        
        # Update fields
        if request.title is not None:
            incident["title"] = request.title
        if request.description is not None:
            incident["description"] = request.description
        if request.priority is not None:
            incident["priority"] = request.priority
        if request.status is not None:
            incident["status"] = request.status
            # Set resolved_at if status is resolved or closed
            if request.status in ["resolved", "closed"] and not incident.get("resolved_at"):
                incident["resolved_at"] = datetime.utcnow().isoformat()
        if request.assigned_to is not None:
            incident["assigned_to"] = request.assigned_to
        if request.category is not None:
            incident["category"] = request.category
        if request.impact is not None:
            incident["impact"] = request.impact
        if request.urgency is not None:
            incident["urgency"] = request.urgency
        if request.resolution_notes is not None:
            incident["resolution_notes"] = request.resolution_notes
        
        incident["updated_at"] = datetime.utcnow().isoformat()
        _incidents[incident_id] = incident
        
        logger.info(f"Updated incident {incident_id}")
        
        return ITSMIncident(**incident)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/incidents/{incident_id}",
    summary="Delete ITSM incident",
    responses={
        200: {"description": "Incident deleted successfully"},
        404: {"description": "Incident not found"},
        500: {"description": "Internal server error"}
    }
)
async def delete_incident(incident_id: str):
    """
    Delete an ITSM incident
    
    Args:
        incident_id: Incident ID
    
    Returns:
        Deletion confirmation
    """
    try:
        incident = _incidents.get(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
        
        del _incidents[incident_id]
        logger.info(f"Deleted incident {incident_id}")
        
        return {"message": f"Incident {incident_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/problems",
    response_model=List[ITSMProblem],
    summary="Get ITSM problems",
    responses={
        200: {"description": "List of problems"},
        500: {"description": "Internal server error"}
    }
)
async def get_problems(
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = Query(None, description="Filter by status")
):
    """
    Get list of ITSM problems
    
    Args:
        limit: Maximum number of problems to return
        status_filter: Optional status filter (open, in_progress, resolved, closed)
    
    Returns:
        List of ITSM problems
    """
    try:
        problems = list(_problems.values())
        
        if status_filter:
            problems = [prob for prob in problems if prob.get("status") == status_filter]
        
        # Add default problems if empty
        if not problems:
            default_problems = [
                {
                    "problem_id": str(uuid4()),
                    "title": "Recurring database connection timeouts",
                    "description": "Database connections are timing out intermittently",
                    "status": "open",
                    "priority": "high",
                    "root_cause": None,
                    "related_incidents": [],
                    "workarounds": ["Restart application server"],
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "resolved_at": None
                }
            ]
            for problem in default_problems:
                _problems[problem["problem_id"]] = problem
            problems = default_problems
        
        return [
            ITSMProblem(**prob)
            for prob in sorted(problems, key=lambda x: x["created_at"], reverse=True)[:limit]
        ]
    except Exception as e:
        logger.error(f"Error getting problems: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/problems",
    response_model=ITSMProblem,
    summary="Create ITSM problem",
    responses={
        200: {"description": "Problem created successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"}
    }
)
async def create_problem(request: ITSMProblemCreate):
    """
    Create a new ITSM problem
    
    Args:
        request: Problem creation request
    
    Returns:
        Created problem details
    """
    try:
        problem_id = str(uuid4())
        now = datetime.utcnow().isoformat()
        
        problem = {
            "problem_id": problem_id,
            "title": request.title,
            "description": request.description,
            "status": "open",
            "priority": request.priority,
            "root_cause": None,
            "related_incidents": request.related_incidents or [],
            "workarounds": [],
            "created_at": now,
            "updated_at": now,
            "resolved_at": None
        }
        
        _problems[problem_id] = problem
        logger.info(f"Created problem {request.title} with ID {problem_id}")
        
        return ITSMProblem(**problem)
    except Exception as e:
        logger.error(f"Error creating problem: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/changes",
    response_model=List[ITSMChange],
    summary="Get ITSM changes",
    responses={
        200: {"description": "List of changes"},
        500: {"description": "Internal server error"}
    }
)
async def get_changes(
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = Query(None, description="Filter by status")
):
    """
    Get list of ITSM changes
    
    Args:
        limit: Maximum number of changes to return
        status_filter: Optional status filter (pending, approved, in_progress, completed, cancelled)
    
    Returns:
        List of ITSM changes
    """
    try:
        changes = list(_changes.values())
        
        if status_filter:
            changes = [ch for ch in changes if ch.get("status") == status_filter]
        
        # Add default changes if empty
        if not changes:
            default_changes = [
                {
                    "change_id": str(uuid4()),
                    "title": "Upgrade web server software",
                    "description": "Upgrade Nginx to version 1.25",
                    "change_type": "normal",
                    "status": "pending",
                    "priority": "medium",
                    "risk_level": "low",
                    "planned_start": datetime.utcnow().isoformat(),
                    "planned_end": datetime.utcnow().isoformat(),
                    "requested_by": "admin",
                    "approved_by": None,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "implemented_at": None
                }
            ]
            for change in default_changes:
                _changes[change["change_id"]] = change
            changes = default_changes
        
        return [
            ITSMChange(**ch)
            for ch in sorted(changes, key=lambda x: x["created_at"], reverse=True)[:limit]
        ]
    except Exception as e:
        logger.error(f"Error getting changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/changes",
    response_model=ITSMChange,
    summary="Create ITSM change",
    responses={
        200: {"description": "Change created successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"}
    }
)
async def create_change(request: ITSMChangeCreate):
    """
    Create a new ITSM change
    
    Args:
        request: Change creation request
    
    Returns:
        Created change details
    """
    try:
        change_id = str(uuid4())
        now = datetime.utcnow().isoformat()
        
        change = {
            "change_id": change_id,
            "title": request.title,
            "description": request.description,
            "change_type": request.change_type,
            "status": "pending",
            "priority": request.priority,
            "risk_level": request.risk_level,
            "planned_start": request.planned_start,
            "planned_end": request.planned_end,
            "requested_by": request.requested_by,
            "approved_by": None,
            "created_at": now,
            "updated_at": now,
            "implemented_at": None
        }
        
        _changes[change_id] = change
        logger.info(f"Created change {request.title} with ID {change_id}")
        
        return ITSMChange(**change)
    except Exception as e:
        logger.error(f"Error creating change: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/service-catalog",
    response_model=List[ServiceCatalogItem],
    summary="Get service catalog",
    responses={
        200: {"description": "Service catalog"},
        500: {"description": "Internal server error"}
    }
)
async def get_service_catalog(
    category_filter: Optional[str] = Query(None, description="Filter by category")
):
    """
    Get service catalog
    
    Args:
        category_filter: Optional category filter
    
    Returns:
        Service catalog items
    """
    try:
        services = list(_service_catalog.values())
        
        if category_filter:
            services = [svc for svc in services if svc.get("category") == category_filter]
        
        return [ServiceCatalogItem(**svc) for svc in services]
    except Exception as e:
        logger.error(f"Error getting service catalog: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/sla",
    response_model=List[SLA],
    summary="Get SLAs",
    responses={
        200: {"description": "List of SLAs"},
        500: {"description": "Internal server error"}
    }
)
async def get_slas(
    service_id: Optional[str] = Query(None, description="Filter by service ID")
):
    """
    Get SLAs
    
    Args:
        service_id: Optional service ID filter
    
    Returns:
        List of SLAs
    """
    try:
        slas = list(_slas.values())
        
        if service_id:
            slas = [sla for sla in slas if sla.get("service_id") == service_id]
        
        return [SLA(**sla) for sla in slas]
    except Exception as e:
        logger.error(f"Error getting SLAs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/knowledge-base",
    response_model=List[KnowledgeBaseArticle],
    summary="Get knowledge base articles",
    responses={
        200: {"description": "Knowledge base articles"},
        500: {"description": "Internal server error"}
    }
)
async def get_knowledge_base(
    category_filter: Optional[str] = Query(None, description="Filter by category"),
    tag_filter: Optional[str] = Query(None, description="Filter by tag"),
    search: Optional[str] = Query(None, description="Search in title and content")
):
    """
    Get knowledge base articles
    
    Args:
        category_filter: Optional category filter
        tag_filter: Optional tag filter
        search: Optional search term
    
    Returns:
        Knowledge base articles
    """
    try:
        articles = list(_knowledge_base.values())
        
        if category_filter:
            articles = [art for art in articles if art.get("category") == category_filter]
        if tag_filter:
            articles = [art for art in articles if tag_filter in art.get("tags", [])]
        if search:
            search_lower = search.lower()
            articles = [
                art for art in articles
                if search_lower in art.get("title", "").lower() or search_lower in art.get("content", "").lower()
            ]
        
        return [KnowledgeBaseArticle(**art) for art in articles]
    except Exception as e:
        logger.error(f"Error getting knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/knowledge-base",
    response_model=KnowledgeBaseArticle,
    summary="Create knowledge base article",
    responses={
        200: {"description": "Article created successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"}
    }
)
async def create_knowledge_base_article(request: KnowledgeBaseArticleCreate):
    """
    Create a new knowledge base article
    
    Args:
        request: Article creation request
    
    Returns:
        Created article details
    """
    try:
        article_id = str(uuid4())
        now = datetime.utcnow().isoformat()
        
        article = {
            "article_id": article_id,
            "title": request.title,
            "content": request.content,
            "category": request.category,
            "tags": request.tags or [],
            "author": request.author,
            "status": "draft",
            "created_at": now,
            "updated_at": now,
            "views": 0,
            "helpful_count": 0
        }
        
        _knowledge_base[article_id] = article
        logger.info(f"Created knowledge base article {request.title} with ID {article_id}")
        
        return KnowledgeBaseArticle(**article)
    except Exception as e:
        logger.error(f"Error creating knowledge base article: {e}")
        raise HTTPException(status_code=500, detail=str(e))
