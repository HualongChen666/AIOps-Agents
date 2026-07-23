# 集成测试环境配置指南

## 概述

本指南描述了AIOps Agent项目的集成测试环境配置和使用方法。

## 目录结构

```
tests/integration/
├── .env.test                    # 集成测试环境变量配置
├── conftest.py                  # 集成测试fixtures和配置
├── test_integration_example.py  # 集成测试示例
└── setup_integration_test_env.py # 环境设置脚本
```

## 环境要求

### 必需依赖

- Python 3.10+
- pytest
- pytest-asyncio
- pytest-timeout
- httpx
- sqlalchemy
- alembic
- redis
- python-dotenv

### 可选服务

- PostgreSQL (用于数据库测试)
- Redis (用于缓存测试)
- Qdrant (用于向量数据库测试)

## 快速开始

### 1. 安装依赖

```bash
pip install pytest pytest-asyncio pytest-timeout httpx sqlalchemy alembic redis python-dotenv
```

### 2. 配置环境变量

编辑 `tests/integration/.env.test` 文件，配置测试环境：

```env
# 数据库配置
DATABASE_URL=postgresql://testuser:testpass@localhost:5432/test_db

# Redis配置
REDIS_URL=redis://localhost:6379/1

# API配置
API_BASE_URL=http://localhost:8000
```

### 3. 设置测试环境

```bash
python tests/integration/setup_integration_test_env.py --setup
```

### 4. 运行集成测试

```bash
# 运行所有集成测试
python tests/integration/setup_integration_test_env.py --run

# 运行特定测试
python tests/integration/setup_integration_test_env.py --run --filter "test_basic"

# 使用pytest直接运行
pytest tests/integration/ -m integration -v
```

## 测试标记

### 可用标记

- `integration`: 标记集成测试
- `database`: 标记需要数据库的测试
- `redis`: 标记需要Redis的测试
- `api`: 标记需要API服务器的测试
- `external`: 标记需要外部服务的测试

### 使用标记

```bash
# 运行所有集成测试
pytest tests/integration/ -m integration

# 只运行数据库测试
pytest tests/integration/ -m database

# 只运行Redis测试
pytest tests/integration/ -m redis

# 运行数据库和Redis测试
pytest tests/integration/ -m "database or redis"

# 排除需要外部服务的测试
pytest tests/integration/ -m "not external"
```

## Fixtures

### 基础Fixtures

#### `sample_user_data`
提供示例用户数据

```python
def test_user_data(sample_user_data):
    assert sample_user_data["username"] == "testuser"
```

#### `sample_alert_data`
提供示例告警数据

```python
def test_alert_data(sample_alert_data):
    assert sample_alert_data["severity"] == "critical"
```

#### `sample_metric_data`
提供示例指标数据

```python
def test_metric_data(sample_metric_data):
    assert "metric_name" in sample_metric_data
```

### 数据库Fixtures

#### `test_database_url`
提供测试数据库URL

#### `test_database_engine`
创建测试数据库引擎

#### `init_test_database`
初始化测试数据库（运行迁移）

#### `db_session`
创建数据库会话

```python
@pytest.mark.integration
@pytest.mark.database
async def test_database_query(db_session):
    result = await db_session.execute("SELECT 1")
    assert result is not None
```

### Redis Fixtures

#### `redis_client`
创建Redis客户端

#### `clean_redis`
清理Redis测试数据

```python
@pytest.mark.integration
@pytest.mark.redis
async def test_redis_operations(redis_client):
    await redis_client.set("test_key", "test_value")
    value = await redis_client.get("test_key")
    assert value == "test_value"
```

### API Fixtures

#### `api_client`
创建API测试客户端

#### `api_session`
创建API会话

```python
@pytest.mark.integration
@pytest.mark.api
async def test_api_endpoint(api_session):
    response = await api_session.get("/api/v1/health")
    assert response.status_code == 200
```

### Mock服务Fixtures

#### `mock_ai_service`
AI服务Mock

#### `mock_alert_service`
告警服务Mock

#### `mock_monitoring_service`
监控服务Mock

```python
def test_mock_service(mock_ai_service):
    result = asyncio.run(mock_ai_service.analyze("test"))
    assert result is not None
```

### 测试工具Fixtures

#### `test_data_cleaner`
测试数据清理器

```python
async def test_cleanup(test_data_cleaner):
    cleanup_called = False
    test_data_cleaner.add_cleanup_task(lambda: cleanup_called.__setattr__('value', True))
    await test_data_cleaner.cleanup()
    assert cleanup_called.value
```

#### `test_isolation`
测试隔离（确保测试间独立）

```python
async def test_isolation(test_isolation):
    # 测试数据会在测试后自动清理
    pass
```

#### `performance_timer`
性能计时器

```python
def test_performance(performance_timer):
    with performance_timer:
        # 执行操作
        pass
    assert performance_timer.elapsed > 0
```

#### `retry_on_failure`
重试装饰器

```python
@pytest.mark.integration
@retry_on_failure(max_retries=3, delay=1)
async def test_with_retry():
    # 测试逻辑
    pass
```

#### `test_data_generator`
测试数据生成器

```python
def test_data_generator(test_data_generator):
    user = test_data_generator.random_user()
    alert = test_data_generator.random_alert()
    metric = test_data_generator.random_metric()
    
    assert user is not None
    assert alert is not None
    assert metric is not None
```

## 测试隔离

集成测试环境提供了完善的测试隔离机制：

1. **数据库隔离**: 每个测试后自动回滚事务
2. **Redis隔离**: 每个测试后自动清理Redis数据
3. **Mock隔离**: 每个测试后自动重置Mock状态
4. **数据清理**: 自动清理测试生成的数据

## 性能测试

### 使用性能计时器

```python
def test_operation_performance(performance_timer):
    with performance_timer:
        # 执行操作
        asyncio.sleep(0.1)
    
    print(f"Operation took {performance_timer.elapsed:.3f} seconds")
```

### 运行性能测试

```bash
# 运行集成测试并测量时间
pytest tests/integration/ -m integration --durations=10
```

## 并行测试

### 配置并行测试

在 `pytest.ini` 中配置：

```ini
[pytest]
addopts = -n auto
```

### 运行并行测试

```bash
# 使用所有CPU核心
pytest tests/integration/ -m integration -n auto

# 使用指定数量的worker
pytest tests/integration/ -m integration -n 4
```

## 调试集成测试

### 详细输出

```bash
pytest tests/integration/ -m integration -vv -s
```

### 停在第一个失败

```bash
pytest tests/integration/ -m integration -x
```

### 只运行失败的测试

```bash
pytest tests/integration/ -m integration --lf
```

## 持续集成

### CI/CD配置示例

```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-timeout
      
      - name: Setup test environment
        run: python tests/integration/setup_integration_test_env.py --setup
      
      - name: Run integration tests
        run: pytest tests/integration/ -m integration -v
        env:
          DATABASE_URL: postgresql://testuser:testpass@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/1
```

## 故障排除

### 数据库连接失败

1. 检查数据库是否运行
2. 检查连接字符串是否正确
3. 检查防火墙设置

### Redis连接失败

1. 检查Redis是否运行
2. 检查Redis端口是否正确
3. 检查Redis密码配置

### 测试超时

1. 增加测试超时时间
2. 检查是否有死锁
3. 优化测试性能

### Mock不工作

1. 检查Mock配置
2. 检查Mock状态重置
3. 查看Mock监控报告

## 最佳实践

### 1. 使用测试标记

始终为测试添加适当的标记，便于选择性运行：

```python
@pytest.mark.integration
@pytest.mark.database
async def test_database_feature(db_session):
    pass
```

### 2. 使用fixtures

充分利用提供的fixtures，避免重复代码：

```python
@pytest.mark.integration
async def test_with_fixtures(sample_user_data, mock_ai_service):
    # 使用提供的fixtures
    pass
```

### 3. 清理测试数据

确保测试不会留下残留数据：

```python
@pytest.mark.integration
async def test_with_cleanup(test_data_cleaner):
    # 添加清理任务
    test_data_cleaner.add_cleanup_task(cleanup_function)
```

### 4. 测试隔离

确保测试之间相互独立：

```python
@pytest.mark.integration
async def test_isolated(test_isolation):
    # 测试会自动隔离
    pass
```

### 5. 性能监控

对性能敏感的测试使用性能计时器：

```python
@pytest.mark.integration
def test_performance_sensitive(performance_timer):
    with performance_timer:
        # 测试操作
        pass
```

## 扩展测试环境

### 添加新的Fixtures

在 `tests/integration/conftest.py` 中添加新的fixtures：

```python
@pytest.fixture
def custom_fixture():
    """自定义fixture"""
    # fixture逻辑
    return some_value
```

### 添加新的测试标记

在 `pytest.ini` 中添加新的标记：

```ini
[pytest]
markers =
    integration: marks tests as integration tests
    custom: marks tests as custom tests
```

### 添加新的环境变量

在 `tests/integration/.env.test` 中添加新的环境变量：

```env
CUSTOM_VAR=value
```

## 总结

集成测试环境提供了：

- ✅ 完善的fixtures支持
- ✅ 测试隔离机制
- ✅ Mock服务支持
- ✅ 性能测试工具
- ✅ 并行测试支持
- ✅ 详细的配置选项

使用这个环境可以确保集成测试的稳定性和可维护性。
