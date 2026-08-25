# -*- coding: utf-8 -*-
"""Compliance Monitoring Service - Main entry point."""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from compliance_monitor import ComplianceMonitor, AlertSeverity
from policy_checker import PolicyChecker, PolicyType
from report_generator import ReportGenerator, ReportFormat, ReportType
from grpc.server import serve as grpc_serve

# Import compliance manager from core
from core.compliance_manager import ComplianceFramework, ComplianceStatus, RiskLevel

SERVICE_NAME = "compliance_monitoring_service"
HTTP_PORT = int(os.getenv("PORT", "8010"))
GRPC_PORT = int(os.getenv("GRPC_PORT", "50060"))

app = FastAPI(title=SERVICE_NAME.replace("_", " ").title())
logger = logging.getLogger(SERVICE_NAME)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=f"[{SERVICE_NAME}] %(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Initialize components
compliance_monitor = ComplianceMonitor()
policy_checker = PolicyChecker()
report_generator = ReportGenerator()


# Initialize on startup
@app.on_event("startup")
async def startup_event():
    """Initialize the service on startup."""
    logger.info(f"Starting {SERVICE_NAME}")
    
    # Start gRPC server in background
    asyncio.create_task(start_grpc_server())
    
    # Start auto monitoring if enabled
    if compliance_monitor.auto_monitor_enabled:
        await compliance_monitor.start_auto_monitoring()
    
    logger.info(f"{SERVICE_NAME} initialized successfully")


async def start_grpc_server():
    """Start gRPC server in background."""
    try:
        await grpc_serve(host="0.0.0.0", port=GRPC_PORT)
    except Exception as e:
        logger.error(f"Failed to start gRPC server: {e}")


# Request/Response Models
class ComplianceCheckRequest(BaseModel):
    rule_id: Optional[str] = None
    framework: Optional[str] = None
    force: bool = False


class ComplianceCheckResponse(BaseModel):
    success: bool
    message: str
    checks: List[Dict[str, Any]]


class ComplianceRuleRequest(BaseModel):
    rule_id: str = Field(..., min_length=1)
    rule_name: str = Field(..., min_length=1)
    framework: str = Field(..., regex="^(gdpr|hipaa|pci_dss|soc2|iso27001|nist)$")
    description: str = Field(..., min_length=1)
    severity: str = Field(default="medium", regex="^(critical|high|medium|low)$")
    enabled: bool = True
    check_frequency: int = Field(default=86400, ge=60)
    metadata: Dict[str, str] = Field(default_factory=dict)


class ComplianceRuleResponse(BaseModel):
    rule_id: str
    rule_name: str
    framework: str
    description: str
    severity: str
    enabled: bool
    check_frequency: int
    metadata: Dict[str, str]


class ReportRequest(BaseModel):
    framework: str = Field(..., regex="^(gdpr|hipaa|pci_dss|soc2|iso27001|nist)$")
    period_start: str = Field(..., description="ISO format datetime")
    period_end: str = Field(..., description="ISO format datetime")
    report_type: str = Field(default="detailed", regex="^(summary|detailed|executive|audit|trend)$")
    format: str = Field(default="json", regex="^(json|html|pdf|csv|markdown)$")
    include_recommendations: bool = True
    include_evidence: bool = True


class AlertAcknowledgeRequest(BaseModel):
    acknowledged_by: str = Field(..., min_length=1)


class TrendRequest(BaseModel):
    framework: Optional[str] = None
    days: int = Field(default=30, ge=1, le=365)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = SERVICE_NAME


# Health Check Endpoints
@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", service=SERVICE_NAME)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": SERVICE_NAME,
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "checks": "/checks",
            "rules": "/rules",
            "reports": "/reports",
            "alerts": "/alerts",
            "trends": "/trends",
            "statistics": "/statistics",
        },
    }


# Compliance Check Endpoints
@app.post("/checks", response_model=ComplianceCheckResponse)
async def run_compliance_check(request: ComplianceCheckRequest) -> ComplianceCheckResponse:
    """Run compliance check."""
    try:
        # Convert framework string to enum
        framework = None
        if request.framework:
            framework = ComplianceFramework(request.framework)

        # Run compliance check
        checks = await compliance_monitor.compliance_manager.run_compliance_check(
            rule_id=request.rule_id,
            framework=framework,
        )

        # Convert to dict
        check_dicts = [
            {
                "check_id": c.check_id,
                "rule_id": c.rule_id,
                "status": c.status.value,
                "checked_at": c.checked_at.isoformat(),
                "findings": c.findings,
                "recommendations": c.recommendations,
                "evidence": c.evidence,
                "metadata": c.metadata,
            }
            for c in checks
        ]

        return ComplianceCheckResponse(
            success=True,
            message=f"Completed {len(checks)} compliance checks",
            checks=check_dicts,
        )
    except Exception as e:
        logger.error(f"Compliance check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/checks/history")
async def get_check_history(
    rule_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """Get compliance check history."""
    try:
        history = compliance_monitor.compliance_manager.get_check_history(
            rule_id=rule_id,
            limit=limit,
        )
        return {
            "success": True,
            "history": history,
            "total_count": len(history),
        }
    except Exception as e:
        logger.error(f"Failed to get check history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Compliance Rules Endpoints
@app.get("/rules")
async def get_compliance_rules(
    framework: Optional[str] = None,
    enabled_only: bool = False,
):
    """Get compliance rules."""
    try:
        # Convert framework string to enum
        framework_enum = None
        if framework:
            framework_enum = ComplianceFramework(framework)

        rules = compliance_monitor.compliance_manager.get_compliance_rules(
            framework=framework_enum,
        )

        # Filter if enabled_only
        if enabled_only:
            rules = {k: v for k, v in rules.items() if v.get("enabled", True)}

        return {
            "success": True,
            "rules": list(rules.values()),
            "total_count": len(rules),
        }
    except Exception as e:
        logger.error(f"Failed to get compliance rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/rules", response_model=ComplianceRuleResponse)
async def register_compliance_rule(request: ComplianceRuleRequest) -> ComplianceRuleResponse:
    """Register a custom compliance rule."""
    try:
        from core.compliance_manager import ComplianceRule

        framework = ComplianceFramework(request.framework)
        severity = RiskLevel(request.severity)

        rule = ComplianceRule(
            rule_id=request.rule_id,
            rule_name=request.rule_name,
            framework=framework,
            description=request.description,
            severity=severity,
            enabled=request.enabled,
            check_frequency=request.check_frequency,
            metadata=request.metadata,
        )

        compliance_monitor.compliance_manager.register_rule(rule)

        return ComplianceRuleResponse(
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            framework=rule.framework.value,
            description=rule.description,
            severity=rule.severity.value,
            enabled=rule.enabled,
            check_frequency=rule.check_frequency,
            metadata=rule.metadata,
        )
    except Exception as e:
        logger.error(f"Failed to register compliance rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.delete("/rules/{rule_id}")
async def delete_compliance_rule(rule_id: str):
    """Delete a compliance rule."""
    try:
        if rule_id not in compliance_monitor.compliance_manager.compliance_rules:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rule not found"
            )

        del compliance_monitor.compliance_manager.compliance_rules[rule_id]

        return {
            "success": True,
            "message": f"Rule {rule_id} deleted successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete compliance rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Policy Checker Endpoints
@app.get("/policies")
async def get_policies(
    framework: Optional[str] = None,
    policy_type: Optional[str] = None,
):
    """Get policies."""
    try:
        # Convert to enums
        framework_enum = None
        if framework:
            framework_enum = ComplianceFramework(framework)

        policy_type_enum = None
        if policy_type:
            policy_type_enum = PolicyType(policy_type)

        policies = policy_checker.get_policies(
            framework=framework_enum,
            policy_type=policy_type_enum,
        )

        return {
            "success": True,
            "policies": policies,
            "total_count": len(policies),
        }
    except Exception as e:
        logger.error(f"Failed to get policies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/policies/check")
async def check_policy(
    policy_id: str,
    context: Optional[Dict[str, Any]] = None,
):
    """Check a specific policy."""
    try:
        result = await policy_checker.check_policy(policy_id, context)

        return {
            "success": True,
            "result": {
                "policy_id": result.policy_id,
                "policy_name": result.policy_name,
                "policy_type": result.policy_type.value,
                "passed": result.passed,
                "checked_at": result.checked_at.isoformat(),
                "findings": result.findings,
                "recommendations": result.recommendations,
                "severity": result.severity.value,
            },
        }
    except Exception as e:
        logger.error(f"Failed to check policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Report Endpoints
@app.post("/reports")
async def generate_report(request: ReportRequest):
    """Generate compliance report."""
    try:
        # Parse dates
        period_start = datetime.fromisoformat(request.period_start)
        period_end = datetime.fromisoformat(request.period_end)

        # Convert to enums
        framework = ComplianceFramework(request.framework)
        report_type = ReportType(request.report_type)
        report_format = ReportFormat(request.format)

        # Create report config
        from report_generator import ReportConfig
        config = ReportConfig(
            report_type=report_type,
            format=report_format,
            include_recommendations=request.include_recommendations,
            include_evidence=request.include_evidence,
        )

        # Run compliance checks for the period
        checks = await compliance_monitor.compliance_manager.run_compliance_check(
            framework=framework,
        )

        # Generate report
        report = await report_generator.generate_report(
            framework=framework,
            period_start=period_start,
            period_end=period_end,
            checks=checks,
            report_config=config,
        )

        return {
            "success": True,
            "message": "Report generated successfully",
            "report": {
                "report_id": report.report_id,
                "report_type": report.report_type.value,
                "format": report.format.value,
                "framework": report.framework.value,
                "period_start": report.period_start.isoformat(),
                "period_end": report.period_end.isoformat(),
                "generated_at": report.generated_at.isoformat(),
                "file_path": report.file_path,
                "metadata": report.metadata,
            },
        }
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/reports")
async def list_reports(
    framework: Optional[str] = None,
    limit: int = 100,
):
    """List generated reports."""
    try:
        framework_enum = None
        if framework:
            framework_enum = ComplianceFramework(framework)

        reports = report_generator.list_reports(
            framework=framework_enum,
            limit=limit,
        )

        return {
            "success": True,
            "reports": reports,
            "total_count": len(reports),
        }
    except Exception as e:
        logger.error(f"Failed to list reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Get a specific report."""
    try:
        report = report_generator.get_report(report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )

        return {
            "success": True,
            "report": {
                "report_id": report.report_id,
                "report_type": report.report_type.value,
                "format": report.format.value,
                "framework": report.framework.value,
                "period_start": report.period_start.isoformat(),
                "period_end": report.period_end.isoformat(),
                "generated_at": report.generated_at.isoformat(),
                "file_path": report.file_path,
                "metadata": report.metadata,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.delete("/reports/{report_id}")
async def delete_report(report_id: str):
    """Delete a report."""
    try:
        success = report_generator.delete_report(report_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )

        return {
            "success": True,
            "message": f"Report {report_id} deleted successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Alert Endpoints
@app.get("/alerts")
async def get_alerts(
    severity: Optional[str] = None,
    framework: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = 100,
):
    """Get compliance alerts."""
    try:
        # Convert to enums
        severity_enum = None
        if severity:
            severity_enum = AlertSeverity(severity)

        framework_enum = None
        if framework:
            framework_enum = ComplianceFramework(framework)

        alerts = compliance_monitor.get_alerts(
            severity=severity_enum,
            framework=framework_enum,
            acknowledged=acknowledged,
            limit=limit,
        )

        return {
            "success": True,
            "alerts": alerts,
            "total_count": len(alerts),
        }
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, request: AlertAcknowledgeRequest):
    """Acknowledge a compliance alert."""
    try:
        success = compliance_monitor.acknowledge_alert(alert_id, request.acknowledged_by)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

        return {
            "success": True,
            "message": f"Alert {alert_id} acknowledged successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Trend Analysis Endpoints
@app.post("/trends")
async def get_compliance_trend(request: TrendRequest):
    """Get compliance trend analysis."""
    try:
        framework_enum = None
        if request.framework:
            framework_enum = ComplianceFramework(request.framework)

        trend = compliance_monitor.get_trend_analysis(
            framework=framework_enum,
            days=request.days,
        )

        return {
            "success": True,
            "trend": trend,
        }
    except Exception as e:
        logger.error(f"Failed to get compliance trend: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Statistics Endpoints
@app.get("/statistics")
async def get_statistics():
    """Get compliance statistics."""
    try:
        compliance_stats = compliance_monitor.compliance_manager.get_statistics()
        monitor_stats = compliance_monitor.get_statistics()

        return {
            "success": True,
            "statistics": {
                **compliance_stats,
                **monitor_stats,
            },
        }
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Monitoring Cycle Endpoint
@app.post("/monitoring/run")
async def run_monitoring_cycle():
    """Manually trigger a monitoring cycle."""
    try:
        checks = await compliance_monitor.run_monitoring_cycle()

        check_dicts = [
            {
                "check_id": c.check_id,
                "rule_id": c.rule_id,
                "status": c.status.value,
                "checked_at": c.checked_at.isoformat(),
            }
            for c in checks
        ]

        return {
            "success": True,
            "message": f"Monitoring cycle completed with {len(checks)} checks",
            "checks": check_dicts,
        }
    except Exception as e:
        logger.error(f"Failed to run monitoring cycle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=HTTP_PORT)
