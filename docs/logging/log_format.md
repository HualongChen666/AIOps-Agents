# 日志格式文档

## 概述

本文档描述AIOps Agent系统的结构化日志格式规范，包括日志字段定义、命名规范和使用示例。

## 日志格式规范

### JSON格式

系统采用JSON格式的结构化日志，确保日志的可解析性和可查询性。

```json
{
  "timestamp": "2026-07-03T10:30:45.123Z",
  "level": "INFO",
  "logger": "module.name",
  "message": "Operation completed successfully",
  "context": {
    "trace_id": "abc123def456",
    "span_id": "789ghi012jkl",
    "user_id": "user-123",
    "session_id": "session-456",
    "request_id": "req-789"
  },
  "module": "module_name",
  "function": "function_name",
  "line": 42
}
```

### 时间戳格式

- **格式**: ISO 8601
- **时区**: UTC
- **示例**: `2026-07-03T10:30:45.123Z`

## 日志字段定义

### 标准字段

| 字段名 | 类型 | 必需 | 说明 | 示例 |
|--------|------|------|------|------|
| `timestamp` | string | 是 | 日志时间戳（ISO 8601格式） | `2026-07-03T10:30:45.123Z` |
| `level` | string | 是 | 日志级别 | `INFO` |
| `logger` | string | 是 | 日志器名称 | `module.name` |
| `message` | string | 是 | 日志消息 | `Operation completed` |
| `module` | string | 否 | 模块名称 | `module_name` |
| `function` | string | 否 | 函数名称 | `function_name` |
| `line` | integer | 否 | 代码行号 | `42` |

### 上下文字段

| 字段名 | 类型 | 必需 | 说明 | 示例 |
|--------|------|------|------|------|
| `trace_id` | string | 否 | 分布式追踪ID | `abc123def456` |
| `span_id` | string | 否 | 当前跨度ID | `789ghi012jkl` |
| `parent_span_id` | string | 否 | 父跨度ID | `mno345pqr678` |
| `user_id` | string | 否 | 用户ID | `user-123` |
| `session_id` | string | 否 | 会话ID | `session-456` |
| `request_id` | string | 否 | 请求ID | `req-789` |
| `correlation_id` | string | 否 | 关联ID | `corr-012` |

### 扩展字段

| 字段名 | 类型 | 必需 | 说明 | 示例 |
|--------|------|------|------|------|
| `response_time` | float | 否 | 响应时间（秒） | `0.123` |
| `status_code` | integer | 否 | HTTP状态码 | `200` |
| `client_ip` | string | 否 | 客户端IP地址 | `192.168.1.1` |
| `user_agent` | string | 否 | 用户代理 | `Mozilla/5.0...` |
| `request_method` | string | 否 | HTTP方法 | `GET` |
| `request_path` | string | 否 | 请求路径 | `/api/users` |

### 异常字段

| 字段名 | 类型 | 必需 | 说明 | 示例 |
|--------|------|------|------|------|
| `exception` | object | 否 | 异常信息 | - |
| `exception.type` | string | 否 | 异常类型 | `ValueError` |
| `exception.message` | string | 否 | 异常消息 | `Invalid value` |
| `exception.traceback` | string | 否 | 异常堆栈 | `Traceback...` |

## 日志级别

| 级别 | 说明 | 使用场景 |
|------|------|----------|
| `DEBUG` | 调试信息 | 开发调试、详细执行流程 |
| `INFO` | 一般信息 | 正常操作、状态变更 |
| `WARNING` | 警告信息 | 潜在问题、降级操作 |
| `ERROR` | 错误信息 | 错误发生、操作失败 |
| `CRITICAL` | 严重错误 | 系统故障、服务不可用 |

## 字段命名规范

### 命名规则

- 使用蛇形命名法（snake_case）
- 使用小写字母
- 使用下划线分隔单词
- 避免使用缩写（除非是通用缩写）

### 示例

- ✅ `user_id`
- ✅ `response_time`
- ✅ `trace_id`
- ❌ `userId`
- ❌ `responseTime`
- ❌ `TraceID`

## 日志分类

### 应用日志

记录应用程序的运行状态和业务操作。

```json
{
  "timestamp": "2026-07-03T10:30:45.123Z",
  "level": "INFO",
  "logger": "auth.service",
  "message": "User login successful",
  "context": {
    "user_id": "user-123",
    "session_id": "session-456"
  }
}
```

### 访问日志

记录HTTP请求和响应信息。

```json
{
  "timestamp": "2026-07-03T10:30:45.123Z",
  "level": "INFO",
  "logger": "access.log",
  "message": "HTTP request received",
  "context": {
    "request_method": "GET",
    "request_path": "/api/users",
    "status_code": 200,
    "response_time": 0.123,
    "client_ip": "192.168.1.1"
  }
}
```

### 错误日志

记录错误和异常信息。

```json
{
  "timestamp": "2026-07-03T10:30:45.123Z",
  "level": "ERROR",
  "logger": "database.service",
  "message": "Database connection failed",
  "context": {
    "trace_id": "abc123def456"
  },
  "exception": {
    "type": "ConnectionError",
    "message": "Connection timeout",
    "traceback": "Traceback (most recent call last)..."
  }
}
```

### 审计日志

记录敏感操作和审计追踪。

```json
{
  "timestamp": "2026-07-03T10:30:45.123Z",
  "level": "INFO",
  "logger": "audit.log",
  "message": "User permission changed",
  "context": {
    "user_id": "admin-001",
    "target_user_id": "user-123",
    "action": "permission_change",
    "old_permissions": ["read"],
    "new_permissions": ["read", "write"]
  }
}
```

### 性能日志

记录性能指标和响应时间。

```json
{
  "timestamp": "2026-07-03T10:30:45.123Z",
  "level": "INFO",
  "logger": "performance.monitor",
  "message": "API performance metrics",
  "context": {
    "endpoint": "/api/users",
    "response_time": 0.123,
    "memory_usage": 1024000,
    "cpu_usage": 0.45
  }
}
```

## 敏感信息脱敏

### 脱敏规则

| 敏感字段 | 脱敏策略 | 示例 |
|----------|----------|------|
| `password` | 完全脱敏 | `******` |
| `token` | 部分脱敏 | `abc****xyz` |
| `phone` | 部分脱敏 | `138****1234` |
| `id_card` | 部分脱敏 | `110***********123` |
| `email` | 部分脱敏 | `u***@example.com` |

### 脱敏实现

```python
from aiops_core.logging.context import LoggingContextManager

manager = LoggingContextManager()
# 敏感信息会自动脱敏
manager.set_custom_context("password", "secret123")
# 日志输出: password: ******
```

## 最佳实践

### 1. 结构化日志

始终使用结构化日志格式，避免字符串拼接。

```python
# ✅ 推荐
logger.info("User login", context={"user_id": "user-123", "ip": "192.168.1.1"})

# ❌ 不推荐
logger.info(f"User login: user-123 from 192.168.1.1")
```

### 2. 上下文追踪

使用上下文管理器自动注入追踪信息。

```python
from aiops_core.logging.context import LoggingContextManager

manager = LoggingContextManager()
with manager.context(trace_id="abc123", user_id="user-456"):
    logger.info("Processing request")
```

### 3. 日志级别选择

根据日志的重要性选择合适的级别。

```python
logger.debug("Variable value: x=5")  # 调试信息
logger.info("Operation completed")    # 一般信息
logger.warning("Cache miss")         # 警告信息
logger.error("Database error")        # 错误信息
logger.critical("System down")        # 严重错误
```

### 4. 异常日志

记录异常时包含完整的异常信息。

```python
try:
    operation()
except Exception as e:
    logger.exception("Operation failed", context={"operation": "task_name"})
```

## 常见问题

### Q: 如何添加自定义字段？

A: 通过上下文管理器添加自定义字段：

```python
from aiops_core.logging.context import LoggingContextManager

manager = LoggingContextManager()
manager.set_custom_context("custom_field", "custom_value")
```

### Q: 如何追踪分布式请求？

A: 使用trace_id和span_id进行分布式追踪：

```python
from aiops_core.logging.context import LoggingContextManager

manager = LoggingContextManager()
manager.start_trace()
# 自动生成trace_id和span_id
```

### Q: 如何过滤特定级别的日志？

A: 使用日志分级策略：

```python
from aiops_core.logging.level import LogLevelManager

manager = LogLevelManager()
manager.set_module_level("noisy.module", LogLevel.WARNING)
```

## 技术评审检查清单

- [x] 日志格式符合JSON规范
- [x] 时间戳使用ISO 8601格式
- [x] 字段命名遵循蛇形命名法
- [x] 包含所有必需的标准字段
- [x] 包含完整的上下文字段定义
- [x] 包含扩展字段定义
- [x] 包含异常字段定义
- [x] 包含日志级别定义
- [x] 包含日志分类和示例
- [x] 包含敏感信息脱敏规则
- [x] 包含最佳实践指南
- [x] 包含常见问题解答
