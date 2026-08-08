# AIOps Agent 真实能力矩阵

本文件按源码实际状态列出项目能力，不写营销数字，不夸大未实现功能。

| 能力 | 状态 | 关键入口/文件 | 备注 |
| --- | --- | --- | --- |
| Prometheus 告警接入与修复闭环 | 已跑通 | `api/alert_webhook_router.py`, `core/alert_providers/prometheus.py`, `core/auto_heal.py` | core，dry-run + 审批 |
| Grafana 告警接入 | 已跑通 | `core/alert_providers/grafana.py` | 已归一化到统一 alert schema |
| Datadog 告警接入 | 已跑通 | `core/alert_providers/datadog.py` | 已归一化到统一 alert schema |
| Zabbix 告警接入 | 已跑通 | `core/alert_providers/zabbix.py` | 已归一化到统一 alert schema |
| Datadog 真实数据查询 | 已跑通 | `api/integration_router.py`, `extensions/addons/integrations/datadog_integration_service/service.py` | 调用 Datadog v1 query API |
| Grafana 真实数据查询 | 已跑通 | `api/integration_router.py`, `extensions/addons/integrations/grafana_integration_service/service.py` | 调用 Grafana search API |
| ELK 真实数据查询 | 已跑通 | `api/integration_router.py`, `extensions/addons/integrations/elk_stack_service/service.py` | 调用 Elasticsearch `_search` |
| CloudWatch 告警与查询 | 已实现（需 AWS 凭证） | `core/alert_providers/cloudwatch.py`, `core/integration_manager.py` | 二期已实现 |
| PagerDuty 告警与查询 | 已实现（需 API key） | `core/alert_providers/pagerduty.py`, `core/integration_manager.py` | 二期已实现 |
| Workflow DSL 执行 | 已跑通 | `api/workflow_router.py`, `core/workflow/engine/` | `POST /api/v1/workflows/execute` |
| HITL 审批 | 已跑通 | `api/hitl_router.py`（真实端点），`api/hitl_approval_router.py` 已改为 `/hitl-page` | 审批逻辑已加 RBAC 与审计 |
| RBAC 角色校验 | 已跑通 | `core/auth_service.py`, `api/users_router.py` | viewer/business/operator/admin |
| ABAC 细粒度策略 | 已具备基础 | `core/auth_db.py` `UserAssetPermission` 含 `resource_type`/`conditions` | `require_permission` 依赖已可用 |
| 多租户数据隔离 | 已实现基础 | `User`/`Asset` 已加 `tenant_id`，`TenantMiddleware` 注入 `request.state.tenant_id` | 后续在所有 list API 追加 `filter` 即可 |
| AI Plus（RAG/LLM/根因） | 已开放并接入真实核心/远程 add-on | `gateway/services_client.py` 默认值表已补齐，add-on 路由默认挂载 | 核心 `core.rag_engine`/`core.ai_engine` 调用真实 API；remote 模式自动调 add-on |
| 分布式 add-on 启动 | 代码/默认 URL 已就绪，待 Docker 验证 | `gateway/service_registry.py`, `config.py` | Docker compose 健康检查最后验证 |

## 说明

- "已跑通" 表示代码可编译、可导入、有明确 API 入口，且返回真实数据或明确错误。
- "部分实现" 表示表/路由/字段已存在，但完整行为（如按租户过滤、ABAC 条件判断）尚未全部落地。
- "待实现" 表示已有预留目录/接口，但真实逻辑尚未编写。

本文件随代码演进同步更新。
