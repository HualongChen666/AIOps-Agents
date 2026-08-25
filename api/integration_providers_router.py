# -*- coding: utf-8 -*-
"""
Integration Providers Router
============================

API endpoints for managing integration provider configurations including:
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

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/integration", tags=["集成提供商"])

# ============================================================================
# In-Memory Storage (Replace with database in production)
# ============================================================================

TEAMS_CONFIGS: Dict[str, Dict[str, Any]] = {}
KAFKA_CONFIGS: Dict[str, Dict[str, Any]] = {}
CLOUD_CONFIGS: Dict[str, Dict[str, Any]] = {}
GITOPS_CONFIGS: Dict[str, Dict[str, Any]] = {}
CICD_CONFIGS: Dict[str, Dict[str, Any]] = {}
ITSM_CONFIGS: Dict[str, Dict[str, Any]] = {}
ONCALL_CONFIGS: Dict[str, Dict[str, Any]] = {}
SLACK_CONFIGS: Dict[str, Dict[str, Any]] = {}
JIRA_CONFIGS: Dict[str, Dict[str, Any]] = {}
SERVICENOW_CONFIGS: Dict[str, Dict[str, Any]] = {}
MESSAGE_QUEUE_CONFIGS: Dict[str, Dict[str, Any]] = {}
GITHUB_CONFIGS: Dict[str, Dict[str, Any]] = {}
ELK_CONFIGS: Dict[str, Dict[str, Any]] = {}
DATADOG_CONFIGS: Dict[str, Dict[str, Any]] = {}
GRAFANA_CONFIGS: Dict[str, Dict[str, Any]] = {}
PROMETHEUS_CONFIGS: Dict[str, Dict[str, Any]] = {}

# ============================================================================
# Pydantic Models
# ============================================================================

class TeamsConfigRequest(BaseModel):
    """Teams configuration request"""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    tenant_id: str = Field(..., min_length=1, description="Microsoft tenant ID")
    client_id: str = Field(..., min_length=1, description="Microsoft client ID")
    client_secret: str = Field(..., min_length=1, description="Microsoft client secret")
    enabled: bool = Field(default=True, description="Enable configuration")

    model_config = {"extra": "ignore"}


class KafkaConfigRequest(BaseModel):
    """Kafka configuration request"""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    bootstrap_servers: str = Field(..., min_length=1, description="Kafka bootstrap servers")
    security_protocol: str = Field(default="PLAINTEXT", description="Security protocol")
    sasl_mechanism: Optional[str] = Field(None, description="SASL mechanism")
    username: Optional[str] = Field(None, description="Username for authentication")
    password: Optional[str] = Field(None, description="Password for authentication")
    enabled: bool = Field(default=True, description="Enable configuration")

    model_config = {"extra": "ignore"}


class CloudConfigRequest(BaseModel):
    """Cloud platform configuration request"""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    provider: str = Field(..., description="Cloud provider: aws, azure, gcp, alibaba")
    region: str = Field(..., min_length=1, description="Cloud region")
    access_key: str = Field(..., min_length=1, description="Access key")
    secret_key: str = Field(..., min_length=1, description="Secret key")
    enabled: bool = Field(default=True, description="Enable configuration")

    @validator('provider')
    def validate_provider(cls, v):
        valid_providers = ['aws', 'azure', 'gcp', 'alibaba']
        if v.lower() not in valid_providers:
            raise ValueError(f'Provider must be one of: {", ".join(valid_providers)}')
        return v.lower()

    model_config = {"extra": "ignore"}


class GitOpsConfigRequest(BaseModel):
    """GitOps configuration request"""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    gitops_type: str = Field(..., description="GitOps type: argocd, flux, jenkins-x")
    url: str = Field(..., min_length=1, description="GitOps server URL")
    token: str = Field(..., min_length=1, description="Authentication token")
    enabled: bool = Field(default=True, description="Enable configuration")

    @validator('gitops_type')
    def validate_gitops_type(cls, v):
        valid_types = ['argocd', 'flux', 'jenkins-x']
        if v.lower() not in valid_types:
            raise ValueError(f'GitOps type must be one of: {", ".join(valid_types)}')
        return v.lower()

    model_config = {"extra": "ignore"}


class CICDConfigRequest(BaseModel):
    """CI/CD configuration request"""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    cicd_type: str = Field(..., description="CI/CD type: jenkins, gitlab, circleci, github-actions")
    url: str = Field(..., min_length=1, description="CI/CD server URL")
    token: str = Field(..., min_length=1, description="Authentication token")
    enabled: bool = Field(default=True, description="Enable configuration")

    @validator('cicd_type')
    def validate_cicd_type(cls, v):
        valid_types = ['jenkins', 'gitlab', 'circleci', 'github-actions']
        if v.lower() not in valid_types:
            raise ValueError(f'CI/CD type must be one of: {", ".join(valid_types)}')
        return v.lower()

    model_config = {"extra": "ignore"}


class ITSMConfigRequest(BaseModel):
    """ITSM configuration request"""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    itsm_type: str = Field(..., description="ITSM type: servicenow, bmc, cherwell")
    url: str = Field(..., min_length=1, description="ITSM server URL")
    username: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Password")
    enabled: bool = Field(default=True, description="Enable configuration")

    @validator('itsm_type')
    def validate_itsm_type(cls, v):
        valid_types = ['servicenow', 'bmc', 'cherwell']
        if v.lower() not in valid_types:
            raise ValueError(f'ITSM type must be one of: {", ".join(valid_types)}')
        return v.lower()

    model_config = {"extra": "ignore"}


class OncallConfigRequest(BaseModel):
    """Oncall configuration request"""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    provider: str = Field(..., description="Provider: pagerduty, opsgenie")
    api_key: str = Field(..., min_length=1, description="API key")
    enabled: bool = Field(default=True, description="Enable configuration")

    @validator('provider')
    def validate_provider(cls, v):
        valid_providers = ['pagerduty', 'opsgenie']
        if v.lower() not in valid_providers:
            raise ValueError(f'Provider must be one of: {", ".join(valid_providers)}')
        return v.lower()

    model_config = {"extra": "ignore"}


class SlackConfigRequest(BaseModel):
    """Slack configuration request"""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    workspace: str = Field(..., min_length=1, description="Slack workspace name")
    bot_token: str = Field(..., min_length=1, description="Slack bot token")
    signing_secret: Optional[str] = Field(None, description="Slack signing secret")
    enabled: bool = Field(default=True, description="Enable configuration")

    model_config = {"extra": "ignore"}


class JiraConfigRequest(BaseModel):
    """Jira configuration request"""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    url: str = Field(..., min_length=1, description="Jira server URL")
    username: str = Field(..., min_length=1, description="Username")
    api_token: str = Field(..., min_length=1, description="API token")
    enabled: bool = Field(default=True, description="Enable configuration")

    model_config = {"extra": "ignore"}


class ServiceNowConfigRequest(BaseModel):
    """ServiceNow configuration request"""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    instance_url: str = Field(..., min_length=1, description="ServiceNow instance URL")
    username: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Password")
    enabled: bool = Field(default=True, description="Enable configuration")

    model_config = {"extra": "ignore"}


class MessageQueueConfigRequest(BaseModel):
    """Message queue configuration request"""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    mq_type: str = Field(..., description="MQ type: rabbitmq, activemq, redis, sqs")
    host: str = Field(..., min_length=1, description="MQ host")
    port: int = Field(..., gt=0, le=65535, description="MQ port")
    username: Optional[str] = Field(None, description="Username")
    password: Optional[str] = Field(None, description="Password")
    enabled: bool = Field(default=True, description="Enable configuration")

    @validator('mq_type')
    def validate_mq_type(cls, v):
        valid_types = ['rabbitmq', 'activemq', 'redis', 'sqs']
        if v.lower() not in valid_types:
            raise ValueError(f'MQ type must be one of: {", ".join(valid_types)}')
        return v.lower()

    model_config = {"extra": "ignore"}


class GitHubConfigRequest(BaseModel):
    """GitHub configuration request"""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    owner: str = Field(..., min_length=1, description="Repository owner")
    repo: str = Field(..., min_length=1, description="Repository name")
    token: str = Field(..., min_length=1, description="GitHub personal access token")
    enabled: bool = Field(default=True, description="Enable configuration")

    model_config = {"extra": "ignore"}


class ELKConfigRequest(BaseModel):
    """ELK Stack configuration request"""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    elasticsearch_url: str = Field(..., min_length=1, description="Elasticsearch URL")
    kibana_url: Optional[str] = Field(None, description="Kibana URL")
    logstash_url: Optional[str] = Field(None, description="Logstash URL")
    username: Optional[str] = Field(None, description="Username")
    password: Optional[str] = Field(None, description="Password")
    enabled: bool = Field(default=True, description="Enable configuration")

    model_config = {"extra": "ignore"}


class DatadogConfigRequest(BaseModel):
    """Datadog configuration request"""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    api_key: str = Field(..., min_length=1, description="Datadog API key")
    app_key: str = Field(..., min_length=1, description="Datadog application key")
    site: str = Field(default="datadoghq.com", description="Datadog site")
    enabled: bool = Field(default=True, description="Enable configuration")

    model_config = {"extra": "ignore"}


class GrafanaConfigRequest(BaseModel):
    """Grafana configuration request"""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    url: str = Field(..., min_length=1, description="Grafana URL")
    api_key: str = Field(..., min_length=1, description="Grafana API key")
    enabled: bool = Field(default=True, description="Enable configuration")

    model_config = {"extra": "ignore"}


class PrometheusConfigRequest(BaseModel):
    """Prometheus configuration request"""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    url: str = Field(..., min_length=1, description="Prometheus URL")
    username: Optional[str] = Field(None, description="Username for basic auth")
    password: Optional[str] = Field(None, description="Password for basic auth")
    enabled: bool = Field(default=True, description="Enable configuration")

    model_config = {"extra": "ignore"}


# ============================================================================
# Helper Functions
# ============================================================================

def generate_config_id() -> str:
    """Generate a unique configuration ID"""
    return str(uuid.uuid4())


def mask_sensitive_value(value: str) -> str:
    """Mask sensitive values for display"""
    if not value or len(value) < 4:
        return "***"
    return value[:2] + "*" * (len(value) - 4) + value[-2:]


def test_connection_mock(provider: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock connection test function.
    In production, this would make actual API calls to the provider.
    """
    import time
    import random
    
    # Simulate network delay
    time.sleep(0.5)
    
    # Simulate random success/failure (90% success rate)
    success = random.random() < 0.9
    
    if success:
        return {
            "status": "success",
            "message": f"Successfully connected to {provider}",
            "latency_ms": random.randint(50, 200),
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        return {
            "status": "error",
            "message": f"Failed to connect to {provider}: Connection timeout",
            "error_code": "CONNECTION_TIMEOUT",
            "timestamp": datetime.utcnow().isoformat()
        }


# ============================================================================
# Microsoft Teams Endpoints
# ============================================================================

@router.get("/teams/config", summary="获取Teams配置列表")
async def get_teams_configs() -> Dict[str, Any]:
    """
    获取所有Microsoft Teams配置
    """
    configs = []
    for config_id, config in TEAMS_CONFIGS.items():
        configs.append({
            "config_id": config_id,
            "name": config["name"],
            "tenant_id": config["tenant_id"],
            "client_id": config["client_id"],
            "enabled": config["enabled"],
            "status": config["status"],
            "last_sync": config["last_sync"],
            "team_count": config.get("team_count", 0)
        })
    
    return {
        "status": "success",
        "configs": configs
    }


@router.post("/teams/config", summary="创建Teams配置")
async def create_teams_config(request: TeamsConfigRequest) -> Dict[str, Any]:
    """
    创建新的Microsoft Teams配置
    """
    config_id = generate_config_id()
    
    TEAMS_CONFIGS[config_id] = {
        "name": request.name,
        "tenant_id": request.tenant_id,
        "client_id": request.client_id,
        "client_secret": request.client_secret,
        "enabled": request.enabled,
        "status": "disconnected",
        "last_sync": None,
        "team_count": 0,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Created Teams configuration: {config_id}")
    
    return {
        "status": "success",
        "config_id": config_id,
        "message": "Teams configuration created successfully"
    }


@router.post("/teams/test/{config_id}", summary="测试Teams连接")
async def test_teams_connection(config_id: str = Path(..., description="Configuration ID")) -> Dict[str, Any]:
    """
    测试Microsoft Teams配置的连接
    """
    if config_id not in TEAMS_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Teams configuration {config_id} not found")
    
    config = TEAMS_CONFIGS[config_id]
    result = test_connection_mock("Microsoft Teams", config)
    
    # Update status based on test result
    config["status"] = "connected" if result["status"] == "success" else "error"
    config["last_sync"] = datetime.utcnow().isoformat()
    
    return {
        "status": "success",
        "test_result": result
    }


# ============================================================================
# Kafka Endpoints
# ============================================================================

@router.get("/kafka/config", summary="获取Kafka配置列表")
async def get_kafka_configs() -> Dict[str, Any]:
    """
    获取所有Kafka配置
    """
    configs = []
    for config_id, config in KAFKA_CONFIGS.items():
        configs.append({
            "config_id": config_id,
            "name": config["name"],
            "bootstrap_servers": config["bootstrap_servers"],
            "enabled": config["enabled"],
            "status": config["status"],
            "last_sync": config["last_sync"],
            "topic_count": config.get("topic_count", 0)
        })
    
    return {
        "status": "success",
        "configs": configs
    }


@router.post("/kafka/config", summary="创建Kafka配置")
async def create_kafka_config(request: KafkaConfigRequest) -> Dict[str, Any]:
    """
    创建新的Kafka配置
    """
    config_id = generate_config_id()
    
    KAFKA_CONFIGS[config_id] = {
        "name": request.name,
        "bootstrap_servers": request.bootstrap_servers,
        "security_protocol": request.security_protocol,
        "sasl_mechanism": request.sasl_mechanism,
        "username": request.username,
        "password": request.password,
        "enabled": request.enabled,
        "status": "disconnected",
        "last_sync": None,
        "topic_count": 0,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Created Kafka configuration: {config_id}")
    
    return {
        "status": "success",
        "config_id": config_id,
        "message": "Kafka configuration created successfully"
    }


@router.post("/kafka/test/{config_id}", summary="测试Kafka连接")
async def test_kafka_connection(config_id: str = Path(..., description="Configuration ID")) -> Dict[str, Any]:
    """
    测试Kafka配置的连接
    """
    if config_id not in KAFKA_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Kafka configuration {config_id} not found")
    
    config = KAFKA_CONFIGS[config_id]
    result = test_connection_mock("Kafka", config)
    
    config["status"] = "connected" if result["status"] == "success" else "error"
    config["last_sync"] = datetime.utcnow().isoformat()
    
    return {
        "status": "success",
        "test_result": result
    }


# ============================================================================
# Cloud Platform Endpoints
# ============================================================================

@router.get("/cloud/config", summary="获取云平台配置列表")
async def get_cloud_configs() -> Dict[str, Any]:
    """
    获取所有云平台配置
    """
    configs = []
    for config_id, config in CLOUD_CONFIGS.items():
        configs.append({
            "config_id": config_id,
            "name": config["name"],
            "provider": config["provider"],
            "region": config["region"],
            "access_key": mask_sensitive_value(config["access_key"]),
            "enabled": config["enabled"],
            "status": config["status"],
            "last_sync": config["last_sync"]
        })
    
    return {
        "status": "success",
        "configs": configs
    }


@router.post("/cloud/config", summary="创建云平台配置")
async def create_cloud_config(request: CloudConfigRequest) -> Dict[str, Any]:
    """
    创建新的云平台配置
    """
    config_id = generate_config_id()
    
    CLOUD_CONFIGS[config_id] = {
        "name": request.name,
        "provider": request.provider,
        "region": request.region,
        "access_key": request.access_key,
        "secret_key": request.secret_key,
        "enabled": request.enabled,
        "status": "disconnected",
        "last_sync": None,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Created cloud configuration: {config_id}")
    
    return {
        "status": "success",
        "config_id": config_id,
        "message": "Cloud configuration created successfully"
    }


@router.post("/cloud/test/{config_id}", summary="测试云平台连接")
async def test_cloud_connection(config_id: str = Path(..., description="Configuration ID")) -> Dict[str, Any]:
    """
    测试云平台配置的连接
    """
    if config_id not in CLOUD_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Cloud configuration {config_id} not found")
    
    config = CLOUD_CONFIGS[config_id]
    result = test_connection_mock(f"{config['provider'].upper()}", config)
    
    config["status"] = "connected" if result["status"] == "success" else "error"
    config["last_sync"] = datetime.utcnow().isoformat()
    
    return {
        "status": "success",
        "test_result": result
    }


# ============================================================================
# GitOps Endpoints
# ============================================================================

@router.get("/gitops/config", summary="获取GitOps配置列表")
async def get_gitops_configs() -> Dict[str, Any]:
    """
    获取所有GitOps配置
    """
    configs = []
    for config_id, config in GITOPS_CONFIGS.items():
        configs.append({
            "config_id": config_id,
            "name": config["name"],
            "gitops_type": config["gitops_type"],
            "url": config["url"],
            "enabled": config["enabled"],
            "status": config["status"],
            "last_sync": config["last_sync"]
        })
    
    return {
        "status": "success",
        "configs": configs
    }


@router.post("/gitops/config", summary="创建GitOps配置")
async def create_gitops_config(request: GitOpsConfigRequest) -> Dict[str, Any]:
    """
    创建新的GitOps配置
    """
    config_id = generate_config_id()
    
    GITOPS_CONFIGS[config_id] = {
        "name": request.name,
        "gitops_type": request.gitops_type,
        "url": request.url,
        "token": request.token,
        "enabled": request.enabled,
        "status": "disconnected",
        "last_sync": None,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Created GitOps configuration: {config_id}")
    
    return {
        "status": "success",
        "config_id": config_id,
        "message": "GitOps configuration created successfully"
    }


@router.post("/gitops/test/{config_id}", summary="测试GitOps连接")
async def test_gitops_connection(config_id: str = Path(..., description="Configuration ID")) -> Dict[str, Any]:
    """
    测试GitOps配置的连接
    """
    if config_id not in GITOPS_CONFIGS:
        raise HTTPException(status_code=404, detail=f"GitOps configuration {config_id} not found")
    
    config = GITOPS_CONFIGS[config_id]
    result = test_connection_mock(config["gitops_type"], config)
    
    config["status"] = "connected" if result["status"] == "success" else "error"
    config["last_sync"] = datetime.utcnow().isoformat()
    
    return {
        "status": "success",
        "test_result": result
    }


# ============================================================================
# CI/CD Endpoints
# ============================================================================

@router.get("/cicd/config", summary="获取CI/CD配置列表")
async def get_cicd_configs() -> Dict[str, Any]:
    """
    获取所有CI/CD配置
    """
    configs = []
    for config_id, config in CICD_CONFIGS.items():
        configs.append({
            "config_id": config_id,
            "name": config["name"],
            "cicd_type": config["cicd_type"],
            "url": config["url"],
            "enabled": config["enabled"],
            "status": config["status"],
            "last_sync": config["last_sync"]
        })
    
    return {
        "status": "success",
        "configs": configs
    }


@router.post("/cicd/config", summary="创建CI/CD配置")
async def create_cicd_config(request: CICDConfigRequest) -> Dict[str, Any]:
    """
    创建新的CI/CD配置
    """
    config_id = generate_config_id()
    
    CICD_CONFIGS[config_id] = {
        "name": request.name,
        "cicd_type": request.cicd_type,
        "url": request.url,
        "token": request.token,
        "enabled": request.enabled,
        "status": "disconnected",
        "last_sync": None,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Created CI/CD configuration: {config_id}")
    
    return {
        "status": "success",
        "config_id": config_id,
        "message": "CI/CD configuration created successfully"
    }


@router.post("/cicd/test/{config_id}", summary="测试CI/CD连接")
async def test_cicd_connection(config_id: str = Path(..., description="Configuration ID")) -> Dict[str, Any]:
    """
    测试CI/CD配置的连接
    """
    if config_id not in CICD_CONFIGS:
        raise HTTPException(status_code=404, detail=f"CI/CD configuration {config_id} not found")
    
    config = CICD_CONFIGS[config_id]
    result = test_connection_mock(config["cicd_type"], config)
    
    config["status"] = "connected" if result["status"] == "success" else "error"
    config["last_sync"] = datetime.utcnow().isoformat()
    
    return {
        "status": "success",
        "test_result": result
    }


# ============================================================================
# ITSM Endpoints
# ============================================================================

@router.get("/itsm/config", summary="获取ITSM配置列表")
async def get_itsm_configs() -> Dict[str, Any]:
    """
    获取所有ITSM配置
    """
    configs = []
    for config_id, config in ITSM_CONFIGS.items():
        configs.append({
            "config_id": config_id,
            "name": config["name"],
            "itsm_type": config["itsm_type"],
            "url": config["url"],
            "username": config["username"],
            "enabled": config["enabled"],
            "status": config["status"],
            "last_sync": config["last_sync"]
        })
    
    return {
        "status": "success",
        "configs": configs
    }


@router.post("/itsm/config", summary="创建ITSM配置")
async def create_itsm_config(request: ITSMConfigRequest) -> Dict[str, Any]:
    """
    创建新的ITSM配置
    """
    config_id = generate_config_id()
    
    ITSM_CONFIGS[config_id] = {
        "name": request.name,
        "itsm_type": request.itsm_type,
        "url": request.url,
        "username": request.username,
        "password": request.password,
        "enabled": request.enabled,
        "status": "disconnected",
        "last_sync": None,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Created ITSM configuration: {config_id}")
    
    return {
        "status": "success",
        "config_id": config_id,
        "message": "ITSM configuration created successfully"
    }


@router.post("/itsm/test/{config_id}", summary="测试ITSM连接")
async def test_itsm_connection(config_id: str = Path(..., description="Configuration ID")) -> Dict[str, Any]:
    """
    测试ITSM配置的连接
    """
    if config_id not in ITSM_CONFIGS:
        raise HTTPException(status_code=404, detail=f"ITSM configuration {config_id} not found")
    
    config = ITSM_CONFIGS[config_id]
    result = test_connection_mock(config["itsm_type"], config)
    
    config["status"] = "connected" if result["status"] == "success" else "error"
    config["last_sync"] = datetime.utcnow().isoformat()
    
    return {
        "status": "success",
        "test_result": result
    }


# ============================================================================
# Oncall Endpoints
# ============================================================================

@router.get("/oncall/config", summary="获取Oncall配置列表")
async def get_oncall_configs() -> Dict[str, Any]:
    """
    获取所有Oncall配置
    """
    configs = []
    for config_id, config in ONCALL_CONFIGS.items():
        configs.append({
            "config_id": config_id,
            "name": config["name"],
            "provider": config["provider"],
            "enabled": config["enabled"],
            "status": config["status"],
            "last_sync": config["last_sync"]
        })
    
    return {
        "status": "success",
        "configs": configs
    }


@router.post("/oncall/config", summary="创建Oncall配置")
async def create_oncall_config(request: OncallConfigRequest) -> Dict[str, Any]:
    """
    创建新的Oncall配置
    """
    config_id = generate_config_id()
    
    ONCALL_CONFIGS[config_id] = {
        "name": request.name,
        "provider": request.provider,
        "api_key": request.api_key,
        "enabled": request.enabled,
        "status": "disconnected",
        "last_sync": None,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Created Oncall configuration: {config_id}")
    
    return {
        "status": "success",
        "config_id": config_id,
        "message": "Oncall configuration created successfully"
    }


@router.post("/oncall/test/{config_id}", summary="测试Oncall连接")
async def test_oncall_connection(config_id: str = Path(..., description="Configuration ID")) -> Dict[str, Any]:
    """
    测试Oncall配置的连接
    """
    if config_id not in ONCALL_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Oncall configuration {config_id} not found")
    
    config = ONCALL_CONFIGS[config_id]
    result = test_connection_mock(config["provider"], config)
    
    config["status"] = "connected" if result["status"] == "success" else "error"
    config["last_sync"] = datetime.utcnow().isoformat()
    
    return {
        "status": "success",
        "test_result": result
    }


# ============================================================================
# Slack Endpoints
# ============================================================================

@router.get("/slack/config", summary="获取Slack配置列表")
async def get_slack_configs() -> Dict[str, Any]:
    """
    获取所有Slack配置
    """
    configs = []
    for config_id, config in SLACK_CONFIGS.items():
        configs.append({
            "config_id": config_id,
            "name": config["name"],
            "workspace": config["workspace"],
            "enabled": config["enabled"],
            "status": config["status"],
            "last_sync": config["last_sync"],
            "channel_count": config.get("channel_count", 0)
        })
    
    return {
        "status": "success",
        "configs": configs
    }


@router.post("/slack/config", summary="创建Slack配置")
async def create_slack_config(request: SlackConfigRequest) -> Dict[str, Any]:
    """
    创建新的Slack配置
    """
    config_id = generate_config_id()
    
    SLACK_CONFIGS[config_id] = {
        "name": request.name,
        "workspace": request.workspace,
        "bot_token": request.bot_token,
        "signing_secret": request.signing_secret,
        "enabled": request.enabled,
        "status": "disconnected",
        "last_sync": None,
        "channel_count": 0,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Created Slack configuration: {config_id}")
    
    return {
        "status": "success",
        "config_id": config_id,
        "message": "Slack configuration created successfully"
    }


@router.post("/slack/test/{config_id}", summary="测试Slack连接")
async def test_slack_connection(config_id: str = Path(..., description="Configuration ID")) -> Dict[str, Any]:
    """
    测试Slack配置的连接
    """
    if config_id not in SLACK_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Slack configuration {config_id} not found")
    
    config = SLACK_CONFIGS[config_id]
    result = test_connection_mock("Slack", config)
    
    config["status"] = "connected" if result["status"] == "success" else "error"
    config["last_sync"] = datetime.utcnow().isoformat()
    
    return {
        "status": "success",
        "test_result": result
    }


# ============================================================================
# Jira Endpoints
# ============================================================================

@router.get("/jira/config", summary="获取Jira配置列表")
async def get_jira_configs() -> Dict[str, Any]:
    """
    获取所有Jira配置
    """
    configs = []
    for config_id, config in JIRA_CONFIGS.items():
        configs.append({
            "config_id": config_id,
            "name": config["name"],
            "url": config["url"],
            "username": config["username"],
            "enabled": config["enabled"],
            "status": config["status"],
            "last_sync": config["last_sync"]
        })
    
    return {
        "status": "success",
        "configs": configs
    }


@router.post("/jira/config", summary="创建Jira配置")
async def create_jira_config(request: JiraConfigRequest) -> Dict[str, Any]:
    """
    创建新的Jira配置
    """
    config_id = generate_config_id()
    
    JIRA_CONFIGS[config_id] = {
        "name": request.name,
        "url": request.url,
        "username": request.username,
        "api_token": request.api_token,
        "enabled": request.enabled,
        "status": "disconnected",
        "last_sync": None,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Created Jira configuration: {config_id}")
    
    return {
        "status": "success",
        "config_id": config_id,
        "message": "Jira configuration created successfully"
    }


@router.post("/jira/test/{config_id}", summary="测试Jira连接")
async def test_jira_connection(config_id: str = Path(..., description="Configuration ID")) -> Dict[str, Any]:
    """
    测试Jira配置的连接
    """
    if config_id not in JIRA_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Jira configuration {config_id} not found")
    
    config = JIRA_CONFIGS[config_id]
    result = test_connection_mock("Jira", config)
    
    config["status"] = "connected" if result["status"] == "success" else "error"
    config["last_sync"] = datetime.utcnow().isoformat()
    
    return {
        "status": "success",
        "test_result": result
    }


# ============================================================================
# ServiceNow Endpoints
# ============================================================================

@router.get("/servicenow/config", summary="获取ServiceNow配置列表")
async def get_servicenow_configs() -> Dict[str, Any]:
    """
    获取所有ServiceNow配置
    """
    configs = []
    for config_id, config in SERVICENOW_CONFIGS.items():
        configs.append({
            "config_id": config_id,
            "name": config["name"],
            "instance_url": config["instance_url"],
            "username": config["username"],
            "enabled": config["enabled"],
            "status": config["status"],
            "last_sync": config["last_sync"]
        })
    
    return {
        "status": "success",
        "configs": configs
    }


@router.post("/servicenow/config", summary="创建ServiceNow配置")
async def create_servicenow_config(request: ServiceNowConfigRequest) -> Dict[str, Any]:
    """
    创建新的ServiceNow配置
    """
    config_id = generate_config_id()
    
    SERVICENOW_CONFIGS[config_id] = {
        "name": request.name,
        "instance_url": request.instance_url,
        "username": request.username,
        "password": request.password,
        "enabled": request.enabled,
        "status": "disconnected",
        "last_sync": None,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Created ServiceNow configuration: {config_id}")
    
    return {
        "status": "success",
        "config_id": config_id,
        "message": "ServiceNow configuration created successfully"
    }


@router.post("/servicenow/test/{config_id}", summary="测试ServiceNow连接")
async def test_servicenow_connection(config_id: str = Path(..., description="Configuration ID")) -> Dict[str, Any]:
    """
    测试ServiceNow配置的连接
    """
    if config_id not in SERVICENOW_CONFIGS:
        raise HTTPException(status_code=404, detail=f"ServiceNow configuration {config_id} not found")
    
    config = SERVICENOW_CONFIGS[config_id]
    result = test_connection_mock("ServiceNow", config)
    
    config["status"] = "connected" if result["status"] == "success" else "error"
    config["last_sync"] = datetime.utcnow().isoformat()
    
    return {
        "status": "success",
        "test_result": result
    }


# ============================================================================
# Message Queue Endpoints
# ============================================================================

@router.get("/message-queue/config", summary="获取消息队列配置列表")
async def get_message_queue_configs() -> Dict[str, Any]:
    """
    获取所有消息队列配置
    """
    configs = []
    for config_id, config in MESSAGE_QUEUE_CONFIGS.items():
        configs.append({
            "config_id": config_id,
            "name": config["name"],
            "mq_type": config["mq_type"],
            "host": config["host"],
            "port": config["port"],
            "enabled": config["enabled"],
            "status": config["status"],
            "last_sync": config["last_sync"],
            "queue_count": config.get("queue_count", 0)
        })
    
    return {
        "status": "success",
        "configs": configs
    }


@router.post("/message-queue/config", summary="创建消息队列配置")
async def create_message_queue_config(request: MessageQueueConfigRequest) -> Dict[str, Any]:
    """
    创建新的消息队列配置
    """
    config_id = generate_config_id()
    
    MESSAGE_QUEUE_CONFIGS[config_id] = {
        "name": request.name,
        "mq_type": request.mq_type,
        "host": request.host,
        "port": request.port,
        "username": request.username,
        "password": request.password,
        "enabled": request.enabled,
        "status": "disconnected",
        "last_sync": None,
        "queue_count": 0,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Created message queue configuration: {config_id}")
    
    return {
        "status": "success",
        "config_id": config_id,
        "message": "Message queue configuration created successfully"
    }


@router.post("/message-queue/test/{config_id}", summary="测试消息队列连接")
async def test_message_queue_connection(config_id: str = Path(..., description="Configuration ID")) -> Dict[str, Any]:
    """
    测试消息队列配置的连接
    """
    if config_id not in MESSAGE_QUEUE_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Message queue configuration {config_id} not found")
    
    config = MESSAGE_QUEUE_CONFIGS[config_id]
    result = test_connection_mock(config["mq_type"], config)
    
    config["status"] = "connected" if result["status"] == "success" else "error"
    config["last_sync"] = datetime.utcnow().isoformat()
    
    return {
        "status": "success",
        "test_result": result
    }


# ============================================================================
# GitHub Endpoints
# ============================================================================

@router.get("/github/config", summary="获取GitHub配置列表")
async def get_github_configs() -> Dict[str, Any]:
    """
    获取所有GitHub配置
    """
    configs = []
    for config_id, config in GITHUB_CONFIGS.items():
        configs.append({
            "config_id": config_id,
            "name": config["name"],
            "owner": config["owner"],
            "repo": config["repo"],
            "enabled": config["enabled"],
            "status": config["status"],
            "last_sync": config["last_sync"]
        })
    
    return {
        "status": "success",
        "configs": configs
    }


@router.post("/github/config", summary="创建GitHub配置")
async def create_github_config(request: GitHubConfigRequest) -> Dict[str, Any]:
    """
    创建新的GitHub配置
    """
    config_id = generate_config_id()
    
    GITHUB_CONFIGS[config_id] = {
        "name": request.name,
        "owner": request.owner,
        "repo": request.repo,
        "token": request.token,
        "enabled": request.enabled,
        "status": "disconnected",
        "last_sync": None,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Created GitHub configuration: {config_id}")
    
    return {
        "status": "success",
        "config_id": config_id,
        "message": "GitHub configuration created successfully"
    }


@router.post("/github/test/{config_id}", summary="测试GitHub连接")
async def test_github_connection(config_id: str = Path(..., description="Configuration ID")) -> Dict[str, Any]:
    """
    测试GitHub配置的连接
    """
    if config_id not in GITHUB_CONFIGS:
        raise HTTPException(status_code=404, detail=f"GitHub configuration {config_id} not found")
    
    config = GITHUB_CONFIGS[config_id]
    result = test_connection_mock("GitHub", config)
    
    config["status"] = "connected" if result["status"] == "success" else "error"
    config["last_sync"] = datetime.utcnow().isoformat()
    
    return {
        "status": "success",
        "test_result": result
    }


# ============================================================================
# ELK Stack Endpoints
# ============================================================================

@router.get("/elk/config", summary="获取ELK Stack配置列表")
async def get_elk_configs() -> Dict[str, Any]:
    """
    获取所有ELK Stack配置
    """
    configs = []
    for config_id, config in ELK_CONFIGS.items():
        configs.append({
            "config_id": config_id,
            "name": config["name"],
            "elasticsearch_url": config["elasticsearch_url"],
            "kibana_url": config.get("kibana_url"),
            "logstash_url": config.get("logstash_url"),
            "enabled": config["enabled"],
            "status": config["status"],
            "last_sync": config["last_sync"],
            "index_count": config.get("index_count", 0)
        })
    
    return {
        "status": "success",
        "configs": configs
    }


@router.post("/elk/config", summary="创建ELK Stack配置")
async def create_elk_config(request: ELKConfigRequest) -> Dict[str, Any]:
    """
    创建新的ELK Stack配置
    """
    config_id = generate_config_id()
    
    ELK_CONFIGS[config_id] = {
        "name": request.name,
        "elasticsearch_url": request.elasticsearch_url,
        "kibana_url": request.kibana_url,
        "logstash_url": request.logstash_url,
        "username": request.username,
        "password": request.password,
        "enabled": request.enabled,
        "status": "disconnected",
        "last_sync": None,
        "index_count": 0,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Created ELK Stack configuration: {config_id}")
    
    return {
        "status": "success",
        "config_id": config_id,
        "message": "ELK Stack configuration created successfully"
    }


@router.post("/elk/test/{config_id}", summary="测试ELK Stack连接")
async def test_elk_connection(config_id: str = Path(..., description="Configuration ID")) -> Dict[str, Any]:
    """
    测试ELK Stack配置的连接
    """
    if config_id not in ELK_CONFIGS:
        raise HTTPException(status_code=404, detail=f"ELK Stack configuration {config_id} not found")
    
    config = ELK_CONFIGS[config_id]
    result = test_connection_mock("Elasticsearch", config)
    
    config["status"] = "connected" if result["status"] == "success" else "error"
    config["last_sync"] = datetime.utcnow().isoformat()
    
    return {
        "status": "success",
        "test_result": result
    }


# ============================================================================
# Datadog Endpoints
# ============================================================================

@router.get("/datadog/config", summary="获取Datadog配置列表")
async def get_datadog_configs() -> Dict[str, Any]:
    """
    获取所有Datadog配置
    """
    configs = []
    for config_id, config in DATADOG_CONFIGS.items():
        configs.append({
            "config_id": config_id,
            "name": config["name"],
            "site": config["site"],
            "enabled": config["enabled"],
            "status": config["status"],
            "last_sync": config["last_sync"]
        })
    
    return {
        "status": "success",
        "configs": configs
    }


@router.post("/datadog/config", summary="创建Datadog配置")
async def create_datadog_config(request: DatadogConfigRequest) -> Dict[str, Any]:
    """
    创建新的Datadog配置
    """
    config_id = generate_config_id()
    
    DATADOG_CONFIGS[config_id] = {
        "name": request.name,
        "api_key": request.api_key,
        "app_key": request.app_key,
        "site": request.site,
        "enabled": request.enabled,
        "status": "disconnected",
        "last_sync": None,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Created Datadog configuration: {config_id}")
    
    return {
        "status": "success",
        "config_id": config_id,
        "message": "Datadog configuration created successfully"
    }


@router.post("/datadog/test/{config_id}", summary="测试Datadog连接")
async def test_datadog_connection(config_id: str = Path(..., description="Configuration ID")) -> Dict[str, Any]:
    """
    测试Datadog配置的连接
    """
    if config_id not in DATADOG_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Datadog configuration {config_id} not found")
    
    config = DATADOG_CONFIGS[config_id]
    result = test_connection_mock("Datadog", config)
    
    config["status"] = "connected" if result["status"] == "success" else "error"
    config["last_sync"] = datetime.utcnow().isoformat()
    
    return {
        "status": "success",
        "test_result": result
    }


# ============================================================================
# Grafana Endpoints
# ============================================================================

@router.get("/grafana/config", summary="获取Grafana配置列表")
async def get_grafana_configs() -> Dict[str, Any]:
    """
    获取所有Grafana配置
    """
    configs = []
    for config_id, config in GRAFANA_CONFIGS.items():
        configs.append({
            "config_id": config_id,
            "name": config["name"],
            "url": config["url"],
            "enabled": config["enabled"],
            "status": config["status"],
            "last_sync": config["last_sync"],
            "dashboard_count": config.get("dashboard_count", 0)
        })
    
    return {
        "status": "success",
        "configs": configs
    }


@router.post("/grafana/config", summary="创建Grafana配置")
async def create_grafana_config(request: GrafanaConfigRequest) -> Dict[str, Any]:
    """
    创建新的Grafana配置
    """
    config_id = generate_config_id()
    
    GRAFANA_CONFIGS[config_id] = {
        "name": request.name,
        "url": request.url,
        "api_key": request.api_key,
        "enabled": request.enabled,
        "status": "disconnected",
        "last_sync": None,
        "dashboard_count": 0,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Created Grafana configuration: {config_id}")
    
    return {
        "status": "success",
        "config_id": config_id,
        "message": "Grafana configuration created successfully"
    }


@router.post("/grafana/test/{config_id}", summary="测试Grafana连接")
async def test_grafana_connection(config_id: str = Path(..., description="Configuration ID")) -> Dict[str, Any]:
    """
    测试Grafana配置的连接
    """
    if config_id not in GRAFANA_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Grafana configuration {config_id} not found")
    
    config = GRAFANA_CONFIGS[config_id]
    result = test_connection_mock("Grafana", config)
    
    config["status"] = "connected" if result["status"] == "success" else "error"
    config["last_sync"] = datetime.utcnow().isoformat()
    
    return {
        "status": "success",
        "test_result": result
    }


# ============================================================================
# Prometheus Endpoints
# ============================================================================

@router.get("/prometheus/config", summary="获取Prometheus配置列表")
async def get_prometheus_configs() -> Dict[str, Any]:
    """
    获取所有Prometheus配置
    """
    configs = []
    for config_id, config in PROMETHEUS_CONFIGS.items():
        configs.append({
            "config_id": config_id,
            "name": config["name"],
            "url": config["url"],
            "enabled": config["enabled"],
            "status": config["status"],
            "last_sync": config["last_sync"],
            "metrics_count": config.get("metrics_count", 0)
        })
    
    return {
        "status": "success",
        "configs": configs
    }


@router.post("/prometheus/config", summary="创建Prometheus配置")
async def create_prometheus_config(request: PrometheusConfigRequest) -> Dict[str, Any]:
    """
    创建新的Prometheus配置
    """
    config_id = generate_config_id()
    
    PROMETHEUS_CONFIGS[config_id] = {
        "name": request.name,
        "url": request.url,
        "username": request.username,
        "password": request.password,
        "enabled": request.enabled,
        "status": "disconnected",
        "last_sync": None,
        "metrics_count": 0,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Created Prometheus configuration: {config_id}")
    
    return {
        "status": "success",
        "config_id": config_id,
        "message": "Prometheus configuration created successfully"
    }


@router.post("/prometheus/test/{config_id}", summary="测试Prometheus连接")
async def test_prometheus_connection(config_id: str = Path(..., description="Configuration ID")) -> Dict[str, Any]:
    """
    测试Prometheus配置的连接
    """
    if config_id not in PROMETHEUS_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Prometheus configuration {config_id} not found")
    
    config = PROMETHEUS_CONFIGS[config_id]
    result = test_connection_mock("Prometheus", config)
    
    config["status"] = "connected" if result["status"] == "success" else "error"
    config["last_sync"] = datetime.utcnow().isoformat()
    
    return {
        "status": "success",
        "test_result": result
    }
