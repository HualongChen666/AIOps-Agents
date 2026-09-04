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
from core.middleware.rate_limit_middleware import rate_limit_middleware
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

# Core Engine Modules
# from core.alert_engine import AlertEngine  # noqa: F401
# AlertEngine class does not exist in core.alert_engine
# The module provides alert processing functions and classes like AlertTopologyCorrelation, AutomaticAlertRouter, AlertTrendPredictor
# from core.auto_heal import AutoHealEngine  # noqa: F401
# AutoHealEngine class does not exist in core.auto_heal
# The module provides auto-heal functions like handle_alert, simulate_repair, and classes like RepairScriptLibrary, RiskAssessmentEngine
# from core.collector import Collector  # noqa: F401
# Collector class does not exist in core.collector
# The module provides data collection functions
# from core.db_engine import DatabaseEngine  # noqa: F401
# DatabaseEngine class does not exist in core.db_engine
# from core.linux_collector import LinuxCollector  # noqa: F401
# LinuxCollector class does not exist in core.linux_collector
# from core.linux_repair import LinuxRepair  # noqa: F401
# LinuxRepair class does not exist in core.linux_repair
# from core.log_collector import LogCollector  # noqa: F401
# LogCollector class does not exist in core.log_collector
# from core.metrics_history import MetricsHistory  # noqa: F401
# MetricsHistory class does not exist in core.metrics_history
# from core.repair_engine import RepairEngine  # noqa: F401
# RepairEngine class does not exist in core.repair_engine
# from core.runbook_generator import RunbookGenerator  # noqa: F401
# RunbookGenerator class does not exist in core.runbook_generator
# from core.topology_engine import TopologyEngine  # noqa: F401
# TopologyEngine class does not exist in core.topology_engine
# from core.workflow_engine import WorkflowEngine  # noqa: F401
# WorkflowEngine class does not exist in core.workflow_engine

# AI/Analysis Modules
# from core.ai_interface import AIInterface  # noqa: F401
# AIInterface class does not exist in core.ai_interface
# from core.ai_service import AIService  # noqa: F401
# AIService class does not exist in core.ai_service
# from core.ai_enhancement import AIEnhancement  # noqa: F401
# AIEnhancement class does not exist in core.ai_enhancement
# from core.advanced_ai_capabilities import AdvancedAICapabilities  # noqa: F401
# AdvancedAICapabilities class does not exist in core.advanced_ai_capabilities
# from core.enhanced_ai_capabilities import EnhancedAICapabilities  # noqa: F401
# EnhancedAICapabilities class does not exist in core.enhanced_ai_capabilities
# from core.analysis.l2.langgraph_engine import LangGraphEngine  # noqa: F401
# LangGraphEngine class does not exist in core.analysis.l2.langgraph_engine
# from core.analysis.l2.model_router import ModelRouter  # noqa: F401
# ModelRouter class does not exist in core.analysis.l2.model_router
from core.analysis.l2.rag_engine import RAGEngine  # noqa: F401
# from core.root_cause_intelligence import RootCauseIntelligence  # noqa: F401
# RootCauseIntelligence class does not exist in core.root_cause_intelligence
# from core.enhanced_root_cause_analyzer import EnhancedRootCauseAnalyzer  # noqa: F401
# EnhancedRootCauseAnalyzer class does not exist in core.enhanced_root_cause_analyzer

# Security/Auth Modules
# from core.auth import Auth  # noqa: F401
# Auth class does not exist in core.auth
# from core.auth_service import AuthService  # noqa: F401
# AuthService class does not exist in core.auth_service
# from core.authentication import Authentication  # noqa: F401
# Authentication class does not exist in core.authentication
# from core.auth_interface import AuthInterface  # noqa: F401
# AuthInterface class does not exist in core.auth_interface
# from core.rbac import RBAC  # noqa: F401
# RBAC class does not exist in core.rbac
# from core.fine_rbac import FineRBAC  # noqa: F401
# FineRBAC class does not exist in core.fine_rbac
# from core.abac import ABAC  # noqa: F401
# ABAC class does not exist in core.abac
# from core.mfa_service import MFAService  # noqa: F401
# MFAService class does not exist in core.mfa_service
# from core.crypto import Crypto  # noqa: F401
# Crypto class does not exist in core.crypto
# from core.key_management import KeyManagement  # noqa: F401
# KeyManagement class does not exist in core.key_management
# from core.token_blacklist import TokenBlacklist  # noqa: F401
# TokenBlacklist class does not exist in core.token_blacklist

# Fault Tolerance/Recovery Modules
# from core.error_handler import ErrorHandler  # noqa: F401
# ErrorHandler class does not exist in core.error_handler
# from core.error_handling import ErrorHandling  # noqa: F401
# ErrorHandling class does not exist in core.error_handling
# from core.error_handling_logging import ErrorHandlingLogging  # noqa: F401
# ErrorHandlingLogging class does not exist in core.error_handling_logging
# from core.resilience import Resilience  # noqa: F401
# Resilience class does not exist in core.resilience
# from core.retry_enhanced import RetryEnhanced  # noqa: F401
# RetryEnhanced class does not exist in core.retry_enhanced
# from core.circuit_breaker import CircuitBreaker  # noqa: F401
# CircuitBreaker class does not exist in core.circuit_breaker
# from core.idempotent import Idempotent  # noqa: F401
# Idempotent class does not exist in core.idempotent

# Monitoring/Observability Modules
# from core.anomaly_detection import AnomalyDetection  # noqa: F401
# AnomalyDetection class does not exist in core.anomaly_detection
# from core.anomaly_engine import AnomalyEngine  # noqa: F401
# AnomalyEngine class does not exist in core.anomaly_engine
# from core.health_check import HealthCheck  # noqa: F401
# HealthCheck class does not exist in core.health_check
# from core.heartbeat import Heartbeat  # noqa: F401
# Heartbeat class does not exist in core.heartbeat
# from core.observability_query import ObservabilityQuery  # noqa: F401
# ObservabilityQuery class does not exist in core.observability_query
# from core.observability_schema import ObservabilitySchema  # noqa: F401
# ObservabilitySchema class does not exist in core.observability_schema
# from core.monitoring_system_integrator import MonitoringSystemIntegrator  # noqa: F401
# MonitoringSystemIntegrator class does not exist in core.monitoring_system_integrator
# from core.prometheus_client import PrometheusClient  # noqa: F401
# PrometheusClient class does not exist in core.prometheus_client
# from core.loki_client import LokiClient  # noqa: F401
# LokiClient class does not exist in core.loki_client
# from core.tempo_client import TempoClient  # noqa: F401
# TempoClient class does not exist in core.tempo_client
# from core.elasticsearch_client import ElasticsearchClient  # noqa: F401
# ElasticsearchClient class does not exist in core.elasticsearch_client

# Performance Optimization Modules
# from core.api_response_time_optimizer import APIResponseTimeOptimizer  # noqa: F401
# APIResponseTimeOptimizer class does not exist in core.api_response_time_optimizer
# from core.api_throughput_optimizer import APIThroughputOptimizer  # noqa: F401
# APIThroughputOptimizer class does not exist in core.api_throughput_optimizer
# from core.api_resource_optimizer import APIResourceOptimizer  # noqa: F401
# APIResourceOptimizer class does not exist in core.api_resource_optimizer
# from core.database_cache_optimizer import DatabaseCacheOptimizer  # noqa: F401
# DatabaseCacheOptimizer class does not exist in core.database_cache_optimizer
# from core.database_connection_optimizer import DatabaseConnectionOptimizer  # noqa: F401
# DatabaseConnectionOptimizer class does not exist in core.database_connection_optimizer
# from core.connection_pool_optimization import ConnectionPoolOptimization  # noqa: F401
# ConnectionPoolOptimization class does not exist in core.connection_pool_optimization
# from core.cpu_usage_optimizer import CPUUsageOptimizer  # noqa: F401
# CPUUsageOptimizer class does not exist in core.cpu_usage_optimizer
# from core.memory_usage_optimizer import MemoryUsageOptimizer  # noqa: F401
# MemoryUsageOptimizer class does not exist in core.memory_usage_optimizer
# from core.performance_regression_detector import PerformanceRegressionDetector  # noqa: F401
# PerformanceRegressionDetector class does not exist in core.performance_regression_detector
# from core.performance_data_collector import PerformanceDataCollector  # noqa: F401
# PerformanceDataCollector class does not exist in core.performance_data_collector
# from core.performance_report_generator import PerformanceReportGenerator  # noqa: F401
# PerformanceReportGenerator class does not exist in core.performance_report_generator
# from core.performance_scheduler import PerformanceScheduler  # noqa: F401
# PerformanceScheduler class does not exist in core.performance_scheduler
# from core.performance_tuning import PerformanceTuning  # noqa: F401
# PerformanceTuning class does not exist in core.performance_tuning

# Alert/Notification Modules
# from core.alert_service import AlertService  # noqa: F401
# AlertService class does not exist in core.alert_service
# from core.alert_intelligence import AlertIntelligence  # noqa: F401
# AlertIntelligence class does not exist in core.alert_intelligence (it's AlertIntelligenceEngine)
# from core.alert_rules import AlertRules  # noqa: F401
# AlertRules class does not exist in core.alert_rules
# from core.intelligent_alert_analyzer import IntelligentAlertAnalyzer  # noqa: F401
# IntelligentAlertAnalyzer class does not exist in core.intelligent_alert_analyzer
# from core.oncall_adapter import OncallAdapter  # noqa: F401
# OncallAdapter class does not exist in core.oncall_adapter
# from core.escalation import Escalation  # noqa: F401
# Escalation class does not exist in core.escalation

# Integration/Collaboration Modules
# from core.integration_manager import IntegrationManager  # noqa: F401
# IntegrationManager class does not exist in core.integration_manager
# from core.integration_ecosystem import IntegrationEcosystem  # noqa: F401
# IntegrationEcosystem class does not exist in core.integration_ecosystem
# from core.integration_repository import IntegrationRepository  # noqa: F401
# IntegrationRepository class does not exist in core.integration_repository
# from core.integration_helpers import IntegrationHelpers  # noqa: F401
# IntegrationHelpers class does not exist in core.integration_helpers
# from core.real_integration import RealIntegration  # noqa: F401
# RealIntegration class does not exist in core.real_integration
# from core.collaboration_engine import CollaborationEngine  # noqa: F401
# CollaborationEngine class does not exist in core.collaboration_engine
# from core.team_collaboration_engine import TeamCollaborationEngine  # noqa: F401
# TeamCollaborationEngine class does not exist in core.team_collaboration_engine
from core.integration.l7.collaboration_integration import CollaborationIntegration  # noqa: F401
from core.integration.l7.itSM_integration import ITSMIntegration  # noqa: F401

# Storage/Database Modules
# from core.database import Database  # noqa: F401
# Database class does not exist in core.database
# from core.db_replication import DBReplication  # noqa: F401
# DBReplication class does not exist in core.db_replication
# from core.db_optimization import DBOptimization  # noqa: F401
# DBOptimization class does not exist in core.db_optimization
# from core.database_query_optimizer import DatabaseQueryOptimizer  # noqa: F401
# DatabaseQueryOptimizer class does not exist in core.database_query_optimizer
# from core.query_optimizer import QueryOptimizer  # noqa: F401
# QueryOptimizer class does not exist in core.query_optimizer
# from core.query_optimization import QueryOptimization  # noqa: F401
# QueryOptimization class does not exist in core.query_optimization
# from core.dual_write import DualWrite  # noqa: F401
# DualWrite class does not exist in core.dual_write
# from core.redis_cluster import RedisCluster  # noqa: F401
# RedisCluster class does not exist in core.redis_cluster
# from core.redis_cluster_manager import RedisClusterManager  # noqa: F401
# RedisClusterManager class does not exist in core.redis_cluster_manager
# from core.snapshot_store import SnapshotStore  # noqa: F401
# SnapshotStore class does not exist in core.snapshot_store

# Repository Modules
from core.repositories.alert_repository import AlertRepository  # noqa: F401
from core.repositories.database_monitoring_repository import DatabaseMonitoringRepository  # noqa: F401
from core.repositories.frontend_repository import FrontendRepository  # noqa: F401
from core.repositories.monitoring_repository import MonitoringRepository  # noqa: F401
from core.repositories.security_repository import SecurityRepository  # noqa: F401
from core.repositories.user_repository import UserRepository  # noqa: F401

# Alert Providers
# from core.alert_providers.base import BaseAlertProvider  # noqa: F401
# BaseAlertProvider class does not exist in core.alert_providers.base (it's AlertProvider)
# from core.alert_providers.cloudwatch import CloudWatchProvider  # noqa: F401
# CloudWatchProvider class does not exist in core.alert_providers.cloudwatch
# from core.alert_providers.datadog import DatadogProvider  # noqa: F401
# DatadogProvider class does not exist in core.alert_providers.datadog
# from core.alert_providers.grafana import GrafanaProvider  # noqa: F401
# GrafanaProvider class does not exist in core.alert_providers.grafana
# from core.alert_providers.pagerduty import PagerDutyProvider  # noqa: F401
# PagerDutyProvider class does not exist in core.alert_providers.pagerduty
# from core.alert_providers.prometheus import PrometheusProvider  # noqa: F401
# PrometheusProvider class does not exist in core.alert_providers.prometheus
# from core.alert_providers.zabbix import ZabbixProvider  # noqa: F401
# ZabbixProvider class does not exist in core.alert_providers.zabbix

# Agent Framework
# from core.agent.behavior_monitor import BehaviorMonitor  # noqa: F401
# BehaviorMonitor class does not exist in core.agent.behavior_monitor
# from core.agent.coding_subagent import CodingSubagent  # noqa: F401
# CodingSubagent class does not exist in core.agent.coding_subagent (it's CodingSubAgent)
# from core.agent.coding_tools import CodingTools  # noqa: F401
# CodingTools class does not exist in core.agent.coding_tools
# from core.agent.executor import Executor  # noqa: F401
# Executor class does not exist in core.agent.executor
# from core.agent.memory_bridge import MemoryBridge  # noqa: F401
# MemoryBridge class does not exist in core.agent.memory_bridge
# from core.agent.observability_client import ObservabilityClient  # noqa: F401
# ObservabilityClient class does not exist in core.agent.observability_client
# from core.agent.planner import Planner  # noqa: F401
# Planner class does not exist in core.agent.planner
# from core.agent.state import AgentState  # noqa: F401
# AgentState class does not exist in core.agent.state
# from core.agent.subagent import Subagent  # noqa: F401
# Subagent class does not exist in core.agent.subagent
# from core.agent.tools import AgentTools  # noqa: F401
# AgentTools class does not exist in core.agent.tools

# AI Submodules
# from core.ai.token_budget import TokenBudget  # noqa: F401
# TokenBudget class does not exist in core.ai.token_budget
# from core.ai.langgraph.dsl import LangGraphDSL  # noqa: F401
# LangGraphDSL class does not exist in core.ai.langgraph.dsl
# from core.ai.langgraph.executor import LangGraphExecutor  # noqa: F401
# LangGraphExecutor class does not exist in core.ai.langgraph.executor
# from core.ai.langgraph.nodes import LangGraphNodes  # noqa: F401
# LangGraphNodes class does not exist in core.ai.langgraph.nodes
# from core.ai.langgraph.visualizer import LangGraphVisualizer  # noqa: F401
# LangGraphVisualizer class does not exist in core.ai.langgraph.visualizer
# from core.ai.langgraph.workflow import LangGraphWorkflow  # noqa: F401
# LangGraphWorkflow class does not exist in core.ai.langgraph.workflow
# from core.ai.langgraph._core import LangGraphCore  # noqa: F401
# LangGraphCore class does not exist in core.ai.langgraph._core
from core.ai.llm_router.capability_evaluator import CapabilityEvaluator  # noqa: F401
from core.ai.llm_router.cost_optimizer import CostOptimizer  # noqa: F401
# from core.ai.llm_router.enhanced_router import EnhancedRouter  # noqa: F401
# EnhancedRouter class does not exist in core.ai.llm_router.enhanced_router (it's EnhancedLLMRouter)
from core.ai.llm_router.load_balancer import LoadBalancer  # noqa: F401
# from core.ai.rag.fusion import RAGFusion  # noqa: F401
# RAGFusion class does not exist in core.ai.rag.fusion
from core.ai.rag.knowledge_base import KnowledgeBase  # noqa: F401
from core.ai.rag.reranker import Reranker  # noqa: F401
from core.ai.rag.retriever import Retriever  # noqa: F401
# from core.ai.rag.vectorizer import Vectorizer  # noqa: F401
# Vectorizer class does not exist in core.ai.rag.vectorizer

# Base Modules
from core.base.analyzer import BaseAnalyzer  # noqa: F401
from core.base.collector import BaseCollector  # noqa: F401
from core.base.executor import BaseExecutor  # noqa: F401
from core.base.storage import BaseStorage  # noqa: F401

# Causal Analysis Modules
# from core.causal.algorithms import CausalAlgorithms  # noqa: F401
# CausalAlgorithms class does not exist in core.causal.algorithms
from core.causal.graph import CausalGraph  # noqa: F401
# from core.causal.impact import CausalImpact  # noqa: F401
# CausalImpact class does not exist in core.causal.impact
# from core.causal.inference import CausalInference  # noqa: F401
# CausalInference class does not exist in core.causal.inference (it's RootCauseInference)
# from core.causal.prediction import CausalPrediction  # noqa: F401
# CausalPrediction class does not exist in core.causal.prediction (it's CausalPredictor)
# from core.causal.preprocessing import CausalPreprocessing  # noqa: F401
# CausalPreprocessing class does not exist in core.causal.preprocessing

# Error Codes
# from core.error_codes.definitions import ErrorCodesDefinitions  # noqa: F401
# ErrorCodesDefinitions class does not exist in core.error_codes.definitions
# from core.error_codes.manager import ErrorCodesManager  # noqa: F401
# ErrorCodesManager class does not exist in core.error_codes.manager (it's ErrorCodeManager)

# Error Logging
# from core.error_logging.alerting import ErrorLoggingAlerting  # noqa: F401
# ErrorLoggingAlerting class does not exist in core.error_logging.alerting
# from core.error_logging.fastapi_handlers import FastAPIHandlers  # noqa: F401
# FastAPIHandlers class does not exist in core.error_logging.fastapi_handlers
# from core.error_logging.handler import ErrorLoggingHandler  # noqa: F401
# ErrorLoggingHandler class does not exist in core.error_logging.handler (it's ErrorLogHandler)
# from core.error_logging.logger import ErrorLoggingLogger  # noqa: F401
# ErrorLoggingLogger class does not exist in core.error_logging.logger

# Exceptions
# from core.exceptions.base import BaseExceptions  # noqa: F401
# from core.exceptions.business import BusinessExceptions  # noqa: F401
# from core.exceptions.critical import CriticalExceptions  # noqa: F401
# from core.exceptions.security import SecurityExceptions  # noqa: F401
# from core.exceptions.system import SystemExceptions  # noqa: F401
# from core.exceptions.third_party import ThirdPartyExceptions  # noqa: F401

# HITL Modules
# from core.hitl.approval import HITLApproval  # noqa: F401
# from core.hitl.conditional import HITLConditional  # noqa: F401
# from core.hitl.history import HITLHistory  # noqa: F401
# from core.hitl.multi_level import HITLMultiLevel  # noqa: F401
# from core.hitl.notification import HITLNotification  # noqa: F401
# from core.hitl.timeout import HITLTimeout  # noqa: F401

# Interface Modules
# from core.interface.graphql.auth import GraphQLAuth  # noqa: F401
# from core.interface.graphql.dataloader import GraphQLDataloader  # noqa: F401
# from core.interface.graphql.resolvers import GraphQLResolvers  # noqa: F401
# from core.interface.graphql.schema import GraphQLSchema  # noqa: F401
# from core.interface.graphql.subscription import GraphQLSubscription  # noqa: F401
# from core.interface.grpc.client import GRPCClient  # noqa: F401
# from core.interface.grpc.interceptor import GRPCInterceptor  # noqa: F401
# from core.interface.grpc.server import GRPCServer  # noqa: F401
# from core.interface.l5.graphql_interface import GraphQLInterface  # noqa: F401
# from core.interface.l5.mcp_interface import MCPInterface  # noqa: F401
# from core.interface.mcp.client import MCPClient  # noqa: F401
# from core.interface.mcp.context import MCPContext  # noqa: F401
# from core.interface.mcp.protocol import MCPProtocol  # noqa: F401
# from core.interface.mcp.server import MCPServer  # noqa: F401
# from core.interface.mcp.tools import MCPTools  # noqa: F401

# Logging Modules
# from core.logging.analysis.log_alerting import LogAlerting  # noqa: F401
# from core.logging.analysis.log_analyzer import LogAnalyzer  # noqa: F401
# from core.logging.context.context_manager import LoggingContextManager  # noqa: F401
# from core.logging.level.filter_strategy import FilterStrategy  # noqa: F401
# from core.logging.level.level_manager import LevelManager  # noqa: F401
# from core.logging.level.routing_strategy import RoutingStrategy  # noqa: F401
# from core.logging.level.sampling_strategy import SamplingStrategy  # noqa: F401

# Middleware
# from core.middleware.auth_middleware import AuthMiddleware  # noqa: F401

# Priority Modules
# from core.priority.assessor import PriorityAssessor  # noqa: F401
# from core.priority.dynamic import PriorityDynamic  # noqa: F401
# from core.priority.ranker import PriorityRanker  # noqa: F401
# from core.priority.resource_allocator import PriorityResourceAllocator  # noqa: F401
# from core.priority.sla_aware import PrioritySLAAware  # noqa: F401

# Processing Modules
# from core.processing.l3.causal_graph import CausalGraphProcessor  # noqa: F401
# from core.processing.l3.workflow_engine import WorkflowEngineProcessor  # noqa: F401

# Security Modules
# from core.security.subprocess_runner import SecuritySubprocessRunner  # noqa: F401

# Storage Modules
# from core.storage.l4.loki import LokiStorage  # noqa: F401
# from core.storage.l4.retry import RetryStorage  # noqa: F401
# from core.storage.l4.storage_manager import StorageManager  # noqa: F401
# from core.storage.l4.tempo import TempoStorage  # noqa: F401
# from core.storage.l4.victoriametrics import VictoriaMetricsStorage  # noqa: F401

# Telemetry Modules
# from core.telemetry.fastapi import FastAPITelemetry  # noqa: F401

# Workflow Modules
# from core.workflow.engine.dag import WorkflowDAG  # noqa: F401
# from core.workflow.engine.dsl import WorkflowDSL  # noqa: F401
# from core.workflow.engine.executor import WorkflowExecutor  # noqa: F401
# from core.workflow.engine.state_machine import WorkflowStateMachine  # noqa: F401

# Modules imports
# from modules.analyze.anomaly.data_preprocessing import DataPreprocessor  # noqa: F401
# from modules.analyze.anomaly.ensemble import AnomalyEnsemble  # noqa: F401
# from modules.analyze.anomaly.isolation_forest import IsolationForestDetector  # noqa: F401
# from modules.analyze.anomaly.prophet_model import ProphetModel  # noqa: F401
# from modules.analyze.anomaly.train_transformer import TransformerTrainer  # noqa: F401
# from modules.analyze.anomaly.transformer_model import TransformerModel  # noqa: F401
# from modules.analyze.anomaly.transformer_service import TransformerService  # noqa: F401
# from modules.analyze.capacity.forecast import CapacityForecaster  # noqa: F401
# from modules.analyze.cost.forecast import CostForecaster  # noqa: F401
# from modules.analyze.root_cause.causal_graph_builder import CausalGraphBuilder  # noqa: F401
# from modules.analyze.root_cause.causal_inference import CausalInference  # noqa: F401
# from modules.analyze.root_cause.causal_service import CausalService  # noqa: F401
# from modules.analyze.root_cause.gnn import GNNModel  # noqa: F401
# from modules.analyze.root_cause.graph_builder import GraphBuilder  # noqa: F401
# from modules.analyze.root_cause.inference import InferenceEngine  # noqa: F401
# from modules.analyze.runbook.generator import RunbookGenerator  # noqa: F401
# from modules.analyze.runbook.vector_store import RunbookVectorStore  # noqa: F401
# from modules.apm.code_profiler import CodeProfiler  # noqa: F401
# from modules.apm.dependency_analyzer import DependencyAnalyzer  # noqa: F401
# from modules.compliance.gdpr_compliance import GDPRCompliance  # noqa: F401
# from modules.compliance.soc2_compliance import SOC2Compliance  # noqa: F401
# from modules.execute.autoscaler.custom_hpa import CustomHPA  # noqa: F401
# from modules.execute.autoscaler.custom_hpa_controller import CustomHPAController  # noqa: F401
# from modules.execute.auto_heal.operator import AutoHealOperator  # noqa: F401
# from modules.execute.auto_heal.playbook_manager import PlaybookManager  # noqa: F401
# from modules.execute.saga.coordinator import SagaCoordinator  # noqa: F401
# from modules.execute.saga.participants import SagaParticipants  # noqa: F401
# from modules.execute.scheduler.temporal_worker import TemporalWorker  # noqa: F401
# from modules.high_availability.multi_region import MultiRegion  # noqa: F401
# from modules.high_availability.self_healing import SelfHealing  # noqa: F401
# from modules.multi_tenant.tenant_isolation import TenantIsolation  # noqa: F401
# from modules.multi_tenant.tenant_manager import TenantManager  # noqa: F401
# from modules.observability.auto_discovery import AutoDiscovery  # noqa: F401
# from modules.observability.smart_alerting import SmartAlerting  # noqa: F401
# from modules.observability.smart_analysis import SmartAnalysis  # noqa: F401
# from modules.optimization.cache_optimizer import CacheOptimizer  # noqa: F401
# from modules.optimization.concurrency_optimizer import ConcurrencyOptimizer  # noqa: F401
# from modules.optimization.query_optimizer import QueryOptimizer  # noqa: F401
# from modules.optimization.resource_optimizer import ResourceOptimizer  # noqa: F401
# from modules.optimization.storage_optimizer import StorageOptimizer  # noqa: F401
# from modules.rum.data_collector import RUMDataCollector  # noqa: F401
# from modules.rum.sdk import RUMSDK  # noqa: F401
# from modules.storage.clickhouse.storage import ClickHouseStorage  # noqa: F401
# from modules.storage.postgres.storage import PostgresStorage  # noqa: F401

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
from fastapi.responses import JSONResponse
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
from api.assets_advanced_router import router as assets_advanced_router
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
from api.capacity_advanced_router import router as capacity_advanced_router
from api.change_management_router import router as change_management_router
from api.change_advanced_router import router as change_advanced_router
from api.collaboration_advanced_router import router as collaboration_advanced_router
from api.collaboration_router import router as collaboration_router
from api.compliance_audit_router import router as compliance_audit_router
from api.cost_advanced_router import router as cost_advanced_router
from api.cost_router import router as cost_router
from api.cost_management_router import router as cost_management_router
from api.monitoring_config_router import router as monitoring_config_router
from api.monitoring_advanced_router import router as monitoring_advanced_router
from api.database_monitoring_router import router as database_monitoring_router
from api.performance_optimization_router import router as performance_optimization_router
from api.performance_router import router as performance_router
from api.guard_router import router as guard_router
from api.guard_router import security_router as security_router
from api.security_advanced_router import router as security_advanced_router
from api.health_router import router as health_router
from api.hitl_approval_router import router as hitl_approval_router
from api.incident_management_router import router as incident_management_router
from api.linux_router import router as linux_router
from api.macos_router import router as macos_router
from api.maturity_router import router as maturity_router
from api.repair_advanced_router import router as repair_advanced_router
from api.repair_router_append import router as repair_router_append
from api.repair_scripts_router import router as repair_scripts_router
from api.approvals_router import router as approvals_router
from api.settings_router import router as settings_router
from api.slack_router import router as slack_router
from api.slo_router import router as slo_router
from api.slo_advanced_router import router as slo_advanced_router
from api.sse_router import router as sse_router
from api.stats_router import router as stats_router
from api.team_collaboration_router import router as team_collaboration_router
from api.integration_providers_router import router as integration_providers_router
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
from api.user_router import router as user_router
from api.users_advanced_router import router as users_advanced_router
from api.users_unified_router import router as users_unified_router
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
    RELEASE_MANAGEMENT_ENABLED,
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
topology_simple_router: Any = None
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
        from api.knowledge_base_router import router as knowledge_base_router
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
        from api.topology_simple_router import router as topology_simple_router
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
    if RELEASE_MANAGEMENT_ENABLED:
        from api.release_management_router import router as release_management_router
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
# from core.concurrency_control import ConcurrencyController  # noqa: F401
# ConcurrencyController class does not exist in core.concurrency_control
from core.config_validation import setup_config_validation  # noqa: F401
from core.data_lifecycle_operations import archive_alerts, archive_metrics  # noqa: F401
from core.db_query_optimization import optimize_database_queries  # noqa: F401
from core.dependency_injection import di_container, setup_dependency_injection  # noqa: F401
from core.enhanced_caching import setup_enhanced_caching  # noqa: F401
from core.environment_config import setup_environment_configuration  # noqa: F401
# from core.rate_limiting import ENDPOINT_LIMITS  # noqa: F401
# ENDPOINT_LIMITS does not exist in core.rate_limiting
from core.security_config import setup_enterprise_security  # noqa: F401
from core.security_middleware import (  # noqa: F401
    mfa_manager,
    password_policy,
    rate_limiter,
    security_headers,
    tls_enforcer,
)
# from core.smart_cache_strategy import SmartCacheStrategy  # noqa: F401
# SmartCacheStrategy class does not exist in core.smart_cache_strategy
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

# Release Management Router (conditionally loaded)
release_management_router: Any = None

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

# Static files are now served by Next.js frontend (port 3000)
# API requests are proxied from Next.js to FastAPI (port 8000)
# See frontend/next.config.js for proxy configuration


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirect to frontend"""
    return JSONResponse({
        "message": "AIOps Agent API Server",
        "frontend": "http://localhost:3000",
        "api_docs": "/docs",
        "health": "/api/v1/health/ping"
    })


app.add_exception_handler(
    RateLimitExceeded, _rate_limit_exception_handler  # type: ignore[arg-type]
)

# Apply API response middleware for unified format
setup_api_response_middleware(app)

# Apply rate limit middleware
app.middleware("http")(rate_limit_middleware)

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
    # Check if TEST_MODE is enabled
    if os.getenv("TEST_MODE") == "true":
        # In test mode, skip all security checks
        return await call_next(request)
    
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
    monitoring_advanced_router,
    database_monitoring_router,
    performance_optimization_router,
    performance_router,
    health_router,
    hitl_approval_router,
    incident_management_router,
    linux_router,
    macos_router,
    docker_router,
    hardware_log_router,
    repair_advanced_router,
    repair_router_append,
    repair_scripts_router,
    approvals_router,
    unified_repair_router,
    unified_repair_advanced_router,
    unified_repair_advanced_router_v1,
    windows_repair_router,
    guard_router,
    security_router,
    security_advanced_router,
    api_performance_router,
    cost_router,
    cost_advanced_router,
    cost_management_router,
    auth_router,
    settings_router,
    user_router,
    users_advanced_router,
    users_unified_router,
    assets_router,
    assets_advanced_router,
    sso_router,
    slack_router,
    teams_router,
    vulnerability_router,
    websocket_router,
    sse_router,
    stats_router,
    capacity_router,
    capacity_advanced_router,
    anomaly_router,
    slo_router,
    slo_advanced_router,
    chaos_simple_router,
    tenant_router,
    tenant_advanced_router,
    business_impact_router,
    business_impact_advanced_router,
    change_management_router,
    change_advanced_router,
    maturity_router,
    collaboration_router,
    collaboration_advanced_router,
    team_collaboration_router,
    integration_providers_router,
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
    (knowledge_base_router, RAG_ENABLED),
    # Observability & Topology Pack
    (metrics_router, METRICS_ENABLED),
    (topology_router, TOPOLOGY_ENABLED),
    (topology_simple_router, TOPOLOGY_ENABLED),
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
    (release_management_router, RELEASE_MANAGEMENT_ENABLED),
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
