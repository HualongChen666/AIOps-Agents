# AIOps SRE Agent 项目目录结构

## 项目规模概览

- **总Python文件数**: 2,442个
- **核心业务代码**: 563个 (api + core)
- **扩展微服务**: 1,009个 (extensions)
- **测试代码**: 552个 (tests)
- **脚本工具**: 80个 (scripts)
- **前端代码**: 大量TypeScript/React文件

## 顶层目录结构

```
aiops-sre-agent/
├── api/                          # API路由层 (149个Python文件)
├── core/                         # 核心业务逻辑 (414个Python文件)
├── extensions/                   # 扩展微服务 (1,009个Python文件)
├── tests/                        # 测试文件 (552个Python文件)
├── scripts/                      # 脚本工具 (80个Python文件)
├── docs/                         # 文档目录
├── config/                       # 配置文件
├── services/                     # 独立服务
├── frontend/                     # 前端代码
├── monitoring/                   # 监控配置
├── alembic/                      # 数据库迁移
├── aiops_agent/                  # CLI工具
├── sdk/                          # Python SDK
├── .github/                      # GitHub配置
├── alertmanager/                 # Alertmanager配置
├── alerts/                       # 告警规则
├── loki-config/                  # Loki配置
├── otel-config/                  # OpenTelemetry配置
└── [配置文件]                    # 各种配置文件
```

## 主要目录详解

### 1. api/ - API路由层 (149个Python文件)

**用途**: FastAPI路由定义，处理HTTP请求和响应

**主要文件**:
- `auth_router.py` - 认证授权API
- `alert_router.py` - 告警管理API
- `ai_router.py` - AI功能API
- `user_router.py` - 用户管理API
- `slo_router.py` - SLO/SLA管理API
- `capacity_router.py` - 容量规划API
- `cost_router.py` - 成本管理API
- `chaos_router.py` - 混沌工程API
- `apm_router.py` - APM监控API
- `topology_router.py` - 拓扑管理API
- `repair_router.py` - 自动修复API
- `workflow_router.py` - 工作流API
- `integration_router.py` - 集成API
- `slack_router.py` - Slack集成API
- `k8s_router.py` - Kubernetes API
- `graphql_router.py` - GraphQL API
- `grpc_router.py` - gRPC API
- `plugin_router.py` - 插件管理API
- `builder_router.py` - 可视化构建器API
- `compliance_audit_router.py` - 合规审计API
- `advanced_ai_router.py` - 高级AI功能API
- `alerts_advanced_router.py` - 高级告警API
- `ai_advanced_router.py` - 高级AI API
- `business_impact_advanced_router.py` - 业务影响分析API
- `capacity_advanced_router.py` - 高级容量规划API
- `cost_advanced_router.py` - 高级成本管理API
- `change_advanced_router.py` - 变更管理API
- `chaos_advanced_router.py` - 高级混沌工程API
- `collaboration_advanced_router.py` - 协作功能API
- `monitoring_advanced_router.py` - 高级监控API
- `plugin_marketplace_advanced_router.py` - 插件市场API
- `security_advanced_router.py` - 安全管理API
- `slo_advanced_router.py` - 高级SLO API
- `tracing_advanced_router.py` - 分布式追踪API
- `unified_repair_advanced_router.py` - 统一修复API
- `workflow_advanced_router.py` - 高级工作流API
- `common/` - 通用工具函数
  - `cache_helpers.py` - 缓存辅助函数
  - `error_handlers.py` - 错误处理器
  - `logging_helpers.py` - 日志辅助函数
  - `validation_helpers.py` - 验证辅助函数
- `schemas/` - API数据模型
  - `repair.py` - 修复相关模型
  - `responses.py` - 响应模型
  - `examples.py` - 示例数据
- `middleware/` - 中间件
  - `rbac_middleware.py` - RBAC权限中间件
  - `tenant_middleware.py` - 租户中间件

### 2. core/ - 核心业务逻辑 (414个Python文件)

**用途**: 核心业务逻辑、AI引擎、数据处理等

**主要子目录**:
- `ai/` - AI相关功能
  - `langgraph/` - LangGraph工作流引擎
  - `llm_router/` - LLM路由服务
  - `rag/` - RAG检索增强生成
- `agent/` - Agent相关功能
  - `executor.py` - 执行器
  - `planner.py` - 规划器
  - `subagent.py` - 子代理
  - `tools.py` - 工具集
- `alert_providers/` - 告警提供者
  - `prometheus.py` - Prometheus告警
  - `grafana.py` - Grafana告警
  - `datadog.py` - Datadog告警
  - `cloudwatch.py` - CloudWatch告警
  - `zabbix.py` - Zabbix告警
- `analysis/` - 分析引擎
  - `l2/` - L2级分析
- `causal/` - 因果分析
- `base/` - 基础组件
  - `analyzer.py` - 分析器基类
  - `collector.py` - 收集器基类
  - `executor.py` - 执行器基类
  - `storage.py` - 存储基类
- `interface/` - 接口定义
  - `mcp/` - MCP接口
- `storage/` - 存储实现
  - `postgres_storage.py` - PostgreSQL存储
- `workflow/` - 工作流引擎
  - `templates/` - 工作流模板

**主要文件**:
- `ai_engine.py` - AI引擎核心
- `ai_service.py` - AI服务
- `alert_engine.py` - 告警引擎
- `alert_service.py` - 告警服务
- `auto_heal.py` - 自动修复
- `authentication.py` - 认证服务
- `auth_service.py` - 授权服务
- `backup.py` - 备份功能
- `business_impact_engine.py` - 业务影响分析
- `capacity_engine.py` - 容量规划引擎
- `config_center.py` - 配置中心
- `database.py` - 数据库连接
- `db_engine.py` - 数据库引擎
- `error_handler.py` - 错误处理
- `health_check.py` - 健康检查
- `lifecycle_manager.py` - 生命周期管理
- `memory_monitor.py` - 内存监控
- `models.py` - 数据库模型 (41个模型)
- `module_health_check.py` - 模块健康检查
- `performance_optimizer.py` - 性能优化
- `slo_engine.py` - SLO引擎
- `topology_engine.py` - 拓扑引擎
- `verifier.py` - 验证器
- `workflow_engine.py` - 工作流引擎

### 3. extensions/ - 扩展微服务 (1,009个Python文件)

**用途**: 独立的微服务扩展，采用插件化架构

**主要分类**:

#### 3.1 addons/ai-plus/ - AI Plus服务
- `knowledge_graph_service/` - 知识图谱服务
- `llm_router_service/` - LLM路由服务
- `rag_service/` - RAG服务

#### 3.2 addons/ai_plus/ - AI高级服务
- `access_control_service/` - 访问控制服务 (RBAC/ABAC)
- `automated_testing_service/` - 自动化测试服务
- `certificate_management_service/` - 证书管理服务
- `code_quality_service/` - 代码质量服务
- `compliance_monitoring_service/` - 合规监控服务
- `dependency_management_service/` - 依赖管理服务
- `environment_management_service/` - 环境管理服务
- `identity_management_service/` - 身份管理服务
- `knowledge_graph_service/` - 知识图谱服务
- `llm_router_service/` - LLM路由服务
- `rag_service/` - RAG服务
- `release_management_service/` - 发布管理服务
- `secret_management_service/` - 密钥管理服务

#### 3.3 addons/infrastructure/ - 基础设施服务
- `alert_rule_service/` - 告警规则服务
- `ansible_automation_service/` - Ansible自动化服务
- `api_standards_service/` - API标准服务
- `automated_deployment_service/` - 自动部署服务
- `automated_ops_service/` - 自动运维服务
- `backup_recovery_drill_service/` - 备份恢复演练服务
- `cache_optimization_service/` - 缓存优化服务
- `cache_service/` - 缓存服务
- `chaos_mesh_service/` - Chaos Mesh服务
- `cloud_monitoring_service/` - 云监控服务
- `config_service/` - 配置服务
- `data_access_service/` - 数据访问服务
- `data_standards_service/` - 数据标准服务
- `database_optimization_service/` - 数据库优化服务
- `datacenter_visualization_service/` - 数据中心可视化服务
- `fastapi_security_service/` - FastAPI安全服务
- `kubernetes_orchestration_service/` - K8s编排服务
- `open_source_license_service/` - 开源许可证服务
- `performance_monitoring_service/` - 性能监控服务
- `pgbackrest_backup_service/` - PgBackRest备份服务
- `plugin_market_service/` - 插件市场服务
- `plugin_system_service/` - 插件系统服务
- `postgresql_shard_service/` - PostgreSQL分片服务
- `qdrant_shard_service/` - Qdrant分片服务
- `redis_shard_service/` - Redis分片服务
- `service_mesh_service/` - 服务网格服务
- `terraform_iac_service/` - Terraform IaC服务
- `user_service/` - 用户服务
- `vector_retrieval_service/` - 向量检索服务
- `velero_backup_service/` - Velero备份服务

#### 3.4 addons/integrations/ - 集成服务
- `datadog_integration_service/` - Datadog集成服务
- `elasticsearch_audit_service/` - Elasticsearch审计服务
- `elk_stack_service/` - ELK Stack服务
- `github_repository_service/` - GitHub仓库服务
- `grafana_integration_service/` - Grafana集成服务
- `kafka_event_service/` - Kafka事件服务
- `message_queue_service/` - 消息队列服务
- `prometheus_integration_service/` - Prometheus集成服务

#### 3.5 addons/observability/ - 可观测性服务
- `distributed_tracing_service/` - 分布式追踪服务
- `log_aggregation_service/` - 日志聚合服务
- `metrics_monitoring_service/` - 指标监控服务
- `topology_service/` - 拓扑服务
- `tracing_service/` - 追踪服务

#### 3.6 addons/operations/ - 运维服务
- `capacity_planning_service/` - 容量规划服务
- `incident_response_service/` - 事件响应服务
- `incident_runbook_service/` - 事件手册服务
- `scenario_memory_service/` - 场景记忆服务
- `workflow_engine_service/` - 工作流引擎服务
- `workflow_service/` - 工作流服务

#### 3.7 addons/security/ - 安全服务
- `penetration_testing_service/` - 渗透测试服务
- `security_audit_service/` - 安全审计服务
- `security_scanning_service/` - 安全扫描服务
- `sqlalchemy_security_service/` - SQLAlchemy安全服务

#### 3.8 addons/documentation/ - 文档服务
- `sphinx_documentation_service/` - Sphinx文档服务

**每个微服务的标准结构**:
```
service_name/
├── __init__.py
├── main.py / main_app.py          # 服务入口
├── architecture.md               # 架构文档
├── README.md                     # 服务说明
├── config.py                     # 配置
├── schemas.py                    # 数据模型
├── cache.py                      # 缓存
├── retry.py                      # 重试逻辑
├── health_check.py               # 健康检查
├── metrics.py                    # 指标
├── grpc/                         # gRPC接口
│   ├── __init__.py
│   ├── server.py
│   └── client.py
├── k8s/                          # Kubernetes配置
│   ├── deployment.yaml
│   └── service.yaml
├── Dockerfile                    # Docker配置
├── docker-compose.yml            # Docker Compose配置
├── prometheus.yml                # Prometheus配置
└── tests/                        # 测试文件
```

### 4. tests/ - 测试文件 (552个Python文件)

**用途**: 单元测试、集成测试、E2E测试

**主要分类**:
- `api/` - API路由测试
- `core/` - 核心模块测试
- `test_*.py` - 根目录下的综合测试
- `integration/` - 集成测试
- `e2e/` - 端到端测试

**主要测试文件**:
- `test_alert_engine.py` - 告警引擎测试
- `test_ai_service.py` - AI服务测试
- `test_auth.py` - 认证测试
- `test_auto_heal.py` - 自动修复测试
- `test_performance_baseline.py` - 性能基准测试
- `test_ai_advanced_router_db.py` - AI高级路由数据库测试
- `test_*_real_branches.py` - 真实分支覆盖率测试

### 5. scripts/ - 脚本工具 (80个Python文件)

**用途**: 开发工具、部署脚本、测试脚本

**主要分类**:
- 性能测试脚本
- 代码分析脚本
- 数据库迁移脚本
- 配置验证脚本
- 覆盖率分析脚本

**主要脚本**:
- `analyze_performance_regression.py` - 性能回归分析
- `check_performance_gates.py` - 性能门禁检查
- `generate_coverage_badge.py` - 生成覆盖率徽章
- `migrate_memory_to_db.py` - 内存到数据库迁移
- `validate_config.py` - 配置验证
- `test_performance_integration.py` - 性能集成测试

### 6. docs/ - 文档目录

**用途**: 项目文档、架构文档、API文档

**主要文档**:
- `architecture/` - 架构文档
  - `full_7_layer_architecture.md` - 7层架构
  - `per_layer/` - 各层详细设计
- `api/` - API文档
  - `openapi.yaml` - OpenAPI规范
  - `openapi.json` - OpenAPI JSON
- `deployment/` - 部署文档
- `testing/` - 测试文档
- `logging/` - 日志文档
- `error_handling/` - 错误处理文档
- `configuration/` - 配置文档
- `contributing/` - 贡献指南
- `troubleshooting/` - 故障排除指南

### 7. config/ - 配置文件

**用途**: 环境配置

**主要文件**:
- `development.yaml` - 开发环境配置
- `staging.yaml` - 预发布环境配置
- `production.yaml` - 生产环境配置
- `performance.yaml` - 性能配置
- `kpi_slo_config.yaml` - KPI/SLO配置

### 8. services/ - 独立服务

**用途**: 独立运行的微服务

**主要服务**:
- `agent_orchestration_service/` - Agent编排服务
- `alert_service/` - 告警服务
- `audit_service/` - 审计服务
- `repair_service/` - 修复服务

### 9. frontend/ - 前端代码

**用途**: React/TypeScript前端应用

**主要结构**:
- `app/` - Next.js应用页面
- `components/` - React组件
- `__tests__/` - 前端测试
  - `components/` - 组件测试
  - `e2e/` - E2E测试
  - `visual/` - 视觉测试
  - `performance/` - 性能测试

### 10. monitoring/ - 监控配置

**用途**: 监控系统配置

**主要配置**:
- `prometheus/` - Prometheus配置
- `grafana/` - Grafana配置
- `alertmanager/` - Alertmanager配置
- `docker-compose.yml` - 监控栈Docker Compose

### 11. alembic/ - 数据库迁移

**用途**: 数据库版本管理和迁移

**主要文件**:
- `versions/` - 迁移版本
  - `001_phase3_initial_schema.py` - 初始schema
  - `002_add_ai_compliance_builder_models.py` - AI合规模型
  - `003_add_asset_management_models.py` - 资产管理模型
  - `004_add_capacity_planning_models.py` - 容量规划模型
  - `005_add_cost_management_models.py` - 成本管理模型
  - `006_add_change_management_models.py` - 变更管理模型
  - `007_add_ai_advanced_models.py` - AI高级模型
  - `008_add_collaboration_models.py` - 协作模型
  - `009_add_plugin_marketplace_models.py` - 插件市场模型
  - `010_add_business_impact_models.py` - 业务影响模型
  - `011_add_chaos_engineering_models.py` - 混沌工程模型

### 12. aiops_agent/ - CLI工具

**用途**: 命令行工具

**主要文件**:
- `cli.py` - CLI入口
- `__main__.py` - 主模块

### 13. sdk/ - Python SDK

**用途**: Python SDK

**主要文件**:
- `python/` - Python SDK实现

## 关键配置文件

### 顶层配置文件
- `README.md` - 项目说明
- `pyproject.toml` - Python项目配置
- `Dockerfile` - Docker配置
- `docker-compose.yml` - Docker Compose配置
- `.env.example` - 环境变量示例
- `.gitignore` - Git忽略文件
- `alembic.ini` - Alembic配置
- `pytest.ini` - pytest配置
- `.coveragerc` - 覆盖率配置
- `.flake8` - Flake8配置
- `.pre-commit-config.yaml` - Pre-commit配置
- `Makefile` - Make配置

### GitHub配置
- `.github/workflows/` - GitHub Actions工作流
  - `ci.yml` - CI工作流
  - `cd.yml` - CD工作流
  - `test.yml` - 测试工作流
  - `coverage.yml` - 覆盖率工作流
  - `security-scan.yml` - 安全扫描工作流
  - `performance-test.yml` - 性能测试工作流

### 监控配置
- `alertmanager/` - Alertmanager配置
- `alerts/` - 告警规则
- `loki-config/` - Loki配置
- `otel-config/` - OpenTelemetry配置

## 依赖关系

### 核心依赖关系
```
api/ → core/ → extensions/
tests/ → api/ + core/
scripts/ → core/ + api/
frontend/ → api/
services/ → core/ + extensions/
```

### 数据流关系
```
Frontend → API Routers → Core Business Logic → Database
              ↓
         Extensions (Microservices)
              ↓
         External Integrations
```

## 文件统计总结

| 目录 | Python文件数 | 主要用途 |
|------|-------------|----------|
| api/ | 149 | HTTP API路由 |
| core/ | 414 | 核心业务逻辑 |
| extensions/ | 1,009 | 微服务扩展 |
| tests/ | 552 | 测试代码 |
| scripts/ | 80 | 工具脚本 |
| services/ | ~50 | 独立服务 |
| **总计** | **2,442** | **完整项目** |

## 开发导航

### 新开发者入门路径
1. 阅读 `README.md` 了解项目概览
2. 查看 `docs/architecture/` 理解架构设计
3. 运行 `config/development.yaml` 配置开发环境
4. 从 `api/` 和 `core/` 开始阅读核心代码
5. 参考 `tests/` 了解使用方式
6. 使用 `scripts/` 中的工具辅助开发

### 功能开发路径
1. 在 `api/` 中添加新的路由
2. 在 `core/` 中实现业务逻辑
3. 在 `core/models.py` 中定义数据模型
4. 在 `alembic/versions/` 中创建数据库迁移
5. 在 `tests/` 中编写测试
6. 在 `docs/` 中更新文档

### 微服务开发路径
1. 在 `extensions/addons/` 中创建新服务
2. 按照标准服务结构组织代码
3. 实现gRPC和REST API
4. 添加Docker和K8s配置
5. 编写服务测试
6. 更新服务文档

## 维护指南

### 代码审查重点
- `api/` - API接口设计和错误处理
- `core/` - 业务逻辑正确性和性能
- `extensions/` - 微服务独立性和接口契约
- `tests/` - 测试覆盖率和测试质量

### 性能优化重点
- `core/ai_engine.py` - AI引擎性能
- `core/alert_engine.py` - 告警处理性能
- `api/` - API响应时间
- 数据库查询优化

### 安全审查重点
- `api/auth_router.py` - 认证授权
- `core/authentication.py` - 身份验证
- `extensions/addons/security/` - 安全服务
- 依赖包安全性

---

**文档版本**: 1.0  
**最后更新**: 2026-08-26  
**维护者**: AIOps SRE Agent Team
