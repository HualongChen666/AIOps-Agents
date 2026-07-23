# 日志分析文档

## 概述

本文档提供AIOps Agent系统的日志分析指南，包括日志统计、日志趋势分析、日志模式识别和日志分析最佳实践。

## 日志统计

### 基础统计

#### 日志总量统计

```python
from aiops_core.logging.analysis import LogAnalyzer

analyzer = LogAnalyzer()

# 添加日志数据
logs = [
    {"timestamp": "2026-07-03T10:30:45Z", "level": "INFO", "logger": "api", "message": "Test"},
    {"timestamp": "2026-07-03T10:31:45Z", "level": "ERROR", "logger": "database", "message": "Error"}
]
analyzer.add_logs(logs)

# 计算统计信息
stats = analyzer.calculate_statistics()
print(f"Total logs: {stats.total_logs}")
print(f"Error rate: {stats.error_rate}")
print(f"Unique users: {stats.unique_users}")
print(f"Unique traces: {stats.unique_traces}")
```

#### 按级别统计

```python
stats = analyzer.calculate_statistics()
print("Level distribution:")
for level, count in stats.level_counts.items():
    print(f"  {level}: {count}")
```

#### 按模块统计

```python
stats = analyzer.calculate_statistics()
print("Module distribution:")
for module, count in stats.module_counts.items():
    print(f"  {module}: {count}")
```

### 高级统计

#### 响应时间统计

```python
stats = analyzer.calculate_statistics()
print(f"Average response time: {stats.avg_response_time}")
```

#### 时间范围统计

```python
from datetime import datetime, timedelta

stats = analyzer.calculate_statistics(
    time_range=(datetime.now() - timedelta(hours=1), datetime.now())
)
print(f"Logs in last hour: {stats.total_logs}")
```

## 日志趋势分析

### 时间序列分析

#### 日志量趋势

```python
from datetime import timedelta

analyzer = LogAnalyzer()

# 计算趋势
trends = analyzer.calculate_trends(interval=timedelta(minutes=5))

print("Log volume trend:")
for timestamp, count in trends.time_series:
    print(f"  {timestamp}: {count}")
```

#### 错误率趋势

```python
trends = analyzer.calculate_trends()

print("Error rate trend:")
for timestamp, rate in trends.error_trend:
    print(f"  {timestamp}: {rate:.2%}")
```

#### 增长率分析

```python
trends = analyzer.calculate_trends()
print(f"Growth rate: {trends.growth_rate:.2%}")
print(f"Peak time: {trends.peak_time}")
print(f"Peak value: {trends.peak_value}")
```

### 级别趋势分析

```python
trends = analyzer.calculate_trends()

print("Level trends:")
for level, level_trends in trends.level_trends.items():
    print(f"  {level}:")
    for timestamp, count in level_trends[-5:]:  # 最近5个数据点
        print(f"    {timestamp}: {count}")
```

## 日志模式识别

### 模式检测

#### 基础模式检测

```python
from aiops_core.logging.analysis import LogAnalyzer

analyzer = LogAnalyzer()

# 添加日志数据
logs = [
    {"timestamp": "2026-07-03T10:30:45Z", "level": "ERROR", "message": "Connection failed to server 192.168.1.1"},
    {"timestamp": "2026-07-03T10:31:45Z", "level": "ERROR", "message": "Connection failed to server 192.168.1.2"},
]
analyzer.add_logs(logs)

# 检测模式
patterns = analyzer.detect_patterns(min_occurrences=2)
for pattern in patterns:
    print(f"Pattern: {pattern.pattern}")
    print(f"Count: {pattern.count}")
    print(f"Severity: {pattern.severity}")
    print(f"Examples: {pattern.examples}")
```

#### 错误模式检测

```python
patterns = analyzer.detect_patterns(min_occurrences=5)
error_patterns = [p for p in patterns if p.severity == "error"]

print("Error patterns:")
for pattern in error_patterns:
    print(f"  {pattern.pattern}: {pattern.count}")
```

### 模式分析

#### 模式时间分析

```python
patterns = analyzer.detect_patterns(min_occurrences=3)

for pattern in patterns:
    print(f"Pattern: {pattern.pattern}")
    print(f"First seen: {pattern.first_seen}")
    print(f"Last seen: {pattern.last_seen}")
    print(f"Duration: {pattern.last_seen - pattern.first_seen}")
```

#### 模式示例分析

```python
patterns = analyzer.detect_patterns(min_occurrences=3)

for pattern in patterns:
    print(f"Pattern: {pattern.pattern}")
    print(f"Examples:")
    for example in pattern.examples:
        print(f"  {example}")
```

## 异常检测

### 错误率异常检测

```python
from aiops_core.logging.analysis import LogAnalyzer, LogAlertManager

analyzer = LogAnalyzer()
manager = LogAlertManager(analyzer)

# 添加日志数据...
analyzer.add_logs(logs)

# 检测错误率异常
alert = manager.anomaly_detector.detect_error_rate_anomaly(threshold=2.0)
if alert:
    print(f"Anomaly detected: {alert.message}")
    print(f"Z-score: {alert.metadata['z_score']}")
```

### 日志量异常检测

```python
# 检测日志量异常
alert = manager.anomaly_detector.detect_volume_anomaly(threshold=2.0)
if alert:
    print(f"Volume anomaly: {alert.message}")
    print(f"Current volume: {alert.metadata['current_volume']}")
    print(f"Baseline volume: {alert.metadata['baseline_volume']}")
```

### 模式异常检测

```python
# 检测新的错误模式
alert = manager.anomaly_detector.detect_pattern_anomaly(min_occurrences=10)
if alert:
    print(f"Pattern anomaly: {alert.message}")
    print(f"Pattern: {alert.metadata['pattern']}")
    print(f"Count: {alert.metadata['count']}")
```

## 日志分析工具

### Kibana分析

#### Discover面板

使用Kibana Discover面板进行交互式日志分析：

1. 选择索引模式：`aiops-logs-*`
2. 设置时间范围
3. 添加过滤条件
4. 查看日志详情

#### Visualize面板

创建可视化图表：

- 柱状图：日志量分布
- 饼图：日志级别分布
- 折线图：日志趋势
- 热力图：模块错误分布

#### Dashboard面板

创建综合仪表板：

- 日志总量
- 错误率
- 响应时间
- 模块分布
- 时间趋势

### Grafana分析

#### Prometheus查询

使用Prometheus查询语言进行日志分析：

```promql
# 日志总量
sum(logs_total)

# 错误率
rate(logs_error_total[5m]) / rate(logs_total[5m]) * 100

# 响应时间分位数
histogram_quantile(0.95, logs_response_time)
```

#### Grafana面板

创建Grafana面板：

- 单值面板：关键指标
- 时间序列面板：趋势分析
- 表格面板：详细数据
- 热力图：分布分析

### Python分析

#### 使用Pandas分析

```python
import pandas as pd
from aiops_core.logging.analysis import LogAnalyzer

analyzer = LogAnalyzer()
analyzer.add_logs(logs)

# 转换为DataFrame
stats = analyzer.calculate_statistics()
df = pd.DataFrame([stats.to_dict()])

# 分析
print(df.describe())
```

#### 使用Matplotlib可视化

```python
import matplotlib.pyplot as plt
from aiops_core.logging.analysis import LogAnalyzer
from datetime import timedelta

analyzer = LogAnalyzer()
analyzer.add_logs(logs)

# 获取趋势数据
trends = analyzer.calculate_trends(interval=timedelta(minutes=5))

# 绘制趋势图
timestamps, counts = zip(*trends.time_series)
plt.plot(timestamps, counts)
plt.xlabel('Time')
plt.ylabel('Log Count')
plt.title('Log Volume Trend')
plt.show()
```

## 分析最佳实践

### 1. 定期分析

建立定期的日志分析流程：

```python
import schedule
import time
from aiops_core.logging.analysis import LogAnalyzer

def analyze_logs():
    analyzer = LogAnalyzer()
    analyzer.add_logs(get_recent_logs())
    
    stats = analyzer.calculate_statistics()
    print(f"Error rate: {stats.error_rate}")
    
    trends = analyzer.calculate_trends()
    print(f"Growth rate: {trends.growth_rate}")

# 每小时分析一次
schedule.every().hour.do(analyze_logs)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 2. 设置基线

建立正常操作的基线指标：

```python
from aiops_core.logging.analysis import LogAnalyzer

analyzer = LogAnalyzer()

# 收集正常时期的日志数据
analyzer.add_logs(normal_period_logs)

# 计算基线统计
baseline_stats = analyzer.calculate_statistics()
baseline_trends = analyzer.calculate_trends()

# 保存基线
save_baseline(baseline_stats, baseline_trends)
```

### 3. 异常告警

设置合理的异常检测阈值：

```python
from aiops_core.logging.analysis import LogAlertManager, ThresholdAlert, AlertSeverity

manager = LogAlertManager()

# 配置错误率告警
alert = ThresholdAlert(
    name="error_rate_alert",
    metric="error_rate",
    threshold=0.05,  # 5%错误率
    operator=">",
    severity=AlertSeverity.WARNING
)
manager.add_threshold_alert(alert)

# 启动监控
manager.start_monitoring()
```

### 4. 模式监控

监控关键日志模式：

```python
from aiops_core.logging.analysis import LogAnalyzer

analyzer = LogAnalyzer()

# 定期检测新模式
def monitor_patterns():
    patterns = analyzer.detect_patterns(min_occurrences=5)
    error_patterns = [p for p in patterns if p.severity == "error"]
    
    for pattern in error_patterns:
        if pattern.count > 10:  # 频繁出现的错误模式
            send_alert(f"Frequent error pattern: {pattern.pattern}")
```

### 5. 趋势分析

关注长期趋势而非短期波动：

```python
from aiops_core.logging.analysis import LogAnalyzer
from datetime import timedelta

analyzer = LogAnalyzer()

# 分析24小时趋势
trends = analyzer.calculate_trends(interval=timedelta(hours=1))

# 计算移动平均
def moving_average(data, window=3):
    return [sum(data[i:i+window])/window for i in range(len(data)-window+1)]

counts = [count for _, count in trends.time_series]
ma = moving_average(counts)
print(f"Moving average: {ma}")
```

## 分析场景

### 场景1：性能分析

**目标**: 分析系统性能问题

**步骤**:

1. 收集性能日志
```python
analyzer = LogAnalyzer()
analyzer.add_logs(performance_logs)
```

2. 分析响应时间
```python
stats = analyzer.calculate_statistics()
print(f"Average response time: {stats.avg_response_time}")
```

3. 识别慢请求
```python
slow_requests = [log for log in analyzer._log_buffer 
                 if log.get("context", {}).get("response_time", 0) > 1.0]
print(f"Slow requests: {len(slow_requests)}")
```

4. 分析趋势
```python
trends = analyzer.calculate_trends()
print(f"Growth rate: {trends.growth_rate}")
```

### 场景2：错误分析

**目标**: 分析错误模式和频率

**步骤**:

1. 收集错误日志
```python
error_logs = [log for log in all_logs if log.get("level") in ("ERROR", "CRITICAL")]
analyzer.add_logs(error_logs)
```

2. 检测错误模式
```python
patterns = analyzer.detect_patterns(min_occurrences=3)
error_patterns = [p for p in patterns if p.severity == "error"]
```

3. 分析错误分布
```python
stats = analyzer.calculate_statistics()
print("Error distribution by module:")
for module, count in stats.module_counts.items():
    print(f"  {module}: {count}")
```

4. 识别高频错误
```python
frequent_errors = sorted(error_patterns, key=lambda p: p.count, reverse=True)
for error in frequent_errors[:5]:
    print(f"{error.pattern}: {error.count}")
```

### 场景3：容量规划

**目标**: 基于日志数据规划系统容量

**步骤**:

1. 收集历史日志数据
```python
analyzer = LogAnalyzer()
analyzer.add_logs(historical_logs)
```

2. 分析增长趋势
```python
trends = analyzer.calculate_trends(interval=timedelta(days=1))
print(f"Daily growth rate: {trends.growth_rate}")
```

3. 预测未来需求
```python
current_volume = stats.total_logs
growth_rate = trends.growth_rate

# 预测30天后的日志量
predicted_volume = current_volume * (1 + growth_rate) ** 30
print(f"Predicted volume in 30 days: {predicted_volume}")
```

4. 规划存储容量
```python
avg_log_size = 1.5  # KB per log
required_storage = predicted_volume * avg_log_size / 1024  # GB
print(f"Required storage: {required_storage:.2f} GB")
```

## 分析报告

### 生成日报

```python
from aiops_core.logging.analysis import LogAnalyzer
from datetime import datetime, timedelta

def generate_daily_report():
    analyzer = LogAnalyzer()
    
    # 收集当日日志
    today = datetime.now().date()
    logs = get_logs_for_date(today)
    analyzer.add_logs(logs)
    
    # 计算统计信息
    stats = analyzer.calculate_statistics()
    trends = analyzer.calculate_trends(interval=timedelta(hours=1))
    patterns = analyzer.detect_patterns(min_occurrences=5)
    
    # 生成报告
    report = {
        "date": today.isoformat(),
        "total_logs": stats.total_logs,
        "error_rate": stats.error_rate,
        "avg_response_time": stats.avg_response_time,
        "growth_rate": trends.growth_rate,
        "top_errors": [
            {"pattern": p.pattern, "count": p.count}
            for p in patterns if p.severity == "error"
        ][:10]
    }
    
    return report
```

### 生成周报

```python
def generate_weekly_report():
    analyzer = LogAnalyzer()
    
    # 收集本周日志
    week_start = datetime.now() - timedelta(days=7)
    logs = get_logs_since(week_start)
    analyzer.add_logs(logs)
    
    # 计算统计信息
    stats = analyzer.calculate_statistics()
    trends = analyzer.calculate_trends(interval=timedelta(days=1))
    
    # 生成报告
    report = {
        "week_start": week_start.isoformat(),
        "week_end": datetime.now().isoformat(),
        "total_logs": stats.total_logs,
        "error_rate": stats.error_rate,
        "daily_growth": trends.growth_rate,
        "peak_time": trends.peak_time.isoformat() if trends.peak_time else None,
        "peak_value": trends.peak_value
    }
    
    return report
```

## 常见问题

### Q: 如何处理大量日志数据？

A: 使用日志采样和过滤：

```python
from aiops_core.logging.level import LevelBasedSampler, LogLevel

sampler = LevelBasedSampler()
sampler.set_level_sampling_rate(LogLevel.DEBUG, 0.01)  # 只保留1%的DEBUG日志
```

### Q: 如何识别性能瓶颈？

A: 分析响应时间和慢请求：

```python
slow_logs = [log for log in analyzer._log_buffer 
             if log.get("context", {}).get("response_time", 0) > 1.0]
```

### Q: 如何设置合理的告警阈值？

A: 基于历史数据设置阈值：

```python
# 使用历史数据计算基线
baseline_stats = calculate_baseline_stats()
threshold = baseline_stats.error_rate * 2  # 阈值为基线的2倍
```

### Q: 如何减少误报？

A: 调整异常检测参数：

```python
alert = manager.anomaly_detector.detect_error_rate_anomaly(threshold=3.0)
# 提高阈值以减少误报
```

## 技术评审检查清单

- [x] 包含日志统计指南
- [x] 包含日志趋势分析
- [x] 包含日志模式识别
- [x] 包含异常检测方法
- [x] 包含日志分析工具
- [x] 包含分析最佳实践
- [x] 包含分析场景示例
- [x] 包含分析报告生成
- [x] 包含常见问题解答
