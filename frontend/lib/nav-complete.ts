import { translate, type Locale } from './i18n';

export interface NavItem {
  href: string;
  label: string;
  target?: string;
}

export interface NavGroup {
  title: string;
  items: NavItem[];
}

export function getCompleteNavGroups(locale: Locale): NavGroup[] {
  const t = (key: string) => translate(locale, key);

  return [
    // ==================== AI智能运维（30个功能）====================
    {
      title: 'AI智能运维',
      items: [
        { href: '/ai/llm-router', label: 'LLM路由器' },
        { href: '/ai/cost-optimizer', label: '成本优化器' },
        { href: '/ai/capability-evaluator', label: '能力评估器' },
        { href: '/ai/load-balancer', label: '负载均衡器' },
        { href: '/ai/rag-knowledge-base', label: 'RAG知识库' },
        { href: '/ai/retriever', label: '检索器' },
        { href: '/ai/vectorizer', label: '向量化处理' },
        { href: '/ai/reranker', label: '重排序器' },
        { href: '/ai/fusion', label: '结果融合' },
        { href: '/ai/knowledge-graph', label: '知识图谱' },
        { href: '/ai/root-cause-analysis', label: '根因分析' },
        { href: '/ai/topology-analysis', label: '拓扑分析' },
        { href: '/ai/cross-layer-tracking', label: '跨层追踪' },
        { href: '/ai/pattern-matching', label: '模式匹配' },
        { href: '/ai/semantic-search', label: '语义搜索' },
        { href: '/ai/document-index', label: '文档索引' },
        { href: '/ai/knowledge-retrieval', label: '知识库检索' },
        { href: '/ai/ai-feedback', label: 'AI反馈收集' },
        { href: '/ai/model-optimization', label: '模型优化' },
        { href: '/ai/advanced-ai', label: '高级AI功能' },
        { href: '/ai/deep-learning', label: '深度学习模型' },
        { href: '/ai/langgraph-workflow', label: 'LangGraph工作流' },
        { href: '/ai/langgraph-executor', label: '工作流执行器' },
        { href: '/ai/langgraph-dsl', label: 'DSL语言定义' },
        { href: '/ai/langgraph-nodes', label: '节点类型' },
        { href: '/ai/langgraph-visualizer', label: '工作流可视化' },
        { href: '/ai/ai-copilot', label: 'AI助手' },
        { href: '/ai/intelligent-analysis', label: '智能分析' },
        { href: '/ai/runbook-generator', label: 'Runbook生成器' },
        { href: '/ai/model-fine-tuning', label: '模型微调' },
      ],
    },

    // ==================== 告警管理（25个功能）====================
    {
      title: '告警管理',
      items: [
        { href: '/alerts/prometheus', label: 'Prometheus告警' },
        { href: '/alerts/grafana', label: 'Grafana告警' },
        { href: '/alerts/datadog', label: 'Datadog告警' },
        { href: '/alerts/pagerduty', label: 'PagerDuty告警' },
        { href: '/alerts/cloudwatch', label: 'CloudWatch告警' },
        { href: '/alerts/zabbix', label: 'Zabbix告警' },
        { href: '/alerts/alert-rules', label: '告警规则' },
        { href: '/alerts/alert-routing', label: '告警路由' },
        { href: '/alerts/alert-aggregation', label: '告警聚合' },
        { href: '/alerts/alert-deduplication', label: '告警去重' },
        { href: '/alerts/dynamic-threshold', label: '动态阈值' },
        { href: '/alerts/intelligent-analysis', label: '智能告警分析' },
        { href: '/alerts/alert-webhook', label: '告警Webhook' },
        { href: '/alerts/alert-forwarding', label: '告警转发' },
        { href: '/alerts/alert-history', label: '告警历史' },
        { href: '/alerts/alert-statistics', label: '告警统计' },
        { href: '/alerts/alert-trends', label: '告警趋势' },
        { href: '/alerts/alert-suppression', label: '告警抑制' },
        { href: '/alerts/alert-escalation', label: '告警升级' },
        { href: '/alerts/alert-acknowledgement', label: '告警确认' },
        { href: '/alerts/alert-correlation', label: '告警关联' },
        { href: '/alerts/alert-prediction', label: '告警预测' },
        { href: '/alerts/alert-notification', label: '告警通知' },
        { href: '/alerts/alert-dashboard', label: '告警仪表盘' },
        { href: '/alerts/alert-configuration', label: '告警配置' },
      ],
    },

    // ==================== 自动修复（20个功能）====================
    {
      title: '自动修复',
      items: [
        { href: '/repair/auto-heal', label: '自动治愈' },
        { href: '/repair/intelligent-repair', label: '智能修复' },
        { href: '/repair/repair-scripts', label: '修复脚本' },
        { href: '/repair/script-management', label: '脚本管理' },
        { href: '/repair/repair-history', label: '修复历史' },
        { href: '/repair/unified-repair', label: '统一修复' },
        { href: '/repair/cross-platform', label: '跨平台修复' },
        { href: '/repair/linux-repair', label: 'Linux修复' },
        { href: '/repair/windows-repair', label: 'Windows修复' },
        { href: '/repair/macos-repair', label: 'macOS修复' },
        { href: '/repair/docker-repair', label: 'Docker修复' },
        { href: '/repair/k8s-repair', label: 'Kubernetes修复' },
        { href: '/repair/pod-repair', label: 'Pod修复' },
        { href: '/repair/cluster-repair', label: '集群修复' },
        { href: '/repair/cloud-repair', label: '云平台修复' },
        { href: '/repair/hardware-repair', label: '硬件修复' },
        { href: '/repair/repair-verification', label: '修复验证' },
        { href: '/repair/repair-effectiveness', label: '修复效果评估' },
        { href: '/repair/hitl-approval', label: '人工审批' },
        { href: '/repair/repair-configuration', label: '修复配置' },
      ],
    },

    // ==================== 监控可观测性（35个功能）====================
    {
      title: '监控可观测性',
      items: [
        { href: '/monitoring/metrics', label: '系统指标' },
        { href: '/monitoring/metrics-snapshot', label: '指标快照' },
        { href: '/monitoring/metrics-history', label: '历史数据' },
        { href: '/monitoring/process-monitoring', label: '进程监控' },
        { href: '/monitoring/linux-monitoring', label: 'Linux监控' },
        { href: '/monitoring/windows-monitoring', label: 'Windows监控' },
        { href: '/monitoring/macos-monitoring', label: 'macOS监控' },
        { href: '/monitoring/docker-monitoring', label: 'Docker监控' },
        { href: '/monitoring/k8s-monitoring', label: 'Kubernetes监控' },
        { href: '/monitoring/cloud-monitoring', label: '云平台监控' },
        { href: '/monitoring/apm', label: '应用性能监控' },
        { href: '/monitoring/api-performance', label: 'API性能监控' },
        { href: '/monitoring/log-collection', label: '日志采集' },
        { href: '/monitoring/error-logs', label: '错误日志' },
        { href: '/monitoring/log-search', label: '日志搜索' },
        { href: '/monitoring/linux-logs', label: 'Linux日志' },
        { href: '/monitoring/anomaly-detection', label: '异常检测' },
        { href: '/monitoring/anomaly-analysis', label: '异常分析' },
        { href: '/monitoring/prometheus-metrics', label: 'Prometheus指标' },
        { href: '/monitoring/metrics-exporter', label: '指标导出器' },
        { href: '/monitoring/metrics-converter', label: '指标转换器' },
        { href: '/monitoring/otel-collector', label: 'OpenTelemetry采集' },
        { href: '/monitoring/health-check', label: '健康检查' },
        { href: '/monitoring/readiness-check', label: '就绪检查' },
        { href: '/monitoring/detailed-health', label: '详细健康信息' },
        { href: '/monitoring/observability-query', label: '可观测性查询' },
        { href: '/monitoring/telemetry-core', label: '遥测核心' },
        { href: '/monitoring/fastapi-telemetry', label: 'FastAPI遥测' },
        { href: '/monitoring/cross-service-tracing', label: '跨服务追踪' },
        { href: '/monitoring/tracing-visualization', label: '追踪可视化' },
        { href: '/monitoring/victoriametrics', label: 'VictoriaMetrics' },
        { href: '/monitoring/loki', label: 'Loki日志存储' },
        { href: '/monitoring/tempo', label: 'Tempo追踪存储' },
        { href: '/monitoring/elasticsearch', label: 'Elasticsearch日志' },
        { href: '/monitoring/log-analysis', label: '日志分析' },
        { href: '/monitoring/log-alerting', label: '日志告警' },
      ],
    },

    // ==================== 服务拓扑（15个功能）====================
    {
      title: '服务拓扑',
      items: [
        { href: '/topology/topology-management', label: '拓扑管理' },
        { href: '/topology/topology-types', label: '拓扑类型' },
        { href: '/topology/topology-status', label: '拓扑状态' },
        { href: '/topology/full-link-topology', label: '全链路拓扑' },
        { href: '/topology/topology-view', label: '拓扑视图' },
        { href: '/topology/topology-visualization', label: '拓扑可视化' },
        { href: '/topology/service-discovery', label: '服务发现' },
        { href: '/topology/service-registration', label: '服务注册' },
        { href: '/topology/dependency-modeling', label: '依赖建模' },
        { href: '/topology/impact-analysis', label: '影响分析' },
        { href: '/topology/call-chain-analysis', label: '调用链分析' },
        { href: '/topology/call-chain-search', label: '调用链搜索' },
        { href: '/topology/causal-graph', label: '因果图' },
        { href: '/topology/causal-inference', label: '因果推断' },
        { href: '/topology/causal-prediction', label: '因果预测' },
      ],
    },

    // ==================== 工作流自动化（18个功能）====================
    {
      title: '工作流自动化',
      items: [
        { href: '/workflow/workflow-management', label: '工作流管理' },
        { href: '/workflow/workflow-execution', label: '工作流执行' },
        { href: '/workflow/workflow-status', label: '工作流状态' },
        { href: '/workflow/workflow-visualization', label: '工作流可视化' },
        { href: '/workflow/flowchart', label: '流程图展示' },
        { href: '/workflow/state-machine', label: '状态机' },
        { href: '/workflow/executor', label: '执行器' },
        { href: '/workflow/dsl-definition', label: 'DSL定义' },
        { href: '/workflow/dag', label: 'DAG图' },
        { href: '/workflow/task-scheduler', label: '任务调度器' },
        { href: '/workflow/performance-scheduler', label: '性能调度器' },
        { href: '/workflow/change-management', label: '变更管理' },
        { href: '/workflow/change-approval', label: '变更审批' },
        { href: '/workflow/change-records', label: '变更记录' },
        { href: '/workflow/cicd-pipeline', label: 'CI/CD管道' },
        { href: '/workflow/gitops', label: 'GitOps管理' },
        { href: '/workflow/ansible-automation', label: 'Ansible自动化' },
        { href: '/workflow/terraform-iac', label: 'Terraform IaC' },
      ],
    },

    // ==================== 安全合规（25个功能）====================
    {
      title: '安全合规',
      items: [
        { href: '/security/command-guard', label: '高危指令管控' },
        { href: '/security/command-check', label: '命令检查' },
        { href: '/security/command-rewrite', label: '命令重写' },
        { href: '/security/security-audit', label: '安全审计' },
        { href: '/security/operation-records', label: '操作记录' },
        { href: '/security/audit-center', label: '审计中心' },
        { href: '/security/vulnerability-scan', label: '漏洞扫描' },
        { href: '/security/vulnerability-intelligence', label: '漏洞情报' },
        { href: '/security/vulnerability-management', label: '漏洞管理' },
        { href: '/security/security-testing', label: '安全测试' },
        { href: '/security/penetration-testing', label: '渗透测试' },
        { href: '/security/input-validation', label: '输入验证' },
        { href: '/security/api-security', label: 'API安全' },
        { href: '/security/database-security', label: '数据库安全' },
        { href: '/security/compliance-check', label: '合规检查' },
        { href: '/security/compliance-management', label: '合规管理' },
        { href: '/security/data-privacy', label: '数据隐私' },
        { href: '/security/data-encryption', label: '数据加密' },
        { href: '/security/snapshot-encryption', label: '快照加密' },
        { href: '/security/https', label: 'HTTPS配置' },
        { href: '/security/rate-limit', label: '速率限制' },
        { href: '/security/rbac', label: '角色访问控制' },
        { href: '/security/abac', label: '属性访问控制' },
        { href: '/security/mfa', label: '多因子认证' },
        { href: '/security/key-management', label: '密钥管理' },
      ],
    },

    // ==================== SLO/SLA管理（12个功能）====================
    {
      title: 'SLO/SLA管理',
      items: [
        { href: '/slo/slo-management', label: 'SLO管理' },
        { href: '/slo/slo-definition', label: 'SLO定义' },
        { href: '/slo/slo-monitoring', label: 'SLO监控' },
        { href: '/slo/slo-evaluation', label: 'SLO评估' },
        { href: '/slo/slo-storage', label: 'SLO存储' },
        { href: '/slo/slo-metrics', label: 'SLO指标' },
        { href: '/slo/slo-incident', label: 'SLO事件' },
        { href: '/slo/sla-management', label: 'SLA管理' },
        { href: '/slo/sla-report', label: 'SLA报告' },
        { href: '/slo/sla-storage', label: 'SLA存储' },
        { href: '/slo/kpi-management', label: 'KPI管理' },
        { href: '/slo/kpi-config', label: 'KPI配置' },
      ],
    },

    // ==================== 成本管理（8个功能）====================
    {
      title: '成本管理',
      items: [
        { href: '/cost/cost-monitoring', label: '成本监控' },
        { href: '/cost/cost-collection', label: '成本收集' },
        { href: '/cost/cost-prediction', label: '成本预测' },
        { href: '/cost/budget-management', label: '预算管理' },
        { href: '/cost/llm-cost', label: 'LLM成本监控' },
        { href: '/cost/resource-cost', label: '资源成本' },
        { href: '/cost/cost-optimization', label: '成本优化' },
        { href: '/cost/cost-report', label: '成本报告' },
      ],
    },

    // ==================== 集成能力（20个功能）====================
    {
      title: '集成能力',
      items: [
        { href: '/integration/integration-ecosystem', label: '集成生态' },
        { href: '/integration/integration-registration', label: '集成注册' },
        { href: '/integration/integration-list', label: '集成列表' },
        { href: '/integration/notification-sending', label: '通知发送' },
        { href: '/integration/prometheus', label: 'Prometheus集成' },
        { href: '/integration/grafana', label: 'Grafana集成' },
        { href: '/integration/datadog', label: 'Datadog集成' },
        { href: '/integration/elk-stack', label: 'ELK Stack' },
        { href: '/integration/github', label: 'GitHub集成' },
        { href: '/integration/kafka', label: 'Kafka集成' },
        { href: '/integration/message-queue', label: '消息队列' },
        { href: '/integration/servicenow', label: 'ServiceNow集成' },
        { href: '/integration/jira', label: 'Jira集成' },
        { href: '/integration/slack', label: 'Slack集成' },
        { href: '/integration/teams', label: 'Teams集成' },
        { href: '/integration/oncall', label: 'Oncall集成' },
        { href: '/integration/itsm', label: 'ITSM集成' },
        { href: '/integration/cicd', label: 'CI/CD集成' },
        { href: '/integration/gitops', label: 'GitOps集成' },
        { href: '/integration/cloud-platform', label: '云平台集成' },
      ],
    },

    // ==================== 插件生态（15个功能）====================
    {
      title: '插件生态',
      items: [
        { href: '/plugin/plugin-management', label: '插件管理' },
        { href: '/plugin/plugin-system', label: '插件系统' },
        { href: '/plugin/plugin-run', label: '插件运行' },
        { href: '/plugin/plugin-status', label: '插件状态' },
        { href: '/plugin/plugin-sdk', label: '插件SDK' },
        { href: '/plugin/plugin-interface', label: '插件接口定义' },
        { href: '/plugin/plugin-registration', label: '插件注册' },
        { href: '/plugin/plugin-development', label: '插件开发' },
        { href: '/plugin/plugin-template', label: '开发模板' },
        { href: '/plugin/code-generation', label: '代码生成' },
        { href: '/plugin/plugin-marketplace', label: '插件市场' },
        { href: '/plugin/plugin-publish', label: '插件发布' },
        { href: '/plugin/plugin-list', label: '插件列表' },
        { href: '/plugin/batch-operations', label: '批量操作' },
        { href: '/plugin/plugin-configuration', label: '插件配置' },
      ],
    },

    // ==================== 多租户（10个功能）====================
    {
      title: '多租户',
      items: [
        { href: '/tenant/tenant-management', label: '租户管理' },
        { href: '/tenant/tenant-isolation', label: '租户隔离' },
        { href: '/tenant/tenant-configuration', label: '租户配置' },
        { href: '/tenant/tenant-quota', label: '租户配额' },
        { href: '/tenant/tenant-billing', label: '租户计费' },
        { href: '/tenant/tenant-resources', label: '租户资源' },
        { href: '/tenant/tenant-permissions', label: '租户权限' },
        { href: '/tenant/tenant-audit', label: '租户审计' },
        { href: '/tenant/tenant-monitoring', label: '租户监控' },
        { href: '/tenant/tenant-api', label: '租户API' },
      ],
    },

    // ==================== 数据库优化（15个功能）====================
    {
      title: '数据库优化',
      items: [
        { href: '/database/optimization', label: '数据库优化' },
        { href: '/database/slow-query', label: '慢查询分析' },
        { href: '/database/index-optimization', label: '索引优化' },
        { href: '/database/query-optimization', label: '查询优化' },
        { href: '/database/connection-optimization', label: '连接优化' },
        { href: '/database/cache-optimization', label: '缓存优化' },
        { href: '/database/optimization-manager', label: '优化管理器' },
        { href: '/database/read-write-routing', label: '读写分离' },
        { href: '/database/replication', label: '数据库复制' },
        { href: '/database/failover', label: '故障转移' },
        { href: '/database/sharding', label: '分片管理' },
        { href: '/database/postgresql-shard', label: 'PostgreSQL分片' },
        { href: '/database/query-cache', label: '查询缓存' },
        { href: '/database/performance-tuning', label: '性能调优' },
        { href: '/database/health-monitoring', label: '健康监控' },
      ],
    },

    // ==================== 性能优化（20个功能）====================
    {
      title: '性能优化',
      items: [
        { href: '/performance/performance-monitoring', label: '性能监控' },
        { href: '/performance/performance-data', label: '性能数据采集' },
        { href: '/performance/performance-optimizer', label: '性能优化器' },
        { href: '/performance/performance-tuning', label: '性能调优' },
        { href: '/performance/performance-report', label: '性能报告' },
        { href: '/performance/regression-detection', label: '性能回归检测' },
        { href: '/performance/integration-testing', label: '性能集成测试' },
        { href: '/performance/api-performance', label: 'API性能' },
        { href: '/performance/api-response-time', label: 'API响应时间' },
        { href: '/performance/api-throughput', label: 'API吞吐量' },
        { href: '/performance/api-resources', label: 'API资源优化' },
        { href: '/performance/cpu-optimization', label: 'CPU优化' },
        { href: '/performance/memory-optimization', label: '内存优化' },
        { href: '/performance/memory-monitor', label: '内存监控' },
        { href: '/performance/cache-strategy', label: '缓存策略' },
        { href: '/performance/smart-cache', label: '智能缓存' },
        { href: '/performance/cache-preheat', label: '缓存预热' },
        { href: '/performance/query-optimization', label: '查询优化' },
        { href: '/performance/concurrent-control', label: '并发控制' },
        { href: '/performance/rate-limiting', label: '限流控制' },
      ],
    },

    // ==================== 灾难恢复（12个功能）====================
    {
      title: '灾难恢复',
      items: [
        { href: '/disaster/backup-management', label: '备份管理' },
        { href: '/disaster/data-backup', label: '数据备份' },
        { href: '/disaster/backup-recovery', label: '备份恢复' },
        { href: '/disaster/backup-strategy', label: '备份策略' },
        { href: '/disaster/pgbackrest', label: 'pgBackRest备份' },
        { href: '/disaster/velero', label: 'Velero备份' },
        { href: '/disaster/dr-drill', label: '灾难恢复演练' },
        { href: '/disaster/dr-testing', label: 'DR测试' },
        { href: '/disaster/dr-scenarios', label: '灾难恢复场景' },
        { href: '/disaster/disaster-recovery', label: '灾难恢复' },
        { href: '/disaster/ha-configuration', label: '高可用配置' },
        { href: '/disaster/recovery-plan', label: '恢复计划' },
      ],
    },

    // ==================== 混沌工程（8个功能）====================
    {
      title: '混沌工程',
      items: [
        { href: '/chaos/chaos-engineering', label: '混沌工程' },
        { href: '/chaos/fault-injection', label: '故障注入' },
        { href: '/chaos/chaos-mesh', label: 'Chaos Mesh' },
        { href: '/chaos/chaos-experiments', label: '混沌实验' },
        { href: '/chaos/chaos-scenarios', label: '混沌场景' },
        { href: '/chaos/chaos-dashboard', label: '混沌仪表盘' },
        { href: '/chaos/chaos-reports', label: '混沌报告' },
        { href: '/chaos/chaos-configuration', label: '混沌配置' },
      ],
    },

    // ==================== 测试自动化（15个功能）====================
    {
      title: '测试自动化',
      items: [
        { href: '/testing/test-automation', label: '测试自动化' },
        { href: '/testing/test-framework', label: '测试框架' },
        { href: '/testing/test-management', label: '测试管理' },
        { href: '/testing/test-coverage', label: '测试覆盖率' },
        { href: '/testing/code-coverage', label: '代码覆盖率' },
        { href: '/testing/integration-testing', label: '集成测试' },
        { href: '/testing/integration-validator', label: '集成验证' },
        { href: '/testing/testing-system', label: '测试系统' },
        { href: '/testing/type-validation', label: '类型验证' },
        { href: '/testing/input-validation', label: '输入验证' },
        { href: '/testing/verifier', label: '验证器' },
        { href: '/testing/automated-tests', label: '自动化测试' },
        { href: '/testing/test-reports', label: '测试报告' },
        { href: '/testing/test-scheduling', label: '测试调度' },
        { href: '/testing/test-results', label: '测试结果' },
      ],
    },

    // ==================== 文档生成（8个功能）====================
    {
      title: '文档生成',
      items: [
        { href: '/docs/documentation-management', label: '文档管理' },
        { href: '/docs/document-creation', label: '文档创建' },
        { href: '/docs/document-list', label: '文档列表' },
        { href: '/docs/doc-generator', label: '文档生成器' },
        { href: '/docs/template-management', label: '模板管理' },
        { href: '/docs/doc-generation', label: '文档生成' },
        { href: '/docs/sphinx', label: 'Sphinx文档' },
        { href: '/docs/documentation-api', label: '文档API' },
      ],
    },

    // ==================== 服务网格（12个功能）====================
    {
      title: '服务网格',
      items: [
        { href: '/service-mesh/service-mesh', label: '服务网格' },
        { href: '/service-mesh/mesh-management', label: '网格管理' },
        { href: '/service-mesh/microservice-mesh', label: '微服务网格' },
        { href: '/service-mesh/service-monitoring', label: '服务监控' },
        { href: '/service-mesh/health-check', label: '健康检查' },
        { href: '/service-mesh/traffic-management', label: '流量管理' },
        { href: '/service-mesh/service-discovery', label: '服务发现' },
        { href: '/service-mesh/load-balancing', label: '负载均衡' },
        { href: '/service-mesh/circuit-breaker', label: '熔断器' },
        { href: '/service-mesh/retry-policy', label: '重试策略' },
        { href: '/service-mesh/timeout-config', label: '超时配置' },
        { href: '/service-mesh/mesh-observability', label: '网格可观测性' },
      ],
    },

    // ==================== 实时通信（15个功能）====================
    {
      title: '实时通信',
      items: [
        { href: '/realtime/realtime-communication', label: '实时通信' },
        { href: '/realtime/event-stream', label: '事件流' },
        { href: '/realtime/websocket', label: 'WebSocket' },
        { href: '/realtime/websocket-connection', label: 'WebSocket连接' },
        { href: '/realtime/websocket-manager', label: 'WebSocket管理' },
        { href: '/realtime/enhanced-websocket', label: '增强WebSocket' },
        { href: '/realtime/sse', label: 'SSE事件流' },
        { href: '/realtime/realtime-status', label: '实时状态' },
        { href: '/realtime/bidirectional-communication', label: '双向通信' },
        { href: '/realtime/push-notification', label: '推送通知' },
        { href: '/realtime/message-queue', label: '消息队列' },
        { href: '/realtime/kafka-stream', label: 'Kafka流处理' },
        { href: '/realtime/flink-stream', label: 'Flink流处理' },
        { href: '/realtime/event-processing', label: '事件处理' },
        { href: '/realtime/stream-monitoring', label: '流监控' },
      ],
    },

    // ==================== 系统资源（12个功能）====================
    {
      title: '系统资源',
      items: [
        { href: '/resources/system-resources', label: '系统资源' },
        { href: '/resources/resource-optimization', label: '资源优化' },
        { href: '/resources/cpu-usage', label: 'CPU使用' },
        { href: '/resources/memory-usage', label: '内存使用' },
        { href: '/resources/disk-usage', label: '磁盘使用' },
        { href: '/resources/network-usage', label: '网络使用' },
        { href: '/resources/capacity-planning', label: '容量规划' },
        { href: '/resources/resource-allocation', label: '资源分配' },
        { href: '/resources/resource-quota', label: '资源配额' },
        { href: '/resources/resource-monitoring', label: '资源监控' },
        { href: '/resources/resource-alerts', label: '资源告警' },
        { href: '/resources/resource-reports', label: '资源报告' },
      ],
    },

    // ==================== GraphQL/gRPC（10个功能）====================
    {
      title: 'GraphQL/gRPC',
      items: [
        { href: '/graphql/graphql-api', label: 'GraphQL接口' },
        { href: '/graphql/graphql-query', label: 'GraphQL查询' },
        { href: '/graphql/graphql-schema', label: 'GraphQL Schema' },
        { href: '/graphql/graphql-resolvers', label: 'GraphQL解析器' },
        { href: '/graphql/graphql-auth', label: 'GraphQL认证' },
        { href: '/graphql/graphql-dataloader', label: 'GraphQL数据加载' },
        { href: '/graphql/graphql-subscription', label: 'GraphQL订阅' },
        { href: '/grpc/grpc-service', label: 'gRPC服务' },
        { href: '/grpc/grpc-health', label: 'gRPC健康检查' },
        { href: '/grpc/grpc-management', label: 'gRPC服务管理' },
      ],
    },

    // ==================== 向量数据库（8个功能）====================
    {
      title: '向量数据库',
      items: [
        { href: '/vector/qdrant', label: 'Qdrant向量库' },
        { href: '/vector/collection-management', label: '集合管理' },
        { href: '/vector/vector-search', label: '向量搜索' },
        { href: '/vector/similarity-search', label: '相似度搜索' },
        { href: '/vector/vector-retrieval', label: '向量检索' },
        { href: '/vector/vector-sharding', label: '向量分片' },
        { href: '/vector/vector-pipeline', label: '向量管道' },
        { href: '/vector/vector-service', label: '向量服务' },
      ],
    },

    // ==================== 国际化（10个功能）====================
    {
      title: '国际化',
      items: [
        { href: '/i18n/i18n-management', label: '国际化管理' },
        { href: '/i18n/language-support', label: '语言支持' },
        { href: '/i18n/translation', label: '翻译管理' },
        { href: '/i18n/formatting', label: '格式化' },
        { href: '/i18n/localization-adapter', label: '本地化适配器' },
        { href: '/i18n/date-format', label: '日期格式' },
        { href: '/i18n/currency-format', label: '货币格式' },
        { href: '/i18n/localization-resource', label: '本地化资源' },
        { href: '/i18n/resource-management', label: '资源管理' },
        { href: '/i18n/locale-switching', label: '语言切换' },
      ],
    },

    // ==================== 成熟度评估（6个功能）====================
    {
      title: '成熟度评估',
      items: [
        { href: '/maturity/sre-maturity', label: 'SRE成熟度评估' },
        { href: '/maturity/capability-assessment', label: '能力评估' },
        { href: '/maturity/maturity-score', label: '成熟度评分' },
        { href: '/maturity/maturity-report', label: '成熟度报告' },
        { href: '/maturity/benchmark', label: '基准对比' },
        { href: '/maturity/improvement-plan', label: '改进计划' },
      ],
    },

    // ==================== 前端增强（8个功能）====================
    {
      title: '前端增强',
      items: [
        { href: '/frontend/frontend-enhancement', label: '前端增强' },
        { href: '/frontend/performance-optimization', label: '性能优化' },
        { href: '/frontend/cache-strategy', label: '缓存策略' },
        { href: '/frontend/ui-experience', label: 'UI体验' },
        { href: '/frontend/accessibility', label: '无障碍支持' },
        { href: '/frontend/user-preferences', label: '用户偏好' },
        { href: '/frontend/theme-management', label: '主题管理' },
        { href: '/frontend/frontend-integration', label: '前端集成' },
      ],
    },

    // ==================== 企业功能（15个功能）====================
    {
      title: '企业功能',
      items: [
        { href: '/enterprise/enterprise-features', label: '企业功能' },
        { href: '/enterprise/multi-tenant', label: '多租户支持' },
        { href: '/enterprise/tenant-engine', label: '租户引擎' },
        { href: '/enterprise/compliance', label: '合规管理' },
        { href: '/enterprise/compliance-manager', label: '合规管理器' },
        { href: '/enterprise/data-privacy', label: '数据隐私' },
        { href: '/enterprise/data-lifecycle', label: '数据生命周期' },
        { href: '/enterprise/data-lineage', label: '数据血缘' },
        { href: '/enterprise/audit-trail', label: '审计追踪' },
        { href: '/enterprise/security-center', label: '安全中心' },
        { href: '/enterprise/priority-management', label: '优先级管理' },
        { href: '/enterprise/business-impact', label: '业务影响' },
        { href: '/enterprise/sla-status', label: 'SLA状态' },
        { href: '/enterprise/enterprise-settings', label: '企业设置' },
        { href: '/enterprise/enterprise-api', label: '企业API' },
      ],
    },

    // ==================== 用户管理（10个功能）====================
    {
      title: '用户管理',
      items: [
        { href: '/users/user-management', label: '用户管理' },
        { href: '/users/user-authentication', label: '用户认证' },
        { href: '/users/user-authorization', label: '用户授权' },
        { href: '/users/user-permissions', label: '用户权限' },
        { href: '/users/user-profile', label: '用户信息' },
        { href: '/users/mfa', label: '多因子认证' },
        { href: '/users/password-management', label: '密码管理' },
        { href: '/users/session-management', label: '会话管理' },
        { href: '/users/user-training', label: '用户培训' },
        { href: '/users/user-audit', label: '用户审计' },
      ],
    },

    // ==================== 仪表盘与概览（5个功能）====================
    {
      title: '仪表盘与概览',
      items: [
        { href: '/', label: '首页' },
        { href: '/overview', label: '概览' },
        { href: '/dashboard', label: '仪表盘' },
        { href: '/kpi', label: 'KPI指标' },
        { href: '/stats', label: '统计数据' },
      ],
    },

    // ==================== 协作与通知（8个功能）====================
    {
      title: '协作与通知',
      items: [
        { href: '/collaboration/collaboration', label: '协作工作区' },
        { href: '/collaboration/workspace', label: '工作区管理' },
        { href: '/collaboration/messages', label: '消息管理' },
        { href: '/collaboration/team', label: '团队协作' },
        { href: '/collaboration/team-management', label: '团队管理' },
        { href: '/collaboration/notification', label: '通知配置' },
        { href: '/collaboration/notification-test', label: '通知测试' },
        { href: '/collaboration/hitl', label: '人工审批' },
      ],
    },

    // ==================== 资产管理（5个功能）====================
    {
      title: '资产管理',
      items: [
        { href: '/assets/assets-management', label: '资产管理' },
        { href: '/assets/assets-inventory', label: '资产清单' },
        { href: '/assets/assets-monitoring', label: '资产监控' },
        { href: '/assets/assets-lifecycle', label: '资产生命周期' },
        { href: '/assets/assets-report', label: '资产报告' },
      ],
    },

    // ==================== 系统设置（5个功能）====================
    {
      title: '系统设置',
      items: [
        { href: '/settings/system-settings', label: '系统设置' },
        { href: '/settings/config-management', label: '配置管理' },
        { href: '/settings/feature-flags', label: '功能开关' },
        { href: '/settings/environment-config', label: '环境配置' },
        { href: 'http://127.0.0.1:3000/docs', label: 'API文档', target: '_blank' },
      ],
    },
  ];
}

// Backward-compatible static export for consumers that do not need i18n yet.
export const completeNavGroups = getCompleteNavGroups('zh-CN');
