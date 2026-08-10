# 错误处理最佳实践

## 1. 概述

本文档提供AIOps Agent系统的错误处理最佳实践，包括异常处理规范、错误恢复策略、错误监控指南等。

## 2. 异常处理规范

### 2.1 异常使用原则

**原则1: 使用自定义异常而非通用异常**

```python
# ❌ 不推荐
raise ValueError("用户名不能为空")

# ✅ 推荐
from aiops_core.exceptions import ValidationException
raise ValidationException(
    message="用户名不能为空",
    field="username",
    value=""
)
```

**原则2: 提供丰富的上下文信息**

```python
# ❌ 不推荐
raise DatabaseException("数据库错误")

# ✅ 推荐
from aiops_core.exceptions import DatabaseException
raise DatabaseException(
    message="数据库连接失败",
    host="localhost",
    port=5432,
    database="aiops",
    context={"query": "SELECT * FROM users"}
)
```

**原则3: 正确使用异常链**

```python
# ❌ 不推荐
try:
    result = external_api_call()
except Exception as e:
    raise BusinessLogicException("操作失败")

# ✅ 推荐
try:
    result = external_api_call()
except Exception as e:
    raise BusinessLogicException(
        message="操作失败",
        context={"operation": "external_api_call"},
        original_exception=e
    )
```

### 2.2 异常捕获规范

**原则1: 精确捕获异常**

```python
# ❌ 不推荐
try:
    result = operation()
except Exception:
    pass

# ✅ 推荐
try:
    result = operation()
except ValidationException as e:
    # 处理验证错误
    pass
except DatabaseException as e:
    # 处理数据库错误
    pass
```

**原则2: 不要吞掉异常**

```python
# ❌ 不推荐
try:
    result = operation()
except Exception:
    pass  # 静默失败

# ✅ 推荐
try:
    result = operation()
except Exception as e:
    log_exception(e)
    raise  # 重新抛出或处理
```

**原则3: 在适当的层级处理异常**

```python
# ❌ 不推荐：在底层处理业务逻辑
def get_user(user_id):
    try:
        user = db.query(user_id)
        if not user:
            return None  # 静默失败
    except Exception:
        return None

# ✅ 推荐：在业务层处理
def get_user(user_id):
    user = db.query(user_id)
    if not user:
        raise ResourceNotFoundException(
            message="用户不存在",
            resource_type="User",
            resource_id=user_id
        )
    return user
```

### 2.3 异常日志规范

**原则1: 记录所有异常**

```python
from aiops_core.error_logging import log_exception

try:
    result = operation()
except Exception as e:
    log_exception(e)
    raise
```

**原则2: 记录结构化日志**

```python
from aiops_core.error_logging import log_error

log_error(
    error_code="01_01_0001",
    message="参数验证失败",
    severity="warning",
    category="business",
    context={"field": "username", "value": ""}
)
```

**原则3: 敏感信息脱敏**

```python
# ❌ 不推荐
log_error(
    error_code="02_01_0001",
    message="认证失败",
    context={"password": "secret123"}  # 泄露密码
)

# ✅ 推荐
log_error(
    error_code="02_01_0001",
    message="认证失败",
    context={"username": "user@example.com"}  # 不记录密码
)
```

## 3. 错误恢复策略

### 3.1 重试策略

**适用场景**: 网络抖动、临时服务不可用、数据库连接超时

```python
from aiops_core.error_recovery import retry_with_backoff

@retry_with_backoff(
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0,
    multiplier=2.0
)
def call_external_api():
    # 可能失败的操作
    return external_api_call()
```

**最佳实践**:

- 设置合理的重试次数（通常3-5次）
- 使用指数退避策略
- 只对临时性错误重试
- 避免重试非幂等操作

### 3.2 降级策略

**适用场景**: 服务完全不可用、性能严重下降

```python
def get_user_data(user_id):
    try:
        # 尝试从缓存获取
        return cache.get(f"user:{user_id}")
    except CacheException:
        # 降级到数据库
        return db.query(user_id)
```

**最佳实践**:

- 优先使用缓存
- 提供默认值
- 简化功能
- 切换到只读模式

### 3.3 熔断策略

**适用场景**: 下游服务不稳定、防止级联故障

```python
from aiops_core.error_recovery import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,
    success_threshold=2,
    timeout=60
)

@breaker
def call_external_service():
    return external_service_call()
```

**最佳实践**:

- 设置合理的故障阈值
- 监控熔断状态
- 提供降级方案
- 定期尝试恢复

### 3.4 回滚策略

**适用场景**: 数据库事务失败、状态更新失败

```python
def update_user(user_id, data):
    try:
        with db.transaction():
            user = db.get(user_id)
            user.update(data)
            db.save(user)
    except DatabaseException as e:
        # 事务自动回滚
        log_exception(e)
        raise
```

**最佳实践**:

- 使用数据库事务
- 实现补偿操作
- 记录回滚原因
- 提供重试机制

## 4. 错误监控指南

### 4.1 错误统计

```python
from aiops_core.error_logging import get_error_stats, get_error_count

# 获取错误统计
stats = get_error_stats()
for error_code, count in stats.items():
    print(f"{error_code}: {count}")

# 获取特定错误数量
count = get_error_count("01_01_0001")
```

### 4.2 错误趋势

```python
from aiops_core.error_logging import get_error_log_handler

handler = get_error_log_handler()

# 获取错误趋势
trends = handler.get_error_trends("01_01_0001", hours=24)
print(f"过去24小时错误次数: {len(trends)}")

# 获取错误率
rate = handler.get_error_rate("01_01_0001", hours=1)
print(f"错误率: {rate} 次/小时")
```

### 4.3 错误告警

```python
from aiops_core.error_logging import get_error_log_handler

handler = get_error_log_handler()

# 获取最频繁的错误
top_errors = handler.get_top_errors(limit=10)
for error_code, count in top_errors:
    if count > 100:  # 阈值
        send_alert(f"错误码 {error_code} 频繁出现: {count} 次")
```

### 4.4 错误分类统计

```python
handler = get_error_log_handler()

# 按分类统计
category_stats = handler.get_category_stats()
print(f"业务错误: {category_stats.get('business', 0)}")
print(f"系统错误: {category_stats.get('system', 0)}")

# 按严重程度统计
severity_stats = handler.get_severity_stats()
print(f"错误: {severity_stats.get('error', 0)}")
print(f"警告: {severity_stats.get('warning', 0)}")
```

## 5. API错误处理

### 5.1 FastAPI异常处理

```python
from fastapi import FastAPI, HTTPException
from aiops_core.exceptions import ValidationException, ResourceNotFoundException

app = FastAPI()

@app.exception_handler(ValidationException)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "error_id": exc.error_id,
            "context": exc.context
        }
    )

@app.exception_handler(ResourceNotFoundException)
async def not_found_exception_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "error_id": exc.error_id
        }
    )
```

### 5.2 统一错误响应格式

```python
{
    "error_code": "01_01_0001",
    "error_type": "ValidationException",
    "message": "参数验证失败",
    "error_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-01T00:00:00Z",
    "context": {
        "field": "username",
        "value": ""
    }
}
```

### 5.3 错误码使用

```python
from aiops_core.error_codes import ErrorCode
from aiops_core.exceptions import ValidationException

# 使用错误码枚举
raise ValidationException(
    message="用户名不能为空",
    error_code=ErrorCode.GEN_VALIDATION_FAILED,
    field="username"
)
```

## 6. 数据库错误处理

### 6.1 连接错误

```python
from aiops_core.exceptions import DatabaseException
from aiops_core.error_recovery import retry_with_backoff

@retry_with_backoff(max_attempts=3, base_delay=1.0)
def execute_query(query):
    try:
        return db.execute(query)
    except DatabaseException as e:
        if e.error_code == "09_06_0001":  # 连接失败
            raise  # 重试
        else:
            raise  # 不重试
```

### 6.2 约束错误

```python
def create_user(username, email):
    try:
        db.insert(User(username=username, email=email))
    except DatabaseException as e:
        if e.error_code == "09_08_0001":  # 唯一约束冲突
            raise ValidationException(
                message="用户名或邮箱已存在",
                field="username"
            )
        raise
```

### 6.3 事务错误

```python
def transfer_money(from_id, to_id, amount):
    try:
        with db.transaction():
            from_account = db.get(from_id)
            to_account = db.get(to_id)
            
            from_account.balance -= amount
            to_account.balance += amount
            
            db.save(from_account)
            db.save(to_account)
    except DatabaseException as e:
        log_exception(e)
        raise BusinessLogicException(
            message="转账失败",
            context={"from_id": from_id, "to_id": to_id, "amount": amount}
        )
```

## 7. 第三方服务错误处理

### 7.1 API调用错误

```python
from aiops_core.exceptions import ExternalServiceException
from aiops_core.error_recovery import retry_with_backoff

@retry_with_backoff(max_attempts=3, base_delay=1.0)
def call_openai_api(prompt):
    try:
        return openai.Completion.create(prompt=prompt)
    except ExternalServiceException as e:
        if e.error_code == "11_10_0001":  # 限流
            time.sleep(60)  # 等待后重试
            raise
        elif e.error_code == "11_09_0001":  # 超时
            raise  # 重试
        else:
            raise  # 不重试
```

### 7.2 降级策略

```python
def get_ai_response(prompt):
    try:
        # 尝试调用GPT-4
        return call_gpt4(prompt)
    except ExternalServiceException:
        # 降级到GPT-3.5
        try:
            return call_gpt35(prompt)
        except ExternalServiceException:
            # 降级到规则引擎
            return rule_engine_response(prompt)
```

## 8. 安全错误处理

### 8.1 认证错误

```python
from aiops_core.exceptions import AuthenticationException

def authenticate(username, password):
    user = db.get_user(username)
    if not user:
        raise AuthenticationException(
            message="用户名或密码错误",
            # 不记录密码
        )
    
    if not verify_password(password, user.password_hash):
        raise AuthenticationException(
            message="用户名或密码错误"
        )
    
    return user
```

### 8.2 授权错误

```python
from aiops_core.exceptions import PermissionDeniedException

def delete_user(user_id, requester):
    if not requester.has_permission("user:delete"):
        raise PermissionDeniedException(
            message="无权删除用户",
            resource=f"user:{user_id}",
            action="delete"
        )
    
    user = db.get(user_id)
    db.delete(user)
```

### 8.3 敏感信息脱敏

```python
def log_authentication_failure(username):
    log_error(
        error_code="02_01_0001",
        message="认证失败",
        context={"username": username}  # 不记录密码
    )
```

## 9. 性能考虑

### 9.1 避免过度日志

```python
# ❌ 不推荐：在循环中记录日志
for item in items:
    log_error("Processing item", context={"item": item})

# ✅ 推荐：批量记录
errors = []
for item in items:
    try:
        process(item)
    except Exception as e:
        errors.append(e)

if errors:
    log_error(
        error_code="01_04_0001",
        message=f"处理失败 {len(errors)} 项",
        context={"error_count": len(errors)}
    )
```

### 9.2 异步日志

```python
import asyncio
from aiops_core.error_logging import log_error

async def async_log_error(error_code, message, **kwargs):
    # 异步记录日志
    await asyncio.to_thread(log_error, error_code, message, **kwargs)
```

## 10. 测试错误处理

### 10.1 测试异常抛出

```python
import pytest
from aiops_core.exceptions import ValidationException

def test_validation_error():
    with pytest.raises(ValidationException) as exc_info:
        validate_username("")
    
    assert exc_info.value.field == "username"
    assert exc_info.value.error_code == "01_01_0001"
```

### 10.2 测试异常处理

```python
def test_error_handling():
    with pytest.raises(ValidationException):
        try:
            process_user("")
        except ValidationException as e:
            log_exception(e)
            raise
```

### 10.3 Fake 外部错误

```python
import external_api

def test_external_service_error():
    original = external_api.call
    external_api.call = lambda *args, **kwargs: (_ for _ in ()).throw(Exception("API Error"))
    try:
        with pytest.raises(ExternalServiceException):
            call_external_service()
    finally:
        external_api.call = original
```

## 11. 总结

### 11.1 关键要点

1. **使用自定义异常**: 提供丰富的上下文信息
2. **精确捕获异常**: 避免吞掉异常
3. **记录所有异常**: 使用结构化日志
4. **实施恢复策略**: 重试、降级、熔断、回滚
5. **监控错误趋势**: 及时发现和解决问题
6. **保护敏感信息**: 脱敏处理
7. **考虑性能影响**: 避免过度日志
8. **编写测试**: 确保错误处理正确

### 11.2 常见错误

1. ❌ 使用通用异常而非自定义异常
2. ❌ 吞掉异常而不处理
3. ❌ 记录敏感信息
4. ❌ 过度重试
5. ❌ 不记录异常
6. ❌ 在错误的层级处理异常
7. ❌ 不实施恢复策略
8. ❌ 不监控错误趋势
