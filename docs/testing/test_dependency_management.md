# 测试依赖管理文档

## 概述

本文档提供了AIOps Agent项目测试依赖的完整清单、安装指南和配置说明。

## 测试依赖清单

### 必需依赖

#### Python包依赖

```txt
# 核心测试框架
pytest>=9.1.0
pytest-asyncio>=1.4.0
pytest-cov>=7.1.0
pytest-xdist>=3.8.0
pytest-timeout>=2.4.0

# HTTP客户端
httpx>=0.27.0

# 数据库
sqlalchemy>=2.0.0
aiosqlite>=0.19.0
alembic>=1.13.0

# 缓存
fakeredis>=2.23.0  # 可选，用于Redis模拟测试

# 异步支持
asyncio>=3.4.3

# 日志
loguru>=0.7.0

# 类型检查
mypy>=1.0.0

# 代码质量
black>=24.0.0
isort>=5.13.0
flake8>=7.0.0
```

#### 系统依赖

- Python 3.10+
- PostgreSQL 14+ (可选，用于真实数据库测试)
- Redis 7+ (可选，用于真实缓存测试)

### 可选依赖

#### AI/ML依赖

```txt
# RAG相关
sentence-transformers>=2.2.0
crossencoder>=0.1.0

# 向量数据库
qdrant-client>=1.7.0
```

#### 外部服务依赖

- OpenAI API Key (可选，用于AI功能测试)
- Anthropic API Key (可选，用于AI功能测试)
- GitLab访问权限 (可选，用于GitLab集成测试)

## 安装指南

### 基础安装

1. **创建虚拟环境**

```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

1. **安装核心依赖**

```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov pytest-xdist pytest-timeout
pip install httpx sqlalchemy aiosqlite alembic
pip install fakeredis
```

1. **安装开发依赖**

```bash
pip install black isort flake8 mypy
```

### 完整安装（包含AI/ML功能）

```bash
pip install sentence-transformers crossencoder
pip install qdrant-client
```

## 配置说明

### 环境变量配置

创建 `.env.test` 文件：

```env
# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///:memory:
POSTGRES_URL=postgresql://test:test@localhost:5432/test_db

# Redis配置
REDIS_URL=redis://localhost:6379

# AI服务配置
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# 测试配置
LOG_LEVEL=INFO
DEBUG=False
ENVIRONMENT=testing
```

### Pytest配置

`pytest.ini` 文件已配置：

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
timeout = 30
timeout_method = thread
addopts = 
    -v
    --strict-markers
    --tb=short
    --cov=.
    --cov-report=html
    --cov-report=term-missing
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    e2e: marks tests as end-to-end tests
```

## 测试分类说明

### 单元测试 (Unit Tests)

**标记**: `@pytest.mark.unit`
**依赖**: 最少，仅需要核心Python包
**执行**: `pytest -m unit`
**说明**: 测试单个函数/类的行为，使用mock隔离依赖

### 集成测试 (Integration Tests)

**标记**: `@pytest.mark.integration`
**依赖**: fakeredis, aiosqlite
**执行**: `pytest -m integration`
**说明**: 测试多个组件的集成，使用真实的数据库和缓存模拟

### E2E测试 (End-to-End Tests)

**标记**: `@pytest.mark.e2e`
**依赖**: PostgreSQL, Redis, 外部服务
**执行**: `pytest -m e2e`
**说明**: 测试完整的用户流程，需要真实的外部服务

### 慢速测试 (Slow Tests)

**标记**: `@pytest.mark.slow`
**执行**: `pytest -m "not slow"` (跳过慢速测试)
**说明**: 执行时间较长的测试

## 特殊依赖说明

### fakeredis

**用途**: 模拟Redis用于测试
**安装**: `pip install fakeredis`
**配置**: 自动使用，无需额外配置
**注意**: 如果未安装，测试会自动使用mock

### aiosqlite

**用途**: SQLite异步驱动用于测试
**安装**: `pip install aiosqlite`
**配置**: 自动使用，无需额外配置
**注意**: 用于内存数据库测试

### sentence-transformers

**用途**: RAG功能测试
**安装**: `pip install sentence-transformers`
**配置**: 需要网络访问下载模型
**注意**: 如果未安装，相关测试会被跳过

### qdrant-client

**用途**: 向量数据库测试
**安装**: `pip install qdrant-client`
**配置**: 需要Qdrant服务运行
**注意**: 如果未安装或服务不可用，相关测试会被跳过

## 常见问题

### 1. 导入错误

**问题**: `ImportError: No module named 'xxx'`
**解决**: 安装缺失的依赖包

```bash
pip install xxx
```

### 2. fakeredis未安装

**问题**: Redis测试使用mock而非真实模拟
**解决**: 安装fakeredis

```bash
pip install fakeredis
```

### 3. 数据库连接失败

**问题**: 无法连接到PostgreSQL
**解决**: 使用SQLite内存数据库（默认配置）

```env
DATABASE_URL=sqlite+aiosqlite:///:memory:
```

### 4. AI模型下载失败

**问题**: 网络访问受限，无法下载模型
**解决**: 跳过相关测试或配置模型缓存

```bash
pytest -m "not slow"
```

### 5. 端口冲突

**问题**: 测试服务端口被占用
**解决**: 修改测试配置或停止占用端口的服务

## 测试执行指南

### 运行所有测试

```bash
pytest
```

### 运行特定类型的测试

```bash
# 单元测试
pytest -m unit

# 集成测试
pytest -m integration

# E2E测试
pytest -m e2e

# 跳过慢速测试
pytest -m "not slow"
```

### 并行执行测试

```bash
pytest -n auto
```

### 生成覆盖率报告

```bash
pytest --cov=. --cov-report=html
```

### 只运行失败的测试

```bash
pytest --lf
```

## CI/CD配置

### GitHub Actions示例

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov pytest-xdist
          pip install fakeredis aiosqlite
      - name: Run tests
        run: pytest -m "not e2e" --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 依赖更新策略

### 定期更新

- 每月检查依赖更新
- 优先更新安全补丁
- 测试兼容性后再更新

### 版本锁定

- 使用固定版本号
- 避免使用`>=`（除了核心测试框架）
- 定期审查依赖树

### 安全扫描

```bash
pip install safety
safety check
```

## 总结

本文档提供了完整的测试依赖管理指南。遵循这些指南可以确保测试环境的一致性和可重复性。

**文档版本**: 1.0
**最后更新**: 2026-07-06
**维护者**: AIOps Agent Team
