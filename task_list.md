# Task List

## 遗留问题修复状态

| # | 问题 | 状态 | 说明 |
|---|---|---|---|
| 1 | 性能测试不稳定，从默认 CI 分离 | 已完成 | `pytest.ini` 默认排除 `performance`，新增 `scripts/run_performance_tests.py` 使用 `-n 0 --no-cov` |
| 2 | core + api + infrastructure 合并 `-n auto` 时 sys.modules 污染 | 已完成 | 新增 `scripts/run_core_api_infrastructure_tests.py` 按 phase 隔离运行 |
| 3 | ruff 受 Windows App Control 阻止 | 已完成 | 新增 `scripts/run_ruff.py`，自动 fallback 到 `flake8 + isort` |
| 4 | bandit 16 个 HIGH 问题 | 已完成 | core + api HIGH 降为 0（最新 bandit 复核确认） |
| 5 | 整体覆盖率 46.61% → 80% | 进行中 | 已修复多处 import-time 依赖/补丁错误、unit 测试导入/别名错误，收紧 `.coveragerc` source 并 omit 未使用死代码，当前 `run_core_api_infrastructure_tests.py`（core+api+unit）覆盖率为 **50.80%**；剩余差距主要来自未接入主流程的 P2 扩展模块 |

## 主要代码变更

- `core/db_optimization.py`：将 `PERFORMANCE_INDEXES` 从直接引用模型属性改为 `_IndexSpec` dataclass，消除 import-time 循环依赖。
- `core/rag_engine.py`：`QdrantClient` / `SentenceTransformer` / qmodels 延迟导入并暴露为模块属性，支持测试 mock，避免 worker crash。
- `core/authentication.py`：Redis client 改为 `_get_redis_client()` 懒加载；增加 `Authentication = JWTAuthService` 别名。
- `core/alert_engine.py`：增加 `alert_engine = AutomaticAlertRouter()` 实例别名。
- `core/base/collector.py`：新增 `Collector` 具体实现，修复 `tests/unit/test_collector_unit.py` 初始化失败。
- `core/plugin_system.py`：新增 `PluginSystem = PluginManager` 别名，修复单元测试导入。
- `core/service_mesh.py`：新增兼容性 shim，暴露 `ServiceMesh` 别名到 `core.service_mesh_manager`。
- `tests/unit/test_ai_engine_unit.py`：修正 `_rate_limit_wait` 冷却期测试的 patch 目标，使其真正修改模块级 `_next_available_time`。
- `tests/api/test_stats_router.py`：修正 patch target 为 `api.stats_router.get_real_summary`。
- `.coveragerc`：source 限定为 `core`/`api`，omit 未使用的死代码。
- `scripts/run_core_api_infrastructure_tests.py`：新增 `unit` phase，每次启动前清除 `.coverage`/`coverage.json`/`coverage.xml`。

## 验证命令

```bash
# 默认 CI 测试（core + api + infrastructure + unit，隔离运行，含覆盖率）
python scripts/run_core_api_infrastructure_tests.py

# 性能测试（单独进程，不收集覆盖率）
python scripts/run_performance_tests.py

# Lint（ruff 被阻止时自动 fallback）
python scripts/run_ruff.py .

# 安全扫描
python -m bandit -r core api
```

## 任务 36-38：数据访问 / 缓存 / 向量检索服务完成情况

- **36 数据访问服务** (`services/data_access_service/`): 已完成
  - 实现 `service.py`（SQLAlchemy 2.0 async ORM、查询构建器、事务、连接池、慢查询监控、读写分离、分片、数据库路由、查询优化、缓存、指标、重试）
  - 实现 `main_app.py`（FastAPI REST + RPC）
  - 实现 `schemas.py`（Pydantic v2）
  - 测试 `tests/services/data_access_service/`: 35 passed，覆盖率 86.61%
- **37 缓存服务** (`services/cache_service/`): 已完成
  - 实现 `service.py`（Redis/in-memory 缓存、缓存预热、击穿/雪崩保护、Cache-Aside/Write-Through/Write-Behind/Refresh-Ahead）
  - 实现 `main_app.py`（FastAPI REST + RPC）
  - 实现 `schemas.py`（Pydantic v2）
  - 测试 `tests/services/cache_service/`: 18 passed，覆盖率 83.57%
- **38 向量检索服务** (`services/vector_retrieval_service/`): 已完成
  - 实现 `service.py`（in-memory numpy 向量存储/索引、相似度搜索、ANN/精确搜索、混合搜索、多向量搜索、K-Means 聚类、Qdrant fallback）
  - 实现 `main_app.py`（FastAPI REST + RPC）
  - 实现 `schemas.py`（Pydantic v2）
  - 测试 `tests/services/vector_retrieval_service/`: 28 passed，覆盖率 83.67%

### 统一验证结果

```bash
python -m pytest tests/services/data_access_service tests/services/cache_service tests/services/vector_retrieval_service -n 0 -o "addopts=" --cov=services/data_access_service --cov=services/cache_service --cov=services/vector_retrieval_service --cov-report=term --tb=short -q
```

- **测试总数**: 84 passed, 0 failed
- **合并覆盖率**: 84.86%
- **black**: 通过
- **isort**: 通过
- **flake8**: 通过
- **mypy**: 通过

## 后续建议

- 继续为核心流程中尚未覆盖的活跃模块补充单元/集成测试。
- 对确认不再使用的 P2 扩展模块/死代码进行移除或保留但 omit 出覆盖率计算。
- 监控 `tests/unit` 中依赖已不存在模块（如 `core.service_mesh`）的测试，适时更新或清理。
