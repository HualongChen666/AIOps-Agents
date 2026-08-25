# -*- coding: utf-8 -*-
"""
Hardware Log Analyzer

Analyzes hardware logs from various vendors (Dell, HP, Lenovo, Cisco, Huawei)
to detect component failures and generate repair recommendations.

Features:
- Multi-vendor log parsing (Dell iDRAC, HP iLO, Lenovo XClarity, Cisco IMC, Huawei iBMC)
- Component pattern matching (CPU, Memory, Storage, Network, Power, Cooling, Firmware, RAID)
- Integration with repair_script_library for automated remediation
- Risk assessment and repair recommendation generation
- Security integration with command_guard and verifier
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.auto_heal import RepairScript, repair_script_library
from core.command_guard import RiskLevel, analyze_command

logger = logging.getLogger(__name__)


class HardwareVendor(Enum):
    """Supported hardware vendors"""
    DELL = "dell"
    HP = "hp"
    LENOVO = "lenovo"
    CISCO = "cisco"
    HUAWEI = "huawei"
    GENERIC = "generic"


class ComponentType(Enum):
    """Hardware component types"""
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"
    POWER = "power"
    COOLING = "cooling"
    FIRMWARE = "firmware"
    RAID = "raid"
    MOTHERBOARD = "motherboard"
    CHASSIS = "chassis"


class SeverityLevel(Enum):
    """Log severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LogEntry:
    """Individual log entry"""
    timestamp: str
    severity: SeverityLevel
    component: ComponentType
    message: str
    vendor: HardwareVendor
    raw_line: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComponentIssue:
    """Detected hardware component issue"""
    component: ComponentType
    severity: SeverityLevel
    issue_type: str
    description: str
    affected_units: List[str] = field(default_factory=list)
    log_entries: List[LogEntry] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    repair_recommendations: List[str] = field(default_factory=list)
    script_keys: List[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Complete hardware log analysis result"""
    vendor: HardwareVendor
    total_entries: int
    issues: List[ComponentIssue]
    summary: Dict[str, Any] = field(default_factory=dict)
    analysis_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class HardwareLogAnalyzer:
    """
    Hardware log analyzer for multi-vendor systems
    
    Supports:
    - Dell iDRAC logs
    - HP iLO logs
    - Lenovo XClarity logs
    - Cisco IMC logs
    - Huawei iBMC logs
    - Generic syslog format
    """

    def __init__(self):
        self._vendor_patterns = self._initialize_vendor_patterns()
        self._component_patterns = self._initialize_component_patterns()
        self._repair_mapping = self._initialize_repair_mapping()

    def _initialize_vendor_patterns(self) -> Dict[HardwareVendor, List[re.Pattern]]:
        """Initialize vendor-specific log patterns"""
        return {
            HardwareVendor.DELL: [
                re.compile(r"iDRAC", re.IGNORECASE),
                re.compile(r"Dell Inc\.|DELL", re.IGNORECASE),
                re.compile(r"System E-Series|PowerEdge", re.IGNORECASE),
                re.compile(r"RAC0179|RAC0218", re.IGNORECASE),
            ],
            HardwareVendor.HP: [
                re.compile(r"iLO|Integrated Lights-Out", re.IGNORECASE),
                re.compile(r"Hewlett Packard|HP\s+ProLiant", re.IGNORECASE),
                re.compile(r"ProLiant|BL\d+c", re.IGNORECASE),
                re.compile(r"ILO\d+", re.IGNORECASE),
            ],
            HardwareVendor.LENOVO: [
                re.compile(r"XClarity|XCC", re.IGNORECASE),
                re.compile(r"Lenovo|ThinkSystem", re.IGNORECASE),
                re.compile(r"ThinkServer|System x", re.IGNORECASE),
            ],
            HardwareVendor.CISCO: [
                re.compile(r"CIMC|UCS", re.IGNORECASE),
                re.compile(r"Cisco Systems", re.IGNORECASE),
                re.compile(r"UCS\s+[A-Z]", re.IGNORECASE),
            ],
            HardwareVendor.HUAWEI: [
                re.compile(r"iBMC|BMC", re.IGNORECASE),
                re.compile(r"Huawei|Huawei Technologies", re.IGNORECASE),
                re.compile(r"FusionServer|2288H", re.IGNORECASE),
            ],
            HardwareVendor.GENERIC: [
                re.compile(r"syslog|kernel", re.IGNORECASE),
            ],
        }

    def _initialize_component_patterns(self) -> Dict[ComponentType, Dict[str, Any]]:
        """Initialize component detection patterns and severity rules"""
        return {
            ComponentType.CPU: {
                "patterns": [
                    re.compile(r"CPU\s+\d+|processor\s+\d+", re.IGNORECASE),
                    re.compile(r"thermal\s+trip|overheat|temperature", re.IGNORECASE),
                    re.compile(r"machine\s+check|MCE|CPU\s+error", re.IGNORECASE),
                    re.compile(r"core\s+disabled|degraded", re.IGNORECASE),
                    re.compile(r"CPU\s+failure|processor\s+failure", re.IGNORECASE),
                ],
                "severity_keywords": {
                    SeverityLevel.CRITICAL: ["failure", "error", "trip", "disabled"],
                    SeverityLevel.ERROR: ["degraded", "warning", "high temp"],
                    SeverityLevel.WARNING: ["threshold", "elevated"],
                },
            },
            ComponentType.MEMORY: {
                "patterns": [
                    re.compile(r"DIMM\s+[A-Z]\d+|memory\s+module", re.IGNORECASE),
                    re.compile(r"ECC\s+error|correctable|uncorrectable", re.IGNORECASE),
                    re.compile(r"memory\s+failure|DIMM\s+failure", re.IGNORECASE),
                    re.compile(r"single-bit|double-bit", re.IGNORECASE),
                    re.compile(r"parity\s+error", re.IGNORECASE),
                ],
                "severity_keywords": {
                    SeverityLevel.CRITICAL: ["uncorrectable", "failure", "double-bit"],
                    SeverityLevel.ERROR: ["correctable", "single-bit", "ECC"],
                    SeverityLevel.WARNING: ["threshold", "usage"],
                },
            },
            ComponentType.STORAGE: {
                "patterns": [
                    re.compile(r"disk\s+\d+|drive\s+\d+|SD\s+[A-Z]", re.IGNORECASE),
                    re.compile(r"SMART\s+error|predict\s+failure", re.IGNORECASE),
                    re.compile(r"media\s+error|read\s+error|write\s+error", re.IGNORECASE),
                    re.compile(r"RAID\s+degraded|rebuild\s+failed", re.IGNORECASE),
                    re.compile(r"drive\s+failure|disk\s+failure", re.IGNORECASE),
                ],
                "severity_keywords": {
                    SeverityLevel.CRITICAL: ["failure", "predict failure", "critical"],
                    SeverityLevel.ERROR: ["degraded", "rebuild", "SMART error"],
                    SeverityLevel.WARNING: ["threshold", "slow", "retry"],
                },
            },
            ComponentType.NETWORK: {
                "patterns": [
                    re.compile(r"NIC\s+\d+|port\s+\d+|ethernet", re.IGNORECASE),
                    re.compile(r"link\s+down|cable\s+disconnect", re.IGNORECASE),
                    re.compile(r"network\s+error|tx\s+error|rx\s+error", re.IGNORECASE),
                    re.compile(r"MAC\s+address|phy\s+error", re.IGNORECASE),
                    re.compile(r"connectivity\s+loss", re.IGNORECASE),
                ],
                "severity_keywords": {
                    SeverityLevel.CRITICAL: ["link down", "disconnect", "failure"],
                    SeverityLevel.ERROR: ["error", "high rate", "collision"],
                    SeverityLevel.WARNING: ["threshold", "degraded"],
                },
            },
            ComponentType.POWER: {
                "patterns": [
                    re.compile(r"power\s+supply\s+\d+|PSU\s+\d+", re.IGNORECASE),
                    re.compile(r"power\s+failure|PSU\s+failure", re.IGNORECASE),
                    re.compile(r"voltage\s+error|overvoltage|undervoltage", re.IGNORECASE),
                    re.compile(r"power\s+redundancy\s+lost", re.IGNORECASE),
                    re.compile(r"AC\s+loss|DC\s+loss", re.IGNORECASE),
                ],
                "severity_keywords": {
                    SeverityLevel.CRITICAL: ["failure", "lost", "AC loss", "DC loss"],
                    SeverityLevel.ERROR: ["voltage", "redundancy"],
                    SeverityLevel.WARNING: ["threshold", "load"],
                },
            },
            ComponentType.COOLING: {
                "patterns": [
                    re.compile(r"fan\s+\d+|cooling\s+fan", re.IGNORECASE),
                    re.compile(r"fan\s+failure|fan\s+error", re.IGNORECASE),
                    re.compile(r"temperature\s+high|overheat", re.IGNORECASE),
                    re.compile(r"thermal\s+shutdown|thermal\s+event", re.IGNORECASE),
                    re.compile(r"airflow\s+error", re.IGNORECASE),
                ],
                "severity_keywords": {
                    SeverityLevel.CRITICAL: ["failure", "shutdown", "overheat"],
                    SeverityLevel.ERROR: ["error", "high", "thermal"],
                    SeverityLevel.WARNING: ["threshold", "slow"],
                },
            },
            ComponentType.FIRMWARE: {
                "patterns": [
                    re.compile(r"BIOS|firmware|ROM", re.IGNORECASE),
                    re.compile(r"firmware\s+update|flash\s+error", re.IGNORECASE),
                    re.compile(r"BIOS\s+error|ROM\s+error", re.IGNORECASE),
                    re.compile(r"corruption|checksum\s+error", re.IGNORECASE),
                    re.compile(r"version\s+mismatch", re.IGNORECASE),
                ],
                "severity_keywords": {
                    SeverityLevel.CRITICAL: ["corruption", "checksum error"],
                    SeverityLevel.ERROR: ["error", "flash error", "mismatch"],
                    SeverityLevel.WARNING: ["update", "old version"],
                },
            },
            ComponentType.RAID: {
                "patterns": [
                    re.compile(r"RAID\s+\d+|virtual\s+disk", re.IGNORECASE),
                    re.compile(r"RAID\s+degraded|rebuild\s+required", re.IGNORECASE),
                    re.compile(r"controller\s+error|battery\s+error", re.IGNORECASE),
                    re.compile(r"write\s+cache|BBU", re.IGNORECASE),
                    re.compile(r"array\s+failure", re.IGNORECASE),
                ],
                "severity_keywords": {
                    SeverityLevel.CRITICAL: ["array failure", "controller failure"],
                    SeverityLevel.ERROR: ["degraded", "rebuild", "battery"],
                    SeverityLevel.WARNING: ["cache", "threshold"],
                },
            },
            ComponentType.MOTHERBOARD: {
                "patterns": [
                    re.compile(r"motherboard|system\s+board", re.IGNORECASE),
                    re.compile(r"chipset\s+error|PCI\s+error", re.IGNORECASE),
                    re.compile(r"board\s+failure|system\s+failure", re.IGNORECASE),
                    re.compile(r"spurious\s+interrupt|NMI", re.IGNORECASE),
                ],
                "severity_keywords": {
                    SeverityLevel.CRITICAL: ["failure", "NMI"],
                    SeverityLevel.ERROR: ["error", "chipset"],
                    SeverityLevel.WARNING: ["threshold"],
                },
            },
            ComponentType.CHASSIS: {
                "patterns": [
                    re.compile(r"chassis|enclosure", re.IGNORECASE),
                    re.compile(r"intrusion|door\s+open", re.IGNORECASE),
                    re.compile(r"chassis\s+error|enclosure\s+error", re.IGNORECASE),
                    re.compile(r"thermal\s+shutdown", re.IGNORECASE),
                ],
                "severity_keywords": {
                    SeverityLevel.CRITICAL: ["failure", "shutdown"],
                    SeverityLevel.ERROR: ["error", "intrusion"],
                    SeverityLevel.WARNING: ["open", "threshold"],
                },
            },
        }

    def _initialize_repair_mapping(self) -> Dict[ComponentType, Dict[str, Any]]:
        """Initialize component to repair script mapping"""
        return {
            ComponentType.CPU: {
                "scripts": ["ipmi_power_cycle", "redfish_reboot"],
                "recommendations": [
                    "Check CPU thermal sensors and cooling system",
                    "Verify CPU seating and thermal paste",
                    "Consider power cycling the server",
                    "If persistent, replace affected CPU",
                ],
            },
            ComponentType.MEMORY: {
                "scripts": ["ipmi_power_cycle", "redfish_reboot"],
                "recommendations": [
                    "Reseat the affected DIMM module",
                    "Run memory diagnostic (memtest86)",
                    "If uncorrectable errors persist, replace DIMM",
                    "Check memory controller on motherboard",
                ],
            },
            ComponentType.STORAGE: {
                "scripts": ["raid_check_consistency", "raid_rebuild", "smartctl_health_check"],
                "recommendations": [
                    "Run SMART health check on affected drive",
                    "If SMART predicts failure, replace drive immediately",
                    "For RAID arrays, initiate rebuild after replacement",
                    "Check backplane and cabling",
                ],
            },
            ComponentType.NETWORK: {
                "scripts": ["ipmi_power_cycle", "redfish_reboot"],
                "recommendations": [
                    "Check network cable connections",
                    "Verify switch port configuration",
                    "Reseat network interface card",
                    "Update NIC firmware if applicable",
                ],
            },
            ComponentType.POWER: {
                "scripts": ["ipmi_power_cycle", "redfish_reboot"],
                "recommendations": [
                    "Replace failed power supply unit",
                    "Verify power redundancy configuration",
                    "Check power distribution unit (PDU)",
                    "Ensure proper power load balancing",
                ],
            },
            ComponentType.COOLING: {
                "scripts": ["ipmi_get_sensor", "redfish_reboot"],
                "recommendations": [
                    "Replace failed fan module",
                    "Clean air filters and vents",
                    "Check ambient temperature in data center",
                    "Verify fan speed control settings",
                ],
            },
            ComponentType.FIRMWARE: {
                "scripts": ["firmware_update"],
                "recommendations": [
                    "Update to latest stable firmware version",
                    "Verify firmware checksum before update",
                    "Use vendor-recommended update procedure",
                    "Schedule maintenance window for update",
                ],
            },
            ComponentType.RAID: {
                "scripts": ["raid_check_consistency", "raid_rebuild", "raid_create_hot_spare"],
                "recommendations": [
                    "Check RAID controller logs",
                    "Replace failed drives and rebuild array",
                    "Verify RAID battery/flash cache",
                    "Update RAID controller firmware",
                ],
            },
            ComponentType.MOTHERBOARD: {
                "scripts": ["ipmi_power_cycle", "redfish_reboot"],
                "recommendations": [
                    "Check for peripheral card conflicts",
                    "Reseat expansion cards",
                    "If persistent, motherboard replacement required",
                    "Contact vendor for RMA",
                ],
            },
            ComponentType.CHASSIS: {
                "scripts": ["ipmi_get_sensor"],
                "recommendations": [
                    "Check chassis intrusion sensor",
                    "Verify all panels are properly closed",
                    "Check environmental sensors",
                    "Review physical security logs",
                ],
            },
        }

    def detect_vendor(self, log_content: str) -> HardwareVendor:
        """Detect hardware vendor from log content"""
        for vendor, patterns in self._vendor_patterns.items():
            for pattern in patterns:
                if pattern.search(log_content):
                    logger.debug(f"Detected vendor: {vendor.value}")
                    return vendor
        logger.debug("Using generic vendor detection")
        return HardwareVendor.GENERIC

    def parse_log_line(self, line: str, vendor: HardwareVendor) -> Optional[LogEntry]:
        """Parse a single log line into structured LogEntry"""
        if not line or not line.strip():
            return None

        line = line.strip()
        
        # Extract timestamp (common formats)
        timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}',
            r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}',
            r'\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}',
        ]
        timestamp = "unknown"
        for ts_pattern in timestamp_patterns:
            match = re.search(ts_pattern, line)
            if match:
                timestamp = match.group(0)
                break

        # Determine severity
        severity = SeverityLevel.INFO
        if re.search(r"critical|fatal|emergency", line, re.IGNORECASE):
            severity = SeverityLevel.CRITICAL
        elif re.search(r"error|fail|exception", line, re.IGNORECASE):
            severity = SeverityLevel.ERROR
        elif re.search(r"warn|alert", line, re.IGNORECASE):
            severity = SeverityLevel.WARNING

        # Detect component
        component = self._detect_component(line)

        return LogEntry(
            timestamp=timestamp,
            severity=severity,
            component=component,
            message=line,
            vendor=vendor,
            raw_line=line,
            metadata={"parsed": True},
        )

    def _detect_component(self, line: str) -> ComponentType:
        """Detect which component the log line refers to"""
        for component, config in self._component_patterns.items():
            for pattern in config["patterns"]:
                if pattern.search(line):
                    return component
        return ComponentType.CHASSIS  # Default fallback

    def _determine_severity(self, line: str, component: ComponentType) -> SeverityLevel:
        """Determine severity based on component-specific keywords"""
        component_config = self._component_patterns.get(component, {})
        severity_keywords = component_config.get("severity_keywords", {})
        
        for severity, keywords in severity_keywords.items():
            for keyword in keywords:
                if keyword.lower() in line.lower():
                    return severity
        
        return SeverityLevel.INFO

    def _parse_log_entries(self, log_content: str, vendor: Optional[HardwareVendor]) -> tuple:
        """
        Parse log content into entries and detect vendor.
        
        Args:
            log_content: Raw log content as string
            vendor: Optional vendor hint
            
        Returns:
            Tuple of (detected_vendor, log_entries, lines_count)
        """
        detected_vendor = vendor or self.detect_vendor(log_content)
        lines = log_content.split('\n')
        log_entries = []
        
        for line in lines:
            entry = self.parse_log_line(line, detected_vendor)
            if entry:
                log_entries.append(entry)
        
        return detected_vendor, log_entries, len(lines)

    def _group_entries_by_component(self, log_entries: List[LogEntry]) -> Dict[ComponentType, List[LogEntry]]:
        """
        Group log entries by component type.
        
        Args:
            log_entries: List of parsed log entries
            
        Returns:
            Dictionary mapping component types to their entries
        """
        component_entries: Dict[ComponentType, List[LogEntry]] = {}
        for entry in log_entries:
            if entry.component not in component_entries:
                component_entries[entry.component] = []
            component_entries[entry.component].append(entry)
        return component_entries

    def _analyze_all_components(self, component_entries: Dict[ComponentType, List[LogEntry]]) -> List[ComponentIssue]:
        """
        Analyze all components for issues.
        
        Args:
            component_entries: Dictionary of component entries
            
        Returns:
            List of all detected issues
        """
        issues = []
        for component, entries in component_entries.items():
            component_issues = self._analyze_component(component, entries)
            issues.extend(component_issues)
        return issues

    def _build_analysis_summary(self, detected_vendor: HardwareVendor, log_entries: List[LogEntry], 
                                component_entries: Dict[ComponentType, List[LogEntry]], 
                                issues: List[ComponentIssue], lines_count: int) -> Dict[str, Any]:
        """
        Build analysis summary dictionary.
        
        Args:
            detected_vendor: Detected hardware vendor
            log_entries: All parsed log entries
            component_entries: Grouped component entries
            issues: Detected issues
            lines_count: Total number of log lines
            
        Returns:
            Summary dictionary
        """
        return {
            "vendor": detected_vendor.value,
            "total_entries": len(log_entries),
            "components_analyzed": len(component_entries),
            "issues_found": len(issues),
            "critical_issues": sum(1 for i in issues if i.severity == SeverityLevel.CRITICAL),
            "error_issues": sum(1 for i in issues if i.severity == SeverityLevel.ERROR),
            "warning_issues": sum(1 for i in issues if i.severity == SeverityLevel.WARNING),
        }

    def analyze_log(self, log_content: str, vendor: Optional[HardwareVendor] = None) -> AnalysisResult:
        """
        Analyze hardware log content and detect issues
        
        Args:
            log_content: Raw log content as string
            vendor: Optional vendor hint (auto-detected if not provided)
            
        Returns:
            AnalysisResult with detected issues and recommendations
        """
        if not log_content:
            return AnalysisResult(
                vendor=HardwareVendor.GENERIC,
                total_entries=0,
                issues=[],
                summary={"error": "Empty log content"},
            )

        # Parse log entries
        detected_vendor, log_entries, lines_count = self._parse_log_entries(log_content, vendor)

        if not log_entries:
            return AnalysisResult(
                vendor=detected_vendor,
                total_entries=0,
                issues=[],
                summary={"warning": "No valid log entries parsed"},
            )

        # Group by component and detect issues
        component_entries = self._group_entries_by_component(log_entries)
        issues = self._analyze_all_components(component_entries)

        # Build summary
        summary = self._build_analysis_summary(detected_vendor, log_entries, component_entries, issues, lines_count)

        return AnalysisResult(
            vendor=detected_vendor,
            total_entries=len(log_entries),
            issues=issues,
            summary=summary,
            metadata={"log_lines": lines_count},
        )

    def _analyze_component(self, component: ComponentType, entries: List[LogEntry]) -> List[ComponentIssue]:
        """Analyze log entries for a specific component and identify issues"""
        issues = []
        
        # Filter entries with severity >= WARNING
        significant_entries = [e for e in entries if e.severity in (SeverityLevel.WARNING, SeverityLevel.ERROR, SeverityLevel.CRITICAL)]
        
        if not significant_entries:
            return issues

        # Group by issue type
        issue_groups: Dict[str, List[LogEntry]] = {}
        for entry in significant_entries:
            issue_type = self._classify_issue_type(entry)
            if issue_type not in issue_groups:
                issue_groups[issue_type] = []
            issue_groups[issue_type].append(entry)

        # Create ComponentIssue for each group
        for issue_type, group_entries in issue_groups.items():
            # Determine overall severity for this issue
            severity_order = [SeverityLevel.CRITICAL, SeverityLevel.ERROR, SeverityLevel.WARNING, SeverityLevel.INFO]
            max_severity = min(group_entries, key=lambda e: severity_order.index(e.severity)).severity
            
            # Extract affected units (e.g., CPU0, DIMM_A1)
            affected_units = self._extract_affected_units(group_entries)
            
            # Determine risk level
            risk_level = self._assess_risk(component, max_severity, issue_type)
            
            # Get repair recommendations
            repair_config = self._repair_mapping.get(component, {})
            recommendations = repair_config.get("recommendations", []).copy()
            script_keys = repair_config.get("scripts", []).copy()
            
            # Add specific recommendations based on issue type
            specific_recs = self._get_specific_recommendations(component, issue_type)
            recommendations.extend(specific_recs)

            issue = ComponentIssue(
                component=component,
                severity=max_severity,
                issue_type=issue_type,
                description=self._generate_issue_description(component, issue_type, max_severity),
                affected_units=affected_units,
                log_entries=group_entries,
                risk_level=risk_level,
                repair_recommendations=recommendations,
                script_keys=script_keys,
            )
            issues.append(issue)

        return issues

    def _classify_issue_type(self, entry: LogEntry) -> str:
        """
        Classify the type of issue from a log entry.
        
        Args:
            entry: Log entry to classify
            
        Returns:
            Issue type string
        """
        message = entry.message.lower()
        
        # Define issue type patterns
        issue_patterns = [
            (("failure", "fail"), "failure"),
            (("error",), "error"),
            (("warning", "warn"), "warning"),
            (("threshold",), "threshold_exceeded"),
            (("degraded",), "degraded"),
            (("overheat", "thermal", "temperature"), "thermal"),
            (("disconnect", "link down"), "connectivity_loss"),
        ]
        
        # Check each pattern
        for patterns, issue_type in issue_patterns:
            if any(pattern in message for pattern in patterns):
                return issue_type
        
        return "generic"

    def _extract_affected_units(self, entries: List[LogEntry]) -> List[str]:
        """Extract affected component identifiers from log entries"""
        units = set()
        
        # Common patterns for component identifiers
        patterns = [
            r'CPU\s*(\d+)',
            r'DIMM\s*([A-Z]\d+)',
            r'Disk\s*(\d+)',
            r'Fan\s*(\d+)',
            r'PSU\s*(\d+)',
            r'NIC\s*(\d+)',
            r'Port\s*(\d+)',
            r'Slot\s*(\d+)',
        ]
        
        for entry in entries:
            for pattern in patterns:
                matches = re.findall(pattern, entry.message, re.IGNORECASE)
                for match in matches:
                    units.add(match)
        
        return sorted(list(units))

    def _assess_risk(self, component: ComponentType, severity: SeverityLevel, issue_type: str) -> RiskLevel:
        """Assess risk level based on component, severity, and issue type"""
        if severity == SeverityLevel.CRITICAL:
            return RiskLevel.CRITICAL
        elif severity == SeverityLevel.ERROR:
            if component in (ComponentType.CPU, ComponentType.MOTHERBOARD, ComponentType.RAID):
                return RiskLevel.HIGH
            return RiskLevel.MEDIUM
        elif severity == SeverityLevel.WARNING:
            if issue_type in ("thermal", "threshold_exceeded"):
                return RiskLevel.MEDIUM
            return RiskLevel.LOW
        return RiskLevel.LOW

    def _get_specific_recommendations(self, component: ComponentType, issue_type: str) -> List[str]:
        """
        Get specific recommendations based on component and issue type.
        
        Args:
            component: Component type
            issue_type: Type of issue
            
        Returns:
            List of specific recommendations
        """
        # Define recommendation matrix
        recommendation_matrix = {
            (ComponentType.CPU, "thermal"): [
                "Immediate action: Check ambient temperature",
                "Verify all fans are operational",
                "Consider throttling CPU if thermal shutdown imminent",
            ],
            (ComponentType.MEMORY, "failure"): [
                "Immediate action: Backup data before DIMM replacement",
                "Test memory in different slot to rule out motherboard issue",
            ],
            (ComponentType.STORAGE, "failure"): [
                "Immediate action: Backup critical data",
                "Do not write to affected drive",
                "Prepare replacement drive of same or larger capacity",
            ],
            (ComponentType.RAID, "degraded"): [
                "Check RAID array status immediately",
                "Ensure hot spare is available if configured",
                "Schedule drive replacement during maintenance window",
            ],
        }
        
        return recommendation_matrix.get((component, issue_type), [])

    def _generate_issue_description(self, component: ComponentType, issue_type: str, severity: SeverityLevel) -> str:
        """Generate human-readable issue description"""
        component_name = component.value.capitalize()
        severity_name = severity.value.upper()
        
        descriptions = {
            "failure": f"{component_name} failure detected",
            "error": f"{component_name} error condition",
            "warning": f"{component_name} warning condition",
            "threshold_exceeded": f"{component_name} threshold exceeded",
            "degraded": f"{component_name} operating in degraded mode",
            "thermal": f"{component_name} thermal issue detected",
            "connectivity_loss": f"{component_name} connectivity loss",
            "generic": f"{component_name} issue detected",
        }
        
        base_desc = descriptions.get(issue_type, f"{component_name} issue")
        return f"[{severity_name}] {base_desc}"

    def get_repair_scripts_for_issue(self, issue: ComponentIssue) -> List[RepairScript]:
        """Get available repair scripts for a specific issue"""
        scripts = []
        
        for script_key in issue.script_keys:
            script = repair_script_library.get_script(script_key)
            if script:
                scripts.append(script)
        
        return scripts

    def validate_repair_command(self, command: str) -> Tuple[bool, str]:
        """
        Validate a repair command through command_guard
        
        Args:
            command: Command string to validate
            
        Returns:
            (is_allowed, reason) tuple
        """
        try:
            analysis = analyze_command(command)
            risk_level = analysis.get("risk_level")
            
            if risk_level == RiskLevel.BLOCKED:
                return False, f"Command blocked: {analysis.get('reason', 'Unknown reason')}"
            elif risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                return False, f"Command requires approval: {analysis.get('reason', 'High risk')}"
            
            return True, "Command allowed"
        except Exception as e:
            logger.error(f"Error validating command: {e}")
            return False, f"Validation error: {str(e)}"

    def generate_repair_plan(self, analysis_result: AnalysisResult) -> Dict[str, Any]:
        """
        Generate a comprehensive repair plan from analysis result
        
        Args:
            analysis_result: Result from analyze_log()
            
        Returns:
            Repair plan with prioritized actions
        """
        # Sort issues by severity and risk
        sorted_issues = sorted(
            analysis_result.issues,
            key=lambda i: (
                0 if i.severity == SeverityLevel.CRITICAL else
                1 if i.severity == SeverityLevel.ERROR else
                2 if i.severity == SeverityLevel.WARNING else 3
            )
        )

        repair_plan = {
            "analysis_summary": analysis_result.summary,
            "total_issues": len(sorted_issues),
            "prioritized_actions": [],
            "estimated_downtime": 0,
            "requires_maintenance_window": False,
        }

        for issue in sorted_issues:
            action = {
                "priority": "critical" if issue.severity == SeverityLevel.CRITICAL else (
                    "high" if issue.severity == SeverityLevel.ERROR else "medium"
                ),
                "component": issue.component.value,
                "issue_type": issue.issue_type,
                "description": issue.description,
                "affected_units": issue.affected_units,
                "risk_level": issue.risk_level.value,
                "recommendations": issue.repair_recommendations,
                "available_scripts": issue.script_keys,
                "requires_approval": issue.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL),
            }
            repair_plan["prioritized_actions"].append(action)

            # Check if maintenance window needed
            if action["requires_approval"]:
                repair_plan["requires_maintenance_window"] = True

        return repair_plan


def register_hardware_log_scripts() -> None:
    """
    Register hardware log analysis scripts in the global RepairScriptLibrary.
    This function is called during module initialization.
    """
    try:
        from core.repair_script_library import RepairScriptLibrary
        
        library = RepairScriptLibrary()
        
        # Register hardware log analysis script
        library.register_script(
            name="analyze_hardware_log",
            description="Analyze hardware logs to detect issues and generate repair recommendations",
            execute_func=lambda log_content: str(_hardware_log_analyzer.analyze_log(log_content)),
            dry_run_func=lambda log_content: str(_hardware_log_analyzer.analyze_log(log_content)),
            category="hardware",
            risk_level="low"
        )
        
        logger.info("Hardware log analysis scripts registered successfully")
    except ImportError:
        logger.warning("RepairScriptLibrary not available, skipping hardware log script registration")
    except Exception as e:
        logger.error(f"Error registering hardware log scripts: {e}")


# Global analyzer instance
_hardware_log_analyzer = HardwareLogAnalyzer()


def get_hardware_log_analyzer() -> HardwareLogAnalyzer:
    """Get the global hardware log analyzer instance"""
    return _hardware_log_analyzer
