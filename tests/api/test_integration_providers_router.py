# -*- coding: utf-8 -*-
"""
Test suite for Integration Providers Router
============================================

Comprehensive tests for integration provider configurations including:
- Microsoft Teams
- Kafka
- Cloud Platforms (AWS, Azure, GCP, Alibaba)
- GitOps (ArgoCD, Flux, Jenkins X)
- CI/CD (Jenkins, GitLab CI, CircleCI, GitHub Actions)
- ITSM (ServiceNow, BMC, Cherwell)
- Oncall (PagerDuty, OpsGenie)
- Slack
- Jira
- ServiceNow
- Message Queues (RabbitMQ, ActiveMQ, Redis, SQS)
- GitHub
- ELK Stack
- Datadog
- Grafana
- Prometheus
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uuid

from api.integration_providers_router import router
from api.integration_providers_router import (
    TeamsConfigRequest, KafkaConfigRequest, CloudConfigRequest,
    GitOpsConfigRequest, CICDConfigRequest, ITSMConfigRequest,
    OncallConfigRequest, SlackConfigRequest, JiraConfigRequest,
    ServiceNowConfigRequest, MessageQueueConfigRequest, GitHubConfigRequest,
    ELKConfigRequest, DatadogConfigRequest, GrafanaConfigRequest,
    PrometheusConfigRequest
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Create a test client for the integration providers router"""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    # Disable CORS for testing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return TestClient(app)


@pytest.fixture
def sample_teams_config():
    """Sample Teams configuration"""
    return TeamsConfigRequest(
        name="Test Teams",
        tenant_id="tenant-123",
        client_id="client-123",
        client_secret="secret-123",
        enabled=True
    )


@pytest.fixture
def sample_kafka_config():
    """Sample Kafka configuration"""
    return KafkaConfigRequest(
        name="Test Kafka",
        bootstrap_servers="localhost:9092",
        security_protocol="PLAINTEXT",
        enabled=True
    )


@pytest.fixture
def sample_cloud_config():
    """Sample Cloud configuration"""
    return CloudConfigRequest(
        name="Test Cloud",
        provider="aws",
        region="us-east-1",
        access_key="access-key",
        secret_key="secret-key",
        enabled=True
    )


@pytest.fixture
def sample_gitops_config():
    """Sample GitOps configuration"""
    return GitOpsConfigRequest(
        name="Test GitOps",
        gitops_type="argocd",
        url="https://argocd.example.com",
        token="token-123",
        enabled=True
    )


@pytest.fixture
def sample_cicd_config():
    """Sample CI/CD configuration"""
    return CICDConfigRequest(
        name="Test CI/CD",
        cicd_type="jenkins",
        url="https://jenkins.example.com",
        token="token-123",
        enabled=True
    )


@pytest.fixture
def sample_itsm_config():
    """Sample ITSM configuration"""
    return ITSMConfigRequest(
        name="Test ITSM",
        itsm_type="servicenow",
        url="https://servicenow.example.com",
        username="user",
        password="pass",
        enabled=True
    )


@pytest.fixture
def sample_oncall_config():
    """Sample Oncall configuration"""
    return OncallConfigRequest(
        name="Test Oncall",
        provider="pagerduty",
        api_key="api-key-123",
        enabled=True
    )


@pytest.fixture
def sample_slack_config():
    """Sample Slack configuration"""
    return SlackConfigRequest(
        name="Test Slack",
        workspace="test-workspace",
        bot_token="xoxb-test",
        signing_secret="signing-secret",
        enabled=True
    )


@pytest.fixture
def sample_jira_config():
    """Sample Jira configuration"""
    return JiraConfigRequest(
        name="Test Jira",
        url="https://jira.example.com",
        username="user",
        api_token="token-123",
        enabled=True
    )


@pytest.fixture
def sample_servicenow_config():
    """Sample ServiceNow configuration"""
    return ServiceNowConfigRequest(
        name="Test ServiceNow",
        instance_url="https://instance.service-now.com",
        username="user",
        password="pass",
        enabled=True
    )


@pytest.fixture
def sample_message_queue_config():
    """Sample Message Queue configuration"""
    return MessageQueueConfigRequest(
        name="Test MQ",
        mq_type="rabbitmq",
        host="localhost",
        port=5672,
        username="user",
        password="pass",
        enabled=True
    )


@pytest.fixture
def sample_github_config():
    """Sample GitHub configuration"""
    return GitHubConfigRequest(
        name="Test GitHub",
        owner="test-owner",
        repo="test-repo",
        token="ghp-token",
        enabled=True
    )


@pytest.fixture
def sample_elk_config():
    """Sample ELK Stack configuration"""
    return ELKConfigRequest(
        name="Test ELK",
        elasticsearch_url="https://elasticsearch.example.com",
        kibana_url="https://kibana.example.com",
        username="user",
        password="pass",
        enabled=True
    )


@pytest.fixture
def sample_datadog_config():
    """Sample Datadog configuration"""
    return DatadogConfigRequest(
        name="Test Datadog",
        api_key="dd-api-key",
        app_key="dd-app-key",
        site="datadoghq.com",
        enabled=True
    )


@pytest.fixture
def sample_grafana_config():
    """Sample Grafana configuration"""
    return GrafanaConfigRequest(
        name="Test Grafana",
        url="https://grafana.example.com",
        api_key="grafana-key",
        enabled=True
    )


@pytest.fixture
def sample_prometheus_config():
    """Sample Prometheus configuration"""
    return PrometheusConfigRequest(
        name="Test Prometheus",
        url="https://prometheus.example.com",
        username="user",
        password="pass",
        enabled=True
    )


# ============================================================================
# Microsoft Teams Tests
# ============================================================================

class TestTeamsIntegration:
    """Test suite for Microsoft Teams integration"""

    def test_get_teams_configs_empty(self, client):
        """Test getting Teams configs when empty"""
        response = client.get("/api/v1/integration/teams/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "configs" in data
        assert isinstance(data["configs"], list)

    def test_create_teams_config(self, client, sample_teams_config):
        """Test creating a Teams configuration"""
        response = client.post(
            "/api/v1/integration/teams/config",
            json=sample_teams_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "config_id" in data
        assert data["message"] == "Teams configuration created successfully"

    def test_create_teams_config_missing_required_field(self, client):
        """Test creating Teams config without required field"""
        invalid_config = {
            "name": "Test Teams",
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/teams/config",
            json=invalid_config
        )
        assert response.status_code == 422

    def test_create_teams_config_invalid_name_length(self, client):
        """Test creating Teams config with invalid name length"""
        invalid_config = {
            "name": "",  # Too short
            "tenant_id": "tenant-123",
            "client_id": "client-123",
            "client_secret": "secret-123"
        }
        response = client.post(
            "/api/v1/integration/teams/config",
            json=invalid_config
        )
        assert response.status_code == 422

    def test_test_teams_connection(self, client, sample_teams_config):
        """Test testing Teams connection"""
        # First create a config
        create_response = client.post(
            "/api/v1/integration/teams/config",
            json=sample_teams_config.dict()
        )
        config_id = create_response.json()["config_id"]

        # Test connection
        response = client.post(f"/api/v1/integration/teams/test/{config_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "test_result" in data

    def test_test_teams_connection_not_found(self, client):
        """Test testing Teams connection for non-existent config"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/integration/teams/test/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# Kafka Tests
# ============================================================================

class TestKafkaIntegration:
    """Test suite for Kafka integration"""

    def test_get_kafka_configs_empty(self, client):
        """Test getting Kafka configs when empty"""
        response = client.get("/api/v1/integration/kafka/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "configs" in data

    def test_create_kafka_config(self, client, sample_kafka_config):
        """Test creating a Kafka configuration"""
        response = client.post(
            "/api/v1/integration/kafka/config",
            json=sample_kafka_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "config_id" in data

    def test_create_kafka_config_with_sasl(self, client):
        """Test creating Kafka config with SASL authentication"""
        config = {
            "name": "Test Kafka SASL",
            "bootstrap_servers": "localhost:9092",
            "security_protocol": "SASL_PLAINTEXT",
            "sasl_mechanism": "PLAIN",
            "username": "user",
            "password": "pass",
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/kafka/config",
            json=config
        )
        assert response.status_code == 200

    def test_test_kafka_connection(self, client, sample_kafka_config):
        """Test testing Kafka connection"""
        # First create a config
        create_response = client.post(
            "/api/v1/integration/kafka/config",
            json=sample_kafka_config.dict()
        )
        config_id = create_response.json()["config_id"]

        # Test connection
        response = client.post(f"/api/v1/integration/kafka/test/{config_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_test_kafka_connection_not_found(self, client):
        """Test testing Kafka connection for non-existent config"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/integration/kafka/test/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# Cloud Platform Tests
# ============================================================================

class TestCloudIntegration:
    """Test suite for Cloud platform integration"""

    def test_get_cloud_configs_empty(self, client):
        """Test getting Cloud configs when empty"""
        response = client.get("/api/v1/integration/cloud/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "configs" in data

    def test_create_cloud_config_aws(self, client, sample_cloud_config):
        """Test creating AWS cloud configuration"""
        response = client.post(
            "/api/v1/integration/cloud/config",
            json=sample_cloud_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "config_id" in data

    def test_create_cloud_config_azure(self, client):
        """Test creating Azure cloud configuration"""
        config = {
            "name": "Test Azure",
            "provider": "azure",
            "region": "eastus",
            "access_key": "access-key",
            "secret_key": "secret-key",
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/cloud/config",
            json=config
        )
        assert response.status_code == 200

    def test_create_cloud_config_gcp(self, client):
        """Test creating GCP cloud configuration"""
        config = {
            "name": "Test GCP",
            "provider": "gcp",
            "region": "us-central1",
            "access_key": "access-key",
            "secret_key": "secret-key",
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/cloud/config",
            json=config
        )
        assert response.status_code == 200

    def test_create_cloud_config_alibaba(self, client):
        """Test creating Alibaba cloud configuration"""
        config = {
            "name": "Test Alibaba",
            "provider": "alibaba",
            "region": "cn-hangzhou",
            "access_key": "access-key",
            "secret_key": "secret-key",
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/cloud/config",
            json=config
        )
        assert response.status_code == 200

    def test_create_cloud_config_invalid_provider(self, client):
        """Test creating cloud config with invalid provider"""
        invalid_config = {
            "name": "Test Invalid",
            "provider": "invalid",
            "region": "us-east-1",
            "access_key": "access-key",
            "secret_key": "secret-key"
        }
        response = client.post(
            "/api/v1/integration/cloud/config",
            json=invalid_config
        )
        assert response.status_code == 422

    def test_create_cloud_config_case_insensitive(self, client):
        """Test that provider validation is case insensitive"""
        config = {
            "name": "Test AWS",
            "provider": "AWS",  # Uppercase
            "region": "us-east-1",
            "access_key": "access-key",
            "secret_key": "secret-key"
        }
        response = client.post(
            "/api/v1/integration/cloud/config",
            json=config
        )
        assert response.status_code == 200

    def test_test_cloud_connection(self, client, sample_cloud_config):
        """Test testing Cloud connection"""
        # First create a config
        create_response = client.post(
            "/api/v1/integration/cloud/config",
            json=sample_cloud_config.dict()
        )
        config_id = create_response.json()["config_id"]

        # Test connection
        response = client.post(f"/api/v1/integration/cloud/test/{config_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_test_cloud_connection_not_found(self, client):
        """Test testing Cloud connection for non-existent config"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/integration/cloud/test/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# GitOps Tests
# ============================================================================

class TestGitOpsIntegration:
    """Test suite for GitOps integration"""

    def test_get_gitops_configs_empty(self, client):
        """Test getting GitOps configs when empty"""
        response = client.get("/api/v1/integration/gitops/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "configs" in data

    def test_create_gitops_config_argocd(self, client, sample_gitops_config):
        """Test creating ArgoCD configuration"""
        response = client.post(
            "/api/v1/integration/gitops/config",
            json=sample_gitops_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_create_gitops_config_flux(self, client):
        """Test creating Flux configuration"""
        config = {
            "name": "Test Flux",
            "gitops_type": "flux",
            "url": "https://flux.example.com",
            "token": "token-123",
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/gitops/config",
            json=config
        )
        assert response.status_code == 200

    def test_create_gitops_config_jenkins_x(self, client):
        """Test creating Jenkins X configuration"""
        config = {
            "name": "Test Jenkins X",
            "gitops_type": "jenkins-x",
            "url": "https://jenkinsx.example.com",
            "token": "token-123",
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/gitops/config",
            json=config
        )
        assert response.status_code == 200

    def test_create_gitops_config_invalid_type(self, client):
        """Test creating GitOps config with invalid type"""
        invalid_config = {
            "name": "Test Invalid",
            "gitops_type": "invalid",
            "url": "https://example.com",
            "token": "token-123"
        }
        response = client.post(
            "/api/v1/integration/gitops/config",
            json=invalid_config
        )
        assert response.status_code == 422

    def test_test_gitops_connection(self, client, sample_gitops_config):
        """Test testing GitOps connection"""
        # First create a config
        create_response = client.post(
            "/api/v1/integration/gitops/config",
            json=sample_gitops_config.dict()
        )
        config_id = create_response.json()["config_id"]

        # Test connection
        response = client.post(f"/api/v1/integration/gitops/test/{config_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_test_gitops_connection_not_found(self, client):
        """Test testing GitOps connection for non-existent config"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/integration/gitops/test/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# CI/CD Tests
# ============================================================================

class TestCICDIntegration:
    """Test suite for CI/CD integration"""

    def test_get_cicd_configs_empty(self, client):
        """Test getting CI/CD configs when empty"""
        response = client.get("/api/v1/integration/cicd/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "configs" in data

    def test_create_cicd_config_jenkins(self, client, sample_cicd_config):
        """Test creating Jenkins configuration"""
        response = client.post(
            "/api/v1/integration/cicd/config",
            json=sample_cicd_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_create_cicd_config_gitlab(self, client):
        """Test creating GitLab CI configuration"""
        config = {
            "name": "Test GitLab",
            "cicd_type": "gitlab",
            "url": "https://gitlab.example.com",
            "token": "token-123",
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/cicd/config",
            json=config
        )
        assert response.status_code == 200

    def test_create_cicd_config_circleci(self, client):
        """Test creating CircleCI configuration"""
        config = {
            "name": "Test CircleCI",
            "cicd_type": "circleci",
            "url": "https://circleci.example.com",
            "token": "token-123",
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/cicd/config",
            json=config
        )
        assert response.status_code == 200

    def test_create_cicd_config_github_actions(self, client):
        """Test creating GitHub Actions configuration"""
        config = {
            "name": "Test GitHub Actions",
            "cicd_type": "github-actions",
            "url": "https://github.com",
            "token": "token-123",
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/cicd/config",
            json=config
        )
        assert response.status_code == 200

    def test_create_cicd_config_invalid_type(self, client):
        """Test creating CI/CD config with invalid type"""
        invalid_config = {
            "name": "Test Invalid",
            "cicd_type": "invalid",
            "url": "https://example.com",
            "token": "token-123"
        }
        response = client.post(
            "/api/v1/integration/cicd/config",
            json=invalid_config
        )
        assert response.status_code == 422

    def test_test_cicd_connection(self, client, sample_cicd_config):
        """Test testing CI/CD connection"""
        # First create a config
        create_response = client.post(
            "/api/v1/integration/cicd/config",
            json=sample_cicd_config.dict()
        )
        config_id = create_response.json()["config_id"]

        # Test connection
        response = client.post(f"/api/v1/integration/cicd/test/{config_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_test_cicd_connection_not_found(self, client):
        """Test testing CI/CD connection for non-existent config"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/integration/cicd/test/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# ITSM Tests
# ============================================================================

class TestITSMIntegration:
    """Test suite for ITSM integration"""

    def test_get_itsm_configs_empty(self, client):
        """Test getting ITSM configs when empty"""
        response = client.get("/api/v1/integration/itsm/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "configs" in data

    def test_create_itsm_config_servicenow(self, client, sample_itsm_config):
        """Test creating ServiceNow configuration"""
        response = client.post(
            "/api/v1/integration/itsm/config",
            json=sample_itsm_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_create_itsm_config_bmc(self, client):
        """Test creating BMC configuration"""
        config = {
            "name": "Test BMC",
            "itsm_type": "bmc",
            "url": "https://bmc.example.com",
            "username": "user",
            "password": "pass",
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/itsm/config",
            json=config
        )
        assert response.status_code == 200

    def test_create_itsm_config_cherwell(self, client):
        """Test creating Cherwell configuration"""
        config = {
            "name": "Test Cherwell",
            "itsm_type": "cherwell",
            "url": "https://cherwell.example.com",
            "username": "user",
            "password": "pass",
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/itsm/config",
            json=config
        )
        assert response.status_code == 200

    def test_create_itsm_config_invalid_type(self, client):
        """Test creating ITSM config with invalid type"""
        invalid_config = {
            "name": "Test Invalid",
            "itsm_type": "invalid",
            "url": "https://example.com",
            "username": "user",
            "password": "pass"
        }
        response = client.post(
            "/api/v1/integration/itsm/config",
            json=invalid_config
        )
        assert response.status_code == 422

    def test_test_itsm_connection(self, client, sample_itsm_config):
        """Test testing ITSM connection"""
        # First create a config
        create_response = client.post(
            "/api/v1/integration/itsm/config",
            json=sample_itsm_config.dict()
        )
        config_id = create_response.json()["config_id"]

        # Test connection
        response = client.post(f"/api/v1/integration/itsm/test/{config_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_test_itsm_connection_not_found(self, client):
        """Test testing ITSM connection for non-existent config"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/integration/itsm/test/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# Oncall Tests
# ============================================================================

class TestOncallIntegration:
    """Test suite for Oncall integration"""

    def test_get_oncall_configs_empty(self, client):
        """Test getting Oncall configs when empty"""
        response = client.get("/api/v1/integration/oncall/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "configs" in data

    def test_create_oncall_config_pagerduty(self, client, sample_oncall_config):
        """Test creating PagerDuty configuration"""
        response = client.post(
            "/api/v1/integration/oncall/config",
            json=sample_oncall_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_create_oncall_config_opsgenie(self, client):
        """Test creating OpsGenie configuration"""
        config = {
            "name": "Test OpsGenie",
            "provider": "opsgenie",
            "api_key": "api-key-123",
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/oncall/config",
            json=config
        )
        assert response.status_code == 200

    def test_create_oncall_config_invalid_provider(self, client):
        """Test creating Oncall config with invalid provider"""
        invalid_config = {
            "name": "Test Invalid",
            "provider": "invalid",
            "api_key": "api-key-123"
        }
        response = client.post(
            "/api/v1/integration/oncall/config",
            json=invalid_config
        )
        assert response.status_code == 422

    def test_test_oncall_connection(self, client, sample_oncall_config):
        """Test testing Oncall connection"""
        # First create a config
        create_response = client.post(
            "/api/v1/integration/oncall/config",
            json=sample_oncall_config.dict()
        )
        config_id = create_response.json()["config_id"]

        # Test connection
        response = client.post(f"/api/v1/integration/oncall/test/{config_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_test_oncall_connection_not_found(self, client):
        """Test testing Oncall connection for non-existent config"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/integration/oncall/test/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# Slack Tests
# ============================================================================

class TestSlackIntegration:
    """Test suite for Slack integration"""

    def test_get_slack_configs_empty(self, client):
        """Test getting Slack configs when empty"""
        response = client.get("/api/v1/integration/slack/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "configs" in data

    def test_create_slack_config(self, client, sample_slack_config):
        """Test creating Slack configuration"""
        response = client.post(
            "/api/v1/integration/slack/config",
            json=sample_slack_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "config_id" in data

    def test_create_slack_config_without_signing_secret(self, client):
        """Test creating Slack config without signing secret (optional)"""
        config = {
            "name": "Test Slack",
            "workspace": "test-workspace",
            "bot_token": "xoxb-test",
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/slack/config",
            json=config
        )
        assert response.status_code == 200

    def test_test_slack_connection(self, client, sample_slack_config):
        """Test testing Slack connection"""
        # First create a config
        create_response = client.post(
            "/api/v1/integration/slack/config",
            json=sample_slack_config.dict()
        )
        config_id = create_response.json()["config_id"]

        # Test connection
        response = client.post(f"/api/v1/integration/slack/test/{config_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_test_slack_connection_not_found(self, client):
        """Test testing Slack connection for non-existent config"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/integration/slack/test/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# Jira Tests
# ============================================================================

class TestJiraIntegration:
    """Test suite for Jira integration"""

    def test_get_jira_configs_empty(self, client):
        """Test getting Jira configs when empty"""
        response = client.get("/api/v1/integration/jira/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "configs" in data

    def test_create_jira_config(self, client, sample_jira_config):
        """Test creating Jira configuration"""
        response = client.post(
            "/api/v1/integration/jira/config",
            json=sample_jira_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "config_id" in data

    def test_test_jira_connection(self, client, sample_jira_config):
        """Test testing Jira connection"""
        # First create a config
        create_response = client.post(
            "/api/v1/integration/jira/config",
            json=sample_jira_config.dict()
        )
        config_id = create_response.json()["config_id"]

        # Test connection
        response = client.post(f"/api/v1/integration/jira/test/{config_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_test_jira_connection_not_found(self, client):
        """Test testing Jira connection for non-existent config"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/integration/jira/test/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# ServiceNow Tests
# ============================================================================

class TestServiceNowIntegration:
    """Test suite for ServiceNow integration"""

    def test_get_servicenow_configs_empty(self, client):
        """Test getting ServiceNow configs when empty"""
        response = client.get("/api/v1/integration/servicenow/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "configs" in data

    def test_create_servicenow_config(self, client, sample_servicenow_config):
        """Test creating ServiceNow configuration"""
        response = client.post(
            "/api/v1/integration/servicenow/config",
            json=sample_servicenow_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "config_id" in data

    def test_test_servicenow_connection(self, client, sample_servicenow_config):
        """Test testing ServiceNow connection"""
        # First create a config
        create_response = client.post(
            "/api/v1/integration/servicenow/config",
            json=sample_servicenow_config.dict()
        )
        config_id = create_response.json()["config_id"]

        # Test connection
        response = client.post(f"/api/v1/integration/servicenow/test/{config_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_test_servicenow_connection_not_found(self, client):
        """Test testing ServiceNow connection for non-existent config"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/integration/servicenow/test/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# Message Queue Tests
# ============================================================================

class TestMessageQueueIntegration:
    """Test suite for Message Queue integration"""

    def test_get_message_queue_configs_empty(self, client):
        """Test getting Message Queue configs when empty"""
        response = client.get("/api/v1/integration/message-queue/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "configs" in data

    def test_create_message_queue_config_rabbitmq(self, client, sample_message_queue_config):
        """Test creating RabbitMQ configuration"""
        response = client.post(
            "/api/v1/integration/message-queue/config",
            json=sample_message_queue_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_create_message_queue_config_activemq(self, client):
        """Test creating ActiveMQ configuration"""
        config = {
            "name": "Test ActiveMQ",
            "mq_type": "activemq",
            "host": "localhost",
            "port": 61616,
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/message-queue/config",
            json=config
        )
        assert response.status_code == 200

    def test_create_message_queue_config_redis(self, client):
        """Test creating Redis configuration"""
        config = {
            "name": "Test Redis",
            "mq_type": "redis",
            "host": "localhost",
            "port": 6379,
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/message-queue/config",
            json=config
        )
        assert response.status_code == 200

    def test_create_message_queue_config_sqs(self, client):
        """Test creating SQS configuration"""
        config = {
            "name": "Test SQS",
            "mq_type": "sqs",
            "host": "sqs.us-east-1.amazonaws.com",
            "port": 443,
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/message-queue/config",
            json=config
        )
        assert response.status_code == 200

    def test_create_message_queue_config_invalid_type(self, client):
        """Test creating Message Queue config with invalid type"""
        invalid_config = {
            "name": "Test Invalid",
            "mq_type": "invalid",
            "host": "localhost",
            "port": 5672
        }
        response = client.post(
            "/api/v1/integration/message-queue/config",
            json=invalid_config
        )
        assert response.status_code == 422

    def test_create_message_queue_config_invalid_port(self, client):
        """Test creating Message Queue config with invalid port"""
        invalid_config = {
            "name": "Test Invalid Port",
            "mq_type": "rabbitmq",
            "host": "localhost",
            "port": 70000  # Too high
        }
        response = client.post(
            "/api/v1/integration/message-queue/config",
            json=invalid_config
        )
        assert response.status_code == 422

    def test_create_message_queue_config_port_zero(self, client):
        """Test creating Message Queue config with port 0"""
        invalid_config = {
            "name": "Test Port Zero",
            "mq_type": "rabbitmq",
            "host": "localhost",
            "port": 0
        }
        response = client.post(
            "/api/v1/integration/message-queue/config",
            json=invalid_config
        )
        assert response.status_code == 422

    def test_test_message_queue_connection(self, client, sample_message_queue_config):
        """Test testing Message Queue connection"""
        # First create a config
        create_response = client.post(
            "/api/v1/integration/message-queue/config",
            json=sample_message_queue_config.dict()
        )
        config_id = create_response.json()["config_id"]

        # Test connection
        response = client.post(f"/api/v1/integration/message-queue/test/{config_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_test_message_queue_connection_not_found(self, client):
        """Test testing Message Queue connection for non-existent config"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/integration/message-queue/test/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# GitHub Tests
# ============================================================================

class TestGitHubIntegration:
    """Test suite for GitHub integration"""

    def test_get_github_configs_empty(self, client):
        """Test getting GitHub configs when empty"""
        response = client.get("/api/v1/integration/github/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "configs" in data

    def test_create_github_config(self, client, sample_github_config):
        """Test creating GitHub configuration"""
        response = client.post(
            "/api/v1/integration/github/config",
            json=sample_github_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "config_id" in data

    def test_test_github_connection(self, client, sample_github_config):
        """Test testing GitHub connection"""
        # First create a config
        create_response = client.post(
            "/api/v1/integration/github/config",
            json=sample_github_config.dict()
        )
        config_id = create_response.json()["config_id"]

        # Test connection
        response = client.post(f"/api/v1/integration/github/test/{config_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_test_github_connection_not_found(self, client):
        """Test testing GitHub connection for non-existent config"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/integration/github/test/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# ELK Stack Tests
# ============================================================================

class TestELKIntegration:
    """Test suite for ELK Stack integration"""

    def test_get_elk_configs_empty(self, client):
        """Test getting ELK configs when empty"""
        response = client.get("/api/v1/integration/elk/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "configs" in data

    def test_create_elk_config(self, client, sample_elk_config):
        """Test creating ELK Stack configuration"""
        response = client.post(
            "/api/v1/integration/elk/config",
            json=sample_elk_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "config_id" in data

    def test_create_elk_config_elasticsearch_only(self, client):
        """Test creating ELK config with only Elasticsearch URL"""
        config = {
            "name": "Test Elasticsearch",
            "elasticsearch_url": "https://elasticsearch.example.com",
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/elk/config",
            json=config
        )
        assert response.status_code == 200

    def test_test_elk_connection(self, client, sample_elk_config):
        """Test testing ELK connection"""
        # First create a config
        create_response = client.post(
            "/api/v1/integration/elk/config",
            json=sample_elk_config.dict()
        )
        config_id = create_response.json()["config_id"]

        # Test connection
        response = client.post(f"/api/v1/integration/elk/test/{config_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_test_elk_connection_not_found(self, client):
        """Test testing ELK connection for non-existent config"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/integration/elk/test/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# Datadog Tests
# ============================================================================

class TestDatadogIntegration:
    """Test suite for Datadog integration"""

    def test_get_datadog_configs_empty(self, client):
        """Test getting Datadog configs when empty"""
        response = client.get("/api/v1/integration/datadog/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "configs" in data

    def test_create_datadog_config(self, client, sample_datadog_config):
        """Test creating Datadog configuration"""
        response = client.post(
            "/api/v1/integration/datadog/config",
            json=sample_datadog_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "config_id" in data

    def test_create_datadog_config_custom_site(self, client):
        """Test creating Datadog config with custom site"""
        config = {
            "name": "Test Datadog EU",
            "api_key": "dd-api-key",
            "app_key": "dd-app-key",
            "site": "datadoghq.eu",
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/datadog/config",
            json=config
        )
        assert response.status_code == 200

    def test_test_datadog_connection(self, client, sample_datadog_config):
        """Test testing Datadog connection"""
        # First create a config
        create_response = client.post(
            "/api/v1/integration/datadog/config",
            json=sample_datadog_config.dict()
        )
        config_id = create_response.json()["config_id"]

        # Test connection
        response = client.post(f"/api/v1/integration/datadog/test/{config_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_test_datadog_connection_not_found(self, client):
        """Test testing Datadog connection for non-existent config"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/integration/datadog/test/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# Grafana Tests
# ============================================================================

class TestGrafanaIntegration:
    """Test suite for Grafana integration"""

    def test_get_grafana_configs_empty(self, client):
        """Test getting Grafana configs when empty"""
        response = client.get("/api/v1/integration/grafana/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "configs" in data

    def test_create_grafana_config(self, client, sample_grafana_config):
        """Test creating Grafana configuration"""
        response = client.post(
            "/api/v1/integration/grafana/config",
            json=sample_grafana_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "config_id" in data

    def test_test_grafana_connection(self, client, sample_grafana_config):
        """Test testing Grafana connection"""
        # First create a config
        create_response = client.post(
            "/api/v1/integration/grafana/config",
            json=sample_grafana_config.dict()
        )
        config_id = create_response.json()["config_id"]

        # Test connection
        response = client.post(f"/api/v1/integration/grafana/test/{config_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_test_grafana_connection_not_found(self, client):
        """Test testing Grafana connection for non-existent config"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/integration/grafana/test/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# Prometheus Tests
# ============================================================================

class TestPrometheusIntegration:
    """Test suite for Prometheus integration"""

    def test_get_prometheus_configs_empty(self, client):
        """Test getting Prometheus configs when empty"""
        response = client.get("/api/v1/integration/prometheus/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "configs" in data

    def test_create_prometheus_config(self, client, sample_prometheus_config):
        """Test creating Prometheus configuration"""
        response = client.post(
            "/api/v1/integration/prometheus/config",
            json=sample_prometheus_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "config_id" in data

    def test_create_prometheus_config_without_auth(self, client):
        """Test creating Prometheus config without authentication"""
        config = {
            "name": "Test Prometheus",
            "url": "https://prometheus.example.com",
            "enabled": True
        }
        response = client.post(
            "/api/v1/integration/prometheus/config",
            json=config
        )
        assert response.status_code == 200

    def test_test_prometheus_connection(self, client, sample_prometheus_config):
        """Test testing Prometheus connection"""
        # First create a config
        create_response = client.post(
            "/api/v1/integration/prometheus/config",
            json=sample_prometheus_config.dict()
        )
        config_id = create_response.json()["config_id"]

        # Test connection
        response = client.post(f"/api/v1/integration/prometheus/test/{config_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_test_prometheus_connection_not_found(self, client):
        """Test testing Prometheus connection for non-existent config"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/integration/prometheus/test/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# Data Validation Tests
# ============================================================================

class TestDataValidation:
    """Test suite for data validation across all integrations"""

    def test_name_length_validation(self, client):
        """Test name field length validation"""
        # Test minimum length
        invalid_config = {
            "name": "",  # Too short
            "tenant_id": "tenant-123",
            "client_id": "client-123",
            "client_secret": "secret-123"
        }
        response = client.post(
            "/api/v1/integration/teams/config",
            json=invalid_config
        )
        assert response.status_code == 422

        # Test maximum length
        invalid_config = {
            "name": "a" * 101,  # Too long
            "tenant_id": "tenant-123",
            "client_id": "client-123",
            "client_secret": "secret-123"
        }
        response = client.post(
            "/api/v1/integration/teams/config",
            json=invalid_config
        )
        assert response.status_code == 422

    def test_provider_validation_case_insensitive(self, client):
        """Test that provider validation is case insensitive"""
        providers = ["AWS", "Azure", "GCP", "ALIBABA"]
        for provider in providers:
            config = {
                "name": f"Test {provider}",
                "provider": provider,
                "region": "us-east-1",
                "access_key": "access-key",
                "secret_key": "secret-key"
            }
            response = client.post(
                "/api/v1/integration/cloud/config",
                json=config
            )
            assert response.status_code == 200

    def test_gitops_type_validation_case_insensitive(self, client):
        """Test that GitOps type validation is case insensitive"""
        types = ["ArgoCD", "FLUX", "Jenkins-X"]
        for gitops_type in types:
            config = {
                "name": f"Test {gitops_type}",
                "gitops_type": gitops_type,
                "url": "https://example.com",
                "token": "token-123"
            }
            response = client.post(
                "/api/v1/integration/gitops/config",
                json=config
            )
            assert response.status_code == 200

    def test_cicd_type_validation_case_insensitive(self, client):
        """Test that CI/CD type validation is case insensitive"""
        types = ["Jenkins", "GitLab", "CircleCI", "GitHub-Actions"]
        for cicd_type in types:
            config = {
                "name": f"Test {cicd_type}",
                "cicd_type": cicd_type,
                "url": "https://example.com",
                "token": "token-123"
            }
            response = client.post(
                "/api/v1/integration/cicd/config",
                json=config
            )
            assert response.status_code == 200

    def test_itsm_type_validation_case_insensitive(self, client):
        """Test that ITSM type validation is case insensitive"""
        types = ["ServiceNow", "BMC", "Cherwell"]
        for itsm_type in types:
            config = {
                "name": f"Test {itsm_type}",
                "itsm_type": itsm_type,
                "url": "https://example.com",
                "username": "user",
                "password": "pass"
            }
            response = client.post(
                "/api/v1/integration/itsm/config",
                json=config
            )
            assert response.status_code == 200

    def test_oncall_provider_validation_case_insensitive(self, client):
        """Test that Oncall provider validation is case insensitive"""
        providers = ["PagerDuty", "OpsGenie"]
        for provider in providers:
            config = {
                "name": f"Test {provider}",
                "provider": provider,
                "api_key": "api-key-123"
            }
            response = client.post(
                "/api/v1/integration/oncall/config",
                json=config
            )
            assert response.status_code == 200

    def test_mq_type_validation_case_insensitive(self, client):
        """Test that MQ type validation is case insensitive"""
        types = ["RabbitMQ", "ActiveMQ", "Redis", "SQS"]
        for mq_type in types:
            config = {
                "name": f"Test {mq_type}",
                "mq_type": mq_type,
                "host": "localhost",
                "port": 5672
            }
            response = client.post(
                "/api/v1/integration/message-queue/config",
                json=config
            )
            assert response.status_code == 200


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test suite for error handling across all integrations"""

    def test_404_on_nonexistent_config_test(self, client):
        """Test 404 error for testing non-existent configs"""
        fake_id = str(uuid.uuid4())
        endpoints = [
            f"/api/v1/integration/teams/test/{fake_id}",
            f"/api/v1/integration/kafka/test/{fake_id}",
            f"/api/v1/integration/cloud/test/{fake_id}",
            f"/api/v1/integration/gitops/test/{fake_id}",
            f"/api/v1/integration/cicd/test/{fake_id}",
            f"/api/v1/integration/itsm/test/{fake_id}",
            f"/api/v1/integration/oncall/test/{fake_id}",
            f"/api/v1/integration/slack/test/{fake_id}",
            f"/api/v1/integration/jira/test/{fake_id}",
            f"/api/v1/integration/servicenow/test/{fake_id}",
            f"/api/v1/integration/message-queue/test/{fake_id}",
            f"/api/v1/integration/github/test/{fake_id}",
            f"/api/v1/integration/elk/test/{fake_id}",
            f"/api/v1/integration/datadog/test/{fake_id}",
            f"/api/v1/integration/grafana/test/{fake_id}",
            f"/api/v1/integration/prometheus/test/{fake_id}",
        ]
        for endpoint in endpoints:
            response = client.post(endpoint)
            assert response.status_code == 404

    def test_validation_error_on_missing_required_fields(self, client):
        """Test validation error when required fields are missing"""
        invalid_configs = [
            {"name": "Test"},  # Missing tenant_id, client_id, client_secret for Teams
            {"name": "Test"},  # Missing bootstrap_servers for Kafka
            {"name": "Test"},  # Missing provider, region, access_key, secret_key for Cloud
        ]
        for invalid_config in invalid_configs:
            response = client.post(
                "/api/v1/integration/teams/config",
                json=invalid_config
            )
            assert response.status_code == 422


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Test suite for performance across all integrations"""

    def test_multiple_config_creates(self, client, sample_teams_config):
        """Test creating multiple configurations"""
        for i in range(10):
            config_data = sample_teams_config.dict()
            config_data["name"] = f"Test Teams {i}"
            response = client.post(
                "/api/v1/integration/teams/config",
                json=config_data
            )
            assert response.status_code == 200

    def test_get_after_multiple_creates(self, client, sample_teams_config):
        """Test getting list after creating multiple configurations"""
        # Create multiple configs
        for i in range(5):
            config_data = sample_teams_config.dict()
            config_data["name"] = f"Test Teams {i}"
            client.post(
                "/api/v1/integration/teams/config",
                json=config_data
            )

        # Get all configs
        response = client.get("/api/v1/integration/teams/config")
        assert response.status_code == 200
        data = response.json()
        assert len(data["configs"]) >= 5

    def test_concurrent_connection_tests(self, client, sample_teams_config):
        """Test multiple connection tests concurrently"""
        # Create configs
        config_ids = []
        for i in range(3):
            config_data = sample_teams_config.dict()
            config_data["name"] = f"Test Teams {i}"
            create_response = client.post(
                "/api/v1/integration/teams/config",
                json=config_data
            )
            config_ids.append(create_response.json()["config_id"])

        # Test connections
        for config_id in config_ids:
            response = client.post(f"/api/v1/integration/teams/test/{config_id}")
            assert response.status_code == 200


# ============================================================================
# Security Tests
# ============================================================================

class TestSecurity:
    """Test suite for security considerations"""

    def test_sensitive_data_masking(self, client, sample_cloud_config):
        """Test that sensitive data is masked in responses"""
        # Create a config
        create_response = client.post(
            "/api/v1/integration/cloud/config",
            json=sample_cloud_config.dict()
        )

        # Get configs
        response = client.get("/api/v1/integration/cloud/config")
        assert response.status_code == 200
        data = response.json()
        if len(data["configs"]) > 0:
            # Access key should be masked
            assert "***" in data["configs"][0]["access_key"] or len(data["configs"][0]["access_key"]) < 10

    def test_extra_fields_ignored(self, client, sample_teams_config):
        """Test that extra fields in request are ignored"""
        config_data = sample_teams_config.dict()
        config_data["extra_field"] = "should_be_ignored"
        response = client.post(
            "/api/v1/integration/teams/config",
            json=config_data
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=api.integration_providers_router", "--cov-report=html"])
