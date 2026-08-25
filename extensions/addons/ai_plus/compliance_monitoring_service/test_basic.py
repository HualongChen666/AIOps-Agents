# -*- coding: utf-8 -*-
"""Basic test for Compliance Monitoring Service."""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from compliance_monitor import ComplianceMonitor, AlertSeverity
from policy_checker import PolicyChecker, PolicyType
from report_generator import ReportGenerator, ReportFormat, ReportType
from core.compliance_manager import ComplianceFramework, ComplianceStatus


async def test_compliance_monitor():
    """Test compliance monitor."""
    print("Testing Compliance Monitor...")
    
    monitor = ComplianceMonitor()
    
    # Test monitoring cycle
    checks = await monitor.run_monitoring_cycle()
    print(f"  [OK] Ran {len(checks)} compliance checks")
    
    # Test alerts
    alerts = monitor.get_alerts(limit=10)
    print(f"  [OK] Retrieved {len(alerts)} alerts")
    
    # Test trend analysis
    trend = monitor.get_trend_analysis(days=7)
    print(f"  [OK] Trend analysis: {trend['overall_trend']}")
    
    # Test statistics
    stats = monitor.get_statistics()
    print(f"  [OK] Statistics: {stats['total_alerts']} total alerts")
    
    print("[OK] Compliance Monitor tests passed\n")


async def test_policy_checker():
    """Test policy checker."""
    print("Testing Policy Checker...")
    
    checker = PolicyChecker()
    
    # Test getting policies
    policies = checker.get_policies()
    print(f"  [OK] Retrieved {len(policies)} policies")
    
    # Test checking a specific policy
    context = {
        "data_fields": ["name", "email", "phone"],
        "has_consent_tracking": True,
    }
    result = await checker.check_policy("gdpr_data_minimization", context)
    print(f"  [OK] Policy check result: {result.passed}")
    
    # Test checking all policies
    results = await checker.check_all_policies(framework=ComplianceFramework.GDPR)
    print(f"  [OK] Checked {len(results)} GDPR policies")
    
    print("[OK] Policy Checker tests passed\n")


async def test_report_generator():
    """Test report generator."""
    print("Testing Report Generator...")
    
    generator = ReportGenerator()
    
    # Create sample checks
    from core.compliance_manager import ComplianceCheck
    checks = [
        ComplianceCheck(
            check_id="check_1",
            rule_id="gdpr_data_minimization",
            status=ComplianceStatus.COMPLIANT,
            findings=[],
            recommendations=[],
        ),
        ComplianceCheck(
            check_id="check_2",
            rule_id="gdpr_consent_management",
            status=ComplianceStatus.NON_COMPLIANT,
            findings=["Consent tracking not implemented"],
            recommendations=["Implement consent tracking system"],
        ),
    ]
    
    # Test JSON report
    from report_generator import ReportConfig
    config = ReportConfig(format=ReportFormat.JSON)
    report = await generator.generate_report(
        framework=ComplianceFramework.GDPR,
        period_start=datetime.now(timezone.utc) - timedelta(days=30),
        period_end=datetime.now(timezone.utc),
        checks=checks,
        report_config=config,
    )
    print(f"  [OK] Generated JSON report: {report.report_id}")
    
    # Test HTML report
    config = ReportConfig(format=ReportFormat.HTML)
    report = await generator.generate_report(
        framework=ComplianceFramework.GDPR,
        period_start=datetime.now(timezone.utc) - timedelta(days=30),
        period_end=datetime.now(timezone.utc),
        checks=checks,
        report_config=config,
    )
    print(f"  [OK] Generated HTML report: {report.report_id}")
    
    # Test Markdown report
    config = ReportConfig(format=ReportFormat.MARKDOWN)
    report = await generator.generate_report(
        framework=ComplianceFramework.GDPR,
        period_start=datetime.now(timezone.utc) - timedelta(days=30),
        period_end=datetime.now(timezone.utc),
        checks=checks,
        report_config=config,
    )
    print(f"  [OK] Generated Markdown report: {report.report_id}")
    
    # Test listing reports
    reports = generator.list_reports()
    print(f"  [OK] Listed {len(reports)} reports")
    
    print("[OK] Report Generator tests passed\n")


async def test_integration():
    """Test integration with core compliance manager."""
    print("Testing Integration with Core...")
    
    from core.compliance_manager import get_compliance_manager
    
    manager = get_compliance_manager()
    
    # Test getting rules
    rules = manager.get_compliance_rules()
    print(f"  [OK] Retrieved {len(rules)} compliance rules from core")
    
    # Test running check
    checks = await manager.run_compliance_check(framework=ComplianceFramework.GDPR)
    print(f"  [OK] Ran {len(checks)} compliance checks via core")
    
    # Test statistics
    stats = manager.get_statistics()
    print(f"  [OK] Core statistics: {stats['total_rules']} rules, {stats['total_checks']} checks")
    
    print("[OK] Integration tests passed\n")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Compliance Monitoring Service - Basic Tests")
    print("=" * 60 + "\n")
    
    try:
        await test_compliance_monitor()
        await test_policy_checker()
        await test_report_generator()
        await test_integration()
        
        print("=" * 60)
        print("[OK] All tests passed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
