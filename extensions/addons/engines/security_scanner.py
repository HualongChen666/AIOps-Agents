# -*- coding: utf-8 -*-
"""SecurityScanner engine that wraps real security tooling via subprocess."""

from __future__ import annotations

import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional


class SecurityScanner:
    """Run common security scanners and parse JSON/text output.

    dry_run is ``True`` by default. Real subprocess execution is only enabled
    when ``INFRA_EXECUTE_ENABLED`` is set to ``"true"`` in the environment.
    """

    def __init__(self, dry_run: Optional[bool] = None) -> None:
        execute_enabled = os.environ.get("INFRA_EXECUTE_ENABLED") == "true"
        if dry_run is None:
            dry_run = not execute_enabled
        self.dry_run = dry_run

    def _run(self, cmd: List[str], default_output: str = "") -> str:
        if self.dry_run:
            return default_output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return result.stdout or result.stderr or ""

    @staticmethod
    def _load_json(text: str) -> Optional[Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def scan_code(self, target: str, scanners: List[str]) -> List[Dict[str, Any]]:
        """Run bandit/semgrep against ``target`` and return findings."""
        findings: List[Dict[str, Any]] = []

        if not scanners:
            scanners = ["bandit"]

        if "bandit" in scanners:
            bandit_default = json.dumps(
                {
                    "results": [
                        {
                            "test_id": "B105",
                            "issue_text": "Possible hardcoded password",
                            "filename": "app.py",
                            "line_number": 42,
                            "issue_severity": "HIGH",
                        }
                    ]
                }
            )
            raw = self._run(["bandit", "-r", target, "-f", "json"], default_output=bandit_default)
            data = self._load_json(raw)
            if isinstance(data, dict):
                for item in data.get("results", []):
                    findings.append(
                        {
                            "scanner": "bandit",
                            "test_id": item.get("test_id"),
                            "text": item.get("issue_text"),
                            "file": item.get("filename"),
                            "line": item.get("line_number"),
                            "severity": item.get("issue_severity"),
                        }
                    )

        if "semgrep" in scanners:
            semgrep_default = json.dumps(
                {
                    "results": [
                        {
                            "check_id": "python.sql-injection",
                            "path": "app.py",
                            "start": {"line": 15},
                            "extra": {
                                "message": "Possible SQL injection",
                                "severity": "ERROR",
                            },
                        }
                    ]
                }
            )
            raw = self._run(
                ["semgrep", "--config=auto", "--json", "--quiet", target],
                default_output=semgrep_default,
            )
            data = self._load_json(raw)
            if isinstance(data, dict):
                for item in data.get("results", []):
                    extra = item.get("extra", {})
                    findings.append(
                        {
                            "scanner": "semgrep",
                            "check_id": item.get("check_id"),
                            "file": item.get("path"),
                            "line": item.get("start", {}).get("line"),
                            "message": extra.get("message"),
                            "severity": extra.get("severity"),
                        }
                    )

        return findings

    def scan_dependencies(self, target: str) -> List[Dict[str, Any]]:
        """Run safety and return vulnerable packages."""
        default = json.dumps(
            [
                {
                    "package": "requests",
                    "vulnerability": "CVE-2023-32681",
                    "affected": "<2.31.0",
                }
            ]
        )
        raw = self._run(["safety", "check", "--json", "--file", target], default_output=default)
        data = self._load_json(raw)

        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("vulnerabilities", [])
        return []

    def scan_api(self, target: str) -> List[Dict[str, Any]]:
        """Run OWASP ZAP baseline and return alerts."""
        default = json.dumps(
            {
                "alerts": [
                    {
                        "alert": "Reflected XSS",
                        "risk": "High",
                        "url": target,
                    }
                ]
            }
        )
        raw = self._run(
            ["zap-baseline.py", "-t", target, "-J", "-"],
            default_output=default,
        )
        data = self._load_json(raw)

        if isinstance(data, dict):
            return data.get("alerts", [data])
        return [{"raw": raw}]

    def scan_network(self, target: str) -> List[Dict[str, Any]]:
        """Run nmap and return discovered ports/hosts."""
        default = (
            '<?xml version="1.0"?>\n'
            "<nmaprun>\n"
            "  <host>\n"
            "    <address addr=\"10.0.0.1\"/>\n"
            "    <ports>\n"
            '      <port portid="80">\n'
            '        <state state="open"/>\n'
            '        <service name="http"/>\n'
            "      </port>\n"
            "    </ports>\n"
            "  </host>\n"
            "</nmaprun>"
        )
        raw = self._run(
            ["nmap", "-p-", "-T4", "-oX", "-", target],
            default_output=default,
        )
        results: List[Dict[str, Any]] = []
        text = raw.strip()
        if text.startswith("<?xml") or text.startswith("<nmaprun"):
            try:
                root = ET.fromstring(text)
            except ET.ParseError:
                return results
            for host in root.findall(".//host"):
                address_el = host.find(".//address")
                host_ip = address_el.get("addr") if address_el is not None else target
                ports: List[Dict[str, Any]] = []
                for port in host.findall(".//port"):
                    portid = port.get("portid")
                    state_el = port.find(".//state")
                    state = state_el.get("state") if state_el is not None else "unknown"
                    service_el = port.find(".//service")
                    service_name = service_el.get("name") if service_el is not None else ""
                    ports.append(
                        {"port": portid, "state": state, "service": service_name}
                    )
                results.append({"host": host_ip, "ports": ports})
            return results

        current_host = target
        for line in text.splitlines():
            host_match = re.match(r"Nmap scan report for\s+(.+?)\s*(?:\(([^)]+)\))?$", line)
            if host_match:
                current_host = host_match.group(2) or host_match.group(1)
                continue
            port_match = re.match(r"^(\d+)/(tcp|udp)\s+(\w+)\s+(\S+)", line)
            if port_match:
                results.append(
                    {
                        "host": current_host,
                        "port": port_match.group(1),
                        "protocol": port_match.group(2),
                        "state": port_match.group(3),
                        "service": port_match.group(4),
                    }
                )
        return results

    def scan_container(self, image: str) -> List[Dict[str, Any]]:
        """Run trivy and return container vulnerabilities."""
        default = json.dumps(
            {
                "Results": [
                    {
                        "Target": image,
                        "Vulnerabilities": [
                            {
                                "VulnerabilityID": "CVE-2024-1234",
                                "PkgName": "openssl",
                                "Severity": "HIGH",
                            }
                        ],
                    }
                ]
            }
        )
        raw = self._run(
            ["trivy", "image", "-f", "json", image],
            default_output=default,
        )
        data = self._load_json(raw)

        if not isinstance(data, dict):
            return []

        vulnerabilities: List[Dict[str, Any]] = []
        for result in data.get("Results", []):
            for vuln in result.get("Vulnerabilities", []):
                vulnerabilities.append(
                    {
                        "id": vuln.get("VulnerabilityID"),
                        "package": vuln.get("PkgName"),
                        "severity": vuln.get("Severity"),
                        "target": result.get("Target"),
                    }
                )
        return vulnerabilities

    def check_license(self, dependencies: Any) -> List[Dict[str, Any]]:
        """Check dependency license compliance against an allow-list."""
        allowed = {
            "mit",
            "apache-2.0",
            "apache-2",
            "bsd-2-clause",
            "bsd-3-clause",
            "isc",
            "python-software-foundation",
            "cc0",
            "unlicense",
            "mpl-2.0",
            "lgpl-3.0",
            "gpl-3.0",
        }

        if isinstance(dependencies, str):
            dep_items = [d.strip() for d in dependencies.split(",") if d.strip()]
        elif isinstance(dependencies, list):
            dep_items = dependencies
        else:
            dep_items = []

        issues: List[Dict[str, Any]] = []
        for dep in dep_items:
            if isinstance(dep, dict):
                name = dep.get("name", "unknown")
                license_name = dep.get("license", "unknown")
            else:
                parts = str(dep).split(":", 1)
                if len(parts) == 2:
                    name, license_name = parts[0].strip(), parts[1].strip()
                else:
                    name, license_name = parts[0].strip() if parts else "unknown", "unknown"

            normalized = license_name.lower().replace(" ", "-")
            if normalized not in allowed:
                issues.append(
                    {
                        "package": name,
                        "license": license_name,
                        "allowed": False,
                    }
                )
        return issues

    def check_sql_injection(self, code: str) -> List[Dict[str, Any]]:
        """Simple regex/static rule check for SQL injection patterns."""
        if not isinstance(code, str):
            return []

        rules = [
            (
                r"(cursor|session|db|conn|connection)\.execute\s*\([^)]*([+]|%s|%d|\.format|f[\"'])",
                "Possible SQL injection in execute() call",
            ),
            (
                r"SELECT\s+.*\s+FROM\s+.*\s+WHERE\s+.*([+]|%s|%d|\.format|f[\"'])",
                "Possible SQL injection in SELECT statement",
            ),
            (
                r"INSERT\s+INTO\s+.*VALUES\s*\([^)]*([+]|%s|%d|\.format|f[\"'])",
                "Possible SQL injection in INSERT statement",
            ),
        ]

        findings: List[Dict[str, Any]] = []
        for pattern, message in rules:
            for match in re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE):
                line_number = code[: match.start()].count("\n") + 1
                findings.append(
                    {
                        "line": line_number,
                        "match": match.group(0),
                        "description": message,
                    }
                )
        return findings

    def check_api_baseline(self, spec: Any) -> List[Dict[str, Any]]:
        """OpenAPI/HTTP baseline checks."""
        if isinstance(spec, str):
            try:
                spec = json.loads(spec)
            except json.JSONDecodeError:
                return [{"check": "parse", "passed": False, "reason": "Invalid JSON"}]
        if not isinstance(spec, dict):
            return [{"check": "parse", "passed": False, "reason": "Spec must be a dict"}]

        findings: List[Dict[str, Any]] = []

        servers = spec.get("servers", [])
        https_found = any(
            str(s.get("url", "")).startswith("https://") for s in servers if isinstance(s, dict)
        )
        findings.append(
            {
                "check": "https",
                "passed": https_found,
                "reason": None if https_found else "No HTTPS server URL found",
            }
        )

        components = spec.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        has_auth = bool(security_schemes)
        findings.append(
            {
                "check": "authentication",
                "passed": has_auth,
                "reason": None if has_auth else "No securitySchemes defined",
            }
        )

        paths = spec.get("paths", {})
        has_health = any("/health" in p or "/ready" in p for p in paths.keys())
        findings.append(
            {
                "check": "health_endpoint",
                "passed": has_health,
                "reason": None if has_health else "No /health or /ready endpoint",
            }
        )

        versioned = any(re.search(r"/api/v\d+", p) for p in paths.keys())
        findings.append(
            {
                "check": "versioning",
                "passed": versioned,
                "reason": None if versioned else "No /api/v{n} version prefix found",
            }
        )

        return findings
