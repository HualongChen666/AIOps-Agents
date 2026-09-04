# -*- coding: utf-8 -*-
"""
Application lifecycle management for startup and shutdown operations.
This module handles the complex initialization and cleanup of various system components.
"""

import asyncio
import inspect
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Optional

from loguru import logger

from config import ENABLE_ADDONS

_logger = logger

# Import required modules for initialization
try:
    from core.notify import _get_http_client as _notify_get_http_client
    from core.notify import close_slack_client, close_teams_client
except ImportError:
    _notify_get_http_client = None
    close_slack_client = None
    close_teams_client = None

try:
    from core.ai_engine import _get_http_client as _ai_get_http_client
except ImportError:
    _ai_get_http_client = None

try:
    from core.stats import _get_http_client as _stats_get_http_client
except ImportError:
    _stats_get_http_client = None

try:
    from core.command_guard import register_self_pid
except ImportError:
    register_self_pid = None

try:
    from core.access_control import setup_default_access_policies
except ImportError:
    setup_default_access_policies = None


# Core init names that always run regardless of ENABLE_ADDONS
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


async def _safe_init(
    coro_or_callable: Any,
    name: str,
    timeout: float = 2.0,
    addon: Optional[bool] = None,
) -> Any:
    """
    Safely initialize a component with timeout and error handling.

    Args:
        coro_or_callable: Coroutine or callable to execute
        name: Name of the component being initialized
        timeout: Timeout in seconds
        addon: Whether this is an add-on component (auto-detected if None)

    Returns:
        Result of the initialization or None on failure
    """
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
            result = await asyncio.wait_for(asyncio.to_thread(coro_or_callable), timeout=timeout)
            if inspect.isawaitable(result):
                result = await asyncio.wait_for(result, timeout=timeout)
        else:
            result = coro_or_callable
        _logger.info(f"{name} initialized successfully")
        return result
    except asyncio.TimeoutError:
        _logger.warning(f"{name} initialization timed out after {timeout}s; continuing without it")
    except Exception as exc:
        if is_addon:
            _logger.debug(f"{name} initialization failed: {exc}; continuing without it")
        else:
            _logger.warning(f"{name} initialization failed: {exc}; continuing without it")
    return None


async def _safe_init_core(coro_or_callable: Any, name: str, timeout: float = 2.0) -> Any:
    """
    Always-run variant for core components.

    Args:
        coro_or_callable: Coroutine or callable to execute
        name: Name of the component being initialized
        timeout: Timeout in seconds

    Returns:
        Result of the initialization or None on failure
    """
    return await _safe_init(coro_or_callable, name, timeout=timeout, addon=False)


async def _initialize_hardware_remediation() -> None:
    """Register hardware remediation dry-run scripts."""
    try:
        import extensions.hardware_remediation  # noqa: F401

        _logger.info("Hardware remediation extensions registered")
    except ImportError:
        _logger.info("Hardware remediation extensions not available")
    except Exception as e:
        _logger.info(f"Hardware remediation extensions registration failed: {e}")


async def _initialize_pre_startup_components() -> None:
    """Initialize components that need to run before main startup."""
    # Pre-warm http clients
    if _notify_get_http_client:
        _notify_get_http_client()
    if _ai_get_http_client:
        _ai_get_http_client()
    if _stats_get_http_client:
        _stats_get_http_client()

    # Register self PID to prevent AI-generated suicide commands
    if register_self_pid:
        register_self_pid()

    # Load default ABAC access policies
    if setup_default_access_policies:
        setup_default_access_policies()


async def _initialize_l4_storage_layer() -> None:
    """Initialize L4 Storage Layer (7-Layer Architecture - Phase 1)."""
    from config import L4_STORAGE_CONFIG
    from core.storage.l4.storage_manager import init_l4_storage_manager

    try:
        await _safe_init(
            lambda: init_l4_storage_manager(L4_STORAGE_CONFIG), "L4 Storage Layer", timeout=5.0
        )
        _logger.info("L4 Storage Layer initialized successfully")
    except Exception as e:
        _logger.info(f"L4 Storage Layer initialization failed (continuing without it): {e}")


async def _initialize_l2_analysis_layer() -> None:
    """Initialize L2 Analysis Layer (7-Layer Architecture - Phase 2)."""
    from config import L2_ANALYSIS_CONFIG
    from core.analysis.l2.model_router import init_model_router
    from core.analysis.l2.rag_engine import init_rag_engine

    try:
        # Make RAG engine initialization more tolerant with longer timeout
        await _safe_init(
            lambda: init_rag_engine(L2_ANALYSIS_CONFIG.get("rag", {})), "RAG engine", timeout=10.0
        )
    except Exception as e:
        _logger.warning(f"RAG engine initialization failed (continuing without it): {e}")
    
    try:
        await _safe_init(
            lambda: init_model_router(L2_ANALYSIS_CONFIG.get("model_router", {})),
            "Model router",
            timeout=5.0,
        )
        _logger.info("L2 Analysis Layer initialized successfully")
    except Exception as e:
        _logger.warning(f"L2 Analysis Layer initialization failed (continuing without it): {e}")


async def _initialize_l5_interface_layer(_grpc_server: Any) -> None:
    """Initialize L5 Interface Layer (7-Layer Architecture - Phase 3)."""
    from config import L5_INTERFACE_CONFIG
    from core.interface.grpc import AIOpsGrpcServer
    from core.interface.l5.graphql_interface import init_graphql_interface
    from core.interface.l5.mcp_interface import init_mcp_interface

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

        # Start gRPC server in background
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


async def _initialize_l7_integration_layer() -> None:
    """Initialize L7 Integration Layer (7-Layer Architecture - Phase 3)."""
    from config import L7_INTEGRATION_CONFIG
    from core.integration.l7.collaboration_integration import (
        init_collaboration_integration,
    )
    from core.integration.l7.itSM_integration import init_itsm_integration

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


async def _initialize_l3_processing_layer() -> None:
    """Initialize L3 Processing Layer (7-Layer Architecture - Phase 4)."""
    from config import L3_PROCESSING_CONFIG
    from core.processing.l3.causal_graph import init_causal_graph
    from core.processing.l3.workflow_engine import init_workflow_engine

    try:
        workflow_engine = await _safe_init(
            lambda: init_workflow_engine(L3_PROCESSING_CONFIG.get("workflow_engine", {})),
            "Workflow engine",
            timeout=5.0,
        )
        if workflow_engine:
            workflow_engine.create_incident_response_workflow()

        causal_graph = await _safe_init(
            lambda: init_causal_graph(L3_PROCESSING_CONFIG.get("causal_graph", {})),
            "Causal graph",
            timeout=5.0,
        )
        if causal_graph and L3_PROCESSING_CONFIG.get("causal_graph", {}).get("auto_build", True):
            causal_graph.build_system_topology()

        # Initialize priority and HITL components
        from core.hitl import ApprovalWorkflow
        from core.priority import BusinessImpactAssessor, PriorityRanker

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


async def _initialize_l6_execution_layer() -> None:
    """Initialize L6 Execution Layer (7-Layer Architecture - Phase 4)."""
    from config import L6_EXECUTION_CONFIG
    from core.execution.l6.optimized_executor import init_optimized_executor

    try:
        await _safe_init(
            lambda: init_optimized_executor(L6_EXECUTION_CONFIG), "Optimized executor", timeout=5.0
        )
        _logger.info("L6 Execution Layer initialized successfully")
    except Exception as e:
        _logger.info(f"L6 Execution Layer initialization failed (continuing without it): {e}")


async def _initialize_telemetry(app: Any) -> None:
    """Initialize OpenTelemetry for APM monitoring."""
    from config import (
        ENVIRONMENT,
        LOKI_ENABLED,
        LOKI_URL,
        OTEL_COLLECTOR_ENDPOINT,
        TEMPO_ENABLED,
        TEMPO_URL,
    )
    from core.telemetry import (
        instrument_kafka,
        setup_trace_propagation,
        setup_tracing_middleware,
    )
    from core.telemetry.fastapi import setup_fastapi_telemetry

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
        setup_tracing_middleware(app)
        setup_trace_propagation()
        instrument_kafka()
        _logger.info("OpenTelemetry initialized for APM monitoring (L5 Layer)")
    else:
        _logger.info("OpenTelemetry initialization returned False")

    # Wire structured logs to Loki when enabled
    if LOKI_ENABLED and LOKI_URL:
        from core.structured_logging import setup_loki_logging

        if await _safe_init(
            lambda: setup_loki_logging(LOKI_URL, service_name="aiops-agent"),
            "Loki log shipping",
            timeout=5.0,
        ):
            _logger.info(f"Loki log shipping enabled for {LOKI_URL}")
        else:
            _logger.info("Loki log shipping not available")


async def _initialize_database_optimization() -> None:
    """Initialize database optimization components."""
    from core.db_optimization import PERFORMANCE_INDEXES
    from core.models import Alert

    try:
        Alert.__table_args__ = (
            tuple(PERFORMANCE_INDEXES[:5])  # type: ignore[assignment]
            if PERFORMANCE_INDEXES
            else ()
        )
        _logger.info("Database performance indexes configured (L4 Layer)")
    except Exception as e:
        _logger.info(f"Database optimization initialization failed: {e}")

    try:
        from core.database_optimization_manager import get_database_optimization_manager

        db_opt_manager = await _safe_init(
            lambda: get_database_optimization_manager(),
            "Database Optimization Manager",
            timeout=2.0,
        )
        if db_opt_manager:
            optimization_result = db_opt_manager.run_comprehensive_optimization()
            _logger.info(
                f"Database optimization manager initialized: {optimization_result['overall_status']}"
            )
    except Exception as e:
        _logger.info(f"Database optimization manager initialization failed: {e}")


async def _initialize_performance_optimizers() -> None:
    """Initialize various performance optimizer components."""
    from core.api_performance_optimizer import get_api_performance_optimizer
    from core.automation_manager import get_automation_manager
    from core.coverage_manager import get_coverage_manager
    from core.documentation_generator import get_documentation_generator
    from core.documentation_manager import get_documentation_manager
    from core.ecosystem_manager import get_ecosystem_manager
    from core.i18n_manager import get_i18n_manager
    from core.localization_adapter import get_localization_adapter
    from core.marketplace_manager import get_marketplace_manager
    from core.plugin_sdk import get_plugin_sdk
    from core.plugin_system_manager import get_plugin_system_manager
    from core.resource_manager import get_resource_manager
    from core.service_discovery_manager import get_service_discovery_manager
    from core.service_mesh_manager import get_service_mesh_manager
    from core.service_monitoring_manager import get_service_monitoring_manager
    from core.system_resource_optimizer import get_system_resource_optimizer
    from core.test_framework_manager import get_test_framework_manager

    optimizers = [
        ("Api Performance Optimizer", lambda: get_api_performance_optimizer()),
        ("System Resource Optimizer", lambda: get_system_resource_optimizer()),
        ("Service Mesh Manager", lambda: get_service_mesh_manager()),
        ("Service Discovery Manager", lambda: get_service_discovery_manager()),
        ("Service Monitoring Manager", lambda: get_service_monitoring_manager()),
        ("Plugin System Manager", lambda: get_plugin_system_manager()),
        ("Plugin Sdk", lambda: get_plugin_sdk()),
        ("Marketplace Manager", lambda: get_marketplace_manager()),
        ("Ecosystem Manager", lambda: get_ecosystem_manager()),
        ("I18N Manager", lambda: get_i18n_manager()),
        ("Resource Manager", lambda: get_resource_manager()),
        ("Localization Adapter", lambda: get_localization_adapter()),
        ("Test Framework Manager", lambda: get_test_framework_manager()),
        ("Coverage Manager", lambda: get_coverage_manager()),
        ("Automation Manager", lambda: get_automation_manager()),
        ("Documentation Manager", lambda: get_documentation_manager()),
        ("Documentation Generator", lambda: get_documentation_generator()),
    ]

    for name, getter in optimizers:
        try:
            await _safe_init(getter, name, timeout=2.0)  # noqa: F841
            _logger.info(f"{name} initialized")
        except Exception as e:
            _logger.info(f"{name} initialization failed: {e}")


async def _initialize_enterprise_enhancements() -> None:
    """Initialize P0/P1/P2 Enterprise Enhancements."""
    from core.accessibility_support import setup_accessibility_support
    from core.api_governance import setup_api_governance
    from core.business_metrics import setup_business_metrics
    from core.chaos_engineering import setup_chaos_engineering
    from core.data_lifecycle_manager import setup_data_lifecycle
    from core.dependency_injection import setup_dependency_injection
    from core.disaster_recovery_drill import setup_disaster_recovery
    from core.error_recovery import setup_error_recovery
    from core.frontend_cache_strategy import setup_cache_headers_middleware
    from core.memory_monitoring import setup_memory_monitoring
    from core.module_validation import check_all_modules_health, validate_initialization_order

    enhancements = [
        ("Memory monitoring", lambda: setup_memory_monitoring(), "P0-4"),
        ("Error recovery", lambda: setup_error_recovery(), "P0-5"),
        ("Dependency injection", lambda: setup_dependency_injection(), "P1-1"),
        ("Business metrics", lambda: setup_business_metrics(), "P1-3"),
        ("Cache headers middleware", lambda: setup_cache_headers_middleware(), "P1-4"),
        ("Data lifecycle", lambda: setup_data_lifecycle(), "P2-1"),
        ("API governance", lambda: setup_api_governance(), "P2-2"),
        (
            "Module initialization order validation",
            lambda: validate_initialization_order(),
            "Phase 1",
        ),
        ("Module health check", lambda: check_all_modules_health(), "Phase 1"),
        ("Disaster recovery", lambda: setup_disaster_recovery(), "P2-3"),
        ("Accessibility support", lambda: setup_accessibility_support(), "P2-4"),
        ("Chaos engineering", lambda: setup_chaos_engineering(), "P2-5"),
    ]

    for name, getter, phase in enhancements:
        try:
            await _safe_init(getter, name, timeout=5.0)
            _logger.info(f"{name} initialized ({phase})")
        except Exception as e:
            _logger.info(f"{name} initialization failed: {e}")


async def _initialize_infrastructure_enhancements() -> None:
    """Initialize Phase 1 Infrastructure Enhancement components."""
    from core.config_center import get_config_center, get_service_discovery
    from core.distributed_storage import get_distributed_storage_manager
    from core.flink_stream_processor import get_flink_job_manager
    from core.kafka_stream_processor import get_kafka_processor
    from core.l1l2_data_flow_integrator import get_l1l2_data_flow_integrator
    from core.monitoring_infrastructure import get_monitoring_infrastructure

    try:
        await _safe_init(lambda: get_kafka_processor(), "Kafka Processor", timeout=2.0)
        await _safe_init(lambda: get_flink_job_manager(), "Flink Job Manager", timeout=2.0)
        await _safe_init(
            lambda: get_distributed_storage_manager(), "Distributed Storage Manager", timeout=2.0
        )
        await _safe_init(lambda: get_config_center(), "Config Center", timeout=2.0)
        await _safe_init(lambda: get_service_discovery(), "Service Discovery", timeout=2.0)
        await _safe_init(
            lambda: get_monitoring_infrastructure(), "Monitoring Infrastructure", timeout=2.0
        )

        data_flow_integrator = await _safe_init(
            lambda: get_l1l2_data_flow_integrator(), "L1L2 Data Flow Integrator", timeout=2.0
        )
        if data_flow_integrator:
            await _safe_init(
                lambda: data_flow_integrator.start_data_flow(), "L1-L2 Data Flow start", timeout=5.0
            )

        _logger.info("Phase 1 Infrastructure Enhancement initialized successfully")
    except Exception as e:
        _logger.info(
            f"Phase 1 Infrastructure Enhancement initialization failed (continuing without it): {e}"
        )


async def _initialize_core_function_enhancements() -> None:
    """Initialize Phase 2 Core Function Enhancement and Integration components."""
    from core.analysis.l2.enhanced_causal_analyzer import get_enhanced_causal_analyzer
    from core.db_read_write_router import get_read_write_router
    from core.enhanced_auth_integration import get_enhanced_auth_integration
    from core.enhanced_websocket_manager import get_enhanced_websocket_manager
    from core.execution.l6.fault_tolerant_executor import get_fault_tolerant_executor
    from core.l2l3_workflow_integrator import get_l2l3_workflow_integrator
    from core.l3l4_storage_integrator import get_l3l4_storage_integrator
    from core.websocket_integrator import get_websocket_integrator

    try:
        await _safe_init(
            lambda: get_enhanced_causal_analyzer(), "Enhanced Causal Analyzer", timeout=2.0
        )
        await _safe_init(
            lambda: get_fault_tolerant_executor(), "Fault Tolerant Executor", timeout=2.0
        )
        await _safe_init(lambda: get_read_write_router(), "Read Write Router", timeout=2.0)
        await _safe_init(
            lambda: get_enhanced_websocket_manager(), "Enhanced Websocket Manager", timeout=2.0
        )

        l2l3_workflow_integrator = await _safe_init(
            lambda: get_l2l3_workflow_integrator(), "L2L3 Workflow Integrator", timeout=2.0
        )
        await _safe_init(
            lambda: get_l3l4_storage_integrator(), "L3L4 Storage Integrator", timeout=2.0
        )
        await _safe_init(
            lambda: get_enhanced_auth_integration(), "Enhanced Auth Integration", timeout=2.0
        )

        websocket_integrator = await _safe_init(
            lambda: get_websocket_integrator(), "Websocket Integrator", timeout=2.0
        )
        if websocket_integrator:
            await _safe_init(
                lambda: websocket_integrator.start(), "WebSocket Integrator start", timeout=5.0
            )

        _logger.info("Phase 2 Core Function Enhancement and Integration initialized successfully")
    except Exception as e:
        _logger.info(
            f"Phase 2 Core Function Enhancement and Integration initialization failed "
            f"(continuing without it): {e}"
        )


async def _initialize_advanced_functions() -> None:
    """Initialize Phase 3 Advanced Function Implementation and Integration components."""
    from core.cicd_integration_manager import get_cicd_integration_manager
    from core.cicd_pipeline_manager import get_cicd_pipeline_manager
    from core.frontend_performance_optimizer import get_frontend_performance_optimizer
    from core.kubernetes_deployment_manager import get_kubernetes_deployment_manager
    from core.l4l5_data_integrator import get_l4l5_data_integrator
    from core.l5l6_execution_integrator import get_l5l6_execution_integrator
    from core.l6l7_frontend_integrator import get_l6l7_frontend_integrator
    from core.model_fine_tuner import get_model_fine_tuner
    from core.third_party_service_integrator import get_third_party_service_integrator

    try:
        await _safe_init(lambda: get_model_fine_tuner(), "Model Fine Tuner", timeout=2.0)
        await _safe_init(
            lambda: get_frontend_performance_optimizer(),
            "Frontend Performance Optimizer",
            timeout=2.0,
        )
        await _safe_init(
            lambda: get_kubernetes_deployment_manager(),
            "Kubernetes Deployment Manager",
            timeout=2.0,
        )
        await _safe_init(lambda: get_cicd_pipeline_manager(), "Cicd Pipeline Manager", timeout=2.0)

        l4l5_data_integrator = await _safe_init(
            lambda: get_l4l5_data_integrator(), "L4L5 Data Integrator", timeout=2.0
        )
        if l4l5_data_integrator:
            await _safe_init(
                lambda: l4l5_data_integrator.start_realtime_processing(),
                "L4-L5 Data Integrator start",
                timeout=5.0,
            )

        l5l6_execution_integrator = await _safe_init(
            lambda: get_l5l6_execution_integrator(), "L5L6 Execution Integrator", timeout=2.0
        )
        if l5l6_execution_integrator:
            await _safe_init(
                lambda: l5l6_execution_integrator.start_execution_processor(),
                "L5-L6 Execution Integrator start",
                timeout=5.0,
            )

        l6l7_frontend_integrator = await _safe_init(
            lambda: get_l6l7_frontend_integrator(), "L6L7 Frontend Integrator", timeout=2.0
        )
        if l6l7_frontend_integrator:
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

        third_party_service_integrator = await _safe_init(
            lambda: get_third_party_service_integrator(),
            "Third Party Service Integrator",
            timeout=2.0,
        )
        if third_party_service_integrator:
            await _safe_init(
                lambda: third_party_service_integrator.start_health_check_loop(),
                "Third-party service integrator health check",
                timeout=5.0,
            )

        await _safe_init(
            lambda: get_cicd_integration_manager(), "Cicd Integration Manager", timeout=2.0
        )

        _logger.info(
            "Phase 3 Advanced Function Implementation and Integration initialized successfully"
        )
    except Exception as e:
        _logger.info(
            f"Phase 3 Advanced Function Implementation and Integration initialization failed "
            f"(continuing without it): {e}"
        )


async def _initialize_security_components() -> None:
    """Initialize Phase 4 Security Compliance and Security Integration components."""
    from core.audit_integration_manager import get_audit_integration_manager
    from core.compliance_manager import get_compliance_manager
    from core.data_integration_manager import get_data_integration_manager
    from core.security_audit_system import get_security_audit_system
    from core.security_system_integrator import get_security_system_integrator
    from core.security_testing_system import get_security_testing_system
    from core.vulnerability_manager import get_vulnerability_manager

    try:
        compliance_manager = await _safe_init(
            lambda: get_compliance_manager(), "Compliance Manager", timeout=2.0
        )
        if compliance_manager:
            await _safe_init(
                lambda: compliance_manager.start_auto_check_loop(),
                "Compliance manager auto check",
                timeout=5.0,
            )

        if os.environ.get("AIOPS_DISABLE_SECURITY_SCAN") != "1":
            security_testing_system = await _safe_init(
                lambda: get_security_testing_system(), "Security Testing System", timeout=2.0
            )
            if security_testing_system:
                await _safe_init(
                    lambda: security_testing_system.start_auto_scan_loop(),
                    "Security testing auto scan",
                    timeout=5.0,
                )
        else:
            _logger.info("Security Testing System skipped (AIOPS_DISABLE_SECURITY_SCAN=1)")

        vulnerability_manager = await _safe_init(
            lambda: get_vulnerability_manager(), "Vulnerability Manager", timeout=2.0
        )
        if vulnerability_manager:
            await _safe_init(
                lambda: vulnerability_manager.start_sla_monitoring(),
                "Vulnerability SLA monitoring",
                timeout=5.0,
            )

        await _safe_init(lambda: get_security_audit_system(), "Security Audit System", timeout=2.0)

        security_system_integrator = await _safe_init(
            lambda: get_security_system_integrator(), "Security System Integrator", timeout=2.0
        )
        if security_system_integrator:
            await _safe_init(
                lambda: security_system_integrator.start_auto_health_check(),
                "Security system integrator health check",
                timeout=5.0,
            )

        audit_integration_manager = await _safe_init(
            lambda: get_audit_integration_manager(), "Audit Integration Manager", timeout=2.0
        )
        if audit_integration_manager:
            await _safe_init(
                lambda: audit_integration_manager.start_auto_collection(),
                "Audit integration auto collection",
                timeout=5.0,
            )

        data_integration_manager = await _safe_init(
            lambda: get_data_integration_manager(), "Data Integration Manager", timeout=2.0
        )
        if data_integration_manager:
            await _safe_init(
                lambda: data_integration_manager.start_auto_sync(),
                "Data integration auto sync",
                timeout=5.0,
            )

        _logger.info(
            "Phase 4 Security Compliance and Security Integration initialized successfully"
        )
    except Exception as e:
        _logger.info(
            f"Phase 4 Security Compliance and Security Integration initialization failed "
            f"(continuing without it): {e}"
        )


async def _initialize_optimization_components() -> None:
    """Initialize Phase 5 Optimization Verification and Integration Verification components."""
    from core.documentation_manager import get_documentation_manager
    from core.integration_documentation_manager import get_integration_documentation_manager
    from core.integration_monitoring_system import get_integration_monitoring_system
    from core.integration_test_validator import get_integration_test_validator
    from core.integration_testing_system import get_integration_testing_system
    from core.performance_integration_tester import get_performance_integration_tester
    from core.performance_optimizer import get_performance_optimizer
    from core.user_training_system import get_user_training_system

    try:
        await _safe_init(lambda: get_performance_optimizer(), "Performance Optimizer", timeout=2.0)

        integration_testing_system = await _safe_init(
            lambda: get_integration_testing_system(), "Integration Testing System", timeout=2.0
        )
        if integration_testing_system:
            await _safe_init(
                lambda: integration_testing_system.start_auto_run(),
                "Integration testing auto run",
                timeout=5.0,
            )

        integration_monitoring_system = await _safe_init(
            lambda: get_integration_monitoring_system(),
            "Integration Monitoring System",
            timeout=2.0,
        )
        if integration_monitoring_system:
            await _safe_init(
                lambda: integration_monitoring_system.start_monitoring(),
                "Integration monitoring start",
                timeout=5.0,
            )

        await _safe_init(lambda: get_documentation_manager(), "Documentation Manager", timeout=2.0)
        await _safe_init(lambda: get_user_training_system(), "User Training System", timeout=2.0)
        await _safe_init(
            lambda: get_integration_test_validator(), "Integration Test Validator", timeout=2.0
        )
        await _safe_init(
            lambda: get_performance_integration_tester(),
            "Performance Integration Tester",
            timeout=2.0,
        )
        await _safe_init(
            lambda: get_integration_documentation_manager(),
            "Integration Documentation Manager",
            timeout=2.0,
        )

        _logger.info(
            "Phase 5 Optimization Verification and Integration Verification initialized successfully"
        )
    except Exception as e:
        _logger.info(
            f"Phase 5 Optimization Verification and Integration Verification initialization failed "
            f"(continuing without it): {e}"
        )


async def _initialize_core_components() -> None:
    """Initialize Core Components - Authentication, Data Lineage, Feature Flags, Plugin Marketplace."""
    try:
        from core.authentication import AUTH_SERVICE as auth_service  # noqa: F401

        _logger.info("JWT AuthService initialized successfully")
    except Exception as e:
        _logger.info(f"JWT AuthService initialization failed (continuing without it): {e}")

    try:
        from core.db_engine import alert_repository  # noqa: F401

        _logger.info("PostgreSQL Alert Repository initialized successfully")
    except Exception as e:
        _logger.info(
            f"PostgreSQL Alert Repository initialization failed (continuing without it): {e}"
        )

    try:
        from core.ai_engine import LLMAnalysisService

        _llm_analysis_service = LLMAnalysisService()  # noqa: F841
        _logger.info("LLM Analysis Service initialized successfully")
    except Exception as e:
        _logger.info(f"LLM Analysis Service initialization failed (continuing without it): {e}")

    from core.storage.l4.storage_manager import get_l4_storage_manager

    l4_storage = await _safe_init(
        lambda: get_l4_storage_manager(), "L4 Storage Manager", timeout=2.0
    )

    try:
        from core.data_lineage import create_data_lineage_manager

        _data_lineage_manager = create_data_lineage_manager(storage=l4_storage)
        if _data_lineage_manager:
            _logger.info("Data Lineage Manager initialized successfully")
        else:
            _logger.info("Data Lineage Manager initialization failed")
    except Exception as e:
        _logger.info(f"Data Lineage Manager initialization failed (continuing without it): {e}")

    try:
        from core.feature_flag import create_feature_flag_manager

        _feature_flag_manager = create_feature_flag_manager(storage=l4_storage)
        if _feature_flag_manager:
            _logger.info("Feature Flag Manager initialized successfully")
        else:
            _logger.info("Feature Flag Manager initialization failed")
    except Exception as e:
        _logger.info(f"Feature Flag Manager initialization failed (continuing without it): {e}")

    try:
        from core.plugin_marketplace import PluginMarketplace

        _plugin_marketplace = PluginMarketplace(storage=l4_storage)
        if await _safe_init(
            lambda: _plugin_marketplace.initialize(), "Plugin Marketplace initialize", timeout=5.0
        ):
            _logger.info("Plugin Marketplace initialized successfully")
        else:
            _logger.info("Plugin Marketplace initialization failed")
    except Exception as e:
        _logger.info(f"Plugin Marketplace initialization failed (continuing without it): {e}")


async def _initialize_storage_implementations() -> None:
    """Initialize Storage Implementations (Loki, Tempo, VictoriaMetrics)."""
    from config import L4_STORAGE_CONFIG
    from core.storage.l4.loki import LokiStorage
    from core.storage.l4.tempo import TempoStorage
    from core.storage.l4.victoriametrics import VictoriaMetricsStorage

    try:
        storage_config = L4_STORAGE_CONFIG.get("implementations", L4_STORAGE_CONFIG)

        _loki_storage = None
        _tempo_storage = None
        _victoriametrics_storage = None

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


async def _shutdown_http_clients() -> None:
    """Close all reused HTTP client resources."""
    clients_to_close = []
    if _notify_get_http_client:
        clients_to_close.append(_notify_get_http_client)
    if _ai_get_http_client:
        clients_to_close.append(_ai_get_http_client)
    if _stats_get_http_client:
        clients_to_close.append(_stats_get_http_client)

    for _get_client in clients_to_close:
        try:
            client = _get_client()
            if client is not None:
                close_coro = getattr(client, "aclose", getattr(client, "close", None))
                if close_coro is not None:
                    await close_coro()
        except Exception as e:
            _logger.info(f"HTTP client shutdown failed: {e}")


async def _shutdown_notification_clients() -> None:
    """Close Slack and Teams clients."""
    if close_slack_client:
        try:
            await close_slack_client()
        except Exception as exc:  # pragma: no cover
            _logger.error("Shutdown Slack client error: %s", exc, exc_info=True)

    if close_teams_client:
        try:
            await close_teams_client()
        except Exception as exc:  # pragma: no cover
            _logger.error("Shutdown Teams client error: %s", exc, exc_info=True)


async def _shutdown_storage_layers() -> None:
    """Close L4 and L2 storage layers."""
    from core.analysis.l2.rag_engine import get_rag_engine
    from core.storage.l4.storage_manager import get_l4_storage_manager

    try:
        l4_manager = await _safe_init(
            lambda: get_l4_storage_manager(), "L4 Storage Manager", timeout=2.0
        )
        if l4_manager:
            l4_manager.close()
            _logger.info("L4 Storage Layer closed successfully")
    except Exception as exc:  # pragma: no cover
        _logger.error("Shutdown L4 Storage Layer error: %s", exc, exc_info=True)

    try:
        rag_engine = await _safe_init(lambda: get_rag_engine(), "Rag Engine", timeout=2.0)
        if rag_engine:
            rag_engine.close()
            _logger.info("L2 Analysis Layer closed successfully")
    except Exception as exc:  # pragma: no cover
        _logger.error("Shutdown L2 Analysis Layer error: %s", exc, exc_info=True)


async def _shutdown_interface_layers() -> None:
    """Close L5 and L7 interface layers."""
    from core.integration.l7.collaboration_integration import (
        get_collaboration_integration,
    )
    from core.integration.l7.itSM_integration import get_itsm_integration
    from core.interface.l5.graphql_interface import get_graphql_interface
    from core.interface.l5.mcp_interface import get_mcp_interface

    try:
        await _safe_init(lambda: get_mcp_interface(), "Mcp Interface", timeout=2.0)
        await _safe_init(lambda: get_graphql_interface(), "Graphql Interface", timeout=2.0)

        # Stop gRPC server
        if _grpc_server:
            try:
                await _grpc_server.stop()
                _logger.info("gRPC server stopped successfully")
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)

        _logger.info("L5 Interface Layer closed successfully")
    except Exception as exc:  # pragma: no cover
        _logger.error("Shutdown L5 Interface Layer error: %s", exc, exc_info=True)

    try:
        await _safe_init(lambda: get_itsm_integration(), "Itsm Integration", timeout=2.0)
        await _safe_init(
            lambda: get_collaboration_integration(), "Collaboration Integration", timeout=2.0
        )
        _logger.info("L7 Integration Layer closed successfully")
    except Exception as exc:  # pragma: no cover
        _logger.error("Shutdown L7 Integration Layer error: %s", exc, exc_info=True)


async def _shutdown_processing_layers() -> None:
    """Close L3 and L6 processing layers."""
    from core.execution.l6.optimized_executor import get_optimized_executor

    try:
        executor = await _safe_init(
            lambda: get_optimized_executor(), "Optimized Executor", timeout=2.0
        )
        if executor:
            executor.clear_cache()
        _logger.info("L6 Execution Layer closed successfully")
    except Exception as exc:  # pragma: no cover
        _logger.error("Shutdown L6 Execution Layer error: %s", exc, exc_info=True)


# Global variable for gRPC server
_grpc_server: Any = None


@asynccontextmanager
async def lifespan(app: Any) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager for startup and shutdown operations.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup
    _logger.info("Application startup started.")

    # Initialize hardware remediation
    await _initialize_hardware_remediation()

    # Pre-startup components
    await _initialize_pre_startup_components()

    # Initialize 7-Layer Architecture components
    try:
        await _initialize_l4_storage_layer()
    except Exception as e:
        _logger.warning(f"L4 Storage Layer initialization failed (continuing without it): {e}")
    
    try:
        await _initialize_l2_analysis_layer()
    except Exception as e:
        _logger.warning(f"L2 Analysis Layer initialization failed (continuing without it): {e}")
    
    try:
        await _initialize_l5_interface_layer(_grpc_server)
    except Exception as e:
        _logger.warning(f"L5 Interface Layer initialization failed (continuing without it): {e}")
    
    try:
        await _initialize_l7_integration_layer()
    except Exception as e:
        _logger.warning(f"L7 Integration Layer initialization failed (continuing without it): {e}")
    
    try:
        await _initialize_l3_processing_layer()
    except Exception as e:
        _logger.warning(f"L3 Processing Layer initialization failed (continuing without it): {e}")
    
    try:
        await _initialize_l6_execution_layer()
    except Exception as e:
        _logger.warning(f"L6 Execution Layer initialization failed (continuing without it): {e}")

    # Initialize telemetry
    try:
        await _initialize_telemetry(app)
    except Exception as e:
        _logger.warning(f"Telemetry initialization failed (continuing without it): {e}")

    # Initialize database optimization
    try:
        await _initialize_database_optimization()
    except Exception as e:
        _logger.warning(f"Database optimization initialization failed (continuing without it): {e}")

    # Initialize performance optimizers
    try:
        await _initialize_performance_optimizers()
    except Exception as e:
        _logger.warning(f"Performance optimizers initialization failed (continuing without it): {e}")

    # Initialize enterprise enhancements
    try:
        await _initialize_enterprise_enhancements()
    except Exception as e:
        _logger.warning(f"Enterprise enhancements initialization failed (continuing without it): {e}")

    # Initialize infrastructure enhancements
    try:
        await _initialize_infrastructure_enhancements()
    except Exception as e:
        _logger.warning(f"Infrastructure enhancements initialization failed (continuing without it): {e}")

    # Initialize core function enhancements
    try:
        await _initialize_core_function_enhancements()
    except Exception as e:
        _logger.warning(f"Core function enhancements initialization failed (continuing without it): {e}")

    # Initialize advanced functions
    try:
        await _initialize_advanced_functions()
    except Exception as e:
        _logger.warning(f"Advanced functions initialization failed (continuing without it): {e}")

    # Initialize security components
    try:
        await _initialize_security_components()
    except Exception as e:
        _logger.warning(f"Security components initialization failed (continuing without it): {e}")

    # Initialize optimization components
    try:
        await _initialize_optimization_components()
    except Exception as e:
        _logger.warning(f"Optimization components initialization failed (continuing without it): {e}")

    # Initialize AI enhancement
    try:
        from core.ai_enhancement import get_ai_enhancer

        global _ai_enhancer
        _ai_enhancer = await _safe_init(lambda: get_ai_enhancer(), "Ai Enhancer", timeout=2.0)
        _logger.info("AI enhancement module initialized (L2 Layer)")
    except Exception as e:
        _logger.warning(f"AI enhancement initialization failed (continuing without it): {e}")

    # Apply real integrations
    try:
        from core.real_integration import apply_real_integrations

        apply_real_integrations()
        _logger.info("P0 Real enhancements applied to actual code")
    except Exception as e:
        _logger.warning(f"P0 Real enhancements application failed (continuing without it): {e}")

    # Initialize core components
    try:
        await _initialize_core_components()
    except Exception as e:
        _logger.warning(f"Core components initialization failed (continuing without it): {e}")

    # Initialize storage implementations
    try:
        await _initialize_storage_implementations()
    except Exception as e:
        _logger.warning(f"Storage implementations initialization failed (continuing without it): {e}")

    _logger.info("Application startup completed.")

    # Start alert monitor loop
    try:
        from core.alert_engine import alert_monitor_loop

        asyncio.create_task(alert_monitor_loop())
        _logger.info("Alert monitor loop started")
    except Exception as e:
        _logger.warning(f"Failed to start alert monitor loop: {e}")

    # Initialize database
    try:
        from core.db_engine import async_init_db, init_db

        await _safe_init_core(lambda: init_db(), "auth database init")
        await _safe_init_core(async_init_db, "async database init", timeout=15.0)
    except Exception as e:
        _logger.warning(f"Database init failed (continuing without it): {e}")

    yield

    # Shutdown
    _logger.info("Application shutdown started.")

    # Shutdown telemetry
    try:
        from core.telemetry import shutdown_telemetry

        shutdown_telemetry()
    except Exception as e:
        _logger.info(f"OpenTelemetry shutdown failed: {e}")

    # Shutdown HTTP clients
    await _shutdown_http_clients()

    # Shutdown notification clients
    await _shutdown_notification_clients()

    # Shutdown storage layers
    await _shutdown_storage_layers()

    # Shutdown interface layers
    await _shutdown_interface_layers()

    # Shutdown processing layers
    await _shutdown_processing_layers()

    # Shutdown vulnerability intelligence
    try:
        from core.vulnerability_intelligence import vulnerability_intelligence

        await vulnerability_intelligence.close()
        _logger.info("Vulnerability Intelligence clients closed successfully")
    except Exception as exc:
        _logger.error("Shutdown Vulnerability Intelligence error: %s", exc, exc_info=True)

    _logger.info("Application shutdown completed.")
