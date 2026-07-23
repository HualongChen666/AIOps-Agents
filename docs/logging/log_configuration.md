# 日志配置文档

## 概述

本文档提供AIOps Agent系统的日志配置指南，包括日志级别配置、日志输出配置、日志上下文配置等。

## 基础配置

### 初始化结构化日志

```python
from aiops_core.structured_logging import StructuredLogger

# 创建结构化日志器
logger = StructuredLogger(
    name="my_app",
    level="INFO",
    output_format="json",
    output_file="logs/app.log"
)
```

### 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | string | `"app"` | 日志器名称 |
| `level` | string | `"INFO"` | 日志级别 |
| `output_format` | string | `"json"` | 输出格式（json/text） |
| `output_file` | string | `None` | 输出文件路径 |
| `enable_console` | bool | `True` | 是否输出到控制台 |
| `enable_context` | bool | `True` | 是否启用上下文注入 |

## 日志级别配置

### 全局日志级别

```python
from aiops_core.logging.level import LogLevelManager, LogLevel

# 获取日志级别管理器
manager = LogLevelManager()

# 设置默认日志级别
manager.set_default_level(LogLevel.DEBUG)

# 设置模块特定日志级别
manager.set_module_level("noisy_module", LogLevel.WARNING)
```

### 动态调整日志级别

```python
from aiops_core.logging.level import LogLevelManager, LogLevel

manager = LogLevelManager()

# 运行时动态调整
manager.set_default_level(LogLevel.ERROR)

# 查看当前级别
current_level = manager.get_effective_level()
print(f"Current level: {current_level.to_string()}")
```

### 配置文件配置

```json
{
  "default_level": "INFO",
  "module_levels": {
    "database": "WARNING",
    "api": "DEBUG",
    "cache": "ERROR"
  }
}
```

加载配置文件：

```python
from aiops_core.logging.level import LogLevelManager

manager = LogLevelManager()
manager.load_config_from_file("config/log_levels.json")
```

## 日志输出配置

### 文件输出

```python
from aiops_core.structured_logging import StructuredLogger

logger = StructuredLogger(
    name="my_app",
    output_file="logs/app.log",
    rotation="10 MB",
    retention="30 days"
)
```

### 多文件输出

```python
from aiops_core.logging.level import FileRouter, LogLevel

router = FileRouter()
router.set_level_file(LogLevel.ERROR, "logs/error.log")
router.set_level_file(LogLevel.CRITICAL, "logs/critical.log")
router.set_default_file("logs/app.log")

# 使用路由器
logger = StructuredLogger(router=router)
```

### 控制台输出

```python
from aiops_core.structured_logging import StructuredLogger

logger = StructuredLogger(
    name="my_app",
    enable_console=True,
    console_format="text"
)
```

### 系统输出

```python
from aiops_core.logging.level import SystemRouter

router = SystemRouter()
router.add_system_route("elk", LogLevel.ERROR, True)
router.add_system_route("syslog", LogLevel.CRITICAL, True)

logger = StructuredLogger(router=router)
```

## 日志上下文配置

### 启用上下文追踪

```python
from aiops_core.logging.context import LoggingContextManager

# 获取上下文管理器
manager = LoggingContextManager()

# 启用上下文注入
logger = StructuredLogger(enable_context=True)
```

### 设置用户上下文

```python
from aiops_core.logging.context import set_user_context

# 设置用户信息
set_user_context(user_id="user-123", session_id="session-456")

# 日志会自动包含用户上下文
logger.info("User action performed")
```

### 设置请求上下文

```python
from aiops_core.logging.context import set_request_context

# 设置请求信息
set_request_context(
    request_id="req-789",
    correlation_id="corr-012",
    trace_id="trace-abc"
)
```

### 分布式追踪

```python
from aiops_core.logging.context import LoggingContextManager

manager = LoggingContextManager()

# 开始追踪
manager.start_trace()

# 创建子跨度
manager.start_span("operation_name")

# 结束跨度
manager.end_span()

# 结束追踪
manager.end_trace()
```

## 日志过滤配置

### 模块过滤

```python
from aiops_core.logging.level import ModuleFilter

# 只记录特定模块的日志
filter = ModuleFilter(include_modules={"api", "auth"})

# 排除特定模块
filter = ModuleFilter(exclude_modules={"debug", "test"})
```

### 级别过滤

```python
from aiops_core.logging.level import LevelFilter, LogLevel

# 只记录WARNING及以上级别的日志
filter = LevelFilter(min_level=LogLevel.WARNING)

# 只记录ERROR和CRITICAL级别的日志
filter = LevelFilter(allowed_levels={LogLevel.ERROR, LogLevel.CRITICAL})
```

### 关键词过滤

```python
from aiops_core.logging.level import KeywordFilter

# 只记录包含特定关键词的日志
filter = KeywordFilter(include_keywords={"error", "exception"})

# 排除包含特定关键词的日志
filter = KeywordFilter(exclude_keywords={"debug", "trace"})
```

### 组合过滤

```python
from aiops_core.logging.level import CompositeFilter, ModuleFilter, LevelFilter

# 组合多个过滤器
composite = CompositeFilter(
    filters=[
        ModuleFilter(include_modules={"api"}),
        LevelFilter(min_level=LogLevel.WARNING)
    ],
    operator="AND"
)
```

## 日志采样配置

### 比例采样

```python
from aiops_core.logging.level import RatioSampler

# 采样50%的日志
sampler = RatioSampler(sampling_rate=0.5)
```

### 级别采样

```python
from aiops_core.logging.level import LevelBasedSampler, LogLevel

# 不同级别使用不同采样率
sampler = LevelBasedSampler()
sampler.set_level_sampling_rate(LogLevel.DEBUG, 0.1)  # 10%的DEBUG日志
sampler.set_level_sampling_rate(LogLevel.INFO, 0.5)   # 50%的INFO日志
sampler.set_level_sampling_rate(LogLevel.ERROR, 1.0)  # 100%的ERROR日志
```

### 动态采样

```python
from aiops_core.logging.level import DynamicSampler

# 根据系统负载动态调整采样率
def adjust_callback(current_rate):
    # 根据负载调整采样率
    load = get_system_load()
    if load > 0.8:
        return max(0.1, current_rate - 0.2)
    return current_rate

sampler = DynamicSampler(
    initial_rate=1.0,
    rate_adjustment_callback=adjust_callback
)
```

## 日志告警配置

### 阈值告警

```python
from aiops_core.logging.analysis import LogAlertManager, ThresholdAlert, AlertSeverity

manager = LogAlertManager()

# 配置错误率阈值告警
alert = ThresholdAlert(
    name="error_rate_alert",
    metric="error_rate",
    threshold=0.1,
    operator=">",
    severity=AlertSeverity.ERROR
)
manager.add_threshold_alert(alert)
```

### 异常检测

```python
from aiops_core.logging.analysis import LogAlertManager

manager = LogAlertManager()

# 启动异常检测
manager.start_monitoring()

# 停止异常检测
manager.stop_monitoring()
```

### 告警处理器

```python
from aiops_core.logging.analysis import LogAlertManager, AlertHandler, LogAlert

class EmailAlertHandler(AlertHandler):
    def handle_alert(self, alert: LogAlert):
        # 发送邮件告警
        send_email(
            to="admin@example.com",
            subject=f"Alert: {alert.alert_type}",
            message=alert.message
        )

manager = LogAlertManager()
manager.add_alert_handler(EmailAlertHandler())
```

## 环境变量配置

### 环境变量列表

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `LOG_LEVEL` | `INFO` | 默认日志级别 |
| `LOG_FORMAT` | `json` | 日志输出格式 |
| `LOG_FILE` | `None` | 日志文件路径 |
| `LOG_ROTATION` | `10 MB` | 日志轮转大小 |
| `LOG_RETENTION` | `30 days` | 日志保留时间 |
| `ELASTICSEARCH_HOST` | `localhost:9200` | Elasticsearch主机 |
| `KIBANA_HOST` | `localhost:5601` | Kibana主机 |

### 使用环境变量

```python
import os
from aiops_core.structured_logging import StructuredLogger

logger = StructuredLogger(
    level=os.getenv("LOG_LEVEL", "INFO"),
    output_format=os.getenv("LOG_FORMAT", "json"),
    output_file=os.getenv("LOG_FILE")
)
```

## 配置示例

### 开发环境配置

```python
from aiops_core.structured_logging import StructuredLogger
from aiops_core.logging.level import LogLevelManager, LogLevel

# 详细日志级别
manager = LogLevelManager()
manager.set_default_level(LogLevel.DEBUG)

# 控制台输出
logger = StructuredLogger(
    name="dev_app",
    level="DEBUG",
    enable_console=True,
    console_format="text"
)
```

### 生产环境配置

```python
from aiops_core.structured_logging import StructuredLogger
from aiops_core.logging.level import LogLevelManager, LogLevel

# 限制日志级别
manager = LogLevelManager()
manager.set_default_level(LogLevel.INFO)

# 文件输出和系统输出
logger = StructuredLogger(
    name="prod_app",
    level="INFO",
    output_file="logs/app.log",
    rotation="100 MB",
    retention="7 days",
    enable_console=False
)

# 启用告警
from aiops_core.logging.analysis import LogAlertManager
alert_manager = LogAlertManager()
alert_manager.start_monitoring()
```

### 测试环境配置

```python
from aiops_core.structured_logging import StructuredLogger
from aiops_core.logging.level import LogLevelManager, LogLevel

# 警告级别
manager = LogLevelManager()
manager.set_default_level(LogLevel.WARNING)

# 简单输出
logger = StructuredLogger(
    name="test_app",
    level="WARNING",
    enable_console=True
)
```

## 配置验证

### 验证配置

```python
from aiops_core.logging.level import LogLevelManager

manager = LogLevelManager()

# 验证配置
config = manager.get_all_module_levels()
print(f"Module levels: {config}")

# 查看配置历史
history = manager.get_level_history()
print(f"Configuration history: {history}")
```

### 重置配置

```python
from aiops_core.logging.level import LogLevelManager

manager = LogLevelManager()

# 重置到默认配置
manager.reset_to_defaults()
```

## 最佳实践

### 1. 分层配置

根据环境使用不同的配置：

```python
import os

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    log_level = "INFO"
    log_file = "logs/app.log"
else:
    log_level = "DEBUG"
    log_file = None
```

### 2. 模块化配置

为不同模块配置不同的日志级别：

```python
from aiops_core.logging.level import LogLevelManager, LogLevel

manager = LogLevelManager()
manager.set_module_level("database", LogLevel.WARNING)
manager.set_module_level("api", LogLevel.INFO)
manager.set_module_level("cache", LogLevel.DEBUG)
```

### 3. 性能优化

在高流量场景下使用日志采样：

```python
from aiops_core.logging.level import LevelBasedSampler, LogLevel

sampler = LevelBasedSampler()
sampler.set_level_sampling_rate(LogLevel.DEBUG, 0.01)  # 1%的DEBUG日志
sampler.set_level_sampling_rate(LogLevel.INFO, 0.1)   # 10%的INFO日志
```

### 4. 安全考虑

避免在日志中记录敏感信息：

```python
# ❌ 不推荐
logger.info(f"User login: {username}, password: {password}")

# ✅ 推荐
logger.info("User login", context={"user_id": user_id})
```

## 常见问题

### Q: 如何禁用特定模块的日志？

A: 使用模块过滤或设置ERROR级别：

```python
from aiops_core.logging.level import LogLevelManager, LogLevel

manager = LogLevelManager()
manager.set_module_level("noisy_module", LogLevel.ERROR)
```

### Q: 如何实现日志轮转？

A: 配置输出文件时指定轮转参数：

```python
logger = StructuredLogger(
    output_file="logs/app.log",
    rotation="10 MB",
    retention="30 days"
)
```

### Q: 如何在分布式系统中追踪请求？

A: 使用上下文管理器的分布式追踪功能：

```python
from aiops_core.logging.context import LoggingContextManager

manager = LoggingContextManager()
manager.start_trace()
# 自动生成和传播trace_id
```

## 技术评审检查清单

- [x] 包含基础配置指南
- [x] 包含日志级别配置
- [x] 包含日志输出配置
- [x] 包含日志上下文配置
- [x] 包含日志过滤配置
- [x] 包含日志采样配置
- [x] 包含日志告警配置
- [x] 包含环境变量配置
- [x] 包含配置示例
- [x] 包含配置验证方法
- [x] 包含最佳实践指南
- [x] 包含常见问题解答
