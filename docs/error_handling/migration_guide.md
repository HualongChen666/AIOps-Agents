# 错误处理迁移指南

## 1. 概述

本文档提供从现有错误处理实现迁移到新的统一错误处理体系的指南。

## 2. 现有错误处理实现

项目中存在以下错误处理实现：

- `core/api_error.py`: API错误代码常量和FastAPI异常处理器
- `core/error_handler.py`: 全面的错误处理器（ErrorHandler）
- `core/error_handling.py`: 错误码枚举和AIOpsException
- `core/error_handling_logging.py`: ErrorHandler和StructuredLogger
- `core/exception_handler.py`: AIOpsException和FastAPI异常处理器

## 3. 新的错误处理体系

新的错误处理体系包括：

- `core/exceptions/`: 自定义异常类（20种）
- `core/error_codes/`: 错误码定义和管理器（100+错误码）
- `core/error_logging/`: 错误日志记录、处理和告警
- `core/error_recovery/`: 错误恢复策略装饰器

## 4. 迁移步骤

### 4.1 阶段1: 新旧代码共存

在迁移初期，新旧代码可以共存。逐步将新功能使用新的异常类。

```python
# 旧代码（保持不变）
from aiops_core.error_handling import AIOpsException

# 新代码（使用新异常类）
from aiops_core.exceptions import ValidationException
```

### 4.2 阶段2: 逐步替换

按照以下优先级逐步替换：

1. **高优先级**: 核心业务逻辑
2. **中优先级**: API路由
3. **低优先级**: 辅助功能

#### 替换示例

**旧代码**:
```python
from aiops_core.error_handling import AIOpsException

def validate_user(username):
    if not username:
        raise AIOpsException(
            error_code="01_01_0001",
            message="用户名不能为空"
        )
```

**新代码**:
```python
from aiops_core.exceptions import ValidationException

def validate_user(username):
    if not username:
        raise ValidationException(
            message="用户名不能为空",
            field="username",
            value=""
        )
```

### 4.3 阶段3: FastAPI集成

使用新的FastAPI异常处理器：

```python
from fastapi import FastAPI
from aiops_core.error_logging import setup_exception_handlers

app = FastAPI()
setup_exception_handlers(app)
```

### 4.4 阶段4: 错误日志集成

使用新的错误日志记录器：

```python
from aiops_core.error_logging import log_error, log_exception

# 记录错误
log_error(
    error_code="01_01_0001",
    message="参数验证失败",
    severity="error",
    category="business"
)

# 记录异常
try:
    operation()
except Exception as e:
    log_exception(e)
```

### 4.5 阶段5: 错误恢复策略

使用错误恢复策略装饰器：

```python
from aiops_core.error_recovery import retry_with_backoff, circuit_breaker

@retry_with_backoff(max_attempts=3, base_delay=1.0)
def call_external_api():
    return external_api_call()

@circuit_breaker(failure_threshold=5, timeout=60)
def call_critical_service():
    return critical_service_call()
```

## 5. 映射关系

### 5.1 异常类映射

| 旧异常类 | 新异常类 | 说明 |
|---------|---------|------|
| AIOpsException | AIOpsBaseException | 基础异常类 |
| ValidationError | ValidationException | 验证异常 |
| NotFoundError | ResourceNotFoundException | 资源未找到 |
| PermissionDeniedError | PermissionDeniedException | 权限拒绝 |
| DatabaseException | DatabaseException | 数据库异常（保持不变） |
| AIException | AIModelException | AI模型异常 |

### 5.2 错误码映射

| 旧错误码 | 新错误码 | 说明 |
|---------|---------|------|
| VALIDATION_ERROR | 01_01_0001 | 验证错误 |
| NOT_FOUND | 01_02_0001 | 资源未找到 |
| PERMISSION_DENIED | 02_03_0001 | 权限拒绝 |
| DATABASE_ERROR | 09_06_0001 | 数据库错误 |

## 6. 兼容性处理

### 6.1 临时兼容层

为了平滑迁移，可以创建临时兼容层：

```python
# core/exceptions/compat.py
from aiops_core.exceptions import ValidationException as NewValidationException

class ValidationException(NewValidationException):
    """兼容层：保持旧API"""
    def __init__(self, message, error_code=None, **kwargs):
        if error_code is None:
            error_code = "01_01_0001"
        super().__init__(message=message, error_code=error_code, **kwargs)
```

### 6.2 渐进式迁移

使用特性开关控制新旧代码：

```python
from aiops_core.config import settings

if settings.USE_NEW_EXCEPTIONS:
    from aiops_core.exceptions import ValidationException
else:
    from aiops_core.exceptions.compat import ValidationException
```

## 7. 测试策略

### 7.1 单元测试

为迁移的代码编写单元测试：

```python
def test_validate_user_with_new_exception():
    with pytest.raises(ValidationException) as exc_info:
        validate_user("")
    
    assert exc_info.value.field == "username"
    assert exc_info.value.error_code == "01_01_0001"
```

### 7.2 集成测试

测试FastAPI异常处理器：

```python
def test_api_validation_error(client):
    response = client.post("/api/users", json={"username": ""})
    assert response.status_code == 400
    assert response.json()["error_code"] == "01_01_0001"
```

### 7.3 回归测试

确保迁移后功能正常：

```python
def test_user_creation_flow():
    # 测试完整的用户创建流程
    user = create_user("test@example.com")
    assert user.username == "test@example.com"
```

## 8. 监控和验证

### 8.1 错误统计

监控迁移前后的错误统计：

```python
from aiops_core.error_logging import get_error_stats

stats = get_error_stats()
print(f"错误统计: {stats}")
```

### 8.2 性能监控

监控异常处理的性能影响：

```python
import time

start = time.time()
for _ in range(1000):
    try:
        validate_user("")
    except ValidationException:
        pass
end = time.time()

print(f"平均处理时间: {(end - start) / 1000 * 1000:.2f}ms")
```

## 9. 回滚计划

如果迁移出现问题，可以回滚：

1. 恢复旧代码
2. 禁用新异常处理器
3. 使用特性开关切换回旧实现

## 10. 完成标准

迁移完成的标志：

- ✅ 所有核心业务逻辑使用新异常类
- ✅ 所有API路由使用新异常处理器
- ✅ 所有错误日志使用新日志记录器
- ✅ 所有单元测试通过
- ✅ 错误统计正常
- ✅ 性能无明显下降
- ✅ 旧代码可以安全删除

## 11. 清理旧代码

迁移完成后，可以删除旧代码：

```bash
# 删除旧文件
rm core/api_error.py
rm core/error_handler.py
rm core/error_handling.py
rm core/error_handling_logging.py
rm core/exception_handler.py
```

## 12. 常见问题

### Q1: 迁移会影响现有功能吗？

A: 使用渐进式迁移和特性开关，可以最小化影响。

### Q2: 如何处理旧代码中的自定义异常？

A: 创建兼容层或逐步迁移到新异常类。

### Q3: 迁移需要多长时间？

A: 取决于代码规模，建议分阶段进行，每个阶段1-2周。

### Q4: 如何确保迁移质量？

A: 编写完整的单元测试和集成测试，进行充分的回归测试。

## 13. 总结

迁移到新的错误处理体系是一个渐进的过程，需要仔细规划和执行。按照本指南的步骤，可以平滑地完成迁移，同时保证系统的稳定性和可靠性。
