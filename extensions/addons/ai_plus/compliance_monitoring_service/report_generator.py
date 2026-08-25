# -*- coding: utf-8 -*-
"""Report Generator - Generates compliance reports in various formats."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

# Import compliance manager from core
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from core.compliance_manager import (
    ComplianceFramework,
    ComplianceStatus,
    RiskLevel,
    ComplianceCheck,
    ComplianceReport,
)


class ReportFormat(Enum):
    """Report output formats"""
    JSON = "json"
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"
    MARKDOWN = "markdown"


class ReportType(Enum):
    """Report types"""
    SUMMARY = "summary"
    DETAILED = "detailed"
    EXECUTIVE = "executive"
    AUDIT = "audit"
    TREND = "trend"


@dataclass
class ReportConfig:
    """Report configuration"""
    report_type: ReportType = ReportType.DETAILED
    format: ReportFormat = ReportFormat.JSON
    include_recommendations: bool = True
    include_evidence: bool = True
    include_trend_analysis: bool = False
    include_alerts: bool = True
    custom_sections: List[str] = field(default_factory=list)


@dataclass
class GeneratedReport:
    """Generated compliance report"""
    report_id: str
    report_type: ReportType
    format: ReportFormat
    framework: ComplianceFramework
    period_start: datetime
    period_end: datetime
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    file_path: Optional[str] = None


class ReportGenerator:
    """Compliance report generator"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize report generator

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Report storage
        self.report_storage_path = Path(self.config.get("report_storage_path", "./reports"))
        self.report_storage_path.mkdir(parents=True, exist_ok=True)

        # Generated reports cache
        self.reports: Dict[str, GeneratedReport] = {}

        logger.info("Report generator initialized")

    async def generate_report(
        self,
        framework: ComplianceFramework,
        period_start: datetime,
        period_end: datetime,
        checks: List[ComplianceCheck],
        report_config: Optional[ReportConfig] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> GeneratedReport:
        """
        Generate a compliance report

        Args:
            framework: Compliance framework
            period_start: Report period start
            period_end: Report period end
            checks: Compliance check results
            report_config: Report configuration
            additional_data: Additional data for the report

        Returns:
            Generated report
        """
        config = report_config or ReportConfig()

        # Generate report ID
        report_id = (
            f"report_{framework.value}_{period_start.strftime('%Y%m%d')}_"
            f"{period_end.strftime('%Y%m%d')}_{datetime.now(timezone.utc).strftime('%H%M%S')}"
        )

        # Calculate statistics
        stats = self._calculate_statistics(checks)

        # Generate content based on format
        if config.format == ReportFormat.JSON:
            content = self._generate_json_report(
                framework, period_start, period_end, checks, stats, config, additional_data
            )
        elif config.format == ReportFormat.HTML:
            content = self._generate_html_report(
                framework, period_start, period_end, checks, stats, config, additional_data
            )
        elif config.format == ReportFormat.MARKDOWN:
            content = self._generate_markdown_report(
                framework, period_start, period_end, checks, stats, config, additional_data
            )
        elif config.format == ReportFormat.CSV:
            content = self._generate_csv_report(
                framework, period_start, period_end, checks, stats, config, additional_data
            )
        else:
            content = self._generate_json_report(
                framework, period_start, period_end, checks, stats, config, additional_data
            )

        # Save report to file
        file_extension = self._get_file_extension(config.format)
        file_path = self.report_storage_path / f"{report_id}.{file_extension}"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Create report object
        report = GeneratedReport(
            report_id=report_id,
            report_type=config.report_type,
            format=config.format,
            framework=framework,
            period_start=period_start,
            period_end=period_end,
            content=content,
            metadata={
                "total_checks": stats["total_checks"],
                "passed_checks": stats["passed_checks"],
                "failed_checks": stats["failed_checks"],
                "compliance_rate": stats["compliance_rate"],
                "overall_status": stats["overall_status"],
            },
            file_path=str(file_path),
        )

        self.reports[report_id] = report

        logger.info(f"Generated report: {report_id}")

        return report

    def _calculate_statistics(self, checks: List[ComplianceCheck]) -> Dict[str, Any]:
        """
        Calculate report statistics

        Args:
            checks: Compliance check results

        Returns:
            Statistics dictionary
        """
        total_checks = len(checks)
        passed_checks = len([c for c in checks if c.status == ComplianceStatus.COMPLIANT])
        failed_checks = total_checks - passed_checks
        compliance_rate = passed_checks / total_checks if total_checks > 0 else 0.0

        # Determine overall status
        if failed_checks == 0:
            overall_status = ComplianceStatus.COMPLIANT
        elif passed_checks > failed_checks:
            overall_status = ComplianceStatus.PARTIALLY_COMPLIANT
        else:
            overall_status = ComplianceStatus.NON_COMPLIANT

        # Count by severity
        severity_counts = {}
        for check in checks:
            # Get rule severity from check metadata or default to MEDIUM
            severity = check.metadata.get("severity", RiskLevel.MEDIUM.value)
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "compliance_rate": compliance_rate,
            "overall_status": overall_status.value,
            "severity_counts": severity_counts,
        }

    def _generate_json_report(
        self,
        framework: ComplianceFramework,
        period_start: datetime,
        period_end: datetime,
        checks: List[ComplianceCheck],
        stats: Dict[str, Any],
        config: ReportConfig,
        additional_data: Optional[Dict[str, Any]],
    ) -> str:
        """Generate JSON format report"""
        report_data = {
            "report_id": "",
            "report_type": config.report_type.value,
            "framework": framework.value,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_checks": stats["total_checks"],
                "passed_checks": stats["passed_checks"],
                "failed_checks": stats["failed_checks"],
                "compliance_rate": stats["compliance_rate"],
                "overall_status": stats["overall_status"],
            },
            "checks": [],
        }

        # Add check details
        for check in checks:
            check_data = {
                "check_id": check.check_id,
                "rule_id": check.rule_id,
                "status": check.status.value,
                "checked_at": check.checked_at.isoformat(),
            }

            if config.include_recommendations:
                check_data["findings"] = check.findings
                check_data["recommendations"] = check.recommendations

            if config.include_evidence:
                check_data["evidence"] = check.evidence

            report_data["checks"].append(check_data)

        # Add additional data
        if additional_data:
            report_data["additional_data"] = additional_data

        return json.dumps(report_data, indent=2)

    def _generate_html_report(
        self,
        framework: ComplianceFramework,
        period_start: datetime,
        period_end: datetime,
        checks: List[ComplianceCheck],
        stats: Dict[str, Any],
        config: ReportConfig,
        additional_data: Optional[Dict[str, Any]],
    ) -> str:
        """Generate HTML format report"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Compliance Report - {framework.value.upper()}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; }}
        .summary {{ background-color: #f2f2f2; padding: 15px; margin: 20px 0; }}
        .check {{ border: 1px solid #ddd; padding: 10px; margin: 10px 0; }}
        .pass {{ border-left: 5px solid #4CAF50; }}
        .fail {{ border-left: 5px solid #f44336; }}
        .findings {{ margin-top: 10px; }}
        .recommendations {{ margin-top: 10px; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Compliance Report</h1>
        <h2>{framework.value.upper()}</h2>
        <p>Period: {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}</p>
    </div>

    <div class="summary">
        <h3>Summary</h3>
        <p>Total Checks: {stats['total_checks']}</p>
        <p>Passed: {stats['passed_checks']}</p>
        <p>Failed: {stats['failed_checks']}</p>
        <p>Compliance Rate: {stats['compliance_rate']:.2%}</p>
        <p>Overall Status: {stats['overall_status']}</p>
    </div>

    <h3>Compliance Checks</h3>
"""

        for check in checks:
            status_class = "pass" if check.status == ComplianceStatus.COMPLIANT else "fail"
            html += f"""
    <div class="check {status_class}">
        <h4>{check.rule_id}</h4>
        <p>Status: {check.status.value}</p>
        <p>Checked: {check.checked_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
"""

            if config.include_recommendations and check.findings:
                html += f"""
        <div class="findings">
            <strong>Findings:</strong>
            <ul>
"""
                for finding in check.findings:
                    html += f"                <li>{finding}</li>\n"
                html += "            </ul>\n        </div>\n"

            if config.include_recommendations and check.recommendations:
                html += f"""
        <div class="recommendations">
            <strong>Recommendations:</strong>
            <ul>
"""
                for rec in check.recommendations:
                    html += f"                <li>{rec}</li>\n"
                html += "            </ul>\n        </div>\n"

            html += "    </div>\n"

        html += """
</body>
</html>
"""
        return html

    def _generate_markdown_report(
        self,
        framework: ComplianceFramework,
        period_start: datetime,
        period_end: datetime,
        checks: List[ComplianceCheck],
        stats: Dict[str, Any],
        config: ReportConfig,
        additional_data: Optional[Dict[str, Any]],
    ) -> str:
        """Generate Markdown format report"""
        md = f"""# Compliance Report - {framework.value.upper()}

**Period:** {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}
**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

## Summary

- **Total Checks:** {stats['total_checks']}
- **Passed:** {stats['passed_checks']}
- **Failed:** {stats['failed_checks']}
- **Compliance Rate:** {stats['compliance_rate']:.2%}
- **Overall Status:** {stats['overall_status']}

## Compliance Checks

"""

        for check in checks:
            status_icon = "✅" if check.status == ComplianceStatus.COMPLIANT else "❌"
            md += f"### {status_icon} {check.rule_id}\n\n"
            md += f"- **Status:** {check.status.value}\n"
            md += f"- **Checked:** {check.checked_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

            if config.include_recommendations and check.findings:
                md += "\n**Findings:**\n"
                for finding in check.findings:
                    md += f"- {finding}\n"

            if config.include_recommendations and check.recommendations:
                md += "\n**Recommendations:**\n"
                for rec in check.recommendations:
                    md += f"- {rec}\n"

            md += "\n"

        return md

    def _generate_csv_report(
        self,
        framework: ComplianceFramework,
        period_start: datetime,
        period_end: datetime,
        checks: List[ComplianceCheck],
        stats: Dict[str, Any],
        config: ReportConfig,
        additional_data: Optional[Dict[str, Any]],
    ) -> str:
        """Generate CSV format report"""
        csv = "Check ID,Rule ID,Status,Checked At"

        if config.include_recommendations:
            csv += ",Findings,Recommendations"

        csv += "\n"

        for check in checks:
            row = f"{check.check_id},{check.rule_id},{check.status.value},{check.checked_at.isoformat()}"

            if config.include_recommendations:
                findings_str = "; ".join(check.findings) if check.findings else ""
                recommendations_str = "; ".join(check.recommendations) if check.recommendations else ""
                row += f',"{findings_str}","{recommendations_str}"'

            csv += row + "\n"

        return csv

    def _get_file_extension(self, format: ReportFormat) -> str:
        """Get file extension for format"""
        extensions = {
            ReportFormat.JSON: "json",
            ReportFormat.HTML: "html",
            ReportFormat.PDF: "pdf",
            ReportFormat.CSV: "csv",
            ReportFormat.MARKDOWN: "md",
        }
        return extensions.get(format, "json")

    def get_report(self, report_id: str) -> Optional[GeneratedReport]:
        """
        Get a generated report

        Args:
            report_id: Report identifier

        Returns:
            Generated report or None
        """
        return self.reports.get(report_id)

    def list_reports(
        self,
        framework: Optional[ComplianceFramework] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List generated reports

        Args:
            framework: Filter by framework
            limit: Maximum number of results

        Returns:
            List of reports
        """
        reports = list(self.reports.values())

        if framework:
            reports = [r for r in reports if r.framework == framework]

        reports = reports[-limit:]

        return [
            {
                "report_id": r.report_id,
                "report_type": r.report_type.value,
                "format": r.format.value,
                "framework": r.framework.value,
                "period_start": r.period_start.isoformat(),
                "period_end": r.period_end.isoformat(),
                "generated_at": r.generated_at.isoformat(),
                "file_path": r.file_path,
                "metadata": r.metadata,
            }
            for r in reports
        ]

    def delete_report(self, report_id: str) -> bool:
        """
        Delete a generated report

        Args:
            report_id: Report identifier

        Returns:
            True if successful
        """
        if report_id not in self.reports:
            return False

        report = self.reports[report_id]

        # Delete file if it exists
        if report.file_path and Path(report.file_path).exists():
            Path(report.file_path).unlink()

        del self.reports[report_id]

        logger.info(f"Deleted report: {report_id}")

        return True

    async def generate_executive_summary(
        self,
        framework: ComplianceFramework,
        period_start: datetime,
        period_end: datetime,
        checks: List[ComplianceCheck],
        trend_data: Optional[List[Dict[str, Any]]] = None,
    ) -> GeneratedReport:
        """
        Generate executive summary report

        Args:
            framework: Compliance framework
            period_start: Report period start
            period_end: Report period end
            checks: Compliance check results
            trend_data: Trend analysis data

        Returns:
            Generated executive summary
        """
        config = ReportConfig(report_type=ReportType.EXECUTIVE, format=ReportFormat.MARKDOWN)

        stats = self._calculate_statistics(checks)

        # Generate executive summary content
        md = f"""# Executive Compliance Summary - {framework.value.upper()}

**Reporting Period:** {period_start.strftime('%B %Y')}

## Executive Overview

This report provides a high-level overview of compliance status for {framework.value.upper()} requirements during the period of {period_start.strftime('%B %d, %Y')} to {period_end.strftime('%B %d, %Y')}.

## Key Metrics

- **Overall Compliance Rate:** {stats['compliance_rate']:.1%}
- **Total Compliance Checks:** {stats['total_checks']}
- **Passed Checks:** {stats['passed_checks']}
- **Failed Checks:** {stats['failed_checks']}
- **Overall Status:** {stats['overall_status'].upper()}

## Risk Assessment

"""

        # Add risk assessment based on compliance rate
        if stats['compliance_rate'] >= 0.95:
            md += "The organization demonstrates strong compliance posture with minimal risk exposure.\n\n"
        elif stats['compliance_rate'] >= 0.80:
            md += "The organization maintains acceptable compliance levels with moderate risk exposure.\n\n"
        else:
            md += "The organization has significant compliance gaps that require immediate attention.\n\n"

        # Add trend analysis if available
        if trend_data:
            md += "## Trend Analysis\n\n"
            md += "Compliance performance over the reporting period shows "
            if len(trend_data) >= 2:
                first_rate = trend_data[0].get('compliance_rate', 0)
                last_rate = trend_data[-1].get('compliance_rate', 0)
                if last_rate > first_rate:
                    md += "an **improving trend**.\n\n"
                elif last_rate < first_rate:
                    md += "a **declining trend**.\n\n"
                else:
                    md += "a **stable trend**.\n\n"
            else:
                md += "insufficient data for trend analysis.\n\n"

        # Add critical issues
        failed_checks = [c for c in checks if c.status != ComplianceStatus.COMPLIANT]
        if failed_checks:
            md += "## Critical Issues Requiring Attention\n\n"
            for check in failed_checks[:5]:  # Top 5 issues
                md += f"- **{check.rule_id}:** {'; '.join(check.findings[:2])}\n"
            md += "\n"

        md += "## Recommendations\n\n"
        md += "1. Review and address failed compliance checks\n"
        md += "2. Implement corrective actions for identified gaps\n"
        md += "3. Schedule follow-up compliance assessments\n"
        md += "4. Update compliance documentation as needed\n"

        # Generate report
        return await self.generate_report(
            framework=framework,
            period_start=period_start,
            period_end=period_end,
            checks=checks,
            report_config=config,
            additional_data={"executive_summary": True},
        )
