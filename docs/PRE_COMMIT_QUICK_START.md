# Pre-commit Hooks 快速开始指南

## 快速安装

### 1. 安装 pre-commit
```bash
pip install pre-commit
```

### 2. 安装 Git hooks
```bash
cd C:\AIOps_Agent_bak
pre-commit install
```

## 常用命令

### 运行所有 hooks
```bash
# 检查所有文件
pre-commit run --all-files

# 只检查已修改的文件
pre-commit run
```

### 运行特定 hook
```bash
# 只运行 black
pre-commit run black --all-files

# 只运行 isort
pre-commit run isort --all-files

# 只运行 flake8
pre-commit run flake8 --all-files
```

### 更新 hooks
```bash
# 更新所有 hooks 到最新版本
pre-commit autoupdate
```

### 清理
```bash
# 清理缓存
pre-commit clean

# 卸载 hooks
pre-commit uninstall
```

## 验证配置

```bash
# 验证配置文件语法
pre-commit validate-config

# 运行配置验证脚本
python test_pre_commit_config.py
```

## 配置文件

- **主配置**: `.pre-commit-config.yaml`
- **工具配置**: `pyproject.toml`
- **详细文档**: `docs/PRE_COMMIT_SETUP.md`
- **变更说明**: `docs/PRE_COMMIT_CHANGES.md`

## Black 配置

Black 自动从 `pyproject.toml` 读取配置：

```toml
[tool.black]
line-length = 100
target-version = ['py310']
```

**无需在 pre-commit 中硬编码参数！**

## 故障排除

### Hook 执行失败
```bash
# 查看详细输出
pre-commit run --all-files --verbose
```

### 配置未生效
```bash
# 重新安装 hooks
pre-commit uninstall
pre-commit install
```

### 跳过特定 hook
```bash
# 跳过 mypy（可能很慢）
pre-commit run --all-files --skip mypy
```

## 更多信息

- 完整文档: `docs/PRE_COMMIT_SETUP.md`
- 变更说明: `docs/PRE_COMMIT_CHANGES.md`
- 官方文档: https://pre-commit.com/
