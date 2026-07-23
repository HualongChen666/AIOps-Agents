# 日志FAQ文档

## 概述

本文档提供AIOps Agent系统日志相关的常见问题和解决方案。

## 基础问题

### Q: 如何开始使用结构化日志？

A: 按照以下步骤开始使用：

```python
from aiops_core.structured_logging import StructuredLogger

# 创建日志器
logger = StructuredLogger(
    name="my_app",
    level="INFO",
    output_format="json"
)

# 记录日志
logger.info("Application started")
```

### Q: 日志文件存储在哪里？

A: 默认情况下，日志文件存储在项目根目录的 `logs/` 文件夹中。可以通过配置自定义路径：

```python
logger = StructuredLogger(output_file="/path/to/custom/logs/app.log")
```

### Q: 如何查看实时日志？

A: 使用以下方法查看实时日志：

```bash
# Linux/Mac
tail -f logs/app.log

# Windows
Get-Content logs/app.log -Wait
```

或者使用Kibana的实时监控功能。

### Q: 如何禁用日志输出？

A: 设置日志级别为CRITICAL或更高：

```python
from aiops_core.logging.level import LogLevelManager, LogLevel

manager = LogLevelManager()
manager.set_default_level(LogLevel.CRITICAL)
```

## 配置问题

### Q: 如何修改日志级别？

A: 有多种方法修改日志级别：

**方法1: 代码配置**
```python
from aiops_core.logging.level import LogLevelManager, LogLevel

manager = LogLevelManager()
manager.set_default_level(LogLevel.DEBUG)
```

**方法2: 配置文件**
```json
{
  "default_level": "DEBUG",
  "module_levels": {
    "database": "WARNING"
  }
}
```

**方法3: 环境变量**
```bash
export LOG_LEVEL=DEBUG
```

### Q: 如何为不同模块设置不同的日志级别？

A: 使用模块级别配置：

```python
from aiops_core.logging.level import LogLevelManager, LogLevel

manager = LogLevelManager()
manager.set_module_level("database", LogLevel.WARNING)
manager.set_module_level("api", LogLevel.DEBUG)
```

### Q: 如何配置日志轮转？

A: 在创建日志器时指定轮转参数：

```python
logger = StructuredLogger(
    output_file="logs/app.log",
    rotation="10 MB",      # 按大小轮转
    retention="30 days"    # 保留时间
)
```

### Q: 如何将日志输出到多个目标？

A: 使用日志路由策略：

```python
from aiops_core.logging.level import FileRouter, LogLevel

router = FileRouter()
router.set_level_file(LogLevel.ERROR, "logs/error.log")
router.set_default_file("logs/app.log")

logger = StructuredLogger(router=router)
```

## 上下文问题

### Q: 如何在日志中包含用户信息？

A: 使用上下文管理器设置用户上下文：

```python
from aiops_core.logging.context import set_user_context

set_user_context(user_id="user-123", session_id="session-456")
logger.info("User action performed")
```

### Q: 如何追踪分布式请求？

A: 使用分布式追踪功能：

```python
from aiops_core.logging.context import LoggingContextManager

manager = LoggingContextManager()
manager.start_trace()

# 所有日志会自动包含trace_id和span_id
logger.info("Processing request")
```

### Q: 如何传递自定义上下文？

A: 使用自定义上下文字段：

```python
from aiops_core.logging.context import LoggingContextManager

manager = LoggingContextManager()
manager.set_custom_context("request_id", "req-789")
manager.set_custom_context("correlation_id", "corr-012")
```

### Q: 上下文信息会自动注入到所有日志吗？

A: 是的，如果启用了上下文注入，上下文信息会自动注入到所有日志：

```python
logger = StructuredLogger(enable_context=True)
```

## 性能问题

### Q: 日志会影响系统性能吗？

A: 日志会对系统性能产生一定影响，但可以通过以下方式优化：

1. 使用合适的日志级别
2. 启用日志采样
3. 使用异步日志写入
4. 避免在高频循环中记录详细日志

### Q: 如何在高流量场景下减少日志量？

A: 使用日志采样策略：

```python
from aiops_core.logging.level import LevelBasedSampler, LogLevel

sampler = LevelBasedSampler()
sampler.set_level_sampling_rate(LogLevel.DEBUG, 0.01)  # 1%的DEBUG日志
sampler.set_level_sampling_rate(LogLevel.INFO, 0.1)   # 10%的INFO日志
```

### Q: 如何优化日志写入性能？

A: 采用以下优化措施：

1. 使用异步日志写入
2. 批量写入日志
3. 使用高效的日志格式（如JSON）
4. 避免在热路径中记录详细日志

### Q: 日志文件过大怎么办？

A: 配置日志轮转和清理策略：

```python
logger = StructuredLogger(
    output_file="logs/app.log",
    rotation="100 MB",
    retention="7 days"
)
```

## 错误问题

### Q: 如何记录异常信息？

A: 使用logger.exception()记录完整的异常信息：

```python
try:
    operation()
except Exception as e:
    logger.exception("Operation failed")
```

### Q: 如何排查日志记录失败的问题？

A: 检查以下方面：

1. 日志文件权限
2. 磁盘空间
3. 日志配置是否正确
4. 日志器是否正确初始化

### Q: 为什么某些日志没有记录？

A: 可能的原因包括：

1. 日志级别设置过高
2. 日志过滤器过滤掉了这些日志
3. 日志采样策略丢弃了这些日志
4. 日志路由配置不正确

### Q: 如何调试日志配置问题？

A: 使用以下方法调试：

```python
from aiops_core.logging.level import LogLevelManager

manager = LogLevelManager()
print(f"Default level: {manager.get_default_level()}")
print(f"Module levels: {manager.get_all_module_levels()}")
print(f"Config history: {manager.get_level_history()}")
```

## 查询问题

### Q: 如何查询特定时间范围的日志？

A: 使用时间范围查询：

```kql
@timestamp: [now-1h TO now]
```

### Q: 如何查询特定用户的日志？

A: 使用用户ID查询：

```kql
context.user_id: "user-123"
```

### Q: 如何查询特定trace的所有日志？

A: 使用trace_id查询：

```kql
context.trace_id: "abc123def456"
```

### Q: 如何查询包含特定关键词的日志？

A: 使用通配符查询：

```kql
message: "*error*"
```

## 分析问题

### Q: 如何计算错误率？

A: 使用日志分析器：

```python
from aiops_core.logging.analysis import LogAnalyzer

analyzer = LogAnalyzer()
analyzer.add_logs(logs)

stats = analyzer.calculate_statistics()
print(f"Error rate: {stats.error_rate}")
```

### Q: 如何识别频繁出现的错误模式？

A: 使用模式检测：

```python
patterns = analyzer.detect_patterns(min_occurrences=5)
error_patterns = [p for p in patterns if p.severity == "error"]

for pattern in error_patterns:
    print(f"{pattern.pattern}: {pattern.count}")
```

### Q: 如何设置告警？

A: 配置阈值告警：

```python
from aiops_core.logging.analysis import LogAlertManager, ThresholdAlert, AlertSeverity

manager = LogAlertManager()
alert = ThresholdAlert(
    name="error_rate_alert",
    metric="error_rate",
    threshold=0.1,
    operator=">",
    severity=AlertSeverity.ERROR
)
manager.add_threshold_alert(alert)
manager.start_monitoring()
```

### Q: 如何减少误报？

A: 调整异常检测参数：

```python
# 提高阈值以减少误报
alert = manager.anomaly_detector.detect_error_rate_anomaly(threshold=3.0)
```

## 安全问题

### Q: 如何避免在日志中记录敏感信息？

A: 使用敏感信息脱敏功能：

```python
from aiops_core.logging.context import LoggingContextManager

manager = LoggingContextManager()
# 敏感信息会自动脱敏
manager.set_custom_context("password", "secret123")
# 日志输出: password: ******
```

### Q: 如何保护日志文件的安全？

A: 采用以下安全措施：

1. 设置适当的文件权限
2. 加密敏感日志
3. 定期清理旧日志
4. 使用安全的日志传输协议

### Q: 如何审计日志访问？

A: 启用日志访问审计：

```python
# 配置日志访问审计
logger = StructuredLogger(
    enable_audit=True,
    audit_log_file="logs/audit.log"
)
```

### Q: 如何确保日志的完整性？

A: 使用日志签名和校验：

```python
# 配置日志签名
logger = StructuredLogger(
    enable_signing=True,
    signing_key="path/to/key.pem"
)
```

## 集成问题

### Q: 如何与Elasticsearch集成？

A: 配置Filebeat或Fluentd将日志发送到Elasticsearch：

```yaml
# filebeat.yml
output.elasticsearch:
  hosts: ["localhost:9200"]
  index: "aiops-logs-%{+yyyy.MM.dd}"
```

### Q: 如何与Kibana集成？

A: 在Kibana中创建索引模式：

```yaml
# filebeat.yml
setup.kibana:
  host: "localhost:5601"
```

### Q: 如何与Grafana集成？

A: 配置Prometheus或Elasticsearch数据源：

```promql
# Grafana查询示例
rate(logs_total[5m])
```

### Q: 如何与告警系统集成？

A: 配置告警处理器：

```python
from aiops_core.logging.analysis import LogAlertManager, AlertHandler

class EmailAlertHandler(AlertHandler):
    def handle_alert(self, alert):
        send_email(alert.message)

manager = LogAlertManager()
manager.add_alert_handler(EmailAlertHandler())
```

## 故障排查

### Q: 日志文件无法创建怎么办？

A: 检查以下方面：

1. 目录是否存在
2. 目录权限是否正确
3. 磁盘空间是否充足
4. 日志配置路径是否正确

### Q: 日志格式不正确怎么办？

A: 检查以下方面：

1. 日志格式配置是否正确
2. 日志器是否正确初始化
3. 日志字段是否符合规范

### Q: 日志时间戳不正确怎么办？

A: 检查系统时区配置：

```python
from datetime import datetime
print(f"System time: {datetime.now()}")
print(f"System timezone: {datetime.now().astimezone().tzinfo}")
```

### Q: 日志丢失怎么办？

A: 检查以下方面：

1. 日志采样策略是否过于激进
2. 日志缓冲区是否已满
3. 日志写入是否失败
4. 磁盘空间是否充足

## 最佳实践

### Q: 应该使用什么日志级别？

A: 按照以下原则选择日志级别：

- DEBUG: 开发调试信息
- INFO: 一般操作信息
- WARNING: 潜在问题
- ERROR: 错误信息
- CRITICAL: 严重错误

### Q: 应该记录哪些信息？

A: 记录以下类型的信息：

1. 关键操作的开始和结束
2. 错误和异常信息
3. 性能指标
4. 审计追踪信息
5. 调试信息（仅在DEBUG级别）

### Q: 如何避免日志过多？

A: 采用以下策略：

1. 使用合适的日志级别
2. 避免循环中的详细日志
3. 使用日志采样
4. 定期清理旧日志

### Q: 如何提高日志的可读性？

A: 采用以下方法：

1. 使用结构化日志格式
2. 包含上下文信息
3. 使用清晰的日志消息
4. 避免冗余信息

## 常见错误

### Q: 为什么会出现"日志器未初始化"错误？

A: 确保在使用日志器之前正确初始化：

```python
# 正确
logger = StructuredLogger(name="my_app")
logger.info("Message")

# 错误
logger.info("Message")  # 未初始化
```

### Q: 为什么会出现"上下文未设置"错误？

A: 确保在使用上下文之前正确设置：

```python
# 正确
from aiops_core.logging.context import set_user_context
set_user_context(user_id="user-123")
logger.info("Message")

# 错误
logger.info("Message")  # 未设置用户上下文
```

### Q: 为什么会出现"权限拒绝"错误？

A: 检查日志文件和目录的权限：

```bash
# Linux/Mac
chmod 755 logs/
chmod 644 logs/*.log

# Windows
icacls logs /grant Users:F
```

### Q: 为什么会出现"磁盘空间不足"错误？

A: 清理旧日志或增加磁盘空间：

```bash
# 清理旧日志
find logs/ -name "*.log" -mtime +30 -delete
```

## 性能优化

### Q: 如何减少日志I/O开销？

A: 采用以下优化措施：

1. 使用异步日志写入
2. 批量写入日志
3. 减少日志详细程度
4. 使用内存缓冲

### Q: 如何优化日志查询性能？

A: 采用以下优化措施：

1. 使用时间范围索引
2. 避免通配符开头查询
3. 使用过滤器而非查询
4. 限制返回字段数量

### Q: 如何减少日志存储空间？

A: 采用以下优化措施：

1. 启用日志压缩
2. 配置日志轮转
3. 使用日志采样
4. 定期清理旧日志

### Q: 如何提高日志分析效率？

A: 采用以下优化措施：

1. 使用预聚合
2. 缓存常用查询
3. 使用增量分析
4. 并行处理

## 监控和维护

### Q: 如何监控日志系统健康状态？

A: 使用以下监控指标：

1. 日志写入速率
2. 日志文件大小
3. 错误率
4. 系统资源使用情况

### Q: 如何维护日志系统？

A: 定期执行以下维护任务：

1. 清理旧日志
2. 检查磁盘空间
3. 验证日志配置
4. 测试告警系统

### Q: 如何备份日志？

A: 使用以下备份策略：

1. 定期备份到远程存储
2. 使用日志聚合系统
3. 配置日志复制
4. 使用版本控制

### Q: 如何迁移日志？

A: 按照以下步骤迁移：

1. 停止日志写入
2. 备份现有日志
3. 配置新日志系统
4. 验证日志写入
5. 清理旧日志

## 技术支持

### Q: 如何获取技术支持？

A: 通过以下方式获取支持：

1. 查看本文档
2. 查看代码注释
3. 查看GitHub Issues
4. 联系技术支持团队

### Q: 如何报告bug？

A: 按照以下步骤报告bug：

1. 复现问题
2. 收集日志信息
3. 记录环境信息
4. 提交bug报告

### Q: 如何请求新功能？

A: 按照以下步骤请求新功能：

1. 描述功能需求
2. 说明使用场景
3. 提供设计建议
4. 提交功能请求

### Q: 如何贡献代码？

A: 按照以下步骤贡献代码：

1. Fork项目仓库
2. 创建功能分支
3. 编写代码和测试
4. 提交Pull Request

## 技术评审检查清单

- [x] 包含基础问题解答
- [x] 包含配置问题解答
- [x] 包含上下文问题解答
- [x] 包含性能问题解答
- [x] 包含错误问题解答
- [x] 包含查询问题解答
- [x] 包含分析问题解答
- [x] 包含安全问题解答
- [x] 包含集成问题解答
- [x] 包含故障排查指南
- [x] 包含最佳实践建议
- [x] 包含常见错误分析
- [x] 包含性能优化建议
- [x] 包含监控维护指南
- [x] 包含技术支持信息
