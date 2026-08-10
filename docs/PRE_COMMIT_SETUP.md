# Pre-commit Hooks 配置说明

## 概述

本文档说明 AIOps Agent 项目的 pre-commit hooks 配置，包括安装、使用和自定义指南。

## 配置文件位置

- **主配置文件**: `.pre-commit-config.yaml`
- **工具配置文件**: `pyproject.toml`

## 配置架构

### 配置层级

```
.pre-commit-config.yaml (pre-commit 配置)
 ↓
pyproject.toml (工具特定配置)
 ↓
[tool.black] - Black 格式化配置
[tool.isort] - isort 导入排序配置
[tool.flake8] - flake8 代码检查配置
[tool.mypy] - mypy 类型检查配置
```

### 主要改进

#### 1. Black Hook 优化

**之前的问题**:
- 使用硬编码参数 `args: [--line-length=100]`
- 覆盖了 pyproject.toml 中的配置
- 没有使用 pyproject.toml 中的 include/exclude 规则

**优化后**:
```yaml
- repo: https://github.com/psf/black
 rev: 24.3.0
 hooks:
 - id: black
 name: Black - Python Code Formatter
 language_version: python3.10
 # Black 自动从 pyproject.toml 读取配置
 # 不再需要硬编码参数
```

**优势**:
- ✅ 单一配置源（pyproject.toml）
- ✅ 配置一致性保证
- ✅ 支持 include/exclude 规则
- ✅ 易于维护

#### 2. 全局配置

添加了全局配置以简化管理：

```yaml
# 默认 Python 版本
default_language_version:
 python: python3.10

# 全局排除模式
exclude: |
 (?x)^(
 \.git/|
 \.mypy_cache/|
 \.pytest_cache/|
 \.venv/|
 venv/|
 __pycache__/|
 build/|
 dist/|
 \.eggs/|
 .*\.egg-info/
 node_modules/|
 \.tox/
 )$
```

#### 3. 增强的 Hook 描述

每个 hook 都添加了详细的 `name` 和 `description` 字段，便于理解功能。

#### 4. 额外的 Flake8 插件

添加了有用的 flake8 插件：
- `flake8-docstrings` - 检查文档字符串
- `flake8-bugbear` - 查找可能的 bug
- `flake8-comprehensions` - 改进列表/集合/字典推导式

## 安装步骤

### 1. 安装 pre-commit

```bash
pip install pre-commit
```

### 2. 安装 Git hooks

```bash
cd C:\AIOps_Agent_bak
pre-commit install
```

这会在 `.git/hooks/` 目录中安装 pre-commit 脚本。

### 3. 可选：安装 pre-commit 到特定环境

如果使用虚拟环境：

```bash
# 激活虚拟环境
venv\Scripts\activate # Windows
# 或
source venv/bin/activate # Linux/Mac

# 安装 pre-commit
pip install pre-commit

# 安装 hooks
pre-commit install
```

## 使用方法

### 手动运行所有 hooks

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

### 更新 hook 版本

```bash
# 更新所有 hooks 到最新版本
pre-commit autoupdate

# 查看当前版本
pre-commit autoupdate --dry-run
```

### 清理缓存

```bash
# 清理 pre-commit 缓存
pre-commit clean

# 清理 Git hooks
pre-commit uninstall
```

## 配置验证

### 验证配置文件语法

```bash
pre-commit validate-config
```

### 验证特定 hook

```bash
# 测试 black 配置
pre-commit run black --all-files --verbose

# 测试 isort 配置
pre-commit run isort --all-files --verbose
```

## Black 配置详情

### pyproject.toml 配置

```toml
[tool.black]
line-length = 100
target-version = ['py310']
include = '\.pyi?$'
exclude = '''
/(
 # directories
 \.eggs
 | \.git
 | \.hg
 | \.mypy_cache
 | \.tox
 | \.venv
 | venv
 | __pycache__
 | .pytest_cache
 | build
 | dist
 | .*\.egg-info
)/
'''
```

### Black 如何读取配置

1. **自动查找**: Black 会自动在当前目录和父目录中查找配置文件
2. **配置优先级**: 命令行参数 > pyproject.toml > 默认配置
3. **推荐做法**: 不在 pre-commit 中传递参数，让 Black 自动读取 pyproject.toml

### 手动测试 Black

```bash
# 测试 black 是否正确读取配置
black --check --diff .

# 查看当前配置
black --config pyproject.toml --help
```

## Hook 执行顺序

Pre-commit hooks 按照在配置文件中出现的顺序执行：

1. **通用检查** (pre-commit-hooks)
 - trailing-whitespace
 - end-of-file-fixer
 - check-yaml
 - check-added-large-files
 - check-json
 - check-merge-conflict
 - check-toml
 - debug-statements

2. **代码格式化** (black)
 - 自动格式化 Python 代码

3. **导入排序** (isort)
 - 自动排序和格式化导入

4. **代码检查** (flake8)
 - 检查代码风格和语法错误

5. **安全检查** (bandit)
 - 检查安全问题

6. **类型检查** (mypy)
 - 静态类型检查

7. **自定义检查** (local hooks)
 - test-collection-validation
 - test-syntax-check

## CI/CD 集成

### GitHub Actions 集成

在 `.github/workflows/lint.yml` 中添加：

```yaml
name: Lint

on: [push, pull_request]

jobs:
 lint:
 runs-on: ubuntu-latest
 steps:
 - uses: actions/checkout@v3
 - uses: actions/setup-python@v4
 with:
 python-version: '3.10'
 - name: Install dependencies
 run: |
 pip install pre-commit
 - name: Run pre-commit
 run: |
 pre-commit run --all-files
```

### GitLab CI 集成

在 `.gitlab-ci.yml` 中添加：

```yaml
lint:
 stage: test
 image: python:3.10
 script:
 - pip install pre-commit
 - pre-commit run --all-files
 only:
 - merge_requests
 - main
```

## 故障排除

### 问题：Hook 执行失败

**解决方案**:
```bash
# 查看详细输出
pre-commit run --all-files --verbose

# 跳过失败的 hook
pre-commit run --all-files --hook-stage manual
```

### 问题：Black 配置未生效

**解决方案**:
```bash
# 验证 pyproject.toml 语法
python -c "import toml; toml.load('pyproject.toml')"

# 手动测试 black
black --config pyproject.toml --check file.py
```

### 问题：Hook 速度慢

**解决方案**:
```bash
# 使用缓存
pre-commit run --all-files --cache

# 只运行必要的 hooks
pre-commit run black isort flake8 --all-files
```

### 问题：虚拟环境问题

**解决方案**:
```bash
# 重新安装 hooks
pre-commit uninstall
pre-commit install

# 使用系统 Python
pre-commit install --hook-type pre-commit
```

## 最佳实践

### 1. 提交前运行

```bash
# 在提交前运行所有 hooks
git add .
pre-commit run
git commit -m "Your message"
```

### 2. 定期更新

```bash
# 每月更新一次 hooks
pre-commit autoupdate
```

### 3. 自定义排除

如果需要排除特定文件：

```yaml
repos:
 - repo: https://github.com/psf/black
 hooks:
 - id: black
 exclude: ^(legacy/|deprecated/)
```

### 4. 团队协作

确保所有团队成员：
1. 安装相同版本的 pre-commit
2. 运行 `pre-commit install`
3. 使用相同的 pyproject.toml 配置

## 性能优化

### 并行执行

Pre-commit 默认并行执行 hooks。可以调整并发数：

```bash
# 单线程执行（调试用）
PRE_COMMIT_PARALLEL=false pre-commit run --all-files
```

### 选择性执行

只对修改的文件运行：

```bash
pre-commit run
```

### 跳过特定 hook

```bash
# 跳过 mypy（可能很慢）
pre-commit run --all-files --skip mypy
```

## 配置文件参考

### 完整配置示例

参见项目根目录的 `.pre-commit-config.yaml` 文件。

### 相关文档

- [Pre-commit 官方文档](https://pre-commit.com/)
- [Black 官方文档](https://black.readthedocs.io/)
- [isort 官方文档](https://pycqa.github.io/isort/)
- [flake8 官方文档](https://flake8.pycqa.org/)

## 维护日志

### 2024-01-XX
- ✅ 优化 Black hook 配置，移除硬编码参数
- ✅ 添加全局配置（语言版本、排除模式）
- ✅ 增强所有 hook 的描述信息
- ✅ 添加 flake8 插件（docstrings, bugbear, comprehensions）
- ✅ 修复 YAML 语法错误
- ✅ 添加详细的配置文档

## 联系方式

如有问题或建议，请联系项目维护团队。
