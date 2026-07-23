# 测试设计指南

## 概述

本指南提供了如何设计真正执行代码的测试用例的最佳实践，帮助开发者编写高质量的测试。

## 测试设计原则

### 1. 测试行为而非实现

测试应该关注系统的外部行为，而不是内部实现细节。这使得测试更加稳定，当内部实现改变时测试仍然有效。

**反模式**:
```python
# ❌ 测试内部实现
def test_internal_function():
    from aiops_core.module import _internal_function
    assert _internal_function() == "expected"
```

**推荐模式**:
```python
# ✅ 测试外部行为
def test_public_api():
    result = core.module.public_api()
    assert result == "expected"
```

### 2. 使用真实集成

尽可能使用真实的组件集成，而不是mock。这可以确保测试真正验证系统的集成逻辑。

**反模式**:
```python
# ❌ Mock数据库
with patch("core.database.execute"):
    result = await create_user("test")
```

**推荐模式**:
```python
# ✅ 使用真实数据库
async def test_create_user(test_db_session: AsyncSession):
    user = User(username="test")
    test_db_session.add(user)
    await test_db_session.commit()
    assert user.id is not None
```

### 3. 测试真实场景

测试应该模拟真实的业务场景，包括正常流程、边界条件和错误场景。

**反模式**:
```python
# ❌ 只测试正常流程
def test_add():
    assert add(1, 2) == 3
```

**推荐模式**:
```python
# ✅ 测试多种场景
def test_add():
    assert add(1, 2) == 3  # 正常流程
    assert add(-1, 1) == 0  # 边界条件
    assert add(0, 0) == 0  # 边界条件
```

### 4. 保持测试独立

每个测试应该独立运行，不依赖其他测试的状态或全局状态。

**反模式**:
```python
# ❌ 依赖全局状态
global_state = {}
def test_step1():
    global_state["value"] = 1

def test_step2():
    assert global_state["value"] == 1  # 依赖step1
```

**推荐模式**:
```python
# ✅ 每个测试独立
def test_step1():
    state = initialize()
    assert state["value"] == 1

def test_step2():
    state = initialize()
    assert state["value"] == 1
```

## 测试分类

### 单元测试

**目的**: 测试单个函数或类的行为
**特点**:
- 快速执行
- 隔离依赖
- 使用mock外部依赖

**示例**:
```python
@pytest.mark.unit
def test_user_validation():
    # 测试单个函数，mock外部依赖
    with patch("core.user.database"):
        result = validate_username("test_user")
        assert result is True
```

### 集成测试

**目的**: 测试多个组件的集成
**特点**:
- 中等执行速度
- 真实组件集成
- 部分mock外部依赖

**示例**:
```python
@pytest.mark.integration
async def test_user_api_integration(client: AsyncClient, test_db_session: AsyncSession):
    # 测试API和数据库的集成
    user = User(username="test")
    test_db_session.add(user)
    await test_db_session.commit()

    response = await client.get("/api/users/1")
    assert response.status_code == 200
```

### E2E测试

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

## 何时使用Mock

### 应该使用Mock的场景

#### 1. 外部依赖
当测试代码依赖于外部服务时，应该使用mock：

```python
# ✅ Mock外部API
async def test_ai_analysis():
    with patch("core.ai.openai_client.chat") as mock_chat:
        mock_chat.return_value = {"content": "CPU usage analysis"}
        result = await analyze_with_openai("CPU usage high")
        assert result is not None
```

#### 2. 慢速操作
当操作执行时间较长时，应该使用mock：

```python
# ✅ Mock慢速操作
async def test_large_file_upload():
    with patch("core.storage.upload_file") as mock_upload:
        mock_upload.return_value = {"success": True, "file_id": "123"}
        result = await upload_large_file("test.dat")
        assert result.success
```

#### 3. 不稳定依赖
当依赖不稳定或不可靠时，应该使用mock：

```python
# ✅ Mock不稳定的依赖
async def test_external_api():
    with patch("core.external.call_api") as mock_call:
        mock_call.return_value = {"data": "test"}
        result = await call_external_api()
        assert result is not None
```

#### 4. 错误场景测试
当需要测试错误处理逻辑时，应该使用mock：

```python
# ✅ Mock错误场景
async def test_api_error_handling():
    with patch("core.api_client.call") as mock_call:
        mock_call.side_effect = HTTPException(500, "Internal Error")
        with pytest.raises(HTTPException):
            await call_api()
```

### 不应该使用Mock的场景

#### 1. 数据库操作
对于数据库CRUD操作，应该使用真实的数据库连接：

```python
# ✅ 使用真实数据库
async def test_create_user(test_db_session: AsyncSession):
    user = User(username="test")
    test_db_session.add(user)
    await test_db_session.commit()
    assert user.id is not None
```

#### 2. 缓存操作
对于缓存操作，应该使用真实的缓存客户端：

```python
# ✅ 使用真实缓存
async def test_cache_operations(test_redis_client):
    await test_redis_client.set("key", "value")
    result = await test_redis_client.get("key")
    assert result == "value"
```

#### 3. HTTP客户端
对于API端点测试，应该使用真实的HTTP客户端：

```python
# ✅ 使用真实HTTP客户端
async def test_api_endpoint(client: AsyncClient):
    response = await client.get("/api/users")
    assert response.status_code == 200
```

## 测试覆盖率

### 覆盖率目标

- **整体覆盖率**: >= 80%
- **核心模块覆盖率**: >= 90%
- **边界条件覆盖率**: >= 70%

### 覆盖率工具

使用pytest-cov生成覆盖率报告：

```bash
# 生成覆盖率报告
pytest --cov=. --cov-report=html --cov-report=term-missing

# 查看HTML报告
open htmlcov/index.html
```

### 覆盖率分析

1. **识别未覆盖的代码路径**
   - 使用覆盖率报告识别未测试的代码
   - 分析为什么这些代码未被测试
   - 添加测试用例覆盖这些代码路径

2. **识别过度Mock的测试**
   - 查看覆盖率报告
   - 如果某些代码路径从未被测试，可能是被mock了
   - 替换mock为真实集成

## 测试命名规范

### 测试文件命名
- 单元测试: `tests/unit/test_<module>.py`
- 集成测试: `tests/integration/test_<feature>.py`
- E2E测试: `tests/e2e/test_<flow>.py`

### 测试函数命名
使用描述性的测试名称：
```python
# ✅ 好的测试名称
def test_user_registration_with_valid_data()
def test_user_registration_with_duplicate_username()
def test_user_registration_with_invalid_email()

# ❌ 不好的测试名称
def test_registration()
def test_user()
def test_1()
```

### 测试类命名
使用描述性的测试类名称：
```python
# ✅ 好的测试类名称
class TestUserAuthentication:
class TestDatabaseOperations:
class TestAPIEndpoints:

# ❌ 不好的测试类名称
class TestAuth:
class TestDB:
class TestAPI:
```

## 测试数据管理

### 使用Fixtures
使用pytest fixtures来管理测试数据：

```python
@pytest.fixture
def test_user():
    return User(username="test", email="test@example.com")

def test_user_operations(test_user):
    assert test_user.username == "test"
```

### 清理测试数据
在测试完成后清理测试数据：

```python
@pytest.fixture(autouse=True)
async def cleanup_test_data(test_db_session: AsyncSession):
    yield
    # 清理测试数据
    await test_db_session.execute(delete(User))
    await test_db_session.commit()
```

### 使用工厂模式
使用工厂模式创建测试数据：

```python
def create_user(username="test", email="test@example.com"):
    return User(username=username, email=email)

def test_user_operations():
    user = create_user(username="custom")
    assert user.username == "custom"
```

## 测试性能优化

### 并行执行
使用pytest-xdist并行执行测试：

```bash
pytest -n auto
```

### 选择性执行
使用pytest标记选择性运行测试：

```bash
# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration

# 跳过慢速测试
pytest -m "not slow"
```

### 使用缓存
使用pytest的缓存功能加速测试：

```bash
# 使用缓存
pytest --cache-clear
```

## 测试最佳实践清单

### 编写测试时
- [ ] 测试行为而非实现
- [ ] 使用真实集成而非mock
- [ ] 测试真实场景（正常、边界、错误）
- [ ] 保持测试独立
- [ ] 使用描述性的测试名称
- [ ] 使用fixtures管理测试数据
- [ ] 清理测试数据
- [ ] 添加适当的测试标记

### 代码审查时
- [ ] 检查测试覆盖率是否达标
- [ ] 检查是否过度使用mock
- [ ] 检查测试是否真正执行代码
- [ ] 检查测试是否独立
- [ ] 检查测试数据是否正确清理
- [ ] 检查测试名称是否描述性

### 持续集成时
- [ ] 运行完整的测试套件
- [ ] 生成覆盖率报告
- [ ] 检查覆盖率是否达标
- [ ] 检查测试执行时间是否在可接受范围内

## 常见错误

### 错误1: 过度Mock
**问题**: 测试mock了应该使用真实集成的组件
**解决**: 使用真实的数据库、缓存、HTTP客户端

### 错误2: 测试内部实现
**问题**: 测试内部函数而非外部API
**解决**: 测试公开的API和行为

### 错误3: 测试之间有依赖
**问题**: 测试依赖其他测试的状态
**解决**: 每个测试独立，使用fixtures设置测试环境

### 错误4: 不清理测试数据
**问题**: 测试数据影响其他测试
**解决**: 在测试完成后清理测试数据

### 错误5: 只测试正常流程
**问题**: 只测试正常流程，不测试边界条件和错误场景
**解决**: 测试多种场景，包括边界条件和错误场景

## 总结

遵循本指南可以帮助开发者编写高质量的测试，确保测试真正执行代码路径，提高代码质量和可靠性。

**文档版本**: 1.0
**最后更新**: 2026-07-06
**维护者**: AIOps Agent Team
