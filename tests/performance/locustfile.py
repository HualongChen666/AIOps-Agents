# -*- coding: utf-8 -*-
"""
Performance Baseline Test for AIOps Agent

This Locust test file measures the current performance baseline for key API endpoints.
It simulates realistic user load and provides metrics for:
- API response times (P50, P95, P99)
- Request throughput (RPS)
- Error rates
- Database query performance

Based on the implementation plan, the target baselines are:
- API P50 latency: 200ms (current) → 150ms (target)
- API P95 latency: 500ms (current) → 300ms (target)
- API P99 latency: 1000ms (current) → 500ms (target)
- Database query P95: 100ms (current) → 50ms (target)
- Cache hit rate: 0% (current) → 70% (target)
- QPS: 100 (current) → 200 (target)
"""

import json
import random
import time
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner

# Test configuration
BASE_URL = "http://localhost:8000"  # Adjust based on your deployment
TEST_USER = "test_user"
TEST_PASSWORD = "test_password_123"


class AIOpsUser(HttpUser):
    """
    Simulates a typical AIOps user performing various operations.
    """
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a user starts. Login and get token."""
        self.client.verify = False  # Skip SSL verification for local testing
        self.token = None
        self._login()
    
    def _login(self):
        """Login and get authentication token."""
        try:
            response = self.client.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={
                    "username": TEST_USER,
                    "password": TEST_PASSWORD
                }
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                logger.info(f"User logged in successfully")
            else:
                logger.warning(f"Login failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Login error: {e}")
    
    def _get_headers(self):
        """Get headers with authentication token."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    @task(3)
    def get_alerts(self):
        """Get alerts list - most common operation."""
        try:
            response = self.client.get(
                f"{BASE_URL}/api/v1/alerts",
                headers=self._get_headers()
            )
            if response.status_code == 200:
                logger.debug(f"Got alerts: {len(response.json())} alerts")
        except Exception as e:
            logger.error(f"Get alerts error: {e}")
    
    @task(2)
    def get_metrics(self):
        """Get metrics data."""
        try:
            response = self.client.get(
                f"{BASE_URL}/api/v1/metrics",
                headers=self._get_headers()
            )
            if response.status_code == 200:
                logger.debug("Got metrics successfully")
        except Exception as e:
            logger.error(f"Get metrics error: {e}")
    
    @task(2)
    def get_topology(self):
        """Get system topology."""
        try:
            response = self.client.get(
                f"{BASE_URL}/api/v1/topology",
                headers=self._get_headers()
            )
            if response.status_code == 200:
                logger.debug("Got topology successfully")
        except Exception as e:
            logger.error(f"Get topology error: {e}")
    
    @task(1)
    def create_alert(self):
        """Create a new alert."""
        try:
            alert_data = {
                "alert_id": f"test-alert-{int(time.time())}",
                "severity": random.choice(["low", "medium", "high", "critical"]),
                "source": "performance-test",
                "service": "test-service",
                "metric": "test-metric",
                "value": random.uniform(0.1, 1.0),
                "threshold": 0.8,
                "message": "Performance test alert"
            }
            response = self.client.post(
                f"{BASE_URL}/api/v1/alerts",
                json=alert_data,
                headers=self._get_headers()
            )
            if response.status_code in (200, 201):
                logger.debug("Alert created successfully")
        except Exception as e:
            logger.error(f"Create alert error: {e}")
    
    @task(1)
    def get_ai_analysis(self):
        """Get AI analysis for alerts."""
        try:
            response = self.client.get(
                f"{BASE_URL}/api/v1/ai/analysis",
                headers=self._get_headers()
            )
            if response.status_code == 200:
                logger.debug("Got AI analysis successfully")
        except Exception as e:
            logger.error(f"Get AI analysis error: {e}")
    
    @task(1)
    def get_auto_heal_status(self):
        """Get auto-heal status."""
        try:
            response = self.client.get(
                f"{BASE_URL}/api/v1/auto-heal/status",
                headers=self._get_headers()
            )
            if response.status_code == 200:
                logger.debug("Got auto-heal status successfully")
        except Exception as e:
            logger.error(f"Get auto-heal status error: {e}")
    
    @task(1)
    def get_workflows(self):
        """Get workflow list."""
        try:
            response = self.client.get(
                f"{BASE_URL}/api/v1/workflows",
                headers=self._get_headers()
            )
            if response.status_code == 200:
                logger.debug("Got workflows successfully")
        except Exception as e:
            logger.error(f"Get workflows error: {e}")


class AIOpsReadOnlyUser(HttpUser):
    """
    Simulates a read-only user (viewer role).
    Tests the performance of read operations without write permissions.
    """
    
    wait_time = between(2, 4)
    
    def on_start(self):
        """Called when a user starts."""
        self.client.verify = False
        self.token = None
        self._login()
    
    def _login(self):
        """Login as viewer."""
        try:
            response = self.client.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={
                    "username": "viewer_user",
                    "password": "viewer_password_123"
                }
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
        except Exception as e:
            logger.error(f"Viewer login error: {e}")
    
    def _get_headers(self):
        """Get headers with authentication token."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    @task(5)
    def get_alerts(self):
        """Get alerts list - primary read operation."""
        try:
            response = self.client.get(
                f"{BASE_URL}/api/v1/alerts",
                headers=self._get_headers()
            )
        except Exception as e:
            logger.error(f"Get alerts error: {e}")
    
    @task(3)
    def get_metrics(self):
        """Get metrics data."""
        try:
            response = self.client.get(
                f"{BASE_URL}/api/v1/metrics",
                headers=self._get_headers()
            )
        except Exception as e:
            logger.error(f"Get metrics error: {e}")
    
    @task(2)
    def get_topology(self):
        """Get system topology."""
        try:
            response = self.client.get(
                f"{BASE_URL}/api/v1/topology",
                headers=self._get_headers()
            )
        except Exception as e:
            logger.error(f"Get topology error: {e}")


# Event handlers for custom reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts."""
    logger.info("Performance baseline test started")
    logger.info(f"Target users: {environment.target_user_count if hasattr(environment, 'target_user_count') else 'N/A'}")
    logger.info(f"Spawn rate: {environment.spawn_rate if hasattr(environment, 'spawn_rate') else 'N/A'}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops."""
    logger.info("Performance baseline test stopped")
    
    # Generate baseline report
    if environment.stats.total.fail_ratio > 0:
        logger.warning(f"Error rate: {environment.stats.total.fail_ratio:.2%}")
    else:
        logger.info(f"Error rate: {environment.stats.total.fail_ratio:.2%}")
    
    logger.info(f"Total requests: {environment.stats.total.num_requests}")
    logger.info(f"RPS: {environment.stats.total.total_rps:.2f}")
    logger.info(f"Response times (ms):")
    logger.info(f"  P50: {environment.stats.total.get_response_time_percentile(0.5):.2f}")
    logger.info(f"  P95: {environment.stats.total.get_response_time_percentile(0.95):.2f}")
    logger.info(f"  P99: {environment.stats.total.get_response_time_percentile(0.99):.2f}")


# Simple logger for Locust
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    # Run Locust with default settings
    import sys
    from locust import run_locust
    
    # Default configuration
    sys.argv = [
        "locust",
        "-f", __file__,
        "--host", BASE_URL,
        "--users", "100",  # Target QPS baseline
        "--spawn-rate", "10",
        "--run-time", "5m",  # Run for 5 minutes
        "--headless",  # Run in headless mode
        "--html", "performance_baseline_report.html",
        "--csv", "performance_baseline"
    ]
    
    run_locust()