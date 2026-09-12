# 页面分类台账：用户端 vs 开发/运维端后端功能

生成时间：2026-09-12 ｜ 依据：frontend/app 下全部 page.tsx（实测 539 个）+ lib/nav-complete.ts 产品导航分组 + 后端 openapi 端点实测

## 分类规则（用户决策）
- **USER 用户端业务页**：需要展示给用户的前端页面 → 必须满足前端页面/功能模块/路由调用等业务逻辑（真实可交互）。
- **DEVOPS 开发/运维端后端功能**：用户不需要的前端展示 → 先后端功能满足调用（保证真实后端能力/接口可用即可，不追求业务前端页）。

## 汇总
- 总计 **539** 页；USER **445**（其中 74 行模板页 137）；DEVOPS **94**（其中 74 行模板页 56）。

## DEVOPS（开发/运维端后端功能）明细 —— 共 94 页

### 测试自动化/覆盖率框架（开发者·QA·CI 内部）（19）
- `/test-coverage` — 测试覆盖率（446行，3端点）
- `/test-management` — 测试管理（550行，6端点）
- `/test/test-automation-advanced` — 高级测试自动化（458行，4端点）
- `/testing/automated-tests` — 自动化测试（74行，1端点）
- `/testing/code-coverage` — 代码覆盖率（74行，1端点）
- `/testing/input-validation` — 输入验证（74行，1端点）
- `/testing/integration-testing` — 集成测试（74行，1端点）
- `/testing/integration-validator` — 集成验证（74行，1端点）
- `/testing/test-automation` — 测试自动化（74行，1端点）
- `/testing/test-coverage` — 测试覆盖率（74行，1端点）
- `/testing/test-framework` — 测试框架（74行，1端点）
- `/testing/test-framework-advanced` — 测试框架高级配置（1026行，4端点）
- `/testing/test-management` — 测试管理（74行，1端点）
- `/testing/test-reports` — 测试报告（74行，1端点）
- `/testing/test-results` — 测试结果（74行，1端点）
- `/testing/test-scheduling` — 测试调度（74行，1端点）
- `/testing/testing-system` — 测试系统（74行，1端点）
- `/testing/type-validation` — 类型验证（74行，1端点）
- `/testing/verifier` — 验证器（74行，1端点）

### 国际化基建（资源/格式化/适配器/翻译）（11）
- `/i18n` — 国际化管理（202行，3端点）
- `/i18n/currency-format` — 货币格式（74行，1端点）
- `/i18n/date-format` — 日期格式（74行，1端点）
- `/i18n/formatting` — 格式化（74行，1端点）
- `/i18n/i18n-management` — 国际化管理（74行，1端点）
- `/i18n/language-support` — 语言支持（74行，1端点）
- `/i18n/locale-switching` — 语言切换（74行，1端点）
- `/i18n/localization-adapter` — 本地化适配器（74行，1端点）
- `/i18n/localization-resource` — 本地化资源（74行，1端点）
- `/i18n/resource-management` — 资源管理（74行，1端点）
- `/i18n/translation` — 翻译管理（74行，1端点）

### 文档生成工具链（Sphinx/模板/文档API，开发者）（8）
- `/docs/doc-generation` — 文档生成（74行，1端点）
- `/docs/doc-generator` — 文档生成器（74行，1端点）
- `/docs/document-creation` — 文档创建（74行，1端点）
- `/docs/document-list` — 文档列表（74行，1端点）
- `/docs/documentation-api` — 文档API（74行，1端点）
- `/docs/documentation-management` — 文档管理（74行，1端点）
- `/docs/sphinx` — Sphinx文档（74行，1端点）
- `/docs/template-management` — 模板管理（74行，1端点）

### 前端基建（主题/缓存/性能/无障碍/偏好/集成）（8）
- `/frontend/accessibility` — 无障碍支持（74行，1端点）
- `/frontend/cache-strategy` — 缓存策略（74行，1端点）
- `/frontend/frontend-enhancement` — 前端增强（74行，1端点）
- `/frontend/frontend-integration` — 前端集成（74行，1端点）
- `/frontend/performance-optimization` — 性能优化（74行，1端点）
- `/frontend/theme-management` — 主题管理（74行，1端点）
- `/frontend/ui-experience` — UI体验（74行，1端点）
- `/frontend/user-preferences` — 用户偏好（74行，1端点）

### UI 组件/开发演示页（前端基建）（7）
- `/accessibility` — 可访问性设置（360行，0端点）
- `/advanced-table` — 高级数据表格（400行，1端点）
- `/animation` — 实时指标动画（386行，1端点）
- `/charts` — 指标趋势看板（318行，1端点）
- `/forms` — 创建变更请求（211行，1端点）
- `/frontend-advanced` — 前端高级功能（773行，5端点）
- `/frontend-enhancement` — 前端增强（958行，10端点）

### GraphQL API 层（开发者接口）（7）
- `/graphql/graphql-api` — GraphQL接口（74行，1端点）
- `/graphql/graphql-auth` — GraphQL认证（74行，1端点）
- `/graphql/graphql-dataloader` — GraphQL DataLoader（214行，3端点）
- `/graphql/graphql-query` — GraphQL查询（74行，1端点）
- `/graphql/graphql-resolvers` — GraphQL解析器（74行，1端点）
- `/graphql/graphql-schema` — GraphQL Schema（74行，1端点）
- `/graphql/graphql-subscription` — GraphQL订阅（74行，1端点）

### RAG/AI 内部组件（向量化/检索/重排/融合/索引）（5）
- `/ai/document-index` — 文档索引（195行，3端点）
- `/ai/fusion` — 结果融合（194行，2端点）
- `/ai/reranker` — 重排序器（207行，2端点）
- `/ai/retriever` — 检索器（219行，2端点）
- `/ai/vectorizer` — 向量化处理（235行，3端点）

### AI 工作流引擎内部（DSL/节点/执行器/可视化）（5）
- `/ai/langgraph-dsl` — DSL语言定义（226行，3端点）
- `/ai/langgraph-executor` — 工作流执行器（226行，3端点）
- `/ai/langgraph-nodes` — 节点类型（210行，2端点）
- `/ai/langgraph-visualizer` — 工作流可视化（220行，4端点）
- `/ai/langgraph-workflow` — LangGraph工作流（188行，3端点）

### 数据库基础设施（高可用/复制/分片，运维端后端能力）（5）
- `/database/failover` — 故障转移（74行，1端点）
- `/database/postgresql-shard` — PostgreSQL分片（74行，1端点）
- `/database/read-write-routing` — 读写分离（74行，1端点）
- `/database/replication` — 数据库复制（74行，1端点）
- `/database/sharding` — 分片管理（74行，1端点）

### 模型训练/优化（开发者·ML 内部）（3）
- `/ai/deep-learning` — 深度学习模型（183行，3端点）
- `/ai/model-fine-tuning` — 模型微调（292行，4端点）
- `/ai/model-optimization` — 模型优化（215行，3端点）

### gRPC 服务层（开发者接口）（3）
- `/grpc/grpc-health` — gRPC健康检查（74行，1端点）
- `/grpc/grpc-management` — gRPC服务管理（74行，1端点）
- `/grpc/grpc-service` — gRPC服务（74行，1端点）

### 文档生成/管理工具（开发者）（2）
- `/documentation/doc-generator` — 文档生成器（246行，6端点）
- `/documentation/documentation-advanced` — 文档管理高级（572行，4端点）

### 系统初始化/认证入口（非业务展示页）（2）
- `/login` — LoginPage（94行，0端点）
- `/setup` — SetupPage（70行，1端点）

### API 文档（开发者）（1）
- `/api-documentation` — API文档（381行，7端点）

### 变更请求构建器（内部工具）（1）
- `/builder` — 变更请求管理（286行，1端点）

### UI 图表组件（前端基建）（1）
- `/charts/chart-aggregation` — 图表聚合（508行，5端点）

### 本地化基建（1）
- `/localization/localization-advanced` — 高级本地化管理（534行，6端点）

### 性能集成测试（测试工具）（1）
- `/performance/integration-testing` — 集成测试（74行，1端点）

### 插件开发（开发者工具）（1）
- `/plugin-development` — 插件开发（545行，6端点）

### MCP 协议接入（开发者工具）（1）
- `/plugin/mcp` — MCP协议管理（531行，5端点）

### 插件开发高级（开发者工具）（1）
- `/plugin/plugin-development-advanced` — 高级插件开发（740行，5端点）

### 插件 SDK（开发者工具）（1）
- `/plugin/plugin-sdk` — 插件SDK（774行，5端点）

## 待确认边界（USER/DEVOPS 归类需你拍板）
- `/ai/langgraph-workflow` — 工作流编排（用户编排 or 引擎内部？）
- `/disaster/pgbackrest` — pgBackRest 备份引擎（运维端 or 用户端？）
- `/disaster/velero` — Velero 备份引擎（运维端 or 用户端？）
- `/documentation` — 平台文档展示（用户 or 开发者？）
- `/frontend/user-preferences` — 用户偏好（用户端设置 or 前端基建？）
- `/maturity` — 组织成熟度评估（管理端 or 用户端？）
- `/vector/collection-management` — 向量库集合运维
- `/vector/qdrant` — Qdrant 引擎管理
- `/vector/vector-service` — 向量服务部署
- `/vector/vector-sharding` — 向量分片运维

## 对 task #11（5 个数据库页）的判定
5 页 `failover / replication / read-write-routing / sharding / postgresql-shard` 均归入 **DEVOPS 运维端后端能力**。后端实测：
- `core/db_replication.py`：configure_replication / get_replication_status / perform_failover / promote_replica_to_primary / check_replica_health → 覆盖 replication、failover
- `core/db_read_write_router.py`：ReadWriteRouter / get_read_write_router → 覆盖 read-write-routing
- `modules/high_availability/multi_region.py`：MultiRegionManager / DataSyncManager → 多区域
- 无任何 sharding 专用后端模块（仅 elasticsearch shard），且 openapi 无 shard/replication/failover/routing 业务端点。
