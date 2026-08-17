# -*- coding: utf-8 -*-
"""
Integration tests for Hardware Log Analyzer
硬件日志分析器集成测试

Tests API integration, data flow, integration with auto_heal/repair_script_library,
and complete business workflows with real components.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

from extensions.hardware_remediation.hardware_log_analyzer import (
    HardwareVendor,
    ComponentType,
    SeverityLevel,
    LogEntry,
    ComponentIssue,
    AnalysisResult,
    HardwareLogAnalyzer,
    get_hardware_log_analyzer,
)
from core.auto_heal import RepairScript, repair_script_library, PlatformType, RiskLevel


class TestHardwareLogAnalyzerAutoHealIntegration:
    """Test integration with auto_heal repair script library"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test"""
        # Save original scripts
        original_scripts = dict(repair_script_library.scripts)
        yield
        # Restore original scripts
        repair_script_library.scripts = original_scripts

    def test_hardware_scripts_registered_in_library(self):
        """Test that hardware remediation scripts are registered in repair_script_library"""
        # Check for IPMI scripts
        ipmi_power_cycle = repair_script_library.get_script("ipmi_power_cycle")
        assert ipmi_power_cycle is not None
        assert ipmi_power_cycle.name == "IPMI Power Cycle"
        assert ipmi_power_cycle.risk_level == RiskLevel.HIGH
        assert ipmi_power_cycle.requires_approval is True

        ipmi_sensor = repair_script_library.get_script("ipmi_get_sensor")
        assert ipmi_sensor is not None
        assert ipmi_sensor.name == "IPMI Sensor Data"
        assert ipmi_sensor.risk_level == RiskLevel.LOW

        # Check for Redfish scripts
        redfish_reboot = repair_script_library.get_script("redfish_reboot")
        assert redfish_reboot is not None
        assert redfish_reboot.name == "Redfish / iDRAC / iLO Reboot"
        assert redfish_reboot.risk_level == RiskLevel.HIGH

        redfish_health = repair_script_library.get_script("redfish_health")
        assert redfish_health is not None
        assert redfish_health.name == "Redfish / iDRAC Health"
        assert redfish_health.risk_level == RiskLevel.LOW

        # Check for RAID scripts
        raid_rebuild = repair_script_library.get_script("raid_rebuild")
        assert raid_rebuild is not None
        assert raid_rebuild.name == "RAID Rebuild (StorCLI)"
        assert raid_rebuild.risk_level == RiskLevel.HIGH

        raid_status = repair_script_library.get_script("raid_status")
        assert raid_status is not None
        assert raid_status.name == "RAID Status"
        assert raid_status.risk_level == RiskLevel.LOW

        # Check for SMART scripts
        smart_test = repair_script_library.get_script("smart_test")
        assert smart_test is not None
        assert smart_test.name == "SMART Short Test"
        assert smart_test.risk_level == RiskLevel.HIGH

        smart_info = repair_script_library.get_script("smart_info")
        assert smart_info is not None
        assert smart_info.name == "SMART Info"
        assert smart_info.risk_level == RiskLevel.LOW

        # Check for K8s scripts
        k8s_cordon = repair_script_library.get_script("k8s_cordon")
        assert k8s_cordon is not None
        assert k8s_cordon.name == "K8s Cordon Node"
        assert k8s_cordon.risk_level == RiskLevel.MEDIUM

        k8s_drain = repair_script_library.get_script("k8s_drain")
        assert k8s_drain is not None
        assert k8s_drain.name == "K8s Drain Node"
        assert k8s_drain.risk_level == RiskLevel.HIGH

        k8s_uncordon = repair_script_library.get_script("k8s_uncordon")
        assert k8s_uncordon is not None
        assert k8s_uncordon.name == "K8s Uncordon Node"
        assert k8s_uncordon.risk_level == RiskLevel.LOW

        # Check for ticket scripts
        jira_ticket = repair_script_library.get_script("create_jira_ticket")
        assert jira_ticket is not None
        assert jira_ticket.name == "Create Jira Ticket"
        assert jira_ticket.risk_level == RiskLevel.LOW

        servicenow_ticket = repair_script_library.get_script("create_servicenow_ticket")
        assert servicenow_ticket is not None
        assert servicenow_ticket.name == "Create ServiceNow Ticket"
        assert servicenow_ticket.risk_level == RiskLevel.LOW

    def test_hardware_script_metadata(self):
        """Test that hardware scripts have correct metadata"""
        ipmi_script = repair_script_library.get_script("ipmi_power_cycle")
        assert ipmi_script.metadata["category"] == "hardware"
        assert ipmi_script.metadata["interface"] == "ipmi"

        redfish_script = repair_script_library.get_script("redfish_reboot")
        assert redfish_script.metadata["category"] == "hardware"
        assert redfish_script.metadata["interface"] == "redfish"

        raid_script = repair_script_library.get_script("raid_rebuild")
        assert raid_script.metadata["category"] == "hardware"
        assert raid_script.metadata["interface"] == "storcli"

        smart_script = repair_script_library.get_script("smart_test")
        assert smart_script.metadata["category"] == "hardware"
        assert smart_script.metadata["interface"] == "smartctl"

    def test_hardware_script_platforms(self):
        """Test that hardware scripts have correct platform support"""
        # IPMI scripts should support Linux
        ipmi_script = repair_script_library.get_script("ipmi_power_cycle")
        assert PlatformType.LINUX in ipmi_script.platforms

        # Redfish scripts should support Linux
        redfish_script = repair_script_library.get_script("redfish_reboot")
        assert PlatformType.LINUX in redfish_script.platforms

        # RAID scripts should support Linux
        raid_script = repair_script_library.get_script("raid_rebuild")
        assert PlatformType.LINUX in raid_script.platforms

        # SMART scripts should support Linux
        smart_script = repair_script_library.get_script("smart_test")
        assert PlatformType.LINUX in smart_script.platforms

        # K8s scripts should support Linux and Kubernetes
        k8s_drain = repair_script_library.get_script("k8s_drain")
        assert PlatformType.LINUX in k8s_drain.platforms
        assert PlatformType.KUBERNETES in k8s_drain.platforms

        # Ticket scripts should support multiple platforms
        jira_script = repair_script_library.get_script("create_jira_ticket")
        assert PlatformType.LINUX in jira_script.platforms
        assert PlatformType.WINDOWS in jira_script.platforms
        assert PlatformType.MACOS in jira_script.platforms

    def test_hardware_script_rollback(self):
        """Test that high-risk hardware scripts have rollback scripts"""
        ipmi_script = repair_script_library.get_script("ipmi_power_cycle")
        assert ipmi_script.rollback_script is not None
        assert "power on" in ipmi_script.rollback_script.lower()

        redfish_script = repair_script_library.get_script("redfish_reboot")
        assert redfish_script.rollback_script is not None

        raid_script = repair_script_library.get_script("raid_rebuild")
        assert raid_script.rollback_script is not None
        assert "stop rebuild" in raid_script.rollback_script.lower()

        k8s_cordon = repair_script_library.get_script("k8s_cordon")
        assert k8s_cordon.rollback_script is not None
        assert "uncordon" in k8s_cordon.rollback_script.lower()

        k8s_drain = repair_script_library.get_script("k8s_drain")
        assert k8s_drain.rollback_script is not None
        assert "uncordon" in k8s_drain.rollback_script.lower()


class TestHardwareLogAnalyzerDataFlow:
    """Test data flow through the hardware log analyzer"""

    def test_log_to_analysis_to_issue_flow(self):
        """Test complete flow from log input to issue output"""
        log_data = "Dell Inc. CPU 0 temperature critical"
        
        # Step 1: Analyze log
        analyzer = HardwareLogAnalyzer()
        result = analyzer.analyze_log(log_data)
        
        # Step 2: Verify analysis result
        assert result.vendor == HardwareVendor.DELL
        assert result.total_entries == 1
        
        # Step 3: Extract issue if any
        if result.issues:
            issue = result.issues[0]
            
            # Step 4: Verify issue properties
            assert issue.component == ComponentType.CPU
            assert issue.severity in (SeverityLevel.ERROR, SeverityLevel.CRITICAL)
            assert len(issue.repair_recommendations) > 0

    def test_multiple_logs_aggregation(self):
        """Test aggregating multiple log entries"""
        log_data = """Dell Inc. CPU 0 temperature critical
DIMM A1 ECC error
Disk 0 failure"""
        
        analyzer = HardwareLogAnalyzer()
        result = analyzer.analyze_log(log_data)
        
        assert result.total_entries == 3
        assert result.summary["total_entries"] == 3
        
        # Verify components analyzed
        assert result.summary["components_analyzed"] >= 1

    def test_analysis_result_serialization(self):
        """Test serializing analysis result to JSON"""
        log_data = "Dell Inc. CPU 0 temperature critical"
        analyzer = HardwareLogAnalyzer()
        result = analyzer.analyze_log(log_data)
        
        # Convert to dict manually (AnalysisResult is a dataclass)
        result_dict = {
            "vendor": result.vendor.value,
            "total_entries": result.total_entries,
            "issues": [
                {
                    "component": issue.component.value,
                    "severity": issue.severity.value,
                    "issue_type": issue.issue_type,
                    "description": issue.description,
                }
                for issue in result.issues
            ],
            "summary": result.summary,
            "analysis_timestamp": result.analysis_timestamp,
        }
        
        # Serialize to JSON
        json_str = json.dumps(result_dict, default=str)
        
        # Deserialize
        deserialized = json.loads(json_str)
        
        # Verify
        assert deserialized["vendor"] == "dell"
        assert deserialized["total_entries"] == 1

    def test_vendor_detection_in_data_flow(self):
        """Test vendor detection is part of data flow"""
        dell_log = "Dell PowerEdge: CPU 0 temperature critical"
        hp_log = "HP ProLiant: DIMM A1 ECC error"
        
        dell_analyzer = HardwareLogAnalyzer()
        dell_result = dell_analyzer.analyze_log(dell_log)
        
        hp_analyzer = HardwareLogAnalyzer()
        hp_result = hp_analyzer.analyze_log(hp_log)
        
        assert dell_result.vendor == HardwareVendor.DELL
        assert hp_result.vendor == HardwareVendor.HP

    def test_risk_assessment_in_data_flow(self):
        """Test risk assessment is calculated in data flow"""
        log_data = "Dell Inc. CPU 0 temperature critical"
        analyzer = HardwareLogAnalyzer()
        result = analyzer.analyze_log(log_data)
        
        if result.issues:
            issue = result.issues[0]
            assert issue.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.MEDIUM, RiskLevel.LOW)

    def test_repair_recommendations_generation(self):
        """Test repair recommendations are generated in data flow"""
        log_data = "Dell Inc. CPU 0 temperature critical"
        analyzer = HardwareLogAnalyzer()
        result = analyzer.analyze_log(log_data)
        
        if result.issues:
            issue = result.issues[0]
            assert len(issue.repair_recommendations) > 0


class TestHardwareLogAnalyzerBusinessWorkflows:
    """Test complete business workflows"""

    def test_cpu_failure_detection_workflow(self):
        """Test complete CPU failure detection and remediation workflow"""
        # Step 1: Detect CPU failure in logs
        cpu_log = "Dell Inc. CPU 0 temperature critical"
        analyzer = HardwareLogAnalyzer()
        result = analyzer.analyze_log(cpu_log)
        
        assert result.vendor == HardwareVendor.DELL
        assert result.total_entries == 1
        
        # Step 2: Check for repair script
        ipmi_power = repair_script_library.get_script("ipmi_power_cycle")
        assert ipmi_power is not None
        
        # Step 3: Verify repair recommendations
        if result.issues:
            issue = result.issues[0]
            assert len(issue.repair_recommendations) > 0

    def test_memory_failure_workflow(self):
        """Test memory failure detection and remediation workflow"""
        # Step 1: Detect memory failure
        memory_log = "HP ProLiant DIMM A1 ECC error"
        analyzer = HardwareLogAnalyzer()
        result = analyzer.analyze_log(memory_log)
        
        assert result.vendor == HardwareVendor.HP
        assert result.total_entries == 1
        
        # Step 2: Check for repair script
        ipmi_power = repair_script_library.get_script("ipmi_power_cycle")
        assert ipmi_power is not None
        
        # Step 3: Verify repair recommendations
        if result.issues:
            issue = result.issues[0]
            assert len(issue.repair_recommendations) > 0

    def test_storage_failure_workflow(self):
        """Test storage failure detection and remediation workflow"""
        # Step 1: Detect storage failure
        storage_log = "Dell Inc. Disk 0 failure"
        analyzer = HardwareLogAnalyzer()
        result = analyzer.analyze_log(storage_log)
        
        assert result.vendor == HardwareVendor.DELL
        assert result.total_entries == 1
        
        # Step 2: Check for SMART script
        smart_info = repair_script_library.get_script("smart_info")
        assert smart_info is not None
        
        # Step 3: Verify repair recommendations
        if result.issues:
            issue = result.issues[0]
            assert len(issue.repair_recommendations) > 0

    def test_power_failure_workflow(self):
        """Test power failure detection and remediation workflow"""
        # Step 1: Detect power failure
        power_log = "Dell Inc. Power supply 0 failure"
        analyzer = HardwareLogAnalyzer()
        result = analyzer.analyze_log(power_log)
        
        assert result.vendor == HardwareVendor.DELL
        assert result.total_entries == 1
        
        # Step 2: Verify critical severity
        if result.issues:
            issue = result.issues[0]
            assert issue.severity in (SeverityLevel.CRITICAL, SeverityLevel.ERROR)

    def test_multi_vendor_detection_workflow(self):
        """Test workflow with multiple vendor logs"""
        dell_log = "Dell PowerEdge: CPU 0 temperature critical"
        hp_log = "HP ProLiant: DIMM A1 ECC error"
        
        dell_analyzer = HardwareLogAnalyzer()
        dell_result = dell_analyzer.analyze_log(dell_log)
        
        hp_analyzer = HardwareLogAnalyzer()
        hp_result = hp_analyzer.analyze_log(hp_log)
        
        # Verify vendor-specific detection
        assert dell_result.vendor == HardwareVendor.DELL
        assert hp_result.vendor == HardwareVendor.HP

    def test_complete_analysis_pipeline(self):
        """Test complete analysis pipeline from log collection to action recommendation"""
        # Simulate log collection from multiple sources
        logs = [
            "Dell Inc. CPU 0 temperature critical",
            "HP ProLiant DIMM A1 ECC error",
            "Lenovo ThinkSystem Disk 0 failure",
            "Cisco UCS NIC 0 link down",
        ]
        
        results = []
        for log in logs:
            analyzer = HardwareLogAnalyzer()
            results.append(analyzer.analyze_log(log))
        
        # Verify all sources analyzed
        assert len(results) == 4
        assert all(r.total_entries == 1 for r in results)
        
        # Verify vendors detected
        vendors = [r.vendor for r in results]
        assert HardwareVendor.DELL in vendors
        assert HardwareVendor.HP in vendors
        assert HardwareVendor.LENOVO in vendors
        assert HardwareVendor.CISCO in vendors


class TestHardwareLogAnalyzerErrorHandling:
    """Test error handling in integration scenarios"""

    def test_handle_malformed_log_data(self):
        """Test handling malformed log data"""
        malformed_logs = [
            "",
            "   ",
            "\n\n\n",
        ]
        
        for log_data in malformed_logs:
            analyzer = HardwareLogAnalyzer()
            result = analyzer.analyze_log(log_data)
            
            # Should not raise exception
            assert result is not None
            assert isinstance(result, AnalysisResult)

    def test_handle_very_large_log(self):
        """Test handling very large log data"""
        large_log = "Dell Inc. CPU 0 temperature critical\n" * 1000
        analyzer = HardwareLogAnalyzer()
        result = analyzer.analyze_log(large_log)
        
        # Should process all lines (may filter some based on severity)
        assert result.total_entries == 1000

    def test_handle_special_characters_in_logs(self):
        """Test handling special characters in logs"""
        special_logs = [
            "Dell Inc. CPU 0 temperature critical \x00\x01\x02",
            "Dell Inc. CPU 0 temperature critical \n\t\r",
            "Dell Inc. CPU 0 temperature critical <>&\"'",
            "Dell Inc. CPU 0 temperature critical 中文日本語한국어",
        ]
        
        for log_data in special_logs:
            analyzer = HardwareLogAnalyzer()
            result = analyzer.analyze_log(log_data)
            
            # Should not raise exception
            assert result is not None


class TestHardwareLogAnalyzerRealWorldScenarios:
    """Test real-world usage scenarios"""

    def test_data_center_monitoring_scenario(self):
        """Test data center monitoring scenario"""
        # Simulate logs from multiple servers
        server_logs = {
            "server1": "Dell PowerEdge: CPU 0 temperature critical",
            "server2": "HP ProLiant: Fan 0 failure",
            "server3": "Lenovo ThinkSystem: DIMM A1 ECC error",
            "server4": "Cisco UCS: Power supply 0 failure",
        }
        
        results = {}
        for server, log in server_logs.items():
            analyzer = HardwareLogAnalyzer()
            results[server] = analyzer.analyze_log(log)
        
        # Verify all servers analyzed
        assert len(results) == 4
        
        # Verify vendors detected
        vendors = [r.vendor for r in results.values()]
        assert HardwareVendor.DELL in vendors
        assert HardwareVendor.HP in vendors
        assert HardwareVendor.LENOVO in vendors
        assert HardwareVendor.CISCO in vendors

    def test_mixed_log_sources_scenario(self):
        """Test scenario with mixed log sources"""
        logs = [
            "Dell Inc. CPU 0 temperature critical",
            "HP ProLiant System Status Critical",
            "Lenovo ThinkSystem Drive State Failed",
            "Cisco UCS SMART overall-health self-assessment test result: FAILED",
        ]
        
        results = []
        for log in logs:
            analyzer = HardwareLogAnalyzer()
            results.append(analyzer.analyze_log(log))
        
        # Verify all sources processed
        assert len(results) == 4
        assert all(r.total_entries == 1 for r in results)

    def test_vendor_specific_workflow(self):
        """Test vendor-specific workflow"""
        dell_log = "Dell PowerEdge R740: CPU 0 temperature critical"
        
        analyzer = HardwareLogAnalyzer()
        result = analyzer.analyze_log(dell_log)
        
        # Verify Dell vendor detected
        assert result.vendor == HardwareVendor.DELL


class TestHardwareLogAnalyzerCrossComponentIntegration:
    """Test integration across different components"""

    def test_log_analyzer_to_repair_script_mapping(self):
        """Test mapping from log analyzer issues to repair scripts"""
        # Test CPU issue -> IPMI script
        cpu_log = "Dell Inc. CPU 0 temperature critical"
        analyzer = HardwareLogAnalyzer()
        result = analyzer.analyze_log(cpu_log)
        
        assert result.total_entries == 1
        
        # Verify corresponding script exists
        ipmi_power = repair_script_library.get_script("ipmi_power_cycle")
        assert ipmi_power is not None

    def test_risk_level_alignment(self):
        """Test risk level alignment between analyzer and repair scripts"""
        # Critical issue should map to high-risk script
        critical_log = "Dell Inc. CPU 0 temperature critical"
        analyzer = HardwareLogAnalyzer()
        result = analyzer.analyze_log(critical_log)
        
        if result.issues:
            assert result.issues[0].severity == SeverityLevel.CRITICAL
        
        # Verify corresponding high-risk script
        ipmi_power = repair_script_library.get_script("ipmi_power_cycle")
        assert ipmi_power.risk_level == RiskLevel.HIGH

    def test_approval_requirement_alignment(self):
        """Test approval requirement alignment"""
        # High-risk operations should require approval
        raid_log = "Dell Inc. RAID 0 degraded"
        analyzer = HardwareLogAnalyzer()
        result = analyzer.analyze_log(raid_log)
        
        # Verify rebuild script requires approval
        raid_rebuild = repair_script_library.get_script("raid_rebuild")
        assert raid_rebuild.requires_approval is True

    def test_platform_compatibility(self):
        """Test platform compatibility across components"""
        # K8s drain should work on both Linux and Kubernetes
        k8s_drain = repair_script_library.get_script("k8s_drain")
        assert PlatformType.LINUX in k8s_drain.platforms
        assert PlatformType.KUBERNETES in k8s_drain.platforms
        
        # Ticket scripts should work on all platforms
        jira_script = repair_script_library.get_script("create_jira_ticket")
        assert PlatformType.LINUX in jira_script.platforms
        assert PlatformType.WINDOWS in jira_script.platforms
        assert PlatformType.MACOS in jira_script.platforms


class TestHardwareLogAnalyzerRepairPlanGeneration:
    """Test repair plan generation"""

    def test_generate_repair_plan_single_issue(self):
        """Test generating repair plan for single issue"""
        analyzer = HardwareLogAnalyzer()
        
        issue = ComponentIssue(
            component=ComponentType.CPU,
            severity=SeverityLevel.CRITICAL,
            issue_type="thermal",
            description="CPU thermal issue",
            risk_level=RiskLevel.CRITICAL,
            repair_recommendations=["Check cooling"],
            script_keys=["ipmi_power_cycle"],
        )
        
        result = AnalysisResult(
            vendor=HardwareVendor.DELL,
            total_entries=1,
            issues=[issue],
            summary={"total_issues": 1},
        )
        
        plan = analyzer.generate_repair_plan(result)
        
        assert "analysis_summary" in plan
        assert "total_issues" in plan
        assert "prioritized_actions" in plan
        assert len(plan["prioritized_actions"]) == 1
        assert plan["requires_maintenance_window"] is True

    def test_generate_repair_plan_multiple_issues(self):
        """Test generating repair plan for multiple issues"""
        analyzer = HardwareLogAnalyzer()
        
        issues = [
            ComponentIssue(
                component=ComponentType.CPU,
                severity=SeverityLevel.CRITICAL,
                issue_type="thermal",
                description="CPU thermal issue",
                risk_level=RiskLevel.CRITICAL,
            ),
            ComponentIssue(
                component=ComponentType.MEMORY,
                severity=SeverityLevel.ERROR,
                issue_type="error",
                description="Memory error",
                risk_level=RiskLevel.HIGH,
            ),
            ComponentIssue(
                component=ComponentType.STORAGE,
                severity=SeverityLevel.WARNING,
                issue_type="warning",
                description="Storage warning",
                risk_level=RiskLevel.LOW,
            ),
        ]
        
        result = AnalysisResult(
            vendor=HardwareVendor.DELL,
            total_entries=3,
            issues=issues,
            summary={"total_issues": 3},
        )
        
        plan = analyzer.generate_repair_plan(result)
        
        assert len(plan["prioritized_actions"]) == 3
        # Critical should be first
        assert plan["prioritized_actions"][0]["priority"] == "critical"
        # Error should be second
        assert plan["prioritized_actions"][1]["priority"] == "high"
        # Warning should be last
        assert plan["prioritized_actions"][2]["priority"] == "medium"


class TestHardwareLogAnalyzerCommandValidation:
    """Test command validation integration"""

    def test_validate_safe_command(self):
        """Test validating safe command"""
        analyzer = HardwareLogAnalyzer()
        
        with patch('extensions.hardware_remediation.hardware_log_analyzer.analyze_command') as mock_analyze:
            mock_analyze.return_value = {"risk_level": RiskLevel.LOW, "reason": "Safe"}
            
            allowed, reason = analyzer.validate_repair_command("echo test")
            
            assert allowed is True

    def test_validate_dangerous_command(self):
        """Test validating dangerous command"""
        analyzer = HardwareLogAnalyzer()
        
        with patch('extensions.hardware_remediation.hardware_log_analyzer.analyze_command') as mock_analyze:
            mock_analyze.return_value = {"risk_level": RiskLevel.BLOCKED, "reason": "Dangerous"}
            
            allowed, reason = analyzer.validate_repair_command("rm -rf /")
            
            assert allowed is False

    def test_validate_high_risk_command(self):
        """Test validating high-risk command"""
        analyzer = HardwareLogAnalyzer()
        
        with patch('extensions.hardware_remediation.hardware_log_analyzer.analyze_command') as mock_analyze:
            mock_analyze.return_value = {"risk_level": RiskLevel.HIGH, "reason": "High risk"}
            
            allowed, reason = analyzer.validate_repair_command("systemctl restart critical-service")
            
            assert allowed is False
