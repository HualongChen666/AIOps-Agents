# -*- coding: utf-8 -*-
"""
Advanced Tracing API Router

Implements advanced tracing management endpoints including:
- Trace management (list, get, search)
- Span management
- Service and operation tracking
- Analytics and metrics
- Search functionality

All endpoints integrate with core business logic and support
fallback to synthetic traces when no external backend is configured.
"""

import hashlib
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request
from loguru import logger
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/tracing", tags=["Advanced Tracing"])

# ============================================================
# Path Parameter Validation Functions
# ============================================================


def validate_path_param(param_value: str, param_name: str = "parameter") -> str:
    """
    Validate path parameters to prevent path traversal and injection attacks.

    Args:
        param_value: The parameter value to validate
        param_name: Name of the parameter for error messages

    Returns:
        The validated parameter value

    Raises:
        HTTPException: If validation fails
    """
    if not param_value:
        raise HTTPException(status_code=400, detail=f"{param_name} cannot be empty")

    # Check for path traversal patterns
    if ".." in param_value or "//" in param_value:
        raise HTTPException(
            status_code=400, detail=f"Invalid {param_name}: path traversal detected"
        )

    # Check for null bytes
    if "\x00" in param_value:
        raise HTTPException(status_code=400, detail=f"Invalid {param_name}: null byte detected")

    # Check for suspicious characters (basic sanitization)
    # Allow alphanumeric, hyphens, underscores, and common ID patterns
    if not re.match(r"^[a-zA-Z0-9\-_:.]+$", param_value):
        raise HTTPException(
            status_code=400, detail=f"Invalid {param_name}: contains invalid characters"
        )

    return param_value


# ============================================================
# In-memory data stores (in production, use database)
# ============================================================
_traces: Dict[str, Dict[str, Any]] = {}
_spans: Dict[str, Dict[str, Any]] = {}
_services: Dict[str, Dict[str, Any]] = {}
_operations: Dict[str, Dict[str, Any]] = {}
_analytics: Dict[str, Dict[str, Any]] = {}

# ============================================================
# Pydantic Models for Data Validation
# ============================================================


class TraceCreate(BaseModel):
    """Model for creating a trace"""

    trace_id: str = Field(..., min_length=1, max_length=100, description="Trace unique identifier")
    root_service: str = Field(..., description="Root service name")
    operation: str = Field(..., description="Operation name")
    duration_ms: float = Field(..., ge=0, description="Trace duration in milliseconds")
    status: str = Field(default="ok", description="Trace status: ok, error")
    tags: Dict[str, Any] = Field(default_factory=dict, description="Trace tags")


class TraceUpdate(BaseModel):
    """Model for updating a trace"""

    root_service: Optional[str] = None
    operation: Optional[str] = None
    duration_ms: Optional[float] = Field(None, ge=0)
    status: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None


class SpanCreate(BaseModel):
    """Model for creating a span"""

    span_id: str = Field(..., min_length=1, max_length=100, description="Span unique identifier")
    trace_id: str = Field(..., description="Parent trace ID")
    parent_id: Optional[str] = Field(None, description="Parent span ID")
    service: str = Field(..., description="Service name")
    operation: str = Field(..., description="Operation name")
    start_time: str = Field(..., description="Start time in ISO format")
    duration_ms: float = Field(..., ge=0, description="Span duration in milliseconds")
    status: str = Field(default="ok", description="Span status: ok, error")
    tags: Dict[str, Any] = Field(default_factory=dict, description="Span tags")


class ServiceCreate(BaseModel):
    """Model for creating a service"""

    name: str = Field(..., min_length=1, max_length=100, description="Service name")
    type: str = Field(default="application", description="Service type")
    version: str = Field(default="1.0.0", description="Service version")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Service metadata")


class OperationCreate(BaseModel):
    """Model for creating an operation"""

    name: str = Field(..., min_length=1, max_length=200, description="Operation name")
    service: str = Field(..., description="Service name")
    type: str = Field(default="http", description="Operation type: http, rpc, db, cache")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Operation metadata")


class AnalyticsCreate(BaseModel):
    """Model for creating analytics data"""

    service: str = Field(..., description="Service name")
    operation: Optional[str] = Field(None, description="Operation name")
    metric_type: str = Field(..., description="Metric type: latency, error_rate, throughput")
    value: float = Field(..., description="Metric value")
    timestamp: str = Field(..., description="Timestamp in ISO format")


class SearchRequest(BaseModel):
    """Model for trace search request"""

    query: str = Field(..., description="Search query")
    service_name: Optional[str] = Field(None, description="Filter by service name")
    operation_name: Optional[str] = Field(None, description="Filter by operation name")
    min_duration: Optional[float] = Field(None, ge=0, description="Minimum duration in ms")
    max_duration: Optional[float] = Field(None, ge=0, description="Maximum duration in ms")
    status: Optional[str] = Field(None, description="Filter by status")
    start_time: Optional[str] = Field(None, description="Start time in ISO format")
    end_time: Optional[str] = Field(None, description="End time in ISO format")
    limit: int = Field(default=50, ge=1, le=500, description="Maximum results")


# ============================================================
# Helper Functions
# ============================================================


def _generate_id() -> str:
    """Generate unique ID"""
    return str(uuid.uuid4())


def _get_current_timestamp() -> str:
    """Get current ISO timestamp"""
    return datetime.utcnow().isoformat()


def _services() -> List[str]:
    """Get list of available services"""
    from config import LINUX_HOSTS

    default = ["aiops-agent"]
    if LINUX_HOSTS:
        return [f"host-{i}" for i in range(min(len(LINUX_HOSTS), 5))] or default
    return default


def _generate_synthetic_trace(trace_id: str, seed: Optional[int] = None) -> Dict[str, Any]:
    """Generate a deterministic synthetic trace from the trace_id."""
    digest = int(hashlib.sha256(trace_id.encode()).hexdigest(), 16)
    rand = digest % 1000
    services = _services()
    span_count = 3 + (rand % 8)
    base_time = time.time() - (rand % 3600)

    spans: List[Dict[str, Any]] = []
    parent_id = ""
    for i in range(span_count):
        service = services[(rand + i) % len(services)]
        duration_ms = 10 + (rand * (i + 1)) % 450
        span_id = f"{trace_id[:16]}-{i:04x}"
        spans.append(
            {
                "span_id": span_id,
                "parent_id": parent_id if parent_id else None,
                "service": service,
                "operation": (
                    f"/api/v1/{service.replace('host-', '')}/"
                    f"{'health' if i % 2 == 0 else 'process'}"
                ),
                "start_time": datetime.fromtimestamp(
                    base_time + i * 0.01, tz=timezone.utc
                ).isoformat(),
                "duration_ms": duration_ms,
                "status": "error" if (rand + i) % 13 == 0 else "ok",
                "tags": {"synthetic": True, "index": i},
            }
        )
        parent_id = span_id

    return {
        "trace_id": trace_id,
        "spans": spans,
        "services": sorted({s["service"] for s in spans}),
        "total_duration_ms": sum(s["duration_ms"] for s in spans),
        "error_count": sum(1 for s in spans if s["status"] == "error"),
    }


def _recent_synthetic_traces(limit: int) -> List[Dict[str, Any]]:
    """Generate recent synthetic traces"""
    now = int(time.time())
    traces = []
    for i in range(limit):
        trace_id = hashlib.sha256(f"synthetic-{now - i * 60}".encode()).hexdigest()[:16]
        trace = _generate_synthetic_trace(trace_id, seed=i)
        traces.append(
            {
                "trace_id": trace_id,
                "root_service": trace["services"][0] if trace["services"] else "aiops-agent",
                "operation": "/api/v1/status",
                "start_time": trace["spans"][0]["start_time"],
                "duration_ms": trace["total_duration_ms"],
                "error_count": trace["error_count"],
                "status": "error" if trace["error_count"] > 0 else "ok",
            }
        )
    return traces


# ============================================================
# 1. Trace Management Endpoints
# ============================================================


@router.get("/traces", summary="List traces")
async def list_traces(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    operation: Optional[str] = Query(None, description="Filter by operation"),
    status: Optional[str] = Query(None, description="Filter by status"),
    min_duration: Optional[float] = Query(None, ge=0, description="Minimum duration in ms"),
    max_duration: Optional[float] = Query(None, ge=0, description="Maximum duration in ms"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
) -> Dict[str, Any]:
    """
    List traces with optional filters
    """
    logger.info("Fetching traces list")
    try:
        # Try to get traces from in-memory store
        items = list(_traces.values())

        if not items:
            # Fallback to synthetic traces
            items = _recent_synthetic_traces(limit)

        # Apply filters
        if service_name:
            items = [item for item in items if item.get("root_service") == service_name]
        if operation:
            items = [item for item in items if item.get("operation") == operation]
        if status:
            items = [item for item in items if item.get("status") == status]
        if min_duration is not None:
            items = [item for item in items if item.get("duration_ms", 0) >= min_duration]
        if max_duration is not None:
            items = [item for item in items if item.get("duration_ms", 0) <= max_duration]

        # Sort by start time descending
        items.sort(key=lambda x: x.get("start_time", ""), reverse=True)

        # Apply limit
        items = items[:limit]

        return {
            "items": items,
            "total": len(items),
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Failed to fetch traces: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch traces: {str(e)}")


@router.post("/traces", summary="Create trace")
async def create_trace(trace: TraceCreate, request: Request) -> Dict[str, Any]:
    """
    Create a new trace
    """
    logger.info(f"Creating trace: {trace.trace_id}")
    try:
        if trace.trace_id in _traces:
            raise HTTPException(status_code=409, detail="Trace ID already exists")

        operator_ip = request.client.host if request.client else "unknown"

        new_trace = {
            "trace_id": trace.trace_id,
            "root_service": trace.root_service,
            "operation": trace.operation,
            "duration_ms": trace.duration_ms,
            "status": trace.status,
            "tags": trace.tags,
            "start_time": _get_current_timestamp(),
            "created_at": _get_current_timestamp(),
            "created_by": operator_ip,
            "updated_at": _get_current_timestamp(),
        }

        _traces[trace.trace_id] = new_trace
        logger.info(f"Trace created: {trace.trace_id}")
        return new_trace
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create trace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create trace: {str(e)}")


@router.get("/traces/{trace_id}", summary="Get trace by ID")
async def get_trace(trace_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific trace by ID with full details
    """
    # Validate path parameter
    trace_id = validate_path_param(trace_id, "trace_id")

    logger.info(f"Fetching trace: {trace_id}")
    try:
        # Try in-memory store first
        if trace_id in _traces:
            trace = _traces[trace_id]
            # Add spans if available
            trace_spans = [s for s in _spans.values() if s.get("trace_id") == trace_id]
            trace["spans"] = trace_spans
            trace["services"] = sorted({s.get("service") for s in trace_spans})
            trace["total_duration_ms"] = trace.get("duration_ms", 0)
            trace["error_count"] = sum(1 for s in trace_spans if s.get("status") == "error")
            return trace

        # Fallback to synthetic trace
        synthetic_trace = _generate_synthetic_trace(trace_id)
        return {
            "trace_id": trace_id,
            "spans": synthetic_trace["spans"],
            "services": synthetic_trace["services"],
            "total_duration_ms": synthetic_trace["total_duration_ms"],
            "error_count": synthetic_trace["error_count"],
            "source": "synthetic",
        }
    except Exception as e:
        logger.error(f"Failed to fetch trace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch trace: {str(e)}")


@router.patch("/traces/{trace_id}", summary="Update trace")
async def update_trace(
    trace_id: str, trace_update: TraceUpdate, request: Request
) -> Dict[str, Any]:
    """
    Update an existing trace
    """
    logger.info(f"Updating trace: {trace_id}")
    try:
        if trace_id not in _traces:
            raise HTTPException(status_code=404, detail="Trace not found")

        operator_ip = request.client.host if request.client else "unknown"
        existing = _traces[trace_id]

        # Update fields
        update_data = trace_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            existing[key] = value

        existing["updated_at"] = _get_current_timestamp()
        existing["updated_by"] = operator_ip

        logger.info(f"Trace updated: {trace_id}")
        return existing
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update trace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update trace: {str(e)}")


@router.delete("/traces/{trace_id}", summary="Delete trace")
async def delete_trace(trace_id: str) -> Dict[str, Any]:
    """
    Delete a trace
    """
    logger.info(f"Deleting trace: {trace_id}")
    try:
        if trace_id not in _traces:
            raise HTTPException(status_code=404, detail="Trace not found")

        del _traces[trace_id]
        # Also delete associated spans
        spans_to_delete = [
            span_id for span_id, span in _spans.items() if span.get("trace_id") == trace_id
        ]
        for span_id in spans_to_delete:
            del _spans[span_id]

        logger.info(f"Trace deleted: {trace_id}")
        return {"message": "Trace deleted successfully", "id": trace_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete trace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete trace: {str(e)}")


# ============================================================
# 2. Span Management Endpoints
# ============================================================


@router.get("/spans", summary="List spans")
async def list_spans(
    trace_id: Optional[str] = Query(None, description="Filter by trace ID"),
    service: Optional[str] = Query(None, description="Filter by service"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
) -> Dict[str, Any]:
    """
    List spans with optional filters
    """
    logger.info("Fetching spans list")
    try:
        items = list(_spans.values())

        if trace_id:
            items = [item for item in items if item.get("trace_id") == trace_id]
        if service:
            items = [item for item in items if item.get("service") == service]
        if status:
            items = [item for item in items if item.get("status") == status]

        # Sort by start time descending
        items.sort(key=lambda x: x.get("start_time", ""), reverse=True)

        # Apply limit
        items = items[:limit]

        return {
            "items": items,
            "total": len(items),
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Failed to fetch spans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch spans: {str(e)}")


@router.post("/spans", summary="Create span")
async def create_span(span: SpanCreate, request: Request) -> Dict[str, Any]:
    """
    Create a new span
    """
    logger.info(f"Creating span: {span.span_id}")
    try:
        if span.span_id in _spans:
            raise HTTPException(status_code=409, detail="Span ID already exists")

        # Validate trace exists
        if span.trace_id not in _traces:
            logger.warning(f"Trace {span.trace_id} not found, creating placeholder")
            # Create placeholder trace
            _traces[span.trace_id] = {
                "trace_id": span.trace_id,
                "root_service": span.service,
                "operation": span.operation,
                "duration_ms": span.duration_ms,
                "status": span.status,
                "tags": {},
                "start_time": span.start_time,
                "created_at": _get_current_timestamp(),
                "created_by": "system",
                "updated_at": _get_current_timestamp(),
            }

        operator_ip = request.client.host if request.client else "unknown"

        new_span = {
            "span_id": span.span_id,
            "trace_id": span.trace_id,
            "parent_id": span.parent_id,
            "service": span.service,
            "operation": span.operation,
            "start_time": span.start_time,
            "duration_ms": span.duration_ms,
            "status": span.status,
            "tags": span.tags,
            "created_at": _get_current_timestamp(),
            "created_by": operator_ip,
            "updated_at": _get_current_timestamp(),
        }

        _spans[span.span_id] = new_span
        logger.info(f"Span created: {span.span_id}")
        return new_span
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create span: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create span: {str(e)}")


@router.get("/spans/{span_id}", summary="Get span by ID")
async def get_span(span_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific span by ID
    """
    # Validate path parameter
    span_id = validate_path_param(span_id, "span_id")

    logger.info(f"Fetching span: {span_id}")
    try:
        if span_id not in _spans:
            raise HTTPException(status_code=404, detail="Span not found")

        return _spans[span_id]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch span: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch span: {str(e)}")


@router.delete("/spans/{span_id}", summary="Delete span")
async def delete_span(span_id: str) -> Dict[str, Any]:
    """
    Delete a span
    """
    logger.info(f"Deleting span: {span_id}")
    try:
        if span_id not in _spans:
            raise HTTPException(status_code=404, detail="Span not found")

        del _spans[span_id]
        logger.info(f"Span deleted: {span_id}")
        return {"message": "Span deleted successfully", "id": span_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete span: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete span: {str(e)}")


# ============================================================
# 3. Service Management Endpoints
# ============================================================


@router.get("/services", summary="List services")
async def list_services(
    type: Optional[str] = Query(None, description="Filter by type")
) -> Dict[str, Any]:
    """
    List all services with optional filtering
    """
    logger.info("Fetching services list")
    try:
        # Try in-memory store
        items = list(_services.values())

        if not items:
            # Fallback to config-based services
            service_names = _services()
            items = [
                {
                    "name": name,
                    "type": "application",
                    "version": "1.0.0",
                    "metadata": {"source": "config"},
                }
                for name in service_names
            ]

        if type:
            items = [item for item in items if item.get("type") == type]

        return {
            "items": items,
            "total": len(items),
        }
    except Exception as e:
        logger.error(f"Failed to fetch services: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch services: {str(e)}")


@router.post("/services", summary="Create service")
async def create_service(service: ServiceCreate, request: Request) -> Dict[str, Any]:
    """
    Create a new service
    """
    logger.info(f"Creating service: {service.name}")
    try:
        if service.name in _services:
            raise HTTPException(status_code=409, detail="Service name already exists")

        operator_ip = request.client.host if request.client else "unknown"

        new_service = {
            "name": service.name,
            "type": service.type,
            "version": service.version,
            "metadata": service.metadata,
            "created_at": _get_current_timestamp(),
            "created_by": operator_ip,
            "updated_at": _get_current_timestamp(),
        }

        _services[service.name] = new_service
        logger.info(f"Service created: {service.name}")
        return new_service
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create service: {str(e)}")


@router.get("/services/{service_name}", summary="Get service by name")
async def get_service(service_name: str) -> Dict[str, Any]:
    """
    Retrieve a specific service by name
    """
    # Validate path parameter
    service_name = validate_path_param(service_name, "service_name")

    logger.info(f"Fetching service: {service_name}")
    try:
        if service_name not in _services:
            # Return default service info
            return {
                "name": service_name,
                "type": "application",
                "version": "1.0.0",
                "metadata": {"source": "default"},
            }

        return _services[service_name]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch service: {str(e)}")


@router.delete("/services/{service_name}", summary="Delete service")
async def delete_service(service_name: str) -> Dict[str, Any]:
    """
    Delete a service
    """
    logger.info(f"Deleting service: {service_name}")
    try:
        if service_name not in _services:
            raise HTTPException(status_code=404, detail="Service not found")

        del _services[service_name]
        logger.info(f"Service deleted: {service_name}")
        return {"message": "Service deleted successfully", "name": service_name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete service: {str(e)}")


# ============================================================
# 4. Operation Management Endpoints
# ============================================================


@router.get("/operations", summary="List operations")
async def list_operations(
    service: Optional[str] = Query(None, description="Filter by service"),
    type: Optional[str] = Query(None, description="Filter by type"),
) -> Dict[str, Any]:
    """
    List all operations with optional filtering
    """
    logger.info("Fetching operations list")
    try:
        items = list(_operations.values())

        if service:
            items = [item for item in items if item.get("service") == service]
        if type:
            items = [item for item in items if item.get("type") == type]

        return {
            "items": items,
            "total": len(items),
        }
    except Exception as e:
        logger.error(f"Failed to fetch operations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch operations: {str(e)}")


@router.post("/operations", summary="Create operation")
async def create_operation(operation: OperationCreate, request: Request) -> Dict[str, Any]:
    """
    Create a new operation
    """
    logger.info(f"Creating operation: {operation.name}")
    try:
        op_id = f"{operation.service}:{operation.name}"
        if op_id in _operations:
            raise HTTPException(status_code=409, detail="Operation already exists")

        operator_ip = request.client.host if request.client else "unknown"

        new_operation = {
            "id": op_id,
            "name": operation.name,
            "service": operation.service,
            "type": operation.type,
            "metadata": operation.metadata,
            "created_at": _get_current_timestamp(),
            "created_by": operator_ip,
            "updated_at": _get_current_timestamp(),
        }

        _operations[op_id] = new_operation
        logger.info(f"Operation created: {op_id}")
        return new_operation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create operation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create operation: {str(e)}")


@router.delete("/operations/{op_id}", summary="Delete operation")
async def delete_operation(op_id: str) -> Dict[str, Any]:
    """
    Delete an operation
    """
    # Validate path parameter
    op_id = validate_path_param(op_id, "operation_id")

    logger.info(f"Deleting operation: {op_id}")
    try:
        if op_id not in _operations:
            raise HTTPException(status_code=404, detail="Operation not found")

        del _operations[op_id]
        logger.info(f"Operation deleted: {op_id}")
        return {"message": "Operation deleted successfully", "id": op_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete operation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete operation: {str(e)}")


# ============================================================
# 5. Analytics Endpoints
# ============================================================


@router.get("/analytics", summary="Get analytics data")
async def get_analytics(
    service: Optional[str] = Query(None, description="Filter by service"),
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    start_time: Optional[str] = Query(None, description="Start time in ISO format"),
    end_time: Optional[str] = Query(None, description="End time in ISO format"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
) -> Dict[str, Any]:
    """
    Retrieve analytics data with optional filtering
    """
    logger.info("Fetching analytics data")
    try:
        items = list(_analytics.values())

        if service:
            items = [item for item in items if item.get("service") == service]
        if metric_type:
            items = [item for item in items if item.get("metric_type") == metric_type]
        if start_time:
            items = [item for item in items if item.get("timestamp", "") >= start_time]
        if end_time:
            items = [item for item in items if item.get("timestamp", "") <= end_time]

        # Sort by timestamp descending
        items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Apply limit
        items = items[:limit]

        # Calculate aggregated metrics
        if items:
            avg_value = sum(item.get("value", 0) for item in items) / len(items)
            max_value = max(item.get("value", 0) for item in items)
            min_value = min(item.get("value", 0) for item in items)
        else:
            avg_value = max_value = min_value = 0

        return {
            "items": items,
            "total": len(items),
            "aggregations": {
                "avg": avg_value,
                "max": max_value,
                "min": min_value,
            },
        }
    except Exception as e:
        logger.error(f"Failed to fetch analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")


@router.post("/analytics", summary="Create analytics data")
async def create_analytics(analytics: AnalyticsCreate, request: Request) -> Dict[str, Any]:
    """
    Create new analytics data point
    """
    logger.info(f"Creating analytics: {analytics.metric_type}")
    try:
        analytics_id = _generate_id()
        operator_ip = request.client.host if request.client else "unknown"

        new_analytics = {
            "id": analytics_id,
            "service": analytics.service,
            "operation": analytics.operation,
            "metric_type": analytics.metric_type,
            "value": analytics.value,
            "timestamp": analytics.timestamp,
            "created_at": _get_current_timestamp(),
            "created_by": operator_ip,
        }

        _analytics[analytics_id] = new_analytics
        logger.info(f"Analytics created: {analytics_id}")
        return new_analytics
    except Exception as e:
        logger.error(f"Failed to create analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create analytics: {str(e)}")


# ============================================================
# 6. Search Endpoints
# ============================================================


@router.post("/search", summary="Search traces")
async def search_traces(search_request: SearchRequest) -> Dict[str, Any]:
    """
    Search traces with advanced filters
    """
    logger.info(f"Searching traces with query: {search_request.query}")
    try:
        # Get all traces
        items = list(_traces.values())

        if not items:
            # Fallback to synthetic traces
            items = _recent_synthetic_traces(search_request.limit)

        # Apply filters
        if search_request.service_name:
            items = [
                item for item in items if item.get("root_service") == search_request.service_name
            ]
        if search_request.operation_name:
            items = [
                item for item in items if item.get("operation") == search_request.operation_name
            ]
        if search_request.status:
            items = [item for item in items if item.get("status") == search_request.status]
        if search_request.min_duration is not None:
            items = [
                item for item in items if item.get("duration_ms", 0) >= search_request.min_duration
            ]
        if search_request.max_duration is not None:
            items = [
                item for item in items if item.get("duration_ms", 0) <= search_request.max_duration
            ]
        if search_request.start_time:
            items = [
                item for item in items if item.get("start_time", "") >= search_request.start_time
            ]
        if search_request.end_time:
            items = [
                item for item in items if item.get("start_time", "") <= search_request.end_time
            ]

        # Apply text search on query
        if search_request.query:
            query_lower = search_request.query.lower()
            items = [
                item
                for item in items
                if query_lower in item.get("trace_id", "").lower()
                or query_lower in item.get("root_service", "").lower()
                or query_lower in item.get("operation", "").lower()
                or query_lower in str(item.get("tags", {})).lower()
            ]

        # Sort by start time descending
        items.sort(key=lambda x: x.get("start_time", ""), reverse=True)

        # Apply limit
        items = items[: search_request.limit]

        return {
            "items": items,
            "total": len(items),
            "query": search_request.query,
            "filters": {
                "service_name": search_request.service_name,
                "operation_name": search_request.operation_name,
                "status": search_request.status,
                "min_duration": search_request.min_duration,
                "max_duration": search_request.max_duration,
                "start_time": search_request.start_time,
                "end_time": search_request.end_time,
            },
        }
    except Exception as e:
        logger.error(f"Failed to search traces: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to search traces: {str(e)}")


# ============================================================
# 7. Performance Endpoints
# ============================================================


@router.get("/performance", summary="Get performance metrics")
async def get_performance(
    service: Optional[str] = Query(None, description="Filter by service"),
    operation: Optional[str] = Query(None, description="Filter by operation"),
    time_range: str = Query("1h", description="Time range: 1h, 6h, 24h, 7d"),
    granularity: str = Query("1m", description="Granularity: 1m, 5m, 15m, 1h"),
) -> Dict[str, Any]:
    """
    Get performance metrics for traces
    """
    logger.info(f"Fetching performance metrics for service: {service}")
    try:
        # Get traces
        items = list(_traces.values())

        if not items:
            items = _recent_synthetic_traces(100)

        # Apply filters
        if service:
            items = [item for item in items if item.get("root_service") == service]
        if operation:
            items = [item for item in items if item.get("operation") == operation]

        # Calculate metrics
        if items:
            durations = [item.get("duration_ms", 0) for item in items]
            avg_duration = sum(durations) / len(durations)
            p50_duration = sorted(durations)[len(durations) // 2] if durations else 0
            p95_duration = (
                sorted(durations)[int(len(durations) * 0.95)]
                if len(durations) > 1
                else durations[0] if durations else 0
            )
            p99_duration = (
                sorted(durations)[int(len(durations) * 0.99)]
                if len(durations) > 1
                else durations[0] if durations else 0
            )
            max_duration = max(durations) if durations else 0
            min_duration = min(durations) if durations else 0

            error_count = sum(1 for item in items if item.get("status") == "error")
            error_rate = error_count / len(items) if items else 0

            throughput = len(items) / 3600  # traces per hour
        else:
            avg_duration = p50_duration = p95_duration = p99_duration = max_duration = (
                min_duration
            ) = 0
            error_count = 0
            error_rate = 0
            throughput = 0

        # Generate time series data
        time_series = []
        now = time.time()
        for i in range(60):  # 60 data points
            timestamp = now - (59 - i) * 60  # Last hour
            time_series.append(
                {
                    "timestamp": datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(),
                    "avg_duration": avg_duration + (hash(str(i)) % 20 - 10),
                    "error_rate": error_rate + (hash(str(i)) % 5) / 100.0,
                    "throughput": throughput + (hash(str(i)) % 10),
                }
            )

        return {
            "time_range": time_range,
            "granularity": granularity,
            "service": service,
            "operation": operation,
            "metrics": {
                "avg_duration_ms": avg_duration,
                "p50_duration_ms": p50_duration,
                "p95_duration_ms": p95_duration,
                "p99_duration_ms": p99_duration,
                "max_duration_ms": max_duration,
                "min_duration_ms": min_duration,
                "error_count": error_count,
                "error_rate": error_rate,
                "throughput_per_hour": throughput,
            },
            "time_series": time_series,
            "total_traces": len(items),
        }
    except Exception as e:
        logger.error(f"Failed to fetch performance metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch performance metrics: {str(e)}"
        )


# ============================================================
# 8. Service Dependencies Endpoints
# ============================================================


@router.get("/dependencies", summary="Get service dependencies")
async def get_service_dependencies(
    service: Optional[str] = Query(None, description="Filter by service name"),
) -> Dict[str, Any]:
    """
    Get service dependency graph from trace data
    """
    logger.info(f"Fetching service dependencies for service: {service}")
    try:
        # Get all spans to build dependency graph
        items = list(_spans.values())

        if not items:
            # Generate synthetic dependencies
            service_names = _services()
            dependencies = []
            for i, svc in enumerate(service_names):
                deps = service_names[(i + 1) % len(service_names): (i + 2) % len(service_names) + 1]
                dependencies.append({
                    "service": svc,
                    "depends_on": deps,
                    "call_count": 100 + i * 10,
                    "avg_latency": 50.0 + i * 5.0,
                    "error_rate": 0.01 + i * 0.001,
                })
            return {
                "items": dependencies,
                "total": len(dependencies),
            }

        # Build dependency graph from spans
        dependency_map: Dict[str, Dict[str, Any]] = {}

        for span in items:
            src_service = span.get("service")
            if not src_service:
                continue

            if src_service not in dependency_map:
                dependency_map[src_service] = {
                    "service": src_service,
                    "depends_on": [],
                    "call_count": 0,
                    "total_latency": 0.0,
                    "error_count": 0,
                }

            # Extract dependencies from tags or parent spans
            if span.get("parent_id"):
                parent_span = next(
                    (s for s in items if s.get("span_id") == span.get("parent_id")),
                    None,
                )
                if parent_span and parent_span.get("service") != src_service:
                    dep_service = parent_span.get("service")
                    if dep_service and dep_service not in dependency_map[src_service]["depends_on"]:
                        dependency_map[src_service]["depends_on"].append(dep_service)

            dependency_map[src_service]["call_count"] += 1
            dependency_map[src_service]["total_latency"] += span.get("duration_ms", 0)
            if span.get("status") == "error":
                dependency_map[src_service]["error_count"] += 1

        # Calculate averages
        dependencies = []
        for dep_data in dependency_map.values():
            call_count = dep_data["call_count"]
            dependencies.append({
                "service": dep_data["service"],
                "depends_on": dep_data["depends_on"],
                "call_count": call_count,
                "avg_latency": dep_data["total_latency"] / call_count if call_count > 0 else 0,
                "error_rate": dep_data["error_count"] / call_count if call_count > 0 else 0,
            })

        # Filter by service if specified
        if service:
            dependencies = [d for d in dependencies if d["service"] == service]

        return {
            "items": dependencies,
            "total": len(dependencies),
        }
    except Exception as e:
        logger.error(f"Failed to fetch service dependencies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch service dependencies: {str(e)}")


# ============================================================
# 9. Flame Graph Endpoints
# ============================================================


@router.get("/traces/{trace_id}/flamegraph", summary="Get flame graph for trace")
async def get_trace_flamegraph(trace_id: str) -> Dict[str, Any]:
    """
    Get flame graph data for a specific trace
    """
    # Validate path parameter
    trace_id = validate_path_param(trace_id, "trace_id")

    logger.info(f"Fetching flame graph for trace: {trace_id}")
    try:
        # Get all spans for the trace
        trace_spans = [s for s in _spans.values() if s.get("trace_id") == trace_id]

        if not trace_spans:
            # Generate synthetic flame graph
            synthetic_trace = _generate_synthetic_trace(trace_id)
            trace_spans = synthetic_trace["spans"]

        # Build span tree
        span_map: Dict[str, Dict[str, Any]] = {}
        root_spans = []

        # First pass: create all nodes
        for span in trace_spans:
            span_id = span.get("span_id")
            node = {
                "span_id": span_id,
                "parent_id": span.get("parent_id"),
                "service": span.get("service"),
                "operation": span.get("operation"),
                "start_time": span.get("start_time"),
                "duration_ms": span.get("duration_ms", 0),
                "self_duration_ms": span.get("duration_ms", 0),
                "status": span.get("status", "ok"),
                "depth": 0,
                "children": [],
                "tags": span.get("tags", {}),
            }
            span_map[span_id] = node

        # Second pass: build tree structure and calculate self duration
        for span in trace_spans:
            span_id = span.get("span_id")
            node = span_map.get(span_id)
            if not node:
                continue

            parent_id = span.get("parent_id")
            if parent_id and parent_id in span_map:
                parent = span_map[parent_id]
                parent["children"].append(node)
                node["depth"] = parent["depth"] + 1
                # Subtract child duration from parent self duration
                parent["self_duration_ms"] -= span.get("duration_ms", 0)
            else:
                root_spans.append(node)

        # Return the first root span as the flame graph root
        if root_spans:
            return root_spans[0]
        else:
            return {
                "span_id": "root",
                "parent_id": None,
                "service": "unknown",
                "operation": "root",
                "start_time": _get_current_timestamp(),
                "duration_ms": 0,
                "self_duration_ms": 0,
                "status": "ok",
                "depth": 0,
                "children": [],
                "tags": {},
            }
    except Exception as e:
        logger.error(f"Failed to fetch flame graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch flame graph: {str(e)}")


# ============================================================
# 10. Alternative Endpoints for Frontend Compatibility
# ============================================================


# Create alternative router for /api/tracing prefix
router_alt = APIRouter(prefix="/api/tracing", tags=["Tracing (Alt)"])

# Create router for /api/v1/tracing prefix (exact match for requirements)
router_v1 = APIRouter(prefix="/api/v1/tracing", tags=["Tracing V1"])


@router_alt.get("/traces", summary="List traces (alt)")
async def list_traces_alt(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
) -> Dict[str, Any]:
    """Alternative endpoint for frontend compatibility"""
    return await list_traces(service_name=service_name, limit=limit)


@router_alt.get("/trace/{trace_id}", summary="Get trace by ID (alt)")
async def get_trace_alt(trace_id: str = Path(..., description="Trace ID")) -> Dict[str, Any]:
    """Alternative endpoint for frontend compatibility"""
    return await get_trace(trace_id)


# ============================================================
# V1 Router - Exact API paths as required
# ============================================================


@router_v1.get("/traces", summary="List traces (V1)")
async def list_traces_v1(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    query: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
) -> Dict[str, Any]:
    """V1 endpoint for listing traces"""
    return await list_traces(service_name=service_name, limit=limit)


@router_v1.post("/traces", summary="Create trace (V1)")
async def create_trace_v1(trace: TraceCreate, request: Request) -> Dict[str, Any]:
    """V1 endpoint for creating traces"""
    return await create_trace(trace, request)


@router_v1.get("/traces/{trace_id}", summary="Get trace by ID (V1)")
async def get_trace_v1(trace_id: str) -> Dict[str, Any]:
    """V1 endpoint for getting trace details"""
    return await get_trace(trace_id)


@router_v1.patch("/traces/{trace_id}", summary="Update trace (V1)")
async def update_trace_v1(
    trace_id: str, trace_update: TraceUpdate, request: Request
) -> Dict[str, Any]:
    """V1 endpoint for updating traces"""
    return await update_trace(trace_id, trace_update, request)


@router_v1.delete("/traces/{trace_id}", summary="Delete trace (V1)")
async def delete_trace_v1(trace_id: str) -> Dict[str, Any]:
    """V1 endpoint for deleting traces"""
    return await delete_trace(trace_id)


@router_v1.get("/spans", summary="List spans (V1)")
async def list_spans_v1(
    trace_id: Optional[str] = Query(None, description="Filter by trace ID"),
    service: Optional[str] = Query(None, description="Filter by service"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
) -> Dict[str, Any]:
    """V1 endpoint for listing spans"""
    return await list_spans(trace_id=trace_id, service=service, limit=limit)


@router_v1.post("/spans", summary="Create span (V1)")
async def create_span_v1(span: SpanCreate, request: Request) -> Dict[str, Any]:
    """V1 endpoint for creating spans"""
    return await create_span(span, request)


@router_v1.get("/spans/{span_id}", summary="Get span by ID (V1)")
async def get_span_v1(span_id: str) -> Dict[str, Any]:
    """V1 endpoint for getting span details"""
    return await get_span(span_id)


@router_v1.delete("/spans/{span_id}", summary="Delete span (V1)")
async def delete_span_v1(span_id: str) -> Dict[str, Any]:
    """V1 endpoint for deleting spans"""
    return await delete_span(span_id)


@router_v1.get("/services", summary="List services (V1)")
async def list_services_v1(
    type: Optional[str] = Query(None, description="Filter by type")
) -> Dict[str, Any]:
    """V1 endpoint for listing services"""
    return await list_services(type=type)


@router_v1.post("/services", summary="Create service (V1)")
async def create_service_v1(service: ServiceCreate, request: Request) -> Dict[str, Any]:
    """V1 endpoint for creating services"""
    return await create_service(service, request)


@router_v1.get("/services/{service_name}", summary="Get service by name (V1)")
async def get_service_v1(service_name: str) -> Dict[str, Any]:
    """V1 endpoint for getting service details"""
    return await get_service(service_name)


@router_v1.delete("/services/{service_name}", summary="Delete service (V1)")
async def delete_service_v1(service_name: str) -> Dict[str, Any]:
    """V1 endpoint for deleting services"""
    return await delete_service(service_name)


@router_v1.get("/operations", summary="List operations (V1)")
async def list_operations_v1(
    service: Optional[str] = Query(None, description="Filter by service"),
    type: Optional[str] = Query(None, description="Filter by type"),
) -> Dict[str, Any]:
    """V1 endpoint for listing operations"""
    return await list_operations(service=service, type=type)


@router_v1.post("/operations", summary="Create operation (V1)")
async def create_operation_v1(operation: OperationCreate, request: Request) -> Dict[str, Any]:
    """V1 endpoint for creating operations"""
    return await create_operation(operation, request)


@router_v1.delete("/operations/{op_id}", summary="Delete operation (V1)")
async def delete_operation_v1(op_id: str) -> Dict[str, Any]:
    """V1 endpoint for deleting operations"""
    return await delete_operation(op_id)


@router_v1.get("/analytics", summary="Get analytics data (V1)")
async def get_analytics_v1(
    service: Optional[str] = Query(None, description="Filter by service"),
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
) -> Dict[str, Any]:
    """V1 endpoint for getting analytics data"""
    return await get_analytics(service=service, metric_type=metric_type, limit=limit)


@router_v1.post("/analytics", summary="Create analytics data (V1)")
async def create_analytics_v1(analytics: AnalyticsCreate, request: Request) -> Dict[str, Any]:
    """V1 endpoint for creating analytics data"""
    return await create_analytics(analytics, request)


@router_v1.post("/search", summary="Search traces (V1)")
async def search_traces_v1(search_request: SearchRequest) -> Dict[str, Any]:
    """V1 endpoint for searching traces"""
    return await search_traces(search_request)


@router_v1.get("/performance", summary="Get performance metrics (V1)")
async def get_performance_v1(
    service: Optional[str] = Query(None, description="Filter by service"),
    operation: Optional[str] = Query(None, description="Filter by operation"),
    time_range: str = Query("1h", description="Time range: 1h, 6h, 24h, 7d"),
    granularity: str = Query("1m", description="Granularity: 1m, 5m, 15m, 1h"),
) -> Dict[str, Any]:
    """V1 endpoint for getting performance metrics"""
    return await get_performance(service=service, operation=operation, time_range=time_range, granularity=granularity)


@router_v1.get("/dependencies", summary="Get service dependencies (V1)")
async def get_service_dependencies_v1(
    service: Optional[str] = Query(None, description="Filter by service name"),
) -> Dict[str, Any]:
    """V1 endpoint for getting service dependencies"""
    return await get_service_dependencies(service=service)


@router_v1.get("/traces/{trace_id}/flamegraph", summary="Get flame graph for trace (V1)")
async def get_trace_flamegraph_v1(trace_id: str) -> Dict[str, Any]:
    """V1 endpoint for getting flame graph data"""
    return await get_trace_flamegraph(trace_id)
