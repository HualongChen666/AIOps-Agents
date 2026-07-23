# 异常类型设计文档

## 1. 概述

本文档定义了AIOps Agent系统的统一异常类型体系，包括17种自定义异常类的详细设计。

## 2. 异常层次结构

```
BaseException (Python内置)
    └── AIOpsBaseException (AIOps基础异常)
            ├── BusinessException (业务异常)
            │   ├── ValidationException (验证异常)
            │   ├── ResourceNotFoundException (资源未找到)
            │   ├── BusinessLogicException (业务逻辑异常)
            │   └── StateInvalidException (状态无效异常)
            │
            ├── SystemException (系统异常)
            │   ├── DatabaseException (数据库异常)
            │   ├── NetworkException (网络异常)
            │   ├── CacheException (缓存异常)
            │   ├── ConfigurationException (配置异常)
            │   └── ResourceException (资源异常)
            │
            ├── SecurityException (安全异常)
            │   ├── AuthenticationException (认证异常)
            │   ├── AuthorizationException (授权异常)
            │   └── PermissionDeniedException (权限拒绝异常)
            │
            ├── ThirdPartyException (第三方异常)
            │   ├── ExternalServiceException (外部服务异常)
            │   ├── AIModelException (AI模型异常)
            │   └── IntegrationException (集成异常)
            │
            └── CriticalException (严重异常)
                ├── SystemFatalException (系统致命异常)
                └── DataCorruptionException (数据损坏异常)
```

## 3. 异常类型详细定义

### 3.1 AIOpsBaseException

**描述**: AIOps系统的基础异常类，所有自定义异常的基类。

**属性**:
- `message`: 错误消息
- `error_code`: 错误码
- `severity`: 严重程度 (DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL)
- `category`: 错误分类
- `context`: 上下文信息
- `error_id`: 错误唯一标识
- `timestamp`: 发生时间
- `stack_trace`: 堆栈追踪
- `original_exception`: 原始异常

**方法**:
- `to_dict()`: 转换为字典格式
- `to_json()`: 转换为JSON格式
- `with_context()`: 添加上下文信息

### 3.2 BusinessException

**描述**: 业务逻辑相关的异常基类。

**子类**:
- ValidationException
- ResourceNotFoundException
- BusinessLogicException
- StateInvalidException

### 3.3 ValidationException

**描述**: 输入验证失败异常。

**适用场景**:
- 参数验证失败
- 数据格式错误
- 必填字段缺失
- 数据类型不匹配

**HTTP状态码**: 400

**错误码**: 01_01_0001

**示例**:
```python
raise ValidationException(
    message="用户名不能为空",
    field="username",
    value=""
)
```

### 3.4 ResourceNotFoundException

**描述**: 资源未找到异常。

**适用场景**:
- 数据库记录不存在
- 文件不存在
- API端点不存在
- 配置项不存在

**HTTP状态码**: 404

**错误码**: 01_02_0001

**示例**:
```python
raise ResourceNotFoundException(
    message="用户不存在",
    resource_type="User",
    resource_id=123
)
```

### 3.5 BusinessLogicException

**描述**: 业务逻辑错误异常。

**适用场景**:
- 业务规则违反
- 操作不允许
- 数据冲突
- 依赖关系错误

**HTTP状态码**: 422

**错误码**: 01_04_0001

**示例**:
```python
raise BusinessLogicException(
    message="用户余额不足",
    operation="withdraw",
    current_balance=100,
    required_amount=200
)
```

### 3.6 StateInvalidException

**描述**: 状态无效异常。

**适用场景**:
- 对象状态不允许操作
- 工作流状态错误
- 生命周期状态错误

**HTTP状态码**: 422

**错误码**: 01_05_0001

**示例**:
```python
raise StateInvalidException(
    message="订单状态不允许取消",
    current_state="shipped",
    required_state="pending"
)
```

### 3.7 SystemException

**描述**: 系统相关的异常基类。

**子类**:
- DatabaseException
- NetworkException
- CacheException
- ConfigurationException
- ResourceException

### 3.8 DatabaseException

**描述**: 数据库相关异常。

**适用场景**:
- 数据库连接失败
- SQL查询错误
- 约束冲突
- 事务失败

**HTTP状态码**: 500

**错误码**: 09_06_0001

**示例**:
```python
raise DatabaseException(
    message="数据库连接失败",
    host="localhost",
    port=5432,
    database="aiops"
)
```

### 3.9 NetworkException

**描述**: 网络相关异常。

**适用场景**:
- 网络连接失败
- 请求超时
- DNS解析失败
- 连接中断

**HTTP状态码**: 503

**错误码**: 17_06_0001

**示例**:
```python
raise NetworkException(
    message="连接超时",
    url="https://api.example.com",
    timeout=30
)
```

### 3.10 CacheException

**描述**: 缓存相关异常。

**适用场景**:
- 缓存连接失败
- 缓存读写错误
- 缓存序列化错误

**HTTP状态码**: 500

**错误码**: 10_06_0001

**示例**:
```python
raise CacheException(
    message="缓存写入失败",
    cache_type="redis",
    key="user:123"
)
```

### 3.11 ConfigurationException

**描述**: 配置相关异常。

**适用场景**:
- 配置文件缺失
- 配置项错误
- 环境变量缺失
- 配置格式错误

**HTTP状态码**: 500

**错误码**: 16_14_0001

**示例**:
```python
raise ConfigurationException(
    message="配置项缺失",
    config_key="DATABASE_URL",
    config_file="config.yaml"
)
```

### 3.12 ResourceException

**描述**: 资源相关异常。

**适用场景**:
- 内存不足
- 磁盘空间不足
- CPU使用率过高
- 文件句柄耗尽

**HTTP状态码**: 503

**错误码**: 18_06_0001

**示例**:
```python
raise ResourceException(
    message="内存不足",
    resource_type="memory",
    available_mb=100,
    required_mb=500
)
```

### 3.13 SecurityException

**描述**: 安全相关的异常基类。

**子类**:
- AuthenticationException
- AuthorizationException
- PermissionDeniedException

### 3.14 AuthenticationException

**描述**: 认证失败异常。

**适用场景**:
- 用户名或密码错误
- Token无效
- Token过期
- 认证服务不可用

**HTTP状态码**: 401

**错误码**: 02_01_0001

**示例**:
```python
raise AuthenticationException(
    message="Token已过期",
    token="eyJhbGciOiJIUzI1NiIs...",
    expired_at="2024-01-01T00:00:00Z"
)
```

### 3.15 AuthorizationException

**描述**: 授权失败异常。

**适用场景**:
- 权限不足
- 角色权限不足
- 资源访问被拒绝

**HTTP状态码**: 403

**错误码**: 02_03_0001

**示例**:
```python
raise AuthorizationException(
    message="权限不足",
    required_role="admin",
    current_role="user"
)
```

### 3.16 PermissionDeniedException

**描述**: 权限拒绝异常。

**适用场景**:
- 资源访问被拒绝
- 操作权限不足
- 访问控制拒绝

**HTTP状态码**: 403

**错误码**: 02_03_0002

**示例**:
```python
raise PermissionDeniedException(
    message="无权访问该资源",
    resource="user:123",
    action="delete"
)
```

### 3.17 ThirdPartyException

**描述**: 第三方服务相关的异常基类。

**子类**:
- ExternalServiceException
- AIModelException
- IntegrationException

### 3.18 ExternalServiceException

**描述**: 外部服务异常。

**适用场景**:
- 外部API调用失败
- 第三方服务不可用
- 外部服务响应错误

**HTTP状态码**: 502

**错误码**: 15_06_0001

**示例**:
```python
raise ExternalServiceException(
    message="外部服务不可用",
    service_name="OpenAI API",
    service_url="https://api.openai.com"
)
```

### 3.19 AIModelException

**描述**: AI模型相关异常。

**适用场景**:
- 模型加载失败
- 模型推理错误
- API调用限流
- Token使用超限

**HTTP状态码**: 500

**错误码**: 11_12_0001

**示例**:
```python
raise AIModelException(
    message="模型推理失败",
    model_name="gpt-4",
    error_type="timeout"
)
```

### 3.20 IntegrationException

**描述**: 集成相关异常。

**适用场景**:
- 集成接口错误
- 数据同步失败
- 集成配置错误

**HTTP状态码**: 502

**错误码**: 19_06_0001

**示例**:
```python
raise IntegrationException(
    message="数据同步失败",
    integration_type="GitLab",
    sync_operation="pull"
)
```

### 3.21 CriticalException

**描述**: 严重异常基类。

**子类**:
- SystemFatalException
- DataCorruptionException

### 3.22 SystemFatalException

**描述**: 系统致命异常。

**适用场景**:
- 系统崩溃
- 核心服务不可用
- 严重资源耗尽

**HTTP状态码**: 500

**错误码**: 20_15_0001

**示例**:
```python
raise SystemFatalException(
    message="系统核心服务崩溃",
    service="database",
    error_code="FATAL_ERROR"
)
```

### 3.23 DataCorruptionException

**描述**: 数据损坏异常。

**适用场景**:
- 数据完整性损坏
- 数据不一致
- 数据文件损坏

**HTTP状态码**: 500

**错误码**: 09_13_0001

**示例**:
```python
raise DataCorruptionException(
    message="数据完整性检查失败",
    table="users",
    constraint="unique_username"
)
```

## 4. 异常属性定义

### 4.1 ErrorSeverity 枚举

```python
from enum import Enum

class ErrorSeverity(Enum):
    """错误严重程度"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"
```

### 4.2 ErrorCategory 枚举

```python
class ErrorCategory(Enum):
    """错误分类"""
    BUSINESS = "business"
    SYSTEM = "system"
    SECURITY = "security"
    THIRD_PARTY = "third_party"
    CRITICAL = "critical"
```

## 5. 异常使用示例

### 5.1 基本使用

```python
from aiops_core.exceptions import ValidationException, DatabaseException

# 验证异常
if not username:
    raise ValidationException(
        message="用户名不能为空",
        field="username"
    )

# 数据库异常
try:
    await db.execute(query)
except Exception as e:
    raise DatabaseException(
        message="数据库查询失败",
        query=str(query),
        original_exception=e
    )
```

### 5.2 带上下文的异常

```python
from aiops_core.exceptions import BusinessLogicException

raise BusinessLogicException(
    message="用户余额不足",
    context={
        "user_id": 123,
        "current_balance": 100,
        "required_amount": 200,
        "operation": "withdraw"
    }
)
```

### 5.3 异常链

```python
from aiops_core.exceptions import ExternalServiceException, NetworkException

try:
    response = await external_api.call()
except ConnectionError as e:
    raise NetworkException(
        message="网络连接失败",
        url=external_api.url,
        original_exception=e
    ) from e
except Exception as e:
    raise ExternalServiceException(
        message="外部服务调用失败",
        service_name="External API",
        original_exception=e
    ) from e
```

## 6. 异常处理最佳实践

### 6.1 异常捕获

```python
from aiops_core.exceptions import (
    ValidationException,
    ResourceNotFoundException,
    DatabaseException,
    AIOpsBaseException
)

try:
    # 业务逻辑
    result = await some_operation()
except ValidationException as e:
    # 处理验证错误
    return {"error": e.message, "field": e.context.get("field")}
except ResourceNotFoundException as e:
    # 处理资源未找到
    return {"error": e.message, "resource": e.context.get("resource_type")}
except DatabaseException as e:
    # 处理数据库错误
    logger.error(f"Database error: {e.message}")
    raise
except AIOpsBaseException as e:
    # 处理所有AIOps异常
    logger.error(f"AIOps error: {e.message}")
    raise
except Exception as e:
    # 处理未知异常
    logger.error(f"Unexpected error: {e}")
    raise
```

### 6.2 异常日志记录

```python
from loguru import logger
from aiops_core.exceptions import AIOpsBaseException

try:
    await some_operation()
except AIOpsBaseException as e:
    logger.error(
        f"Error occurred: {e.message}",
        extra={
            "error_code": e.error_code,
            "severity": e.severity.value,
            "category": e.category.value,
            "context": e.context,
            "error_id": e.error_id,
        }
    )
    raise
```

### 6.3 异常转换

```python
from aiops_core.exceptions import DatabaseException, AIOpsBaseException

def convert_exception(e: Exception) -> AIOpsBaseException:
    """将标准异常转换为AIOps异常"""
    if isinstance(e, ConnectionError):
        return DatabaseException(
            message="数据库连接失败",
            original_exception=e
        )
    elif isinstance(e, TimeoutError):
        return DatabaseException(
            message="数据库操作超时",
            original_exception=e
        )
    else:
        return DatabaseException(
            message="数据库错误",
            original_exception=e
        )
```

## 7. 异常测试

### 7.1 单元测试示例

```python
import pytest
from aiops_core.exceptions import ValidationException, DatabaseException

def test_validation_exception():
    """测试验证异常"""
    exc = ValidationException(
        message="用户名不能为空",
        field="username"
    )
    
    assert exc.message == "用户名不能为空"
    assert exc.context["field"] == "username"
    assert exc.severity.value == "warning"
    assert exc.category.value == "business"

def test_exception_to_dict():
    """测试异常转换为字典"""
    exc = DatabaseException(
        message="数据库连接失败",
        host="localhost"
    )
    
    exc_dict = exc.to_dict()
    assert exc_dict["message"] == "数据库连接失败"
    assert exc_dict["error_code"] == "09_06_0001"
    assert "error_id" in exc_dict
    assert "timestamp" in exc_dict
```

## 8. 异常与错误码映射

| 异常类型 | 默认错误码 | HTTP状态码 | 严重程度 |
|---------|-----------|-----------|---------|
| ValidationException | 01_01_0001 | 400 | WARNING |
| ResourceNotFoundException | 01_02_0001 | 404 | ERROR |
| BusinessLogicException | 01_04_0001 | 422 | ERROR |
| StateInvalidException | 01_05_0001 | 422 | ERROR |
| DatabaseException | 09_06_0001 | 500 | ERROR |
| NetworkException | 17_06_0001 | 503 | ERROR |
| CacheException | 10_06_0001 | 500 | WARNING |
| ConfigurationException | 16_14_0001 | 500 | CRITICAL |
| ResourceException | 18_06_0001 | 503 | ERROR |
| AuthenticationException | 02_01_0001 | 401 | WARNING |
| AuthorizationException | 02_03_0001 | 403 | ERROR |
| PermissionDeniedException | 02_03_0002 | 403 | ERROR |
| ExternalServiceException | 15_06_0001 | 502 | ERROR |
| AIModelException | 11_12_0001 | 500 | ERROR |
| IntegrationException | 19_06_0001 | 502 | ERROR |
| SystemFatalException | 20_15_0001 | 500 | FATAL |
| DataCorruptionException | 09_13_0001 | 500 | FATAL |

## 9. 附录

### 9.1 异常类文件结构

```
core/exceptions/
├── __init__.py           # 导出所有异常类
├── base.py              # 基础异常类
├── business.py          # 业务异常
├── system.py            # 系统异常
├── security.py          # 安全异常
├── third_party.py       # 第三方异常
└── critical.py          # 严重异常
```

### 9.2 版本历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|---------|
| 1.0 | 2024-01-01 | AIOps Team | 初始版本，定义17种异常类型 |
