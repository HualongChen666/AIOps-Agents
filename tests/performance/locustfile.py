# -*- coding: utf-8 -*-
"""
AIOps Agent API Performance Tests
基于Locust的API性能测试框架
"""

import logging
import random
from typing import Any, Dict

from locust import HttpUser, between, events, task
from locust.runners import MasterRunner

logger = logging.getLogger(__name__)


class AIOpsUser(HttpUser):
    """
    AIOps API性能测试用户类
    模拟真实用户行为，覆盖核心API端点
    """

    wait_time = between(1, 3)
    weight = 1

    def on_start(self):
        """用户启动时的初始化操作"""
        logger.info(f"User {self} started")

    def on_stop(self):
        """用户停止时的清理操作"""
        logger.info(f"User {self} stopped")

    # ==================== 健康检查端点 ====================

    @task(5)
    def health_check(self):
        """健康检查 - 高频访问"""
        with self.client.get("/health", catch_response=True, name="/health") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    # ==================== 告警相关端点 ====================

    @task(4)
    def get_alerts(self):
        """获取告警列表"""
        with self.client.get(
            "/api/v1/alerts", catch_response=True, name="/api/v1/alerts"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get alerts failed: {response.status_code}")

    @task(2)
    def get_alert_detail(self):
        """获取告警详情"""
        alert_id = random.randint(1, 1000)
        with self.client.get(
            f"/api/v1/alerts/{alert_id}", catch_response=True, name="/api/v1/alerts/{id}"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Get alert detail failed: {response.status_code}")

    @task(1)
    def create_alert(self):
        """创建告警"""
        alert_data = {
            "title": f"Test Alert {random.randint(1, 10000)}",
            "severity": random.choice(["info", "warning", "error", "critical"]),
            "description": "Performance test alert",
        }
        with self.client.post(
            "/api/v1/alerts", json=alert_data, catch_response=True, name="/api/v1/alerts [POST]"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Create alert failed: {response.status_code}")

    # ==================== AI推理端点 ====================

    @task(2)
    def ai_inference(self):
        """AI推理"""
        prompt_data = {
            "prompt": "What is the status of the system?",
            "model": "gpt-3.5-turbo",
            "max_tokens": 100,
        }
        with self.client.post(
            "/api/v1/ai/inference",
            json=prompt_data,
            catch_response=True,
            name="/api/v1/ai/inference",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"AI inference failed: {response.status_code}")

    @task(1)
    def rag_retrieve(self):
        """RAG检索"""
        query_data = {"query": "How to fix database connection error?", "top_k": 5}
        with self.client.post(
            "/api/v1/ai/rag/retrieve",
            json=query_data,
            catch_response=True,
            name="/api/v1/ai/rag/retrieve",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"RAG retrieve failed: {response.status_code}")

    # ==================== 自动修复端点 ====================

    @task(1)
    def autoheal_execute(self):
        """自动修复执行"""
        heal_data = {"issue_type": "database_connection", "target": "primary_db"}
        with self.client.post(
            "/api/v1/autoheal/execute",
            json=heal_data,
            catch_response=True,
            name="/api/v1/autoheal/execute",
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Autoheal execute failed: {response.status_code}")

    # ==================== 拓扑相关端点 ====================

    @task(3)
    def get_topology(self):
        """获取拓扑"""
        with self.client.get(
            "/api/v1/topology", catch_response=True, name="/api/v1/topology"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get topology failed: {response.status_code}")

    @task(1)
    def get_topology_node(self):
        """获取拓扑节点"""
        node_id = random.randint(1, 100)
        with self.client.get(
            f"/api/v1/topology/nodes/{node_id}",
            catch_response=True,
            name="/api/v1/topology/nodes/{id}",
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Get topology node failed: {response.status_code}")

    # ==================== 用户认证端点 ====================

    @task(2)
    def user_login(self):
        """用户登录"""
        login_data = {
            "username": f"test_user_{random.randint(1, 100)}",
            "password": "test_password",
        }
        with self.client.post(
            "/api/v1/auth/login", json=login_data, catch_response=True, name="/api/v1/auth/login"
        ) as response:
            if response.status_code in [200, 401]:
                response.success()
            else:
                response.failure(f"User login failed: {response.status_code}")

    # ==================== 指标相关端点 ====================

    @task(4)
    def get_metrics_summary(self):
        """获取指标摘要"""
        with self.client.get(
            "/api/v1/metrics/summary", catch_response=True, name="/api/v1/metrics/summary"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get metrics summary failed: {response.status_code}")

    @task(2)
    def get_metrics_detail(self):
        """获取指标详情"""
        metric_name = random.choice(["cpu_usage", "memory_usage", "disk_usage", "network_io"])
        with self.client.get(
            f"/api/v1/metrics/{metric_name}", catch_response=True, name="/api/v1/metrics/{name}"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Get metrics detail failed: {response.status_code}")

    # ==================== 日志相关端点 ====================

    @task(2)
    def get_logs(self):
        """获取日志"""
        params = {"limit": 100, "offset": 0, "level": random.choice(["INFO", "WARNING", "ERROR"])}
        with self.client.get(
            "/api/v1/logs", params=params, catch_response=True, name="/api/v1/logs"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get logs failed: {response.status_code}")

    # ==================== 修复相关端点 ====================

    @task(1)
    def get_repairs(self):
        """获取修复列表"""
        with self.client.get(
            "/api/v1/repairs", catch_response=True, name="/api/v1/repairs"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get repairs failed: {response.status_code}")

    @task(1)
    def execute_repair(self):
        """执行修复"""
        repair_data = {"repair_type": "restart_service", "target": "api_service"}
        with self.client.post(
            "/api/v1/repairs/execute",
            json=repair_data,
            catch_response=True,
            name="/api/v1/repairs/execute",
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Execute repair failed: {response.status_code}")

    # ==================== 根因分析端点 ====================

    @task(1)
    def analyze_root_cause(self):
        """根因分析"""
        analysis_data = {"alert_id": random.randint(1, 1000), "time_range": "1h"}
        with self.client.post(
            "/api/v1/root-cause/analyze",
            json=analysis_data,
            catch_response=True,
            name="/api/v1/root-cause/analyze",
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Root cause analysis failed: {response.status_code}")

    # ==================== 工作流端点 ====================

    @task(1)
    def get_workflows(self):
        """获取工作流列表"""
        with self.client.get(
            "/api/v1/workflows", catch_response=True, name="/api/v1/workflows"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get workflows failed: {response.status_code}")

    @task(1)
    def execute_workflow(self):
        """执行工作流"""
        workflow_data = {"workflow_id": f"workflow_{random.randint(1, 10)}", "parameters": {}}
        with self.client.post(
            "/api/v1/workflows/execute",
            json=workflow_data,
            catch_response=True,
            name="/api/v1/workflows/execute",
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Execute workflow failed: {response.status_code}")

    # ==================== 系统资源端点 ====================

    @task(2)
    def get_system_resources(self):
        """获取系统资源"""
        with self.client.get(
            "/api/v1/system/resources", catch_response=True, name="/api/v1/system/resources"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get system resources failed: {response.status_code}")

    # ==================== 服务发现端点 ====================

    @task(1)
    def discover_services(self):
        """服务发现"""
        with self.client.get(
            "/api/v1/service-discovery", catch_response=True, name="/api/v1/service-discovery"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Service discovery failed: {response.status_code}")

    # ==================== 监控端点 ====================

    @task(2)
    def get_monitoring_status(self):
        """获取监控状态"""
        with self.client.get(
            "/api/v1/monitoring/status", catch_response=True, name="/api/v1/monitoring/status"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get monitoring status failed: {response.status_code}")

    # ==================== 通知端点 ====================

    @task(1)
    def send_notification(self):
        """发送通知"""
        notification_data = {
            "channel": "slack",
            "message": "Performance test notification",
            "severity": "info",
        }
        with self.client.post(
            "/api/v1/notify/send",
            json=notification_data,
            catch_response=True,
            name="/api/v1/notify/send",
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Send notification failed: {response.status_code}")

    # ==================== 插件端点 ====================

    @task(1)
    def get_plugins(self):
        """获取插件列表"""
        with self.client.get(
            "/api/v1/plugins", catch_response=True, name="/api/v1/plugins"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get plugins failed: {response.status_code}")

    # ==================== 测试覆盖端点 ====================

    @task(1)
    def get_test_coverage(self):
        """获取测试覆盖率"""
        with self.client.get(
            "/api/v1/test-coverage", catch_response=True, name="/api/v1/test-coverage"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get test coverage failed: {response.status_code}")

    # ==================== API性能端点 ====================

    @task(1)
    def get_api_performance(self):
        """获取API性能"""
        with self.client.get(
            "/api/v1/api-performance", catch_response=True, name="/api/v1/api-performance"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get API performance failed: {response.status_code}")

    # ==================== APM端点 ====================

    @task(1)
    def get_apm_metrics(self):
        """获取APM指标"""
        with self.client.get(
            "/api/v1/apm/metrics", catch_response=True, name="/api/v1/apm/metrics"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get APM metrics failed: {response.status_code}")

    @task(1)
    def get_apm_traces(self):
        """获取APM追踪"""
        with self.client.get(
            "/api/v1/apm/traces", catch_response=True, name="/api/v1/apm/traces"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get APM traces failed: {response.status_code}")

    # ==================== 审计端点 ====================

    @task(1)
    def get_audit_logs(self):
        """获取审计日志"""
        with self.client.get(
            "/api/v1/audit/logs", catch_response=True, name="/api/v1/audit/logs"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get audit logs failed: {response.status_code}")

    # ==================== 混沌工程端点 ====================

    @task(1)
    def get_chaos_experiments(self):
        """获取混沌实验"""
        with self.client.get(
            "/api/v1/chaos/experiments", catch_response=True, name="/api/v1/chaos/experiments"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get chaos experiments failed: {response.status_code}")

    # ==================== 云端端点 ====================

    @task(1)
    def get_cloud_resources(self):
        """获取云端资源"""
        with self.client.get(
            "/api/v1/cloud/resources", catch_response=True, name="/api/v1/cloud/resources"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get cloud resources failed: {response.status_code}")

    # ==================== 成本端点 ====================

    @task(1)
    def get_cost_analysis(self):
        """获取成本分析"""
        with self.client.get(
            "/api/v1/cost/analysis", catch_response=True, name="/api/v1/cost/analysis"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get cost analysis failed: {response.status_code}")

    # ==================== 数据库优化端点 ====================

    @task(1)
    def get_db_optimization(self):
        """获取数据库优化建议"""
        with self.client.get(
            "/api/v1/database-optimization",
            catch_response=True,
            name="/api/v1/database-optimization",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get DB optimization failed: {response.status_code}")

    # ==================== 文档生成端点 ====================

    @task(1)
    def generate_docs(self):
        """生成文档"""
        with self.client.post(
            "/api/v1/docs/generate",
            json={"format": "markdown"},
            catch_response=True,
            name="/api/v1/docs/generate",
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Generate docs failed: {response.status_code}")

    # ==================== Docker端点 ====================

    @task(1)
    def get_docker_containers(self):
        """获取Docker容器"""
        with self.client.get(
            "/api/v1/docker/containers", catch_response=True, name="/api/v1/docker/containers"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get Docker containers failed: {response.status_code}")

    # ==================== 企业端点 ====================

    @task(1)
    def get_enterprise_settings(self):
        """获取企业设置"""
        with self.client.get(
            "/api/v1/enterprise/settings", catch_response=True, name="/api/v1/enterprise/settings"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get enterprise settings failed: {response.status_code}")

    # ==================== GraphQL端点 ====================

    @task(1)
    def graphql_query(self):
        """GraphQL查询"""
        query = "{ __schema { types { name } } }"
        with self.client.post(
            "/api/v1/graphql", json={"query": query}, catch_response=True, name="/api/v1/graphql"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"GraphQL query failed: {response.status_code}")

    # ==================== gRPC端点 ====================

    @task(1)
    def get_grpc_services(self):
        """获取gRPC服务"""
        with self.client.get(
            "/api/v1/grpc/services", catch_response=True, name="/api/v1/grpc/services"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get gRPC services failed: {response.status_code}")

    # ==================== 守护端点 ====================

    @task(1)
    def get_guard_status(self):
        """获取守护状态"""
        with self.client.get(
            "/api/v1/guard/status", catch_response=True, name="/api/v1/guard/status"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get guard status failed: {response.status_code}")

    # ==================== HITL端点 ====================

    @task(1)
    def get_hitl_requests(self):
        """获取HITL请求"""
        with self.client.get(
            "/api/v1/hitl/requests", catch_response=True, name="/api/v1/hitl/requests"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get HITL requests failed: {response.status_code}")

    # ==================== 国际化端点 ====================

    @task(1)
    def get_i18n_messages(self):
        """获取国际化消息"""
        lang = random.choice(["en", "zh"])
        with self.client.get(
            f"/api/v1/i18n/messages?lang={lang}", catch_response=True, name="/api/v1/i18n/messages"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get i18n messages failed: {response.status_code}")

    # ==================== 基础设施端点 ====================

    @task(1)
    def get_infrastructure_status(self):
        """获取基础设施状态"""
        with self.client.get(
            "/api/v1/infrastructure/status",
            catch_response=True,
            name="/api/v1/infrastructure/status",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get infrastructure status failed: {response.status_code}")

    # ==================== 集成端点 ====================

    @task(1)
    def get_integrations(self):
        """获取集成列表"""
        with self.client.get(
            "/api/v1/integrations", catch_response=True, name="/api/v1/integrations"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get integrations failed: {response.status_code}")

    # ==================== ITSM端点 ====================

    @task(1)
    def get_itsm_tickets(self):
        """获取ITSM工单"""
        with self.client.get(
            "/api/v1/itsm/tickets", catch_response=True, name="/api/v1/itsm/tickets"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get ITSM tickets failed: {response.status_code}")

    # ==================== Kubernetes端点 ====================

    @task(1)
    def get_k8s_pods(self):
        """获取K8s Pod"""
        with self.client.get(
            "/api/v1/k8s/pods", catch_response=True, name="/api/v1/k8s/pods"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get K8s pods failed: {response.status_code}")

    # ==================== Linux端点 ====================

    @task(1)
    def get_linux_metrics(self):
        """获取Linux指标"""
        with self.client.get(
            "/api/v1/linux/metrics", catch_response=True, name="/api/v1/linux/metrics"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get Linux metrics failed: {response.status_code}")

    # ==================== 日志路由端点 ====================

    @task(1)
    def get_log_streams(self):
        """获取日志流"""
        with self.client.get(
            "/api/v1/log/streams", catch_response=True, name="/api/v1/log/streams"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get log streams failed: {response.status_code}")

    # ==================== MCP端点 ====================

    @task(1)
    def get_mcp_status(self):
        """获取MCP状态"""
        with self.client.get(
            "/api/v1/mcp/status", catch_response=True, name="/api/v1/mcp/status"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get MCP status failed: {response.status_code}")

    # ==================== 优先级端点 ====================

    @task(1)
    def get_priority_rules(self):
        """获取优先级规则"""
        with self.client.get(
            "/api/v1/priority/rules", catch_response=True, name="/api/v1/priority/rules"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get priority rules failed: {response.status_code}")

    # ==================== Qdrant端点 ====================

    @task(1)
    def get_qdrant_collections(self):
        """获取Qdrant集合"""
        with self.client.get(
            "/api/v1/qdrant/collections", catch_response=True, name="/api/v1/qdrant/collections"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get Qdrant collections failed: {response.status_code}")

    # ==================== RAG历史端点 ====================

    @task(1)
    def get_rag_history(self):
        """获取RAG历史"""
        with self.client.get(
            "/api/v1/rag/history", catch_response=True, name="/api/v1/rag/history"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get RAG history failed: {response.status_code}")

    # ==================== 修复脚本端点 ====================

    @task(1)
    def get_repair_scripts(self):
        """获取修复脚本"""
        with self.client.get(
            "/api/v1/repair-scripts", catch_response=True, name="/api/v1/repair-scripts"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get repair scripts failed: {response.status_code}")

    # ==================== 服务网格端点 ====================

    @task(1)
    def get_service_mesh_status(self):
        """获取服务网格状态"""
        with self.client.get(
            "/api/v1/service-mesh/status", catch_response=True, name="/api/v1/service-mesh/status"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get service mesh status failed: {response.status_code}")

    # ==================== Slack端点 ====================

    @task(1)
    def get_slack_channels(self):
        """获取Slack频道"""
        with self.client.get(
            "/api/v1/slack/channels", catch_response=True, name="/api/v1/slack/channels"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get Slack channels failed: {response.status_code}")

    # ==================== 统计端点 ====================

    @task(1)
    def get_stats_summary(self):
        """获取统计摘要"""
        with self.client.get(
            "/api/v1/stats/summary", catch_response=True, name="/api/v1/stats/summary"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get stats summary failed: {response.status_code}")

    # ==================== 测试自动化端点 ====================

    @task(1)
    def get_test_automation_status(self):
        """获取测试自动化状态"""
        with self.client.get(
            "/api/v1/test-automation/status",
            catch_response=True,
            name="/api/v1/test-automation/status",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get test automation status failed: {response.status_code}")

    # ==================== 测试框架端点 ====================

    @task(1)
    def get_test_framework_config(self):
        """获取测试框架配置"""
        with self.client.get(
            "/api/v1/test-framework/config",
            catch_response=True,
            name="/api/v1/test-framework/config",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get test framework config failed: {response.status_code}")

    # ==================== 追踪端点 ====================

    @task(1)
    def get_tracing_data(self):
        """获取追踪数据"""
        with self.client.get(
            "/api/v1/tracing/data", catch_response=True, name="/api/v1/tracing/data"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get tracing data failed: {response.status_code}")

    # ==================== 统一修复端点 ====================

    @task(1)
    def get_unified_repairs(self):
        """获取统一修复"""
        with self.client.get(
            "/api/v1/unified-repairs", catch_response=True, name="/api/v1/unified-repairs"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get unified repairs failed: {response.status_code}")

    # ==================== 用户端点 ====================

    @task(1)
    def get_user_profile(self):
        """获取用户资料"""
        user_id = random.randint(1, 100)
        with self.client.get(
            f"/api/v1/users/{user_id}", catch_response=True, name="/api/v1/users/{id}"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Get user profile failed: {response.status_code}")

    # ==================== WebSocket端点 ====================

    @task(1)
    def get_websocket_status(self):
        """获取WebSocket状态"""
        with self.client.get(
            "/api/v1/websocket/status", catch_response=True, name="/api/v1/websocket/status"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get WebSocket status failed: {response.status_code}")

    # ==================== Windows修复端点 ====================

    @task(1)
    def get_windows_repairs(self):
        """获取Windows修复"""
        with self.client.get(
            "/api/v1/windows-repairs", catch_response=True, name="/api/v1/windows-repairs"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get Windows repairs failed: {response.status_code}")

    # ==================== 工作流可视化端点 ====================

    @task(1)
    def get_workflow_visualization(self):
        """获取工作流可视化"""
        with self.client.get(
            "/api/v1/workflow-visualization",
            catch_response=True,
            name="/api/v1/workflow-visualization",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get workflow visualization failed: {response.status_code}")

    # ==================== 批处理端点 ====================

    @task(1)
    def get_batch_jobs(self):
        """获取批处理任务"""
        with self.client.get(
            "/api/v1/batch/jobs", catch_response=True, name="/api/v1/batch/jobs"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get batch jobs failed: {response.status_code}")

    # ==================== 备份端点 ====================

    @task(1)
    def get_backups(self):
        """获取备份"""
        with self.client.get(
            "/api/v1/backups", catch_response=True, name="/api/v1/backups"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get backups failed: {response.status_code}")

    # ==================== 仪表板端点 ====================

    @task(1)
    def get_dashboard_data(self):
        """获取仪表板数据"""
        with self.client.get(
            "/api/v1/dashboard", catch_response=True, name="/api/v1/dashboard"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get dashboard data failed: {response.status_code}")


class AdminUser(HttpUser):
    """
    管理员用户类 - 执行管理操作
    """

    wait_time = between(2, 5)
    weight = 0.1  # 较低权重，模拟较少的管理操作

    @task
    def get_system_status(self):
        """获取系统状态"""
        with self.client.get(
            "/api/v1/system/status", catch_response=True, name="/api/v1/system/status [ADMIN]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get system status failed: {response.status_code}")

    @task
    def get_audit_logs(self):
        """获取审计日志"""
        with self.client.get(
            "/api/v1/audit/logs", catch_response=True, name="/api/v1/audit/logs [ADMIN]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get audit logs failed: {response.status_code}")


class PerformanceReporter:
    """性能测试报告生成器"""

    def __init__(self):
        self.test_results: Dict[str, Any] = {}

    def record_result(self, request_type, name, response_time, success):
        """记录测试结果"""
        if name not in self.test_results:
            self.test_results[name] = {
                "request_type": request_type,
                "total_requests": 0,
                "success_count": 0,
                "failure_count": 0,
                "response_times": [],
                "min_response_time": float("inf"),
                "max_response_time": 0,
                "total_response_time": 0,
            }

        result = self.test_results[name]
        result["total_requests"] += 1

        if success:
            result["success_count"] += 1
            result["response_times"].append(response_time)
            result["total_response_time"] += response_time
            result["min_response_time"] = min(result["min_response_time"], response_time)
            result["max_response_time"] = max(result["max_response_time"], response_time)
        else:
            result["failure_count"] += 1

    def calculate_statistics(self):
        """计算统计信息"""
        for name, result in self.test_results.items():
            if result["response_times"]:
                result["avg_response_time"] = result["total_response_time"] / len(
                    result["response_times"]
                )
                result["response_times"].sort()
                n = len(result["response_times"])
                result["p50_response_time"] = result["response_times"][int(n * 0.5)]
                result["p95_response_time"] = result["response_times"][int(n * 0.95)]
                result["p99_response_time"] = result["response_times"][int(n * 0.99)]
                result["error_rate"] = result["failure_count"] / result["total_requests"]
            else:
                result["avg_response_time"] = 0
                result["p50_response_time"] = 0
                result["p95_response_time"] = 0
                result["p99_response_time"] = 0
                result["error_rate"] = 1.0 if result["total_requests"] > 0 else 0

    def generate_report(self):
        """生成报告"""
        self.calculate_statistics()
        return self.test_results


# 全局报告实例
reporter = PerformanceReporter()


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """请求事件监听器"""
    success = exception is None
    reporter.record_result(request_type, name, response_time, success)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试停止事件监听器"""
    if isinstance(environment.runner, MasterRunner):
        return  # 只有worker节点生成报告

    report = reporter.generate_report()

    # 保存JSON报告
    import json
    import os
    from datetime import datetime

    report_dir = "tests/performance/reports"
    os.makedirs(report_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(report_dir, f"performance_report_{timestamp}.json")

    with open(json_file, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Performance report saved to {json_file}")
