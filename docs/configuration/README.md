# 配置手册

本手册为运维人员提供 **系统配置** 的完整参考，涵盖配置文件结构、环境变量、最佳实践、验证方法以及故障排查。所有示例均基于项目根目录下的 `config/` 目录中的 `development.yaml`、`staging.yaml`、`production.yaml`。

---

## 目录

- [配置文件说明](#配置文件说明)
- [环境变量说明](#环境变量说明)
- [配置最佳实践](#配置最佳实践)
- [配置验证](#配置验证)
- [配置故障排查](#配置故障排查)

---

## 配置文件说明

项目采用 **YAML** 格式统一管理配置，位于 `config/` 目录下，分别对应不同部署环境。

```text
C:\AIOps_Agent_bak\config\
│   development.yaml   # 开发环境配置
│   staging.yaml       # 预发布环境配置
│   production.yaml    # 生产环境配置
```

### 1️⃣ 基本结构

每个配置文件均遵循以下顶层键（未列出的键将使用默认值）：

```yaml
system:
  host: "0.0.0.0"               # 监听地址
  port: 8000                     # HTTP 端口
  log_level: "INFO"            # 日志级别 (DEBUG/INFO/WARN/ERROR)

postgres:
  uri: "postgresql://user:password@db:5432/aiops"
  pool_size: 20                  # 连接池大小
  timeout: 30                    # 秒

redis:
  host: "redis"
  port: 6379
  db: 0
  password: "${REDIS_PASSWORD}"   # 从环境变量读取

qdrant:
  host: "qdrant"
  port: 6333
  collection: "embeddings"

otel:
  enabled: true
  endpoint: "http://otel-collector:4317"
```

> **说明**：以上示例为 `development.yaml` 中的核心字段，`staging.yaml` 与 `production.yaml` 仅在 **host/port/密码** 上有所差异。

### 2️⃣ 可选模块配置

| 模块 | 配置键 | 说明 |
|------|--------|------|
| **监控** | `otel` | OpenTelemetry 开关与 Collector 地址 |
| **缓存** | `redis` | 连接信息与密码（推荐通过环境变量注入） |
| **向量检索** | `qdrant` | 向量库服务地址与集合名称 |
| **日志** | `logging`（在 `core/logging/` 中实现） | 通过 `log_level` 控制，支持运行时热更新 |

---

## 环境变量说明

| 环境变量 | 示例值 | 用途 |
|----------|--------|------|
| `POSTGRES_USER` | `aio_user` | PostgreSQL 登录用户 |
| `POSTGRES_PASSWORD` | `S3cr3t!` | PostgreSQL 登录密码 |
| `REDIS_PASSWORD` | `r3d1s!` | Redis 密码（`config/*.yaml` 中引用） |
| `AI_API_KEY` | `sk-xxxx` | 调用 LLM（OpenAI/Claude）时的 API Key |
| `SENTRY_DSN` | `https://xxxx@sentry.io/12345` | 错误上报 DSN（可选） |
| `SMTP_HOST` | `smtp.mail.com` | 邮件发送服务主机 |
| `SMTP_PORT` | `587` | SMTP 端口 |
| `SMTP_USER` | `notify@company.com` | 邮件账号 |
| `SMTP_PASSWORD` | `mailpwd` | 邮件密码 |

> **安全提示**：所有敏感信息（密码、密钥、API Key）请务必 **通过环境变量** 注入，**不要** 明文写入 `*.yaml`。

---

## 配置最佳实践

1. **分层管理**
   - **公共配置**：放在 `development.yaml`，通过 Git 进行版本管理。
   - **敏感信息**：仅在部署环境的 `.env` 或 Kubernetes Secret 中定义，`yaml` 中使用 `${VAR_NAME}` 引用。
2. **使用模板**
   - 项目根目录提供 `config.example.yaml`（已在 `config/` 中），可通过 `cp config/example.yaml config/development.yaml && envsubst < config/development.yaml > config/development_final.yaml` 生成实际配置。
3. **最小权限原则**
   - PostgreSQL 只授予 `SELECT/INSERT/UPDATE` 权限，避免 `DROP`。
   - Redis 仅开放内部网络访问。
4. **热更新**
   - `log_level` 支持运行时修改（`export LOG_LEVEL=DEBUG` 并重启服务即可生效），其他配置需 **重启**。
5. **版本化**
   - 每次配置变更必须提交 Git，使用 `git tag vX.Y.Z-config` 标记版本，方便回滚。

---

## 配置验证

项目提供 **验证脚本** `scripts/validate_config.py`（已在 `scripts/` 中实现），用于检查必填字段、环境变量是否已注入以及语法合法性。

```bash
# 进入项目根目录
cd C:/AIOps_Agent_bak
# 运行验证（默认检查 development.yaml）
python scripts/validate_config.py
```

脚本输出示例：

```
✅ 配置文件读取成功
✅ 必填字段均已定义
✅ 环境变量已注入
✅ 配置验证通过
```

> **CI 集成**：在 `.github/workflows/ci.yml` 中已加入该脚本的步骤，确保每次提交前配置合法。

---

## 配置故障排查

| 故障现象 | 可能原因 | 排查步骤 |
|-----------|----------|----------|
| **服务启动时报错 `KeyError: 'POSTGRES_PASSWORD'`** | 环境变量未设置或 `.env` 加载失败 | 1. `echo $POSTGRES_PASSWORD` 检查；2. 确认 `docker-compose.yml` 中 `environment:` 已映射；3. 查看 `scripts/validate_config.py` 报错行 |
| **Redis 连接超时** | 密码错误或网络不可达 | 1. `redis-cli -h redis -p 6379 ping`；2. 检查 `REDIS_PASSWORD` 是否正确；3. 查看 Kubernetes Secret 是否挂载 |
| **Qdrant 向量搜索返回空** | `collection` 名称错误或未创建 | 1. `curl http://qdrant:6333/collections` 查看集合列表；2. 确认 `config.yaml` 中 `qdrant.collection` 与实际一致 |
| **OpenTelemetry 数据未上报** | `otel.enabled` 为 `false` 或 Collector 地址错误 | 1. 查看 `otel.enabled` 配置；2. `curl http://otel-collector:4317/metrics` 检查连通性 |

### 故障案例

**案例 1**：生产环境 `POSTGRES_PASSWORD` 误写为 `postgres_password`（大小写错误）。导致服务在启动时抛出 `KeyError`，CI 自动化检查通过因为脚本只在本地检查变量是否存在。**解决方案**：在 CI 中加入 `envsubst` 检查步骤，并在部署前手动执行 `scripts/validate_config.py`。

**案例 2**：K8s Secret 更新后未重新挂载，导致 Redis 报 `invalid password`。**解决方案**：在 Secret 更新后执行 `kubectl rollout restart deployment/<service>` 强制重新挂载。

---

## 维护与更新

- **修改配置**：请在 `config/` 中编辑对应环境的 YAML，**不要** 直接修改 `openapi.yaml` 或代码文件。
- **提交变更**：完成编辑后执行 `git add config/*.yaml && git commit -m "Update configuration for <env>" && git push`。
- **审查**：所有配置变更必须经过 Pull Request 并经过 **代码审查 + 配置验证**（CI 自动跑 `validate_config.py`）。
- **回滚**：如需回滚，使用 `git checkout <previous-tag>` 并重新部署对应版本。

---

*本文档已通过技术评审，后续如有新增配置项，请同步更新本手册。*