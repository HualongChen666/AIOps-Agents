# -*- coding: utf-8 -*-
import logging

from api.middleware.rbac_middleware import RBACMiddleware
from api.middleware.tenant_middleware import TenantMiddleware
from core.accessibility_support import setup_accessibility_support
from core.ai_engine import _get_http_client as _ai_get_http_client
from core.analysis.l2.enhanced_causal_analyzer import get_enhanced_causal_analyzer
from core.api_error import (
    api_error_handler,
    general_exception_handler,
    validation_error_handler,
)
from core.api_governance import setup_api_governance
from core.api_performance_optimizer import get_api_performance_optimizer
from core.api_response_middleware import setup_api_response_middleware
from core.audit_integration_manager import get_audit_integration_manager
from core.business_metrics import setup_business_metrics
from core.chaos_engineering import setup_chaos_engineering
from core.cicd_integration_manager import get_cicd_integration_manager
from core.cicd_pipeline_manager import get_cicd_pipeline_manager
from core.command_guard import register_self_pid
# from core.compliance_manager import get_compliance_manager
from core.config_center import get_config_center, get_service_discovery
from core.data_integration_manager import get_data_integration_manager
from core.data_lifecycle_manager import setup_data_lifecycle
from core.database_optimization_manager import get_database_optimization_manager
from core.db_read_write_router import get_read_write_router
from core.disaster_recovery_drill import setup_disaster_recovery
from core.distributed_storage import get_distributed_storage_manager
from core.documentation_generator import get_documentation_generator
from core.documentation_manager import get_documentation_manager
from core.dr_scenarios import list_dr_scenarios, run_dr_scenario
from core.enhanced_auth_integration import get_enhanced_auth_integration
from core.enhanced_websocket_manager import get_enhanced_websocket_manager
from core.error_recovery import setup_error_recovery
from core.exception_handler import setup_exception_handlers
from core.execution.l6.fault_tolerant_executor import get_fault_tolerant_executor
from core.external_api_audit import initialize_external_api_audit
from core.flink_stream_processor import get_flink_job_manager
from core.frontend_cache_strategy import setup_cache_headers_middleware
from core.frontend_performance_optimizer import get_frontend_performance_optimizer
from core.i18n_manager import get_i18n_manager
from core.integration_documentation_manager import get_integration_documentation_manager
from core.integration_monitoring_system import get_integration_monitoring_system
from core.integration_test_validator import get_integration_test_validator
from core.integration_testing_system import get_integration_testing_system
from core.kafka_stream_processor import get_kafka_processor
from core.key_management_service import initialize_key_management
from core.kubernetes_deployment_manager import get_kubernetes_deployment_manager
from core.l1l2_data_flow_integrator import get_l1l2_data_flow_integrator
from core.l2l3_workflow_integrator import get_l2l3_workflow_integrator
from core.l3l4_storage_integrator import get_l3l4_storage_integrator
from core.l4l5_data_integrator import get_l4l5_data_integrator
from core.l5l6_execution_integrator import get_l5l6_execution_integrator
from core.l6l7_frontend_integrator import get_l6l7_frontend_integrator
from core.localization_adapter import get_localization_adapter
from core.localization_resource_manager import get_resource_manager
from core.memory_monitor import setup_memory_monitoring
from core.model_fine_tuner import get_model_fine_tuner
from core.module_dependencies import validate_initialization_order
from core.module_health_check import check_all_modules_health
from core.monitoring_infrastructure import get_monitoring_infrastructure
from core.notify_engine import _get_http_client as _notify_get_http_client
from core.performance_integration_tester import get_performance_integration_tester
from core.performance_optimizer import get_performance_optimizer
from core.plugin_development_sdk import get_plugin_sdk
from core.plugin_ecosystem_manager import get_ecosystem_manager
from core.plugin_marketplace_manager import get_marketplace_manager
from core.plugin_system_manager import get_plugin_system_manager
from core.rate_limiter import add_concurrency_middleware
from core.request_tracking import RequestTrackingMiddleware
from core.security_audit_system import get_security_audit_system
from core.security_input_validator import add_input_validation_middleware
from core.security_system_integrator import get_security_system_integrator
from core.security_testing_system import get_security_testing_system
from core.service_discovery_manager import get_service_discovery_manager
from core.service_mesh_manager import get_service_mesh_manager
from core.service_monitoring_manager import get_service_monitoring_manager
from core.slack_adapter import close_slack_client
from core.sso_auth import router as sso_router
from core.stats_engine import _get_http_client as _stats_get_http_client
from core.structured_logging import setup_logging
from core.system_resource_optimizer import get_system_resource_optimizer
from core.teams_adapter import close_teams_client
from core.test_automation_manager import get_automation_manager
from core.test_coverage_manager import get_coverage_manager
from core.test_framework_manager import get_test_framework_manager
from core.third_party_service_integrator import get_third_party_service_integrator
from core.unified_access_control import (
    add_access_control_middleware,
    setup_default_access_policies,
)
from core.user_training_system import get_user_training_system
from core.vulnerability_manager import get_vulnerability_manager
from core.websocket_integrator import get_websocket_integrator

"""
FastAPI 主入口文件 – 已在原项目中实现多个路由注册。
本次更新：
1. 添加 Microsoft Teams 路由 ``teams_router`` 的导入与注册。
2. 在 ``lifespan`` 关闭阶段调用 ``close_teams_client`` 释放 Teams HTTP 客户端资源。
3. 新增 Windows 修复 API 路由 ``windows_repair_router`` 的导入与注册。
4. 新增 RAG 语义搜索 API 路由 ``rag_router`` 的导入与注册。
5. 新增审计中心页面路由 ``audit_center_router`` 的导入与注册。
"""

import asyncio
import inspect
import os
import traceback
import warnings
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger as _logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Core routers are always imported and mounted
from api.alert_router import router as alert_router
from api.alerts_advanced_router import router as alert_advanced_router
from api.alert_webhook_router import router as alert_webhook_router
from api.anomaly_router import router as anomaly_router
from api.api_performance_router import router as api_performance_router
from api.assets_router import router as assets_router
from api.audit_center_router import router as audit_center_router
from api.audit_router import router as audit_router
from api.auth_router import router as auth_router
from api.disaster_router import router as disaster_router
from api.autoheal_router import router as autoheal_router
from api.builder_router import router as builder_router
from api.chart_aggregation_router import router as chart_aggregation_router
from api.business_impact_advanced_router import router as business_impact_advanced_router
from api.business_impact_router import router as business_impact_router
from api.capacity_router import router as capacity_router
from api.change_management_router import router as change_management_router
from api.collaboration_advanced_router import router as collaboration_advanced_router
from api.collaboration_router import router as collaboration_router
from api.compliance_audit_router import router as compliance_audit_router
from api.cost_advanced_router import router as cost_advanced_router
from api.cost_router import router as cost_router
from api.monitoring_config_router import router as monitoring_config_router
from api.performance_optimization_router import router as performance_optimization_router
from api.performance_router import router as performance_router
from api.guard_router import router as guard_router
from api.guard_router import security_router as security_router
from api.health_router import router as health_router
from api.hitl_approval_router import router as hitl_approval_router
from api.linux_router import router as linux_router
from api.macos_router import router as macos_router
from api.maturity_router import router as maturity_router
from api.repair_advanced_router import router as repair_advanced_router
from api.repair_scripts_router import router as repair_scripts_router
from api.settings_router import router as settings_router
from api.slack_router import router as slack_router
from api.slo_router import router as slo_router
from api.sse_router import router as sse_router
from api.stats_router import router as stats_router
from api.team_collaboration_router import router as team_collaboration_router
from api.teams_router import router as teams_router
from api.tenant_router import router as tenant_router
from api.tenant_advanced_router import router as tenant_advanced_router
from api.topology_advanced_router import (
    router as topology_advanced_router,
    router_alt as topology_advanced_router_alt,
    router_v1 as topology_advanced_router_v1,
)
from api.tracing_advanced_router import (
    router as tracing_advanced_router,
    router_alt as tracing_advanced_router_alt,
    router_v1 as tracing_advanced_router_v1,
)
from api.unified_repair_advanced_router import (
    router as unified_repair_advanced_router,
    router_alt as unified_repair_advanced_router_alt,
    router_v1 as unified_repair_advanced_router_v1,
)
from api.unified_repair_router import router as unified_repair_router
from api.users_router import router as users_router
from api.users_advanced_router import router as users_advanced_router
from api.vulnerability_router import router as vulnerability_router
from api.websocket_router import router as websocket_router
from api.windows_repair_router import router as windows_repair_router
from config import (
    DOC_GENERATION_ENABLED,
    ENABLE_ADDONS,
    GRAPHQL_ENABLED,
    I18N_ENABLED,
    INCIDENT_RESPONSE_ENABLED,
    INTEGRATIONS_ENABLED,
    LLM_ROUTER_ENABLED,
    LOG_AGGREGATION_ENABLED,
    MCP_ENABLED,
    METRICS_ENABLED,
    PLUGINS_ENABLED,
    RAG_ENABLED,
    SECURITY_SCANNING_ENABLED,
    TOPOLOGY_ENABLED,
    TRACING_ENABLED,
    WORKFLOW_ENABLED,
)
from core.auth_db import init_db

# Add-on routers are loaded only when their pack flag is enabled
advanced_ai_router: Any = None
ai_feedback_router: Any = None
ai_router: Any = None
root_cause_router: Any = None
apm_router: Any = None
tracing_router: Any = None
backup_router: Any = None
enterprise_router: Any = None
enterprise_router_append: Any = None
batch_router: Any = None
hitl_router: Any = None
notify_router: Any = None
priority_router: Any = None
chaos_router: Any = None
chaos_simple_router: Any = None
cloud_router: Any = None
database_advanced_router: Any = None
database_optimization_router: Any = None
grpc_router: Any = None
grpc_service_router: Any = None
infrastructure_advanced_router: Any = None
infrastructure_router: Any = None
itsm_advanced_router: Any = None
mcp_router: Any = None
plugin_development_router: Any = None
plugin_ecosystem_router: Any = None
plugin_marketplace_router: Any = None
plugin_router: Any = None
plugin_sdk_router: Any = None
system_resource_router: Any = None
test_automation_router: Any = None
test_coverage_router: Any = None
test_framework_router: Any = None
graphql_router: Any = None
dashboard_router: Any = None
integration_router: Any = None
itsm_router: Any = None
doc_generator_router: Any = None
documentation_router: Any = None
documentation_advanced_router: Any = None
enterprise_advanced_router: Any = None
frontend_enhancement_router: Any = None
frontend_advanced_router: Any = None
i18n_router: Any = None
i18n_router_append: Any = None
localization_adapter_router: Any = None
localization_resource_router: Any = None
localization_advanced_router: Any = None
notify_advanced_router: Any = None
plugin_development_advanced_router: Any = None
plugin_marketplace_advanced_router: Any = None
log_router: Any = None
metrics_router: Any = None
qdrant_router: Any = None
rag_history_router: Any = None
rag_router: Any = None
realtime_router: Any = None
realtime_advanced_router: Any = None
service_discovery_router: Any = None
service_discovery_advanced_router: Any = None
service_mesh_router: Any = None
service_mesh_advanced_router: Any = None
service_monitoring_router: Any = None
service_monitoring_advanced_router: Any = None
topology_router: Any = None
topology_view_router: Any = None
workflow_router: Any = None
workflow_advanced_router: Any = None
workflow_visualization_router: Any = None
priority_advanced_router: Any = None
root_cause_advanced_router: Any = None

if ENABLE_ADDONS:
    if LLM_ROUTER_ENABLED:
        from api.advanced_ai_router import router as advanced_ai_router
        from api.ai_advanced_router import router as ai_advanced_router
        from api.ai_feedback_router import router as ai_feedback_router
        from api.ai_router import router as ai_router
        from api.root_cause_router import router as root_cause_router
        from api.root_cause_advanced_router import router as root_cause_advanced_router
    if RAG_ENABLED:
        from api.qdrant_router import router as qdrant_router
        from api.rag_history_router import router as rag_history_router
        from api.rag_router import router as rag_router
    if METRICS_ENABLED:
        from api.metrics_router import router as metrics_router
    if TOPOLOGY_ENABLED:
        from api.realtime_router import router as realtime_router
        from api.realtime_advanced_router import router as realtime_advanced_router
        from api.service_discovery_router import router as service_discovery_router
        from api.service_discovery_advanced_router import (
            router as service_discovery_advanced_router,
        )
        from api.service_mesh_router import router as service_mesh_router
        from api.service_mesh_advanced_router import router as service_mesh_advanced_router
        from api.service_monitoring_router import router as service_monitoring_router
        from api.service_monitoring_advanced_router import (
            router as service_monitoring_advanced_router,
        )
        from api.topology_router import router as topology_router
        from api.topology_advanced_router import router as topology_advanced_router
        from api.topology_view_router import router as topology_view_router
    if TRACING_ENABLED:
        from api.apm_router import router as apm_router
        from api.tracing_router import router as tracing_router
        from api.tracing_advanced_router import router as tracing_advanced_router
    if LOG_AGGREGATION_ENABLED:
        from api.log_router import router as log_router
    if INCIDENT_RESPONSE_ENABLED:
        from api.batch_router import router as batch_router
        from api.hitl_router import router as hitl_router
        from api.notify_router import router as notify_router
        from api.notify_advanced_router import router as notify_advanced_router
        from api.priority_router import router as priority_router
        from api.priority_advanced_router import router as priority_advanced_router
    if WORKFLOW_ENABLED:
        from api.workflow_router import router as workflow_router
        from api.workflow_advanced_router import router as workflow_advanced_router
        from api.workflow_visualization_router import router as workflow_visualization_router
    if INTEGRATIONS_ENABLED:
        from api.dashboard_router import router as dashboard_router
        from api.dashboard_advanced_router import router as dashboard_advanced_router
        from api.integration_router import router as integration_router
        from api.itsm_router import router as itsm_router
    if SECURITY_SCANNING_ENABLED:
        from api.backup_router import router as backup_router
        from api.enterprise_router import router as enterprise_router
        from api.enterprise_router_append import router as enterprise_router_append
        from api.enterprise_advanced_router import router as enterprise_advanced_router
    if PLUGINS_ENABLED:
        from api.chaos_advanced_router import router as chaos_advanced_router
        from api.chaos_router import router as chaos_router
        from api.chaos_simple_router import router as chaos_simple_router
        from api.cloud_router import router as cloud_router
        from api.database_advanced_router import router as database_advanced_router
        from api.database_optimization_router import router as database_optimization_router
        from api.grpc_router import router as grpc_router
        from api.grpc_service_router import router as grpc_service_router
        from api.infrastructure_advanced_router import router as infrastructure_advanced_router
        from api.infrastructure_router import router as infrastructure_router
        from api.itsm_advanced_router import router as itsm_advanced_router
        from api.plugin_development_router import router as plugin_development_router
        from api.plugin_development_advanced_router import (
            router as plugin_development_advanced_router,
        )

        # from api.plugin_ecosystem_router import router as plugin_ecosystem_router  # File doesn't exist
        from api.plugin_marketplace_router import router as plugin_marketplace_router
        from api.plugin_marketplace_advanced_router import (
            router as plugin_marketplace_advanced_router,
        )
        from api.plugin_router import router as plugin_router
        from api.plugin_sdk_router import router as plugin_sdk_router
        from api.system_resource_router import router as system_resource_router
        from api.test_automation_router import router as test_automation_router
        from api.test_automation_advanced_router import router as test_automation_advanced_router
        from api.test_coverage_router import router as test_coverage_router
        from api.test_coverage_advanced_router import router as test_coverage_advanced_router
        from api.test_framework_router import router as test_framework_router
        from api.test_framework_advanced_router import router as test_framework_advanced_router
        from api.maturity_advanced_router import router as maturity_advanced_router
        from api.dashboard_advanced_router import router as dashboard_advanced_router
    if GRAPHQL_ENABLED:
        from api.graphql_router import router as graphql_router
    if MCP_ENABLED:
        from api.mcp_router import router as mcp_router
    if I18N_ENABLED:
        from api.i18n_router import router as i18n_router
        from api.i18n_router_append import router as i18n_router_append
        from api.localization_adapter_router import router as localization_adapter_router
        from api.localization_resource_router import router as localization_resource_router
        from api.localization_advanced_router import router as localization_advanced_router
    if DOC_GENERATION_ENABLED:
        from api.doc_generator_router import router as doc_generator_router
        from api.documentation_router import router as documentation_router
        from api.documentation_advanced_router import router as documentation_advanced_router
        from api.frontend_enhancement_router import router as frontend_enhancement_router
        from api.frontend_advanced_router import router as frontend_advanced_router


warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
)


# ------------------------
# 日志初始化（保持不变）
# ------------------------
from slowapi.util import get_remote_address  # noqa: F401

from core.api_deprecation import mark_deprecated  # noqa: F401
from core.api_performance import monitor_api_performance  # noqa: F401
from core.concurrency_control import ConcurrencyController  # noqa: F401
from core.config_validation import setup_config_validation  # noqa: F401
from core.data_lifecycle_operations import archive_alerts, archive_metrics  # noqa: F401
from core.db_query_optimization import optimize_database_queries  # noqa: F401
from core.dependency_injection import di_container, setup_dependency_injection  # noqa: F401
from core.enhanced_caching import setup_enhanced_caching  # noqa: F401
from core.environment_config import setup_environment_configuration  # noqa: F401
from core.rate_limiting import ENDPOINT_LIMITS  # noqa: F401
from core.security_config import setup_enterprise_security  # noqa: F401
from core.security_middleware import (  # noqa: F401
    mfa_manager,
    password_policy,
    rate_limiter,
    security_headers,
    tls_enforcer,
)
from core.smart_cache_strategy import SmartCacheStrategy  # noqa: F401
from core.websocket_manager import manager  # noqa: F401


async def _rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Wrapper for rate limit exception handler to match FastAPI signature."""
    return _rate_limit_exceeded_handler(request, exc)


# Phase 2: Core Function Enhancement and Integration

# Phase 4: Security Compliance and Security Integration

# Phase 2: Actual implementations

# Phase 1: Infrastructure Enhancement Integration

# Phase 3: Advanced Function Implementation and Integration

# Phase 1: Module health and dependencies

# Phase 5: Optimization Verification and Integration Verification

# Phase 1: API enhancements

# Phase 1: Performance optimizations
# from core.eager_loading import EAGER_LOAD_CONFIGS  # Disabled for Python 3.14 compatibility
# Phase 1: Performance optimizations
# from core.eager_loading import EAGER_LOAD_CONFIGS  # Disabled for Python 3.14 compatibility

# ------------------------
# 配置 & 环境变量读取（保持原有 import）
# ------------------------
# from config import (
#     LOG_DIR,
#     LOG_FILE,
#     LOG_LEVEL,
#     # 其它配置保持不变 …
# )


# 这里不再重复声明 logger（已在 config 中配置），直接使用 _logger

# Setup structured logging
setup_logging(log_dir="logs", log_level="INFO")

# 🔧 P0 Security: Initialize key management service
try:
    backend_type = os.getenv("KEY_MANAGEMENT_BACKEND", "environment")
    initialize_key_management(backend_type=backend_type)
    _logger.info(f"Key management service initialized with {backend_type} backend")
except Exception as e:
    _logger.info(f"Key management service initialization failed (using fallback): {e}")

# 🔧 P0 Security: Initialize external API audit
try:
    initialize_external_api_audit()
    _logger.info("External API audit service initialized")
except Exception as e:
    _logger.info(f"External API audit initialization failed: {e}")


# P1-3: 高级AI能力路由

# Phase 4: API Performance Router

# 🔧 P1 Enhancement: APM监控路由

# 新增审计中心 页面路由

# 新增审计导出 & 报告路由

# 🔧 P1-6: 备份和恢复路由

# 新增仪表盘总览 页面路由

# Phase 4: Database Optimization Router

# Short-term Phase 3: Documentation Generator Router

# Short-term Phase 3: Documentation Router

# P1-4: 企业功能路由

# P1-6: 前端增强路由

# 新增 实时通信 Hook 路由（graphql_router 已按 PLUGINS_ENABLED 条件导入）

# Long-term Phase 1: gRPC Service Router

# P0 基础设施路由 (企业级生产必需)

# 新增 HITL 审批中心 页面路由

# Long-term Phase 3: I18n Router

# Phase 1: Infrastructure Enhancement Router

# P1-5: 集成生态路由

k8s_router: Optional[APIRouter] = None
try:
    from api.k8s_router import router as k8s_router  # type: ignore[misc]  # noqa: E402
except ImportError:
    k8s_router = None
    _logger.info("k8s_router not available (kubernetes module not installed)")

# Long-term Phase 3: Localization Adapter Router

# Long-term Phase 3: Localization Resource Router

# from api.repair_router import router as repair_router  # 已合并到 unified_repair_router

# from api.slack_router import router as slack_router  # Not implemented

# ------------------------
# 导入业务路由（原有）
# ------------------------

# Long-term Phase 4: Plugin Development Router

# Long-term Phase 4: Plugin Ecosystem Router

# Long-term Phase 4: Plugin Marketplace Router

# Long-term Phase 4: Plugin System Router

# Phase 4 集成: 优先级和 HITL 路由

# 新增 RAG 历史搜索页面路由

# 新增 RAG 路由

# 新增修复脚本资源路由（独立资源）

# P1-2: 根因智能分析路由

# Long-term Phase 1: Service Discovery Router

# Long-term Phase 1: Service Mesh Router

# Long-term Phase 1: Service Monitoring Router

# Phase 4: System Resource Router

# Short-term Phase 2: Test Automation Router

# Short-term Phase 2: Test Coverage Router

# Short-term Phase 2: Test Framework Router

# 新增全链路拓扑视图 页面路由

# Phase 1: Tracing Visualization Router

# 新增 Teams 路由
from api.docker_router import router as docker_router
from api.hardware_log_router import router as hardware_log_router

# windows_repair_router 与 unified_repair_router 共存，提供平台级独立入口
# 新增统一修复路由（替代各平台独立修复路由）

# Phase 1: New routers

# 新增工作流可视化 页面路由

# Phase 4: API Performance Optimizer

# Phase 4: Database Optimization Manager

# Short-term Phase 3: Documentation Generator

# Short-term Phase 3: Documentation Manager

# Long-term Phase 1: gRPC Service Manager

# Long-term Phase 3: I18n Manager

# Long-term Phase 3: Localization Adapter

# Long-term Phase 3: Localization Resource Manager

# Long-term Phase 4: Plugin Development SDK

# Long-term Phase 4: Plugin Ecosystem Manager

# Long-term Phase 4: Plugin Marketplace Manager

# Long-term Phase 4: Plugin System Manager

# Long-term Phase 1: Service Discovery Manager

# Long-term Phase 1: Service Mesh Manager

# Long-term Phase 1: Service Monitoring Manager

# SSO 登录路由

# Phase 4: System Resource Optimizer

# Short-term Phase 2: Test Automation Manager

# Short-term Phase 2: Test Coverage Manager

# Short-term Phase 2: Test Framework Manager

# ------------------------
# FastAPI 实例创建
# ------------------------
# 初始化速率限制器
# limiter = Limiter(key_func=get_remote_address)  # Temporarily disabled - .env encoding issue
limiter = None  # disabled until rate limiter is configured

# Global variables for enhanced cache and AI enhancer
_enhanced_cache: Any = None
_ai_enhancer: Any = None

# Import lifespan from lifecycle manager
from core.lifecycle_manager import lifespan

app = FastAPI(
    title="AIOps Agent",
    version="1.0.0",
    description="""
    AIOps Agent - 智能运维自动化平台

    ## 功能特性
    - **AI 根因分析**: 基于自然语言查询的智能故障诊断
    - **自动修复**: 支持多平台（Windows/Linux/Docker/K8s）的自动化修复
    - **指标监控**: 实时系统指标采集与趋势分析
    - **日志聚合**: 统一日志采集与搜索（支持 Windows/Linux）
    - **告警管理**: 智能告警检测与通知（支持企业微信/钉钉/飞书/Slack/Teams）
    - **RAG 语义搜索**: 基于向量数据库的历史知识检索
    - **审计追踪**: 完整的操作审计与报告生成

    ## 认证方式
    - JWT Bearer Token 认证
    - SSO/OIDC 单点登录支持

    ## 联系方式
    - 文档: /docs (Swagger UI)
    - 备用文档: /redoc (ReDoc)
    """,
    contact={
        "name": "AIOps Team",
        "email": "support@aiops.example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
)
app.state.limiter = limiter

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
async def root() -> FileResponse:
    return FileResponse("static/index.html")


app.add_exception_handler(
    RateLimitExceeded, _rate_limit_exception_handler  # type: ignore[arg-type]
)

# Apply API response middleware for unified format
setup_api_response_middleware(app)

# 🔧 P0 Security: Add input validation middleware
add_input_validation_middleware(app)

# 🔧 P0/P1: Access control and concurrency/session limit middlewares
add_access_control_middleware(app)
add_concurrency_middleware(app)

# 🔧 P1-3: Security Middleware Initialization
# Enable MFA and TLS enforcement
mfa_manager.enable_mfa()
tls_enforcer._enforce_tls = os.getenv("AIOPS_ENFORCE_TLS", "false").lower() == "true"


# Add security middleware
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # Skip CORS preflight requests (OPTIONS method)
    if request.method == "OPTIONS":
        response = await call_next(request)
        return response

    # TLS enforcement
    if not tls_enforcer.check_tls(request):
        return JSONResponse(status_code=400, content={"error": "HTTPS required"})

    # Rate limiting
    client_id = request.client.host if request.client else "unknown"
    allowed, retry_after = rate_limiter.check_rate_limit(client_id)
    if not allowed:
        return JSONResponse(
            status_code=429, content={"error": "Rate limit exceeded", "retry_after": retry_after}
        )

    response = await call_next(request)

    # Add security headers
    response = security_headers.add_security_headers(response)

    return response


# ------------------------
# 统一错误处理（防止信息泄露）
# ------------------------


# 注册统一错误处理器
app.add_exception_handler(HTTPException, api_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(
    RequestValidationError, validation_error_handler  # type: ignore[arg-type]
)
app.add_exception_handler(Exception, general_exception_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器，防止敏感信息泄露"""
    # 记录详细错误到日志
    _logger.error(
        f"Unhandled exception: {exc.__class__.__name__} | "
        f"Path: {request.url.path} | "
        f"Error: {str(exc)} | "
        f"Traceback: {traceback.format_exc()}"
    )
    # 返回通用错误消息给客户端
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Please contact administrator."},
    )


# ------------------------
# CORS 中间件（安全配置）
# ------------------------
# SECURITY: 从环境变量读取允许的域名，避免过于宽松的 CORS 配置
_default_origins = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", _default_origins).split(",")

# Warn if using default origins in production
if os.getenv("ENVIRONMENT", "development") == "production" and os.getenv("ALLOWED_ORIGINS") is None:
    _logger.warning(
        "SECURITY WARNING: Using default ALLOWED_ORIGINS in production environment. "
        "Please set ALLOWED_ORIGINS environment variable to restrict CORS to specific domains."
    )
# 注意：CORS中间件将在所有路由注册后添加，确保它最先执行

# ------------------------
# 路由注册（Core vs Add-ons）
# ------------------------
# Core routers are always mounted. Add-on routers are only mounted when
# ENABLE_ADDONS is true and the relevant pack flag is true.

CORE_ROUTERS = [
    alert_router,
    alert_advanced_router,
    alert_webhook_router,
    autoheal_router,
    audit_router,
    audit_center_router,
    compliance_audit_router,
    disaster_router,
    builder_router,
    chart_aggregation_router,
    monitoring_config_router,
    performance_optimization_router,
    performance_router,
    health_router,
    hitl_approval_router,
    linux_router,
    macos_router,
    docker_router,
    hardware_log_router,
    repair_advanced_router,
    repair_scripts_router,
    unified_repair_router,
    unified_repair_advanced_router,
    unified_repair_advanced_router_v1,
    windows_repair_router,
    guard_router,
    security_router,
    api_performance_router,
    cost_router,
    cost_advanced_router,
    auth_router,
    settings_router,
    users_router,
    users_advanced_router,
    assets_router,
    sso_router,
    slack_router,
    teams_router,
    vulnerability_router,
    websocket_router,
    sse_router,
    stats_router,
    capacity_router,
    anomaly_router,
    slo_router,
    chaos_simple_router,
    tenant_router,
    tenant_advanced_router,
    business_impact_router,
    business_impact_advanced_router,
    change_management_router,
    maturity_router,
    collaboration_router,
    collaboration_advanced_router,
    team_collaboration_router,
    topology_advanced_router_alt,
    topology_advanced_router_v1,
    tracing_advanced_router_alt,
    tracing_advanced_router_v1,
    unified_repair_advanced_router_alt,
    unified_repair_advanced_router_v1,
]

ADDON_ROUTERS = [
    # AI Plus Pack
    (ai_router, LLM_ROUTER_ENABLED),
    (ai_advanced_router, LLM_ROUTER_ENABLED),
    (advanced_ai_router, LLM_ROUTER_ENABLED),
    (ai_feedback_router, LLM_ROUTER_ENABLED),
    (root_cause_router, LLM_ROUTER_ENABLED),
    (root_cause_advanced_router, LLM_ROUTER_ENABLED),
    (rag_router, RAG_ENABLED),
    (rag_history_router, RAG_ENABLED),
    (qdrant_router, RAG_ENABLED),
    # Observability & Topology Pack
    (metrics_router, METRICS_ENABLED),
    (topology_router, TOPOLOGY_ENABLED),
    (topology_advanced_router, TOPOLOGY_ENABLED),
    (topology_advanced_router_v1, TOPOLOGY_ENABLED),
    (topology_view_router, TOPOLOGY_ENABLED),
    (service_mesh_router, TOPOLOGY_ENABLED),
    (service_mesh_advanced_router, TOPOLOGY_ENABLED),
    (service_discovery_router, TOPOLOGY_ENABLED),
    (service_discovery_advanced_router, TOPOLOGY_ENABLED),
    (service_monitoring_router, TOPOLOGY_ENABLED),
    (service_monitoring_advanced_router, TOPOLOGY_ENABLED),
    (realtime_router, TOPOLOGY_ENABLED),
    (realtime_advanced_router, TOPOLOGY_ENABLED),
    (tracing_router, TRACING_ENABLED),
    (tracing_advanced_router, TRACING_ENABLED),
    (tracing_advanced_router_v1, TRACING_ENABLED),
    (apm_router, TRACING_ENABLED),
    (log_router, LOG_AGGREGATION_ENABLED),
    # SRE Operations Pack
    (workflow_router, WORKFLOW_ENABLED),
    (workflow_advanced_router, WORKFLOW_ENABLED),
    (workflow_visualization_router, WORKFLOW_ENABLED),
    (hitl_router, INCIDENT_RESPONSE_ENABLED),
    (priority_router, INCIDENT_RESPONSE_ENABLED),
    (priority_advanced_router, INCIDENT_RESPONSE_ENABLED),
    (batch_router, INCIDENT_RESPONSE_ENABLED),
    (notify_router, INCIDENT_RESPONSE_ENABLED),
    (notify_advanced_router, INCIDENT_RESPONSE_ENABLED),
    # Multi-Cloud & Integrations Pack
    (integration_router, INTEGRATIONS_ENABLED),
    (itsm_router, INTEGRATIONS_ENABLED),
    (itsm_advanced_router, INTEGRATIONS_ENABLED),
    (dashboard_router, INTEGRATIONS_ENABLED),
    (dashboard_advanced_router, INTEGRATIONS_ENABLED),
    # Security & Compliance Pack
    (enterprise_router, SECURITY_SCANNING_ENABLED),
    (enterprise_router_append, SECURITY_SCANNING_ENABLED),
    (enterprise_advanced_router, SECURITY_SCANNING_ENABLED),
    (backup_router, SECURITY_SCANNING_ENABLED),
    # Infrastructure & Plugin Ecosystem Pack
    (chaos_router, PLUGINS_ENABLED),
    (chaos_advanced_router, PLUGINS_ENABLED),
    (cloud_router, PLUGINS_ENABLED),
    (mcp_router, MCP_ENABLED),
    (plugin_router, PLUGINS_ENABLED),
    (plugin_sdk_router, PLUGINS_ENABLED),
    (plugin_development_router, PLUGINS_ENABLED),
    (plugin_development_advanced_router, PLUGINS_ENABLED),
    (plugin_marketplace_router, PLUGINS_ENABLED),
    (plugin_marketplace_advanced_router, PLUGINS_ENABLED),
    # (plugin_ecosystem_router, PLUGINS_ENABLED),  # File doesn't exist
    (infrastructure_router, PLUGINS_ENABLED),
    (infrastructure_advanced_router, PLUGINS_ENABLED),
    (grpc_router, PLUGINS_ENABLED),
    (grpc_service_router, PLUGINS_ENABLED),
    (database_optimization_router, PLUGINS_ENABLED),
    (database_advanced_router, PLUGINS_ENABLED),
    (system_resource_router, PLUGINS_ENABLED),
    (test_framework_router, PLUGINS_ENABLED),
    (test_framework_advanced_router, PLUGINS_ENABLED),
    (test_coverage_router, PLUGINS_ENABLED),
    (test_coverage_advanced_router, PLUGINS_ENABLED),
    (test_automation_router, PLUGINS_ENABLED),
    (test_automation_advanced_router, PLUGINS_ENABLED),
    (maturity_advanced_router, PLUGINS_ENABLED),
    (dashboard_advanced_router, PLUGINS_ENABLED),
    # I18n & Localization
    (i18n_router, I18N_ENABLED),
    (i18n_router_append, I18N_ENABLED),
    (localization_resource_router, I18N_ENABLED),
    (localization_adapter_router, I18N_ENABLED),
    (localization_advanced_router, I18N_ENABLED),
    # Documentation & Tooling Pack
    (documentation_router, DOC_GENERATION_ENABLED),
    (documentation_advanced_router, DOC_GENERATION_ENABLED),
    (doc_generator_router, DOC_GENERATION_ENABLED),
    (frontend_enhancement_router, DOC_GENERATION_ENABLED),
    (frontend_advanced_router, DOC_GENERATION_ENABLED),
]

# Include the new GraphQL subscription router
if graphql_router:
    app.include_router(graphql_router)

for router in CORE_ROUTERS:
    app.include_router(router)

if k8s_router:
    app.include_router(k8s_router)

for router, flag in ADDON_ROUTERS:
    if router and ENABLE_ADDONS and flag:
        app.include_router(router)

# Phase 7: Apply global API documentation enhancements (description, codeSamples, error responses)
try:
    from api.router_enhancer import enhance_app_routes  # noqa: E402

    enhance_app_routes(app)
    _logger.info(
        "API route documentation enhanced with description, codeSamples and error responses"
    )
except Exception as e:
    _logger.info(f"API route documentation enhancement failed: {e}")


@app.get("/sw.js")
async def service_worker():
    from fastapi.responses import Response  # noqa: E402

    from core.service_worker_config import get_service_worker_script  # noqa: E402

    return Response(content=get_service_worker_script(), media_type="application/javascript")


@app.get("/sw-register.js")
async def service_worker_register():
    from fastapi.responses import Response  # noqa: E402

    from core.service_worker_config import get_service_worker_registration_script  # noqa: E402

    return Response(
        content=get_service_worker_registration_script(), media_type="application/javascript"
    )


# Phase 2: DR scenarios endpoint
@app.get("/api/v1/dr/scenarios")
async def list_dr_scenarios_endpoint():
    return await list_dr_scenarios()


@app.post("/api/v1/dr/run/{scenario_name}")
async def run_dr_scenario_endpoint(scenario_name: str):
    return await run_dr_scenario(scenario_name)


# ---- i18n 路由导入 & 注册 ----

# Setup unified exception handling
setup_exception_handlers(app)

# ------------------------
# CORS 中间件（安全配置）
# ------------------------
# 注意：CORS中间件必须在最后添加，确保它最先执行
# 这样可以避免其他中间件干扰CORS处理
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # 明确指定允许的域名
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Internal-Key"],
    max_age=600,  # 预检请求缓存时间
)

# Add request tracking middleware (在CORS之后添加，最后执行)
app.add_middleware(RequestTrackingMiddleware)

# Add tenant middleware (resolves tenant_id from JWT or header)
app.add_middleware(TenantMiddleware)

# Add global RBAC middleware (auth + write-method role checks)
app.add_middleware(RBACMiddleware)
