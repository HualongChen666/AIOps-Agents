# 集成测试指南

## 概述

本指南提供了在AIOps Agent项目中编写集成测试的最佳实践，包括何时使用mock、何时使用真实集成，以及如何平衡测试真实性和执行速度。

## 测试金字塔

```
        /\
       /  \      E2E Tests (少量)
      /____\     真实环境，测试完整流程
     /      \
    /        \   Integration Tests (适量)
   /__________\  真实组件，测试集成逻辑
  /            \
 /              \ Unit Tests (大量)
/________________\ Mock依赖，测试单个组件
```

## 何时使用Mock

### 应该使用Mock的场景

#### 1. 外部依赖
当测试代码依赖于外部服务时，应该使用mock：

```python
# ❌ 不推荐：调用真实的OpenAI API
async def test_ai_analysis():
    result = await analyze_with_openai("CPU usage high")
    assert result is not None

# ✅ 推荐：mock外部API
async def test_ai_analysis_with_mock():
    with patch("core.ai_engine.openai_client.chat") as mock_chat:
        mock_chat.return_value = {"content": "CPU usage analysis"}
        result = await analyze_with_openai("CPU usage high")
        assert result is not None
```

**适用场景**:
- OpenAI、Anthropic等AI服务
- GitLab、Jira等外部服务
- AWS、Azure等云服务
- 第三方API调用

#### 2. 慢速操作
当操作执行时间较长时，应该使用mock：

```python
# ❌ 不推荐：等待真实的慢速操作
async def test_large_file_upload():
    result = await upload_large_file("test.dat")  # 可能需要几分钟
    assert result.success

# ✅ 推荐：mock慢速操作
async def test_large_file_upload_with_mock():
    with patch("core.storage.upload_file") as mock_upload:
        mock_upload.return_value = {"success": True, "file_id": "123"}
        result = await upload_large_file("test.dat")
        assert result.success
```

**适用场景**:
- 大文件上传/下载
- 复杂计算任务
- 长时间运行的批处理
- 视频处理、图像处理

#### 3. 不稳定依赖
当依赖不稳定或不可靠时，应该使用mock：

```python
# ❌ 不推荐：依赖不稳定的网络服务
async def test_external_api():
    result = await call_external_api()  # 可能超时或失败
    assert result is not None

# ✅ 推荐：mock不稳定的依赖
async def test_external_api_with_mock():
    with patch("core.external.call_api") as mock_call:
        mock_call.return_value = {"data": "test"}
        result = await call_external_api()
        assert result is not None
```

**适用场景**:
- 网络依赖
- 第三方服务
- 外部数据库
- 不稳定的API

#### 4. 错误场景测试
当需要测试错误处理逻辑时，应该使用mock：

```python
# ✅ 推荐：mock错误场景
async def test_api_error_handling():
    with patch("core.api_client.call") as mock_call:
        mock_call.side_effect = HTTPException(500, "Internal Error")
        with pytest.raises(HTTPException):
            await call_api()
```

**适用场景**:
- API失败场景
- 网络超时场景
- 服务不可用场景
- 权限错误场景

#### 5. 边界条件测试
当需要测试极端情况时，应该使用mock：

```python
# ✅ 推荐：mock边界条件
async def test_extreme_data_size():
    with patch("core.processor.process") as mock_process:
        mock_process.return_value = {"result": "processed"}
        # 测试极大输入
        result = await process_data("x" * 1000000)
        assert result is not None
```

**适用场景**:
- 极大数据量
- 极小数据量
- 特殊字符
- 边界值测试

## 何时使用真实集成

### 应该使用真实集成的场景

#### 1. 数据库操作
对于数据库CRUD操作，应该使用真实的数据库连接：

```python
# ✅ 推荐：使用真实数据库集成
@pytest.mark.asyncio
async def test_create_user(test_db_session: AsyncSession):
    # 使用真实的数据库会话
    user = User(username="test", email="test@example.com")
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    
    # 验证数据真实写入
    assert user.id is not None
    assert user.username == "test"
```

**适用场景**:
- CRUD操作测试
- 查询逻辑测试
- 事务处理测试
- 数据验证测试

**使用fixture**:
- `test_db_engine`: SQLite内存数据库引擎
- `test_db_session`: 数据库会话

#### 2. 缓存操作
对于缓存操作，应该使用真实的Redis客户端（使用fakeredis）：

```python
# ✅ 推荐：使用真实缓存集成
@pytest.mark.asyncio
async def test_cache_operations(test_redis_client):
    # 使用真实的Redis客户端（fakeredis）
    await test_redis_client.set("key", "value")
    result = await test_redis_client.get("key")
    
    # 验证缓存真实工作
    assert result == "value"
```

**适用场景**:
- 缓存读写测试
- 缓存过期测试
- 缓存统计测试
- 分布式锁测试

**使用fixture**:
- `test_redis_client`: fakeredis模拟的Redis客户端

#### 3. HTTP客户端
对于API端点测试，应该使用真实的HTTP客户端：

```python
# ✅ 推荐：使用真实HTTP客户端
@pytest.mark.asyncio
async def test_api_endpoint(client: AsyncClient, test_db_session: AsyncSession):
    # 设置测试数据
    user = User(username="test", email="test@example.com")
    test_db_session.add(user)
    await test_db_session.commit()
    
    # 使用真实的HTTP客户端测试API
    response = await client.get("/api/users/1")
    
    # 验证API真实工作
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "test"
```

**适用场景**:
- API端点测试
- 请求验证测试
- 响应格式测试
- 认证授权测试

**使用fixture**:
- `client`: AsyncClient for FastAPI
- `authenticated_client`: 带认证的AsyncClient

#### 4. 消息队列
对于消息队列操作，应该使用真实的消息队列客户端：

```python
# ✅ 推荐：使用真实消息队列集成
@pytest.mark.asyncio
async def test_message_queue(test_message_queue):
    # 使用真实的消息队列
    await test_message_queue.publish("test_queue", {"message": "test"})
    
    message = await test_message_queue.consume("test_queue")
    
    # 验证消息队列真实工作
    assert message["message"] == "test"
```

**适用场景**:
- 消息发布/订阅测试
- 消息顺序测试
- 消息持久化测试
- 消息重试测试

#### 5. 文件系统
对于文件系统操作，应该使用真实的文件系统（临时目录）：

```python
# ✅ 推荐：使用真实文件系统
@pytest.mark.asyncio
async def test_file_operations(tmp_path):
    # 使用真实的临时文件系统
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    # 验证文件操作真实工作
    assert test_file.exists()
    assert test_file.read_text() == "test content"
```

**适用场景**:
- 文件读写测试
- 目录操作测试
- 文件权限测试
- 文件路径测试

## 测试分层策略

### 单元测试（Unit Tests）
**目的**: 测试单个函数/类的行为

**特点**:
- 快速执行
- 隔离依赖
- 使用mock

**示例**:
```python
@pytest.mark.unit
async def test_user_validation():
    # 测试单个函数，mock所有依赖
    with patch("core.user.database"):
        result = validate_username("test_user")
        assert result is True
```

### 集成测试（Integration Tests）
**目的**: 测试多个组件的集成

**特点**:
- 中等执行速度
- 真实组件集成
- 部分mock

**示例**:
```python
@pytest.mark.integration
async def test_user_api_integration(client: AsyncClient, test_db_session: AsyncSession):
    # 测试API和数据库的集成
    user = User(username="test", email="test@example.com")
    test_db_session.add(user)
    await test_db_session.commit()
    
    response = await client.get("/api/users/1")
    assert response.status_code == 200
```

### E2E测试（End-to-End Tests）
**目的**: 测试完整的用户流程

**特点**:
- 较慢执行
- 真实环境
- 最少mock

**示例**:
```python
@pytest.mark.e2e
async def test_user_registration_flow(client: AsyncClient):
    # 测试完整的用户注册流程
    response = await client.post("/api/register", json={
        "username": "test",
        "email": "test@example.com",
        "password": "password123"
    })
    
    assert response.status_code == 201
    
    # 验证用户可以登录
    login_response = await client.post("/api/login", json={
        "username": "test",
        "password": "password123"
    })
    
    assert login_response.status_code == 200
```

## 性能考虑

### 平衡真实性和速度

| 测试类型 | 执行速度 | 真实性 | 使用频率 |
|---------|---------|--------|---------|
| 单元测试 | 快（<1s） | 低（mock） | 高（70%） |
| 集成测试 | 中（1-10s） | 中（部分真实） | 中（20%） |
| E2E测试 | 慢（>10s） | 高（真实） | 低（10%） |

### 优化策略

1. **使用内存数据库**: SQLite内存数据库比PostgreSQL快
2. **使用fakeredis**: fakeredis比真实Redis快
3. **并行执行**: 使用pytest-xdist并行运行测试
4. **选择性执行**: 使用pytest标记选择性运行测试

```bash
# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration

# 只运行E2E测试
pytest -m e2e

# 并行运行测试
pytest -n auto

# 跳过慢速测试
pytest -m "not slow"
```

## 最佳实践

### 1. 明确测试类型
在测试文件名和测试函数中明确标注测试类型：

```python
# tests/unit/test_user_service.py
@pytest.mark.unit
def test_user_validation():
    pass

# tests/integration/test_user_api.py
@pytest.mark.integration
async def test_user_api():
    pass

# tests/e2e/test_user_flow.py
@pytest.mark.e2e
async def test_user_registration_flow():
    pass
```

### 2. 合理使用fixtures
利用conftest.py中提供的fixtures：

```python
# 数据库相关
test_db_engine      # SQLite内存数据库引擎
test_db_session     # 数据库会话

# 缓存相关
test_redis_client   # fakeredis模拟的Redis客户端

# HTTP相关
client              # AsyncClient for FastAPI
authenticated_client  # 带认证的AsyncClient

# Mock相关
mock_ai_analyze     # AI分析mock
mock_alert_service  # 告警服务mock
mock_database       # 数据库mock（谨慎使用）
mock_cache          # 缓存mock（谨慎使用）
```

### 3. 测试数据隔离
每个测试应该有独立的测试数据：

```python
@pytest.mark.asyncio
async def test_user_creation(test_db_session: AsyncSession):
    # 创建独立的测试数据
    user = User(username="unique_test", email="unique@test.com")
    test_db_session.add(user)
    await test_db_session.commit()
    
    # 验证
    assert user.id is not None
```

### 4. 清理测试数据
测试完成后清理测试数据：

```python
@pytest.fixture(autouse=True)
async def cleanup_test_data(test_db_session: AsyncSession):
    yield
    # 清理测试数据
    await test_db_session.execute(delete(User))
    await test_db_session.commit()
```

### 5. 避免测试依赖
测试之间不应该有依赖关系：

```python
# ❌ 不推荐：测试之间有依赖
async def test_create_user():
    global user_id
    user_id = await create_user("test")

async def test_get_user():
    user = await get_user(user_id)  # 依赖上一个测试

# ✅ 推荐：每个测试独立
async def test_create_user():
    user = await create_user("test")
    assert user.id is not None

async def test_get_user():
    user = await create_user("test2")
    result = await get_user(user.id)
    assert result.username == "test2"
```

## 常见错误

### 错误1: 过度Mock
```python
# ❌ 错误：mock了应该使用真实集成的组件
async def test_database_operations():
    with patch("core.database.execute"):
        result = await create_user("test")
        assert result is not None

# ✅ 正确：使用真实数据库集成
async def test_database_operations(test_db_session: AsyncSession):
    user = User(username="test")
    test_db_session.add(user)
    await test_db_session.commit()
    assert user.id is not None
```

### 错误2: Mock外部依赖
```python
# ❌ 错误：没有mock外部依赖
async def test_external_api():
    result = await call_openai_api()  # 调用真实的OpenAI API
    assert result is not None

# ✅ 正确：mock外部依赖
async def test_external_api():
    with patch("core.ai.openai_client") as mock_client:
        mock_client.return_value = {"content": "test"}
        result = await call_openai_api()
        assert result is not None
```

### 错误3: 测试之间有依赖
```python
# ❌ 错误：测试之间有依赖
async def test_step1():
    global state
    state = "initialized"

async def test_step2():
    assert state == "initialized"  # 依赖上一个测试

# ✅ 正确：每个测试独立
async def test_step1():
    state = initialize()
    assert state == "initialized"

async def test_step2():
    state = initialize()
    result = process(state)
    assert result is not None
```

### 错误4: 不清理测试数据
```python
# ❌ 错误：不清理测试数据
async def test_user_creation(test_db_session: AsyncSession):
    user = User(username="test")
    test_db_session.add(user)
    await test_db_session.commit()
    # 没有清理，影响其他测试

# ✅ 正确：清理测试数据
async def test_user_creation(test_db_session: AsyncSession):
    user = User(username="test")
    test_db_session.add(user)
    await test_db_session.commit()
    
    # 清理
    await test_db_session.delete(user)
    await test_db_session.commit()
```

## 工具和资源

### 测试工具
- **pytest**: 测试框架
- **pytest-asyncio**: 异步测试支持
- **pytest-xdist**: 并行测试执行
- **pytest-cov**: 覆盖率测试
- **fakeredis**: Redis模拟
- **httpx**: 异步HTTP客户端

### 相关文档
- [Mock使用情况分析报告](./mock_usage_analysis.md)
- [pytest文档](https://docs.pytest.org/)
- [FastAPI测试文档](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy异步文档](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

---

**文档版本**: 1.0
**最后更新**: 2026-07-06
**维护者**: AIOps Agent Team
