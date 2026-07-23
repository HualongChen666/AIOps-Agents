# 部署文档

## 1. 环境要求

### 1.1 硬件要求
- CPU: 至少 8 核心 (推荐 16 核心)
- 内存: 32 GB 以上 (推荐 64 GB)
- 存储: SSD，至少 200 GB 可用空间
- 网络: 千兆网卡，内部网络最低 1 Gbps 带宽

### 1.2 软件要求
- 操作系统: 64‑bit Linux (Ubuntu 22.04 LTS、CentOS 8/9、Alpine 3.18均可)
- Docker Engine: 20.10 以上，已启用 `--experimental`（用于多阶段构建）
- Docker Compose: 2.20 以上
- Kubernetes: 1.27+（可选，生产环境推荐使用）
- Python: 3.11（仅用于本地开发环境）
- PostgreSQL: 15+（用于持久化业务数据）
- Redis: 7+（用于缓存、会话、消息队列）
- Qdrant: 1.6+（向量检索）
- ClickHouse: 23.8+（时序数据、日志）

### 1.3 网络要求
- 端口开放：
  - `80/443` – HTTP/HTTPS（外部访问）
  - `8000` – FastAPI 服务（内部调试）
  - `6379` – Redis
  - `5432` – PostgreSQL
  - `6333` – Qdrant
  - `9000` – ClickHouse
- 防火墙：仅对内部子网开放数据库与缓存端口，外部仅暴露 HTTP/HTTPS

## 2. 安装步骤

### 2.1 克隆代码仓库
```bash
git clone https://gitlab.com/your-org/aiops-agent.git
cd aiops-agent
```

### 2.2 初始化子模块（若有）
```bash
git submodule update --init --recursive
```

### 2.3 环境变量配置
复制示例配置并根据实际情况调整：
```bash
cp .env.example .env
# 使用编辑器打开 .env，根据实际部署填写以下关键变量
# DATABASE_URL, REDIS_URL, QDRANT_URL, CLICKHOUSE_URL, JWT_SECRET_KEY, etc.
```

### 2.4 依赖安装（仅本地开发/测试）
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2.5 数据库初始化
```bash
alembic upgrade head   # 创建/迁移 PostgreSQL 表结构
```

### 2.6 第三方服务准备
- **Qdrant**：确保已创建对应的 collection（示例脚本位于 `scripts/qdrant_init.py`）
- **ClickHouse**：创建所需的数据库与表（脚本 `scripts/clickhouse_init.sql`）

## 3. 部署步骤

### 3.1 开发环境部署（Docker Compose）
```bash
docker compose -f docker-compose.dev.yml up -d
```
- 该组合文件以 `dev` 配置启动所有服务，开启 hot‑reload（FastAPI 的 `--reload`）
- 访问 http://localhost 为 Swagger UI

### 3.2 测试环境部署（Kubernetes）
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml   # 包含 .env 内容的 ConfigMap
kubectl apply -f k8s/secret.yaml      # Sensitive credentials
kubectl apply -f k8s/statefulset.yaml # PostgreSQL, Redis, ClickHouse, Qdrant
kubectl apply -f k8s/deployment.yaml  # FastAPI + Workers
kubectl apply -f k8s/ingress.yaml     # Ingress 暴露 HTTP/HTTPS
```
- 所有资源使用 `aiops` 命名空间，便于环境隔离
- 通过 `kubectl port-forward svc/aiops-api 8080:80` 本地调试

### 3.3 生产环境部署（Helm Chart）
```bash
helm repo add aiops https://your-org.github.io/aiops-helm
helm upgrade --install aiops aiops/aiops-agent \
  --namespace prod \
  --set image.tag=latest \
  --set env.SECRET_KEY=$(openssl rand -hex 32) \
  --set persistence.enabled=true
```
- 推荐使用 `values-prod.yaml` 进行细粒度配置（副本数、资源限制、日志采集）
- 支持滚动升级、蓝绿发布以及 Canary

## 4. 部署验证

### 4.1 健康检查
```bash
curl -s -o /dev/null -w "%{http_code}" http://<host>/health
# 预期返回 200
```
### 4.2 组件连通性
- **PostgreSQL**：`psql $DATABASE_URL -c "SELECT 1;"`
- **Redis**：`redis-cli -u $REDIS_URL ping`
- **Qdrant**：`curl $QDRANT_URL/collections` (返回 collections 列表)
- **ClickHouse**：`clickhouse-client --query "SELECT 1"`
### 4.3 功能验证（Smoke Test）
执行项目自带的 smoke‑test 脚本：
```bash
python scripts/smoke_test.py --host <host>
```
脚本会依次调用健康、认证、异常检测、自动修复等关键 API，若全部返回 `success` 则认为部署成功。

## 5. 故障排查

| 场景 | 常见原因 | 排查步骤 |
|------|----------|----------|
| API 404/502 | Service 未就绪或 Ingress 配置错误 | `kubectl get pods -n <ns>` 检查容器状态；`kubectl describe ingress` 查看规则；`kubectl logs <pod>`
| 数据库连接失败 | 环境变量 `DATABASE_URL` 错误、网络策略阻塞 | `echo $DATABASE_URL` → `psql $DATABASE_URL` 检查是否能手动连接；查看 `NetworkPolicy` 是否放行
| Redis 超时 | Redis 实例资源不足、maxmemory 达上限 | `redis-cli info memory`；检查 Pod 资源 limit/requests；适当调高 `maxmemory`
| Qdrant 向量检索慢 | collection 未创建索引、硬件 I/O 受限 | `curl $QDRANT_URL/collections/<col>/info` 检查 `index` 配置；使用 `iostat` 观察磁盘
| ClickHouse 写入慢 | 表分区不合理、batch 大小过小 | 查看 `system.metrics` 中 `Query`、`Insert` 时间；调整 `INSERT` 批次大小

### 5.1 常用日志位置
- Docker Compose: `./logs/<service>.log`
- Kubernetes: `kubectl logs -n <ns> <pod> -c <container>`
- Helm: `helm get values aiops -n prod`

### 5.2 监控告警
- Prometheus 采集 `process_cpu_seconds_total`、`http_request_duration_seconds`
- Alertmanager 已内置以下告警规则：
  - `HighCPUUsage`（CPU > 80% 持续 5min）
  - `ServiceDown`（Endpoint 返回非200）
  - `DBConnectionError`（PostgreSQL 连接错误次数 > 10）

## 6. 文档评审

- 本文档已通过技术评审（2026‑07‑09）。
- 如需更新，请在 `docs/deployment/README.md` 中对应章节提交 PR。
