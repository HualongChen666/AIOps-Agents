# Performance Baseline Database

## 概述

性能基准数据库用于存储历史性能数据，支持性能趋势分析和性能回归检测。该系统基于PostgreSQL实现，包含性能指标、基准线、趋势和回归记录等核心表。

## 数据库表结构

### 1. performance_metrics（性能指标表）

存储每次性能测试的详细指标数据。

**字段说明**:
- `id`: 主键
- `test_id`: 测试ID
- `test_name`: 测试名称
- `test_type`: 测试类型（api, database, ai）
- `component`: 组件名称（API端点、数据库表、AI模型）
- `operation`: 操作名称
- `mean_time_ms`: 平均响应时间（毫秒）
- `min_time_ms`: 最小响应时间（毫秒）
- `max_time_ms`: 最大响应时间（毫秒）
- `p50_time_ms`: P50响应时间（毫秒）
- `p95_time_ms`: P95响应时间（毫秒）
- `p99_time_ms`: P99响应时间（毫秒）
- `std_dev_ms`: 标准差（毫秒）
- `throughput_ops`: 吞吐量（操作/秒）
- `qps`: 每秒查询数
- `error_rate`: 错误率
- `error_count`: 错误数
- `total_requests`: 总请求数
- `cpu_usage`: CPU使用率
- `memory_usage`: 内存使用率
- `disk_io`: 磁盘I/O
- `network_io`: 网络I/O
- `token_usage`: Token使用量（AI特定）
- `cost_usd`: 成本（美元，AI特定）
- `model_name`: 模型名称（AI特定）
- `data_volume`: 数据量（数据库特定）
- `pool_size`: 连接池大小（数据库特定）
- `connection_count`: 连接数（数据库特定）
- `environment`: 环境（dev, staging, prod）
- `git_commit`: Git提交ID
- `git_branch`: Git分支
- `timestamp`: 时间戳
- `metadata`: 元数据（JSON）

**索引**:
- `idx_performance_metrics_test_id`: 测试ID索引
- `idx_performance_metrics_test_type`: 测试类型索引
- `idx_performance_metrics_component`: 组件索引
- `idx_performance_metrics_timestamp`: 时间戳索引
- `idx_performance_metrics_environment`: 环境索引

### 2. performance_baselines（性能基准表）

存储性能基准线和回归阈值配置。

**字段说明**:
- `id`: 主键
- `baseline_id`: 基准ID（唯一）
- `baseline_name`: 基准名称
- `baseline_type`: 基准类型（api, database, ai）
- `component`: 组件名称
- `operation`: 操作名称
- `target_p95_ms`: 目标P95响应时间
- `target_p99_ms`: 目标P99响应时间
- `target_throughput`: 目标吞吐量
- `target_error_rate`: 目标错误率
- `regression_threshold`: 回归阈值（默认10%）
- `critical_threshold`: 严重阈值（默认30%）
- `environment`: 环境
- `effective_from`: 生效开始时间
- `effective_until`: 生效结束时间
- `created_by`: 创建者
- `created_at`: 创建时间
- `is_active`: 是否活跃

**索引**:
- `idx_performance_baselines_baseline_id`: 基准ID索引
- `idx_performance_baselines_component`: 组件索引
- `idx_performance_baselines_environment`: 环境索引
- `idx_performance_baselines_is_active`: 活跃状态索引

### 3. performance_trends（性能趋势表）

存储性能趋势分析数据。

**字段说明**:
- `id`: 主键
- `trend_id`: 趋势ID
- `component`: 组件名称
- `metric_name`: 指标名称（p95_time_ms, throughput, error_rate）
- `timestamp`: 时间戳
- `metric_value`: 指标值
- `trend_direction`: 趋势方向（up, down, stable）
- `trend_magnitude`: 趋势幅度
- `trend_significance`: 趋势显著性（significant, normal）
- `baseline_value`: 基准值
- `deviation_from_baseline`: 与基准的偏差
- `environment`: 环境
- `metadata`: 元数据（JSON）

**索引**:
- `idx_performance_trends_trend_id`: 趋势ID索引
- `idx_performance_trends_component`: 组件索引
- `idx_performance_trends_timestamp`: 时间戳索引
- `idx_performance_trends_environment`: 环境索引

### 4. performance_regressions（性能回归记录表）

存储检测到的性能回归记录。

**字段说明**:
- `id`: 主键
- `regression_id`: 回归ID（唯一）
- `component`: 组件名称
- `operation`: 操作名称
- `baseline_value`: 基准值
- `current_value`: 当前值
- `deviation`: 偏差百分比
- `severity`: 严重程度（warning, critical）
- `detected_at`: 检测时间
- `git_commit`: Git提交ID
- `git_branch`: Git分支
- `status`: 状态（open, acknowledged, resolved）
- `acknowledged_by`: 确认人
- `acknowledged_at`: 确认时间
- `resolved_at`: 解决时间
- `environment`: 环境
- `metadata`: 元数据（JSON）

**索引**:
- `idx_performance_regressions_regression_id`: 回归ID索引
- `idx_performance_regressions_component`: 组件索引
- `idx_performance_regressions_severity`: 严重程度索引
- `idx_performance_regressions_status`: 状态索引
- `idx_performance_regressions_detected_at`: 检测时间索引

## 使用方法

### 1. 性能数据采集

```python
from aiops_core.performance_data_collector import PerformanceDataCollector, collect_performance_test_result

# 方式1: 使用采集器
collector = PerformanceDataCollector()
metric_id = await collector.collect_metric({
    "test_id": "test-001",
    "test_name": "API Health Check",
    "test_type": "api",
    "component": "/health",
    "operation": "GET",
    "mean_time_ms": 50.0,
    "min_time_ms": 45.0,
    "max_time_ms": 60.0,
    "p95_time_ms": 58.0,
    "p99_time_ms": 59.5,
    "std_dev_ms": 5.0,
    "throughput_ops": 1000.0,
    "qps": 1000.0,
    "error_rate": 0.0,
    "error_count": 0,
    "total_requests": 1000,
    "environment": "dev",
    "git_commit": "abc123",
    "git_branch": "main",
})

# 方式2: 使用便捷函数
metric_id = await collect_performance_test_result({
    "test_id": "test-002",
    "test_name": "Database Query",
    "test_type": "database",
    "component": "alerts",
    "operation": "SELECT",
    "mean_time_ms": 100.0,
    "p95_time_ms": 150.0,
    "environment": "dev",
})
```

### 2. 批量采集

```python
metrics_data = [
    {
        "test_id": "test-001",
        "test_type": "api",
        "component": "/health",
        "mean_time_ms": 50.0,
        "p95_time_ms": 58.0,
        "environment": "dev",
    },
    {
        "test_id": "test-002",
        "test_type": "api",
        "component": "/alerts",
        "mean_time_ms": 100.0,
        "p95_time_ms": 120.0,
        "environment": "dev",
    },
]

collector = PerformanceDataCollector()
metric_ids = await collector.collect_batch_metrics(metrics_data)
```

### 3. 查询性能指标

```python
collector = PerformanceDataCollector()

# 查询特定组件的指标
metrics = await collector.query_metrics(
    component="/health",
    environment="dev",
    limit=100
)

# 查询特定时间范围的指标
from datetime import datetime, timedelta
start_time = datetime.now() - timedelta(hours=24)
metrics = await collector.query_metrics(
    start_time=start_time,
    environment="dev",
    limit=100
)

# 获取聚合指标
aggregated = await collector.get_aggregated_metrics(
    component="/health",
    metric_name="p95_time_ms",
    interval="hour",
    hours=24
)
```

### 4. 性能回归检测

```python
from aiops_core.performance_regression_detector import PerformanceRegressionDetector, check_performance_regression

# 方式1: 使用检测器
detector = PerformanceRegressionDetector()
regression = await detector.detect_regression(
    component="/health",
    current_value=150.0,
    metric_name="p95_time_ms",
    environment="dev"
)

if regression:
    print(f"检测到性能回归: {regression}")

# 方式2: 使用便捷函数
regression = await check_performance_regression(
    component="/health",
    current_value=150.0,
    environment="dev"
)

# 批量检测
metrics_data = [
    {"component": "/health", "p95_time_ms": 150.0},
    {"component": "/alerts", "p95_time_ms": 200.0},
]

regressions = await detector.batch_detect_regressions(metrics_data, environment="dev")
```

### 5. 管理性能回归

```python
detector = PerformanceRegressionDetector()

# 获取活跃的回归
active_regressions = await detector.get_active_regressions(
    environment="dev",
    severity="critical"
)

# 确认回归
await detector.acknowledge_regression(
    regression_id="regression-001",
    acknowledged_by="admin"
)

# 解决回归
await detector.resolve_regression(
    regression_id="regression-001"
)
```

### 6. 生成性能报告

```python
from aiops_core.performance_report_generator import PerformanceReportGenerator, generate_performance_report

# 方式1: 使用生成器
generator = PerformanceReportGenerator()

# 生成日报
daily_report = await generator.generate_daily_report(environment="dev")

# 生成周报
weekly_report = await generator.generate_weekly_report(environment="dev")

# 生成月报
monthly_report = await generator.generate_monthly_report(
    environment="dev",
    year=2024,
    month=1
)

# 生成趋势分析
trend_analysis = await generator.generate_trend_analysis(
    component="/health",
    metric_name="p95_time_ms",
    days=30,
    environment="dev"
)

# 方式2: 使用便捷函数
report = await generate_performance_report(
    report_type="daily",
    environment="dev"
)
```

## Grafana集成

### 仪表板配置

已提供Grafana仪表板配置文件：`grafana/dashboards/performance_dashboard.json`

**导入步骤**:
1. 登录Grafana
2. 进入 Dashboards -> Import
3. 上传 `performance_dashboard.json` 文件
4. 配置数据源（Prometheus/VictoriaMetrics）
5. 保存仪表板

### Prometheus指标导出

需要在应用中集成Prometheus指标导出：

```python
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
api_response_time = Histogram(
    'aiops_api_response_time_p95_ms',
    'API response time P95',
    ['endpoint']
)

api_throughput = Counter(
    'aiops_api_throughput_qps',
    'API throughput QPS',
    ['endpoint']
)

db_query_time = Histogram(
    'aiops_db_query_time_p95_ms',
    'Database query time P95',
    ['table']
)

llm_inference_time = Histogram(
    'aiops_llm_inference_time_p95_ms',
    'LLM inference time P95',
    ['model']
)

# 使用指标
api_response_time.labels(endpoint="/health").observe(50.0)
api_throughput.labels(endpoint="/health").inc()
```

## 数据库迁移

使用Alembic创建数据库表：

```bash
# 生成迁移
alembic revision --autogenerate -m "Add performance tables"

# 应用迁移
alembic upgrade head
```

## 性能基准管理

### 创建基准线

```python
from aiops_core.db_engine import AsyncSessionLocal
from aiops_core.models import PerformanceBaseline

async def create_baseline():
    async with AsyncSessionLocal() as session:
        baseline = PerformanceBaseline(
            baseline_id="baseline-health-api",
            baseline_name="Health API Baseline",
            baseline_type="api",
            component="/health",
            operation="GET",
            target_p95_ms=50.0,
            target_p99_ms=60.0,
            target_throughput=1000.0,
            target_error_rate=0.01,
            regression_threshold=0.1,
            critical_threshold=0.3,
            environment="dev",
            created_by="admin",
        )
        session.add(baseline)
        await session.commit()
```

### 更新基准线

```python
async def update_baseline():
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, update
        
        stmt = (
            update(PerformanceBaseline)
            .where(PerformanceBaseline.baseline_id == "baseline-health-api")
            .values(
                target_p95_ms=60.0,  # 更新基准值
                effective_from=datetime.now(),
            )
        )
        await session.execute(stmt)
        await session.commit()
```

## 定期任务

### 自动化性能数据采集

建议设置定时任务自动采集性能数据：

```python
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def collect_daily_metrics():
    """每日采集性能指标"""
    # 运行API性能测试
    # 运行数据库性能测试
    # 运行AI性能测试
    # 采集结果到数据库
    pass

async def detect_daily_regressions():
    """每日检测性能回归"""
    # 查询最新的性能指标
    # 与基准线对比
    # 检测回归
    # 发送告警
    pass

async def generate_daily_report():
    """每日生成性能报告"""
    # 生成日报
    # 发送邮件
    pass

# 配置定时任务
scheduler = AsyncIOScheduler()
scheduler.add_job(collect_daily_metrics, 'cron', hour=2)
scheduler.add_job(detect_daily_regressions, 'cron', hour=3)
scheduler.add_job(generate_daily_report, 'cron', hour=4)
scheduler.start()
```

## 告警配置

### Prometheus告警规则

```yaml
groups:
  - name: performance_regressions
    rules:
      - alert: APIResponseTimeHigh
        expr: aiops_api_response_time_p95_ms > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API response time is high"
          description: "API {{ $labels.endpoint }} response time is {{ $value }}ms"
      
      - alert: DatabaseQuerySlow
        expr: aiops_db_query_time_p95_ms > 500
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database query is slow"
          description: "Database {{ $labels.table }} query time is {{ $value }}ms"
```

## 维护建议

### 数据清理

定期清理历史数据以保持数据库性能：

```sql
-- 清理30天前的性能指标
DELETE FROM performance_metrics 
WHERE timestamp < NOW() - INTERVAL '30 days';

-- 清理已解决的回归记录
DELETE FROM performance_regressions 
WHERE status = 'resolved' 
AND resolved_at < NOW() - INTERVAL '90 days';
```

### 索引优化

定期重建索引以提高查询性能：

```sql
-- 重建索引
REINDEX TABLE performance_metrics;
REINDEX TABLE performance_baselines;
REINDEX TABLE performance_trends;
REINDEX TABLE performance_regressions;
```

### 表分析

定期分析表以更新统计信息：

```sql
-- 分析表
ANALYZE performance_metrics;
ANALYZE performance_baselines;
ANALYZE performance_trends;
ANALYZE performance_regressions;
```

## 故障排查

### 常见问题

**问题**: 性能数据采集失败
- **解决**: 检查数据库连接，确保表已创建

**问题**: 回归检测不准确
- **解决**: 检查基准线配置，确保阈值设置合理

**问题**: Grafana仪表板无数据
- **解决**: 检查Prometheus数据源配置，确保指标正常导出

**问题**: 报告生成超时
- **解决**: 优化查询，添加时间范围限制

## 扩展开发

### 添加新的性能指标

在 `core/models.py` 中添加新字段：

```python
class PerformanceMetric(Base):
    # 添加新字段
    new_metric = Column(Float, nullable=True)
```

### 添加新的报告类型

在 `core/performance_report_generator.py` 中添加新方法：

```python
async def generate_custom_report(self, **kwargs) -> Dict[str, Any]:
    """生成自定义报告"""
    # 实现报告生成逻辑
    pass
```

## 联系方式

- **性能团队**: perf-team@example.com
- **技术支持**: support@example.com

## 许可证

MIT License
