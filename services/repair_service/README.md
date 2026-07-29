---
pack: core
enabled_by: N/A (always on)
docker_profile: core
core_dependency: True
---

# Repair Microservice

修复服务微服务化实现，对应 `docs/document/task_list.md` 任务 25。

## 服务拆分

1. **repair-orchestrator** (`orchestrator.py`)
   - 接收修复请求，维护状态机
   - 调用 executor 执行修复、verifier 验证结果
   - 触发 rollback 与 Saga 分布式事务

2. **repair-executor** (`executor.py`)
   - 解析/执行 Runbook（YAML）
   - 管理修复策略与规则引擎
   - 批量/并行执行修复步骤

3. **repair-verifier** (`verifier.py`)
   - 修复结果验证
   - 回滚执行
   - 审计日志与性能监控

## 技术栈

- FastAPI
- Pydantic v2
- Redis / in-memory message queue fallback
- Prometheus metrics
- Docker & Kubernetes
- gRPC（可选）
- Saga 分布式事务

## 启动

```bash
python -m services.repair_service.orchestrator
python -m services.repair_service.executor
python -m services.repair_service.verifier
```

## 测试

```bash
pytest tests/services/repair_service -n auto --timeout=30
```
