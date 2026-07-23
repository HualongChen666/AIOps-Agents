# CI/CD 文档

本文档说明 AIOps Agent 项目的持续集成、持续部署流程和配置。

## CI/CD 概述

项目使用 GitHub Actions 作为 CI/CD 平台，自动化测试、代码质量检查、安全扫描和部署。

## CI/CD 架构

- `.github/workflows/*.yml` 定义工作流。
- 工作流包括：测试、代码质量、安全检查、构建与部署。

## CI/CD 工作流

### 测试工作流

运行所有单元测试、集成测试和 E2E 测试：

```bash
pytest
```

### 代码质量工作流

运行格式化、排序、Lint 和类型检查：

```bash
python -m black .
python -m isort .
python -m flake8 .
python -m mypy .
```

### 安全工作流

运行 `bandit` 和 `safety`：

```bash
bandit -r .
safety check
```

### 部署工作流

构建 Docker 镜像并推送，或部署到 Kubernetes。

## CI/CD 最佳实践

- 每次提交触发 CI，确保构建通过。
- 环境变量和密钥通过 GitHub Secrets 管理。
- 使用缓存加速依赖安装。
- 部署前进行配置验证。

## CI/CD 安全配置

- 限制工作流权限，最小化 token 范围。
- 敏感信息不写入仓库。
- 使用 `environment` 和 `secrets` 保护生产部署。

## CI/CD 故障排查

- 测试失败时查看日志输出。
- 依赖安装失败时检查 `requirements.txt` 和 `poetry.lock`。
- 部署失败时检查环境变量和镜像标签。

## CI/CD FAQ

- **如何跳过 CI**：提交信息包含 `[skip ci]`。
- **如何手动触发**：在 GitHub Actions 页面使用 `workflow_dispatch`。
