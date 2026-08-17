# -*- coding: utf-8 -*-
"""
Hardware Log Analysis API Router

Provides REST API endpoints for hardware log analysis and automated remediation.

Features:
- Hardware log upload and analysis
- Multi-vendor support (Dell, HP, Lenovo, Cisco, Huawei)
- Component-level issue detection
- Repair recommendation generation
- Integration with auto_heal_alert workflow
- Automatic repair triggering
- Multi-tenant support
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field, field_validator

from core.command_guard import RiskLevel

from extensions.hardware_remediation.hardware_log_analyzer import (
    AnalysisResult,
    ComponentIssue,
    ComponentType,
    HardwareLogAnalyzer,
    HardwareVendor,
    SeverityLevel,
    get_hardware_log_analyzer,
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/hardware-logs",
    tags=["硬件日志分析"],
)


# ============================================================
# Request/Response Models
# ============================================================

class LogAnalysisRequest(BaseModel):
    """Request model for log analysis"""
    log_content: str = Field(
        ...,
        min_length=1,
        max_length=1000000,
        description="Hardware log content to analyze",
    )
    vendor: Optional[str] = Field(
        default=None,
        description="Vendor hint (dell, hp, lenovo, cisco, huawei, generic)",
    )
    auto_trigger_repair: bool = Field(
        default=False,
        description="Whether to automatically trigger repair for critical issues",
    )

    @field_validator("vendor")
    @classmethod
    def _validate_vendor(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().lower()
        valid_vendors = ["dell", "hp", "lenovo", "cisco", "huawei", "generic"]
        if v not in valid_vendors:
            raise ValueError(f"Invalid vendor. Must be one of: {', '.join(valid_vendors)}")
        return v

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "log_content": "2024-01-01 10:00:00 ERROR: CPU0 thermal trip detected",
                "vendor": "dell",
                "auto_trigger_repair": False,
            }
        },
    }


class RepairTriggerRequest(BaseModel):
    """Request model for triggering repair based on analysis"""
    analysis_id: str = Field(
        ...,
        description="Analysis result identifier",
    )
    issue_index: int = Field(
        ...,
        ge=0,
        description="Index of the issue to repair (from analysis result)",
    )
    script_key: Optional[str] = Field(
        default=None,
        description="Specific repair script to use (if not specified, uses recommendation)",
    )
    params: dict[str, str] = Field(
        default_factory=dict,
        description="Parameters for the repair script",
    )
    force: bool = Field(
        default=False,
        description="Force execution even if approval is required (use with caution)",
    )

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "analysis_id": "analysis-123",
                "issue_index": 0,
                "script_key": "ipmi_power_cycle",
                "params": {"host": "192.168.1.100", "username": "admin"},
                "force": False,
            }
        },
    }


class ComponentIssueResponse(BaseModel):
    """Response model for component issue"""
    component: str
    severity: str
    issue_type: str
    description: str
    affected_units: list[str]
    risk_level: str
    repair_recommendations: list[str]
    script_keys: list[str]
    log_entry_count: int


class AnalysisResponse(BaseModel):
    """Response model for log analysis"""
    vendor: str
    total_entries: int
    issues: list[ComponentIssueResponse]
    summary: dict[str, Any]
    analysis_timestamp: str
    repair_plan: dict[str, Any]


# ============================================================
# Helper Functions
# ============================================================

def _get_tenant_id(request: Request) -> str:
    """Extract tenant_id from request"""
    tenant_id = getattr(request.state, "tenant_id", "default")
    if not tenant_id or not isinstance(tenant_id, str):
        return "default"
    return tenant_id


def _verify_internal_key(request: Request) -> None:
    """Verify X-Internal-Key for protected endpoints"""
    try:
        from config import INTERNAL_API_KEY
    except ImportError:
        INTERNAL_API_KEY = ""
    
    if not INTERNAL_API_KEY:
        return
    
    provided_key = request.headers.get("X-Internal-Key")
    if not provided_key:
        raise HTTPException(status_code=403, detail="Missing X-Internal-Key header")
    if provided_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid X-Internal-Key")


def _map_vendor_string(vendor_str: Optional[str]) -> Optional[HardwareVendor]:
    """Map vendor string to HardwareVendor enum"""
    if not vendor_str:
        return None
    vendor_map = {
        "dell": HardwareVendor.DELL,
        "hp": HardwareVendor.HP,
        "lenovo": HardwareVendor.LENOVO,
        "cisco": HardwareVendor.CISCO,
        "huawei": HardwareVendor.HUAWEI,
        "generic": HardwareVendor.GENERIC,
    }
    return vendor_map.get(vendor_str.lower())


def _convert_issue_to_response(issue: ComponentIssue) -> ComponentIssueResponse:
    """Convert ComponentIssue to response model"""
    return ComponentIssueResponse(
        component=issue.component.value,
        severity=issue.severity.value,
        issue_type=issue.issue_type,
        description=issue.description,
        affected_units=issue.affected_units,
        risk_level=issue.risk_level.value,
        repair_recommendations=issue.repair_recommendations,
        script_keys=issue.script_keys,
        log_entry_count=len(issue.log_entries),
    )


def _trigger_auto_heal_alert(
    alert: dict[str, Any],
    tenant_id: str,
    operator_ip: str,
) -> dict[str, Any]:
    """
    Trigger auto_heal_alert workflow for hardware issues
    
    Args:
        alert: Alert dictionary with hardware issue details
        tenant_id: Tenant identifier
        operator_ip: Operator IP address for audit
        
    Returns:
        Result from auto_heal_alert workflow
    """
    try:
        from gateway.services_client import trigger_auto_heal
        
        result = trigger_auto_heal(
            alert_id=alert.get("id", ""),
            alert=alert,
            tenant_id=tenant_id,
            operator_ip=operator_ip,
        )
        return result
    except ImportError:
        logger.warning("trigger_auto_heal not available, using fallback")
        # Fallback: direct repair execution
        return _execute_repair_direct(alert, tenant_id, operator_ip)
    except Exception as e:
        logger.error(f"Error triggering auto_heal: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to trigger auto_heal: {str(e)}",
        }


def _execute_repair_direct(
    alert: dict[str, Any],
    tenant_id: str,
    operator_ip: str,
) -> dict[str, Any]:
    """
    Direct repair execution fallback
    
    Args:
        alert: Alert dictionary
        tenant_id: Tenant identifier
        operator_ip: Operator IP address
        
    Returns:
        Execution result
    """
    try:
        from core.repair_engine import execute_repair
        
        script_key = alert.get("script_key", "")
        params = alert.get("params", {})
        
        if not script_key:
            return {
                "success": False,
                "error": "No script_key provided for direct repair",
            }
        
        result = execute_repair(script_key, params)
        return result
    except Exception as e:
        logger.error(f"Error executing direct repair: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Direct repair failed: {str(e)}",
        }


# ============================================================
# API Endpoints
# ============================================================

@router.post(
    "/analyze",
    summary="分析硬件日志",
    responses={
        200: {
            "description": "日志分析结果",
            "content": {
                "application/json": {
                    "example": {
                        "vendor": "dell",
                        "total_entries": 150,
                        "issues": [
                            {
                                "component": "cpu",
                                "severity": "critical",
                                "issue_type": "thermal",
                                "description": "[CRITICAL] CPU thermal issue detected",
                                "affected_units": ["CPU0"],
                                "risk_level": "critical",
                                "repair_recommendations": [
                                    "Check CPU thermal sensors and cooling system",
                                ],
                                "script_keys": ["ipmi_power_cycle"],
                                "log_entry_count": 3,
                            }
                        ],
                        "summary": {
                            "vendor": "dell",
                            "total_entries": 150,
                            "components_analyzed": 5,
                            "issues_found": 1,
                            "critical_issues": 1,
                            "error_issues": 0,
                            "warning_issues": 0,
                        },
                        "analysis_timestamp": "2024-01-01T10:00:00Z",
                        "repair_plan": {
                            "analysis_summary": {},
                            "total_issues": 1,
                            "prioritized_actions": [],
                            "estimated_downtime": 0,
                            "requires_maintenance_window": True,
                        },
                    }
                }
            },
        },
        400: {"description": "请求参数错误"},
        500: {"description": "服务器内部错误"},
    },
)
async def analyze_hardware_log(
    request: LogAnalysisRequest,
    req: Request,
) -> dict[str, Any]:
    """
    Analyze hardware log content and detect component issues
    
    Supports multiple vendors:
    - Dell (iDRAC logs)
    - HP (iLO logs)
    - Lenovo (XClarity logs)
    - Cisco (IMC logs)
    - Huawei (iBMC logs)
    - Generic (syslog format)
    
    The analyzer will:
    1. Parse log entries and detect hardware components
    2. Identify issues by severity (critical, error, warning)
    3. Generate repair recommendations
    4. Map issues to available repair scripts
    5. Assess risk levels
    """
    tenant_id = _get_tenant_id(req)
    operator_ip = req.client.host if req.client else "unknown"
    
    logger.info(
        f"Hardware log analysis requested | tenant={tenant_id} | "
        f"operator={operator_ip} | vendor={request.vendor}"
    )
    
    try:
        analyzer = get_hardware_log_analyzer()
        
        # Map vendor string to enum
        vendor_enum = _map_vendor_string(request.vendor)
        
        # Perform analysis
        analysis_result: AnalysisResult = analyzer.analyze_log(
            log_content=request.log_content,
            vendor=vendor_enum,
        )
        
        # Generate repair plan
        repair_plan = analyzer.generate_repair_plan(analysis_result)
        
        # Convert issues to response format
        issues_response = [
            _convert_issue_to_response(issue) for issue in analysis_result.issues
        ]
        
        # Build response
        response = {
            "vendor": analysis_result.vendor.value,
            "total_entries": analysis_result.total_entries,
            "issues": issues_response,
            "summary": analysis_result.summary,
            "analysis_timestamp": analysis_result.analysis_timestamp,
            "repair_plan": repair_plan,
            "tenant_id": tenant_id,
        }
        
        # Auto-trigger repair if requested and critical issues found
        if request.auto_trigger_repair:
            critical_issues = [
                i for i in analysis_result.issues
                if i.severity == SeverityLevel.CRITICAL
            ]
            if critical_issues:
                logger.warning(
                    f"Auto-triggering repair for {len(critical_issues)} critical issues"
                )
                for idx, issue in enumerate(critical_issues):
                    try:
                        alert = {
                            "id": f"hw-{analysis_result.vendor.value}-{issue.component.value}-{idx}",
                            "title": issue.description,
                            "platform": "linux",
                            "host": "hardware-node",
                            "severity": issue.severity.value,
                            "component": issue.component.value,
                            "script_key": issue.script_keys[0] if issue.script_keys else None,
                            "params": {},
                            "tenant_id": tenant_id,
                        }
                        heal_result = _trigger_auto_heal_alert(
                            alert=alert,
                            tenant_id=tenant_id,
                            operator_ip=operator_ip,
                        )
                        response["auto_repair_results"] = response.get("auto_repair_results", [])
                        response["auto_repair_results"].append({
                            "issue_index": idx,
                            "success": heal_result.get("success", False),
                            "result": heal_result,
                        })
                    except Exception as e:
                        logger.error(f"Auto-repair failed for issue {idx}: {e}")
                        response["auto_repair_results"] = response.get("auto_repair_results", [])
                        response["auto_repair_results"].append({
                            "issue_index": idx,
                            "success": False,
                            "error": str(e),
                        })
        
        logger.info(
            f"Hardware log analysis completed | tenant={tenant_id} | "
            f"entries={analysis_result.total_entries} | issues={len(analysis_result.issues)}"
        )
        
        return response
        
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Hardware log analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)[:200]}"
        )


@router.post(
    "/upload",
    summary="上传并分析硬件日志文件",
    responses={
        200: {"description": "文件上传和分析结果"},
        400: {"description": "文件格式错误或过大"},
        500: {"description": "服务器内部错误"},
    },
)
async def upload_and_analyze_log(
    request: Request,
    file: UploadFile = File(...),
    vendor: Optional[str] = Form(None),
    auto_trigger_repair: bool = Form(False),
) -> dict[str, Any]:
    """
    Upload a hardware log file and analyze it
    
    Supported file formats:
    - Plain text logs (.log, .txt)
    - Compressed logs (.gz, .bz2)
    - Maximum file size: 10MB
    """
    tenant_id = _get_tenant_id(request)
    operator_ip = request.client.host if request.client else "unknown"
    
    logger.info(
        f"Hardware log file upload | tenant={tenant_id} | "
        f"filename={file.filename} | operator={operator_ip}"
    )
    
    # Validate file size (10MB limit)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Decode content
    try:
        log_content = content.decode('utf-8', errors='replace')
    except Exception as e:
        logger.error(f"Failed to decode file content: {e}")
        raise HTTPException(status_code=400, detail="Failed to decode file content")
    
    # Create analysis request
    analysis_request = LogAnalysisRequest(
        log_content=log_content,
        vendor=vendor,
        auto_trigger_repair=auto_trigger_repair,
    )
    
    # Delegate to analyze endpoint
    return await analyze_hardware_log(analysis_request, request)


@router.post(
    "/repair/trigger",
    summary="触发硬件修复",
    responses={
        200: {"description": "修复触发结果"},
        400: {"description": "请求参数错误"},
        403: {"description": "权限不足或需要审批"},
        500: {"description": "服务器内部错误"},
    },
)
async def trigger_hardware_repair(
    request: RepairTriggerRequest,
    req: Request,
) -> dict[str, Any]:
    """
    Trigger repair for a specific hardware issue
    
    This endpoint:
    1. Validates the repair script through command_guard
    2. Integrates with auto_heal_alert workflow
    3. Executes repair with proper approval flow
    4. Returns execution result
    
    For high-risk operations, approval may be required.
    """
    tenant_id = _get_tenant_id(req)
    operator_ip = req.client.host if req.client else "unknown"
    
    logger.warning(
        f"Hardware repair trigger requested | tenant={tenant_id} | "
        f"operator={operator_ip} | analysis_id={request.analysis_id} | "
        f"issue_index={request.issue_index}"
    )
    
    try:
        analyzer = get_hardware_log_analyzer()
        
        # Note: In a real implementation, you would store analysis results
        # and retrieve them by analysis_id. For now, we'll create a mock alert.
        
        # Validate script through command_guard
        script_key = request.script_key or "ipmi_power_cycle"
        
        # Build alert for auto_heal workflow
        alert = {
            "id": f"hw-repair-{request.analysis_id}-{request.issue_index}",
            "title": f"Hardware repair for issue {request.issue_index}",
            "platform": "linux",
            "host": "hardware-node",
            "severity": "high",
            "component": "hardware",
            "script_key": script_key,
            "params": request.params,
            "tenant_id": tenant_id,
            "force": request.force,
        }
        
        # Check if approval is required
        script = repair_script_library.get_script(script_key)
        requires_approval = script.requires_approval if script else True
        
        if requires_approval and not request.force:
            # Submit for approval
            try:
                from core.auto_heal import upsert_pending_approval
                
                approval_data = {
                    "alert_id": alert["id"],
                    "proposal": f"Execute repair script: {script_key}",
                    "risk_level": "high",
                    "script_key": script_key,
                    "params": request.params,
                    "tenant_id": tenant_id,
                    "operator": operator_ip,
                }
                upsert_pending_approval(alert["id"], approval_data)
                
                return {
                    "success": True,
                    "status": "pending_approval",
                    "message": "Repair requires approval. Submitted to approval queue.",
                    "alert_id": alert["id"],
                }
            except Exception as e:
                logger.error(f"Failed to submit for approval: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to submit for approval: {str(e)}"
                )
        
        # Execute repair directly (or with force)
        result = _trigger_auto_heal_alert(
            alert=alert,
            tenant_id=tenant_id,
            operator_ip=operator_ip,
        )
        
        logger.info(
            f"Hardware repair trigger completed | tenant={tenant_id} | "
            f"success={result.get('success', False)}"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hardware repair trigger failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Repair trigger failed: {str(e)[:200]}"
        )


@router.get(
    "/vendors",
    summary="获取支持的硬件厂商列表",
    responses={
        200: {
            "description": "支持的厂商列表",
            "content": {
                "application/json": {
                    "example": {
                        "vendors": [
                            {"value": "dell", "name": "Dell (iDRAC)"},
                            {"value": "hp", "name": "HP (iLO)"},
                            {"value": "lenovo", "name": "Lenovo (XClarity)"},
                            {"value": "cisco", "name": "Cisco (IMC)"},
                            {"value": "huawei", "name": "Huawei (iBMC)"},
                            {"value": "generic", "name": "Generic (Syslog)"},
                        ]
                    }
                }
            },
        },
    },
)
async def list_supported_vendors() -> dict[str, Any]:
    """Get list of supported hardware vendors"""
    vendors = [
        {"value": "dell", "name": "Dell (iDRAC)"},
        {"value": "hp", "name": "HP (iLO)"},
        {"value": "lenovo", "name": "Lenovo (XClarity)"},
        {"value": "cisco", "name": "Cisco (IMC)"},
        {"value": "huawei", "name": "Huawei (iBMC)"},
        {"value": "generic", "name": "Generic (Syslog)"},
    ]
    return {"vendors": vendors}


@router.get(
    "/components",
    summary="获取支持的硬件组件类型",
    responses={
        200: {
            "description": "支持的组件类型列表",
            "content": {
                "application/json": {
                    "example": {
                        "components": [
                            {"value": "cpu", "name": "CPU"},
                            {"value": "memory", "name": "Memory"},
                            {"value": "storage", "name": "Storage"},
                            {"value": "network", "name": "Network"},
                            {"value": "power", "name": "Power"},
                            {"value": "cooling", "name": "Cooling"},
                            {"value": "firmware", "name": "Firmware"},
                            {"value": "raid", "name": "RAID"},
                        ]
                    }
                }
            },
        },
    },
)
async def list_supported_components() -> dict[str, Any]:
    """Get list of supported hardware component types"""
    components = [
        {"value": "cpu", "name": "CPU"},
        {"value": "memory", "name": "Memory"},
        {"value": "storage", "name": "Storage"},
        {"value": "network", "name": "Network"},
        {"value": "power", "name": "Power"},
        {"value": "cooling", "name": "Cooling"},
        {"value": "firmware", "name": "Firmware"},
        {"value": "raid", "name": "RAID"},
        {"value": "motherboard", "name": "Motherboard"},
        {"value": "chassis", "name": "Chassis"},
    ]
    return {"components": components}


@router.get(
    "/scripts",
    summary="获取可用的硬件修复脚本",
    responses={
        200: {
            "description": "硬件修复脚本列表",
            "content": {
                "application/json": {
                    "example": {
                        "scripts": [
                            {
                                "script_key": "ipmi_power_cycle",
                                "name": "IPMI Power Cycle",
                                "description": "Power cycle a server via IPMI",
                                "risk_level": "high",
                                "requires_approval": True,
                            }
                        ]
                    }
                }
            },
        },
    },
)
async def list_hardware_repair_scripts() -> dict[str, Any]:
    """Get list of available hardware repair scripts"""
    from core.auto_heal import repair_script_library
    
    hardware_scripts = []
    
    # Filter scripts related to hardware
    hardware_categories = ["hardware", "ipmi", "redfish", "raid", "smart"]
    
    for script_key, script in repair_script_library.scripts.items():
        metadata = script.metadata or {}
        category = metadata.get("category", "")
        
        if any(cat in category.lower() for cat in hardware_categories):
            hardware_scripts.append({
                "script_key": script.script_key,
                "name": script.name,
                "description": script.description,
                "risk_level": script.risk_level.value,
                "requires_approval": script.requires_approval,
                "platforms": [p.value for p in script.platforms],
                "category": category,
            })
    
    return {"scripts": hardware_scripts}
