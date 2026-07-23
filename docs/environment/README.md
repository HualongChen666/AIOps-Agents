# 环境变量文档

本文档说明 AIOps Agent 项目中环境变量的配置、加载、使用和安全管理。

## 环境变量概述

环境变量是运行时为应用提供敏感信息和环境相关配置的主要方式。项目使用 `pydantic-settings` 和 `python-dotenv` 加载环境变量。

## 环境变量列表

项目支持的环境变量主要来自 `core/config_models.py` 中 `Field` 的 `alias` 定义，例如：

- `POSTGRES_HOST`、`POSTGRES_PORT`、`POSTGRES_USER`、`POSTGRES_PASSWORD`
- `REDIS_HOST`、`REDIS_PORT`、`REDIS_PASSWORD`
- `JWT_SECRET_KEY`、`JWT_ALGORITHM`
- `OPENAI_API_KEY`、`AI_BASE_URL`
- `METRICS_ENABLED`、`TRACING_ENABLED`

完整列表请参考项目根目录下的 `.env.example`。

## 环境变量使用

1. 复制 `.env.example` 为 `.env`。
2. 按运行环境填充变量值。
3. 应用启动时 `ConfigManager` 会自动通过 `python-dotenv` 加载 `.env`。

## 环境变量优先级

配置加载优先级（从高到低）：

1. 操作系统环境变量
2. `.env` 文件
3. YAML 配置文件（`config/*.yaml`）
4. `pydantic-settings` 字段默认值

## 环境变量安全

- 不要将 `.env` 文件或包含真实密钥的 YAML 提交到 Git。
- 生产环境使用 Kubernetes Secrets、CI/CD 变量或 Vault。
- 敏感字段在 `ConfigManager.get_config_dict()` 中默认被排除。

## 环境变量验证

运行 `python scripts/validate_config.py` 可检查必填环境变量是否已设置。

## 最佳实践

- 按环境维护 `.env.development`、`.env.staging`、`.env.production`。
- 使用 `pydantic-settings` 的 `env_prefix` 实现分组管理。
- 配置变更需记录审计日志，必要时支持回滚。
