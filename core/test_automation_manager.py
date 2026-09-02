# -*- coding: utf-8 -*-
"""
Test Automation Manager
Enterprise-grade test automation and CI/CD integration
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class AutomationStatus(Enum):
    """Automation status"""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AutomationJob:
    """Automation job metadata"""

    job_id: str
    job_name: str
    job_type: str
    status: AutomationStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    trigger_type: str = "manual"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationConfig:
    """Notification configuration"""

    enabled: bool
    on_success: bool = True
    on_failure: bool = True
    channels: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TestAutomationManager:
    """
    Enterprise-grade test automation manager
    Provides CI/CD integration, report generation, and notification
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize test automation manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Repository (set via set_repository method)
        self._repository = None

        # Notification configuration
        self.notification_config: NotificationConfig = NotificationConfig(
            enabled=self.config.get("notification_enabled", False),
            channels=self.config.get("notification_channels", ["email", "slack"]),
        )

        # CI/CD configuration
        self.cicd_config: Dict[str, Any] = {
            "enabled": self.config.get("cicd_enabled", False),
            "platform": self.config.get("cicd_platform", "github_actions"),
            "pipeline_file": self.config.get("pipeline_file", ".github/workflows/tests.yml"),
        }

        logger.info("Test automation manager initialized")

    def set_repository(self, repository):
        """
        Set the repository for database operations

        Args:
            repository: TestRepository instance
        """
        self._repository = repository
        logger.info("Repository set for test automation manager")

    def create_automation_job(
        self, job_id: str, job_name: str, job_type: str, trigger_type: str = "manual", created_by: Optional[str] = None
    ) -> bool:
        """
        Create an automation job

        Args:
            job_id: Job ID
            job_name: Job name
            job_type: Job type
            trigger_type: Trigger type (manual, scheduled, webhook)
            created_by: Creator username

        Returns:
            True if created, False otherwise
        """
        if not self._repository:
            logger.error("Repository not set")
            return False

        try:
            self._repository.create_automation_job(
                job_id=job_id,
                job_name=job_name,
                job_type=job_type,
                trigger_type=trigger_type,
                created_by=created_by,
            )
            logger.info(f"Created automation job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating automation job {job_id}: {e}")
            return False

    def run_automation_job(self, job_id: str) -> bool:
        """
        Run an automation job

        Args:
            job_id: Job ID

        Returns:
            True if started, False otherwise
        """
        if not self._repository:
            logger.error("Repository not set")
            return False

        try:
            job = self._repository.get_automation_job(job_id)
            if not job:
                logger.error(f"Automation job {job_id} not found")
                return False

            # Update job status to running
            self._repository.update_automation_job(
                job_id=job_id,
                status="running",
                start_time=datetime.now(timezone.utc),
            )

            logger.info(f"Started automation job: {job_id}")

            # Simulate job completion (in real implementation, this would run actual tests)
            self._repository.update_automation_job(
                job_id=job_id,
                status="completed",
                end_time=datetime.now(timezone.utc),
            )

            return True
        except Exception as e:
            logger.error(f"Error running automation job {job_id}: {e}")
            return False

    def generate_ci_cd_pipeline(self, output_path: str, platform: str = "github_actions", created_by: Optional[str] = None) -> bool:
        """
        Generate CI/CD pipeline configuration

        Args:
            output_path: Output file path
            platform: CI/CD platform
            created_by: Creator username

        Returns:
            True if generated, False otherwise
        """
        try:
            if platform == "github_actions":
                pipeline_config = self._generate_github_actions_config()
            elif platform == "gitlab_ci":
                pipeline_config = self._generate_gitlab_ci_config()
            elif platform == "jenkins":
                pipeline_config = self._generate_jenkins_config()
            else:
                logger.error(f"Unsupported platform: {platform}")
                return False

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(pipeline_config)

            # Set restrictive permissions for pipeline file (644 - owner read/write, group/others read)
            try:
                import os
                import stat

                os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            except (OSError, AttributeError):
                # chmod may fail on Windows or non-Unix systems
                pass

            # Save config to database if repository is available
            if self._repository:
                try:
                    config_id = f"{platform}_{datetime.now(timezone.utc).timestamp()}"
                    self._repository.create_cicd_config(
                        config_id=config_id,
                        name=f"{platform}_pipeline",
                        platform=platform,
                        config_content=pipeline_config,
                        created_by=created_by,
                    )
                except Exception as e:
                    logger.warning(f"Failed to save CI/CD config to database: {e}")

            logger.info(f"Generated CI/CD pipeline: {output_path}")

            return True
        except Exception as e:
            logger.error(f"Error generating CI/CD pipeline: {e}")
            return False

    def _generate_github_actions_config(self) -> str:
        """Generate GitHub Actions configuration"""
        return """name: Automated Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pytest pytest-cov pytest-asyncio
        pip install -r requirements.txt

    - name: Run unit tests
      run: |
        pytest tests/unit/ --cov=core --cov-report=xml --cov-report=html

    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pytest pytest-cov pytest-asyncio
        pip install -r requirements.txt

    - name: Run integration tests
      run: |
        pytest tests/integration/ --cov=integration --cov-report=xml

    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: integration
        name: codecov-umbrella

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pytest pytest-cov pytest-asyncio
        pip install -r requirements.txt

    - name: Run end-to-end tests
      run: |
        pytest tests/e2e/ --cov=e2e --cov-report=xml

    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: e2e
        name: codecov-umbrella
"""

    def _generate_gitlab_ci_config(self) -> str:
        """Generate GitLab CI configuration"""
        return """stages:
  - unit
  - integration
  - e2e

unit_tests:
  stage: unit
  script:
    - pip install pytest pytest-cov pytest-asyncio
    - pip install -r requirements.txt
    - pytest tests/unit/ --cov=core --cov-report=xml
  coverage: '/TOTAL.*\\s+(\\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml

integration_tests:
  stage: integration
  needs: [unit_tests]
  script:
    - pip install pytest pytest-cov pytest-asyncio
    - pip install -r requirements.txt
    - pytest tests/integration/ --cov=integration --cov-report=xml
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml

e2e_tests:
  stage: e2e
  needs: [integration_tests]
  script:
    - pip install pytest pytest-cov pytest-asyncio
    - pip install -r requirements.txt
    - pytest tests/e2e/ --cov=e2e --cov-report=xml
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
"""

    def _generate_jenkins_config(self) -> str:
        """Generate Jenkins configuration"""
        return """pipeline {
    agent any

    stages {
        stage('Unit Tests') {
            steps {
                sh 'pip install pytest pytest-cov pytest-asyncio'
                sh 'pip install -r requirements.txt'
                sh 'pytest tests/unit/ --cov=core --cov-report=xml'
            }
        }

        stage('Integration Tests') {
            steps {
                sh 'pytest tests/integration/ --cov=integration --cov-report=xml'
            }
        }

        stage('E2E Tests') {
            steps {
                sh 'pytest tests/e2e/ --cov=e2e --cov-report=xml'
            }
        }
    }

    post {
        always {
            publishHTML([
                reportDir: 'htmlcov',
                reportFiles: 'index.html',
                reportName: 'Coverage Report'
            ])
        }
    }
}
"""

    def generate_test_report(
        self, report_type: str = "html", output_path: str = "test_report.html"
    ) -> bool:
        """
        Generate test report

        Args:
            report_type: Report type (html, json, xml)
            output_path: Output file path

        Returns:
            True if generated, False otherwise
        """
        try:
            if report_type == "html":
                report_content = self._generate_html_report()
            elif report_type == "json":
                report_content = self._generate_json_report()
            elif report_type == "xml":
                report_content = self._generate_xml_report()
            else:
                logger.error(f"Unsupported report type: {report_type}")
                return False

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report_content)

            # Set restrictive permissions for report file (644 - owner read/write, group/others read)
            try:
                import os
                import stat

                os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            except (OSError, AttributeError):
                # chmod may fail on Windows or non-Unix systems
                pass

            logger.info(f"Generated test report: {output_path}")

            return True
        except Exception as e:
            logger.error(f"Error generating test report: {e}")
            return False

    def _generate_html_report(self) -> str:
        """Generate HTML test report"""
        return """<!DOCTYPE html>
<html>
<head>
    <title>Test Report</title>
    <style>
        body {{ font-family:: Arial, sans-serif; margin:: 20px; }}
        .summary {{ background:: #f0f0f0; padding:: 20px; margin-bottom:: 20px; }}
        .passed {{ color:: green; }}
        .failed {{ color:: red; }}
        table {{ width:: 100%; border-collapse:: collapse; }}
        th, td {{ border:: 1px solid #ddd; padding:: 8px; text-align:: left; }}
        th {{ background-color:: #4CAF50; color:: white; }}
    </style>
</head>
<body>
    <h1>Test Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <p>Total Jobs: {}</p>
        <p>Successful: {}</p>
        <p>Failed: {}</p>
    </div>
    <h2>Automation Jobs</h2>
    <table>
        <tr>
            <th>Job ID</th>
            <th>Job Name</th>
            <th>Status</th>
            <th>Start Time</th>
            <th>End Time</th>
        </tr>
    </table>
</body>
</html>
""".format(self.total_jobs, self.successful_jobs, self.failed_jobs)

    def _generate_json_report(self) -> str:
        """Generate JSON test report"""
        report = {
            "summary": {
                "total_jobs": self.total_jobs,
                "successful_jobs": self.successful_jobs,
                "failed_jobs": self.failed_jobs,
            },
            "jobs": [
                {
                    "job_id": job.job_id,
                    "job_name": job.job_name,
                    "status": job.status.value,
                    "start_time": job.start_time.isoformat(),
                    "end_time": job.end_time.isoformat() if job.end_time else None,
                }
                for job in self.automation_jobs.values()
            ],
        }

        return json.dumps(report, indent=2)

    def _generate_xml_report(self) -> str:
        """Generate XML test report"""
        report = f"""<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
    <testsuite name="Automation Jobs" tests="{self.total_jobs}" failures="{self.failed_jobs}">
"""

        for job in self.automation_jobs.values():
            report += f"""
        <testcase name="{job.job_name}" status="{job.status.value}">
            <system-out><![CDATA[Start: {job.start_time.isoformat()}]]></system-out>
        </testcase>"""

        report += """
    </testsuite>
</testsuites>
"""
        return report

    def send_notification(self, job_id: str, status: str, message: str) -> bool:
        """
        Send notification

        Args:
            job_id: Job ID
            status: Job status
            message: Notification message

        Returns:
            True if sent, False otherwise
        """
        if not self.notification_config.enabled:
            logger.info("Notifications are disabled")
            return False

        # Get notification config from database if available
        if self._repository:
            try:
                config = self._repository.get_notification_config()
                if config and not config.enabled:
                    logger.info("Notifications are disabled in database config")
                    return False
            except Exception as e:
                logger.warning(f"Failed to get notification config: {e}")

        # Simulate sending notification (in real implementation, this would call actual notification services)
        logger.info(f"Sending notification for job {job_id}: {status} - {message}")

        return True

    def get_automation_summary(self) -> Dict[str, Any]:
        """
        Get automation summary

        Returns:
            Automation summary
        """
        if self._repository:
            try:
                return self._repository.get_automation_statistics()
            except Exception as e:
                logger.error(f"Error getting automation statistics from repository: {e}")

        # Fallback to default values
        return {
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "running_jobs": 0,
            "success_rate": 0.0,
            "notification_enabled": self.notification_config.enabled,
            "cicd_enabled": self.cicd_config["enabled"],
        }


# Global instance
_automation_manager: Optional[TestAutomationManager] = None


def get_automation_manager() -> TestAutomationManager:
    """
    Get the global test automation manager instance

    Returns:
        TestAutomationManager instance
    """
    global _automation_manager
    if _automation_manager is None:
        _automation_manager = TestAutomationManager()
    return _automation_manager
