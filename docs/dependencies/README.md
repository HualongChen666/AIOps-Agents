# 依赖管理文档

本文档说明 AIOps Agent 项目的依赖架构、管理流程和安全最佳实践。

## 依赖概述

项目使用 `pip` 和 `requirements.txt` 管理运行依赖，同时在 `pyproject.toml` 中维护 `tool.poetry` 配置，支持逐步迁移到 Poetry。

## 依赖列表

主要依赖包括：

- **Web 框架**：FastAPI、uvicorn
- **数据库**：SQLAlchemy、asyncpg、alembic
- **缓存**：redis
- **配置**：pydantic、pydantic-settings、python-dotenv
- **AI/ML**：openai、langchain、anthropic
- **监控**：prometheus-client、OpenTelemetry

完整依赖见 `requirements.txt` 和 `pyproject.toml`。

## 依赖管理

### 添加依赖

在 `requirements.txt` 中追加并按功能分组。若使用 Poetry：

```bash
poetry add <package>
poetry lock
```

### 更新依赖

```bash
pip install -r requirements.txt --upgrade
```

### 移除依赖

从 `requirements.txt` 和 `pyproject.toml` 中移除对应行，并重新生成 `poetry.lock`。

## 依赖安全

- 使用 `bandit` 和 `safety` 扫描依赖漏洞。
- CI/CD 中运行 `safety check`。
- 固定主版本号，避免自动升级破坏兼容性。

## 依赖最佳实践

- 运行依赖与开发依赖分组存放。
- 使用 `poetry.lock` 锁定版本，确保环境一致。
- 定期使用 `pip-audit` 或 `safety` 检查漏洞。

## 依赖 FAQ

- **requirements.txt 与 poetry 是否会冲突**：当前 `requirements.txt` 为主源，`pyproject.toml` 作为迁移目标，保持同步即可。
- **lock 文件多久更新一次**：当新增或升级依赖时更新。
