# -*- coding: utf-8 -*-
"""
Security Testing System (Phase 4)
Enterprise-grade security testing system with automated vulnerability scanning
"""

import asyncio
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class TestType(Enum):
    """Security test type"""

    SAST = "sast"  # Static Application Security Testing
    DAST = "dast"  # Dynamic Application Security Testing
    SCA = "sca"  # Software Composition Analysis
    DEPENDENCY_SCAN = "dependency_scan"
    CONTAINER_SCAN = "container_scan"
    INFRASTRUCTURE_SCAN = "infrastructure_scan"
    PENETRATION_TEST = "penetration_test"
    CODE_REVIEW = "code_review"


class SeverityLevel(Enum):
    """Vulnerability severity level"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class TestStatus(Enum):
    """Security test status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SecurityTest:
    """Security test configuration"""

    test_id: str
    test_name: str
    test_type: TestType
    target: str
    enabled: bool = True
    schedule: str = "manual"
    timeout: int = 3600
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Vulnerability:
    """Vulnerability finding"""

    vulnerability_id: str
    title: str
    severity: SeverityLevel
    cwe_id: Optional[str] = None
    description: str = ""
    affected_component: str = ""
    remediation: str = ""
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Security test result"""

    test_id: str
    status: TestStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: float = 0.0
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Real security-tool adapters.
#
# Each adapter locates the tool binary on ``PATH``, runs it against the test
# target with ``shell=False`` and converts its machine readable output into
# findings.  A tool that is not installed is reported as unavailable; it is
# never replaced by synthetic results.
# ---------------------------------------------------------------------------


def _map_severity(raw: Any) -> SeverityLevel:
    """Translate a scanner severity label into :class:`SeverityLevel`."""
    label = str(raw or "").strip().upper()
    if label in {"CRITICAL", "BLOCKER"}:
        return SeverityLevel.CRITICAL
    if label in {"HIGH", "ERROR", "MAJOR"}:
        return SeverityLevel.HIGH
    if label in {"MEDIUM", "WARNING", "MODERATE"}:
        return SeverityLevel.MEDIUM
    if label in {"LOW", "MINOR"}:
        return SeverityLevel.LOW
    return SeverityLevel.INFO


def _json_loader(output: str) -> Any:
    """Parse a JSON document produced by a scanner."""
    text = output.strip()
    if not text:
        raise ValueError("scanner produced no output")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"scanner output is not valid JSON: {exc}") from exc


def _text_loader(output: str) -> str:
    return output


def _bandit_argv(test_type: TestType, target: str) -> List[str]:
    return ["bandit", "-r", target, "-f", "json", "-q"]


def _semgrep_argv(test_type: TestType, target: str) -> List[str]:
    return ["semgrep", "--config=auto", "--json", "--quiet", target]


def _trivy_argv(test_type: TestType, target: str) -> List[str]:
    if test_type is TestType.CONTAINER_SCAN:
        return ["trivy", "image", "-f", "json", "-q", target]
    if test_type is TestType.INFRASTRUCTURE_SCAN:
        return ["trivy", "config", "-f", "json", "-q", target]
    return ["trivy", "fs", "-f", "json", "-q", target]


def _safety_argv(test_type: TestType, target: str) -> List[str]:
    argv = ["safety", "check", "--json"]
    if target.endswith((".txt", ".toml", ".lock")):
        argv += ["--file", target]
    return argv


def _snyk_argv(test_type: TestType, target: str) -> List[str]:
    return ["snyk", "test", "--json"]


def _zap_argv(test_type: TestType, target: str) -> List[str]:
    return ["zap-baseline.py", "-t", target, "-J", "-"]


def _nmap_argv(test_type: TestType, target: str) -> List[str]:
    return ["nmap", "-Pn", "-oX", "-", target]


def _parse_bandit(payload: Any) -> List[Dict[str, Any]]:
    findings = []
    for item in (payload or {}).get("results", []):
        cwe = item.get("issue_cwe") or {}
        findings.append(
            {
                "vulnerability_id": item.get("test_id"),
                "title": item.get("issue_text") or "bandit finding",
                "severity": item.get("issue_severity"),
                "cwe_id": f"CWE-{cwe['id']}" if cwe.get("id") else None,
                "description": item.get("issue_text") or "",
                "affected_component": f"{item.get('filename')}:{item.get('line_number')}",
                "remediation": item.get("more_info") or "",
            }
        )
    return findings


def _parse_semgrep(payload: Any) -> List[Dict[str, Any]]:
    findings = []
    for item in (payload or {}).get("results", []):
        extra = item.get("extra") or {}
        metadata = extra.get("metadata") or {}
        cwe = metadata.get("cwe")
        if isinstance(cwe, list):
            cwe = cwe[0] if cwe else None
        findings.append(
            {
                "vulnerability_id": item.get("check_id"),
                "title": extra.get("message") or item.get("check_id"),
                "severity": extra.get("severity"),
                "cwe_id": cwe,
                "description": extra.get("message") or "",
                "affected_component": f"{item.get('path')}:{(item.get('start') or {}).get('line')}",
                "remediation": (extra.get("metadata") or {}).get("fix") or "",
            }
        )
    return findings


def _parse_trivy(payload: Any) -> List[Dict[str, Any]]:
    findings = []
    for result in (payload or {}).get("Results", []):
        for vuln in result.get("Vulnerabilities", []) or []:
            cwe_ids = vuln.get("CweIDs") or []
            fixed = vuln.get("FixedVersion")
            findings.append(
                {
                    "vulnerability_id": vuln.get("VulnerabilityID"),
                    "title": vuln.get("Title") or vuln.get("VulnerabilityID"),
                    "severity": vuln.get("Severity"),
                    "cwe_id": cwe_ids[0] if cwe_ids else None,
                    "description": vuln.get("Description") or "",
                    "affected_component": (
                        f"{vuln.get('PkgName')}@{vuln.get('InstalledVersion')}"
                    ),
                    "remediation": f"upgrade to {fixed}" if fixed else "",
                }
            )
    return findings


def _parse_safety(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        entries: List[Any] = payload.get("vulnerabilities") or []
    elif isinstance(payload, list):
        entries = payload
    else:
        entries = []

    findings = []
    for item in entries:
        if isinstance(item, dict):
            findings.append(
                {
                    "vulnerability_id": item.get("vulnerability_id") or item.get("cve"),
                    "title": item.get("advisory") or item.get("vulnerability_id") or "safety",
                    "severity": item.get("severity"),
                    "cwe_id": item.get("cwe"),
                    "description": item.get("advisory") or "",
                    "affected_component": (
                        f"{item.get('package_name') or item.get('package')}"
                        f"@{item.get('analyzed_version') or item.get('installed_version')}"
                    ),
                    "remediation": item.get("fixed_versions")
                    and f"upgrade to {item.get('fixed_versions')}"
                    or "",
                }
            )
        elif isinstance(item, (list, tuple)) and len(item) >= 4:
            # safety 1.x emits [package, specifier, installed, vuln_id, advisory]
            findings.append(
                {
                    "vulnerability_id": str(item[3]),
                    "title": str(item[4]) if len(item) > 4 else str(item[3]),
                    "severity": None,
                    "cwe_id": None,
                    "description": str(item[4]) if len(item) > 4 else "",
                    "affected_component": f"{item[0]}@{item[2]}",
                    "remediation": "",
                }
            )
    return findings


def _parse_snyk(payload: Any) -> List[Dict[str, Any]]:
    findings = []
    for item in (payload or {}).get("vulnerabilities", []):
        identifiers = item.get("identifiers") or {}
        cwe = identifiers.get("CWE") or []
        findings.append(
            {
                "vulnerability_id": item.get("id"),
                "title": item.get("title") or item.get("id"),
                "severity": item.get("severity"),
                "cwe_id": cwe[0] if cwe else None,
                "description": item.get("description") or "",
                "affected_component": item.get("packageName") or "",
                "remediation": item.get("upgradePath") and str(item.get("upgradePath")) or "",
            }
        )
    return findings


def _parse_zap(payload: Any) -> List[Dict[str, Any]]:
    findings = []
    for alert in (payload or {}).get("alerts", []):
        cwe_id = alert.get("cweid")
        findings.append(
            {
                "vulnerability_id": alert.get("pluginid") or alert.get("alertRef"),
                "title": alert.get("alert") or alert.get("name"),
                "severity": alert.get("riskdesc") or alert.get("risk"),
                "cwe_id": f"CWE-{cwe_id}" if cwe_id else None,
                "description": alert.get("desc") or "",
                "affected_component": alert.get("url") or "",
                "remediation": alert.get("solution") or "",
            }
        )
    return findings


def _parse_nmap(output: str) -> List[Dict[str, Any]]:
    findings = []
    text = output.strip()
    if not (text.startswith("<?xml") or text.startswith("<nmaprun")):
        return findings
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return findings
    for host in root.findall(".//host"):
        address = host.find(".//address")
        host_ip = address.get("addr") if address is not None else ""
        for port in host.findall(".//port"):
            state = port.find(".//state")
            if state is None or state.get("state") != "open":
                continue
            service = port.find(".//service")
            findings.append(
                {
                    "vulnerability_id": f"open-port-{port.get('portid')}",
                    "title": f"Exposed port {port.get('portid')}",
                    "severity": "MEDIUM",
                    "cwe_id": None,
                    "description": (
                        f"Port {port.get('portid')} is reachable on {host_ip} "
                        f"({service.get('name') if service is not None else 'unknown'})"
                    ),
                    "affected_component": f"{host_ip}:{port.get('portid')}",
                    "remediation": "Restrict the port to trusted networks",
                }
            )
    return findings


SCANNER_ADAPTERS: Dict[str, Dict[str, Any]] = {
    "bandit": {"argv": _bandit_argv, "loader": _json_loader, "parse": _parse_bandit},
    "semgrep": {"argv": _semgrep_argv, "loader": _json_loader, "parse": _parse_semgrep},
    "trivy": {"argv": _trivy_argv, "loader": _json_loader, "parse": _parse_trivy},
    "safety": {"argv": _safety_argv, "loader": _json_loader, "parse": _parse_safety},
    "snyk": {"argv": _snyk_argv, "loader": _json_loader, "parse": _parse_snyk},
    "owasp_zap": {"argv": _zap_argv, "loader": _json_loader, "parse": _parse_zap},
    "nmap": {"argv": _nmap_argv, "loader": _text_loader, "parse": _parse_nmap},
}


class SecurityTestingSystem:
    """Enterprise-grade security testing system"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize security testing system

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Security tests
        self.security_tests: Dict[str, SecurityTest] = {}
        self._initialize_default_tests()

        # Test results
        self.test_results: Dict[str, TestResult] = {}

        # Vulnerability database
        self.vulnerabilities: List[Vulnerability] = []

        # Report storage
        self.reports_dir = Path(self.config.get("reports_dir", "./security_reports"))
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Configuration
        self.auto_scan_enabled = self.config.get("auto_scan_enabled", True)
        self.scan_interval = self.config.get("scan_interval", 604800)  # 7 days

        # Statistics
        self.total_tests = 0
        self.total_vulnerabilities = 0
        self.critical_vulnerabilities = 0

        logger.info("Security testing system initialized")

    def _initialize_default_tests(self):
        """Initialize default security tests"""
        # SAST test
        self.security_tests["sast_scan"] = SecurityTest(
            test_id="sast_scan",
            test_name="Static Application Security Testing",
            test_type=TestType.SAST,
            target="source_code",
            enabled=True,
            schedule="weekly",
            config={"tools": ["bandit", "semgrep", "sonarqube"]},
        )

        # DAST test
        self.security_tests["dast_scan"] = SecurityTest(
            test_id="dast_scan",
            test_name="Dynamic Application Security Testing",
            test_type=TestType.DAST,
            target="web_application",
            enabled=True,
            schedule="weekly",
            config={"tools": ["owasp_zap", "burp_suite"]},
        )

        # SCA test
        self.security_tests["sca_scan"] = SecurityTest(
            test_id="sca_scan",
            test_name="Software Composition Analysis",
            test_type=TestType.SCA,
            target="dependencies",
            enabled=True,
            schedule="daily",
            config={"tools": ["snyk", "dependabot", "trivy"]},
        )

        # Dependency scan
        self.security_tests["dependency_scan"] = SecurityTest(
            test_id="dependency_scan",
            test_name="Dependency Security Scan",
            test_type=TestType.DEPENDENCY_SCAN,
            target="package_files",
            enabled=True,
            schedule="daily",
            config={"tools": ["safety", "audit"]},
        )

        # Container scan
        self.security_tests["container_scan"] = SecurityTest(
            test_id="container_scan",
            test_name="Container Security Scan",
            test_type=TestType.CONTAINER_SCAN,
            target="docker_images",
            enabled=True,
            schedule="on_build",
            config={"tools": ["trivy", "clair"]},
        )

        # Infrastructure scan
        self.security_tests["infrastructure_scan"] = SecurityTest(
            test_id="infrastructure_scan",
            test_name="Infrastructure Security Scan",
            test_type=TestType.INFRASTRUCTURE_SCAN,
            target="cloud_infrastructure",
            enabled=True,
            schedule="weekly",
            config={"tools": ["prowler", "scout"]},
        )

        logger.info(f"Initialized {len(self.security_tests)} default security tests")

    def register_test(self, test: SecurityTest) -> None:
        """
        Register security test

        Args:
            test: Security test configuration
        """
        self.security_tests[test.test_id] = test
        logger.info(f"Registered security test: {test.test_id}")

    async def run_security_test(self, test_id: str, target_override: Optional[str] = None) -> str:
        """
        Run security test

        Args:
            test_id: Test ID
            target_override: Override target (optional)

        Returns:
            Result ID
        """
        if test_id not in self.security_tests:
            raise ValueError(f"Test not found: {test_id}")

        self.security_tests[test_id]

        # Create test result
        result = TestResult(
            test_id=test_id, status=TestStatus.RUNNING, started_at=datetime.now(timezone.utc)
        )

        self.test_results[test_id] = result
        self.total_tests += 1

        logger.info(f"Starting security test: {test_id}")

        # Run test asynchronously
        asyncio.create_task(self._execute_test(test_id, target_override))

        return test_id

    async def _execute_test(self, test_id: str, target_override: Optional[str] = None) -> None:
        """
        Execute security test

        Args:
            test_id: Test ID
            target_override: Override target
        """
        if test_id not in self.test_results:
            return

        result = self.test_results[test_id]
        test = self.security_tests[test_id]

        try:
            # Execute the real scanners configured for this test.
            target = target_override or self._concrete_target(test)
            vulnerabilities = await self._run_scanners(test, target)

            # Update result
            result.status = TestStatus.COMPLETED
            result.completed_at = datetime.now(timezone.utc)
            if result.started_at is not None:
                result.duration = (result.completed_at - result.started_at).total_seconds()
            else:
                result.duration = 0.0
            result.vulnerabilities = vulnerabilities
            result.summary = {
                "total_vulnerabilities": len(vulnerabilities),
                "critical_count": len(
                    [v for v in vulnerabilities if v.severity == SeverityLevel.CRITICAL]
                ),
                "high_count": len([v for v in vulnerabilities if v.severity == SeverityLevel.HIGH]),
                "medium_count": len(
                    [v for v in vulnerabilities if v.severity == SeverityLevel.MEDIUM]
                ),
                "low_count": len([v for v in vulnerabilities if v.severity == SeverityLevel.LOW]),
            }

            # Update vulnerability database
            self.vulnerabilities.extend(vulnerabilities)
            self.total_vulnerabilities += len(vulnerabilities)
            self.critical_vulnerabilities += len(
                [v for v in vulnerabilities if v.severity == SeverityLevel.CRITICAL]
            )

            logger.info(
                f"Security test completed: {test_id}, found {len(vulnerabilities)} vulnerabilities"
            )

        except Exception as e:
            result.status = TestStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now(timezone.utc)
            if result.started_at is not None:
                result.duration = (result.completed_at - result.started_at).total_seconds()
            else:
                result.duration = 0.0

            logger.error(f"Security test failed: {test_id}, error: {e}")

    @staticmethod
    def _repository_root() -> Path:
        """Root of the deployed repository (used as the default scan target)."""
        return Path(__file__).resolve().parents[1]

    def _concrete_target(self, test: SecurityTest) -> str:
        """Resolve a concrete, existing target for ``test``.

        The default test catalogue uses abstract targets ("source_code",
        "docker_images", ...).  A concrete target is taken from
        ``test.config['target']`` when present, otherwise it is derived from the
        test type.  Tests that address a remote system (DAST, container,
        penetration) have no safe default and must be given an explicit target.
        """
        configured = test.config.get("target")
        if configured:
            return str(configured)

        if test.test_type in (
            TestType.SAST,
            TestType.CODE_REVIEW,
            TestType.INFRASTRUCTURE_SCAN,
        ):
            return str(self._repository_root())

        if test.test_type in (TestType.SCA, TestType.DEPENDENCY_SCAN):
            for candidate in ("requirements.txt", "pyproject.toml"):
                path = self._repository_root() / candidate
                if path.exists():
                    return str(path)
            return str(self._repository_root())

        raise RuntimeError(
            f"test {test.test_id} requires an explicit target: pass target_override "
            "to run_security_test() or set test.config['target']"
        )

    @staticmethod
    def _execute_scanner(adapter: Dict[str, Any], argv: List[str]) -> List[Dict[str, Any]]:
        """Run a scanner binary and parse its output (executed in a worker thread)."""
        completed = subprocess.run(  # noqa: S603 - argv is built from a static adapter
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            check=False,
            timeout=adapter.get("timeout", 1800),
        )
        output = completed.stdout or completed.stderr
        payload = adapter["loader"](output)
        return adapter["parse"](payload)

    async def _run_scanners(self, test: SecurityTest, target: str) -> List[Vulnerability]:
        """Run the first usable scanner declared in ``test.config['tools']``.

        A scanner is usable when it has a real adapter and its binary is
        installed.  When no scanner can be executed a :class:`RuntimeError` is
        raised so the test is reported as failed instead of silently passing
        with no findings.
        """
        tools = list(test.config.get("tools") or [])
        if not tools:
            raise RuntimeError(f"no scanner configured for test {test.test_id}")

        unavailable: List[str] = []
        for tool in tools:
            name = str(tool).strip().lower()
            adapter = SCANNER_ADAPTERS.get(name)
            if adapter is None:
                unavailable.append(f"{name} (no adapter)")
                continue

            argv = adapter["argv"](test.test_type, target)
            if shutil.which(argv[0]) is None:
                unavailable.append(f"{name} (not installed)")
                continue

            findings = await asyncio.to_thread(self._execute_scanner, adapter, argv)
            logger.info(f"{name} reported {len(findings)} findings for {test.test_id}")
            return [
                self._to_vulnerability(test, name, finding, index)
                for index, finding in enumerate(findings)
            ]

        raise RuntimeError(
            f"no usable security scanner for test {test.test_id}: "
            + ", ".join(unavailable or ["none configured"])
        )

    @staticmethod
    def _to_vulnerability(
        test: SecurityTest, scanner: str, finding: Dict[str, Any], index: int
    ) -> Vulnerability:
        """Convert a raw scanner finding into a :class:`Vulnerability`."""
        identifier = finding.get("vulnerability_id") or f"{scanner}-{test.test_id}-{index}"
        return Vulnerability(
            vulnerability_id=str(identifier),
            title=str(finding.get("title") or "security finding"),
            severity=_map_severity(finding.get("severity")),
            cwe_id=finding.get("cwe_id"),
            description=str(finding.get("description") or ""),
            affected_component=str(finding.get("affected_component") or test.target),
            remediation=str(finding.get("remediation") or ""),
            metadata={"scanner": scanner, "test_id": test.test_id},
        )

    async def run_all_tests(self, test_type: Optional[TestType] = None) -> List[str]:
        """
        Run all enabled security tests

        Args:
            test_type: Filter by test type (optional)

        Returns:
            List of test IDs
        """
        test_ids = []

        for test_id, test in self.security_tests.items():
            if not test.enabled:
                continue

            if test_type and test.test_type != test_type:
                continue

            result_id = await self.run_security_test(test_id)
            test_ids.append(result_id)

        return test_ids

    def get_test_result(self, test_id: str) -> Optional[Dict[str, Any]]:
        """
        Get test result

        Args:
            test_id: Test ID

        Returns:
            Test result dictionary
        """
        if test_id not in self.test_results:
            return None

        result = self.test_results[test_id]

        return {
            "test_id": result.test_id,
            "status": result.status.value,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
            "duration": result.duration,
            "vulnerabilities": [
                {
                    "vulnerability_id": v.vulnerability_id,
                    "title": v.title,
                    "severity": v.severity.value,
                    "cwe_id": v.cwe_id,
                    "description": v.description,
                    "affected_component": v.affected_component,
                    "remediation": v.remediation,
                    "discovered_at": v.discovered_at.isoformat(),
                }
                for v in result.vulnerabilities
            ],
            "summary": result.summary,
            "error_message": result.error_message,
        }

    def get_vulnerabilities(
        self, severity: Optional[SeverityLevel] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get vulnerabilities

        Args:
            severity: Filter by severity (optional)
            limit: Maximum number of records

        Returns:
            Vulnerabilities list
        """
        vulns = self.vulnerabilities

        if severity:
            vulns = [v for v in vulns if v.severity == severity]

        vulns = vulns[-limit:]

        return [
            {
                "vulnerability_id": v.vulnerability_id,
                "title": v.title,
                "severity": v.severity.value,
                "cwe_id": v.cwe_id,
                "description": v.description,
                "affected_component": v.affected_component,
                "remediation": v.remediation,
                "discovered_at": v.discovered_at.isoformat(),
            }
            for v in vulns
        ]

    async def generate_security_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive security report

        Returns:
            Security report
        """
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_tests": self.total_tests,
            "total_vulnerabilities": self.total_vulnerabilities,
            "critical_vulnerabilities": self.critical_vulnerabilities,
            "vulnerabilities_by_severity": {
                "critical": len(
                    [v for v in self.vulnerabilities if v.severity == SeverityLevel.CRITICAL]
                ),
                "high": len([v for v in self.vulnerabilities if v.severity == SeverityLevel.HIGH]),
                "medium": len(
                    [v for v in self.vulnerabilities if v.severity == SeverityLevel.MEDIUM]
                ),
                "low": len([v for v in self.vulnerabilities if v.severity == SeverityLevel.LOW]),
            },
            "test_results": {
                test_id: self.get_test_result(test_id)
                for test_id in self.security_tests.keys()
                if test_id in self.test_results
            },
        }

        # Save report
        report_path = (
            self.reports_dir
            / f"security_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Generated security report: {report_path}")

        return report

    async def start_auto_scan_loop(self) -> None:
        """Start automatic security scan loop"""
        if not self.auto_scan_enabled:
            return

        async def scan_loop():
            while True:
                try:
                    # Run all tests
                    await self.run_all_tests()

                    await asyncio.sleep(self.scan_interval)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Auto scan loop error: {e}")
                    await asyncio.sleep(self.scan_interval)

        asyncio.create_task(scan_loop())
        logger.info("Auto security scan loop started")

    def get_statistics(self) -> Dict[str, Any]:
        """Get security testing statistics"""
        return {
            "total_tests": self.total_tests,
            "total_vulnerabilities": self.total_vulnerabilities,
            "critical_vulnerabilities": self.critical_vulnerabilities,
            "enabled_tests": len([t for t in self.security_tests.values() if t.enabled]),
            "registered_tests": len(self.security_tests),
        }


def get_security_testing_system(config: Optional[Dict[str, Any]] = None) -> SecurityTestingSystem:
    """
    Factory function to get security testing system instance

    Args:
        config: Optional configuration dictionary

    Returns:
        SecurityTestingSystem: System instance
    """
    return SecurityTestingSystem(config)
