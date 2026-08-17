# -*- coding: utf-8 -*-
"""
Security System Integration (Phase 4)
Enterprise-grade security system integration with centralized management
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from core.vulnerability_intelligence import (
    VulnerabilityIntelligenceEngine,
    VulnerabilityRecord,
    VulnerabilitySeverity,
    VulnerabilityDataSource,
    RiskAssessment,
)


class SecurityComponent(Enum):
    """Security component types"""

    COMPLIANCE_MANAGER = "compliance_manager"
    SECURITY_TESTING = "security_testing"
    VULNERABILITY_MANAGER = "vulnerability_manager"
    VULNERABILITY_INTELLIGENCE = "vulnerability_intelligence"
    SECURITY_AUDIT = "security_audit"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    ENCRYPTION = "encryption"
    NETWORK_SECURITY = "network_security"


class IntegrationStatus(Enum):
    """Integration status"""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    DEGRADED = "degraded"


@dataclass
class SecurityIntegration:
    """Security integration configuration"""

    integration_id: str
    component: SecurityComponent
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    status: IntegrationStatus = IntegrationStatus.DISCONNECTED
    connected_at: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityIncident:
    """Security incident"""

    incident_id: str
    title: str
    severity: str
    component: SecurityComponent
    description: str = ""
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "open"
    related_events: List[str] = field(default_factory=list)
    remediation: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecuritySystemIntegrator:
    """Enterprise-grade security system integrator"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize security system integrator

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Security integrations
        self.security_integrations: Dict[str, SecurityIntegration] = {}

        # Security incidents
        self.security_incidents: List[SecurityIncident] = []

        # Component references
        self.component_refs: Dict[SecurityComponent, Any] = {}

        # Alert handlers
        self.alert_handlers: List[Callable] = []

        # Configuration
        self.auto_reconnect = self.config.get("auto_reconnect", True)
        self.health_check_interval = self.config.get("health_check_interval", 300)

        # Vulnerability Intelligence
        self.vulnerability_intelligence: Optional[VulnerabilityIntelligenceEngine] = None
        self.vulnerability_monitoring_enabled = self.config.get("vulnerability_monitoring_enabled", True)
        self.vulnerability_monitoring_interval = self.config.get("vulnerability_monitoring_interval", 3600)
        self._vulnerability_monitoring_task: Optional[asyncio.Task] = None
        self._vulnerability_monitoring_running = False

        # Statistics
        self.total_incidents = 0
        self.active_incidents = 0
        self.total_advisories_processed = 0
        self.critical_advisories_detected = 0

        logger.info("Security system integrator initialized")

    async def register_component(
        self, integration: SecurityIntegration, component_ref: Optional[Any] = None
    ) -> None:
        """
        Register security component

        Args:
            integration: Security integration
            component_ref: Component reference
        """
        self.security_integrations[integration.integration_id] = integration

        if component_ref:
            self.component_refs[integration.component] = component_ref

        # Connect to component
        await self._connect_component(integration)

        logger.info(f"Registered security component: {integration.component.value}")

    async def _connect_component(self, integration: SecurityIntegration) -> None:
        """
        Connect to security component

        Args:
            integration: Security integration
        """
        try:
            # Simulate connection
            await asyncio.sleep(1)

            integration.status = IntegrationStatus.CONNECTED
            integration.connected_at = datetime.now(timezone.utc)
            integration.last_health_check = datetime.now(timezone.utc)

            logger.info(f"Connected to security component: {integration.component.value}")

        except Exception as e:
            integration.status = IntegrationStatus.ERROR
            logger.error(
                f"Failed to connect to security component {integration.component.value}: {e}"
            )

    async def disconnect_component(self, integration_id: str) -> bool:
        """
        Disconnect from security component

        Args:
            integration_id: Integration ID

        Returns:
            Success status
        """
        if integration_id not in self.security_integrations:
            return False

        integration = self.security_integrations[integration_id]
        integration.status = IntegrationStatus.DISCONNECTED

        if integration.component in self.component_refs:
            del self.component_refs[integration.component]

        logger.info(f"Disconnected from security component: {integration.component.value}")

        return True

    async def report_incident(self, incident: SecurityIncident) -> str:
        """
        Report security incident

        Args:
            incident: Security incident

        Returns:
            Incident ID
        """
        self.security_incidents.append(incident)
        self.total_incidents += 1
        self.active_incidents += 1

        # Notify handlers
        await self._notify_incident(incident)

        logger.warning(f"Reported security incident: {incident.incident_id}")

        return incident.incident_id

    async def _notify_incident(self, incident: SecurityIncident) -> None:
        """
        Notify about security incident

        Args:
            incident: Security incident
        """
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(incident)
                else:
                    handler(incident)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")

    async def resolve_incident(self, incident_id: str, resolution_notes: str = "") -> bool:
        """
        Resolve security incident

        Args:
            incident_id: Incident ID
            resolution_notes: Resolution notes

        Returns:
            Success status
        """
        for incident in self.security_incidents:
            if incident.incident_id == incident_id:
                incident.status = "resolved"
                incident.remediation = resolution_notes
                self.active_incidents -= 1

                logger.info(f"Resolved security incident: {incident_id}")
                return True

        return False

    async def run_security_scan(self) -> Dict[str, Any]:
        """
        Run comprehensive security scan

        Returns:
            Scan results
        """
        components_dict: Dict[str, Any] = {}
        incidents_list: List[str] = []
        scan_results: Dict[str, Any] = {
            "scan_id": f"scan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "components": components_dict,
            "incidents": incidents_list,
        }

        # Scan each component
        for integration_id, integration in self.security_integrations.items():
            if not integration.enabled:
                continue

            component_result = await self._scan_component(integration)
            scan_results["components"][integration_id] = component_result

        # Check for new incidents
        for component_result in scan_results["components"].values():
            if component_result.get("has_vulnerabilities"):
                incident = SecurityIncident(
                    incident_id=f"inc_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                    title=f"Vulnerabilities detected in {component_result['component']}",
                    severity=component_result.get("max_severity", "medium"),
                    component=SecurityComponent(component_result["component"]),
                    description=(
                        f"Security scan found vulnerabilities in {component_result['component']}"
                    ),
                )
                await self.report_incident(incident)
                scan_results["incidents"].append(incident.incident_id)

        scan_results["completed_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"Completed security scan: {scan_results['scan_id']}")

        return scan_results

    async def _scan_component(self, integration: SecurityIntegration) -> Dict[str, Any]:
        """
        Scan individual component

        Args:
            integration: Security integration

        Returns:
            Component scan results
        """
        try:
            # Simulate component scan
            await asyncio.sleep(1)

            # Get component-specific scan results
            component_ref = self.component_refs.get(integration.component)

            if component_ref:
                # Call component's scan method if available
                if hasattr(component_ref, "get_statistics"):
                    stats = component_ref.get_statistics()
                    return {
                        "component": integration.component.value,
                        "status": integration.status.value,
                        "has_vulnerabilities": stats.get("total_vulnerabilities", 0) > 0,
                        "vulnerability_count": stats.get("total_vulnerabilities", 0),
                        "max_severity": (
                            "critical" if stats.get("critical_vulnerabilities", 0) > 0 else "medium"
                        ),
                    }

            return {
                "component": integration.component.value,
                "status": integration.status.value,
                "has_vulnerabilities": False,
                "vulnerability_count": 0,
                "max_severity": "none",
            }

        except Exception as e:
            logger.error(f"Component scan failed for {integration.component.value}: {e}")
            return {"component": integration.component.value, "status": "error", "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all components

        Returns:
            Health check results
        """
        components_dict: Dict[str, Any] = {}
        health_results: Dict[str, Any] = {
            "overall_status": "healthy",
            "components": components_dict,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        for integration_id, integration in self.security_integrations.items():
            component_health = await self._check_component_health(integration)
            health_results["components"][integration_id] = component_health

            if component_health["status"] != "healthy":
                health_results["overall_status"] = "degraded"

        return health_results

    async def _check_component_health(self, integration: SecurityIntegration) -> Dict[str, Any]:
        """
        Check component health

        Args:
            integration: Security integration

        Returns:
            Component health status
        """
        try:
            # Simulate health check
            await asyncio.sleep(0.5)

            integration.last_health_check = datetime.now(timezone.utc)

            if integration.status == IntegrationStatus.CONNECTED:
                return {
                    "component": integration.component.value,
                    "status": "healthy",
                    "last_check": integration.last_health_check.isoformat(),
                }
            else:
                return {
                    "component": integration.component.value,
                    "status": integration.status.value,
                    "last_check": integration.last_health_check.isoformat(),
                }

        except Exception as e:
            return {"component": integration.component.value, "status": "error", "error": str(e)}

    async def start_auto_health_check(self) -> None:
        """Start automatic health check loop"""

        async def health_check_loop():
            while True:
                try:
                    await self.health_check()
                    await asyncio.sleep(self.health_check_interval)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Auto health check loop error: {e}")
                    await asyncio.sleep(self.health_check_interval)

        asyncio.create_task(health_check_loop())
        logger.info("Auto health check loop started")

    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """
        Get incident details

        Args:
            incident_id: Incident ID

        Returns:
            Incident details
        """
        for incident in self.security_incidents:
            if incident.incident_id == incident_id:
                return {
                    "incident_id": incident.incident_id,
                    "title": incident.title,
                    "severity": incident.severity,
                    "component": incident.component.value,
                    "description": incident.description,
                    "detected_at": incident.detected_at.isoformat(),
                    "status": incident.status,
                    "remediation": incident.remediation,
                }

        return None

    def list_incidents(
        self, status: Optional[str] = None, component: Optional[SecurityComponent] = None
    ) -> List[Dict[str, Any]]:
        """
        List incidents with filters

        Args:
            status: Filter by status
            component: Filter by component

        Returns:
            List of incidents
        """
        incidents = []

        for incident in self.security_incidents:
            if status and incident.status != status:
                continue
            if component and incident.component != component:
                continue

            incidents.append(
                {
                    "incident_id": incident.incident_id,
                    "title": incident.title,
                    "severity": incident.severity,
                    "component": incident.component.value,
                    "status": incident.status,
                    "detected_at": incident.detected_at.isoformat(),
                }
            )

        return incidents

    def register_alert_handler(self, handler: Callable) -> None:
        """
        Register alert handler

        Args:
            handler: Handler function
        """
        self.alert_handlers.append(handler)
        logger.info("Registered security alert handler")

    def get_statistics(self) -> Dict[str, Any]:
        """Get security integration statistics"""
        stats = {
            "total_integrations": len(self.security_integrations),
            "active_integrations": len(
                [
                    i
                    for i in self.security_integrations.values()
                    if i.status == IntegrationStatus.CONNECTED
                ]
            ),
            "total_incidents": self.total_incidents,
            "active_incidents": self.active_incidents,
            "registered_components": len(self.component_refs),
        }

        # Add vulnerability intelligence statistics if available
        if self.vulnerability_intelligence:
            intel_stats = self.vulnerability_intelligence.get_statistics()
            stats["vulnerability_intelligence"] = intel_stats
            stats["total_advisories_processed"] = self.total_advisories_processed
            stats["critical_advisories_detected"] = self.critical_advisories_detected

        return stats

    async def initialize_vulnerability_intelligence(
        self,
        nvd_api_key: Optional[str] = None,
        nvd_api_url: Optional[str] = None,
        osv_api_url: Optional[str] = None,
        github_token: Optional[str] = None,
        monitoring_enabled: Optional[bool] = None,
        monitoring_interval: Optional[int] = None,
    ) -> None:
        """
        Initialize vulnerability intelligence integration

        Args:
            nvd_api_key: NVD API key (optional)
            nvd_api_url: NVD API URL (optional)
            osv_api_url: OSV API URL (optional)
            github_token: GitHub API token (optional)
            monitoring_enabled: Enable background monitoring
            monitoring_interval: Monitoring interval in seconds
        """
        intel_config = VulnerabilityIntelligenceConfig(
            nvd_api_key=nvd_api_key or self.config.get("nvd_api_key", ""),
            nvd_api_url=nvd_api_url or self.config.get("nvd_api_url", "https://services.nvd.nist.gov/rest/json/cves/2.0"),
            osv_api_url=osv_api_url or self.config.get("osv_api_url", "https://api.osv.dev"),
            github_token=github_token or self.config.get("github_token", ""),
            enable_caching=True,
            enable_rate_limiting=True,
        )

        self.vulnerability_intelligence = VulnerabilityIntelligenceEngine(intel_config)

        # Register as a security component
        integration = SecurityIntegration(
            integration_id="vulnerability_intelligence",
            component=SecurityComponent.VULNERABILITY_INTELLIGENCE,
            config={
                "nvd_api_key": intel_config.nvd_api_key,
                "nvd_api_url": intel_config.nvd_api_url,
                "osv_api_url": intel_config.osv_api_url,
                "monitoring_enabled": monitoring_enabled if monitoring_enabled is not None else self.vulnerability_monitoring_enabled,
                "monitoring_interval": monitoring_interval or self.vulnerability_monitoring_interval,
            },
            enabled=True,
        )

        await self.register_component(integration, self.vulnerability_intelligence)

        logger.info("Vulnerability intelligence initialized")

    async def query_vulnerability_intelligence(
        self,
        keyword: Optional[str] = None,
        package: Optional[str] = None,
        ecosystem: str = "PyPI",
        sources: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query vulnerability intelligence

        Args:
            keyword: Search keyword
            package: Package name
            ecosystem: Package ecosystem (PyPI, npm, etc.)
            sources: Data sources to search (nvd, osv, github_advisory)

        Returns:
            List of vulnerability records
        """
        if not self.vulnerability_intelligence:
            logger.warning("Vulnerability intelligence not initialized")
            return []

        # Convert source strings to enums
        source_enums = None
        if sources:
            source_map = {
                "nvd": VulnerabilityDataSource.NVD,
                "osv": VulnerabilityDataSource.OSV,
                "github_advisory": VulnerabilityDataSource.GITHUB_ADVISORY,
            }
            source_enums = [source_map.get(s) for s in sources if s in source_map]

        # Execute search
        vulns = await self.vulnerability_intelligence.search_vulnerabilities(
            keyword=keyword,
            package=package,
            ecosystem=ecosystem,
            sources=source_enums,
        )

        # Process vulnerabilities
        results = []
        for vuln in vulns:
            results.append(self._vulnerability_record_to_dict(vuln))
            self.total_advisories_processed += 1

            # Check for critical vulnerabilities
            if vuln.severity == VulnerabilitySeverity.CRITICAL:
                self.critical_advisories_detected += 1

                # Assess risk
                risk = await self.vulnerability_intelligence.assess_vulnerability_risk(vuln)

                # Create security incident for critical vulnerabilities
                incident = SecurityIncident(
                    incident_id=f"inc_vuln_{vuln.vuln_id}",
                    title=f"Critical vulnerability detected: {vuln.vuln_id}",
                    severity="critical",
                    component=SecurityComponent.VULNERABILITY_INTELLIGENCE,
                    description=vuln.description,
                    metadata={
                        "vuln_id": vuln.vuln_id,
                        "source": vuln.source.value,
                        "cvss_score": vuln.cvss_score,
                        "affected_packages": vuln.affected_packages,
                        "risk_score": risk.risk_score,
                        "risk_level": risk.risk_level,
                    },
                )
                await self.report_incident(incident)

        logger.info(f"Vulnerability intelligence query returned {len(results)} vulnerabilities")

        return results

    def _vulnerability_record_to_dict(self, vuln: VulnerabilityRecord) -> Dict[str, Any]:
        """
        Convert VulnerabilityRecord to dictionary

        Args:
            vuln: VulnerabilityRecord

        Returns:
            Dictionary representation
        """
        return {
            "vuln_id": vuln.vuln_id,
            "source": vuln.source.value,
            "title": vuln.title,
            "description": vuln.description,
            "severity": vuln.severity.value,
            "cvss_score": vuln.cvss_score,
            "cvss_vector": vuln.cvss_vector,
            "affected_packages": vuln.affected_packages,
            "affected_versions": vuln.affected_versions,
            "published_date": vuln.published_date.isoformat() if vuln.published_date else None,
            "modified_date": vuln.modified_date.isoformat() if vuln.modified_date else None,
            "references": vuln.references,
            "cwe_ids": vuln.cwe_ids,
            "exploit_available": vuln.exploit_available,
            "patch_available": vuln.patch_available,
        }

    async def get_cve_details(self, cve_id: str) -> Optional[Dict[str, Any]]:
        """
        Get CVE details from NVD

        Args:
            cve_id: CVE ID (e.g., CVE-2023-1234)

        Returns:
            Vulnerability details or None
        """
        if not self.vulnerability_intelligence:
            logger.warning("Vulnerability intelligence not initialized")
            return None

        vuln = await self.vulnerability_intelligence.get_cve(cve_id)
        if vuln:
            self.total_advisories_processed += 1
            return self._vulnerability_record_to_dict(vuln)

        return None

    async def get_recent_vulnerabilities(
        self,
        keyword: Optional[str] = None,
        package: Optional[str] = None,
        ecosystem: str = "PyPI",
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get recent vulnerabilities

        Args:
            keyword: Search keyword
            package: Package name
            ecosystem: Package ecosystem
            limit: Maximum number of results

        Returns:
            List of recent vulnerability records
        """
        if not self.vulnerability_intelligence:
            logger.warning("Vulnerability intelligence not initialized")
            return []

        vulns = await self.vulnerability_intelligence.search_vulnerabilities(
            keyword=keyword,
            package=package,
            ecosystem=ecosystem,
        )

        results = []
        for vuln in vulns[:limit]:
            results.append(self._vulnerability_record_to_dict(vuln))
            self.total_advisories_processed += 1

        return results

    async def check_component_vulnerabilities(
        self,
        component_names: List[str],
        ecosystem: str = "PyPI",
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Check if components are affected by known vulnerabilities

        Args:
            component_names: List of component/package names
            ecosystem: Package ecosystem

        Returns:
            Dictionary mapping component to list of vulnerabilities
        """
        if not self.vulnerability_intelligence:
            logger.warning("Vulnerability intelligence not initialized")
            return {}

        results = {}

        for component in component_names:
            vulns = await self.vulnerability_intelligence.query_osv(
                package=component,
                ecosystem=ecosystem,
            )

            if vulns:
                results[component] = [self._vulnerability_record_to_dict(vuln) for vuln in vulns]
                self.total_advisories_processed += len(vulns)

                # Create incidents for high/critical vulnerabilities
                for vuln in vulns:
                    if vuln.severity in (VulnerabilitySeverity.CRITICAL, VulnerabilitySeverity.HIGH):
                        risk = await self.vulnerability_intelligence.assess_vulnerability_risk(vuln)

                        incident = SecurityIncident(
                            incident_id=f"inc_comp_{component}_{vuln.vuln_id}",
                            title=f"Vulnerability in component {component}: {vuln.vuln_id}",
                            severity=vuln.severity.value,
                            component=SecurityComponent.VULNERABILITY_INTELLIGENCE,
                            description=f"Component {component} is affected by {vuln.vuln_id}",
                            metadata={
                                "component": component,
                                "vuln_id": vuln.vuln_id,
                                "source": vuln.source.value,
                                "cvss_score": vuln.cvss_score,
                                "risk_score": risk.risk_score,
                                "risk_level": risk.risk_level,
                            },
                        )
                        await self.report_incident(incident)

        return results

    async def start_vulnerability_monitoring(self) -> None:
        """Start background vulnerability monitoring"""
        if not self.vulnerability_intelligence:
            logger.warning("Vulnerability intelligence not initialized")
            return

        if self._vulnerability_monitoring_running:
            logger.warning("Vulnerability monitoring is already running")
            return

        self._vulnerability_monitoring_running = True
        self._vulnerability_monitoring_task = asyncio.create_task(self._vulnerability_monitoring_loop())
        logger.info("Vulnerability monitoring started")

    async def stop_vulnerability_monitoring(self) -> None:
        """Stop background vulnerability monitoring"""
        if not self._vulnerability_monitoring_running:
            return

        self._vulnerability_monitoring_running = False

        if self._vulnerability_monitoring_task:
            self._vulnerability_monitoring_task.cancel()
            try:
                await self._vulnerability_monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Vulnerability monitoring stopped")

    async def _vulnerability_monitoring_loop(self) -> None:
        """Background vulnerability monitoring loop"""
        while self._vulnerability_monitoring_running:
            try:
                # Search for recent critical/high vulnerabilities
                # Note: The existing engine doesn't have a direct "recent" method,
                # so we'll search with a common keyword or monitor specific packages
                vulns = await self.vulnerability_intelligence.search_vulnerabilities(
                    keyword="critical",
                    sources=[VulnerabilityDataSource.NVD],
                )

                if vulns:
                    logger.info(f"Vulnerability monitoring found {len(vulns)} vulnerabilities")

                    # Process vulnerabilities
                    for vuln in vulns:
                        self.total_advisories_processed += 1

                        # Check for critical/high severity
                        if vuln.severity in (VulnerabilitySeverity.CRITICAL, VulnerabilitySeverity.HIGH):
                            self.critical_advisories_detected += 1

                            # Assess risk
                            risk = await self.vulnerability_intelligence.assess_vulnerability_risk(vuln)

                            # Create incident
                            incident = SecurityIncident(
                                incident_id=f"inc_monitor_{vuln.vuln_id}",
                                title=f"Monitoring detected: {vuln.vuln_id}",
                                severity=vuln.severity.value,
                                component=SecurityComponent.VULNERABILITY_INTELLIGENCE,
                                description=vuln.description,
                                metadata={
                                    "vuln_id": vuln.vuln_id,
                                    "source": vuln.source.value,
                                    "cvss_score": vuln.cvss_score,
                                    "risk_score": risk.risk_score,
                                    "risk_level": risk.risk_level,
                                    "detected_by": "monitoring",
                                },
                            )
                            await self.report_incident(incident)

                # Wait for next interval
                await asyncio.sleep(self.vulnerability_monitoring_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Vulnerability monitoring loop error: {e}")
                await asyncio.sleep(self.vulnerability_monitoring_interval)

    async def get_vulnerability_advisory(self, cve_id: str) -> Optional[Dict[str, Any]]:
        """
        Get vulnerability advisory details

        Args:
            cve_id: CVE ID

        Returns:
            Advisory details
        """
        return await self.get_cve_details(cve_id)

    async def assess_vulnerability_risk(self, vuln_id: str) -> Optional[Dict[str, Any]]:
        """
        Assess risk for a vulnerability

        Args:
            vuln_id: Vulnerability ID

        Returns:
            Risk assessment details
        """
        if not self.vulnerability_intelligence:
            return None

        # First get the vulnerability
        vuln = await self.vulnerability_intelligence.get_cve(vuln_id)
        if not vuln:
            return None

        # Assess risk
        risk = await self.vulnerability_intelligence.assess_vulnerability_risk(vuln)

        return {
            "vuln_id": risk.vuln_id,
            "risk_score": risk.risk_score,
            "risk_level": risk.risk_level,
            "exploitability": risk.exploitability,
            "impact": risk.impact,
            "factors": risk.factors,
            "recommended_action": risk.recommended_action,
            "remediation_priority": risk.remediation_priority,
        }

    async def get_intelligence_statistics(self) -> Dict[str, Any]:
        """Get vulnerability intelligence statistics"""
        if not self.vulnerability_intelligence:
            return {}

        cache_stats = await self.vulnerability_intelligence.get_cache_stats()
        nvd_rate_limit = await self.vulnerability_intelligence.get_rate_limit_info("nvd")
        osv_rate_limit = await self.vulnerability_intelligence.get_rate_limit_info("osv")

        return {
            "cache": cache_stats,
            "rate_limits": {
                "nvd": nvd_rate_limit,
                "osv": osv_rate_limit,
            },
            "total_advisories_processed": self.total_advisories_processed,
            "critical_advisories_detected": self.critical_advisories_detected,
        }

    async def cleanup_vulnerability_intelligence(self) -> None:
        """Cleanup vulnerability intelligence resources"""
        await self.stop_vulnerability_monitoring()

        if self.vulnerability_intelligence:
            await self.vulnerability_intelligence.clear_cache()
            await self.vulnerability_intelligence.reset_rate_limits()
            self.vulnerability_intelligence = None

        logger.info("Vulnerability intelligence cleaned up")


def get_security_system_integrator(
    config: Optional[Dict[str, Any]] = None,
) -> SecuritySystemIntegrator:
    """
    Factory function to get security system integrator instance

    Args:
        config: Optional configuration dictionary

    Returns:
        SecuritySystemIntegrator: Integrator instance
    """
    return SecuritySystemIntegrator(config)
