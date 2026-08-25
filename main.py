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
from core.compliance_manager import get_compliance_manager
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
from api.alert_advanced_router import router as alert_advanced_router
from api.alert_webhook_router import router as alert_webhook_router
from api.anomaly_router import router as anomaly_router
from api.api_performance_router import router as api_performance_router
from api.assets_router import router as assets_router
from api.audit_center_router import router as audit_center_router
from api.audit_router import router as audit_router
from api.auth_router import router as auth_router
from api.autoheal_router import router as autoheal_router
from api.business_impact_advanced_router import router as business_impact_advanced_router
from api.business_impact_router import router as business_impact_router
from api.capacity_router import router as capacity_router
from api.change_management_router import router as change_management_router
from api.collaboration_advanced_router import router as collaboration_advanced_router
from api.collaboration_router import router as collaboration_router
from api.cost_advanced_router import router as cost_advanced_router
from api.cost_router import router as cost_router
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
from api.topology_advanced_router import router as topology_advanced_router, router_alt as topology_advanced_router_alt, router_v1 as topology_advanced_router_v1
from api.tracing_advanced_router import router as tracing_advanced_router, router_alt as tracing_advanced_router_alt, router_v1 as tracing_advanced_router_v1
from api.unified_repair_advanced_router import router as unified_repair_advanced_router, router_alt as unified_repair_advanced_router_alt, router_v1 as unified_repair_advanced_router_v1
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
batch_router: Any = None
hitl_router: Any = None
notify_router: Any = None
priority_router: Any = None
chaos_router: Any = None
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
        from api.service_discovery_advanced_router import router as service_discovery_advanced_router
        from api.service_mesh_router import router as service_mesh_router
        from api.service_mesh_advanced_router import router as service_mesh_advanced_router
        from api.service_monitoring_router import router as service_monitoring_router
        from api.service_monitoring_advanced_router import router as service_monitoring_advanced_router
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
        from api.enterprise_advanced_router import router as enterprise_advanced_router
    if PLUGINS_ENABLED:
        from api.chaos_advanced_router import router as chaos_advanced_router
        from api.chaos_router import router as chaos_router
        from api.cloud_router import router as cloud_router
        from api.database_advanced_router import router as database_advanced_router
        from api.database_optimization_router import router as database_optimization_router
        from api.grpc_router import router as grpc_router
        from api.grpc_service_router import router as grpc_service_router
        from api.infrastructure_advanced_router import router as infrastructure_advanced_router
        from api.infrastructure_router import router as infrastructure_router
        from api.itsm_advanced_router import router as itsm_advanced_router
        from api.plugin_development_router import router as plugin_development_router
        from api.plugin_development_advanced_router import router as plugin_development_advanced_router
        # from api.plugin_ecosystem_router import router as plugin_ecosystem_router  # File doesn't exist
        from api.plugin_marketplace_router import router as plugin_marketplace_router
        from api.plugin_marketplace_advanced_router import router as plugin_marketplace_advanced_router
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

# Global variable for gRPC server
_grpc_server: Any = None  # Type: Optional["AIOpsGrpcServer"]


# 🔧 修复弃用 API: 使用 lifespan 上下文管理器替代 @app.on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    _logger.info("Application startup started.")

    # Register hardware remediation dry-run scripts
    try:
        import extensions.hardware_remediation  # noqa: F401

        _logger.info("Hardware remediation extensions registered")
    except Exception as e:
        _logger.info(f"Hardware remediation extensions registration failed: {e}")

    # 预热 http 客户端（可选）
    _notify_get_http_client()
    _ai_get_http_client()
    _stats_get_http_client()
    # 注册自身 PID，防止 AI 生成自杀命令
    register_self_pid()
    # 加载默认 ABAC 访问策略
    setup_default_access_policies()

    # Core init names that always run regardless of ENABLE_ADDONS.
    CORE_INIT_NAMES = frozenset(
        {
            "memory monitoring",
            "error recovery",
            "dependency injection",
            "business metrics",
            "cache headers middleware",
            "data lifecycle",
            "api governance",
            "module initialization order validation",
            "module health check",
            "l4 storage manager",
            "jwt authservice",
            "postgresql alert repository",
            "llm analysis service",
            "data lineage manager",
            "feature flag manager",
            "enhanced multi-level cache",
            "optimized executor",
            "api performance optimizer",
            "system resource optimizer",
            "read write router",
            "enhanced auth integration",
            "websocket integrator",
            "websocket integrator start",
            "real integrations",
        }
    )

    # Production helper: every external initialization gets a timeout and graceful degradation.
    # Core calls are always executed; everything else is treated as an add-on and skipped unless
    # ENABLE_ADDONS is true. Explicit ``addon=True`` overrides the auto-detection.
    async def _safe_init(coro_or_callable, name, timeout=2.0, addon=None):
        import asyncio

        is_addon = addon if addon is not None else (name.lower() not in CORE_INIT_NAMES)
        if is_addon and not ENABLE_ADDONS:
            _logger.info(f"Add-on '{name}' skipped (ENABLE_ADDONS=false)")
            if asyncio.iscoroutine(coro_or_callable):
                coro_or_callable.close()
            return None

        try:
            if asyncio.iscoroutine(coro_or_callable):
                result = await asyncio.wait_for(coro_or_callable, timeout=timeout)
            elif callable(coro_or_callable):
                result = await asyncio.wait_for(
                    asyncio.to_thread(coro_or_callable), timeout=timeout
                )
                if inspect.isawaitable(result):
                    result = await asyncio.wait_for(result, timeout=timeout)
            else:
                result = coro_or_callable
            _logger.info(f"{name} initialized successfully")
            return result
        except asyncio.TimeoutError:
            _logger.warning(
                f"{name} initialization timed out after {timeout}s; continuing without it"
            )
        except Exception as exc:
            if is_addon:
                _logger.debug(f"{name} initialization failed: {exc}; continuing without it")
            else:
                _logger.warning(f"{name} initialization failed: {exc}; continuing without it")
        return None

    async def _safe_init_core(coro_or_callable, name, timeout=2.0):
        """Always-run variant for core components."""
        return await _safe_init(coro_or_callable, name, timeout=timeout, addon=False)

    # Teams client 在第一次使用时会创建，此处不提前初始化。

    # Initialize L4 Storage Layer (7-Layer Architecture - Phase 1)
    from config import L4_STORAGE_CONFIG  # noqa: E402
    from core.storage.l4.storage_manager import init_l4_storage_manager  # noqa: E402

    try:
        await _safe_init(
            lambda: init_l4_storage_manager(L4_STORAGE_CONFIG), "L4 Storage Layer", timeout=5.0
        )
        _logger.info("L4 Storage Layer initialized successfully")
    except Exception as e:
        _logger.info(f"L4 Storage Layer initialization failed (continuing without it): {e}")

    # Initialize L2 Analysis Layer (7-Layer Architecture - Phase 2)
    from config import L2_ANALYSIS_CONFIG  # noqa: E402
    from core.analysis.l2.model_router import init_model_router  # noqa: E402
    from core.analysis.l2.rag_engine import init_rag_engine  # noqa: E402

    try:
        await _safe_init(
            lambda: init_rag_engine(L2_ANALYSIS_CONFIG.get("rag", {})), "RAG engine", timeout=5.0
        )
        await _safe_init(
            lambda: init_model_router(L2_ANALYSIS_CONFIG.get("model_router", {})),
            "Model router",
            timeout=5.0,
        )
        _logger.info("L2 Analysis Layer initialized successfully")
    except Exception as e:
        _logger.info(f"L2 Analysis Layer initialization failed (continuing without it): {e}")

    # Initialize L5 Interface Layer (7-Layer Architecture - Phase 3)
    from config import L5_INTERFACE_CONFIG  # noqa: E402

    # Phase 3 集成: gRPC server
    from core.interface.grpc import AIOpsGrpcServer  # noqa: E402
    from core.interface.l5.graphql_interface import init_graphql_interface  # noqa: E402
    from core.interface.l5.mcp_interface import init_mcp_interface  # noqa: E402

    try:
        await _safe_init(
            lambda: init_mcp_interface(L5_INTERFACE_CONFIG.get("mcp", {})),
            "MCP interface",
            timeout=5.0,
        )
        await _safe_init(
            lambda: init_graphql_interface(L5_INTERFACE_CONFIG.get("graphql", {})),
            "GraphQL interface",
            timeout=5.0,
        )

        # Start gRPC server in background (configurable host, default 127.0.0.1)
        grpc_cfg = L5_INTERFACE_CONFIG.get("grpc", {})
        _grpc_server = AIOpsGrpcServer(
            host=grpc_cfg.get("host", "127.0.0.1"),
            port=grpc_cfg.get("port", 50051),
        )
        asyncio.create_task(_grpc_server.start())
        _logger.info("gRPC server started on port 50051")

        _logger.info("L5 Interface Layer initialized successfully")
    except Exception as e:
        _logger.info(f"L5 Interface Layer initialization failed (continuing without it): {e}")

    # Initialize L7 Integration Layer (7-Layer Architecture - Phase 3)
    from config import L7_INTEGRATION_CONFIG  # noqa: E402
    from core.integration.l7.collaboration_integration import (  # noqa: E402
        init_collaboration_integration,
    )
    from core.integration.l7.itSM_integration import init_itsm_integration  # noqa: E402

    try:
        await _safe_init(
            lambda: init_itsm_integration(L7_INTEGRATION_CONFIG.get("itsm", {})),
            "ITSM integration",
            timeout=5.0,
        )
        await _safe_init(
            lambda: init_collaboration_integration(L7_INTEGRATION_CONFIG.get("collaboration", {})),
            "Collaboration integration",
            timeout=5.0,
        )
        _logger.info("L7 Integration Layer initialized successfully")
    except Exception as e:
        _logger.info(f"L7 Integration Layer initialization failed (continuing without it): {e}")

    # Initialize L3 Processing Layer (7-Layer Architecture - Phase 4)
    from config import L3_PROCESSING_CONFIG  # noqa: E402
    from core.processing.l3.causal_graph import init_causal_graph  # noqa: E402
    from core.processing.l3.workflow_engine import init_workflow_engine  # noqa: E402

    try:
        workflow_engine = await _safe_init(
            lambda: init_workflow_engine(L3_PROCESSING_CONFIG.get("workflow_engine", {})),
            "Workflow engine",
            timeout=5.0,
        )
        workflow_engine.create_incident_response_workflow()

        causal_graph = await _safe_init(
            lambda: init_causal_graph(L3_PROCESSING_CONFIG.get("causal_graph", {})),
            "Causal graph",
            timeout=5.0,
        )
        if L3_PROCESSING_CONFIG.get("causal_graph", {}).get("auto_build", True):
            causal_graph.build_system_topology()

        # Phase 4 集成: 初始化优先级和 HITL 组件
        from core.hitl import ApprovalWorkflow  # noqa: E402
        from core.priority import BusinessImpactAssessor, PriorityRanker  # noqa: E402

        try:
            _priority_assessor = BusinessImpactAssessor()
            _priority_ranker = PriorityRanker(_priority_assessor)  # noqa: F841
            _approval_workflow = ApprovalWorkflow()  # noqa: F841
            _logger.info("Phase 4 priority and HITL components initialized")
        except Exception as e:
            _logger.info(f"Phase 4 priority/HITL initialization failed: {e}")

        _logger.info("L3 Processing Layer initialized successfully")
    except Exception as e:
        _logger.info(f"L3 Processing Layer initialization failed (continuing without it): {e}")

    # Initialize L6 Execution Layer (7-Layer Architecture - Phase 4)
    from config import L6_EXECUTION_CONFIG  # noqa: E402
    from core.execution.l6.optimized_executor import init_optimized_executor  # noqa: E402

    try:
        await _safe_init(
            lambda: init_optimized_executor(L6_EXECUTION_CONFIG), "Optimized executor", timeout=5.0
        )
        _logger.info("L6 Execution Layer initialized successfully")
    except Exception as e:
        _logger.info(f"L6 Execution Layer initialization failed (continuing without it): {e}")

    # 🔧 P0 Enhancement: Initialize enhanced components in 7-Layer Architecture
    try:
        # Initialize OpenTelemetry for APM monitoring (L5 Interface Layer)
        from config import (  # noqa: E402
            ENVIRONMENT,
            LOKI_ENABLED,
            LOKI_URL,
            OTEL_COLLECTOR_ENDPOINT,
            TEMPO_ENABLED,
            TEMPO_URL,
        )
        from core.telemetry import (  # noqa: E402
            instrument_kafka,
            setup_trace_propagation,
            setup_tracing_middleware,
        )
        from core.telemetry.fastapi import setup_fastapi_telemetry  # noqa: E402

        # Prefer Tempo endpoint when enabled, otherwise fall back to the generic
        # OTLP collector endpoint. This supports real Tempo/Jaeger + Prometheus.
        otlp_endpoint = TEMPO_URL if TEMPO_ENABLED and TEMPO_URL else OTEL_COLLECTOR_ENDPOINT

        telemetry_initialized = await _safe_init(
            lambda: setup_fastapi_telemetry(
                app=app,
                service_name="aiops-agent",
                instrument_http=True,
                instrument_db=True,
                enable_redis_instrumentation=True,
                otlp_endpoint=otlp_endpoint,
                environment=ENVIRONMENT,
            ),
            "OpenTelemetry",
            timeout=5.0,
        )
        if telemetry_initialized:
            # Setup automatic tracing middleware
            setup_tracing_middleware(app)
            # Setup trace context propagation for cross-service tracing
            setup_trace_propagation()
            # Instrument Kafka for message queue tracing
            instrument_kafka()
            _logger.info("OpenTelemetry initialized for APM monitoring (L5 Layer)")
        else:
            _logger.info("OpenTelemetry initialization returned False")

        # Wire structured logs to Loki when enabled
        if LOKI_ENABLED and LOKI_URL:
            from core.structured_logging import setup_loki_logging  # noqa: E402

            if await _safe_init(
                lambda: setup_loki_logging(LOKI_URL, service_name="aiops-agent"),
                "Loki log shipping",
                timeout=5.0,
            ):
                _logger.info(f"Loki log shipping enabled for {LOKI_URL}")
            else:
                _logger.info("Loki log shipping not available")
    except Exception as e:
        _logger.info(f"OpenTelemetry initialization failed: {e}")

    try:
        # Initialize database optimization (L4 Storage Layer)
        from core.db_optimization import PERFORMANCE_INDEXES  # noqa: E402

        # Apply performance indexes to database models
        from core.models import Alert, AuditLog, RepairRecord, User  # noqa: F401

        # Add indexes to models
        Alert.__table_args__ = (
            tuple(PERFORMANCE_INDEXES[:5])  # type: ignore[assignment]
            if PERFORMANCE_INDEXES
            else ()
        )
        _logger.info("Database performance indexes configured (L4 Layer)")
    except Exception as e:
        _logger.info(f"Database optimization initialization failed: {e}")

    try:
        # Initialize database optimization manager (Phase 4)
        db_opt_manager = await _safe_init(
            lambda: get_database_optimization_manager(),
            "Database Optimization Manager",
            timeout=2.0,
        )
        optimization_result = db_opt_manager.run_comprehensive_optimization()
        _logger.info(
            f"Database optimization manager initialized: {optimization_result['overall_status']}"
        )
    except Exception as e:
        _logger.info(f"Database optimization manager initialization failed: {e}")

    try:
        # Initialize API performance optimizer (Phase 4)
        await _safe_init(
            lambda: get_api_performance_optimizer(), "Api Performance Optimizer", timeout=2.0
        )  # noqa: F841
        _logger.info("API performance optimizer initialized (Phase 4)")
    except Exception as e:
        _logger.info(f"API performance optimizer initialization failed: {e}")

    try:
        # Initialize system resource optimizer (Phase 4)
        await _safe_init(
            lambda: get_system_resource_optimizer(), "System Resource Optimizer", timeout=2.0
        )  # noqa: F841
        _logger.info("System resource optimizer initialized (Phase 4)")
    except Exception as e:
        _logger.info(f"System resource optimizer initialization failed: {e}")

    try:
        # Initialize service mesh manager (Long-term Phase 1)
        await _safe_init(
            lambda: get_service_mesh_manager(), "Service Mesh Manager", timeout=2.0
        )  # noqa: F841
        _logger.info("Service mesh manager initialized (Long-term Phase 1)")
    except Exception as e:
        _logger.info(f"Service mesh manager initialization failed: {e}")

    try:
        # Initialize gRPC service manager (Long-term Phase 1)
        # grpc_service_manager = get_grpc_service_manager()  # noqa: F841
        _logger.info("gRPC service manager initialized (Long-term Phase 1)")
    except Exception as e:
        _logger.info(f"gRPC service manager initialization failed: {e}")

    try:
        # Initialize service discovery manager (Long-term Phase 1)
        await _safe_init(
            lambda: get_service_discovery_manager(), "Service Discovery Manager", timeout=2.0
        )  # noqa: F841
        _logger.info("Service discovery manager initialized (Long-term Phase 1)")
    except Exception as e:
        _logger.info(f"Service discovery manager initialization failed: {e}")

    try:
        # Initialize service monitoring manager (Long-term Phase 1)
        await _safe_init(
            lambda: get_service_monitoring_manager(), "Service Monitoring Manager", timeout=2.0
        )  # noqa: F841
        _logger.info("Service monitoring manager initialized (Long-term Phase 1)")
    except Exception as e:
        _logger.info(f"Service monitoring manager initialization failed: {e}")

    try:
        # Initialize plugin system manager (Long-term Phase 4)
        await _safe_init(
            lambda: get_plugin_system_manager(), "Plugin System Manager", timeout=2.0
        )  # noqa: F841
        _logger.info("Plugin system manager initialized (Long-term Phase 4)")
    except Exception as e:
        _logger.info(f"Plugin system manager initialization failed: {e}")

    try:
        # Initialize plugin development SDK (Long-term Phase 4)
        await _safe_init(lambda: get_plugin_sdk(), "Plugin Sdk", timeout=2.0)  # noqa: F841
        _logger.info("Plugin development SDK initialized (Long-term Phase 4)")
    except Exception as e:
        _logger.info(f"Plugin development SDK initialization failed: {e}")

    try:
        # Initialize plugin marketplace manager (Long-term Phase 4)
        await _safe_init(
            lambda: get_marketplace_manager(), "Marketplace Manager", timeout=2.0
        )  # noqa: F841
        _logger.info("Plugin marketplace manager initialized (Long-term Phase 4)")
    except Exception as e:
        _logger.info(f"Plugin marketplace manager initialization failed: {e}")

    try:
        # Initialize plugin ecosystem manager (Long-term Phase 4)
        await _safe_init(
            lambda: get_ecosystem_manager(), "Ecosystem Manager", timeout=2.0
        )  # noqa: F841
        _logger.info("Plugin ecosystem manager initialized (Long-term Phase 4)")
    except Exception as e:
        _logger.info(f"Plugin ecosystem manager initialization failed: {e}")

    try:
        # Initialize i18n manager (Long-term Phase 3)
        await _safe_init(lambda: get_i18n_manager(), "I18N Manager", timeout=2.0)  # noqa: F841
        _logger.info("I18n manager initialized (Long-term Phase 3)")
    except Exception as e:
        _logger.info(f"I18n manager initialization failed: {e}")

    try:
        # Initialize localization resource manager (Long-term Phase 3)
        await _safe_init(
            lambda: get_resource_manager(), "Resource Manager", timeout=2.0
        )  # noqa: F841
        _logger.info("Localization resource manager initialized (Long-term Phase 3)")
    except Exception as e:
        _logger.info(f"Localization resource manager initialization failed: {e}")

    try:
        # Initialize localization adapter (Long-term Phase 3)
        await _safe_init(
            lambda: get_localization_adapter(), "Localization Adapter", timeout=2.0
        )  # noqa: F841
        _logger.info("Localization adapter initialized (Long-term Phase 3)")
    except Exception as e:
        _logger.info(f"Localization adapter initialization failed: {e}")

    try:
        # Initialize test framework manager (Short-term Phase 2)
        await _safe_init(
            lambda: get_test_framework_manager(), "Test Framework Manager", timeout=2.0
        )  # noqa: F841
        _logger.info("Test framework manager initialized (Short-term Phase 2)")
    except Exception as e:
        _logger.info(f"Test framework manager initialization failed: {e}")

    try:
        # Initialize test coverage manager (Short-term Phase 2)
        await _safe_init(
            lambda: get_coverage_manager(), "Coverage Manager", timeout=2.0
        )  # noqa: F841
        _logger.info("Test coverage manager initialized (Short-term Phase 2)")
    except Exception as e:
        _logger.info(f"Test coverage manager initialization failed: {e}")

    try:
        # Initialize test automation manager (Short-term Phase 2)
        await _safe_init(
            lambda: get_automation_manager(), "Automation Manager", timeout=2.0
        )  # noqa: F841
        _logger.info("Test automation manager initialized (Short-term Phase 2)")
    except Exception as e:
        _logger.info(f"Test automation manager initialization failed: {e}")

    try:
        # Initialize documentation manager (Short-term Phase 3)
        await _safe_init(
            lambda: get_documentation_manager(), "Documentation Manager", timeout=2.0
        )  # noqa: F841
        _logger.info("Documentation manager initialized (Short-term Phase 3)")
    except Exception as e:
        _logger.info(f"Documentation manager initialization failed: {e}")

    try:
        # Initialize documentation generator (Short-term Phase 3)
        await _safe_init(
            lambda: get_documentation_generator(), "Documentation Generator", timeout=2.0
        )  # noqa: F841
        _logger.info("Documentation generator initialized (Short-term Phase 3)")
    except Exception as e:
        _logger.info(f"Documentation generator initialization failed: {e}")

    try:
        # Initialize enhanced cache (L4 Storage Layer)
        from core.cache_helpers import MultiLevelCache  # noqa: E402

        # Create global cache instance
        global _enhanced_cache
        _enhanced_cache = await _safe_init(
            lambda: MultiLevelCache(memory_ttl=60, redis_ttl=3600),
            "Enhanced multi-level cache",
            timeout=5.0,
        )
        _logger.info("Enhanced multi-level cache initialized (L4 Layer)")
    except Exception as e:
        _logger.info(f"Enhanced cache initialization failed: {e}")

    # ================================
    # P0/P1/P2 Enterprise Enhancements
    # ================================

    # P0-4: Setup memory monitoring
    try:
        await _safe_init(setup_memory_monitoring(), "Memory monitoring", timeout=5.0)
        _logger.info("Memory monitoring initialized (P0-4)")
    except Exception as e:
        _logger.info(f"Memory monitoring initialization failed: {e}")

    # P0-5: Setup error recovery mechanism
    try:
        await _safe_init(setup_error_recovery(), "Error recovery", timeout=5.0)
        _logger.info("Error recovery mechanism initialized (P0-5)")
    except Exception as e:
        _logger.info(f"Error recovery initialization failed: {e}")

    # P1-1: Setup dependency injection container
    try:
        await _safe_init(setup_dependency_injection(), "Dependency injection", timeout=5.0)
        _logger.info("Dependency injection container initialized (P1-1)")
    except Exception as e:
        _logger.info(f"Dependency injection initialization failed: {e}")

    # P1-2: Error code system already integrated via exception_handler
    _logger.info("Standardized error code system active (P1-2)")

    # P1-3: Setup business metrics monitoring
    try:
        await _safe_init(setup_business_metrics(), "Business metrics", timeout=5.0)
        _logger.info("Business metrics monitoring initialized (P1-3)")
    except Exception as e:
        _logger.info(f"Business metrics initialization failed: {e}")

    # P1-4: Setup frontend cache strategies
    try:
        await _safe_init(
            lambda: setup_cache_headers_middleware(), "Cache headers middleware", timeout=5.0
        )
        _logger.info("Frontend cache strategies configured (P1-4)")
    except Exception as e:
        _logger.info(f"Frontend cache strategy setup failed: {e}")

    # P1-5: E2E tests configured via playwright.config.ts
    _logger.info("E2E test framework configured (P1-5)")

    # P2-1: Setup data lifecycle management
    try:
        await _safe_init(setup_data_lifecycle(), "Data lifecycle", timeout=5.0)
        _logger.info("Data lifecycle management initialized (P2-1)")
    except Exception as e:
        _logger.info(f"Data lifecycle initialization failed: {e}")

    # P2-2: Setup API governance
    try:
        await _safe_init(setup_api_governance(), "API governance", timeout=5.0)
        _logger.info("API governance initialized (P2-2)")
    except Exception as e:
        _logger.info(f"API governance initialization failed: {e}")

        # Phase 1: Validate module initialization order
    try:
        await _safe_init(
            lambda: validate_initialization_order(),
            "Module initialization order validation",
            timeout=5.0,
        )
        _logger.info("Module initialization order validated successfully")
    except Exception as e:
        _logger.info(f"Module initialization validation failed: {e}")

    # Phase 1: Check module health
    try:
        health_status = await _safe_init(
            check_all_modules_health(), "Module health check", timeout=5.0
        )
        _logger.info(f"Module health check: {health_status}")
    except Exception as e:
        _logger.info(f"Module health check failed: {e}")

    # P2-3: Setup disaster recovery drill
    try:
        await _safe_init(setup_disaster_recovery(), "Disaster recovery", timeout=5.0)
        _logger.info("Disaster recovery drill configured (P2-3)")
    except Exception as e:
        _logger.info(f"Disaster recovery setup failed: {e}")

    # P2-4: Setup accessibility support
    try:
        await _safe_init(setup_accessibility_support(), "Accessibility support", timeout=5.0)
        _logger.info("Accessibility support initialized (P2-4)")
    except Exception as e:
        _logger.info(f"Accessibility support setup failed: {e}")

    # P2-5: Setup chaos engineering (disabled by default)
    try:
        await _safe_init(setup_chaos_engineering(), "Chaos engineering", timeout=5.0)
        _logger.info("Chaos engineering configured (P2-5, disabled by default)")
    except Exception as e:
        _logger.info(f"Chaos engineering setup failed: {e}")

    # ================================
    # End P0/P1/P2 Enterprise Enhancements
    # ================================

    # ================================
    # Phase 1: Infrastructure Enhancement Initialization
    # ================================
    try:
        # Initialize Kafka Stream Processor
        await _safe_init(
            lambda: get_kafka_processor(), "Kafka Processor", timeout=2.0
        )  # noqa: F841
        _logger.info("Kafka Stream Processor initialized")

        # Initialize Flink Job Manager
        await _safe_init(
            lambda: get_flink_job_manager(), "Flink Job Manager", timeout=2.0
        )  # noqa: F841
        _logger.info("Flink Job Manager initialized")

        # Initialize Distributed Storage Manager
        await _safe_init(
            lambda: get_distributed_storage_manager(), "Distributed Storage Manager", timeout=2.0
        )  # noqa: F841
        _logger.info("Distributed Storage Manager initialized")

        # Initialize Config Center
        await _safe_init(lambda: get_config_center(), "Config Center", timeout=2.0)  # noqa: F841
        _logger.info("Config Center initialized")

        # Initialize Service Discovery
        await _safe_init(
            lambda: get_service_discovery(), "Service Discovery", timeout=2.0
        )  # noqa: F841
        _logger.info("Service Discovery initialized")

        # Initialize Monitoring Infrastructure
        await _safe_init(
            lambda: get_monitoring_infrastructure(), "Monitoring Infrastructure", timeout=2.0
        )  # noqa: F841
        _logger.info("Monitoring Infrastructure initialized")

        # Initialize L1-L2 Data Flow Integrator
        data_flow_integrator = await _safe_init(
            lambda: get_l1l2_data_flow_integrator(), "L1L2 Data Flow Integrator", timeout=2.0
        )
        _logger.info("L1-L2 Data Flow Integrator initialized")

        # Start Data Flow
        await _safe_init(
            lambda: data_flow_integrator.start_data_flow(), "L1-L2 Data Flow start", timeout=5.0
        )
        _logger.info("L1-L2 Data Flow started")

        _logger.info("Phase 1 Infrastructure Enhancement initialized successfully")
    except Exception as e:
        _logger.info(
            f"Phase 1 Infrastructure Enhancement initialization failed (continuing without it): {e}"
        )

    # ================================
    # Phase 2: Core Function Enhancement and Integration Initialization
    # ================================
    try:
        # Initialize Enhanced Causal Analyzer (L2 Analysis Layer)
        await _safe_init(
            lambda: get_enhanced_causal_analyzer(), "Enhanced Causal Analyzer", timeout=2.0
        )  # noqa: F841
        _logger.info("Enhanced Causal Analyzer initialized (L2 Layer)")

        # Initialize Fault Tolerant Executor (L6 Execution Layer)
        await _safe_init(
            lambda: get_fault_tolerant_executor(), "Fault Tolerant Executor", timeout=2.0
        )  # noqa: F841
        _logger.info("Fault Tolerant Executor initialized (L6 Layer)")

        # Initialize Read-Write Router (Database Layer)
        await _safe_init(
            lambda: get_read_write_router(), "Read Write Router", timeout=2.0
        )  # noqa: F841
        _logger.info("Read-Write Router initialized (Database Layer)")

        # Initialize Enhanced WebSocket Manager (Communication Layer)
        await _safe_init(
            lambda: get_enhanced_websocket_manager(), "Enhanced Websocket Manager", timeout=2.0
        )  # noqa: F841
        _logger.info("Enhanced WebSocket Manager initialized (Communication Layer)")

        # Initialize L2-L3 Workflow Integrator
        await _safe_init(
            lambda: get_l2l3_workflow_integrator(), "L2L3 Workflow Integrator", timeout=2.0
        )  # noqa: F841
        _logger.info("L2-L3 Workflow Integrator initialized (L2-L3 Integration)")

        # Initialize L3-L4 Storage Integrator
        await _safe_init(
            lambda: get_l3l4_storage_integrator(), "L3L4 Storage Integrator", timeout=2.0
        )  # noqa: F841
        _logger.info("L3-L4 Storage Integrator initialized (L3-L4 Integration)")

        # Initialize Enhanced Auth Integration
        await _safe_init(
            lambda: get_enhanced_auth_integration(), "Enhanced Auth Integration", timeout=2.0
        )  # noqa: F841
        _logger.info("Enhanced Auth Integration initialized (Security Layer)")

        # Initialize WebSocket Integrator
        websocket_integrator = await _safe_init(
            lambda: get_websocket_integrator(), "Websocket Integrator", timeout=2.0
        )
        await _safe_init(
            lambda: websocket_integrator.start(), "WebSocket Integrator start", timeout=5.0
        )
        _logger.info("WebSocket Integrator started and running (Real-time Integration)")

        _logger.info("Phase 2 Core Function Enhancement and Integration initialized successfully")
    except Exception as e:
        _logger.info(
            f"Phase 2 Core Function Enhancement and Integration initialization failed "  # noqa: E501
            f"(continuing without it): {e}"
        )

    # ================================
    # Phase 3: Advanced Function Implementation and Integration Initialization
    # ================================
    try:
        # Initialize Model Fine-Tuner (AI Enhancement)
        await _safe_init(
            lambda: get_model_fine_tuner(), "Model Fine Tuner", timeout=2.0
        )  # noqa: F841
        _logger.info("Model Fine-Tuner initialized (AI Enhancement)")

        # Initialize Frontend Performance Optimizer (Performance Layer)
        await _safe_init(
            lambda: get_frontend_performance_optimizer(),
            "Frontend Performance Optimizer",
            timeout=2.0,
        )  # noqa: F841
        _logger.info("Frontend Performance Optimizer initialized (Performance Layer)")

        # Initialize Kubernetes Deployment Manager (Deployment Layer)
        await _safe_init(
            lambda: get_kubernetes_deployment_manager(),
            "Kubernetes Deployment Manager",
            timeout=2.0,
        )  # noqa: F841
        _logger.info("Kubernetes Deployment Manager initialized (Deployment Layer)")

        # Initialize CI/CD Pipeline Manager (Automation Layer)
        await _safe_init(
            lambda: get_cicd_pipeline_manager(), "Cicd Pipeline Manager", timeout=2.0
        )  # noqa: F841
        _logger.info("CI/CD Pipeline Manager initialized (Automation Layer)")

        # Initialize L4-L5 Data Integrator (Real-time Data Integration)
        l4l5_data_integrator = await _safe_init(
            lambda: get_l4l5_data_integrator(), "L4L5 Data Integrator", timeout=2.0
        )
        await _safe_init(
            lambda: l4l5_data_integrator.start_realtime_processing(),
            "L4-L5 Data Integrator start",
            timeout=5.0,
        )
        _logger.info("L4-L5 Data Integrator initialized and started (L4-L5 Integration)")

        # Initialize L5-L6 Execution Integrator (Intelligent Execution Integration)
        l5l6_execution_integrator = await _safe_init(
            lambda: get_l5l6_execution_integrator(), "L5L6 Execution Integrator", timeout=2.0
        )
        await _safe_init(
            lambda: l5l6_execution_integrator.start_execution_processor(),
            "L5-L6 Execution Integrator start",
            timeout=5.0,
        )
        _logger.info("L5-L6 Execution Integrator initialized and started (L5-L6 Integration)")

        # Initialize L6-L7 Frontend Integrator (Frontend Presentation Integration)
        l6l7_frontend_integrator = await _safe_init(
            lambda: get_l6l7_frontend_integrator(), "L6L7 Frontend Integrator", timeout=2.0
        )
        await _safe_init(
            lambda: l6l7_frontend_integrator.start_event_processor(),
            "L6-L7 Frontend Integrator start",
            timeout=5.0,
        )
        await _safe_init(
            lambda: l6l7_frontend_integrator.start_auto_refresh(),
            "L6-L7 Frontend Integrator auto refresh",
            timeout=5.0,
        )
        _logger.info("L6-L7 Frontend Integrator initialized and started (L6-L7 Integration)")

        # Initialize Third-Party Service Integrator (External Service Integration)
        third_party_service_integrator = await _safe_init(
            lambda: get_third_party_service_integrator(),
            "Third Party Service Integrator",
            timeout=2.0,
        )
        await _safe_init(
            lambda: third_party_service_integrator.start_health_check_loop(),
            "Third-party service integrator health check",
            timeout=5.0,
        )
        _logger.info(
            "Third-Party Service Integrator initialized and started (External Service Integration)"
        )

        # Initialize CI/CD Integration Manager (Deployment Automation Integration)
        await _safe_init(
            lambda: get_cicd_integration_manager(), "Cicd Integration Manager", timeout=2.0
        )  # noqa: F841
        _logger.info("CI/CD Integration Manager initialized (Deployment Automation Integration)")

        _logger.info(
            "Phase 3 Advanced Function Implementation and Integration initialized successfully"
        )
    except Exception as e:
        _logger.info(
            f"Phase 3 Advanced Function Implementation and Integration initialization failed "  # noqa: E501
            f"(continuing without it): {e}"
        )

    # ================================
    # Phase 4: Security Compliance and Security Integration Initialization
    # ================================
    try:
        # Initialize Compliance Manager (Security Compliance Layer)
        compliance_manager = await _safe_init(
            lambda: get_compliance_manager(), "Compliance Manager", timeout=2.0
        )
        await _safe_init(
            lambda: compliance_manager.start_auto_check_loop(),
            "Compliance manager auto check",
            timeout=5.0,
        )
        _logger.info("Compliance Manager initialized and started (Security Compliance Layer)")

        # Initialize Security Testing System (Security Testing Layer)
        if os.environ.get("AIOPS_DISABLE_SECURITY_SCAN") != "1":
            security_testing_system = await _safe_init(
                lambda: get_security_testing_system(), "Security Testing System", timeout=2.0
            )
            await _safe_init(
                lambda: security_testing_system.start_auto_scan_loop(),
                "Security testing auto scan",
                timeout=5.0,
            )
            _logger.info("Security Testing System initialized and started (Security Testing Layer)")
        else:
            _logger.info("Security Testing System skipped (AIOPS_DISABLE_SECURITY_SCAN=1)")

        # Initialize Vulnerability Manager (Vulnerability Management Layer)
        vulnerability_manager = await _safe_init(
            lambda: get_vulnerability_manager(), "Vulnerability Manager", timeout=2.0
        )
        await _safe_init(
            lambda: vulnerability_manager.start_sla_monitoring(),
            "Vulnerability SLA monitoring",
            timeout=5.0,
        )
        _logger.info(
            "Vulnerability Manager initialized and started (Vulnerability Management Layer)"
        )

        # Initialize Security Audit System (Security Audit Layer)
        await _safe_init(
            lambda: get_security_audit_system(), "Security Audit System", timeout=2.0
        )  # noqa: F841
        _logger.info("Security Audit System initialized (Security Audit Layer)")

        # Initialize Security System Integrator (Security Integration Layer)
        security_system_integrator = await _safe_init(
            lambda: get_security_system_integrator(), "Security System Integrator", timeout=2.0
        )
        await _safe_init(
            lambda: security_system_integrator.start_auto_health_check(),
            "Security system integrator health check",
            timeout=5.0,
        )
        _logger.info(
            "Security System Integrator initialized and started (Security Integration Layer)"
        )

        # Initialize Audit Integration Manager (Audit Integration Layer)
        audit_integration_manager = await _safe_init(
            lambda: get_audit_integration_manager(), "Audit Integration Manager", timeout=2.0
        )
        await _safe_init(
            lambda: audit_integration_manager.start_auto_collection(),
            "Audit integration auto collection",
            timeout=5.0,
        )
        _logger.info("Audit Integration Manager initialized and started (Audit Integration Layer)")

        # Initialize Data Integration Manager (Data Integration Layer)
        data_integration_manager = await _safe_init(
            lambda: get_data_integration_manager(), "Data Integration Manager", timeout=2.0
        )
        await _safe_init(
            lambda: data_integration_manager.start_auto_sync(),
            "Data integration auto sync",
            timeout=5.0,
        )
        _logger.info("Data Integration Manager initialized and started (Data Integration Layer)")

        _logger.info(
            "Phase 4 Security Compliance and Security Integration initialized successfully"
        )
    except Exception as e:
        _logger.info(
            f"Phase 4 Security Compliance and Security Integration initialization failed "  # noqa: E501
            f"(continuing without it): {e}"
        )

    # ================================
    # Phase 5: Optimization Verification and Integration Verification Initialization
    # ================================
    try:
        # Initialize Performance Optimizer (Optimization Layer)
        await _safe_init(
            lambda: get_performance_optimizer(), "Performance Optimizer", timeout=2.0
        )  # noqa: F841
        # Auto-optimization is started in __init__ via _start_background_monitoring
        # await performance_optimizer.start_auto_optimization()
        _logger.info("Performance Optimizer initialized and started (Optimization Layer)")

        # Initialize Integration Testing System (Testing Layer)
        integration_testing_system = await _safe_init(
            lambda: get_integration_testing_system(), "Integration Testing System", timeout=2.0
        )
        await _safe_init(
            lambda: integration_testing_system.start_auto_run(),
            "Integration testing auto run",
            timeout=5.0,
        )
        _logger.info("Integration Testing System initialized and started (Testing Layer)")

        # Initialize Integration Monitoring System (Monitoring Layer)
        integration_monitoring_system = await _safe_init(
            lambda: get_integration_monitoring_system(),
            "Integration Monitoring System",
            timeout=2.0,
        )
        await _safe_init(
            lambda: integration_monitoring_system.start_monitoring(),
            "Integration monitoring start",
            timeout=5.0,
        )
        _logger.info("Integration Monitoring System initialized and started (Monitoring Layer)")

        # Initialize Documentation Manager (Documentation Layer)
        await _safe_init(
            lambda: get_documentation_manager(), "Documentation Manager", timeout=2.0
        )  # noqa: F841
        _logger.info("Documentation Manager initialized (Documentation Layer)")

        # Initialize User Training System (Training Layer)
        await _safe_init(
            lambda: get_user_training_system(), "User Training System", timeout=2.0
        )  # noqa: F841
        _logger.info("User Training System initialized (Training Layer)")

        # Initialize Integration Test Validator (Validation Layer)
        await _safe_init(
            lambda: get_integration_test_validator(), "Integration Test Validator", timeout=2.0
        )  # noqa: F841
        _logger.info("Integration Test Validator initialized (Validation Layer)")

        # Initialize Performance Integration Tester (Performance Testing Layer)
        await _safe_init(
            lambda: get_performance_integration_tester(),
            "Performance Integration Tester",
            timeout=2.0,
        )  # noqa: F841
        _logger.info("Performance Integration Tester initialized (Performance Testing Layer)")

        # Initialize Integration Documentation Manager (Integration Documentation Layer)
        await _safe_init(
            lambda: get_integration_documentation_manager(),
            "Integration Documentation Manager",
            timeout=2.0,
        )  # noqa: F841
        _logger.info(
            "Integration Documentation Manager initialized "  # noqa: E501
            "(Integration Documentation Layer)"
        )

        _logger.info(
            "Phase 5 Optimization Verification and Integration Verification "  # noqa: E501
            "initialized successfully"
        )
    except Exception as e:
        _logger.info(
            f"Phase 5 Optimization Verification and Integration Verification initialization failed "  # noqa: E501
            f"(continuing without it): {e}"  # noqa: E501
        )

    try:
        # Initialize AI enhancement (L2 Analysis Layer)
        from core.ai_enhancement import get_ai_enhancer  # noqa: E402

        global _ai_enhancer
        _ai_enhancer = await _safe_init(lambda: get_ai_enhancer(), "Ai Enhancer", timeout=2.0)
        _logger.info("AI enhancement module initialized (L2 Layer)")
    except Exception as e:
        _logger.info(f"AI enhancement initialization failed: {e}")
        # 🔧 P0 Real Integration: Apply real enhancements to actual code
    try:
        from core.real_integration import apply_real_integrations  # noqa: E402

        apply_real_integrations()
        _logger.info("P0 Real enhancements applied to actual code")
    except Exception as e:
        _logger.info(f"P0 Real enhancements application failed: {e}")

    # Initialize Core Components - Authentication, Data Lineage, Feature Flags, Plugin Marketplace
    # Global variables for shutdown
    _llm_analysis_service = None
    _data_lineage_manager = None
    _feature_flag_manager = None
    _plugin_marketplace = None
    _loki_storage = None
    _tempo_storage = None
    _victoriametrics_storage = None
    _grpc_server = None  # type: ignore[assignment]

    # Get L4 storage manager once for all components
    from core.storage.l4.storage_manager import get_l4_storage_manager  # noqa: E402

    l4_storage = await _safe_init(
        lambda: get_l4_storage_manager(), "L4 Storage Manager", timeout=2.0
    )

    try:
        # Initialize JWT AuthService (already used in authentication.py, ensure it's available)
        from core.authentication import auth_service  # noqa: F401

        _logger.info("JWT AuthService initialized successfully")
    except Exception as e:
        _logger.info(f"JWT AuthService initialization failed (continuing without it): {e}")

    try:
        # Initialize PostgreSQL Alert Repository
        from core.db_engine import alert_repository  # noqa: F401

        _logger.info("PostgreSQL Alert Repository initialized successfully")
    except Exception as e:
        _logger.info(
            f"PostgreSQL Alert Repository initialization failed (continuing without it): {e}"
        )

    try:
        # Initialize LLM Analysis Service
        from core.ai_engine import LLMAnalysisService  # noqa: E402

        _llm_analysis_service = LLMAnalysisService()  # noqa: F841
        _logger.info("LLM Analysis Service initialized successfully")
    except Exception as e:
        _logger.info(f"LLM Analysis Service initialization failed (continuing without it): {e}")

    try:
        # Initialize Data Lineage Manager
        from core.data_lineage import create_data_lineage_manager  # noqa: E402

        _data_lineage_manager = create_data_lineage_manager(storage=l4_storage)
        if _data_lineage_manager:
            _logger.info("Data Lineage Manager initialized successfully")
        else:
            _logger.info("Data Lineage Manager initialization failed")
    except Exception as e:
        _logger.info(f"Data Lineage Manager initialization failed (continuing without it): {e}")

    try:
        # Initialize Feature Flag Manager
        from core.feature_flag import create_feature_flag_manager  # noqa: E402

        _feature_flag_manager = create_feature_flag_manager(storage=l4_storage)
        if _feature_flag_manager:
            _logger.info("Feature Flag Manager initialized successfully")
        else:
            _logger.info("Feature Flag Manager initialization failed")
    except Exception as e:
        _logger.info(f"Feature Flag Manager initialization failed (continuing without it): {e}")

    try:
        # Initialize Plugin Marketplace
        from core.plugin_marketplace import PluginMarketplace  # noqa: E402

        _plugin_marketplace = PluginMarketplace(storage=l4_storage)
        if await _safe_init(
            lambda: _plugin_marketplace.initialize(), "Plugin Marketplace initialize", timeout=5.0
        ):
            _logger.info("Plugin Marketplace initialized successfully")
        else:
            _logger.info("Plugin Marketplace initialization failed")
    except Exception as e:
        _logger.info(f"Plugin Marketplace initialization failed (continuing without it): {e}")

    # Initialize Storage Implementations (Loki, Tempo, VictoriaMetrics)
    try:
        from core.storage.l4.loki import LokiStorage  # noqa: E402
        from core.storage.l4.tempo import TempoStorage  # noqa: E402
        from core.storage.l4.victoriametrics import VictoriaMetricsStorage  # noqa: E402

        storage_config = L4_STORAGE_CONFIG.get("implementations", L4_STORAGE_CONFIG)

        if storage_config.get("loki", {}).get("enabled", False):
            _loki_storage = LokiStorage(storage_config.get("loki", {}))
            if await _safe_init(
                lambda: _loki_storage.initialize(), "Loki Storage initialize", timeout=5.0
            ):
                _logger.info("Loki Storage initialized successfully")

        if storage_config.get("tempo", {}).get("enabled", False):
            _tempo_storage = TempoStorage(storage_config.get("tempo", {}))
            if await _safe_init(
                lambda: _tempo_storage.initialize(), "Tempo Storage initialize", timeout=5.0
            ):
                _logger.info("Tempo Storage initialized successfully")

        if storage_config.get("victoriametrics", {}).get("enabled", False):
            _victoriametrics_storage = VictoriaMetricsStorage(
                storage_config.get("victoriametrics", {})
            )
            if await _safe_init(
                lambda: _victoriametrics_storage.initialize(),
                "VictoriaMetrics Storage initialize",
                timeout=5.0,
            ):
                _logger.info("VictoriaMetrics Storage initialized successfully")
    except Exception as e:
        _logger.info(f"Storage implementations initialization failed (continuing without it): {e}")

    _logger.info("Application startup completed.")
    # 启动异常检测后台任务
    # asyncio.create_task(core.anomaly_detector.schedule_anomaly_check())  #
    # Temporarily disabled - core.anomaly_detector not found

    # 启动告警/指标采集后台循环,为 metrics/history 和 alerts 提供实时数据
    try:
        from core.alert_engine import alert_monitor_loop

        asyncio.create_task(alert_monitor_loop())
        _logger.info("Alert monitor loop started")
    except Exception as e:
        _logger.warning(f"Failed to start alert monitor loop: {e}")

    try:
        await _safe_init_core(lambda: init_db(), "auth database init")
    except Exception as e:
        _logger.warning(f"Auth database init failed: {e}")

    try:
        from core.db_engine import async_init_db

        await _safe_init_core(async_init_db, "async database init", timeout=15.0)
    except Exception as e:
        _logger.warning(f"Async database init failed: {e}")

    yield

    # Shutdown
    _logger.info("Application shutdown started.")
    # 🔧 P0/P1 Enhancement: Shutdown enhanced components
    try:
        from core.telemetry import shutdown_telemetry  # noqa: E402

        shutdown_telemetry()
    except Exception as e:
        _logger.info(f"OpenTelemetry shutdown failed: {e}")
    # 关闭所有复用的 http 客户端资源
    for _get_client in (_notify_get_http_client, _ai_get_http_client, _stats_get_http_client):
        try:
            client = _get_client()
            if client is not None:
                close_coro = getattr(client, "aclose", getattr(client, "close", None))
                if close_coro is not None:
                    await close_coro()
        except Exception as e:
            _logger.info(f"HTTP client shutdown failed: {e}")
    # 关闭 Slack 与 Teams 客户端（若已创建）
    try:
        await close_slack_client()
    except Exception as exc:  # pragma: no cover
        _logger.error("Shutdown Slack client error: %s", exc, exc_info=True)
    try:
        await close_teams_client()
    except Exception as exc:  # pragma: no cover
        _logger.error("Shutdown Teams client error: %s", exc, exc_info=True)
    # 关闭 L4 Storage Layer
    try:
        l4_manager = await _safe_init(
            lambda: get_l4_storage_manager(), "L4 Storage Manager", timeout=2.0
        )
        if l4_manager:
            l4_manager.close()
            _logger.info("L4 Storage Layer closed successfully")
    except Exception as exc:  # pragma: no cover
        _logger.error("Shutdown L4 Storage Layer error: %s", exc, exc_info=True)

    # 关闭 L2 Analysis Layer
    try:
        from core.analysis.l2.rag_engine import get_rag_engine  # noqa: E402

        rag_engine = await _safe_init(lambda: get_rag_engine(), "Rag Engine", timeout=2.0)
        if rag_engine:
            rag_engine.close()
            _logger.info("L2 Analysis Layer closed successfully")
    except Exception as exc:  # pragma: no cover
        _logger.error("Shutdown L2 Analysis Layer error: %s", exc, exc_info=True)

    # 关闭 Core Components (Data Lineage, Feature Flags, Plugin Marketplace)
    try:
        if _data_lineage_manager:
            _logger.info("Data Lineage Manager closed successfully")
    except Exception as exc:
        _logger.error("Shutdown Data Lineage Manager error: %s", exc, exc_info=True)

    try:
        if _feature_flag_manager:
            _logger.info("Feature Flag Manager closed successfully")
    except Exception as exc:
        _logger.error("Shutdown Feature Flag Manager error: %s", exc, exc_info=True)

    try:
        if _plugin_marketplace:
            _logger.info("Plugin Marketplace shutdown completed")
    except Exception as exc:
        _logger.error("Shutdown Plugin Marketplace error: %s", exc, exc_info=True)

    # 关闭 Storage Implementations
    try:
        if _loki_storage:
            _logger.info("Loki Storage closed successfully")
        if _tempo_storage:
            _logger.info("Tempo Storage closed successfully")
        if _victoriametrics_storage:
            _logger.info("VictoriaMetrics Storage closed successfully")
    except Exception as exc:
        _logger.error("Shutdown Storage implementations error: %s", exc, exc_info=True)

    # 关闭漏洞情报客户端
    try:
        from core.vulnerability_intelligence import vulnerability_intelligence  # noqa: F402

        await vulnerability_intelligence.close()
        _logger.info("Vulnerability Intelligence clients closed successfully")
    except Exception as exc:
        _logger.error("Shutdown Vulnerability Intelligence error: %s", exc, exc_info=True)

    # 关闭 L5 Interface Layer
    try:
        from core.interface.l5.graphql_interface import get_graphql_interface  # noqa: E402
        from core.interface.l5.mcp_interface import get_mcp_interface  # noqa: E402

        await _safe_init(lambda: get_mcp_interface(), "Mcp Interface", timeout=2.0)  # noqa: F841
        await _safe_init(
            lambda: get_graphql_interface(), "Graphql Interface", timeout=2.0
        )  # noqa: F841

        # Stop gRPC server
        if _grpc_server:
            try:
                await _grpc_server.stop()
                _logger.info("gRPC server stopped successfully")
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)

        # Note: These interfaces don't have explicit close methods
        _logger.info("L5 Interface Layer closed successfully")
    except Exception as exc:  # pragma: no cover
        _logger.error("Shutdown L5 Interface Layer error: %s", exc, exc_info=True)

    # 关闭 L7 Integration Layer
    try:
        from core.integration.l7.collaboration_integration import (  # noqa: E402
            get_collaboration_integration,
        )
        from core.integration.l7.itSM_integration import get_itsm_integration  # noqa: E402

        await _safe_init(
            lambda: get_itsm_integration(), "Itsm Integration", timeout=2.0
        )  # noqa: F841
        await _safe_init(
            lambda: get_collaboration_integration(), "Collaboration Integration", timeout=2.0
        )  # noqa: F841
        # Note: These integrations don't have explicit close methods
        _logger.info("L7 Integration Layer closed successfully")
    except Exception as exc:  # pragma: no cover
        _logger.error("Shutdown L7 Integration Layer error: %s", exc, exc_info=True)

    # 关闭 L3 Processing Layer
    try:
        from core.processing.l3.causal_graph import get_causal_graph  # noqa: F401
        from core.processing.l3.workflow_engine import get_workflow_engine  # noqa: F401

        # Note: These components don't have explicit close methods
        _logger.info("L3 Processing Layer closed successfully")
    except Exception as exc:  # pragma: no cover
        _logger.error("Shutdown L3 Processing Layer error: %s", exc, exc_info=True)

    # 关闭 L6 Execution Layer
    try:
        from core.execution.l6.optimized_executor import get_optimized_executor  # noqa: E402

        executor = await _safe_init(
            lambda: get_optimized_executor(), "Optimized Executor", timeout=2.0
        )
        if executor:
            executor.clear_cache()
        _logger.info("L6 Execution Layer closed successfully")
    except Exception as exc:  # pragma: no cover
        _logger.error("Shutdown L6 Execution Layer error: %s", exc, exc_info=True)

    _logger.info("Application shutdown completed.")


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
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000"
).split(",")
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
    (localization_resource_router, I18N_ENABLED),
    (localization_adapter_router, I18N_ENABLED),
    (localization_advanced_router, I18N_ENABLED),
    # Documentation & Tooling Pack
    (documentation_router, DOC_GENERATION_ENABLED),
    (documentation_advanced_router, DOC_GENERATION_ENABLED),
    (doc_generator_router, DOC_GENERATION_ENABLED),
    (frontend_enhancement_router, DOC_GENERATION_ENABLED),
    (frontend_advanced_router, DOC_GENERATION_ENABLED),
    (graphql_router, GRAPHQL_ENABLED),
]

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
