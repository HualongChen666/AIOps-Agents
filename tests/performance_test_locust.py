# -*- coding: utf-8 -*-
"""
Performance Tests
性能测试
"""

import logging

from locust import HttpUser, between, task

logger = logging.getLogger(__name__)


class AIOpsUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def view_dashboard(self):
        self.client.get("/api/v1/metrics/summary")

    @task
    def view_alerts(self):
        self.client.get("/api/v1/alerts")

    @task
    def health_check(self):
        self.client.get("/api/v1/health")
