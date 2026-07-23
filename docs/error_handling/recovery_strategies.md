# 错误恢复策略矩阵

## 1. 概述

本文档定义了AIOps Agent系统中各类异常的恢复策略，包括重试、降级、熔断、回滚等策略的详细配置。

## 2. 恢复策略类型

### 2.1 重试策略 (Retry)

**描述**: 在操作失败时自动重试，适用于临时性故障。

**适用场景**:
- 网络抖动
- 临时服务不可用
- 数据库连接超时
- 外部API限流

**配置参数**:
- `max_attempts`: 最大重试次数
- `base_delay`: 基础延迟（秒）
- `max_delay`: 最大延迟（秒）
- `multiplier`: 退避乘数
- `jitter`: 是否添加随机抖动

### 2.2 降级策略 (Fallback)

**描述**: 当主服务不可用时，切换到备用方案。

**适用场景**:
- 服务完全不可用
- 性能严重下降
- 依赖服务故障

**降级方案**:
- 使用缓存数据
- 返回默认值
- 简化功能
- 只读模式

### 2.3 熔断策略 (Circuit Breaker)

**描述**: 当服务连续失败达到阈值时，暂时停止调用，避免雪崩效应。

**适用场景**:
- 下游服务不稳定
- 依赖服务响应慢
- 防止级联故障

**状态转换**:
- 关闭 (CLOSED): 正常工作
- 打开 (OPEN): 拒绝请求
- 半开 (HALF_OPEN): 尝试恢复

### 2.4 回滚策略 (Rollback)

**描述**: 当操作失败时，回滚到之前的状态。

**适用场景**:
- 数据库事务失败
- 状态更新失败
- 批量操作部分失败

### 2.5 补偿策略 (Compensation)

**描述**: 在分布式事务中，通过执行补偿操作来撤销已完成的操作。

**适用场景**:
- Saga模式
- 分布式事务
- 跨服务操作

## 3. 异常类型与恢复策略映射

### 3.1 业务异常

| 异常类型 | 推荐策略 | 重试次数 | 退避策略 | 降级方案 | 熔断阈值 | 说明 |
|---------|---------|---------|---------|---------|---------|------|
| ValidationException | 不重试 | 0 | - | 返回详细错误信息 | - | 输入验证失败，无需重试 |
| ResourceNotFoundException | 不重试 | 0 | - | 返回404 | - | 资源不存在，重试无意义 |
| BusinessLogicException | 不重试 | 0 | - | 返回错误信息 | - | 业务逻辑错误，需人工介入 |
| StateInvalidException | 不重试 | 0 | - | 返回错误信息 | - | 状态错误，需修正状态 |

### 3.2 系统异常

| 异常类型 | 推荐策略 | 重试次数 | 退避策略 | 降级方案 | 熔断阈值 | 说明 |
|---------|---------|---------|---------|---------|---------|------|
| DatabaseException | 重试+降级 | 3 | 指数退避 | 使用缓存/只读模式 | 5次失败 | 数据库错误，可重试 |
| NetworkException | 重试+熔断 | 5 | 指数退避 | 使用本地缓存 | 10次失败 | 网络错误，可重试 |
| CacheException | 降级 | 0 | - | 直接查询数据库 | - | 缓存错误，降级到数据库 |
| ConfigurationException | 不重试 | 0 | - | 使用默认配置 | - | 配置错误，需修正配置 |
| ResourceException | 降级 | 0 | - | 限流/排队 | - | 资源不足，需限流 |

### 3.3 安全异常

| 异常类型 | 推荐策略 | 重试次数 | 退避策略 | 降级方案 | 熔断阈值 | 说明 |
|---------|---------|---------|---------|---------|---------|------|
| AuthenticationException | 不重试 | 0 | - | 返回401 | - | 认证失败，需重新认证 |
| AuthorizationException | 不重试 | 0 | - | 返回403 | - | 授权失败，需检查权限 |
| PermissionDeniedException | 不重试 | 0 | - | 返回403 | - | 权限拒绝，需申请权限 |

### 3.4 第三方异常

| 异常类型 | 推荐策略 | 重试次数 | 退避策略 | 降级方案 | 熔断阈值 | 说明 |
|---------|---------|---------|---------|---------|---------|------|
| ExternalServiceException | 重试+降级+熔断 | 3 | 指数退避 | 使用本地数据 | 5次失败 | 外部服务错误，可重试 |
| AIModelException | 重试+降级 | 2 | 固定延迟 | 使用备用模型 | 3次失败 | AI模型错误，可重试 |
| IntegrationException | 重试+熔断 | 3 | 指数退避 | 跳过集成 | 5次失败 | 集成错误，可重试 |

### 3.5 严重异常

| 异常类型 | 推荐策略 | 重试次数 | 退避策略 | 降级方案 | 熔断阈值 | 说明 |
|---------|---------|---------|---------|---------|---------|------|
| SystemFatalException | 不重试 | 0 | - | 紧急告警 | - | 系统致命错误，需立即处理 |
| DataCorruptionException | 回滚 | 0 | - | 恢复备份 | - | 数据损坏，需恢复备份 |

## 4. 详细配置

### 4.1 重试策略配置

#### 指数退避配置

```python
EXPONENTIAL_BACKOFF_CONFIG = {
    "name": "exponential_backoff",
    "max_attempts": 3,
    "base_delay": 1.0,      # 基础延迟（秒）
    "max_delay": 60.0,      # 最大延迟（秒）
    "multiplier": 2.0,      # 退避乘数
    "jitter": True,         # 添加随机抖动
    "retryable_exceptions": [
        "NetworkException",
        "DatabaseException",
        "ExternalServiceException",
    ],
}
```

**延迟计算**: `delay = min(base_delay * (multiplier ** (attempt - 1)), max_delay)`

**示例**:
- 第1次重试: 1.0秒
- 第2次重试: 2.0秒
- 第3次重试: 4.0秒

#### 固定延迟配置

```python
FIXED_DELAY_CONFIG = {
    "name": "fixed_delay",
    "max_attempts": 3,
    "delay": 2.0,           # 固定延迟（秒）
    "jitter": False,
    "retryable_exceptions": [
        "AIModelException",
    ],
}
```

#### 线性退避配置

```python
LINEAR_BACKOFF_CONFIG = {
    "name": "linear_backoff",
    "max_attempts": 5,
    "initial_delay": 1.0,   # 初始延迟（秒）
    "increment": 1.0,       # 每次增加（秒）
    "max_delay": 30.0,      # 最大延迟（秒）
    "jitter": True,
    "retryable_exceptions": [
        "NetworkException",
    ],
}
```

**延迟计算**: `delay = min(initial_delay + (increment * (attempt - 1)), max_delay)`

**示例**:
- 第1次重试: 1.0秒
- 第2次重试: 2.0秒
- 第3次重试: 3.0秒
- 第4次重试: 4.0秒
- 第5次重试: 5.0秒

### 4.2 断路器配置

```python
CIRCUIT_BREAKER_CONFIG = {
    "name": "default",
    "failure_threshold": 5,      # 失败阈值
    "recovery_timeout": 60,      # 恢复超时（秒）
    "half_open_max_calls": 3,    # 半开状态最大调用数
    "success_threshold": 2,      # 成功阈值（半开→关闭）
    "expected_exception": Exception,
}
```

**状态转换规则**:
- **CLOSED → OPEN**: 失败次数达到 `failure_threshold`
- **OPEN → HALF_OPEN**: 经过 `recovery_timeout` 秒后
- **HALF_OPEN → CLOSED**: 成功次数达到 `success_threshold`
- **HALF_OPEN → OPEN**: 失败次数达到 `half_open_max_calls`

### 4.3 降级策略配置

```python
FALLBACK_CONFIG = {
    "database": {
        "strategy": "cache",
        "cache_ttl": 300,  # 缓存有效期（秒）
        "fallback_to_readonly": True,
    },
    "external_service": {
        "strategy": "local_data",
        "data_source": "local_cache",
        "max_staleness": 3600,  # 最大陈旧时间（秒）
    },
    "ai_model": {
        "strategy": "backup_model",
        "backup_models": ["gpt-3.5-turbo", "claude-instant"],
        "quality_threshold": 0.7,
    },
}
```

### 4.4 回滚策略配置

```python
ROLLBACK_CONFIG = {
    "database_transaction": {
        "auto_rollback": True,
        "savepoint_interval": 100,  # 每100条记录创建保存点
    },
    "state_update": {
        "auto_rollback": True,
        "backup_state": True,
    },
    "batch_operation": {
        "auto_rollback": True,
        "partial_commit": False,  # 不允许部分提交
    },
}
```

## 5. 策略选择决策树

```
┌─────────────┐
│  发生异常    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 是否可重试?  │
└──────┬──────┘
       │
   ┌───┴───┐
   │       │
  否       是
   │       │
   ▼       ▼
┌──────┐ ┌──────────┐
│不重试 │ │重试次数>0?│
└───┬──┘ └────┬─────┘
    │        │
    │    ┌───┴───┐
    │    │       │
    │   否       是
    │    │       │
    │    ▼       ▼
    │ ┌──────┐ ┌──────────┐
    │ │直接报错│ │执行重试  │
    │ └───┬──┘ └────┬─────┘
    │     │        │
    │     │        ▼
    │     │ ┌────────────┐
    │     │ │重试成功?   │
    │     │ └─────┬──────┘
    │     │       │
    │     │   ┌───┴───┐
    │     │   │       │
    │     │  是       否
    │     │   │       │
    │     │   ▼       ▼
    │     │ ┌──┐ ┌──────────┐
    │     │ │返回│ │是否可降级?│
    │     │ └──┘ └────┬─────┘
    │     │         │
    │     │     ┌───┴───┐
    │     │     │       │
    │     │    否       是
    │     │     │       │
    │     │     ▼       ▼
    │     │ ┌──────┐ ┌──────────┐
    │     │ │直接报错│ │执行降级  │
    │     │ └───┬──┘ └────┬─────┘
    │     │     │        │
    │     │     │        ▼
    │     │     │ ┌────────────┐
    │     │     │ │降级成功?   │
    │     │     │ └─────┬──────┘
    │     │     │       │
    │     │     │   ┌───┴───┐
    │     │     │   │       │
    │     │     │  是       否
    │     │     │   │       │
    │     │     │   ▼       ▼
    │     │     │ ┌──┐ ┌──────────┐
    │     │     │ │返回│ │触发熔断? │
    │     │     │ └──┘ └────┬─────┘
    │     │     │        │
    │     │     │    ┌───┴───┐
    │     │     │    │       │
    │     │     │   否       是
    │     │     │    │       │
    │     │     │    ▼       ▼
    │     │     │ ┌──────┐ ┌──────────┐
    │     │     │ │直接报错│ │打开断路器│
    │     │     │ └───┬──┘ └────┬─────┘
    │     │     │     │        │
    │     │     │     └───┬────┘
    │     │     │         │
    │     │     │         ▼
    │     │     │ ┌────────────┐
    │     │     │ │返回降级结果│
    │     │     │ └────────────┘
    │     │     │
    │     │     └─────────────┘
    │     │
    │     └─────────────────┘
    │
    └─────────────────────┘
```

## 6. 实现示例

### 6.1 重试装饰器示例

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    retry=(lambda e: isinstance(e, (NetworkException, DatabaseException))),
)
async def call_external_service():
    """调用外部服务，失败时自动重试"""
    pass
```

### 6.2 断路器示例

```python
from pybreaker import CircuitBreaker

circuit_breaker = CircuitBreaker(
    fail_max=5,
    timeout_duration=60,
)

@circuit_breaker
async def call_database():
    """调用数据库，使用断路器保护"""
    pass
```

### 6.3 降级策略示例

```python
async def get_user_data(user_id: int):
    """获取用户数据，支持降级"""
    try:
        return await database.get_user(user_id)
    except DatabaseException:
        # 降级到缓存
        cached_data = await cache.get(f"user:{user_id}")
        if cached_data:
            return cached_data
        # 降级到默认值
        return {"id": user_id, "name": "Unknown"}
```

## 7. 监控和告警

### 7.1 监控指标

- **重试成功率**: 重试操作的成功率
- **重试次数分布**: 各类异常的重试次数分布
- **降级触发次数**: 降级策略的触发次数
- **断路器状态**: 断路器的状态变化
- **回滚次数**: 回滚操作的次数

### 7.2 告警规则

| 指标 | 阈值 | 级别 | 通知渠道 |
|------|------|------|---------|
| 重试成功率 < 50% | 1小时 | WARNING | 邮件 |
| 降级触发次数 > 100 | 1小时 | ERROR | 邮件+Slack |
| 断路器打开 | 立即 | CRITICAL | 邮件+Slack+短信 |
| 回滚次数 > 10 | 1小时 | ERROR | 邮件+Slack |

## 8. 最佳实践

### 8.1 重试策略

- 只对临时性错误进行重试
- 设置合理的重试次数和延迟
- 使用指数退避避免雪崩
- 添加随机抖动避免惊群效应

### 8.2 降级策略

- 降级方案应该简单可靠
- 降级数据应该有明确的陈旧度
- 降级应该有明确的触发条件
- 降级后应该有恢复机制

### 8.3 熔断策略

- 熔断阈值应该根据实际情况调整
- 熔断后应该有自动恢复机制
- 熔断状态应该可监控
- 熔断应该有手动干预能力

### 8.4 回滚策略

- 回滚应该是原子的
- 回滚应该有日志记录
- 回滚应该有补偿机制
- 回滚应该可测试

## 9. 附录

### 9.1 术语表

| 术语 | 定义 |
|------|------|
| 重试 (Retry) | 在操作失败时自动重新执行 |
| 降级 (Fallback) | 切换到备用方案 |
| 熔断 (Circuit Breaker) | 暂停调用失败的服务 |
| 回滚 (Rollback) | 恢复到之前的状态 |
| 补偿 (Compensation) | 执行补偿操作 |
| 指数退避 (Exponential Backoff) | 每次重试延迟按指数增长 |
| 随机抖动 (Jitter) | 在延迟中添加随机性 |

### 9.2 参考资料

- [Retry Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/retry)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Fallback Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker)
- [Saga Pattern](https://microservices.io/patterns/data/saga.html)

### 9.3 版本历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|---------|
| 1.0 | 2024-01-01 | AIOps Team | 初始版本 |
