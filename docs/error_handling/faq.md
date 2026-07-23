# 错误处理FAQ

## 1. 异常使用

### Q1: 什么时候应该使用自定义异常？

**A**: 当需要提供额外的上下文信息或实现特定的错误处理逻辑时，应该使用自定义异常。例如：

- 需要记录错误码
- 需要提供详细的上下文信息
- 需要实现特定的恢复策略
- 需要区分不同类型的错误

```python
from aiops_core.exceptions import ValidationException

raise ValidationException(
    message="用户名不能为空",
    field="username",
    value=""
)
```

### Q2: 如何选择正确的异常类型？

**A**: 根据错误的性质选择异常类型：

- **ValidationException**: 输入验证失败
- **ResourceNotFoundException**: 资源未找到
- **BusinessLogicException**: 业务逻辑错误
- **DatabaseException**: 数据库相关错误
- **NetworkException**: 网络相关错误
- **AuthenticationException**: 认证失败
- **AuthorizationException**: 授权失败
- **ExternalServiceException**: 外部服务错误

### Q3: 如何在异常中传递上下文信息？

**A**: 使用`context`参数传递上下文信息：

```python
raise DatabaseException(
    message="数据库连接失败",
    host="localhost",
    port=5432,
    context={"query": "SELECT * FROM users"}
)
```

## 2. 错误码使用

### Q4: 错误码的格式是什么？

**A**: 错误码格式为`MM_TT_NNNN`：

- **MM**: 模块码（2位数字，01-20）
- **TT**: 错误类型码（2位数字，01-16）
- **NNNN**: 序号（4位数字，0001-9999）

例如：`01_01_0001`表示通用模块的验证错误。

### Q5: 如何查找错误码？

**A**: 可以通过以下方式查找错误码：

1. 查看`docs/error_handling/error_codes.md`文档
2. 使用`ErrorCode`枚举类：

```python
from aiops_core.error_codes import ErrorCode

print(ErrorCode.GEN_VALIDATION_FAILED)  # 01_01_0001
```

3. 使用错误码管理器：

```python
from aiops_core.error_codes import get_error_message

message = get_error_message("01_01_0001", "zh")
print(message)  # 参数验证失败
```

### Q6: 如何添加新的错误码？

**A**: 按照以下步骤添加新的错误码：

1. 确定模块码和错误类型码
2. 查找该模块和类型下的最大序号
3. 新序号 = 最大序号 + 1
4. 在`core/error_codes/definitions.py`中添加错误码
5. 在`core/error_codes/manager.py`中添加错误消息

## 3. 错误日志

### Q7: 如何记录错误日志？

**A**: 使用`log_error`或`log_exception`函数：

```python
from aiops_core.error_logging import log_error, log_exception

# 记录错误
log_error(
    error_code="01_01_0001",
    message="参数验证失败",
    severity="error",
    category="business",
    context={"field": "username"}
)

# 记录异常
try:
    operation()
except Exception as e:
    log_exception(e)
```

### Q8: 如何查询错误统计？

**A**: 使用错误日志处理器：

```python
from aiops_core.error_logging import get_error_log_handler

handler = get_error_log_handler()

# 获取错误统计
stats = handler.get_error_stats()

# 获取错误数量
count = handler.get_error_count("01_01_0001")

# 获取错误历史
history = handler.get_error_history(limit=100)

# 获取最频繁的错误
top_errors = handler.get_top_errors(limit=10)
```

### Q9: 如何设置错误告警？

**A**: 监控错误统计并设置阈值：

```python
from aiops_core.error_logging import get_error_log_handler

handler = get_error_log_handler()

# 获取最频繁的错误
top_errors = handler.get_top_errors(limit=10)
for error_code, count in top_errors:
    if count > 100:  # 阈值
        send_alert(f"错误码 {error_code} 频繁出现: {count} 次")
```

## 4. 错误恢复

### Q10: 如何实现重试机制？

**A**: 使用`@retry_with_backoff`装饰器：

```python
from aiops_core.error_recovery import retry_with_backoff

@retry_with_backoff(
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0,
    multiplier=2.0
)
def call_external_api():
    return external_api_call()
```

### Q11: 如何实现降级策略？

**A**: 提供备用方案：

```python
def get_user_data(user_id):
    try:
        # 尝试从缓存获取
        return cache.get(f"user:{user_id}")
    except CacheException:
        # 降级到数据库
        return db.query(user_id)
```

### Q12: 如何实现熔断机制？

**A**: 使用`CircuitBreaker`：

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

## 5. FastAPI集成

### Q13: 如何在FastAPI中处理异常？

**A**: 注册异常处理器：

```python
from fastapi import FastAPI
from aiops_core.exceptions import ValidationException

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
```

### Q14: 如何返回统一的错误响应格式？

**A**: 使用统一的响应格式：

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

## 6. 数据库错误

### Q15: 如何处理数据库连接错误？

**A**: 使用重试机制：

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

### Q16: 如何处理数据库约束错误？

**A**: 转换为业务异常：

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

## 7. 安全

### Q17: 如何保护敏感信息？

**A**: 脱敏处理：

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

### Q18: 如何处理认证错误？

**A**: 使用AuthenticationException：

```python
from aiops_core.exceptions import AuthenticationException

def authenticate(username, password):
    user = db.get_user(username)
    if not user:
        raise AuthenticationException(
            message="用户名或密码错误"
        )
    
    if not verify_password(password, user.password_hash):
        raise AuthenticationException(
            message="用户名或密码错误"
        )
    
    return user
```

## 8. 性能

### Q19: 如何避免过度日志？

**A**: 批量记录：

```python
# ❌ 不推荐
for item in items:
    log_error("Processing item", context={"item": item})

# ✅ 推荐
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

### Q20: 如何实现异步日志？

**A**: 使用异步函数：

```python
import asyncio
from aiops_core.error_logging import log_error

async def async_log_error(error_code, message, **kwargs):
    await asyncio.to_thread(log_error, error_code, message, **kwargs)
```

## 9. 测试

### Q21: 如何测试异常抛出？

**A**: 使用pytest.raises：

```python
import pytest
from aiops_core.exceptions import ValidationException

def test_validation_error():
    with pytest.raises(ValidationException) as exc_info:
        validate_username("")
    
    assert exc_info.value.field == "username"
    assert exc_info.value.error_code == "01_01_0001"
```

### Q22: 如何Mock外部错误？

**A**: 使用unittest.mock：

```python
from unittest.mock import patch

def test_external_service_error():
    with patch('external_api.call', side_effect=Exception("API Error")):
        with pytest.raises(ExternalServiceException):
            call_external_service()
```

## 10. 常见问题

### Q23: 为什么我的异常没有被捕获？

**A**: 检查以下几点：

1. 确保异常类型正确
2. 确保异常在正确的层级被捕获
3. 检查是否有其他异常处理器优先处理
4. 确保异常没有被静默吞掉

### Q24: 如何调试错误处理逻辑？

**A**: 使用以下方法：

1. 添加日志记录
2. 使用调试器
3. 检查异常链
4. 验证错误码

### Q25: 如何处理未知错误？

**A**: 使用通用异常处理器：

```python
try:
    operation()
except KnownException as e:
    # 处理已知异常
    pass
except Exception as e:
    # 处理未知异常
    log_exception(e)
    raise
```

### Q26: 如何实现错误追踪？

**A**: 使用error_id追踪：

```python
from aiops_core.exceptions import ValidationException

exc = ValidationException(message="Test error")
print(exc.error_id)  # 追踪ID
```

### Q27: 如何国际化错误消息？

**A**: 使用错误码管理器：

```python
from aiops_core.error_codes import get_error_message

# 获取中文消息
message_zh = get_error_message("01_01_0001", "zh")

# 获取英文消息
message_en = get_error_message("01_01_0001", "en")
```

### Q28: 如何清理错误历史？

**A**: 使用clear_history方法：

```python
from aiops_core.error_logging import get_error_log_handler

handler = get_error_log_handler()
handler.clear_history()
```

### Q29: 如何导出错误统计？

**A**: 获取统计并导出：

```python
from aiops_core.error_logging import get_error_log_handler
import json

handler = get_error_log_handler()
stats = handler.get_error_stats()

with open("error_stats.json", "w") as f:
    json.dump(stats, f)
```

### Q30: 如何集成到监控系统？

**A**: 使用Prometheus或Grafana：

```python
from aiops_core.prometheus_metrics import error_counter

error_counter.labels(error_code="01_01_0001").inc()
```
