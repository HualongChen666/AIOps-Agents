#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example usage of SLO Advanced API endpoints.

This script demonstrates how to use the SLO Advanced API endpoints
for creating, reading, updating, and deleting SLO resources.
"""

import asyncio
from typing import Optional

import httpx


class SLOAdvancedAPIClient:
    """Client for interacting with SLO Advanced API endpoints."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        import os

        self.base_url = base_url or os.getenv("SLO_API_BASE_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("INTERNAL_API_KEY")
        if not self.api_key:
            raise ValueError("INTERNAL_API_KEY must be set via environment variable or parameter")
        self.headers = {}
        if self.api_key:
            self.headers["X-Internal-Key"] = self.api_key

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make an HTTP request to the API."""
        url = f"{self.base_url}{endpoint}"
        # Use environment variable to control SSL verification (default: True for security)
        ssl_verify = os.environ.get("SLO_API_CLIENT_SSL_VERIFY", "true").lower() == "true"
        if not ssl_verify:
            import logging

            logging.warning(
                "SSL verification is disabled in SLO API client - this is a security risk!"
            )
        async with httpx.AsyncClient(verify=ssl_verify) as client:
            response = await client.request(
                method, url, headers=self.headers, timeout=30.0, **kwargs
            )
            response.raise_for_status()
            return response.json()

    # SLO Definitions
    async def list_definitions(self) -> dict:
        """List all SLO definitions."""
        return await self._request("GET", "/api/v1/slo/definitions")

    async def create_definition(self, data: dict) -> dict:
        """Create a new SLO definition."""
        return await self._request("POST", "/api/v1/slo/definitions", json=data)

    async def get_definition(self, definition_id: str) -> dict:
        """Get a single SLO definition."""
        return await self._request("GET", f"/api/v1/slo/definitions/{definition_id}")

    async def update_definition(self, definition_id: str, data: dict) -> dict:
        """Update an SLO definition."""
        return await self._request("PATCH", f"/api/v1/slo/definitions/{definition_id}", json=data)

    async def delete_definition(self, definition_id: str) -> dict:
        """Delete an SLO definition."""
        return await self._request("DELETE", f"/api/v1/slo/definitions/{definition_id}")

    # SLO Metrics
    async def get_metrics(self, service: Optional[str] = None) -> dict:
        """Get SLO metrics."""
        params = {"service": service} if service else {}
        return await self._request("GET", "/api/v1/slo/metrics", params=params)

    # SLO Budgets
    async def get_budgets(self) -> dict:
        """Get error budgets."""
        return await self._request("GET", "/api/v1/slo/budgets")

    # SLO Burn Rates
    async def get_burn_rates(self) -> dict:
        """Get burn rates."""
        return await self._request("GET", "/api/v1/slo/burn-rates")

    # SLO Error Budgets (Detailed)
    async def get_error_budgets(self) -> dict:
        """Get detailed error budgets."""
        return await self._request("GET", "/api/v1/slo/error-budgets")

    # SLO Alerts
    async def list_alerts(
        self, status: Optional[str] = None, severity: Optional[str] = None
    ) -> dict:
        """List SLO alerts."""
        params = {}
        if status:
            params["status"] = status
        if severity:
            params["severity"] = severity
        return await self._request("GET", "/api/v1/slo/alerts", params=params)

    async def create_alert(self, data: dict) -> dict:
        """Create a new SLO alert."""
        return await self._request("POST", "/api/v1/slo/alerts", json=data)

    # SLO Reports
    async def get_reports(self, period: str = "30d") -> dict:
        """Get SLO reports."""
        return await self._request("GET", "/api/v1/slo/reports", params={"period": period})

    # SLO Historical Data
    async def get_historical_data(self, slo_id: Optional[str] = None, period: str = "7d") -> dict:
        """Get historical SLO data."""
        params = {"period": period}
        if slo_id:
            params["slo_id"] = slo_id
        return await self._request("GET", "/api/v1/slo/historical-data", params=params)

    # SLO Services
    async def get_services(self) -> dict:
        """List services with SLOs."""
        return await self._request("GET", "/api/v1/slo/services")

    # SLO Objectives
    async def list_objectives(self, service: Optional[str] = None) -> dict:
        """List SLO objectives."""
        params = {"service": service} if service else {}
        return await self._request("GET", "/api/v1/slo/objectives", params=params)

    async def create_objective(self, data: dict) -> dict:
        """Create a new SLO objective."""
        return await self._request("POST", "/api/v1/slo/objectives", json=data)

    async def update_objective(self, objective_id: str, data: dict) -> dict:
        """Update an SLO objective."""
        return await self._request("PATCH", f"/api/v1/slo/objectives/{objective_id}", json=data)

    async def delete_objective(self, objective_id: str) -> dict:
        """Delete an SLO objective."""
        return await self._request("DELETE", f"/api/v1/slo/objectives/{objective_id}")

    # SLO Rollups
    async def get_rollups(self, service: Optional[str] = None) -> dict:
        """Get SLO rollups."""
        params = {"service": service} if service else {}
        return await self._request("GET", "/api/v1/slo/rollups", params=params)


async def main():
    """Example usage of the SLO Advanced API client."""
    # Initialize client (use internal API key for authentication)
    # API key and base URL are read from environment variables
    try:
        client = SLOAdvancedAPIClient()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please set INTERNAL_API_KEY environment variable")
        return

    print("=" * 60)
    print("SLO Advanced API Example Usage")
    print("=" * 60)

    # Example 1: Create an SLO definition
    print("\n1. Creating SLO definition...")
    definition_data = {
        "name": "API Availability",
        "description": "API service availability SLO",
        "metric_type": "availability",
        "threshold": 99.9,
        "operator": "gte",
        "window": "30d",
        "alerting": True,
    }
    try:
        definition = await client.create_definition(definition_data)
        print(f"   Created definition: {definition['id']}")
        definition_id = definition["id"]
    except Exception as e:
        print(f"   Error creating definition: {e}")
        definition_id = None

    # Example 2: List all SLO definitions
    print("\n2. Listing SLO definitions...")
    try:
        definitions = await client.list_definitions()
        print(f"   Found {len(definitions['definitions'])} definitions")
        for defn in definitions["definitions"][:3]:  # Show first 3
            print(f"   - {defn['id']}: {defn['name']}")
    except Exception as e:
        print(f"   Error listing definitions: {e}")

    # Example 3: Get SLO metrics
    print("\n3. Getting SLO metrics...")
    try:
        metrics = await client.get_metrics()
        print(f"   Found {len(metrics['metrics'])} metrics")
        for metric in metrics["metrics"][:3]:  # Show first 3
            print(f"   - {metric['name']}: {metric['current']}% (target: {metric['target']}%)")
    except Exception as e:
        print(f"   Error getting metrics: {e}")

    # Example 4: Get error budgets
    print("\n4. Getting error budgets...")
    try:
        budgets = await client.get_budgets()
        print(f"   Found {len(budgets['budgets'])} budgets")
        for budget in budgets["budgets"][:3]:  # Show first 3
            print(f"   - {budget['slo_name']}: {budget['error_budget_remaining']}% remaining")
    except Exception as e:
        print(f"   Error getting budgets: {e}")

    # Example 5: Get burn rates
    print("\n5. Getting burn rates...")
    try:
        burn_rates = await client.get_burn_rates()
        print(f"   Found {len(burn_rates['burn_rates'])} burn rates")
        for br in burn_rates["burn_rates"][:3]:  # Show first 3
            print(f"   - {br['slo_name']}: 1h={br['burn_rate_1h']}, 24h={br['burn_rate_24h']}")
    except Exception as e:
        print(f"   Error getting burn rates: {e}")

    # Example 6: Create an SLO objective
    print("\n6. Creating SLO objective...")
    objective_data = {
        "name": "API Latency",
        "service": "api-service",
        "metric": "latency",
        "target": 99.0,
        "window": "24h",
        "description": "API latency objective",
    }
    try:
        objective = await client.create_objective(objective_data)
        print(f"   Created objective: {objective['id']}")
        objective_id = objective["id"]
    except Exception as e:
        print(f"   Error creating objective: {e}")
        objective_id = None

    # Example 7: List SLO objectives
    print("\n7. Listing SLO objectives...")
    try:
        objectives = await client.list_objectives()
        print(f"   Found {len(objectives['objectives'])} objectives")
        for obj in objectives["objectives"][:3]:  # Show first 3
            print(f"   - {obj['id']}: {obj['name']} ({obj['status']})")
    except Exception as e:
        print(f"   Error listing objectives: {e}")

    # Example 8: Get SLO reports
    print("\n8. Getting SLO reports...")
    try:
        reports = await client.get_reports(period="30d")
        print(f"   Found {len(reports['reports'])} reports")
        for report in reports["reports"][:3]:  # Show first 3
            print(f"   - {report['slo_name']}: {report['availability']}% ({report['compliance']})")
    except Exception as e:
        print(f"   Error getting reports: {e}")

    # Example 9: Get services
    print("\n9. Getting services...")
    try:
        services = await client.get_services()
        print(f"   Found {len(services['services'])} services")
        for svc in services["services"][:3]:  # Show first 3
            print(f"   - {svc['name']}: {svc['slo_count']} SLOs")
    except Exception as e:
        print(f"   Error getting services: {e}")

    # Example 10: Get rollups
    print("\n10. Getting rollups...")
    try:
        rollups = await client.get_rollups()
        print(f"   Found {len(rollups['rollups'])} rollups")
        for rollup in rollups["rollups"][:3]:  # Show first 3
            print(
                f"   - {rollup['service']}: {rollup['healthy_slos']}/{rollup['total_slos']} healthy"
            )
    except Exception as e:
        print(f"   Error getting rollups: {e}")

    # Example 11: Create an alert
    print("\n11. Creating SLO alert...")
    alert_data = {
        "slo_id": "SLO-001",  # Replace with actual SLO ID
        "severity": "critical",
        "message": "SLO breached due to high error rate",
        "metadata": {"error_rate": "5%"},
    }
    try:
        alert = await client.create_alert(alert_data)
        print(f"   Created alert: {alert['id']}")
    except Exception as e:
        print(f"   Error creating alert: {e}")

    # Example 12: List alerts
    print("\n12. Listing alerts...")
    try:
        alerts = await client.list_alerts(status="open")
        print(f"   Found {len(alerts['alerts'])} open alerts")
        for alert in alerts["alerts"][:3]:  # Show first 3
            print(f"   - {alert['id']}: {alert['severity']} - {alert['message']}")
    except Exception as e:
        print(f"   Error listing alerts: {e}")

    # Cleanup (optional)
    if definition_id:
        print(f"\nCleaning up definition {definition_id}...")
        try:
            await client.delete_definition(definition_id)
            print("   Definition deleted")
        except Exception as e:
            print(f"   Error deleting definition: {e}")

    if objective_id:
        print(f"\nCleaning up objective {objective_id}...")
        try:
            await client.delete_objective(objective_id)
            print("   Objective deleted")
        except Exception as e:
            print(f"   Error deleting objective: {e}")

    print("\n" + "=" * 60)
    print("Example completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
