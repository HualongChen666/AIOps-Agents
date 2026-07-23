# Alert Microservice

告警服务微服务化实现，按 `docs/document/task_list.md` 任务 24 设计。

## 服务拆分

1. **alert-collector** (`collector.py`)
   - 接收 Prometheus webhook (`POST /alerts`)
   - 解析、校验、入库，并发布到 `alerts.raw` 队列
2. **alert-processor** (`processor.py`)
   - 消费 `alerts.raw`，执行聚合、去重、路由、升级、分类、噪声抑制、模式识别
   - 将处理结果发布到 `alerts.routed` 队列
3. **alert-notifier** (`notifier.py`)
   - 消费 `alerts.routed`，调用 Webhook/Email 等通道发送通知

## 技术栈

- FastAPI
- Pydantic v2
- Redis / in-memory message queue fallback
- PostgreSQL / in-memory repository fallback
- Prometheus metrics
- Docker & Kubernetes

## 通信方式

- 异步消息队列 (`InMemoryMessageQueue` / Redis Streams)
- REST API 用于管理规则、健康检查、指标

## 目录结构

```text
services/alert_service/
├── collector.py          # 采集服务
├── processor.py          # 处理服务
├── notifier.py           # 通知服务
├── schemas.py            # Pydantic 模型
├── repository.py         # 告警仓储
├── mq.py                 # 消息队列
├── dedup.py              # 去重
├── aggregator.py         # 聚合
├── router.py             # 路由
├── escalator.py          # 升级
├── classifier.py         # 分类
├── noise_suppressor.py   # 噪声抑制
├── pattern_engine.py     # 模式识别
├── saga.py               # Saga 分布式事务
├── Dockerfile
├── docker-compose.yml
└── k8s/
```

## 启动

```bash
python -m services.alert_service.collector
python -m services.alert_service.processor
python -m services.alert_service.notifier
```

## 测试

```bash
pytest tests/services/alert_service -n auto --timeout=30
```
