# 结构化日志格式设计文档

## 1. 设计目标

### 1.1 核心目标
- **标准化**: 统一日志格式，便于日志解析和分析
- **结构化**: 使用JSON格式，支持机器解析和查询
- **可扩展**: 支持自定义字段和元数据
- **高性能**: 最小化日志对系统性能的影响
- **安全性**: 支持敏感信息脱敏

### 1.2 设计原则
- **一致性**: 所有日志使用统一的格式和字段命名
- **完整性**: 包含足够的上下文信息用于问题排查
- **可读性**: JSON格式便于人类阅读和机器解析
- **可追溯**: 支持分布式追踪和请求链路追踪
- **合规性**: 满足安全审计和合规要求

## 2. 日志格式标准

### 2.1 基础格式规范

所有日志采用JSON格式，遵循以下规范：

```json
{
  "timestamp": "2026-07-03T14:30:45.123Z",
  "level": "INFO",
  "logger": "core.ai_engine",
  "message": "AI request processed successfully",
  "context": {
    "trace_id": "abc123def456",
    "span_id": "789xyz",
    "user_id": "user_123",
    "request_id": "req_456",
    "module": "ai_engine",
    "function": "process_request",
    "line": 123
  },
  "extra": {
    "response_time": 150,
    "status_code": 200,
    "model": "gpt-4",
    "tokens": 1500
  }
}
```

### 2.2 字段命名规范
- 使用蛇形命名法（snake_case）
- 字段名使用小写字母和下划线
- 避免使用特殊字符和空格
- 保持字段名简洁但具有描述性

### 2.3 时间戳格式
- 使用ISO 8601格式
- 时区使用UTC
- 精度到毫秒
- 示例: `2026-07-03T14:30:45.123Z`

## 3. 日志字段体系

### 3.1 标准字段（20+个）

#### 3.1.1 必需字段（5个）

| 字段名 | 类型 | 描述 | 示例 |
|--------|------|------|------|
| `timestamp` | string | 日志时间戳（ISO 8601 UTC） | "2026-07-03T14:30:45.123Z" |
| `level` | string | 日志级别 | "INFO", "ERROR", "DEBUG" |
| `logger` | string | 日志器名称（模块路径） | "core.ai_engine" |
| `message` | string | 日志消息 | "AI request processed successfully" |
| `context` | object | 上下文信息 | {"trace_id": "abc123"} |

#### 3.1.2 上下文字段（10个）

| 字段名 | 类型 | 描述 | 示例 |
|--------|------|------|------|
| `trace_id` | string | 分布式追踪ID | "abc123def456" |
| `span_id` | string | 当前span ID | "789xyz" |
| `parent_span_id` | string | 父span ID | "parent_123" |
| `user_id` | string | 用户ID | "user_123" |
| `session_id` | string | 会话ID | "session_456" |
| `request_id` | string | 请求ID | "req_789" |
| `correlation_id` | string | 关联ID | "corr_012" |
| `module` | string | 模块名称 | "ai_engine" |
| `function` | string | 函数名称 | "process_request" |
| `line` | integer | 代码行号 | 123 |

#### 3.1.3 扩展字段（10+个）

| 字段名 | 类型 | 描述 | 示例 |
|--------|------|------|------|
| `response_time` | number | 响应时间（毫秒） | 150.5 |
| `status_code` | integer | HTTP状态码 | 200 |
| `error_code` | string | 错误码 | "ERR_001" |
| `error_type` | string | 错误类型 | "ValidationException" |
| `error_message` | string | 错误消息 | "Invalid input" |
| `stack_trace` | string | 堆栈跟踪 | "Traceback..." |
| `host` | string | 主机名 | "server-01" |
| `service` | string | 服务名称 | "ai-service" |
| `version` | string | 服务版本 | "v2.0.1" |
| `environment` | string | 环境名称 | "production" |

#### 3.1.4 自定义字段（动态）

| 字段名 | 类型 | 描述 | 示例 |
|--------|------|------|------|
| `custom_*` | any | 自定义字段 | "custom_field": "value" |

### 3.2 字段定义规范

#### 3.2.1 字段类型
- **string**: 字符串类型
- **number**: 数值类型（整数或浮点数）
- **boolean**: 布尔类型
- **object**: 对象类型（嵌套结构）
- **array**: 数组类型
- **null**: 空值

#### 3.2.2 字段约束
- 字段名长度: 1-64字符
- 字符串值长度: 最多1024字符
- 嵌套深度: 最多5层
- 数组长度: 最多100个元素

## 4. 日志分类体系

### 4.1 日志分类（5种）

#### 4.1.1 应用日志（Application Log）
- **描述**: 应用程序运行时产生的日志
- **级别**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **用途**: 应用程序调试和监控
- **示例**:
```json
{
  "timestamp": "2026-07-03T14:30:45.123Z",
  "level": "INFO",
  "logger": "core.ai_engine",
  "message": "AI request processed successfully",
  "category": "application",
  "context": {
    "module": "ai_engine",
    "function": "process_request"
  }
}
```

#### 4.1.2 访问日志（Access Log）
- **描述**: HTTP请求和响应日志
- **级别**: INFO
- **用途**: API访问分析和安全审计
- **示例**:
```json
{
  "timestamp": "2026-07-03T14:30:45.123Z",
  "level": "INFO",
  "logger": "api.health_router",
  "message": "GET /api/health 200",
  "category": "access",
  "context": {
    "method": "GET",
    "path": "/api/health",
    "status_code": 200,
    "client_ip": "192.168.1.100",
    "user_agent": "Mozilla/5.0",
    "response_time": 50
  }
}
```

#### 4.1.3 错误日志（Error Log）
- **描述**: 错误和异常日志
- **级别**: ERROR, CRITICAL
- **用途**: 错误排查和问题诊断
- **示例**:
```json
{
  "timestamp": "2026-07-03T14:30:45.123Z",
  "level": "ERROR",
  "logger": "core.ai_engine",
  "message": "AI model inference failed",
  "category": "error",
  "context": {
    "error_code": "AI_001",
    "error_type": "AIModelException",
    "error_message": "Model timeout",
    "stack_trace": "Traceback..."
  }
}
```

#### 4.1.4 审计日志（Audit Log）
- **描述**: 安全审计和合规日志
- **级别**: INFO, WARNING
- **用途**: 安全审计和合规检查
- **示例**:
```json
{
  "timestamp": "2026-07-03T14:30:45.123Z",
  "level": "INFO",
  "logger": "core.authentication",
  "message": "User login successful",
  "category": "audit",
  "context": {
    "user_id": "user_123",
    "action": "login",
    "resource": "/api/dashboard",
    "result": "success",
    "ip_address": "192.168.1.100"
  }
}
```

#### 4.1.5 性能日志（Performance Log）
- **描述**: 性能指标和监控日志
- **级别**: INFO, WARNING
- **用途**: 性能监控和优化
- **示例**:
```json
{
  "timestamp": "2026-07-03T14:30:45.123Z",
  "level": "INFO",
  "logger": "core.performance",
  "message": "API response time",
  "category": "performance",
  "context": {
    "endpoint": "/api/ai/query",
    "response_time": 150,
    "p50": 100,
    "p95": 200,
    "p99": 350,
    "throughput": 1000
  }
}
```

### 4.2 日志分类标识

所有日志必须包含`category`字段，用于标识日志分类：

```json
{
  "category": "application|access|error|audit|performance"
}
```

## 5. 敏感信息脱敏规则

### 5.1 脱敏策略

#### 5.1.1 完全脱敏
- **适用字段**: 密码、密钥、Token
- **脱敏方式**: 完全替换为`[REDACTED]`
- **示例**:
```json
{
  "password": "[REDACTED]",
  "api_key": "[REDACTED]",
  "secret": "[REDACTED]"
}
```

#### 5.1.2 部分脱敏
- **适用字段**: 手机号、身份证号、邮箱
- **脱敏方式**: 保留部分信息，其余替换为`*`
- **示例**:
```json
{
  "phone": "138****5678",
  "id_card": "110101********1234",
  "email": "user***@example.com"
}
```

#### 5.1.3 哈希脱敏
- **适用字段**: 用户ID、会话ID
- **脱敏方式**: 使用SHA-256哈希
- **示例**:
```json
{
  "user_id": "a1b2c3d4e5f6...",
  "session_id": "f6e5d4c3b2a1..."
}
```

### 5.2 脱敏字段列表

| 字段名 | 脱敏方式 | 示例 |
|--------|----------|------|
| `password` | 完全脱敏 | "[REDACTED]" |
| `api_key` | 完全脱敏 | "[REDACTED]" |
| `secret` | 完全脱敏 | "[REDACTED]" |
| `token` | 完全脱敏 | "[REDACTED]" |
| `phone` | 部分脱敏 | "138****5678" |
| `mobile` | 部分脱敏 | "138****5678" |
| `id_card` | 部分脱敏 | "110101********1234" |
| `email` | 部分脱敏 | "user***@example.com" |
| `user_id` | 哈希脱敏 | "a1b2c3d4e5f6..." |
| `session_id` | 哈希脱敏 | "f6e5d4c3b2a1..." |
| `credit_card` | 部分脱敏 | "1234****5678" |
| `bank_account` | 部分脱敏 | "6222********1234" |

### 5.3 脱敏实现

#### 5.3.1 自动脱敏
- 日志记录器自动识别敏感字段
- 根据字段名匹配脱敏规则
- 应用相应的脱敏策略

#### 5.3.2 手动脱敏
- 开发者手动标记敏感字段
- 使用`@sensitive`装饰器
- 调用脱敏API

## 6. 日志压缩和归档策略

### 6.1 日志轮转

#### 6.1.1 时间轮转
- **轮转周期**: 每天（00:00）
- **文件命名**: `{logger}_{YYYY-MM-DD}.jsonl`
- **示例**: `ai_engine_2026-07-03.jsonl`

#### 6.1.2 大小轮转
- **文件大小限制**: 100MB
- **文件数量限制**: 30个文件
- **超出策略**: 删除最旧的文件

### 6.2 日志压缩

#### 6.2.1 压缩格式
- **压缩算法**: Gzip
- **压缩级别**: 6
- **压缩后命名**: `{logger}_{YYYY-MM-DD}.jsonl.gz`

#### 6.2.2 压缩时机
- **自动压缩**: 日志轮转后立即压缩
- **延迟压缩**: 轮转后24小时压缩
- **手动压缩**: 通过API触发

#### 6.2.3 压缩效果
- **压缩比**: 约10:1
- **压缩时间**: 100MB文件约10秒
- **CPU影响**: 轻微（<5%）

### 6.3 日志归档

#### 6.3.1 归档策略
- **短期归档**: 保留最近30天
- **中期归档**: 保留最近90天（压缩存储）
- **长期归档**: 保留最近365天（冷存储）

#### 6.3.2 归档存储
- **本地存储**: `/var/log/aiops/`
- **对象存储**: S3/OSS兼容存储
- **归档路径**: `aiops/logs/{year}/{month}/{day}/`

#### 6.3.3 归档清理
- **自动清理**: 超过365天的日志自动删除
- **手动清理**: 通过API手动删除
- **保留策略**: 重要日志永久保留

### 6.4 日志保留策略

| 日志分类 | 短期（30天） | 中期（90天） | 长期（365天） | 永久保留 |
|----------|--------------|--------------|---------------|----------|
| 应用日志 | ✅ 原始 | ✅ 压缩 | ✅ 冷存储 | ❌ |
| 访问日志 | ✅ 原始 | ✅ 压缩 | ✅ 冷存储 | ❌ |
| 错误日志 | ✅ 原始 | ✅ 压缩 | ✅ 冷存储 | ✅ |
| 审计日志 | ✅ 原始 | ✅ 压缩 | ✅ 冷存储 | ✅ |
| 性能日志 | ✅ 原始 | ✅ 压缩 | ✅ 冷存储 | ❌ |

## 7. 日志格式示例

### 7.1 完整示例

```json
{
  "timestamp": "2026-07-03T14:30:45.123Z",
  "level": "INFO",
  "logger": "core.ai_engine",
  "message": "AI request processed successfully",
  "category": "application",
  "context": {
    "trace_id": "abc123def456",
    "span_id": "789xyz",
    "parent_span_id": "parent_123",
    "user_id": "a1b2c3d4e5f6...",
    "session_id": "f6e5d4c3b2a1...",
    "request_id": "req_789",
    "correlation_id": "corr_012",
    "module": "ai_engine",
    "function": "process_request",
    "line": 123
  },
  "extra": {
    "response_time": 150.5,
    "status_code": 200,
    "model": "gpt-4",
    "tokens": 1500,
    "host": "server-01",
    "service": "ai-service",
    "version": "v2.0.1",
    "environment": "production"
  }
}
```

### 7.2 错误日志示例

```json
{
  "timestamp": "2026-07-03T14:30:45.123Z",
  "level": "ERROR",
  "logger": "core.ai_engine",
  "message": "AI model inference failed",
  "category": "error",
  "context": {
    "trace_id": "abc123def456",
    "module": "ai_engine",
    "function": "process_request",
    "line": 456
  },
  "extra": {
    "error_code": "AI_001",
    "error_type": "AIModelException",
    "error_message": "Model timeout after 30 seconds",
    "stack_trace": "Traceback (most recent call last):\n  File \"core/ai_engine.py\", line 456, in process_request\n    result = await model.predict(input)\nTimeoutError: Model timeout"
  }
}
```

### 7.3 访问日志示例

```json
{
  "timestamp": "2026-07-03T14:30:45.123Z",
  "level": "INFO",
  "logger": "api.health_router",
  "message": "GET /api/health 200",
  "category": "access",
  "context": {
    "request_id": "req_789",
    "module": "health_router",
    "function": "health_check"
  },
  "extra": {
    "method": "GET",
    "path": "/api/health",
    "status_code": 200,
    "client_ip": "192.168.1.100",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "response_time": 50,
    "request_size": 1024,
    "response_size": 2048
  }
}
```

### 7.4 审计日志示例

```json
{
  "timestamp": "2026-07-03T14:30:45.123Z",
  "level": "INFO",
  "logger": "core.authentication",
  "message": "User login successful",
  "category": "audit",
  "context": {
    "user_id": "a1b2c3d4e5f6...",
    "session_id": "f6e5d4c3b2a1...",
    "module": "authentication",
    "function": "login"
  },
  "extra": {
    "action": "login",
    "resource": "/api/dashboard",
    "result": "success",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0",
    "mfa_verified": true,
    "login_method": "password"
  }
}
```

### 7.5 性能日志示例

```json
{
  "timestamp": "2026-07-03T14:30:45.123Z",
  "level": "INFO",
  "logger": "core.performance",
  "message": "API response time",
  "category": "performance",
  "context": {
    "request_id": "req_789",
    "module": "performance",
    "function": "record_metrics"
  },
  "extra": {
    "endpoint": "/api/ai/query",
    "response_time": 150,
    "p50": 100,
    "p95": 200,
    "p99": 350,
    "throughput": 1000,
    "error_rate": 0.01,
    "cpu_usage": 45.5,
    "memory_usage": 512,
    "disk_usage": 75.2
  }
}
```

## 8. 技术评审检查清单

- [x] 日志格式采用JSON标准
- [x] 定义了20+个标准字段
- [x] 定义了5种日志分类
- [x] 定义了敏感信息脱敏规则
- [x] 定义了日志压缩和归档策略
- [x] 提供了完整的日志格式示例
- [x] 字段命名规范一致
- [x] 时间戳格式符合ISO 8601标准
- [x] 支持分布式追踪（trace_id, span_id）
- [x] 支持用户行为追踪（user_id, session_id）
- [x] 支持请求链路追踪（request_id, correlation_id）
- [x] 脱敏规则覆盖常见敏感信息
- [x] 压缩策略合理，不影响性能
- [x] 归档策略符合合规要求
- [x] 日志分类清晰，用途明确

## 9. 附录

### 9.1 字段完整列表

| 字段名 | 类型 | 必需 | 描述 | 分类 |
|--------|------|------|------|------|
| timestamp | string | ✅ | 日志时间戳 | 标准 |
| level | string | ✅ | 日志级别 | 标准 |
| logger | string | ✅ | 日志器名称 | 标准 |
| message | string | ✅ | 日志消息 | 标准 |
| context | object | ✅ | 上下文信息 | 标准 |
| category | string | ✅ | 日志分类 | 标准 |
| trace_id | string | ❌ | 分布式追踪ID | 上下文 |
| span_id | string | ❌ | 当前span ID | 上下文 |
| parent_span_id | string | ❌ | 父span ID | 上下文 |
| user_id | string | ❌ | 用户ID | 上下文 |
| session_id | string | ❌ | 会话ID | 上下文 |
| request_id | string | ❌ | 请求ID | 上下文 |
| correlation_id | string | ❌ | 关联ID | 上下文 |
| module | string | ❌ | 模块名称 | 上下文 |
| function | string | ❌ | 函数名称 | 上下文 |
| line | integer | ❌ | 代码行号 | 上下文 |
| response_time | number | ❌ | 响应时间 | 扩展 |
| status_code | integer | ❌ | HTTP状态码 | 扩展 |
| error_code | string | ❌ | 错误码 | 扩展 |
| error_type | string | ❌ | 错误类型 | 扩展 |
| error_message | string | ❌ | 错误消息 | 扩展 |
| stack_trace | string | ❌ | 堆栈跟踪 | 扩展 |
| host | string | ❌ | 主机名 | 扩展 |
| service | string | ❌ | 服务名称 | 扩展 |
| version | string | ❌ | 服务版本 | 扩展 |
| environment | string | ❌ | 环境名称 | 扩展 |

### 9.2 日志级别定义

| 级别 | 数值 | 描述 | 用途 |
|------|------|------|------|
| DEBUG | 10 | 调试信息 | 开发和调试 |
| INFO | 20 | 一般信息 | 正常运行信息 |
| WARNING | 30 | 警告信息 | 潜在问题 |
| ERROR | 40 | 错误信息 | 错误和异常 |
| CRITICAL | 50 | 严重错误 | 系统故障 |

### 9.3 脱敏算法实现

#### SHA-256哈希实现
```python
import hashlib

def hash_sensitive(value: str) -> str:
    """使用SHA-256哈希脱敏"""
    return hashlib.sha256(value.encode()).hexdigest()[:16]
```

#### 部分脱敏实现
```python
def mask_partial(value: str, visible_chars: int = 4) -> str:
    """部分脱敏"""
    if len(value) <= visible_chars:
        return "*" * len(value)
    return value[:visible_chars] + "*" * (len(value) - visible_chars)
```

### 9.4 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 日志写入延迟 | <10ms | 单条日志写入时间 |
| 日志吞吐量 | >10000条/秒 | 系统日志处理能力 |
| 压缩比 | >10:1 | Gzip压缩效果 |
| 磁盘占用 | <1GB/天 | 日志存储空间 |
| CPU占用 | <5% | 日志处理CPU影响 |
| 内存占用 | <100MB | 日志处理内存影响 |

## 10. 版本历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v1.0 | 2026-07-03 | AI Agent | 初始版本，完成基础设计 |

## 11. 参考文档

- [RFC 3339 - Date and Time on the Internet](https://tools.ietf.org/html/rfc3339)
- [ISO 8601 - Date and time format](https://www.iso.org/iso-8601-date-and-time-format.html)
- [OpenTelemetry Logging Specification](https://opentelemetry.io/docs/reference/specification/logs/)
- [ELK Stack Logging Best Practices](https://www.elastic.co/guide/en/elastic-stack/current/logging-best-practices.html)
